"""
load_database.py — Data Acquisition Script 4

Loads the three generated CSV files (pokemon.csv, type_chart.csv, battles.csv)
into a local SQLite database (pokemon_battler.db).

Design decision: We DROP and re-CREATE all tables on every run to ensure
a clean, idempotent load. This is acceptable for a portfolio project where
the source CSVs are the ground truth; in production you'd use UPSERT logic.
"""

import os
import sqlite3
import pandas as pd


def get_paths() -> dict[str, str]:
    """
    Resolve all file paths relative to this script's directory.

    Returns:
        Dict with keys 'db', 'schema', 'pokemon_csv', 'type_chart_csv', 'battles_csv'.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    return {
        "db": os.path.join(project_root, "pokemon_battler.db"),
        "schema": os.path.join(project_root, "sql", "00_schema.sql"),
        "pokemon_csv": os.path.join(script_dir, "pokemon.csv"),
        "type_chart_csv": os.path.join(script_dir, "type_chart.csv"),
        "battles_csv": os.path.join(script_dir, "battles.csv"),
    }


def drop_tables(conn: sqlite3.Connection) -> None:
    """Drop all existing tables for a clean reload."""
    tables = ["battles", "type_chart", "pokemon"]  # Order matters for FK constraints
    cursor = conn.cursor()
    for table in tables:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")
    # Also drop indexes (they're auto-dropped with tables, but be explicit)
    conn.commit()


def create_tables(conn: sqlite3.Connection, schema_path: str) -> None:
    """Execute the schema SQL file to create all tables and indexes."""
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)
    print("  Tables and indexes created.")


def load_csv_to_table(
    conn: sqlite3.Connection,
    csv_path: str,
    table_name: str,
) -> int:
    """
    Load a CSV file into the specified SQLite table.

    Args:
        conn: Active SQLite connection.
        csv_path: Path to the source CSV.
        table_name: Target table name.

    Returns:
        Number of rows inserted.
    """
    df = pd.read_csv(csv_path)
    df.to_sql(table_name, conn, if_exists="append", index=False)
    return len(df)


def validate(conn: sqlite3.Connection) -> bool:
    """
    Run post-load validation queries.

    Returns:
        True if all counts match expectations, False otherwise.
    """
    expected = {"pokemon": 151, "type_chart": 324, "battles": 10_000}
    cursor = conn.cursor()
    all_ok = True

    for table, expected_count in expected.items():
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        actual = cursor.fetchone()[0]
        status = "✓" if actual == expected_count else "✗"
        print(f"  {status} {table}: {actual} rows (expected {expected_count})")
        if actual != expected_count:
            all_ok = False

    return all_ok


def main() -> None:
    """Entry point — orchestrates drop → create → load → validate pipeline."""
    paths = get_paths()

    # Check that all source files exist before touching the database
    for key in ("schema", "pokemon_csv", "type_chart_csv", "battles_csv"):
        if not os.path.exists(paths[key]):
            print(f"FATAL: Missing required file: {paths[key]}")
            print("Run the data fetch/generate scripts first.")
            return

    print(f"Connecting to database: {paths['db']}")
    conn = sqlite3.connect(paths["db"])

    try:
        print("Dropping existing tables...")
        drop_tables(conn)

        print("Creating schema from 00_schema.sql...")
        create_tables(conn, paths["schema"])

        print("Loading CSVs...")
        for csv_key, table_name in [
            ("pokemon_csv", "pokemon"),
            ("type_chart_csv", "type_chart"),
            ("battles_csv", "battles"),
        ]:
            rows = load_csv_to_table(conn, paths[csv_key], table_name)
            print(f"  Loaded {rows} rows into {table_name}")

        print("\nValidating row counts...")
        if validate(conn):
            print(f"\n✓ Database loaded successfully: {paths['db']}")
        else:
            print("\n⚠ Validation failed — row counts do not match expectations.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
