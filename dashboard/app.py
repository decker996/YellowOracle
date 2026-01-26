"""
YellowOracle - Dashboard
Esegui con: streamlit run dashboard/app.py
"""

import streamlit as st
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Carica variabili d'ambiente
load_dotenv()

# Configurazione pagina
st.set_page_config(
    page_title="YellowOracle",
    page_icon="🟨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Connessione Supabase (cached)
@st.cache_resource
def get_supabase_client() -> Client:
    """Crea connessione a Supabase."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        st.error("Configura SUPABASE_URL e SUPABASE_KEY nel file .env")
        st.stop()
    return create_client(url, key)

# Homepage
def main():
    st.title("🟨 YellowOracle")
    st.subheader("Sistema di analisi cartellini per La Liga")

    st.markdown("---")

    # Statistiche rapide
    supabase = get_supabase_client()

    col1, col2, col3, col4 = st.columns(4)

    # Conta squadre
    try:
        teams = supabase.table("teams").select("id", count="exact").execute()
        col1.metric("Squadre", teams.count or 0)
    except:
        col1.metric("Squadre", "N/A")

    # Conta giocatori
    try:
        players = supabase.table("players").select("id", count="exact").execute()
        col2.metric("Giocatori", players.count or 0)
    except:
        col2.metric("Giocatori", "N/A")

    # Conta partite
    try:
        matches = supabase.table("matches").select("id", count="exact").execute()
        col3.metric("Partite", matches.count or 0)
    except:
        col3.metric("Partite", "N/A")

    # Conta arbitri
    try:
        referees = supabase.table("referees").select("id", count="exact").execute()
        col4.metric("Arbitri", referees.count or 0)
    except:
        col4.metric("Arbitri", "N/A")

    st.markdown("---")

    # Istruzioni
    st.markdown("""
    ### Come usare YellowOracle

    Usa il menu a sinistra per navigare tra le pagine:

    1. **Giocatori** - Statistiche cartellini per giocatore e stagione
    2. **Arbitri** - Statistiche arbitri e giocatori più ammoniti
    3. **Analisi Partita** - Analisi pre-partita con i 3 fattori di rischio

    ### Fattori di rischio analizzati

    | Fattore | Descrizione |
    |---------|-------------|
    | Storico stagionale | Cartellini per 90 minuti nella stagione |
    | Storico arbitro | Quante volte l'arbitro ha ammonito il giocatore |
    | Scontri diretti | Cartellini storici negli head-to-head |

    ### Stagioni disponibili

    - 2020-2021, 2021-2022, 2022-2023
    - 2023-2024, 2024-2025, 2025-2026 (corrente)
    """)

    st.markdown("---")
    st.caption("YellowOracle v1.0 - Dati da football-data.org")


if __name__ == "__main__":
    main()
