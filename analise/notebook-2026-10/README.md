# A história dos dados v2 — notebook

`historia_v2.ipynb` conta, em atos, o que a robustez refeita com o protocolo v2 mostrou: do
problema do protocolo antigo ao resultado central (num mapa que muda, quem vence depende de a
heurística poder ser atualizada). Serve para explorar os dados e para tirar as figuras.

## Como rodar

O notebook já aponta para o kernel **"Heurísticas v2 (.venv da análise)"**
(`heuristicas-v2`), que é o `.venv` de `analise/estatistica-2026-08/`. Numa máquina nova, crie o
ambiente e registre o kernel uma vez, de dentro daquela pasta:

```fish
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m ipykernel install --user --name heuristicas-v2 --display-name "Heurísticas v2 (.venv da análise)"
```

Depois é só abrir o notebook no VS Code e usar "Run All" (uns 15 s). Se o VS Code abrir com
outro kernel, clique no nome do kernel no canto superior direito e escolha "Heurísticas v2" em
"Jupyter Kernel".

Pela linha de comando, da pasta do notebook:

```fish
../estatistica-2026-08/.venv/bin/jupyter nbconvert --to notebook --execute historia_v2.ipynb --output /tmp/historia_v2.ipynb
```

## O que ele precisa

- As tabelas do pipeline: `analise/estatistica-2026-08/tabelas_v2/`, `tabelas_v2_fora_treino/`,
  `tabelas/` e `medicoes/` (versionadas). Para refazê-las: `run_all.py --v2`.
- Os dados brutos v2 em `dados/brutos/v2/` (ou `HEURISTICAS_DADOS_V2`). Na primeira execução o
  notebook cria `dados/brutos/v2/cache/robustez_v2.parquet` (sem as colunas de tempo) e os
  grids de exemplo em `dados/brutos/v2/cache/grids/` (`make grids` em `codigo/robustez-2026-11/`).
  Tudo fora do Git.
- O `resultados_robustez.csv` de março, para o comprimento dos caminhos dos sobreviventes do v1.
  O notebook procura em `HEURISTICAS_DADOS`, depois em `dados/brutos/` e depois em `~/Downloads`.

## Regras

- Nenhum número é escrito à mão: toda frase que cita um valor sai de uma célula de código.
- Nenhuma análise estatística é refeita: o notebook lê as tabelas do pipeline. As únicas contas
  novas são descritivas (medianas de caminho) e o IC do ganho estático, com a mesma
  `bootstrap_bca_geom` de `comum.py`.
- Determinístico: as figuras saem byte a byte iguais a cada execução.

## Figuras

Exportadas para `figuras/`, em PNG (300 dpi) e PDF:

| Arquivo | Ato |
|---|---|
| `orientadora_ganho_estatico_degradado` | 5 — o resultado central |
| `orientadora_sobrevivencia_v1_v2` | 3 — os pares que o v1 perdia |
| `mapas_por_perfil` | 1 |
| `ganho_estatico` | 2 |
| `exemplo_linear_den501d_v1_v2` | 3 |
| `deformacao_por_padrao`, `exemplo_radial_den501d_v1_v2` | 4 |
| `ganho_por_nivel` | 5 |
| `delta_contra_ganho` | 6 |
| `consistencia_por_mapa` | 7 |
| `inversao_postos` | 8 |
| `padroes_facetas`, `eta2_v1_v2` | 9 |
| `wastar_controle` | 15 — fórmula contra Weighted A\* com o mesmo ρ |
