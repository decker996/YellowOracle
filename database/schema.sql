-- YellowOracle Database Schema
-- Esegui questo script nell'SQL Editor di Supabase

-- Abilita UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tabella Squadre
CREATE TABLE teams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    stadium VARCHAR(100),
    avg_cards_home DECIMAL(4,2) DEFAULT 0,
    avg_cards_away DECIMAL(4,2) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabella Giocatori
CREATE TABLE players (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    team_id UUID REFERENCES teams(id),
    position VARCHAR(20) CHECK (position IN ('GK', 'DF', 'MF', 'FW')),
    nationality VARCHAR(50),
    birth_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabella Arbitri
CREATE TABLE referees (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    avg_cards_per_match DECIMAL(4,2) DEFAULT 0,
    total_matches INTEGER DEFAULT 0,
    total_yellows INTEGER DEFAULT 0,
    total_reds INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabella Partite
CREATE TABLE matches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    season VARCHAR(10) NOT NULL,
    match_date DATE NOT NULL,
    home_team_id UUID REFERENCES teams(id),
    away_team_id UUID REFERENCES teams(id),
    referee_id UUID REFERENCES referees(id),
    home_score INTEGER,
    away_score INTEGER,
    is_derby BOOLEAN DEFAULT FALSE,
    home_position INTEGER,
    away_position INTEGER,
    matchday INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabella Cartellini
CREATE TABLE cards (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    match_id UUID REFERENCES matches(id) ON DELETE CASCADE,
    player_id UUID REFERENCES players(id),
    minute INTEGER,
    card_type VARCHAR(10) CHECK (card_type IN ('yellow', 'red')),
    reason VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabella Statistiche Giocatore per Stagione
CREATE TABLE player_season_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    player_id UUID REFERENCES players(id),
    season VARCHAR(10) NOT NULL,
    team_id UUID REFERENCES teams(id),
    matches_played INTEGER DEFAULT 0,
    minutes_played INTEGER DEFAULT 0,
    yellow_cards INTEGER DEFAULT 0,
    red_cards INTEGER DEFAULT 0,
    fouls_committed INTEGER DEFAULT 0,
    cards_per_90 DECIMAL(4,2) GENERATED ALWAYS AS (
        CASE WHEN minutes_played > 0
        THEN ROUND((yellow_cards::DECIMAL / (minutes_played::DECIMAL / 90)), 2)
        ELSE 0 END
    ) STORED,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(player_id, season)
);

-- Indici per performance
CREATE INDEX idx_matches_season ON matches(season);
CREATE INDEX idx_matches_date ON matches(match_date);
CREATE INDEX idx_cards_match ON cards(match_id);
CREATE INDEX idx_cards_player ON cards(player_id);
CREATE INDEX idx_player_stats_season ON player_season_stats(season);
CREATE INDEX idx_player_stats_player ON player_season_stats(player_id);

-- Vista per classifica rischio cartellino
CREATE VIEW player_card_risk AS
SELECT
    p.id,
    p.name,
    t.name as team_name,
    p.position,
    pss.season,
    pss.matches_played,
    pss.minutes_played,
    pss.yellow_cards,
    pss.cards_per_90,
    RANK() OVER (PARTITION BY pss.season ORDER BY pss.cards_per_90 DESC) as risk_rank
FROM players p
JOIN player_season_stats pss ON p.id = pss.player_id
JOIN teams t ON p.team_id = t.id
WHERE pss.minutes_played >= 450;  -- Almeno 5 partite complete

-- Vista per statistiche arbitro
CREATE VIEW referee_stats AS
SELECT
    r.id,
    r.name,
    r.total_matches,
    r.total_yellows,
    r.total_reds,
    r.avg_cards_per_match,
    RANK() OVER (ORDER BY r.avg_cards_per_match DESC) as severity_rank
FROM referees r
WHERE r.total_matches >= 5;
