"""
queries.py — Centralised SQL Query Store

This module centralises all SQL queries used in the Streamlit app.
Keeping queries here (not inline in app.py) makes them testable,
reusable, and easy to diff against the standalone .sql files.

Each constant is the complete SQL string matching its corresponding
.sql file. Parameterised queries use ? placeholders for SQLite.
"""

# ---------------------------------------------------------------------------
# Query 01: Data validation — battle distribution by type
# ---------------------------------------------------------------------------
QUERY_SANITY_CHECK = """
SELECT
    p.primary_type,
    COUNT(*)                        AS total_battles,
    COUNT(DISTINCT b.attacker_name) AS distinct_attackers,
    ROUND(AVG(p.bst), 1)           AS avg_bst
FROM battles AS b
INNER JOIN pokemon AS p ON b.attacker_name = p.name
GROUP BY p.primary_type
ORDER BY total_battles DESC;
"""

# ---------------------------------------------------------------------------
# Query 02: Raw (naive) win rate — the misleading baseline
# ---------------------------------------------------------------------------
QUERY_RAW_WIN_RATE = """
WITH win_counts AS (
    SELECT
        attacker_name                                           AS name,
        COUNT(*)                                                AS total_battles,
        SUM(CASE WHEN winner_name = attacker_name THEN 1 ELSE 0 END) AS wins
    FROM battles
    GROUP BY attacker_name
    HAVING total_battles >= {min_battles}
),
ranked AS (
    SELECT
        wc.name,
        p.primary_type,
        wc.total_battles,
        wc.wins,
        ROUND(wc.wins * 100.0 / NULLIF(wc.total_battles, 0), 1) AS raw_win_pct,
        RANK() OVER (ORDER BY wc.wins * 100.0 / NULLIF(wc.total_battles, 0) DESC) AS overall_rank
    FROM win_counts AS wc
    INNER JOIN pokemon AS p ON wc.name = p.name
)
SELECT overall_rank, name, primary_type, total_battles, wins, raw_win_pct
FROM ranked
ORDER BY overall_rank ASC
LIMIT 20;
"""

# ---------------------------------------------------------------------------
# Query 04: Adjusted win rate — THE HEADLINE QUERY
# ---------------------------------------------------------------------------
QUERY_ADJUSTED_WIN_RATE = """
WITH battle_with_types AS (
    SELECT
        b.battle_id,
        b.attacker_name,
        b.defender_name,
        b.winner_name,
        p_att.primary_type  AS attacker_type,
        p_def.primary_type  AS defender_type,
        p_att.bst           AS attacker_bst,
        p_def.bst           AS defender_bst,
        COALESCE(t.multiplier, 1.0) AS type_mult
    FROM battles AS b
    INNER JOIN pokemon AS p_att ON b.attacker_name = p_att.name
    INNER JOIN pokemon AS p_def ON b.defender_name = p_def.name
    LEFT JOIN type_chart AS t
        ON t.attacking_type = p_att.primary_type
       AND t.defending_type = p_def.primary_type
),
pokemon_stats AS (
    SELECT
        bwt.attacker_name                                                       AS pokemon_name,
        p.primary_type,
        COUNT(*)                                                                AS total_battles,
        SUM(CASE WHEN bwt.winner_name = bwt.attacker_name THEN 1 ELSE 0 END)   AS wins,
        ROUND(
            SUM(CASE WHEN bwt.winner_name = bwt.attacker_name THEN 1 ELSE 0 END)
                * 100.0 / NULLIF(COUNT(*), 0), 1
        )                                                                       AS raw_win_pct,
        ROUND(
            (SUM(CASE WHEN bwt.winner_name = bwt.attacker_name THEN 1 ELSE 0 END)
                * 1.0 / AVG(bwt.type_mult))
                * 100.0 / NULLIF(COUNT(*), 0), 1
        )                                                                       AS adjusted_win_pct,
        ROUND(AVG(bwt.type_mult), 3)                                            AS avg_type_mult
    FROM battle_with_types AS bwt
    INNER JOIN pokemon AS p ON bwt.attacker_name = p.name
    GROUP BY bwt.attacker_name, p.primary_type
    HAVING COUNT(*) >= {min_battles}
),
ranked AS (
    SELECT
        ps.pokemon_name,
        ps.primary_type,
        ps.total_battles,
        ps.raw_win_pct,
        ps.adjusted_win_pct,
        ROUND(ps.raw_win_pct - ps.adjusted_win_pct, 1) AS inflation_gap,
        ps.avg_type_mult,
        RANK() OVER (PARTITION BY ps.primary_type ORDER BY ps.adjusted_win_pct DESC) AS rank_in_type,
        ROUND(PERCENT_RANK() OVER (ORDER BY ps.adjusted_win_pct) * 100, 1) AS overall_percentile,
        CASE
            WHEN RANK() OVER (PARTITION BY ps.primary_type ORDER BY ps.adjusted_win_pct DESC) = 1
                 AND ps.adjusted_win_pct >= ps.raw_win_pct
                THEN '🏆 TRUE ELITE'
            WHEN RANK() OVER (PARTITION BY ps.primary_type ORDER BY ps.adjusted_win_pct DESC) <= 3
                THEN '⭐ TYPE LEADER'
            WHEN ps.raw_win_pct - ps.adjusted_win_pct > 5
                THEN '⚠️ OVERRATED'
            WHEN ps.adjusted_win_pct - ps.raw_win_pct > 5
                THEN '📈 UNDERRATED'
            ELSE '— STANDARD'
        END AS analyst_tag
    FROM pokemon_stats AS ps
)
SELECT
    pokemon_name, primary_type, total_battles, raw_win_pct,
    adjusted_win_pct, inflation_gap, avg_type_mult,
    rank_in_type, overall_percentile, analyst_tag
FROM ranked
ORDER BY adjusted_win_pct DESC;
"""

