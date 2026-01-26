-- YellowOracle Database Schema v2
-- Include tutti i dati da football-data.org (Deep Data + Statistics Add-On)
-- Esegui questo script nell'SQL Editor di Supabase

-- Prima elimina le tabelle esistenti (se vuoi ripartire da zero)
-- ATTENZIONE: questo cancella tutti i dati!
DROP VIEW IF EXISTS referee_stats;
DROP VIEW IF EXISTS player_card_risk;
DROP TABLE IF EXISTS match_statistics;
DROP TABLE IF EXISTS match_events;
DROP TABLE IF EXISTS lineups;
DROP TABLE IF EXISTS player_season_stats;
DROP TABLE IF EXISTS cards;
DROP TABLE IF EXISTS matches;
DROP TABLE IF EXISTS players;
DROP TABLE IF EXISTS referees;
DROP TABLE IF EXISTS teams;
DROP TABLE IF EXISTS competitions;

-- Abilita UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- TABELLE PRINCIPALI
-- ============================================

-- Tabella Competizioni
CREATE TABLE competitions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id INTEGER UNIQUE,  -- ID da football-data.org
    code VARCHAR(10) UNIQUE NOT NULL,  -- PD, SA, BL1, PL, FL1
    name VARCHAR(100) NOT NULL,
    area_name VARCHAR(50),  -- Spain, Italy, Germany, etc.
    area_code VARCHAR(5),   -- ESP, ITA, GER, etc.
    emblem_url TEXT,
    plan VARCHAR(20),  -- TIER_ONE, TIER_TWO, etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabella Squadre
CREATE TABLE teams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id INTEGER UNIQUE,  -- ID da football-data.org
    name VARCHAR(100) NOT NULL,
    short_name VARCHAR(50),
    tla VARCHAR(5),  -- Abbreviazione (es. "RMA", "BAR")
    crest_url TEXT,  -- URL dello stemma
    stadium VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabella Giocatori
