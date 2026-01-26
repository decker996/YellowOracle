# YellowOracle - Design Document

**Data:** 2026-01-26
**Stato:** Approvato
**Obiettivo:** Sistema di analisi per scommesse sui cartellini gialli nel calcio

---

## 1. Panoramica

YellowOracle è un sistema che aiuta l'utente a effettuare scelte ragionate sulle scommesse relative ai cartellini gialli. Il sistema analizza dati storici, statistiche dei giocatori e degli arbitri, e informazioni in tempo reale per fornire raccomandazioni con percentuali di probabilità.

### Caratteristiche principali

- Analisi basata su dati storici (3 stagioni)
- Ricerca in tempo reale su formazioni, infortuni, quote
- Interfaccia conversazionale (chat con Claude)
- Dashboard per consultazione dati
- Architettura espandibile a più campionati

### Scope iniziale

- **Campionato:** La Liga (Spagna)
- **Stagioni:** 2023/24, 2024/25, 2025/26 (corrente)
- **Uso:** Personale, con possibilità di espansione futura

---

## 2. Architettura

```
┌─────────────────────────────────────────────────────────┐
│                    UTENTE                               │
│         (chat o dashboard)                              │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│              CLAUDE (Cervello)                          │
│  - Risponde alle domande in linguaggio naturale         │
│  - Analizza i dati statistici                           │
│  - Fa ricerche web in tempo reale                       │
│  - Produce raccomandazioni ragionate                    │
└─────────────────┬───────────────────────────────────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
┌───────────────┐   ┌───────────────────┐
│   DATABASE    │   │   FONTI ESTERNE   │
│  (Supabase)   │   │                   │
│               │   │ - Quote betting   │
│ - Giocatori   │   │ - News/infortuni  │
│ - Partite     │   │ - Formazioni live │
│ - Cartellini  │   │                   │
│ - Arbitri     │   │                   │
└───────────────┘   └───────────────────┘
```

### Componenti

| Componente | Tecnologia | Costo |
|------------|------------|-------|
| Database | Supabase (PostgreSQL) | Gratuito |
| Raccolta dati | Python scripts | Gratuito |
| Connessione Claude-DB | MCP (Model Context Protocol) | Gratuito |
| Dashboard | Streamlit | Gratuito |
| Ricerche web | Claude integrato | Gratuito |

**Costo totale stimato: €0/mese**

---

## 3. Struttura Database

### Tabelle

#### `teams` - Squadre
| Campo | Tipo | Descrizione |
|-------|------|-------------|
| id | UUID | Chiave primaria |
| name | VARCHAR | Nome squadra |
| stadium | VARCHAR | Nome stadio |
| avg_cards_home | DECIMAL | Media cartellini ricevuti in casa |
| avg_cards_away | DECIMAL | Media cartellini ricevuti in trasferta |

#### `players` - Giocatori
| Campo | Tipo | Descrizione |
|-------|------|-------------|
| id | UUID | Chiave primaria |
| name | VARCHAR | Nome completo |
| team_id | UUID | FK squadra attuale |
| position | VARCHAR | Ruolo (GK, DF, MF, FW) |
| nationality | VARCHAR | Nazionalità |
| birth_date | DATE | Data di nascita |

#### `referees` - Arbitri
| Campo | Tipo | Descrizione |
|-------|------|-------------|
| id | UUID | Chiave primaria |
| name | VARCHAR | Nome completo |
| avg_cards_per_match | DECIMAL | Media cartellini per partita |
| total_matches | INTEGER | Partite totali dirette |
| total_yellows | INTEGER | Totale cartellini gialli dati |
| total_reds | INTEGER | Totale cartellini rossi dati |

#### `matches` - Partite
| Campo | Tipo | Descrizione |
|-------|------|-------------|
| id | UUID | Chiave primaria |
| season | VARCHAR | Stagione (es. "2025/26") |
| match_date | DATE | Data partita |
| home_team_id | UUID | FK squadra casa |
| away_team_id | UUID | FK squadra ospite |
| referee_id | UUID | FK arbitro |
| home_score | INTEGER | Gol squadra casa |
| away_score | INTEGER | Gol squadra ospite |
| is_derby | BOOLEAN | È un derby? |
| home_position | INTEGER | Posizione classifica casa |
| away_position | INTEGER | Posizione classifica ospite |

#### `cards` - Cartellini
| Campo | Tipo | Descrizione |
|-------|------|-------------|
| id | UUID | Chiave primaria |
| match_id | UUID | FK partita |
| player_id | UUID | FK giocatore |
| minute | INTEGER | Minuto del cartellino |
| card_type | VARCHAR | "yellow" o "red" |
| reason | VARCHAR | Motivo (se disponibile) |

#### `player_season_stats` - Statistiche giocatore per stagione
| Campo | Tipo | Descrizione |
|-------|------|-------------|
| id | UUID | Chiave primaria |
| player_id | UUID | FK giocatore |
| season | VARCHAR | Stagione |
| team_id | UUID | FK squadra |
| matches_played | INTEGER | Partite giocate |
| minutes_played | INTEGER | Minuti totali |
| yellow_cards | INTEGER | Cartellini gialli |
| red_cards | INTEGER | Cartellini rossi |
| fouls_committed | INTEGER | Falli commessi |

### Indici calcolati

- **Indice rischio cartellino giocatore:** `yellow_cards / (minutes_played / 90)`
- **Severità arbitro:** `total_yellows / total_matches`
- **Tensione partita:** Combinazione di derby + differenza classifica + storico scontri

---

## 4. Fonti Dati

### Dati storici (raccolta periodica)

| Dato | Fonte | Frequenza |
|------|-------|-----------|
| Statistiche giocatori | FBref.com | Settimanale |
| Statistiche partite | FBref.com | Settimanale |
| Cartellini per partita | FBref.com | Settimanale |
| Statistiche arbitri | Transfermarkt.com | Settimanale |

