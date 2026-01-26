"""
YellowOracle - Sincronizzazione dati da football-data.org
Uso: python scripts/sync_football_data.py --season 2024-2025

Richiede piano "Free + Deep Data" (€29/mese) + "Statistics Add-On" (€15/mese)
"""

import os
import sys
import time
import argparse
from datetime import datetime
from typing import Optional

import requests
from supabase import create_client, Client
from dotenv import load_dotenv

# Carica variabili d'ambiente
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")

# Configurazione API
API_BASE = "https://api.football-data.org/v4"
COMPETITION_CODE = "PD"  # La Liga (Primera Division)

# Rate limiting: 30 chiamate/minuto con piano a pagamento
RATE_LIMIT_DELAY = 2.5  # secondi tra le chiamate


def get_supabase_client() -> Client:
    """Crea connessione a Supabase."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Errore: SUPABASE_URL e SUPABASE_KEY devono essere impostati in .env")
        sys.exit(1)
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def api_request(endpoint: str) -> dict:
    """Esegue una richiesta all'API football-data.org."""
    if not FOOTBALL_API_KEY:
        print("❌ Errore: FOOTBALL_API_KEY deve essere impostato in .env")
        sys.exit(1)

    url = f"{API_BASE}{endpoint}"
    headers = {"X-Auth-Token": FOOTBALL_API_KEY}

    print(f"  📡 API: {endpoint}")

    response = requests.get(url, headers=headers)

    if response.status_code == 429:
        print("  ⏳ Rate limit raggiunto, attendo 60 secondi...")
        time.sleep(60)
        response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"  ❌ Errore API: {response.status_code} - {response.text[:200]}")
        return {}

    time.sleep(RATE_LIMIT_DELAY)
    return response.json()


def sync_teams(supabase: Client, season: str) -> dict:
    """Sincronizza le squadre della competizione."""
    print("\n📋 Sincronizzazione squadre...")

    # Determina l'anno per l'API (es. "2024-2025" -> 2024)
    api_season = season.split("-")[0]

    data = api_request(f"/competitions/{COMPETITION_CODE}/teams?season={api_season}")

    if not data.get("teams"):
        print("  ⚠️ Nessuna squadra trovata")
        return {}

    team_map = {}  # external_id -> internal_id

    for team in data["teams"]:
        try:
            result = supabase.table("teams").upsert({
                "external_id": team["id"],
                "name": team["name"],
                "short_name": team.get("shortName"),
                "tla": team.get("tla"),
                "crest_url": team.get("crest"),
                "stadium": team.get("venue"),
                "updated_at": datetime.now().isoformat()
            }, on_conflict="external_id").execute()

            # Recupera l'ID interno
            query = supabase.table("teams").select("id").eq("external_id", team["id"]).execute()
            if query.data:
                team_map[team["id"]] = query.data[0]["id"]

        except Exception as e:
            print(f"  ❌ Errore salvando {team['name']}: {e}")

    print(f"  ✅ Sincronizzate {len(team_map)} squadre")
    return team_map


def sync_players(supabase: Client, team_map: dict) -> dict:
    """Sincronizza i giocatori di tutte le squadre."""
    print("\n👥 Sincronizzazione giocatori...")

    player_map = {}  # external_id -> internal_id
    total = 0

    for external_team_id, internal_team_id in team_map.items():
        data = api_request(f"/teams/{external_team_id}")

        if not data.get("squad"):
            continue

        for player in data["squad"]:
            try:
                # Mappa la posizione
                position = player.get("position", "")

                result = supabase.table("players").upsert({
                    "external_id": player["id"],
                    "name": player["name"],
                    "first_name": player.get("firstName"),
                    "last_name": player.get("lastName"),
                    "date_of_birth": player.get("dateOfBirth"),
                    "nationality": player.get("nationality"),
                    "position": position,
                    "shirt_number": player.get("shirtNumber"),
                    "current_team_id": internal_team_id,
                    "updated_at": datetime.now().isoformat()
                }, on_conflict="external_id").execute()

                # Recupera l'ID interno
                query = supabase.table("players").select("id").eq("external_id", player["id"]).execute()
                if query.data:
                    player_map[player["id"]] = query.data[0]["id"]
                    total += 1

            except Exception as e:
                print(f"  ❌ Errore salvando {player.get('name', 'unknown')}: {e}")

    print(f"  ✅ Sincronizzati {total} giocatori")
    return player_map


def sync_referees(supabase: Client, matches_data: list) -> dict:
    """Sincronizza gli arbitri dalle partite."""
    print("\n🎯 Sincronizzazione arbitri...")

    referee_map = {}  # external_id -> internal_id
    seen = set()

    for match in matches_data:
        for referee in match.get("referees", []):
            if referee["id"] in seen:
                continue
            seen.add(referee["id"])

            try:
                result = supabase.table("referees").upsert({
                    "external_id": referee["id"],
                    "name": referee["name"],
                    "nationality": referee.get("nationality"),
                    "updated_at": datetime.now().isoformat()
                }, on_conflict="external_id").execute()

                query = supabase.table("referees").select("id").eq("external_id", referee["id"]).execute()
                if query.data:
                    referee_map[referee["id"]] = query.data[0]["id"]

            except Exception as e:
                print(f"  ❌ Errore salvando arbitro {referee.get('name')}: {e}")

    print(f"  ✅ Sincronizzati {len(referee_map)} arbitri")
    return referee_map


