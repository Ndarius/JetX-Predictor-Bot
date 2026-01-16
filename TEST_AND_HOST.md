# Guide de Test et Hébergement Gratuit

## 🧪 Comment tester l'outil ?

Pour vérifier que tout fonctionne correctement sans risquer d'argent :

1.  **Mode Simulation** : Le bot enregistre les données et fait des prédictions même si vous ne placez pas de paris. Observez simplement la console et le dashboard pendant 10-20 tours.
2.  **Vérification de la Précision** :
    *   Lancez le dashboard (`streamlit run dashboard.py`).
    *   Regardez le graphique : la ligne pointillée verte (prédiction) doit suivre globalement la tendance de la ligne rouge (réel).
    *   Vérifiez l'onglet "Analyse par Heure" pour voir si certaines heures sont plus rentables.
3.  **Logs** : Consultez le fichier `jetx_bot.log` pour voir si des erreurs d'extraction surviennent.

---

## ☁️ Où héberger l'outil gratuitement ?

Voici les meilleures options pour faire tourner le bot 24h/24 sans frais :

### 1. Oracle Cloud (Toujours Gratuit) - **Recommandé**
*   **Offre** : "Always Free" ARM Ampere.
*   **Avantages** : Jusqu'à 4 instances, 24 Go de RAM. C'est largement suffisant pour faire tourner Chrome en mode headless et Streamlit.
*   **Lien** : [Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/)

### 2. Google Cloud Platform (GCP)
*   **Offre** : Instance `e2-micro` gratuite à vie (dans certaines régions comme us-west1).
*   **Avantages** : Très stable.
*   **Lien** : [GCP Free Tier](https://cloud.google.com/free)

### 3. PythonAnywhere (Pour le Dashboard uniquement)
*   **Offre** : Un compte gratuit permet d'héberger une application web Python.
*   **Note** : Ne permet pas de faire tourner Selenium (le bot) sur le plan gratuit, mais peut afficher vos données.

### 4. Render / Railway
*   **Offre** : Plans gratuits avec des limites d'heures par mois.
*   **Usage** : Bien pour tester le dashboard en ligne.

---

## 🛠️ Étapes pour déployer sur un VPS (Oracle/GCP)

1.  **Connectez-vous en SSH** à votre serveur.
2.  **Installez les dépendances système** :
    ```bash
    sudo apt update
    sudo apt install -y python3-pip google-chrome-stable
    ```
3.  **Clonez votre dépôt** et installez les requirements.
4.  **Lancez le bot en arrière-plan** avec `screen` ou `tmux` :
    ```bash
    screen -S jetx_bot
    python3 jetx_betpawa_bot.py
    ```
    (Appuyez sur `Ctrl+A` puis `D` pour quitter l'écran sans arrêter le bot).
5.  **Lancez le dashboard** :
    ```bash
    streamlit run dashboard.py --server.port 80
    ```

---

## 🚀 Déploiement sur Render (Spécifique)

Si vous utilisez Render comme sur votre capture d'écran :

1.  **Fichier render.yaml** : J'ai ajouté ce fichier à la racine de votre dépôt. Render le détectera automatiquement maintenant.
2.  **Configuration** :
    *   Sur le tableau de bord Render, cliquez sur **"New +"** puis **"Blueprint"**.
    *   Connectez votre dépôt GitHub.
    *   Render lira le fichier `render.yaml` et configurera tout (Installation de Chrome, Python, et lancement de Streamlit).
3.  **Note Importante** : Sur le plan gratuit de Render, l'application s'arrête après 15 minutes d'inactivité. Pour que le bot tourne 24h/24, il est préférable d'utiliser le plan "Starter" ou de rester sur **Oracle Cloud** (qui est 100% gratuit et ne s'arrête jamais).
