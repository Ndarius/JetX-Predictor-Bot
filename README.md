# JetX Predictor Bot (betpawa.bj)

Ce bot automatise la surveillance du jeu JetX sur le site betpawa.bj. Il collecte les multiplicateurs en temps réel, enregistre l'heure exacte de chaque événement et fournit des signaux basés sur une analyse statistique simple.

## Fonctionnalités
- **Surveillance en temps réel** : Extraction du multiplicateur sans recharger la page.
- **Horodatage précis** : Enregistrement de chaque changement de valeur avec millisecondes.
- **Journalisation CSV** : Sauvegarde automatique dans `jetx_data_log.csv`.
- **Analyse Statistique** : Calcul dynamique des seuils d'encaissement (Moyenne +/- Écart-type).

## Installation

1. **Cloner le dépôt** :
   ```bash
   git clone https://github.com/Ndarius/JetX-Predictor-Bot.git
   cd JetX-Predictor-Bot
   ```

2. **Installer les dépendances** :
   ```bash
   pip install -r requirements.txt
   ```

3. **Installer Google Chrome** (si non présent) et le driver sera géré automatiquement par le script.

## Utilisation

Lancez le script avec Python :
```bash
python jetx_betpawa_bot.py
```

### Configuration
- Ouvrez `jetx_betpawa_bot.py` pour modifier le `margin_factor` (par défaut 1.5) afin d'ajuster la sensibilité des signaux.
- Le script est configuré pour s'exécuter avec interface graphique par défaut. Pour un serveur (VPS), décommentez la ligne `chrome_options.add_argument("--headless")`.

## Déploiement sur un VPS (Ubuntu/Debian)

1. Mettez à jour le système : `sudo apt update && sudo apt upgrade`
2. Installez Python et Chrome :
   ```bash
   sudo apt install python3-pip google-chrome-stable
   ```
3. Suivez les étapes d'installation ci-dessus.
4. Utilisez `screen` ou `tmux` pour laisser le bot tourner en arrière-plan :
   ```bash
   screen -S jetx_bot
   python3 jetx_betpawa_bot.py
   ```

## Avertissement
Ce bot est un outil d'analyse statistique. Le jeu JetX est basé sur le hasard (RNG). L'utilisation de ce script comporte des risques financiers. Jouez de manière responsable.
