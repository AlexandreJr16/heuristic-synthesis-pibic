# Protocolo de degradação v2 — robustez refeita (outubro–novembro/2026)

Refaz **só a robustez** do experimento, para o artigo do JBCS. Síntese, fórmulas e linha de base
são as de março. Código em `codigo/robustez-2026-11/`, requisitos em
[`especificacoes/degradacao-conectividade/spec.md`](especificacoes/degradacao-conectividade/spec.md),
análise em `analise/estatistica-2026-08/scripts/b1_protocolo_v2.py`.

---

## 1. Por que refazer

O laço de robustez de março (`main.cpp:204-266`) tinha dois defeitos:

- **P2.** Os pares válidos eram escolhidos uma vez, no estado de 30%, e reaproveitados a 10% e 20%.
- **Degradação destrutiva.** `degradaMapa*` bloqueava origem e destino de pares e desconectava o
  mapa. A 30% sobravam de 0,75% (linear) a 10,7% (estocástico) dos pares, cada padrão com uma
  população diferente e enviesada para pares curtos. Isso impedia comparar δ entre padrões.

## 2. O que o v2 faz

Os mesmos cinco mecanismos de `map.cpp`, com os mesmos parâmetros, o mesmo limite de tentativas
e a mesma sequência de `rand()` (`grid = original; srand(semente)` por padrão, cumulativo
10 → 20 → 30). Só o ponto de bloqueio passa por três regras:

- **R1.** Origem e destino de todos os pares do `.scen` nunca são bloqueados.
- **R2.** Uma célula só é bloqueada se não dividir a componente conexa (4-vizinhança) a que
  pertence. Teste local no anel 3×3; quando ele não decide, BFS bidirecional com parada
  antecipada entre os vizinhos livres. A célula recusada fica livre e vira passagem; no linear,
  a parede ganha uma porta. Componentes que já existiam no original continuam como estão.
- **R3.** Meta absoluta por nível (alvo do nível − células já bloqueadas). O resumo registra o %
  atingido e as células recusadas.

`verificaNivel` aborta a execução se, em qualquer nível, R1, R2, a cumulatividade ou a
conectividade de algum par original falhar.

## 3. Decisões tomadas

| Decisão | Escolha | Por quê |
|---|---|---|
| Meta do nível seguinte quando um nível não atinge o alvo | **absoluta** (alvo − já bloqueadas) | não acumula déficit nem excesso; no fim nenhuma combinação ficou abaixo do alvo |
| Coluna de memória com as distâncias do original | **incluída** (`exp_deg_mem_congelado`) | separa o efeito do recálculo (P1) |
| Pivôs | **não protegidos**, como em março | proteger mudaria o objeto medido |
| Colapso de pivô (P8) | **mantido sem correção** | a comparação com o estático depende do mesmo código |
| `rejeitadas_r1/r2` | **células distintas**; tentativas em `tentativas_r1/r2` | é o que o nome diz; a contagem por tentativa ficou guardada |
| Compilação | `g++ -O2 -std=c++17`, como `medicoes-2026-08` | os tempos não sustentam conclusão (P3); IEEE portável |
| Divergência da fórmula no `den602d` | **exceção declarada** (3 problemas, valores fixos no código) | ver §4; qualquer outra divergência aborta |
| Nomes dos regimes da memória | **com atualização** (recalculada) e **sem atualização** (congelada) | o recálculo não garante o melhor resultado: no v1 ele piorava o δ do padrão linear |

Consequências registradas:

- Até a primeira rejeição, a sequência de sorteios do v2 é idêntica à de março; depois diverge,
  porque o laço até a meta e o passeio do orgânico dependem de quantas células foram bloqueadas.
- No `arena` (130 pares) todos os pares estão na amostra de treino do AG
  (`main.cpp:108-117`); o recorte fora do treino tem n = 16 mapas.
- Um pivô bloqueado continua sendo fonte da BFS (`bfsPivo` não confere `grid[pivô]`); ver §6.

## 4. Verificações

