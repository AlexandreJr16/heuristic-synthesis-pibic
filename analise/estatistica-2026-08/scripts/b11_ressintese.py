"""B11 - Teste 4 do JBCS: a vitoria da formula sobre a memoria congelada sobrevive a ressintese?

Dados: dados/brutos/v2/ressintese_v2.csv (codigo/robustez-2026-11, make ressintese && make juntar-ressintese):
por par valido, a formula de marco (run_seed 0) e as 3 ressintetizadas com semente fixa (run_seed 1, 2, 3; sintese
no original, mesmos pares de treino, reutilizadas sem nova sintese), no original e nos 5 padroes x 3 niveis x
5 sementes do v2. Formulas e metadados em formulas_v2_seed/formulas_v2_seed.csv.

Por mapa, cenario e formula:
  ganho     media geometrica de exp_Manhattan / exp_formula (escada do b1: instancia -> (mapa, padrao) -> mapa)
  rho       media geometrica de caminho_formula / caminho_Manhattan (o caminho da Manhattan e o otimo; 0 -> 1)
  sobre     fracao dos pares com h(origem) > comprimento otimo (superestimacao na celula de origem)
A Memoria-100 congelada (exp_deg_mem_congelado, n = 100) entra pela mesma escada. A GBFS vem de wastar_v2 (pares
fora do treino; arena nao tem nenhum). Recortes: todos os pares (tabelas_v2) e so em_treino == 0
(tabelas_v2_fora_treino), como nos outros b.
"""
import sys, numpy as np, pandas as pd
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from comum import *
from comum import _robustez_v2
from figuras_comum import *

if not V2:
    raise SystemExit("b11 roda so com PROTOCOLO=v2")
TABELAS.mkdir(exist_ok=True)
FIGURAS.mkdir(exist_ok=True)
ARQ = Path(os.environ.get("RESSINTESE_CSV", DADOS_V2 / "ressintese_v2.csv"))
FORM = RAIZ / "formulas_v2_seed" / "formulas_v2_seed.csv"
if not ARQ.exists():
    raise SystemExit(f"\n{ARQ} nao encontrado. Gere com `make ressintese` e `make juntar-ressintese` em "
                     f"codigo/robustez-2026-11/ (depois de scripts/sintese_pool.py --sementes 1,2,3).\n")
num = lambda x, c=2: f"{x:.{c}f}".replace(".", ",")

R = pd.read_csv(ARQ, dtype={"mapa": "category", "tipo_degradacao": "category", "semente": "int16",
                            "run_seed": "int8", "id_problema": "int32", "exp": "int32", "path": "int32",
                            "h_origem": "int64"})
R["porcentagem_bloqueio"] = R.porcentagem_bloqueio.round(1)
R["mapa"] = R.mapa.astype(str)
R["tipo_degradacao"] = R.tipo_degradacao.astype(str)

rob = _robustez_v2()
rob = rob[rob.n_pivos == 100][["mapa", "semente", "id_problema", "tipo_degradacao", "porcentagem_bloqueio",
                               "exp_orig_manh", "exp_deg_manh", "path_orig_manh", "path_deg_manh", "exp_deg_form",
                               "exp_orig_form", "exp_deg_mem_congelado", "em_treino"]].copy()
rob["mapa"] = rob.mapa.astype(str)
rob["tipo_degradacao"] = rob.tipo_degradacao.astype(str)
rob["porcentagem_bloqueio"] = rob.porcentagem_bloqueio.round(1)
CH = ["mapa", "semente", "id_problema", "tipo_degradacao", "porcentagem_bloqueio"]

deg = R[R.tipo_degradacao != "original"].merge(rob, on=CH, how="left")
assert deg.exp_deg_manh.notna().all(), "par do ressintese sem linha na robustez v2"
z = deg[deg.run_seed == 0]
assert (z.exp == z.exp_deg_form).all(), "a formula de marco nao reproduz robustez_v2"
deg = deg.rename(columns={"exp_deg_manh": "exp_manh", "path_deg_manh": "otimo"})
orig_ref = rob[(rob.semente == 42) & (rob.tipo_degradacao == "Linear") & (rob.porcentagem_bloqueio == 0.1)][
    ["mapa", "id_problema", "exp_orig_manh", "path_orig_manh", "exp_orig_form", "em_treino"]]
