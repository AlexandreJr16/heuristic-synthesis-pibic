"""Carga, deduplicação e utilitários estatísticos comuns às análises A0-A11.

Regras que valem para todo o pacote (ver plano):
  1. Razões agregam por média GEOMÉTRICA, nunca aritmética (Fleming & Wallace, 1986).
  2. A unidade de replicação para generalizar é o MAPA (n=17), não a instância (n=116.700).
  3. Normalizar por mapa antes de agrupar entre mapas.
  4. `arena` está duplicado nos CSVs (execução repetida em modo append) e é deduplicado
     em toda carga; a duplicata é insumo exclusivo do A9.

Protocolo v2 (novembro/2026, `codigo/robustez-2026-11/`), por variavel de ambiente:
  PROTOCOLO=v2   a robustez vem de resultados_robustez_v2.csv (HEURISTICAS_DADOS_V2,
                 padrao dados/brutos/v2) e a saida vai para tabelas_v2/ e figuras_v2/;
  FORA_TREINO=1  so os pares com em_treino == 0 (fora da amostra de aptidao do AG),
                 com saida em tabelas_v2_fora_treino/ e figuras_v2_fora_treino/.
Sem as variaveis, nada muda: tabelas/ e figuras/ continuam as de agosto.
"""
import os
from pathlib import Path
import numpy as np
import pandas as pd

SEED = 20260820

RAIZ = Path(__file__).resolve().parent.parent   # analise/estatistica-2026-08/
REPO = RAIZ.parent.parent                       # raiz do repositório

V2 = os.environ.get("PROTOCOLO") == "v2"
FORA_TREINO = os.environ.get("FORA_TREINO") == "1"
if FORA_TREINO and not V2:
    raise SystemExit("FORA_TREINO=1 exige PROTOCOLO=v2 (os dados de março não têm em_treino)")
SUFIXO = ("_v2" if V2 else "") + ("_fora_treino" if FORA_TREINO else "")

MEDICOES = RAIZ / "medicoes"
TABELAS = RAIZ / f"tabelas{SUFIXO}"
FIGURAS = RAIZ / f"figuras{SUFIXO}"
MAPAS_DIR = REPO / "maps"

# Os 4 CSVs brutos somam ~170 MB e NÃO ficam versionados no Git; eles vivem no
# pacote do Drive (02-dados-brutos/). Para rodar a análise, escolha uma das duas:
#   1) copie-os para <repo>/dados/brutos/ ; ou
#   2) exporte HEURISTICAS_DADOS apontando para a pasta que os contém, p.ex.
#      set -x HEURISTICAS_DADOS ~/Drive/PIBIC/02-dados-brutos   (fish)
# Ver dados/MANIFESTO.md para o esquema e os checksums de cada arquivo.
DADOS = Path(os.environ.get("HEURISTICAS_DADOS", REPO / "dados" / "brutos"))
DADOS_V2 = Path(os.environ.get("HEURISTICAS_DADOS_V2", REPO / "dados" / "brutos" / "v2"))


def _csv_bruto(nome):
    """Abre um dos CSVs brutos, com mensagem clara se os dados não estiverem no lugar."""
    caminho = DADOS / nome
    if not caminho.exists():
        raise SystemExit(
            f"\nDado bruto não encontrado: {caminho}\n"
            f"Os CSVs brutos (~170 MB) ficam fora do Git, no pacote do Drive.\n"
            f"Copie-os para {REPO / 'dados' / 'brutos'}/ ou exporte HEURISTICAS_DADOS\n"
            f"apontando para a pasta que os contém. Ver dados/MANIFESTO.md.\n"
        )
    return pd.read_csv(caminho)

CONFIGS = ["manhattan", "formula", "memory10", "memory20", "memory50", "memory100"]
ROTULOS = {"manhattan": "Manhattan", "formula": "Fórmula", "memory10": "Memória-10",
           "memory20": "Memória-20", "memory50": "Memória-50", "memory100": "Memória-100"}
PADROES = ["Linear", "Organic", "Radial", "Sparse", "Stochastic"]
NIVEIS = [0.1, 0.2, 0.3]
SEMENTES = [42, 123, 456, 789, 1011]

# Categorias conforme main.tex:653
def categoria(m):
    if m.startswith("arena"): return "Arena"
    if m.startswith("brc"):   return "Área aberta"
    if m.startswith("den"):   return "Dungeon"
    return "Natureza"

# Células (mapa, semente, n_pivos) em que o sorteio do 1º pivô caiu num bolsão
# desconexo e a heurística de memória colapsou para h≡0 (A11).
def celulas_degeneradas():
    p = pd.read_csv(MEDICOES / "pivos_precomp.csv")
    d = p[p.frac_consultas_h_zero > 0.5]
    return set(zip(d.mapa, d.semente, d.n_pivos))

