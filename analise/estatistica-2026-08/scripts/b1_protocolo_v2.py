"""B1 - Robustez com o protocolo de degradacao v2 (codigo/robustez-2026-11/).

Todos os pares conectados no original sobrevivem nos 5 padroes e nos 3 niveis (R1, R2), entao
as populacoes sao iguais e o P2 deixa de confundir a comparacao entre padroes.

A memoria aparece em dois regimes:
  com atualizacao  distancias dos pivos recalculadas no mapa degradado (exp_deg_mem, P1);
  sem atualizacao  distancias do mapa original (exp_deg_mem_congelado).
E duas metricas, ambas agregadas pela escada geometrica de comum (instancia -> (mapa, padrao)
-> mapa, padroes com peso igual) e com o mapa como unidade:
  delta     exp_deg / exp_orig da propria heuristica (perda relativa);
  absoluta  exp_heuristica / exp_manhattan no mesmo estado do mapa (menor = melhor; o ganho
            sobre a Manhattan e o inverso). Separa "o problema ficou dificil" de "a
            heuristica perdeu informacao", o que o delta sozinho nao faz.
Saida em tabelas_v2/ (ou tabelas_v2_fora_treino/ com FORA_TREINO=1).
"""
import sys, numpy as np, pandas as pd
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from comum import *
from figuras_comum import *
from scipy.stats import friedmanchisquare, wilcoxon
import statsmodels.formula.api as smf
from statsmodels.stats.anova import anova_lm

if not V2:
    raise SystemExit("b1 roda so com PROTOCOLO=v2")
TABELAS.mkdir(exist_ok=True)
FIGURAS.mkdir(exist_ok=True)

ESTRATEGIAS = ["Manhattan", "Fórmula"] + [f"Memória-{n}" for n in (10, 20, 50, 100)]
REGIMES = {"com_atualizacao": "deg_mem", "sem_atualizacao": "cong_mem"}
NOME_REGIME = {"com_atualizacao": "com atualização", "sem_atualizacao": "sem atualização"}
NIVEIS_ = {"10": [0.1], "20": [0.2], "30": [0.3], "todos": NIVEIS}
CHAVE = ["mapa", "semente", "id_problema", "tipo_degradacao", "porcentagem_bloqueio"]

# Uma linha por (par, padrao, nivel), com as expansoes de todas as estrategias lado a lado
rob = carregar_robustez()
W = rob[rob.n_pivos == 10].sort_values(CHAVE).reset_index(drop=True)
W = W[CHAVE + ["exp_orig_manh", "exp_deg_manh", "exp_orig_form", "exp_deg_form", "em_treino"]].copy()
for n in (10, 20, 50, 100):
    s = rob[rob.n_pivos == n].sort_values(CHAVE).reset_index(drop=True)
    for c in CHAVE:
        assert (s[c].values == W[c].values).all(), (n, c)
    W[f"orig_mem{n}"] = s.exp_orig_mem.values
    W[f"deg_mem{n}"] = s.exp_deg_mem.values
    W[f"cong_mem{n}"] = s.exp_deg_mem_congelado.values
del rob, s
print(f"instâncias × padrão × nível: {len(W)}   mapas: {W.mapa.nunique()}   "
      f"pares por (padrão, nível): {len(W) // 15}")

def colunas(regime, estado):
    """Expansoes de cada estrategia no estado 'orig' ou 'deg' do mapa."""
    if estado == "orig":
        mem = [f"orig_mem{n}" for n in (10, 20, 50, 100)]
        return ["exp_orig_manh", "exp_orig_form"] + mem
    return ["exp_deg_manh", "exp_deg_form"] + [f"{REGIMES[regime]}{n}" for n in (10, 20, 50, 100)]

def log_razao(df, metrica, regime, estado="deg"):
    """log da metrica por instancia, uma coluna por estrategia."""
    deg = np.log(df[colunas(regime, estado)].clip(lower=1).to_numpy(float))
    if metrica == "delta":
        v = deg - np.log(df[colunas(regime, "orig")].clip(lower=1).to_numpy(float))
    else:
        v = deg - deg[:, :1]
    return pd.DataFrame(v, columns=ESTRATEGIAS, index=df.index)

def por_mapa(df, lr):
    """Escada geometrica em log: (mapa, padrao) e depois mapa."""
    g = lr.assign(mapa=df.mapa.values, padrao=df.tipo_degradacao.values)
    return np.exp(g.groupby(["mapa", "padrao"]).mean().groupby("mapa").mean())

