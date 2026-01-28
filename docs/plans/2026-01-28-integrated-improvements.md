# Piano Integrato: Research Improvements + Dashboard

> **Per Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implementare miglioramenti al modello di scoring (+15-25% accuratezza) E aggiornare la dashboard per riflettere tutte le nuove feature.

**Struttura:**
- **Fase 0:** Ricerca preliminare derby
- **Fase A (Task 1-4):** Migrazioni database (parallele)
- **Fase B (Task 5):** Integrazione MCP server
- **Fase C (Task 6-10):** Dashboard updates (5 task)
- **Fase D (Task 11):** Documentazione finale

**Tech Stack:** PostgreSQL (Supabase), Python 3.x, FastMCP, Streamlit, SQL Views/Functions

---

## FASE 0: RICERCA PRELIMINARE

---

## Task 0: Ricerca Completa Derby e Rivalità

**Prerequisito:** Questo task DEVE essere completato PRIMA di eseguire Task 1.

**Obiettivo:** Ricercare sul web tutti i derby e le rivalità storiche per le 7 competizioni supportate.

**Step 1: Ricerca Web per ogni competizione**

| Competizione | Query di ricerca |
|--------------|------------------|
| Serie A (SA) | "Serie A derby rivalità lista completa" |
| La Liga (PD) | "La Liga derbies rivalries complete list" |
| Premier League (PL) | "Premier League derbies complete list" |
| Bundesliga (BL1) | "Bundesliga derbies complete list" |
| Ligue 1 (FL1) | "Ligue 1 derbies complete list" |
| Brasileirão (BSA) | "Campeonato Brasileiro clássicos rivalidades" |
| Champions League (CL) | Usa le rivalità nazionali già trovate |

**Step 2: Per ogni rivalità raccogliere:**
- Nome squadra 1 e 2
- Nome del derby (se ha un nome specifico)
- Tipo: `DERBY` (stessa città), `HISTORIC` (rivalità storica), `REGIONAL` (stessa regione)
- Intensità: `1` (minore), `2` (sentito), `3` (storico/massima rivalità)

**Step 3: Verificare nomi squadre nel database**

```bash
./venv/bin/python -c "
from supabase import create_client
import os
from dotenv import load_dotenv
load_dotenv()
sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
result = sb.table('teams').select('name').execute()
for t in sorted([x['name'] for x in result.data]):
    print(t)
"
```

**Step 4: Generare INSERT SQL** per Task 1

**Output atteso:** Lista SQL con 50-100 rivalità.

---

## FASE A: MIGRAZIONI DATABASE

> Task 1-4 possono essere eseguiti in parallelo dopo Task 0.

---

## Task 1: Derby Rivalries - Tabella e Funzione

**Files:** `database/migrations/001_derby_rivalries.sql`

**Step 1: Creare directory**

```bash
mkdir -p /home/salvatore/Scrivania/soccer/database/migrations
```

**Step 2: Creare file migrazione**

```sql
-- database/migrations/001_derby_rivalries.sql
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

-- INSERT rivalità da Task 0 (placeholder - sostituire con output Task 0)
-- INSERT INTO rivalries (team1_id, team2_id, rivalry_name, rivalry_type, intensity) VALUES ...

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

    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, NULL::TEXT, NULL::TEXT, NULL::INTEGER;
    END IF;
END;
$$;

COMMENT ON TABLE rivalries IS 'Definizione rivalità/derby tra squadre per calcolo risk score';
```

**Step 3:** Eseguire in Supabase SQL Editor

**Step 4:** Verificare
```sql
SELECT * FROM rivalries;
SELECT * FROM is_derby_match(
    (SELECT id FROM teams WHERE name ILIKE '%Inter%' LIMIT 1),
    (SELECT id FROM teams WHERE name ILIKE '%Milan%' AND name NOT ILIKE '%Inter%' LIMIT 1)
);
```

**Step 5:** Commit
```bash
git add database/migrations/001_derby_rivalries.sql
git commit -m "feat(db): add rivalries table for derby detection"
```

---

## Task 2: League Baselines - Vista e Funzione

**Files:** `database/migrations/002_league_baselines.sql`

