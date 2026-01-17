#!/usr/bin/env bash

# Fonction pour nettoyer les processus en cas d'arrêt
cleanup() {
    echo "Arrêt des processus..."
    kill $(jobs -p)
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "Démarrage du bot JetX en arrière-plan..."
# On lance le bot et on redirige les sorties vers un fichier log
python jetx_betpawa_bot.py > bot_output.log 2>&1 &
BOT_PID=$!

echo "Démarrage du Dashboard Streamlit..."
# Streamlit est lancé en premier plan pour que Koyeb puisse surveiller le processus
# On utilise le port fourni par Koyeb via la variable d'environnement PORT
streamlit run dashboard.py --server.port ${PORT:-8000} --server.address 0.0.0.0
