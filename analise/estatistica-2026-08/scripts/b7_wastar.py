"""B7 - Controle: formula contra Weighted A* (h = floor(w * Manhattan)) com qualidade de caminho casada.

  Calibracao (codigo/robustez-2026-11/wastar_v2 calibra): por mapa, nos pares em_treino == 1 do original,
      o peso w* cujo rho (media geometrica de caminho / otimo) casa com o da formula (|diferenca| <= 0,005),
      com o cerco final w_inf (rho <= alvo) e w_sup (rho >= alvo). O teto do WA* e a busca gulosa (GBFS, w = inf).
  Avaliacao: pares em_treino == 0, no original e nos 5 padroes x 3 niveis x 5 sementes do v2, pesos fixos.
  Regra por mapa e cenario: vence se exp_form < exp(w_sup); perde se exp_form > exp(w_inf); empata no resto.
      Se nem a GBFS chega ao rho da formula na calibracao, o mapa e "fora da curva": a formula faz uma troca
      entre expansoes e qualidade de caminho que nenhum peso uniforme sobre a Manhattan reproduz.
Roda so no recorte tabelas_v2 (ja usa so os pares fora do treino por desenho). arena nao tem par fora do treino.
"""
import sys, numpy as np, pandas as pd
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from comum import *
from comum import _robustez_v2
from figuras_comum import *
from scipy.stats import wilcoxon

if not V2 or FORA_TREINO:
    raise SystemExit("b7 roda so com PROTOCOLO=v2, sem FORA_TREINO (o recorte fora do treino ja e o desenho dele)")
TABELAS.mkdir(exist_ok=True)
FIGURAS.mkdir(exist_ok=True)

def le(nome):
    caminho = DADOS_V2 / f"wastar_{nome}.csv"
    if not caminho.exists():
        raise SystemExit(f"\nDado v2 não encontrado: {caminho}\n"
                         f"Gere com `make wastar-calibra`, `make wastar` e `make juntar-wastar` em codigo/robustez-2026-11/.\n")
    return pd.read_csv(caminho)

PESOS, CAL, W1, ORIG, AVAL = le("pesos"), le("calibracao"), le("w1"), le("orig"), le("aval")
PESOS = PESOS.set_index("mapa")
# o C++ grava o nivel com 17 digitos (0.29999999999999999), que o leitor rapido do pandas nao devolve como 0.3
for df in (W1, AVAL):
    df["porcentagem_bloqueio"] = df.porcentagem_bloqueio.round(1)
r10 = _robustez_v2()
r10 = r10[r10.n_pivos == 10].copy()
r10["mapa"] = r10.mapa.astype(str)
r10["tipo_degradacao"] = r10.tipo_degradacao.astype(str)
num = lambda x, c=2: f"{x:.{c}f}".replace(".", ",")

# o original nao depende da semente nem do padrao: uma linha por par
orig = r10[(r10.semente == 42) & (r10.tipo_degradacao == "Linear") & (r10.porcentagem_bloqueio == 0.1)]
for c in ("exp_orig_manh", "path_orig_manh", "exp_orig_form", "path_orig_form"):
    assert (r10.groupby(["mapa", "id_problema"])[c].nunique() == 1).all(), f"{c} varia entre sementes"

def rho(caminho, otimo):
    caminho, otimo = np.asarray(caminho, float), np.asarray(otimo, float)
    return np.where(otimo == 0, 1.0, caminho / np.where(otimo == 0, 1, otimo))

# ---------------------------------------------------------------- 1. conferencia w = 1 e rho alvo
o1 = W1[W1.tipo_degradacao == "original"].merge(orig[["mapa", "id_problema", "exp_orig_manh", "path_orig_manh"]],
                                                on=["mapa", "id_problema"], how="left")
d1 = W1[W1.tipo_degradacao != "original"].merge(
    r10[r10.porcentagem_bloqueio == 0.3][["mapa", "semente", "id_problema", "tipo_degradacao", "exp_deg_manh",
                                          "path_deg_manh"]],
    on=["mapa", "semente", "id_problema", "tipo_degradacao"], how="left")
