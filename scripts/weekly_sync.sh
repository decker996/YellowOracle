#!/bin/bash
# YellowOracle - Script di sincronizzazione settimanale (incrementale)
# Usa --days 7 per sincronizzare solo le partite degli ultimi 7 giorni
# Esegui manualmente: ./scripts/weekly_sync.sh [COMPETITIONS]
# Esempi:
#   ./scripts/weekly_sync.sh              # Tutte le competizioni
#   ./scripts/weekly_sync.sh "SA PL"      # Solo Serie A e Premier
#   ./scripts/weekly_sync.sh SA           # Solo Serie A
# Configura cron: crontab -e

# Configurazione
PROJECT_DIR="/home/salvatore/Scrivania/soccer"
VENV_PYTHON="$PROJECT_DIR/venv/bin/python"
SYNC_SCRIPT="$PROJECT_DIR/scripts/sync_football_data.py"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/sync_$(date +%Y%m%d_%H%M%S).log"

# Competizioni di default (tutte)
ALL_COMPETITIONS="SA PL PD BL1 FL1 CL EL"
COMPETITIONS="${1:-$ALL_COMPETITIONS}"

# Crea directory log se non esiste
mkdir -p "$LOG_DIR"

# Funzione di logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Inizio
log "=========================================="
log "Inizio sincronizzazione YellowOracle"
log "Competizioni: $COMPETITIONS"
log "=========================================="

# Vai nella directory del progetto
cd "$PROJECT_DIR" || {
    log "ERRORE: Impossibile accedere a $PROJECT_DIR"
    exit 1
}

# Verifica che il venv esista
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
    log "--- Sincronizzazione $COMP ---"

    $VENV_PYTHON "$SYNC_SCRIPT" --competition "$COMP" --days 7 --full 2>&1 | tee -a "$LOG_FILE"

    SYNC_EXIT_CODE=${PIPESTATUS[0]}

    if [ $SYNC_EXIT_CODE -eq 0 ]; then
        log "✅ $COMP completato"
        SUCCESS=$((SUCCESS + 1))
    else
        log "❌ $COMP fallito (exit code: $SYNC_EXIT_CODE)"
        FAILED=$((FAILED + 1))
    fi
done

# Pulizia log vecchi (mantieni ultimi 30 giorni)
log ""
log "Pulizia log vecchi..."
find "$LOG_DIR" -name "sync_*.log" -mtime +30 -delete 2>/dev/null

# Riepilogo
log ""
log "=========================================="
log "Fine sincronizzazione"
log "Totale: $TOTAL | Successo: $SUCCESS | Falliti: $FAILED"
log "=========================================="

# Mostra riepilogo
echo ""
echo "Log salvato in: $LOG_FILE"
echo "Per vedere i log recenti: ls -la $LOG_DIR"

# Exit con errore se almeno una sync è fallita
if [ $FAILED -gt 0 ]; then
    exit 1
fi
exit 0
