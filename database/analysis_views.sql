-- YellowOracle - Viste e Funzioni per Analisi Cartellini
-- Esegui questo script nell'SQL Editor di Supabase DOPO schema_v2.sql
-- Data: 2026-01-26

-- ============================================
-- VISTE PER ANALISI
-- ============================================

-- Drop viste esistenti se presenti
DROP VIEW IF EXISTS player_season_cards CASCADE;
DROP VIEW IF EXISTS referee_player_history CASCADE;
DROP VIEW IF EXISTS head_to_head_player_cards CASCADE;
DROP VIEW IF EXISTS match_analysis_summary CASCADE;

-- Drop funzioni esistenti se presenti
DROP FUNCTION IF EXISTS get_player_season_stats(TEXT, TEXT);
DROP FUNCTION IF EXISTS get_referee_player_cards(TEXT, TEXT, TEXT);
DROP FUNCTION IF EXISTS get_head_to_head_cards(TEXT, TEXT, TEXT);

-- ============================================
-- VISTA 1: Statistiche cartellini per giocatore/stagione
-- ============================================

CREATE VIEW player_season_cards AS
SELECT
    p.id AS player_id,
    p.name AS player_name,
    p.position,
    t.id AS team_id,
    t.name AS team_name,
    t.short_name AS team_short,
    m.season,
    COUNT(DISTINCT m.id) AS matches_played,
    COUNT(CASE WHEN me.event_type = 'YELLOW_CARD' THEN 1 END) AS yellow_cards,
    COUNT(CASE WHEN me.event_type = 'RED_CARD' THEN 1 END) AS red_cards,
    -- Minuti totali dalla tabella lineups (se disponibili)
    COALESCE(SUM(l.minutes_played), COUNT(DISTINCT m.id) * 90) AS minutes_played,
    -- Media cartellini gialli per 90 minuti
    CASE
        WHEN COALESCE(SUM(l.minutes_played), COUNT(DISTINCT m.id) * 90) >= 90 THEN
            ROUND(
                COUNT(CASE WHEN me.event_type = 'YELLOW_CARD' THEN 1 END)::DECIMAL /
                (COALESCE(SUM(l.minutes_played), COUNT(DISTINCT m.id) * 90)::DECIMAL / 90),
                2
            )
        ELSE NULL
    END AS yellows_per_90
FROM players p
JOIN match_events me ON p.id = me.player_id
JOIN matches m ON me.match_id = m.id
JOIN teams t ON me.team_id = t.id
LEFT JOIN lineups l ON l.player_id = p.id AND l.match_id = m.id
WHERE me.event_type IN ('YELLOW_CARD', 'RED_CARD')
GROUP BY p.id, p.name, p.position, t.id, t.name, t.short_name, m.season
ORDER BY m.season DESC, yellow_cards DESC;


-- ============================================
-- VISTA 2: Storico arbitro-giocatore per squadre specifiche
-- Questa vista mostra tutti i cartellini dati da ogni arbitro
-- Le funzioni filtreranno per squadre specifiche
-- ============================================

CREATE VIEW referee_player_history AS
SELECT
    r.id AS referee_id,
    r.name AS referee_name,
    p.id AS player_id,
    p.name AS player_name,
    t.id AS team_id,
    t.name AS team_name,
    m.home_team_id,
    m.away_team_id,
    COUNT(CASE WHEN me.event_type = 'YELLOW_CARD' THEN 1 END) AS yellow_cards,
    COUNT(CASE WHEN me.event_type = 'RED_CARD' THEN 1 END) AS red_cards,
    COUNT(DISTINCT m.id) AS matches_with_referee,
    MAX(m.match_date) AS last_booking_date,
    -- Lista partite con cartellino (JSON)
    JSON_AGG(
        JSON_BUILD_OBJECT(
            'date', m.match_date,
            'match', CONCAT(ht.name, ' vs ', at.name),
            'card', me.event_type,
            'minute', me.minute
        ) ORDER BY m.match_date DESC
    ) AS booking_details
FROM referees r
JOIN matches m ON r.id = m.referee_id
JOIN match_events me ON m.id = me.match_id AND me.event_type IN ('YELLOW_CARD', 'RED_CARD')
JOIN players p ON me.player_id = p.id
JOIN teams t ON me.team_id = t.id
JOIN teams ht ON m.home_team_id = ht.id
JOIN teams at ON m.away_team_id = at.id
GROUP BY r.id, r.name, p.id, p.name, t.id, t.name, m.home_team_id, m.away_team_id
ORDER BY yellow_cards DESC;


