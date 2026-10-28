# ============================================================================
#  Robustez com o protocolo de degradacao v2 - novembro/2026
#
#    robustez_v2        um (mapa, semente): linha de base conferida contra marco,
#                       degradacao v2 (R1, R2, R3) e A* nos tres niveis
#    testa_degradacao   fidelidade a map.cpp, R1, R2, cumulatividade e determinismo
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

all: robustez_v2 testa_degradacao

robustez_v2 testa_degradacao: %: %.cpp degradacao_v2.cpp degradacao_v2.h $(BASE)
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

clean:
	rm -f robustez_v2 testa_degradacao
