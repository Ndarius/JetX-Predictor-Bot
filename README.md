# JetX Predictor Pro (betpawa.bj)

Cet outil est une solution complète de surveillance et de prédiction pour le jeu JetX sur betpawa.bj. Il combine un bot d'extraction de données automatisé avec une interface web de visualisation en temps réel.

## 🌟 Fonctionnalités Clés
- **Connexion Automatisée** : Le bot gère automatiquement la connexion à votre compte betpawa pour accéder aux données en direct.
- **Analyse Historique & Temporelle** : Le bot prend en compte **l'intégralité des tours passés** et analyse les performances par **tranche horaire** pour affiner ses prédictions.
- **Prédictions Intelligentes** : Combine EMA (Moyenne Mobile Exponentielle), tendance court terme et statistiques horaires.
- **Interface Web Pro** : Dashboard Streamlit avec graphiques de tendance et statistiques par heure.
- **Gestion des Iframes** : Extraction robuste des données même lorsque le jeu est encapsulé.
- **Stockage SQLite** : Base de données locale pour un suivi historique complet et persistant.

## 🚀 Installation Rapide

1. **Cloner le dépôt** :
   ```bash
   git clone https://github.com/Ndarius/JetX-Predictor-Bot.git
   cd JetX-Predictor-Bot
   ```

2. **Installer les dépendances** :
   ```bash
   pip install -r requirements.txt
   ```

3. **Configurer vos identifiants** :
   Ouvrez `config.yaml` et vérifiez vos informations dans la section `auth` :
   ```yaml
   auth:
     phone: "0162448761"
     pin: "2006"
   ```

## 🛠️ Utilisation

L'outil fonctionne en deux parties :

### 1. Lancer le Bot (Collecte & Prédiction)
Le bot doit tourner en arrière-plan pour collecter les données et générer les prédictions.
```bash
python jetx_betpawa_bot.py
```

### 2. Lancer l'Interface Web (Visuel)
Ouvrez un nouveau terminal et lancez le dashboard pour voir les prédictions graphiquement.
```bash
streamlit run dashboard.py
```
L'interface sera accessible sur `http://localhost:8501`.

## 📊 Logique de Prédiction Avancée
Le bot utilise une `StatisticalStrategy` améliorée :
- **Historique Global** : Analyse de tous les tours enregistrés dans la base de données.
- **Pondération Exponentielle (EMA)** : Les tours les plus récents ont un impact plus important sur la prédiction (alpha=0.1).
- **Facteur de Tendance** : Ajustement dynamique basé sur la comparaison entre la performance court terme (10 derniers tours) et long terme.
- **Score de Confiance** : Calculé en fonction de la volatilité actuelle du marché.

## 🧪 Test et Hébergement
Consultez le fichier [TEST_AND_HOST.md](./TEST_AND_HOST.md) pour savoir comment tester l'outil et l'héberger gratuitement sur le Cloud.

## ⚠️ Avertissement
Cet outil est destiné à des fins d'analyse statistique uniquement. Le jeu JetX utilise un générateur de nombres aléatoires (RNG). Aucune prédiction n'est garantie à 100%. Jouez de manière responsable.
