-- database/migrations/004_possession_factor.sql
-- Vista e funzione per calcolo fattore possesso
-- Eseguire in Supabase SQL Editor

-- 1. Vista statistiche possesso per squadra
CREATE OR REPLACE VIEW team_possession_stats AS
SELECT
    t.id AS team_id,
    t.name AS team_name,
    m.season,
    COUNT(DISTINCT m.id) AS matches_played,
    ROUND(AVG(ms.ball_possession)::NUMERIC, 1) AS avg_possession,
    -- Classificazione stile di gioco
    CASE
        WHEN AVG(ms.ball_possession) >= 55 THEN 'POSSESSION_HEAVY'
        WHEN AVG(ms.ball_possession) >= 50 THEN 'BALANCED'
        WHEN AVG(ms.ball_possession) >= 45 THEN 'COUNTER_ATTACK'
        ELSE 'DEFENSIVE'
    END AS play_style,
    ROUND(AVG(ms.fouls_committed)::NUMERIC, 1) AS avg_fouls_committed
FROM teams t
JOIN match_statistics ms ON t.id = ms.team_id
JOIN matches m ON ms.match_id = m.id
WHERE m.status = 'FINISHED'
AND ms.ball_possession IS NOT NULL
GROUP BY t.id, t.name, m.season
HAVING COUNT(DISTINCT m.id) >= 3;  -- Minimo 3 partite per essere significativo

COMMENT ON VIEW team_possession_stats IS 'Statistiche possesso e stile di gioco per squadra/stagione';

-- 2. Funzione per calcolare il fattore possesso tra due squadre
-- Squadre con meno possesso tendono a commettere più falli = più rischio cartellini
CREATE OR REPLACE FUNCTION get_possession_factor(
    p_home_team_name TEXT,
    p_away_team_name TEXT,
    p_season TEXT DEFAULT '2025-2026'
)
RETURNS TABLE (
    home_team TEXT,
    home_avg_possession NUMERIC,
    home_play_style TEXT,
    home_possession_factor NUMERIC,
    away_team TEXT,
    away_avg_possession NUMERIC,
    away_play_style TEXT,
    away_possession_factor NUMERIC,
    expected_possession_diff NUMERIC
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_home_poss NUMERIC;
    v_away_poss NUMERIC;
    v_home_style TEXT;
    v_away_style TEXT;
    v_home_factor NUMERIC;
    v_away_factor NUMERIC;
BEGIN
    -- Ottieni possesso medio squadra casa
    SELECT tps.avg_possession, tps.play_style INTO v_home_poss, v_home_style
    FROM team_possession_stats tps
    WHERE LOWER(tps.team_name) LIKE '%' || LOWER(p_home_team_name) || '%'
    AND tps.season = p_season
    LIMIT 1;

    -- Ottieni possesso medio squadra trasferta
    SELECT tps.avg_possession, tps.play_style INTO v_away_poss, v_away_style
    FROM team_possession_stats tps
    WHERE LOWER(tps.team_name) LIKE '%' || LOWER(p_away_team_name) || '%'
    AND tps.season = p_season
    LIMIT 1;

    -- Default se non trovato
    v_home_poss := COALESCE(v_home_poss, 50);
    v_away_poss := COALESCE(v_away_poss, 50);
    v_home_style := COALESCE(v_home_style, 'BALANCED');
    v_away_style := COALESCE(v_away_style, 'BALANCED');

    -- Calcola fattore possesso
    -- Logica: squadre con meno possesso commettono più falli
    -- 50% possesso = fattore 1.0
    -- Ogni 5% sotto 50% = +5% rischio (max +15%)
    -- Ogni 5% sopra 50% = -3% rischio (max -15%)
    v_home_factor := 1 + (50 - v_home_poss) * 0.01;
    v_away_factor := 1 + (50 - v_away_poss) * 0.01;

    -- Limita tra 0.85 e 1.15
    v_home_factor := GREATEST(0.85, LEAST(1.15, v_home_factor));
    v_away_factor := GREATEST(0.85, LEAST(1.15, v_away_factor));

    RETURN QUERY SELECT
        p_home_team_name,
        v_home_poss,
        v_home_style,
        ROUND(v_home_factor, 2),
        p_away_team_name,
        v_away_poss,
        v_away_style,
        ROUND(v_away_factor, 2),
        ROUND(v_home_poss - v_away_poss, 1);
END;
$$;

COMMENT ON FUNCTION get_possession_factor IS 'Calcola fattori possesso per due squadre (0.85-1.15)';

-- 3. Vista riepilogativa stili di gioco (utile per dashboard)
CREATE OR REPLACE VIEW team_play_styles AS
SELECT
    team_name,
    season,
    avg_possession,
    play_style,
    avg_fouls_committed,
    matches_played
FROM team_possession_stats
ORDER BY season DESC, avg_possession DESC;

COMMENT ON VIEW team_play_styles IS 'Riepilogo stili di gioco squadre';

-- 4. Verifica
SELECT * FROM team_possession_stats WHERE season = '2025-2026' ORDER BY avg_possession DESC LIMIT 10;
SELECT * FROM get_possession_factor('Inter', 'Napoli', '2025-2026');
SELECT * FROM get_possession_factor('Manchester City', 'Liverpool', '2025-2026');
SELECT * FROM team_play_styles WHERE season = '2025-2026' LIMIT 20;
