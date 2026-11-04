"""B9 - Conferencias pedidas para o JBCS, nos dados v2 ja gerados (sem experimento novo).

  1. rho <= w no Weighted A*: A* sem reabrir fechados, h = floor(w * Manhattan). Pares que violam e maior
     rho / w, no original e no degradado (pares fora do treino, os da avaliacao do b7).
  2. Caminho da calibracao do w: mapas que passaram da grade 1,1..3, ate que peso foram, onde a GBFS virou teto.
  3. Os 174.075 pares conferidos contra a BFS no degradado: de onde sai o numero.
  4. Farthest-first esgotando a componente do primeiro pivo (medido por incremental_v2, tabela do b8).
  5. Pivo em celula bloqueada no regime atualizado, e se aparece caminho maior que o otimo nesses casos.
  6. Teste de permutacao da interacao estrategia x padrao do b1 com 10.000 permutacoes (b1 usou 200), nos dois
     recortes. F por projecoes (QR) no lugar do OLS do statsmodels; com 200 permutacoes e a mesma semente o
     p tem que reproduzir o do b1, o que confere o atalho.
  7. Correlacao rank-biserial pareada ao lado do delta de Cliff para todo Wilcoxon pareado (b1, b4, b7).
Roda so no recorte tabelas_v2 e le os dois recortes onde for o caso.
"""
import sys, numpy as np, pandas as pd
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from comum import *
from comum import _robustez_v2
from scipy.stats import wilcoxon, rankdata
import patsy

if not V2 or FORA_TREINO:
    raise SystemExit("b9 roda so com PROTOCOLO=v2, sem FORA_TREINO (le os dois recortes)")
TABELAS.mkdir(exist_ok=True)
T_FT = RAIZ / "tabelas_v2_fora_treino"
NPERM = int(os.environ.get("NPERM_B9", 10000))
resumo = []

def registra(item, resposta, **numeros):
    resumo.append(dict(item=item, resposta=resposta, **{k: v for k, v in numeros.items()}))
    print(f"\n[{item}] {resposta}")

# ---------------------------------------------------------------- base: otimos por par
r = _robustez_v2()
r10 = r[r.n_pivos == 10][["mapa", "semente", "id_problema", "tipo_degradacao", "porcentagem_bloqueio",
                          "path_orig_manh", "path_deg_manh", "em_treino"]].copy()
r10["mapa"] = r10.mapa.astype(str)
r10["tipo_degradacao"] = r10.tipo_degradacao.astype(str)

# ---------------------------------------------------------------- 1. rho <= w
AVAL = pd.read_csv(DADOS_V2 / "wastar_aval.csv")
AVAL["porcentagem_bloqueio"] = AVAL.porcentagem_bloqueio.round(1)
ORIG = pd.read_csv(DADOS_V2 / "wastar_orig.csv")
otimo_orig = r10[(r10.semente == 42) & (r10.tipo_degradacao == "Linear") & (r10.porcentagem_bloqueio == 0.1)][
    ["mapa", "id_problema", "path_orig_manh"]]
o = ORIG.merge(otimo_orig, on=["mapa", "id_problema"], how="left")
d = AVAL.merge(r10[["mapa", "semente", "id_problema", "tipo_degradacao", "porcentagem_bloqueio", "path_deg_manh"]],
               on=["mapa", "semente", "id_problema", "tipo_degradacao", "porcentagem_bloqueio"], how="left")
assert o.path_orig_manh.notna().all() and d.path_deg_manh.notna().all()
linhas = []
for rot, df, ot in (("original", o, "path_orig_manh"), ("degradado", d, "path_deg_manh")):
    df = df[np.isfinite(df.w) & (df[ot] > 0)]
    rho = df.path / df[ot]
    ratio = rho / df.w
    linhas.append(dict(estado=rot, pares_avaliados=len(df), violam=int((rho > df.w + 1e-12).sum()),
                       maior_rho_sobre_w=ratio.max(), maior_rho=rho.max(),
                       w_do_maior=df.w.iloc[int(np.argmax(ratio.values))]))
C1 = pd.DataFrame(linhas)
C1.to_csv(TABELAS / "b9_c1_rho_menor_que_w.csv", index=False)
print(C1.to_string(index=False))
registra("1 rho <= w", "; ".join(f"{x.estado}: {x.violam} de {x.pares_avaliados:,} violam, maior rho/w = "
                                  f"{x.maior_rho_sobre_w:.4f}" for x in C1.itertuples()),
         violam_original=int(C1.violam[0]), violam_degradado=int(C1.violam[1]),
         max_rho_w_original=C1.maior_rho_sobre_w[0], max_rho_w_degradado=C1.maior_rho_sobre_w[1])
