import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import altair as alt
from datetime import datetime

# --- CONFIGURATION GÉNÉRALE ---
st.set_page_config(
    page_title="🌿 Dashboard Bien-être au travail",
    layout="wide",
    page_icon="🌸",
)

# --- EN-TÊTE ---
st.markdown(
    """
    <style>
        body {
            background-color: #f9fafb;
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        h1, h2, h3, h4 {
            color: #1b4332 !important;
        }
        .stProgress > div > div > div > div {
            background-color: #74c69d;
        }
        div[data-testid="stMetricValue"] {
            font-size: 2rem !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📊 Tableau de bord — Questionnaire Bien-être au travail")
st.caption("Suivi global du ressenti des professionnels des EHPAD 🌱")

API_URL = "https://questionnairesantementale.onrender.com"

# --- CHARGEMENT DES STATISTIQUES ---
@st.cache_data(ttl=300)
def load_stats():
    try:
        res = requests.get(f"{API_URL}/stats", timeout=15)
        if res.status_code == 200:
            data = res.json().get("stats", [])
            return pd.DataFrame(data)
        else:
            st.error("⚠️ Impossible de récupérer les statistiques depuis l’API.")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Erreur de connexion à l’API : {e}")
        return pd.DataFrame()

df = load_stats()

# --- SI VIDE ---
if df.empty:
    st.warning("Aucune donnée à afficher. Complétez d’abord le questionnaire.")
    st.stop()

# --- SCORE GLOBAL ---
global_mean = df["moyenne"].mean()
global_color = "#2ecc71" if global_mean >= 4 else "#f39c12" if global_mean >= 3 else "#e74c3c"

st.markdown("### 🌿 Indice global de bien-être")
st.progress(min(global_mean / 5, 1))
st.markdown(
    f"<h2 style='text-align:center; color:{global_color};'>"
    f"{global_mean:.2f} / 5</h2>",
    unsafe_allow_html=True,
)

# --- INDICATEURS CLÉS ---
col1, col2, col3 = st.columns(3)
col1.metric("🌞 Sections évaluées", f"{len(df)}")
col2.metric("👥 Réponses totales", f"{df['nb_reponses'].sum()}")
col3.metric(
    "📅 Dernière mise à jour",
    datetime.now().strftime("%d/%m/%Y à %H:%M"),
)

st.markdown("---")

# --- GRAPHIQUE RADAR ---
st.subheader("🕸️ Profil global par dimension")
df["couleur"] = df["moyenne"].apply(
    lambda s: "#2ecc71" if s >= 4 else "#f39c12" if s >= 3 else "#e74c3c"
)

radar_fig = px.line_polar(
    df,
    r="moyenne",
    theta="section",
    line_close=True,
    range_r=[0, 5],
    color_discrete_sequence=["#1b4332"],
    template="plotly_white",
)
radar_fig.add_trace(
    px.scatter_polar(
        df,
        r="moyenne",
        theta="section",
        color="couleur",
        color_discrete_map="identity",
        size=[12] * len(df),
    ).data[0]
)
radar_fig.update_traces(fill="toself", hovertemplate="%{theta}: %{r:.2f}/5")
radar_fig.update_layout(
    polar=dict(
        radialaxis=dict(visible=True, range=[0, 5], showline=True, gridcolor="#ddd"),
        angularaxis=dict(tickfont=dict(size=11, color="#1b4332")),
    ),
    margin=dict(l=40, r=40, t=20, b=20),
    showlegend=False,
)
st.plotly_chart(radar_fig, use_container_width=True)

# --- BAR CHART ---
st.markdown("### 📈 Scores moyens par section")

df_sorted = df.sort_values("moyenne", ascending=True)

bar_chart = (
    alt.Chart(df_sorted)
    .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
    .encode(
        x=alt.X(
            "moyenne:Q",
            title="Score moyen (1–5)",
            scale=alt.Scale(domain=[0, 5]),
        ),
        y=alt.Y("section:N", sort="-x", title=""),
        color=alt.Color("moyenne:Q", scale=alt.Scale(scheme="greens")),
        tooltip=[
            alt.Tooltip("section", title="Section"),
            alt.Tooltip("moyenne", title="Score moyen", format=".2f"),
            alt.Tooltip("nb_reponses", title="Nombre de réponses"),
        ],
    )
    .properties(height=420)
)
st.altair_chart(bar_chart, use_container_width=True)

st.caption(
    "💡 Ces scores représentent les moyennes corrigées (questions inversées incluses). "
    "Ils sont calculés en temps réel à partir des réponses enregistrées."
)

st.markdown("---")

# --- EXPORT CSV ---
st.subheader("📦 Export des données brutes")
st.write("Téléchargez les réponses complètes au format CSV pour analyse ou archivage.")

if st.button("💾 Générer le fichier CSV"):
    try:
        r = requests.get(f"{API_URL}/export", timeout=15)
        if r.status_code == 200:
            st.download_button(
                label="⬇️ Télécharger les réponses",
                data=r.content,
                file_name="responses_export.csv",
                mime="text/csv",
            )
            st.success("✅ Données prêtes au téléchargement.")
        else:
            st.error("Erreur lors du téléchargement des données.")
    except Exception as e:
        st.error(f"Erreur : {e}")
