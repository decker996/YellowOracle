"""
YellowOracle - Analisi Partita (v2 - MCP Integration)
Usa analyze_match_risk per analisi completa con tutti i fattori
"""

import streamlit as st
import pandas as pd
import json
import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

# Aggiungi path per import mcp_server
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from mcp_server import analyze_match_risk

load_dotenv()

st.set_page_config(page_title="Analisi Partita - YellowOracle", page_icon="⚽", layout="wide")

@st.cache_resource
def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)


def render_match_info(result):
    """Render card info partita con derby, arbitro, possesso."""
    col1, col2 = st.columns(2)

    with col1:
        # Derby info
        derby = result.get("derby")
        if derby and derby.get("is_derby"):
            intensity = derby.get("intensity", 1)
            stars = "⭐" * intensity
            st.success(f"🔥 **{derby.get('name') or 'Derby'}** {stars}")
            st.caption(f"Tipo: {derby.get('type')} | Moltiplicatore: ×{result.get('multipliers', {}).get('derby', 1.0)}")
        else:
            st.info("Partita regolare (no derby)")

        # Possession info
        poss = result.get("possession")
        if poss:
            home_style = poss.get("home_style", "N/A")
            away_style = poss.get("away_style", "N/A")
            st.markdown(f"""
            **Possesso previsto:**
            - Casa: {poss.get('home_avg', 50):.0f}% ({home_style}) → ×{poss.get('home_factor', 1.0)}
            - Trasferta: {poss.get('away_avg', 50):.0f}% ({away_style}) → ×{poss.get('away_factor', 1.0)}
            """)

    with col2:
        # Referee info
        ref_stats = result.get("referee_stats")
        ref_profile = result.get("referee_profile")

        if ref_stats:
            st.markdown(f"**Arbitro:** {ref_stats.get('name', 'N/A')}")
            st.metric(
                "Media gialli/partita",
                f"{ref_stats.get('avg_yellows_per_match', 0):.1f}",
                f"{ref_stats.get('total_matches', 0)} partite"
            )

            if ref_profile:
                profile_type = ref_profile.get("classification", "")
                delta = ref_profile.get("delta", 0)
                badges = {
                    "STRICT_OUTLIER": "🔴 SEVERO",
                    "ABOVE_AVERAGE": "🟠 Sopra media",
                    "AVERAGE": "⚪ Nella media",
                    "BELOW_AVERAGE": "🟢 Sotto media",
                    "LENIENT_OUTLIER": "🟢 PERMISSIVO"
                }
                st.markdown(f"**Profilo:** {badges.get(profile_type, profile_type)} (delta: {delta:+.2f})")
        else:
            st.warning("Arbitro non designato")


def render_multipliers(result):
    """Render multipliers come pills/badges."""
    mults = result.get("multipliers", {})
    derby = result.get("derby")

    pills = []

    if derby and derby.get("is_derby"):
        pills.append(f"🔥 Derby ×{mults.get('derby', 1.0)}")

    pills.append(f"🏠 Casa ×{mults.get('home_away', {}).get('home', 0.94)}")
    pills.append(f"✈️ Trasf. ×{mults.get('home_away', {}).get('away', 1.06)}")

    ref_adj = mults.get("referee_adjustment", 1.0)
    if ref_adj != 1.0:
        pills.append(f"👨‍⚖️ Arbitro ×{ref_adj}")

    poss = mults.get("possession", {})
    if poss.get("home", 1.0) != 1.0 or poss.get("away", 1.0) != 1.0:
        pills.append(f"⚽ Poss. H×{poss.get('home', 1.0)} A×{poss.get('away', 1.0)}")

    st.markdown("**Moltiplicatori attivi:** " + " ".join([f"`{p}`" for p in pills]))


