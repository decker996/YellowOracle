# YellowOracle Alpha Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement Claude Code interface with system prompt, and update sync scripts for multi-competition + incremental sync.

**Architecture:** CLAUDE.md provides instructions to Claude for analyzing matches. Sync scripts loop through all 7 competitions with optional `--days` parameter for incremental updates.

**Tech Stack:** Bash scripts, Python 3.13, Claude Code, MCP tools

---

## Task 1: Create CLAUDE.md System Prompt

**Files:**
- Create: `CLAUDE.md`

**Step 1: Create the system prompt file**

```markdown
# YellowOracle - Sistema di Analisi Cartellini

Sei un assistente specializzato nell'analisi del rischio cartellini gialli per partite di calcio.
Hai accesso a tool MCP che interrogano un database con dati storici.

## Tool Disponibili

| Tool | Uso |
|------|-----|
| `get_matches_by_date` | Trova partite per data e competizione |
| `analyze_match_risk` | Analisi completa con score pesato |
| `get_player_season_stats` | Statistiche giocatore per competizione |
| `get_player_season_stats_total` | Statistiche aggregate tutte competizioni |
| `get_referee_player_cards` | Storico arbitro-giocatore |
| `get_head_to_head_cards` | Cartellini negli scontri diretti |
| `get_teams` | Lista squadre nel database |
| `get_referees` | Lista arbitri con statistiche |
| `get_team_players` | Giocatori di una squadra |
| `get_match_statistics` | Falli, possesso, tiri per squadra |

## Competizioni Supportate

| Codice | Competizione |
|--------|--------------|
| SA | Serie A |
| PL | Premier League |
| PD | La Liga |
| BL1 | Bundesliga |
| FL1 | Ligue 1 |
| CL | UEFA Champions League |
| EL | UEFA Europa League |

## Come Rispondere alle Richieste

### Tipo A: Partita Singola
**Esempio:** "Analizza Roma vs Milan di domenica"

1. Usa `get_matches_by_date` per trovare data e arbitro
2. Usa `analyze_match_risk(home_team, away_team, referee)`
3. Presenta output nel formato standard

### Tipo B: Giornata Intera
**Esempio:** "Analizzami le partite di Serie A di oggi 26.01.2026"

1. Usa `get_matches_by_date(competition="SA", date="2026-01-26")`
2. Per ogni partita, usa `analyze_match_risk`
3. Presenta riepilogo con top candidati per partita

### Tipo C: Giocatore Specifico
**Esempio:** "Barella rischia il giallo contro il Napoli?"

1. Usa `get_player_season_stats("Barella")`
2. Usa `get_head_to_head_cards("Barella", "Inter", "Napoli")`
3. Se conosci l'arbitro, usa `get_referee_player_cards`
4. Presenta analisi focalizzata

## Formato Output Standard

Per ogni analisi, usa questo formato:

```
## 🟨 Analisi: [Squadra Casa] vs [Squadra Trasferta]
**Data:** DD/MM/YYYY | **Arbitro:** Nome (o "Non designato") | **Competizione:** Nome

### Top 3 Rischio Cartellino

| # | Giocatore | Squadra | Score | Stagione | Arbitro | H2H |
|---|-----------|---------|-------|----------|---------|-----|
| 1 | Nome      | Team    | 72.5  | 45.0     | 67.0    | 25.0|
| 2 | Nome      | Team    | 65.3  | 40.0     | 55.0    | 20.0|
| 3 | Nome      | Team    | 58.1  | 38.0     | 45.0    | 15.0|

### Analisi

[Spiega il ragionamento per i top 3:
- Perché il primo è il più a rischio
- Fattori chiave (storico stagionale, rapporto con arbitro, precedenti H2H)
- Contesto della partita se rilevante]
```

## Pesi dello Score

Lo score combinato usa questi pesi:
- **40% Stagionale**: cartellini per 90 minuti nella stagione
- **35% Arbitro**: storico ammonizioni con quell'arbitro
- **25% H2H**: cartellini negli scontri diretti

Se l'arbitro non è designato, i pesi diventano:
- **62% Stagionale**
- **38% H2H**

## Regole Importanti

1. **Non inventare dati** - usa solo ciò che restituiscono i tool
2. **Nessun consiglio quote** - l'utente valuta autonomamente
3. **Sii conciso** - tabella + analisi breve ma ragionata
4. **Ammetti incertezza** - se i dati sono scarsi, dillo
```

**Step 2: Verify file was created**

Run: `head -20 CLAUDE.md`
Expected: First 20 lines of the system prompt

**Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "feat: add CLAUDE.md system prompt for YellowOracle analysis

- Instructions for 3 request types (single match, matchday, player)
- Standard output format with table + discursive analysis
- Tool documentation and competition codes
- Score weighting explanation (40/35/25)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Update weekly_sync.sh for Multi-Competition

**Files:**
- Modify: `scripts/weekly_sync.sh`

**Step 1: Update the script to loop through all competitions**

Replace entire file with:

```bash
#!/bin/bash
# YellowOracle - Script di sincronizzazione settimanale
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

    $VENV_PYTHON "$SYNC_SCRIPT" --competition "$COMP" --season 2025-2026 --full 2>&1 | tee -a "$LOG_FILE"

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
```

