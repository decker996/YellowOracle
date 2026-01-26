# YellowOracle - Architettura di Sistema

## Panoramica

YellowOracle è un sistema di analisi del rischio cartellini gialli per partite di calcio. Combina dati storici con modelli matematici per predire quali giocatori hanno maggiore probabilità di ricevere cartellini.

**Versione:** Alpha v2 (2026-01-26)
**Stato:** Produzione con flusso 3-fasi

## Componenti Principali

```
┌──────────────────────────────────────────────────────────────────┐
│                        YellowOracle                               │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │ football-   │    │   Sync      │    │     Supabase        │  │
│  │ data.org    │───▶│  Pipeline   │───▶│    PostgreSQL       │  │
│  │    API      │    │  (Python)   │    │     Database        │  │
│  └─────────────┘    └─────────────┘    └──────────┬──────────┘  │
│                                                    │              │
│                           ┌────────────────────────┼──────┐      │
│                           │                        │      │      │
│                           ▼                        ▼      ▼      │
│                    ┌─────────────┐          ┌───────────────┐   │
│                    │ MCP Server  │          │   Streamlit   │   │
│                    │  (Claude)   │          │   Dashboard   │   │
│                    └─────────────┘          └───────────────┘   │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

## Stack Tecnologico

| Componente | Tecnologia | Scopo |
|------------|------------|-------|
| Database | Supabase (PostgreSQL) | Storage dati storici, views analitiche, RPC functions |
| MCP Server | Python 3.13 + mcp library | Interfaccia Claude Code (10 tool) |
| Sync Pipeline | Python + asyncio + aiohttp | Sincronizzazione parallela da API |
| Dashboard | Streamlit + Altair | Interfaccia web per esplorazione dati |
| CI/CD | GitHub Actions | Sync automatico schedulato |

## Competizioni Supportate

| Codice | Competizione | Paese | Stato DB |
|--------|--------------|-------|----------|
| SA | Serie A | Italia | ✅ Completo |
| PD | La Liga | Spagna | ⚠️ Parziale |
| PL | Premier League | Inghilterra | ⏳ In corso |
| BL1 | Bundesliga | Germania | ❌ Da sincronizzare |
| FL1 | Ligue 1 | Francia | ❌ Da sincronizzare |
| CL | Champions League | UEFA | ❌ Da sincronizzare |
| EL | Europa League | UEFA | ❌ Da sincronizzare |

## Stagioni Supportate

- 2023-2024
- 2024-2025
- 2025-2026 (corrente)

## Flusso Dati

### 1. Acquisizione (Sync)
```
football-data.org API → sync_football_data.py → Supabase
```
- Partite, formazioni, eventi, statistiche
- Batch paralleli (25 req/batch, 60s delay)
- Modalità incrementale o completa

### 2. Elaborazione (Database)
```
Tabelle raw → Views analitiche → RPC Functions
```
- Aggregazioni per stagione/competizione
- Calcoli yellows_per_90, fouls_per_90
- Storico arbitro-giocatore, head-to-head

### 3. Analisi (MCP/Dashboard)
```
Claude Code ←→ MCP Server ←→ Database
Browser ←→ Streamlit ←→ Database
```
- 10 tool MCP per analisi
- Dashboard per esplorazione visuale

## Struttura File Progetto

```
/home/salvatore/Scrivania/soccer/
├── mcp_server.py              # Server MCP (629 righe)
├── requirements.txt           # Dipendenze Python
├── .env                       # Credenziali (non in git)
├── .mcp.json                  # Configurazione MCP per Claude
├── CLAUDE.md                  # System prompt per analisi
│
├── database/
│   ├── schema_v2.sql          # Schema tabelle
│   └── analysis_views.sql     # Views e RPC functions
│
├── scripts/
│   ├── sync_football_data.py  # Sync principale (1.271 righe)
│   ├── weekly_sync.sh         # Sync incrementale
│   └── full_sync.sh           # Sync completo
│
├── dashboard/
│   ├── app.py                 # Homepage Streamlit
│   └── pages/                 # Pagine analisi
│
├── docs/
│   ├── ARCHITECTURE.md        # Questo documento
│   ├── DATABASE.md            # Schema database
│   ├── MCP_TOOLS.md           # Reference tool MCP
│   ├── SYNC.md                # Pipeline sincronizzazione
│   ├── SCORING.md             # Sistema di scoring
│   └── CLAUDE_WORKFLOW.md     # Flusso analisi Claude
│
└── .github/workflows/
    └── sync.yml               # GitHub Actions per sync
```

## Configurazione Ambiente

### Variabili d'Ambiente (.env)
```
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=sb_xxx
FOOTBALL_API_KEY=xxx
```

### Configurazione MCP (.mcp.json)
```json
{
  "mcpServers": {
    "yelloworacle": {
      "command": "/path/to/venv/bin/python",
      "args": ["/path/to/mcp_server.py"],
      "cwd": "/path/to/soccer"
    }
  }
}
```

## Dipendenze Principali

| Package | Versione | Uso |
|---------|----------|-----|
| supabase | ≥2.27.0 | Client database |
| mcp | ≥1.26.0 | Server MCP |
| aiohttp | ≥3.9.0 | HTTP asincrono |
| streamlit | ≥1.53.0 | Dashboard web |
| python-dotenv | ≥1.0.0 | Gestione .env |

## Documentazione Correlata

| Documento | Contenuto |
|-----------|-----------|
| [DATABASE.md](DATABASE.md) | Schema tabelle, views, RPC functions |
| [MCP_TOOLS.md](MCP_TOOLS.md) | Reference dei 10 tool MCP |
| [SYNC.md](SYNC.md) | Pipeline sincronizzazione dati |
| [SCORING.md](SCORING.md) | Formule e calcolo risk score |
| [CLAUDE_WORKFLOW.md](CLAUDE_WORKFLOW.md) | Flusso 3-fasi per analisi |

## Limiti Noti

- **Rate limit API:** 30 richieste/minuto (piano attuale)
- **Dati statistiche:** Disponibili solo con Statistics Add-On (€15/mese)
- **Copertura:** Non tutte le competizioni sono sincronizzate
- **Formazioni:** Dipendono da fonti web esterne (non sempre disponibili)

## Prossimi Sviluppi

1. Completare sincronizzazione tutte le competizioni
2. Migliorare UI dashboard Streamlit
3. Aggiungere notifiche per partite imminenti
4. Espandere modello di scoring con più fattori
