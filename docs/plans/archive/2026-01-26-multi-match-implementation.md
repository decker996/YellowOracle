# Multi-Match Analysis Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add ability to fetch matches by date and calculate weighted risk scores for yellow card predictions.

**Architecture:** Extend existing MCP server with new `get_matches_by_date` tool and enhance `analyze_match_risk` to use weighted formula (40% seasonal + 35% referee + 25% H2H).

**Tech Stack:** Python 3.13, FastMCP, Supabase, football-data.org API v4

---

## Task 1: Add `get_matches_by_date` Tool

**Files:**
- Modify: `mcp_server.py:28` (add new tool after imports)

**Step 1: Add the new tool function**

Add this code after line 26 (after `get_supabase()` function):

```python
@mcp.tool()
def get_matches_by_date(competition: str = "SA", date: str = None, days_ahead: int = 0) -> str:
    """
    Recupera le partite di una competizione per una data specifica.
    Utile per analizzare tutte le partite di una giornata.

    Args:
        competition: Codice competizione (SA, PL, BL1, PD, FL1, CL, EL). Default: SA (Serie A)
        date: Data in formato "YYYY-MM-DD". Se None, usa oggi + days_ahead
        days_ahead: Giorni da oggi (usato se date è None). Default: 0 (oggi)

    Returns:
        Lista partite con: squadre, orario, arbitro (se designato), stadio
    """
    import requests
    from datetime import datetime, timedelta

    FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")
    if not FOOTBALL_API_KEY:
        return "Errore: FOOTBALL_API_KEY non configurata"

    # Calcola la data
    if date:
        target_date = date
    else:
        target_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    # Mapping competizioni
    comp_names = {
        "SA": "Serie A",
        "PL": "Premier League",
        "BL1": "Bundesliga",
        "PD": "La Liga",
        "FL1": "Ligue 1",
        "CL": "UEFA Champions League",
        "EL": "UEFA Europa League"
    }

    url = f"https://api.football-data.org/v4/competitions/{competition}/matches"
    params = {"dateFrom": target_date, "dateTo": target_date}
    headers = {"X-Auth-Token": FOOTBALL_API_KEY}

    try:
        response = requests.get(url, params=params, headers=headers)
        if response.status_code != 200:
            return f"Errore API: {response.status_code} - {response.text[:200]}"

        data = response.json()
        matches = data.get("matches", [])

        if not matches:
            return json.dumps({
                "competition": comp_names.get(competition, competition),
                "date": target_date,
                "matches": [],
                "message": "Nessuna partita in questa data"
            }, indent=2)

        result = {
            "competition": comp_names.get(competition, competition),
            "date": target_date,
            "matches": []
        }

        for match in matches:
            # Estrai arbitro principale
            referee_name = None
            for ref in match.get("referees", []):
                if ref.get("type") == "REFEREE":
                    referee_name = ref.get("name")
                    break

            # Formatta orario
            utc_date = match.get("utcDate", "")
            kickoff = utc_date[11:16] if len(utc_date) > 16 else "TBD"

            result["matches"].append({
                "home_team": match.get("homeTeam", {}).get("name"),
                "away_team": match.get("awayTeam", {}).get("name"),
                "kickoff": kickoff,
                "stadium": match.get("venue"),
                "referee": referee_name,
                "matchday": match.get("matchday"),
                "status": match.get("status")
            })

        return json.dumps(result, indent=2, ensure_ascii=False)

    except Exception as e:
        return f"Errore: {str(e)}"
```

**Step 2: Add requests import at top of file**

Check if `requests` is already imported. If not, add at line 9:

```python
import requests
```

**Step 3: Test the new tool manually**

Run the MCP server and test with Claude:
```
"Quali partite ci sono in Serie A oggi?"
"Mostrami le partite di Premier League del 2026-02-01"
```

Expected: JSON with matches list or "Nessuna partita" message.

**Step 4: Commit**

