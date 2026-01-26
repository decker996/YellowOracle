#!/bin/bash
# YellowOracle - Sincronizzazione completa
# Usa questo per la prima installazione o per ricostruire tutto

PROJECT_DIR="/home/salvatore/Scrivania/soccer"
VENV_PYTHON="$PROJECT_DIR/venv/bin/python"
SYNC_SCRIPT="$PROJECT_DIR/scripts/sync_football_data.py"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/full_sync_$(date +%Y%m%d_%H%M%S).log"

# Competizione di default (può essere sovrascritta con argomento)
COMPETITION="${1:-PD}"

mkdir -p "$LOG_DIR"

echo "=========================================="
echo "Sincronizzazione COMPLETA YellowOracle"
echo "Competizione: $COMPETITION"
echo "Tutte le stagioni (2023-2026)"
echo "Questo richiederà circa 30-45 minuti"
echo "=========================================="
echo ""
echo "Log: $LOG_FILE"
echo ""

cd "$PROJECT_DIR" || exit 1

$VENV_PYTHON "$SYNC_SCRIPT" --competition "$COMPETITION" --all-seasons --full 2>&1 | tee "$LOG_FILE"

echo ""
echo "Sincronizzazione completata!"
echo "Log salvato in: $LOG_FILE"
