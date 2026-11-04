"""B10 - Teste 2 do JBCS: tempo por busca, tempo por visita da BFS e o c medido.

Dados: medicoes/tempo_busca_v2.csv e tempo_bfs_v2.csv (codigo/robustez-2026-11, make tempo && make juntar-tempo),
200 pares fora do treino por mapa (estratificados pelo comprimento otimo), no original e no Organic 30% s42,
mediana de 5 medicoes depois de 1 aquecimento, uma thread, preso a um nucleo. arena nao tem par fora do treino:
entra so nas BFS.

Duas medidas do tempo por expansao, por (mapa, heuristica, estado):
  razao     mediana sobre os pares de t / expansoes (a do prompt). Inclui o custo fixo de cada busca: o A* de
            marco aloca tres matrizes altura x largura por chamada, entao em buscas curtas a razao mede a alocacao.
  marginal  inclinacao de Theil-Sen de t contra expansoes: o custo de UMA expansao a mais. E o que entra no Q*,
            porque o custo fixo por busca e o mesmo para todas as heuristicas e se cancela em E_alt - E_mem.
c = tempo por expansao da memoria atualizada (Memoria-n, degradado) / tempo por visita da BFS de recalculo
(t das n BFS / celulas visitadas). c_marginal e o principal; c_razao vai junto como sensibilidade.
Q* com o c medido: Q*_total = U_total / (c * Delta E) e Q*_inc = U_inc / (c * Delta E), com U e Delta E do b3 e
do b8 (mesmas medias por mapa, nivel e n).
Q* em tempo: o modelo do b3 cobra o mesmo c de toda expansao. Em tempo, cada heuristica tem o seu custo marginal
tau por expansao (a memoria le k pivos por no), e o ponto de equilibrio vira
  Q*_tempo = U * tau_bfs / (E_alt * tau_alt - E_mem * tau_mem),
com tau_alt da formula ou da memoria congelada e tau_mem da memoria atualizada (degradado, por mapa e n). Se o
denominador nao e positivo, atualizar nunca compensa em tempo (Q* = inf).
Tempo como metrica: ganho sobre a Manhattan em tempo (media geometrica de t_manh / t_h sobre os pares, por mapa)
contra o mesmo ganho em expansoes nos mesmos pares, e a ordem das estrategias nas duas metricas.
"""
import sys, numpy as np, pandas as pd
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from comum import *
from figuras_comum import *
from scipy.stats import theilslopes

if not V2 or FORA_TREINO:
    raise SystemExit("b10 roda so com PROTOCOLO=v2, sem FORA_TREINO (os pares ja sao fora do treino)")
TABELAS.mkdir(exist_ok=True)
FIGURAS.mkdir(exist_ok=True)
FONTE = Path(os.environ.get("TEMPO_DIR", MEDICOES))
for f in ("tempo_busca_v2.csv", "tempo_bfs_v2.csv"):
    if not (FONTE / f).exists():
        raise SystemExit(f"\n{FONTE / f} nao encontrado. Gere com `make tempo` e `make juntar-tempo` em "
                         f"codigo/robustez-2026-11/ (sozinho na maquina).\n")
B = pd.read_csv(FONTE / "tempo_busca_v2.csv")
BFS = pd.read_csv(FONTE / "tempo_bfs_v2.csv")
amb = (FONTE / "tempo_ambiente.txt").read_text().strip() if (FONTE / "tempo_ambiente.txt").exists() else "?"
print(f"ambiente: {amb}")
B["exp"] = B.exp.clip(lower=1)
B["t_por_exp"] = B.t_mediana_ns / B.exp
BFS["t_por_visita"] = BFS.t_mediana_ns / BFS.visitas

# ---------------------------------------------------------------- 1. tempo por expansao
def por_grupo(g):
    sl = theilslopes(g.t_mediana_ns, g.exp) if g.exp.nunique() > 1 else (np.nan, np.nan, np.nan, np.nan)
    return pd.Series(dict(pares=len(g), t_por_exp_razao=g.t_por_exp.median(), t_por_exp_marginal=sl[0],
                          t_fixo_ns=sl[1], t_busca_mediana=g.t_mediana_ns.median(), exp_mediana=g.exp.median()))

