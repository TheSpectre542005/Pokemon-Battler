-- ============================================================================
-- FILE: 01_sanity_check.sql
-- PURPOSE: Validate our data load and check for type distribution bias
--          before we run any analysis. This is the first query an analyst
--          should run after a fresh database load — it confirms the ETL
--          pipeline produced sensible results and surfaces any skew in
--          how battles were distributed across Pokémon types.
-- ============================================================================

SELECT
    p.primary_type,

    -- How many battles featured an attacker of this type?
    -- Uneven distribution here would bias our win-rate calculations.
    COUNT(*)                            AS total_battles,

    -- How many distinct Pokémon of this type appeared as attackers?
    -- Low count means the type's stats are driven by a few individuals.
    COUNT(DISTINCT b.attacker_name)     AS distinct_attackers,

    -- Average Base Stat Total for attackers of this type.
    -- Types with naturally high BST (Dragon, Psychic) will show up here.
    ROUND(AVG(p.bst), 1)               AS avg_bst

FROM battles AS b
-- Join to the pokemon table to get the attacker's primary type and BST.
-- We join on name (not ID) because the battles table stores names directly.
INNER JOIN pokemon AS p
    ON b.attacker_name = p.name

GROUP BY p.primary_type

-- Show the most battle-active types first — this helps us quickly spot
-- over-represented types that could skew aggregate statistics.
ORDER BY total_battles DESC;