```sql
-- database/migrations/002_league_baselines.sql
CREATE OR REPLACE VIEW league_card_baselines AS
SELECT
    c.code AS competition_code,
    c.name AS competition_name,
    CASE c.code
        WHEN 'PD' THEN 5.33   -- La Liga
        WHEN 'SA' THEN 4.10   -- Serie A
        WHEN 'PL' THEN 4.85   -- Premier League
        WHEN 'BL1' THEN 3.90  -- Bundesliga
        WHEN 'FL1' THEN 3.65  -- Ligue 1
        WHEN 'CL' THEN 4.20   -- Champions League
        WHEN 'BSA' THEN 4.50  -- Brasileirão
        ELSE 4.00
    END AS baseline_yellows_per_match,
    CASE c.code
        WHEN 'PD' THEN 1.30
        WHEN 'SA' THEN 1.00
        WHEN 'PL' THEN 1.18
        WHEN 'BL1' THEN 0.95
        WHEN 'FL1' THEN 0.89
        WHEN 'CL' THEN 1.02
        WHEN 'BSA' THEN 1.10
        ELSE 1.00
    END AS normalization_factor
FROM competitions c;

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
```

**Verifica:** `SELECT * FROM league_card_baselines;`

**Commit:** `git commit -m "feat(db): add league baseline normalization"`

---

## Task 3: Referee Delta - Outlier Detection

**Files:** `database/migrations/003_referee_delta.sql`

```sql
-- database/migrations/003_referee_delta.sql
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
```

**Verifica:** `SELECT * FROM referee_league_comparison WHERE competition_code = 'SA' LIMIT 10;`

**Commit:** `git commit -m "feat(db): add referee outlier detection"`

---

## Task 4: Possession Factor - Vista e Funzione

**Files:** `database/migrations/004_possession_factor.sql`

```sql
-- database/migrations/004_possession_factor.sql
CREATE OR REPLACE VIEW team_possession_stats AS
SELECT
    t.id AS team_id,
    t.name AS team_name,
    m.season,
    COUNT(DISTINCT m.id) AS matches_played,
    ROUND(AVG(ms.ball_possession)::NUMERIC, 1) AS avg_possession,
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
HAVING COUNT(DISTINCT m.id) >= 3;

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
    SELECT avg_possession INTO v_home_poss
    FROM team_possession_stats
    WHERE LOWER(team_name) LIKE '%' || LOWER(p_home_team_name) || '%'
    AND season = p_season LIMIT 1;

    SELECT avg_possession INTO v_away_poss
    FROM team_possession_stats
    WHERE LOWER(team_name) LIKE '%' || LOWER(p_away_team_name) || '%'
    AND season = p_season LIMIT 1;

    v_home_poss := COALESCE(v_home_poss, 50);
    v_away_poss := COALESCE(v_away_poss, 50);

    v_home_factor := 1 + (50 - v_home_poss) * 0.01;
    v_away_factor := 1 + (50 - v_away_poss) * 0.01;

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
```

**Verifica:** `SELECT * FROM get_possession_factor('Inter', 'Napoli', '2025-2026');`

**Commit:** `git commit -m "feat(db): add possession differential factor"`

---

## FASE B: INTEGRAZIONE MCP SERVER

---

## Task 5: Integrazione Completa in analyze_match_risk

**Files:** Modify `mcp_server.py`

**Obiettivo:** Sostituire la funzione `analyze_match_risk` con la versione che integra tutti i nuovi fattori:
- Derby detection (×1.10-1.26)
- Home/Away factor (×0.94/×1.06)
- League baseline normalization
- Referee delta/outlier (±15%)
- Possession factor (±15%)
- Matchup bonus (foul drawers)

**Step 1:** Leggere il file corrente e individuare la funzione `analyze_match_risk`

**Step 2:** Sostituire con la versione completa (vedi `docs/plans/2026-01-27-research-improvements.md` Task 5 per il codice completo)

**Step 3:** Testare
```bash
./venv/bin/python -c "
from mcp_server import analyze_match_risk
import json
result = json.loads(analyze_match_risk('Inter', 'Milan', 'Maresca'))
print(f\"Derby: {result.get('derby')}\")
print(f\"Multipliers: {result.get('multipliers')}\")
print(f\"Top 3: {[p['name'] for p in result.get('overall_top5', [])[:3]]}\")
"
```