CREATE TABLE players (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id INTEGER UNIQUE,  -- ID da football-data.org
    name VARCHAR(100) NOT NULL,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    date_of_birth DATE,
    nationality VARCHAR(50),
    position VARCHAR(30),  -- Goalkeeper, Defence, Midfield, Offence
    shirt_number INTEGER,
    current_team_id UUID REFERENCES teams(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabella Arbitri
CREATE TABLE referees (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id INTEGER UNIQUE,  -- ID da football-data.org
    name VARCHAR(100) NOT NULL,
    nationality VARCHAR(50),
    -- Statistiche aggregate (calcolate)
    total_matches INTEGER DEFAULT 0,
    total_yellows INTEGER DEFAULT 0,
    total_reds INTEGER DEFAULT 0,
    avg_yellows_per_match DECIMAL(4,2) DEFAULT 0,
    avg_fouls_per_match DECIMAL(4,2) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabella Partite
CREATE TABLE matches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id INTEGER UNIQUE,  -- ID da football-data.org
    competition_id UUID REFERENCES competitions(id),  -- Competizione (PD, SA, etc.)
    season VARCHAR(10) NOT NULL,  -- es. "2024-2025"
    matchday INTEGER,
    match_date TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(20),  -- SCHEDULED, LIVE, FINISHED, POSTPONED, etc.

    -- Squadre
    home_team_id UUID REFERENCES teams(id),
    away_team_id UUID REFERENCES teams(id),

    -- Risultato
    home_score INTEGER,
    away_score INTEGER,
    home_score_halftime INTEGER,
    away_score_halftime INTEGER,
    winner VARCHAR(20),  -- HOME_TEAM, AWAY_TEAM, DRAW

    -- Arbitri
    referee_id UUID REFERENCES referees(id),
    var_referee_id UUID REFERENCES referees(id),  -- Video Assistant Referee

    -- Metadati partita
    is_derby BOOLEAN DEFAULT FALSE,
    home_position INTEGER,  -- Posizione in classifica al momento della partita
    away_position INTEGER,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- STATISTICHE PARTITA (Statistics Add-On)
-- ============================================

CREATE TABLE match_statistics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    match_id UUID REFERENCES matches(id) ON DELETE CASCADE,
    team_id UUID REFERENCES teams(id),

    -- Possesso e passaggi
    ball_possession INTEGER,  -- percentuale

    -- Tiri
    shots_on_goal INTEGER,
    shots_off_goal INTEGER,
    total_shots INTEGER,

    -- Calci piazzati
    corner_kicks INTEGER,
    free_kicks INTEGER,
    goal_kicks INTEGER,
    throw_ins INTEGER,

    -- Difesa
    saves INTEGER,
    offsides INTEGER,

    -- Falli e disciplina
    fouls_committed INTEGER,
    fouls_suffered INTEGER,
    yellow_cards INTEGER,
    red_cards INTEGER,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(match_id, team_id)
);

-- ============================================
-- FORMAZIONI E SOSTITUZIONI
-- ============================================

CREATE TABLE lineups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    match_id UUID REFERENCES matches(id) ON DELETE CASCADE,
    team_id UUID REFERENCES teams(id),
    player_id UUID REFERENCES players(id),

    -- Tipo di partecipazione
    is_starter BOOLEAN DEFAULT FALSE,  -- Titolare
    is_substitute BOOLEAN DEFAULT FALSE,  -- In panchina

    -- Dettagli
    shirt_number INTEGER,
    position VARCHAR(30),

    -- Minuti giocati
    minutes_played INTEGER,
    subbed_in_minute INTEGER,  -- Minuto entrata (se subentrato)
    subbed_out_minute INTEGER,  -- Minuto uscita (se sostituito)

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(match_id, player_id)
);

-- ============================================
-- EVENTI PARTITA (Gol, Cartellini, Sostituzioni)
-- ============================================

CREATE TABLE match_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    match_id UUID REFERENCES matches(id) ON DELETE CASCADE,
    team_id UUID REFERENCES teams(id),
    player_id UUID REFERENCES players(id),

    -- Tipo evento
    event_type VARCHAR(30) NOT NULL,  -- GOAL, YELLOW_CARD, RED_CARD, SUBSTITUTION, OWN_GOAL, PENALTY
    minute INTEGER,
    extra_time_minute INTEGER,  -- Minuti di recupero

    -- Dettagli aggiuntivi
    detail VARCHAR(100),  -- es. "Penalty", "Header", "Foul", "Second Yellow"

    -- Per sostituzioni
    player_in_id UUID REFERENCES players(id),  -- Giocatore che entra

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- STATISTICHE AGGREGATE GIOCATORE
-- ============================================

CREATE TABLE player_season_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    player_id UUID REFERENCES players(id),
    team_id UUID REFERENCES teams(id),
    season VARCHAR(10) NOT NULL,

    -- Presenze
    matches_played INTEGER DEFAULT 0,
    matches_started INTEGER DEFAULT 0,
    minutes_played INTEGER DEFAULT 0,

    -- Gol
    goals INTEGER DEFAULT 0,
    assists INTEGER DEFAULT 0,

    -- Disciplina
    yellow_cards INTEGER DEFAULT 0,
    red_cards INTEGER DEFAULT 0,

    -- Falli (dal Statistics Add-On)
    fouls_committed INTEGER DEFAULT 0,
    fouls_suffered INTEGER DEFAULT 0,

    -- Indici calcolati
    yellows_per_90 DECIMAL(4,2) GENERATED ALWAYS AS (
        CASE WHEN minutes_played >= 90
        THEN ROUND((yellow_cards::DECIMAL / (minutes_played::DECIMAL / 90)), 2)
        ELSE NULL END
    ) STORED,

    fouls_per_90 DECIMAL(4,2) GENERATED ALWAYS AS (
        CASE WHEN minutes_played >= 90
        THEN ROUND((fouls_committed::DECIMAL / (minutes_played::DECIMAL / 90)), 2)
        ELSE NULL END
    ) STORED,

    -- Indice di rischio cartellino (falli che portano a cartellino)
    foul_to_card_ratio DECIMAL(4,2) GENERATED ALWAYS AS (
        CASE WHEN fouls_committed > 0
        THEN ROUND((yellow_cards::DECIMAL / fouls_committed::DECIMAL), 2)
        ELSE NULL END
    ) STORED,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(player_id, season)
);

-- ============================================
-- INDICI PER PERFORMANCE
-- ============================================