```bash
git add mcp_server.py
git commit -m "feat: add get_matches_by_date MCP tool

Allows fetching matches for a specific competition and date.
Supports all 7 competitions (SA, PL, BL1, PD, FL1, CL, EL).

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Enhance `analyze_match_risk` with Weighted Scoring

**Files:**
- Modify: `mcp_server.py:298-383` (replace `analyze_match_risk` function)

**Step 1: Replace the entire `analyze_match_risk` function**

Replace lines 298-383 with this enhanced version:

```python
@mcp.tool()
def analyze_match_risk(home_team: str, away_team: str, referee: str = None) -> str:
    """
    Analizza il rischio cartellino per una partita specifica.
    Combina 3 fattori con pesi: stagionale (40%), arbitro (35%), H2H (25%).

    Args:
        home_team: Squadra di casa
        away_team: Squadra in trasferta
        referee: Nome arbitro (opzionale)

    Returns:
        Analisi completa con top 3 giocatori a rischio per squadra e breakdown score
    """
    supabase = get_supabase()

    analysis = {
        "match": f"{home_team} vs {away_team}",
        "referee": referee or "Non designato",
        "referee_note": None,
        "home_team_top3": [],
        "away_team_top3": [],
        "overall_top3": []
    }

    # Pesi per il calcolo dello score
    WEIGHT_SEASONAL = 0.40
    WEIGHT_REFEREE = 0.35
    WEIGHT_H2H = 0.25

    try:
        # --- DATI STAGIONALI ---
        home_result = supabase.table("player_season_cards").select("*").ilike(
            "team_name", f"%{home_team}%"
        ).eq("season", "2025-2026").order("yellow_cards", desc=True).limit(15).execute()

        away_result = supabase.table("player_season_cards").select("*").ilike(
            "team_name", f"%{away_team}%"
        ).eq("season", "2025-2026").order("yellow_cards", desc=True).limit(15).execute()

        # --- DATI ARBITRO (se disponibile) ---
        referee_data = {}
        if referee:
            ref_result = supabase.rpc(
                "get_referee_player_cards",
                {
                    "p_referee_name": referee,
                    "p_team1_name": home_team,
                    "p_team2_name": away_team
                }
            ).execute()

            if ref_result.data:
                for r in ref_result.data:
                    player_name = r.get("player_name", "").lower()
                    referee_data[player_name] = {
                        "times_booked": r.get("times_booked", 0),
                        "matches_with_referee": r.get("matches_with_referee", 0),
                        "booking_percentage": float(r.get("booking_percentage", 0))
                    }

        # --- CALCOLO SCORE PER OGNI GIOCATORE ---
        all_players = []

        for team_data, team_name in [(home_result.data or [], home_team), (away_result.data or [], away_team)]:
            for p in team_data:
                player_name = p.get("player_name", "")
                player_name_lower = player_name.lower()

                # 1. SEASONAL SCORE (40%)
                yellows_per_90 = float(p.get("yellows_per_90") or 0)
                seasonal_score = min(yellows_per_90 * 100, 100)

                # 2. REFEREE SCORE (35%)
                referee_score = 0
                referee_info = None
                if referee and player_name_lower in referee_data:
                    ref_info = referee_data[player_name_lower]
                    referee_score = ref_info["booking_percentage"]
                    referee_info = f"{ref_info['times_booked']} in {ref_info['matches_with_referee']} partite"
                elif referee:
                    # Nessuno storico con arbitro: usa 25% della media arbitro come proxy
                    referee_score = 25  # valore conservativo

                # 3. H2H SCORE (25%) - query per i top candidati
                h2h_score = 0
                h2h_info = None
                if seasonal_score > 30:  # Solo per giocatori con storico significativo
                    try:
                        h2h_result = supabase.rpc(
                            "get_head_to_head_cards",
                            {
                                "p_player_name": player_name,
                                "p_team1_name": home_team,
                                "p_team2_name": away_team
                            }
                        ).execute()

                        if h2h_result.data and len(h2h_result.data) > 0:
                            h2h = h2h_result.data[0]
                            h2h_matches = h2h.get("total_h2h_matches", 0)
                            h2h_yellows = h2h.get("total_yellows", 0)
                            if h2h_matches > 0:
                                h2h_score = (h2h_yellows / h2h_matches) * 100
                                h2h_info = f"{h2h_yellows} in {h2h_matches} H2H"
                    except:
                        pass

                # SCORE COMBINATO
                if referee:
                    combined_score = (
                        seasonal_score * WEIGHT_SEASONAL +
                        referee_score * WEIGHT_REFEREE +
                        h2h_score * WEIGHT_H2H
                    )
                else:
                    # Senza arbitro: ricalibra pesi (seasonal 62%, h2h 38%)
                    combined_score = (
                        seasonal_score * 0.62 +
                        h2h_score * 0.38
                    )

                player_data = {
                    "name": player_name,
                    "team": p.get("team_name"),
                    "position": p.get("position"),
                    "combined_score": round(combined_score, 1),
                    "breakdown": {
                        "seasonal": {
                            "score": round(seasonal_score, 1),
                            "yellows": p.get("yellow_cards", 0),
                            "matches": p.get("matches_played", 0),
                            "per_90": yellows_per_90
                        },
                        "referee": {
                            "score": round(referee_score, 1),
                            "detail": referee_info
                        } if referee else None,
                        "h2h": {
                            "score": round(h2h_score, 1),
                            "detail": h2h_info
                        }
                    }
                }
                all_players.append(player_data)

        # Ordina per score combinato
        all_players.sort(key=lambda x: x["combined_score"], reverse=True)

        # Separa per squadra e prendi top 3
        home_players = [p for p in all_players if home_team.lower() in p["team"].lower()]
        away_players = [p for p in all_players if away_team.lower() in p["team"].lower()]

        analysis["home_team_top3"] = home_players[:3]
        analysis["away_team_top3"] = away_players[:3]
        analysis["overall_top3"] = all_players[:3]

        if not referee:
            analysis["referee_note"] = "Arbitro non designato - analisi basata su dati stagionali e H2H"

        return json.dumps(analysis, indent=2, default=str, ensure_ascii=False)

    except Exception as e:
        return f"Errore nell'analisi: {str(e)}"
