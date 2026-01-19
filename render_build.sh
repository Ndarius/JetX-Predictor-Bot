#!/usr/bin/env bash
# exit on error
set -o errexit

# Installer les dépendances Python
pip install -r requirements.txt

# Sur Render, il est préférable d'utiliser les Buildpacks pour Chrome.
# Si vous n'utilisez pas de buildpacks, ce script tente d'installer les dépendances nécessaires.
# Mais pour Selenium, ajoutez ces deux Buildpacks dans les paramètres Render :
# 1. https://github.com/heroku/heroku-buildpack-google-chrome
# 2. https://github.com/heroku/heroku-buildpack-google-chromedriver

echo "Build terminé. Assurez-vous d'avoir ajouté les buildpacks Chrome et Chromedriver dans les paramètres Render."
