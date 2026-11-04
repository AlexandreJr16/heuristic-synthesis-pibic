# Robustez com o protocolo de degradação v2 — novembro/2026

Refaz **só a parte de robustez** do experimento de março, com um gerador de degradação que não
perde pares. A síntese, as fórmulas e a linha de base são as de março: nada é sintetizado aqui.

| Programa | Faz |
|---|---|
| `robustez_v2` | um par (mapa, semente): linha de base conferida contra março, degradação v1 e v2 nos três níveis, A\* nos pares válidos |
| `testa_degradacao` | fidelidade a `map.cpp`, R1, R2, cumulatividade e determinismo, em `arena` e `brc201d` |
| `complemento_v2` | por (mapa, semente): caminho e expansões da memória sem atualização, custo de atualizar os pivôs (células das BFS) e o ótimo por BFS numa amostra |
| `conta_pivos` | pivôs que caem em célula bloqueada, v1 e v2 |
| `exporta_grid` | grids v1 e v2 a 30%, com as passagens da R2, para o notebook |
| `incremental_v2` | teste 1 do JBCS: por (mapa, semente), distâncias dos pivôs que mudam com a degradação (limite inferior do custo de uma atualização incremental) |
| `ressintese_v2` | teste 4 do JBCS: a fórmula de março e as 3 ressintetizadas com semente fixa (1, 2, 3), no original e nos 15 cenários do v2 |
| `tempo_v2` | teste 2 do JBCS: tempo por busca (1 aquecimento + 5 medições) e das BFS de recálculo, para medir o c; rodar sozinho na máquina |
| `wastar_v2` | controle da fórmula: Weighted A\* (h = ⌊w · Manhattan⌋) e busca gulosa (GBFS), com o peso calibrado por mapa para casar o ρ da fórmula nos pares de treino e avaliado fora do treino no original e no v2 |

O protocolo, as decisões e os números estão em `docs/06-protocolo-v2.md`. Os requisitos estão em
`docs/especificacoes/degradacao-conectividade/spec.md`.

## O que muda em relação a março

O laço de robustez de março (`run-referencia-2026-03/src/main.cpp:204-266`) bloqueava origem e
destino dos pares e desconectava o mapa, e escolhia os pares só no estado de 30% (P2). A 30%
sobravam de 0,75% a 10,7% dos pares, com uma população diferente em cada padrão.

O gerador v2 (`degradacao_v2.{h,cpp}`) usa os mesmos cinco mecanismos de `map.cpp`, com os mesmos
parâmetros e os mesmos sorteios, e só troca o ponto de bloqueio por `bloqueia()`:

- **R1.** Origem e destino de todos os pares do `.scen` nunca são bloqueados.
- **R2.** Uma célula só é bloqueada se não dividir a componente conexa (4-vizinhança) a que
  pertence. Teste local no anel 3×3; só quando ele não decide, BFS bidirecional com parada
  antecipada entre os vizinhos livres.
- **R3.** Meta absoluta por nível (alvo − já bloqueadas), com o mesmo limite de tentativas de
  março. O resumo registra o % atingido e as células recusadas.

Com R1 e R2, todo par conectado no original continua conectado nos três níveis. `verificaNivel`
confere isso a cada nível e **aborta** se falhar.

## Compilar e testar

```fish
cd codigo/robustez-2026-11
make                  # robustez_v2 e testa_degradacao (g++ -O2 -std=c++17)
make confere-src      # prova que map/heuristics/astar de medicoes = os de marco
env HEURISTICAS_DADOS=$HOME/Downloads make teste
```

Rode **a partir deste diretório**: `maps` é um link simbólico para `../../maps`.
`HEURISTICAS_DADOS` é a pasta com os CSVs brutos de março (`dados/MANIFESTO.md`). No fish, use
`$HOME` e não `~`: o fish não expande `~` depois do `=`.

O `src/` usado é o de `../medicoes-2026-08/src/`. `map.cpp`, `heuristics.cpp` e `astar.cpp` são
byte a byte os de março; a diferença daquela árvore está só em `synthesis/`, que não entra aqui.

## Rodar

```fish
env HEURISTICAS_DADOS=$HOME/Downloads make piloto        # den501d, 5 sementes (~3 min)
env HEURISTICAS_DADOS=$HOME/Downloads make rodar P=6     # 17 mapas x 5 sementes
make juntar                                              # 85 partes -> 2 CSVs + sha256
```

- `P` é o número de processos em paralelo. `P=6` = um por núcleo físico do Ryzen 5 5500. Os
  tempos medidos não sustentam conclusão nenhuma (P3), então `P` não muda os resultados.
