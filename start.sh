#!/usr/bin/env bash

# Lancer le bot en arrière-plan
echo "Démarrage du bot JetX..."
python jetx_betpawa_bot.py &

# Lancer le dashboard Streamlit (processus principal)
echo "Démarrage du Dashboard Streamlit..."
streamlit run dashboard.py --server.port ${PORT:-8000} --server.address 0.0.0.0
