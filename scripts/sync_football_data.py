"""
YellowOracle - Sincronizzazione dati da football-data.org

Uso:
    # Sync incrementale (dall'ultima partita in DB a oggi) - CONSIGLIATO
    python scripts/sync_football_data.py --competition SA --incremental --full

    # Singola competizione e stagione
    python scripts/sync_football_data.py --competition PD --season 2024-2025

    # Tutte le stagioni per una competizione
    python scripts/sync_football_data.py --competition SA --all --full

    # Multiple competizioni
    python scripts/sync_football_data.py --competitions PD,SA,BL1 --season 2025-2026

    # Tutte le competizioni configurate
    python scripts/sync_football_data.py --all-competitions --season 2025-2026

Competizioni supportate: PD (La Liga), SA (Serie A), BL1 (Bundesliga),
                         PL (Premier League), FL1 (Ligue 1)

Richiede piano "Free + Deep Data" (€29/mese) + "Statistics Add-On" (€15/mese)
"""

import os
import sys
import time
import argparse
from datetime import datetime, timedelta
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

# Competizioni supportate
COMPETITIONS = {
    # Campionati nazionali
    'PD': {'name': 'La Liga', 'area': 'Spain', 'area_code': 'ESP'},
    'SA': {'name': 'Serie A', 'area': 'Italy', 'area_code': 'ITA'},
    'BL1': {'name': 'Bundesliga', 'area': 'Germany', 'area_code': 'GER'},
    'PL': {'name': 'Premier League', 'area': 'England', 'area_code': 'ENG'},
    'FL1': {'name': 'Ligue 1', 'area': 'France', 'area_code': 'FRA'},
    # Competizioni UEFA
    'CL': {'name': 'UEFA Champions League', 'area': 'Europe', 'area_code': 'UEFA'},
    'EL': {'name': 'UEFA Europa League', 'area': 'Europe', 'area_code': 'UEFA'},
}

# Rate limiting: 30 chiamate/minuto con piano a pagamento
RATE_LIMIT_DELAY = 2.5  # secondi tra le chiamate

# Stagioni supportate (piano Free + Deep Data: ultime 3 stagioni)
# Nota: stagioni più vecchie richiedono piano superiore
ALL_SEASONS = [
    "2023-2024",
    "2024-2025",
    "2025-2026",
]


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


def get_last_match_date(supabase: Client, competition_code: str, season: str) -> Optional[str]:
    """
    Trova la data dell'ultima partita FINISHED nel database per una competizione/stagione.
    Restituisce la data in formato YYYY-MM-DD o None se non ci sono partite.
    """
    try:
        # Trova competition_id
        comp_query = supabase.table("competitions").select("id").eq("code", competition_code).execute()
        if not comp_query.data:
            return None

        competition_id = comp_query.data[0]["id"]

        # Trova l'ultima partita FINISHED
        match_query = supabase.table("matches")\
            .select("match_date")\
            .eq("competition_id", competition_id)\
            .eq("season", season)\
            .eq("status", "FINISHED")\
            .order("match_date", desc=True)\
            .limit(1)\
            .execute()

        if match_query.data:
            # Estrai solo la data (YYYY-MM-DD) dalla datetime
            match_date = match_query.data[0]["match_date"]
            if match_date:
                return match_date[:10]  # "2026-01-20T20:45:00Z" -> "2026-01-20"

        return None

    except Exception as e:
        print(f"  ⚠️ Errore recuperando ultima partita: {e}")
        return None


def get_players_from_recent_matches(supabase: Client, match_ids: list) -> set:
    """
    Recupera gli external_id dei giocatori che hanno giocato nelle partite specificate.
    Usato per ottimizzare sync_player_stats in modalità incrementale.
    """
    player_external_ids = set()

    try:
        for _, internal_id in match_ids:
            # Recupera giocatori dalle lineups
            lineups = supabase.table("lineups")\
                .select("player_id")\
                .eq("match_id", internal_id)\
                .execute()

            for lineup in lineups.data:
                # Recupera external_id del giocatore
                player = supabase.table("players")\
                    .select("external_id")\
                    .eq("id", lineup["player_id"])\
                    .execute()
                if player.data:
                    player_external_ids.add(player.data[0]["external_id"])

        return player_external_ids

    except Exception as e:
        print(f"  ⚠️ Errore recuperando giocatori: {e}")
        return set()


