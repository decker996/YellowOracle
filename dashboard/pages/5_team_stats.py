"""
YellowOracle - Statistiche Squadre
Possesso palla, falli e stile di gioco per squadra
"""

import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

st.set_page_config(page_title="Statistiche Squadre - YellowOracle", page_icon="📊", layout="wide")

@st.cache_resource
def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)


def main():
    st.title("📊 Statistiche Squadre")
    st.markdown("Possesso palla, falli e stile di gioco per squadra")

    supabase = get_supabase_client()

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
            st.info("Assicurati di aver eseguito la migrazione 004_possession_factor.sql")
            return

        df = pd.DataFrame(result.data)

        # Calcola risk factor
        df["risk_factor"] = df["avg_possession"].apply(
            lambda x: round(1 + (50 - float(x)) * 0.01, 2) if x else 1.0
        )
        df["risk_factor"] = df["risk_factor"].clip(0.85, 1.15)

        # Filtro stile
        if selected_style != "Tutti":
            df = df[df["play_style"] == selected_style]

        if df.empty:
            st.info(f"Nessuna squadra con stile '{selected_style}'")
            return

        # Metriche
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Squadre", len(df))
        col2.metric("Possesso medio", f"{df['avg_possession'].mean():.1f}%")
        col3.metric("Falli medi", f"{df['avg_fouls_committed'].mean():.1f}")
        if len(df) > 0:
            top_poss = df.iloc[0]
            col4.metric("Piu possesso", top_poss["team_name"][:15], f"{top_poss['avg_possession']}%")

        st.markdown("---")

        # Tabella principale
        df_display = df.copy()
        df_display["Squadra"] = df_display["team_name"]
        df_display["Possesso %"] = df_display["avg_possession"]
        df_display["Falli/Partita"] = df_display["avg_fouls_committed"]
        df_display["Stile"] = df_display["play_style"]
        df_display["Partite"] = df_display["matches_played"]

        # Formatta risk factor con freccia
        def format_risk(x):
            if x < 1:
                return f"×{x:.2f} ↓"
            elif x > 1:
                return f"×{x:.2f} ↑"
            else:
                return f"×{x:.2f}"

        df_display["Risk Factor"] = df_display["risk_factor"].apply(format_risk)

        # Emoji per stile
        style_emoji = {
            "POSSESSION_HEAVY": "🎯",
            "BALANCED": "⚖️",
            "COUNTER_ATTACK": "⚡",
            "DEFENSIVE": "🛡️"
        }
        df_display["Stile"] = df_display["play_style"].apply(
            lambda x: f"{style_emoji.get(x, '')} {x}"
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

        # Prepara dati per scatter
        chart_df = df[["team_name", "avg_possession", "avg_fouls_committed"]].copy()
        chart_df.columns = ["Squadra", "Possesso", "Falli"]

        # Usa plotly per scatter migliore
        try:
            import plotly.express as px

            fig = px.scatter(
                chart_df,
                x="Possesso",
                y="Falli",
                hover_name="Squadra",
                title="Possesso vs Falli (correlazione inversa attesa)",
                labels={"Possesso": "Possesso medio %", "Falli": "Falli/partita"}
            )
            fig.update_traces(marker=dict(size=10))
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            # Fallback a scatter nativo streamlit
            st.scatter_chart(chart_df.set_index("Squadra"))

        st.caption("Tendenza: squadre con meno possesso commettono piu falli → piu rischio cartellini")

        # Legenda stili
        st.markdown("---")
        with st.expander("📖 Legenda Stili"):
            st.markdown("""
| Stile | Possesso | Descrizione | Risk Factor |
|-------|----------|-------------|-------------|
| 🎯 POSSESSION_HEAVY | 55%+ | Controllo totale, pochi falli | ×0.85-0.95 (↓ rischio) |
| ⚖️ BALANCED | 50-55% | Equilibrato | ×0.95-1.05 |
| ⚡ COUNTER_ATTACK | 45-50% | Ripartenze, piu pressing | ×1.00-1.05 (↑ rischio) |
| 🛡️ DEFENSIVE | <45% | Molto difensivo, molti falli | ×1.05-1.15 (↑ rischio) |

**Risk Factor:** Moltiplicatore applicato al punteggio di rischio dei giocatori.
- <1 = squadra con piu possesso, meno falli, meno rischio cartellini
- >1 = squadra con meno possesso, piu falli, piu rischio cartellini
            """)

    except Exception as e:
        st.error(f"Errore: {e}")
        st.info("Assicurati di aver eseguito la migrazione 004_possession_factor.sql")


if __name__ == "__main__":
    main()
