# Manifesto dos dados

Onde estão os dados, o que há em cada arquivo, e como conferir que estão íntegros.

---

## O que está aqui, no Git

| Arquivo | Tamanho | O que é |
|---|---|---|
| `resultados_sintese.csv` | 4,5 KB | As 18 fórmulas campeãs, uma por mapa. Pequeno e central para o texto, por isso versionado. |
| `resultados_sintese_saunders_VAZIO.csv` | 146 B | **Só o cabeçalho.** A comparação com a implementação original de Saunders em Octave foi preparada (`analise/original-2026-03/variante-2026-06/rodar_saunders.py`) mas **nunca executada**. Preservado para que fique registrado que a comparação foi planejada e não realizada. |

Também versionadas, em `analise/estatistica-2026-08/`:

| Pasta | O que é |
|---|---|
| `medicoes/` | 1,1 MB — as medições novas em C++ de agosto (Dijkstra, pivôs, reprocessamento, re-síntese). São **insumo** das tabelas. |
| `tabelas/` | 34 CSVs — o resultado da reanálise. São os dados que sustentam as afirmações corrigidas. |
| `figuras/` | As 2 figuras candidatas ao relatório (diagrama CD e ECDF), em PDF e PNG. |

## O que está no Google Drive, e não no Git

Pasta `02-dados-brutos/` do pacote do Drive. São ~170 MB — grandes demais para versionar com
conforto, e imutáveis (nunca serão editados), o que os torna candidatos naturais a ficar fora
do controle de versão.

| Arquivo | Tamanho | Linhas |
|---|---|---|
| `resultados_base.csv` | 30 MB | 700.200 |
| `resultados_robustez.csv` | 52 MB | 431.016 |
| `resultados_ratio.csv` | 3,5 MB | 116.700 |
| `resultados_sintese.csv` | 4,5 KB | 18 |
| `results.db` | 85 MB | — |

### Sobre o `results.db`

SQLite com quatro tabelas — `base`, `robustez`, `ratio`, `sintese` — que são **espelho exato**
dos quatro CSVs. Verificado por contagem de linhas e soma por coluna: idênticos. **Não é uma
fonte independente de dados**; está no pacote só por conveniência, para quem preferir consultar
com SQL a carregar 700 mil linhas em memória.

```fish
python3 -c "import sqlite3; print(sqlite3.connect('results.db').execute('select count(*) from base').fetchone())"
```

### Integridade

```fish
cd <pacote-do-drive>/02-dados-brutos
sha256sum -c SHA256SUMS.txt
```

```
ab7ea287b1e1b7b180a0ccbec6f2a540fcb0d32b56b8602f59aa9e8f2c2fc2a7  resultados_base.csv
ff70affb0f699741a0c50dfa6188545d9b0e5c57d92a5468aaf3bf42a5edc843  resultados_ratio.csv
6c0c04a916f863fede27c40f7e29f7018942844d8b1ae0faa1ddefa32b122d39  resultados_robustez.csv
4804a745c1e1052ea4ffc9fc1ec1f7ff63cade9b0148c49aa694d1833107061d  resultados_sintese.csv
b59f8828baad666fde5295e2821eef2b41b1fd93ef5bde5cc388f56cbc56035d  results.db
```

### Como apontar a análise para eles

```fish
set -x HEURISTICAS_DADOS ~/caminho/para/02-dados-brutos
```

ou copie-os para `dados/brutos/` (caminho já previsto no `.gitignore`).

---

## Esquemas

Todos gerados por `codigo/run-referencia-2026-03/src/main.cpp`, em março de 2026.

> ⚠️ O código de **junho** grava duas colunas a mais (`implementacao` e `modo`) no início de
> todos os arquivos, e um `resultados_sintese.csv` com outras colunas. Os dados publicados
> **não** têm essas colunas. Ver `docs/00-PROVENIENCIA.md`.

### `resultados_base.csv` — desempenho no mapa original

```
mapa, semente, id_problema, heuristica, n_pivos, expansoes, tempo_ms, caminho_tamanho
```

- `heuristica` ∈ {`manhattan`, `formula`, `memory`}; `n_pivos` ∈ {0, 10, 20, 50, 100}
- 6 configurações × 116.700 instâncias = 700.200 linhas
- **Desenho pareado**: as 6 configurações rodam sobre exatamente os mesmos pares
  origem–destino, identificados por `(mapa, semente, id_problema)`.

### `resultados_robustez.csv` — desempenho sob degradação

```
mapa, semente, id_problema, tipo_degradacao, n_pivos, porcentagem_bloqueio,
exp_orig_manh,  exp_deg_manh,  exp_orig_form,  exp_deg_form,  exp_orig_mem,  exp_deg_mem,
path_orig_manh, path_deg_manh, path_orig_form, path_deg_form, path_orig_mem, path_deg_mem,
tempo_orig_manh_ms, tempo_deg_manh_ms, tempo_orig_form_ms, tempo_deg_form_ms,
tempo_orig_mem_ms,  tempo_deg_mem_ms
```

- `tipo_degradacao` ∈ {`Linear`, `Organic`, `Radial`, `Sparse`, `Stochastic`}
- `porcentagem_bloqueio` ∈ {0.1, 0.2, 0.3}
- Cada linha traz o par **original × degradado** lado a lado, o que dá o fator de degradação
  `δ = exp_deg / exp_orig` pareado por instância — a métrica da tese.