def sync_matches(supabase: Client, season: str, team_map: dict, referee_map: dict) -> list:
    """Sincronizza le partite della stagione."""
    print("\n⚽ Sincronizzazione partite...")

    api_season = season.split("-")[0]
    data = api_request(f"/competitions/{COMPETITION_CODE}/matches?season={api_season}")

    if not data.get("matches"):
        print("  ⚠️ Nessuna partita trovata")
        return []

    matches = data["matches"]
    match_ids = []  # Lista di (external_id, internal_id)

    for match in matches:
        try:
            # Trova gli ID interni
            home_team_id = team_map.get(match["homeTeam"]["id"])
            away_team_id = team_map.get(match["awayTeam"]["id"])

            referee_id = None
            if match.get("referees"):
                ref_ext_id = match["referees"][0]["id"]
                referee_id = referee_map.get(ref_ext_id)

            score = match.get("score", {})
            full_time = score.get("fullTime", {})
            half_time = score.get("halfTime", {})

            result = supabase.table("matches").upsert({
                "external_id": match["id"],
                "season": season,
                "matchday": match.get("matchday"),
                "match_date": match["utcDate"],
                "status": match["status"],
                "home_team_id": home_team_id,
                "away_team_id": away_team_id,
                "home_score": full_time.get("home"),
                "away_score": full_time.get("away"),
                "home_score_halftime": half_time.get("home"),
                "away_score_halftime": half_time.get("away"),
                "winner": score.get("winner"),
                "referee_id": referee_id,
                "updated_at": datetime.now().isoformat()
            }, on_conflict="external_id").execute()

            # Recupera l'ID interno
            query = supabase.table("matches").select("id").eq("external_id", match["id"]).execute()
            if query.data:
                match_ids.append((match["id"], query.data[0]["id"]))

        except Exception as e:
            print(f"  ❌ Errore salvando partita {match['id']}: {e}")

    print(f"  ✅ Sincronizzate {len(match_ids)} partite")
    return match_ids


def sync_match_details(supabase: Client, match_ids: list, team_map: dict, player_map: dict):
    """Sincronizza i dettagli delle partite (eventi, formazioni, statistiche)."""
    print("\n📊 Sincronizzazione dettagli partite...")

    total_events = 0
    total_lineups = 0
    total_stats = 0

    for i, (external_id, internal_id) in enumerate(match_ids):
        print(f"  [{i+1}/{len(match_ids)}] Partita {external_id}")

        data = api_request(f"/matches/{external_id}")

        if not data:
            continue

        # --- FORMAZIONI ---
        if data.get("homeTeam", {}).get("lineup"):
            for lineup_data in [
                (data["homeTeam"], True),
                (data["awayTeam"], True)
            ]:
                team_data, is_home = lineup_data
                team_ext_id = team_data["id"]
                team_int_id = team_map.get(team_ext_id)

                if not team_int_id:
                    continue

                # Titolari
                for player in team_data.get("lineup", []):
                    player_int_id = player_map.get(player["id"])
                    if not player_int_id:
                        continue

                    try:
                        supabase.table("lineups").upsert({
                            "match_id": internal_id,
                            "team_id": team_int_id,
                            "player_id": player_int_id,
                            "is_starter": True,
                            "is_substitute": False,
                            "shirt_number": player.get("shirtNumber"),
                            "position": player.get("position")
                        }, on_conflict="match_id,player_id").execute()
                        total_lineups += 1
                    except Exception as e:
                        pass

                # Panchina
                for player in team_data.get("bench", []):
                    player_int_id = player_map.get(player["id"])
                    if not player_int_id:
                        continue

                    try:
                        supabase.table("lineups").upsert({
                            "match_id": internal_id,
                            "team_id": team_int_id,
                            "player_id": player_int_id,
                            "is_starter": False,
                            "is_substitute": True,
                            "shirt_number": player.get("shirtNumber"),
                            "position": player.get("position")
                        }, on_conflict="match_id,player_id").execute()
                        total_lineups += 1
                    except Exception as e:
                        pass

        # --- EVENTI (GOL, CARTELLINI) ---
        if data.get("goals"):
            for goal in data["goals"]:
                player_int_id = player_map.get(goal.get("scorer", {}).get("id"))
                team_int_id = team_map.get(goal.get("team", {}).get("id"))

                if player_int_id and team_int_id:
                    try:
                        event_type = "OWN_GOAL" if goal.get("type") == "OWN" else "GOAL"
                        if goal.get("type") == "PENALTY":
                            event_type = "PENALTY"

                        supabase.table("match_events").insert({
                            "match_id": internal_id,
                            "team_id": team_int_id,
                            "player_id": player_int_id,
                            "event_type": event_type,
                            "minute": goal.get("minute"),
                            "detail": goal.get("type")
                        }).execute()
                        total_events += 1
                    except Exception as e:
                        pass

        if data.get("bookings"):
            for booking in data["bookings"]:
                player_int_id = player_map.get(booking.get("player", {}).get("id"))
                team_int_id = team_map.get(booking.get("team", {}).get("id"))

                if player_int_id and team_int_id:
                    try:
                        card_type = "YELLOW_CARD" if booking.get("card") == "YELLOW" else "RED_CARD"

                        supabase.table("match_events").insert({
                            "match_id": internal_id,
                            "team_id": team_int_id,
                            "player_id": player_int_id,
                            "event_type": card_type,
                            "minute": booking.get("minute"),
                            "detail": booking.get("card")
                        }).execute()
                        total_events += 1
                    except Exception as e:
                        pass

        # --- STATISTICHE PARTITA (se disponibili con Statistics Add-On) ---
        # Queste potrebbero essere in un endpoint separato o incluse nella risposta

    print(f"  ✅ Sincronizzati {total_events} eventi, {total_lineups} formazioni")


