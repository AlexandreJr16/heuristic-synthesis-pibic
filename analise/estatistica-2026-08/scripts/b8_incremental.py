"""B8 - Teste 1 do JBCS: quanto das distancias dos pivos muda, e o Q* com atualizacao incremental ideal.

Dados: medicoes/incremental_v2.csv (codigo/robustez-2026-11, make incremental && make juntar-incremental),
com a mesma degradacao e os mesmos pivos fixos do v2. Por (mapa, semente, padrao, nivel, n), somado sobre
os pivos:
  mudaram     celulas livres no degradado com d'(p, v) != d(p, v)
  bloqueadas  celulas alcancaveis de p no original que a degradacao bloqueou
  u_inc       mudaram + bloqueadas: o conjunto que qualquer metodo incremental (Delling e Wagner, LPA*,
              D* Lite) precisa tocar ao menos uma vez. E um LIMITE INFERIOR: ignora a fila de prioridade,
              a reabertura de vertices e qualquer outro custo extra do metodo.
  u_total     visitas das BFS completas (o U do b3; conferido aqui contra complemento_custo)
fracao alterada = mudaram / (celulas alcancaveis no original que continuam livres).
Variante mais favoravel ao incremental: u_mud = so as celulas que mudaram (apagar uma celula bloqueada
custaria zero). Com 20% e 30% de bloqueio u_inc passa de u_total, porque as bloqueadas somam ao que mudou.

Q*_inc = U_inc / (c * (E_alternativa - E_mem_atualizada)), com o mesmo Delta E do b3, contra a memoria sem
atualizacao com o mesmo numero de pivos e contra a formula; c em {1, 2, 5, 10} e, se tabelas_v2/c_medido.csv
existir (b10), tambem o c medido por (mapa, n).
"""
import sys, numpy as np, pandas as pd
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from comum import *
from figuras_comum import *

if not V2:
    raise SystemExit("b8 roda so com PROTOCOLO=v2")
TABELAS.mkdir(exist_ok=True)
FIGURAS.mkdir(exist_ok=True)

caminho = MEDICOES / "incremental_v2.csv"
if not caminho.exists():
    raise SystemExit(f"\n{caminho} nao encontrado. Gere com `make incremental` e `make juntar-incremental` "
                     f"em codigo/robustez-2026-11/.\n")
INC = pd.read_csv(caminho)
INC["nivel"] = INC.nivel.round(1)
PIV = INC[INC.padrao == "-"].copy()
INC = INC[INC.padrao != "-"].copy()
for c in ("mudaram", "inalcancaveis", "bloqueadas", "u_inc", "u_total", "celulas_original", "pivos_bloqueados"):
    INC[c] = INC[c].astype("int64")
INC["comparadas"] = INC.celulas_original - INC.bloqueadas
assert len(INC) == 17 * 5 * 5 * 3 * 4, len(INC)

# u_total tem que ser o U do b3
custo = carregar_complemento("custo")
custo["nivel"] = custo.nivel.round(1)
k = ["mapa", "semente", "padrao", "nivel", "n_pivos"]
cf = INC.merge(custo[k + ["celulas_bfs_atualizacao", "pivos_bloqueados"]], on=k, suffixes=("", "_c"))
assert len(cf) == len(INC) and (cf.u_total == cf.celulas_bfs_atualizacao).all() \
    and (cf.pivos_bloqueados == cf.pivos_bloqueados_c).all(), "u_total diferente do complemento_custo"
print(f"u_total = celulas_bfs_atualizacao do complemento em todas as {len(cf)} linhas")

# ---------------------------------------------------------------- 1. fracao alterada e U_inc / U_total
INC["razao_inc_total"] = INC.u_inc / INC.u_total
por_mapa = INC.groupby(["mapa", "nivel", "n_pivos"])[["mudaram", "comparadas", "u_inc", "u_total",
                                                       "bloqueadas", "inalcancaveis"]].sum()
por_mapa["fracao_alterada"] = por_mapa.mudaram / por_mapa.comparadas
por_mapa["razao_inc_total"] = por_mapa.u_inc / por_mapa.u_total
por_mapa["razao_mud_total"] = por_mapa.mudaram / por_mapa.u_total
por_mapa = por_mapa.reset_index()
por_mapa.to_csv(TABELAS / "b8_fracao_por_mapa.csv", index=False)

def faixa(s):
    return pd.Series(dict(mediana=s.median(), minimo=s.min(), maximo=s.max(), q1=s.quantile(0.25),
                          q3=s.quantile(0.75), n_mapas=s.size))

