#!/usr/bin/env bash

# Export paths for Chrome and Driver
export GOOGLE_CHROME_BIN=/usr/bin/google-chrome-stable
export CHROMEDRIVER_PATH=/usr/bin/chromedriver

echo "--- Démarrage de l'environnement JetX ---"

# Fonction pour démarrer le bot avec redémarrage automatique et logs visibles
run_bot() {
    echo "Lancement du bot JetX..."
    while true; do
        python jetx_betpawa_bot.py 2>&1 | tee -a /tmp/bot_stdout.log
        echo "ALERTE : Le bot s'est arrêté avec le code $?. Redémarrage dans 10s..."
        sleep 10
    done
}

# Lancer le bot en arrière-plan
run_bot &

echo "Démarrage du Dashboard Streamlit sur le port ${PORT:-8000}..."
# Streamlit en premier plan pour que Koyeb garde l'instance active
streamlit run dashboard.py --server.port ${PORT:-8000} --server.address 0.0.0.0 --server.headless true
