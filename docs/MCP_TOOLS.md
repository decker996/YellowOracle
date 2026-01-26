# MCP Tools Reference

Il server MCP (`mcp_server.py`) espone 10 tool per l'analisi del rischio cartellini.

## Tool Principale

### analyze_match_risk ⭐

**Scopo:** Analisi completa del rischio cartellino per una partita.

| Parametro | Tipo | Obbligatorio | Default | Descrizione |
|-----------|------|--------------|---------|-------------|
| home_team | string | ✅ | - | Nome squadra di casa |
| away_team | string | ✅ | - | Nome squadra in trasferta |
| referee | string | ❌ | null | Nome arbitro (se designato) |

**Output:**
```json
{
  "match": {
    "home_team": "Inter",
    "away_team": "Milan",
    "referee": "Orsato"
  },
  "referee_stats": {
    "total_matches": 150,
    "avg_yellows_per_match": 4.2
  },
  "team_stats": {
    "home": { "avg_fouls_per_match": 12.5, "foul_to_card_pct": 28.3 },
    "away": { "avg_fouls_per_match": 11.8, "foul_to_card_pct": 25.1 }
  },
  "home_team_top5": [
    {
      "name": "Nicolò Barella",
      "position": "Midfield",
      "combined_score": 72.5,
      "breakdown": {
        "seasonal": 45.2,
        "referee": 33.3,
        "h2h": 50.0,
        "fouls": 38.5
      }
    }
  ],
  "away_team_top5": [...],
  "overall_top5": [...]
}
```

**Note:**
- I pesi cambiano se l'arbitro è specificato o meno (vedi [SCORING.md](SCORING.md))
- Query H2H eseguite solo per giocatori con score stagionale > 25
- Ricerca fuzzy sui nomi squadra

---

## Tool Partite

### get_matches_by_date

**Scopo:** Recupera partite per data e competizione.

| Parametro | Tipo | Default | Descrizione |
|-----------|------|---------|-------------|
| competition | string | "SA" | Codice competizione |
| date | string | null | Data formato YYYY-MM-DD |
| days_ahead | int | 0 | Giorni da oggi (se date è null) |

**Output:**
```json
[
  {
    "home_team": "Inter",
    "away_team": "Milan",
    "kickoff": "2026-01-26T20:45:00",
    "stadium": "San Siro",
    "referee": "Orsato",
    "matchday": 21,
    "status": "SCHEDULED"
  }
]
```

---

## Tool Statistiche Giocatore

### get_player_season_stats

**Scopo:** Statistiche cartellini per competizione specifica.

| Parametro | Tipo | Default | Descrizione |
|-----------|------|---------|-------------|
| player_name | string | - | Nome giocatore (ricerca fuzzy) |
| season | string | null | Stagione (es. "2025-2026") |
| competition | string | null | Codice competizione |

**Output:**
```json
[
  {
    "player_name": "Nicolò Barella",
    "team_name": "Inter",
    "competition": "SA",
    "season": "2025-2026",
    "matches_played": 18,
    "yellow_cards": 6,
    "red_cards": 0,
    "minutes_played": 1520,
    "yellows_per_90": 0.355
  }
]
```

### get_player_season_stats_total

**Scopo:** Statistiche aggregate (tutte le competizioni).

| Parametro | Tipo | Default | Descrizione |
|-----------|------|---------|-------------|
| player_name | string | - | Nome giocatore (ricerca fuzzy) |
| season | string | null | Stagione |

**Output:**
```json
{
  "player_name": "Nicolò Barella",
  "team_name": "Inter",
  "season": "2025-2026",
  "total_matches": 24,
  "total_yellows": 8,
  "total_reds": 0,
  "total_minutes": 2040,
  "yellows_per_90": 0.353,
  "competitions": ["SA", "CL"]
}
```

---

## Tool Storico

### get_referee_player_cards

**Scopo:** Storico ammonizioni di un arbitro verso giocatori di due squadre.

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| referee_name | string | Nome arbitro |
| team1_name | string | Prima squadra |
| team2_name | string | Seconda squadra |

**Output:**
```json
[
  {
    "player_name": "Nicolò Barella",
    "team_name": "Inter",
    "times_booked": 3,
    "matches_with_referee": 8,
    "booking_percentage": 37.5,
    "booking_details": [
      {"match": "Inter vs Juventus", "date": "2025-10-15", "minute": 67}
    ]
  }
]
```

### get_head_to_head_cards

**Scopo:** Cartellini di un giocatore negli scontri diretti tra due squadre.

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| player_name | string | Nome giocatore |
| team1_name | string | Prima squadra |
| team2_name | string | Seconda squadra |

**Output:**
```json
{
  "player_name": "Nicolò Barella",
  "team1": "Inter",
  "team2": "Milan",
  "total_h2h_matches": 12,
  "total_yellows": 5,
  "total_reds": 0,
  "card_percentage": 41.7,
  "match_details": [
    {"date": "2025-09-22", "result": "1-2", "yellow": true, "minute": 34}
  ]
}
```

---

## Tool Supporto

### get_teams

**Scopo:** Lista di tutte le squadre nel database.

**Parametri:** Nessuno

**Output:**
```json
[
  {"name": "Inter", "short_name": "Inter", "tla": "INT"},
  {"name": "AC Milan", "short_name": "Milan", "tla": "MIL"}
]
```

### get_referees

**Scopo:** Lista arbitri con statistiche di severità.

**Parametri:** Nessuno

**Output:** (ordinato per avg_yellows_per_match decrescente)
```json
[
  {
    "name": "Daniele Orsato",
    "nationality": "Italy",
    "total_matches": 150,
    "total_yellows": 630,
    "total_reds": 45,
    "avg_yellows_per_match": 4.2
  }
]
```

### get_team_players

**Scopo:** Rosa di una squadra con statistiche cartellini.

| Parametro | Tipo | Default | Descrizione |
|-----------|------|---------|-------------|
| team_name | string | - | Nome squadra |
| season | string | "2025-2026" | Stagione |

**Output:**
```json
[
  {
    "name": "Nicolò Barella",
    "position": "Midfield",
    "matches_played": 18,
    "yellow_cards": 6,
    "red_cards": 0,
    "yellows_per_90": 0.355
  }
]
```

### get_match_statistics

**Scopo:** Statistiche partite (falli, possesso, tiri).

| Parametro | Tipo | Default | Descrizione |
|-----------|------|---------|-------------|
| team_name | string | null | Filtro squadra (opzionale) |
| season | string | "2025-2026" | Stagione |
| limit | int | 10 | Numero max partite |

**Output (con team_name):**
```json
{
  "team": "Inter",
  "season": "2025-2026",
  "averages": {
    "fouls_per_match": 12.5,
    "yellows_per_match": 2.1,
    "possession_avg": 58.3
  },
  "recent_matches": [
    {
      "opponent": "Milan",
      "date": "2026-01-15",
      "fouls": 14,
      "yellows": 3,
      "possession": 62
    }
  ]
}
```

---

## Note Tecniche

### Ricerca Fuzzy
Tutti i tool che accettano nomi (giocatori, squadre, arbitri) supportano ricerca parziale case-insensitive:
- `"Barella"` → trova `"Nicolò Barella"`
- `"inter"` → trova `"FC Internazionale Milano"`

### Formato Output
- Tutti i tool restituiscono JSON
- Errori: `{"error": "messaggio di errore"}`
- Liste vuote: `[]`

### Limiti
- Dati disponibili solo per competizioni sincronizzate
- Statistiche falli richiedono Statistics Add-On attivo
- H2H limitato alle partite presenti nel database
