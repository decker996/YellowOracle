# YellowOracle - Stato del Progetto

**Ultimo aggiornamento:** 2026-01-28
**Fase attuale:** Beta v2.0 - Moltiplicatori contestuali implementati

---

## Cosa è YellowOracle

Sistema di analisi cartellini per scommesse calcistiche. Analizza:
1. **Storico stagionale giocatore** - Cartellini per competizione (Serie A, PL, La Liga, Bundesliga, Ligue 1, CL, BSA)
2. **Storico arbitro-giocatore** - Come un arbitro si comporta con specifici giocatori
3. **Scontri diretti** - Cartellini storici negli head-to-head tra due squadre
4. **Statistiche partita** - Falli, possesso, tiri (aggregato per squadra)

---

## Stato Database

| Competizione | Codice | Partite | FINISHED | Stato |
|--------------|--------|---------|----------|-------|
| Serie A | SA | 1140 | 979 | ✅ Completo |
| Premier League | PL | 1140 | 990 | ✅ Completo |
| La Liga | PD | 1140 | 969 | ✅ Completo |
| Bundesliga | BL1 | 918 | 779 | ✅ Completo |
| Ligue 1 | FL1 | 918 | 782 | ✅ Completo |
| Champions League | CL | 503 | 440 | ✅ Completo |
| Brasileirão | BSA | - | - | ⏳ Da sincronizzare |

> **Nota:** Europa League (EL) rimossa - non accessibile con il piano API attuale.

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
│   ├── analysis_views.sql            # Views e RPC functions
│   └── migrations/                   # Migrazioni v2.0
│       ├── 001_derby_rivalries.sql   # Tabella rivalries + funzione
│       ├── 002_league_baselines.sql  # Vista normalizzazione lega
│       ├── 003_referee_delta.sql     # Vista outlier arbitri
│       └── 004_possession_factor.sql # Vista possesso squadre
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
│   ├── app.py                        # Homepage Streamlit v2
│   └── pages/
│       ├── 1_players.py              # Statistiche giocatori
│       ├── 2_referees.py             # Arbitri con profilo outlier
│       ├── 3_match_analysis.py       # Analisi partita (MCP integration)
│       ├── 4_rivalries.py            # Derby & Rivalità
│       └── 5_team_stats.py           # Statistiche squadre/possesso
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

### PRIORITÀ 1: Sincronizzare BSA
```bash
./venv/bin/python scripts/sync_football_data.py --competition BSA --season 2025-2026 --full
```

### PRIORITÀ 2: Test Completo
Testare il flusso completo con partite reali:
- Verificare moltiplicatori derby su Inter-Milan, Real-Barca
- Verificare profili arbitro outlier
- Verificare fattori possesso

### PRIORITÀ 3: Deploy Dashboard
Deploy Streamlit su cloud (Streamlit Cloud o Render).

### PRIORITÀ 4: Ottimizzazioni Future
- Cache risultati `analyze_match_risk`
- Matchup bonus per foul drawers (Vinicius, Leao)
- League baseline dinamico (calcolo da dati reali)

---

## Cronologia Sessioni

### 2026-01-28 (Sessione 8) - MAJOR: v2.0
- **Piano Integrato Eseguito** (`docs/plans/2026-01-28-integrated-improvements.md`):
  - 11 task completati in 4 fasi (0, A, B, C, D)
  - Impatto stimato: +15-25% accuratezza predizioni
- **Database (Fase A):**
  - Creata tabella `rivalries` con 50+ rivalità (6 leghe)
  - Creata vista `league_card_baselines` (normalizzazione per lega)
  - Creata vista `referee_league_comparison` (profilo outlier arbitri)
  - Creata vista `team_possession_stats` (stile gioco squadre)
  - 4 migrazioni SQL in `database/migrations/`
- **MCP Server (Fase B):**
  - `analyze_match_risk` integra 5 moltiplicatori contestuali:
    - Derby detection: ×1.10-1.26
    - Home/Away: ×0.94/×1.06
    - Referee outlier: ×0.85-1.15
    - Possession: ×0.85-1.15
    - League normalization (parziale)
  - Output JSON include: `derby`, `possession`, `referee_profile`, `multipliers`
- **Dashboard (Fase C):**
  - `2_referees.py`: Aggiunto filtro competizione, profilo outlier
  - `3_match_analysis.py`: Riscritto con integrazione MCP completa
  - `4_rivalries.py`: Nuova pagina Derby & Rivalità
  - `5_team_stats.py`: Nuova pagina Statistiche Squadre
  - `app.py`: Homepage v2.0 con 5 metriche e quick actions
- **Documentazione (Fase D):**
  - `docs/SCORING.md`: Aggiunta sezione Moltiplicatori Contestuali v2
  - `STATO_PROGETTO.md`: Aggiornato struttura e cronologia

### 2026-01-28 (Sessione 7)
- **Analisi problemi sync:**
  - Verificato stato database: 6 competizioni complete (SA, PL, PD, BL1, FL1, CL)
  - Identificato errore Europa League: 403 Forbidden (non nel piano API)
  - Rimossa EL dalla configurazione e dal database
- **Nuova competizione:**
  - Aggiunto BSA (Brasileirão Série A) alla configurazione
  - Verificato accesso API: BSA accessibile
  - Pronto per sync via GitHub Actions
- **Ottimizzazione sync:**
  - Parallelizzato `sync_players`: da ~90s sequenziale a ~2min parallelo
  - Collo di bottiglia principale: `sync_player_stats` (~25-50 min)
  - Raccomandazione: usare `--incremental --full` per update settimanali
- **Aggiornato piano research-improvements:**
  - Rimosso EL, aggiunto BSA con derby brasiliani
  - Aggiunto fattore normalizzazione BSA (×1.10)
- **GitHub Actions:**
  - Aggiornata lista competizioni default: `SA PL PD BL1 FL1 CL BSA`

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
