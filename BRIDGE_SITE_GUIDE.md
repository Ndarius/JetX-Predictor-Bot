# 🚀 Guide du Site Pont (Dashboard JetX)

Pour garder votre bot stable sur le plan gratuit de Koyeb, nous avons désactivé l'interface visuelle sur l'instance principale. Voici comment déployer votre "Site Pont" pour voir les résultats en temps réel.

## Option 1 : Déploiement sur Streamlit Cloud (Gratuit & Recommandé)

C'est la méthode la plus simple et elle ne consomme aucune ressource sur votre bot.

1.  Connectez-vous sur [share.streamlit.io](https://share.streamlit.io/).
2.  Cliquez sur **"New app"**.
3.  Sélectionnez votre dépôt GitHub `Ndarius/JetX-Predictor-Bot`.
4.  Branche : `main`.
5.  Main file path : `dashboard.py`.
6.  **IMPORTANT** : Cliquez sur "Advanced settings" et ajoutez vos variables d'environnement (Secrets) :
    *   `DATABASE_URL` : (Votre chaîne de connexion Neon complète)
7.  Cliquez sur **Deploy**.

## Option 2 : Déploiement sur une 2ème instance Koyeb

Vous pouvez créer un deuxième service sur Koyeb qui ne fera tourner que l'interface.

1.  Créez un nouveau service sur Koyeb pointant sur le même dépôt.
2.  Dans les paramètres de déploiement, changez la commande de démarrage par :
    `streamlit run dashboard.py --server.port 8000 --server.address 0.0.0.0`
3.  Ajoutez la variable d'environnement `DATABASE_URL`.

---

### Pourquoi cette séparation ?
Le bot a besoin de beaucoup de RAM pour faire tourner Chrome. En déplaçant l'interface (Dashboard) sur un autre service, vous libérez 100% de la RAM de l'instance Koyeb pour le bot, ce qui évite les plantages `code 255`.
