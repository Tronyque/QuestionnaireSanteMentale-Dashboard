import streamlit as st
import pandas as pd
import requests
import altair as alt
import plotly.express as px

# --- Configuration générale ---
st.set_page_config(page_title="Dashboard Bien-être", layout="centered")
st.title("📊 Tableau de bord — Questionnaire Bien-être au travail")

# ✅ API Render (backend FastAPI)
API_URL = "https://questionnairesantementale.onrender.com"

# --- Chargement des statistiques ---
@st.cache_data
def load_stats():
    try:
        with st.spinner("⏳ Récupération des statistiques..."):
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

# --- Chargement des données ---
df = load_stats()

if df.empty:
    st.warning("Aucune donnée à afficher. Complétez d’abord le questionnaire.")
else:
    # --- Score global moyen ---
    global_mean = df["moyenne"].mean()
    score_color = "green" if global_mean >= 4 else "orange" if global_mean >= 3 else "red"

    st.markdown("---")
    st.markdown(
        f"<h2 style='text-align:center; color:{score_color};'>"
        f"🌿 Indice global de bien-être : {global_mean:.2f} / 5"
        f"</h2>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # --- Graphique radar ---
    st.subheader("🕸️ Profil global par dimension")

    df["couleur"] = df["moyenne"].apply(
        lambda s: "#2ECC71" if s >= 4 else "#F5B041" if s >= 3 else "#E74C3C"
    )

    radar_fig = px.line_polar(
        df,
        r="moyenne",
        theta="section",
        line_close=True,
        range_r=[0, 5],
        color_discrete_sequence=["#007BFF"],
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
            radialaxis=dict(visible=True, range=[0, 5]),
            angularaxis=dict(tickfont=dict(size=11)),
        ),
        showlegend=False,
        margin=dict(l=30, r=30, t=30, b=30),
    )
    st.plotly_chart(radar_fig, use_container_width=True)

    # --- Graphique barres ---
    st.subheader("📈 Moyennes par section")
    df = df.sort_values("moyenne", ascending=False)

    bar_chart = (
        alt.Chart(df)
        .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
        .encode(
            x=alt.X("moyenne:Q", title="Score moyen (1–5)", scale=alt.Scale(domain=[0, 5])),
            y=alt.Y("section:N", sort="-x", title=""),
            color=alt.Color("moyenne:Q", scale=alt.Scale(scheme="blues")),
            tooltip=["section", "moyenne", "nb_reponses"],
        )
        .properties(height=400)
    )
    st.altair_chart(bar_chart, use_container_width=True)

    st.caption("💡 Ces scores représentent les moyennes corrigées des réponses (inversées incluses).")

    # --- Export CSV ---
    st.markdown("---")
    st.subheader("📦 Exporter les données brutes")

    if st.button("💾 Télécharger les réponses (CSV)"):
        try:
            r = requests.get(f"{API_URL}/export", timeout=15)
            if r.status_code == 200:
                st.download_button(
                    label="⬇️ Télécharger le fichier CSV",
                    data=r.content,
                    file_name="responses_export.csv",
                    mime="text/csv",
                )
                st.success("✅ Fichier prêt au téléchargement !")
            else:
                st.error("Erreur lors du téléchargement des données.")
        except Exception as e:
            st.error(f"Erreur : {e}")