TE = B.groupby(["mapa", "estado", "heuristica"]).apply(por_grupo, include_groups=False).reset_index()
TE.to_csv(TABELAS / "tempo_por_expansao.csv", index=False)
print("\n=== Tempo por expansão (ns), mediana entre os mapas ===")
print(TE.groupby(["estado", "heuristica"])[["t_por_exp_razao", "t_por_exp_marginal", "t_fixo_ns"]].median()
      .round(1).to_string())

# ---------------------------------------------------------------- 2. c medido
mem = TE[(TE.estado == "degradado") & TE.heuristica.str.fullmatch(r"mem\d+")].copy()
mem["n_pivos"] = mem.heuristica.str[3:].astype(int)
C = mem.merge(BFS[["mapa", "n_pivos", "visitas", "t_por_visita"]], on=["mapa", "n_pivos"])
C["c"] = C.t_por_exp_marginal / C.t_por_visita
C["c_razao"] = C.t_por_exp_razao / C.t_por_visita
C[["mapa", "n_pivos", "c", "c_razao", "t_por_exp_marginal", "t_por_exp_razao", "t_por_visita", "visitas"]] \
    .to_csv(TABELAS / "c_medido.csv", index=False)
CR = C.groupby("n_pivos")[["c", "c_razao"]].agg(["median", "min", "max", lambda s: s.quantile(.25),
                                                  lambda s: s.quantile(.75)])
CR.columns = [f"{a}_{b}".replace("<lambda_0>", "q1").replace("<lambda_1>", "q3") for a, b in CR.columns]
CR.to_csv(TABELAS / "c_medido_resumo.csv")
print("\n=== c = tempo por expansão da memória atualizada / tempo por visita da BFS ===")
print(CR.round(2).to_string())

# ---------------------------------------------------------------- 3. Q* com o c medido
b3 = pd.read_csv(TABELAS / "b3_equilibrio_por_mapa.csv")
b3 = b3[b3.c == 1][["mapa", "nivel", "n_pivos", "alternativa", "custo_atualizar", "economia_por_busca",
                    "exp_mem_atualizada", "exp_alternativa"]]
b8 = pd.read_csv(TABELAS / "b8_q_faixa_por_mapa.csv")
b8 = b8[b8.c.astype(str) == "1"][["mapa", "nivel", "n_pivos", "alternativa", "u_inc", "u_mud", "economia_por_busca"]]
b3["nivel"], b8["nivel"] = b3.nivel.round(1), b8.nivel.round(1)
Q = b3.merge(b8, on=["mapa", "nivel", "n_pivos", "alternativa"], suffixes=("", "_b8"))
assert np.allclose(Q.economia_por_busca, Q.economia_por_busca_b8)
Q = Q.merge(C[["mapa", "n_pivos", "c", "c_razao"]], on=["mapa", "n_pivos"])
for col, cc in (("", "c"), ("_c_razao", "c_razao")):
    den = Q[cc] * Q.economia_por_busca
    Q["q_total" + col] = np.where(Q.economia_por_busca > 0, Q.custo_atualizar / den, np.inf)
    Q["q_inc" + col] = np.where(Q.economia_por_busca > 0, Q.u_inc / den, np.inf)
    Q["q_mud" + col] = np.where(Q.economia_por_busca > 0, Q.u_mud / den, np.inf)
# Q* em tempo, com o custo marginal de cada heuristica
tau = TE[TE.estado == "degradado"].set_index(["mapa", "heuristica"]).t_por_exp_marginal
tv = BFS.set_index(["mapa", "n_pivos"]).t_por_visita
def q_tempo(r):
    alt = "formula" if r.alternativa == "formula" else f"mem{r.n_pivos}_congelada"
    den = r.exp_alternativa * tau[(r.mapa, alt)] - r.exp_mem_atualizada * tau[(r.mapa, f"mem{r.n_pivos}")]
    return (r.custo_atualizar * tv[(r.mapa, r.n_pivos)] / den if den > 0 else np.inf,
            r.u_inc * tv[(r.mapa, r.n_pivos)] / den if den > 0 else np.inf)
