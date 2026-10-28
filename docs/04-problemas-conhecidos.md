# Problemas conhecidos

Tudo que se sabe estar errado, impreciso ou traiçoeiro neste código e nestes dados.
**Leia antes de reaproveitar qualquer parte disto.**

Consolida três fontes, que continuam disponíveis na íntegra:
`docs/historico/code_review.md` (revisão de código de junho/2026),
`docs/historico/ANALISE_LIMITACOES.md` (L1–L10, agosto/2026) e
`docs/historico/BRIEFING_ANALISE_ESTATISTICA.md` (E1–E10).

Legenda: 🔴 afeta conclusões · 🟡 afeta números · 🟢 defeito sem impacto material

---

## 🔴 P1 — O texto do relatório diz que a memória não é reprocessada; o código a reprocessa

`codigo/run-referencia-2026-03/src/main.cpp:244` chama `computarDistPivosFixos`, que roda
`bfsPivo` **na grade já degradada**. Só as posições dos pivôs ficam congeladas; 93,4% das
distâncias mudam.

**Consequência:** os fatores de degradação da heurística de memória devem ser lidos como um
**limite superior** — ela recebe uma atualização completa de tabelas que o texto diz que ela
não recebe. A tese sobrevive e fica mais forte (a fórmula ganha em 5 de 5 padrões sem receber
nada), mas o mecanismo descrito no §5.4 está errado.

*(Achado A0. Correção de texto em `ANALISE_CORRECOES_TEXTO.md`.)*

## 🔴 P2 — O filtro de conectividade é aplicado uma vez só, no estado de 30%

`main.cpp:217-224` seleciona os pares válidos **uma única vez**, com o mapa já a 30% de
bloqueio, e usa esse mesmo conjunto nos níveis de 10% e 20%.

**Consequências, em ordem de gravidade:**

1. Não há como recuperar, dos CSVs, quantos pares teriam sobrevivido a 10% ou a 20% — a
   informação nunca foi gravada (L1).
2. Cada padrão de degradação sobrevive com uma **população de pares diferente e não aninhada**:
   de 0,75% (linear) a 10,73% (estocástico), com caminho ótimo mediano de 5 a 111 células.
   A interseção dos cinco padrões tem **71 instâncias**. Comparar **magnitudes de δ entre
   padrões** é, portanto, confundido, e não tem conserto pleno (L2).
3. A comparação **entre estratégias**, essa sim, é limpa: as 6 configurações rodam sobre o
   mesmo par, na mesma linha do CSV.

Mitigação aplicada: a análise A1 refaz o modelo dentro da faixa de comprimento comum aos cinco
padrões, onde a interação estratégia × padrão sobrevive (η²ₚ = 0,123 contra 0,241). Isso mostra
que a interação não é artefato de seleção, mas não recupera a comparabilidade das magnitudes.

Corrigir exigiria reinstrumentar o laço de seleção e **re-executar toda a robustez**.

> ✅ **Resolvido no protocolo v2 (novembro/2026).** A robustez foi re-executada em
> `codigo/robustez-2026-11/`, com os requisitos de
> [`especificacoes/degradacao-conectividade/spec.md`](especificacoes/degradacao-conectividade/spec.md):
> os pares são validados **em cada nível** e o gerador nunca bloqueia origem ou destino (R1) nem
> divide uma componente (R2). Com isso, os pares válidos são todos os conectados no mapa original,
> nos três níveis e nos cinco padrões: a população é a mesma e as magnitudes de δ passam a ser
> comparáveis entre padrões. O texto acima continua valendo para os dados de março. Decisões e
> números em [`06-protocolo-v2.md`](06-protocolo-v2.md).

## 🔴 P3 — `tempo_ms` não é uma medição confiável de desempenho

Medição única por instância, sem aquecimento, sem repetições, sem isolamento de CPU nem
controle de frequência, com o binário em `-O3 -march=native -ffast-math`, numa máquina
compartilhada com o resto do experimento.