-- ============================================
-- VISTA 3: Cartellini negli scontri diretti
-- ============================================

CREATE VIEW head_to_head_player_cards AS
SELECT
    p.id AS player_id,
    p.name AS player_name,
    t.id AS player_team_id,
    t.name AS player_team_name,
    ht.id AS home_team_id,
    ht.name AS home_team_name,
    at.id AS away_team_id,
    at.name AS away_team_name,
    m.id AS match_id,
    m.match_date,
    m.season,
    r.name AS referee_name,
    -- Cartellini in questa partita
    COUNT(CASE WHEN me.event_type = 'YELLOW_CARD' THEN 1 END) AS yellows_in_match,
    COUNT(CASE WHEN me.event_type = 'RED_CARD' THEN 1 END) AS reds_in_match,
    -- Dettagli cartellini
    JSON_AGG(
        CASE WHEN me.event_type IS NOT NULL THEN
            JSON_BUILD_OBJECT(
                'card', me.event_type,
                'minute', me.minute
            )
        ELSE NULL END
    ) FILTER (WHERE me.event_type IS NOT NULL) AS card_details
FROM matches m
JOIN teams ht ON m.home_team_id = ht.id
JOIN teams at ON m.away_team_id = at.id
LEFT JOIN referees r ON m.referee_id = r.id
-- Giocatori che hanno partecipato alla partita
JOIN lineups l ON l.match_id = m.id
JOIN players p ON l.player_id = p.id
JOIN teams t ON l.team_id = t.id
-- Eventuali cartellini
LEFT JOIN match_events me ON me.match_id = m.id
    AND me.player_id = p.id
    AND me.event_type IN ('YELLOW_CARD', 'RED_CARD')
WHERE m.status = 'FINISHED'
GROUP BY p.id, p.name, t.id, t.name, ht.id, ht.name, at.id, at.name,
         m.id, m.match_date, m.season, r.name
ORDER BY m.match_date DESC;


-- ============================================
-- FUNZIONE 1: Statistiche stagionali giocatore
-- ============================================

