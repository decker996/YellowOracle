#!/usr/bin/env python3
"""
Prototipo: Test parallelizzazione API football-data.org

Confronta:
- Sequenziale: 10 chiamate con 2.5s delay
- Parallelo: 10 chiamate simultanee

Usa l'endpoint /persons/{id} per testare (stesso usato da sync_player_stats)
"""

import os
import sys
import time
import asyncio
from typing import Optional

import aiohttp
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("FOOTBALL_API_KEY")
API_BASE = "https://api.football-data.org/v4"

# ID di alcuni giocatori reali per il test (La Liga)
TEST_PLAYER_IDS = [
    3754,   # Vinícius Júnior
    44,     # Cristiano Ronaldo
    278,    # Benzema
    371,    # Modric
    517,    # Kroos
    1246,   # Pedri
    158,    # Gavi
    3223,   # Bellingham
    9971,   # Lewandowski
    7955,   # Mbappé
]


def sequential_fetch(player_ids: list) -> dict:
    """Metodo sequenziale attuale (con delay 2.5s)"""
    print("\n🐢 TEST SEQUENZIALE (metodo attuale)")
    print(f"   {len(player_ids)} chiamate con 2.5s delay ciascuna")

    headers = {"X-Auth-Token": API_KEY}
    results = {"success": 0, "failed": 0, "data": []}

    start = time.time()

    for i, player_id in enumerate(player_ids):
        url = f"{API_BASE}/persons/{player_id}"
        print(f"   [{i+1}/{len(player_ids)}] Fetching player {player_id}...", end=" ")

        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                results["success"] += 1
                results["data"].append(data.get("name", "Unknown"))
                print(f"✅ {data.get('name', 'Unknown')}")
            else:
                results["failed"] += 1
                print(f"❌ HTTP {response.status_code}")
        except Exception as e:
            results["failed"] += 1
            print(f"❌ {e}")

        # Delay come nello script attuale
        if i < len(player_ids) - 1:
            time.sleep(2.5)

    elapsed = time.time() - start
    results["time"] = elapsed

    print(f"\n   ⏱️  Tempo totale: {elapsed:.1f}s")
    print(f"   ✅ Successi: {results['success']}, ❌ Falliti: {results['failed']}")

    return results


async def fetch_player_async(session: aiohttp.ClientSession, player_id: int) -> Optional[dict]:
    """Fetch singolo giocatore in modo asincrono"""
    url = f"{API_BASE}/persons/{player_id}"
    headers = {"X-Auth-Token": API_KEY}

    try:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                print(f"   ⚠️ Player {player_id}: HTTP {response.status}")
                return None
    except Exception as e:
        print(f"   ⚠️ Player {player_id}: {e}")
        return None


async def parallel_fetch(player_ids: list) -> dict:
    """Metodo parallelo (tutte le chiamate insieme)"""
    print("\n🚀 TEST PARALLELO (nuovo metodo)")
    print(f"   {len(player_ids)} chiamate simultanee")

    results = {"success": 0, "failed": 0, "data": []}

    start = time.time()

    async with aiohttp.ClientSession() as session:
        # Lancia tutte le richieste in parallelo
        tasks = [fetch_player_async(session, pid) for pid in player_ids]
        responses = await asyncio.gather(*tasks)

        for resp in responses:
            if resp:
                results["success"] += 1
                results["data"].append(resp.get("name", "Unknown"))
            else:
                results["failed"] += 1

    elapsed = time.time() - start
    results["time"] = elapsed

    print(f"   Giocatori trovati: {', '.join(results['data'][:5])}...")
    print(f"\n   ⏱️  Tempo totale: {elapsed:.1f}s")
    print(f"   ✅ Successi: {results['success']}, ❌ Falliti: {results['failed']}")

    return results