assert o1.exp_orig_manh.notna().all() and d1.exp_deg_manh.notna().all()
o1["diverge"] = (o1.exp_w1 != o1.exp_orig_manh) | (o1.path_w1 != o1.path_orig_manh)
d1["diverge"] = (d1.exp_w1 != d1.exp_deg_manh) | (d1.path_w1 != d1.path_deg_manh)
tr = orig[orig.em_treino == 1]
alvo_csv = tr.assign(r=rho(tr.path_orig_form, tr.path_orig_manh)).groupby("mapa").r.apply(media_geometrica)
dif_alvo = (alvo_csv - PESOS.rho_alvo).abs().max()
CONF = pd.DataFrame([
    dict(cenario="original (todos os pares conectados)", pares_conferidos=len(o1), divergentes=int(o1.diverge.sum())),
    *[dict(cenario=f"{p} 30%, semente 42", pares_conferidos=len(g), divergentes=int(g.diverge.sum()))
      for p, g in d1.groupby("tipo_degradacao")],
    dict(cenario="total", pares_conferidos=len(o1) + len(d1), divergentes=int(o1.diverge.sum() + d1.diverge.sum()))])
CONF["rho_alvo_cpp_menos_csv_max"] = dif_alvo
CONF.to_csv(TABELAS / "wastar_conferencia_w1.csv", index=False)
print("=== Conferência: WA* com w = 1 contra a Manhattan já medida ===")
print(CONF.to_string(index=False))
if CONF.divergentes.iloc[-1] or dif_alvo > 1e-12:
    pd.concat([o1[o1.diverge], d1[d1.diverge]]).to_csv(TABELAS / "wastar_conferencia_w1_divergentes.csv", index=False)
    raise SystemExit("WA* com w = 1 nao reproduz a Manhattan (ou o rho alvo do C++ difere do CSV)")

# ---------------------------------------------------------------- 2. calibracao
pares_treino = CAL[(CAL.papel == "formula") & (CAL.conjunto == "treino")].set_index("mapa").pares
CALIB = PESOS.assign(pares_treino=pares_treino).reset_index()
CALIB = CALIB[["mapa", "categoria", "pares_treino", "rho_alvo", "exp_formula", "w_inf", "w_estrela", "w_sup",
               "rho_inf", "rho_estrela", "rho_sup", "exp_inf", "exp_estrela", "exp_sup", "rho_gbfs", "exp_gbfs",
               "iteracoes", "grade_ampliada", "atingiu_tolerancia"]]
CALIB.to_csv(TABELAS / "wastar_calibracao.csv", index=False)
print("\n=== Calibração (pares de treino, mapa original) ===")
print(CALIB[["mapa", "categoria", "rho_alvo", "w_inf", "w_estrela", "w_sup", "rho_estrela", "rho_gbfs",
             "grade_ampliada"]].round(4).to_string(index=False))
fin = CALIB.w_estrela[np.isfinite(CALIB.w_estrela)]
print(f"w*: mediana {fin.median():.4g}, de {fin.min():.4g} a {fin.max():.4g} ({len(fin)} mapas com w*)")
if (CALIB.exp_gbfs < CALIB.exp_formula).any():
    raise SystemExit("a GBFS expande menos que a formula em algum mapa: parar e decidir")

# ---------------------------------------------------------------- 3. avaliacao fora do treino
K = ["mapa", "semente", "id_problema", "tipo_degradacao", "porcentagem_bloqueio"]
te = orig[orig.em_treino == 0]
base_o = te.assign(semente=-1, tipo_degradacao="original", porcentagem_bloqueio=0.0)
linhas = [base_o[K].assign(heuristica="formula", exp=te.exp_orig_form.values, path=te.path_orig_form.values,
                           otimo=te.path_orig_manh.values),
          base_o[K].assign(heuristica="manhattan", exp=te.exp_orig_manh.values, path=te.path_orig_manh.values,
                           otimo=te.path_orig_manh.values)]
wo = ORIG.rename(columns={"papel": "heuristica"}).merge(te[["mapa", "id_problema", "path_orig_manh"]],
                                                       on=["mapa", "id_problema"], how="left")
assert wo.path_orig_manh.notna().all()
linhas.append(wo.assign(semente=-1, tipo_degradacao="original", porcentagem_bloqueio=0.0, otimo=wo.path_orig_manh)
              [K + ["heuristica", "exp", "path", "otimo"]])