```

**Step 2: Test the enhanced function**

Test with Claude:
```
"Analizza il rischio cartellini per Napoli vs Inter con arbitro Mariani"
"Analizza Roma vs Milan" (senza arbitro)
```

Expected output structure:
```json
{
  "match": "Napoli vs Inter",
  "referee": "Mariani",
  "home_team_top3": [...],
  "away_team_top3": [...],
  "overall_top3": [
    {
      "name": "Barella",
      "team": "Inter",
      "combined_score": 72.5,
      "breakdown": {
        "seasonal": {"score": 45.0, "yellows": 6, "matches": 18, "per_90": 0.41},
        "referee": {"score": 67.0, "detail": "2 in 3 partite"},
        "h2h": {"score": 25.0, "detail": "1 in 4 H2H"}
      }
    }
  ]
}
```

**Step 3: Commit**

```bash
git add mcp_server.py
git commit -m "feat: enhance analyze_match_risk with weighted scoring

- Weighted formula: 40% seasonal + 35% referee + 25% H2H
- Returns top 3 players per team with score breakdown
- Handles missing referee (recalibrates weights)
- Only queries H2H for high-potential candidates (optimization)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Final Integration Test

**Step 1: Start MCP server**

```bash
cd /home/salvatore/Scrivania/soccer
python mcp_server.py
```

**Step 2: Test full workflow with Claude**

Test query:
```
"Analizza le partite di Serie A del 2026-02-02"
```

Expected behavior:
1. Claude calls `get_matches_by_date(competition="SA", date="2026-02-02")`
2. For each match, Claude calls `analyze_match_risk(home, away, referee)`
3. Claude presents top 3 per match with breakdown

**Step 3: Test edge cases**

```
"Partite di Champions League di domani"
"Analizza Juventus vs Fiorentina" (no referee)
"Partite Serie A del 2020-01-01" (data passata, poche/nessuna partita)
```

**Step 4: Final commit (if any fixes needed)**

```bash
git add -A
git commit -m "fix: address integration test findings

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Summary

| Task | Description | Lines Changed |
|------|-------------|---------------|
| 1 | `get_matches_by_date` tool | +80 lines |
| 2 | Enhanced `analyze_match_risk` | ~85 lines replaced |
| 3 | Integration testing | 0 lines |

**Total:** ~165 lines of code changes in `mcp_server.py`