- **Tempo:** ≈ 9 a 11 h de CPU, ≈ 1h30 a 2h de relógio com `P=6`. O job mais longo é o
  `brc202d` (~35 min). Pico de ~330 MB por processo.
- **Pode parar e retomar.** Cada job (mapa, semente) grava em `.tmp` e só renomeia no fim; ao
  rodar de novo, os jobs prontos são pulados e os interrompidos recomeçam do zero. Não mexa no
  código entre as sessões: o `make` recompilaria e as partes viriam de versões diferentes.
- Progresso: `ls ../../dados/brutos/v2/partes/*_resumo.csv | wc -l` (de 85).
- Log de cada job em `../../dados/brutos/v2/logs/<mapa>_<semente>.log`.

Medições complementares (≈ 1 h com `P=6`, 5,8 h de CPU; também retomáveis):

```fish
make complemento P=6        # dados/brutos/v2/complemento/<mapa>_<semente>_{congelada,custo,otimo}.csv
make juntar-complemento     # dados/brutos/v2/complemento_*.csv + sha256
```

Controle com Weighted A\* (≈ 1 min de calibração e ≈ 15 min de avaliação com `P=6`; retomáveis):

```fish
make wastar-calibra P=6     # por mapa: w = 1 nos pares do original e a 30% (s42), grade + bissecao no treino
make wastar P=6             # por (mapa, semente): w_inf, w*, w_sup e GBFS nos pares fora do treino, 15 cenarios
make juntar-wastar          # dados/brutos/v2/wastar_{w1,calibracao,pesos,orig,aval}.csv + sha256
```

Testes do JBCS (novembro/2026; números em `docs/06-protocolo-v2.md`, §17). A cadeia que depende da
síntese está em `noite_jbcs.sh` (espera a ressíntese, consolida, avalia, mede o tempo):

```fish
make incremental P=6 && make juntar-incremental        # teste 1, ~2 min
# teste 4: sintese (cd ../../analise/estatistica-2026-08; .venv/bin/python scripts/sintese_pool.py --sementes 1,2,3 --maiores-primeiro), ~9 h
make ressintese P=6 && make juntar-ressintese           # teste 4, avaliacao das 4 formulas por mapa
make tempo NUCLEO=2 && make juntar-tempo                # teste 2, uma thread, nada mais rodando
```

O A\* é o de março, sem mudança: a heurística é `floor(w * heuristicaManhattan)`, porque o `aStar` só
aceita h inteiro. O `floor` mantém h ≤ w·h\*, então a garantia de custo ≤ w × ótimo continua valendo,
e com w = 1 o h é exatamente o da Manhattan. A GBFS (f = h, o limite do WA\* quando w → ∞) é uma cópia
do `aStar` que só troca a prioridade; o desempate (maior g primeiro) e o não reabrir fechados são os
mesmos. Nos arquivos, w = `inf` é a GBFS. Saída 7 de `wastar_v2 calibra`: o ρ da fórmula ficou sem
cerco com ρ não monotônico (não aconteceu).

## Saída

Em `dados/brutos/v2/` (fora do Git, ~0,9 GB):

- `resultados_robustez_v2.csv`: as 24 colunas de `resultados_robustez.csv` de março, mais
  `exp_deg_mem_congelado` (memória com as distâncias do mapa original) e `em_treino` (o par
  entrou na amostra de aptidão do AG, `main.cpp:108-117` com `srand(42)`).
- `degradacao_v2_resumo.csv`: uma linha por mapa × semente × padrão × nível, com `pct_atingido`,
  `rejeitadas_r1`, `rejeitadas_r2` (células distintas recusadas, acumuladas até o nível),
  `pares_validos`, `pares_validos_v1`, `pct_atingido_v1`, `colapso_pivo`, `pivos_colapsados`,
  `tentativas_r1` e `tentativas_r2` (a mesma célula conta a cada sorteio). Uma cópia vai para
  `analise/estatistica-2026-08/medicoes/`, onde é versionada.

## Códigos de saída de `robustez_v2`

| Código | Significa |
|---|---|
| 1 | uso errado ou mapa desconhecido |
| 4 | a linha de base não bate com `resultados_base.csv` de março, ou o CSV não foi achado |
| 5 | `verificaNivel` reprovou R1, R2, a cumulatividade ou a conectividade dos pares; ou um par válido ficou sem caminho no A\* |
| 6 | falha ao gravar a saída |

Fórmula ausente em `dados/resultados_sintese.csv` encerra o processo com exceção (`abort`).
Qualquer código diferente de 0 faz o `make rodar` parar e imprimir `FALHOU <mapa> <semente>`.