dg = r10[r10.em_treino == 0]
linhas += [dg[K].assign(heuristica="formula", exp=dg.exp_deg_form.values, path=dg.path_deg_form.values,
                        otimo=dg.path_deg_manh.values),
           dg[K].assign(heuristica="manhattan", exp=dg.exp_deg_manh.values, path=dg.path_deg_manh.values,
                        otimo=dg.path_deg_manh.values)]
av = AVAL.rename(columns={"papel": "heuristica"}).merge(dg[K + ["path_deg_manh"]], on=K, how="left")
assert av.path_deg_manh.notna().all(), "par avaliado pelo WA* sem linha correspondente no v2"
linhas.append(av.assign(otimo=av.path_deg_manh)[K + ["heuristica", "exp", "path", "otimo"]])
L = pd.concat(linhas, ignore_index=True)
L["rho"] = rho(L.path, L.otimo)
assert (L.rho >= 1).all(), "caminho menor que o otimo"
# cada par fora do treino tem todas as heuristicas do mapa em todos os cenarios
n_h = L.groupby(["mapa", "tipo_degradacao", "porcentagem_bloqueio", "heuristica"]).size().unstack()
assert n_h.apply(lambda r: r.dropna().nunique() == 1, axis=1).all(), "heuristicas com pares diferentes numa celula"
del linhas, av, wo, dg

cel = (L.groupby(["mapa", "tipo_degradacao", "porcentagem_bloqueio", "heuristica"])
       .agg(pares=("exp", "size"), exp=("exp", lambda x: media_geometrica(np.maximum(x, 1))),
            rho=("rho", media_geometrica), frac_otimos=("rho", lambda x: float((x == 1).mean())))
       .reset_index())
cel["w"] = cel.apply(lambda r: {"formula": np.nan, "manhattan": 1.0, "gbfs": np.inf}.get(
    r.heuristica, PESOS.loc[r.mapa].get(r.heuristica, np.nan)), axis=1)
cel.to_csv(TABELAS / "wastar_avaliacao.csv", index=False)

# cenarios agregados: media geometrica das celulas (padrao x nivel) dentro do mapa
NOMES_NIVEL = {0.1: "10%", 0.2: "20%", 0.3: "30%"}
def agrega(df, rotulo):
    g = df.groupby(["mapa", "heuristica"]).agg(exp=("exp", media_geometrica), rho=("rho", media_geometrica),
                                                frac_otimos=("frac_otimos", "mean")).reset_index()
    return g.assign(cenario=rotulo)
deg = cel[cel.tipo_degradacao != "original"]
AG = pd.concat([agrega(cel[cel.tipo_degradacao == "original"], "original"),
                *[agrega(deg[deg.porcentagem_bloqueio == nv], NOMES_NIVEL[nv]) for nv in NIVEIS],
                agrega(deg, "degradado (todos)"),
                *[agrega(deg[deg.tipo_degradacao == p], p) for p in PADROES],
                *[agrega(deg[(deg.tipo_degradacao == p) & (deg.porcentagem_bloqueio == nv)], f"{p} {NOMES_NIVEL[nv]}")
                  for p in PADROES for nv in NIVEIS]], ignore_index=True)
CENARIOS = AG.cenario.unique().tolist()
LARGO = AG.pivot_table(index=["cenario", "mapa"], columns="heuristica", values=["exp", "rho"])
LARGO.columns = [f"{a}_{b}" for a, b in LARGO.columns]
LARGO = LARGO.reset_index().merge(PESOS[["categoria"]].reset_index(), on="mapa")

# ---------------------------------------------------------------- 4. cerco fora do treino e 5. decisao
def decide(r):
    if r.categoria == "fora_da_curva":
        return "fora da curva" if r.exp_formula < r.exp_gbfs and r.exp_formula < r.exp_w_inf else "gbfs expande menos"
    if r.exp_formula < r.exp_w_sup:
        return "vence"
    if r.exp_formula > r.exp_w_inf:
        return "perde"
    return "empata"
LARGO["decisao"] = LARGO.apply(decide, axis=1)
LARGO["dentro_do_cerco"] = np.where(LARGO.categoria == "fora_da_curva", np.nan,
                                    (LARGO.rho_w_inf <= LARGO.rho_formula) & (LARGO.rho_formula <= LARGO.rho_w_sup))