del AVAL, d

# ---------------------------------------------------------------- 2. calibracao do w
P = pd.read_csv(DADOS_V2 / "wastar_pesos.csv")
CAL = pd.read_csv(DADOS_V2 / "wastar_calibracao.csv")
fin = CAL[np.isfinite(CAL.w)].groupby("mapa").w.max().rename("maior_w_finito_testado")
C2 = P[["mapa", "categoria", "grade_ampliada", "w_inf", "w_estrela", "w_sup"]].merge(fin, on="mapa")
C2["gbfs_e_teto"] = C2.categoria.isin(["casado_gbfs", "fora_da_curva"])
C2.to_csv(TABELAS / "b9_c2_calibracao_w.csv", index=False)
alem = C2[C2.grade_ampliada == 1]
print(alem.to_string(index=False))
registra("2 calibracao do w",
         f"{len(alem)} de 17 mapas passaram de w = 3 ({', '.join(f'{x.mapa} ate {x.maior_w_finito_testado:g}' for x in alem.itertuples())}); "
         f"GBFS como teto em {int(C2.gbfs_e_teto.sum())}: "
         f"{', '.join(f'{x.mapa} ({x.categoria})' for x in C2[C2.gbfs_e_teto].itertuples())}",
         mapas_ampliados=len(alem), mapas_gbfs_teto=int(C2.gbfs_e_teto.sum()))

# ---------------------------------------------------------------- 3. os 174.075 pares
OT = carregar_complemento("otimo")
OT["porcentagem_bloqueio"] = OT.porcentagem_bloqueio.round(1)
k = OT.merge(r10, on=["mapa", "semente", "id_problema", "tipo_degradacao", "porcentagem_bloqueio"])
iguais = int((k.dist_bfs == k.path_deg_manh).sum())
por_mapa = OT.groupby("mapa").id_problema.nunique()
C3 = pd.DataFrame(dict(pares_id_mod_10=por_mapa, linhas=OT.groupby("mapa").size()))
C3.to_csv(TABELAS / "b9_c3_pares_bfs.csv")
registra("3 os 174.075 pares",
         f"{len(OT):,} linhas = {por_mapa.sum():,} pares com id % 10 == 0 (17 mapas; validos = todos no v2) x "
         f"5 sementes x 5 padroes x 3 niveis; {iguais:,} com caminho da Manhattan = BFS",
         linhas=len(OT), pares=int(por_mapa.sum()), iguais=iguais)

# ---------------------------------------------------------------- 4. farthest-first fora da componente
PF = pd.read_csv(RAIZ / "tabelas_v2" / "b8_pivos_fora_componente.csv")
fora = PF[PF.pivos_fora_comp_primeiro > 0]
fora[["mapa", "semente", "n_pivos", "pivos_fora_comp_primeiro", "tamanho_comp_primeiro"]].to_csv(
    TABELAS / "b9_c4_pivos_fora_componente.csv", index=False)
print(fora[["mapa", "semente", "n_pivos", "pivos_fora_comp_primeiro", "tamanho_comp_primeiro"]].to_string(index=False))
registra("4 farthest-first fora da componente",
         f"{len(fora)} de {len(PF)} combinacoes (mapa, semente, n) sortearam pivo fora da componente do primeiro; "
         f"mapas: {', '.join(sorted(fora.mapa.unique())) or 'nenhum'}",
         combinacoes=len(fora), total=len(PF))

# ---------------------------------------------------------------- 5. pivo bloqueado e admissibilidade
PB = pd.read_csv(MEDICOES / "pivos_bloqueados_v2.csv")
PB = PB[PB.protocolo == "v2"]
PB["nivel"] = PB.nivel.round(1)
com_bloq = PB[PB.pivos_bloqueados > 0]
rr = r[["mapa", "semente", "id_problema", "tipo_degradacao", "porcentagem_bloqueio", "n_pivos",
        "path_deg_mem", "path_deg_manh"]].copy()
