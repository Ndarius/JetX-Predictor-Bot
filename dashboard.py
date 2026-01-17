import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import time
import os
import sys
from datetime import datetime

# Ajouter le répertoire courant au chemin de recherche Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(page_title="JetX Predictor Pro", layout="wide", page_icon="🚀")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #4e5d6c; }
    .prediction-box { background-color: #262730; padding: 20px; border-radius: 15px; border-left: 5px solid #00ff00; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 JetX Predictor Pro - Analyse Temporelle & Horaires")

db_file = "jetx_data.db"

def load_data():
    if not os.path.exists(db_file): return pd.DataFrame()
    try:
        conn = sqlite3.connect(db_file)
        df = pd.read_sql_query("SELECT * FROM jetx_logs ORDER BY timestamp DESC", conn)
        conn.close()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except: return pd.DataFrame()

# Sidebar
st.sidebar.header("⚙️ Configuration")
refresh_rate = st.sidebar.slider("Rafraîchissement (s)", 0.5, 5.0, 1.0)

placeholder = st.empty()

while True:
    df = load_data()
    
    with placeholder.container():
        if df.empty:
            st.info("⏳ En attente de données...")
        else:
            df_results = df[df['type'] == 'result']
            latest_round = df_results.iloc[0] if not df_results.empty else None
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown('<div class="prediction-box">', unsafe_allow_html=True)
                st.subheader("🔮 Prédiction Prochain Tour")
                if latest_round is not None:
                    next_pred = latest_round['prediction']
                    st.markdown(f"<h1 style='text-align: center; color: #00ff00;'>{next_pred:.2f}x</h1>", unsafe_allow_html=True)
                    st.caption(f"Analyse incluant les tendances horaires ({datetime.now().hour}h)")
                st.markdown('</div>', unsafe_allow_html=True)

            with col2:
                st.subheader("📊 Statistiques Globales")
                m1, m2, m3 = st.columns(3)
                m1.metric("Dernier", f"{latest_round['multiplier'] if latest_round is not None else 0}x")
                m2.metric("Moyenne", f"{df_results['multiplier'].mean():.2f}x")
                m3.metric("Tours", len(df_results))

            # Analyse Horaire
            st.subheader("⏰ Analyse par Heure")
            df_results['hour'] = df_results['timestamp'].dt.hour
            hourly_stats = df_results.groupby('hour')['multiplier'].mean().reset_index()
            fig_hour = px.bar(hourly_stats, x='hour', y='multiplier', 
                             title="Multiplicateur Moyen par Heure",
                             labels={'hour': 'Heure de la journée', 'multiplier': 'Moyenne x'},
                             color='multiplier', color_continuous_scale='Viridis')
            fig_hour.update_layout(template="plotly_dark", height=300)
            st.plotly_chart(fig_hour, use_container_width=True)

            # Chart Historique
            st.subheader("📈 Historique des Tours")
            df_plot = df_results.head(100).sort_values('timestamp')
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_plot['timestamp'], y=df_plot['multiplier'], mode='lines+markers', name='Réel', line=dict(color='#ff4b4b')))
            fig.add_trace(go.Scatter(x=df_plot['timestamp'], y=df_plot['prediction'], mode='lines', name='Prédiction', line=dict(color='#00ff00', dash='dash')))
            fig.update_layout(template="plotly_dark", height=400)
            st.plotly_chart(fig, use_container_width=True)
                
    time.sleep(refresh_rate)
