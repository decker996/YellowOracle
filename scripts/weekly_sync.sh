#!/bin/bash
# YellowOracle - Script di sincronizzazione settimanale
# Esegui manualmente: ./scripts/weekly_sync.sh [COMPETITION]
# Esempio: ./scripts/weekly_sync.sh PD
# Configura cron: crontab -e

# Configurazione
PROJECT_DIR="/home/salvatore/Scrivania/soccer"
VENV_PYTHON="$PROJECT_DIR/venv/bin/python"
SYNC_SCRIPT="$PROJECT_DIR/scripts/sync_football_data.py"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/sync_$(date +%Y%m%d_%H%M%S).log"

# Competizione di default (può essere sovrascritta con argomento)
COMPETITION="${1:-PD}"

# Crea directory log se non esiste
mkdir -p "$LOG_DIR"

# Funzione di logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Inizio
log "=========================================="
log "Inizio sincronizzazione YellowOracle"
log "Competizione: $COMPETITION"
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

# Esegui sincronizzazione solo stagione corrente (più veloce per update settimanale)
log "Sincronizzazione stagione corrente (2025-2026)..."
$VENV_PYTHON "$SYNC_SCRIPT" --competition "$COMPETITION" --season 2025-2026 --full 2>&1 | tee -a "$LOG_FILE"

SYNC_EXIT_CODE=${PIPESTATUS[0]}

if [ $SYNC_EXIT_CODE -eq 0 ]; then
    log "Sincronizzazione completata con successo"
else
    log "ERRORE: Sincronizzazione fallita (exit code: $SYNC_EXIT_CODE)"
fi

# Pulizia log vecchi (mantieni ultimi 30 giorni)
log "Pulizia log vecchi..."
find "$LOG_DIR" -name "sync_*.log" -mtime +30 -delete 2>/dev/null

log "=========================================="
log "Fine sincronizzazione"
log "=========================================="

# Mostra riepilogo
echo ""
echo "Log salvato in: $LOG_FILE"
echo "Per vedere i log recenti: ls -la $LOG_DIR"

exit $SYNC_EXIT_CODE
