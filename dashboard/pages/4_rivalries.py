"""
YellowOracle - Derby & Rivalita
Mostra tutte le rivalita configurate nel sistema
"""

import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

st.set_page_config(page_title="Derby & Rivalita - YellowOracle", page_icon="🔥", layout="wide")

@st.cache_resource
def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)


def main():
    st.title("🔥 Derby & Rivalita")
    st.markdown("Elenco delle rivalita storiche configurate nel sistema")

    supabase = get_supabase_client()

    # Sidebar filtri
    st.sidebar.header("Filtri")

    rivalry_types = ["Tutti", "DERBY", "HISTORIC", "REGIONAL"]
    selected_type = st.sidebar.selectbox("Tipo rivalita", rivalry_types)

    intensities = ["Tutte", "3 - Massima", "2 - Sentita", "1 - Minore"]
    selected_intensity = st.sidebar.selectbox("Intensita", intensities)

    try:
        # Query rivalita con join squadre
        result = supabase.table("rivalries").select(
            "id, rivalry_name, rivalry_type, intensity, "
            "team1:team1_id(name), team2:team2_id(name)"
        ).order("intensity", desc=True).execute()

        if not result.data:
            st.warning("Nessuna rivalita configurata. Esegui la migrazione 001_derby_rivalries.sql")
            return

        # Trasforma dati
        rows = []
        for r in result.data:
            rows.append({
                "Squadra 1": r.get("team1", {}).get("name", "N/A") if r.get("team1") else "N/A",
                "Squadra 2": r.get("team2", {}).get("name", "N/A") if r.get("team2") else "N/A",
                "Nome Derby": r.get("rivalry_name") or "-",
                "Tipo": r.get("rivalry_type"),
                "Intensita": r.get("intensity"),
                "Intensita Display": "⭐" * (r.get("intensity") or 1)
            })

        df = pd.DataFrame(rows)

        # Applica filtri
        if selected_type != "Tutti":
            df = df[df["Tipo"] == selected_type]

        if selected_intensity != "Tutte":
            intensity_val = int(selected_intensity[0])
            df = df[df["Intensita"] == intensity_val]

        # Metriche
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Totale Rivalita", len(df))
        col2.metric("Derby (stessa citta)", len(df[df["Tipo"] == "DERBY"]))
        col3.metric("Storiche", len(df[df["Tipo"] == "HISTORIC"]))
        col4.metric("Regionali", len(df[df["Tipo"] == "REGIONAL"]))

        st.markdown("---")

        # Tabella
        st.dataframe(
            df[["Squadra 1", "Squadra 2", "Nome Derby", "Tipo", "Intensita Display"]].rename(
                columns={"Intensita Display": "Intensita"}
            ),
            use_container_width=True,
            hide_index=True
        )

        # Top Derby per intensita
        st.markdown("---")
        st.subheader("🏆 Derby Storici (Intensita Massima)")

        top_derbies = df[df["Intensita"] == 3]
        if not top_derbies.empty:
            for _, row in top_derbies.iterrows():
                name = row["Nome Derby"] if row["Nome Derby"] != "-" else f"{row['Squadra 1']} vs {row['Squadra 2']}"
                st.markdown(f"- **{name}** ({row['Squadra 1']} vs {row['Squadra 2']}) - {row['Tipo']}")
        else:
            st.info("Nessun derby con intensita massima")

        # Info
        st.markdown("---")
        with st.expander("📖 Legenda"):
            st.markdown("""
**Intensita:**
- ⭐ = Rivalita minore (+10% rischio cartellini)
- ⭐⭐ = Rivalita sentita (+18% rischio cartellini)
- ⭐⭐⭐ = Derby storico (+26% rischio cartellini)

**Tipi:**
- **DERBY** = Stessa citta (es. Inter-Milan, Roma-Lazio)
- **HISTORIC** = Rivalita storica tra club (es. Juve-Inter, Real-Barca)
- **REGIONAL** = Rivalita regionale (es. Basque Derby, Derby du Rhone)
            """)

    except Exception as e:
        st.error(f"Errore: {e}")
        st.info("Assicurati di aver eseguito la migrazione 001_derby_rivalries.sql")


if __name__ == "__main__":
    main()
