"""B2 - Qualidade do caminho no v2 e teste da Proposicao A.

  rho = path_form / path_otimo, com o otimo dado pela Manhattan (admissivel e consistente), conferido
        contra a BFS (Dijkstra de custo unitario) no mapa degradado nos pares com id % 10 == 0.
  Proposicao A: a memoria continua admissivel no mapa degradado, com e sem atualizacao, entao o
        caminho dela tem de ser o otimo em 100% dos pares. Qualquer violacao para o pipeline.
Pares com origem = destino (caminho 0) tem rho = 1.
"""
import sys, numpy as np, pandas as pd
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from comum import *
from figuras_comum import *

if not V2:
    raise SystemExit("b2 roda so com PROTOCOLO=v2")
TABELAS.mkdir(exist_ok=True)
FIGURAS.mkdir(exist_ok=True)

K = ["mapa", "semente", "id_problema", "tipo_degradacao", "porcentagem_bloqueio"]
K6 = K[:4] + ["n_pivos", "porcentagem_bloqueio"]
rob = carregar_robustez()

# ---------------------------------------------------------------- 1. o otimo de referencia
oti = carregar_complemento("otimo")
m10 = rob[rob.n_pivos == 10]
c = oti.merge(m10[K + ["path_deg_manh"]], on=K, how="left")
assert c.path_deg_manh.notna().all()
conf = dict(pares_conferidos=len(c), iguais=int((c.dist_bfs == c.path_deg_manh).sum()),
            diferentes=int((c.dist_bfs != c.path_deg_manh).sum()))
print("=== Manhattan no mapa degradado contra BFS (Dijkstra de custo unitário) ===")
print(conf)
pd.DataFrame([conf]).to_csv(TABELAS / "b2_conferencia_otimo.csv", index=False)
if conf["diferentes"]:
    c[c.dist_bfs != c.path_deg_manh].to_csv(TABELAS / "b2_otimo_divergente.csv", index=False)
    raise SystemExit("a Manhattan nao deu o otimo em algum par: ver b2_otimo_divergente.csv")

# ---------------------------------------------------------------- 2. Proposicao A
cong = carregar_complemento("congelada").sort_values(K6).reset_index(drop=True)
r6 = rob.sort_values(K6).reset_index(drop=True)
for k in K6:
    assert (cong[k].to_numpy() == r6[k].to_numpy()).all(), k
assert (cong.exp_deg_mem_congelado.to_numpy() == r6.exp_deg_mem_congelado.to_numpy()).all(), \
    "complemento_v2 nao reproduz as expansoes congeladas de robustez_v2"
linhas = []
for n, idx in r6.groupby("n_pivos").indices.items():
    s, cg = r6.iloc[idx], cong.iloc[idx]
    linhas.append(dict(n_pivos=n, pares=len(s),
                       viol_original=int((s.path_orig_mem != s.path_orig_manh).sum()),
                       viol_com_atualizacao=int((s.path_deg_mem != s.path_deg_manh).sum()),
                       viol_sem_atualizacao=int((cg.path_deg_mem_congelado.to_numpy()
                                                 != s.path_deg_manh.to_numpy()).sum())))
PA = pd.DataFrame(linhas)
print("\n=== Proposição A: pares em que o caminho da memória não é o ótimo ===")
print(PA.to_string(index=False))
PA.to_csv(TABELAS / "b2_proposicao_a.csv", index=False)
if PA[["viol_original", "viol_com_atualizacao", "viol_sem_atualizacao"]].to_numpy().sum():
    ruim = r6[(r6.path_deg_mem != r6.path_deg_manh) |
              (cong.path_deg_mem_congelado.to_numpy() != r6.path_deg_manh.to_numpy())]
    ruim.to_csv(TABELAS / "b2_proposicao_a_violacoes.csv", index=False)
    raise SystemExit("Proposicao A violada: ver b2_proposicao_a_violacoes.csv")
del cong, r6

# ---------------------------------------------------------------- 3. rho da formula
def rho(caminho, otimo):
    return np.where(otimo == 0, 1.0, caminho / np.where(otimo == 0, 1, otimo))

um = m10[(m10.tipo_degradacao == "Linear") & (m10.porcentagem_bloqueio == 0.1)]
est = um.assign(rho=rho(um.path_orig_form.to_numpy(), um.path_orig_manh.to_numpy()))
deg = m10.assign(rho=rho(m10.path_deg_form.to_numpy(), m10.path_deg_manh.to_numpy()))
assert (est.rho >= 1).all() and (deg.rho >= 1).all(), "caminho da formula menor que o otimo"

