#!/usr/bin/env python3
"""Fila de trabalho retomável para as 85 sínteses semeadas (A9/E10).

Cada tarefa é uma síntese (mapa, semente) independente e determinística, tocada por
um processo `sintese_worker` isolado. Três camadas de proteção:

  1. Por tarefa   — o resultado vai para medicoes/sintese/<mapa>__<semente>.csv,
                    gravado com arquivo temporário + rename (atômico). Existir = pronto.
  2. Por geração  — o worker grava .ckpt a cada N gerações. Queda de energia perde,
                    no máximo, N gerações da tarefa em voo.
  3. Por parada   — Ctrl-C manda SIGTERM aos workers, que terminam a geração corrente,
                    gravam checkpoint e saem. Nada é perdido.

Reinvocar continua de onde parou, sempre. Rodar duas vezes em paralelo é seguro:
as tarefas são reivindicadas por lock exclusivo, e locks órfãos são recuperados.

    python scripts/sintese_pool.py                 # roda / continua
    python scripts/sintese_pool.py --status        # só mostra o progresso
    python scripts/sintese_pool.py --merge         # consolida o CSV final
"""
import argparse, os, signal, subprocess, sys, time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SINT = RAIZ / "medicoes" / "sintese"
# O C++ auxiliar das medições fica em codigo/medicoes-2026-08/ (ver docs/02-arquitetura-do-codigo.md).
CPP = RAIZ.parent.parent / "codigo" / "medicoes-2026-08"
FINAL = RAIZ / "medicoes" / "sintese_repetida.csv"
# com --sementes (ressintese do v2), o consolidado vai para formulas_v2_seed/, sem tocar no A9
FINAL_V2 = RAIZ / "formulas_v2_seed" / "formulas_v2_seed.csv"
CABECALHO = ("mapa,run_seed,populacao_inicial,n_geracoes,tempo_sintese_ms,"
             "formula_string,fitness_final,ast_size,ast_depth\n")

MAPAS = ["arena", "arena2", "brc000d", "brc100d", "brc101d", "brc201d", "brc202d",
         "brc203d", "den000d", "den005d", "den011d", "den012d", "den500d", "den501d",
         "den602d", "hrt201n", "lak506d"]
SEMENTES = [1, 2, 3, 4, 5]

MAIORES_PRIMEIRO = False

def custo_mapa(m):
    """tempo de uma sintese ja concluida do mapa (qualquer semente); sem nenhuma, conta como a mais cara"""
    ts = []
    for f in SINT.glob(f"{m}__*.csv"):
        try: ts.append(float(f.read_text().split(",")[4]))
        except Exception: pass
    return min(ts) if ts else float("inf")

def tarefas():
    # rodada completa antes da próxima: parar no meio ainda deixa rodadas inteiras
    t = [(m, s) for s in SEMENTES for m in MAPAS]
    if MAIORES_PRIMEIRO:
        # para encurtar a cauda: os mapas mais caros primeiro (a ordem nao muda o resultado de nenhuma tarefa)
        custo = {m: custo_mapa(m) for m in MAPAS}
        t.sort(key=lambda x: (-custo[x[0]], x[1]))
    return t

def pronta(m, s):   return (SINT / f"{m}__{s}.csv").exists()
def ckpt(m, s):     return SINT / f"{m}__{s}.ckpt"
def lock(m, s):     return SINT / f"{m}__{s}.lock"

def geracao_do_ckpt(m, s):
    p = ckpt(m, s)
    if not p.exists(): return None
    try:
        return int(p.read_text().splitlines()[1].split()[2])
    except Exception:
        return None

def lock_orfao(p):
    """Um lock cujo dono morreu (queda, kill -9) pode ser reivindicado."""
    try:
        pid = int(p.read_text().strip())
    except Exception:
        return True
    try:
        os.kill(pid, 0)
        return False
    except (ProcessLookupError, ValueError):
        return True
    except PermissionError:
        return False

def reivindicar(m, s):
    p = lock(m, s)
    if p.exists() and lock_orfao(p):
        p.unlink(missing_ok=True)
    try:
        fd = os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    os.write(fd, str(os.getpid()).encode()); os.close(fd)
    return True

def status():
    t = tarefas()
    feitas = [x for x in t if pronta(*x)]
    parciais = [(m, s, geracao_do_ckpt(m, s)) for m, s in t
                if not pronta(m, s) and ckpt(m, s).exists()]
    print(f"concluídas : {len(feitas)}/{len(t)}")
    for sem in SEMENTES:
        n = sum(1 for m, s in feitas if s == sem)
        barra = "█" * n + "·" * (len(MAPAS) - n)
        print(f"  rodada {sem}: {barra} {n}/{len(MAPAS)}")
    if parciais:
        print("em progresso (checkpoint gravado):")
        for m, s, g in parciais:
            print(f"  {m} s{s} — geração {g}/100")
    restam = len(t) - len(feitas)
    print(f"faltam     : {restam}")
    return len(feitas), restam

