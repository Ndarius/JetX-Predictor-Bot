#!/usr/bin/env bash

# Export paths for Chromium and Driver
export GOOGLE_CHROME_BIN=${GOOGLE_CHROME_BIN:-/usr/bin/chromium}
export CHROMEDRIVER_PATH=${CHROMEDRIVER_PATH:-/usr/bin/chromedriver}
export PORT=${PORT:-10000}

echo "--- Démarrage du Bot JetX avec Dashboard ---"

# Nettoyage initial des processus pour libérer la RAM
pkill -9 -f chromium || true
pkill -9 -f streamlit || true

# Lancement du Dashboard Streamlit en arrière-plan sur le port Render
# On utilise --server.port pour que Render puisse faire le health check dessus
streamlit run dashboard.py --server.port $PORT --server.address 0.0.0.0 &

echo "Dashboard démarré sur le port $PORT"

# Attendre un peu que le dashboard soit prêt
sleep 5

# Lancement du bot en premier plan
echo "Lancement du bot de surveillance..."
python3 jetx_betpawa_bot.py