# ---------------------------------------------------------------------------
# Query 05: Overrated / Underrated index (top 5 each via UNION ALL)
# ---------------------------------------------------------------------------
QUERY_OVERRATED_INDEX = """
WITH battle_with_types AS (
    SELECT
        b.attacker_name, b.defender_name, b.winner_name,
        p_att.primary_type AS attacker_type,
        p_def.primary_type AS defender_type,
        COALESCE(t.multiplier, 1.0) AS type_mult
    FROM battles AS b
    INNER JOIN pokemon AS p_att ON b.attacker_name = p_att.name
    INNER JOIN pokemon AS p_def ON b.defender_name = p_def.name
    LEFT JOIN type_chart AS t
        ON t.attacking_type = p_att.primary_type
       AND t.defending_type = p_def.primary_type
),
pokemon_stats AS (
    SELECT
        bwt.attacker_name AS pokemon_name,
        p.primary_type,
        COUNT(*) AS total_battles,
        SUM(CASE WHEN bwt.winner_name = bwt.attacker_name THEN 1 ELSE 0 END) AS wins,
        ROUND(SUM(CASE WHEN bwt.winner_name = bwt.attacker_name THEN 1 ELSE 0 END)
            * 100.0 / NULLIF(COUNT(*), 0), 1) AS raw_win_pct,
        ROUND((SUM(CASE WHEN bwt.winner_name = bwt.attacker_name THEN 1 ELSE 0 END)
            * 1.0 / AVG(bwt.type_mult)) * 100.0 / NULLIF(COUNT(*), 0), 1) AS adjusted_win_pct,
        ROUND(AVG(bwt.type_mult), 3) AS avg_type_mult
    FROM battle_with_types AS bwt
    INNER JOIN pokemon AS p ON bwt.attacker_name = p.name
    GROUP BY bwt.attacker_name, p.primary_type
    HAVING COUNT(*) >= {min_battles}
),
with_gap AS (
    SELECT
        ps.pokemon_name, ps.primary_type, ps.total_battles,
        ps.raw_win_pct, ps.adjusted_win_pct,
        ROUND(ps.raw_win_pct - ps.adjusted_win_pct, 1) AS inflation_gap,
        ps.avg_type_mult, p.sprite_url
    FROM pokemon_stats AS ps
    INNER JOIN pokemon AS p ON ps.pokemon_name = p.name
)
SELECT * FROM (
    SELECT 'MOST OVERRATED' AS category, pokemon_name, primary_type,
           total_battles, raw_win_pct, adjusted_win_pct, inflation_gap, sprite_url
    FROM with_gap ORDER BY inflation_gap DESC LIMIT 5
)

UNION ALL

SELECT * FROM (
    SELECT 'MOST UNDERRATED' AS category, pokemon_name, primary_type,
           total_battles, raw_win_pct, adjusted_win_pct, inflation_gap, sprite_url
    FROM with_gap ORDER BY inflation_gap ASC LIMIT 5
);
"""

