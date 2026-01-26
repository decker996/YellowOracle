# YellowOracle - Stato del Progetto

**Ultimo aggiornamento:** 2026-01-26 18:00
**Fase attuale:** Implementazione completata, pronto per sincronizzazione dati

---

## Cosa è YellowOracle

Sistema di analisi cartellini per scommesse calcistiche. Analizza:
1. **Storico stagionale giocatore** - Cartellini per competizione (Serie A, CL, EL...)
2. **Storico arbitro-giocatore** - Come un arbitro si comporta con specifici giocatori
3. **Scontri diretti** - Cartellini storici negli head-to-head tra due squadre
4. **Statistiche partita** - Falli, possesso, tiri (aggregato per squadra)

---

## Stato Database

| Tabella | Record | Note |
|---------|--------|------|
| `competitions` | 0 | Da popolare con sync |
| `teams` | 24 | Solo La Liga (vecchia sync) |
| `players` | 688 | Solo La Liga |
| `referees` | 76 | Solo La Liga |
| `matches` | 542 | Parziale, senza competition_id |
| `match_events` | 271 | Parziale, serve --full |
| `match_statistics` | 0 | Mai sincronizzate |
| `lineups` | 1000 | Solo La Liga |

**AZIONE RICHIESTA:** Eseguire sincronizzazione completa (vedi sezione Prossimi Passi)

---

## Competizioni Supportate (7)

### Campionati Nazionali
| Codice | Campionato | Paese |
|--------|------------|-------|
| PD | La Liga | Spagna |
| SA | Serie A | Italia |
| BL1 | Bundesliga | Germania |
| PL | Premier League | Inghilterra |
| FL1 | Ligue 1 | Francia |

### Competizioni UEFA
| Codice | Competizione |
|--------|--------------|
| CL | UEFA Champions League |
| EL | UEFA Europa League |

---

## MCP Server - 9 Tool Disponibili

| Tool | Descrizione | Parametri |
|------|-------------|-----------|
| `get_player_season_stats` | Cartellini per competizione | player_name, season?, competition? |
| `get_player_season_stats_total` | Cartellini totali (tutte competizioni) | player_name, season? |
| `get_referee_player_cards` | Storico arbitro-giocatore | referee_name, team1, team2 |
| `get_head_to_head_cards` | Scontri diretti | player_name, team1, team2 |
| `get_teams` | Lista squadre | - |
| `get_referees` | Lista arbitri con statistiche | - |
| `get_team_players` | Giocatori di una squadra | team_name, season? |
| `get_match_statistics` | Falli, possesso, tiri | team_name?, season?, limit? |
| `analyze_match_risk` | Analisi rischio partita | home_team, away_team, referee? |

---

## File del Progetto

```
soccer/
├── .env                              # Credenziali (Supabase + Football API)
├── .mcp.json                         # Configurazione MCP per Claude
├── STATO_PROGETTO.md                 # QUESTO FILE - leggilo sempre all'inizio
├── mcp_server.py                     # Server MCP (9 tool)
│
├── database/
│   ├── schema_v2.sql                 # Schema database completo
│   └── analysis_views.sql            # Viste e funzioni SQL per analisi
│
├── scripts/
│   ├── sync_football_data.py         # Script sincronizzazione principale
│   ├── weekly_sync.sh                # Script per cron settimanale
│   └── full_sync.sh                  # Script sync completa
│
├── dashboard/
│   ├── app.py                        # Homepage Streamlit
│   └── pages/
│       ├── 1_players.py              # Statistiche giocatori
│       ├── 2_referees.py             # Statistiche arbitri
│       └── 3_match_analysis.py       # Analisi partita
│
└── docs/
    ├── CRON_SETUP.md                 # Istruzioni cron job
    └── plans/
        ├── 2026-01-26-yelloworacle-design.md
        ├── 2026-01-26-card-analysis-design.md
        └── 2026-01-26-uefa-competitions-design.md
```

---

## Prossimi Passi

### PRIORITA' 1: Sincronizzazione Dati

Il database ha dati parziali. Eseguire sync completa:

