#!/usr/bin/env python3
"""Reproduz toda a análise do zero, a partir dos 4 CSVs originais + medicoes/.

    rm -rf tabelas figuras medicoes/*.pkl
    .venv/bin/python scripts/run_all.py

As medições em C++ (medicoes/dijkstra.csv, pivos_precomp.csv, reprocessamento*.csv,
sintese_repetida.csv) são pré-requisito e se refazem com:
    cd ../../codigo/medicoes-2026-08 && make && ./medir_dijkstra && ./medir_pivos
    for m in <17 mapas>; do ./verifica_reprocessamento $m 42; done
    ./sintese_repetida        # ~13-20 h

Com --v2, roda so a analise do protocolo v2 (b1 a b7, ~8 min por recorte), duas vezes: todos os
pares (tabelas_v2/) e so os pares fora do treino do AG (tabelas_v2_fora_treino/). Precisa de
dados/brutos/v2/ (ou HEURISTICAS_DADOS_V2), dos complementos (make complemento e make
juntar-complemento em codigo/robustez-2026-11/), do Weighted A* (make wastar-calibra, make wastar e
make juntar-wastar; b7 so em tabelas_v2/) e, para o Dijkstra, de HEURISTICAS_DADOS.
Testes do JBCS: b8 (make incremental, juntar-incremental) e b11 (sintese_pool.py --sementes 1,2,3, make ressintese,
juntar-ressintese) rodam nos dois recortes; b9 (conferencias) e b10 (make tempo, juntar-tempo) rodam no fim, so em
tabelas_v2/, porque leem os dois recortes.
"""
import os, subprocess, sys, time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
PY_ = RAIZ / ".venv" / "bin" / "python"

# A ordem importa (dependências entre tabelas):
#   a7  <- a2_escore_*.csv, a6_por_mapa.csv
#   a8  <- a3_speedup_por_mapa.csv, a6_por_mapa.csv
#   a0  <- a1_delta_por_padrao.csv   (por isso a1 vem antes de a0)
ETAPAS = ["a11_pivos", "a10_descartes", "a3_estatico", "a2_ranking",
          "a4_a5_distribuicoes", "a6_subotimalidade", "a12_admissibilidade", "a7_memoria_pareto",
          "a8_formulas", "a9_reprodutibilidade", "a1_tese", "a1b_delta30", "a0_reprocessamento"]

# b2 e b6 leem b1_global/b1_por_mapa, b5 le b1_interacao
ETAPAS_V2 = ["b1_protocolo_v2", "b4_mecanismo", "b5_modelo_misto", "b6_conferencias", "b2_qualidade_caminho",
             "b3_equilibrio", "b7_wastar", "b8_incremental", "b11_ressintese"]
# b7 ja usa so os pares fora do treino por desenho: roda so no primeiro recorte
SO_TABELAS_V2 = {"b7_wastar"}
# rodam depois dos dois recortes, so em tabelas_v2 (leem tabelas_v2 e tabelas_v2_fora_treino)
FINAIS_V2 = ["b9_conferencias_jbcs", "b10_tempo"]
RECORTES_V2 = {"tabelas_v2": {"PROTOCOLO": "v2"},
               "tabelas_v2_fora_treino": {"PROTOCOLO": "v2", "FORA_TREINO": "1"}}

def main_v2():
    falhas = []
    for saida, amb in RECORTES_V2.items():
        for e in ETAPAS_V2:
            if e in SO_TABELAS_V2 and saida != "tabelas_v2":
                continue
            t = time.time()
            print(f"\n{'='*70}\n>>> {e} -> {saida}\n{'='*70}", flush=True)
            r = subprocess.run([str(PY_), str(AQUI / f"{e}.py")], cwd=RAIZ, env={**os.environ, **amb})
            print(f"<<< {e} -> {saida}: {'ok' if r.returncode == 0 else 'FALHOU'} ({time.time()-t:.0f}s)")
            if r.returncode: falhas.append(f"{e} -> {saida}")
    for e in FINAIS_V2:
        t = time.time()
        print(f"\n{'='*70}\n>>> {e} -> tabelas_v2\n{'='*70}", flush=True)
        r = subprocess.run([str(PY_), str(AQUI / f"{e}.py")], cwd=RAIZ, env={**os.environ, "PROTOCOLO": "v2"})
        print(f"<<< {e} -> tabelas_v2: {'ok' if r.returncode == 0 else 'FALHOU'} ({time.time()-t:.0f}s)")
        if r.returncode: falhas.append(f"{e} -> tabelas_v2")
    if falhas:
        print("FALHARAM:", ", ".join(falhas)); sys.exit(1)
    print("v2 reproduzido.")

def main():
    if "--v2" in sys.argv:
        return main_v2()
    (RAIZ / "tabelas").mkdir(exist_ok=True)
    (RAIZ / "figuras").mkdir(exist_ok=True)
    falhas = []
    for e in ETAPAS:
        t = time.time()
        print(f"\n{'='*70}\n>>> {e}\n{'='*70}", flush=True)
        r = subprocess.run([str(PY_), str(AQUI / f"{e}.py")], cwd=RAIZ)
        print(f"<<< {e}: {'ok' if r.returncode == 0 else 'FALHOU'} ({time.time()-t:.0f}s)")
        if r.returncode: falhas.append(e)
    print(f"\n{'='*70}")
    print(f"tabelas: {len(list((RAIZ/'tabelas').glob('*.csv')))}   "
          f"figuras: {len(list((RAIZ/'figuras').glob('*.pdf')))}")
    if falhas:
        print("FALHARAM:", ", ".join(falhas)); sys.exit(1)
    print("tudo reproduzido.")

if __name__ == "__main__":
    main()
