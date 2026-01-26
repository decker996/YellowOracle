# YellowOracle Alpha Interface Design

**Data:** 2026-01-26
**Stato:** Approvato
**Fase:** Alpha (Claude Code come interfaccia principale)

---

## 1. Panoramica

YellowOracle Alpha usa Claude Code come interfaccia conversazionale per l'analisi dei cartellini. L'utente interagisce in linguaggio naturale, Claude chiama i tool MCP e restituisce analisi formattate.

```
┌─────────────────────────────────────────────────────────┐
│                    UTENTE                               │
│    "Analizza Napoli vs Inter di domenica"               │
│    "Partite Serie A di oggi 26.01.2026"                 │
│    "Barella rischia il giallo?"                         │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              CLAUDE CODE + System Prompt                │
│  - Riconosce il tipo di richiesta                       │
│  - Chiama i tool MCP appropriati                        │
│  - Formatta output: tabella + analisi discorsiva        │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              MCP SERVER (10 tool)                       │
│  - get_matches_by_date                                  │
│  - analyze_match_risk                                   │
│  - get_player_season_stats, ecc.                        │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              SUPABASE (Database)                        │
│  Dati sincronizzati da football-data.org                │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Tipi di Richiesta Supportati

### Tipo A: Partita Singola

**Esempio:** "Analizza Roma vs Milan di domenica"

**Flusso:**
1. Chiama `get_matches_by_date` per trovare la partita e l'arbitro
2. Chiama `analyze_match_risk(home, away, referee)`
3. Output: tabella top 3 per squadra + analisi discorsiva

### Tipo B: Giornata Intera

**Esempio:** "Analizzami le partite di Serie A di oggi 26.01.2026"

**Flusso:**
1. Chiama `get_matches_by_date(competition="SA", date="2026-01-26")`
2. Per ogni partita, chiama `analyze_match_risk`
3. Output: riepilogo con top candidati per ogni partita

### Tipo C: Giocatore Specifico

**Esempio:** "Barella rischia il giallo contro il Napoli?"

**Flusso:**
1. Chiama `get_player_season_stats("Barella")`
2. Chiama `get_head_to_head_cards("Barella", "Inter", "Napoli")`
3. Se arbitro noto, chiama `get_referee_player_cards`
4. Output: analisi focalizzata sul giocatore

---

## 3. Formato Output Standard

```markdown
## 🟨 Analisi: [Squadra A] vs [Squadra B]
**Data:** DD/MM/YYYY | **Arbitro:** Nome | **Competizione:** Serie A

### Top 3 Rischio Cartellino

| # | Giocatore | Squadra | Score | Stagione | Arbitro | H2H |
|---|-----------|---------|-------|----------|---------|-----|
| 1 | Nome      | Team    | 72.5  | 45.0     | 67.0    | 25.0|
| 2 | ...       | ...     | ...   | ...      | ...     | ... |
| 3 | ...       | ...     | ...   | ...      | ...     | ... |

### Analisi

[Paragrafo discorsivo che spiega il ragionamento,
il contesto della partita, e le motivazioni per i top 3]
```

**Caratteristiche output:**
- Tabella con dati numerici (score breakdown)
- Analisi discorsiva e ragionata
- Nessun consiglio su quote (l'utente le valuta autonomamente)

---

## 4. Script Sync

### 4.1 Sync Incrementale (nuovo)

Nuovo parametro `--days` per `sync_football_data.py`:

```bash
# Sync incrementale (ultime 7 giornate)
./venv/bin/python scripts/sync_football_data.py --competition SA --days 7

# Sync completo stagione (come ora)
./venv/bin/python scripts/sync_football_data.py --competition SA --season 2025-2026 --full
```

**Logica:**
- `--days N` chiede all'API solo partite degli ultimi N giorni
- Usa parametri `dateFrom` e `dateTo` nell'endpoint `/matches`
- Risparmia chiamate API

### 4.2 Multi-Competizione

**weekly_sync.sh** aggiornato:

```bash
COMPETITIONS="SA PL PD BL1 FL1 CL EL"

for COMP in $COMPETITIONS; do
    log "Sync $COMP..."
    $VENV_PYTHON "$SYNC_SCRIPT" --competition "$COMP" --days 7
done
```

**Parametro opzionale** per selezionare competizioni:
```bash
./scripts/weekly_sync.sh              # tutte e 7
./scripts/weekly_sync.sh "SA PL"      # solo Serie A e Premier
```

### 4.3 Cron (opzionale)

```bash
# Ogni lunedì alle 6:00
0 6 * * 1 /home/salvatore/Scrivania/soccer/scripts/weekly_sync.sh
```

---

## 5. Competizioni Supportate

| Codice | Competizione | Paese |
|--------|--------------|-------|
| SA | Serie A | Italia |
| PL | Premier League | Inghilterra |
| PD | La Liga | Spagna |
| BL1 | Bundesliga | Germania |
| FL1 | Ligue 1 | Francia |
| CL | UEFA Champions League | Europa |
| EL | UEFA Europa League | Europa |

---

## 6. File da Creare/Modificare

| File | Azione | Descrizione |
|------|--------|-------------|
| `CLAUDE.md` | Creare | System prompt per analisi YellowOracle |
| `scripts/sync_football_data.py` | Modificare | Aggiungere `--days N` |
| `scripts/weekly_sync.sh` | Modificare | Loop multi-competizione |
| `scripts/full_sync.sh` | Modificare | Loop multi-competizione |

---

## 7. Criteri di Successo

- [ ] "Analizza Napoli vs Inter" restituisce tabella + analisi
- [ ] "Partite Serie A di domani" restituisce riepilogo multi-partita
- [ ] "Barella rischia il giallo?" restituisce analisi focalizzata
- [ ] `--days 7` funziona per sync incrementale
- [ ] `weekly_sync.sh` sincronizza tutte le 7 competizioni

---

## 8. Fase Futura: Dashboard Web

Dopo la fase Alpha, verrà implementata una dashboard Streamlit con:
- Form per selezione partita/giornata
- Visualizzazione grafica dei risultati
- Storico analisi

*Questo documento sarà aggiornato quando si passerà alla fase Beta.*

---

*Design document creato durante sessione di brainstorming del 2026-01-26*
