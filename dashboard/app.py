"""
YellowOracle - Dashboard v2
Sistema di analisi cartellini con moltiplicatori contestuali
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


def main():
    st.title("🟨 YellowOracle")
    st.subheader("Sistema di analisi rischio cartellini")

    st.markdown("---")

    # Statistiche rapide
    supabase = get_supabase_client()

    col1, col2, col3, col4, col5 = st.columns(5)

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

    # Conta rivalita
    try:
        rivalries = supabase.table("rivalries").select("id", count="exact").execute()
        col5.metric("Rivalita", rivalries.count or 0)
    except:
        col5.metric("Rivalita", "N/A")

    st.markdown("---")

    # Due colonne per info
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("""
### Come usare YellowOracle

Usa il menu a sinistra per navigare tra le pagine:

1. **Giocatori** - Statistiche cartellini per giocatore e stagione
2. **Arbitri** - Classifica severita con profilo outlier
3. **Analisi Partita** - Analisi pre-partita con tutti i fattori
4. **Derby & Rivalita** - Elenco rivalita configurate
5. **Statistiche Squadre** - Possesso e stile di gioco

### Competizioni supportate

| Codice | Competizione |
|--------|--------------|
| SA | Serie A |
| PL | Premier League |
| PD | La Liga |
| BL1 | Bundesliga |
| FL1 | Ligue 1 |
| CL | Champions League |
| BSA | Brasileirao |
        """)

    with col_right:
        st.markdown("""
### Fattori di rischio (v2)

| Fattore | Peso | Descrizione |
|---------|------|-------------|
| Stagionale | 35% | Cartellini per 90 minuti |
| Arbitro | 30% | Storico con arbitro designato |
| Scontri diretti | 15% | Cartellini negli H2H |
| Propensione falli | 20% | Falli squadra + ruolo |

### Moltiplicatori contestuali

| Fattore | Range | Fonte |
|---------|-------|-------|
| Derby | ×1.10-1.26 | Intensita rivalita |
| Casa/Trasferta | ×0.94/×1.06 | Studio CIES |
| Lega | ×0.89-1.30 | Baseline campionato |
| Arbitro outlier | ×0.85-1.15 | Delta vs media lega |
| Possesso | ×0.85-1.15 | Stile di gioco |
        """)

    st.markdown("---")

    # Quick actions
    st.subheader("🚀 Azioni rapide")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.page_link("pages/3_match_analysis.py", label="⚽ Analizza Partita", icon="🔍")

    with col2:
        st.page_link("pages/4_rivalries.py", label="🔥 Vedi Derby", icon="🏟️")

    with col3:
        st.page_link("pages/2_referees.py", label="👨‍⚖️ Classifica Arbitri", icon="📊")

    st.markdown("---")
    st.caption("YellowOracle v2.0 - Dati da football-data.org | Moltiplicatori research-based")


if __name__ == "__main__":
    main()