def render_top5(result):
    """Render tabella top 5 con progress bar."""
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
            "Squadra": p.get("team", "")[:20],
            "Ruolo": (p.get("position", "") or "")[:3].upper(),
            "Score": p.get("combined_score", 0),
            "Base": p.get("base_score", 0),
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
            ),
            "Base": st.column_config.NumberColumn(format="%.1f"),
            "Stagione": st.column_config.NumberColumn(format="%.1f"),
            "H2H": st.column_config.NumberColumn(format="%.1f"),
            "Falli": st.column_config.NumberColumn(format="%.1f"),
        }
    )

    # Expander con breakdown dettagliato
    with st.expander("📊 Breakdown dettagliato"):
        for p in top5:
            bd = p.get("breakdown", {})
            mults = bd.get("multipliers", {})
            seasonal = bd.get("seasonal", {})
            st.markdown(f"""
**{p.get('name')}** ({p.get('team')}) - Score: **{p.get('combined_score')}** (base: {p.get('base_score')})
- Stagionale: {seasonal.get('per_90', 0):.2f} gialli/90 ({seasonal.get('yellows', 0)} in {seasonal.get('matches', 0)} partite) → {seasonal.get('score', 0):.1f}
- Arbitro: {bd.get('referee', {}).get('detail') or 'N/A'} → {bd.get('referee', {}).get('score', 0) if bd.get('referee') else 'N/A'}
- H2H: {bd.get('h2h', {}).get('detail') or 'N/A'} → {bd.get('h2h', {}).get('score', 0):.1f}
- Falli: team_pct={bd.get('fouls', {}).get('team_foul_to_card_pct', 0):.1f}%, pos_mult={bd.get('fouls', {}).get('position_multiplier', 1.0)} → {bd.get('fouls', {}).get('score', 0):.1f}
- Multipliers: derby={mults.get('derby', 1.0)}, home_away={mults.get('home_away', 1.0)}, ref={mults.get('referee_adj', 1.0)}, poss={mults.get('possession', 1.0)}
---
            """)


def render_team_tabs(result, home_team, away_team):
    """Render tabs per squadra."""
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


def main():
    st.title("⚽ Analisi Partita")
    st.markdown("Analisi pre-partita con tutti i fattori di rischio cartellino")

    supabase = get_supabase_client()

    # --- INPUT SECTION ---
    teams_data = supabase.table("teams").select("name").order("name").execute()
    teams_list = [t["name"] for t in teams_data.data]

    referees_data = supabase.table("referees").select("name").order("name").execute()
    referees_list = ["Non designato"] + [r["name"] for r in referees_data.data]

    col1, col2, col3 = st.columns(3)
    with col1:
        home_team = st.selectbox("Squadra Casa", teams_list)
    with col2:
        away_team = st.selectbox("Squadra Trasferta", teams_list, index=1 if len(teams_list) > 1 else 0)
    with col3:
        referee = st.selectbox("Arbitro", referees_list)

    if st.button("🔍 Analizza Partita", type="primary", use_container_width=True):
        if home_team == away_team:
            st.error("Seleziona due squadre diverse")
            return

        # Chiama analyze_match_risk
        ref_param = referee if referee != "Non designato" else None
        with st.spinner("Analisi in corso..."):
            result_json = analyze_match_risk(home_team, away_team, ref_param)

        try:
            result = json.loads(result_json)
        except Exception as e:
            st.error(f"Errore nel parsing: {e}")
            st.code(result_json)
            return

        st.markdown("---")

        # --- HEADER ---
        st.header(f"📊 {result.get('match', '')}")

        # --- INFO PARTITA CARD ---
        render_match_info(result)

        st.markdown("---")

        # --- MULTIPLIERS PILLS ---
        render_multipliers(result)

        st.markdown("---")

        # --- TOP 5 TABLE ---
        st.subheader("🎯 Top 5 Rischio Cartellino")
        render_top5(result)

        st.markdown("---")

        # --- TEAM TABS ---
        st.subheader("📋 Dettaglio per Squadra")
        render_team_tabs(result, home_team, away_team)

        # --- LEGENDA ---
        st.markdown("---")
        with st.expander("📖 Glossario"):
            st.markdown("""
| Campo | Descrizione |
|-------|-------------|
| **Score** | Punteggio finale 0-100 con tutti i moltiplicatori applicati |
| **Base** | Punteggio prima dei moltiplicatori contestuali |
| **Stagione** | Contributo da gialli/90 minuti in stagione (peso 35%) |
| **Arbitro** | Contributo da storico con arbitro designato (peso 30%) |
| **H2H** | Contributo da cartellini negli scontri diretti (peso 15%) |
| **Falli** | Contributo da propensione falli squadra + ruolo (peso 20%) |

**Moltiplicatori contestuali:**
- 🔥 Derby: ×1.10-1.26 basato su intensità rivalità
- 🏠 Casa: ×0.94 (giocatori casa meno ammoniti)
- ✈️ Trasferta: ×1.06 (giocatori trasferta più ammoniti)
- 👨‍⚖️ Arbitro: ×0.85-1.15 basato su severità vs media lega
- ⚽ Possesso: ×0.85-1.15 basato su stile di gioco
            """)


if __name__ == "__main__":
    main()
