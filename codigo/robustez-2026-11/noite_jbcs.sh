#!/bin/sh
# Encadeia os testes do JBCS que dependem da sintese: espera a ressintese (sementes 1-3) terminar, consolida as
# formulas, avalia as formulas no v2 (teste 4) e so entao mede o tempo (teste 2) com a maquina parada.
# Rode a partir de codigo/robustez-2026-11:  setsid nohup sh noite_jbcs.sh > ../../dados/brutos/v2/noite_jbcs.log 2>&1 &
set -e
RAIZ=$(cd ../.. && pwd)
AN=$RAIZ/analise/estatistica-2026-08
PY=$AN/.venv/bin/python
FORM=$AN/formulas_v2_seed/formulas_v2_seed.csv
log() { echo "[$(date '+%F %T')] $*"; }

log "esperando a sintese"
while pgrep -f "sintese_pool.py --sementes" > /dev/null || pgrep -x sintese_worker > /dev/null; do sleep 120; done
(cd $AN && $PY scripts/sintese_pool.py --sementes 1,2,3 --status)
(cd $AN && $PY scripts/sintese_pool.py --sementes 1,2,3 --merge)
n=$(($(wc -l < $FORM) - 1))
log "formulas consolidadas: $n"
if [ "$n" -ne 51 ]; then log "esperava 51 formulas; parando"; exit 1; fi

log "teste 4: avaliando as formulas no v2"
make ressintese P=6 CPUS=0-5
make juntar-ressintese
log "teste 4 pronto"

log "esperando a maquina parar (b9 e qualquer outro job do experimento)"
while pgrep -f "b9_conferencias_jbcs|incremental_v2|ressintese_v2|robustez_v2|complemento_v2|wastar_v2" > /dev/null; do sleep 60; done
sleep 30
log "teste 2: medindo tempo (um nucleo)"
make tempo NUCLEO=2
make juntar-tempo
log "teste 2 pronto"
log "fim"
