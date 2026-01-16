#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Install Google Chrome (Render environment specific)
if [ ! -f "/usr/bin/google-chrome" ]; then
  echo "Installing Google Chrome..."
  wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
  echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list
  apt-get update && apt-get install -y google-chrome-stable
fi
