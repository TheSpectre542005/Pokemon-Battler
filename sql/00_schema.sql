-- ============================================================================
-- FILE: 00_schema.sql
-- PURPOSE: Define the relational schema for the Pokémon Battler database.
--          Three tables capture Pokémon stats, type effectiveness, and
--          simulated battle outcomes. Indexes accelerate the multi-table
--          JOINs used throughout the analytical query layer.
-- ============================================================================

-- Table 1: pokemon
-- Stores base stats and metadata for all 151 Gen 1 Pokémon.
-- BST (Base Stat Total) is pre-computed for performance since every
-- battle-simulation formula depends on it.
CREATE TABLE IF NOT EXISTS pokemon (
    id              INTEGER PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    primary_type    TEXT NOT NULL,
    secondary_type  TEXT,
    hp              INTEGER NOT NULL,
    attack          INTEGER NOT NULL,
    defense         INTEGER NOT NULL,
    sp_atk          INTEGER NOT NULL,
    sp_def          INTEGER NOT NULL,
    speed           INTEGER NOT NULL,
    bst             INTEGER NOT NULL,
    sprite_url      TEXT
);

-- Table 2: type_chart
-- The full 18×18 type effectiveness matrix (324 rows).
-- Each row maps an attacking type to a defending type with a damage
-- multiplier (0.0 = immune, 0.5 = resisted, 1.0 = neutral, 2.0 = super effective).
CREATE TABLE IF NOT EXISTS type_chart (
    attacking_type      TEXT NOT NULL,
    defending_type      TEXT NOT NULL,
    multiplier          REAL NOT NULL,
    effectiveness_label TEXT NOT NULL,
    PRIMARY KEY (attacking_type, defending_type)
);

-- Table 3: battles
-- 10,000 simulated battle records. Each row captures attacker/defender,
-- the winner, BSTs at time of battle, type multiplier applied, and a
-- randomised date for time-series analysis.
CREATE TABLE IF NOT EXISTS battles (
    battle_id       INTEGER PRIMARY KEY,
    attacker_name   TEXT NOT NULL,
    defender_name   TEXT NOT NULL,
    winner_name     TEXT NOT NULL,
    attacker_bst    INTEGER,
    defender_bst    INTEGER,
    type_multiplier REAL,
    attacker_type   TEXT,
    defender_type   TEXT,
    battle_date     TEXT,
    FOREIGN KEY (attacker_name) REFERENCES pokemon(name),
    FOREIGN KEY (defender_name) REFERENCES pokemon(name)
);

-- Indexes for query performance
-- These cover the WHERE / JOIN / GROUP BY patterns used in queries 01–06.
CREATE INDEX IF NOT EXISTS idx_battles_attacker ON battles(attacker_name);
CREATE INDEX IF NOT EXISTS idx_battles_winner   ON battles(winner_name);
CREATE INDEX IF NOT EXISTS idx_battles_type     ON battles(attacker_type);
CREATE INDEX IF NOT EXISTS idx_pokemon_type     ON pokemon(primary_type);
