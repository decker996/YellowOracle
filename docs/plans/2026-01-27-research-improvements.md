# Research-Based Model Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implementare 6 miglioramenti al modello di scoring basati sulle ricerche accademiche analizzate, per aumentare l'accuratezza predittiva del 15-25%.

**Architecture:** Il piano aggiunge nuove variabili al calcolo dello score esistente in `analyze_match_risk()`. Le modifiche toccano: database (nuove tabelle/colonne), SQL views, e la logica Python del server MCP. L'approccio è incrementale: ogni task è indipendente e testabile.

**Tech Stack:** PostgreSQL (Supabase), Python 3.x, FastMCP, SQL Views/Functions

---

## Task 1: Derby Flag - Database e Dati

**Files:**
- Create: `database/migrations/001_derby_rivalries.sql`
- Modify: `database/schema_v2.sql:112-113` (colonna is_derby già esiste, aggiungere tabella rivalità)

**Step 1: Creare file migrazione con tabella rivalries**

```sql
-- database/migrations/001_derby_rivalries.sql
-- Tabella per definire le rivalità/derby tra squadre

CREATE TABLE IF NOT EXISTS rivalries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    team1_id UUID REFERENCES teams(id) NOT NULL,
    team2_id UUID REFERENCES teams(id) NOT NULL,
    rivalry_name VARCHAR(100),  -- es. "Derby della Madonnina", "El Clásico"
    rivalry_type VARCHAR(30) NOT NULL,  -- DERBY, HISTORIC, REGIONAL
    intensity INTEGER DEFAULT 1 CHECK (intensity BETWEEN 1 AND 3),  -- 1=normale, 2=sentito, 3=storico
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(team1_id, team2_id)
);

-- Indice per ricerche veloci
CREATE INDEX idx_rivalries_teams ON rivalries(team1_id, team2_id);

-- Inserimento rivalità Serie A (esempi principali)
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity) VALUES
-- Trova ID tramite nome
((SELECT id FROM teams WHERE name ILIKE '%Inter%' LIMIT 1),
 (SELECT id FROM teams WHERE name ILIKE '%Milan%' AND name NOT ILIKE '%Inter%' LIMIT 1),
 'Derby della Madonnina', 'DERBY', 3),
((SELECT id FROM teams WHERE name ILIKE '%Roma%' LIMIT 1),
 (SELECT id FROM teams WHERE name ILIKE '%Lazio%' LIMIT 1),
 'Derby della Capitale', 'DERBY', 3),
((SELECT id FROM teams WHERE name ILIKE '%Juventus%' LIMIT 1),
 (SELECT id FROM teams WHERE name ILIKE '%Torino%' AND name NOT ILIKE '%Juventus%' LIMIT 1),
 'Derby della Mole', 'DERBY', 3),
((SELECT id FROM teams WHERE name ILIKE '%Juventus%' LIMIT 1),
 (SELECT id FROM teams WHERE name ILIKE '%Inter%' LIMIT 1),
 'Derby d''Italia', 'HISTORIC', 3),
((SELECT id FROM teams WHERE name ILIKE '%Napoli%' LIMIT 1),
 (SELECT id FROM teams WHERE name ILIKE '%Juventus%' LIMIT 1),
 NULL, 'HISTORIC', 2),
((SELECT id FROM teams WHERE name ILIKE '%Genoa%' LIMIT 1),
 (SELECT id FROM teams WHERE name ILIKE '%Sampdoria%' LIMIT 1),
 'Derby della Lanterna', 'DERBY', 3),
((SELECT id FROM teams WHERE name ILIKE '%Fiorentina%' LIMIT 1),
 (SELECT id FROM teams WHERE name ILIKE '%Juventus%' LIMIT 1),
 NULL, 'HISTORIC', 2)
ON CONFLICT DO NOTHING;

-- Rivalità La Liga
INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity) VALUES
((SELECT id FROM teams WHERE name ILIKE '%Real Madrid%' LIMIT 1),
 (SELECT id FROM teams WHERE name ILIKE '%Barcelona%' LIMIT 1),
 'El Clásico', 'HISTORIC', 3),
((SELECT id FROM teams WHERE name ILIKE '%Atlético%' OR name ILIKE '%Atletico%' LIMIT 1),
 (SELECT id FROM teams WHERE name ILIKE '%Real Madrid%' LIMIT 1),
 'Derby Madrileño', 'DERBY', 3),
((SELECT id FROM teams WHERE name ILIKE '%Sevilla%' LIMIT 1),
 (SELECT id FROM teams WHERE name ILIKE '%Betis%' LIMIT 1),
 'Derby de Sevilla', 'DERBY', 3)
ON CONFLICT DO NOTHING;

-- Funzione per verificare se una partita è un derby
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

    -- Se non trovato, ritorna false
    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, NULL::TEXT, NULL::TEXT, NULL::INTEGER;
    END IF;
END;
$$;

COMMENT ON TABLE rivalries IS 'Definizione rivalità/derby tra squadre per calcolo risk score';
COMMENT ON FUNCTION is_derby_match IS 'Verifica se una partita è un derby e restituisce dettagli rivalità';
```