async def parallel_fetch_batched(player_ids: list, batch_size: int = 10) -> dict:
    """Metodo parallelo con batch (rispetta rate limit 30/min)"""
    print(f"\n🚀 TEST PARALLELO A BATCH (batch_size={batch_size})")
    print(f"   {len(player_ids)} chiamate in batch da {batch_size}")

    results = {"success": 0, "failed": 0, "data": []}

    start = time.time()

    async with aiohttp.ClientSession() as session:
        for i in range(0, len(player_ids), batch_size):
            batch = player_ids[i:i+batch_size]
            print(f"   Batch {i//batch_size + 1}: {len(batch)} richieste parallele...", end=" ")

            tasks = [fetch_player_async(session, pid) for pid in batch]
            responses = await asyncio.gather(*tasks)

            batch_success = sum(1 for r in responses if r)
            results["success"] += batch_success
            results["failed"] += len(batch) - batch_success

            for resp in responses:
                if resp:
                    results["data"].append(resp.get("name", "Unknown"))

            print(f"✅ {batch_success}/{len(batch)}")

            # Pausa tra batch per rispettare rate limit (solo se ci sono altri batch)
            if i + batch_size < len(player_ids):
                # Con 30 req/min, dopo 10 richieste aspettiamo 20 secondi
                wait_time = (batch_size / 30) * 60
                print(f"   ⏳ Pausa {wait_time:.0f}s per rate limit...")
                await asyncio.sleep(wait_time)

    elapsed = time.time() - start
    results["time"] = elapsed

    print(f"\n   ⏱️  Tempo totale: {elapsed:.1f}s")
    print(f"   ✅ Successi: {results['success']}, ❌ Falliti: {results['failed']}")

    return results


def main():
    if not API_KEY:
        print("❌ FOOTBALL_API_KEY non impostata in .env")
        sys.exit(1)

    print("=" * 60)
    print("🧪 TEST PARALLELIZZAZIONE API football-data.org")
    print("=" * 60)
    print(f"\nTest con {len(TEST_PLAYER_IDS)} giocatori")

    # Test 1: Sequenziale (metodo attuale)
    seq_results = sequential_fetch(TEST_PLAYER_IDS)

    # Test 2: Parallelo semplice (tutte insieme)
    print("\n" + "-" * 40)
    par_results = asyncio.run(parallel_fetch(TEST_PLAYER_IDS))

    # Confronto
    print("\n" + "=" * 60)
    print("📊 CONFRONTO RISULTATI")
    print("=" * 60)

    speedup = seq_results["time"] / par_results["time"] if par_results["time"] > 0 else 0

    print(f"""
    | Metodo      | Tempo    | Speedup |
    |-------------|----------|---------|
    | Sequenziale | {seq_results['time']:>6.1f}s | 1x      |
    | Parallelo   | {par_results['time']:>6.1f}s | {speedup:.1f}x     |

    🎯 Risparmio: {seq_results['time'] - par_results['time']:.1f}s ({(1 - par_results['time']/seq_results['time'])*100:.0f}%)
    """)

    # Proiezione per sync completo
    print("=" * 60)
    print("📈 PROIEZIONE SYNC COMPLETO (500 giocatori)")
    print("=" * 60)

    # Sequenziale: 500 * 2.5s = 1250s = ~21 min
    seq_projected = 500 * 2.5

    # Parallelo: 500 / 30 batch * 60s = ~17 min (con rate limit)
    # Ma il tempo effettivo delle chiamate è molto minore
    par_projected = (500 / 30) * 60 + (par_results["time"] / len(TEST_PLAYER_IDS)) * 500

    print(f"""
    | Metodo      | Tempo stimato |
    |-------------|---------------|
    | Sequenziale | {seq_projected/60:>6.1f} min   |
    | Parallelo   | {par_projected/60:>6.1f} min   |

    ⚠️  Nota: Il parallelo deve rispettare 30 req/min, quindi il vantaggio
    principale è nella latenza ridotta (1 round-trip invece di 500).
    """)


if __name__ == "__main__":
    main()
