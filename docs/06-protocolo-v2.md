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
| Controle negativo: `verificaNivel` recebe um grid v1 (Linear, s42, 10%) | aborta, em `arena` e `brc201d` (`make teste`) |
| Linha de base contra `resultados_base.csv` de março | Manhattan e memória: 85/85 iguais. Fórmula: igual, exceto 3 problemas do `den602d` |
| Controle negativo da exceção: divergência declarada que não aparece | aborta |
| v1 reproduzido a 30% contra `tabelas/a10_sobrevivencia_por_padrao.csv` | idêntico nos 5 padrões |
| Pares válidos em cada nível = pares conectados no original | 23.210 por semente em todos os 1.275 (mapa, semente, padrão, nível) |
| Análise v2 rodada duas vezes | 22 tabelas byte a byte iguais |
| Análise v1 depois das mudanças em `comum.py` | 34 tabelas byte a byte iguais; figuras com os mesmos pixels |
| `complemento_v2` reproduz as expansões da memória sem atualização do `robustez_v2` | 6.963.000 de 6.963.000 iguais |
| Custo de atualizar contado por componente contra `bfsPivo` real | igual em todos os jobs (o programa aborta se diferir) |
| Caminho da Manhattan no mapa degradado contra BFS (pares com id % 10 == 0) | 174.075 de 174.075 iguais |
| Proposição A: caminho da memória = ótimo | 0 violações em 1.740.750 buscas por número de pivôs, no original e nos dois regimes |

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
- **Medição complementar** (`make complemento P=6`, 28/10/2026): caminho e expansões da memória sem
  atualização, células visitadas para atualizar os pivôs e o ótimo por BFS numa amostra. 85 jobs,
  **5,8 h de CPU**, ≈ 1 h de relógio. sha256 em `dados/MANIFESTO.md`.
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
≤ 0,06). Nesta medida (η²ₚ sobre células), a interação é bem menor que no v1 (0,241), que era inflado
pelas populações diferentes entre padrões (P2). Com o mapa como sujeito, ela continua significativa e
o η²ₚ é grande (§11); o padrão muda o tamanho das diferenças, mas não troca a ordem entre a fórmula e
a memória.

### Só os pares fora do treino do AG (`em_treino == 0`, n = 16)

O quadro se repete. δ com atualização: Manhattan 1,635, Fórmula 1,781, Memória-100 1,569.
Ganho sobre a Manhattan: Fórmula 2,73×, Memória-100 com atualização 9,32×, sem atualização
1,47×. Na razão absoluta sem atualização, a fórmula volta a ter posto 1,00 nos 16 mapas.
Tabelas em `tabelas_v2_fora_treino/`.

## 8. Qualidade do caminho e Proposição A (`b2_qualidade_caminho.py`)

**Método.** ρ = caminho da fórmula ÷ caminho ótimo. No mapa degradado, o ótimo é o caminho da Manhattan
(`path_deg_manh`), conferido contra BFS em 174.075 pares (todos iguais). Pares com origem = destino têm
ρ = 1. A Proposição A é testada comparando o caminho da memória com o ótimo em todas as buscas.

| Cenário | ρ (média geométrica nos mapas, IC 95% BCa) | caminhos ótimos | excesso > 10% |
|---|---|---|---|
| estático | 1,1045 [1,080; 1,126] | 18,5% | 44,9% |
| degradado 10% | 1,1107 [1,091; 1,126] | 12,2% | 50,8% |
| degradado 20% | 1,1043 [1,091; 1,116] | 10,2% | 48,2% |
| degradado 30% | 1,0840 [1,074; 1,096] | 10,1% | 34,3% |
| degradado, todos | 1,0996 [1,086; 1,112] | 10,9% | 44,4% |

- Por mapa, ρ degradado vai de 1,044 a 1,142. Fora do treino: 1,1032 [1,092; 1,114].
- **A degradação não piora o caminho da fórmula:** o excesso médio fica em ~10%, como no estático.
  O que cai é a fração de caminhos exatamente ótimos (18,5% → 10,9%).
- **Proposição A confirmada:** 0 violações nos dois regimes (§4).

> Sem atualização, a fórmula expande **1,84×** menos que a melhor memória congelada (Memória-100), ao
> custo de caminhos **10,0%** mais longos em média. Fora do treino: 1,86× e 10,3%.

Figuras: `figuras_v2/fig_b2_rho`; notebook, `rho_formula_por_mapa`.