# Escore estatico por mapa: o mesmo par aparece 15 vezes em W, basta uma fatia
um = W[(W.tipo_degradacao == "Linear") & (W.porcentagem_bloqueio == 0.1)]
dij = carregar_dijkstra().set_index(["mapa", "id_problema"]).exp_dijkstra
dij = dij.reindex(pd.MultiIndex.from_arrays([um.mapa, um.id_problema])).to_numpy(float)
assert np.isfinite(dij).all()
estatico = {
    "delta": np.exp(pd.DataFrame(np.log(um[colunas(None, "orig")].clip(lower=1).to_numpy(float))
                                 - np.log(dij)[:, None], columns=ESTRATEGIAS)
                    .assign(mapa=um.mapa.values, semente=um.semente.values)
                    .groupby(["mapa", "semente"]).mean().groupby("mapa").mean()),
    "absoluta": np.exp(log_razao(um, "absoluta", None, "orig")
                       .assign(mapa=um.mapa.values, semente=um.semente.values)
                       .groupby(["mapa", "semente"]).mean().groupby("mapa").mean()),
}

def friedman(tab):
    chi, p = friedmanchisquare(*[tab[c].values for c in tab.columns])
    return tab.rank(axis=1).mean(), chi, p, nemenyi_cd(tab.shape[1], tab.shape[0])

# ------------------------------------------------ 1. escores, IC, postos, Cliff
linhas_pm, linhas_gl, linhas_po, linhas_fr, linhas_cl, linhas_pn = [], [], [], [], [], []
for metrica in ("delta", "absoluta"):
    p_est, chi_e, pe, cd = friedman(estatico[metrica])
    linhas_fr.append(dict(metrica=metrica, regime="-", nivel="estatico", chi2=chi_e, p=pe, cd=cd,
                          n_mapas=len(estatico[metrica])))
    for regime in REGIMES:
        for rot, nvs in NIVEIS_.items():
            df = W[W.porcentagem_bloqueio.isin(nvs)]
            lr = log_razao(df, metrica, regime)
            pm = por_mapa(df, lr)
            for m, lin in pm.iterrows():
                for e in ESTRATEGIAS:
                    linhas_pm.append(dict(metrica=metrica, regime=regime, nivel=rot, mapa=m,
                                          estrategia=e, valor=lin[e]))
            for e in ESTRATEGIAS:
                lo, hi = bootstrap_bca_geom(pm[e].values) if pm[e].nunique() > 1 else (np.nan, np.nan)
                linhas_gl.append(dict(metrica=metrica, regime=regime, nivel=rot, estrategia=e,
                                      media_geometrica=media_geometrica(pm[e]), ic95_bca_inf=lo,
                                      ic95_bca_sup=hi, mapas_menor_que_manhattan=int((pm[e] < pm["Manhattan"]).sum()),
                                      mapas_melhor_de_todas=int((pm.idxmin(axis=1) == e).sum()),
                                      n_mapas=len(pm)))
            p_deg, chi, p, cd = friedman(pm)
            linhas_fr.append(dict(metrica=metrica, regime=regime, nivel=rot, chi2=chi, p=p, cd=cd,
                                  n_mapas=len(pm)))
            for e in ESTRATEGIAS:
                linhas_po.append(dict(metrica=metrica, regime=regime, nivel=rot, estrategia=e,
                                      posto_estatico=p_est[e], posto_degradado=p_deg[e],
                                      variacao=p_deg[e] - p_est[e]))
            for a, b in (("Manhattan", "Memória-100"), ("Fórmula", "Memória-100"), ("Fórmula", "Manhattan")):
                if metrica == "absoluta" and "Manhattan" == a:
                    w_p = wilcoxon(pm[b] - 1).pvalue
                else:
                    w_p = wilcoxon(pm[a], pm[b]).pvalue
                d = cliffs_delta(pm[a], pm[b])
                linhas_cl.append(dict(metrica=metrica, regime=regime, nivel=rot, a=a, b=b,
                                      cliff_delta=d, magnitude=magnitude_cliff(d), wilcoxon_p=w_p,
                                      n_mapas=len(pm)))
            if rot != "todos":
                g = lr.assign(mapa=df.mapa.values, padrao=df.tipo_degradacao.values)
                pp = g.groupby(["mapa", "padrao"]).mean().groupby("padrao").mean()
                for pad, lin in np.exp(pp).iterrows():
                    for e in ESTRATEGIAS:
                        linhas_pn.append(dict(metrica=metrica, regime=regime, nivel=rot, padrao=pad,
                                              estrategia=e, valor=lin[e]))
    for e in ESTRATEGIAS:
        linhas_pm += [dict(metrica=metrica, regime="-", nivel="estatico", mapa=m, estrategia=e, valor=v)
                      for m, v in estatico[metrica][e].items()]

