"""
YellowOracle MCP Server
Espone le funzioni di analisi cartellini a Claude

Avvio: python mcp_server.py
"""

import os
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from supabase import create_client, Client

# Carica variabili d'ambiente
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Inizializza MCP server
mcp = FastMCP("YellowOracle")

def get_supabase() -> Client:
    """Crea connessione a Supabase."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)


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
    FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")
    if not FOOTBALL_API_KEY:
        return "Errore: FOOTBALL_API_KEY non configurata"

    # Validazione competizione
    VALID_COMPETITIONS = {"SA", "PL", "BL1", "PD", "FL1", "CL", "EL"}
    if competition not in VALID_COMPETITIONS:
        return f"Errore: Competizione '{competition}' non valida. Usa: {', '.join(sorted(VALID_COMPETITIONS))}"

    # Calcola e valida la data
    if date:
        try:
            datetime.strptime(date, "%Y-%m-%d")
            target_date = date
        except ValueError:
            return "Errore: Formato data non valido. Usa YYYY-MM-DD (es: 2026-02-01)"
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


@mcp.tool()
def get_player_season_stats(player_name: str, season: str = None, competition: str = None) -> str:
    """
    Ottiene le statistiche cartellini di un giocatore per stagione e competizione.
    I dati sono separati per competizione (es: Serie A vs Champions League).

    Args:
        player_name: Nome del giocatore (ricerca parziale supportata)
        season: Stagione specifica (es: "2025-2026") o None per tutte
        competition: Codice competizione (PD, SA, BL1, PL, FL1, CL, EL) o None per tutte

    Returns:
        Statistiche cartellini per competizione: gialli, rossi, partite, media per 90 min
    """
    supabase = get_supabase()

    try:
        result = supabase.rpc(
            "get_player_season_stats",
            {"p_player_name": player_name, "p_season": season, "p_competition": competition}
        ).execute()

        if result.data:
            return json.dumps(result.data, indent=2, default=str)
        else:
            return f"Nessun dato trovato per il giocatore '{player_name}'"
    except Exception as e:
        return f"Errore: {str(e)}"


@mcp.tool()
def get_player_season_stats_total(player_name: str, season: str = None) -> str:
    """
    Ottiene le statistiche cartellini TOTALI di un giocatore (tutte le competizioni aggregate).
    Utile per avere una visione complessiva del comportamento del giocatore.

    Args:
        player_name: Nome del giocatore (ricerca parziale supportata)
        season: Stagione specifica (es: "2025-2026") o None per tutte

    Returns:
        Statistiche totali: gialli, rossi, partite, media per 90 min, lista competizioni
    """
    supabase = get_supabase()

    try:
        result = supabase.rpc(
            "get_player_season_stats_total",
            {"p_player_name": player_name, "p_season": season}
        ).execute()

        if result.data:
            return json.dumps(result.data, indent=2, default=str)
        else:
            return f"Nessun dato trovato per il giocatore '{player_name}'"
    except Exception as e:
        return f"Errore: {str(e)}"


@mcp.tool()
def get_referee_player_cards(referee_name: str, team1_name: str, team2_name: str) -> str:
    """
    Ottiene lo storico delle ammonizioni di un arbitro verso i giocatori di due squadre specifiche.
    Utile per analizzare come un arbitro si comporta con i giocatori di determinate squadre.

    Args:
        referee_name: Nome dell'arbitro
        team1_name: Nome della prima squadra
        team2_name: Nome della seconda squadra

    Returns:
        Lista giocatori con: volte ammoniti, partite con l'arbitro, percentuale ammonizione
    """
    supabase = get_supabase()

    try:
        result = supabase.rpc(
            "get_referee_player_cards",
            {
                "p_referee_name": referee_name,
                "p_team1_name": team1_name,
                "p_team2_name": team2_name
            }
        ).execute()

        if result.data:
            return json.dumps(result.data, indent=2, default=str)
        else:
            return f"Nessuno storico trovato per {referee_name} con {team1_name} e {team2_name}"
    except Exception as e:
        return f"Errore: {str(e)}"


@mcp.tool()
def get_head_to_head_cards(player_name: str, team1_name: str, team2_name: str) -> str:
    """
    Ottiene lo storico cartellini di un giocatore negli scontri diretti tra due squadre.
    Utile per vedere se un giocatore tende a prendere cartellini in partite specifiche.

    Args:
        player_name: Nome del giocatore
        team1_name: Nome della prima squadra
        team2_name: Nome della seconda squadra

    Returns:
        Storico: partite giocate, gialli totali, rossi, dettaglio per partita
    """
    supabase = get_supabase()

    try:
        result = supabase.rpc(
            "get_head_to_head_cards",
            {
                "p_player_name": player_name,
                "p_team1_name": team1_name,
                "p_team2_name": team2_name
            }
        ).execute()

        if result.data:
            return json.dumps(result.data, indent=2, default=str)
        else:
            return f"Nessuno storico trovato per {player_name} in {team1_name} vs {team2_name}"
    except Exception as e:
        return f"Errore: {str(e)}"


@mcp.tool()
def get_teams() -> str:
    """
    Ottiene la lista delle squadre nel database.

    Returns:
        Lista squadre con nome e abbreviazione
    """
    supabase = get_supabase()

    try:
        result = supabase.table("teams").select("name, short_name, tla").order("name").execute()
        return json.dumps(result.data, indent=2)
    except Exception as e:
        return f"Errore: {str(e)}"


@mcp.tool()
def get_referees() -> str:
    """
    Ottiene la lista degli arbitri nel database con le loro statistiche.

    Returns:
        Lista arbitri con: partite totali, gialli totali, media gialli per partita
    """
    supabase = get_supabase()

    try:
        result = supabase.table("referees").select(
            "name, nationality, total_matches, total_yellows, total_reds, avg_yellows_per_match"
        ).gt("total_matches", 0).order("avg_yellows_per_match", desc=True).execute()
        return json.dumps(result.data, indent=2)
    except Exception as e:
        return f"Errore: {str(e)}"


@mcp.tool()
def get_team_players(team_name: str, season: str = "2025-2026") -> str:
    """
    Ottiene i giocatori di una squadra con le loro statistiche cartellini nella stagione.

    Args:
        team_name: Nome della squadra
        season: Stagione (default: 2025-2026)

    Returns:
        Lista giocatori con statistiche cartellini
    """
    supabase = get_supabase()

    try:
        result = supabase.table("player_season_cards").select("*").eq(
            "team_name", team_name
        ).eq("season", season).order("yellow_cards", desc=True).execute()

        if result.data:
            return json.dumps(result.data, indent=2, default=str)
        else:
            return f"Nessun dato trovato per {team_name} nella stagione {season}"
    except Exception as e:
        return f"Errore: {str(e)}"


@mcp.tool()
def get_match_statistics(team_name: str = None, season: str = "2025-2026", limit: int = 10) -> str:
    """
    Ottiene le statistiche delle partite (falli, possesso, tiri) per una squadra.
    Dati dal Statistics Add-On di football-data.org.

    Args:
        team_name: Nome della squadra (opzionale, se None mostra tutte)
        season: Stagione (default: 2025-2026)
        limit: Numero massimo di partite da restituire (default: 10)

    Returns:
        Statistiche partita: falli, possesso palla, tiri, corner, etc.
    """
    supabase = get_supabase()

    try:
        query = supabase.table("match_statistics").select(
            "*, matches!inner(match_date, season, home_team_id, away_team_id, "
            "home_team:teams!matches_home_team_id_fkey(name), "
            "away_team:teams!matches_away_team_id_fkey(name))"
        ).eq("matches.season", season).order("matches(match_date)", desc=True).limit(limit)

        # Se specificata una squadra, filtra
        if team_name:
            # Dobbiamo fare due query separate per home e away
            home_result = supabase.table("match_statistics").select(
                "team_id, ball_possession, fouls_committed, fouls_suffered, "
                "total_shots, shots_on_goal, shots_off_goal, corner_kicks, "
                "yellow_cards, red_cards, saves, offsides, "
                "matches!inner(match_date, season, "
                "home_team:teams!matches_home_team_id_fkey(name), "
                "away_team:teams!matches_away_team_id_fkey(name))"
            ).eq("matches.season", season).ilike(
                "matches.home_team.name", f"%{team_name}%"
            ).order("matches(match_date)", desc=True).limit(limit).execute()

            away_result = supabase.table("match_statistics").select(
                "team_id, ball_possession, fouls_committed, fouls_suffered, "
                "total_shots, shots_on_goal, shots_off_goal, corner_kicks, "
                "yellow_cards, red_cards, saves, offsides, "
                "matches!inner(match_date, season, "
                "home_team:teams!matches_home_team_id_fkey(name), "
                "away_team:teams!matches_away_team_id_fkey(name))"
            ).eq("matches.season", season).ilike(
                "matches.away_team.name", f"%{team_name}%"
            ).order("matches(match_date)", desc=True).limit(limit).execute()

            # Combina risultati
            all_data = (home_result.data or []) + (away_result.data or [])

            if all_data:
                # Calcola medie
                total_matches = len(all_data)
                avg_fouls = sum(d.get("fouls_committed", 0) or 0 for d in all_data) / total_matches if total_matches > 0 else 0
                avg_yellows = sum(d.get("yellow_cards", 0) or 0 for d in all_data) / total_matches if total_matches > 0 else 0

                return json.dumps({
                    "team": team_name,
                    "season": season,
                    "matches_analyzed": total_matches,
                    "averages": {
                        "fouls_per_match": round(avg_fouls, 1),
                        "yellows_per_match": round(avg_yellows, 1)
                    },
                    "recent_matches": all_data[:limit]
                }, indent=2, default=str)
            else:
                return f"Nessuna statistica trovata per {team_name} nella stagione {season}"
        else:
            result = query.execute()
            if result.data:
                return json.dumps(result.data, indent=2, default=str)
            else:
                return f"Nessuna statistica trovata per la stagione {season}"

    except Exception as e:
        return f"Errore: {str(e)}"


@mcp.tool()
def analyze_match_risk(home_team: str, away_team: str, referee: str = None) -> str:
    """
    Analizza il rischio cartellino per una partita specifica.
    Combina 4 fattori con pesi: stagionale (35%), arbitro (30%), H2H (15%), falli (20%).
    Senza arbitro: stagionale (45%), H2H (25%), falli (30%).

    Args:
        home_team: Squadra di casa
        away_team: Squadra in trasferta
        referee: Nome arbitro (opzionale)

    Returns:
        Analisi completa con top 5 giocatori a rischio per squadra e breakdown score
    """
    supabase = get_supabase()

    analysis = {
        "match": f"{home_team} vs {away_team}",
        "referee": referee or "Non designato",
        "referee_stats": None,
        "referee_note": None,
        "team_stats": {},
        "home_team_top5": [],
        "away_team_top5": [],
        "overall_top5": []
    }

    # Pesi per il calcolo dello score (con arbitro)
    WEIGHT_SEASONAL = 0.35
    WEIGHT_REFEREE = 0.30
    WEIGHT_H2H = 0.15
    WEIGHT_FOULS = 0.20
    # Pesi senza arbitro
    WEIGHT_SEASONAL_NO_REF = 0.45
    WEIGHT_H2H_NO_REF = 0.25
    WEIGHT_FOULS_NO_REF = 0.30

    DEFAULT_REFEREE_SCORE = 25  # Fallback conservativo quando non c'è storico con arbitro
    H2H_THRESHOLD = 25  # Soglia seasonal_score per query H2H (ottimizzazione)

    try:
        # --- DATI STAGIONALI GIOCATORI ---
        home_result = supabase.table("player_season_cards").select("*").ilike(
            "team_name", f"%{home_team}%"
        ).eq("season", "2025-2026").order("yellow_cards", desc=True).limit(15).execute()

        away_result = supabase.table("player_season_cards").select("*").ilike(
            "team_name", f"%{away_team}%"
        ).eq("season", "2025-2026").order("yellow_cards", desc=True).limit(15).execute()

        # --- STATISTICHE FALLI SQUADRA ---
        team_fouls = {}
        for team in [home_team, away_team]:
            try:
                fouls_result = supabase.rpc(
                    "get_team_fouls_stats",
                    {"p_team_name": team, "p_season": "2025-2026"}
                ).execute()
                if fouls_result.data and len(fouls_result.data) > 0:
                    tf = fouls_result.data[0]
                    team_fouls[team.lower()] = {
                        "avg_fouls_per_match": float(tf.get("avg_fouls_per_match") or 0),
                        "avg_yellows_per_match": float(tf.get("avg_yellows_per_match") or 0),
                        "foul_to_card_pct": float(tf.get("foul_to_card_pct") or 0)
                    }
            except Exception:
                pass  # Team fouls query failed, continue without

        analysis["team_stats"] = team_fouls

        # --- DATI ARBITRO (se disponibile) ---
        referee_data = {}
        if referee:
            # Statistiche generali arbitro
            ref_stats = supabase.table("referees").select(
                "name, total_matches, total_yellows, avg_yellows_per_match"
            ).ilike("name", f"%{referee}%").limit(1).execute()

            if ref_stats.data and len(ref_stats.data) > 0:
                analysis["referee_stats"] = ref_stats.data[0]

            # Storico arbitro-giocatori
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
            # Recupera stats falli squadra
            team_fouls_data = team_fouls.get(team_name.lower(), {})
            team_foul_to_card = team_fouls_data.get("foul_to_card_pct", 0)

            for p in team_data:
                player_name = p.get("player_name", "")
                player_name_lower = player_name.lower()

                # 1. SEASONAL SCORE (35%)
                yellows_per_90 = float(p.get("yellows_per_90") or 0)
                seasonal_score = min(yellows_per_90 * 100, 100)

                # 2. REFEREE SCORE (30%)
                referee_score = 0
                referee_info = None
                if referee and player_name_lower in referee_data:
                    ref_info = referee_data[player_name_lower]
                    referee_score = ref_info["booking_percentage"]
                    referee_info = f"{ref_info['times_booked']} in {ref_info['matches_with_referee']} partite"
                elif referee:
                    # Nessuno storico con arbitro
                    referee_score = DEFAULT_REFEREE_SCORE

                # 3. H2H SCORE (15%) - query per i top candidati
                h2h_score = 0
                h2h_info = None
                if seasonal_score > H2H_THRESHOLD:
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
                    except Exception:
                        pass  # H2H query failed, continue without H2H data

                # 4. FOULS SCORE (20%) - basato su falli squadra e ruolo
                # Calcolo: (foul_to_card% squadra * 0.5) + (yellows_per_90 normalizzato * 0.5)
                # Centrocampisti difensivi e difensori hanno bonus
                position = p.get("position", "")
                position_multiplier = 1.0
                if position in ["Midfield", "Defence"]:
                    position_multiplier = 1.2  # +20% per ruoli più fallosi

                fouls_score = (
                    (team_foul_to_card * 0.5) +  # Quanto la squadra trasforma falli in cartellini
                    (min(yellows_per_90 * 50, 50))  # Propensione individuale
                ) * position_multiplier
                fouls_score = min(fouls_score, 100)

                # SCORE COMBINATO
                if referee:
                    combined_score = (
                        seasonal_score * WEIGHT_SEASONAL +
                        referee_score * WEIGHT_REFEREE +
                        h2h_score * WEIGHT_H2H +
                        fouls_score * WEIGHT_FOULS
                    )
                else:
                    combined_score = (
                        seasonal_score * WEIGHT_SEASONAL_NO_REF +
                        h2h_score * WEIGHT_H2H_NO_REF +
                        fouls_score * WEIGHT_FOULS_NO_REF
                    )

                player_data = {
                    "name": player_name,
                    "team": p.get("team_name"),
                    "position": position,
                    "combined_score": round(combined_score, 1),
                    "breakdown": {
                        "seasonal": {
                            "score": round(seasonal_score, 1),
                            "yellows": p.get("yellow_cards", 0),
                            "matches": p.get("matches_played", 0),
                            "per_90": round(yellows_per_90, 2)
                        },
                        "referee": {
                            "score": round(referee_score, 1),
                            "detail": referee_info
                        } if referee else None,
                        "h2h": {
                            "score": round(h2h_score, 1),
                            "detail": h2h_info
                        },
                        "fouls": {
                            "score": round(fouls_score, 1),
                            "team_foul_to_card_pct": round(team_foul_to_card, 1),
                            "position_multiplier": position_multiplier
                        }
                    }
                }
                all_players.append(player_data)

        # Ordina per score combinato
        all_players.sort(key=lambda x: x["combined_score"], reverse=True)

        # Separa per squadra e prendi top 5
        home_players = [p for p in all_players if home_team.lower() in p["team"].lower()]
        away_players = [p for p in all_players if away_team.lower() in p["team"].lower()]

        analysis["home_team_top5"] = home_players[:5]
        analysis["away_team_top5"] = away_players[:5]
        analysis["overall_top5"] = all_players[:5]

        if not referee:
            analysis["referee_note"] = "Arbitro non designato - analisi basata su dati stagionali, H2H e falli"

        return json.dumps(analysis, indent=2, default=str, ensure_ascii=False)

    except Exception as e:
        return f"Errore nell'analisi: {str(e)}"


if __name__ == "__main__":
    mcp.run()