**Step 2: Eseguire migrazione su Supabase**

Run: Accedere a Supabase SQL Editor ed eseguire il contenuto di `database/migrations/001_derby_rivalries.sql`

Expected: Tabella `rivalries` creata con dati iniziali, funzione `is_derby_match` disponibile

**Step 3: Verificare creazione tabella**

Run (in SQL Editor):
```sql
SELECT * FROM rivalries;
SELECT * FROM is_derby_match(
    (SELECT id FROM teams WHERE name ILIKE '%Inter%' LIMIT 1),
    (SELECT id FROM teams WHERE name ILIKE '%Milan%' AND name NOT ILIKE '%Inter%' LIMIT 1)
);
```

Expected: Lista rivalità e risultato `is_derby=TRUE, rivalry_name='Derby della Madonnina', intensity=3`

**Step 4: Commit**

```bash
git add database/migrations/001_derby_rivalries.sql
git commit -m "$(cat <<'EOF'
feat(db): add rivalries table for derby detection

- Create rivalries table with team pairs and intensity levels
- Add is_derby_match() function for quick lookup
- Seed with Serie A and La Liga main derbies

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Derby Flag - Integrazione nel Server MCP

**Files:**
- Modify: `mcp_server.py:398-625` (funzione analyze_match_risk)

**Step 1: Leggere il file corrente per conferma**

Run: Verificare che `mcp_server.py` contenga la funzione `analyze_match_risk` alla linea ~398

**Step 2: Aggiungere query derby e moltiplicatore**

Modificare `mcp_server.py`, aggiungendo dopo la riga 467 (dopo `analysis["team_stats"] = team_fouls`):

```python
        # --- VERIFICA DERBY ---
        derby_info = None
        derby_multiplier = 1.0
        try:
            # Trova ID squadre
            home_team_result = supabase.table("teams").select("id").ilike("name", f"%{home_team}%").limit(1).execute()
            away_team_result = supabase.table("teams").select("id").ilike("name", f"%{away_team}%").limit(1).execute()

            if home_team_result.data and away_team_result.data:
                home_id = home_team_result.data[0]["id"]
                away_id = away_team_result.data[0]["id"]

                derby_result = supabase.rpc(
                    "is_derby_match",
                    {"p_home_team_id": home_id, "p_away_team_id": away_id}
                ).execute()

                if derby_result.data and len(derby_result.data) > 0:
                    d = derby_result.data[0]
                    if d.get("is_derby"):
                        derby_info = {
                            "name": d.get("rivalry_name"),
                            "type": d.get("rivalry_type"),
                            "intensity": d.get("intensity")
                        }
                        # Moltiplicatore basato su intensità: 1=+10%, 2=+20%, 3=+25%
                        intensity = d.get("intensity", 1)
                        derby_multiplier = 1.0 + (intensity * 0.08 + 0.02)  # 1.10, 1.18, 1.26
        except Exception:
            pass  # Derby check failed, continue without

        analysis["derby"] = derby_info
        analysis["derby_multiplier"] = derby_multiplier
```

**Step 3: Applicare moltiplicatore nel calcolo score**

Modificare la sezione del calcolo score (dopo riga ~577), cambiando:

```python
                # SCORE COMBINATO (con moltiplicatore derby)
                if referee:
                    combined_score = (
                        seasonal_score * WEIGHT_SEASONAL +
                        referee_score * WEIGHT_REFEREE +
                        h2h_score * WEIGHT_H2H +
                        fouls_score * WEIGHT_FOULS
                    ) * derby_multiplier
                else:
                    combined_score = (
                        seasonal_score * WEIGHT_SEASONAL_NO_REF +
                        h2h_score * WEIGHT_H2H_NO_REF +
                        fouls_score * WEIGHT_FOULS_NO_REF
                    ) * derby_multiplier

                # Cap a 100
                combined_score = min(combined_score, 100)
```

**Step 4: Testare manualmente**

Run:
```bash
cd /home/salvatore/Scrivania/soccer
./venv/bin/python -c "
from mcp_server import analyze_match_risk
import json
result = json.loads(analyze_match_risk('Inter', 'Milan'))
print('Derby info:', result.get('derby'))
print('Derby multiplier:', result.get('derby_multiplier'))
print('Top player score:', result['overall_top5'][0]['combined_score'] if result.get('overall_top5') else 'N/A')
"
```

Expected: `Derby info: {'name': 'Derby della Madonnina', 'type': 'DERBY', 'intensity': 3}`, `Derby multiplier: 1.26`

**Step 5: Commit**

```bash
git add mcp_server.py
git commit -m "$(cat <<'EOF'
feat(mcp): integrate derby detection in match risk analysis

