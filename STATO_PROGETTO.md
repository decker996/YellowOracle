# YellowOracle - Stato del Progetto

**Ultimo aggiornamento:** 2026-01-26 15:30
**Fase attuale:** Modifiche strutturali completate, pronto per sync

---

## Stato Database (verificato)

| Tabella | Record | Note |
|---------|--------|------|
| `competitions` | 0 | Nuova tabella, da popolare con sync |
| `teams` | 24 | La Liga |
| `players` | 688 | |
| `referees` | 76 | |
| `matches` | 542 | Parziale, senza competition_id |
| `match_events` | 271 | Parziale, serve --full |
| `match_statistics` | 0 | Mai sincronizzate |
| `lineups` | 1000 | |

---

## Modifiche Completate Oggi (26/01/2026)

### Sessione 1 (mattina)
1. **Design analisi cartellini** - `docs/plans/2026-01-26-card-analysis-design.md`
2. **Viste e funzioni SQL** - `database/analysis_views.sql`
3. **Dashboard Streamlit** - 4 pagine
4. **Server MCP** - 7 tool
5. **Script sync base** - La Liga

### Sessione 2 (pomeriggio)
1. **Fix funzione SQL** - `get_player_season_stats` (cast ::TEXT e ::NUMERIC)
2. **Statistics Add-On** - Aggiunto sync per tutte le statistiche partita
3. **VAR Referee** - Aggiunta colonna `var_referee_id` a matches
4. **Multi-competizione** - Supporto per 5 campionati:
   - PD (La Liga)
   - SA (Serie A)
   - BL1 (Bundesliga)
   - PL (Premier League)
   - FL1 (Ligue 1)
5. **Tabella competitions** - Nuova tabella per gestire campionati

---

## Struttura Database Attuale

```
competitions (NUOVA)
     │
     ▼
matches ──► teams ──► players
  │  │
  │  └──► referees (referee_id, var_referee_id)
  │
  ├──► match_events (cartellini, gol)
  ├──► match_statistics (falli, possesso, tiri - Statistics Add-On)
  └──► lineups (formazioni)
```

---

## File del Progetto

```
soccer/
├── .env                          # Credenziali (Supabase + Football API)
├── .mcp.json                     # Configurazione MCP
├── STATO_PROGETTO.md             # Questo file
├── mcp_server.py                 # Server MCP (7 tool)
│
├── database/
│   ├── schema_v2.sql             # Schema completo (AGGIORNATO)
│   └── analysis_views.sql        # Viste e funzioni (FIX applicati)
│
├── scripts/
│   ├── sync_football_data.py     # Sync multi-competizione (AGGIORNATO)
│   ├── weekly_sync.sh            # Cron settimanale
│   └── full_sync.sh              # Sync completo (DA AGGIORNARE)
│
├── dashboard/
│   ├── app.py                    # Homepage
│   └── pages/
│       ├── 1_players.py          # Statistiche giocatori
│       ├── 2_referees.py         # Statistiche arbitri
│       └── 3_match_analysis.py   # Analisi partita
│
└── docs/
    ├── CRON_SETUP.md             # Istruzioni cron
    └── plans/
        ├── 2026-01-26-yelloworacle-design.md
        └── 2026-01-26-card-analysis-design.md
```

---

## Prossimi Passi

### PRIORITA' 1: Sincronizzazione Dati

Eseguire sync completa per popolare il database:

```bash
# Sync La Liga con tutti i dettagli
./venv/bin/python scripts/sync_football_data.py \
    --competition PD \
    --all-seasons \
    --full
```

Questo popolerà:
- Tabella `competitions`
- Colonna `matches.competition_id`
- Tabella `match_statistics` (falli, possesso, etc.)
- Eventi mancanti in `match_events`

**Tempo stimato:** ~30-60 minuti (rate limit API)

### PRIORITA' 2: Test Sistema

Dopo la sync:
1. Verificare dati in database
2. Testare funzioni MCP
3. Testare dashboard Streamlit

### PRIORITA' 3: Aggiornamenti Script

- [ ] Aggiornare `full_sync.sh` per multi-competizione
- [ ] Aggiornare `weekly_sync.sh` per multi-competizione
- [ ] Aggiornare MCP server per filtrare per competizione

### OPZIONALE: Espansione

- [ ] Aggiungere altri campionati (Serie A, etc.)
- [ ] Creare CLAUDE.md con istruzioni analisi
- [ ] Configurare cron job automatico

---

## Comandi Utili

```bash
# Sync singola competizione
./venv/bin/python scripts/sync_football_data.py --competition PD --season 2025-2026 --full

# Sync multiple competizioni
./venv/bin/python scripts/sync_football_data.py --competitions PD,SA --all-seasons --full

# Avvia dashboard
./venv/bin/streamlit run dashboard/app.py

# Verifica stato database
./venv/bin/python -c "
from supabase import create_client
import os
from dotenv import load_dotenv
load_dotenv()
sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
for t in ['competitions','teams','players','referees','matches','match_events','match_statistics']:
    print(f'{t}: {len(sb.table(t).select(\"id\").execute().data)}')"
```

---

## Come Riprendere

Quando riapri Claude Code:

> "Leggi STATO_PROGETTO.md"

Per sincronizzare i dati:

> "Avvia la sincronizzazione completa per La Liga"

---

## Piano API football-data.org

| Componente | Piano | Costo |
|------------|-------|-------|
| Deep Data | Free + Deep Data | €29/mese |
| Statistics Add-On | Statistics | €15/mese |
| **Totale** | | **€44/mese** |

Competizioni incluse: 12 (tutti i top 5 europei)
Rate limit: 30 call/min
Stagioni: ultime 3 (2023-2024, 2024-2025, 2025-2026)