A duplicata de `arena` prova o problema: as duas execuções dão **expansões idênticas** (o A\* é
determinístico) e **tempos diferentes**.

**Re-executar não conserta** — sem protocolo de *benchmark* o número continua sem sentido. Por
isso toda a análise lidera com **expansões de nós**. Mantenha a coluna de tempo como
indicativa; não sustente nenhuma conclusão nela (L3).

## 🔴 P4 — Dois geradores de números aleatórios convivem no mesmo programa

`map.cpp` e `generatePivots` usam `rand()` / `srand()` (gerador global do C); o subsistema de
síntese usa `std::mt19937`. Sementear um não afeta o outro, e `rand()` é o gerador global —
qualquer chamada em qualquer ponto avança o mesmo estado.

Na prática funcionou (os resultados por semente são consistentes), mas a reprodutibilidade
depende da **ordem exata das chamadas**, o que torna qualquer refatoração do laço principal
capaz de mudar os números sem mudar a lógica.

## 🔴 P5 — A síntese pelo AG não é reprodutível

`synthesis/GeneticAlgorithm.cpp:19` e `:68` criam `std::mt19937 gen(std::random_device{}())`
dentro de `initPopulation` e `reproduction`. A gramática e os operadores recebem semente 42,
mas **o AG sorteia da entropia do sistema**.

**Consequência:** cada fórmula em `resultados_sintese.csv` é uma **amostra de tamanho 1**, de
uma execução que não pode ser repetida. A Tabela 3 do relatório não é "a fórmula que o método
encontra para o mapa X"; é "uma fórmula que o método encontrou uma vez".

Medido em A9, com uma cópia do código em que essa entropia virou parâmetro: **12 de 13 mapas
testados dão fórmula diferente**. A correção no código é de duas linhas — passar a semente
adiante, como já é feito na gramática e nos operadores. É exatamente o que
`codigo/medicoes-2026-08/src/` faz (L4, E10).

## 🟡 P6 — `ratio` forçado a 1,0 quando não existe caminho

`main.cpp:175`: `ratio = (resD.path.size() <= 1) ? 1.0 : ...`. Pares sem caminho recebem
ρ = 1,0, isto é, aparecem como **perfeitamente ótimos**. São 45 linhas em 116.050, em 6 mapas.
Excluídas do A6; o efeito no ρ médio é da ordem de 10⁻⁴ (L6).

Corrigido na versão de junho — que, por isso mesmo, produziria uma coluna `ratio` ligeiramente
diferente da publicada.

## 🟡 P7 — Os CSVs são abertos em `ios::app`, e `arena` foi contado duas vezes

`main.cpp:73-86` abre os quatro arquivos em modo *append*. `arena` foi processado duas vezes, e
**todos os números do relatório incluem esses 650 pares em dobro** (3.900 linhas em
`resultados_base.csv`, 12.900 em `resultados_robustez.csv`).

Como `arena` é o menor e mais fácil dos mapas, o efeito é puxar médias agrupadas para baixo — é
a origem da diferença entre o 7.472,95 do relatório e o 7.514,59 deduplicado. Toda a reanálise
deduplica automaticamente em `comum.py::_dedup` (L7).

**Se for rodar o experimento de novo, apague os `resultados_*.csv` antes.**

## 🟡 P8 — Colapso de pivô: a heurística de memória vira Dijkstra em silêncio

Detalhado em `docs/03-achados-estatisticos.md` (A11). O primeiro pivô é sorteado uniformemente;
se cair num bolsão desconexo, todos os pivôs ficam presos lá e `h ≡ 0`.

Aconteceu em **7 das 340 células (mapa × semente × nº de pivôs)**, todas em `brc201d` (167
componentes conexas) e `brc000d` (2 componentes). Nessas células a memória fica **pior que
Manhattan** (13.290 contra 7.163 expansões). A nota da Tabela 4 exclui só `(brc000d, 50)` e
mantém caladas as outras seis.

