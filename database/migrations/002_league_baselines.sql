-- database/migrations/002_league_baselines.sql
-- Vista e funzione per normalizzazione cartellini per lega
-- Eseguire in Supabase SQL Editor

-- 1. Vista con baseline cartellini per competizione
-- Basato su dati statistici reali delle diverse leghe
CREATE OR REPLACE VIEW league_card_baselines AS
SELECT
    c.code AS competition_code,
    c.name AS competition_name,
    CASE c.code
        WHEN 'PD' THEN 5.33   -- La Liga (più severa)
        WHEN 'SA' THEN 4.10   -- Serie A
        WHEN 'PL' THEN 4.85   -- Premier League
        WHEN 'BL1' THEN 3.90  -- Bundesliga (più permissiva)
        WHEN 'FL1' THEN 3.65  -- Ligue 1 (più permissiva)
        WHEN 'CL' THEN 4.20   -- Champions League
        WHEN 'BSA' THEN 4.50  -- Brasileirão
        ELSE 4.00
    END AS baseline_yellows_per_match,
    -- Fattore di normalizzazione rispetto alla media (4.00)
    -- >1 = lega più severa, <1 = lega più permissiva
    CASE c.code
        WHEN 'PD' THEN 1.30   -- La Liga +30%
        WHEN 'SA' THEN 1.00   -- Serie A (baseline)
        WHEN 'PL' THEN 1.18   -- Premier League +18%
        WHEN 'BL1' THEN 0.95  -- Bundesliga -5%
        WHEN 'FL1' THEN 0.89  -- Ligue 1 -11%
        WHEN 'CL' THEN 1.02   -- Champions League +2%
        WHEN 'BSA' THEN 1.10  -- Brasileirão +10%
        ELSE 1.00
    END AS normalization_factor
FROM competitions c;

COMMENT ON VIEW league_card_baselines IS 'Baseline cartellini gialli per competizione e fattore di normalizzazione';

-- 2. Funzione per ottenere il fattore di normalizzazione
CREATE OR REPLACE FUNCTION get_league_normalization(p_competition_code TEXT)
RETURNS NUMERIC
LANGUAGE plpgsql
AS $$
DECLARE
    v_factor NUMERIC;
BEGIN
    SELECT normalization_factor INTO v_factor
    FROM league_card_baselines
    WHERE competition_code = p_competition_code;

    RETURN COALESCE(v_factor, 1.0);
END;
$$;

COMMENT ON FUNCTION get_league_normalization IS 'Restituisce il fattore di normalizzazione per una competizione';

-- 3. Verifica
SELECT * FROM league_card_baselines ORDER BY normalization_factor DESC;
SELECT get_league_normalization('PD') AS la_liga_factor;
SELECT get_league_normalization('BL1') AS bundesliga_factor;
