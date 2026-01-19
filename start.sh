#!/usr/bin/env bash

# Export des chemins pour Render
export PORT=${PORT:-10000}

echo "--- Démarrage du Bot JetX sur Render ---"

# Nettoyage des processus pour libérer la RAM
pkill -9 -f chrome || true
pkill -9 -f streamlit || true

# Lancement du Dashboard Streamlit (Indispensable pour le Health Check de Render)
streamlit run dashboard.py --server.port $PORT --server.address 0.0.0.0 &

echo "Dashboard Streamlit lancé sur le port $PORT"

# Attendre que le dashboard soit prêt
sleep 10

# Lancement du bot de surveillance
echo "Lancement du bot JetX..."
python jetx_betpawa_bot.py