| Verificação | Resultado |
|---|---|
| Fidelidade: com R1/R2 desligadas, o v2 dá o mesmo hash de grid que `map.cpp` | 50/50 (`arena`, `brc201d`, 5 sementes × 5 padrões) |
| R1, R2, cumulatividade, determinismo (`make teste`) | 50/50 |
| Controle negativo: `verificaNivel` recebe um grid v1 | aborta por R1 (feito à mão; automatizar está pendente) |
| Linha de base contra `resultados_base.csv` de março | Manhattan e memória: 85/85 iguais. Fórmula: igual, exceto 3 problemas do `den602d` |
| Controle negativo da exceção: divergência declarada que não aparece | aborta |
| v1 reproduzido a 30% contra `tabelas/a10_sobrevivencia_por_padrao.csv` | idêntico nos 5 padrões |
| Pares válidos em cada nível = pares conectados no original | 23.210 por semente em todos os 1.275 (mapa, semente, padrão, nível) |
| Análise v2 rodada duas vezes | 22 tabelas byte a byte iguais |
| Análise v1 depois das mudanças em `comum.py` | 34 tabelas byte a byte iguais; figuras com os mesmos pixels |

**A divergência do `den602d` (P11).** Nos ids 440, 711 e 2075, iguais nas 5 sementes, a fórmula dá
1 expansão a mais ou 2 células de caminho de diferença em relação a março. O valor exato da
fórmula cai em cima de um inteiro e o `double` IEEE trunca 1 abaixo. Uma avaliação com as
constantes decimais exatas reproduz março nos 2.660 problemas do mapa; recompilar com as flags
de março (`-O3 -march=native -ffast-math`) no GCC atual não. No v2, os δ usam a linha de base do
próprio v2, então ficam internamente consistentes.

## 5. Piloto e execução

- **Piloto** (`den501d`, 5 sementes): 2 min 44 s de relógio com 5 processos, 727 s de CPU.
- **Execução completa** (`make rodar P=6`, 28/10/2026): 85 jobs, **7,6 h de CPU**, ≈ 1h40 de
  relógio, pico de 320 MB por processo. O job mais longo foi o `brc202d` (≈ 18 min).
- **Saída:** `resultados_robustez_v2.csv` (6.963.000 linhas, 976 MB) e `degradacao_v2_resumo.csv`
  (1.275 linhas). sha256 em `dados/MANIFESTO.md`.
- **Custo da degradação v2:** menos de 1% do tempo; no pior padrão (orgânico), ~7.600 BFS e
  ~7 milhões de células visitadas por mapa e semente, ~150 ms.

## 6. A degradação

### Sobrevivência dos pares (% de 116.050 por padrão e nível)

| Padrão | 10% v1 → v2 | 20% v1 → v2 | 30% v1 → v2 |
|---|---|---|---|
| Linear | 3,84 → **100** | 1,44 → **100** | 0,75 → **100** |
| Orgânico | 25,75 → **100** | 9,57 → **100** | 4,69 → **100** |
| Esparso | 27,34 → **100** | 10,65 → **100** | 4,31 → **100** |
| Radial | 39,82 → **100** | 19,40 → **100** | 9,55 → **100** |
| Estocástico | 74,20 → **100** | 36,94 → **100** | 10,73 → **100** |

### Bloqueio atingido e rejeições

Células distintas, somadas em mapas e sementes. "Livres" = células livres do mapa original.

| Padrão | Nível | Bloqueado v2 | Bloqueado v1 | R1 / livres | R2 / livres | R2 / bloqueadas |
|---|---|---|---|---|---|---|
| Linear | 10 | 10,12 | 10,12 | 1,13 | 0,32 | 3,19 |
| | 20 | 20,08 | 20,23 | 2,33 | 1,30 | 6,46 |
| | 30 | 30,06 | 30,34 | 3,67 | 3,35 | 11,13 |
| Orgânico | 10 | 10,57 | 10,71 | 1,42 | 2,38 | 22,55 |
| | 20 | 20,48 | 21,41 | 2,80 | 5,12 | 25,01 |
| | 30 | 30,35 | 32,02 | 4,25 | 8,46 | 27,89 |
| Radial | 10 | 10,60 | 10,80 | 1,60 | 3,66 | 34,57 |
| | 20 | 20,47 | 21,71 | 3,10 | 7,21 | 35,20 |
| | 30 | 30,45 | 32,41 | 4,62 | 10,98 | 36,05 |
| Esparso | 10 | 10,81 | 10,99 | 1,32 | 1,19 | 11,02 |
| | 20 | 20,76 | 21,97 | 2,64 | 3,34 | 16,10 |
| | 30 | 30,51 | 32,85 | 4,11 | 6,73 | 22,06 |
| Estocástico | 10 | 10,00 | 10,00 | 1,15 | 0,12 | 1,23 |
| | 20 | 20,00 | 20,00 | 2,33 | 0,57 | 2,83 |
| | 30 | 30,00 | 30,00 | 3,63 | 2,06 | 6,87 |