rr["mapa"] = rr.mapa.astype(str)
rr["tipo_degradacao"] = rr.tipo_degradacao.astype(str)
rr["porcentagem_bloqueio"] = rr.porcentagem_bloqueio.round(1)
rr = rr.merge(PB.rename(columns={"padrao": "tipo_degradacao", "nivel": "porcentagem_bloqueio"})[
    ["mapa", "semente", "tipo_degradacao", "porcentagem_bloqueio", "n_pivos", "pivos_bloqueados"]],
    on=["mapa", "semente", "tipo_degradacao", "porcentagem_bloqueio", "n_pivos"], how="left")
assert rr.pivos_bloqueados.notna().all()
viol = rr[rr.path_deg_mem > rr.path_deg_manh]
C5 = pd.DataFrame([dict(combinacoes=len(PB), combinacoes_com_pivo_bloqueado=len(com_bloq),
                        pares_nessas_combinacoes=int((rr.pivos_bloqueados > 0).sum()),
                        caminhos_maiores_que_otimo_nessas=int((viol.pivos_bloqueados > 0).sum()),
                        caminhos_maiores_que_otimo_total=len(viol), pares_total=len(rr))])
C5.to_csv(TABELAS / "b9_c5_pivo_bloqueado.csv", index=False)
registra("5 pivo em celula bloqueada",
         f"{len(com_bloq):,} de {len(PB):,} combinacoes (mapa, semente, padrao, nivel, n) tem pivo bloqueado; "
         f"nelas, {int((viol.pivos_bloqueados > 0).sum())} de {int((rr.pivos_bloqueados > 0).sum()):,} caminhos da "
         f"memoria atualizada saem maiores que o otimo (em todos os pares: {len(viol)} de {len(rr):,})",
         combinacoes_com_bloqueio=len(com_bloq), violacoes=len(viol))
del rr, r

# ---------------------------------------------------------------- 6. permutacao com 10.000
ESTRATEGIAS = ["Manhattan", "Fórmula"] + [f"Memória-{n}" for n in (10, 20, 50, 100)]
REGIMES = {"com_atualizacao": "deg_mem", "sem_atualizacao": "cong_mem"}
CHAVE = ["mapa", "semente", "id_problema", "tipo_degradacao", "porcentagem_bloqueio"]

def monta_W(fora_treino):
    rob = _robustez_v2()
    if fora_treino:
        rob = rob[rob.em_treino == 0]
    W = rob[rob.n_pivos == 10].sort_values(CHAVE).reset_index(drop=True)
    W = W[CHAVE + ["exp_orig_manh", "exp_deg_manh", "exp_orig_form", "exp_deg_form"]].copy()
    for n in (10, 20, 50, 100):
        s = rob[rob.n_pivos == n].sort_values(CHAVE).reset_index(drop=True)
        assert (s.id_problema.values == W.id_problema.values).all()
        W[f"orig_mem{n}"], W[f"deg_mem{n}"], W[f"cong_mem{n}"] = (s.exp_orig_mem.values, s.exp_deg_mem.values,
                                                                  s.exp_deg_mem_congelado.values)
    W["mapa"] = W.mapa.astype(str)
    W["tipo_degradacao"] = W.tipo_degradacao.astype(str)
    return W

def log_razao(W, metrica, regime):
    cols = lambda est: (["exp_orig_manh", "exp_orig_form"] + [f"orig_mem{n}" for n in (10, 20, 50, 100)]
                        if est == "orig" else
                        ["exp_deg_manh", "exp_deg_form"] + [f"{REGIMES[regime]}{n}" for n in (10, 20, 50, 100)])
    deg = np.log(W[cols("deg")].clip(lower=1).to_numpy(float))
    v = deg - (np.log(W[cols("orig")].clip(lower=1).to_numpy(float)) if metrica == "delta" else deg[:, :1])
    return v

def proj(X):
    """Base ortonormal do espaco coluna de X (QR com pivoteamento; descarta colunas redundantes)."""
    import scipy.linalg as sl
    Q, R, _ = sl.qr(X, mode="economic", pivoting=True)
    rank = int((np.abs(np.diag(R)) > 1e-9 * abs(R[0, 0])).sum())
    return Q[:, :rank], rank