Correção: sortear o primeiro pivô dentro da maior componente conexa.

## 🟡 P9 — Coordenadas trocadas na verificação de admissibilidade *(só na versão de junho)*

Na versão de junho, a checagem de admissibilidade avalia a fórmula com `{coluna, linha}`
enquanto o A\* a avalia com `{linha, coluna}`. Para fórmulas simétricas não muda nada; para
assimétricas, `admissibility_rate` mede uma função diferente da que roda de fato.

**Não afeta os dados publicados** — a versão de março não tem esse campo. Diagnóstico completo
em `docs/historico/code_review.md`, BUG 1.

## 🟢 P10 — Modo `hybrid` nunca gera terminais de pivô *(só na versão de junho)*

O modo existe, mas a gramática não emite os terminais que ele pressupõe, então ele se comporta
como o modo `delta`. Ver `code_review.md`, BUG 2. Nunca foi usado em nada publicado.

## 🟢 P11 — A heurística é truncada para `int`

`heuristicaFormula` faz `static_cast<int>` do valor da AST. Perde precisão fracionária e, para
fórmulas que devolvem valores negativos, não há *clamping* para zero. Na prática o A\* tolera
(um `h` negativo só torna a busca mais parecida com Dijkstra), mas é uma imprecisão real.
Ver `code_review.md`, ISSUE 4 e ISSUE 7.

**Consequência medida em novembro/2026 (robustez v2).** O truncamento torna a fórmula sensível
ao arredondamento quando o valor exato cai em cima de um inteiro. Ao recalcular a linha de base
com o código de março em `double` IEEE (`-O2`), Manhattan e memória batem com
`resultados_base.csv` nas 85 combinações mapa × semente, mas a fórmula do `den602d` diverge em
**3 de 2.660 problemas** (ids 440, 711 e 2075, iguais nas 5 sementes): 1 expansão a mais ou 2
células de caminho de diferença. Uma avaliação com as constantes decimais exatas reproduz março
nos 2.660; recompilar com as flags de março (`-O3 -march=native -ffast-math`) no GCC atual não
reproduz. O binário de março, de outro GCC, calculou mais perto do valor exato.
`codigo/robustez-2026-11/robustez_v2.cpp` declara essas 3 divergências, com os valores dos dois
lados, e aborta se aparecer outra ou se uma delas sumir. No v2, os δ usam a linha de base
recalculada pelo próprio v2, então ficam internamente consistentes.

## 🟢 P12 — `bfsPivo` aloca a grade inteira por pivô

Custo de memória **4,1× o teórico** (até 8,2×), chegando a 109 MB num único mapa com 100 pivôs.
Não afeta a corretude, mas é o número que sustenta o eixo "memória" da conclusão, e ele foi
medido só em agosto (A7, E8).

---

## Resumo: o que é seguro afirmar a partir destes dados

| Afirmação | Segura? |
|---|---|
| Comparar **estratégias entre si**, no mesmo mapa e no mesmo par | ✅ desenho pareado, limpo |
| Comparar **expansões de nós** | ✅ determinístico e reprodutível |
| Comparar **magnitudes de δ entre padrões de degradação** | ❌ populações não aninhadas (P2); ✅ nos dados v2 (`06-protocolo-v2.md`) |
| Sustentar conclusão em **tempo de execução** | ❌ instrumentação inadequada (P3) |
| Tratar as fórmulas da Tabela 3 como **"a" fórmula de cada mapa** | ❌ amostra de tamanho 1 (P5) |
| Dizer que a memória **não é reprocessada** sob degradação | ❌ o código a reprocessa (P1) |
| Usar os *speedups* de memória da Tabela 4 original | ❌ populações diferentes; usar os corrigidos (A3) |
