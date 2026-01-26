"""
YellowOracle - Pagina Statistiche Giocatori
"""

import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

st.set_page_config(page_title="Giocatori - YellowOracle", page_icon="👥", layout="wide")

@st.cache_resource
def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)

def main():
    st.title("👥 Statistiche Giocatori")
    st.markdown("Cartellini per giocatore, filtrabili per squadra e stagione")

    supabase = get_supabase_client()

    # Sidebar filtri
    st.sidebar.header("Filtri")

    # Carica squadre per filtro
    teams_data = supabase.table("teams").select("id, name").order("name").execute()
    teams_list = ["Tutte"] + [t["name"] for t in teams_data.data]
    selected_team = st.sidebar.selectbox("Squadra", teams_list)

    # Carica stagioni disponibili
    seasons = ["Tutte", "2025-2026", "2024-2025", "2023-2024", "2022-2023", "2021-2022", "2020-2021"]
    selected_season = st.sidebar.selectbox("Stagione", seasons)

    # Filtro ruolo
    positions = ["Tutti", "Goalkeeper", "Defence", "Midfield", "Offence"]
    selected_position = st.sidebar.selectbox("Ruolo", positions)

    # Query dati dalla vista
    try:
        query = supabase.table("player_season_cards").select("*")

        if selected_team != "Tutte":
            query = query.eq("team_name", selected_team)

        if selected_season != "Tutte":
            query = query.eq("season", selected_season)

        if selected_position != "Tutti":
            query = query.eq("position", selected_position)

        result = query.order("yellow_cards", desc=True).limit(200).execute()

        if result.data:
            df = pd.DataFrame(result.data)

            # Rinomina colonne per display
            df_display = df.rename(columns={
                "player_name": "Giocatore",
                "team_name": "Squadra",
                "position": "Ruolo",
                "season": "Stagione",
                "matches_played": "Partite",
                "yellow_cards": "Gialli",
                "red_cards": "Rossi",
                "minutes_played": "Minuti",
                "yellows_per_90": "Gialli/90"
            })

            # Seleziona colonne da mostrare
            columns = ["Giocatore", "Squadra", "Ruolo", "Stagione", "Partite", "Gialli", "Rossi", "Gialli/90"]
            df_display = df_display[columns]

            # Metriche riassuntive
            col1, col2, col3 = st.columns(3)
            col1.metric("Giocatori trovati", len(df_display))
            col2.metric("Media gialli/90", f"{df_display['Gialli/90'].mean():.2f}" if not df_display['Gialli/90'].isna().all() else "N/A")
            col3.metric("Max gialli stagione", df_display["Gialli"].max())

            st.markdown("---")

            # Tabella principale
            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Gialli/90": st.column_config.NumberColumn(format="%.2f"),
                    "Gialli": st.column_config.NumberColumn(format="%d"),
                    "Rossi": st.column_config.NumberColumn(format="%d"),
                }
            )

            # Grafico top 10
            if len(df_display) > 0:
                st.markdown("### Top 10 - Cartellini Gialli")
                top10 = df_display.head(10)
                st.bar_chart(top10.set_index("Giocatore")["Gialli"])

        else:
            st.info("Nessun dato trovato con i filtri selezionati")

    except Exception as e:
        st.error(f"Errore nel caricamento dati: {e}")
        st.info("Assicurati di aver eseguito lo script di sincronizzazione e creato le viste SQL")


if __name__ == "__main__":
    main()
