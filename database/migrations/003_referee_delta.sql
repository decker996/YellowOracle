-- database/migrations/003_referee_delta.sql
-- Vista e funzione per outlier detection arbitri
-- Eseguire in Supabase SQL Editor

-- 1. Vista che confronta ogni arbitro con la media della sua lega
CREATE OR REPLACE VIEW referee_league_comparison AS
WITH league_averages AS (
    -- Calcola media gialli per partita per ogni competizione
    SELECT
        c.code AS competition_code,
        AVG(
            (SELECT COUNT(*) FROM match_events me
             WHERE me.match_id = m.id AND me.event_type = 'YELLOW_CARD')
        ) AS league_avg_yellows
    FROM matches m
    JOIN competitions c ON m.competition_id = c.id
    WHERE m.status = 'FINISHED'
    AND m.season = '2025-2026'
    GROUP BY c.code
),
referee_by_league AS (
    -- Calcola media gialli per ogni arbitro in ogni competizione
    SELECT
        r.id AS referee_id,
        r.name AS referee_name,
        c.code AS competition_code,
        COUNT(DISTINCT m.id) AS matches_in_league,
        AVG(
            (SELECT COUNT(*) FROM match_events me
             WHERE me.match_id = m.id AND me.event_type = 'YELLOW_CARD')
        ) AS ref_avg_yellows
    FROM referees r
    JOIN matches m ON r.id = m.referee_id
    JOIN competitions c ON m.competition_id = c.id
    WHERE m.status = 'FINISHED'
    AND m.season = '2025-2026'
    GROUP BY r.id, r.name, c.code
)
SELECT
    rbl.referee_id,
    rbl.referee_name,
    rbl.competition_code,
    rbl.matches_in_league,
    ROUND(rbl.ref_avg_yellows::NUMERIC, 2) AS ref_avg_yellows,
    ROUND(la.league_avg_yellows::NUMERIC, 2) AS league_avg_yellows,
    ROUND((rbl.ref_avg_yellows - la.league_avg_yellows)::NUMERIC, 2) AS ref_league_delta,
    -- Classificazione outlier
    CASE
        WHEN rbl.ref_avg_yellows - la.league_avg_yellows > 1.0 THEN 'STRICT_OUTLIER'
        WHEN rbl.ref_avg_yellows - la.league_avg_yellows < -1.0 THEN 'LENIENT_OUTLIER'
        WHEN rbl.ref_avg_yellows - la.league_avg_yellows > 0.5 THEN 'ABOVE_AVERAGE'
        WHEN rbl.ref_avg_yellows - la.league_avg_yellows < -0.5 THEN 'BELOW_AVERAGE'
        ELSE 'AVERAGE'
    END AS referee_profile
FROM referee_by_league rbl
JOIN league_averages la ON rbl.competition_code = la.competition_code
WHERE rbl.matches_in_league >= 3  -- Minimo 3 partite per essere significativo
ORDER BY ref_league_delta DESC;

COMMENT ON VIEW referee_league_comparison IS 'Confronto arbitri vs media lega con classificazione outlier';

-- 2. Funzione per ottenere il profilo di un arbitro
CREATE OR REPLACE FUNCTION get_referee_profile(p_referee_name TEXT)
RETURNS TABLE (
    referee_name TEXT,
    competition_code VARCHAR(10),
    matches_in_league BIGINT,
    ref_avg_yellows NUMERIC,
    league_avg_yellows NUMERIC,
    ref_league_delta NUMERIC,
    referee_profile TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        rlc.referee_name::TEXT,
        rlc.competition_code,
        rlc.matches_in_league,
        rlc.ref_avg_yellows,
        rlc.league_avg_yellows,
        rlc.ref_league_delta,
        rlc.referee_profile::TEXT
    FROM referee_league_comparison rlc
    WHERE LOWER(rlc.referee_name) LIKE '%' || LOWER(p_referee_name) || '%'
    ORDER BY rlc.matches_in_league DESC
    LIMIT 1;
END;
$$;

COMMENT ON FUNCTION get_referee_profile IS 'Restituisce il profilo outlier di un arbitro';

-- 3. Funzione per calcolare il moltiplicatore arbitro
CREATE OR REPLACE FUNCTION get_referee_multiplier(p_referee_name TEXT)
RETURNS NUMERIC
LANGUAGE plpgsql
AS $$
DECLARE
    v_profile TEXT;
    v_delta NUMERIC;
BEGIN
    SELECT referee_profile, ref_league_delta INTO v_profile, v_delta
    FROM referee_league_comparison
    WHERE LOWER(referee_name) LIKE '%' || LOWER(p_referee_name) || '%'
    ORDER BY matches_in_league DESC
    LIMIT 1;

    IF v_profile IS NULL THEN
        RETURN 1.0;
    END IF;

    -- Calcola moltiplicatore basato sul delta
    -- Ogni +0.5 gialli sopra media = +5% rischio, max ±15%
    RETURN GREATEST(0.85, LEAST(1.15, 1.0 + (v_delta * 0.10)));
END;
$$;

COMMENT ON FUNCTION get_referee_multiplier IS 'Calcola moltiplicatore rischio basato su profilo arbitro (0.85-1.15)';

-- 4. Verifica
SELECT * FROM referee_league_comparison WHERE competition_code = 'SA' LIMIT 10;
SELECT * FROM get_referee_profile('Maresca');
SELECT get_referee_multiplier('Maresca') AS maresca_multiplier;
