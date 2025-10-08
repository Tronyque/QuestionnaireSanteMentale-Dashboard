import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import altair as alt
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="🌿 Dashboard Bien-être", layout="wide", page_icon="🌸")

st.title("📊 Tableau de bord — Questionnaire Bien-être au travail")
st.caption("Visualisez vos résultats individuels 🌱")

API_URL = "https://questionnairesantementale.onrender.com"

# --- INPUT UTILISATEUR ---
st.sidebar.header("🔍 Filtrer vos résultats")
user_id = st.sidebar.text_input("Entrez votre prénom ou pseudo :", "")
compare_global = st.sidebar.checkbox("Afficher la moyenne globale", value=True)

if not user_id:
    st.warning("Veuillez entrer votre prénom ou pseudo pour afficher vos résultats.")
    st.stop()

# --- CHARGEMENT ---
@st.cache_data(ttl=120)
def load_user_stats(user_id: str):
    try:
        res = requests.get(f"{API_URL}/stats/{user_id}", timeout=10)
        if res.status_code == 200:
            return pd.DataFrame(res.json().get("stats", []))
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_global_stats():
    try:
        res = requests.get(f"{API_URL}/stats", timeout=10)
        if res.status_code == 200:
            return pd.DataFrame(res.json().get("stats", []))
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

df = load_user_stats(user_id)
if df.empty:
    st.warning(f"Aucune donnée trouvée pour l'utilisateur « {user_id} ».")
    st.stop()

# --- NORMALISATION ---
def detect_max_scale(section):
    if section in ["Efficacité personnelle"]:
        return 4
    elif section in ["Énergie et engagement"]:
        return 7
    else:
        return 5

df["score_10"] = df.apply(lambda r: 1 + (r["moyenne"] - 1) * (9 / (detect_max_scale(r["section"]) - 1)), axis=1)

def score_to_color(score):
    if score <= 3: return "#e74c3c"
    elif score <= 6: return "#f1c40f"
    else: return "#2ecc71"

df["couleur"] = df["score_10"].apply(score_to_color)

# --- GLOBAL MOYEN ---
global_mean = df["score_10"].mean()
global_color = score_to_color(global_mean)

st.markdown(f"### 🌿 Votre indice global de bien-être : <span style='color:{global_color}'>{global_mean:.2f} / 10</span>", unsafe_allow_html=True)

st.progress(global_mean / 10)
st.caption(f"Dernière mise à jour : {datetime.now().strftime('%d/%m/%Y à %H:%M')}")

# --- COMPARAISON ---
if compare_global:
    df_global = load_global_stats()
    if not df_global.empty:
        df_global["score_10"] = df_global.apply(lambda r: 1 + (r["moyenne"] - 1) * (9 / (detect_max_scale(r["section"]) - 1)), axis=1)

# --- RADAR ---
st.subheader("🕸️ Votre profil par dimension (1–10)")

radar_fig = px.line_polar(df, r="score_10", theta="section", line_close=True, range_r=[0, 10], color_discrete_sequence=["#1b4332"], template="plotly_white")
radar_fig.add_trace(px.scatter_polar(df, r="score_10", theta="section", color="couleur", color_discrete_map="identity", size=[12] * len(df)).data[0])

if compare_global and not df_global.empty:
    radar_fig.add_trace(px.line_polar(df_global, r="score_10", theta="section", line_close=True, range_r=[0, 10], color_discrete_sequence=["#74c0fc"]).update_traces(line=dict(dash="dot", width=2)).data[0])

radar_fig.update_traces(fill="toself", hovertemplate="%{theta}: %{r:.2f}/10")
radar_fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10]), angularaxis=dict(tickfont=dict(size=11))), showlegend=False)
st.plotly_chart(radar_fig, use_container_width=True)

st.markdown(
    "<div style='text-align:center; margin-top:-10px; margin-bottom:25px;'>"
    "<div style='width:200px; height:15px; background:linear-gradient(to right,#e74c3c,#f1c40f,#2ecc71);border-radius:5px;display:inline-block;margin-right:10px;'></div>"
    "<span style='font-size:0.9rem;color:#333;'>1–3 : Faible | 4–6 : Moyen | 7–10 : Élevé</span>"
    "</div>",
    unsafe_allow_html=True,
)

# --- BAR CHART ---
st.subheader("📈 Scores normalisés par section")

df_sorted = df.sort_values("score_10", ascending=True)
bar_chart = (
    alt.Chart(df_sorted)
    .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
    .encode(
        x=alt.X("score_10:Q", title="Score (1–10)", scale=alt.Scale(domain=[0, 10])),
        y=alt.Y("section:N", sort="-x", title=""),
        color=alt.Color("score_10:Q", scale=alt.Scale(scheme="redyellowgreen")),
        tooltip=["section", "moyenne", "score_10", "nb_reponses"],
    )
    .properties(height=420)
)
st.altair_chart(bar_chart, use_container_width=True)

# --- EXPORT CSV ---
st.markdown("---")
st.subheader("📦 Exporter vos réponses")

if st.button("💾 Télécharger vos données"):
    try:
        r = requests.get(f"{API_URL}/export", timeout=15)
        if r.status_code == 200:
            st.download_button("⬇️ Télécharger le CSV", data=r.content, file_name="responses_export.csv", mime="text/csv")
    except Exception as e:
        st.error(f"Erreur : {e}")