LARGO["rho_acima_do_cerco"] = LARGO.rho_formula > LARGO.rho_w_sup
LARGO["exp_nao_monotona"] = LARGO.exp_w_sup > LARGO.exp_w_inf
# fora do cerco a regra perde a referencia; a GBFS e o ponto de menos expansoes da curva (exp cai com w), entao
# formula com menos expansoes e rho <= o da GBFS fica abaixo da curva inteira do WA*
LARGO["abaixo_da_curva_inteira"] = (LARGO.exp_formula < LARGO.exp_gbfs) & (LARGO.rho_formula <= LARGO.rho_gbfs)
LARGO["razao_wastar_formula"] = np.where(LARGO.categoria == "fora_da_curva", np.nan,
                                         LARGO.exp_w_estrela / LARGO.exp_formula)
LARGO["razao_gbfs_formula"] = LARGO.exp_gbfs / LARGO.exp_formula
LARGO["dif_rho_formula_wastar"] = LARGO.rho_formula - LARGO.rho_w_estrela
LARGO["dif_rho_formula_gbfs"] = LARGO.rho_formula - LARGO.rho_gbfs
LARGO.to_csv(TABELAS / "wastar_decisao.csv", index=False)
if (LARGO.decisao == "gbfs expande menos").any():
    print(LARGO[LARGO.decisao == "gbfs expande menos"][["cenario", "mapa"]].to_string(index=False))
    raise SystemExit("a GBFS expande menos que a formula num mapa fora da curva: parar e decidir")

CATS = ["vence", "empata", "perde", "fora da curva"]
CONT = (LARGO.groupby("cenario").decisao.value_counts().unstack(fill_value=0).reindex(columns=CATS, fill_value=0)
        .reindex(CENARIOS))
CONT["mapas"] = CONT[CATS].sum(axis=1)
cerco = LARGO[LARGO.categoria != "fora_da_curva"].groupby("cenario").agg(
    fora_do_cerco=("dentro_do_cerco", lambda x: int((x == 0).sum())),
    rho_formula_acima_do_cerco=("rho_acima_do_cerco", "sum"), exp_nao_monotona=("exp_nao_monotona", "sum"),
    abaixo_da_curva_inteira=("abaixo_da_curva_inteira", "sum"))
CONT = CONT.join(cerco).reset_index()
CONT.to_csv(TABELAS / "wastar_decisao_contagem.csv", index=False)
print("\n=== Vence / empata / perde / fora da curva (mapas com pares fora do treino) ===")
print(CONT.to_string(index=False))

# os mapas fora da curva: quanto a GBFS expande a mais e quanto o caminho dela e melhor
FORA = LARGO[LARGO.categoria == "fora_da_curva"][["cenario", "mapa", "exp_formula", "exp_gbfs", "razao_gbfs_formula",
                                                  "rho_formula", "rho_gbfs", "dif_rho_formula_gbfs", "exp_w_inf",
                                                  "rho_w_inf"]]
FORA.to_csv(TABELAS / "wastar_fora_da_curva.csv", index=False)
print("\n=== Fora da curva: fórmula contra a GBFS ===")
print(FORA[FORA.cenario.isin(["original", "10%", "20%", "30%", "degradado (todos)"])].round(4).to_string(index=False))

# ---------------------------------------------------------------- 6. estatistica
PRINC = ["original", "10%", "20%", "30%", "degradado (todos)"]
est = []
for cen in PRINC:
    q = LARGO[LARGO.cenario == cen]
    for recorte, s in (("rho casado (w*)", q[q.categoria != "fora_da_curva"].assign(
            exp_cmp=lambda d: d.exp_w_estrela, rho_cmp=lambda d: d.rho_w_estrela)),
                       ("todos (w*; GBFS fora da curva)", q.assign(
            exp_cmp=np.where(q.categoria == "fora_da_curva", q.exp_gbfs, q.exp_w_estrela),
            rho_cmp=np.where(q.categoria == "fora_da_curva", q.rho_gbfs, q.rho_w_estrela)))):
        razao = s.exp_cmp / s.exp_formula
        lo, hi = bootstrap_bca_geom(razao.values)
        d = cliffs_delta(s.exp_formula, s.exp_cmp)
        drho = s.rho_formula - s.rho_cmp
        est.append(dict(cenario=cen, recorte=recorte, n_mapas=len(s),
                        razao_mediana=razao.median(), razao_min=razao.min(), razao_max=razao.max(),
                        razao_media_geometrica=media_geometrica(razao), ic95_bca_inf=lo, ic95_bca_sup=hi,
                        mapas_formula_expande_menos=int((razao > 1).sum()),
                        wilcoxon_p=wilcoxon(s.exp_formula, s.exp_cmp).pvalue,
                        cliff_delta=d, magnitude=magnitude_cliff(d),
                        dif_rho_mediana=drho.median(), dif_rho_min=drho.min(), dif_rho_max=drho.max(),
                        wilcoxon_rho_p=wilcoxon(s.rho_formula, s.rho_cmp).pvalue,
                        cliff_delta_rho=cliffs_delta(s.rho_formula, s.rho_cmp)))