Q[["q_tempo_total", "q_tempo_inc"]] = Q.apply(q_tempo, axis=1, result_type="expand")
Q.to_csv(TABELAS / "tempo_q_estrela_c_medido.csv", index=False)
mil = lambda x: "inf" if not np.isfinite(x) else f"{x:,.0f}".replace(",", ".")
S = Q.groupby(["alternativa", "n_pivos"])[["q_inc", "q_mud", "q_total", "q_total_c_razao", "q_tempo_inc",
                                            "q_tempo_total"]].median()
S["combinacoes_sem_compensar_em_tempo"] = Q.groupby(["alternativa", "n_pivos"]).q_tempo_total.apply(
    lambda x: int(np.isinf(x).sum()))
S["combinacoes"] = Q.groupby(["alternativa", "n_pivos"]).size()
S.to_csv(TABELAS / "tempo_q_estrela_resumo.csv")
print("\n=== Q* com o c medido (mediana entre os mapas, todos os níveis) ===")
print(S.round(1).to_string())

# frase: por mapa, todos os niveis juntos, contra a formula; faixa = menor e maior mediana entre os n de pivos
t = Q[Q.alternativa == "formula"].groupby(["mapa", "n_pivos"]).agg(
    ui=("u_inc", "mean"), ut=("custo_atualizar", "mean"), eco=("economia_por_busca", "mean"), c=("c", "mean"))
t["q_inc"], t["q_total"] = t.ui / (t.c * t.eco), t.ut / (t.c * t.eco)
qn = t.groupby("n_pivos")[["q_inc", "q_total"]].median()
qlo, qhi = qn.min().min(), qn.max().max()
tt = Q[Q.alternativa == "formula"].groupby(["mapa", "n_pivos"]).q_tempo_total.median()
qt_n = tt.groupby("n_pivos").median()
nunca = tt.groupby("n_pivos").apply(lambda x: int(np.isinf(x).sum()))
abaixo10 = int((t.xs(100, level="n_pivos").q_inc < 10).sum())
cmin, cmax = CR["c_median"].min(), CR["c_median"].max()

# ---------------------------------------------------------------- 4. tempo como metrica
deg = B[B.estado == "degradado"]
largo = {}
for est in ("original", "degradado"):
    b = B[B.estado == est]
    pt = b.pivot_table(index=["mapa", "id_problema"], columns="heuristica", values="t_mediana_ns")
    pe = b.pivot_table(index=["mapa", "id_problema"], columns="heuristica", values="exp")
    largo[est] = (pt, pe)
linhas = []
NOMES = {"formula": "Fórmula", "wastar": "WA* (w*)", "gbfs": "GBFS",
         **{f"mem{n}": f"Memória-{n}" + (" com atualização" if True else "") for n in (10, 20, 50, 100)},
         **{f"mem{n}_congelada": f"Memória-{n} sem atualização" for n in (10, 20, 50, 100)}}
for est, (pt, pe) in largo.items():
    for h in pt.columns:
        if h == "manhattan":
            continue
        gt = np.exp(np.log(pt.manhattan / pt[h]).groupby("mapa").mean())
        ge = np.exp(np.log(pe.manhattan / pe[h]).groupby("mapa").mean())
        nome = NOMES[h] if est == "degradado" else NOMES[h].replace(" com atualização", "")
        linhas.append(dict(estado=est, estrategia=nome, ganho_tempo=media_geometrica(gt),
                           ganho_expansoes=media_geometrica(ge), mapas_tempo_ganha=int((gt > 1).sum()),
                           mapas_exp_ganha=int((ge > 1).sum()), n_mapas=len(gt)))
