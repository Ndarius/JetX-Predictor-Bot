import streamlit as st
import os
import psycopg2
import pandas as pd

# Configuration de la page
st.set_page_config(page_title="Diagnostic Connexion Neon", layout="wide")

st.title("🔍 Diagnostic de Connexion à la Base de Données")

# Récupération de la variable d'environnement
db_url = os.environ.get('DATABASE_URL')

st.subheader("1. Vérification de la variable d'environnement")
if not db_url:
    st.error("❌ La variable 'DATABASE_URL' n'est pas définie dans les Secrets de Streamlit.")
    st.info("Veuillez l'ajouter dans Settings > Secrets sous la forme : DATABASE_URL='votre_url'")
else:
    # Masquer le mot de passe pour l'affichage
    safe_url = db_url.split('@')[-1] if '@' in db_url else "URL format invalide"
    st.success(f"✅ Variable 'DATABASE_URL' détectée (Host: {safe_url})")

st.subheader("2. Tentative de connexion à PostgreSQL")
if db_url:
    try:
        # Tentative de connexion
        conn = psycopg2.connect(db_url)
        st.success("✅ Connexion établie avec succès à Neon.tech !")
        
        # Test de lecture
        st.subheader("3. Test de lecture des données")
        cur = conn.cursor()
        
        # Vérifier si la table existe
        cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'jetx_logs');")
        table_exists = cur.fetchone()[0]
        
        if table_exists:
            st.success("✅ La table 'jetx_logs' existe.")
            cur.execute("SELECT * FROM jetx_logs ORDER BY timestamp DESC LIMIT 5")
            rows = cur.fetchall()
            colnames = [desc[0] for desc in cur.description]
            
            if rows:
                df = pd.DataFrame(rows, columns=colnames)
                st.write("Derniers enregistrements trouvés :")
                st.dataframe(df)
            else:
                st.warning("⚠️ La table 'jetx_logs' est vide.")
        else:
            st.error("❌ La table 'jetx_logs' n'existe pas encore dans la base de données.")
            st.info("Le bot doit d'abord créer la table et insérer des données.")
            
        cur.close()
        conn.close()
        
    except Exception as e:
        st.error("❌ Échec de la connexion à la base de données.")
        st.code(str(e))
        
        st.info("Conseil : Vérifiez que vous utilisez l'URL du 'pooler' de Neon et que '&sslmode=require' est présent.")

st.divider()
if st.button("🔄 Re-tester la connexion"):
    st.rerun()