### Dati in tempo reale (ricerca live)

| Dato | Fonte | Metodo |
|------|-------|--------|
| Formazioni probabili | Web | Ricerca Claude |
| Infortuni/squalifiche | Web | Ricerca Claude |
| Quote cartellini | Siti betting | Ricerca Claude |
| News recenti | Web | Ricerca Claude |

---

## 5. Logica di Analisi

### Flusso di analisi

```
1. RACCOLTA DATI DAL DATABASE
   → Recupera giocatori delle due rose
   → Per ogni giocatore: cartellini totali, media per 90 min, ultimi 5 match
   → Storico scontri diretti
   → Statistiche arbitro designato

2. RICERCA INFORMAZIONI FRESCHE
   → Formazione probabile
   → Infortuni e squalifiche
   → Quote bookmaker per cartellini
   → News recenti (tensioni, dichiarazioni, diffidati)

3. CALCOLO RISCHIO
   Per ogni giocatore probabile titolare:

   RISCHIO = (storico_personale × 40%)
           + (severità_arbitro × 25%)
           + (tensione_partita × 20%)
           + (fattore_quota × 15%)

4. OUTPUT
   → Classifica giocatori per rischio
   → Spiegazione ragionamento per top 3
   → Raccomandazione con % probabilità
   → Avvertenze (es. dubbi sulla titolarità)
```

### Pesi dei fattori

| Fattore | Peso | Descrizione |
|---------|------|-------------|
| Storico personale | 40% | Cartellini per 90 min del giocatore |
| Severità arbitro | 25% | Media cartellini dell'arbitro |
| Tensione partita | 20% | Derby, classifica, storico acceso |
| Fattore quota | 15% | Indicazioni dal mercato betting |

*I pesi sono configurabili e verranno affinati con l'uso.*

---

## 6. Interfaccia Utente

### Chat con Claude (principale)

Interazione in linguaggio naturale:

```
Utente: "Analizza Real Madrid - Barcellona del 2 febbraio.
        Chi rischia il cartellino giallo?"

Claude: [Interroga database]
        [Cerca informazioni live]
        [Analizza e calcola]
        [Risponde con raccomandazione ragionata]
```

Configurazione tramite MCP per accesso diretto al database.

### Dashboard Streamlit

Pagina web con:
- Classifica "rischio cartellino" dei giocatori
- Statistiche arbitri (severità)
- Storico partite e cartellini
- Filtri per squadra, stagione, ruolo

```
┌─────────────────────────────────────────┐
│  YellowOracle - Dashboard               │
├─────────────────────────────────────────┤
│  Campionato: [La Liga ▼]                │
│                                         │
│  Top 10 - Rischio Cartellino:           │
│  1. Giocatore A - 0.45 per 90min        │
│  2. Giocatore B - 0.41 per 90min        │
│  ...                                    │
│                                         │
│  Arbitri più severi:                    │
│  1. Arbitro X - 5.2 cartellini/partita  │
│  ...                                    │
└─────────────────────────────────────────┘
```

---

## 7. Roadmap Implementazione

### Fase 1: Setup ambiente (1-2 ore)
- [ ] Installare Python
- [ ] Creare account Supabase
- [ ] Creare database con tabelle
- [ ] Configurare connessione Claude-Database (MCP)

### Fase 2: Raccolta dati storici (2-3 ore)
- [ ] Script per scaricare dati La Liga 2023/24
- [ ] Script per scaricare dati La Liga 2024/25
- [ ] Script per scaricare dati La Liga 2025/26 (corrente)
- [ ] Verifica dati nel database

### Fase 3: Test del sistema (1 ora)
- [ ] Prima domanda di prova a Claude
- [ ] Verifica funzionamento analisi
- [ ] Risoluzione eventuali problemi

### Fase 4: Dashboard (1-2 ore)
- [ ] Creare dashboard Streamlit
- [ ] Pubblicare su Streamlit Cloud (opzionale)

### Fase 5: Uso e raffinamento (continuo)
- [ ] Utilizzo per analisi reali
- [ ] Aggiornamento dati settimanale
- [ ] Affinamento pesi analisi

**Tempo totale stimato: 5-8 ore**

---

## 8. Espansione Futura

L'architettura è progettata per supportare:

- **Altri campionati:** Serie A, Bundesliga, Premier League, Ligue 1
- **Altri mercati:** Cartellini rossi, calci d'angolo, falli totali
- **Multiutenza:** Autenticazione, account separati
- **API pubblica:** Esporre le analisi come servizio
- **Tracking risultati:** Verificare accuratezza previsioni nel tempo

---

## 9. Prerequisiti Tecnici

### Software da installare
- Python 3.11+
- pip (gestore pacchetti Python)
- Git (opzionale, per versionamento)

### Account da creare
- Supabase (gratuito)
- Streamlit Cloud (gratuito, opzionale)

### Conoscenze richieste
- Uso base del terminale
- Seguire istruzioni passo-passo

*Non è richiesta esperienza di programmazione. Tutti gli script saranno forniti pronti all'uso con istruzioni dettagliate.*

---

## 10. Decisioni di Design

| Decisione | Motivazione |
|-----------|-------------|
| Supabase vs SQLite locale | Cloud permette accesso da ovunque, backup automatici |
| FBref vs API a pagamento | Costo zero, dati sufficienti per MVP |
| Streamlit vs React | Semplicità, no frontend skills richiesti |
| MCP vs API custom | Integrazione nativa con Claude, meno codice |
| Pesi configurabili | Permette affinamento basato su risultati reali |

---

*Documento generato durante sessione di brainstorming del 2026-01-26*
