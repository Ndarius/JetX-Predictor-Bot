import streamlit as st
import pandas as pd
import psycopg2
import os
from datetime import datetime

# Configuration
st.set_page_config(page_title="JetX Predictor Pro", layout="wide", page_icon="🚀")

def get_db_connection():
    # Prioritize DATABASE_URL if provided by Koyeb/Neon
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        # Ensure endpoint is specified if it's a Neon URL
        if "neon.tech" in db_url or "koyeb.app" in db_url:
            if "options=endpoint%3D" not in db_url and "?" in db_url:
                host = db_url.split("@")[1].split("/")[0]
                endpoint_id = host.split(".")[0]
                db_url += f"&options=endpoint%3D{endpoint_id}"
            elif "options=endpoint%3D" not in db_url and "?" not in db_url:
                host = db_url.split("@")[1].split("/")[0]
                endpoint_id = host.split(".")[0]
                db_url += f"?options=endpoint%3D{endpoint_id}"
        return psycopg2.connect(db_url)

    host = os.environ.get('DATABASE_HOST', '')
    user = os.environ.get('DATABASE_USER', '')
    password = os.environ.get('DATABASE_PASSWORD', '')
    dbname = os.environ.get('DATABASE_NAME', '')
    port = os.environ.get('DATABASE_PORT', '5432')
    
    # Extract the first part of the host (e.g., ep-green-glade-ahx9joi6)
    endpoint_id = host.split('.')[0] if host else ''
    
    # Use the full connection string format required by Neon/Koyeb
    conn_str = f"postgresql://{user}:{password}@{host}:{port}/{dbname}?sslmode=require&options=endpoint%3D{endpoint_id}"
    return psycopg2.connect(conn_str)

@st.cache_data(ttl=1)
def load_data():
    try:
        conn = get_db_connection()
        df = pd.read_sql_query("SELECT * FROM jetx_logs ORDER BY timestamp DESC LIMIT 100", conn)
        conn.close()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except Exception as e:
        return pd.DataFrame()

st.title("🚀 JetX Predictor Pro")
st.sidebar.header("⚙️ Configuration")
refresh_rate = st.sidebar.slider("Rafraîchissement (s)", 1, 10, 2)

df = load_data()

if df.empty:
    st.error("🔴 Bot en attente de données...")
    st.info("Le bot doit d'abord capturer un tour dans la base PostgreSQL.")
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
                <p style="color: #888;">Analyse PostgreSQL en temps réel</p>
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

# Auto-refresh
import time
time.sleep(refresh_rate)
st.rerun()