def sync_competition(supabase: Client, competition_code: str) -> str:
    """Sincronizza/crea la competizione nel DB e restituisce l'ID interno."""
    print(f"\n🏆 Sincronizzazione competizione {competition_code}...")

    if competition_code not in COMPETITIONS:
        print(f"  ❌ Competizione {competition_code} non supportata")
        print(f"  Competizioni valide: {', '.join(COMPETITIONS.keys())}")
        sys.exit(1)

    comp_info = COMPETITIONS[competition_code]

    # Ottieni info dalla API
    data = api_request(f"/competitions/{competition_code}")

    if not data:
        print(f"  ⚠️ Impossibile ottenere dati per {competition_code}, uso dati locali")
        external_id = None
        emblem_url = None
        plan = None
    else:
        external_id = data.get("id")
        emblem_url = data.get("emblem")
        plan = data.get("plan")

    try:
        result = supabase.table("competitions").upsert({
            "external_id": external_id,
            "code": competition_code,
            "name": comp_info['name'],
            "area_name": comp_info['area'],
            "area_code": comp_info['area_code'],
            "emblem_url": emblem_url,
            "plan": plan,
            "updated_at": datetime.now().isoformat()
        }, on_conflict="code").execute()

        # Recupera l'ID interno
        query = supabase.table("competitions").select("id").eq("code", competition_code).execute()
        if query.data:
            competition_id = query.data[0]["id"]
            print(f"  ✅ Competizione {comp_info['name']} ({competition_code}) sincronizzata")
            return competition_id

    except Exception as e:
        print(f"  ❌ Errore salvando competizione: {e}")
        sys.exit(1)


def sync_teams(supabase: Client, competition_code: str, season: str) -> dict:
    """Sincronizza le squadre della competizione."""
    print("\n📋 Sincronizzazione squadre...")

    # Determina l'anno per l'API (es. "2024-2025" -> 2024)
    api_season = season.split("-")[0]

    data = api_request(f"/competitions/{competition_code}/teams?season={api_season}")

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