**Step 4:** Commit
```bash
git commit -m "feat(mcp): integrate all research-based multipliers in analyze_match_risk"
```

---

## FASE C: DASHBOARD UPDATES

---

## Task 6: Aggiornare Pagina Arbitri

**Files:** Modify `dashboard/pages/2_referees.py`

**Obiettivo:** Aggiungere colonna "Profilo" con classificazione outlier (STRICT_OUTLIER, LENIENT_OUTLIER, AVERAGE, etc.)

**Modifiche:**

1. **Tab 1 - Classifica Arbitri:** Aggiungere colonne dalla vista `referee_league_comparison`:
   - `ref_avg_yellows` - Media gialli arbitro
   - `league_avg_yellows` - Media lega
   - `ref_league_delta` - Delta (+/-)
   - `referee_profile` - Badge colorato (rosso=STRICT, verde=LENIENT, grigio=AVERAGE)

2. **Query aggiornata:**
```python
result = supabase.table("referee_league_comparison").select(
    "referee_name, competition_code, matches_in_league, ref_avg_yellows, "
    "league_avg_yellows, ref_league_delta, referee_profile"
).order("ref_league_delta", desc=True).execute()
```

3. **Visualizzazione profilo con colori:**
```python
def format_profile(profile):
    colors = {
        "STRICT_OUTLIER": "🔴",
        "ABOVE_AVERAGE": "🟠",
        "AVERAGE": "⚪",
        "BELOW_AVERAGE": "🟢",
        "LENIENT_OUTLIER": "🟢"
    }
    return f"{colors.get(profile, '⚪')} {profile}"
```

4. **Filtro per competizione** nella sidebar

**Commit:** `git commit -m "feat(dashboard): add referee profile/outlier column"`

---

## Task 7: Riscrivere Pagina Analisi Partita

**Files:** Rewrite `dashboard/pages/3_match_analysis.py`

**Obiettivo:** La pagina deve chiamare `analyze_match_risk` dal MCP server e visualizzare TUTTI i dati restituiti.

### Layout della pagina:

```
┌─────────────────────────────────────────────────────────────────┐
│  HEADER: Input selezione                                        │
│  [Squadra Casa ▼]  [Squadra Trasferta ▼]  [Arbitro ▼]          │
│  [🔍 Analizza Partita]                                          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  CARD INFO PARTITA                                              │
│  ⚽ INTER vs MILAN                                              │
│  ───────────────────────────────────────────────────────────    │
│  🔥 Derby della Madonnina (intensità 3)    │  🏆 Serie A (×1.0) │
│  👨‍⚖️ Maresca - STRICT_OUTLIER (+1.2 delta) │  📊 5.2 gialli/p  │
│  📈 Possesso: Inter 54% (×0.96) │ Milan 48% (×1.02)            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  MULTIPLIERS ATTIVI (pills/badges)                              │
│  [🔥 Derby ×1.26] [🏠 Home ×0.94] [📊 League ×1.0] [⚽ Poss]    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  TOP 5 RISCHIO COMPLESSIVO                                      │
│  ┌─────┬────────────┬─────┬───────┬──────────────────────────┐  │
│  │ #   │ Giocatore  │ Sq. │ Score │ ████████████░░░░░░░░░░░░ │  │
│  ├─────┼────────────┼─────┼───────┼──────────────────────────┤  │
│  │ 1   │ Barella    │ INT │ 72.3  │ ████████████████████░░░░ │  │
│  │ 2   │ Theo       │ MIL │ 68.1  │ ███████████████████░░░░░ │  │
│  │ ... │            │     │       │                          │  │
│  └─────┴────────────┴─────┴───────┴──────────────────────────┘  │
│  [▼ Espandi breakdown]                                          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  TABS: [🏠 Inter (Casa)] [✈️ Milan (Trasferta)]                 │
│  ───────────────────────────────────────────────────────────    │
│  Tabella completa giocatori squadra con breakdown               │
└─────────────────────────────────────────────────────────────────┘
```

### Codice struttura:

