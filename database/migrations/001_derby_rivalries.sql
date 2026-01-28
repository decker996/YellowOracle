-- database/migrations/001_derby_rivalries.sql
-- Tabella rivalità per derby detection nel calcolo risk score
-- Eseguire in Supabase SQL Editor

-- 1. Crea tabella rivalries
CREATE TABLE IF NOT EXISTS rivalries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    team1_id UUID REFERENCES teams(id) NOT NULL,
    team2_id UUID REFERENCES teams(id) NOT NULL,
    rivalry_name VARCHAR(100),
    rivalry_type VARCHAR(30) NOT NULL,  -- DERBY, HISTORIC, REGIONAL
    intensity INTEGER DEFAULT 1 CHECK (intensity BETWEEN 1 AND 3),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(team1_id, team2_id)
);

CREATE INDEX IF NOT EXISTS idx_rivalries_teams ON rivalries(team1_id, team2_id);

COMMENT ON TABLE rivalries IS 'Definizione rivalità/derby tra squadre per calcolo risk score';
COMMENT ON COLUMN rivalries.rivalry_type IS 'DERBY=stessa città, HISTORIC=rivalità storica, REGIONAL=stessa regione';
COMMENT ON COLUMN rivalries.intensity IS '1=minore, 2=sentito, 3=massima rivalità';

