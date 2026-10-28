"""B4 - Mecanismo da perda da memoria sem atualizacao.

Hipotese: a tabela congelada guarda as distancias do mapa antigo, entao o erro da heuristica cresce
com o desvio que o caminho passou a fazer. Por par:
  desvio r   = path_deg_manh / path_orig_manh  (caminho otimo novo / antigo; >= 1)
  aumento    = exp_deg / exp_orig da heuristica (o delta por instancia)
Spearman entre r e o aumento, por mapa (todas as sementes, padroes e niveis); resumo dos coeficientes
por heuristica e Wilcoxon pareado por mapa (memoria sem atualizacao x formula). Pares com origem =
destino (path_orig_manh = 0) ficam fora: r nao existe.
"""
import sys, numpy as np, pandas as pd
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from comum import *
from figuras_comum import *
from scipy.stats import spearmanr, wilcoxon

if not V2:
    raise SystemExit("b4 roda so com PROTOCOLO=v2")
TABELAS.mkdir(exist_ok=True)
FIGURAS.mkdir(exist_ok=True)

FAIXAS = ["r = 1", "1–1,1", "1,1–1,5", "1,5–2", "> 2"]
rob = carregar_robustez()
n0 = int((rob.path_orig_manh == 0).sum())
rob = rob[rob.path_orig_manh > 0]
print(f"linhas com origem = destino (fora): {n0}")

def faixa(r):
    return np.select([r == 1, r <= 1.1, r <= 1.5, r <= 2], FAIXAS[:4], FAIXAS[4])

series = {}
m10 = rob[rob.n_pivos == 10]
series["Manhattan"] = (m10, m10.exp_deg_manh / m10.exp_orig_manh.clip(lower=1))
series["Fórmula"] = (m10, m10.exp_deg_form / m10.exp_orig_form.clip(lower=1))
for n in (10, 20, 50, 100):
    s = rob[rob.n_pivos == n]
    series[f"Memória-{n} com atualização"] = (s, s.exp_deg_mem.clip(lower=1) / s.exp_orig_mem.clip(lower=1))
    series[f"Memória-{n} sem atualização"] = (s, s.exp_deg_mem_congelado.clip(lower=1) / s.exp_orig_mem.clip(lower=1))

linhas_rho, linhas_faixa = [], []
for nome, (df, aumento) in series.items():
    r = (df.path_deg_manh / df.path_orig_manh).to_numpy()
    assert (r >= 1).all(), "caminho otimo degradado menor que o original"
    a = aumento.clip(lower=1e-9).to_numpy()
    for m, idx in df.groupby("mapa", observed=True).indices.items():
        linhas_rho.append(dict(heuristica=nome, mapa=m, spearman=spearmanr(r[idx], a[idx]).statistic,
                               n_instancias=len(idx)))
        f = faixa(r[idx])
        for fx in FAIXAS:
            sel = a[idx][f == fx]
            if len(sel):
                linhas_faixa.append(dict(heuristica=nome, mapa=m, faixa=fx, n_instancias=len(sel),
                                         mediana=float(np.median(sel)), media_geometrica=media_geometrica(sel),
                                         frac_aumento_maior_1=float((sel > 1).mean())))
RHO, FX = pd.DataFrame(linhas_rho), pd.DataFrame(linhas_faixa)
RHO.to_csv(TABELAS / "b4_spearman_por_mapa.csv", index=False)
FX.to_csv(TABELAS / "b4_aumento_por_faixa_por_mapa.csv", index=False)

res = RHO.groupby("heuristica").spearman.agg(mediana="median", minimo="min", maximo="max",
                                              n_mapas="size").loc[list(series)]
print("\n=== Spearman(desvio r, aumento de expansões), por mapa ===")
print(res.round(3).to_string())
res.to_csv(TABELAS / "b4_spearman_resumo.csv")

piv = RHO.pivot(index="mapa", columns="heuristica", values="spearman")
linhas_w = []
for n in (10, 20, 50, 100):
    for regime in ("sem", "com"):
        mem = f"Memória-{n} {regime} atualização"
        for ref in ("Fórmula", "Manhattan"):
            d = piv[mem] - piv[ref]
            linhas_w.append(dict(memoria=mem, referencia=ref, mediana_diferenca=d.median(),
                                 mapas_memoria_maior=int((d > 0).sum()), n_mapas=len(d),
                                 wilcoxon_p=wilcoxon(piv[mem], piv[ref]).pvalue))
W = pd.DataFrame(linhas_w)
W.to_csv(TABELAS / "b4_wilcoxon.csv", index=False)
print("\n=== Wilcoxon pareado por mapa: a memória tem correlação maior que a referência? ===")
print(W.round(4).to_string(index=False))

resumo_fx = FX.groupby(["heuristica", "faixa"]).mediana.agg(
    mediana="median", q1=lambda x: x.quantile(0.25), q3=lambda x: x.quantile(0.75), n_mapas="size")
fracao = FX.groupby(["heuristica", "faixa"]).n_instancias.sum() / FX.groupby("heuristica").n_instancias.sum()
resumo_fx["frac_instancias"] = fracao
resumo_fx = resumo_fx.reset_index()
resumo_fx.to_csv(TABELAS / "b4_aumento_por_faixa.csv", index=False)
print("\n=== Aumento de expansões por faixa de desvio (mediana entre mapas das medianas por mapa) ===")
print(resumo_fx.pivot(index="heuristica", columns="faixa", values="mediana")[FAIXAS].loc[list(series)]
      .round(2).to_string())
r1 = FX[FX.faixa == "r = 1"].groupby("heuristica").agg(
    mediana=("mediana", "median"), frac_aumento_maior_1=("frac_aumento_maior_1", "median")).loc[list(series)]
print("\n=== Caminho ótimo inalterado (r = 1): aumento mediano e fração de pares com aumento > 1 ===")
print(r1.round(3).to_string())
r1.to_csv(TABELAS / "b4_caso_r1.csv")

DESTAQUE = {"Manhattan": ("0.45", "s", "-"), "Fórmula": ("#D55E00", "D", "-"),
            "Memória-100 com atualização": ("#08306b", "o", "-"),
            "Memória-100 sem atualização": ("#08306b", "o", "--")}
fig, ax = plt.subplots(figsize=(3.35, 2.6))
x = np.arange(len(FAIXAS))
for nome, (cor, mk, ls) in DESTAQUE.items():
    q = resumo_fx[resumo_fx.heuristica == nome].set_index("faixa").reindex(FAIXAS)
    ax.fill_between(x, q.q1, q.q3, color=cor, alpha=0.12, lw=0)
    ax.plot(x, q.mediana, color=cor, marker=mk, ls=ls, ms=3.5, mfc="white" if ls == "--" else cor,
            label=nome.replace("Memória", "Mem"))
ax.set_yscale("log"); ax.set_xticks(x, FAIXAS, fontsize=6.5)
ax.set_xlabel("desvio r = caminho ótimo degradado ÷ original")
ax.set_ylabel("aumento de expansões (log)")
ax.legend(fontsize=6, loc="upper left")
salvar(fig, "fig_b4_aumento_por_desvio", FIGURAS)