```python
"""
YellowOracle - Analisi Partita (v2 - MCP Integration)
"""
import streamlit as st
import pandas as pd
import json
import os
import sys

# Aggiungi path per import mcp_server
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from mcp_server import analyze_match_risk, get_supabase

st.set_page_config(page_title="Analisi Partita - YellowOracle", page_icon="⚽", layout="wide")

def main():
    st.title("⚽ Analisi Partita")
    st.markdown("Analisi pre-partita con tutti i fattori di rischio")

    supabase = get_supabase()

    # --- INPUT SECTION ---
    teams_data = supabase.table("teams").select("name").order("name").execute()
    teams_list = [t["name"] for t in teams_data.data]

    referees_data = supabase.table("referees").select("name").order("name").execute()
    referees_list = ["Non designato"] + [r["name"] for r in referees_data.data]

    col1, col2, col3 = st.columns(3)
    with col1:
        home_team = st.selectbox("Squadra Casa", teams_list)
    with col2:
        away_team = st.selectbox("Squadra Trasferta", teams_list, index=1)
    with col3:
        referee = st.selectbox("Arbitro", referees_list)

    if st.button("🔍 Analizza Partita", type="primary", use_container_width=True):
        if home_team == away_team:
            st.error("Seleziona due squadre diverse")
            return

        # Chiama MCP tool
        ref_param = referee if referee != "Non designato" else None
        with st.spinner("Analisi in corso..."):
            result_json = analyze_match_risk(home_team, away_team, ref_param)

        try:
            result = json.loads(result_json)
        except:
            st.error(f"Errore: {result_json}")
            return

        st.markdown("---")

        # --- INFO PARTITA CARD ---
        render_match_info(result)

        # --- MULTIPLIERS PILLS ---
        render_multipliers(result)

        # --- TOP 5 TABLE ---
        render_top5(result)

        # --- TEAM TABS ---
        render_team_tabs(result, home_team, away_team)


def render_match_info(result):
    """Render card info partita."""
    st.subheader(f"⚽ {result['match']}")

    col1, col2 = st.columns(2)

    with col1:
        # Derby info
        derby = result.get("derby")
        if derby:
            st.success(f"🔥 **{derby.get('name') or 'Derby'}** (intensità {derby.get('intensity')})")
        else:
            st.info("Partita regolare (no derby)")

        # Competition
        comp = result.get("competition")
        if comp:
            league_mult = result.get("multipliers", {}).get("league", 1.0)
            st.metric("Competizione", comp, f"×{league_mult}")

    with col2:
        # Referee info
        ref_stats = result.get("referee_stats")
        ref_profile = result.get("referee_profile")

        if ref_stats:
            profile_badge = ""
            if ref_profile:
                profile_type = ref_profile.get("classification", "")
                delta = ref_profile.get("delta", 0)
                badges = {"STRICT_OUTLIER": "🔴", "LENIENT_OUTLIER": "🟢", "AVERAGE": "⚪"}
                profile_badge = f"{badges.get(profile_type, '⚪')} {profile_type} ({delta:+.1f})"

            st.metric(
                f"👨‍⚖️ {ref_stats.get('name', 'N/A')}",
                f"{ref_stats.get('avg_yellows_per_match', 0):.1f} gialli/partita",
                profile_badge
            )
        else:
            st.warning("Arbitro non designato")

        # Possession
        poss = result.get("possession")
        if poss:
            st.caption(f"📈 Possesso atteso: {poss.get('home_avg', 50):.0f}% vs {poss.get('away_avg', 50):.0f}%")


def render_multipliers(result):
    """Render multipliers come pills."""
    mults = result.get("multipliers", {})
    derby = result.get("derby")
    poss = result.get("possession")

    pills = []

    if derby:
        pills.append(f"🔥 Derby ×{mults.get('derby', 1.0)}")

    pills.append(f"🏠 Home ×0.94")
    pills.append(f"✈️ Away ×1.06")

    league = mults.get("league", 1.0)
    if league != 1.0:
        pills.append(f"🏆 League ×{league}")

    ref_adj = mults.get("referee_adjustment", 1.0)
    if ref_adj != 1.0:
        pills.append(f"👨‍⚖️ Ref ×{ref_adj}")

    if poss:
        pills.append(f"⚽ Poss H×{poss.get('home_factor', 1.0)} A×{poss.get('away_factor', 1.0)}")

    st.markdown(" ".join([f"`{p}`" for p in pills]))


def render_top5(result):
    """Render tabella top 5 con progress bar."""
    st.subheader("🎯 Top 5 Rischio Cartellino")

    top5 = result.get("overall_top5", [])
    if not top5:
        st.info("Nessun dato disponibile")
        return

    rows = []
    for i, p in enumerate(top5, 1):
        bd = p.get("breakdown", {})
        rows.append({
            "#": i,
            "Giocatore": p.get("name"),
            "Squadra": p.get("team"),
            "Ruolo": p.get("position", "")[:3].upper(),
            "Score": p.get("combined_score", 0),
            "Stagione": bd.get("seasonal", {}).get("score", 0),
            "Arbitro": bd.get("referee", {}).get("score", 0) if bd.get("referee") else "-",
            "H2H": bd.get("h2h", {}).get("score", 0),
            "Falli": bd.get("fouls", {}).get("score", 0),
        })

    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Score": st.column_config.ProgressColumn(
                "Score",
                min_value=0,
                max_value=100,
                format="%.1f"
            )
        }
    )

    # Expander con breakdown dettagliato
    with st.expander("📊 Breakdown dettagliato"):
        for p in top5:
            bd = p.get("breakdown", {})
            mults = bd.get("multipliers", {})
            st.markdown(f"""
            **{p.get('name')}** ({p.get('team')}) - Score: **{p.get('combined_score')}**
            - Stagionale: {bd.get('seasonal', {}).get('per_90', 0):.2f} gialli/90 → {bd.get('seasonal', {}).get('score', 0):.1f}
            - Arbitro: {bd.get('referee', {}).get('detail') or 'N/A'} → {bd.get('referee', {}).get('score', 0) if bd.get('referee') else 'N/A'}
            - H2H: {bd.get('h2h', {}).get('detail') or 'N/A'} → {bd.get('h2h', {}).get('score', 0):.1f}
            - Multipliers: home/away={mults.get('home_away')}, derby={mults.get('derby')}, poss={mults.get('possession')}, matchup={mults.get('matchup')}
            """)


def render_team_tabs(result, home_team, away_team):
    """Render tabs per squadra."""
    st.markdown("---")

    tab1, tab2 = st.tabs([f"🏠 {home_team}", f"✈️ {away_team}"])

    for tab, team_key, team_name in [
        (tab1, "home_team_top5", home_team),
        (tab2, "away_team_top5", away_team)
    ]:
        with tab:
            players = result.get(team_key, [])
            if not players:
                st.info(f"Nessun dato per {team_name}")
                continue

            rows = []
            for p in players:
                bd = p.get("breakdown", {})
                rows.append({
                    "Giocatore": p.get("name"),
                    "Ruolo": p.get("position", ""),
                    "Score": p.get("combined_score", 0),
                    "Gialli Stagione": bd.get("seasonal", {}).get("yellows", 0),
                    "Gialli/90": bd.get("seasonal", {}).get("per_90", 0),
                })

            df = pd.DataFrame(rows)
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Score": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
                    "Gialli/90": st.column_config.NumberColumn(format="%.2f"),
                }
            )


if __name__ == "__main__":
    main()
```