def permutacao(W, nomes_rot):
    cod, cel = pd.factorize(pd.Series(list(zip(W.mapa, W.semente, W.tipo_degradacao, W.porcentagem_bloqueio))))
    ncel, cnt = len(cel), np.bincount(cod, minlength=len(cel))
    meta = pd.DataFrame(list(cel), columns=["mapa", "semente", "padrao", "nivel"])
    out = []
    for metrica in ("delta", "absoluta"):
        idx = list(range(6)) if metrica == "delta" else list(range(1, 6))
        nomes = [ESTRATEGIAS[i] for i in idx]
        long = meta.loc[np.repeat(np.arange(ncel), len(nomes))].reset_index(drop=True)
        long["estrategia"] = np.tile(nomes, ncel)
        termos = {"full": "C(estrategia)*C(padrao)*C(nivel) + C(mapa)",
                  "aug": "(C(estrategia)+C(padrao)+C(nivel))**2 + C(mapa)",
                  "red": "C(estrategia)+C(padrao)+C(nivel)+C(estrategia):C(nivel)+C(padrao):C(nivel)+C(mapa)"}
        Qs = {k: proj(np.asarray(patsy.dmatrix(f, long), float)) for k, f in termos.items()}
        n = len(long)
        df_ab = Qs["aug"][1] - Qs["red"][1]
        df_res = n - Qs["full"][1]
        def F(M):
            med = np.stack([np.bincount(cod, weights=M[:, j], minlength=ncel) for j in range(M.shape[1])],
                           axis=1) / cnt[:, None]
            y = med.reshape(-1)
            yy = y @ y
            rss = {k: yy - np.sum((Q.T @ y) ** 2) for k, (Q, _) in Qs.items()}
            return ((rss["red"] - rss["aug"]) / df_ab) / (rss["full"] / df_res)
        for regime in REGIMES:
            M = log_razao(W, metrica, regime)[:, idx]
            F_obs = F(M)
            rng = np.random.default_rng(SEED)
            nulos = np.array([F(rng.permuted(M, axis=1)) for _ in range(NPERM)])
            p200 = (1 + (nulos[:200] >= F_obs).sum()) / 201
            out.append(dict(recorte=nomes_rot, metrica=metrica, regime=regime, F=F_obs, df_interacao=df_ab,
                            df_residuo=df_res, p_permutacao_200=p200,
                            p_permutacao=(1 + (nulos >= F_obs).sum()) / (1 + NPERM), n_permutacoes=NPERM,
                            F_nulo_max=nulos.max(), F_nulo_p99=np.quantile(nulos, 0.99)))
            print(f"  {nomes_rot:<16} {metrica:<8} {regime:<16} F={F_obs:8.3f} p_200={p200:.5f} "
                  f"p_{NPERM}={out[-1]['p_permutacao']:.6f} (nulo max {nulos.max():.3f})", flush=True)
    return out

print("\n=== 6. Interação estratégia × padrão: permutação com", NPERM, "===")
perm = []
for rot, ft, tdir in (("todos os pares", False, RAIZ / "tabelas_v2"), ("fora do treino", True, T_FT)):
    res = permutacao(monta_W(ft), rot)
    b1 = pd.read_csv(tdir / "b1_interacao.csv").set_index(["metrica", "regime"])
    for x in res:
        ref = b1.loc[(x["metrica"], x["regime"])]
        assert np.isclose(x["F"], ref.F, rtol=1e-6), (x, ref.F)
        x["p_permutacao_b1"] = ref.p_permutacao
        x["confere_b1"] = bool(np.isclose(x["p_permutacao_200"], ref.p_permutacao))
    perm += res
C6 = pd.DataFrame(perm)
C6.to_csv(TABELAS / "b9_c6_permutacao_10000.csv", index=False)
muda = C6[(C6.p_permutacao < 0.05) != (C6.p_permutacao_b1 < 0.05)]
registra("6 permutacao com 10.000",
         f"F do atalho = F do b1 em todas as {len(C6)} linhas; p com 200 reproduz o b1 em "
         f"{int(C6.confere_b1.sum())} de {len(C6)}; com {NPERM:,} permutacoes, p = "
         f"{', '.join(sorted({f'{p:.5f}' for p in C6.p_permutacao}))}; conclusoes que mudam a 5%: {len(muda)}",
         linhas=len(C6), mudam=len(muda))

# ---------------------------------------------------------------- 7. rank-biserial pareada
def rank_biserial(a, b):
    """r = (W+ - W-) / (W+ + W-), diferencas a - b, zeros descartados (como o wilcoxon padrao do scipy)."""
    dd = np.asarray(a, float) - np.asarray(b, float)
    dd = dd[dd != 0]
    if not len(dd):
        return np.nan
    rk = rankdata(np.abs(dd))
    return float((rk[dd > 0].sum() - rk[dd < 0].sum()) / rk.sum())

