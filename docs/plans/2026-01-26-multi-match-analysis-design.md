# Multi-Match Analysis Feature

**Data:** 2026-01-26
**Stato:** Approvato

## Obiettivo

Permettere all'utente di analizzare tutte le partite di una giornata e ricevere i 3 giocatori più a rischio cartellino per ogni partita, ordinati per probabilità.

## Casi d'uso

### Primario: Query per data
```
USER: "Analizza le partite di Serie A del 2 febbraio"
CLAUDE: [Recupera partite via API, analizza, presenta top 3 per partita]
```

### Alternativo: Screenshot
```
USER: [invia screenshot sito scommesse]
USER: "Analizza queste partite"
CLAUDE: [Legge immagine con Vision, estrae partite, analizza]
```

### Manuale: Input testuale
```
USER: "Analizza Napoli-Inter"
CLAUDE: [Analizza singola partita]
```

## Output Format

Per ogni partita:

```
## Napoli vs Inter (02/02 ore 18:00)
Arbitro: Mariani (media 4.2 gialli/partita)

🟨 TOP 3 RISCHIO CARTELLINO:

1. BARELLA (Inter) - Score: 72/100
   • Stagione: 6 gialli in 18 partite (0.41/90min)
   • Con Mariani: 2 gialli in 3 partite (67%)
   • H2H vs Napoli: 1 giallo in 4 partite
   → Centrocampista aggressivo, Mariani lo ammonisce spesso

2. ANGUISSA (Napoli) - Score: 68/100
   • Stagione: 5 gialli in 17 partite (0.38/90min)
   • Con Mariani: 1 giallo in 2 partite (50%)
   • H2H vs Inter: 2 gialli in 3 partite
   → Alto tasso H2H contro l'Inter

3. DUMFRIES (Inter) - Score: 61/100
   ...
```

## Formula Risk Score

```
RISK_SCORE = (seasonal_score * 0.40) + (referee_score * 0.35) + (h2h_score * 0.25)
```

### Componenti

**Seasonal Score (40%)**
```python
seasonal_score = min(yellows_per_90 * 100, 100)
# Esempio: 0.45 gialli/90min → 45 punti
```

**Referee Score (35%)**
```python
referee_score = (times_booked / matches_with_referee) * 100
# Esempio: 2 gialli in 3 partite → 67 punti
# Nessuno storico → usa media arbitro * 0.5
```

**H2H Score (25%)**
```python
h2h_score = (yellows_in_h2h / h2h_matches_played) * 100
# Esempio: 1 giallo in 4 partite → 25 punti
# Nessuno storico → 0 punti (neutro)
```

### Gestione dati mancanti

| Dato mancante | Comportamento |
|---------------|---------------|
| Arbitro non designato | Analisi parziale: 40% seasonal + 25% H2H, nota "arbitro non designato" |
| Nessuno storico H2H | H2H score = 0 |
| Giocatore nuovo | Solo dati stagionali disponibili |

## Selezione Giocatori

1. **Primario:** Web search per formazioni probabili ("Napoli Inter probabili formazioni")
2. **Fallback:** Top 10 giocatori per minuti giocati dalla nostra DB

## Implementazione

### Nuovo MCP Tool: `get_matches_by_date`

```python
@mcp.tool()
def get_matches_by_date(
    competition: str = "SA",
    date: str = None,
    days_ahead: int = 0
) -> str:
    """
    Recupera le partite di una competizione per una data specifica.

    Args:
        competition: Codice competizione (SA, PL, BL1, PD, FL1, CL, EL)
        date: Data in formato "YYYY-MM-DD" o None per oggi
        days_ahead: Alternativa - prossimi N giorni da oggi

    Returns:
        Lista partite con: squadre, orario, arbitro, stadio
    """
```

**Output:**
```json
{
  "competition": "Serie A",
  "date": "2026-02-02",
  "matches": [
    {
      "home_team": "Napoli",
      "away_team": "Inter",
      "kickoff": "18:00",
      "stadium": "Diego Armando Maradona",
      "referee": "Mariani",
      "matchday": 22
    }
  ]
}
```

**API Call:** `GET /competitions/SA/matches?dateFrom=2026-02-02&dateTo=2026-02-02`

### Modifica: `analyze_match_risk`

Aggiornare la funzione esistente per:

1. Recuperare dati referee history per ogni giocatore candidato
2. Recuperare dati H2H per i top 5-6 candidati
3. Calcolare score combinato con formula pesata (40/35/25)
4. Restituire top 3 invece di top 5
5. Includere breakdown dello score nell'output

### File da modificare

| File | Azione | Stima |
|------|--------|-------|
| `mcp_server.py` | Nuovo tool `get_matches_by_date` | ~40 righe |
| `mcp_server.py` | Modifica `analyze_match_risk` | ~60 righe |

### Cosa NON serve

- ❌ Nuove tabelle database (dati già presenti)
- ❌ Implementare web search (Claude lo fa nativamente)
- ❌ Implementare lettura screenshot (Claude Vision già funziona)

## Flusso Claude

```
1. RECUPERA PARTITE
   → get_matches_by_date(competition="SA", date="2026-02-02")

2. PER OGNI PARTITA:
   a. WEB SEARCH formazioni probabili
      → "Napoli Inter probabili formazioni 2 febbraio 2026"

   b. FALLBACK se web search fallisce
      → get_team_players(team) → top 10 per minuti

   c. CALCOLA SCORE per ogni giocatore titolare
      → Dati già presenti in analyze_match_risk migliorato

   d. SELEZIONA TOP 3 per risk_score

3. PRESENTA OUTPUT formattato con breakdown score
```

## Decisioni di Design

| Aspetto | Decisione | Motivazione |
|---------|-----------|-------------|
| Input primario | Query per data | Sfrutta API già pagata |
| Input alternativi | Screenshot + manuale | Flessibilità |
| Output | Dettagliato con breakdown | Utile per scommesse |
| Pesi score | 40/35/25 | Bilanciato, arbitro importante |
| Top N | 3 giocatori | Sufficiente per scommesse |
| Arbitro mancante | Analisi parziale | Meglio di niente |
