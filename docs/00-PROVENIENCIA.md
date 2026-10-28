# Proveniência — que código gerou que dado

> **Este é o documento mais importante do repositório.** Se você só puder ler um arquivo,
> leia este. Ele existe porque, ao longo do PIBIC, o código foi reescrito duas vezes *depois*
> de os dados terem sido coletados — e sem esta página é impossível saber, olhando o
> repositório, qual versão produziu os números que estão no relatório.

---

## A resposta curta

**Todos os dados e todos os números do relatório final vieram de
`codigo/run-referencia-2026-03/`, executado em março de 2026.**

As outras duas árvores de código são posteriores e **não** participaram dos resultados
publicados. Se você quiser reproduzir o experimento, é a de março que você deve compilar.

**Exceção, a partir de novembro/2026: a robustez v2.** `codigo/robustez-2026-11/` re-executa
só a parte de robustez, com um gerador de degradação corrigido, e gera dados novos em
`dados/brutos/v2/`. Esses dados vão para o artigo do JBCS, não para o relatório. Síntese,
fórmulas e linha de base continuam sendo as de março (a linha de base é recalculada e conferida
contra elas).

---

## A linha do tempo

```
mar/2026        jun/2026              ago/2026                       ago/2026
    │               │                     │                              │
    ▼               ▼                     ▼                              ▼
┌─────────┐   ┌───────────┐         ┌───────────┐                 ┌────────────┐
│ EXECUÇÃO│   │REFATORAÇÃO│         │ REANÁLISE │                 │ ESTE REPO  │
│   DE    │   │           │         │ESTATÍSTICA│                 │REORGANIZADO│
│REFERÊNCIA│  │           │         │           │                 │            │
└────┬────┘   └─────┬─────┘         └─────┬─────┘                 └────────────┘
     │              │                     │
     │ gerou        │ nunca rodou o       │ releu os dados brutos
     │ os 4 CSVs    │ experimento         │ de março e refez a
     │ (~170 MB)    │ completo            │ estatística do zero
     ▼              ▼                     ▼
  RELATÓRIO     (nada)              CORREÇÕES DO
   v1, ETC                            RELATÓRIO
```

### Março/2026 — a execução de referência ⭐

- **Código:** `codigo/run-referencia-2026-03/`
- **Origem:** commit `7d18f0b` ("sintese otimizada e multi thread", 20/03/2026) do repositório
  original, preservado a partir de uma cópia local que nunca foi sobrescrita.
- **Produziu:** `resultados_base.csv`, `resultados_ratio.csv`, `resultados_robustez.csv`,
  `resultados_sintese.csv` — e, portanto, **todas as tabelas e figuras do relatório**.
- **Análise que o acompanha:** `analise/original-2026-03/analise.py` e `gerarGraficos.py`.
- **Log da execução:** `docs/historico/log-execucao-referencia-2026-03.txt`.
- **O que mudou nessa versão em relação ao resumo estendido da SBC:** está descrito, pelo
  próprio autor e na época, em `docs/historico/CONTEXTO_MODIFICACOES.md`.

### Junho/2026 — a refatoração

- **Código:** `codigo/refatoracao-2026-06/`
- **Origem:** commits `fed66f5` e `198b984` do GitHub (02/06/2026). Era o `HEAD` do repositório
  público até esta reorganização.
- **Nunca executou o experimento completo.** Nenhum número do relatório vem daqui.
- **Diferenças que impedem a reprodução dos resultados publicados:**

  | Mudança | Consequência |
  |---|---|
  | Adiciona uma etapa de **Simulated Annealing** depois do AG | A fórmula final não é mais a campeã do AG; muda o objeto medido |
  | Adiciona `src/Config.h` com quatro modos (`--mode absolute\|delta\|admissibility\|hybrid`) | Comportamento condicional que não existia em março |
  | Acrescenta as colunas `implementacao` e `modo` a todos os CSVs | **Esquema incompatível.** Os scripts de análise de março leem por posição/nome e quebram |
  | `resultados_sintese.csv` passa a ter `formula_pre_sa` / `formula_pos_sa` / `tempo_sa_ms` / `admissibility_rate` no lugar de `formula_string` | Idem |
  | Corrige o cálculo de `ratio` quando o caminho ótimo é degenerado | Melhor, mas diferente do que gerou os dados (ver P6) |

- **Traz também** `tests/`, um framework de teste mínimo com 2 casos. É a única parte do
  repositório com teste automatizado.
- **Vale a pena manter?** Sim: contém correções reais de bugs que estão diagnosticados em
  `docs/historico/code_review.md`. Só não pode ser confundida com o código do experimento.

### Agosto/2026 — a reanálise estatística

- **Análise:** `analise/estatistica-2026-08/` — 13 scripts (A0…A12), 34 tabelas, 2 figuras.
- **Código C++ auxiliar:** `codigo/medicoes-2026-08/` — cinco programas que medem coisas que a
  execução de março **não instrumentou** (baseline de Dijkstra, custo de memória e tempo de
  pré-computação dos pivôs, reprocessamento sob degradação, re-síntese com semente fixa).
- **Não re-executou o experimento principal.** Releu os mesmos CSVs brutos de março e refez a
  estatística sobre eles. Por isso os achados de agosto são comparáveis aos números do
  relatório: é literalmente o mesmo dado, tratado de outro jeito.
