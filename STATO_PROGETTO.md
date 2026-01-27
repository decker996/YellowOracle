# YellowOracle - Stato del Progetto

**Ultimo aggiornamento:** 2026-01-27 15:30
**Fase attuale:** Alpha v2 - Piano miglioramenti research-based pronto

---

## Cosa è YellowOracle

Sistema di analisi cartellini per scommesse calcistiche. Analizza:
1. **Storico stagionale giocatore** - Cartellini per competizione (Serie A, CL, EL...)
2. **Storico arbitro-giocatore** - Come un arbitro si comporta con specifici giocatori
3. **Scontri diretti** - Cartellini storici negli head-to-head tra due squadre
4. **Statistiche partita** - Falli, possesso, tiri (aggregato per squadra)

---

## Stato Database

| Competizione | Codice | Stato | Note |
|--------------|--------|-------|------|
| Serie A | SA | ✅ Completo | 3 stagioni |
| La Liga | PD | ⚠️ Parziale | In completamento |
| Premier League | PL | ⏳ In corso | Stagione corrente |
| Bundesliga | BL1 | ❌ Da fare | - |
| Ligue 1 | FL1 | ❌ Da fare | - |
| Champions League | CL | ❌ Da fare | - |
| Europa League | EL | ❌ Da fare | - |

---

## MCP Server - 10 Tool Disponibili

| Tool | Descrizione | Parametri |
|------|-------------|-----------|
| `analyze_match_risk` | **Principale** - Analisi con score pesato | home_team, away_team, referee? |
| `get_matches_by_date` | Partite per data | competition?, date?, days_ahead? |
| `get_player_season_stats` | Cartellini per competizione | player_name, season?, competition? |
| `get_player_season_stats_total` | Cartellini totali (tutte competizioni) | player_name, season? |
| `get_referee_player_cards` | Storico arbitro-giocatore | referee_name, team1, team2 |
| `get_head_to_head_cards` | Scontri diretti | player_name, team1, team2 |
| `get_teams` | Lista squadre | - |
| `get_referees` | Lista arbitri con statistiche | - |
| `get_team_players` | Giocatori di una squadra | team_name, season? |
| `get_match_statistics` | Falli, possesso, tiri | team_name?, season?, limit? |

---

## Struttura File

```
soccer/
├── .env                              # Credenziali (non in git)
├── .mcp.json                         # Configurazione MCP per Claude
├── CLAUDE.md                         # System prompt per analisi
├── STATO_PROGETTO.md                 # QUESTO FILE
├── requirements.txt                  # Dipendenze Python
├── mcp_server.py                     # Server MCP (10 tool)
│
├── .github/workflows/
│   └── sync.yml                      # GitHub Actions per sync
│
├── database/
│   ├── schema_v2.sql                 # Schema database
│   └── analysis_views.sql            # Views e RPC functions
│
├── scripts/
│   ├── sync_football_data.py         # Script sync principale
│   ├── weekly_sync.sh                # Sync incrementale
│   ├── full_sync.sh                  # Sync completo
│   └── archive/                      # Script legacy archiviati
│       ├── scrape_laliga.py
│       └── test_parallel_api.py
│
├── dashboard/
│   ├── app.py                        # Homepage Streamlit
│   └── pages/
│       ├── 1_players.py
│       ├── 2_referees.py
│       └── 3_match_analysis.py
│
└── docs/                             # Documentazione modulare
    ├── ARCHITECTURE.md               # Overview sistema
    ├── DATABASE.md                   # Schema e views
    ├── MCP_TOOLS.md                  # Reference 10 tool
    ├── SYNC.md                       # Pipeline sincronizzazione
    ├── SCORING.md                    # Formule calcolo score
    ├── CLAUDE_WORKFLOW.md            # Logica flusso 3-fasi
    ├── CRON_SETUP.md                 # Setup cron
    └── plans/
        ├── 2026-01-27-research-improvements.md  # Piano miglioramenti (DA ESEGUIRE)
        └── archive/                  # Design docs archiviati (9 file)
```

---

## Documentazione

| Documento | Contenuto |
|-----------|-----------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Overview sistema, componenti, stack |
| [docs/DATABASE.md](docs/DATABASE.md) | Schema tabelle, views, RPC functions |
| [docs/MCP_TOOLS.md](docs/MCP_TOOLS.md) | Reference dei 10 tool MCP |
| [docs/SYNC.md](docs/SYNC.md) | Pipeline sincronizzazione dati |
| [docs/SCORING.md](docs/SCORING.md) | Formule e calcolo risk score |
| [docs/CLAUDE_WORKFLOW.md](docs/CLAUDE_WORKFLOW.md) | Logica del flusso 3-fasi |

---

## Come Usare YellowOracle

### Interfaccia: Claude Code