- Query rivalries table to detect derby matches
- Apply intensity-based multiplier (10-26%) to risk scores
- Add derby info to analysis output

Research shows derby matches have 20-30% more cards than regular matches.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Home/Away Factor

**Files:**
- Modify: `mcp_server.py:398-625` (funzione analyze_match_risk)

**Step 1: Aggiungere costanti per fattore casa/trasferta**

Dopo le costanti dei pesi (riga ~427), aggiungere:

```python
    # Fattori casa/trasferta (basati su studio CIES: 53% cartellini alla trasferta)
    HOME_FACTOR = 0.94   # Squadra di casa riceve ~6% meno cartellini
    AWAY_FACTOR = 1.06   # Squadra in trasferta riceve ~6% più cartellini
```

**Step 2: Applicare fattore nel loop giocatori**

Modificare il loop (riga ~502), aggiungendo dopo `for team_data, team_name in [(home_result.data...`:

```python
        for team_data, team_name, is_home in [
            (home_result.data or [], home_team, True),
            (away_result.data or [], away_team, False)
        ]:
            # Fattore casa/trasferta
            home_away_factor = HOME_FACTOR if is_home else AWAY_FACTOR
```

E modificare il calcolo score per applicare il fattore:

```python
                # SCORE COMBINATO (con moltiplicatori)
                base_score = 0
                if referee:
                    base_score = (
                        seasonal_score * WEIGHT_SEASONAL +
                        referee_score * WEIGHT_REFEREE +
                        h2h_score * WEIGHT_H2H +
                        fouls_score * WEIGHT_FOULS
                    )
                else:
                    base_score = (
                        seasonal_score * WEIGHT_SEASONAL_NO_REF +
                        h2h_score * WEIGHT_H2H_NO_REF +
                        fouls_score * WEIGHT_FOULS_NO_REF
                    )

                # Applica moltiplicatori
                combined_score = base_score * home_away_factor * derby_multiplier
                combined_score = min(combined_score, 100)
```

**Step 3: Aggiungere info nel breakdown**

Nel `player_data` dict, aggiungere:

```python
                    "is_home": is_home,
                    "home_away_factor": home_away_factor,
```

**Step 4: Testare**

Run:
```bash
cd /home/salvatore/Scrivania/soccer
./venv/bin/python -c "
from mcp_server import analyze_match_risk
import json
result = json.loads(analyze_match_risk('Roma', 'Napoli'))
home_player = result['home_team_top5'][0] if result.get('home_team_top5') else None
away_player = result['away_team_top5'][0] if result.get('away_team_top5') else None
print('Home player factor:', home_player.get('home_away_factor') if home_player else 'N/A')
print('Away player factor:', away_player.get('home_away_factor') if away_player else 'N/A')
"
```

Expected: `Home player factor: 0.94`, `Away player factor: 1.06`

**Step 5: Commit**

```bash
git add mcp_server.py
git commit -m "$(cat <<'EOF'
feat(mcp): add home/away factor to risk calculation

- Home team players: 0.94x multiplier (6% less cards)
- Away team players: 1.06x multiplier (6% more cards)
- Based on CIES study: 53% of cards go to away teams globally

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: League Baseline Normalization

**Files:**
- Modify: `mcp_server.py:398-625` (funzione analyze_match_risk)
- Modify: `database/analysis_views.sql` (aggiungere vista league_baselines)

**Step 1: Creare vista league_baselines nel database**

Creare file `database/migrations/002_league_baselines.sql`:

```sql
-- database/migrations/002_league_baselines.sql
-- Baseline cartellini per lega (da ricerca accademica)

-- Vista con baseline per lega
CREATE OR REPLACE VIEW league_card_baselines AS
SELECT
    c.code AS competition_code,
    c.name AS competition_name,
    -- Baseline da ricerca (gialli/partita medi)
    CASE c.code
        WHEN 'PD' THEN 5.33   -- La Liga (più alta)
        WHEN 'SA' THEN 4.10   -- Serie A
        WHEN 'PL' THEN 4.85   -- Premier League (in aumento per regole dissenso)
        WHEN 'BL1' THEN 3.90  -- Bundesliga (più bassa)
        WHEN 'FL1' THEN 3.65  -- Ligue 1
        WHEN 'CL' THEN 4.20   -- Champions League (stima)
        WHEN 'EL' THEN 4.00   -- Europa League (stima)
        ELSE 4.00             -- Default
    END AS baseline_yellows_per_match,
    -- Fattore normalizzazione (Serie A = 1.0 come riferimento)
    CASE c.code
        WHEN 'PD' THEN 1.30   -- La Liga: +30% rispetto baseline
        WHEN 'SA' THEN 1.00   -- Serie A: baseline
        WHEN 'PL' THEN 1.18   -- Premier League: +18%
        WHEN 'BL1' THEN 0.95  -- Bundesliga: -5%
        WHEN 'FL1' THEN 0.89  -- Ligue 1: -11%
        WHEN 'CL' THEN 1.02   -- Champions: +2%
        WHEN 'EL' THEN 0.98   -- Europa League: -2%
        ELSE 1.00
    END AS normalization_factor
