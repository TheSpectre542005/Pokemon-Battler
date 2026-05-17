-- ============================================================================
-- FILE: 02_raw_win_rate.sql
-- PURPOSE: Calculate the naive (unadjusted) win rate for each Pokémon.
--          This is the BASELINE metric that most casual analyses would use.
--          It answers: "What percentage of battles did this Pokémon win
--          when it was the attacker?"
--
-- NOTE: This ranking is MISLEADING. High-BST Pokémon dominate because
--       they disproportionately faced weaker opponents with type
--       disadvantages. A Pokémon with 80% raw win rate that only fought
--       Grass-types is not truly elite. See query 04 for the corrected
--       version that accounts for opponent difficulty.
-- ============================================================================

-- CTE 1: Count total battles and wins per Pokémon (as attacker only).
-- Using CASE WHEN instead of a filtered COUNT to keep the logic transparent.
WITH win_counts AS (
    SELECT
        attacker_name                                           AS name,
        COUNT(*)                                                AS total_battles,
        SUM(CASE WHEN winner_name = attacker_name THEN 1 ELSE 0 END) AS wins
    FROM battles
    GROUP BY attacker_name
    -- Exclude Pokémon with fewer than 30 battles — small samples produce
    -- unreliable percentages (a coin flip on 4 battles = 100% or 0%).
    HAVING total_battles >= 30
),

-- CTE 2: Apply RANK() window function to create the leaderboard.
-- RANK() (not ROW_NUMBER()) so ties get the same position.
ranked AS (
    SELECT
        wc.name,
        p.primary_type,
        wc.total_battles,
        wc.wins,
        -- NULLIF guards against divide-by-zero, though the HAVING clause
        -- already guarantees total_battles >= 30. Belt-and-suspenders.
        ROUND(wc.wins * 100.0 / NULLIF(wc.total_battles, 0), 1) AS raw_win_pct,
        RANK() OVER (ORDER BY wc.wins * 100.0 / NULLIF(wc.total_battles, 0) DESC) AS overall_rank
    FROM win_counts AS wc
    INNER JOIN pokemon AS p ON wc.name = p.name
)

SELECT
    overall_rank,
    name,
    primary_type,
    total_battles,
    wins,
    raw_win_pct
FROM ranked
ORDER BY overall_rank ASC
LIMIT 20;