org = R[R.tipo_degradacao == "original"].drop(columns=["semente"]).merge(orig_ref, on=["mapa", "id_problema"])
z = org[org.run_seed == 0]
assert (z.exp == z.exp_orig_form).all(), "a formula de marco nao reproduz o original"
org = org.rename(columns={"exp_orig_manh": "exp_manh", "path_orig_manh": "otimo"})
if FORA_TREINO:
    deg, org, rob = deg[deg.em_treino == 0], org[org.em_treino == 0], rob[rob.em_treino == 0]
print(f"pares x cenários (degradado): {len(deg):,}   original: {len(org):,}   mapas: {deg.mapa.nunique()}")

def metricas(df):
    df = df.assign(lg=np.log(df.exp_manh.clip(lower=1) / df.exp.clip(lower=1)),
                   lr=np.log(np.where(df.otimo == 0, 1, df.path / df.otimo.where(df.otimo > 0, 1))),
                   so=(df.h_origem > df.otimo).astype(float))
    return df

deg, org = metricas(deg), metricas(org)

def escada(df, por):
    """media em log por (mapa, padrao, run_seed) sobre pares e sementes, depois sobre os padroes."""
    g = df.groupby(["mapa", "tipo_degradacao", "run_seed"] + por)[["lg", "lr", "so"]].mean()
    g = g.groupby(["mapa", "run_seed"] + por).mean()
    return pd.DataFrame({"ganho": np.exp(g.lg), "rho": np.exp(g.lr), "superestima": g.so})

linhas = []
for cen, df, por in (("degradado (todos)", deg, []),):
    t = escada(df, por).reset_index().assign(cenario=cen)
    linhas.append(t)
for nv in NIVEIS:
    linhas.append(escada(deg[deg.porcentagem_bloqueio == nv], []).reset_index().assign(cenario=f"{int(nv * 100)}%"))
t = deg.groupby(["mapa", "tipo_degradacao", "porcentagem_bloqueio", "run_seed"])[["lg", "lr", "so"]].mean()
t = pd.DataFrame({"ganho": np.exp(t.lg), "rho": np.exp(t.lr), "superestima": t.so}).reset_index()
t["cenario"] = t.tipo_degradacao + " " + (100 * t.porcentagem_bloqueio).astype(int).astype(str) + "%"
linhas.append(t.drop(columns=["tipo_degradacao", "porcentagem_bloqueio"]))
o = org.groupby(["mapa", "run_seed"])[["lg", "lr", "so"]].mean()
linhas.append(pd.DataFrame({"ganho": np.exp(o.lg), "rho": np.exp(o.lr), "superestima": o.so}).reset_index()
              .assign(cenario="original"))
AV = pd.concat(linhas, ignore_index=True)

# memoria-100 congelada, mesma escada e mesmos pares
mc = rob.assign(lg=np.log(rob.exp_deg_manh.clip(lower=1) / rob.exp_deg_mem_congelado.clip(lower=1)))
def escada_mem(df):
    return np.exp(df.groupby(["mapa", "tipo_degradacao"]).lg.mean().groupby("mapa").mean())
MEM = {"degradado (todos)": escada_mem(mc)}
for nv in NIVEIS:
    MEM[f"{int(nv * 100)}%"] = escada_mem(mc[mc.porcentagem_bloqueio == nv])
mem_cen = np.exp(mc.groupby(["mapa", "tipo_degradacao", "porcentagem_bloqueio"]).lg.mean()).reset_index()
mem_cen["cenario"] = mem_cen.tipo_degradacao + " " + (100 * mem_cen.porcentagem_bloqueio).astype(int).astype(str) + "%"
mem_cen = mem_cen.set_index(["mapa", "cenario"]).lg
AV["ganho_mem100_congelada"] = [MEM[c][m] if c in MEM else mem_cen.get((m, c), np.nan)
                                for m, c in zip(AV.mapa, AV.cenario)]
AV["vence_mem100_congelada"] = (AV.ganho > AV.ganho_mem100_congelada).astype(float)
AV.loc[AV.cenario == "original", "vence_mem100_congelada"] = np.nan
AV["formula"] = np.where(AV.run_seed == 0, "original", "semente " + AV.run_seed.astype(str))
AV = AV[["mapa", "cenario", "run_seed", "formula", "ganho", "rho", "superestima", "ganho_mem100_congelada",
         "vence_mem100_congelada"]].sort_values(["mapa", "cenario", "run_seed"])
AV.to_csv(TABELAS / "ressintese_avaliacao.csv", index=False)

