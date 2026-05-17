-- ============================================================================
-- FILE: 05_overrated_index.sql
-- PURPOSE: Surfaces the most interesting stories in the data — the Pokémon
--          whose reputations don't match reality. This is the narrative
--          query: which Pokémon are living off easy matchups (OVERRATED)
--          and which are hidden gems winning despite the odds (UNDERRATED)?
--
--          We use UNION ALL to combine the top 5 in each category into a
--          single 10-row result set with a category label, making it ideal
--          for a split-panel dashboard display.
-- ============================================================================

-- Reuse the same 3-CTE pipeline from Query 04 (intentional — demonstrates
-- consistent analytical methodology and shows the CTEs are composable).

WITH battle_with_types AS (
    SELECT
        b.battle_id,
        b.attacker_name,
        b.defender_name,
        b.winner_name,
        p_att.primary_type                              AS attacker_type,
        p_def.primary_type                              AS defender_type,
        COALESCE(t.multiplier, 1.0)                     AS type_mult
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
    HAVING COUNT(*) >= 30
),

-- Add inflation gap and sprite URL for dashboard display
with_gap AS (
    SELECT
        ps.pokemon_name,
        ps.primary_type,
        ps.total_battles,
        ps.raw_win_pct,
        ps.adjusted_win_pct,
        ROUND(ps.raw_win_pct - ps.adjusted_win_pct, 1)     AS inflation_gap,
        ps.avg_type_mult,
        p.sprite_url
    FROM pokemon_stats AS ps
    INNER JOIN pokemon AS p ON ps.pokemon_name = p.name
)

SELECT * FROM (
    SELECT
        'MOST OVERRATED'    AS category,
        pokemon_name,
        primary_type,
        total_battles,
        raw_win_pct,
        adjusted_win_pct,
        inflation_gap,
        sprite_url
    FROM with_gap
    ORDER BY inflation_gap DESC
    LIMIT 5
)

-- Combine with UNION ALL (not UNION — we want to preserve all rows,
-- and the two subsets are guaranteed disjoint).
UNION ALL

SELECT * FROM (
    SELECT
        'MOST UNDERRATED'   AS category,
        pokemon_name,
        primary_type,
        total_battles,
        raw_win_pct,
        adjusted_win_pct,
        inflation_gap,
        sprite_url
    FROM with_gap
    ORDER BY inflation_gap ASC
    LIMIT 5
);