R = por_mapa.groupby(["nivel", "n_pivos"]).razao_inc_total.apply(faixa).unstack().reset_index()
F = por_mapa.groupby(["nivel", "n_pivos"]).fracao_alterada.apply(faixa).unstack().reset_index()
RM = por_mapa.groupby(["nivel", "n_pivos"]).razao_mud_total.apply(faixa).unstack().reset_index()
R = R.merge(RM, on=["nivel", "n_pivos"], suffixes=("", "_so_mudaram"))
R.to_csv(TABELAS / "b8_razao_inc_total.csv", index=False)
F.to_csv(TABELAS / "b8_fracao_alterada.csv", index=False)
pct = lambda x: f"{100 * x:.1f}%".replace(".", ",")
print("\n=== Fração das distâncias que mudam (mediana [mín; máx] entre os 17 mapas) ===")
print(F.assign(txt=F.apply(lambda r: f"{pct(r.mediana)} [{pct(r.minimo)}; {pct(r.maximo)}]", axis=1))
      .pivot(index="n_pivos", columns="nivel", values="txt").to_string())
print("\n=== U_inc / U_total (mediana [mín; máx] entre os mapas) ===")
print(R.assign(txt=R.apply(lambda r: f"{pct(r.mediana)} [{pct(r.minimo)}; {pct(r.maximo)}]", axis=1))
      .pivot(index="n_pivos", columns="nivel", values="txt").to_string())
print("\n=== so as celulas que mudaram / U_total (mediana [mín; máx] entre os mapas) ===")
print(R.assign(txt=R.apply(lambda r: f"{pct(r.mediana_so_mudaram)} [{pct(r.minimo_so_mudaram)}; "
                                     f"{pct(r.maximo_so_mudaram)}]", axis=1))
      .pivot(index="n_pivos", columns="nivel", values="txt").to_string())

# por padrao (para a figura): por mapa, depois mediana e quartis entre os mapas
pp = INC.groupby(["mapa", "padrao", "nivel"])[["mudaram", "comparadas"]].sum()
pp["fracao"] = pp.mudaram / pp.comparadas
FP = pp.reset_index().groupby(["padrao", "nivel"]).fracao.apply(faixa).unstack().reset_index()
FP.to_csv(TABELAS / "b8_fracao_por_padrao.csv", index=False)

# ---------------------------------------------------------------- 2. Q*_inc e Q*_total
CS = [1, 2, 5, 10]
rob = carregar_robustez()
m10 = rob[rob.n_pivos == 10]
E_form = m10.groupby(["mapa", "porcentagem_bloqueio"]).exp_deg_form.mean()
mem = rob.groupby(["mapa", "porcentagem_bloqueio", "n_pivos"])
E_upd, E_cong = mem.exp_deg_mem.mean(), mem.exp_deg_mem_congelado.mean()
del rob, m10
U = INC.groupby(["mapa", "nivel", "n_pivos"])[["u_inc", "u_total", "mudaram"]].mean()

c_med = None
if (TABELAS.parent / "tabelas_v2" / "c_medido.csv").exists():
    cm = pd.read_csv(TABELAS.parent / "tabelas_v2" / "c_medido.csv")
    c_med = cm.set_index(["mapa", "n_pivos"]).c

linhas = []
for (m, nv, n), u in U.iterrows():
    eu = E_upd[(m, nv, n)]
    for alt, ea in (("sem_atualizacao", E_cong[(m, nv, n)]), ("formula", E_form[(m, nv)])):
        eco = ea - eu
        cs = [(str(c), c) for c in CS]
        if c_med is not None and (m, n) in c_med.index:
            cs.append(("medido", float(c_med[(m, n)])))
        for rot, c in cs:
            q = lambda x: x / (c * eco) if eco > 0 else np.inf
            linhas.append(dict(mapa=m, nivel=nv, n_pivos=n, c=rot, c_valor=c, alternativa=alt,
                               u_inc=u.u_inc, u_total=u.u_total, u_mud=u.mudaram, economia_por_busca=eco,
                               q_inc=q(u.u_inc), q_mud=q(u.mudaram), q_total=q(u.u_total)))
Q = pd.DataFrame(linhas)
Q.to_csv(TABELAS / "b8_q_faixa_por_mapa.csv", index=False)

def resume(df):
    out = {}
    for col in ("q_inc", "q_mud", "q_total"):
        s = df[col]
        out.update({f"{col}_mediana": s.median(), f"{col}_min": s.min(), f"{col}_max": s.max()})
    out["mapas_q_inc_abaixo_10"] = int((df.q_inc < 10).sum())
    out["mapas_q_mud_abaixo_10"] = int((df.q_mud < 10).sum())
    out["mapas_sem_economia"] = int(np.isinf(df.q_inc).sum())
    out["n_mapas"] = len(df)
    return pd.Series(out)

S = Q.groupby(["alternativa", "c", "n_pivos", "nivel"]).apply(resume, include_groups=False).reset_index()
S.to_csv(TABELAS / "b8_q_faixa_resumo.csv", index=False)
mil = lambda x: "inf" if not np.isfinite(x) else f"{x:,.0f}".replace(",", ".")
for alt in ("formula", "sem_atualizacao"):
    print(f"\n=== Faixa do Q* contra {'a fórmula' if alt == 'formula' else 'a memória sem atualização'}: "
          f"menor de Q*_mud, Q*_inc e Q*_total .. Q*_total (medianas entre os mapas) ===")
    t = S[S.alternativa == alt].copy()
    t["txt"] = t.apply(lambda r: f"{mil(min(r.q_inc_mediana, r.q_mud_mediana, r.q_total_mediana))} .. "
                                 f"{mil(max(r.q_inc_mediana, r.q_total_mediana))}", axis=1)
    print(t[t.c.isin(["1", "10", "medido"])].pivot(index=["c", "n_pivos"], columns="nivel", values="txt").to_string())