- Contém **só as instâncias que sobreviveram** ao filtro de conectividade a 30% (20,5% do
  total). **Não misture com `resultados_base.csv` sem filtrar** — foi exatamente esse erro que
  produziu o *speedup* inflado de 51,98× (ver `docs/03-achados-estatisticos.md`, A3).

### `resultados_ratio.csv` — subotimalidade da fórmula

```
mapa, semente, id_problema, caminho_otimo, caminho_formula, ratio
```

- `ratio = caminho_formula / caminho_otimo`. Só existe para a fórmula — Manhattan e memória são
  admissíveis, logo sempre ótimas.
- 45 linhas têm `caminho_otimo < 1` com `ratio` forçado a 1,0 (pares sem caminho). Devem ser
  excluídas. Ver `docs/04-problemas-conhecidos.md`, P6.

### `resultados_sintese.csv` — as fórmulas campeãs

```
mapa, populacao_inicial, n_geracoes, tempo_sintese_ms, formula_string, fitness_final
```

- **18 linhas para 17 mapas**: `arena` aparece duas vezes, com tempos diferentes (4140,47 ms e
  3938,43 ms) e **fórmula idêntica**. São duas execuções independentes — a única evidência de
  reprodutibilidade que existe nos dados originais, e insumo do A9.
- `formula_string` em **notação prefixa**: `(+ (sqr deltaY) (sqr deltaX))`.
  Operadores observados: `+ - * / max min sqr sqrt abs neg`. Terminais: `deltaX`, `deltaY`,
  constantes com uma casa decimal.

---

## Dados da robustez v2 (novembro/2026)

Gerados por `codigo/robustez-2026-11/` (`make rodar P=6` e `make juntar`, em 28/10/2026, 7,6 h
de CPU). Ficam em `dados/brutos/v2/`, fora do Git, como os de março. Só o resumo é versionado,
em `analise/estatistica-2026-08/medicoes/degradacao_v2_resumo.csv`.

| Arquivo | Tamanho | Linhas (sem cabeçalho) |
|---|---|---|
| `resultados_robustez_v2.csv` | 976 MB | 6.963.000 |
| `degradacao_v2_resumo.csv` | 94 KB | 1.275 |

```
d71760d608dca123594ef8eee22c9cbb78cc008784669a70c3c45821f51a06b7  resultados_robustez_v2.csv
848e16603a028f2b90084d4bc00bc4f1a70f1a29e97ee82b4de10cbf59375650  degradacao_v2_resumo.csv
```

### `resultados_robustez_v2.csv`

As 24 colunas de `resultados_robustez.csv`, na mesma ordem, mais duas no fim:

- `exp_deg_mem_congelado`: expansões da memória no mapa degradado usando as distâncias
  calculadas no mapa **original** (sem reprocessar; compare com `exp_deg_mem`, ver P1).
- `em_treino`: 1 se o par entrou na amostra de aptidão do AG (`main.cpp:108-117`, `srand(42)`).
  No `arena` todos os pares são de treino.

Diferenças de população em relação a março:

- Cada nível tem seus próprios pares válidos, que são **todos os pares conectados no mapa
  original**: 23.210 por semente, 116.050 por padrão × nível, os mesmos nos 5 padrões e nos 3
  níveis. As populações são aninhadas (iguais), ao contrário de março (P2).
- `arena` aparece **uma vez** (não há duplicata, P7).
- `exp_orig_*` e `path_orig_*` são a linha de base recalculada pelo v2. Ela bate com
  `resultados_base.csv` em tudo, exceto 3 problemas da fórmula no `den602d` (P11).

### `degradacao_v2_resumo.csv`

Uma linha por mapa × semente × padrão × nível (17 × 5 × 5 × 3):

```
mapa, semente, padrao, nivel, pct_atingido, rejeitadas_r1, rejeitadas_r2, pares_validos,
pares_validos_v1, pct_atingido_v1, colapso_pivo, pivos_colapsados, tentativas_r1, tentativas_r2
```

- `pct_atingido`: fração das células livres do original que ficou bloqueada no v2.
- `rejeitadas_r1/r2`: células **distintas** recusadas por R1 (extremo de par) e R2 (dividiria
  componente), acumuladas até o nível. `tentativas_r1/r2`: o mesmo contando cada sorteio.
- `pares_validos_v1` e `pct_atingido_v1`: o gerador de março reproduzido com as mesmas sementes,
  para comparação lado a lado.
- `colapso_pivo`: `sim` se mais da metade dos pares válidos tem `h = 0` para algum `n`
  (listados em `pivos_colapsados`); o P8 não foi corrigido.

---

## Duas armadilhas que já custaram caro

1. **`arena` está duplicado** em `resultados_base.csv` (3.900 linhas) e `resultados_robustez.csv`
   (12.900 linhas), porque o experimento foi rodado duas vezes com os arquivos em modo *append*.
   Todos os números do relatório incluem esses pares em dobro. Deduplique por
   `(mapa, semente, id_problema, ...)` antes de qualquer agregação — `comum.py::_dedup` já faz
   isso. Ver P7.

2. **`base` e `robustez` são populações diferentes.** `base` tem as 116.700 instâncias;
   `robustez` tem as 23.906 que sobreviveram ao filtro de 30% — e são sistematicamente **os
   pares mais curtos**. Comparar uma coluna de um com uma coluna do outro produz números sem
   sentido. Ver A3.
