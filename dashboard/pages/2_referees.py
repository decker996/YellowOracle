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

        try:
            # Usa la vista referee_stats se esiste, altrimenti query diretta
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

                columns = ["Arbitro", "Nazionalità", "Partite", "Gialli Tot.", "Rossi Tot.", "Media Gialli/Partita"]
                df_display = df_display[columns]

                # Metriche
                col1, col2, col3 = st.columns(3)
                col1.metric("Arbitri totali", len(df_display))
                col2.metric("Media gialli/partita (tutti)", f"{df_display['Media Gialli/Partita'].mean():.2f}")
                col3.metric("Arbitro più severo", df_display.iloc[0]["Arbitro"] if len(df_display) > 0 else "N/A")

                st.markdown("---")

                st.dataframe(
                    df_display,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Media Gialli/Partita": st.column_config.NumberColumn(format="%.2f"),
                    }
                )

                # Grafico
                if len(df_display) > 0:
                    st.markdown("### Top 10 Arbitri più Severi")
                    top10 = df_display.head(10)
                    st.bar_chart(top10.set_index("Arbitro")["Media Gialli/Partita"])

            else:
                st.info("Nessun dato arbitri disponibile")

        except Exception as e:
            st.error(f"Errore: {e}")

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