EST = pd.DataFrame(est)
EST.to_csv(TABELAS / "wastar_estatistica.csv", index=False)
print("\n=== Fórmula × WA* (w*): razão de expansões WA* ÷ fórmula entre os mapas ===")
print(EST.round(4).to_string(index=False))

# ---------------------------------------------------------------- 7. a frase
e = EST[EST.recorte == "rho casado (w*)"].set_index("cenario")
def trecho(cen):
    r = e.loc[cen]
    x = r.razao_mediana
    return (f"{num(x)}× menos" if x >= 1 else f"{num(1 / x)}× mais") + \
        f" (mediana entre {int(r.n_mapas)} mapas; de {num(r.razao_min)}× a {num(r.razao_max)}×)"
n_fora = int((PESOS.categoria == "fora_da_curva").sum())
frase = (f"Com caminhos de qualidade igual, a fórmula expande {trecho('original')} que o WA* no mapa original e "
         f"{trecho('degradado (todos)')} no mapa degradado"
         + ("" if not n_fora else f"; em {n_fora} mapa{'s' if n_fora > 1 else ''} nem a GBFS chega ao ρ da fórmula "
            "(fora da curva).") + ("" if n_fora else "."))
print("\n" + frase)
pd.DataFrame([dict(razao_original=e.loc["original", "razao_mediana"],
                   razao_degradado=e.loc["degradado (todos)", "razao_mediana"], mapas_fora_da_curva=n_fora,
                   frase=frase)]).to_csv(TABELAS / "wastar_frase.csv", index=False)

# ---------------------------------------------------------------- 8. figuras
COR_F, COR_W = "#D55E00", "0.25"
from matplotlib.ticker import FuncFormatter, NullFormatter, LogLocator
def eixo_log(ax, sufixo=""):
    ax.yaxis.set_major_locator(LogLocator(subs=(1, 2, 5)))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}{sufixo}".replace(".", ",")))
    ax.yaxis.set_minor_formatter(NullFormatter())
def curva(ax, mapa, conjunto, rotulos=True):
    c = CAL[(CAL.mapa == mapa) & (CAL.conjunto == conjunto)]
    w = c[c.papel != "formula"].drop_duplicates("w").sort_values("w")
    f = c[c.papel == "formula"].iloc[0]
    ax.plot(w.rho, w.exp_geom, "-o", color=COR_W, ms=2.5, lw=0.8, zorder=1)
    m, g = w[w.w == 1].iloc[0], w[np.isinf(w.w)].iloc[0]
    ax.plot(m.rho, m.exp_geom, "s", color="0.55", ms=4.5, zorder=2)
    ax.plot(g.rho, g.exp_geom, "^", color=COR_W, ms=4.5, zorder=2)
    ax.plot(f.rho, f.exp_geom, "D", color=COR_F, mec="black", mew=0.5, ms=5, zorder=3)
    ax.set_yscale("log")
    eixo_log(ax)
    if rotulos:
        ax.annotate("Manhattan (w = 1)", (m.rho, m.exp_geom), xytext=(4, 2), textcoords="offset points", fontsize=6.5)
        ax.annotate("GBFS (w→∞)", (g.rho, g.exp_geom), xytext=(-4, 5), textcoords="offset points", fontsize=6.5,
                    ha="right")
        ax.annotate("fórmula", (f.rho, f.exp_geom), xytext=(-6, 0), textcoords="offset points", fontsize=6.5,
                    color=COR_F, ha="right", va="center")
    return f