def merge():
    """Consolida os resultados por tarefa, normalizando o formato numérico.

    As 4 sínteses herdadas do programa monolítico gravaram fitness com 6 dígitos
    significativos e o worker grava com 6 casas decimais; o valor é o mesmo, mas o
    CSV fica uniforme assim.
    """
    import csv as _csv, io as _io
    linhas = []
    for m, s in tarefas():
        p = SINT / f"{m}__{s}.csv"
        if not p.exists():
            continue
        c = next(_csv.reader(_io.StringIO(p.read_text())))
        c[4] = f"{float(c[4]):.3f}"      # tempo_sintese_ms
        c[6] = f"{float(c[6]):.6f}"      # fitness_final
        buf = _io.StringIO()
        _csv.writer(buf, lineterminator="").writerow(c)
        linhas.append(buf.getvalue())
    tmp = FINAL.with_suffix(".tmp")
    tmp.write_text(CABECALHO + "\n".join(linhas) + ("\n" if linhas else ""))
    tmp.replace(FINAL)
    print(f"consolidado: {len(linhas)} sínteses -> {FINAL.relative_to(RAIZ)}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--ckpt", type=int, default=5, help="gerações entre checkpoints")
    ap.add_argument("--nice", type=int, default=19)
    ap.add_argument("--cores", default="0-5", help="núcleos permitidos, ex. 0-5")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--sementes", help="restringe a fila, ex. 1,2,3 (ressintese do v2)")
    ap.add_argument("--maiores-primeiro", action="store_true", help="fila pelos mapas mais caros primeiro")
    a = ap.parse_args()
    global MAIORES_PRIMEIRO
    MAIORES_PRIMEIRO = a.maiores_primeiro
    if a.sementes:
        global SEMENTES, FINAL
        SEMENTES = [int(x) for x in a.sementes.split(",")]
        FINAL = FINAL_V2
        FINAL.parent.mkdir(parents=True, exist_ok=True)

    SINT.mkdir(parents=True, exist_ok=True)
    if a.status: status(); return
    if a.merge: merge(); return

    lo, hi = (a.cores.split("-") + [None])[:2]
    nucleos = list(range(int(lo), int(hi) + 1)) if hi else [int(lo)]
    print(f"pool: {a.workers} workers, núcleos {a.cores}, nice {a.nice}, "
          f"checkpoint a cada {a.ckpt} gerações")
    feitas, restam = status()
    if not restam:
        merge(); return

    fila = [x for x in tarefas() if not pronta(*x)]
    ativos = {}          # Popen -> (mapa, semente)
    nucleo_de = {}       # Popen -> nucleo
    parando = False

    def ao_sinal(signum, frame):
        nonlocal parando
        if parando: return
        parando = True
        print(f"\n[parada solicitada] avisando {len(ativos)} worker(s); eles terminam a "
              f"geração corrente e gravam checkpoint...")
        for p in ativos: p.send_signal(signal.SIGTERM)
    signal.signal(signal.SIGINT, ao_sinal)
    signal.signal(signal.SIGTERM, ao_sinal)

    t0 = time.time()
    concluidas_agora = 0
    while (fila or ativos) and not (parando and not ativos):
        while fila and len(ativos) < a.workers and not parando:
            m, s = fila.pop(0)
            if pronta(m, s) or not reivindicar(m, s):
                continue
            # nucleo livre (antes era len(ativos) % n: depois de uma tarefa acabar, duas dividiam o mesmo nucleo)
            usados = {nucleo_de[q] for q in ativos}
            nuc = next((c for c in nucleos if c not in usados), nucleos[len(ativos) % len(nucleos)])
            cmd = ["taskset", "-c", str(nuc), "nice", "-n", str(a.nice),
                   "./sintese_worker", m, str(s), str(a.ckpt), "--saida", str(SINT)]
            p = subprocess.Popen(cmd, cwd=CPP, env={**os.environ, "OMP_NUM_THREADS": "1"},
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            ativos[p] = (m, s)
            nucleo_de[p] = nuc
            print(f"  -> {m} s{s} (núcleo {nuc})")
        time.sleep(2)
        for p in list(ativos):
            if p.poll() is None: continue
            m, s = ativos.pop(p)
            lock(m, s).unlink(missing_ok=True)
            if p.returncode == 0 and pronta(m, s):
                concluidas_agora += 1
                feitos = sum(1 for x in tarefas() if pronta(*x))
                dt = time.time() - t0
                eta = (dt / concluidas_agora) * (len(tarefas()) - feitos) / 3600
                print(f"  ok {m} s{s}   [{feitos}/{len(tarefas())}]  ETA ~{eta:.1f} h")
                merge()
            elif p.returncode == 130:
                g = geracao_do_ckpt(m, s)
                print(f"  ⏸  {m} s{s} pausada na geração {g}/100 (checkpoint gravado)")
            else:
                print(f"  ✗  {m} s{s} falhou (código {p.returncode}) — será refeita")

    merge()
    print("\n[parado — reinvoque para continuar de onde parou]" if parando
          else f"\n[todas as {len(tarefas())} sínteses concluídas]")

if __name__ == "__main__":
    main()
