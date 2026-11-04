# ============================================================================
#  Robustez com o protocolo de degradacao v2 - novembro/2026
#
#    robustez_v2        um (mapa, semente): linha de base conferida contra marco,
#                       degradacao v2 (R1, R2, R3) e A* nos tres niveis
#    testa_degradacao   fidelidade a map.cpp, R1, R2, cumulatividade e determinismo
#    conta_pivos        pivos que caem em celula bloqueada, v1 e v2
#    exporta_grid       grid v1 e v2 a 30% de um (mapa, semente, padrao), para o notebook
#    complemento_v2     memoria sem atualizacao (expansoes e caminho), custo de atualizar, otimo por BFS
#    wastar_v2          controle: Weighted A* com rho casado ao da formula (calibra no original, avalia no v2)
#    ressintese_v2      teste 4 do JBCS: formula de marco e as 3 ressintetizadas (sementes 1-3) no protocolo v2
#    tempo_v2           teste 2 do JBCS: tempo por busca e por visita da BFS (c medido); rodar sozinho
#    incremental_v2     teste 1 do JBCS: distancias dos pivos que mudam (limite inferior da atualizacao incremental)
#
#  Usa o src/ de codigo/medicoes-2026-08 (map, heuristics e astar sao byte a byte
#  os de marco; `make confere-src` prova). Rode a partir DESTE diretorio.
# ============================================================================
CXX   = g++
MED   = ../medicoes-2026-08
BASE  = $(MED)/src/map.cpp $(MED)/src/heuristics.cpp $(MED)/src/astar.cpp
SAIDA ?= ../../dados/brutos/v2
P     ?= 6

SEMENTES = 42 123 456 789 1011
# ordem de comum.h (a do CSV final)
MAPAS = arena arena2 brc000d brc100d brc101d brc201d brc202d brc203d den000d \
        den005d den011d den012d den500d den501d den602d hrt201n lak506d
# maiores primeiro, para equilibrar o paralelismo
MAPAS_POR_CUSTO = brc202d den602d brc100d brc201d brc101d den500d den000d den005d \
        brc000d brc203d arena2 hrt201n den501d den012d lak506d den011d arena
PARTES = $(foreach m,$(MAPAS),$(foreach s,$(SEMENTES),$(SAIDA)/partes/$(m)_$(s)))

all: robustez_v2 testa_degradacao conta_pivos exporta_grid complemento_v2 wastar_v2 incremental_v2 ressintese_v2 tempo_v2

robustez_v2 testa_degradacao conta_pivos exporta_grid complemento_v2 wastar_v2 incremental_v2 ressintese_v2 tempo_v2: %: %.cpp degradacao_v2.cpp degradacao_v2.h $(BASE)
	$(CXX) -O2 -std=c++17 -o $@ $*.cpp degradacao_v2.cpp $(BASE)

confere-src:
	for f in map.cpp map.h heuristics.cpp heuristics.h astar.cpp astar.h synthesis/HeuristicNode.h; do \
	  cmp ../run-referencia-2026-03/src/$$f $(MED)/src/$$f || exit 1; done
	@echo "src de medicoes = src de marco"

teste: all confere-src
	./testa_degradacao arena brc201d
	d=$$(mktemp -d) && ./robustez_v2 arena 42 $$d && ./robustez_v2 brc201d 42 $$d && rm -rf $$d

# um job por (mapa, semente), P em paralelo; log de cada job em $(SAIDA)/logs
define roda
	mkdir -p $(SAIDA)/partes $(SAIDA)/logs
	for m in $(1); do for s in $(SEMENTES); do echo $$m $$s; done; done | \
	  xargs -P $(P) -n 2 sh -c './robustez_v2 $$0 $$1 $(SAIDA) 2> $(SAIDA)/logs/$$0_$$1.log || { echo "FALHOU $$0 $$1"; exit 255; }'
endef

piloto: all
	$(call roda,den501d)

rodar: all
	$(call roda,$(MAPAS_POR_CUSTO))

juntar:
	awk 'FNR>1 || NR==1' $(addsuffix .csv,$(PARTES)) > $(SAIDA)/resultados_robustez_v2.csv
	awk 'FNR>1 || NR==1' $(addsuffix _resumo.csv,$(PARTES)) > $(SAIDA)/degradacao_v2_resumo.csv
	cp $(SAIDA)/degradacao_v2_resumo.csv ../../analise/estatistica-2026-08/medicoes/
	cd $(SAIDA) && sha256sum resultados_robustez_v2.csv degradacao_v2_resumo.csv