ro = LARGO[(LARGO.cenario == "original") & (LARGO.categoria != "fora_da_curva")].sort_values("razao_wastar_formula")
mediano = ro.iloc[len(ro) // 2]
fig, ax = plt.subplots(figsize=(3.35, 2.6))
curva(ax, mediano.mapa, "teste")
ax.set_xlabel("ρ = caminho ÷ ótimo (média geométrica)")
ax.set_ylabel("expansões (média geométrica, log)")
ax.set_title(f"{mediano.mapa} (mapa mediano): com o mesmo ρ,\no WA* expande {num(mediano.razao_wastar_formula)}× o que a "
             "fórmula expande")
salvar(fig, "wastar_curva_mapa_mediano", FIGURAS)

mapas = sorted(PESOS.index)
fig, axs = plt.subplots(5, 4, figsize=(7.2, 8.6))
for ax, mapa in zip(axs.flat, mapas):
    conj = "teste" if (CAL[(CAL.mapa == mapa) & (CAL.conjunto == "teste")].pares > 0).all() else "treino"
    curva(ax, mapa, conj, rotulos=False)
    cat = PESOS.loc[mapa, "categoria"]
    ax.set_title(mapa + (" (treino)" if conj == "treino" else "") + (" — fora da curva" if cat == "fora_da_curva" else ""),
                 fontsize=7)
    ax.tick_params(labelsize=6)
for ax in axs.flat[len(mapas):]:
    ax.axis("off")
from matplotlib.lines import Line2D
axs.flat[-1].legend(handles=[Line2D([], [], color=COR_W, marker="o", ms=2.5, lw=0.8, label="WA* (w crescente)"),
                             Line2D([], [], color="0.55", marker="s", ls="", label="Manhattan (w = 1)"),
                             Line2D([], [], color=COR_W, marker="^", ls="", label="GBFS (w→∞)"),
                             Line2D([], [], color=COR_F, marker="D", mec="black", ls="", label="fórmula")],
                    loc="center", frameon=False)
c0 = CONT.set_index("cenario").loc["original"]
fc0 = PESOS.index[PESOS.categoria == "fora_da_curva"]
fig.suptitle(f"Em {int(c0['abaixo_da_curva_inteira'])} de {int(c0['mapas'])} mapas a fórmula fica abaixo da curva do WA*"
             + (f"; no {', '.join(fc0)} ela fica além da GBFS" if len(fc0) else "")
             + "\n(ρ × expansões no mapa original, pares fora do treino; arena: só há pares de treino)",
             fontsize=9,
             fontweight="bold", x=0.02, ha="left")
fig.supxlabel("ρ = caminho ÷ ótimo", fontsize=8)
fig.supylabel("expansões (média geométrica, log)", fontsize=8)
fig.tight_layout()
salvar(fig, "wastar_curva_multiplos", FIGURAS)

fig, ax = plt.subplots(figsize=(3.35, 2.4))
cen = ["original", "10%", "20%", "30%"]
for i, c in enumerate(cen):
    v = LARGO[(LARGO.cenario == c) & (LARGO.categoria != "fora_da_curva")].razao_wastar_formula.sort_values()
    ax.scatter(i + np.linspace(-0.15, 0.15, len(v)), v.values, s=6, color=COR_F, alpha=0.45, lw=0)
    ax.plot([i, i], [v.min(), v.max()], color="black", lw=0.8)
    ax.plot(i, v.median(), "D", color=COR_F, mec="black", ms=5)
ax.axhline(1, color="0.5", lw=0.6, ls="--")
ax.set_yscale("log")
eixo_log(ax, "×")
ax.set_xticks(range(len(cen)), ["original", "10%", "20%", "30%"])
ax.set_ylabel("expansões WA* (w*) ÷ fórmula")
r_deg = e.loc["degradado (todos)", "razao_mediana"]
vmin = LARGO[LARGO.cenario.isin(cen) & (LARGO.categoria != "fora_da_curva")].razao_wastar_formula.min()
ax.set_title((f"A vantagem sobre o WA* com o mesmo ρ encolhe com a\ndegradação, mas fica acima de 1× em todos os mapas"
              if vmin > 1 else f"No mapa degradado o WA* com o mesmo ρ\nalcança a fórmula em algum mapa"))
salvar(fig, "wastar_degradado", FIGURAS)
