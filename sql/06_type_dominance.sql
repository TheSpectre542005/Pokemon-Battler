-- ============================================================================
-- FILE: 06_type_dominance.sql
-- PURPOSE: This is the macro view — instead of individual Pokémon, we see
--          which elemental types are structurally dominant in the meta.
--
--          We first compute per-Pokémon adjusted win rates (CTE 1–2),
--          then aggregate those up to the type level using AVG. This
--          prevents high-sample Pokémon from drowning out low-sample ones
--          within the same type — each Pokémon gets equal voice.
-- ============================================================================

-- CTE 1: Enrich battles with type effectiveness data (same as Query 04)
WITH battle_with_types AS (
    SELECT
        b.attacker_name,
        b.winner_name,
        p_att.primary_type                              AS attacker_type,
        COALESCE(t.multiplier, 1.0)                     AS type_mult
    FROM battles AS b
    INNER JOIN pokemon AS p_att ON b.attacker_name = p_att.name
    INNER JOIN pokemon AS p_def ON b.defender_name = p_def.name
    LEFT JOIN type_chart AS t
        ON t.attacking_type = p_att.primary_type
       AND t.defending_type = p_def.primary_type
),

-- CTE 2: Per-Pokémon stats (same aggregation pattern as Query 04)
pokemon_stats AS (
    SELECT
        bwt.attacker_name                                                       AS pokemon_name,
        bwt.attacker_type                                                       AS primary_type,
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
        )                                                                       AS adjusted_win_pct
    FROM battle_with_types AS bwt
    GROUP BY bwt.attacker_name, bwt.attacker_type
    HAVING COUNT(*) >= 10  -- Lower threshold at type level to include more data
),

-- CTE 3: Aggregate from Pokémon level up to Type level.
-- Using AVG of per-Pokémon rates (not SUM of wins / SUM of battles) so
-- each Pokémon contributes equally regardless of sample size.
type_aggregated AS (
    SELECT
        ps.primary_type,

        -- Total battles across all Pokémon of this type
        SUM(ps.total_battles)                                       AS total_battles_as_attacker,

        -- Total wins across all Pokémon of this type
        SUM(ps.wins)                                                AS total_wins,

        -- Type-level raw win %: sum of wins / sum of battles
        ROUND(SUM(ps.wins) * 100.0
              / NULLIF(SUM(ps.total_battles), 0), 1)                AS raw_type_win_pct,

        -- Average of individual Pokémon adjusted win rates within this type
        ROUND(AVG(ps.adjusted_win_pct), 1)                          AS avg_type_adjusted_win_pct,

        -- How many Pokémon of this type had enough battles to be included
        COUNT(*)                                                    AS pokemon_count
    FROM pokemon_stats AS ps
    GROUP BY ps.primary_type
)

SELECT
    ta.primary_type,
    ta.total_battles_as_attacker,
    ta.total_wins,
    ta.raw_type_win_pct,
    ta.avg_type_adjusted_win_pct,
    ta.pokemon_count,

    -- Global type ranking by adjusted performance
    RANK() OVER (ORDER BY ta.avg_type_adjusted_win_pct DESC)        AS type_rank,

    -- Qualitative classification for dashboard display
    CASE
        WHEN ta.avg_type_adjusted_win_pct >= 55 THEN 'DOMINANT'
        WHEN ta.avg_type_adjusted_win_pct >= 50 THEN 'STRONG'
        WHEN ta.avg_type_adjusted_win_pct >= 45 THEN 'BALANCED'
        ELSE 'WEAK'
    END                                                             AS type_verdict

FROM type_aggregated AS ta
ORDER BY type_rank ASC;