# um (mapa, semente) por processo; saida versionada em analise/estatistica-2026-08/medicoes
pivos: conta_pivos
	mkdir -p $(SAIDA)/pivos
	echo "mapa,semente,protocolo,padrao,nivel,n_pivos,pivos,pivos_distintos,pivos_bloqueados,bloqueados_sem_vizinho" \
	  > ../../analise/estatistica-2026-08/medicoes/pivos_bloqueados_v2.csv
	for m in $(MAPAS); do for s in $(SEMENTES); do echo $$m $$s; done; done | \
	  xargs -P $(P) -n 2 sh -c './conta_pivos $$0 $$1 > $(SAIDA)/pivos/$$0_$$1.csv' && \
	for m in $(MAPAS); do for s in $(SEMENTES); do cat $(SAIDA)/pivos/$${m}_$$s.csv; done; done \
	  >> ../../analise/estatistica-2026-08/medicoes/pivos_bloqueados_v2.csv

# complemento_v2 por (mapa, semente), P em paralelo, maiores primeiro; log em $(SAIDA)/logs_complemento
complemento: complemento_v2
	mkdir -p $(SAIDA)/logs_complemento
	for m in $(MAPAS_POR_CUSTO); do for s in $(SEMENTES); do echo $$m $$s; done; done | \
	  xargs -P $(P) -n 2 sh -c './complemento_v2 $$0 $$1 $(SAIDA) 2> $(SAIDA)/logs_complemento/$$0_$$1.log || { echo "FALHOU $$0 $$1"; exit 255; }'

juntar-complemento:
	for t in congelada custo otimo; do \
	  awk 'FNR>1 || NR==1' $(foreach m,$(MAPAS),$(foreach s,$(SEMENTES),$(SAIDA)/complemento/$(m)_$(s)_$$t.csv)) \
	    > $(SAIDA)/complemento_$$t.csv || exit 1; done
	cp $(SAIDA)/complemento_custo.csv ../../analise/estatistica-2026-08/medicoes/custo_atualizacao_v2.csv
	cd $(SAIDA) && sha256sum complemento_congelada.csv complemento_custo.csv complemento_otimo.csv

# Weighted A*: calibra por mapa (w = 1 conferido, grade + bissecao no treino), depois avalia por (mapa, semente)
wastar-calibra: wastar_v2
	mkdir -p $(SAIDA)/logs_wastar
	for m in $(MAPAS_POR_CUSTO); do echo $$m; done | \
	  xargs -P $(P) -n 1 sh -c './wastar_v2 calibra $$0 $(SAIDA) 2> $(SAIDA)/logs_wastar/$$0_calibra.log || { echo "FALHOU $$0 (codigo $$?)"; exit 255; }'

wastar: wastar_v2
	mkdir -p $(SAIDA)/logs_wastar
	for m in $(MAPAS_POR_CUSTO); do for s in $(SEMENTES); do echo $$m $$s; done; done | \
	  xargs -P $(P) -n 2 sh -c './wastar_v2 avalia $$0 $$1 $(SAIDA) 2> $(SAIDA)/logs_wastar/$$0_$$1.log || { echo "FALHOU $$0 $$1"; exit 255; }'

juntar-wastar:
	for t in w1 calibracao pesos orig; do \
	  awk 'FNR>1 || NR==1' $(foreach m,$(MAPAS),$(SAIDA)/wastar/$(m)_$$t.csv) > $(SAIDA)/wastar_$$t.csv || exit 1; done
	awk 'FNR>1 || NR==1' $(foreach m,$(MAPAS),$(foreach s,$(SEMENTES),$(SAIDA)/wastar/$(m)_$(s)_aval.csv)) \
	  > $(SAIDA)/wastar_aval.csv
	cp $(SAIDA)/wastar_pesos.csv ../../analise/estatistica-2026-08/medicoes/wastar_pesos.csv
	cp $(SAIDA)/wastar_calibracao.csv ../../analise/estatistica-2026-08/medicoes/wastar_calibracao_bruta.csv
	cd $(SAIDA) && sha256sum wastar_w1.csv wastar_calibracao.csv wastar_pesos.csv wastar_orig.csv wastar_aval.csv

juntar-wastar-calibra:
	for t in w1 calibracao pesos orig; do \
	  awk 'FNR>1 || NR==1' $(foreach m,$(MAPAS),$(SAIDA)/wastar/$(m)_$$t.csv) > $(SAIDA)/wastar_$$t.csv || exit 1; done

