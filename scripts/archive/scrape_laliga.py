"""
YellowOracle - Script per raccogliere dati La Liga da FBref
Uso: python scripts/scrape_laliga.py --season 2024-2025
"""

import os
import sys
import time
import argparse
from datetime import datetime

import cloudscraper
import pandas as pd
from bs4 import BeautifulSoup
from supabase import create_client, Client
from dotenv import load_dotenv

# Carica variabili d'ambiente
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Scraper che bypassa protezioni Cloudflare
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    }
)

# URL base FBref per La Liga
FBREF_BASE = "https://fbref.com"
LALIGA_URLS = {
    "2023-2024": "/en/comps/12/2023-2024/2023-2024-La-Liga-Stats",
    "2024-2025": "/en/comps/12/2024-2025/2024-2025-La-Liga-Stats",
    "2025-2026": "/en/comps/12/La-Liga-Stats",  # Stagione corrente
}

def get_supabase_client() -> Client:
    """Crea connessione a Supabase."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Errore: SUPABASE_URL e SUPABASE_KEY devono essere impostati in .env")
        sys.exit(1)
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_page(url: str) -> BeautifulSoup:
    """Scarica e parsa una pagina web."""
    print(f"  Scaricando: {url}")
    response = scraper.get(url)
    response.raise_for_status()
    time.sleep(4)  # Rispetta il rate limiting
    return BeautifulSoup(response.content, "lxml")

def get_teams(soup: BeautifulSoup, season: str) -> list[dict]:
    """Estrae le squadre dalla pagina principale della stagione."""
    teams = []

    # Cerca la tabella della classifica
    table = soup.find("table", {"id": "results2024-202512overall"}) or \
            soup.find("table", {"id": "results2023-202412overall"}) or \
            soup.find("table", {"id": "results2025-202612overall"}) or \
            soup.find("table", class_="stats_table")

    if not table:
        # Prova a cercare qualsiasi tabella con dati delle squadre
        tables = soup.find_all("table", class_="stats_table")
        for t in tables:
            if t.find("th", {"data-stat": "team"}):
                table = t
                break

    if not table:
        print("  Attenzione: tabella squadre non trovata")
        return teams

    tbody = table.find("tbody")
    if not tbody:
        return teams

    for row in tbody.find_all("tr"):
        team_cell = row.find("td", {"data-stat": "team"})
        if team_cell:
            team_link = team_cell.find("a")
            if team_link:
                teams.append({
                    "name": team_link.text.strip(),
                    "fbref_url": team_link.get("href", "")
                })

    print(f"  Trovate {len(teams)} squadre")
    return teams

def get_player_stats(team_url: str, season: str) -> list[dict]:
    """Estrae statistiche giocatori per una squadra."""
    players = []

    full_url = FBREF_BASE + team_url
    soup = fetch_page(full_url)

    # Cerca la tabella delle statistiche standard
    table = soup.find("table", {"id": lambda x: x and "stats_standard" in str(x)})

    if not table:
        tables = soup.find_all("table", class_="stats_table")
        for t in tables:
            headers = [th.text for th in t.find_all("th")]
            if "Player" in headers and ("CrdY" in headers or "Yellow" in str(headers)):
                table = t
                break

    if not table:
        print(f"    Tabella statistiche non trovata")
        return players

    tbody = table.find("tbody")
    if not tbody:
        return players

    for row in tbody.find_all("tr"):
        # Salta righe di separazione
        if "thead" in row.get("class", []) or row.find("th", {"scope": "row"}) is None:
            continue

        player_cell = row.find("th", {"data-stat": "player"})
        if not player_cell:
            continue

        player_link = player_cell.find("a")
        if not player_link:
            continue

        # Estrai statistiche
        def get_stat(stat_name):
            cell = row.find("td", {"data-stat": stat_name})
            if cell and cell.text.strip():
                try:
                    return int(cell.text.strip())
                except ValueError:
                    try:
                        return float(cell.text.strip())
                    except ValueError:
                        return 0
            return 0

        position_cell = row.find("td", {"data-stat": "position"})
        position = position_cell.text.strip() if position_cell else ""

        # Mappa posizioni FBref alle nostre
        pos_map = {
            "GK": "GK",
            "DF": "DF", "DF,MF": "DF", "DF,FW": "DF",
            "MF": "MF", "MF,DF": "MF", "MF,FW": "MF",
            "FW": "FW", "FW,MF": "FW", "FW,DF": "FW"
        }
        position = pos_map.get(position.split(",")[0] if position else "", "MF")

        nationality_cell = row.find("td", {"data-stat": "nationality"})
        nationality = ""
        if nationality_cell:
            nat_link = nationality_cell.find("a")
            if nat_link:
                nationality = nat_link.text.strip()

        players.append({
            "name": player_link.text.strip(),
            "position": position,
            "nationality": nationality,
            "matches_played": get_stat("games"),
            "minutes_played": get_stat("minutes"),
            "yellow_cards": get_stat("cards_yellow"),
            "red_cards": get_stat("cards_red"),
        })

    print(f"    Trovati {len(players)} giocatori")
    return players

def save_teams_to_db(supabase: Client, teams: list[dict]):
    """Salva le squadre nel database."""
    print("\nSalvando squadre nel database...")

    for team in teams:
        try:
            # Upsert: inserisce o aggiorna se esiste
            supabase.table("teams").upsert({
                "name": team["name"],
            }, on_conflict="name").execute()
        except Exception as e:
            print(f"  Errore salvando {team['name']}: {e}")

    print(f"  Salvate {len(teams)} squadre")

def save_players_to_db(supabase: Client, team_name: str, players: list[dict], season: str):
    """Salva giocatori e statistiche nel database."""

    # Ottieni ID della squadra
    result = supabase.table("teams").select("id").eq("name", team_name).execute()
    if not result.data:
        print(f"  Squadra {team_name} non trovata nel DB")
        return

    team_id = result.data[0]["id"]

    for player in players:
        try:
            # Inserisci o trova giocatore
            player_result = supabase.table("players").upsert({
                "name": player["name"],
                "team_id": team_id,
                "position": player["position"],
                "nationality": player["nationality"],
            }, on_conflict="name,team_id").execute()

            # Ottieni ID giocatore
            player_query = supabase.table("players").select("id").eq("name", player["name"]).eq("team_id", team_id).execute()
            if not player_query.data:
                continue

            player_id = player_query.data[0]["id"]

            # Salva statistiche stagionali
            supabase.table("player_season_stats").upsert({
                "player_id": player_id,
                "season": season,
                "team_id": team_id,
                "matches_played": player["matches_played"],
                "minutes_played": player["minutes_played"],
                "yellow_cards": player["yellow_cards"],
                "red_cards": player["red_cards"],
            }, on_conflict="player_id,season").execute()

        except Exception as e:
            print(f"    Errore salvando {player['name']}: {e}")

def scrape_season(season: str):
    """Raccoglie tutti i dati per una stagione."""
    print(f"\n{'='*50}")
    print(f"RACCOLTA DATI LA LIGA {season}")
    print(f"{'='*50}")

    # Verifica che la stagione sia supportata
    if season not in LALIGA_URLS:
        print(f"Errore: stagione {season} non supportata")
        print(f"Stagioni disponibili: {list(LALIGA_URLS.keys())}")
        return

    # Connetti a Supabase
    supabase = get_supabase_client()

    # Scarica pagina principale
    url = FBREF_BASE + LALIGA_URLS[season]
    print(f"\nScaricando dati da: {url}")
    soup = fetch_page(url)

    # Estrai squadre
    print("\n1. Estrazione squadre...")
    teams = get_teams(soup, season)

    if not teams:
        print("Nessuna squadra trovata. Verificare la struttura della pagina.")
        return

    # Salva squadre
    save_teams_to_db(supabase, teams)

    # Per ogni squadra, estrai giocatori
    print("\n2. Estrazione statistiche giocatori...")
    for i, team in enumerate(teams, 1):
        print(f"\n  [{i}/{len(teams)}] {team['name']}")

        if team.get("fbref_url"):
            players = get_player_stats(team["fbref_url"], season)

            # Salva nel database
            save_players_to_db(supabase, team["name"], players, season)
        else:
            print(f"    URL non disponibile per {team['name']}")

        # Pausa tra le richieste
        time.sleep(2)

    print(f"\n{'='*50}")
    print(f"COMPLETATO: {season}")
    print(f"{'='*50}")

def main():
    parser = argparse.ArgumentParser(description="Raccoglie dati La Liga da FBref")
    parser.add_argument(
        "--season",
        type=str,
        default="2025-2026",
        help="Stagione da raccogliere (es: 2024-2025)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Raccoglie tutte le stagioni disponibili"
    )

    args = parser.parse_args()

    if args.all:
        for season in LALIGA_URLS.keys():
            scrape_season(season)
    else:
        scrape_season(args.season)

    print("\nDone!")

if __name__ == "__main__":
    main()