## 9. Ponto de equilíbrio da atualização (`b3_equilibrio.py`)

**Método.** Custo de atualizar U = células visitadas pelas BFS dos pivôs fixos no mapa degradado,
contadas por `complemento_v2` (por componente conexa, conferido contra `bfsPivo`). Economia por
busca = média aritmética de expansões da alternativa − da memória atualizada, no mesmo mapa, nível e
número de pivôs. Com 1 expansão = c visitas de BFS, Q* = U ÷ (c × economia).

| Memória-100 contra a fórmula, Q* (mediana [mín; máx] nos mapas) | 10% | 20% | 30% |
|---|---|---|---|
| c = 1 | 1.131 [571; 11.649] | 910 [526; 3.167] | 763 [491; 1.503] |
| c = 2 | 565 [285; 5.824] | 455 [263; 1.583] | 381 [245; 751] |
| c = 5 | 226 [114; 2.329] | 182 [105; 633] | 152 [98; 300] |
| c = 10 | 113 [57; 1.165] | 91 [52; 317] | 76 [49; 150] |

- **Com a memória mais barata de cada mapa** (o número de pivôs que alcança a fórmula com menos
  buscas, em geral 10 ou 20), Q* com c = 1 cai para 154 [64; 3.423], 126 [62; 515] e 105 [58; 335]
  buscas a 10, 20 e 30%; com c = 10, para 15, 13 e 11.
- Contra a memória sem atualização com os mesmos pivôs, atualizar compensa mais cedo: medianas de 37 a
  621 buscas com c = 1, conforme nível e pivôs.
- **Sem economia:** em 9 combinações (mapa, nível, pivôs) a memória atualizada expande mais que a
  fórmula e Q* = ∞: `brc000d` com 50 pivôs e `brc201d` com 10 e 50. São exatamente as células de
  colapso de pivô.
- **Sensibilidade a c:** Q*(c) = Q*(1)/c em todas as linhas. A conclusão qualitativa não muda (há um
  limiar; abaixo dele a fórmula vence); c só desloca o limiar.

> Com mudanças a cada menos de **921** buscas (mediana entre os mapas; de 532 a 2.891, com c = 1 e
> Memória-100), a fórmula é a melhor escolha; acima disso, atualizar a memória compensa. Fora do
> treino: 911 (534 a 1.980).

Figuras: `figuras_v2/fig_b3_equilibrio`, `fig_b3_equilibrio_perfis`; notebook, `equilibrio_atualizacao`,
`equilibrio_por_perfil`.

## 10. Mecanismo da perda da memória sem atualização (`b4_mecanismo.py`)

**Método.** Desvio do par r = `path_deg_manh / path_orig_manh`; aumento = `exp_deg / exp_orig` da
heurística. Spearman entre r e o aumento, por mapa (sementes, padrões e níveis juntos); Wilcoxon pareado
por mapa. 2.700 linhas com origem = destino ficam fora.

| Spearman(r, aumento), mediana [mín; máx] nos 17 mapas | |
|---|---|
| Manhattan | 0,44 [0,12; 0,83] |
| Fórmula | 0,60 [0,28; 0,88] |
| Memória-10 sem / com atualização | 0,61 [0,13; 0,83] / 0,46 [0,12; 0,71] |
| Memória-100 sem / com atualização | 0,77 [0,59; 0,84] / 0,76 [0,66; 0,92] |

| Aumento mediano por faixa de desvio | r = 1 | 1–1,1 | 1,1–1,5 | 1,5–2 | > 2 |
|---|---|---|---|---|---|
| Manhattan | 1,00 | 1,02 | 1,17 | 1,65 | 6,60 |
| Fórmula | 1,00 | 1,02 | 1,52 | 2,47 | 7,63 |
| Memória-100 com atualização | 1,00 | 1,08 | 1,40 | 1,94 | 3,36 |
| Memória-100 sem atualização | 1,00 | 7,13 | 12,95 | 18,50 | 26,19 |

- A Memória-100 sem atualização correlaciona mais que a fórmula em 14 de 17 mapas (Wilcoxon p = 0,0004);
  a Memória-10 sem atualização, não (7 de 17, p = 1,00). **A correlação sozinha não separa as
  heurísticas**; o que separa é a magnitude.
- **A perda é em degrau:** com até 10% de desvio, a memória congelada já expande 4 a 7× mais (10 a 100
  pivôs), contra 1,02× da fórmula e da Manhattan.
