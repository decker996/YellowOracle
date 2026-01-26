"""
YellowOracle MCP Server
Espone le funzioni di analisi cartellini a Claude

Avvio: python mcp_server.py
"""

import os
import json
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
                "team_side, ball_possession, fouls_committed, fouls_suffered, "
                "total_shots, shots_on_goal, shots_off_goal, corner_kicks, "
                "yellow_cards, red_cards, saves, offsides, "
                "matches!inner(match_date, season, "
                "home_team:teams!matches_home_team_id_fkey(name), "
                "away_team:teams!matches_away_team_id_fkey(name))"
            ).eq("matches.season", season).ilike(
                "matches.home_team.name", f"%{team_name}%"
            ).order("matches(match_date)", desc=True).limit(limit).execute()

            away_result = supabase.table("match_statistics").select(
                "team_side, ball_possession, fouls_committed, fouls_suffered, "
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
    Combina i 3 fattori: storico stagionale, storico arbitro, scontri diretti.

    Args:
        home_team: Squadra di casa
        away_team: Squadra in trasferta
        referee: Nome arbitro (opzionale)

    Returns:
        Analisi completa con giocatori a rischio e raccomandazioni
    """
    supabase = get_supabase()

    analysis = {
        "match": f"{home_team} vs {away_team}",
        "referee": referee or "Non specificato",
        "home_team_players": [],
        "away_team_players": [],
        "top_risk_players": []
    }

    try:
        # Giocatori squadra casa
        home_result = supabase.table("player_season_cards").select("*").ilike(
            "team_name", f"%{home_team}%"
        ).eq("season", "2025-2026").order("yellow_cards", desc=True).limit(15).execute()

        # Giocatori squadra trasferta
        away_result = supabase.table("player_season_cards").select("*").ilike(
            "team_name", f"%{away_team}%"
        ).eq("season", "2025-2026").order("yellow_cards", desc=True).limit(15).execute()

        all_players = []

        for p in (home_result.data or []):
            risk_score = float(p.get("yellows_per_90") or 0) * 100
            player_data = {
                "name": p["player_name"],
                "team": p["team_name"],
                "position": p.get("position"),
                "season_yellows": p.get("yellow_cards", 0),
                "yellows_per_90": p.get("yellows_per_90"),
                "risk_score": round(risk_score, 1)
            }
            analysis["home_team_players"].append(player_data)
            all_players.append(player_data)

        for p in (away_result.data or []):
            risk_score = float(p.get("yellows_per_90") or 0) * 100
            player_data = {
                "name": p["player_name"],
                "team": p["team_name"],
                "position": p.get("position"),
                "season_yellows": p.get("yellow_cards", 0),
                "yellows_per_90": p.get("yellows_per_90"),
                "risk_score": round(risk_score, 1)
            }
            analysis["away_team_players"].append(player_data)
            all_players.append(player_data)

        # Top 5 a rischio
        all_players.sort(key=lambda x: x["risk_score"], reverse=True)
        analysis["top_risk_players"] = all_players[:5]

        # Se c'è l'arbitro, aggiungi info
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
                analysis["referee_history"] = ref_result.data[:10]

        return json.dumps(analysis, indent=2, default=str)

    except Exception as e:
        return f"Errore nell'analisi: {str(e)}"


if __name__ == "__main__":
    mcp.run()
