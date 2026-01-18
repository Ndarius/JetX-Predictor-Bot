#!/usr/bin/env bash

# Export paths for Chromium and Driver
export GOOGLE_CHROME_BIN=${GOOGLE_CHROME_BIN:-/usr/bin/chromium}
export CHROMEDRIVER_PATH=${CHROMEDRIVER_PATH:-/usr/bin/chromedriver}

echo "--- Démarrage du Bot JetX (Mode Performance) ---"
echo "Note: Le Dashboard Streamlit est désactivé sur cette instance pour économiser la RAM."

# Nettoyage initial des processus pour libérer 100% de la RAM pour Chrome
pkill -9 -f chromium || true
pkill -9 -f streamlit || true
pkill -9 -f python || true

# Lancement direct du bot (pas d'arrière-plan pour que Koyeb puisse monitorer le processus)
# Le bot a déjà sa propre boucle de redémarrage interne
python jetx_betpawa_bot.py
