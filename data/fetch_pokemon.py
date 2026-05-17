"""
fetch_pokemon.py — Data Acquisition Script 1

Fetches all 151 Gen 1 Pokémon from PokéAPI and saves base stats,
types, and sprite URLs to data/pokemon.csv.

Why PokéAPI: It's the canonical open-source Pokémon REST API with
stable endpoints and no authentication required.
"""

import os
import sys
import time
import requests
import pandas as pd


def fetch_pokemon_list(limit: int = 151) -> list[dict]:
    """
    Fetch the name/URL index for the first `limit` Pokémon.

    Args:
        limit: Number of Pokémon to retrieve (default 151 for Gen 1).

    Returns:
        List of dicts with 'name' and 'url' keys.

    Raises:
        SystemExit: If the initial list request fails.
    """
    url = f"https://pokeapi.co/api/v2/pokemon?limit={limit}"
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json()["results"]
    except requests.RequestException as exc:
        print(f"FATAL: Could not fetch Pokémon list — {exc}")
        sys.exit(1)


def extract_stats(stats_list: list[dict]) -> dict[str, int]:
    """
    Map PokéAPI stat objects to flat key-value pairs.

    The API returns stats as [{"base_stat": N, "stat": {"name": "hp"}}, ...].
    We normalise 'special-attack' → 'sp_atk' and 'special-defense' → 'sp_def'
    to match our schema's snake_case convention.
    """
    stat_map = {
        "hp": "hp",
        "attack": "attack",
        "defense": "defense",
        "special-attack": "sp_atk",
        "special-defense": "sp_def",
        "speed": "speed",
    }
    result = {}
    for entry in stats_list:
        api_name = entry["stat"]["name"]
        if api_name in stat_map:
            result[stat_map[api_name]] = entry["base_stat"]
    return result


def fetch_pokemon_detail(url: str) -> dict | None:
    """
    Fetch a single Pokémon's detail page and extract the fields we need.

    Args:
        url: PokéAPI detail URL (e.g. https://pokeapi.co/api/v2/pokemon/1/).

    Returns:
        Dict with schema-aligned keys, or None on HTTP failure.
    """
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        print(f"  ERROR fetching {url}: {exc}")
        return None

    # Types array is ordered — index 0 is primary, index 1 (if present) is secondary
    types = [t["type"]["name"] for t in data["types"]]
    primary_type = types[0]
    secondary_type = types[1] if len(types) > 1 else None

    stats = extract_stats(data["stats"])
    bst = sum(stats.values())

    sprite_url = data["sprites"].get("front_default", "")

    return {
        "id": data["id"],
        "name": data["name"],
        "primary_type": primary_type,
        "secondary_type": secondary_type,
        "hp": stats["hp"],
        "attack": stats["attack"],
        "defense": stats["defense"],
        "sp_atk": stats["sp_atk"],
        "sp_def": stats["sp_def"],
        "speed": stats["speed"],
        "bst": bst,
        "sprite_url": sprite_url,
    }


def main() -> None:
    """Entry point — orchestrates the full fetch-and-save pipeline."""
    print("Fetching Gen 1 Pokémon from PokéAPI...")
    pokemon_list = fetch_pokemon_list(151)

    records: list[dict] = []
    for i, entry in enumerate(pokemon_list, start=1):
        detail = fetch_pokemon_detail(entry["url"])
        if detail:
            records.append(detail)

        # Progress reporting every 20 Pokémon
        if i % 20 == 0:
            print(f"Fetched {i}/151...")

        # Rate-limit courtesy — 0.3 s between requests
        time.sleep(0.3)

    # Determine output path relative to this script's location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(script_dir, "pokemon.csv")

    df = pd.DataFrame(records)
    column_order = [
        "id", "name", "primary_type", "secondary_type",
        "hp", "attack", "defense", "sp_atk", "sp_def", "speed",
        "bst", "sprite_url",
    ]
    df = df[column_order]
    df.to_csv(out_path, index=False)

    print(f"✓ Saved {len(df)} Pokémon to data/pokemon.csv")


if __name__ == "__main__":
    main()
