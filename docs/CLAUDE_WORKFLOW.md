# Workflow di Analisi Claude

Documentazione del flusso obbligatorio per le analisi partita tramite Claude Code.

## Flusso in 3 Fasi

Quando viene richiesta un'analisi partita, il flusso è **obbligatorio e sequenziale**:

```
┌─────────────────────────────────────────────────────────────────┐
│                    FASE 0: Info Partita                          │
│                    (Web Search - SEMPRE)                         │
│                                                                   │
│   • Formazioni probabili/confermate                              │
│   • Arbitro designato                                            │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASE 1: Dati Matematici                       │
│                    (MCP Tools)                                   │
│                                                                   │
│   • analyze_match_risk (principale)                              │
│   • Tool di approfondimento (se necessario)                      │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASE 2: Contesto                              │
│                    (Web Search)                                  │
│                                                                   │
│   • Assenze, infortuni, squalifiche                              │
│   • Classifica e importanza partita                              │
│   • Forma squadra, rivalità                                      │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASE 3: Output                                │
│                    (Ragionamento + Template)                     │
│                                                                   │
│   • Analisi discorsiva                                           │
│   • Tabella Top 5                                                │
│   • Note e fonti                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Fase 0: Ricerca Info Partita

**Questa fase è OBBLIGATORIA e automatica.** Non chiedere conferma all'utente.

### Ricerche da Effettuare

| Ricerca | Query Esempio |
|---------|---------------|
| Formazioni | `"[Squadra1] [Squadra2] formazioni probabili [data]"` |
| Arbitro | `"[Squadra1] [Squadra2] arbitro designato [competizione]"` |

### Gestione Risultati

**Formazioni:**
- ✅ **Confermate** - Fonte ufficiale, formazioni annunciate
- ⚠️ **Probabili** - Previsioni giornalistiche
- ❌ **Non disponibili** - Nessuna informazione trovata

**Arbitro:**
- Se trovato → Passarlo a `analyze_match_risk`
- Se non trovato → Procedere senza (il tool ricalcola i pesi)

## Fase 1: Dati Matematici

### Tool Principale

```
analyze_match_risk(home_team, away_team, referee?)
```

Restituisce:
- Top 5 giocatori a rischio per squadra
- Score breakdown (stagionale, arbitro, H2H, falli)
- Statistiche arbitro e squadre

### Tool di Approfondimento

| Tool | Quando Usarlo |
|------|---------------|
| `get_player_season_stats` | Dettaglio su singolo giocatore |
| `get_referee_player_cards` | Storico completo arbitro (se noto) |
| `get_head_to_head_cards` | Approfondimento H2H specifico |
| `get_match_statistics` | Statistiche falli squadra |
| `get_team_players` | Rosa completa squadra |

## Fase 2: Contesto Web

### Ricerche Contestuali

| Ricerca | Query Esempio | Impatto |
|---------|---------------|---------|
| Assenze | `"[Squadra] infortunati squalificati [mese anno]"` | Escludere giocatori |
| Classifica | `"classifica [competizione] [stagione]"` | Importanza partita |
| Forma | `"[Squadra] ultime 5 partite risultati"` | Squadra nervosa |
| Rivalità | `"[Squadra1] [Squadra2] storia derby rivalità"` | Partite calde |
| Tattica | `"[Squadra] stile gioco [allenatore]"` | Aggressività |

### Fattori Moltiplicativi

Da applicare nel ragionamento (non matematicamente nello score):

| Fattore | Impatto | Esempi |
|---------|---------|--------|
| Derby storico | +20% rischio | Clásico, Derby d'Italia, Derby della Madonnina |
| Partita decisiva | +15% rischio | Scudetto, salvezza, qualificazione CL |
| Squadra in crisi | +10% rischio | 4+ partite senza vittoria |
| Arbitro severo | +10% rischio | Media >5 gialli/partita |

## Fase 3: Output

### Template Obbligatorio

```markdown
## 🟨 Analisi: [Squadra Casa] vs [Squadra Trasferta]
**Data:** DD/MM/YYYY | **Competizione:** Nome | **Giornata:** N