FROM competitions c;

-- Funzione per ottenere fattore normalizzazione
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

COMMENT ON VIEW league_card_baselines IS 'Baseline cartellini per lega da ricerca accademica (2024-2026)';
COMMENT ON FUNCTION get_league_normalization IS 'Restituisce fattore normalizzazione per confronto cross-league';
```

**Step 2: Eseguire migrazione**

Run: Eseguire `database/migrations/002_league_baselines.sql` in Supabase SQL Editor

**Step 3: Modificare analyze_match_risk per usare normalizzazione**

Aggiungere dopo le query iniziali (riga ~440):

```python
        # --- BASELINE LEGA ---
        league_factor = 1.0
        competition_code = None
        try:
            # Determina la competizione dalla squadra di casa
            comp_result = supabase.table("matches").select(
                "competitions!inner(code)"
            ).ilike("home_team.name", f"%{home_team}%").eq(
                "season", "2025-2026"
            ).limit(1).execute()

            if comp_result.data and len(comp_result.data) > 0:
                competition_code = comp_result.data[0].get("competitions", {}).get("code")

                if competition_code:
                    factor_result = supabase.rpc(
                        "get_league_normalization",
                        {"p_competition_code": competition_code}
                    ).execute()
                    if factor_result.data:
                        league_factor = float(factor_result.data)
        except Exception:
            pass  # League baseline query failed

        analysis["competition"] = competition_code
        analysis["league_factor"] = league_factor
```

**Step 4: Applicare fattore nel calcolo**

Modificare il calcolo score:

```python
                # Applica tutti i moltiplicatori
                combined_score = base_score * home_away_factor * derby_multiplier * league_factor
                combined_score = min(combined_score, 100)
```

**Step 5: Commit**

```bash
git add database/migrations/002_league_baselines.sql mcp_server.py
git commit -m "$(cat <<'EOF'
feat: add league baseline normalization

- Create league_card_baselines view with research-based values
- La Liga highest (1.30x), Bundesliga lowest (0.95x)
- Serie A as baseline (1.0x)
- Apply normalization factor to risk scores

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Referee League Delta (Outlier Detection)

**Files:**
- Modify: `database/analysis_views.sql` (aggiungere colonna ref_league_delta)
- Modify: `mcp_server.py` (usare delta nel calcolo)

**Step 1: Creare migrazione per ref_league_delta**

Creare `database/migrations/003_referee_delta.sql`:

```sql
-- database/migrations/003_referee_delta.sql
-- Aggiunge calcolo delta arbitro rispetto alla media della lega

-- Vista arricchita degli arbitri con delta
CREATE OR REPLACE VIEW referee_league_comparison AS
WITH league_averages AS (
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
    -- Classificazione: outlier se delta > 1.0 o < -1.0
    CASE
        WHEN rbl.ref_avg_yellows - la.league_avg_yellows > 1.0 THEN 'STRICT_OUTLIER'
        WHEN rbl.ref_avg_yellows - la.league_avg_yellows < -1.0 THEN 'LENIENT_OUTLIER'
        WHEN rbl.ref_avg_yellows - la.league_avg_yellows > 0.5 THEN 'ABOVE_AVERAGE'
        WHEN rbl.ref_avg_yellows - la.league_avg_yellows < -0.5 THEN 'BELOW_AVERAGE'
        ELSE 'AVERAGE'
    END AS referee_profile
FROM referee_by_league rbl
JOIN league_averages la ON rbl.competition_code = la.competition_code
WHERE rbl.matches_in_league >= 3
ORDER BY ref_league_delta DESC;

-- Funzione per ottenere profilo arbitro
CREATE OR REPLACE FUNCTION get_referee_profile(p_referee_name TEXT)
RETURNS TABLE (
    referee_name TEXT,
    competition_code VARCHAR(10),
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

COMMENT ON VIEW referee_league_comparison IS 'Confronto arbitri vs media lega con classificazione outlier';
COMMENT ON FUNCTION get_referee_profile IS 'Restituisce profilo arbitro con delta rispetto a media lega';
```

**Step 2: Eseguire migrazione**

Run: Eseguire in Supabase SQL Editor

**Step 3: Integrare nel server MCP**

Modificare sezione arbitro in `mcp_server.py` (dopo riga ~478):

