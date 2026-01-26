# Pipeline di Sincronizzazione

Documentazione della pipeline di acquisizione dati da football-data.org.

## Fonte Dati

| Aspetto | Dettaglio |
|---------|-----------|
| **API** | football-data.org |
| **Piano** | Free + Deep Data (€29/mese) + Statistics Add-On (€15/mese) |
| **Rate Limit** | 30 richieste/minuto |
| **Autenticazione** | API Key in header `X-Auth-Token` |

## Script Principale

**File:** `scripts/sync_football_data.py` (1.271 righe)

### Modalità di Sincronizzazione

| Modalità | Flag | Comportamento | Durata |
|----------|------|---------------|--------|
| **Incrementale** | `--incremental` | Solo partite nuove dall'ultimo sync | ~15 min |
| **Completo** | `--full` | Ricostruzione totale stagione | ~45 min/competizione |

### Sintassi Comando

```bash
python scripts/sync_football_data.py \
  --competition <CODICE> \
  --season <STAGIONE> \
  --full|--incremental
```

### Esempi

```bash
# Sync incrementale Serie A stagione corrente
python scripts/sync_football_data.py --competition SA --season 2025-2026 --incremental

# Sync completo La Liga tutte le stagioni
python scripts/sync_football_data.py --competition PD --season 2023-2024 --full
python scripts/sync_football_data.py --competition PD --season 2024-2025 --full
python scripts/sync_football_data.py --competition PD --season 2025-2026 --full

# Sync Premier League
python scripts/sync_football_data.py --competition PL --season 2025-2026 --full
```

## Dati Sincronizzati

Per ogni partita vengono acquisiti:

| Tipo | Endpoint API | Tabella DB |
|------|--------------|------------|
| Metadata partita | `/matches/{id}` | matches |
| Formazioni | `/matches/{id}` | lineups |
| Eventi | `/matches/{id}` | match_events |
| Statistiche | `/matches/{id}` | match_statistics |

### Dettaglio Dati Acquisiti

**Partita:**
- Data, ora, stadio
- Risultato (finale e primo tempo)
- Arbitro principale e VAR
- Status (SCHEDULED, LIVE, FINISHED, POSTPONED)

**Formazioni:**
- Titolari e panchinari
- Posizione in campo
- Numero maglia
- Minuti giocati, entrate/uscite

**Eventi:**
- Goal (con minuto e autore)
- Cartellini gialli e rossi
- Sostituzioni
- Autogol, rigori

**Statistiche:**
- Possesso palla
- Tiri (totali, in porta, fuori)
- Corner, punizioni
- Falli commessi/subiti
- Parate, fuorigioco

## Strategia di Parallelizzazione

Per rispettare il rate limit mantenendo velocità:

| Parametro | Valore |
|-----------|--------|
| Batch size | 25 richieste |
| Delay tra batch | 60 secondi |
| Richieste parallele | asyncio + aiohttp |
| Velocità effettiva | ~800 partite in 30 min |

### Flusso Batch

```
┌─────────────────────────────────────────────────────────┐
│                    Batch 1 (25 req)                      │
│  match_1, match_2, ... match_25 → parallelo             │
└─────────────────────────────────────────────────────────┘
                          │
                    ⏱️ 60 secondi
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    Batch 2 (25 req)                      │
│  match_26, match_27, ... match_50 → parallelo           │
└─────────────────────────────────────────────────────────┘
                          │
                         ...
```

## Shell Script

### weekly_sync.sh (Incrementale)

**Uso:** Sync settimanale automatico

```bash
./scripts/weekly_sync.sh [COMPETITIONS]

# Esempi
./scripts/weekly_sync.sh           # Tutte le competizioni
./scripts/weekly_sync.sh SA PL     # Solo Serie A e Premier League
```

**Caratteristiche:**
- Modalità incrementale (solo nuove partite)
- Log salvati in `logs/sync_YYYYMMDD_HHMMSS.log`
- Durata: ~15 minuti

### full_sync.sh (Completo)

**Uso:** Ricostruzione completa database

```bash
./scripts/full_sync.sh [COMPETITIONS]

# Esempi
./scripts/full_sync.sh SA          # Solo Serie A
./scripts/full_sync.sh             # Tutte le competizioni
```

**Caratteristiche:**
- Modalità completa (tutte le 3 stagioni)
- Durata: ~45 min per competizione
- Usare solo per setup iniziale o recovery

## GitHub Actions

**File:** `.github/workflows/sync.yml`

### Trigger

```yaml
on:
  workflow_dispatch:
    inputs:
      competitions:
        description: 'Competizioni (spazio-separate)'
        default: 'SA PL PD'
      sync_type:
        description: 'Tipo sync'
        default: 'incremental'
      season:
        description: 'Stagione'
        default: '2025-2026'
```

### Configurazione

| Parametro | Valore |
|-----------|--------|
| Runner | ubuntu-latest |
| Python | 3.13 |
| Timeout | 6 ore |
| Caching | pip dependencies |

### Secrets Richiesti

```
SUPABASE_URL      # URL istanza Supabase
SUPABASE_KEY      # Chiave API Supabase
FOOTBALL_API_KEY  # Chiave football-data.org
```

## Scheduling Consigliato

### Cron Locale

```bash
# Ogni lunedì alle 6:00
0 6 * * 1 /path/to/weekly_sync.sh SA PL >> /path/to/logs/cron.log 2>&1
```

### GitHub Actions Schedule

```yaml
on:
  schedule:
    - cron: '0 6 * * 1'  # Ogni lunedì alle 6:00 UTC
```

## Troubleshooting

### Rate Limit Exceeded

```
Error: 429 Too Many Requests
```

**Soluzione:** Aumentare delay tra batch (default 60s) o ridurre batch size.

### Timeout

```
Error: Connection timeout
```

**Soluzione:** Rilanciare con `--incremental` (riprende da ultima partita).

### Dati Mancanti

```
Warning: No statistics for match XXX
```

**Causa:** Statistics Add-On non attivo o partita senza statistiche.
**Impatto:** Score falli sarà calcolato solo con dati individuali.

## Stato Attuale Database

| Competizione | Stagioni | Partite | Status |
|--------------|----------|---------|--------|
| Serie A (SA) | 2023-2026 | ~1140 | ✅ Completo |
| La Liga (PD) | 2023-2026 | ~760 | ⚠️ Parziale |
| Premier League (PL) | 2025-2026 | - | ⏳ In corso |
| Bundesliga (BL1) | - | - | ❌ Da fare |
| Ligue 1 (FL1) | - | - | ❌ Da fare |
| Champions League (CL) | - | - | ❌ Da fare |
| Europa League (EL) | - | - | ❌ Da fare |