```bash
# OPZIONE A: Una competizione alla volta (consigliato per test)
./venv/bin/python scripts/sync_football_data.py --competition SA --season 2025-2026 --full

# OPZIONE B: Tutte le competizioni, stagione corrente
./venv/bin/python scripts/sync_football_data.py --all-competitions --season 2025-2026 --full

# OPZIONE C: Tutto (tutte le competizioni, tutte le stagioni)
./venv/bin/python scripts/sync_football_data.py --all-competitions --all-seasons --full
```

**Nota:** Rate limit API = 30 call/min. La sync completa richiede tempo.

### PRIORITA' 2: Test Sistema

Dopo la sync:
1. Verificare dati: `./venv/bin/python -c "..."` (vedi Comandi Utili)
2. Testare MCP tool tramite Claude
3. Avviare dashboard: `./venv/bin/streamlit run dashboard/app.py`

### PRIORITA' 3: Script Cron (opzionale)

- [ ] Aggiornare `full_sync.sh` per multi-competizione
- [ ] Aggiornare `weekly_sync.sh` per multi-competizione
- [ ] Configurare cron job automatico

---

## Comandi Utili

```bash
# === SINCRONIZZAZIONE ===

# Singola competizione + stagione
./venv/bin/python scripts/sync_football_data.py --competition SA --season 2025-2026 --full

# Champions League
./venv/bin/python scripts/sync_football_data.py --competition CL --season 2025-2026 --full

# Multiple competizioni
./venv/bin/python scripts/sync_football_data.py --competitions SA,CL,EL --season 2025-2026 --full

# Tutte le competizioni, tutte le stagioni
./venv/bin/python scripts/sync_football_data.py --all-competitions --all-seasons --full


# === VERIFICA DATABASE ===

./venv/bin/python -c "
from supabase import create_client
import os
from dotenv import load_dotenv
load_dotenv()
sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
for t in ['competitions','teams','players','referees','matches','match_events','match_statistics','lineups']:
    print(f'{t}: {len(sb.table(t).select(\"id\").execute().data)}')"


# === DASHBOARD ===

./venv/bin/streamlit run dashboard/app.py


# === TEST MCP SERVER ===

./venv/bin/python -c "
from mcp_server import get_teams
print(get_teams())"
```

---

## Come Riprendere una Sessione

Quando apri una nuova chat Claude Code:

```
Leggi STATO_PROGETTO.md
```

Per continuare con la sincronizzazione:

```
Avvia la sincronizzazione per Serie A stagione 2025-2026
```

---

## Architettura

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
│ football-data   │────▶│ sync_football_   │────▶│  Supabase   │
│ .org API        │     │ data.py          │     │  Database   │
└─────────────────┘     └──────────────────┘     └─────────────┘
                                                        │
                        ┌───────────────────────────────┤
                        │                               │
                        ▼                               ▼
                ┌──────────────┐               ┌──────────────┐
                │  MCP Server  │               │  Streamlit   │
                │  (Claude)    │               │  Dashboard   │
                └──────────────┘               └──────────────┘
```

---

## Piano API football-data.org

| Componente | Piano | Costo |
|------------|-------|-------|
| Deep Data | Free + Deep Data | €29/mese |
| Statistics Add-On | Statistics | €15/mese |
| **Totale** | | **€44/mese** |

- Competizioni incluse: 12 (top 5 europei + coppe UEFA)
- Rate limit: 30 call/min (delay 2.5s tra chiamate)
- Stagioni disponibili: ultime 3 (2023-2024, 2024-2025, 2025-2026)

---

## Limitazioni Note

1. **Falli**: Disponibili solo come aggregato per squadra, NON per singolo giocatore
2. **VAR**: Tracciato come `var_referee_id` ma raramente popolato dall'API
3. **Minuti giocati**: Stimati se non disponibili (partite * 90)

---

## Cronologia Sessioni

### 2026-01-26
- **Mattina**: Design iniziale, viste SQL, dashboard Streamlit, MCP server (7 tool)
- **Pomeriggio**: Fix SQL, Statistics Add-On, VAR, multi-competizione (5 campionati)
- **Sera**: Tool `get_match_statistics`, supporto UEFA (CL + EL), analisi per competizione, MCP server (9 tool)

---

*Documento di stato per continuità tra sessioni Claude Code*