CREATE INDEX idx_matches_season ON matches(season);
CREATE INDEX idx_matches_date ON matches(match_date);
CREATE INDEX idx_matches_status ON matches(status);
CREATE INDEX idx_matches_home_team ON matches(home_team_id);
CREATE INDEX idx_matches_away_team ON matches(away_team_id);
CREATE INDEX idx_matches_referee ON matches(referee_id);
CREATE INDEX idx_matches_competition ON matches(competition_id);

CREATE INDEX idx_match_events_match ON match_events(match_id);
CREATE INDEX idx_match_events_player ON match_events(player_id);
CREATE INDEX idx_match_events_type ON match_events(event_type);

CREATE INDEX idx_lineups_match ON lineups(match_id);
CREATE INDEX idx_lineups_player ON lineups(player_id);

CREATE INDEX idx_match_stats_match ON match_statistics(match_id);

CREATE INDEX idx_player_stats_player ON player_season_stats(player_id);
CREATE INDEX idx_player_stats_season ON player_season_stats(season);

-- ============================================
-- VISTE UTILI
-- ============================================

-- Vista: Classifica rischio cartellino giocatori
CREATE VIEW player_card_risk AS
SELECT
    p.id,
    p.name,
    p.position,
    t.name as team_name,
    t.short_name as team_short,
    pss.season,
    pss.matches_played,
    pss.minutes_played,
    pss.yellow_cards,
    pss.red_cards,
    pss.fouls_committed,
    pss.yellows_per_90,
    pss.fouls_per_90,
    pss.foul_to_card_ratio,
    RANK() OVER (
        PARTITION BY pss.season
        ORDER BY pss.yellows_per_90 DESC NULLS LAST
    ) as risk_rank
FROM players p
JOIN player_season_stats pss ON p.id = pss.player_id
JOIN teams t ON pss.team_id = t.id
WHERE pss.minutes_played >= 450;  -- Almeno 5 partite complete

-- Vista: Statistiche arbitri
CREATE VIEW referee_stats AS
SELECT
    r.id,
    r.name,
    r.nationality,
    r.total_matches,
    r.total_yellows,
    r.total_reds,
    r.avg_yellows_per_match,
    r.avg_fouls_per_match,
    RANK() OVER (ORDER BY r.avg_yellows_per_match DESC) as severity_rank
FROM referees r
WHERE r.total_matches >= 5;

-- Vista: Storico cartellini per partita
CREATE VIEW match_cards AS
SELECT
    m.id as match_id,
    m.match_date,
    m.season,
    m.matchday,
    ht.name as home_team,
    at.name as away_team,
    r.name as referee_name,
    me.event_type,
    me.minute,
    p.name as player_name,
    t.name as player_team,
    me.detail
FROM matches m
JOIN teams ht ON m.home_team_id = ht.id
JOIN teams at ON m.away_team_id = at.id
LEFT JOIN referees r ON m.referee_id = r.id
JOIN match_events me ON m.id = me.match_id
JOIN players p ON me.player_id = p.id
JOIN teams t ON me.team_id = t.id
WHERE me.event_type IN ('YELLOW_CARD', 'RED_CARD')
ORDER BY m.match_date DESC, me.minute;

-- Vista: Confronto diretto tra squadre (storico cartellini negli scontri diretti)
CREATE VIEW head_to_head_cards AS
SELECT
    m.season,
    m.match_date,
    ht.name as home_team,
    at.name as away_team,
    r.name as referee,
    COUNT(CASE WHEN me.event_type = 'YELLOW_CARD' THEN 1 END) as total_yellows,
    COUNT(CASE WHEN me.event_type = 'RED_CARD' THEN 1 END) as total_reds,
    ms_home.fouls_committed as home_fouls,
    ms_away.fouls_committed as away_fouls
FROM matches m
JOIN teams ht ON m.home_team_id = ht.id
JOIN teams at ON m.away_team_id = at.id
LEFT JOIN referees r ON m.referee_id = r.id
LEFT JOIN match_events me ON m.id = me.match_id AND me.event_type IN ('YELLOW_CARD', 'RED_CARD')
LEFT JOIN match_statistics ms_home ON m.id = ms_home.match_id AND ms_home.team_id = m.home_team_id
LEFT JOIN match_statistics ms_away ON m.id = ms_away.match_id AND ms_away.team_id = m.away_team_id
GROUP BY m.id, m.season, m.match_date, ht.name, at.name, r.name, ms_home.fouls_committed, ms_away.fouls_committed
ORDER BY m.match_date DESC;
