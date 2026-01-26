# YellowOracle - Supporto UEFA Champions League & Europa League

**Data:** 2026-01-26
**Stato:** Implementato

---

## Obiettivo

Aggiungere supporto per analisi cartellini in UEFA Champions League e Europa League, con dati differenziati per competizione.

---

## Decisioni di Design

| Decisione | Scelta | Motivazione |
|-----------|--------|-------------|
| Approccio analisi | Combinata | Usa dati CL + campionato nazionale |
| Gestione squadre | Automatica | Upsert su external_id, nessun duplicato |
| Differenziazione cartellini | Separata per competizione | Giocatore si comporta diversamente in CL |
| Competizioni | CL + EL | Conference League esclusa per ora |

---

## Modifiche Implementate

### 1. Sync Script (sync_football_data.py)

Aggiunte competizioni al dizionario:
```python
COMPETITIONS = {
    # Campionati nazionali (esistenti)
    'PD', 'SA', 'BL1', 'PL', 'FL1',
    # Competizioni UEFA (nuove)
    'CL': {'name': 'UEFA Champions League', 'area': 'Europe', 'area_code': 'UEFA'},
    'EL': {'name': 'UEFA Europa League', 'area': 'Europe', 'area_code': 'UEFA'},
}
```

### 2. Viste SQL (analysis_views.sql)

**Vista modificata:** `player_season_cards`
- Aggiunto: `competition_id`, `competition_code`, `competition_name`
- Raggruppamento per competizione

**Nuova vista:** `player_season_cards_total`
- Aggregato tutte le competizioni
- Campo `competitions` con lista codici (es: "SA, CL")

### 3. Funzioni SQL

**Modificata:** `get_player_season_stats(player_name, season, competition)`
- Nuovo parametro `p_competition` (opzionale)
- Restituisce dati separati per competizione

**Nuova:** `get_player_season_stats_total(player_name, season)`
- Restituisce totale aggregato
- Include lista competizioni

### 4. MCP Server (mcp_server.py)

**Modificato:** `get_player_season_stats`
- Nuovo parametro `competition` (PD/SA/CL/EL/...)

**Nuovo tool:** `get_player_season_stats_total`
- Statistiche aggregate tutte le competizioni

---

## Esempio di Utilizzo

```
Utente: "Analizza Barella per Inter-Bayern in CL"

Claude:
1. get_player_season_stats("Barella", "2025-2026", "SA")
   → 5 gialli in Serie A, 0.32/90min

2. get_player_season_stats("Barella", "2025-2026", "CL")
   → 2 gialli in Champions, 0.45/90min

3. get_player_season_stats_total("Barella", "2025-2026")
   → 7 gialli totali, competizioni: SA, CL

Analisi: "Barella tende a prendere più cartellini in CL (0.45/90)
rispetto alla Serie A (0.32/90). Rischio cartellino ALTO."
```

---

## Comandi Sync

```bash
# Solo Champions League stagione corrente
./venv/bin/python scripts/sync_football_data.py --competition CL --season 2025-2026 --full

# CL + EL
./venv/bin/python scripts/sync_football_data.py --competitions CL,EL --season 2025-2026 --full

# Tutto (campionati + UEFA)
./venv/bin/python scripts/sync_football_data.py --all-competitions --season 2025-2026 --full
```

---

## MCP Tools Disponibili (9 totali)

| Tool | Descrizione |
|------|-------------|
| `get_player_season_stats` | Statistiche per competizione |
| `get_player_season_stats_total` | Statistiche aggregate |
| `get_referee_player_cards` | Storico arbitro-giocatore |
| `get_head_to_head_cards` | Scontri diretti |
| `get_teams` | Lista squadre |
| `get_referees` | Lista arbitri |
| `get_team_players` | Giocatori squadra |
| `get_match_statistics` | Falli, possesso, tiri |
| `analyze_match_risk` | Analisi rischio partita |

---

*Documento generato il 2026-01-26*