- **Com r = 1** (caminho ótimo inalterado), o aumento mediano é 1,00 em todas as heurísticas, inclusive
  a memória congelada; 18% a 32% dos pares pioram um pouco em todas.

Figuras: `figuras_v2/fig_b4_aumento_por_desvio`; notebook, `mecanismo_desvio`.

## 11. Interação estratégia × padrão sem pseudorreplicação (`b5_modelo_misto.py`)

**Método.** Células = média de log da razão por (mapa, semente, padrão, nível, estratégia). (1) Modelo
misto `log y ~ estratégia × padrão × nível`, intercepto aleatório por mapa e variância da semente dentro
do mapa, ML; teste de razão de verossimilhança para os termos com estratégia × padrão. (2) O mesmo com
variância da estratégia dentro do mapa. (3) `AnovaRM` sobre as médias por mapa, com o mapa como sujeito.

- **Os quatro testes** (os três acima e a permutação do b1) **dão p < 0,05 nas quatro combinações** de
  métrica e regime, nos dois recortes. Todos convergiram; alguns ajustes avisam "MLE na fronteira".
- Componentes de variância (modelo padrão, escala log): mapa 0,015 a 0,091; semente 0,0014 a 0,015;
  resíduo 0,039 a 0,136.
- **Medidas repetidas, η²ₚ da interação:** δ com atualização 0,64; δ sem 0,50; ganho com 0,66; ganho sem
  0,33. É grande porque o erro passa a ser só a variação da interação entre mapas; não se compara ao
  η²ₚ sobre células da §7 (0,073).
- **Leitura:** a interação existe também com o mapa como unidade. O padrão muda o tamanho das diferenças
  entre as estratégias, mas não troca a ordem entre a fórmula e a memória (com atualização acima, sem
  atualização abaixo) em nenhum padrão e nível.

Tabelas: `b5_modelo_misto.csv`, `b5_anovarm_<métrica>_<regime>.csv`.

## 12. Conferências (`b6_conferencias.py`)

- **Memória-10 estática, 4,37× (v2) contra 4,70× (agosto).** Agosto publicou o ganho **excluindo** as
  7 células (mapa, semente, pivôs) de colapso de pivô; com elas, o mesmo cálculo dá 4,37×. O v2
  reproduz as duas versões exatamente (tolerância relativa 10⁻⁹). O mesmo vale para a Memória-50
  (7,32× sem colapso, 5,92× com). Memória-20 e -100 não têm colapso. **Para o artigo:** usar o número
  com colapso (4,37×), porque o v2 mantém o colapso em toda a análise degradada; o sem colapso entra
  como sensibilidade.
- **Memória sem atualização pior que a Manhattan.** Por mapa: `brc000d` (Memória-50, 0,69×), `brc201d`
  (Memória-10, 0,91×; Memória-50, 0,76×). Por (mapa, semente, pivôs): 8 células, das quais 7 são
  exatamente as de colapso; a oitava é `arena` s42 com 10 pivôs, razão 1,001 (empate). Sem as células
  de colapso, nenhum mapa fica pior que a Manhattan (a Memória-10 sem atualização vai de 1,276× para
  1,305×; a Memória-50, de 1,321× para 1,417×).

## 13. Controle: fórmula contra Weighted A* (`b7_wastar.py`)

**Pergunta.** A fórmula ganha da Manhattan porque superestima: troca caminhos ~10% mais longos por menos
expansões. O Weighted A\* (WA\*, h = w · Manhattan) faz a mesma troca sem aprender nada. Com caminhos de
qualidade igual, a fórmula expande menos que o WA\*? Se sim, a forma dela vale mais que um peso; se não,
a vantagem vem só da superestimação.

**Método** (`codigo/robustez-2026-11/wastar_v2`, dados em `dados/brutos/v2/wastar_*.csv`).

- **WA\*:** o `aStar` de março sem mudança, com h = ⌊w · Manhattan⌋ (o A\* só aceita h inteiro; o ⌊·⌋
  mantém h ≤ w · h\* e, com w = 1, dá exatamente a Manhattan). O teto do WA\* (w → ∞) é a busca gulosa
  (**GBFS**, f = h): uma cópia do `aStar` que só troca a prioridade, com o mesmo desempate (maior g) e sem
  reabrir fechados.
- **Conferência:** com w = 1, o WA\* reproduz as expansões e os caminhos da Manhattan já medidos em
  **139.260 pares** (23.210 no original e 23.210 em cada padrão a 30%, semente 42): **0 divergências**.
