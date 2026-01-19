import streamlit as st
import os
import psycopg2
import pandas as pd
import plotly.express as px
import time
import warnings
from datetime import datetime

# Ignorer les avertissements
warnings.filterwarnings("ignore")

# Configuration de la page
st.set_page_config(page_title="JetX Predictor Dashboard", layout="wide", page_icon="🚀")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #4e5d6c; }
    .prediction-box { background-color: #262730; padding: 20px; border-radius: 15px; border-left: 5px solid #ff4b4b; margin-bottom: 20px; }
    .live-indicator { float: right; color: #ff4b4b; font-weight: bold; animation: blinker 1.5s linear infinite; }
    @keyframes blinker { 50% { opacity: 0; } }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="live-indicator">● LIVE</div>', unsafe_allow_html=True)
st.title("🚀 JetX Predictor Pro - Dashboard")

@st.cache_resource(ttl=30)
def get_db_connection():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url: return None
    try: return psycopg2.connect(db_url)
    except: return None

def load_data():
    conn = get_db_connection()
    if not conn: return pd.DataFrame()
    try:
        query = "SELECT * FROM jetx_logs ORDER BY timestamp DESC LIMIT 100"
        return pd.read_sql(query, conn)
    except: return pd.DataFrame()

# --- SECTION DEBUG SÉCURISÉE ---
debug_files = ["debug_betpawa_initial.png", "debug_betpawa_login_page.png", "debug_betpawa_after_login.png", "debug_betpawa_jetx_loaded.png", "debug_betpawa.png"]

with st.expander("🔍 Voir l'état du Bot (Debug)", expanded=False):
    available_debug = [f for f in debug_files if os.path.exists(f)]
    if available_debug:
        cols = st.columns(len(available_debug))
        for i, img_path in enumerate(available_debug):
            with cols[i]:
                try:
                    # On ouvre le fichier en binaire pour Streamlit pour éviter les erreurs de chemin/cache
                    with open(img_path, "rb") as f:
                        st.image(f.read(), caption=f"Capture: {img_path}", use_container_width=True)
                except Exception as e:
                    st.error(f"Erreur image: {img_path}")
    else:
        st.info("En attente des premières captures d'écran...")

# Sidebar
st.sidebar.header("Statut du Système")
db_status = "✅ Connecté" if os.environ.get('DATABASE_URL') else "❌ Non configuré"
st.sidebar.write(f"Base de données : {db_status}")
st.sidebar.write(f"Dernier rafraîchissement : {datetime.now().strftime('%H:%M:%S')}")

# Données
df = load_data()

if not df.empty:
    last_prediction = df[df['prediction'].notnull()].iloc[0] if not df[df['prediction'].notnull()].empty else None
    
    st.markdown('<div class="prediction-box">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("🎯 Prochaine Prédiction")
        if last_prediction is not None:
            st.markdown(f"<h1 style='color: #ff4b4b;'>{last_prediction['prediction']:.2f}x</h1>", unsafe_allow_html=True)
        else: st.write("En attente...")
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

    # Graphique
    results_only = df[df['type'] == 'result']
    if not results_only.empty:
        st.subheader("📈 Historique")
        fig = px.line(results_only, x='timestamp', y='multiplier', template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 Derniers Tours")
    st.dataframe(df[['timestamp', 'multiplier', 'type', 'prediction']].head(20), use_container_width=True)
else:
    st.warning("⚠️ Aucune donnée trouvée.")
    st.info("Le bot est en cours de navigation vers JetX...")

time.sleep(3)
st.rerun()