**Step 2: Make executable and verify**

Run: `chmod +x scripts/weekly_sync.sh && head -30 scripts/weekly_sync.sh`
Expected: Script header with ALL_COMPETITIONS variable

**Step 3: Commit**

```bash
git add scripts/weekly_sync.sh
git commit -m "feat: update weekly_sync.sh for multi-competition support

- Loops through all 7 competitions by default
- Optional parameter to select specific competitions
- Adds success/failure counters and summary
- Maintains backward compatibility (single comp still works)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Update full_sync.sh for Multi-Competition

**Files:**
- Modify: `scripts/full_sync.sh`

**Step 1: Update the script to loop through all competitions**

Replace entire file with:

```bash
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

cd "$PROJECT_DIR" || exit 1

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
```

**Step 2: Make executable and verify**

Run: `chmod +x scripts/full_sync.sh && head -30 scripts/full_sync.sh`
Expected: Script header with ALL_COMPETITIONS variable

**Step 3: Commit**

```bash
git add scripts/full_sync.sh
git commit -m "feat: update full_sync.sh for multi-competition support

- Loops through all 7 competitions by default
- Optional parameter to select specific competitions
- Adds logging and success/failure counters
- Warns about long execution time

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Add Incremental Sync (--days parameter)

**Prerequisites:** Wait for current sync to finish before modifying this file.

**Files:**
- Modify: `scripts/sync_football_data.py:60-67` (add --days argument)
- Modify: `scripts/sync_football_data.py:280-350` (modify sync_matches function)

**Step 1: Add --days argument to argparse**

After line 67 (after ALL_SEASONS definition), find the argparse section and add:

```python
parser.add_argument(
    "--days",
    type=int,
    help="Sync only matches from last N days (incremental sync)"
)
```

**Step 2: Modify sync_matches function to support date range**

In `sync_matches` function, add date filtering logic:

```python
def sync_matches(supabase: Client, competition_code: str, competition_id: str,
                 season: str, team_map: dict, full: bool = False, days: int = None) -> list:
    """Sincronizza le partite della competizione."""
    print(f"\n📅 Sincronizzazione partite {season}...")

    api_season = season.split("-")[0]

    # Build API URL with optional date range
    url = f"/competitions/{competition_code}/matches?season={api_season}"

    if days:
        from datetime import datetime, timedelta
        date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        date_to = datetime.now().strftime("%Y-%m-%d")
        url += f"&dateFrom={date_from}&dateTo={date_to}"
        print(f"  📆 Filtro date: {date_from} -> {date_to}")

    data = api_request(url)
    # ... rest of function
```

**Step 3: Update main() to pass days parameter**

In the main sync loop, pass the `days` argument:

```python
matches_data = sync_matches(
    supabase, competition_code, competition_id,
    season, team_map, args.full, args.days
)
```

**Step 4: Test incremental sync**

Run: `./venv/bin/python scripts/sync_football_data.py --competition SA --days 7 --help`
Expected: Help shows --days parameter

**Step 5: Commit**

```bash
git add scripts/sync_football_data.py
git commit -m "feat: add --days parameter for incremental sync

- New --days N parameter syncs only matches from last N days
- Reduces API calls for regular updates
- Works with all existing parameters

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Update weekly_sync.sh to use --days

**Files:**
- Modify: `scripts/weekly_sync.sh:47`

**Step 1: Change sync command to use --days 7**

Replace the sync command line:

```bash
# Old:
$VENV_PYTHON "$SYNC_SCRIPT" --competition "$COMP" --season 2025-2026 --full 2>&1 | tee -a "$LOG_FILE"

# New:
$VENV_PYTHON "$SYNC_SCRIPT" --competition "$COMP" --days 7 --full 2>&1 | tee -a "$LOG_FILE"
```

**Step 2: Update header comment**

Update the script description to mention incremental sync.

**Step 3: Commit**

```bash
git add scripts/weekly_sync.sh
git commit -m "feat: use --days 7 for incremental weekly sync

- Uses new incremental sync (last 7 days)
- Faster execution, fewer API calls

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Update STATO_PROGETTO.md

**Files:**
- Modify: `STATO_PROGETTO.md`

**Step 1: Update status and commands**

Update the document to reflect:
- CLAUDE.md created
- Scripts updated for multi-competition
- Incremental sync available

**Step 2: Commit**

```bash
git add STATO_PROGETTO.md
git commit -m "docs: update project status with Alpha implementation

- CLAUDE.md system prompt created
- Multi-competition sync scripts
- Incremental sync with --days parameter

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Summary

| Task | Description | Depends On |
|------|-------------|------------|
| 1 | Create CLAUDE.md | - |
| 2 | Update weekly_sync.sh (multi-comp) | - |
| 3 | Update full_sync.sh (multi-comp) | - |
| 4 | Add --days to sync_football_data.py | Sync finished |
| 5 | Update weekly_sync.sh (use --days) | Task 4 |
| 6 | Update STATO_PROGETTO.md | All tasks |

**Tasks 1-3 can run now.** Task 4+ requires sync to finish.

---

*Implementation plan created 2026-01-26*