- **Calibração** (pares `em_treino == 1`, mapa original): ρ alvo = média geométrica de
  caminho da fórmula ÷ ótimo. Grade w ∈ {1,1; 1,25; 1,5; 2; 3}, ampliada para 5 e 10 e, se preciso, até a
  GBFS; bisseção entre os vizinhos que cercam o alvo até |Δρ| ≤ 0,005 (no máximo 8 iterações; com a GBFS
  como teto, bisseção em 1/w). Ficam w\*, o cerco w_inf (ρ ≤ alvo) e w_sup (ρ ≥ alvo).
- **Avaliação** (pares `em_treino == 0`; o `arena` não tem nenhum, então n = 16): original e os 5 padrões ×
  3 níveis × 5 sementes do v2, com os pesos fixos, como a fórmula, que também não é atualizada. Por mapa e
  cenário, médias geométricas como no b2.
- **Regra:** **vence** se a fórmula expande menos que o WA\* com w_sup; **perde** se expande mais que o
  WA\* com w_inf; **empata** entre os dois. **Fora da curva:** nem a GBFS chega ao ρ da fórmula na
  calibração, e a GBFS expande mais que ela. A fórmula faz uma troca entre expansões e qualidade de
  caminho que nenhum peso uniforme sobre a Manhattan reproduz. Não conta como vitória nem como derrota.

**Calibração.** 16 mapas casam o ρ (todos dentro da tolerância). w\* mediano 5,75, de 1,05 (`arena`) a 40
(`brc202d`). 11 mapas precisaram de w > 3. Em 6 deles (`arena2`, `brc202d`, `den000d`, `den005d`,
`den501d`, `den602d`), w = 10 ainda não chegava ao alvo e foi a GBFS que fechou o cerco. Só no `brc202d` o
w_sup é a própria GBFS. Fora da curva: **`brc100d`** (ρ alvo 1,097; GBFS 1,093, com 1,12× as expansões da
fórmula). A GBFS expande mais que a fórmula em todos os 17 mapas (de 1,01× a 2,21×).

| Cenário (pares fora do treino) | vence | empata | perde | fora da curva |
|---|---|---|---|---|
| original | 15 | 0 | 0 | 1 |
| degradado 10% | 15 | 0 | 0 | 1 |
| degradado 20% | 15 | 0 | 0 | 1 |
| degradado 30% | 15 | 0 | 0 | 1 |

Por padrão (níveis agregados): 15 / 0 / 0 / 1 em todos. Por padrão × nível, os únicos empates são
`Linear` 20% (1) e `Linear` 30% (2).

| Expansões WA\* (w\*) ÷ fórmula, 15 mapas | média geométrica | IC 95% BCa | mediana | intervalo entre os mapas | Wilcoxon p | δ de Cliff |
|---|---|---|---|---|---|---|
| original | **1,55** | [1,37; 1,93] | 1,38 | 1,15–3,51 | 6,1·10⁻⁵ | −0,46 (médio) |
| degradado 10% | **1,39** | [1,26; 1,67] | 1,27 | 1,11–2,83 | 6,1·10⁻⁵ | −0,46 (médio) |
| degradado 20% | **1,33** | [1,21; 1,57] | 1,21 | 1,09–2,55 | 6,1·10⁻⁵ | −0,45 (médio) |
| degradado 30% | **1,27** | [1,17; 1,49] | 1,17 | 1,06–2,35 | 6,1·10⁻⁵ | −0,36 (médio) |
| degradado, todos | **1,33** | [1,22; 1,58] | 1,23 | 1,09–2,57 | 6,1·10⁻⁵ | −0,44 (médio) |

A estatística-padrão é a média geométrica nos mapas com IC 95% BCa (n = 15); a mediana e o intervalo
entram como apoio.

A fórmula expande menos que o WA\* com w\* nos 15 mapas, em todos os cenários (p = 6,1·10⁻⁵ é o menor
possível do Wilcoxon exato com n = 15). Com o `brc100d` comparado à GBFS, n = 16: média geométrica
1,51× [1,34; 1,90] no original e 1,31× [1,21; 1,55] no degradado.

> Com caminhos de qualidade igual, a fórmula expande **1,55× menos** que o WA\* no mapa original
> (média geométrica entre 15 mapas, IC 95% BCa 1,37–1,93) e **1,33× menos** no mapa degradado
> (IC 1,22–1,58).
> Em 1 mapa nem a GBFS chega ao ρ da fórmula (fora da curva).