**Step 1:** Sostituire il contenuto di `dashboard/pages/3_match_analysis.py`

**Step 2:** Testare
```bash
./venv/bin/streamlit run dashboard/app.py
```

**Step 3:** Commit
```bash
git commit -m "feat(dashboard): rewrite match analysis page with MCP integration"
```

---

## Task 8: Nuova Pagina Derby & Rivalità

**Files:** Create `dashboard/pages/4_rivalries.py`

**Obiettivo:** Mostrare tutte le rivalità configurate, filtrabili per competizione.

### Layout:

```
┌─────────────────────────────────────────────────────────────────┐
│  🔥 Derby & Rivalità                                            │
│  ───────────────────────────────────────────────────────────    │
│  Sidebar: [Competizione ▼] [Tipo ▼] [Intensità ▼]              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  METRICHE                                                       │
│  [Tot. Rivalità: 87] [Derby: 34] [Historic: 41] [Regional: 12] │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  TABELLA RIVALITÀ                                               │
│  ┌────────────────┬────────────────┬──────────────────┬───────┐ │
│  │ Squadra 1      │ Squadra 2      │ Nome Derby       │ Int.  │ │
│  ├────────────────┼────────────────┼──────────────────┼───────┤ │
│  │ Inter          │ Milan          │ Derby Madonnina  │ ⭐⭐⭐ │ │
│  │ Real Madrid    │ Barcelona      │ El Clásico       │ ⭐⭐⭐ │ │
│  └────────────────┴────────────────┴──────────────────┴───────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Codice:

```python
"""
YellowOracle - Derby & Rivalità
"""
import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

