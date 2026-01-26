# Design: Sync Completo con Verifiche

**Data:** 2026-01-26
**Obiettivo:** Garantire che `sync_football_data.py` popoli TUTTI i campi del database

## Problema

Lo script attuale non popola:
- `player_season_stats` (intera tabella vuota)
- `referees` campi aggregati (total_matches, avg_yellows_per_match, etc.)
- `lineups.minutes_played` (sempre NULL)
- Sostituzioni in `match_events`

## Soluzione

### 1. Nuova funzione: `sync_player_stats()`

Chiama `/persons/{id}/matches` per ogni giocatore e popola `player_season_stats`.

```python
def sync_player_stats(supabase: Client, player_map: dict, competition_code: str, season: str):
    """Sincronizza statistiche aggregate giocatori da API Person."""

    api_season = season.split("-")[0]

    for external_id, internal_id in player_map.items():
        data = api_request(f"/persons/{external_id}/matches?competitions={competition_code}&season={api_season}&limit=100")

        if not data.get("aggregations"):
            continue

        agg = data["aggregations"]

        # Trova team_id corrente del giocatore
        player = supabase.table("players").select("current_team_id").eq("id", internal_id).execute()
        team_id = player.data[0]["current_team_id"] if player.data else None

        supabase.table("player_season_stats").upsert({
            "player_id": internal_id,
            "team_id": team_id,
            "season": season,
            "matches_played": agg.get("matchesOnPitch", 0),
            "matches_started": agg.get("startingXI", 0),
            "minutes_played": agg.get("minutesPlayed", 0),
            "goals": agg.get("goals", 0),
            "assists": agg.get("assists", 0),
            "yellow_cards": agg.get("yellowCards", 0),
            "red_cards": agg.get("redCards", 0) + agg.get("yellowRedCards", 0),
        }, on_conflict="player_id,season").execute()
```

**Chiamate API:** ~500 per competizione (una per giocatore)

### 2. Nuova funzione: `update_referee_stats()`

Calcola statistiche aggregate arbitri dalle partite nel database.

```python
def update_referee_stats(supabase: Client, season: str):
    """Aggiorna statistiche aggregate arbitri da partite."""

    # Query per calcolare aggregati
    query = """
    SELECT
        r.id,
        COUNT(DISTINCT m.id) as total_matches,
        COALESCE(SUM(ms.yellow_cards), 0) as total_yellows,
        COALESCE(SUM(ms.red_cards), 0) as total_reds,
        COALESCE(AVG(ms.fouls_committed), 0) as avg_fouls
    FROM referees r
    JOIN matches m ON m.referee_id = r.id
    LEFT JOIN match_statistics ms ON ms.match_id = m.id
    WHERE m.status = 'FINISHED'
    GROUP BY r.id
    """

    # Esegui via RPC o itera sui risultati
    # Aggiorna ogni arbitro con i valori calcolati
```

**Chiamate API:** 0 (calcolo interno)

### 3. Nuova funzione: `sync_substitutions()`

Estrae sostituzioni dal match detail e aggiorna `lineups.minutes_played`.

```python
def sync_substitutions(supabase: Client, match_data: dict, match_internal_id: str, player_map: dict):
    """Sincronizza sostituzioni e calcola minuti giocati."""

    if not match_data.get("substitutions"):
        return

    for sub in match_data["substitutions"]:
        minute = sub.get("minute", 90)
        player_out_id = player_map.get(sub.get("playerOut", {}).get("id"))
        player_in_id = player_map.get(sub.get("playerIn", {}).get("id"))

        if player_out_id:
            # Aggiorna minuti giocatore uscito
            supabase.table("lineups").update({
                "subbed_out_minute": minute,
                "minutes_played": minute
            }).eq("match_id", match_internal_id).eq("player_id", player_out_id).execute()

        if player_in_id:
            # Aggiorna minuti giocatore entrato
            supabase.table("lineups").update({
                "subbed_in_minute": minute,
                "minutes_played": 90 - minute  # Approssimazione
            }).eq("match_id", match_internal_id).eq("player_id", player_in_id).execute()
```

**Chiamate API:** 0 (dati già nel match detail)

### 4. Nuova funzione: `verify_sync()`

Genera report finale con conteggi e warning.

```python
def verify_sync(supabase: Client, competition_code: str, season: str) -> dict:
    """Verifica completezza sync e genera report."""

    report = {
        "competition": competition_code,
        "season": season,
        "tables": {},
        "warnings": [],
        "status": "OK"
    }

    # Conta record per tabella
    tables = ["competitions", "teams", "players", "referees", "matches",
              "match_events", "lineups", "match_statistics", "player_season_stats"]

    for table in tables:
        count = supabase.table(table).select("id", count="exact").execute()
        report["tables"][table] = count.count

    # Verifica campi critici
    # 1. player_season_stats deve avere record
    if report["tables"]["player_season_stats"] == 0:
        report["warnings"].append("CRITICAL: player_season_stats is empty!")
        report["status"] = "WARNING"

    # 2. Arbitri devono avere statistiche
    refs_no_stats = supabase.table("referees").select("id").eq("total_matches", 0).execute()
    if refs_no_stats.data:
        report["warnings"].append(f"WARNING: {len(refs_no_stats.data)} referees with no stats")

    # 3. Match FINISHED devono avere eventi
    # ... altre verifiche

    return report
```

### 5. Flusso Aggiornato

```
sync_season():
  1. sync_competition()
  2. sync_teams()
  3. sync_players()
  4. fetch matches → sync_referees()
  5. sync_matches()
  6. sync_match_details()  ← include sync_substitutions()
  7. sync_player_stats()   ← NUOVO
  8. update_referee_stats() ← NUOVO
  9. verify_sync()          ← NUOVO
```

### 6. Stima Tempi

| Competizione | Chiamate API | Tempo stimato |
|--------------|--------------|---------------|
| Esistenti | ~400 | ~15 min |
| Player stats | ~500 | ~17 min |
| **Totale** | ~900 | **~32 min** |

Per 7 competizioni: ~4 ore (entro timeout 6h)

### 7. Output GitHub Actions

Il report di `verify_sync()` viene scritto nel `$GITHUB_STEP_SUMMARY`:

```markdown
### Sync Report: SA 2025-2026

| Tabella | Record |
|---------|--------|
| teams | 20 |
| players | 520 |
| matches | 380 |
| match_events | 2840 |
| player_season_stats | 520 |

**Warnings:**
- None

**Status:** OK
```

## File da Modificare

1. `scripts/sync_football_data.py` - Aggiungere funzioni
2. `.github/workflows/sync.yml` - Formattare output report

## Rischi

1. **Rate limit API** - 500 chiamate extra potrebbero causare 429. Mitigazione: delay 2.5s già presente
2. **Timeout workflow** - 4h per 7 competizioni, margine 2h OK
3. **Dati mancanti API** - Alcuni giocatori potrebbero non avere aggregations. Mitigazione: skip con warning