**O que enfraquece, e quanto.**

- **O casamento de ρ escorrega fora do treino.** O cerco [w_inf, w_sup] é estreito (|Δρ| ≤ 0,005), e o ρ
  da fórmula nos pares novos sai dele em 8 dos 15 mapas no original (em 5 fica acima de w_sup). A
  diferença de ρ fórmula − WA\*(w\*) tem mediana +0,004 no original (Wilcoxon p = 0,64) e cresce com a
  degradação: +0,005, +0,009 e +0,010 a 10, 20 e 30% (p = 0,11; 0,04; 0,06). No degradado, então, parte da
  vantagem é comprada com caminhos um pouco piores que os do WA\*. **Isso não muda a conclusão:** a
  expansão do WA\* cai com w (uma exceção de 0,2%, `den005d` entre w = 10,625 e 11,25). A GBFS é o ponto
  de menos expansões em todas as curvas da calibração e em todos os cenários avaliados. E nos 15 mapas, em
  todos os cenários agregados, a fórmula expande menos que a GBFS, com ρ ≤ o dela: fica **abaixo da curva
  inteira**, qualquer que seja o peso. Por padrão × nível isso vale em 11 a 15
  mapas; os casos que faltam se concentram no `Linear` a 20–30%, os mesmos dos empates.
- **A vantagem encolhe com a degradação** (média geométrica 1,55× → 1,27× a 30%), mas fica acima de 1× em todos os mapas e
  níveis.
- **`brc100d`:** fora da curva no original. No degradado, a GBFS passa a ter ρ pior que o da fórmula
  (1,107 contra 1,102) e continua expandindo 1,08× mais: lá a fórmula domina a GBFS. O mapa fica na
  categoria definida pela calibração.
- **⌊w · Manhattan⌋:** o arredondamento discretiza h. É o mesmo para todos os pesos e não afeta w = 1.

Tabelas: `wastar_conferencia_w1.csv`, `wastar_calibracao.csv`, `wastar_avaliacao.csv`, `wastar_decisao.csv`,
`wastar_decisao_contagem.csv`, `wastar_fora_da_curva.csv`, `wastar_estatistica.csv`, `wastar_frase.csv`.
Figuras: `figuras_v2/wastar_curva_mapa_mediano` (`den012d`, o mapa de razão mediana),
`wastar_curva_multiplos` e `wastar_degradado`; notebook, `wastar_controle` (ato 15).

## 14. O que os números sustentam

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
- **Quando atualizar compensa (§9):** em operações, atualizar a Memória-100 se paga a partir de ~921
  buscas entre mudanças (mediana; c = 1), ou de ~105 a 154 com a memória mais barata de cada mapa. Abaixo
  disso, a fórmula é a melhor escolha. O limiar escala com 1/c.
- **O preço da fórmula (§8):** caminhos ~10% mais longos que o ótimo, no estático e no degradado.
- **O mecanismo (§10):** a memória congelada perde em degrau assim que o caminho ótimo desvia; se o
  caminho não muda, ela não perde.
- **A forma da fórmula vale mais que um peso (§13):** com o mesmo ρ, o WA\* expande 1,55× o que a fórmula
  expande no original e 1,33× no degradado (média geométrica entre 15 mapas, IC 95% BCa 1,37–1,93 e
  1,22–1,58; todos os mapas a favor da fórmula); num 16º
  mapa nem a busca gulosa chega ao ρ da fórmula.

## 15. Limitações que continuam

- **P3:** os tempos não sustentam conclusão; o v2 grava as colunas de tempo, mas a análise não
  as usa.
- **P5:** cada mapa tem uma fórmula só, de uma síntese não reprodutível.
- **P8:** o colapso de pivô foi mantido (§6) e entra nas médias.
- **P11:** 3 problemas do `den602d` divergem de março na linha de base (§4).
- **Ponto de equilíbrio:** o custo é contado em operações, com 1 expansão = c visitas de BFS; o c real
  depende da implementação e não foi medido (P3). Não entra o custo da pré-computação inicial, que é o
  mesmo para os dois regimes da memória, nem o da síntese da fórmula, que é feita uma vez, fora de
  linha.

## 16. Como reproduzir

`docs/05-como-reproduzir.md`, seção 5 (C++), e `analise/estatistica-2026-08/README.md`, seção
"Protocolo v2" (`run_all.py --v2`).
