"""B6 - Conferencias do v2 contra agosto e o papel do colapso de pivo (P8).

  1. Ganho estatico da memoria: agosto publicou 4,70x (Memoria-10) e 7,32x (Memoria-50) excluindo as
     celulas (mapa, semente, n) de colapso de pivo; o v2 mantem o P8 e da 4,37x e 5,92x. Aqui os dois
     sao recalculados com os dados v2 e conferidos contra tabelas/a3_speedups_corrigidos.csv.
  2. Memoria sem atualizacao pior que a Manhattan: os casos por mapa e por (mapa, semente, n), e se
     coincidem com o colapso de pivo.
  3. Sensibilidade: o ganho degradado com e sem as celulas de colapso.
"""
import sys, numpy as np, pandas as pd
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from comum import *

if not V2:
    raise SystemExit("b6 roda so com PROTOCOLO=v2")
TABELAS.mkdir(exist_ok=True)

rob = carregar_robustez()
colapso = celulas_degeneradas()
res = pd.read_csv(MEDICOES / "degradacao_v2_resumo.csv")
col_v2 = {(m, s, int(n)) for m, s, lst in res[res.colapso_pivo == "sim"][["mapa", "semente", "pivos_colapsados"]]
          .drop_duplicates().itertuples(index=False) for n in str(lst).split(";")}
assert col_v2 == colapso, (col_v2, colapso)
print(f"células de colapso (mapa, semente, n), iguais em agosto e no v2: {sorted(colapso)}")

def fora(df, n):
    mau = {(m, s) for (m, s, k) in colapso if k == n}
    return df[~pd.MultiIndex.from_arrays([df.mapa, df.semente]).isin(mau)]

# ---------------------------------------------------------------- 1. estatico
um = rob[(rob.tipo_degradacao == "Linear") & (rob.porcentagem_bloqueio == 0.1)]
linhas = []
for n in (10, 20, 50, 100):
    s = um[um.n_pivos == n].assign(r=lambda d: d.exp_orig_manh / d.exp_orig_mem.clip(lower=1))
    _, com = escada_geometrica(s, "r")
    _, sem = escada_geometrica(fora(s, n), "r")
    linhas.append(dict(estrategia=f"Memória-{n}", ganho_com_colapso=com, ganho_sem_colapso=sem,
                       celulas_colapso=sum(k == n for (_, _, k) in colapso)))
E = pd.DataFrame(linhas).set_index("estrategia")
if not FORA_TREINO:
    a3 = pd.read_csv(RAIZ / "tabelas" / "a3_speedups_corrigidos.csv").set_index("config")
    E["agosto_publicado"] = a3.speedup_geometrico.reindex(E.index)
    E["agosto_com_colapso"] = a3.geom_com_degeneradas.reindex(E.index)
    assert np.allclose(E.ganho_sem_colapso, E.agosto_publicado, rtol=1e-9)
    assert np.allclose(E.ganho_com_colapso, E.agosto_com_colapso, rtol=1e-9)
    print("v2 reproduz agosto nas duas versões (com e sem as células de colapso)")
print("\n=== Ganho estático sobre a Manhattan, com e sem as células de colapso de pivô ===")
print(E.round(4).to_string())
E.to_csv(TABELAS / "b6_ganho_estatico_colapso.csv")

# ---------------------------------------------------------------- 2. pior que a Manhattan
pm = pd.read_csv(TABELAS / "b1_por_mapa.csv", dtype={"nivel": str})
q = pm[(pm.metrica == "absoluta") & (pm.nivel == "todos") & (pm.regime == "sem_atualizacao")
       & pm.estrategia.str.startswith("Memória")]
piores = q[q.valor > 1][["mapa", "estrategia", "valor"]].assign(ganho=lambda d: 1 / d.valor)
piores["mapa_tem_colapso"] = piores.mapa.isin({m for m, _, _ in colapso})
print("\n=== Mapas em que a memória sem atualização expande mais que a Manhattan ===")
print(piores.round(3).to_string(index=False))
piores.to_csv(TABELAS / "b6_piores_que_manhattan_mapa.csv", index=False)

cel = []
for n in (10, 20, 50, 100):
    s = rob[rob.n_pivos == n].assign(r=lambda d: np.log(d.exp_deg_mem_congelado.clip(lower=1) /
                                                         d.exp_deg_manh.clip(lower=1)))
    g = np.exp(s.groupby(["mapa", "semente", "tipo_degradacao"], observed=True).r.mean()
               .groupby(["mapa", "semente"]).mean())
    for (m, sm), v in g.items():
        cel.append(dict(mapa=m, semente=sm, n_pivos=n, razao_cong_manh=v, colapso=(m, sm, n) in colapso))
C = pd.DataFrame(cel)
C.to_csv(TABELAS / "b6_celulas_cong_manh.csv", index=False)
pior = C[C.razao_cong_manh > 1]
tab = pd.crosstab(C.razao_cong_manh > 1, C.colapso, rownames=["pior_que_manhattan"], colnames=["colapso"])
print("\n=== Por (mapa, semente, n): pior que a Manhattan × colapso de pivô ===")
print(tab.to_string())
print(pior.round(3).to_string(index=False))
tab.to_csv(TABELAS / "b6_coincidencia_colapso.csv")

# ---------------------------------------------------------------- 3. sensibilidade no degradado
gl = []
for n in (10, 20, 50, 100):
    s = rob[rob.n_pivos == n]
    for regime, col in (("com_atualizacao", "exp_deg_mem"), ("sem_atualizacao", "exp_deg_mem_congelado")):
        for rot, d in (("com_colapso", s), ("sem_colapso", fora(s, n))):
            d = d.assign(r=d.exp_deg_manh.clip(lower=1) / d[col].clip(lower=1))
            g = d.groupby(["mapa", "tipo_degradacao"], observed=True).r.apply(media_geometrica) \
                .groupby("mapa").apply(media_geometrica)
            gl.append(dict(estrategia=f"Memória-{n}", regime=regime, celulas=rot, ganho=media_geometrica(g),
                           mapas_pior_que_manhattan=int((g < 1).sum())))
G = pd.DataFrame(gl).pivot_table(index=["estrategia", "regime"], columns="celulas",
                                 values=["ganho", "mapas_pior_que_manhattan"])
print("\n=== Ganho degradado sobre a Manhattan, com e sem as células de colapso ===")
print(G.round(3).to_string())
G.to_csv(TABELAS / "b6_ganho_degradado_colapso.csv")
