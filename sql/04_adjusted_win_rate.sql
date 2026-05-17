-- ============================================================================
-- FILE: 04_adjusted_win_rate.sql — THE HEADLINE QUERY
-- ============================================================================
-- WHAT: Computes adjusted win rates for every Pokémon, ranked both within
--       their elemental type and globally, with an analyst classification tag.
--
-- WHY ADJUSTED > RAW: Raw win rate treats all victories equally. A win
--       against a type-disadvantaged opponent is "free" — it inflates the
--       record without proving strength. Adjusted win rate divides by the
--       average type multiplier to normalise for schedule difficulty.
--       This mirrors strength-of-schedule adjustment used in NCAA rankings.
--
-- CTE 1 (battle_with_types): Enriches each battle row with both combatants'
--       stats and the type effectiveness multiplier between them.
-- CTE 2 (pokemon_stats): Aggregates per-Pokémon: total battles, wins,
--       raw win %, adjusted win %, and average type multiplier.
-- CTE 3 (ranked): Applies RANK() within each type and PERCENT_RANK()
--       globally, then calculates the inflation_gap (raw − adjusted)
--       and assigns the analyst_tag classification.
--
-- The inflation_gap column is the core insight: positive values reveal
--       Pokémon whose reputations are propped up by easy matchups; negative
--       values reveal hidden gems who won despite unfavourable type draws.
-- ============================================================================

-- CTE 1: Enrich every battle with both combatants' types + the applicable
--         type effectiveness multiplier.
WITH battle_with_types AS (
    SELECT
        b.battle_id,
        b.attacker_name,
        b.defender_name,
        b.winner_name,
        p_att.primary_type                              AS attacker_type,
        p_def.primary_type                              AS defender_type,
        p_att.bst                                       AS attacker_bst,
        p_def.bst                                       AS defender_bst,

        -- Default to neutral (1.0) if the type pair isn't in the chart.
        COALESCE(t.multiplier, 1.0)                     AS type_mult
    FROM battles AS b
    INNER JOIN pokemon AS p_att ON b.attacker_name = p_att.name
    INNER JOIN pokemon AS p_def ON b.defender_name = p_def.name
    LEFT JOIN type_chart AS t
        ON t.attacking_type = p_att.primary_type
       AND t.defending_type = p_def.primary_type
),

-- CTE 2: Aggregate combat performance per Pokémon.
pokemon_stats AS (
    SELECT
        bwt.attacker_name                                                       AS pokemon_name,
        p.primary_type,
        COUNT(*)                                                                AS total_battles,

        -- Win count using conditional aggregation
        SUM(CASE WHEN bwt.winner_name = bwt.attacker_name THEN 1 ELSE 0 END)   AS wins,

        -- Raw (naive) win percentage
        ROUND(
            SUM(CASE WHEN bwt.winner_name = bwt.attacker_name THEN 1 ELSE 0 END)
                * 100.0
                / NULLIF(COUNT(*), 0),
            1
        )                                                                       AS raw_win_pct,

        -- Adjusted win percentage: normalise wins by average schedule difficulty.
        ROUND(
            (SUM(CASE WHEN bwt.winner_name = bwt.attacker_name THEN 1 ELSE 0 END)
                * 1.0
                / AVG(bwt.type_mult))
                * 100.0
                / NULLIF(COUNT(*), 0),
            1
        )                                                                       AS adjusted_win_pct,

        -- Average type multiplier — the "schedule strength" indicator.
        ROUND(AVG(bwt.type_mult), 3)                                            AS avg_type_mult

    FROM battle_with_types AS bwt
    INNER JOIN pokemon AS p ON bwt.attacker_name = p.name
    GROUP BY bwt.attacker_name, p.primary_type

    -- Minimum sample size filter: 30 battles prevents noisy outliers.
    HAVING COUNT(*) >= 30
),

-- CTE 3: Rank within type, rank globally, compute inflation gap, assign tags.
ranked AS (
    SELECT
        ps.pokemon_name,
        ps.primary_type,
        ps.total_battles,
        ps.raw_win_pct,
        ps.adjusted_win_pct,

        -- Inflation gap: positive = overrated (easy schedule inflated record),
        --                negative = underrated (hard schedule deflated record).
        ROUND(ps.raw_win_pct - ps.adjusted_win_pct, 1)                          AS inflation_gap,

        ps.avg_type_mult,

        -- Rank within the Pokémon's own element type (e.g., best Fire type).
        RANK() OVER (
            PARTITION BY ps.primary_type
            ORDER BY ps.adjusted_win_pct DESC
        )                                                                       AS rank_in_type,

        -- Global percentile position (0 = worst, 100 = best).
        ROUND(PERCENT_RANK() OVER (ORDER BY ps.adjusted_win_pct) * 100, 1)     AS overall_percentile,

        -- Analyst classification tag — turns numbers into narrative.
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
        END                                                                     AS analyst_tag

    FROM pokemon_stats AS ps
)

SELECT
    pokemon_name,
    primary_type,
    total_battles,
    raw_win_pct,
    adjusted_win_pct,
    inflation_gap,
    avg_type_mult,
    rank_in_type,
    overall_percentile,
    analyst_tag
FROM ranked
WHERE rank_in_type <= 3
ORDER BY adjusted_win_pct DESC;
