# YellowOracle - Stato del Progetto

**Ultimo aggiornamento:** 2026-01-26 14:30
**Fase attuale:** Alpha - Interfaccia Claude Code attiva, La Liga sincronizzata

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
| `competitions` | 1 | La Liga sincronizzata |
| `teams` | 24 | La Liga |
| `players` | 688 | La Liga |
| `referees` | 76 | La Liga |
| `matches` | 760 | La Liga 2025-2026 |
| `match_events` | 1000+ | Gol e cartellini |
| `match_statistics` | 760 | Falli, possesso, tiri |
| `lineups` | 1000+ | Formazioni |

**Prossimo:** Sincronizzare altre competizioni (Serie A, Premier, ecc.)

---

## Competizioni Supportate (7)

### Campionati Nazionali
| Codice | Campionato | Paese | Stato |
|--------|------------|-------|-------|
| PD | La Liga | Spagna | ✅ Sincronizzata |
| SA | Serie A | Italia | ⏳ Da sincronizzare |
| BL1 | Bundesliga | Germania | ⏳ Da sincronizzare |
| PL | Premier League | Inghilterra | ⏳ Da sincronizzare |
| FL1 | Ligue 1 | Francia | ⏳ Da sincronizzare |

### Competizioni UEFA
| Codice | Competizione | Stato |
|--------|--------------|-------|
| CL | UEFA Champions League | ⏳ Da sincronizzare |
| EL | UEFA Europa League | ⏳ Da sincronizzare |

---

## MCP Server - 10 Tool Disponibili

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
| `get_matches_by_date` | Partite per data | competition?, date?, days_ahead? |
| `analyze_match_risk` | Analisi con score pesato (40/35/25) | home_team, away_team, referee? |

---

## File del Progetto

```
soccer/
├── .env                              # Credenziali (Supabase + Football API)
├── .mcp.json                         # Configurazione MCP per Claude
├── CLAUDE.md                         # **NUOVO** System prompt per analisi
├── STATO_PROGETTO.md                 # QUESTO FILE
├── requirements.txt                  # **NUOVO** Dipendenze Python
├── mcp_server.py                     # Server MCP (10 tool)
│
├── .github/
│   └── workflows/
│       └── sync.yml                  # **NUOVO** GitHub Actions per sync automatico
│
├── database/
│   ├── schema_v2.sql                 # Schema database completo
│   └── analysis_views.sql            # Viste e funzioni SQL per analisi
│
├── scripts/
│   ├── sync_football_data.py         # Script sync (ora con --days!)
│   ├── weekly_sync.sh                # Sync settimanale multi-competizione
│   └── full_sync.sh                  # Sync completa multi-competizione
│
├── dashboard/
│   ├── app.py                        # Homepage Streamlit
│   └── pages/
│       ├── 1_players.py              # Statistiche giocatori
│       ├── 2_referees.py             # Statistiche arbitri
│       └── 3_match_analysis.py       # Analisi partita
│
└── docs/
    └── plans/
        ├── 2026-01-26-yelloworacle-design.md
        ├── 2026-01-26-alpha-interface-design.md    # **NUOVO**
        └── 2026-01-26-alpha-implementation.md      # **NUOVO**
```

---

## Come Usare YellowOracle (Alpha)

### Interfaccia: Claude Code

Apri Claude Code nella directory del progetto e chiedi:

**Partita singola:**
```
Analizza Real Madrid vs Barcelona di domenica
```

**Giornata intera:**
```
Analizzami le partite di La Liga di oggi
```

**Giocatore specifico:**
```
Vinicius rischia il giallo contro l'Atletico?
```

### Output Atteso

Claude risponderà con:
- Tabella top 3 giocatori a rischio per squadra
- Score breakdown (stagionale/arbitro/H2H)
- Analisi discorsiva

---

## Comandi Utili

```bash
# === SINCRONIZZAZIONE ===

# Sync incrementale (ultimi 7 giorni) - VELOCE
./venv/bin/python scripts/sync_football_data.py --competition SA --days 7 --full

# Sync completa stagione
./venv/bin/python scripts/sync_football_data.py --competition SA --season 2025-2026 --full

# Sync tutte le competizioni (script)
./scripts/weekly_sync.sh              # Tutte, incrementale
./scripts/weekly_sync.sh "SA PL"      # Solo alcune

# Sync completa (tutte stagioni)
./scripts/full_sync.sh SA             # Solo Serie A
./scripts/full_sync.sh                # Tutte


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
```

---

## GitHub Actions (Sync Automatico)

Il sync può girare automaticamente su GitHub:

1. **Configura Secrets** nel repo GitHub:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `FOOTBALL_API_KEY`

2. **Trigger:**
   - Manuale: Actions → "YellowOracle Sync" → Run workflow
   - Automatico: Ogni lunedì alle 6:00 UTC

---

## Prossimi Passi

### PRIORITÀ 1: Sincronizzare Altre Competizioni

```bash
# Serie A
./venv/bin/python scripts/sync_football_data.py --competition SA --season 2025-2026 --full

# Premier League
./venv/bin/python scripts/sync_football_data.py --competition PL --season 2025-2026 --full
```

### PRIORITÀ 2: Test Analisi

Dopo aver sincronizzato i dati, testare:
```
Analizza Napoli vs Inter
Analizza le partite di Serie A di domani
```

### PRIORITÀ 3: Dashboard Web (Fase Beta)

- Migliorare dashboard Streamlit
- Aggiungere form per analisi partita
- Deploy su Streamlit Cloud

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
                        │
                        ▼
                ┌──────────────┐
                │ GitHub       │
                │ Actions      │
                └──────────────┘
```

---

## Cronologia Sessioni

### 2026-01-26 (Sessione 2 - Pomeriggio)
- **Alpha implementata:**
  - `CLAUDE.md` - System prompt per analisi cartellini
  - Script sync multi-competizione (`weekly_sync.sh`, `full_sync.sh`)
  - Sync incrementale con `--days N`
  - GitHub Actions per sync automatico
  - La Liga 2025-2026 sincronizzata (380 partite, 1461 eventi, 760 statistiche)

### 2026-01-26 (Sessione 1 - Mattina/Notte)
- Design iniziale, viste SQL, dashboard Streamlit
- MCP server con 10 tool
- Supporto 7 competizioni (5 campionati + 2 UEFA)
- Score pesato (40% stagionale + 35% arbitro + 25% H2H)

---

## Come Riprendere una Sessione

```
Leggi STATO_PROGETTO.md
```

---

*Documento di stato per continuità tra sessioni Claude Code*