# ---------------------------------------------------------------- 1. a conclusao se mantem?
PRINC = ["degradado (todos)", "10%", "20%", "30%"]
cont = []
for cen in PRINC:
    v = AV[AV.cenario == cen].groupby("mapa").vence_mem100_congelada.sum().astype(int)
    for k in range(5):
        cont.append(dict(cenario=cen, formulas_que_vencem=k, mapas=int((v == k).sum())))
CONT = pd.DataFrame(cont).pivot(index="formulas_que_vencem", columns="cenario", values="mapas")[PRINC]
CONT.to_csv(TABELAS / "ressintese_contagem_vitorias.csv")
print("\n=== Mapas por número de fórmulas (de 4) que vencem a Memória-100 congelada em ganho sobre a Manhattan ===")
print(CONT.to_string())
porf = AV[AV.cenario == "degradado (todos)"].groupby("formula").vence_mem100_congelada.agg(
    lambda s: int(s.sum())).rename("mapas_em_que_vence")
print("\n  por fórmula (degradado, padrões agregados):", porf.to_dict())
n_mapas = AV.mapa.nunique()
perdem = porf[(n_mapas - porf) > n_mapas / 2]
if len(perdem):
    print(f"\n*** ATENCAO: {list(perdem.index)} perdem para a Memória-100 congelada na maioria dos mapas: "
          f"condicao de parada do prompt ***")

# ---------------------------------------------------------------- 2. variancia entre sinteses
D = AV[AV.cenario == "degradado (todos)"]
cv = lambda s: s.std(ddof=1) / s.mean()
VAR = D.groupby("mapa").agg(cv_ganho=("ganho", cv), cv_rho=("rho", cv), ganho_min=("ganho", "min"),
                            ganho_max=("ganho", "max"), rho_min=("rho", "min"), rho_max=("rho", "max"))
entre_mapas = dict(cv_ganho=cv(D[D.run_seed == 0].ganho),
                   cv_ganho_media4=cv(D.groupby("mapa").ganho.apply(media_geometrica)),
                   cv_rho=cv(D[D.run_seed == 0].rho))
VAR.to_csv(TABELAS / "ressintese_variancia_por_mapa.csv")
VR = pd.DataFrame([dict(medida=m, cv_entre_sinteses_mediana=VAR[f"cv_{m}"].median(),
                        cv_entre_sinteses_min=VAR[f"cv_{m}"].min(), cv_entre_sinteses_max=VAR[f"cv_{m}"].max(),
                        cv_entre_mapas=entre_mapas[f"cv_{m}"]) for m in ("ganho", "rho")])
VR.to_csv(TABELAS / "ressintese_variancia.csv", index=False)
print("\n=== Coeficiente de variação: entre as 4 sínteses de cada mapa × entre os mapas (fórmula original) ===")
print(VR.round(4).to_string(index=False))

# ---------------------------------------------------------------- 3. dominancia sobre a GBFS (fora do treino)
dom = None
if (DADOS_V2 / "wastar_aval.csv").exists():
    A = pd.read_csv(DADOS_V2 / "wastar_aval.csv", usecols=["mapa", "semente", "id_problema", "tipo_degradacao",
                                                            "porcentagem_bloqueio", "papel", "exp"])
    A = A[A.papel == "gbfs"].drop(columns="papel").rename(columns={"exp": "exp_gbfs"})
    A["porcentagem_bloqueio"] = A.porcentagem_bloqueio.round(1)
    Ao = pd.read_csv(DADOS_V2 / "wastar_orig.csv")
    Ao = Ao[Ao.papel == "gbfs"][["mapa", "id_problema", "exp"]].rename(columns={"exp": "exp_gbfs"})
    linhas = []
    for cen, df, gb, k in (("original", org, Ao, ["mapa", "id_problema"]), ("degradado (todos)", deg, A, CH)):
        x = df[df.em_treino == 0].merge(gb, on=k)
        x = x.assign(lgb=np.log(x.exp_gbfs.clip(lower=1) / x.exp.clip(lower=1)))
        g = (x.groupby(["mapa", "run_seed"]).lgb.mean() if cen == "original" else
             x.groupby(["mapa", "tipo_degradacao", "run_seed"]).lgb.mean().groupby(["mapa", "run_seed"]).mean())
        g = np.exp(g).rename("razao_gbfs_sobre_formula").reset_index().assign(cenario=cen)
        linhas.append(g)
    dom = pd.concat(linhas)
    dom["formula_expande_menos"] = dom.razao_gbfs_sobre_formula > 1
    dom.to_csv(TABELAS / "ressintese_gbfs.csv", index=False)
    DC = dom.groupby(["cenario", "run_seed"]).agg(mapas_formula_expande_menos=("formula_expande_menos", "sum"),
                                                  n_mapas=("mapa", "nunique")).reset_index()
    DC.to_csv(TABELAS / "ressintese_gbfs_contagem.csv", index=False)
    print("\n=== Mapas em que a fórmula expande menos que a GBFS (pares fora do treino) ===")
    print(DC.to_string(index=False))

