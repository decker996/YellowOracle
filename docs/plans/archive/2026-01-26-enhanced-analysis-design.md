# YellowOracle - Design Analisi Potenziata

**Data:** 2026-01-26
**Stato:** In attesa di approvazione

---

## Obiettivo

Migliorare l'analisi del rischio cartellino su due fronti:
1. **Dato matematico**: integrare metriche sui falli nel calcolo dello score
2. **Contesto Claude**: arricchire l'analisi con ricerche web automatiche (formazioni, arbitro, assenze, importanza partita, derby, stile di gioco)

---

## Flusso di Analisi (3 Fasi)

```
┌─────────────────────────────────────────────────────────────────────┐
│  FASE 0: RICERCA INFORMAZIONI PARTITA (OBBLIGATORIA)                │
│  ─────────────────────────────────────────────────────────────────  │
│  1. WebSearch: "[Squadra1] [Squadra2] formazioni titolari [data]"   │
│  2. WebSearch: "[Squadra1] [Squadra2] arbitro designato"            │
│  3. Se trova → usa quei dati                                        │
│  4. Se non trova → prosegue con dati storici                        │
└─────────────────────────────────────────────────────────────────────┘
                                   ↓
┌─────────────────────────────────────────────────────────────────────┐
│  FASE 1: DATI MATEMATICI (Tool MCP)                                 │
│  ─────────────────────────────────────────────────────────────────  │
│  • analyze_match_risk_v2 → score pesato + falli + statistiche       │
│  • get_team_players → rosa completa con metriche                    │
│  • get_referee_player_cards → storico arbitro (se noto)             │
└─────────────────────────────────────────────────────────────────────┘
                                   ↓
┌─────────────────────────────────────────────────────────────────────┐
│  FASE 2: CONTESTO WEB                                               │
│  ─────────────────────────────────────────────────────────────────  │
│  • WebSearch: assenze/infortuni/squalifiche                         │
│  • WebSearch: importanza partita (classifica, obiettivi)            │
│  • WebSearch: storico derby/rivalità                                │
│  • WebSearch: forma recente squadre                                 │
└─────────────────────────────────────────────────────────────────────┘
                                   ↓
┌─────────────────────────────────────────────────────────────────────┐
│  FASE 3: RAGIONAMENTO E OUTPUT                                      │
│  ─────────────────────────────────────────────────────────────────  │
│  Claude incrocia TUTTO e produce analisi ragionata                  │
└─────────────────────────────────────────────────────────────────────┘
```

**Punto chiave:** La Fase 0 è OBBLIGATORIA e automatica. Claude cerca sempre formazioni e arbitro senza che l'utente lo chieda.

---

## Miglioramenti al Dato Matematico

### Nuove metriche per giocatore

| Metrica | Fonte | Uso |
|---------|-------|-----|
| `fouls_per_90` | `player_season_stats` | Indica aggressività del giocatore |
| `foul_to_card_ratio` | Calcolato | % falli che diventano cartellino |
| `avg_card_minute` | `match_events` | Minuto medio in cui prende cartellino |

### Nuove metriche per squadra

| Metrica | Fonte | Uso |
|---------|-------|-----|
| `team_fouls_per_match` | `match_statistics` | Squadra "fallosa" = più occasioni cartellino |
| `team_fouls_suffered` | `match_statistics` | Squadra che subisce falli = avversari a rischio |

### Nuovo calcolo score

**Con arbitro noto:**
```
Score = (Stagionale × 35%) + (Arbitro × 30%) + (H2H × 15%) + (Falli × 20%)

Dove "Falli" = (fouls_per_90 normalizzato × 50) + (foul_to_card_ratio × 50)
```

**Senza arbitro:**
```
Score = (Stagionale × 45%) + (H2H × 25%) + (Falli × 30%)
```

**Soglia titolare:** Se la formazione titolare è nota dalla Fase 0, filtrare solo quei giocatori per il ranking. Altrimenti mostrare i top 5 della rosa.

---

## Ricerche Web e Contesto

### Ricerche obbligatorie (Fase 0)

| Ricerca | Query esempio | Scopo |
|---------|---------------|-------|
| Formazioni | "Real Madrid Barcelona formazioni probabili 26 gennaio 2026" | Filtrare solo titolari |
| Arbitro | "Real Madrid Barcelona arbitro designato La Liga" | Attivare analisi storico arbitro |

### Ricerche contestuali (Fase 2)

| Ricerca | Query esempio | Impatto sull'analisi |
|---------|---------------|----------------------|
| Assenze | "Real Madrid infortunati squalificati gennaio 2026" | Escludere giocatori, valutare sostituti |
| Classifica | "classifica La Liga 2025-2026" | Importanza partita (salvezza, titolo, Europa) |
| Forma | "Real Madrid ultime 5 partite risultati" | Squadra nervosa = più cartellini |
| Derby/Rivalità | "El Clasico storia rivalità" | Partite calde = fattore moltiplicativo |
| Stile gioco | "Real Madrid stile di gioco tattica Ancelotti" | Squadra aggressiva vs possesso |

### Fattori moltiplicativi per il ragionamento