def sync_matches(supabase: Client, competition_code: str, competition_id: str, season: str, team_map: dict, referee_map: dict, matches_data: list = None) -> list:
    """
    Sincronizza le partite della stagione.

    Args:
        matches_data: Lista di partite già recuperata dall'API (evita doppia chiamata)
    """
    print("\n⚽ Sincronizzazione partite...")

    if matches_data is None:
        # Fallback: recupera tutte le partite della stagione
        api_season = season.split("-")[0]
        endpoint = f"/competitions/{competition_code}/matches?season={api_season}"
        data = api_request(endpoint)
        matches = data.get("matches", [])
    else:
        matches = matches_data

    if not matches:
        print("  ⚠️ Nessuna partita trovata")
        return []

    print(f"  📊 {len(matches)} partite da sincronizzare")
    match_ids = []  # Lista di (external_id, internal_id)

    for match in matches:
        try:
            # Trova gli ID interni
            home_team_id = team_map.get(match["homeTeam"]["id"])
            away_team_id = team_map.get(match["awayTeam"]["id"])

            referee_id = None
            var_referee_id = None
            for ref in match.get("referees", []):
                ref_type = ref.get("type", "")
                ref_int_id = referee_map.get(ref["id"])
                if ref_type == "REFEREE":
                    referee_id = ref_int_id
                elif ref_type == "VIDEO_ASSISTANT_REFEREE_N1":
                    var_referee_id = ref_int_id

            score = match.get("score", {})
            full_time = score.get("fullTime", {})
            half_time = score.get("halfTime", {})

            result = supabase.table("matches").upsert({
                "external_id": match["id"],
                "competition_id": competition_id,
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
                "var_referee_id": var_referee_id,
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

        # --- STATISTICHE PARTITA (Statistics Add-On) ---
        for team_key, is_home in [('homeTeam', True), ('awayTeam', False)]:
            team_data = data.get(team_key, {})
            stats = team_data.get('statistics', {})
            if stats:
                team_ext_id = team_data.get('id')
                team_int_id = team_map.get(team_ext_id)

                if team_int_id:
                    try:
                        supabase.table("match_statistics").upsert({
                            "match_id": internal_id,
                            "team_id": team_int_id,
                            "ball_possession": stats.get("ball_possession"),
                            "shots_on_goal": stats.get("shots_on_goal"),
                            "shots_off_goal": stats.get("shots_off_goal"),
                            "total_shots": stats.get("shots"),
                            "corner_kicks": stats.get("corner_kicks"),
                            "free_kicks": stats.get("free_kicks"),
                            "goal_kicks": stats.get("goal_kicks"),
                            "throw_ins": stats.get("throw_ins"),
                            "saves": stats.get("saves"),
                            "offsides": stats.get("offsides"),
                            "fouls_committed": stats.get("fouls"),
                            "yellow_cards": stats.get("yellow_cards"),
                            "red_cards": stats.get("red_cards")
                        }, on_conflict="match_id,team_id").execute()
                        total_stats += 1
                    except Exception as e:
                        print(f"    ⚠️ Errore statistiche: {e}")

        # --- SOSTITUZIONI (per calcolare minuti giocati) ---
        if data.get("substitutions"):
            for sub in data["substitutions"]:
                minute = sub.get("minute", 90)
                player_out_ext = sub.get("playerOut", {}).get("id")
                player_in_ext = sub.get("playerIn", {}).get("id")

                # Aggiorna giocatore uscito
                if player_out_ext:
                    player_out_id = player_map.get(player_out_ext)
                    if player_out_id:
                        try:
                            supabase.table("lineups").update({
                                "subbed_out_minute": minute,
                                "minutes_played": minute
                            }).eq("match_id", internal_id).eq("player_id", player_out_id).execute()
                        except:
                            pass

                # Aggiorna giocatore entrato
                if player_in_ext:
                    player_in_id = player_map.get(player_in_ext)
                    if player_in_id:
                        try:
                            # Stima minuti: 90 - minuto entrata (approssimazione)
                            minutes_in = max(0, 90 - minute)
                            supabase.table("lineups").update({
                                "subbed_in_minute": minute,
                                "minutes_played": minutes_in
                            }).eq("match_id", internal_id).eq("player_id", player_in_id).execute()
                        except:
                            pass

                # Salva anche come evento SUBSTITUTION
                if player_out_ext and player_in_ext:
                    player_out_id = player_map.get(player_out_ext)
                    player_in_id = player_map.get(player_in_ext)
                    team_ext_id = sub.get("team", {}).get("id")
                    team_int_id = team_map.get(team_ext_id)

                    if player_out_id and player_in_id and team_int_id:
                        try:
                            supabase.table("match_events").insert({
                                "match_id": internal_id,
                                "team_id": team_int_id,
                                "player_id": player_out_id,
                                "player_in_id": player_in_id,
                                "event_type": "SUBSTITUTION",
                                "minute": minute
                            }).execute()
                            total_events += 1
                        except:
                            pass

    print(f"  ✅ Sincronizzati {total_events} eventi, {total_lineups} formazioni, {total_stats} statistiche")


def sync_player_stats(supabase: Client, player_map: dict, competition_code: str, season: str, filter_player_ids: set = None):
    """
    Sincronizza statistiche aggregate giocatori da API /persons/{id}/matches.
    Questa è la fonte più accurata per minutes_played, matches_played, yellow_cards.

    NOTA: Chiama l'API SENZA filtro competizione per ottenere i totali stagionali.
    Le statistiche per singola competizione sono calcolate dalle viste (player_season_cards).

    Args:
        filter_player_ids: Se specificato, sincronizza solo questi external_id (modalità incrementale)
    """
    if filter_player_ids:
        print(f"\n📊 Sincronizzazione statistiche giocatori (incrementale: {len(filter_player_ids)} giocatori)...")
        # Filtra player_map per includere solo i giocatori specificati
        player_items = [(ext_id, int_id) for ext_id, int_id in player_map.items() if ext_id in filter_player_ids]
    else:
        print("\n📊 Sincronizzazione statistiche giocatori (API Person)...")
        player_items = list(player_map.items())

    api_season = season.split("-")[0]
    total_synced = 0
    total_skipped = 0

    total_players = len(player_items)

    for i, (external_id, internal_id) in enumerate(player_items):
        if (i + 1) % 50 == 0 or i == 0:
            print(f"  [{i+1}/{total_players}] Sincronizzazione statistiche giocatori...")

        # Chiama API Person per statistiche aggregate (TUTTE le competizioni per avere totali stagionali)
        data = api_request(f"/persons/{external_id}/matches?season={api_season}&limit=100")

        if not data:
            total_skipped += 1
            continue

        agg = data.get("aggregations", {})
        if not agg:
            total_skipped += 1
            continue

        try:
            # Trova team_id corrente del giocatore
            player_query = supabase.table("players").select("current_team_id").eq("id", internal_id).execute()
            team_id = player_query.data[0]["current_team_id"] if player_query.data else None

            # Calcola rossi totali (rossi diretti + doppi gialli)
            red_cards = agg.get("redCards", 0) + agg.get("yellowRedCards", 0)

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
                "red_cards": red_cards,
                "updated_at": datetime.now().isoformat()
            }, on_conflict="player_id,season").execute()

            total_synced += 1

        except Exception as e:
            print(f"    ⚠️ Errore giocatore {external_id}: {e}")
            total_skipped += 1

    print(f"  ✅ Sincronizzati {total_synced} giocatori, {total_skipped} saltati")
    return total_synced