# ---------------------------------------------------------------- 4. a original e tipica?
tip = []
for cen in ["original"] + PRINC:
    q = AV[AV.cenario == cen].pivot(index="mapa", columns="run_seed", values="ganho")
    novas = q[[1, 2, 3]]
    entre = (q[0] >= novas.min(axis=1)) & (q[0] <= novas.max(axis=1))
    tip.append(dict(cenario=cen, mapas_original_entre_pior_e_melhor=int(entre.sum()),
                    mapas_original_acima_de_todas=int((q[0] > novas.max(axis=1)).sum()),
                    mapas_original_abaixo_de_todas=int((q[0] < novas.min(axis=1)).sum()), n_mapas=len(q)))
TIP = pd.DataFrame(tip)
TIP.to_csv(TABELAS / "ressintese_original_tipica.csv", index=False)
print("\n=== A fórmula original fica entre a pior e a melhor das 3 novas? (ganho) ===")
print(TIP.to_string(index=False))

# ---------------------------------------------------------------- 5. a frase
v = D.groupby("mapa").vence_mem100_congelada.sum().astype(int)
k_max = int(v.max())
y4 = int((v == 4).sum())
y3 = int((v >= 3).sum())
frase = (f"A vantagem da fórmula sobre a memória congelada se mantém em 4 de 4 sínteses independentes em {y4} de "
         f"{n_mapas} mapas (em ao menos 3 de 4 em {y3}); a variação entre sínteses é CV = "
         f"{num(VR.cv_entre_sinteses_mediana[0], 3)} no ganho (mediana entre os mapas; de "
         f"{num(VR.cv_entre_sinteses_min[0], 3)} a {num(VR.cv_entre_sinteses_max[0], 3)}), contra "
         f"{num(VR.cv_entre_mapas[0], 3)} entre os mapas.")
print("\n" + frase)
pd.DataFrame([dict(mapas_4_de_4=y4, mapas_3_ou_mais=y3, n_mapas=n_mapas,
                   cv_sinteses_mediana=VR.cv_entre_sinteses_mediana[0], cv_entre_mapas=VR.cv_entre_mapas[0],
                   frase=frase)]).to_csv(TABELAS / "ressintese_frase.csv", index=False)

# ---------------------------------------------------------------- 6. figura
ordem = D[D.run_seed == 0].sort_values("ganho").mapa.tolist()
fig, ax = plt.subplots(figsize=(7, 2.6))
xs = {m: i for i, m in enumerate(ordem)}
for rs, mk, rot in ((0, "D", "original (março)"), (1, "o", "semente 1"), (2, "s", "semente 2"), (3, "^", "semente 3")):
    q = D[D.run_seed == rs]
    ax.scatter([xs[m] + (rs - 1.5) * 0.12 for m in q.mapa], q.ganho, marker=mk, s=12 if rs else 16,
               facecolor="none" if rs else "0.1", edgecolor="0.1", lw=0.7, label=rot, zorder=3)
mm = MEM["degradado (todos)"]
for m in ordem:
    ax.hlines(mm[m], xs[m] - 0.4, xs[m] + 0.4, color="#08306b", lw=1.2, zorder=2)
ax.plot([], [], color="#08306b", lw=1.2, label="Memória-100 sem atualização")
ax.set_yscale("log")
ax.set_xticks(range(len(ordem)))
ax.set_xticklabels(ordem, rotation=45, ha="right", fontsize=6.5)
ax.set_ylabel("ganho sobre a Manhattan no degradado (log)")
ax.set_title(f"As 4 sínteses vencem a memória congelada em {y4} de {n_mapas} mapas; "
             f"a variação entre sínteses (CV {num(VR.cv_entre_sinteses_mediana[0], 2)}) é menor que entre mapas "
             f"(CV {num(VR.cv_entre_mapas[0], 2)})" if VR.cv_entre_sinteses_mediana[0] < VR.cv_entre_mapas[0] else
             f"As 4 sínteses vencem a memória congelada em {y4} de {n_mapas} mapas", fontsize=7.5)
ax.legend(fontsize=6, ncol=5, loc="upper left")
salvar(fig, "ressintese_ganho", FIGURAS)