- **Derby storico** (Clasico, Derby d'Italia, ecc.): rischio +20%
- **Partita decisiva** (scudetto, salvezza, qualificazione): rischio +15%
- **Squadra in crisi** (4+ partite senza vittoria): rischio +10%
- **Arbitro severo** (>5 gialli/partita media): rischio +10%

Questi moltiplicatori non sono nel calcolo matematico, ma Claude li usa nel ragionamento discorsivo.

---

## Formato Output

```markdown
## 🟨 Analisi: Real Madrid vs Barcelona
**Data:** 26/01/2026 | **Competizione:** La Liga | **Giornata:** 21

### 📋 Info Partita
- **Arbitro:** Jesús Gil Manzano (media 5.2 gialli/partita)
- **Formazioni:** ✅ Confermate | ⚠️ Probabili | ❌ Non disponibili
- **Contesto:** Derby, Madrid -3 punti dal Barça, decisiva per titolo

### 📊 Ragionamento

Tchouaméni è il giocatore più a rischio di questa partita, e non è un caso.
Il francese gioca come scudo davanti alla difesa del Real Madrid: è lui che
deve interrompere le ripartenze del Barcellona e bloccare Pedri e Gavi quando
accelerano. Questo ruolo lo porta inevitabilmente a commettere molti falli
(4.2 a partita, il dato più alto della squadra).

Ma c'è di più: Gil Manzano, l'arbitro designato, ha un rapporto particolare
con lui. Lo ha ammonito in 3 delle ultime 4 partite dirette - sembra quasi
che lo tenga d'occhio. E nei derby Tchouaméni si accende: negli ultimi 3
Clasico è sempre uscito col giallo.

Aggiungiamo il contesto: questa è una partita da dentro o fuori per il Real,
sotto di 3 punti e con pressione altissima. Quando la tensione sale, i
centrocampisti difensivi sono i primi a pagare dazio.

Gavi è la seconda scelta per motivi simili - stesso ruolo speculare nel
Barcellona, stesso temperamento focoso. In un Clasico tirato, uno dei due
(o entrambi) vedrà quasi certamente il cartellino giallo.

### 🎯 Top 5 Rischio Cartellino

| # | Giocatore | Ruolo | Score | Stagione | Falli | Arbitro | H2H |
|---|-----------|-------|-------|----------|-------|---------|-----|
| 1 | Tchouaméni | MED | 78.4 | 42.0 | 18.5 | 12.0 | 5.9 |
| 2 | Gavi | MED | 71.2 | 38.0 | 16.0 | 10.5 | 6.7 |
| 3 | Camavinga | MED | 65.8 | 35.0 | 15.0 | 9.8 | 6.0 |
| 4 | Araujo | DIF | 62.1 | 33.0 | 14.0 | 8.5 | 6.6 |
| 5 | Valverde | MED | 58.9 | 30.0 | 13.5 | 10.4 | 5.0 |

### ⚠️ Note
- Formazioni basate su fonti web del 25/01, potrebbero variare
- Bellingham assente per squalifica (fonte: Marca)

### 📖 Glossario

| Sigla | Significato |
|-------|-------------|
| **Score** | Punteggio combinato 0-100 che indica la probabilità di cartellino. Più alto = più a rischio |
| **Stagione** | Contributo dal rendimento stagionale (gialli per 90 minuti) |
| **Falli** | Contributo dalla propensione al fallo (falli/90' + rapporto fallo→cartellino) |
| **Arbitro** | Contributo dallo storico con l'arbitro designato (% ammonizioni in partite dirette) |
| **H2H** | Head-to-Head: storico cartellini negli scontri diretti tra le due squadre |
| **MED/DIF/ATT** | Ruolo: Mediano (centrocampista), Difensore, Attaccante |
| **per 90'** | Statistica normalizzata su 90 minuti di gioco |
```

---

## Modifiche Tecniche

### 1. Fix bug esistente - `mcp_server.py`
Il tool `get_match_statistics` usa `team_side` che non esiste → correggere con `team_id`

### 2. Nuovo tool MCP - `analyze_match_risk_v2`
- Aggiunge metriche falli al calcolo score
- Nuovi pesi: Stagionale 35%, Arbitro 30%, H2H 15%, Falli 20%
- Restituisce anche `fouls_per_90` e `foul_to_card_ratio` per ogni giocatore

### 3. Nuova vista SQL - `player_fouls_stats`
- Aggrega falli per giocatore dalla tabella `match_statistics`
- Calcola `avg_fouls_per_90` e `foul_to_card_ratio`

### 4. Aggiornare CLAUDE.md
- Nuovo flusso a 3 fasi (Fase 0 → Fase 1 → Fase 2 → Output)
- Checklist ricerche web obbligatorie
- Template output con ragionamento discorsivo e glossario
- Fattori moltiplicativi contestuali

### 5. Nessuna modifica a:
- Schema database (i campi falli esistono già)
- Script di sync (già importa i falli)
- Dashboard Streamlit (per ora)

### File toccati

```
├── mcp_server.py          # Fix bug + nuovo tool
├── CLAUDE.md              # Nuovo flusso completo
└── database/
    └── analysis_views.sql # Nuova vista falli
```

---

## Piano Implementazione

1. Fix bug `get_match_statistics`
2. Creare vista SQL `player_fouls_stats`
3. Creare tool `analyze_match_risk_v2`
4. Aggiornare `CLAUDE.md` con nuovo flusso e template
5. Test con partita reale
