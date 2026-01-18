#!/usr/bin/env bash

# Export paths for Chromium and Driver
export GOOGLE_CHROME_BIN=${GOOGLE_CHROME_BIN:-/usr/bin/chromium}
export CHROMEDRIVER_PATH=${CHROMEDRIVER_PATH:-/usr/bin/chromedriver}

echo "--- Démarrage de l'environnement JetX ---"

# Nettoyage initial des processus potentiels pour libérer de la RAM
pkill -9 -f chromium || true
pkill -9 -f streamlit || true
pkill -9 -f python || true

# Fonction pour démarrer le bot avec redémarrage automatique
run_bot() {
    echo "Lancement du bot JetX..."
    while true; do
        # On attend un peu que Streamlit se stabilise avant de lancer Chrome
        sleep 10
        python jetx_betpawa_bot.py
        echo "ALERTE : Le bot s'est arrêté. Nettoyage et redémarrage dans 20s..."
        pkill -9 -f chromium || true
        sleep 20
    done
}

# Lancer le bot en arrière-plan
run_bot &

echo "Démarrage du Dashboard Streamlit sur le port ${PORT:-8000}..."
# Streamlit est lancé en premier car il est plus léger au repos
streamlit run dashboard.py --server.port ${PORT:-8000} --server.address 0.0.0.0 --server.headless true --browser.gatherUsageStats false