G = pd.DataFrame(linhas)
G["ordem_tempo"] = G.groupby("estado").ganho_tempo.rank(ascending=False).astype(int)
G["ordem_expansoes"] = G.groupby("estado").ganho_expansoes.rank(ascending=False).astype(int)
G.to_csv(TABELAS / "tempo_ganho_sobre_manhattan.csv", index=False)
print("\n=== Ganho sobre a Manhattan em tempo e em expansões (mesmos pares) ===")
print(G.sort_values(["estado", "ordem_expansoes"]).round(3).to_string(index=False))
# a ordem que importa: formula x memoria nos dois regimes, no degradado
foco = G[(G.estado == "degradado") & G.estrategia.str.match(r"Fórmula|Memória-100")]
igual = (foco.sort_values("ganho_tempo").estrategia.tolist() == foco.sort_values("ganho_expansoes").estrategia.tolist())
igual_todas = all((g.sort_values("ganho_tempo").estrategia.tolist() == g.sort_values("ganho_expansoes").estrategia.tolist())
                  for _, g in G.groupby("estado"))

frase = (f"Uma expansão do A* custa entre {cmin:.1f} e {cmax:.1f} visitas da BFS (c marginal, mediana entre os mapas "
         f"para 10 a 100 pivôs; dividindo o tempo da busca pelas expansões, com o custo fixo de cada busca, "
         f"{CR['c_razao_median'].min():.0f} a {CR['c_razao_median'].max():.0f}); com o c medido, o ponto de "
         f"equilíbrio contra a fórmula fica entre {mil(qlo)} e {mil(qhi)} buscas (medianas entre os mapas, de "
         f"{qn.index.min()} a {qn.index.max()} pivôs, incremental ideal a recálculo completo; cobrando de cada "
         f"heurística o seu próprio custo por expansão, {', '.join(f'{mil(v)} com {n}' for n, v in qt_n.items())} "
         f"pivôs, e atualizar nunca compensa em {', '.join(f'{v} mapas com {n}' for n, v in nunca.items() if v)}"
         f"{'' if nunca.sum() else 'nenhum mapa'}); a ordem entre fórmula e Memória-100 nos dois regimes em tempo é "
         f"{'igual à' if igual else 'diferente da'} ordem em expansões"
         + ("" if igual_todas else " (entre todas as estratégias, alguma posição muda)") + ".")
print("\n" + frase)
pd.DataFrame([dict(c_min=cmin, c_max=cmax, q_min=qlo, q_max=qhi,
                   mapas_q_inc_abaixo_10_mem100=abaixo10, ordem_igual_foco=igual, ordem_igual_todas=igual_todas,
                   ambiente=amb, frase=frase)]).to_csv(TABELAS / "tempo_frase.csv", index=False)
qn.to_csv(TABELAS / "tempo_q_estrela_por_pivos.csv")
if abaixo10 > 17 / 2:
    print(f"\n*** ATENCAO: Q*_inc < 10 com c medido em {abaixo10} mapas (Memoria-100): condicao de parada ***")

# ---------------------------------------------------------------- 5. figura
fig, ax = plt.subplots(figsize=(3.35, 2.3))
x = np.array(sorted(C.n_pivos.unique()))
for col, rot, ls, mk in (("c", "marginal (inclinação)", "-", "o"), ("c_razao", "tempo / expansões", "--", "s")):
    g = C.groupby("n_pivos")[col]
    ax.errorbar(x, g.median(), yerr=[g.median() - g.quantile(.25), g.quantile(.75) - g.median()],
                ls=ls, marker=mk, ms=3, capsize=2, color="0.1", lw=0.9, label=rot)
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xticks(x); ax.set_xticklabels(x)
ax.set_xlabel("número de pivôs")
ax.set_ylabel("c (visitas da BFS por expansão)")
ax.set_title(f"Uma expansão da memória custa de {cmin:.1f} a {cmax:.1f} visitas da BFS\n"
             f"(mediana e quartis entre os mapas)", fontsize=7.5)
ax.legend(fontsize=6)
salvar(fig, "c_medido", FIGURAS)