st.set_page_config(page_title="Derby & Rivalità - YellowOracle", page_icon="🔥", layout="wide")

@st.cache_resource
def get_supabase():
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def main():
    st.title("🔥 Derby & Rivalità")
    st.markdown("Elenco delle rivalità storiche configurate nel sistema")

    supabase = get_supabase()

    # Sidebar filtri
    st.sidebar.header("Filtri")

    rivalry_types = ["Tutti", "DERBY", "HISTORIC", "REGIONAL"]
    selected_type = st.sidebar.selectbox("Tipo rivalità", rivalry_types)

    intensities = ["Tutte", "3 - Massima", "2 - Sentita", "1 - Minore"]
    selected_intensity = st.sidebar.selectbox("Intensità", intensities)

    # Query rivalità con join squadre
    try:
        result = supabase.table("rivalries").select(
            "id, rivalry_name, rivalry_type, intensity, "
            "team1:team1_id(name), team2:team2_id(name)"
        ).execute()

        if not result.data:
            st.warning("Nessuna rivalità configurata. Esegui Task 0-1 del piano.")
            return

        # Trasforma dati
        rows = []
        for r in result.data:
            rows.append({
                "Squadra 1": r.get("team1", {}).get("name", "N/A"),
                "Squadra 2": r.get("team2", {}).get("name", "N/A"),
                "Nome Derby": r.get("rivalry_name") or "-",
                "Tipo": r.get("rivalry_type"),
                "Intensità": r.get("intensity"),
                "Intensità Display": "⭐" * r.get("intensity", 1)
            })

        df = pd.DataFrame(rows)

        # Applica filtri
        if selected_type != "Tutti":
            df = df[df["Tipo"] == selected_type]

        if selected_intensity != "Tutte":
            intensity_val = int(selected_intensity[0])
            df = df[df["Intensità"] == intensity_val]

        # Metriche
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Totale Rivalità", len(df))
        col2.metric("Derby (stessa città)", len(df[df["Tipo"] == "DERBY"]))
        col3.metric("Storiche", len(df[df["Tipo"] == "HISTORIC"]))
        col4.metric("Regionali", len(df[df["Tipo"] == "REGIONAL"]))

        st.markdown("---")

        # Tabella
        st.dataframe(
            df[["Squadra 1", "Squadra 2", "Nome Derby", "Tipo", "Intensità Display"]].rename(
                columns={"Intensità Display": "Intensità"}
            ),
            use_container_width=True,
            hide_index=True
        )

        # Info
        st.markdown("---")
        st.caption("""
        **Legenda Intensità:**
        - ⭐ = Rivalità minore
        - ⭐⭐ = Rivalità sentita
        - ⭐⭐⭐ = Derby storico (massimo impatto sul rischio cartellini)

        **Tipi:**
        - DERBY = Stessa città
        - HISTORIC = Rivalità storica tra club
        - REGIONAL = Rivalità regionale
        """)

    except Exception as e:
        st.error(f"Errore: {e}")
        st.info("La tabella 'rivalries' potrebbe non esistere. Esegui le migrazioni SQL.")


if __name__ == "__main__":
    main()
```

**Commit:** `git commit -m "feat(dashboard): add rivalries page"`

---

## Task 9: Nuova Pagina Statistiche Squadre

**Files:** Create `dashboard/pages/5_team_stats.py`

**Obiettivo:** Mostrare statistiche squadre: possesso, falli, stile di gioco.

### Layout:

```
┌─────────────────────────────────────────────────────────────────┐
│  📊 Statistiche Squadre                                         │
│  ───────────────────────────────────────────────────────────    │
│  Sidebar: [Stagione ▼] [Stile gioco ▼]                          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  TABELLA SQUADRE                                                │
│  ┌────────────┬──────────┬────────┬────────────┬──────────────┐ │
│  │ Squadra    │ Possesso │ Falli  │ Stile      │ Risk Factor  │ │
│  ├────────────┼──────────┼────────┼────────────┼──────────────┤ │
│  │ Man City   │ 64.2%    │ 9.1    │ POSSESSION │ ×0.86 ↓     │ │
│  │ Atalanta   │ 42.3%    │ 14.8   │ COUNTER    │ ×1.08 ↑     │ │
│  └────────────┴──────────┴────────┴────────────┴──────────────┘ │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  GRAFICO: Possesso vs Falli (scatter plot)                      │
│  [Chart showing inverse correlation]                            │
└─────────────────────────────────────────────────────────────────┘
```

### Codice:

```python
"""
YellowOracle - Statistiche Squadre
"""
import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