- Todas as 1.275 combinações atingiram o alvo inteiro `(int)(S·nível)`. O v1 passava do alvo
  (até 32,85% no esparso a 30%).
- O radial é o que mais vira passagem: a 30%, 36% das células que ele bloquearia ficaram livres
  para não dividir o mapa. O orgânico sorteia muito perto do que já foi recusado: por tentativa,
  a razão R2 / bloqueadas chega a 99% a 30% (`tentativas_r2`), contra 28% em células distintas.
- Tabela completa: `tabelas_v2/b1_rejeicao.csv`.

### Pivôs em célula bloqueada

`bfsPivo` não confere se a célula do pivô está livre. Um pivô bloqueado começa a BFS com
distância 0 e se espalha pelos vizinhos livres: a tabela dele vira "1 + distância ao vizinho
livre mais próximo", que continua 1-Lipschitz, então a heurística continua admissível e
consistente. Se o pivô bloqueado não tem nenhum vizinho livre, a tabela fica −1 em todas as outras
células e ele deixa de contribuir. Na memória sem atualização isso não importa (ela usa as
distâncias do original).

| Nível | Pivôs bloqueados v2 | dos quais sem vizinho livre | Pivôs bloqueados v1 | sem vizinho livre v1 |
|---|---|---|---|---|
| 10% | 9,6% (7.361) | 1.344 | 10,0% (7.614) | 2.570 |
| 20% | 18,1% (13.825) | 2.818 | 19,0% (14.498) | 5.390 |
| 30% | 27,1% (20.698) | 4.828 | 28,1% (21.471) | 8.784 |

De 76.500 pivôs por nível (85 mapa × semente × 5 padrões × 180 pivôs). O estocástico é o que
mais bloqueia pivôs (31% a 30%), o radial o que menos bloqueia (24%). Por padrão:
`tabelas_v2/b1_pivos_bloqueados.csv`. Programa: `codigo/robustez-2026-11/conta_pivos.cpp`.

**Colapso de pivô (P8):** 6 combinações de mapa e semente, nos 15 padrões × níveis de cada uma:
`brc000d` s123 e s789 (n = 50); `brc201d` s42 e s789 (n = 50), s123 (n = 10), s456 (n = 10 e 50).

## 7. Resultados

Duas métricas, ambas pela escada geométrica (instância → (mapa, padrão) → mapa, padrões com peso
igual), com o mapa como unidade (n = 17):

- **δ** = `exp_deg / exp_orig` da própria heurística: perda relativa;
- **razão absoluta** = `exp_heurística / exp_Manhattan` no mesmo estado do mapa. O ganho sobre a
  Manhattan é o inverso.

O δ sozinho engana: a Manhattan não sabe nada do mapa, então não tem informação a perder, e o δ
dela mede só o quanto o problema ficou mais difícil. Uma métrica de perda relativa sempre favorece
quem é pouco informado. A razão absoluta compara as heurísticas no mesmo mapa degradado.

### δ (todos os níveis; IC 95% BCa)