### 📋 Info Partita
- **Arbitro:** Nome (media X.X gialli/partita) | Non ancora designato
- **Formazioni:** ✅ Confermate | ⚠️ Probabili | ❌ Non disponibili
- **Contesto:** [Derby/Rivalità, posizione classifica, posta in gioco]

### 📊 Ragionamento

[ANALISI DISCORSIVA - Non elencare numeri, INTERPRETA i dati]

Spiega:
- Perché questi giocatori sono a rischio
- Il loro ruolo in campo e come influisce
- Il rapporto con l'arbitro designato
- Lo storico contro questo avversario
- Il contesto della partita (derby? pressione?)

Esempio di tono:
"Tchouaméni è il candidato principale perché gioca come schermo
davanti alla difesa: è lui che deve fermare le ripartenze avversarie,
e questo lo porta a commettere molti falli tattici. Con Mateu Lahoz
ha un rapporto complicato: è stato ammonito in 4 delle 7 partite
dirette dall'aragonese..."

### 🎯 Top 5 Rischio Cartellino

| # | Giocatore | Ruolo | Score | Stagione | Falli | Arbitro | H2H |
|---|-----------|-------|-------|----------|-------|---------|-----|
| 1 | Nome | POS | XX.X | XX.X | XX.X | XX.X | XX.X |
| 2 | Nome | POS | XX.X | XX.X | XX.X | XX.X | XX.X |
| 3 | Nome | POS | XX.X | XX.X | XX.X | XX.X | XX.X |
| 4 | Nome | POS | XX.X | XX.X | XX.X | XX.X | XX.X |
| 5 | Nome | POS | XX.X | XX.X | XX.X | XX.X | XX.X |

### ⚠️ Note
- [Fonte formazioni e data pubblicazione]
- [Assenze rilevanti con fonte]
- [Altre informazioni utili]

### 📖 Glossario

| Sigla | Significato |
|-------|-------------|
| **Score** | Punteggio 0-100: probabilità cartellino. Più alto = più rischio |
| **Stagione** | Contributo da gialli/90 minuti in stagione |
| **Falli** | Contributo da propensione al fallo (individuale + squadra) |
| **Arbitro** | Contributo da storico con arbitro designato |
| **H2H** | Head-to-Head: storico cartellini contro questa squadra |
| **MED/DIF/ATT/POR** | Centrocampista, Difensore, Attaccante, Portiere |
```

## Tipi di Richiesta

### Tipo A: Partita Singola

**Utente:** "Analizza Roma vs Milan di domenica"

**Flusso:**
1. WebSearch formazioni Roma Milan
2. WebSearch arbitro Roma Milan Serie A
3. `analyze_match_risk("Roma", "Milan", "arbitro")`
4. WebSearch assenze Roma Milan
5. WebSearch classifica Serie A
6. Output con template

### Tipo B: Giornata Intera

**Utente:** "Analizzami le partite di Serie A di oggi"

**Flusso:**
1. `get_matches_by_date(competition="SA")`
2. Per ogni partita: flusso completo Tipo A
3. Riepilogo con top candidati globali

### Tipo C: Giocatore Specifico

**Utente:** "Barella rischia il giallo contro il Napoli?"

**Flusso:**
1. WebSearch formazioni Inter Napoli (conferma titolarità)
2. WebSearch arbitro Inter Napoli
3. `get_player_season_stats("Barella")`
4. `get_head_to_head_cards("Barella", "Inter", "Napoli")`
5. `get_referee_player_cards("arbitro", "Inter", "Napoli")`
6. Analisi focalizzata su Barella

## Regole Fondamentali

1. **SEMPRE cercare formazioni e arbitro** - Anche se l'utente non lo chiede
2. **Non inventare dati** - Usa solo ciò che restituiscono tool e ricerche
3. **Cita le fonti** - Indica da dove hai preso formazioni, assenze
4. **Nessun consiglio quote** - Non suggerire importi o strategie scommessa
5. **Ammetti incertezza** - Se i dati sono scarsi, dillo chiaramente
6. **Ragiona, non elencare** - L'analisi discorsiva è più importante della tabella
