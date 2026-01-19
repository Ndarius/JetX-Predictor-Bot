#!/usr/bin/env bash

# Export paths for Chromium and Driver
export GOOGLE_CHROME_BIN=${GOOGLE_CHROME_BIN:-/usr/bin/chromium}
export CHROMEDRIVER_PATH=${CHROMEDRIVER_PATH:-/usr/bin/chromedriver}
export PORT=${PORT:-8000}

echo "--- Démarrage du Bot JetX (Mode Performance) ---"

# Lancement d'un mini-serveur HTTP pour le Health Check de Koyeb (consomme < 5MB RAM)
# Cela évite que Koyeb ne redémarre l'instance parce que le port 8000 est fermé
python3 healthcheck.py &

# Nettoyage initial des processus pour libérer la RAM
pkill -9 -f chromium || true
pkill -9 -f streamlit || true

echo "Surveillance active et Health Check démarré sur le port $PORT"

# Lancement du bot
python3 jetx_betpawa_bot.py