| Estratégia | Com atualização | Sem atualização |
|---|---|---|
| Manhattan | 1,690 [1,52; 1,95] | 1,690 [1,52; 1,95] |
| Fórmula | 1,789 [1,57; 2,07] | 1,789 [1,57; 2,07] |
| Memória-10 | 1,549 [1,46; 1,64] | 5,790 [4,76; 6,57] |
| Memória-20 | 1,630 [1,56; 1,71] | 7,348 [5,96; 8,16] |
| Memória-50 | 1,552 [1,42; 1,64] | 7,579 [5,48; 9,18] |
| Memória-100 | 1,550 [1,49; 1,61] | 9,245 [7,12; 10,41] |

Por nível (com atualização / sem atualização, só a memória muda):

| Estratégia | 10% | 20% | 30% |
|---|---|---|---|
| Manhattan | 1,466 | 1,734 | 1,899 |
| Fórmula | 1,493 | 1,804 | 2,128 |
| Memória-10 | 1,317 / 4,286 | 1,573 / 6,175 | 1,795 / 7,333 |
| Memória-100 | 1,267 / 6,382 | 1,554 / 9,999 | 1,891 / 12,381 |

**No v2 a fórmula não é a menos degradada.** No v1 (agosto) ela tinha o menor δ (1,128) e era a
menos degradada em 14 de 17 mapas; no v2 o δ dela (1,789) é o maior dos seis com atualização, e
ela é a menos degradada em 4 mapas. Restringindo o v2 aos mesmos pares que sobreviveram no v1 (cálculo exploratório, fora das
tabelas), a memória com atualização ainda fica à frente (δ 1,44 a 1,53 contra 1,75 da fórmula), então a mudança não vem só da população: vem de a
degradação v2 forçar desvios (parede com porta) onde a v1 descartava o par.

### Ganho sobre a Manhattan (1 / razão absoluta)

| Estratégia | Estático | Degradado | 10% | 20% | 30% |
|---|---|---|---|---|---|
| Fórmula | 2,80× | **2,64×** | 2,75 | 2,69 | 2,50 |
| Memória-10 com atualização | 4,37× | 4,77× | 4,87 | 4,82 | 4,63 |
| Memória-10 sem atualização | 4,37× | **1,28×** | 1,50 | 1,23 | 1,13 |
| Memória-100 com atualização | 7,87× | **8,58×** | 9,10 | 8,78 | 7,90 |
| Memória-100 sem atualização | 7,87× | **1,44×** | 1,81 | 1,36 | 1,21 |

Memória-20 e -50 em `tabelas_v2/b1_global.csv`.

### Postos de Friedman (1 = melhor), estático → degradado, todos os níveis

| Estratégia | δ, com atualização | δ, sem atualização | absoluta, com atualização | absoluta, sem atualização |
|---|---|---|---|---|
| Manhattan | 5,94 → 3,53 | 5,94 → **1,41** | 5,94 → 6,00 | 5,94 → 5,82 |
| Fórmula | 4,47 → 4,06 | 4,47 → 1,59 | 4,47 → 4,82 | 4,47 → **1,00** |
| Memória-10 | 4,12 → 2,41 | 4,12 → 3,12 | 4,12 → 3,94 | 4,12 → 4,94 |
| Memória-20 | 2,94 → 4,18 | 2,94 → 4,12 | 2,94 → 2,88 | 2,94 → 3,88 |
| Memória-50 | 2,47 → 4,06 | 2,47 → 4,76 | 2,47 → 2,35 | 2,47 → 3,35 |
| Memória-100 | 1,06 → 2,76 | 1,06 → **6,00** | 1,06 → 1,00 | 1,06 → 2,00 |

- Friedman estático: χ² = 70,98, p < 10⁻¹³. Distância crítica de Nemenyi = 1,83 em todos.
- δ com atualização: χ² = 13,64, p = 0,018, e a Nemenyi não separa nenhum par. Sem atualização:
  χ² = 79,6, p ≈ 1,0 × 10⁻¹⁵.
- **Sem atualização, a ordem do δ se inverte por completo**: estático Mem-100 > 50 > 20 > 10 >
  Fórmula > Manhattan, degradado exatamente o contrário.
- **Na razão absoluta sem atualização, a fórmula é a melhor heurística nos 17 mapas** (posto
  1,00, em todos os níveis), e a memória perde quase toda a vantagem estática (Memória-100: de
  7,87× para 1,44×). Com atualização, a memória continua à frente nos 17 mapas.

