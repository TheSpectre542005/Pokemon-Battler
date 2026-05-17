"""
generate_battles.py — Data Acquisition Script 3

Simulates 10,000 competitive battle records using a BST + type-multiplier
win probability formula. This mirrors strength-of-schedule adjustments
used in sports analytics and risk-adjusted returns in finance.

Win probability formula:
    type_adjusted_att = attacker_bst × type_multiplier
    P(attacker wins) = type_adjusted_att / (type_adjusted_att + defender_bst)

This formula ensures that:
- Higher BST → higher base win chance (raw strength)
- Type advantage (2.0×) roughly doubles the effective strength
- Type disadvantage (0.5×) roughly halves it
- The result is a value between 0 and 1 suitable for Bernoulli sampling
"""

import os
import random
from datetime import datetime, timedelta
import pandas as pd


def load_pokemon(csv_path: str) -> pd.DataFrame:
    """Load the pokemon.csv file and validate required columns exist."""
    df = pd.read_csv(csv_path)
    required = {"name", "primary_type", "bst"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"pokemon.csv is missing columns: {missing}")
    return df


def load_type_chart(csv_path: str) -> dict[tuple[str, str], float]:
    """
    Load type_chart.csv into a lookup dict keyed by (attacking, defending).

    Returns:
        Dict mapping (atk_type, def_type) → multiplier (float).
        Missing pairs default to 1.0 via dict.get() at call site.
    """
    df = pd.read_csv(csv_path)
    lookup = {}
    for _, row in df.iterrows():
        lookup[(row["attacking_type"], row["defending_type"])] = row["multiplier"]
    return lookup


def simulate_battles(
    pokemon_df: pd.DataFrame,
    type_lookup: dict[tuple[str, str], float],
    num_battles: int = 10_000,
    seed: int = 42,
) -> list[dict]:
    """
    Generate `num_battles` simulated battle records.

    Args:
        pokemon_df: DataFrame with columns [name, primary_type, bst].
        type_lookup: Dict mapping (atk_type, def_type) → multiplier.
        num_battles: Number of battles to simulate.
        seed: Random seed for reproducibility.

    Returns:
        List of battle record dicts ready for DataFrame construction.

    Note on weighted sampling:
        We use uniform random selection. While the spec mentions discouraging
        same-species battles, with 151 Pokémon the probability of a self-matchup
        is ~0.66% per battle — negligible. We explicitly re-roll if attacker == defender.
    """
    random.seed(seed)
    names = pokemon_df["name"].tolist()
    bst_map = dict(zip(pokemon_df["name"], pokemon_df["bst"]))
    type_map = dict(zip(pokemon_df["name"], pokemon_df["primary_type"]))

    now = datetime.now()
    records = []

    for battle_id in range(1, num_battles + 1):
        # Select two different Pokémon
        attacker = random.choice(names)
        defender = random.choice(names)
        while defender == attacker:
            defender = random.choice(names)

        atk_bst = bst_map[attacker]
        def_bst = bst_map[defender]
        atk_type = type_map[attacker]
        def_type = type_map[defender]

        # Look up type multiplier; default to 1.0 (neutral) if pair not found
        type_mult = type_lookup.get((atk_type, def_type), 1.0)

        # Win probability formula (see module docstring)
        type_adjusted_att = atk_bst * type_mult
        win_prob = type_adjusted_att / (type_adjusted_att + def_bst)

        winner = attacker if random.random() < win_prob else defender

        # Random battle date within the last 365 days
        battle_date = (now - timedelta(days=random.randint(0, 365))).strftime("%Y-%m-%d")

        records.append({
            "battle_id": battle_id,
            "attacker_name": attacker,
            "defender_name": defender,
            "winner_name": winner,
            "attacker_bst": atk_bst,
            "defender_bst": def_bst,
            "type_multiplier": type_mult,
            "attacker_type": atk_type,
            "defender_type": def_type,
            "battle_date": battle_date,
        })

    return records


def print_summary(df: pd.DataFrame) -> None:
    """Print a human-readable summary of the generated battle data."""
    total = len(df)
    unique_attackers = df["attacker_name"].nunique()
    most_common = df["attacker_name"].value_counts().idxmax()
    most_common_count = df["attacker_name"].value_counts().max()
    attacker_wins = (df["winner_name"] == df["attacker_name"]).sum()
    win_rate = round(attacker_wins / total * 100, 1)

    print(f"\n--- Battle Simulation Summary ---")
    print(f"  Total battles: {total}")
    print(f"  Unique attackers: {unique_attackers}")
    print(f"  Most common attacker: {most_common} ({most_common_count} battles)")
    print(f"  Overall attacker win rate: {win_rate}%")


def main() -> None:
    """Entry point — load inputs, simulate battles, save CSV."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pokemon_path = os.path.join(script_dir, "pokemon.csv")
    type_chart_path = os.path.join(script_dir, "type_chart.csv")
    out_path = os.path.join(script_dir, "battles.csv")

    print("Loading Pokémon data...")
    pokemon_df = load_pokemon(pokemon_path)

    print("Loading type chart...")
    type_lookup = load_type_chart(type_chart_path)

    print(f"Simulating 10,000 battles (seed=42)...")
    records = simulate_battles(pokemon_df, type_lookup, num_battles=10_000)

    df = pd.DataFrame(records)
    column_order = [
        "battle_id", "attacker_name", "defender_name", "winner_name",
        "attacker_bst", "defender_bst", "type_multiplier",
        "attacker_type", "defender_type", "battle_date",
    ]
    df = df[column_order]
    df.to_csv(out_path, index=False)

    print_summary(df)
    print(f"\n✓ Saved 10,000 battles to data/battles.csv")


if __name__ == "__main__":
    main()
