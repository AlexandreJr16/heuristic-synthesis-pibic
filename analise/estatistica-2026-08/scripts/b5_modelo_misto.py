"""B5 - Interacao estrategia x padrao sem pseudorreplicacao.

O teste do b1 (OLS sobre medias de celula + permutacao) trata as ~7.650 celulas
(mapa x semente x padrao x nivel x estrategia) como independentes, mas elas vem de 17 mapas.
Aqui:
  1. modelo misto: log(metrica) ~ estrategia x padrao x nivel, intercepto aleatorio por mapa e
     componente de variancia para a semente dentro do mapa (ML, para o teste de razao de
     verossimilhanca da interacao estrategia x padrao, que sai junto com a de 3a ordem);
  2. o mesmo com um componente de variancia estrategia-dentro-do-mapa (sensibilidade);
  3. ANOVA de medidas repetidas (AnovaRM) sobre as medias por mapa, com o mapa como sujeito.
A celula e a media de log da razao por instancia (= log da media geometrica).
"""
import sys, warnings, numpy as np, pandas as pd
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from comum import *
import statsmodels.formula.api as smf
from statsmodels.stats.anova import AnovaRM
from scipy.stats import chi2

if not V2:
    raise SystemExit("b5 roda so com PROTOCOLO=v2")
TABELAS.mkdir(exist_ok=True)

ESTRATEGIAS = ["Manhattan", "Fórmula"] + [f"Memória-{n}" for n in (10, 20, 50, 100)]
REGIMES = {"com_atualizacao": "exp_deg_mem", "sem_atualizacao": "exp_deg_mem_congelado"}
K = ["mapa", "semente", "tipo_degradacao", "porcentagem_bloqueio"]

rob = carregar_robustez()
log_ = lambda s: np.log(s.clip(lower=1).astype(float))

def celulas(metrica, regime):
    m10 = rob[rob.n_pivos == 10]
    ref = log_(m10.exp_deg_manh).to_numpy()
    partes = []
    for e, deg, orig, df in [("Manhattan", "exp_deg_manh", "exp_orig_manh", m10),
                             ("Fórmula", "exp_deg_form", "exp_orig_form", m10)] + \
                            [(f"Memória-{n}", REGIMES[regime], "exp_orig_mem", rob[rob.n_pivos == n])
                             for n in (10, 20, 50, 100)]:
        df = df.sort_values(K + ["id_problema"])
        y = log_(df[deg]).to_numpy()
        if metrica == "delta":
            y = y - log_(df[orig]).to_numpy()
        else:
            if e == "Manhattan":
                continue
            base = m10.sort_values(K + ["id_problema"])
            assert (base[K + ["id_problema"]].to_numpy() == df[K + ["id_problema"]].to_numpy()).all()
            y = y - log_(base.exp_deg_manh).to_numpy()
        partes.append(df[K].assign(estrategia=e, y=y))
    c = pd.concat(partes).groupby(K + ["estrategia"], observed=True).y.mean().reset_index()
    return c.rename(columns={"tipo_degradacao": "padrao", "porcentagem_bloqueio": "nivel"})

def ajusta(c, formula, vc):
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        res = None
        for metodo in ("lbfgs", "bfgs", "powell"):
            res = smf.mixedlm(formula, c, groups="mapa", re_formula="1", vc_formula=vc).fit(
                reml=False, method=[metodo])
            if res.converged:
                break
    avisos = sorted({str(x.message).split("\n")[0][:80] for x in w
                     if "divide" not in str(x.message) and "FutureWarning" not in type(x.message).__name__})
    return res, metodo, avisos

COMPLETO = "y ~ C(estrategia)*C(padrao)*C(nivel)"
SEM_EP = "y ~ C(estrategia)*C(nivel) + C(padrao)*C(nivel)"
VC = {"padrao": {"semente": "0 + C(semente)"},
      "ampliado": {"semente": "0 + C(semente)", "estrategia": "0 + C(estrategia)"}}

linhas = []
inter = pd.read_csv(TABELAS / "b1_interacao.csv").set_index(["metrica", "regime"])
for metrica in ("delta", "absoluta"):
    for regime in REGIMES:
        c = celulas(metrica, regime)
        for nome, vc in VC.items():
            cheio, met, av = ajusta(c, COMPLETO, vc)
            red, met_r, av_r = ajusta(c, SEM_EP, vc)
            lr = 2 * (cheio.llf - red.llf)
            gl = len(cheio.fe_params) - len(red.fe_params)
            vcomp = dict(zip(cheio.model.exog_vc.names, cheio.vcomp))
            linhas.append(dict(metrica=metrica, regime=regime, modelo=f"misto_{nome}", teste="LRT",
                               estatistica=lr, gl=gl, p=chi2.sf(lr, gl), convergiu=cheio.converged and red.converged,
                               metodo=met, var_mapa=float(cheio.cov_re.iloc[0, 0]),
                               var_semente=vcomp.get("semente", np.nan),
                               var_estrategia_mapa=vcomp.get("estrategia", np.nan), var_residuo=cheio.scale,
                               avisos="; ".join(sorted(set(av + av_r)))))
        pm = c.groupby(["mapa", "estrategia", "padrao", "nivel"], observed=True).y.mean().reset_index()
        rm = AnovaRM(pm, "y", "mapa", within=["estrategia", "padrao", "nivel"]).fit().anova_table
        rm.to_csv(TABELAS / f"b5_anovarm_{metrica}_{regime}.csv")
        t = rm.loc["estrategia:padrao"]
        linhas.append(dict(metrica=metrica, regime=regime, modelo="anova_rm_mapa", teste="F",
                           estatistica=t["F Value"], gl=t["Num DF"], gl_den=t["Den DF"], p=t["Pr > F"],
                           eta2_parcial=t["F Value"] * t["Num DF"] / (t["F Value"] * t["Num DF"] + t["Den DF"]),
                           convergiu=True, n_mapas=pm.mapa.nunique()))
        b1 = inter.loc[(metrica, regime)]
        linhas.append(dict(metrica=metrica, regime=regime, modelo="ols_permutacao_b1", teste="F (permutação)",
                           estatistica=b1.F, p=b1.p_permutacao, convergiu=True))
        print(f"  {metrica:<8} {regime:<15} ok")

T = pd.DataFrame(linhas)
T.to_csv(TABELAS / "b5_modelo_misto.csv", index=False)
print("\n=== Interação estratégia × padrão: três testes ===")
print(T[["metrica", "regime", "modelo", "estatistica", "gl", "p", "convergiu"]].round(4).to_string(index=False))
print("\n=== Componentes de variância (modelo misto padrão) ===")
v = T[T.modelo == "misto_padrao"][["metrica", "regime", "var_mapa", "var_semente", "var_residuo", "avisos"]]
print(v.round(5).to_string(index=False))
sig = T.groupby(["metrica", "regime"]).p.apply(lambda p: bool((p < 0.05).all()) or bool((p >= 0.05).all()))
print("\nOs três testes concordam (todos p<0,05 ou todos p>=0,05)?", sig.to_dict())
