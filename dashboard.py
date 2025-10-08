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

# --- STYLE PERSONNALISÉ ---
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

# --- EN-TÊTE ---
st.title("📊 Tableau de bord — Questionnaire Bien-être au travail")
st.caption("Suivi global du ressenti des professionnels des EHPAD 🌱")

# --- API BACKEND ---
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

# --- SI AUCUNE DONNÉE ---
if df.empty:
    st.warning("Aucune donnée à afficher. Complétez d’abord le questionnaire.")
    st.stop()

# --- NORMALISATION 1–10 ---
def detect_max_scale(section: str):
    """Déduit l’échelle d’origine selon la section"""
    if section in ["Efficacité personnelle"]:
        return 4
    elif section in ["Énergie et engagement"]:
        return 7
    else:
        return 5

def normalize_score(row):
    """Convertit la moyenne de chaque section sur une échelle 1–10"""
    max_scale = detect_max_scale(row["section"])
    return 1 + (row["moyenne"] - 1) * (9 / (max_scale - 1))

df["score_10"] = df.apply(normalize_score, axis=1)

# --- COULEUR DYNAMIQUE ---
def score_to_color(score):
    """Dégradé rouge → jaune → vert"""
    if score <= 3:
        return "#e74c3c"  # rouge
    elif score <= 6:
        return "#f1c40f"  # jaune
    else:
        return "#2ecc71"  # vert

df["couleur"] = df["score_10"].apply(score_to_color)

# --- SCORE GLOBAL ---
global_mean = df["score_10"].mean()
global_color = score_to_color(global_mean)

st.markdown("### 🌿 Indice global de bien-être (normalisé 1–10)")
st.progress(min(global_mean / 10, 1))
st.markdown(
    f"<h2 style='text-align:center; color:{global_color};'>{global_mean:.2f} / 10</h2>",
    unsafe_allow_html=True,
)

# --- MÉTRIQUES CLÉS ---
col1, col2, col3 = st.columns(3)
col1.metric("🌞 Sections évaluées", f"{len(df)}")
col2.metric("👥 Réponses totales", f"{df['nb_reponses'].sum()}")
col3.metric("📅 Dernière mise à jour", datetime.now().strftime("%d/%m/%Y à %H:%M"))

st.markdown("---")

# --- RADAR SUR ÉCHELLE 1–10 ---
st.subheader("🕸️ Profil global par dimension (échelle 1–10)")

radar_fig = px.line_polar(
    df,
    r="score_10",
    theta="section",
    line_close=True,
    range_r=[0, 10],
    color_discrete_sequence=["#1b4332"],
    template="plotly_white",
)
radar_fig.add_trace(
    px.scatter_polar(
        df,
        r="score_10",
        theta="section",
        color="couleur",
        color_discrete_map="identity",
        size=[12] * len(df),
    ).data[0]
)
radar_fig.update_traces(fill="toself", hovertemplate="%{theta}: %{r:.2f}/10")
radar_fig.update_layout(
    polar=dict(
        radialaxis=dict(visible=True, range=[0, 10], tickfont=dict(size=10)),
        angularaxis=dict(tickfont=dict(size=11)),
    ),
    margin=dict(l=40, r=40, t=20, b=20),
    showlegend=False,
)
st.plotly_chart(radar_fig, use_container_width=True)

# --- LÉGENDE VISUELLE ---
st.markdown(
    """
    <div style='text-align:center; margin-top:-10px; margin-bottom:25px;'>
        <div style='display:inline-flex; align-items:center;'>
            <div style='width:200px; height:15px; background: linear-gradient(to right, #e74c3c, #f1c40f, #2ecc71); border-radius:5px; margin-right:10px;'></div>
            <span style='font-size:0.9rem; color:#333;'>1–3 : Faible &nbsp; | &nbsp; 4–6 : Moyen &nbsp; | &nbsp; 7–10 : Élevé</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- BARRES SUR 1–10 ---
st.markdown("### 📈 Scores normalisés par section (1–10)")

df_sorted = df.sort_values("score_10", ascending=True)

bar_chart = (
    alt.Chart(df_sorted)
    .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
    .encode(
        x=alt.X("score_10:Q", title="Score normalisé (1–10)", scale=alt.Scale(domain=[0, 10])),
        y=alt.Y("section:N", sort="-x", title=""),
        color=alt.Color("score_10:Q", scale=alt.Scale(scheme="redyellowgreen")),
        tooltip=[
            alt.Tooltip("section", title="Section"),
            alt.Tooltip("moyenne", title="Moyenne originale", format=".2f"),
            alt.Tooltip("score_10", title="Score 1–10", format=".2f"),
            alt.Tooltip("nb_reponses", title="Réponses"),
        ],
    )
    .properties(height=420)
)
st.altair_chart(bar_chart, use_container_width=True)

st.caption(
    "💡 Ces scores sont normalisés sur 1–10 pour permettre la comparaison entre les sections "
    "(quelle que soit leur échelle d’origine). Les couleurs reflètent la satisfaction perçue : "
    "rouge = faible, jaune = moyen, vert = élevé."
)

# --- EXPORT CSV ---
st.markdown("---")
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
