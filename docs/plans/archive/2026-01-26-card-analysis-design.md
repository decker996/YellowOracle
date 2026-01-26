# YellowOracle - Design Analisi Cartellini

**Data:** 2026-01-26
**Stato:** Implementato
**Ultimo aggiornamento:** 2026-01-26 15:30

---

## Obiettivo

Implementare 3 tipologie di analisi per supportare il ragionamento di Claude:

1. **Analisi stagionale giocatore** - Cartellini per giocatore nella stagione
2. **Storico arbitro-giocatore** - Quante volte un arbitro ha ammonito un giocatore (nelle partite delle squadre coinvolte)
3. **Scontri diretti** - Storico cartellini di un giocatore negli scontri diretti tra due squadre

---

## Decisioni di Design

| Decisione | Scelta | Stato |
|-----------|--------|-------|
| Storico stagioni | 3 stagioni (limite piano API) | ✅ |
| Arbitro-giocatore | Solo partite delle squadre coinvolte | ✅ |
| Filtri minimi | Nessuno (mostra tutti i dati) | ✅ |
| Output | Viste SQL + Funzioni + Dashboard Streamlit | ✅ |
| Arbitro sconosciuto | Claude cerca via web, chiede conferma | ✅ |
| Multi-competizione | 5 campionati (PD, SA, BL1, PL, FL1) | ✅ |
| Statistics Add-On | Falli, possesso, tiri per squadra | ✅ |
| VAR Referee | Tracciato separatamente | ✅ |

---

## Viste SQL

### 1. `player_season_cards`
Statistiche cartellini per giocatore e stagione.

```sql
-- Output: giocatore, squadra, stagione, gialli, rossi, partite, minuti, media_per_90
```

### 2. `referee_player_history`
Storico ammonizioni arbitro verso giocatori delle squadre specificate.

```sql
-- Input: referee_id, team1_id, team2_id
-- Output: arbitro, giocatore, squadra, ammonizioni_totali, partite_arbitrate
```

### 3. `head_to_head_player_cards`
Cartellini di un giocatore negli scontri diretti.

```sql
-- Input: player_id, team1_id, team2_id
-- Output: giocatore, partite_giocate, gialli, rossi, dettaglio_partite
```

### 4. `match_analysis_summary`
Vista aggregata per analisi completa di una partita.

---

## Funzioni SQL

### `get_player_season_stats(player_name TEXT, season TEXT)`
Restituisce statistiche cartellini. Se season è NULL, tutte le stagioni.

### `get_referee_player_cards(referee_name TEXT, team1_name TEXT, team2_name TEXT)`
Storico ammonizioni dell'arbitro verso giocatori delle due squadre.

### `get_head_to_head_cards(player_name TEXT, team1_name TEXT, team2_name TEXT)`
Cartellini del giocatore negli scontri diretti tra le due squadre.

---

## Flusso Claude

```
Utente: "Analizza Roma-Milan di domenica"

Claude:
1. [WebSearch: "Roma Milan arbitro designato"]
2. "Ho trovato arbitro X. Confermi?"
3. [Query: get_player_season_stats per ogni giocatore]
4. [Query: get_referee_player_cards]
5. [Query: get_head_to_head_cards per giocatori chiave]
6. [Ragionamento combinato]
7. [Output: Top giocatori a rischio + spiegazione]
```

Se arbitro non trovato: analisi con soli 2 fattori + avviso.

---

## Dashboard Streamlit

### Pagina 1: Statistiche Giocatori
- Filtri: squadra, stagione, ruolo
- Tabella ordinabile per cartellini/90 min

### Pagina 2: Statistiche Arbitri
- Lista arbitri con media cartellini/partita
- Dettaglio giocatori più ammoniti

### Pagina 3: Analisi Partita
- Input: squadra casa, squadra trasferta, arbitro (opzionale)
- Output: tutti i giocatori con i 3 indici di rischio

---

## File Creati/Modificati

| File | Stato |
|------|-------|
| `database/schema_v2.sql` | ✅ Aggiornato (competitions, var_referee_id, competition_id) |
| `database/analysis_views.sql` | ✅ Creato + fix cast |
| `scripts/sync_football_data.py` | ✅ Multi-competizione + Statistics |
| `dashboard/app.py` | ✅ Creato |
| `dashboard/pages/1_players.py` | ✅ Creato |
| `dashboard/pages/2_referees.py` | ✅ Creato |
| `dashboard/pages/3_match_analysis.py` | ✅ Creato |
| `mcp_server.py` | ✅ Creato (7 tool) |
| `STATO_PROGETTO.md` | ✅ Aggiornato |

---

## Schema Database Aggiornato

### Nuova tabella: `competitions`
```sql
- id, external_id, code (PD/SA/BL1/PL/FL1)
- name, area_name, area_code, emblem_url, plan
```

### Modifiche a `matches`
```sql
- competition_id UUID REFERENCES competitions(id)  -- NUOVO
- var_referee_id UUID REFERENCES referees(id)      -- NUOVO
```

### Tabella `match_statistics` (Statistics Add-On)
```sql
- ball_possession, fouls_committed, fouls_suffered
- shots_on_goal, shots_off_goal, total_shots
- corner_kicks, free_kicks, saves, offsides
- yellow_cards, red_cards (per squadra)
```

---

## Competizioni Supportate

### Campionati Nazionali
| Codice | Campionato | Paese |
|--------|------------|-------|
| PD | La Liga | Spagna |
| SA | Serie A | Italia |
| BL1 | Bundesliga | Germania |
| PL | Premier League | Inghilterra |
| FL1 | Ligue 1 | Francia |

### Competizioni UEFA
| Codice | Competizione | Note |
|--------|--------------|------|
| CL | UEFA Champions League | Analisi separata da campionati |
| EL | UEFA Europa League | Analisi separata da campionati |

---

## Comandi Sync

```bash
# Singola competizione
python sync_football_data.py --competition PD --season 2025-2026 --full

# Multiple competizioni
python sync_football_data.py --competitions PD,SA --all-seasons --full

# Tutte le competizioni
python sync_football_data.py --all-competitions --all-seasons --full
```

---

*Documento generato durante sessione di brainstorming del 2026-01-26*
*Aggiornato il 2026-01-26 con modifiche multi-competizione*