st.set_page_config(page_title="Statistiche Squadre - YellowOracle", page_icon="📊", layout="wide")

@st.cache_resource
def get_supabase():
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def main():
    st.title("📊 Statistiche Squadre")
    st.markdown("Possesso palla, falli e stile di gioco per squadra")

    supabase = get_supabase()

    # Sidebar
    st.sidebar.header("Filtri")
    seasons = ["2025-2026", "2024-2025", "2023-2024"]
    selected_season = st.sidebar.selectbox("Stagione", seasons)

    styles = ["Tutti", "POSSESSION_HEAVY", "BALANCED", "COUNTER_ATTACK", "DEFENSIVE"]
    selected_style = st.sidebar.selectbox("Stile gioco", styles)

    try:
        # Query vista team_possession_stats
        result = supabase.table("team_possession_stats").select("*").eq(
            "season", selected_season
        ).order("avg_possession", desc=True).execute()

        if not result.data:
            st.warning(f"Nessun dato per la stagione {selected_season}")
            st.info("La vista 'team_possession_stats' potrebbe non esistere o non avere dati.")
            return

        df = pd.DataFrame(result.data)

        # Calcola risk factor
        df["risk_factor"] = df["avg_possession"].apply(
            lambda x: round(1 + (50 - x) * 0.01, 2) if x else 1.0
        )
        df["risk_factor"] = df["risk_factor"].clip(0.85, 1.15)

        # Filtro stile
        if selected_style != "Tutti":
            df = df[df["play_style"] == selected_style]

        # Metriche
        col1, col2, col3 = st.columns(3)
        col1.metric("Squadre", len(df))
        col2.metric("Possesso medio", f"{df['avg_possession'].mean():.1f}%")
        col3.metric("Falli medi", f"{df['avg_fouls_committed'].mean():.1f}")

        st.markdown("---")

        # Tabella principale
        df_display = df.rename(columns={
            "team_name": "Squadra",
            "avg_possession": "Possesso %",
            "avg_fouls_committed": "Falli/Partita",
            "play_style": "Stile",
            "matches_played": "Partite",
            "risk_factor": "Risk Factor"
        })

        # Formatta risk factor con freccia
        df_display["Risk Factor"] = df_display["Risk Factor"].apply(
            lambda x: f"×{x:.2f} {'↓' if x < 1 else '↑' if x > 1 else ''}"
        )

        st.dataframe(
            df_display[["Squadra", "Possesso %", "Falli/Partita", "Stile", "Partite", "Risk Factor"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Possesso %": st.column_config.NumberColumn(format="%.1f%%"),
                "Falli/Partita": st.column_config.NumberColumn(format="%.1f"),
            }
        )

        # Grafico scatter: Possesso vs Falli
        st.markdown("---")
        st.subheader("📈 Correlazione Possesso - Falli")

        chart_data = df[["team_name", "avg_possession", "avg_fouls_committed"]].copy()
        chart_data.columns = ["Squadra", "Possesso", "Falli"]

        st.scatter_chart(
            chart_data,
            x="Possesso",
            y="Falli",
            size=100
        )

        st.caption("Tendenza: squadre con meno possesso commettono più falli → più rischio cartellini")

        # Legenda stili
        st.markdown("---")
        st.caption("""
        **Stili di gioco:**
        - POSSESSION_HEAVY (55%+): Controllo totale, pochi falli
        - BALANCED (50-55%): Equilibrato
        - COUNTER_ATTACK (45-50%): Ripartenze, più pressing
        - DEFENSIVE (<45%): Molto difensivo, molti falli
        """)

    except Exception as e:
        st.error(f"Errore: {e}")
        st.info("Esegui Task 4 per creare la vista 'team_possession_stats'")


if __name__ == "__main__":
    main()
```

**Commit:** `git commit -m "feat(dashboard): add team stats page with possession/fouls"`

---

## Task 10: Aggiornare Homepage

**Files:** Modify `dashboard/app.py`

**Obiettivo:** Aggiornare homepage con nuove metriche e info.

**Modifiche:**

1. **Nuove metriche:**
   - Rivalità configurate
   - Prossimi derby (se disponibili)

2. **Aggiornare descrizione** con nuovi fattori

3. **Quick links** alle nuove pagine

```python
# Aggiungere dopo le metriche esistenti:

# Conta rivalità
try:
    rivalries = supabase.table("rivalries").select("id", count="exact").execute()
    col5.metric("Rivalità", rivalries.count or 0)
except:
    pass

# Aggiornare sezione istruzioni con nuovi fattori
st.markdown("""
### Fattori di rischio analizzati (v2)

| Fattore | Peso | Descrizione |
|---------|------|-------------|
| Storico stagionale | 35% | Cartellini per 90 minuti |
| Storico arbitro | 30% | Frequenza ammonizioni con l'arbitro |
| Scontri diretti | 15% | Cartellini negli H2H |
| Propensione falli | 20% | Falli squadra + ruolo |

### Moltiplicatori contestuali

| Fattore | Range | Fonte |
|---------|-------|-------|
| Derby | ×1.10-1.26 | Intensità rivalità |
| Casa/Trasferta | ×0.94/×1.06 | Studio CIES |
| Lega | ×0.89-1.30 | Baseline per campionato |
| Arbitro outlier | ×0.85-1.15 | Delta vs media lega |
| Possesso | ×0.85-1.15 | Stile di gioco |
""")
```

**Commit:** `git commit -m "feat(dashboard): update homepage with new metrics"`

---

## FASE D: DOCUMENTAZIONE

---

## Task 11: Aggiornare Documentazione

**Files:**
- Modify `docs/SCORING.md`
- Modify `STATO_PROGETTO.md`
- Modify `CLAUDE.md` (se necessario)

**Step 1:** Aggiornare `docs/SCORING.md` con sezione "Moltiplicatori Contestuali v2"

**Step 2:** Aggiornare `STATO_PROGETTO.md` con:
- Nuova struttura dashboard (5 pagine)
- Cronologia sessione
- Nuovi comandi

**Step 3:** Commit finale
```bash
git add docs/SCORING.md STATO_PROGETTO.md
git commit -m "docs: update documentation with v2 features and dashboard"
```

---

## Riepilogo Finale

| Task | File Principali | Tipo | Dipendenze |
|------|-----------------|------|------------|
| 0 | Ricerca web | Prerequisito | - |
| 1 | `001_derby_rivalries.sql` | DB | Task 0 |
| 2 | `002_league_baselines.sql` | DB | - |
| 3 | `003_referee_delta.sql` | DB | - |
| 4 | `004_possession_factor.sql` | DB | - |
| 5 | `mcp_server.py` | Python | Task 1-4 |
| 6 | `2_referees.py` | Dashboard | Task 3 |
| 7 | `3_match_analysis.py` | Dashboard | Task 5 |
| 8 | `4_rivalries.py` | Dashboard | Task 1 |
| 9 | `5_team_stats.py` | Dashboard | Task 4 |
| 10 | `app.py` | Dashboard | - |
| 11 | `docs/*.md` | Docs | Tutti |

## Ordine di Esecuzione

```
FASE 0: Task 0 (ricerca derby)
    ↓
FASE A: Task 1, 2, 3, 4 (paralleli)
    ↓
FASE B: Task 5 (MCP integration)
    ↓
FASE C: Task 6, 7, 8, 9, 10 (dashboard - possono essere paralleli)
    ↓
FASE D: Task 11 (documentazione)
```

## Stima Effort

| Fase | Task | Effort |
|------|------|--------|
| 0 | Ricerca derby | 30 min |
| A | 4 migrazioni SQL | 20 min (parallele) |
| B | MCP integration | 30 min |
| C | 5 dashboard updates | 45 min |
| D | Documentazione | 15 min |
| **Totale** | | **~2h** |