def update_referee_stats(supabase: Client):
    """
    Aggiorna statistiche aggregate arbitri calcolandole dalle partite nel database.
    L'API non fornisce statistiche arbitri, quindi le calcoliamo internamente.
    """
    print("\n🎯 Aggiornamento statistiche arbitri...")

    try:
        # Recupera tutti gli arbitri
        referees = supabase.table("referees").select("id, external_id").execute()

        if not referees.data:
            print("  ⚠️ Nessun arbitro nel database")
            return

        updated = 0
        for ref in referees.data:
            ref_id = ref["id"]

            # Conta partite arbitrate
            matches = supabase.table("matches")\
                .select("id", count="exact")\
                .eq("referee_id", ref_id)\
                .eq("status", "FINISHED")\
                .execute()
            total_matches = matches.count or 0

            if total_matches == 0:
                continue

            # Recupera statistiche cartellini dalle partite arbitrate
            match_ids_query = supabase.table("matches")\
                .select("id")\
                .eq("referee_id", ref_id)\
                .eq("status", "FINISHED")\
                .execute()

            if not match_ids_query.data:
                continue

            match_ids = [m["id"] for m in match_ids_query.data]

            # Conta cartellini totali da match_statistics
            total_yellows = 0
            total_reds = 0
            total_fouls = 0

            for match_id in match_ids:
                stats = supabase.table("match_statistics")\
                    .select("yellow_cards, red_cards, fouls_committed")\
                    .eq("match_id", match_id)\
                    .execute()

                for s in stats.data:
                    total_yellows += s.get("yellow_cards") or 0
                    total_reds += s.get("red_cards") or 0
                    total_fouls += s.get("fouls_committed") or 0

            # Calcola medie
            avg_yellows = round(total_yellows / total_matches, 2) if total_matches > 0 else 0
            avg_fouls = round(total_fouls / total_matches, 2) if total_matches > 0 else 0

            # Aggiorna arbitro
            supabase.table("referees").update({
                "total_matches": total_matches,
                "total_yellows": total_yellows,
                "total_reds": total_reds,
                "avg_yellows_per_match": avg_yellows,
                "avg_fouls_per_match": avg_fouls,
                "updated_at": datetime.now().isoformat()
            }).eq("id", ref_id).execute()

            updated += 1

        print(f"  ✅ Aggiornati {updated} arbitri")

    except Exception as e:
        print(f"  ❌ Errore aggiornamento arbitri: {e}")