def _dedup(df, chaves):
    """Remove a 2ª execução de `arena`, mantendo a 1ª ocorrência."""
    n0 = len(df)
    df = df.drop_duplicates(subset=chaves, keep="first").reset_index(drop=True)
    if n0 != len(df):
        print(f"    dedup: {n0} -> {len(df)} linhas ({n0-len(df)} duplicatas de arena)")
    return df

def carregar_base():
    df = _csv_bruto("resultados_base.csv")
    df = _dedup(df, ["mapa", "semente", "id_problema", "heuristica", "n_pivos"])
    df["config"] = np.where(df.heuristica == "memory",
                            "memory" + df.n_pivos.astype(str), df.heuristica)
    assert set(df.config) == set(CONFIGS), set(df.config)
    return df

def base_larga():
    """Uma linha por instância, uma coluna de expansões por configuração."""
    df = carregar_base()
    w = df.pivot_table(index=["mapa", "semente", "id_problema"],
                       columns="config", values="expansoes").reset_index()
    w.columns.name = None
    assert len(w) == 116050, len(w)
    return w

def base_larga_cache():
    p = MEDICOES / "base_larga.pkl"
    w = pd.read_pickle(p) if p.exists() else base_larga()
    if FORA_TREINO:
        w = w.merge(pares_fora_treino(), on=["mapa", "semente", "id_problema"])
    return w

def carregar_ratio():
    df = _csv_bruto("resultados_ratio.csv")
    return _dedup(df, ["mapa", "semente", "id_problema"])

def _robustez_v2():
    """resultados_robustez_v2.csv sem as colunas de tempo (P3), com tipos compactos e cache."""
    p = DADOS_V2 / "robustez_v2.pkl"
    if p.exists():
        return pd.read_pickle(p)
    caminho = DADOS_V2 / "resultados_robustez_v2.csv"
    if not caminho.exists():
        raise SystemExit(f"\nDado v2 não encontrado: {caminho}\n"
                         f"Gere com `make rodar` e `make juntar` em codigo/robustez-2026-11/,\n"
                         f"ou exporte HEURISTICAS_DADOS_V2. Ver dados/MANIFESTO.md.\n")
    inteiras = [f"{t}_{q}_{s}" for t in ("exp", "path") for q in ("orig", "deg")
                for s in ("manh", "form", "mem")] + ["exp_deg_mem_congelado"]
    tipos = {"mapa": "category", "tipo_degradacao": "category", "semente": "int16",
             "id_problema": "int32", "n_pivos": "int16", "porcentagem_bloqueio": "float64",
             "em_treino": "int8", **{c: "int32" for c in inteiras}}
    df = pd.read_csv(caminho, usecols=list(tipos), dtype=tipos)
    df.to_pickle(p)
    return df

def pares_fora_treino():
    """(mapa, semente, id_problema) com em_treino == 0, a partir dos dados v2."""
    r = _robustez_v2()
    k = r[(r.n_pivos == 10) & (r.tipo_degradacao == "Linear") & (r.porcentagem_bloqueio == 0.1)]
    k = k[k.em_treino == 0][["mapa", "semente", "id_problema"]]
    k["mapa"] = k.mapa.astype(str)
    return k.reset_index(drop=True)

def carregar_complemento(tipo):
    """complemento_<tipo>.csv de codigo/robustez-2026-11 (make complemento && make juntar-complemento):
    'congelada' (expansoes e caminho da memoria sem atualizacao), 'custo' (celulas das BFS de
    atualizacao) ou 'otimo' (distancia BFS no mapa degradado, pares com id % 10 == 0)."""
    caminho = DADOS_V2 / f"complemento_{tipo}.csv"
    if not caminho.exists():
        raise SystemExit(f"\nDado v2 não encontrado: {caminho}\n"
                         f"Gere com `make complemento` e `make juntar-complemento` em codigo/robustez-2026-11/.\n")
    df = pd.read_csv(caminho)
    if FORA_TREINO and "id_problema" in df:
        df = df.merge(pares_fora_treino(), on=["mapa", "semente", "id_problema"])
    return df