```python
            # Profilo arbitro (delta rispetto a lega)
            if referee:
                try:
                    profile_result = supabase.rpc(
                        "get_referee_profile",
                        {"p_referee_name": referee}
                    ).execute()

                    if profile_result.data and len(profile_result.data) > 0:
                        profile = profile_result.data[0]
                        analysis["referee_profile"] = {
                            "avg_yellows": float(profile.get("ref_avg_yellows") or 0),
                            "league_avg": float(profile.get("league_avg_yellows") or 0),
                            "delta": float(profile.get("ref_league_delta") or 0),
                            "classification": profile.get("referee_profile")
                        }

                        # Aggiusta score arbitro in base a delta
                        # Outlier severo: +15% al peso arbitro
                        # Outlier permissivo: -15% al peso arbitro
                        ref_delta = float(profile.get("ref_league_delta") or 0)
                        if ref_delta > 1.0:
                            analysis["referee_adjustment"] = 1.15
                        elif ref_delta < -1.0:
                            analysis["referee_adjustment"] = 0.85
                        else:
                            analysis["referee_adjustment"] = 1.0
                except Exception:
                    analysis["referee_adjustment"] = 1.0
```

**Step 4: Applicare adjustment**

Modificare calcolo referee_score:

```python
                if referee and player_name_lower in referee_data:
                    ref_info = referee_data[player_name_lower]
                    referee_score = ref_info["booking_percentage"] * analysis.get("referee_adjustment", 1.0)
```

**Step 5: Commit**

```bash
git add database/migrations/003_referee_delta.sql mcp_server.py
git commit -m "$(cat <<'EOF'
feat: add referee outlier detection with league delta

- Create referee_league_comparison view
- Calculate ref_league_delta (avg vs league avg)
- Classify referees: STRICT_OUTLIER, LENIENT_OUTLIER, AVERAGE
- Apply ±15% adjustment for outlier referees

Research: ~23% of referees are statistical outliers.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Matchup Posizionale (Pace Differential)

**Files:**
- Modify: `mcp_server.py` (aggiungere logica matchup)

**Step 1: Definire matchup rischiosi**

Aggiungere costanti dopo i pesi (riga ~435):

```python
    # Matchup posizionali rischiosi (ricerca: SPA = Stopping Promising Attack)
    # Terzini vs ali veloci = alto rischio SPA
    RISKY_MATCHUPS = {
        # (posizione_difensore, posizione_attaccante_avversario): bonus_rischio
        ("Defence", "Offence"): 0.10,      # Difensore vs Attaccante: +10%
        ("Midfield", "Offence"): 0.08,     # Centrocampista vs Attaccante: +8%
        ("Defence", "Midfield"): 0.05,     # Difensore vs Centrocampista: +5%
    }

    # Giocatori noti per creare falli (dribblatori, velocisti)
    # Questi dati potrebbero venire da un'API o tabella dedicata
    HIGH_FOUL_DRAWERS = {
        "vinícius": 1.15,
        "vinicius": 1.15,
        "rafael leao": 1.12,
        "leao": 1.12,
        "khvicha kvaratskhelia": 1.12,
        "kvaratskhelia": 1.12,
        "doku": 1.10,
        "saka": 1.10,
        "yamal": 1.08,
    }
```

**Step 2: Calcolare opponent foul drawing**

Aggiungere dopo le query squadra (riga ~465):

```python
        # --- OPPONENT FOUL DRAWING ---
        # Calcola quanto l'avversario tende a subire falli
        opponent_foul_factor = {}
        for team, opponent in [(home_team, away_team), (away_team, home_team)]:
            try:
                opp_result = supabase.table("player_season_cards").select(
                    "player_name"
                ).ilike("team_name", f"%{opponent}%").eq(
                    "season", "2025-2026"
                ).execute()

                factor = 1.0
                if opp_result.data:
                    for p in opp_result.data:
                        pname = p.get("player_name", "").lower()
                        for foul_drawer, bonus in HIGH_FOUL_DRAWERS.items():
                            if foul_drawer in pname:
                                factor = max(factor, bonus)

                opponent_foul_factor[team.lower()] = factor
            except Exception:
                opponent_foul_factor[team.lower()] = 1.0

        analysis["opponent_foul_factors"] = opponent_foul_factor
```

**Step 3: Applicare matchup nel calcolo score**

Nel loop giocatori, dopo `position_multiplier`:

```python
                # Matchup bonus (SPA risk)
                matchup_bonus = 1.0
                opponent_name = away_team if is_home else home_team

                # Bonus se l'avversario ha foul drawers
                matchup_bonus *= opponent_foul_factor.get(team_name.lower(), 1.0)

                # Bonus posizionale
                if position in ["Defence", "Midfield"]:
                    # Difensori e centrocampisti rischiano SPA contro attaccanti veloci
                    matchup_bonus *= 1.05  # +5% base per ruoli difensivi