PM, GL, PO = pd.DataFrame(linhas_pm), pd.DataFrame(linhas_gl), pd.DataFrame(linhas_po)
FR, CL, PN = pd.DataFrame(linhas_fr), pd.DataFrame(linhas_cl), pd.DataFrame(linhas_pn)
for nome, t in (("por_mapa", PM), ("global", GL), ("postos", PO), ("friedman", FR),
                ("cliff", CL), ("padrao_nivel", PN)):
    t.to_csv(TABELAS / f"b1_{nome}.csv", index=False)

for metrica, titulo in (("delta", "δ = exp_deg / exp_orig (menor = menos degradada)"),
                        ("absoluta", "razão absoluta = exp_heurística / exp_Manhattan no mapa degradado "
                                     "(menor = melhor; ganho = 1/razão)")):
    print(f"\n=== {titulo} ===")
    t = GL[GL.metrica == metrica].pivot_table(index=["regime", "nivel"], columns="estrategia",
                                               values="media_geometrica")[ESTRATEGIAS]
    print(t.round(3).to_string())
    print("\n  postos (estático -> degradado, todos os níveis):")
    for regime in REGIMES:
        q = PO[(PO.metrica == metrica) & (PO.regime == regime) & (PO.nivel == "todos")].set_index("estrategia")
        print(f"   {NOME_REGIME[regime]:<16}", "  ".join(
            f"{e}={q.posto_estatico[e]:.2f}->{q.posto_degradado[e]:.2f}" for e in ESTRATEGIAS))
    print("\n  Friedman:")
    print(FR[FR.metrica == metrica].round(4).to_string(index=False))
    print("\n  Cliff e Wilcoxon (unidade = mapa):")
    print(CL[(CL.metrica == metrica)].round(3).to_string(index=False))

est_abs = estatico["absoluta"]
print("\n=== ganho estático sobre a Manhattan (1/razão absoluta) ===")
print({e: round(1 / media_geometrica(est_abs[e]), 2) for e in ESTRATEGIAS})

# ------------------------------------------------ 2. figura: diagramas CD, estatico x dois regimes
for metrica in ("delta", "absoluta"):
    fig, axes = plt.subplots(3, 1, figsize=(3.35, 4.3))
    p_est, _, _, cd = friedman(estatico[metrica])
    diagrama_cd(axes[0], p_est.values, cd, p_est.index.tolist(), "(a) Cenário estático")
    for ax, regime, letra in zip(axes[1:], REGIMES, "bc"):
        q = PO[(PO.metrica == metrica) & (PO.regime == regime) & (PO.nivel == "todos")].set_index("estrategia")
        cd_r = FR[(FR.metrica == metrica) & (FR.regime == regime) & (FR.nivel == "todos")].cd.iloc[0]
        diagrama_cd(ax, q.posto_degradado.values, cd_r, q.index.tolist(),
                    f"({letra}) Degradado, memória {NOME_REGIME[regime]}")
    fig.subplots_adjust(hspace=0.30)
    salvar(fig, f"fig_b1_cd_{metrica}", FIGURAS)

# ------------------------------------------------ 3. interacao estrategia x padrao
print("\n=== Interação estratégia × padrão (células mapa × semente × padrão × nível) ===")
NPERM = 200
cod, cel = pd.factorize(pd.Series(list(zip(W.mapa, W.semente, W.tipo_degradacao, W.porcentagem_bloqueio))))
ncel = len(cel)
cnt = np.bincount(cod, minlength=ncel)
meta = pd.DataFrame(list(cel), columns=["mapa", "semente", "padrao", "nivel"])

def anova(M, nomes):
    medias = np.stack([np.bincount(cod, weights=M[:, j], minlength=ncel) for j in range(M.shape[1])],
                      axis=1) / cnt[:, None]
    c = pd.DataFrame(medias, columns=nomes).join(meta).melt(
        id_vars=["mapa", "semente", "padrao", "nivel"], var_name="estrategia", value_name="y")
    av = anova_lm(smf.ols("y ~ C(estrategia)*C(padrao)*C(nivel) + C(mapa)", data=c).fit(), typ=2)
    av["eta2_parcial"] = av.sum_sq / (av.sum_sq + av.loc["Residual", "sum_sq"])
    return av

