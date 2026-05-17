-- ============================================================================
-- FILE: 03_type_matchup_join.sql
-- PURPOSE: Intermediate complexity query that joins battles to the type
--          chart, computing both raw AND adjusted win rates side-by-side.
--
--          The adjustment logic:
--          If a Pokémon's average type multiplier is > 1.0, it means it
--          faced opponents it had a type advantage against MORE often than
--          not. Its raw win rate is therefore INFLATED and the adjusted
--          rate will be lower (deflated to account for the easy schedule).
--
--          Conversely, if avg_type_mult < 1.0, the Pokémon fought uphill
--          against type-resistant opponents, and its adjusted rate will be
--          HIGHER than raw (inflated to credit the tough schedule).
--
--          Formula: adjusted_win_pct = (wins / avg_type_mult) × 100 / total
--          This is analogous to strength-of-schedule adjustment in sports.
-- ============================================================================

WITH battle_details AS (
    SELECT
        b.attacker_name,
        b.defender_name,
        b.winner_name,
        p_att.primary_type                              AS attacker_type,
        p_def.primary_type                              AS defender_type,

        -- COALESCE handles edge cases where the type chart might not have
        -- coverage (e.g., if the CSV load was partial). Default to 1.0 = neutral.
        COALESCE(t.multiplier, 1.0)                     AS type_mult
    FROM battles AS b

    -- Join to pokemon TWICE: once for the attacker, once for the defender.
    -- This is a common pattern in match/transaction tables.
    INNER JOIN pokemon AS p_att ON b.attacker_name = p_att.name
    INNER JOIN pokemon AS p_def ON b.defender_name = p_def.name

    -- LEFT JOIN to the type chart so we don't drop battles where the
    -- type pair might be missing (defensive coding).
    LEFT JOIN type_chart AS t
        ON t.attacking_type = p_att.primary_type
       AND t.defending_type = p_def.primary_type
),

aggregated AS (
    SELECT
        attacker_name                                                           AS name,
        COUNT(*)                                                                AS total_battles,
        SUM(CASE WHEN winner_name = attacker_name THEN 1 ELSE 0 END)           AS wins,

        -- Average type multiplier across all of this Pokémon's battles.
        -- > 1.0 means easy schedule (mostly super-effective matchups).
        -- < 1.0 means hard schedule (mostly resisted/immune matchups).
        ROUND(AVG(type_mult), 3)                                                AS avg_type_mult
    FROM battle_details
    GROUP BY attacker_name
    HAVING COUNT(*) >= 30
)

SELECT
    a.name,
    p.primary_type,
    a.total_battles,
    a.wins,

    -- Raw win rate: the naive metric that doesn't account for difficulty.
    ROUND(a.wins * 100.0 / NULLIF(a.total_battles, 0), 1)                      AS raw_win_pct,

    -- Adjusted win rate: deflate/inflate wins based on average opponent difficulty.
    -- Dividing wins by avg_type_mult penalises easy schedules and rewards hard ones.
    ROUND((a.wins * 1.0 / a.avg_type_mult) * 100.0 / NULLIF(a.total_battles, 0), 1) AS adjusted_win_pct,

    a.avg_type_mult
FROM aggregated AS a
INNER JOIN pokemon AS p ON a.name = p.name
ORDER BY adjusted_win_pct DESC
LIMIT 25;
