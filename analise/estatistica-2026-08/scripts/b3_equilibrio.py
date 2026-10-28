"""B3 - Ponto de equilibrio da atualizacao da memoria.

Entre duas mudancas do mapa ha Q buscas. Custo do intervalo, em visitas de BFS:
  sem atualizar: Q * c * E_h                 (E_h = expansoes medias por busca da heuristica h)
  atualizando:   U + Q * c * E_mem_atualizada (U = celulas visitadas pelas BFS dos pivos fixos)
com 1 expansao do A* = c visitas de BFS. Atualizar compensa a partir de
  Q* = U / (c * (E_alternativa - E_mem_atualizada)),
contra (a) a memoria sem atualizacao com o mesmo numero de pivos e (b) a formula. Medias aritmeticas
(custo soma), por mapa, nivel e numero de pivos, sobre sementes, padroes e pares; U medido por
complemento_v2 (contagem conferida contra a BFS real). Sem economia (E_alt <= E_mem), Q* = inf.
"""
import sys, numpy as np, pandas as pd
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from comum import *
from figuras_comum import *

if not V2:
    raise SystemExit("b3 roda so com PROTOCOLO=v2")
TABELAS.mkdir(exist_ok=True)
FIGURAS.mkdir(exist_ok=True)

CS = [1, 2, 5, 10]
PIVOS = [10, 20, 50, 100]
rob = carregar_robustez()
custo = carregar_complemento("custo")
custo = custo[custo.mapa.isin(rob.mapa.unique())]

m10 = rob[rob.n_pivos == 10]
E = {"manhattan": m10.groupby(["mapa", "porcentagem_bloqueio"]).exp_deg_manh.mean(),
     "formula": m10.groupby(["mapa", "porcentagem_bloqueio"]).exp_deg_form.mean()}
mem = rob.groupby(["mapa", "porcentagem_bloqueio", "n_pivos"])
E_upd, E_cong = mem.exp_deg_mem.mean(), mem.exp_deg_mem_congelado.mean()
U = custo.groupby(["mapa", "nivel", "n_pivos"]).celulas_bfs_atualizacao.mean()
U.index = U.index.set_names(["mapa", "porcentagem_bloqueio", "n_pivos"])

linhas = []
for (m, nv, n), u in U.items():
    eu, ec = E_upd[(m, nv, n)], E_cong[(m, nv, n)]
    ef, em = E["formula"][(m, nv)], E["manhattan"][(m, nv)]
    for alt, ea in (("sem_atualizacao", ec), ("formula", ef)):
        for c in CS:
            eco = ea - eu
            linhas.append(dict(mapa=m, nivel=nv, n_pivos=n, c=c, alternativa=alt, custo_atualizar=u,
                               exp_mem_atualizada=eu, exp_alternativa=ea, exp_manhattan=em,
                               economia_por_busca=eco, q_estrela=u / (c * eco) if eco > 0 else np.inf))
Q = pd.DataFrame(linhas)
Q["perfil"] = Q.mapa.map(categoria)
Q.to_csv(TABELAS / "b3_equilibrio_por_mapa.csv", index=False)

def resume(df):
    q = df.q_estrela
    return pd.Series(dict(mediana=q.median(), minimo=q.min(), maximo=q.max(), q1=q.quantile(0.25),
                          q3=q.quantile(0.75), mapas_sem_economia=int(np.isinf(q).sum()), n_mapas=len(q)))

S = Q.groupby(["alternativa", "c", "n_pivos", "nivel"]).apply(resume, include_groups=False).reset_index()
S.to_csv(TABELAS / "b3_equilibrio_resumo.csv", index=False)
print("=== Q* (buscas entre mudanças) a partir do qual atualizar a memória compensa ===")
print("    mediana [mínimo, máximo] entre os mapas")
for alt in ("formula", "sem_atualizacao"):
    print(f"\n--- contra {'a fórmula' if alt == 'formula' else 'a memória sem atualização'} ---")
    t = S[(S.alternativa == alt)].copy()
    t["txt"] = t.apply(lambda r: f"{r.mediana:,.0f} [{r.minimo:,.0f}; {r.maximo:,.0f}]" +
                       (f" ({int(r.mapas_sem_economia)} sem economia)" if r.mapas_sem_economia else ""), axis=1)
    print(t[t.c.isin([1, 10])].pivot(index=["c", "n_pivos"], columns="nivel", values="txt").to_string())

# melhor memoria atualizada por mapa: a que alcanca a formula com menos buscas
bm = Q[Q.alternativa == "formula"].groupby(["mapa", "nivel", "c"]).q_estrela.min().reset_index()
B = bm.groupby(["c", "nivel"]).q_estrela.agg(mediana="median", minimo="min", maximo="max").reset_index()
B.to_csv(TABELAS / "b3_equilibrio_melhor_memoria.csv", index=False)
print("\n=== Q* contra a fórmula, usando por mapa o número de pivôs que compensa mais cedo ===")
print(B.round({"mediana": 0, "minimo": 0, "maximo": 0}).to_string(index=False))
sem = Q[(Q.alternativa == "formula") & (Q.c == 1) & np.isinf(Q.q_estrela)][["mapa", "nivel", "n_pivos",
                                                                            "exp_mem_atualizada", "exp_alternativa"]]
