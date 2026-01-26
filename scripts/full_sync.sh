#!/bin/bash
# YellowOracle - Sincronizzazione completa
# Usa questo per la prima installazione o per ricostruire tutto
# Esegui: ./scripts/full_sync.sh [COMPETITIONS]
# Esempi:
#   ./scripts/full_sync.sh              # Tutte le competizioni
#   ./scripts/full_sync.sh "SA PL"      # Solo Serie A e Premier

PROJECT_DIR="/home/salvatore/Scrivania/soccer"
VENV_PYTHON="$PROJECT_DIR/venv/bin/python"
SYNC_SCRIPT="$PROJECT_DIR/scripts/sync_football_data.py"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/full_sync_$(date +%Y%m%d_%H%M%S).log"

# Competizioni di default (tutte)
ALL_COMPETITIONS="SA PL PD BL1 FL1 CL EL"
COMPETITIONS="${1:-$ALL_COMPETITIONS}"

mkdir -p "$LOG_DIR"

# Funzione di logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

echo "=========================================="
echo "Sincronizzazione COMPLETA YellowOracle"
echo "Competizioni: $COMPETITIONS"
echo "Tutte le stagioni (2023-2026)"
echo ""
echo "⚠️  Questa operazione richiede molto tempo"
echo "    (circa 30-45 minuti per competizione)"
echo "=========================================="
echo ""
echo "Log: $LOG_FILE"
echo ""

cd "$PROJECT_DIR" || {
    log "ERRORE: Impossibile accedere a $PROJECT_DIR"
    exit 1
}

# Verifica esistenza venv
if [ ! -f "$VENV_PYTHON" ]; then
    log "ERRORE: Python venv non trovato: $VENV_PYTHON"
    exit 1
fi

# Contatori
TOTAL=0
SUCCESS=0
FAILED=0

# Loop su tutte le competizioni
for COMP in $COMPETITIONS; do
    TOTAL=$((TOTAL + 1))
    log ""
    log "=========================================="
    log "Sincronizzazione COMPLETA: $COMP"
    log "=========================================="

    $VENV_PYTHON "$SYNC_SCRIPT" --competition "$COMP" --all-seasons --full 2>&1 | tee -a "$LOG_FILE"

    SYNC_EXIT_CODE=${PIPESTATUS[0]}

    if [ $SYNC_EXIT_CODE -eq 0 ]; then
        log "✅ $COMP completato"
        SUCCESS=$((SUCCESS + 1))
    else
        log "❌ $COMP fallito (exit code: $SYNC_EXIT_CODE)"
        FAILED=$((FAILED + 1))
    fi
done

# Pulizia log vecchi (più di 30 giorni)
find "$LOG_DIR" -name "full_sync_*.log" -mtime +30 -delete 2>/dev/null

# Riepilogo
log ""
log "=========================================="
log "Sincronizzazione COMPLETA terminata"
log "Totale: $TOTAL | Successo: $SUCCESS | Falliti: $FAILED"
log "=========================================="

echo ""
echo "Log salvato in: $LOG_FILE"

if [ $FAILED -gt 0 ]; then
    exit 1
fi
exit 0