CREATE OR REPLACE FUNCTION get_player_season_stats(
    p_player_name TEXT,
    p_season TEXT DEFAULT NULL
)
RETURNS TABLE (
    player_name TEXT,
    team_name TEXT,
    season VARCHAR(10),
    matches_played BIGINT,
    yellow_cards BIGINT,
    red_cards BIGINT,
    minutes_played NUMERIC,
    yellows_per_90 NUMERIC
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        psc.player_name::TEXT,
        psc.team_name::TEXT,
        psc.season,
        psc.matches_played,
        psc.yellow_cards,
        psc.red_cards,
        psc.minutes_played,
        psc.yellows_per_90
    FROM player_season_cards psc
    WHERE LOWER(psc.player_name) LIKE '%' || LOWER(p_player_name) || '%'
    AND (p_season IS NULL OR psc.season = p_season)
    ORDER BY psc.season DESC, psc.yellow_cards DESC;
END;
$$;


-- ============================================
-- FUNZIONE 2: Storico arbitro-giocatore per squadre
-- ============================================

CREATE OR REPLACE FUNCTION get_referee_player_cards(
    p_referee_name TEXT,
    p_team1_name TEXT,
    p_team2_name TEXT
)
RETURNS TABLE (
    referee_name TEXT,
    player_name TEXT,
    team_name TEXT,
    times_booked BIGINT,
    matches_with_referee BIGINT,
    booking_percentage NUMERIC,
    last_booking DATE,
    booking_details JSON
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_team1_id UUID;
    v_team2_id UUID;
    v_referee_id UUID;
BEGIN
    -- Trova gli ID delle squadre (ricerca fuzzy)
    SELECT id INTO v_team1_id FROM teams
    WHERE LOWER(name) LIKE '%' || LOWER(p_team1_name) || '%'
    LIMIT 1;

    SELECT id INTO v_team2_id FROM teams
    WHERE LOWER(name) LIKE '%' || LOWER(p_team2_name) || '%'
    LIMIT 1;

    SELECT id INTO v_referee_id FROM referees
    WHERE LOWER(name) LIKE '%' || LOWER(p_referee_name) || '%'
    LIMIT 1;

    RETURN QUERY
    WITH referee_team_matches AS (
        -- Partite dove l'arbitro ha arbitrato una delle due squadre
        SELECT DISTINCT m.id AS match_id
        FROM matches m
        WHERE m.referee_id = v_referee_id
        AND (m.home_team_id IN (v_team1_id, v_team2_id)
             OR m.away_team_id IN (v_team1_id, v_team2_id))
    ),
    player_bookings AS (
        -- Cartellini dei giocatori in quelle partite
        SELECT
            p.id AS player_id,
            p.name AS player_name,
            t.name AS team_name,
            COUNT(CASE WHEN me.event_type = 'YELLOW_CARD' THEN 1 END) AS yellows,
            COUNT(CASE WHEN me.event_type = 'RED_CARD' THEN 1 END) AS reds,
            COUNT(DISTINCT m.id) AS total_matches,
            MAX(m.match_date)::DATE AS last_booking,
            JSON_AGG(
                JSON_BUILD_OBJECT(
                    'date', m.match_date,
                    'match', CONCAT(ht.name, ' vs ', at.name),
                    'card', me.event_type,
                    'minute', me.minute
                ) ORDER BY m.match_date DESC
            ) FILTER (WHERE me.event_type IS NOT NULL) AS details
        FROM referee_team_matches rtm
        JOIN matches m ON rtm.match_id = m.id
        JOIN lineups l ON l.match_id = m.id AND l.team_id IN (v_team1_id, v_team2_id)
        JOIN players p ON l.player_id = p.id
        JOIN teams t ON l.team_id = t.id
        JOIN teams ht ON m.home_team_id = ht.id
        JOIN teams at ON m.away_team_id = at.id
        LEFT JOIN match_events me ON me.match_id = m.id
            AND me.player_id = p.id
            AND me.event_type IN ('YELLOW_CARD', 'RED_CARD')
        GROUP BY p.id, p.name, t.name
    )
    SELECT
        r.name::TEXT AS referee_name,
        pb.player_name::TEXT,
        pb.team_name::TEXT,
        (pb.yellows + pb.reds) AS times_booked,
        pb.total_matches AS matches_with_referee,
        CASE
            WHEN pb.total_matches > 0 THEN
                ROUND(((pb.yellows + pb.reds)::NUMERIC / pb.total_matches::NUMERIC) * 100, 1)
            ELSE 0
        END AS booking_percentage,
        pb.last_booking,
        pb.details AS booking_details
    FROM player_bookings pb
    CROSS JOIN referees r
    WHERE r.id = v_referee_id
    AND (pb.yellows + pb.reds) > 0
    ORDER BY (pb.yellows + pb.reds) DESC, pb.total_matches DESC;
END;
$$;


-- ============================================
-- FUNZIONE 3: Cartellini scontri diretti
-- ============================================

CREATE OR REPLACE FUNCTION get_head_to_head_cards(
    p_player_name TEXT,
    p_team1_name TEXT,
    p_team2_name TEXT
)
RETURNS TABLE (
    player_name TEXT,
    team_name TEXT,
    opponent TEXT,
    total_h2h_matches BIGINT,
    total_yellows BIGINT,
    total_reds BIGINT,
    card_percentage NUMERIC,
    match_details JSON
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_team1_id UUID;
    v_team2_id UUID;
    v_player_id UUID;
BEGIN
    -- Trova gli ID (ricerca fuzzy)
    SELECT id INTO v_team1_id FROM teams
    WHERE LOWER(name) LIKE '%' || LOWER(p_team1_name) || '%'
    LIMIT 1;

    SELECT id INTO v_team2_id FROM teams
    WHERE LOWER(name) LIKE '%' || LOWER(p_team2_name) || '%'
    LIMIT 1;

    SELECT id INTO v_player_id FROM players
    WHERE LOWER(name) LIKE '%' || LOWER(p_player_name) || '%'
    LIMIT 1;

    RETURN QUERY
    WITH h2h_matches AS (
        -- Scontri diretti tra le due squadre
        SELECT m.id AS match_id, m.match_date, m.season,
               ht.name AS home_team, at.name AS away_team,
               r.name AS referee_name
        FROM matches m
        JOIN teams ht ON m.home_team_id = ht.id
        JOIN teams at ON m.away_team_id = at.id
        LEFT JOIN referees r ON m.referee_id = r.id
        WHERE m.status = 'FINISHED'
        AND (
            (m.home_team_id = v_team1_id AND m.away_team_id = v_team2_id)
            OR (m.home_team_id = v_team2_id AND m.away_team_id = v_team1_id)
        )
    ),
    player_h2h AS (
        -- Partecipazione del giocatore a questi scontri
        SELECT
            h2h.match_id,
            h2h.match_date,
            h2h.season,
            h2h.home_team,
            h2h.away_team,
            h2h.referee_name,
            p.name AS player_name,
            t.name AS player_team,
            CASE
                WHEN t.id = v_team1_id THEN (SELECT name FROM teams WHERE id = v_team2_id)
                ELSE (SELECT name FROM teams WHERE id = v_team1_id)
            END AS opponent_name,
            COUNT(CASE WHEN me.event_type = 'YELLOW_CARD' THEN 1 END) AS yellows,
            COUNT(CASE WHEN me.event_type = 'RED_CARD' THEN 1 END) AS reds,
            me.minute AS card_minute
        FROM h2h_matches h2h
        JOIN lineups l ON l.match_id = h2h.match_id AND l.player_id = v_player_id
        JOIN players p ON p.id = v_player_id
        JOIN teams t ON l.team_id = t.id
        LEFT JOIN match_events me ON me.match_id = h2h.match_id
            AND me.player_id = v_player_id
            AND me.event_type IN ('YELLOW_CARD', 'RED_CARD')
        GROUP BY h2h.match_id, h2h.match_date, h2h.season, h2h.home_team,
                 h2h.away_team, h2h.referee_name, p.name, t.name, t.id, me.minute
    )
    SELECT
        MAX(ph.player_name)::TEXT AS player_name,
        MAX(ph.player_team)::TEXT AS team_name,
        MAX(ph.opponent_name)::TEXT AS opponent,
        COUNT(DISTINCT ph.match_id) AS total_h2h_matches,
        SUM(ph.yellows) AS total_yellows,
        SUM(ph.reds) AS total_reds,
        CASE
            WHEN COUNT(DISTINCT ph.match_id) > 0 THEN
                ROUND((SUM(ph.yellows) + SUM(ph.reds))::NUMERIC / COUNT(DISTINCT ph.match_id)::NUMERIC * 100, 1)
            ELSE 0
        END AS card_percentage,
        JSON_AGG(
            JSON_BUILD_OBJECT(
                'date', ph.match_date,
                'season', ph.season,
                'match', CONCAT(ph.home_team, ' vs ', ph.away_team),
                'referee', ph.referee_name,
                'yellow', ph.yellows > 0,
                'red', ph.reds > 0,
                'minute', ph.card_minute
            ) ORDER BY ph.match_date DESC
        ) AS match_details
    FROM player_h2h ph
    GROUP BY ph.player_name;
END;
$$;


-- ============================================
-- VISTA 4: Riepilogo analisi partita
-- Combina tutte le info per una singola partita
-- ============================================

CREATE VIEW match_analysis_summary AS
SELECT
    p.id AS player_id,
    p.name AS player_name,
    p.position,
    t.id AS team_id,
    t.name AS team_name,
    -- Statistiche stagione corrente
    COALESCE(psc.yellow_cards, 0) AS season_yellows,
    COALESCE(psc.red_cards, 0) AS season_reds,
    COALESCE(psc.matches_played, 0) AS season_matches,
    psc.yellows_per_90 AS season_yellows_per_90
FROM players p
JOIN teams t ON p.current_team_id = t.id
LEFT JOIN player_season_cards psc ON psc.player_id = p.id AND psc.season = '2025-2026'
ORDER BY psc.yellows_per_90 DESC NULLS LAST;


-- ============================================
-- COMMENTI E DOCUMENTAZIONE
-- ============================================

COMMENT ON VIEW player_season_cards IS 'Statistiche cartellini per giocatore raggruppate per stagione';
COMMENT ON VIEW referee_player_history IS 'Storico completo cartellini arbitro-giocatore';
COMMENT ON VIEW head_to_head_player_cards IS 'Cartellini giocatori negli scontri diretti';
COMMENT ON VIEW match_analysis_summary IS 'Riepilogo per analisi pre-partita';

COMMENT ON FUNCTION get_player_season_stats IS 'Restituisce statistiche cartellini di un giocatore per stagione. Usa ricerca fuzzy sul nome.';
COMMENT ON FUNCTION get_referee_player_cards IS 'Restituisce storico ammonizioni arbitro verso giocatori delle squadre specificate.';
COMMENT ON FUNCTION get_head_to_head_cards IS 'Restituisce storico cartellini di un giocatore negli scontri diretti tra due squadre.';