print("\n=== Combinações em que a memória atualizada não economiza nada em relação à fórmula (c = 1) ===")
print(sem.round(1).to_string(index=False))
sem.to_csv(TABELAS / "b3_sem_economia.csv", index=False)

# sensibilidade a c: Q* escala com 1/c, entao a ordem entre mapas, niveis e pivos nao muda
ordem_ok = all(np.allclose(
    Q[(Q.c == c) & np.isfinite(Q.q_estrela)].sort_values(["alternativa", "mapa", "nivel", "n_pivos"]).q_estrela.values * c,
    Q[(Q.c == 1) & np.isfinite(Q.q_estrela)].sort_values(["alternativa", "mapa", "nivel", "n_pivos"]).q_estrela.values)
    for c in CS)
print(f"\nQ*(c) = Q*(1)/c em todas as linhas: {ordem_ok}")

# a frase: memoria com 100 pivos contra a formula, todos os niveis juntos, c = 1
tot = Q[(Q.alternativa == "formula") & (Q.n_pivos == 100) & (Q.c == 1)].groupby("mapa").agg(
    u=("custo_atualizar", "mean"), eu=("exp_mem_atualizada", "mean"), ef=("exp_alternativa", "mean"))
qf = tot.u / (tot.ef - tot.eu)
mil = lambda x: f"{x:,.0f}".replace(",", ".")
frase = (f"Com mudanças a cada menos de {mil(qf.median())} buscas (mediana entre os mapas; de {mil(qf.min())} a "
         f"{mil(qf.max())}, com c = 1 e Memória-100), a fórmula é a melhor escolha; acima disso, atualizar a "
         f"memória compensa.")
print("\n" + frase)
pd.DataFrame([dict(q_estrela_mediana=qf.median(), q_estrela_min=qf.min(), q_estrela_max=qf.max(), frase=frase)]) \
    .to_csv(TABELAS / "b3_frase.csv", index=False)

# figura: custo total por intervalo, em buscas-Manhattan equivalentes (normaliza o tamanho do mapa)
qs = np.logspace(0, 6, 200)
def curvas(maps, c=1, n=100):
    t = Q[(Q.alternativa == "formula") & (Q.n_pivos == n) & (Q.c == c) & Q.mapa.isin(maps)]
    t = t.groupby("mapa").agg(u=("custo_atualizar", "mean"), eu=("exp_mem_atualizada", "mean"),
                              ef=("exp_alternativa", "mean"), em=("exp_manhattan", "mean"))
    ec = Q[(Q.alternativa == "sem_atualizacao") & (Q.n_pivos == n) & (Q.c == c) & Q.mapa.isin(maps)] \
        .groupby("mapa").exp_alternativa.mean()
    cur = {"Manhattan": np.outer(np.ones(len(t)), qs),
           "Fórmula": np.outer(t.ef / t.em, qs),
           f"Memória-{n} sem atualização": np.outer(ec.reindex(t.index) / t.em, qs),
           f"Memória-{n} com atualização": np.outer(t.eu / t.em, qs) + (t.u / (c * t.em)).values[:, None]}
    return {k: np.median(v, axis=0) for k, v in cur.items()}

ESTILO = {"Manhattan": dict(color="0.45", ls=":"), "Fórmula": dict(color="#D55E00", ls="-"),
          "Memória-100 sem atualização": dict(color="#08306b", ls="--"),
          "Memória-100 com atualização": dict(color="#08306b", ls="-")}
def painel(ax, cur, titulo):
    for k, v in cur.items():
        ax.plot(qs, v, lw=1.3, label=k.replace("Memória", "Mem"), **ESTILO[k])
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_title(titulo, fontsize=8)

fig, ax = plt.subplots(figsize=(3.35, 2.6))
painel(ax, curvas(Q.mapa.unique()), "")
ax.set_xlabel("buscas entre duas mudanças do mapa (Q, log)")
ax.set_ylabel("custo do intervalo, em buscas Manhattan (log)")
ax.legend(fontsize=6)
salvar(fig, "fig_b3_equilibrio", FIGURAS)

perfis = sorted(Q.perfil.unique())
fig, axes = plt.subplots(1, len(perfis), figsize=(7, 2.2), sharey=True)
for ax, p in zip(axes, perfis):
    painel(ax, curvas(Q[Q.perfil == p].mapa.unique()), f"{p} ({Q[Q.perfil == p].mapa.nunique()} mapas)")
    ax.set_xlabel("Q (log)", fontsize=7)
axes[0].set_ylabel("custo, em buscas Manhattan")
axes[-1].legend(fontsize=5.5)
salvar(fig, "fig_b3_equilibrio_perfis", FIGURAS)