def carregar_robustez(cache=True):
    """Robustez deduplicada, com as colunas delta_* (fator de degradação pareado)."""
    if V2:
        df = _robustez_v2()
        if FORA_TREINO:
            df = df[df.em_treino == 0].reset_index(drop=True)
        df["mapa"] = df.mapa.astype(str)
        df["tipo_degradacao"] = df.tipo_degradacao.astype(str)
        for suf in ("manh", "form", "mem"):
            df[f"delta_{suf}"] = df[f"exp_deg_{suf}"] / df[f"exp_orig_{suf}"].clip(lower=1)
        df["delta_mem_congelado"] = df.exp_deg_mem_congelado / df.exp_orig_mem.clip(lower=1)
        return df
    p = MEDICOES / "robustez.pkl"
    if cache and p.exists():
        return pd.read_pickle(p)
    df = _csv_bruto("resultados_robustez.csv")
    df = _dedup(df, ["mapa", "semente", "id_problema", "tipo_degradacao",
                     "n_pivos", "porcentagem_bloqueio"])
    for suf in ("manh", "form", "mem"):
        df[f"delta_{suf}"] = df[f"exp_deg_{suf}"] / df[f"exp_orig_{suf}"].clip(lower=1)
    return df

def carregar_sintese():
    return _csv_bruto("resultados_sintese.csv")

def carregar_dijkstra():
    return pd.read_csv(MEDICOES / "dijkstra.csv")

def carregar_pivos():
    return pd.read_csv(MEDICOES / "pivos_precomp.csv")

def celulas_transitaveis():
    """|S| e estrutura de componentes conexas de cada mapa, a partir dos .map."""
    from collections import deque
    out = []
    for f in sorted(MAPAS_DIR.glob("*.map")):
        L = f.read_text().split("\n")
        h, w = int(L[1].split()[1]), int(L[2].split()[1])
        g = [[c == "." for c in L[4 + i]] for i in range(h)]
        seen = [[False] * w for _ in range(h)]
        comps = []
        for i in range(h):
            for j in range(w):
                if g[i][j] and not seen[i][j]:
                    q, n = deque([(i, j)]), 0
                    seen[i][j] = True
                    while q:
                        x, y = q.popleft(); n += 1
                        for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                            a, b = x+dx, y+dy
                            if 0<=a<h and 0<=b<w and g[a][b] and not seen[a][b]:
                                seen[a][b] = True; q.append((a,b))
                    comps.append(n)
        comps.sort(reverse=True)
        out.append(dict(mapa=f.stem, altura=h, largura=w, S=sum(comps),
                        n_componentes=len(comps), maior_componente=comps[0],
                        frac_fora_maior=1 - comps[0]/sum(comps)))
    return pd.DataFrame(out)

# ---------------------------------------------------------------- estatística

def media_geometrica(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x) & (x > 0)]
    return float(np.exp(np.mean(np.log(x)))) if len(x) else np.nan

def cliffs_delta(a, b):
    """δ de Cliff via postos: O(n log n). δ>0 => valores de `a` tendem a ser maiores."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    na, nb = len(a), len(b)
    todos = np.concatenate([a, b])
    r = pd.Series(todos).rank().to_numpy()
    ra = r[:na].sum()
    # U de Mann-Whitney a partir da soma de postos
    u = ra - na * (na + 1) / 2
    return float(2 * u / (na * nb) - 1)

def magnitude_cliff(d):
    a = abs(d)
    return "desprezível" if a < 0.147 else "pequeno" if a < 0.33 else \
           "médio" if a < 0.474 else "grande"

def holm(pvals):
    """Correção de Holm-Bonferroni. Devolve p ajustados na ordem original."""
    p = np.asarray(pvals, float)
    ordem = np.argsort(p)
    m = len(p)
    aj = np.empty(m)
    corr = 0.0
    for i, idx in enumerate(ordem):
        corr = max(corr, (m - i) * p[idx])
        aj[idx] = min(1.0, corr)
    return aj

def bootstrap_bca_geom(x, n_boot=10000, alpha=0.05, seed=SEED):
    """IC BCa para a média geométrica de x (usa scipy)."""
    from scipy.stats import bootstrap
    x = np.asarray(x, float)
    x = x[np.isfinite(x) & (x > 0)]
    if len(x) < 3:
        return (np.nan, np.nan)
    res = bootstrap((x,), media_geometrica, n_resamples=n_boot, method="BCa",
                    confidence_level=1 - alpha, random_state=np.random.default_rng(seed))
    return (float(res.confidence_interval.low), float(res.confidence_interval.high))

def nemenyi_cd(k, n, alpha=0.05):
    """Distância crítica de Nemenyi (Demšar 2006) para k tratamentos e n blocos."""
    from scipy.stats import studentized_range
    q = studentized_range.ppf(1 - alpha, k, np.inf) / np.sqrt(2)
    return float(q * np.sqrt(k * (k + 1) / (6.0 * n)))

def escada_geometrica(df, col_razao, por=("mapa", "semente")):
    """Instância -> (mapa,semente) -> mapa -> global, tudo por média geométrica."""
    g = df.groupby(list(por))[col_razao].apply(media_geometrica).reset_index()
    por_mapa = g.groupby("mapa")[col_razao].apply(media_geometrica)
    return por_mapa, media_geometrica(por_mapa)