def resume(df, rotulo, por_padrao=True):
    g = df.groupby(["mapa", "tipo_degradacao"] if por_padrao else ["mapa", "semente"], observed=True).rho
    pm = g.apply(media_geometrica).groupby("mapa").apply(media_geometrica)
    lo, hi = bootstrap_bca_geom(pm.values)
    return dict(cenario=rotulo, n_mapas=len(pm), rho_media_geometrica=media_geometrica(pm), ic95_bca_inf=lo,
                ic95_bca_sup=hi, rho_mapa_min=pm.min(), rho_mapa_max=pm.max(),
                frac_otimos=float((df.rho == 1).mean()), frac_excesso_10pct=float((df.rho > 1.1).mean()),
                frac_otimos_mapa_mediana=float(df.groupby("mapa").rho.apply(lambda x: (x == 1).mean()).median()),
                frac_excesso_10pct_mapa_mediana=float(df.groupby("mapa").rho.apply(lambda x: (x > 1.1).mean()).median()))

tab = [resume(est, "estático", por_padrao=False)]
for nv in NIVEIS:
    tab.append(resume(deg[deg.porcentagem_bloqueio == nv], f"degradado {int(100 * nv)}%"))
tab.append(resume(deg, "degradado (todos)"))
R = pd.DataFrame(tab)
R.to_csv(TABELAS / "b2_rho.csv", index=False)
print("\n=== ρ da fórmula (caminho ÷ ótimo) ===")
print(R.round(4).to_string(index=False))

pp = (deg.groupby(["mapa", "tipo_degradacao", "porcentagem_bloqueio"], observed=True).rho
      .apply(media_geometrica).groupby(["tipo_degradacao", "porcentagem_bloqueio"]).apply(media_geometrica)
      .unstack())
pp.to_csv(TABELAS / "b2_rho_padrao_nivel.csv")
print("\n=== ρ por padrão e nível (média geométrica nos mapas) ===")
print(pp.round(4).to_string())
rpm = deg.groupby(["mapa", "tipo_degradacao"], observed=True).rho.apply(media_geometrica).groupby("mapa") \
    .apply(media_geometrica).rename("rho_degradado").to_frame()
rpm["rho_estatico"] = est.groupby(["mapa", "semente"]).rho.apply(media_geometrica).groupby("mapa") \
    .apply(media_geometrica)
rpm.to_csv(TABELAS / "b2_rho_por_mapa.csv")

# ---------------------------------------------------------------- 4. a frase
gl = pd.read_csv(TABELAS / "b1_global.csv", dtype={"nivel": str})
g = gl[(gl.metrica == "absoluta") & (gl.nivel == "todos") & (gl.regime == "sem_atualizacao")] \
    .set_index("estrategia").media_geometrica
melhor = g.drop(["Manhattan", "Fórmula"]).idxmin()
X = g[melhor] / g["Fórmula"]
Y = 100 * (R.set_index("cenario").loc["degradado (todos)", "rho_media_geometrica"] - 1)
frase = (f"Sem atualização, a fórmula expande {X:.2f}× menos que a melhor memória congelada ({melhor}), "
         f"ao custo de caminhos {Y:.1f}% mais longos em média (média geométrica de ρ nos mapas).")
print("\n" + frase)
pd.DataFrame([dict(melhor_memoria_congelada=melhor, expansoes_x=X, excesso_caminho_pct=Y, frase=frase)]) \
    .to_csv(TABELAS / "b2_frase.csv", index=False)

fig, ax = plt.subplots(figsize=(3.35, 2.4))
cen = ["estático", "degradado 10%", "degradado 20%", "degradado 30%"]
for i, rot in enumerate(cen):
    q = R.set_index("cenario").loc[rot]
    vals = rpm.rho_estatico if i == 0 else deg[deg.porcentagem_bloqueio == NIVEIS[i - 1]].groupby(
        ["mapa", "tipo_degradacao"], observed=True).rho.apply(media_geometrica).groupby("mapa").apply(media_geometrica)
    ax.scatter(i + np.linspace(-0.15, 0.15, len(vals)), np.sort(vals.values), s=6, color="#D55E00", alpha=0.4, lw=0)
    ax.plot([i, i], [q.ic95_bca_inf, q.ic95_bca_sup], color="black", lw=1)
    ax.plot(i, q.rho_media_geometrica, "D", color="#D55E00", mec="black", ms=5)
ax.set_xticks(range(len(cen)), ["estático", "10%", "20%", "30%"])
ax.set_ylabel("ρ = caminho da fórmula ÷ ótimo")
salvar(fig, "fig_b2_rho", FIGURAS)
