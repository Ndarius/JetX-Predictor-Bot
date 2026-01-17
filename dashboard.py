import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime

# Configuration
st.set_page_config(page_title="JetX Predictor Pro", layout="wide", page_icon="🚀")

# Unified DB Path Logic
if os.path.exists("/bot"):
    db_file = "/bot/jetx_data.db"
else:
    db_file = "/tmp/jetx_data.db"

@st.cache_data(ttl=1)
def load_data():
    if not os.path.exists(db_file):
        return pd.DataFrame()
    try:
        conn = sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)
        df = pd.read_sql_query("SELECT * FROM jetx_logs ORDER BY timestamp DESC LIMIT 100", conn)
        conn.close()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except:
        return pd.DataFrame()

st.title("🚀 JetX Predictor Pro")
st.sidebar.header("⚙️ Configuration")
refresh_rate = st.sidebar.slider("Rafraîchissement (s)", 1, 10, 2)

df = load_data()

if df.empty:
    st.error("🔴 Bot en attente de données...")
    st.info(f"Le bot doit d'abord capturer un tour. DB: `{db_file}`")
    if st.button("🔄 Actualiser"):
        st.rerun()
else:
    df_results = df[df['type'] == 'result'].copy()
    
    if not df_results.empty:
        latest = df_results.iloc[0]
        
        # 1. PREDICTION TOUR SUIVANT
        st.markdown(f"""
            <div style="background-color: #262730; padding: 30px; border-radius: 15px; border-left: 10px solid #00ff00; text-align: center; margin-bottom: 25px;">
                <h2 style="margin: 0; color: #00ff00;">🔮 PRÉDICTION PROCHAIN TOUR</h2>
                <h1 style="font-size: 80px; margin: 10px 0;">{latest['prediction']:.2f}x</h1>
                <p style="color: #888;">Basé sur l'analyse en temps réel</p>
            </div>
        """, unsafe_allow_html=True)
        
        # 2. DERNIERS 5 TOURS
        st.subheader("📊 Historique des 5 derniers tours")
        cols = st.columns(5)
        last_5 = df_results.head(5)
        for i, (_, row) in enumerate(last_5.iterrows()):
            with cols[i]:
                color = "#00ff00" if row['multiplier'] >= 2.0 else "#ff4b4b"
                st.markdown(f"""
                    <div style="background-color: #1e2130; padding: 15px; border-radius: 10px; text-align: center; border: 1px solid #4e5d6c;">
                        <p style="margin: 0; color: #888; font-size: 12px;">{row['timestamp'].strftime('%H:%M:%S')}</p>
                        <h2 style="margin: 5px 0; color: {color};">{row['multiplier']:.2f}x</h2>
                    </div>
                """, unsafe_allow_html=True)

        # 3. GRAPHIQUE
        st.subheader("📈 Tendance")
        fig = px.line(df_results.head(20), x='timestamp', y='multiplier', markers=True)
        fig.update_layout(template="plotly_dark", height=300, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)

# Auto-refresh
import time
time.sleep(refresh_rate)
st.rerun()
