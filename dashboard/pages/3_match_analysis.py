"""
YellowOracle - Pagina Analisi Partita
"""

import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

st.set_page_config(page_title="Analisi Partita - YellowOracle", page_icon="⚽", layout="wide")

@st.cache_resource
def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)

def get_team_players_stats(supabase, team_name, season="2025-2026"):
    """Recupera statistiche giocatori di una squadra."""
    try:
        result = supabase.table("player_season_cards").select("*").eq(
            "team_name", team_name
        ).eq("season", season).order("yellow_cards", desc=True).execute()
        return result.data
    except:
        return []

def get_referee_history(supabase, referee_name, team1_name, team2_name):
    """Recupera storico arbitro-giocatore."""
    try:
        result = supabase.rpc(
            "get_referee_player_cards",
            {
                "p_referee_name": referee_name,
                "p_team1_name": team1_name,
                "p_team2_name": team2_name
            }
        ).execute()
        return result.data
    except:
        return []

def get_h2h_history(supabase, player_name, team1_name, team2_name):
    """Recupera storico scontri diretti per giocatore."""
    try:
        result = supabase.rpc(
            "get_head_to_head_cards",
            {
                "p_player_name": player_name,
                "p_team1_name": team1_name,
                "p_team2_name": team2_name
            }
        ).execute()
        return result.data
    except:
        return []

