# Como reproduzir

Todos os comandos partem da **raiz do repositório**. Os exemplos usam sintaxe **fish**.

---

## 1. Compilar o C++

```fish
make ajuda          # lista os alvos
make referencia     # código de março/2026 -> bin/pathfinding-referencia
make refatoracao    # código de junho/2026 -> bin/pathfinding-refatorado
make testes         # compila e roda os 2 testes unitários
make limpar         # remove bin/
```

Requisitos: `g++` com C++17 e OpenMP. As flags são
`-O3 -march=native -ffast-math -fopenmp` — as mesmas do experimento original.

> `-march=native` gera instruções específicas da máquina onde se compila (o experimento
> original rodou num Ryzen 5 5500, Zen 3). O binário não é portátil entre máquinas, mas a
> contagem de **expansões** é determinística e independente disso — só os tempos mudam.

## 2. Re-executar o experimento completo ⚠️

```fish
rm -f resultados_base.csv resultados_ratio.csv resultados_robustez.csv resultados_sintese.csv
./bin/pathfinding-referencia
```

- **Leva cerca de 20 horas** nos 17 mapas.
- Os arquivos são abertos em modo *append*: **apague-os antes**, senão os dados novos se somam
  aos antigos (foi assim que `arena` ficou duplicado — ver `04-problemas-conhecidos.md`, P7).
- O resultado **não será idêntico** ao publicado: a síntese pelo AG usa entropia do sistema e
  produz fórmulas diferentes a cada execução (P5). As partes determinísticas — expansões de
  Manhattan, de Dijkstra, e a escolha dos pivôs por semente — sim, se repetem.

Para acompanhar, compare com `docs/historico/log-execucao-referencia-2026-03.txt`, que é o log
da execução original.

## 3. Refazer a reanálise estatística

Esta é a parte que **reproduz exatamente**, e é a que vale a pena rodar.

### 3.1 Obter os dados brutos

Os quatro CSVs (~170 MB) não estão no Git. Pegue-os no pacote do Drive
(`02-dados-brutos/`) e faça uma das duas coisas:

```fish
# opção A — copiar para dentro do repositório (dados/brutos/ está no .gitignore)
mkdir -p dados/brutos
cp ~/Drive/PIBIC/02-dados-brutos/resultados_*.csv dados/brutos/

# opção B — apontar a variável de ambiente para onde eles estiverem
set -x HEURISTICAS_DADOS ~/Drive/PIBIC/02-dados-brutos
```

Confira a integridade com `dados/MANIFESTO.md`:

```fish
cd ~/Drive/PIBIC/02-dados-brutos; and sha256sum -c SHA256SUMS.txt
```

### 3.2 Preparar o ambiente Python

```fish
cd analise/estatistica-2026-08
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Versões fixadas em `requirements.txt`: numpy 2.3.5, pandas 2.3.3, scipy 1.16.3,
statsmodels 0.14.6, matplotlib 3.10.8.

### 3.3 Rodar

```fish
cd analise/estatistica-2026-08
.venv/bin/python scripts/run_all.py
```

**~3 minutos.** Regenera as **34 tabelas** em `tabelas/` e as **2 figuras** em `figuras/`.
A ordem das etapas em `run_all.py` importa: há dependências entre tabelas (`a7` depende de
`a2` e `a6`; `a0` depende de `a1`).

Semente global dos scripts: `20260820`. A execução é determinística — as tabelas geradas devem
bater **byte a byte** com as versionadas. Se não baterem, algo mudou no ambiente:

```fish
cd analise/estatistica-2026-08
git status tabelas/     # deve estar limpo depois de rodar
```

### 3.4 Refazer as medições em C++ (opcional)

`medicoes/` já traz os resultados prontos. Para refazê-los:

```fish
cd codigo/medicoes-2026-08
make
./medir_dijkstra                        # ~minutos
./medir_pivos                           # ~minutos
for m in arena arena2 brc000d brc100d brc101d brc201d brc202d brc203d \
         den000d den005d den011d den012d den500d den501d den602d hrt201n lak506d
    ./verifica_reprocessamento $m 42
end
```

A re-síntese do A9 é o único trabalho longo (~12 h em 6 núcleos) e roda por um supervisor com
checkpoint e retomada segura:

```fish
cd analise/estatistica-2026-08
.venv/bin/python scripts/sintese_pool.py --status   # onde está
.venv/bin/python scripts/sintese_pool.py            # roda / continua de onde parou
.venv/bin/python scripts/sintese_pool.py --merge    # consolida o CSV final
```

Parar com `Ctrl-C` é seguro em qualquer momento. O manual completo — as três camadas de
proteção, por que a retomada não altera resultados, e o que fazer se algo falhar — está em
`docs/historico/ANALISE_RETOMAR.md`.

## 4. Refazer as figuras da análise original de março

```fish
cd analise/original-2026-03
python3 analise.py          # imprime 11 blocos de tabelas no terminal
python3 gerarGraficos.py    # gera as figuras
```

Estes scripts esperam os `resultados_*.csv` **no diretório de trabalho** — eles são de antes da
reorganização e não foram adaptados, de propósito: são o registro de como as tabelas da
primeira versão do texto foram produzidas. Copie os CSVs para junto deles, ou rode a partir de
uma pasta que os contenha.

> Os números que esses scripts produzem são os **antigos**, incluindo os que a reanálise
> depois corrigiu (ver `03-achados-estatisticos.md`, A3). Eles estão preservados para
> rastreabilidade, não para uso.

## 5. Re-executar a robustez com o protocolo v2 (novembro/2026)

Refaz só a robustez, com o gerador que protege os extremos dos pares (R1) e preserva a
conectividade (R2). Não sintetiza nada: as fórmulas vêm de `dados/resultados_sintese.csv`, e a
linha de base é recalculada e **conferida contra `resultados_base.csv` de março** (aborta se não
bater). Por isso precisa dos dados brutos de março (seção 3.1).

```fish
cd codigo/robustez-2026-11
make                                                     # g++ -O2 -std=c++17
env HEURISTICAS_DADOS=$HOME/Downloads make teste         # R1, R2, cumulativa, determinismo, linha de base
env HEURISTICAS_DADOS=$HOME/Downloads make piloto        # den501d, 5 sementes, ~3 min
env HEURISTICAS_DADOS=$HOME/Downloads make rodar P=6     # 85 jobs, ~1h30 a 2h com 6 processos
make juntar                                              # dados/brutos/v2/*.csv + sha256
```

- Troque `$HOME/Downloads` pela pasta onde estão os CSVs de março. No fish, use `$HOME`, não `~`:
  o fish não expande `~` depois do `=`, e o programa aborta sem achar o CSV.
- **Parar com `Ctrl-C` é seguro.** Cada job (mapa, semente) só grava o arquivo final quando
  termina; rodar `make rodar` de novo pula os prontos e refaz os interrompidos. Não altere o
  código entre as sessões.
- O resultado é **determinístico**: mesma semente, mesmo grid e mesmas expansões. Só as colunas
  de tempo mudam entre execuções (P3).
- Detalhes em `codigo/robustez-2026-11/README.md`; decisões e números em `06-protocolo-v2.md`.

---

## Verificação rápida de que tudo está no lugar

```fish
make testes                                          # 2 passed, 0 failed
make referencia; and ls -la bin/                     # binário gerado
cd analise/estatistica-2026-08; and .venv/bin/python -c "import comum; print(comum.DADOS)"
```

O último comando imprime onde os scripts vão procurar os dados brutos.
