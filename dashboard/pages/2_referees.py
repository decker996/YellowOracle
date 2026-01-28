"""
YellowOracle - Pagina Statistiche Arbitri
"""

import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

st.set_page_config(page_title="Arbitri - YellowOracle", page_icon="🎯", layout="wide")

@st.cache_resource
def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)

def main():
    st.title("🎯 Statistiche Arbitri")
    st.markdown("Severità arbitri e giocatori più ammoniti")

    supabase = get_supabase_client()

    # Tab per diverse viste
    tab1, tab2 = st.tabs(["Classifica Arbitri", "Storico Arbitro-Giocatore"])

    with tab1:
        st.subheader("Classifica Arbitri per Severità")

        # Filtro competizione
        competitions = ["Tutte", "SA", "PL", "PD", "BL1", "FL1", "CL", "BSA"]
        selected_comp = st.selectbox("Competizione", competitions, key="ref_comp_filter")

        try:
            # Prova prima la vista con profilo outlier
            if selected_comp != "Tutte":
                profile_result = supabase.table("referee_league_comparison").select(
                    "referee_name, competition_code, matches_in_league, ref_avg_yellows, "
                    "league_avg_yellows, ref_league_delta, referee_profile"
                ).eq("competition_code", selected_comp).order("ref_league_delta", desc=True).execute()
            else:
                profile_result = supabase.table("referee_league_comparison").select(
                    "referee_name, competition_code, matches_in_league, ref_avg_yellows, "
                    "league_avg_yellows, ref_league_delta, referee_profile"
                ).order("ref_league_delta", desc=True).execute()

            if profile_result.data:
                df = pd.DataFrame(profile_result.data)

                # Formatta profilo con emoji
                def format_profile(profile):
                    colors = {
                        "STRICT_OUTLIER": "🔴 SEVERO",
                        "ABOVE_AVERAGE": "🟠 Sopra media",
                        "AVERAGE": "⚪ Nella media",
                        "BELOW_AVERAGE": "🟢 Sotto media",
                        "LENIENT_OUTLIER": "🟢 PERMISSIVO"
                    }
                    return colors.get(profile, "⚪ N/A")

                df["Profilo"] = df["referee_profile"].apply(format_profile)

                df_display = df.rename(columns={
                    "referee_name": "Arbitro",
                    "competition_code": "Lega",
                    "matches_in_league": "Partite",
                    "ref_avg_yellows": "Media Arbitro",
                    "league_avg_yellows": "Media Lega",
                    "ref_league_delta": "Delta"
                })

                # Metriche
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Arbitri", len(df_display))
                strict_count = len(df[df["referee_profile"] == "STRICT_OUTLIER"])
                lenient_count = len(df[df["referee_profile"] == "LENIENT_OUTLIER"])
                col2.metric("Severi (outlier)", strict_count)
                col3.metric("Permissivi (outlier)", lenient_count)
                if len(df_display) > 0:
                    col4.metric("Più severo", df_display.iloc[0]["Arbitro"])

                st.markdown("---")

                st.dataframe(
                    df_display[["Arbitro", "Lega", "Partite", "Media Arbitro", "Media Lega", "Delta", "Profilo"]],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Media Arbitro": st.column_config.NumberColumn(format="%.2f"),
                        "Media Lega": st.column_config.NumberColumn(format="%.2f"),
                        "Delta": st.column_config.NumberColumn(format="%+.2f"),
                    }
                )

                # Legenda
                st.caption("""
                **Profilo:** Confronto con la media della lega
                - 🔴 SEVERO: +1.0 gialli sopra media lega
                - 🟠 Sopra media: +0.5 a +1.0
                - ⚪ Nella media: -0.5 a +0.5
                - 🟢 Sotto media/PERMISSIVO: -0.5 o meno
                """)

            else:
                # Fallback alla query base
                result = supabase.table("referees").select(
                    "id, name, nationality, total_matches, total_yellows, total_reds, avg_yellows_per_match"
                ).gt("total_matches", 0).order("avg_yellows_per_match", desc=True).execute()

                if result.data:
                    df = pd.DataFrame(result.data)
                    df_display = df.rename(columns={
                        "name": "Arbitro",
                        "nationality": "Nazionalità",
                        "total_matches": "Partite",
                        "total_yellows": "Gialli Tot.",
                        "total_reds": "Rossi Tot.",
                        "avg_yellows_per_match": "Media Gialli/Partita"
                    })

                    st.dataframe(
                        df_display[["Arbitro", "Nazionalità", "Partite", "Gialli Tot.", "Rossi Tot.", "Media Gialli/Partita"]],
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("Nessun dato arbitri disponibile")

        except Exception as e:
            st.error(f"Errore: {e}")
            st.info("Assicurati di aver eseguito la migrazione 003_referee_delta.sql")

    with tab2:
        st.subheader("Storico Arbitro-Giocatore")
        st.markdown("Seleziona un arbitro e due squadre per vedere lo storico ammonizioni")

        col1, col2, col3 = st.columns(3)

        # Carica arbitri
        referees_data = supabase.table("referees").select("id, name").order("name").execute()
        referees_list = [r["name"] for r in referees_data.data]

        # Carica squadre
        teams_data = supabase.table("teams").select("id, name").order("name").execute()
        teams_list = [t["name"] for t in teams_data.data]

        with col1:
            selected_referee = st.selectbox("Arbitro", referees_list if referees_list else ["Nessun arbitro"])

        with col2:
            selected_team1 = st.selectbox("Squadra 1", teams_list if teams_list else ["Nessuna squadra"])

        with col3:
            selected_team2 = st.selectbox("Squadra 2", teams_list if teams_list else ["Nessuna squadra"], index=1 if len(teams_list) > 1 else 0)

        if st.button("Cerca storico", type="primary"):
            if selected_referee and selected_team1 and selected_team2:
                try:
                    # Chiama la funzione RPC
                    result = supabase.rpc(
                        "get_referee_player_cards",
                        {
                            "p_referee_name": selected_referee,
                            "p_team1_name": selected_team1,
                            "p_team2_name": selected_team2
                        }
                    ).execute()

                    if result.data:
                        df = pd.DataFrame(result.data)

                        df_display = df.rename(columns={
                            "referee_name": "Arbitro",
                            "player_name": "Giocatore",
                            "team_name": "Squadra",
                            "times_booked": "Volte Ammonito",
                            "matches_with_referee": "Partite con Arbitro",
                            "booking_percentage": "% Ammonizione",
                            "last_booking": "Ultimo Cartellino"
                        })

                        st.success(f"Trovati {len(df_display)} giocatori con cartellini da {selected_referee}")

                        st.dataframe(
                            df_display[["Giocatore", "Squadra", "Volte Ammonito", "Partite con Arbitro", "% Ammonizione", "Ultimo Cartellino"]],
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.info("Nessuno storico trovato per questa combinazione")

                except Exception as e:
                    st.error(f"Errore nella ricerca: {e}")
                    st.info("Assicurati di aver creato le funzioni SQL (analysis_views.sql)")


if __name__ == "__main__":
    main()