- **O `src/` dentro de `codigo/medicoes-2026-08/` é uma cópia do código de março com uma única
  alteração deliberada:** as sementes do algoritmo genético viraram parâmetro explícito, em vez
  de virem de `std::random_device`. Sem essa alteração a análise A9 (reprodutibilidade da
  síntese) seria impossível. Ver `docs/04-problemas-conhecidos.md`, P5.

### Novembro/2026 — a robustez com o protocolo de degradação v2

- **Código:** `codigo/robustez-2026-11/` (branch `robustez-v2`). Usa o `src/` de
  `codigo/medicoes-2026-08/`, cujos `map.cpp`, `heuristics.cpp` e `astar.cpp` são byte a byte
  os de março (`make confere-src`).
- **Por quê:** o laço de robustez de março perdia de 89% a 99% dos pares a 30% e escolhia os
  pares só nesse nível (P2). O gerador v2 usa os mesmos mecanismos e sorteios de `map.cpp`, mas
  nunca bloqueia origem ou destino de par (R1) nem divide uma componente (R2), e registra a meta
  atingida (R3). Requisitos em `docs/especificacoes/degradacao-conectividade/spec.md`.
- **Não sintetiza nada.** As fórmulas vêm de `dados/resultados_sintese.csv` (P7: `arena` usa a
  primeira linha). A linha de base no mapa original é recalculada e o programa **aborta** se ela
  não bater com `resultados_base.csv` de março.
- **Produziu** (fora do Git, ~0,9 GB):
  - `dados/brutos/v2/resultados_robustez_v2.csv`: as colunas de `resultados_robustez.csv`, mais
    `exp_deg_mem_congelado` e `em_treino`;
  - `dados/brutos/v2/degradacao_v2_resumo.csv`: % atingido, células recusadas por R1 e R2,
    pares válidos v2 e v1 e colapso de pivô, por mapa × semente × padrão × nível. Uma cópia é
    versionada em `analise/estatistica-2026-08/medicoes/`.
- **Decisões e números:** `docs/06-protocolo-v2.md`.

---

## Onde os dados brutos estão

Fora do Git, por tamanho. Ver [`dados/MANIFESTO.md`](../dados/MANIFESTO.md).

Um detalhe que economiza confusão: existia um `WPerformance/results.db` (SQLite, 85 MB) versionado
no GitHub. Foi verificado célula a célula que ele é **espelho exato** dos quatro CSVs — mesma
contagem de linhas e mesma soma por coluna. Não é uma fonte independente; é uma cópia em outro
formato, mantida no pacote do Drive por conveniência de consulta.

---

## As citações de linha nos documentos de análise continuam válidas

Os documentos da reanálise (`docs/historico/ANALISE_*.md`) citam trechos de código por número
de linha — `main.cpp:227`, `main.cpp:73-86`, `heuristics.cpp`, `GeneticAlgorithm.cpp:19,68`.
**Todas essas referências são à versão de março**, e os arquivos foram copiados para cá sem
nenhuma edição. Basta prefixar o caminho:

```
main.cpp:227            →  codigo/run-referencia-2026-03/src/main.cpp:227
GeneticAlgorithm.cpp:19 →  codigo/run-referencia-2026-03/src/synthesis/GeneticAlgorithm.cpp:19
```

As referências a `main.tex:NNN` são ao fonte LaTeX do relatório, que **não** está neste
repositório — só o PDF compilado está, em `relatorio/`.

---

## O que foi descartado na reorganização, e por quê

| Descartado | Motivo |
|---|---|
| `Nova Analise/heuristicas/` | Cópia byte a byte de `Run Antiga/heuristicas/` (verificado com `diff -r`). Redundante. |
| `Nova Analise/resultados_*.csv` | Cópia byte a byte dos CSVs de março (verificado com `md5sum`). Redundante. |
| `pathfinding` (binário ELF, 178 KB) | Binário compilado versionado por engano. Reconstruível com `make`. |
| `.gemini/`, `.claude/`, `.specify/` | Ferramental de assistentes de IA, sem valor de arquivo. |
| `.venv/` da análise | Ambiente virtual Python. Reconstruível a partir de `requirements.txt`. |
| Binários das medições de agosto | Reconstruíveis com `make` em `codigo/medicoes-2026-08/`. |
| `.git/` das cópias antigas | Continham no *reflog* um commit atribuído a um colaborador indevido. Ver abaixo. |

O `openspec/specs/` **não** foi descartado: virou `docs/especificacoes/`. São requisitos
formais do experimento, escritos antes da implementação, e explicam *a intenção* por trás de
decisões que o código sozinho não justifica.

Nada foi apagado de fato: o material descartado está em
`~/projetos/heuristicas-DESCARTADO-20260827/`, e há um backup completo do estado anterior em
`~/projetos/heuristicas-BACKUP-20260827-1802.tar.gz`.

---

## Autoria

O trabalho é de **Alexandre Pereira de Souza Junior**.

Durante a reorganização apurou-se que um commit de março de 2026 havia sido gravado com uma
identidade de `git` de terceiro, trazida por engano numa cópia de *dotfiles*. O commit foi
corrigido por `--amend` ainda na época, com a autoria correta, mas o objeto original continuou
pendurado no *reflog* de cópias locais do repositório — nunca no histórico público.

Situação após a reorganização: o histórico do Git foi reiniciado do zero e **todo o histórico
é atribuído a um único autor**, sem nenhum objeto ou referência remanescente a terceiros.