# grids do den501d s42 a 30% (os cinco padroes) para analise/notebook-2026-10
grids: exporta_grid
	for p in Linear Organic Radial Sparse Stochastic; do ./exporta_grid den501d 42 $$p $(SAIDA)/cache/grids || exit 1; done

# teste 1 do JBCS: por (mapa, semente); CPUS restringe os nucleos (ex. CPUS=6-11 enquanto a sintese ocupa 0-5)
CPUS ?= 0-11
incremental: incremental_v2
	mkdir -p $(SAIDA)/logs_incremental
	for m in $(MAPAS_POR_CUSTO); do for s in $(SEMENTES); do echo $$m $$s; done; done | \
	  xargs -P $(P) -n 2 sh -c 'taskset -c $(CPUS) nice -n 10 ./incremental_v2 $$0 $$1 $(SAIDA) 2> $(SAIDA)/logs_incremental/$$0_$$1.log || { echo "FALHOU $$0 $$1"; exit 255; }'

juntar-incremental:
	awk 'FNR>1 || NR==1' $(foreach m,$(MAPAS),$(foreach s,$(SEMENTES),$(SAIDA)/incremental/$(m)_$(s).csv)) \
	  > ../../analise/estatistica-2026-08/medicoes/incremental_v2.csv
	sha256sum ../../analise/estatistica-2026-08/medicoes/incremental_v2.csv

# teste 4 do JBCS: depois da sintese (sintese_pool.py --sementes 1,2,3 e --merge)
FORMULAS_V2 = ../../analise/estatistica-2026-08/formulas_v2_seed/formulas_v2_seed.csv
ressintese: ressintese_v2
	mkdir -p $(SAIDA)/logs_ressintese
	for m in $(MAPAS_POR_CUSTO); do for s in $(SEMENTES); do echo $$m $$s; done; done | \
	  xargs -P $(P) -n 2 sh -c 'taskset -c $(CPUS) ./ressintese_v2 $$0 $$1 $(SAIDA) $(FORMULAS_V2) 2> $(SAIDA)/logs_ressintese/$$0_$$1.log || { echo "FALHOU $$0 $$1"; exit 255; }'

juntar-ressintese:
	awk 'FNR>1 || NR==1' $(foreach m,$(MAPAS),$(foreach s,$(SEMENTES),$(SAIDA)/ressintese/$(m)_$(s).csv)) \
	  > $(SAIDA)/ressintese_v2.csv
	cd $(SAIDA) && sha256sum ressintese_v2.csv

# teste 2 do JBCS: um mapa por vez, uma thread, preso ao nucleo NUCLEO; nada mais do experimento rodando
NUCLEO ?= 2
tempo: tempo_v2
	mkdir -p $(SAIDA)/logs_tempo
	cat /sys/devices/system/cpu/cpu$(NUCLEO)/cpufreq/scaling_governor > $(SAIDA)/logs_tempo/ambiente.txt 2>&1 || true
	cat /sys/devices/system/cpu/cpu$(NUCLEO)/cpufreq/energy_performance_preference >> $(SAIDA)/logs_tempo/ambiente.txt 2>&1 || true
	uptime >> $(SAIDA)/logs_tempo/ambiente.txt
	for m in $(MAPAS); do taskset -c $(NUCLEO) ./tempo_v2 $$m $(SAIDA) 2> $(SAIDA)/logs_tempo/$$m.log || { echo "FALHOU $$m"; exit 255; }; done

juntar-tempo:
	awk 'FNR>1 || NR==1' $(foreach m,$(MAPAS),$(SAIDA)/tempo/$(m)_busca.csv) > ../../analise/estatistica-2026-08/medicoes/tempo_busca_v2.csv
	awk 'FNR>1 || NR==1' $(foreach m,$(MAPAS),$(SAIDA)/tempo/$(m)_bfs.csv) > ../../analise/estatistica-2026-08/medicoes/tempo_bfs_v2.csv
	cp $(SAIDA)/logs_tempo/ambiente.txt ../../analise/estatistica-2026-08/medicoes/tempo_ambiente.txt
	sha256sum ../../analise/estatistica-2026-08/medicoes/tempo_busca_v2.csv ../../analise/estatistica-2026-08/medicoes/tempo_bfs_v2.csv

clean:
	rm -f tempo_v2 ressintese_v2 robustez_v2 testa_degradacao conta_pivos exporta_grid complemento_v2 wastar_v2 incremental_v2
