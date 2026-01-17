import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import os
import sys
from datetime import datetime

# Configuration de la page
st.set_page_config(page_title="JetX Predictor Pro", layout="wide", page_icon="🚀")

# Styles CSS optimisés
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #4e5d6c; }
    .prediction-box { background-color: #262730; padding: 20px; border-radius: 15px; border-left: 5px solid #00ff00; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# Gestion du chemin de la base de données
if os.path.exists("/bot/jetx_data.db"):
    db_file = "/bot/jetx_data.db"
elif os.environ.get('KOYEB_APP_ID') or os.environ.get('PORT'):
    db_file = os.path.join("/tmp", "jetx_data.db")
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_file = os.path.join(base_dir, "jetx_data.db")

@st.cache_data(ttl=1) # Cache de 1 seconde pour la rapidité
def load_data():
    if not os.path.exists(db_file):
        return pd.DataFrame()
    try:
        # Utilisation de mode lecture seule pour éviter les blocages avec le bot
        conn = sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)
        df = pd.read_sql_query("SELECT * FROM jetx_logs ORDER BY timestamp DESC LIMIT 500", conn)
        conn.close()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except Exception as e:
        return pd.DataFrame()

st.title("🚀 JetX Predictor Pro")

# Sidebar pour le contrôle
st.sidebar.header("⚙️ Configuration")
refresh_rate = st.sidebar.slider("Rafraîchissement (s)", 1, 10, 3)
if st.sidebar.button("🔄 Forcer l'actualisation"):
    st.rerun()

# Chargement des données
df = load_data()

if df.empty:
    st.error("🔴 Bot en attente de connexion ou de données...")
    st.info("⏳ Le bot JetX démarre en arrière-plan. Cela peut prendre 1 à 2 minutes lors du premier lancement sur Koyeb.")
    st.write(f"Chemin DB recherché : `{db_file}`")
    if st.button("🔄 Vérifier à nouveau"):
        st.rerun()
else:
    # Indicateur de statut
    last_update = df.iloc[0]['timestamp']
    diff = (datetime.now() - last_update).total_seconds()
    
    if diff < 60:
        st.success(f"🟢 Bot Actif - Mise à jour il y a {int(diff)}s")
    else:
        st.warning(f"🟠 Bot Inactif ou en attente - Dernier tour il y a {int(diff/60)} min")

    df_results = df[df['type'] == 'result']
    latest_round = df_results.iloc[0] if not df_results.empty else None
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown('<div class="prediction-box">', unsafe_allow_html=True)
        st.subheader("🔮 Prédiction Prochain Tour")
        if latest_round is not None:
            next_pred = latest_round['prediction']
            st.markdown(f"<h1 style='text-align: center; color: #00ff00;'>{next_pred:.2f}x</h1>", unsafe_allow_html=True)
            st.caption(f"Analyse basée sur les derniers tours ({datetime.now().strftime('%H:%M:%S')})")
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.subheader("📊 Statistiques")
        m1, m2, m3 = st.columns(3)
        m1.metric("Dernier", f"{latest_round['multiplier'] if latest_round is not None else 0}x")
        m2.metric("Moyenne", f"{df_results['multiplier'].mean():.2f}x")
        m3.metric("Tours", len(df_results))

    # Graphiques simplifiés pour la rapidité
    st.subheader("📈 Historique des Tours")
    df_plot = df_results.head(50).sort_values('timestamp')
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_plot['timestamp'], y=df_plot['multiplier'], mode='lines+markers', name='Réel', line=dict(color='#ff4b4b')))
    fig.add_trace(go.Scatter(x=df_plot['timestamp'], y=df_plot['prediction'], mode='lines', name='Prédiction', line=dict(color='#00ff00', dash='dash')))
    fig.update_layout(template="plotly_dark", height=350, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# Auto-refresh
st.empty()
import time
time.sleep(refresh_rate)
st.rerun()