def verify_sync(supabase: Client, competition_code: str, season: str) -> dict:
    """
    Verifica completezza del sync e genera report.
    Restituisce un dizionario con conteggi e warning.
    """
    print("\n🔍 Verifica completezza sync...")

    report = {
        "competition": competition_code,
        "season": season,
        "tables": {},
        "warnings": [],
        "status": "OK"
    }

    # Recupera competition_id
    comp_query = supabase.table("competitions").select("id").eq("code", competition_code).execute()
    competition_id = comp_query.data[0]["id"] if comp_query.data else None

    # 1. Conta record per tabella principale
    tables_to_check = [
        ("competitions", None),
        ("teams", None),
        ("players", None),
        ("referees", None),
    ]

    for table, filter_col in tables_to_check:
        try:
            query = supabase.table(table).select("id", count="exact")
            result = query.execute()
            report["tables"][table] = result.count or 0
        except Exception as e:
            report["tables"][table] = f"ERROR: {e}"

    # 2. Conta partite per questa competizione/stagione
    try:
        matches_query = supabase.table("matches")\
            .select("id", count="exact")\
            .eq("competition_id", competition_id)\
            .eq("season", season)\
            .execute()
        report["tables"]["matches"] = matches_query.count or 0

        # Conta partite FINISHED
        finished_query = supabase.table("matches")\
            .select("id", count="exact")\
            .eq("competition_id", competition_id)\
            .eq("season", season)\
            .eq("status", "FINISHED")\
            .execute()
        report["tables"]["matches_finished"] = finished_query.count or 0
    except Exception as e:
        report["tables"]["matches"] = f"ERROR: {e}"

    # 3. Conta eventi (cartellini)
    try:
        events_query = supabase.table("match_events")\
            .select("id", count="exact")\
            .execute()
        report["tables"]["match_events"] = events_query.count or 0

        # Conta solo cartellini
        cards_query = supabase.table("match_events")\
            .select("id", count="exact")\
            .in_("event_type", ["YELLOW_CARD", "RED_CARD"])\
            .execute()
        report["tables"]["cards_total"] = cards_query.count or 0
    except Exception as e:
        report["tables"]["match_events"] = f"ERROR: {e}"

    # 4. Conta player_season_stats
    try:
        stats_query = supabase.table("player_season_stats")\
            .select("id", count="exact")\
            .eq("season", season)\
            .execute()
        report["tables"]["player_season_stats"] = stats_query.count or 0
    except Exception as e:
        report["tables"]["player_season_stats"] = f"ERROR: {e}"

    # 5. Conta lineups
    try:
        lineups_query = supabase.table("lineups")\
            .select("id", count="exact")\
            .execute()
        report["tables"]["lineups"] = lineups_query.count or 0
    except Exception as e:
        report["tables"]["lineups"] = f"ERROR: {e}"

    # 6. Conta match_statistics
    try:
        match_stats_query = supabase.table("match_statistics")\
            .select("id", count="exact")\
            .execute()
        report["tables"]["match_statistics"] = match_stats_query.count or 0
    except Exception as e:
        report["tables"]["match_statistics"] = f"ERROR: {e}"

    # === VERIFICHE E WARNING ===

    # Warning 1: player_season_stats vuota
    if isinstance(report["tables"].get("player_season_stats"), int):
        if report["tables"]["player_season_stats"] == 0:
            report["warnings"].append("CRITICAL: player_season_stats is EMPTY!")
            report["status"] = "WARNING"
        elif report["tables"]["player_season_stats"] < 100:
            report["warnings"].append(f"LOW: Only {report['tables']['player_season_stats']} players in player_season_stats")

    # Warning 2: Nessun cartellino
    if isinstance(report["tables"].get("cards_total"), int):
        if report["tables"]["cards_total"] == 0:
            report["warnings"].append("CRITICAL: No cards (YELLOW_CARD/RED_CARD) in match_events!")
            report["status"] = "WARNING"

    # Warning 3: Arbitri senza statistiche
    try:
        refs_no_stats = supabase.table("referees")\
            .select("id", count="exact")\
            .eq("total_matches", 0)\
            .execute()
        if refs_no_stats.count and refs_no_stats.count > 0:
            report["warnings"].append(f"INFO: {refs_no_stats.count} referees with total_matches=0")
    except:
        pass

    # Warning 4: Partite FINISHED senza eventi
    if isinstance(report["tables"].get("matches_finished"), int) and report["tables"]["matches_finished"] > 0:
        if isinstance(report["tables"].get("match_events"), int) and report["tables"]["match_events"] == 0:
            report["warnings"].append("WARNING: FINISHED matches but no events!")
            report["status"] = "WARNING"

    # Stampa report
    print("\n" + "="*50)
    print(f"📋 SYNC REPORT: {competition_code} {season}")
    print("="*50)

    print("\n📊 Record per tabella:")
    for table, count in report["tables"].items():
        status_icon = "✅" if isinstance(count, int) and count > 0 else "⚠️"
        print(f"  {status_icon} {table}: {count}")

    if report["warnings"]:
        print("\n⚠️ Warning:")
        for w in report["warnings"]:
            print(f"  - {w}")
    else:
        print("\n✅ Nessun warning")

    print(f"\n🏁 Status: {report['status']}")
    print("="*50)

    return report


