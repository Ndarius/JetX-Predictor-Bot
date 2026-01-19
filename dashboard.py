import streamlit as st
import os
import psycopg2
import pandas as pd
import plotly.express as px
import time
import warnings
from datetime import datetime

# Ignorer les avertissements de Pandas concernant la connexion directe DBAPI2
warnings.filterwarnings("ignore", category=UserWarning, message=".*pandas only supports SQLAlchemy.*")

# Configuration de la page
st.set_page_config(page_title="JetX Predictor Dashboard", layout="wide", page_icon="🚀")

# Style CSS personnalisé pour une interface plus "temps réel"
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
        color: #ffffff;
    }
    .stMetric {
        background-color: #1e2130;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #4e5d6c;
    }
    .prediction-box {
        background-color: #262730;
        padding: 20px;
        border-radius: 15px;
        border-left: 5px solid #ff4b4b;
        margin-bottom: 20px;
    }
    /* Animation de pulsation pour indiquer le live */
    .live-indicator {
        float: right;
        color: #ff4b4b;
        font-weight: bold;
        animation: blinker 1.5s linear infinite;
    }
    @keyframes blinker {
        50% { opacity: 0; }
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="live-indicator">● LIVE</div>', unsafe_allow_html=True)
st.title("🚀 JetX Predictor Pro - Dashboard")

# Connexion à la base de données avec cache pour la performance
@st.cache_resource(ttl=60)
def get_db_connection():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        return None
    try:
        return psycopg2.connect(db_url)
    except:
        return None

def load_data():
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame()
    try:
        # On récupère les 100 derniers logs pour l'historique
        query = "SELECT * FROM jetx_logs ORDER BY timestamp DESC LIMIT 100"
        df = pd.read_sql(query, conn)
        return df
    except Exception as e:
        return pd.DataFrame()

# Debug Images Section
debug_files = ["debug_betpawa.png", "debug_betpawa_initial.png", "debug_betpawa_after_login.png"]
available_debug = [f for f in debug_files if os.path.exists(f)]

if available_debug:
    with st.expander("🔍 Voir l'état du Bot (Debug)", expanded=False):
        cols = st.columns(len(available_debug))
        for i, img_path in enumerate(available_debug):
            with cols[i]:
                # Ajout d'un paramètre de temps pour forcer le rafraîchissement de l'image
                st.image(f"{img_path}?t={int(time.time())}", caption=f"Capture: {img_path}")
else:
    st.sidebar.info("ℹ️ Aucune capture de debug disponible.")

# Sidebar pour le statut
st.sidebar.header("Statut du Système")
db_status = "✅ Connecté" if os.environ.get('DATABASE_URL') else "❌ Non configuré"
st.sidebar.write(f"Base de données : {db_status}")
st.sidebar.write(f"Dernier rafraîchissement : {datetime.now().strftime('%H:%M:%S')}")

# Chargement des données
df = load_data()

if not df.empty:
    # Zone de Prédiction
    last_prediction = df[df['prediction'].notnull()].iloc[0] if not df[df['prediction'].notnull()].empty else None
    
    st.markdown('<div class="prediction-box">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("🎯 Prochaine Prédiction")
        if last_prediction is not None:
            st.markdown(f"<h1 style='color: #ff4b4b;'>{last_prediction['prediction']:.2f}x</h1>", unsafe_allow_html=True)
        else:
            st.write("En attente de données...")
            
    with col2:
        st.subheader("📊 Dernier Résultat")
        last_result = df[df['type'] == 'result'].iloc[0] if not df[df['type'] == 'result'].empty else None
        if last_result is not None:
            color = "#00ff00" if last_result['multiplier'] >= 2.0 else "#ff4b4b"
            st.markdown(f"<h1 style='color: {color};'>{last_result['multiplier']:.2f}x</h1>", unsafe_allow_html=True)
            
    with col3:
        st.subheader("⏱️ Mis à jour à")
        st.write(df.iloc[0]['timestamp'].strftime("%H:%M:%S"))
    st.markdown('</div>', unsafe_allow_html=True)

    # Statistiques
    st.divider()
    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
    
    results_only = df[df['type'] == 'result']
    if not results_only.empty:
        with col_stat1:
            st.metric("Moyenne", f"{results_only['multiplier'].mean():.2f}x")
        with col_stat2:
            st.metric("Médiane", f"{results_only['multiplier'].median():.2f}x")
        with col_stat3:
            win_rate = (results_only['multiplier'] >= 1.5).mean() * 100
            st.metric("Taux > 1.5x", f"{win_rate:.1f}%")
        with col_stat4:
            st.metric("Total Tours", len(results_only))

    # Graphique d'historique
    st.subheader("📈 Historique des Multiplicateurs")
    if not results_only.empty:
        fig = px.line(results_only, x='timestamp', y='multiplier', 
                     title="Évolution des multiplicateurs",
                     template="plotly_dark",
                     labels={'multiplier': 'Multiplicateur', 'timestamp': 'Heure'})
        fig.add_hline(y=2.0, line_dash="dash", line_color="green", annotation_text="Objectif 2x")
        st.plotly_chart(fig, use_container_width=True)

    # Tableau des données
    st.subheader("📋 Derniers Tours")
    st.dataframe(df[['timestamp', 'multiplier', 'type', 'prediction']].head(20), use_container_width=True)

else:
    st.warning("⚠️ Aucune donnée trouvée dans la base de données.")
    st.info("Le bot est connecté mais attend la fin du premier tour pour enregistrer des données.")

# Rafraîchissement dynamique toutes les 3 secondes
time.sleep(3)
st.rerun()