linhas = []
for rot, tdir in (("todos os pares", RAIZ / "tabelas_v2"), ("fora do treino", T_FT)):
    pm = pd.read_csv(tdir / "b1_por_mapa.csv", dtype={"nivel": str})
    cl = pd.read_csv(tdir / "b1_cliff.csv", dtype={"nivel": str})
    for x in cl.itertuples():
        t = pm[(pm.metrica == x.metrica) & (pm.regime == x.regime) & (pm.nivel == x.nivel)].pivot(
            index="mapa", columns="estrategia", values="valor")
        a, b = t[x.a], t[x.b]
        pw = wilcoxon(b - 1).pvalue if (x.metrica == "absoluta" and x.a == "Manhattan") else wilcoxon(a, b).pvalue
        assert np.isclose(pw, x.wilcoxon_p), (x, pw)
        linhas.append(dict(fonte="b1", recorte=rot, comparacao=f"{x.a} x {x.b}",
                           contexto=f"{x.metrica}, {x.regime}, nivel {x.nivel}", n_mapas=len(t),
                           wilcoxon_p=x.wilcoxon_p, wilcoxon_p_holm=x.wilcoxon_p_holm, cliff_delta=x.cliff_delta,
                           rank_biserial_pareada=rank_biserial(a, b)))
    sp = pd.read_csv(tdir / "b4_spearman_por_mapa.csv").pivot(index="mapa", columns="heuristica", values="spearman")
    for x in pd.read_csv(tdir / "b4_wilcoxon.csv").itertuples():
        a, b = sp[x.memoria], sp[x.referencia]
        assert np.isclose(wilcoxon(a, b).pvalue, x.wilcoxon_p)
        linhas.append(dict(fonte="b4", recorte=rot, comparacao=f"{x.memoria} x {x.referencia}",
                           contexto="spearman(desvio, aumento de expansoes)", n_mapas=len(a),
                           wilcoxon_p=x.wilcoxon_p, wilcoxon_p_holm=x.wilcoxon_p_holm,
                           cliff_delta=cliffs_delta(a, b), rank_biserial_pareada=rank_biserial(a, b)))
LG = pd.read_csv(RAIZ / "tabelas_v2" / "wastar_decisao.csv")
for x in pd.read_csv(RAIZ / "tabelas_v2" / "wastar_estatistica.csv").itertuples():
    q = LG[LG.cenario == x.cenario]
    if x.recorte.startswith("rho casado"):
        q = q[q.categoria != "fora_da_curva"]
        ec, rc = q.exp_w_estrela, q.rho_w_estrela
    else:
        ff = q.categoria == "fora_da_curva"
        ec, rc = np.where(ff, q.exp_gbfs, q.exp_w_estrela), np.where(ff, q.rho_gbfs, q.rho_w_estrela)
    assert np.isclose(wilcoxon(q.exp_formula, ec).pvalue, x.wilcoxon_p)
    for alvo, a, b, p, ph, cd in (("expansoes", q.exp_formula, ec, x.wilcoxon_p, x.wilcoxon_p_holm, x.cliff_delta),
                                  ("rho", q.rho_formula, rc, x.wilcoxon_rho_p, x.wilcoxon_rho_p_holm,
                                   x.cliff_delta_rho)):
        linhas.append(dict(fonte="b7", recorte="fora do treino (desenho do b7)",
                           comparacao=f"Fórmula x WA* ({x.recorte})", contexto=f"{alvo}, {x.cenario}",
                           n_mapas=len(q), wilcoxon_p=p, wilcoxon_p_holm=ph, cliff_delta=cd,
                           rank_biserial_pareada=rank_biserial(a, b)))
EF = pd.DataFrame(linhas)
EF["magnitude_cliff"] = EF.cliff_delta.map(magnitude_cliff)
EF["mesmo_sinal"] = np.sign(EF.cliff_delta) == np.sign(EF.rank_biserial_pareada)
EF.to_csv(TABELAS / "efeito_pareado.csv", index=False)
registra("7 rank-biserial pareada",
         f"{len(EF)} Wilcoxon pareados (b1, b4, b7) em tabelas_v2/efeito_pareado.csv; sinal igual ao do Cliff em "
         f"{int(EF.mesmo_sinal.sum())}; |r| mediano {EF.rank_biserial_pareada.abs().median():.2f} contra "
         f"|delta| mediano {EF.cliff_delta.abs().median():.2f}",
         testes=len(EF), mesmo_sinal=int(EF.mesmo_sinal.sum()))

pd.DataFrame(resumo).to_csv(TABELAS / "b9_resumo.csv", index=False)