def sync_season(competition_code: str, season: str, full_sync: bool = False, days: int = None, incremental: bool = False):
    """
    Sincronizza tutti i dati per una stagione e competizione.

    Args:
        incremental: Se True, sincronizza dall'ultima partita nel DB fino a oggi
    """
    comp_name = COMPETITIONS.get(competition_code, {}).get('name', competition_code)

    print(f"\n{'='*60}")
    print(f"🏆 SINCRONIZZAZIONE {comp_name} {season}")
    print(f"{'='*60}")

    supabase = get_supabase_client()

    # 0. Competizione
    competition_id = sync_competition(supabase, competition_code)

    # 1. Squadre
    team_map = sync_teams(supabase, competition_code, season)
    if not team_map:
        print("❌ Impossibile continuare senza squadre")
        return None

    # 2. Giocatori
    player_map = sync_players(supabase, team_map)

    # 3. Partite (recupera anche gli arbitri)
    # Build API URL with optional date range
    api_season = season.split("-")[0]
    date_from = None
    date_to = datetime.now().strftime("%Y-%m-%d")

    if incremental:
        # Modalità incrementale: dall'ultima partita nel DB a oggi
        last_match_date = get_last_match_date(supabase, competition_code, season)
        if last_match_date:
            date_from = last_match_date
            print(f"\n📅 Modalità INCREMENTALE: {date_from} → {date_to}")
        else:
            print(f"\n📅 Nessuna partita trovata nel DB, sync completa stagione")
    elif days is not None:
        # Modalità --days: ultimi N giorni
        date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        print(f"\n📅 Modalità DAYS: ultimi {days} giorni ({date_from} → {date_to})")

    if date_from:
        matches_endpoint = f"/competitions/{competition_code}/matches?season={api_season}&dateFrom={date_from}&dateTo={date_to}"
    else:
        matches_endpoint = f"/competitions/{competition_code}/matches?season={api_season}"

    matches_data = api_request(matches_endpoint)
    matches_list = matches_data.get("matches", [])

    # 4. Arbitri
    referee_map = sync_referees(supabase, matches_list)

    # 5. Salva partite (passa i dati già recuperati per evitare doppia chiamata API)
    match_ids = sync_matches(supabase, competition_code, competition_id, season, team_map, referee_map, matches_data=matches_list)

    # 6. Dettagli partite (solo se full_sync o poche partite)
    if full_sync or len(match_ids) <= 50:
        sync_match_details(supabase, match_ids, team_map, player_map)
    else:
        print(f"\n⚠️ {len(match_ids)} partite trovate. Usa --full per sincronizzare i dettagli.")
        print("   (Questo richiede molte chiamate API)")

    # 7. Statistiche giocatori da API Person
    if full_sync:
        if incremental and match_ids:
            # Modalità incrementale: sincronizza solo giocatori delle partite recenti
            recent_player_ids = get_players_from_recent_matches(supabase, match_ids)
            if recent_player_ids:
                sync_player_stats(supabase, player_map, competition_code, season, filter_player_ids=recent_player_ids)
            else:
                print("\n⚠️ Nessun giocatore trovato nelle partite recenti")
        else:
            # Modalità completa: sincronizza tutti i giocatori
            sync_player_stats(supabase, player_map, competition_code, season)
    else:
        print("\n⚠️ Usa --full per sincronizzare statistiche giocatori (player_season_stats)")

    # 8. Aggiorna statistiche arbitri (calcolo interno, 0 chiamate API)
    update_referee_stats(supabase)

    # 9. Verifica completezza e genera report
    report = verify_sync(supabase, competition_code, season)

    print(f"\n{'='*60}")
    print(f"✅ SINCRONIZZAZIONE {comp_name} {season} COMPLETATA")
    print(f"{'='*60}")

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Sincronizza dati calcio da football-data.org",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Competizioni supportate: {', '.join(COMPETITIONS.keys())}"
    )

    # Competizioni
    parser.add_argument(
        "--competition",
        type=str,
        default="PD",
        help="Competizione da sincronizzare (default: PD). Es: PD, SA, BL1, PL, FL1"
    )
    parser.add_argument(
        "--competitions",
        type=str,
        help="Lista competizioni separate da virgola (es: PD,SA,BL1)"
    )
    parser.add_argument(
        "--all-competitions",
        action="store_true",
        help="Sincronizza tutte le competizioni configurate"
    )

    # Stagioni
    parser.add_argument(
        "--season",
        type=str,
        default="2025-2026",
        help="Stagione da sincronizzare (es: 2024-2025)"
    )
    parser.add_argument(
        "--seasons",
        type=str,
        help="Lista stagioni separate da virgola (es: 2023-2024,2024-2025)"
    )
    parser.add_argument(
        "--all-seasons",
        action="store_true",
        help="Sincronizza tutte le stagioni supportate"
    )

    # Opzioni
    parser.add_argument(
        "--full",
        action="store_true",
        help="Sincronizzazione completa inclusi dettagli partite"
    )
    parser.add_argument(
        "--days",
        type=int,
        help="Sync only matches from last N days"
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Sync incrementale: dall'ultima partita nel DB a oggi (CONSIGLIATO per update settimanali)"
    )

    args = parser.parse_args()

    # Determina lista competizioni
    if args.all_competitions:
        competitions_list = list(COMPETITIONS.keys())
    elif args.competitions:
        competitions_list = [c.strip().upper() for c in args.competitions.split(",")]
    else:
        competitions_list = [args.competition.upper()]

    # Valida competizioni
    for comp in competitions_list:
        if comp not in COMPETITIONS:
            print(f"❌ Competizione '{comp}' non valida.")
            print(f"   Competizioni supportate: {', '.join(COMPETITIONS.keys())}")
            sys.exit(1)

    # Determina lista stagioni
    if args.all_seasons:
        seasons_list = ALL_SEASONS
    elif args.seasons:
        seasons_list = [s.strip() for s in args.seasons.split(",")]
    else:
        seasons_list = [args.season]

    # Esegui sincronizzazione
    all_reports = []
    for comp in competitions_list:
        for season in seasons_list:
            report = sync_season(comp, season, args.full, args.days, args.incremental)
            if report:
                all_reports.append(report)

    # Genera summary finale
    print("\n" + "="*60)
    print("📋 SUMMARY FINALE")
    print("="*60)

    has_warnings = False
    for report in all_reports:
        status_icon = "✅" if report["status"] == "OK" else "⚠️"
        print(f"\n{status_icon} {report['competition']} {report['season']}: {report['status']}")
        if report["warnings"]:
            has_warnings = True
            for w in report["warnings"]:
                print(f"   - {w}")

    # Scrivi nel GITHUB_STEP_SUMMARY se presente
    github_summary = os.getenv("GITHUB_STEP_SUMMARY")
    if github_summary:
        try:
            with open(github_summary, "a") as f:
                f.write("\n## YellowOracle Sync Report\n\n")

                for report in all_reports:
                    status_icon = "✅" if report["status"] == "OK" else "⚠️"
                    f.write(f"### {status_icon} {report['competition']} {report['season']}\n\n")

                    f.write("| Tabella | Record |\n")
                    f.write("|---------|--------|\n")
                    for table, count in report["tables"].items():
                        f.write(f"| {table} | {count} |\n")
                    f.write("\n")

                    if report["warnings"]:
                        f.write("**Warnings:**\n")
                        for w in report["warnings"]:
                            f.write(f"- {w}\n")
                        f.write("\n")

                f.write(f"\n**Sync completato:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        except Exception as e:
            print(f"⚠️ Impossibile scrivere GITHUB_STEP_SUMMARY: {e}")

    print("\n🎉 Done!")


if __name__ == "__main__":
    main()