-- 2. Funzione per verificare se una partita è un derby
CREATE OR REPLACE FUNCTION is_derby_match(p_home_team_id UUID, p_away_team_id UUID)
RETURNS TABLE (
    is_derby BOOLEAN,
    rivalry_name TEXT,
    rivalry_type TEXT,
    intensity INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        TRUE AS is_derby,
        r.rivalry_name::TEXT,
        r.rivalry_type::TEXT,
        r.intensity
    FROM rivalries r
    WHERE (r.team1_id = p_home_team_id AND r.team2_id = p_away_team_id)
       OR (r.team1_id = p_away_team_id AND r.team2_id = p_home_team_id)
    LIMIT 1;

    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, NULL::TEXT, NULL::TEXT, NULL::INTEGER;
    END IF;
END;
$$;

-- 3. INSERT rivalità
-- Formato: (team1_id, team2_id, rivalry_name, rivalry_type, intensity)

-- ============================================================
-- SERIE A (SA) - Italia
-- ============================================================

-- Derby della Madonnina (Milano)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Derby della Madonnina', 'DERBY', 3
FROM teams t1, teams t2
WHERE t1.name = 'FC Internazionale Milano' AND t2.name = 'AC Milan'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Derby della Capitale (Roma)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Derby della Capitale', 'DERBY', 3
FROM teams t1, teams t2
WHERE t1.name = 'AS Roma' AND t2.name = 'SS Lazio'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Derby della Mole (Torino)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Derby della Mole', 'DERBY', 3
FROM teams t1, teams t2
WHERE t1.name = 'Juventus FC' AND t2.name = 'Torino FC'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Derby della Lanterna (Genova)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Derby della Lanterna', 'DERBY', 3
FROM teams t1, teams t2
WHERE t1.name = 'Genoa CFC' AND t2.name ILIKE '%Sampdoria%'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Derby d'Italia (Juventus vs Inter)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Derby d''Italia', 'HISTORIC', 3
FROM teams t1, teams t2
WHERE t1.name = 'Juventus FC' AND t2.name = 'FC Internazionale Milano'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Derby del Sole (Napoli vs Roma)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Derby del Sole', 'REGIONAL', 2
FROM teams t1, teams t2
WHERE t1.name = 'SSC Napoli' AND t2.name = 'AS Roma'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Derby dell'Appennino (Bologna vs Fiorentina)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Derby dell''Appennino', 'REGIONAL', 2
FROM teams t1, teams t2
WHERE t1.name = 'Bologna FC 1909' AND t2.name = 'ACF Fiorentina'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Derby dei Campioni (Milan vs Juventus)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Derby dei Campioni', 'HISTORIC', 2
FROM teams t1, teams t2
WHERE t1.name = 'AC Milan' AND t2.name = 'Juventus FC'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Fiorentina vs Juventus (Roberto Baggio)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Rivalità Baggio', 'HISTORIC', 2
FROM teams t1, teams t2
WHERE t1.name = 'ACF Fiorentina' AND t2.name = 'Juventus FC'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Juventus vs Napoli (Nord vs Sud)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Nord vs Sud', 'HISTORIC', 2
FROM teams t1, teams t2
WHERE t1.name = 'Juventus FC' AND t2.name = 'SSC Napoli'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Derby Lombardo (Atalanta vs Brescia) - Brescia non in Serie A ma può tornare
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Derby Lombardo', 'REGIONAL', 2
FROM teams t1, teams t2
WHERE t1.name = 'Atalanta BC' AND t2.name ILIKE '%Brescia%'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Inter vs Napoli (rivalità moderna)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, NULL, 'HISTORIC', 1
FROM teams t1, teams t2
WHERE t1.name = 'FC Internazionale Milano' AND t2.name = 'SSC Napoli'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Milan vs Napoli
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, NULL, 'HISTORIC', 1
FROM teams t1, teams t2
WHERE t1.name = 'AC Milan' AND t2.name = 'SSC Napoli'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- ============================================================
-- LA LIGA (PD) - Spagna
-- ============================================================

-- El Clásico (Real Madrid vs Barcelona)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'El Clásico', 'HISTORIC', 3
FROM teams t1, teams t2
WHERE t1.name = 'Real Madrid CF' AND t2.name = 'FC Barcelona'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Derby de Madrid
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Derby de Madrid', 'DERBY', 3
FROM teams t1, teams t2
WHERE t1.name = 'Real Madrid CF' AND t2.name = 'Club Atlético de Madrid'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- El Gran Derbi (Sevilla)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'El Gran Derbi', 'DERBY', 3
FROM teams t1, teams t2
WHERE t1.name = 'Sevilla FC' AND t2.name = 'Real Betis Balompié'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Derbi Vasco (Basque Derby)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Derbi Vasco', 'REGIONAL', 3
FROM teams t1, teams t2
WHERE t1.name = 'Athletic Club' AND t2.name = 'Real Sociedad de Fútbol'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Derbi Barceloní (Catalan Derby)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Derbi Barceloní', 'DERBY', 2
FROM teams t1, teams t2
WHERE t1.name = 'FC Barcelona' AND t2.name = 'RCD Espanyol de Barcelona'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Derbi de la Comunitat (Valencia vs Villarreal)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Derbi de la Comunitat', 'REGIONAL', 2
FROM teams t1, teams t2
WHERE t1.name = 'Valencia CF' AND t2.name = 'Villarreal CF'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Barcelona vs Atlético Madrid
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, NULL, 'HISTORIC', 2
FROM teams t1, teams t2
WHERE t1.name = 'FC Barcelona' AND t2.name = 'Club Atlético de Madrid'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- South Madrid Derby (Getafe vs Leganés)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Derby del Sur de Madrid', 'DERBY', 2
FROM teams t1, teams t2
WHERE t1.name = 'Getafe CF' AND t2.name = 'CD Leganés'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Galician Derby (Celta vs Deportivo - Deportivo non in Liga ma può tornare)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'O Noso Derbi', 'REGIONAL', 2
FROM teams t1, teams t2
WHERE t1.name = 'RC Celta de Vigo' AND t2.name ILIKE '%Deportivo%Coruña%'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- ============================================================
-- PREMIER LEAGUE (PL) - Inghilterra
-- ============================================================

-- Northwest Derby (Man Utd vs Liverpool)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Northwest Derby', 'HISTORIC', 3
FROM teams t1, teams t2
WHERE t1.name = 'Manchester United FC' AND t2.name = 'Liverpool FC'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- North London Derby (Arsenal vs Tottenham)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'North London Derby', 'DERBY', 3
FROM teams t1, teams t2
WHERE t1.name = 'Arsenal FC' AND t2.name = 'Tottenham Hotspur FC'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Manchester Derby
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Manchester Derby', 'DERBY', 3
FROM teams t1, teams t2
WHERE t1.name = 'Manchester United FC' AND t2.name = 'Manchester City FC'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Merseyside Derby (Liverpool vs Everton)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Merseyside Derby', 'DERBY', 3
FROM teams t1, teams t2
WHERE t1.name = 'Liverpool FC' AND t2.name = 'Everton FC'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Chelsea vs Tottenham
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'London Derby', 'DERBY', 2
FROM teams t1, teams t2
WHERE t1.name = 'Chelsea FC' AND t2.name = 'Tottenham Hotspur FC'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Liverpool vs Manchester City (modern rivalry)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, NULL, 'HISTORIC', 2
FROM teams t1, teams t2
WHERE t1.name = 'Liverpool FC' AND t2.name = 'Manchester City FC'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Arsenal vs Chelsea
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'London Derby', 'DERBY', 2
FROM teams t1, teams t2
WHERE t1.name = 'Arsenal FC' AND t2.name = 'Chelsea FC'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Arsenal vs Manchester United
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, NULL, 'HISTORIC', 2
FROM teams t1, teams t2
WHERE t1.name = 'Arsenal FC' AND t2.name = 'Manchester United FC'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- West Ham vs Tottenham
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'London Derby', 'DERBY', 2
FROM teams t1, teams t2
WHERE t1.name = 'West Ham United FC' AND t2.name = 'Tottenham Hotspur FC'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Chelsea vs West Ham
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'London Derby', 'DERBY', 1
FROM teams t1, teams t2
WHERE t1.name = 'Chelsea FC' AND t2.name = 'West Ham United FC'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Crystal Palace vs Brighton
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'M23 Derby', 'REGIONAL', 2
FROM teams t1, teams t2
WHERE t1.name = 'Crystal Palace FC' AND t2.name = 'Brighton & Hove Albion FC'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- ============================================================
-- BUNDESLIGA (BL1) - Germania
-- ============================================================

-- Der Klassiker (Bayern vs Dortmund)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Der Klassiker', 'HISTORIC', 3
FROM teams t1, teams t2
WHERE t1.name = 'FC Bayern München' AND t2.name = 'Borussia Dortmund'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Revierderby (Dortmund vs Schalke) - Schalke in 2.Bundesliga ma può tornare
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Revierderby', 'DERBY', 3
FROM teams t1, teams t2
WHERE t1.name = 'Borussia Dortmund' AND t2.name ILIKE '%Schalke%'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Bayern vs Gladbach (rivalità storica anni '70)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, NULL, 'HISTORIC', 2
FROM teams t1, teams t2
WHERE t1.name = 'FC Bayern München' AND t2.name = 'Borussia Mönchengladbach'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Rhinederby (Köln vs Gladbach)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Rhinederby', 'REGIONAL', 3
FROM teams t1, teams t2
WHERE t1.name = '1. FC Köln' AND t2.name = 'Borussia Mönchengladbach'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Köln vs Leverkusen
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Rheinisches Derby', 'DERBY', 2
FROM teams t1, teams t2
WHERE t1.name = '1. FC Köln' AND t2.name = 'Bayer 04 Leverkusen'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Nordderby (Werder Bremen vs Hamburger SV) - HSV in 2.Bundesliga
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Nordderby', 'REGIONAL', 3
FROM teams t1, teams t2
WHERE t1.name = 'SV Werder Bremen' AND t2.name = 'Hamburger SV'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Dortmund vs Gladbach
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, NULL, 'REGIONAL', 1
FROM teams t1, teams t2
WHERE t1.name = 'Borussia Dortmund' AND t2.name = 'Borussia Mönchengladbach'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Bayern vs Leipzig (rivalità moderna)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, NULL, 'HISTORIC', 2
FROM teams t1, teams t2
WHERE t1.name = 'FC Bayern München' AND t2.name = 'RB Leipzig'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- ============================================================
-- LIGUE 1 (FL1) - Francia
-- ============================================================

-- Le Classique (PSG vs Marseille)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Le Classique', 'HISTORIC', 3
FROM teams t1, teams t2
WHERE t1.name = 'Paris Saint-Germain FC' AND t2.name = 'Olympique de Marseille'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Derby du Rhône (Lyon vs Saint-Étienne)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Derby du Rhône', 'DERBY', 3
FROM teams t1, teams t2
WHERE t1.name = 'Olympique Lyonnais' AND t2.name = 'AS Saint-Étienne'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Derby du Nord (Lille vs Lens)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Derby du Nord', 'REGIONAL', 3
FROM teams t1, teams t2
WHERE t1.name = 'Lille OSC' AND t2.name = 'Racing Club de Lens'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Derby Breton (Nantes vs Rennes)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Derby Breton', 'REGIONAL', 2
FROM teams t1, teams t2
WHERE t1.name = 'FC Nantes' AND t2.name = 'Stade Rennais FC 1901'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Olympico (Lyon vs Marseille)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Choc des Olympiques', 'HISTORIC', 2
FROM teams t1, teams t2
WHERE t1.name = 'Olympique Lyonnais' AND t2.name = 'Olympique de Marseille'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Derby de la Côte d'Azur (Nice vs Monaco)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Derby de la Côte d''Azur', 'REGIONAL', 2
FROM teams t1, teams t2
WHERE t1.name = 'OGC Nice' AND t2.name = 'AS Monaco FC'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- PSG vs Lyon (modern rivalry)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, NULL, 'HISTORIC', 2
FROM teams t1, teams t2
WHERE t1.name = 'Paris Saint-Germain FC' AND t2.name = 'Olympique Lyonnais'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- ============================================================
-- BRASILEIRÃO (BSA) - Brasile
-- ============================================================

-- Fla-Flu (Flamengo vs Fluminense)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Fla-Flu', 'DERBY', 3
FROM teams t1, teams t2
WHERE t1.name = 'CR Flamengo' AND t2.name = 'Fluminense FC'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Derby Paulista (Palmeiras vs Corinthians)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Derby Paulista', 'DERBY', 3
FROM teams t1, teams t2
WHERE t1.name = 'SE Palmeiras' AND t2.name = 'SC Corinthians Paulista'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Gre-Nal (Grêmio vs Internacional)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Gre-Nal', 'DERBY', 3
FROM teams t1, teams t2
WHERE t1.name = 'Grêmio FBPA' AND t2.name = 'SC Internacional'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Clássico dos Milhões (Flamengo vs Vasco)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Clássico dos Milhões', 'DERBY', 3
FROM teams t1, teams t2
WHERE t1.name = 'CR Flamengo' AND t2.name = 'CR Vasco da Gama'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Clássico Majestoso (São Paulo vs Corinthians)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Clássico Majestoso', 'DERBY', 3
FROM teams t1, teams t2
WHERE t1.name = 'São Paulo FC' AND t2.name = 'SC Corinthians Paulista'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Choque-Rei (São Paulo vs Palmeiras)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Choque-Rei', 'DERBY', 3
FROM teams t1, teams t2
WHERE t1.name = 'São Paulo FC' AND t2.name = 'SE Palmeiras'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Clássico da Saudade (Santos vs Palmeiras)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Clássico da Saudade', 'REGIONAL', 2
FROM teams t1, teams t2
WHERE t1.name = 'Santos FC' AND t2.name = 'SE Palmeiras'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Clássico Alvinegro (Santos vs Corinthians)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Clássico Alvinegro', 'REGIONAL', 2
FROM teams t1, teams t2
WHERE t1.name = 'Santos FC' AND t2.name = 'SC Corinthians Paulista'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Clássico Vovô (Fluminense vs Botafogo)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Clássico Vovô', 'DERBY', 2
FROM teams t1, teams t2
WHERE t1.name = 'Fluminense FC' AND t2.name = 'Botafogo FR'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Flamengo vs Botafogo
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Clássico da Rivalidade', 'DERBY', 2
FROM teams t1, teams t2
WHERE t1.name = 'CR Flamengo' AND t2.name = 'Botafogo FR'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Clássico Mineiro (Atlético MG vs Cruzeiro)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity)
SELECT t1.id, t2.id, 'Clássico Mineiro', 'DERBY', 3
FROM teams t1, teams t2
WHERE t1.name = 'CA Mineiro' AND t2.name = 'Cruzeiro EC'
ON CONFLICT (team1_id, team2_id) DO NOTHING;

-- Verifica inserimento
SELECT
    t1.name AS team1,
    t2.name AS team2,
    r.rivalry_name,
    r.rivalry_type,
    r.intensity
FROM rivalries r
JOIN teams t1 ON r.team1_id = t1.id
JOIN teams t2 ON r.team2_id = t2.id
ORDER BY r.intensity DESC, r.rivalry_name;
