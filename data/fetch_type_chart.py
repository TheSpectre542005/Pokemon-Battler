"""
fetch_type_chart.py — Data Acquisition Script 2

Builds the complete 18×18 Pokémon type effectiveness matrix by querying
PokéAPI's /type/ endpoint for each type's damage_relations.

Why build from API instead of hardcoding: The matrix changes across
generations. Fetching it programmatically ensures accuracy and
demonstrates data-sourcing discipline in a portfolio context.
"""

import os
import sys
import time
import requests
import pandas as pd


# Canonical list of the 18 battle-relevant types (excludes 'unknown' and 'shadow')
TYPES = [
    "normal", "fire", "water", "electric", "grass", "ice",
    "fighting", "poison", "ground", "flying", "psychic", "bug",
    "rock", "ghost", "dragon", "dark", "steel", "fairy",
]

EFFECTIVENESS_LABELS = {
    0.0: "immune",
    0.5: "not_very_effective",
    1.0: "normal",
    2.0: "super_effective",
}


def fetch_damage_relations(type_name: str) -> dict | None:
    """
    Fetch damage_relations for a single type from PokéAPI.

    Args:
        type_name: One of the 18 canonical type names.

    Returns:
        The damage_relations dict, or None on failure.
    """
    url = f"https://pokeapi.co/api/v2/type/{type_name}/"
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json()["damage_relations"]
    except requests.RequestException as exc:
        print(f"  ERROR fetching type '{type_name}': {exc}")
        return None


def build_type_chart() -> list[dict]:
    """
    Construct the full 18×18 type chart from PokéAPI responses.

    Logic:
    1. Initialise every (attacker, defender) pair to multiplier 1.0.
    2. For each attacker type, override pairs found in double_damage_to,
       half_damage_to, and no_damage_to.
    3. Only types in our TYPES list are considered — the API also returns
       'unknown' and 'shadow' which we intentionally exclude.
    """
    # Pre-fill the matrix with neutral (1.0) effectiveness
    matrix: dict[tuple[str, str], float] = {}
    for atk in TYPES:
        for dfn in TYPES:
            matrix[(atk, dfn)] = 1.0

    for atk_type in TYPES:
        print(f"  Fetching damage relations for {atk_type}...")
        relations = fetch_damage_relations(atk_type)
        if relations is None:
            continue

        # Override with actual effectiveness values
        for entry in relations.get("double_damage_to", []):
            dfn = entry["name"]
            if dfn in TYPES:
                matrix[(atk_type, dfn)] = 2.0

        for entry in relations.get("half_damage_to", []):
            dfn = entry["name"]
            if dfn in TYPES:
                matrix[(atk_type, dfn)] = 0.5

        for entry in relations.get("no_damage_to", []):
            dfn = entry["name"]
            if dfn in TYPES:
                matrix[(atk_type, dfn)] = 0.0

        time.sleep(0.2)  # Rate-limit courtesy

    # Convert to list of dicts for DataFrame construction
    rows = []
    for (atk, dfn), mult in matrix.items():
        rows.append({
            "attacking_type": atk,
            "defending_type": dfn,
            "multiplier": mult,
            "effectiveness_label": EFFECTIVENESS_LABELS[mult],
        })
    return rows


def validate_chart(df: pd.DataFrame) -> None:
    """Print distribution of effectiveness labels as a sanity check."""
    print("\nEffectiveness distribution:")
    counts = df["effectiveness_label"].value_counts()
    for label, count in counts.items():
        print(f"  {label}: {count}")


def main() -> None:
    """Entry point — build the type chart and save to CSV."""
    print("Building 18×18 type effectiveness matrix from PokéAPI...")
    rows = build_type_chart()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(script_dir, "type_chart.csv")

    df = pd.DataFrame(rows)
    df.to_csv(out_path, index=False)

    validate_chart(df)
    print(f"\n✓ Saved {len(df)} type matchup rows to data/type_chart.csv")


if __name__ == "__main__":
    main()