Apri Claude Code nella directory del progetto e chiedi:

**Partita singola:**
```
Analizza Roma vs Milan di domenica
```

**Giornata intera:**
```
Analizzami le partite di Serie A di oggi
```

**Giocatore specifico:**
```
Barella rischia il giallo contro il Napoli?
```

---

## Comandi Utili

```bash
# === SINCRONIZZAZIONE ===

# Sync incrementale (consigliato)
./venv/bin/python scripts/sync_football_data.py --competition SA --season 2025-2026 --incremental

# Sync completo (prima volta o ricostruzione)
./venv/bin/python scripts/sync_football_data.py --competition SA --season 2025-2026 --full

# Sync multi-competizione
./scripts/weekly_sync.sh              # Tutte, incrementale
./scripts/weekly_sync.sh "SA PL"      # Solo alcune


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

## Prossimi Passi

### PRIORITÀ 0: Research-Based Improvements
Eseguire il piano in `docs/plans/2026-01-27-research-improvements.md`:
```bash
# Usa superpowers:executing-plans per implementare
# 6 task, 3 fasi, impatto stimato +15-25% accuratezza
```

### PRIORITÀ 1: Completare Sync
```bash
# Completare Premier League
./venv/bin/python scripts/sync_football_data.py --competition PL --season 2025-2026 --full

# Bundesliga, Ligue 1
./venv/bin/python scripts/sync_football_data.py --competition BL1 --season 2025-2026 --full
./venv/bin/python scripts/sync_football_data.py --competition FL1 --season 2025-2026 --full
```

### PRIORITÀ 2: Test Analisi
Testare il flusso completo con partite reali delle competizioni sincronizzate.

### PRIORITÀ 3: Dashboard (Fase Beta)
Migliorare UI Streamlit e deploy su cloud.

---

## Cronologia Sessioni

### 2026-01-27 (Sessione 6)
- **Piano Research-Based Improvements:**
  - Analizzate ricerche accademiche su fattori predittivi cartellini
  - Creato piano implementazione con 6 task in 3 fasi
  - Piano salvato in `docs/plans/2026-01-27-research-improvements.md`
- **Nuovi fattori pianificati:**
  - Derby detection con tabella `rivalries` (+10-26%)
  - Home/Away factor (×0.94/×1.06)
  - League baseline normalization (La Liga +30%, Bundesliga -5%)
  - Referee delta/outlier detection (±15%)
  - Possession differential factor (±15%)
  - Matchup bonus per foul drawers (Vinicius, Leao, etc.)
- **Struttura piano:**
  - Fase A: 4 migrazioni SQL (parallele)
  - Fase B: Integrazione unica in `mcp_server.py`
  - Fase C: Documentazione
- **Stato:** Piano pronto, da eseguire

### 2026-01-27 (Sessione 5)
- **Chiarimenti sync CL/EL:**
  - Analisi funzionamento upsert su `external_id`
  - Squadre/giocatori già in DB vengono aggiornati, non duplicati
  - API chiamate comunque (possibile ottimizzazione futura)
- **Fix GitHub Actions:**
  - Corretta descrizione fuorviante parametro `season`
  - Era "per sync full" → ora "solo per incremental, full fa tutte"

### 2026-01-26 (Sessione 4 - Sera)
- **Documentazione unificata:**
  - Creati 6 documenti modulari in `docs/`
  - Archiviati 9 vecchi design docs in `docs/plans/archive/`
  - Eliminato `database/schema.sql` (obsoleto)
  - Archiviati script legacy in `scripts/archive/`
  - Aggiornato STATO_PROGETTO.md

### 2026-01-26 (Sessione 3 - Sera)
- **Analisi Potenziata v2:**
  - Flusso a 3 fasi: ricerca web → dati MCP → contesto web
  - Metriche falli integrate nel calcolo score
  - Pesi: 35% stagionale, 30% arbitro, 15% H2H, 20% falli
  - Vista SQL `team_fouls_stats`
  - Template output discorsivo + glossario

### 2026-01-26 (Sessione 2 - Pomeriggio)
- **Alpha implementata:**
  - `CLAUDE.md` system prompt
  - Script sync multi-competizione
  - Sync incrementale con `--days N`
  - GitHub Actions per sync automatico

### 2026-01-26 (Sessione 1 - Mattina/Notte)
- Design iniziale, viste SQL, dashboard Streamlit
- MCP server con 10 tool
- Supporto 7 competizioni

---

## Come Riprendere una Sessione

1. Leggi `STATO_PROGETTO.md` (questo file) per il contesto
2. Consulta `docs/` per dettagli tecnici specifici
3. Verifica stato DB con il comando nella sezione "Comandi Utili"

---

*Documento di stato per continuità tra sessioni Claude Code*