def main():
    st.title("⚽ Analisi Partita")
    st.markdown("Analisi pre-partita con i 3 fattori di rischio cartellino")

    supabase = get_supabase_client()

    # Carica dati per dropdown
    teams_data = supabase.table("teams").select("id, name").order("name").execute()
    teams_list = [t["name"] for t in teams_data.data]

    referees_data = supabase.table("referees").select("id, name").order("name").execute()
    referees_list = ["Non specificato"] + [r["name"] for r in referees_data.data]

    # Input partita
    st.subheader("Seleziona la partita")

    col1, col2, col3 = st.columns(3)

    with col1:
        home_team = st.selectbox("Squadra Casa", teams_list if teams_list else ["Nessuna squadra"])

    with col2:
        away_team = st.selectbox("Squadra Trasferta", teams_list if teams_list else ["Nessuna squadra"],
                                  index=1 if len(teams_list) > 1 else 0)

    with col3:
        referee = st.selectbox("Arbitro", referees_list)

    season = st.selectbox("Stagione di riferimento", ["2025-2026", "2024-2025", "2023-2024"])

    if st.button("Analizza Partita", type="primary"):
        if home_team == away_team:
            st.error("Seleziona due squadre diverse")
            return

        st.markdown("---")
        st.subheader(f"📊 Analisi: {home_team} vs {away_team}")

        if referee != "Non specificato":
            st.info(f"Arbitro: {referee}")
        else:
            st.warning("Arbitro non specificato - analisi basata solo su storico stagionale e scontri diretti")

        # Tab per le due squadre
        tab1, tab2, tab3 = st.tabs([f"🏠 {home_team}", f"✈️ {away_team}", "🔥 Top Rischio"])

        all_players_risk = []

        for tab, team_name, is_home in [(tab1, home_team, True), (tab2, away_team, False)]:
            with tab:
                st.markdown(f"### Giocatori {team_name}")

                # 1. Statistiche stagionali
                players_stats = get_team_players_stats(supabase, team_name, season)

                if not players_stats:
                    st.info(f"Nessuna statistica disponibile per {team_name}")
                    continue

                # 2. Storico con arbitro (se specificato)
                referee_history = {}
                if referee != "Non specificato":
                    ref_data = get_referee_history(supabase, referee, home_team, away_team)
                    for r in ref_data:
                        referee_history[r["player_name"]] = r

                # 3. Costruisci tabella con indici di rischio
                rows = []
                for p in players_stats:
                    player_name = p["player_name"]

                    # Storico con arbitro
                    ref_stats = referee_history.get(player_name, {})
                    times_booked_by_ref = ref_stats.get("times_booked", 0)
                    matches_with_ref = ref_stats.get("matches_with_referee", 0)

                    # Scontri diretti (query per ogni giocatore - ottimizzabile)
                    h2h_data = get_h2h_history(supabase, player_name, home_team, away_team)
                    h2h_yellows = h2h_data[0]["total_yellows"] if h2h_data else 0
                    h2h_matches = h2h_data[0]["total_h2h_matches"] if h2h_data else 0

                    # Calcola indice di rischio complessivo (semplificato)
                    season_risk = float(p.get("yellows_per_90") or 0) * 100
                    referee_risk = (times_booked_by_ref / matches_with_ref * 100) if matches_with_ref > 0 else 0
                    h2h_risk = (h2h_yellows / h2h_matches * 100) if h2h_matches > 0 else 0

                    # Peso: 40% stagione, 30% arbitro, 30% h2h
                    if referee != "Non specificato":
                        total_risk = season_risk * 0.4 + referee_risk * 0.3 + h2h_risk * 0.3
                    else:
                        total_risk = season_risk * 0.6 + h2h_risk * 0.4

                    row = {
                        "Giocatore": player_name,
                        "Ruolo": p.get("position", ""),
                        "Gialli Stagione": p.get("yellow_cards", 0),
                        "Gialli/90": p.get("yellows_per_90", 0),
                        "Amm. da Arbitro": f"{times_booked_by_ref}/{matches_with_ref}" if matches_with_ref > 0 else "-",
                        "Gialli H2H": f"{h2h_yellows}/{h2h_matches}" if h2h_matches > 0 else "-",
                        "Indice Rischio": round(total_risk, 1),
                        "team": team_name
                    }
                    rows.append(row)
                    all_players_risk.append(row)

                if rows:
                    df = pd.DataFrame(rows)
                    df = df.sort_values("Indice Rischio", ascending=False)

                    st.dataframe(
                        df[["Giocatore", "Ruolo", "Gialli Stagione", "Gialli/90", "Amm. da Arbitro", "Gialli H2H", "Indice Rischio"]],
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Indice Rischio": st.column_config.ProgressColumn(
                                "Indice Rischio",
                                min_value=0,
                                max_value=100,
                                format="%.1f"
                            )
                        }
                    )

        # Tab Top Rischio
        with tab3:
            st.markdown("### 🔥 Top 10 Giocatori a Rischio Cartellino")

            if all_players_risk:
                df_all = pd.DataFrame(all_players_risk)
                df_all = df_all.sort_values("Indice Rischio", ascending=False).head(10)

                st.dataframe(
                    df_all[["Giocatore", "team", "Ruolo", "Gialli/90", "Amm. da Arbitro", "Gialli H2H", "Indice Rischio"]].rename(
                        columns={"team": "Squadra"}
                    ),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Indice Rischio": st.column_config.ProgressColumn(
                            "Indice Rischio",
                            min_value=0,
                            max_value=100,
                            format="%.1f"
                        )
                    }
                )

                # Evidenzia top 3
                st.markdown("---")
                st.markdown("### Raccomandazione")

                top3 = df_all.head(3)
                for i, (_, row) in enumerate(top3.iterrows(), 1):
                    risk_emoji = "🔴" if row["Indice Rischio"] > 50 else "🟠" if row["Indice Rischio"] > 30 else "🟡"
                    st.markdown(f"""
                    **{i}. {row['Giocatore']}** ({row['team']}) {risk_emoji}
                    - Rischio: **{row['Indice Rischio']:.1f}%**
                    - Stagione: {row['Gialli/90']} gialli/90min
                    - Arbitro: {row['Amm. da Arbitro']}
                    - Scontri diretti: {row['Gialli H2H']}
                    """)


if __name__ == "__main__":
    main()