```

E nel calcolo finale:

```python
                combined_score = base_score * home_away_factor * derby_multiplier * league_factor * matchup_bonus
```

**Step 4: Aggiungere al breakdown**

```python
                    "matchup": {
                        "bonus": round(matchup_bonus, 2),
                        "opponent_foul_factor": opponent_foul_factor.get(team_name.lower(), 1.0)
                    }
```

**Step 5: Testare**

Run:
```bash
cd /home/salvatore/Scrivania/soccer
./venv/bin/python -c "
from mcp_server import analyze_match_risk
import json
# Test con squadra che ha Leao (Milan)
result = json.loads(analyze_match_risk('Inter', 'Milan'))
print('Opponent foul factors:', result.get('opponent_foul_factors'))
# I difensori dell'Inter dovrebbero avere matchup bonus > 1.0
for p in result.get('home_team_top5', [])[:2]:
    print(f\"{p['name']}: matchup={p.get('breakdown',{}).get('matchup')}\")
"
```

Expected: `Opponent foul factors: {'inter': 1.12, 'milan': ...}` (Leao = 1.12)

**Step 6: Commit**

```bash
git add mcp_server.py
git commit -m "$(cat <<'EOF'
feat(mcp): add positional matchup analysis

- Define risky matchups (defenders vs forwards = SPA risk)
- Track high foul-drawing players (Vinicius, Leao, etc.)
- Apply matchup bonus to defenders facing tricky wingers
- Add matchup breakdown to player analysis

Research: Pace differential between fullback and winger is key SPA predictor.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Aggiornare Documentazione

**Files:**
- Modify: `docs/SCORING.md`
- Modify: `STATO_PROGETTO.md`

**Step 1: Aggiornare SCORING.md**

Aggiungere sezione "Moltiplicatori Contestuali":

```markdown
## Moltiplicatori Contestuali (v2 - Research-Based)

Il sistema applica moltiplicatori basati su ricerca accademica (2024-2026).

### Derby Multiplier

| Intensità | Moltiplicatore | Esempio |
|-----------|----------------|---------|
| 1 (Normale) | ×1.10 | Rivalità regionali minori |
| 2 (Sentito) | ×1.18 | Napoli-Juventus |
| 3 (Storico) | ×1.26 | Derby della Madonnina, El Clásico |

**Fonte:** Ricerca mostra +20-30% cartellini nei derby rispetto a partite standard.

### Home/Away Factor

| Situazione | Moltiplicatore |
|------------|----------------|
| Casa | ×0.94 |
| Trasferta | ×1.06 |

**Fonte:** Studio CIES su 101,491 partite: 53% cartellini alla trasferta.

### League Baseline

| Lega | Fattore | Gialli/Partita |
|------|---------|----------------|
| La Liga | ×1.30 | 5.33 |
| Premier League | ×1.18 | 4.85 |
| Serie A | ×1.00 | 4.10 (baseline) |
| Bundesliga | ×0.95 | 3.90 |
| Ligue 1 | ×0.89 | 3.65 |

### Referee Delta

| Profilo | Delta | Adjustment |
|---------|-------|------------|
| STRICT_OUTLIER | > +1.0 | ×1.15 |
| LENIENT_OUTLIER | < -1.0 | ×0.85 |
| AVERAGE | -1.0 to +1.0 | ×1.00 |

**Fonte:** ~23% degli arbitri sono outlier statistici.

### Matchup Bonus

| Situazione | Bonus |
|------------|-------|
| Difensore vs Foul Drawer (Vinicius, Leao) | fino a ×1.15 |
| Centrocampista difensivo | ×1.05 base |

## Formula Completa v2

```
Score = Base_Score × Home_Away × Derby × League × Matchup

Dove Base_Score = (Stagionale×35%) + (Arbitro×30%×Ref_Adj) + (H2H×15%) + (Falli×20%)
```
```

**Step 2: Aggiornare STATO_PROGETTO.md**

Aggiungere in cronologia:

```markdown
### 2026-01-27 (Sessione 6)
- **Research-Based Improvements:**
  - Task 1-2: Derby flag con tabella rivalità e moltiplicatore intensità
  - Task 3: Fattore casa/trasferta (0.94/1.06)
  - Task 4: Normalizzazione baseline per lega
  - Task 5: Referee delta e outlier detection
  - Task 6: Matchup posizionale (SPA risk)
  - Task 7: Documentazione aggiornata
- **Impatto stimato:** +15-25% accuratezza predittiva
```

**Step 3: Commit finale**

```bash
git add docs/SCORING.md STATO_PROGETTO.md
git commit -m "$(cat <<'EOF'
docs: update scoring documentation with research-based improvements

- Add contextual multipliers section (derby, home/away, league, matchup)
- Document referee delta and outlier detection
- Update project status with session 6 changelog

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Possession Differential Factor

**Fonte:** Reddit r/SoccerBetting - "if you expect one team to dominate possession, you might see more fouling from the other team"

**Logica:** La squadra con meno possesso palla deve rincorrere di più → commette più falli → più rischio cartellini per i suoi giocatori.

**Files:**
- Create: `database/migrations/004_possession_factor.sql`
- Modify: `mcp_server.py` (funzione analyze_match_risk)

**Step 1: Creare vista per possesso medio squadra**

Creare `database/migrations/004_possession_factor.sql`:

```sql
-- database/migrations/004_possession_factor.sql
-- Calcola possesso medio per squadra e fattore di rischio cartellino

-- Vista: Possesso medio per squadra nella stagione
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
    -- Falli medi commessi (correlati inversamente al possesso)
    ROUND(AVG(ms.fouls_committed)::NUMERIC, 1) AS avg_fouls_committed
FROM teams t
JOIN match_statistics ms ON t.id = ms.team_id
JOIN matches m ON ms.match_id = m.id
WHERE m.status = 'FINISHED'
AND ms.ball_possession IS NOT NULL
GROUP BY t.id, t.name, m.season
HAVING COUNT(DISTINCT m.id) >= 3;

-- Funzione: Calcola fattore possesso per una partita
-- Restituisce moltiplicatore per ogni squadra basato sulla differenza di possesso attesa
CREATE OR REPLACE FUNCTION get_possession_factor(
    p_home_team_name TEXT,
    p_away_team_name TEXT,
    p_season TEXT DEFAULT '2025-2026'
)
RETURNS TABLE (
    home_team TEXT,
    home_avg_possession NUMERIC,
    home_possession_factor NUMERIC,
    away_team TEXT,
    away_avg_possession NUMERIC,
    away_possession_factor NUMERIC,
    expected_possession_diff NUMERIC
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_home_poss NUMERIC;
    v_away_poss NUMERIC;
    v_home_factor NUMERIC;
    v_away_factor NUMERIC;
BEGIN
    -- Recupera possesso medio squadra casa
    SELECT avg_possession INTO v_home_poss
    FROM team_possession_stats
    WHERE LOWER(team_name) LIKE '%' || LOWER(p_home_team_name) || '%'
    AND season = p_season
    LIMIT 1;

    -- Recupera possesso medio squadra trasferta
    SELECT avg_possession INTO v_away_poss
    FROM team_possession_stats
    WHERE LOWER(team_name) LIKE '%' || LOWER(p_away_team_name) || '%'
    AND season = p_season
    LIMIT 1;

    -- Default se non trovato
    v_home_poss := COALESCE(v_home_poss, 50);
    v_away_poss := COALESCE(v_away_poss, 50);

    -- Calcola fattori: chi ha meno possesso ha moltiplicatore > 1
    -- Formula: 1 + (50 - possesso) * 0.01
    -- Esempio: 40% possesso → 1 + (50-40)*0.01 = 1.10 (+10% rischio)
    -- Esempio: 60% possesso → 1 + (50-60)*0.01 = 0.90 (-10% rischio)
    v_home_factor := 1 + (50 - v_home_poss) * 0.01;
    v_away_factor := 1 + (50 - v_away_poss) * 0.01;

    -- Limita i fattori tra 0.85 e 1.15
    v_home_factor := GREATEST(0.85, LEAST(1.15, v_home_factor));
    v_away_factor := GREATEST(0.85, LEAST(1.15, v_away_factor));

    RETURN QUERY SELECT
        p_home_team_name,
        v_home_poss,
        ROUND(v_home_factor, 2),
        p_away_team_name,
        v_away_poss,
        ROUND(v_away_factor, 2),
        ROUND(v_home_poss - v_away_poss, 1);
END;
$$;

COMMENT ON VIEW team_possession_stats IS 'Statistiche possesso palla per squadra - correlato inversamente ai falli';
COMMENT ON FUNCTION get_possession_factor IS 'Calcola moltiplicatore rischio cartellino basato su possesso atteso';
```

**Step 2: Eseguire migrazione**

Run: Eseguire `database/migrations/004_possession_factor.sql` in Supabase SQL Editor

**Step 3: Verificare creazione**

Run (in SQL Editor):
```sql
-- Test vista
SELECT * FROM team_possession_stats WHERE season = '2025-2026' ORDER BY avg_possession DESC LIMIT 10;

-- Test funzione
SELECT * FROM get_possession_factor('Inter', 'Napoli', '2025-2026');
```

Expected: Inter ~55% possesso (factor ~0.95), Napoli ~52% possesso (factor ~0.98)

**Step 4: Integrare nel server MCP**

Modificare `mcp_server.py`, aggiungendo dopo la sezione derby (circa riga 495):

```python
        # --- POSSESSION FACTOR ---
        possession_factors = {"home": 1.0, "away": 1.0}
        try:
            poss_result = supabase.rpc(
                "get_possession_factor",
                {
                    "p_home_team_name": home_team,
                    "p_away_team_name": away_team,
                    "p_season": "2025-2026"
                }
            ).execute()

            if poss_result.data and len(poss_result.data) > 0:
                poss = poss_result.data[0]
                possession_factors = {
                    "home": float(poss.get("home_possession_factor") or 1.0),
                    "away": float(poss.get("away_possession_factor") or 1.0)
                }
                analysis["possession"] = {
                    "home_avg": float(poss.get("home_avg_possession") or 50),
                    "away_avg": float(poss.get("away_avg_possession") or 50),
                    "expected_diff": float(poss.get("expected_possession_diff") or 0),
                    "home_factor": possession_factors["home"],
                    "away_factor": possession_factors["away"]
                }
        except Exception:
            pass  # Possession query failed, use default 1.0
```

**Step 5: Applicare fattore nel calcolo score**

Nel loop giocatori, recuperare il fattore corretto:

```python
            # Fattore possesso (chi ha meno possesso commette più falli)
            possession_factor = possession_factors["home"] if is_home else possession_factors["away"]
```

E nel calcolo finale:

```python
                # Applica tutti i moltiplicatori
                combined_score = base_score * home_away_factor * derby_multiplier * league_factor * matchup_bonus * possession_factor
                combined_score = min(combined_score, 100)
```

**Step 6: Aggiungere al breakdown**

```python
                    "possession_factor": possession_factor,
```

**Step 7: Testare**

Run:
```bash
cd /home/salvatore/Scrivania/soccer
./venv/bin/python -c "
from mcp_server import analyze_match_risk
import json

# Test: squadra possesso vs squadra counter-attack
result = json.loads(analyze_match_risk('Napoli', 'Atalanta'))
print('Possession info:', result.get('possession'))
print()
print('Napoli (alto possesso) top player:')
home = result.get('home_team_top5', [{}])[0]
print(f\"  {home.get('name')}: poss_factor={home.get('breakdown',{}).get('possession_factor')}\")
print()
print('Atalanta (pressing aggressivo) top player:')
away = result.get('away_team_top5', [{}])[0]
print(f\"  {away.get('name')}: poss_factor={away.get('breakdown',{}).get('possession_factor')}\")
"
```

Expected: Napoli factor < 1.0 (meno rischio), Atalanta factor > 1.0 (più rischio per pressing)

**Step 8: Commit**

```bash
git add database/migrations/004_possession_factor.sql mcp_server.py
git commit -m "$(cat <<'EOF'
feat: add possession differential factor to risk calculation

- Create team_possession_stats view for avg possession per team
- Add get_possession_factor() function
- Low possession teams: up to +15% card risk (more chasing)
- High possession teams: up to -15% card risk (control game)

Source: Reddit r/SoccerBetting insight on game flow and fouling patterns.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Riepilogo Modifiche

| Task | File Principali | Impatto |
|------|-----------------|---------|
| 1-2 | `001_derby_rivalries.sql`, `mcp_server.py` | Derby +10-26% |
| 3 | `mcp_server.py` | Home -6%, Away +6% |
| 4 | `002_league_baselines.sql`, `mcp_server.py` | Cross-league normalization |
| 5 | `003_referee_delta.sql`, `mcp_server.py` | Outlier ±15% |
| 6 | `mcp_server.py` | Matchup +5-15% |
| 7 | `SCORING.md`, `STATO_PROGETTO.md` | Documentazione |
| 8 | `004_possession_factor.sql`, `mcp_server.py` | Possession ±15% |

## Test Finale Integrato

```bash
cd /home/salvatore/Scrivania/soccer
./venv/bin/python -c "
from mcp_server import analyze_match_risk
import json

# Test completo: Derby Inter-Milan
result = json.loads(analyze_match_risk('Inter', 'Milan', 'Maresca'))
print('=== ANALISI INTER-MILAN (con Maresca) ===')
print(f\"Derby: {result.get('derby')}\")
print(f\"Derby multiplier: {result.get('derby_multiplier')}\")
print(f\"League factor: {result.get('league_factor')}\")
print(f\"Referee profile: {result.get('referee_profile')}\")
print(f\"Opponent foul factors: {result.get('opponent_foul_factors')}\")
print(f\"Possession: {result.get('possession')}\")
print()
print('Top 3 rischio:')
for p in result.get('overall_top5', [])[:3]:
    bd = p.get('breakdown', {})
    print(f\"  {p['name']}: {p['combined_score']} (home={p.get('is_home')}, poss={bd.get('possession_factor')})\")
"
```

Expected output: Scores più alti per trasferta, moltiplicatore derby 1.26, Maresca come STRICT_OUTLIER, possession factors basati su storico squadre.
