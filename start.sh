#!/usr/bin/env bash

# Fonction pour nettoyer les processus en cas d'arrêt
cleanup() {
    echo "Arrêt des processus..."
    kill $(jobs -p)
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "Démarrage du bot JetX en arrière-plan..."
# On lance le bot et on redirige les sorties vers un fichier log pour éviter de polluer la console
python jetx_betpawa_bot.py > bot_output.log 2>&1 &
BOT_PID=$!

echo "Démarrage du Dashboard Streamlit..."
# Streamlit devient le processus surveillé par Koyeb
streamlit run dashboard.py --server.port ${PORT:-8000} --server.address 0.0.0.0 &
STREAMLIT_PID=$!

# Boucle de surveillance pour s'assurer que les deux processus restent en vie
while true; do
    if ! kill -0 $BOT_PID 2>/dev/null; then
        echo "ALERTE : Le bot JetX s'est arrêté. Redémarrage..."
        python jetx_betpawa_bot.py > bot_output.log 2>&1 &
        BOT_PID=$!
    fi
    
    if ! kill -0 $STREAMLIT_PID 2>/dev/null; then
        echo "ALERTE : Streamlit s'est arrêté. Sortie pour redémarrage global."
        exit 1
    fi
    
    sleep 10
done