### δ de Cliff e Wilcoxon (unidade = mapa, todos os níveis)

| Métrica, regime | Comparação | Cliff δ | Wilcoxon p |
|---|---|---|---|
| δ, com atualização | Manhattan × Mem-100 | +0,10 (desprezível) | 0,52 |
| δ, com atualização | Fórmula × Mem-100 | +0,25 (pequeno) | 0,064 |
| δ, sem atualização | Manhattan × Mem-100 | −0,99 (grande) | < 0,001 |
| δ, sem atualização | Fórmula × Mem-100 | −0,99 (grande) | < 0,001 |
| absoluta, sem atualização | Fórmula × Mem-100 | −0,97 (grande) | < 0,001 |
| absoluta, ambos | Fórmula × Manhattan | −1,00 (grande) | < 0,001 |

Por nível em `tabelas_v2/b1_cliff.csv`.

### Interação estratégia × padrão

Modelo `log y ~ estratégia × padrão × nível + mapa` sobre médias de célula (mapa × semente ×
padrão × nível), permutação do rótulo de estratégia dentro da instância (200, semente 20260820).

| Métrica | Regime | F | η²ₚ | p (permutação) |
|---|---|---|---|---|
| δ | com atualização | 29,90 | 0,073 | 0,005 |
| δ | sem atualização | 4,35 | 0,011 | 0,005 |
| absoluta | com atualização | 10,80 | 0,027 | 0,005 |
| absoluta | sem atualização | 6,49 | 0,016 | 0,005 |

p = 0,005 é o piso com 200 permutações (1/201): nenhuma permutação chegou perto (F nulo máximo
≤ 0,06). A interação existe, mas é pequena: no v1 o η²ₚ era 0,241, inflado pelas populações
diferentes entre padrões (P2).

### Só os pares fora do treino do AG (`em_treino == 0`, n = 16)

O quadro se repete. δ com atualização: Manhattan 1,635, Fórmula 1,781, Memória-100 1,569.
Ganho sobre a Manhattan: Fórmula 2,73×, Memória-100 com atualização 9,32×, sem atualização
1,47×. Na razão absoluta sem atualização, a fórmula volta a ter posto 1,00 nos 16 mapas.
Tabelas em `tabelas_v2_fora_treino/`.

## 8. O que os números sustentam

- "A fórmula é a menos degradada" **não vale no v2**. No v1 essa frase vinha dos pares curtos e
  do mapa partido.
- **Quem vence depende de a heurística poder ser atualizada:**
  - com as distâncias recalculadas, a memória continua bem à frente (Memória-100: 8,58× a
    Manhattan no degradado);
  - sem atualização, a ordem estática do δ se inverte por completo, a memória perde quase toda a
    vantagem (7,87× → 1,44×) e a fórmula conserva a maior parte da dela (2,80× → 2,64×), sem
    memória e sem custo de atualização.
- A memória sem atualização continua admissível e só perde eficiência: as distâncias do original
  não superestimam as do mapa degradado, que só perde arestas.
- **Custo de atualizar:** a pré-computação dos pivôs (escolha Farthest-First + BFS) custou de
  5,2 a 207,7 ms por mapa com 100 pivôs (`medicoes/pivos_precomp.csv`, agosto). Recalcular só as
  BFS de pivôs fixos custa menos que isso. Os tempos valem só como ordem de grandeza (P3).

## 9. Limitações que continuam

- **P3:** os tempos não sustentam conclusão; o v2 grava as colunas de tempo, mas a análise não
  as usa.
- **P5:** cada mapa tem uma fórmula só, de uma síntese não reprodutível.
- **P8:** o colapso de pivô foi mantido (§6) e entra nas médias.
- **P11:** 3 problemas do `den602d` divergem de março na linha de base (§4).
- O controle negativo de `verificaNivel` foi feito à mão; automatizar no `testa_degradacao`
  está pendente.

## 10. Como reproduzir

`docs/05-como-reproduzir.md`, seção 5 (C++), e `analise/estatistica-2026-08/README.md`, seção
"Protocolo v2" (`run_all.py --v2`).