def update_aggregated_stats(supabase: Client, season: str):
    """Aggiorna le statistiche aggregate per giocatori e arbitri."""
    print("\n📈 Aggiornamento statistiche aggregate...")

    # Aggiorna statistiche giocatori dalla tabella match_events
    query = """
    INSERT INTO player_season_stats (player_id, team_id, season, yellow_cards, red_cards, matches_played)
    SELECT
        me.player_id,
        p.current_team_id,
        %s as season,
        COUNT(CASE WHEN me.event_type = 'YELLOW_CARD' THEN 1 END) as yellow_cards,
        COUNT(CASE WHEN me.event_type = 'RED_CARD' THEN 1 END) as red_cards,
        COUNT(DISTINCT me.match_id) as matches_played
    FROM match_events me
    JOIN players p ON me.player_id = p.id
    JOIN matches m ON me.match_id = m.id
    WHERE m.season = %s
    AND me.event_type IN ('YELLOW_CARD', 'RED_CARD')
    GROUP BY me.player_id, p.current_team_id
    ON CONFLICT (player_id, season)
    DO UPDATE SET
        yellow_cards = EXCLUDED.yellow_cards,
        red_cards = EXCLUDED.red_cards,
        matches_played = GREATEST(player_season_stats.matches_played, EXCLUDED.matches_played),
        updated_at = NOW()
    """

    # Nota: Supabase non supporta query raw SQL direttamente via client Python
    # Le statistiche aggregate vengono calcolate tramite le viste o trigger
    print("  ℹ️ Statistiche aggregate calcolate tramite viste del database")


def sync_season(season: str, full_sync: bool = False):
    """Sincronizza tutti i dati per una stagione."""
    print(f"\n{'='*60}")
    print(f"🏆 SINCRONIZZAZIONE LA LIGA {season}")
    print(f"{'='*60}")

    supabase = get_supabase_client()

    # 1. Squadre
    team_map = sync_teams(supabase, season)
    if not team_map:
        print("❌ Impossibile continuare senza squadre")
        return

    # 2. Giocatori
    player_map = sync_players(supabase, team_map)

    # 3. Partite (recupera anche gli arbitri)
    api_season = season.split("-")[0]
    matches_data = api_request(f"/competitions/{COMPETITION_CODE}/matches?season={api_season}")
    matches_list = matches_data.get("matches", [])

    # 4. Arbitri
    referee_map = sync_referees(supabase, matches_list)

    # 5. Salva partite
    match_ids = sync_matches(supabase, season, team_map, referee_map)

    # 6. Dettagli partite (solo se full_sync o poche partite)
    if full_sync or len(match_ids) <= 50:
        sync_match_details(supabase, match_ids, team_map, player_map)
    else:
        print(f"\n⚠️ {len(match_ids)} partite trovate. Usa --full per sincronizzare i dettagli.")
        print("   (Questo richiede molte chiamate API)")

    # 7. Aggiorna statistiche aggregate
    update_aggregated_stats(supabase, season)

    print(f"\n{'='*60}")
    print(f"✅ SINCRONIZZAZIONE {season} COMPLETATA")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="Sincronizza dati La Liga da football-data.org")
    parser.add_argument(
        "--season",
        type=str,
        default="2025-2026",
        help="Stagione da sincronizzare (es: 2024-2025)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Sincronizza tutte le stagioni (2023-2024, 2024-2025, 2025-2026)"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Sincronizzazione completa inclusi dettagli partite"
    )

    args = parser.parse_args()

    if args.all:
        for season in ["2023-2024", "2024-2025", "2025-2026"]:
            sync_season(season, args.full)
    else:
        sync_season(args.season, args.full)

    print("\n🎉 Done!")


if __name__ == "__main__":
    main()
