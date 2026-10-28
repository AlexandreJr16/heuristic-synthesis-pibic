# Reanálise estatística — agosto/2026

13 scripts (A0…A12) que releem os dados brutos de março e refazem toda a estatística.
**34 tabelas + 2 figuras, em ~3 minutos.**

```fish
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
set -x HEURISTICAS_DADOS ~/caminho/para/02-dados-brutos   # os CSVs brutos, do Drive
.venv/bin/python scripts/run_all.py
```

A execução é determinística (semente global `20260820`): as tabelas geradas batem **byte a
byte** com as versionadas em `tabelas/`.

## Protocolo v2 (novembro/2026)

A robustez refeita em `codigo/robustez-2026-11/` (todos os pares conectados sobrevivem; ver
`docs/06-protocolo-v2.md`) é analisada por `scripts/b1_protocolo_v2.py`:

```fish
set -x HEURISTICAS_DADOS ~/caminho/para/02-dados-brutos   # para o Dijkstra e o a10 de conferência
.venv/bin/python scripts/run_all.py --v2                   # ~5 min, dois recortes
```

- `tabelas_v2/`, `figuras_v2/`: todos os pares (n = 17 mapas).
- `tabelas_v2_fora_treino/`, `figuras_v2_fora_treino/`: só `em_treino == 0` (n = 16; o `arena`
  sai porque todos os pares dele são de treino).
- Duas métricas: **δ** (`exp_deg / exp_orig` da própria heurística) e **razão absoluta**
  (`exp_heurística / exp_Manhattan` no mesmo estado do mapa). Dois regimes da memória: **com
  atualização** (distâncias recalculadas no mapa degradado, como em março, P1) e **sem
  atualização** (distâncias do original, `exp_deg_mem_congelado`).
- As mesmas três regras de `comum.py` e a semente `20260820`. O v1 não muda: sem `--v2`, as
  34 tabelas saem byte a byte iguais às versionadas.

| Tabela | Conteúdo |
|---|---|
| `b1_global.csv` | média geométrica nos mapas, IC 95% BCa, mapas abaixo da Manhattan, por métrica × regime × nível |
| `b1_por_mapa.csv` | o valor de cada mapa (inclusive o estático) |
| `b1_padrao_nivel.csv` | por padrão e nível |
| `b1_postos.csv`, `b1_friedman.csv` | postos de Friedman estático × degradado, χ², p e distância crítica de Nemenyi |
| `b1_cliff.csv` | δ de Cliff e Wilcoxon (Manhattan × Mem-100, Fórmula × Mem-100, Fórmula × Manhattan) |
| `b1_interacao.csv` | estratégia × padrão: F, η²ₚ e permutação (200, intra-instância) |
| `b1_sobrevivencia_v1_v2.csv` | pares válidos v1 × v2 por padrão e nível (v1 a 30% conferido contra o a10) |
| `b1_rejeicao.csv` | bloqueio atingido e células recusadas por R1 e R2 |
| `b1_pivos_bloqueados.csv`, `b1_colapso_pivo.csv` | pivôs em célula bloqueada; colapso de pivô (P8) |

## Estrutura

```
scripts/     a0…a12 + comum.py (regras de agregação) + run_all.py (orquestrador)
tabelas/     34 CSVs — o resultado
figuras/     fig1 diagrama CD (a inversão de hierarquia), fig2 ECDF
medicoes/    insumos: as medições em C++ de codigo/medicoes-2026-08/
```

## As três regras que mudam quase todos os números

Concentradas em `scripts/comum.py`:

1. razões agregam por **média geométrica**, nunca aritmética;
2. expansões são **normalizadas por mapa** antes de agrupar entre mapas;
3. a unidade de replicação para generalizar é o **mapa (n = 17)**, não a instância (n = 116.050).

`comum.py` também deduplica `arena` em toda carga e expõe `celulas_degeneradas()`, que
identifica onde a heurística de memória colapsou.

## Onde ler os resultados

- Resumo: `docs/03-achados-estatisticos.md`
- Tabela a tabela: `docs/historico/ANALISE_DADOS.md`
- Achados com a frase pronta em português: `docs/historico/ANALISE_RESUMO.md`
- O que **não** se pode afirmar: `docs/historico/ANALISE_LIMITACOES.md`
- Correções a fazer no texto do relatório: `docs/historico/ANALISE_CORRECOES_TEXTO.md`
- Como parar e retomar a re-síntese longa do A9: `docs/historico/ANALISE_RETOMAR.md`

A ordem das etapas em `run_all.py` importa: `a7` depende de `a2` e `a6`; `a8` de `a3` e `a6`;
`a0` de `a1`.