# ---------------------------------------------------------------- 3. a frase e a condicao de parada
def frase_para(crot):
    t = Q[(Q.alternativa == "formula") & (Q.n_pivos == 100) & (Q.c == crot)].groupby("mapa").agg(
        ui=("u_inc", "mean"), ut=("u_total", "mean"), um=("u_mud", "mean"), eco=("economia_por_busca", "mean"),
        c=("c_valor", "mean"))
    qi, qt, qm = t.ui / (t.c * t.eco), t.ut / (t.c * t.eco), t.um / (t.c * t.eco)
    for x in (qi, qt, qm):
        x[t.eco <= 0] = np.inf
    return qi, qt, qm

linhas_f = []
for crot in ["1", "2", "5", "10"] + (["medido"] if c_med is not None else []):
    qi, qt, qm = frase_para(crot)
    linhas_f.append(dict(c=crot, q_inc_mediana=qi.median(), q_inc_min=qi.min(), q_inc_max=qi.max(),
                         q_mud_mediana=qm.median(), q_mud_min=qm.min(), q_mud_max=qm.max(),
                         mapas_q_mud_abaixo_10=int((qm < 10).sum()),
                         q_total_mediana=qt.median(), q_total_min=qt.min(), q_total_max=qt.max(),
                         mapas_q_inc_abaixo_10=int((qi < 10).sum()), n_mapas=len(qi)))
FR = pd.DataFrame(linhas_f)
ref = "medido" if c_med is not None else "1"
r = FR[FR.c == ref].iloc[0]
rz = R[R.n_pivos == 100]
frase = (f"Mesmo com uma atualização incremental ideal, que só toca as distâncias que mudaram "
         f"(U_inc = {pct(rz.mediana.min())} a {pct(rz.mediana.max())} do recálculo completo, medianas por nível, "
         f"Memória-100), atualizar a memória só compensa a partir de {mil(r.q_inc_mediana)} buscas entre mudanças "
         f"(mediana entre os mapas; de {mil(r.q_inc_min)} a {mil(r.q_inc_max)}), contra {mil(r.q_total_mediana)} "
         f"(de {mil(r.q_total_min)} a {mil(r.q_total_max)}) com o recálculo completo "
         f"(c {'medido' if ref == 'medido' else '= 1'}, contra a fórmula, Memória-100). Contando só as distâncias "
         f"que mudam, sem custo para as células bloqueadas, o limiar fica em {mil(r.q_mud_mediana)} "
         f"(de {mil(r.q_mud_min)} a {mil(r.q_mud_max)}).")
FR["frase"] = frase
FR.to_csv(TABELAS / "b8_frase.csv", index=False)
print("\n" + FR.drop(columns="frase").round(1).to_string(index=False))
print("\n" + frase)
abaixo = max(FR[FR.c == ref].mapas_q_inc_abaixo_10.iloc[0], FR[FR.c == ref].mapas_q_mud_abaixo_10.iloc[0])
if abaixo > 17 / 2:
    print(f"\n*** ATENCAO: Q*_inc < 10 buscas em {abaixo} de 17 mapas (c {ref}): condicao de parada do prompt ***")

# conferencia 4 sai daqui: pivos fora da componente do primeiro pivo
PIV["pivos_fora_comp_primeiro"] = PIV.pivos_fora_comp_primeiro.astype(int)
PIV.to_csv(TABELAS / "b8_pivos_fora_componente.csv", index=False)

# ---------------------------------------------------------------- 4. figura
fig, ax = plt.subplots(figsize=(3.35, 2.4))
for i, p in enumerate(PADROES):
    t = FP[FP.padrao == p].sort_values("nivel")
    x = 100 * t.nivel + (i - 2) * 0.35
    ax.errorbar(x, 100 * t.mediana, yerr=[100 * (t.mediana - t.minimo), 100 * (t.maximo - t.mediana)],
                ls=TRACOS[i], marker=MARCAS[i], ms=3, capsize=1.5, color=CINZAS[i], label=p, lw=0.9)
ax.set_xticks([10, 20, 30])
ax.set_xlabel("nível de degradação (%)")
ax.set_ylabel("distâncias dos pivôs que mudam (%)")
lo, hi = F.mediana.min(), F.mediana.max()
ax.set_title(f"Mesmo a 10% de bloqueio, {pct(F[F.nivel == 0.1].mediana.median())} das distâncias mudam\n"
             f"(mediana e extremos entre os 17 mapas)", fontsize=7.5)
ax.legend(fontsize=6, ncol=2)
salvar(fig, "fracao_distancias_mudam", FIGURAS)