linhas_in = []
for metrica in ("delta", "absoluta"):
    nomes = ESTRATEGIAS if metrica == "delta" else ESTRATEGIAS[1:]
    for regime in REGIMES:
        M = log_razao(W, metrica, regime)[nomes].to_numpy()
        av = anova(M, nomes)
        termo = "C(estrategia):C(padrao)"
        F_obs = av.loc[termo, "F"]
        rng = np.random.default_rng(SEED)
        nulos = np.array([anova(rng.permuted(M, axis=1), nomes).loc[termo, "F"] for _ in range(NPERM)])
        p_perm = (1 + (nulos >= F_obs).sum()) / (1 + NPERM)
        linhas_in.append(dict(metrica=metrica, regime=regime, F=F_obs, p_anova=av.loc[termo, "PR(>F)"],
                              eta2_parcial=av.loc[termo, "eta2_parcial"], p_permutacao=p_perm,
                              n_permutacoes=NPERM, F_nulo_max=nulos.max(),
                              eta2_parcial_estrategia=av.loc["C(estrategia)", "eta2_parcial"],
                              eta2_parcial_estrategia_nivel=av.loc["C(estrategia):C(nivel)", "eta2_parcial"]))
        print(f"  {metrica:<8} {NOME_REGIME[regime]:<16} F={F_obs:8.2f}  η²ₚ={av.loc[termo, 'eta2_parcial']:.3f}"
              f"  p_perm={p_perm:.4f} (nulo máx {nulos.max():.2f})")
pd.DataFrame(linhas_in).to_csv(TABELAS / "b1_interacao.csv", index=False)

# ------------------------------------------------ 4. degradacao: sobrevivencia, meta, rejeicao, pivos
res = pd.read_csv(MEDICOES / "degradacao_v2_resumo.csv")
S = celulas_transitaveis().set_index("mapa").S
res["S"] = res.mapa.map(S)
res["bloqueadas"] = (res.pct_atingido * res.S).round()
res["alvo"] = (res.S * res.nivel).astype(int)
assert (res.bloqueadas >= res.alvo).all(), "alguma combinacao ficou abaixo do alvo inteiro"
g = res.groupby(["padrao", "nivel"])
total = 116050
sob = pd.DataFrame({"pares_v2": g.pares_validos.sum(), "pares_v1": g.pares_validos_v1.sum()})
sob["taxa_v2"], sob["taxa_v1"] = sob.pares_v2 / total, sob.pares_v1 / total
a10 = pd.read_csv(RAIZ / "tabelas" / "a10_sobrevivencia_por_padrao.csv").set_index("tipo_degradacao")
v1_30 = sob.xs(0.3, level="nivel").pares_v1
assert (v1_30 == a10.sobreviventes.reindex(v1_30.index)).all(), (v1_30, a10.sobreviventes)
print("\n=== Sobrevivência dos pares: v1 (gerador de março, mesmas sementes) × v2 ===")
print("    v1 a 30% confere com tabelas/a10_sobrevivencia_por_padrao.csv")
print((sob[["taxa_v1", "taxa_v2"]] * 100).round(2).unstack("nivel").to_string())
sob.to_csv(TABELAS / "b1_sobrevivencia_v1_v2.csv")

rej = pd.DataFrame({
    "bloqueadas_pct_S": 100 * g.bloqueadas.sum() / g.S.sum(),
    "bloqueadas_pct_S_v1": 100 * (g.apply(lambda x: (x.pct_atingido_v1 * x.S).sum(), include_groups=False)
                                  / g.S.sum()),
    "r1_pct_S": 100 * g.rejeitadas_r1.sum() / g.S.sum(),
    "r2_pct_S": 100 * g.rejeitadas_r2.sum() / g.S.sum(),
    "r2_pct_bloqueadas": 100 * g.rejeitadas_r2.sum() / g.bloqueadas.sum(),
    "tentativas_r2_pct_bloqueadas": 100 * g.tentativas_r2.sum() / g.bloqueadas.sum(),
    "combinacoes": g.size()})
print("\n=== Bloqueio atingido e rejeições (células distintas, somadas em mapas e sementes) ===")
print(rej.round(2).to_string())
rej.to_csv(TABELAS / "b1_rejeicao.csv")

piv = pd.read_csv(MEDICOES / "pivos_bloqueados_v2.csv")
pb = piv.groupby(["protocolo", "padrao", "nivel"]).agg(
    pivos=("pivos", "sum"), bloqueados=("pivos_bloqueados", "sum"),
    sem_vizinho=("bloqueados_sem_vizinho", "sum"))
pb["pct_bloqueados"] = 100 * pb.bloqueados / pb.pivos
pb["pct_sem_vizinho"] = 100 * pb.sem_vizinho / pb.pivos
print("\n=== Pivôs em célula bloqueada (bfsPivo não confere grid[pivô]) ===")
print(pb.round(2).to_string())
pb.to_csv(TABELAS / "b1_pivos_bloqueados.csv")

col = res[res.colapso_pivo == "sim"][["mapa", "semente", "pivos_colapsados"]].drop_duplicates()
print("\n=== Colapso de pivô (P8, mantido): (mapa, semente) afetados ===")
print(col.to_string(index=False))
col.to_csv(TABELAS / "b1_colapso_pivo.csv", index=False)