# ---------------------------------------------------------------------------
# Query 06: Type-level dominance analysis
# ---------------------------------------------------------------------------
QUERY_TYPE_DOMINANCE = """
WITH battle_with_types AS (
    SELECT
        b.attacker_name, b.winner_name,
        p_att.primary_type AS attacker_type,
        COALESCE(t.multiplier, 1.0) AS type_mult
    FROM battles AS b
    INNER JOIN pokemon AS p_att ON b.attacker_name = p_att.name
    INNER JOIN pokemon AS p_def ON b.defender_name = p_def.name
    LEFT JOIN type_chart AS t
        ON t.attacking_type = p_att.primary_type
       AND t.defending_type = p_def.primary_type
),
pokemon_stats AS (
    SELECT
        bwt.attacker_name AS pokemon_name,
        bwt.attacker_type AS primary_type,
        COUNT(*) AS total_battles,
        SUM(CASE WHEN bwt.winner_name = bwt.attacker_name THEN 1 ELSE 0 END) AS wins,
        ROUND(SUM(CASE WHEN bwt.winner_name = bwt.attacker_name THEN 1 ELSE 0 END)
            * 100.0 / NULLIF(COUNT(*), 0), 1) AS raw_win_pct,
        ROUND((SUM(CASE WHEN bwt.winner_name = bwt.attacker_name THEN 1 ELSE 0 END)
            * 1.0 / AVG(bwt.type_mult)) * 100.0 / NULLIF(COUNT(*), 0), 1) AS adjusted_win_pct
    FROM battle_with_types AS bwt
    GROUP BY bwt.attacker_name, bwt.attacker_type
    HAVING COUNT(*) >= 10
),
type_aggregated AS (
    SELECT
        ps.primary_type,
        SUM(ps.total_battles)   AS total_battles_as_attacker,
        SUM(ps.wins)            AS total_wins,
        ROUND(SUM(ps.wins) * 100.0 / NULLIF(SUM(ps.total_battles), 0), 1) AS raw_type_win_pct,
        ROUND(AVG(ps.adjusted_win_pct), 1) AS avg_type_adjusted_win_pct,
        COUNT(*) AS pokemon_count
    FROM pokemon_stats AS ps
    GROUP BY ps.primary_type
)
SELECT
    ta.primary_type, ta.total_battles_as_attacker, ta.total_wins,
    ta.raw_type_win_pct, ta.avg_type_adjusted_win_pct, ta.pokemon_count,
    RANK() OVER (ORDER BY ta.avg_type_adjusted_win_pct DESC) AS type_rank,
    CASE
        WHEN ta.avg_type_adjusted_win_pct >= 55 THEN 'DOMINANT'
        WHEN ta.avg_type_adjusted_win_pct >= 50 THEN 'STRONG'
        WHEN ta.avg_type_adjusted_win_pct >= 45 THEN 'BALANCED'
        ELSE 'WEAK'
    END AS type_verdict
FROM type_aggregated AS ta
ORDER BY type_rank ASC;
"""

# ---------------------------------------------------------------------------
# Parameterised query for Pokémon detail lookup (uses ? placeholder)
# ---------------------------------------------------------------------------
QUERY_POKEMON_DETAIL = """
SELECT
    p.id, p.name, p.primary_type, p.secondary_type,
    p.hp, p.attack, p.defense, p.sp_atk, p.sp_def, p.speed,
    p.bst, p.sprite_url
FROM pokemon AS p
WHERE p.name = ?;
"""

# ---------------------------------------------------------------------------
# Recent battles for a specific Pokémon (last 10 as attacker or defender)
# ---------------------------------------------------------------------------
QUERY_POKEMON_BATTLES = """
SELECT
    b.battle_id, b.attacker_name, b.defender_name, b.winner_name,
    b.type_multiplier, b.attacker_type, b.defender_type, b.battle_date
FROM battles AS b
WHERE b.attacker_name = ? OR b.defender_name = ?
ORDER BY b.battle_date DESC
LIMIT 10;
"""

# ---------------------------------------------------------------------------
# Full type chart for heatmap rendering
# ---------------------------------------------------------------------------
QUERY_TYPE_CHART = """
SELECT attacking_type, defending_type, multiplier, effectiveness_label
FROM type_chart
ORDER BY attacking_type, defending_type;
"""

# ---------------------------------------------------------------------------
# Simple counts for dashboard metrics
# ---------------------------------------------------------------------------
QUERY_POKEMON_COUNT = "SELECT COUNT(*) AS cnt FROM pokemon;"
QUERY_BATTLE_COUNT = "SELECT COUNT(*) AS cnt FROM battles;"
QUERY_ALL_POKEMON_NAMES = "SELECT name FROM pokemon ORDER BY id;"

# ---------------------------------------------------------------------------
# Battle Center: Head-to-head matchup between two specific Pokémon
# ---------------------------------------------------------------------------
QUERY_HEAD_TO_HEAD = """
SELECT
    b.attacker_name,
    b.defender_name,
    COUNT(*) AS total_matchups,
    SUM(CASE WHEN b.winner_name = b.attacker_name THEN 1 ELSE 0 END) AS attacker_wins,
    SUM(CASE WHEN b.winner_name = b.defender_name THEN 1 ELSE 0 END) AS defender_wins
FROM battles AS b
WHERE (b.attacker_name = ? AND b.defender_name = ?)
   OR (b.attacker_name = ? AND b.defender_name = ?)
GROUP BY b.attacker_name, b.defender_name;
"""

# ---------------------------------------------------------------------------
# Battle Center: Type effectiveness lookup (single pair)
# ---------------------------------------------------------------------------
QUERY_TYPE_EFFECTIVENESS = """
SELECT multiplier, effectiveness_label
FROM type_chart
WHERE attacking_type = ? AND defending_type = ?;
"""

# ---------------------------------------------------------------------------
# Battle Center: Recent battles between two specific Pokémon
# ---------------------------------------------------------------------------
QUERY_BATTLE_HISTORY = """
SELECT
    b.battle_id, b.attacker_name, b.defender_name, b.winner_name,
    b.type_multiplier, b.attacker_type, b.defender_type, b.battle_date
FROM battles AS b
WHERE (b.attacker_name = ? AND b.defender_name = ?)
   OR (b.attacker_name = ? AND b.defender_name = ?)
ORDER BY b.battle_date DESC
LIMIT 15;
"""

