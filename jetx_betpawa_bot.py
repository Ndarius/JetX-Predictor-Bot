import time
import datetime
import numpy as np
import pandas as pd
import logging
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("jetx_bot.log"),
        logging.StreamHandler()
    ]
)

class JetXBetpawaBot:
    def __init__(self, url, margin_factor=1.5, history_size=50):
        self.url = url
        self.margin_factor = margin_factor
        self.history_size = history_size
        self.data_history = []
        self.csv_file = "jetx_data_log.csv"
        
        # Initialisation du fichier CSV s'il n'existe pas
        if not os.path.exists(self.csv_file):
            df = pd.DataFrame(columns=["timestamp", "multiplier", "type"])
            df.to_csv(self.csv_file, index=False)
        
        # Configuration Selenium
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        # chrome_options.add_argument("--headless") # Décommenter pour le déploiement sur serveur
        
        self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
        self.wait = WebDriverWait(self.driver, 20)

    def log_to_csv(self, multiplier, data_type="live"):
        """Enregistre les données avec l'heure exacte."""
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        new_data = pd.DataFrame([[now, multiplier, data_type]], columns=["timestamp", "multiplier", "type"])
        new_data.to_csv(self.csv_file, mode='a', header=False, index=False)
        return now

    def extract_multiplier(self):
        """Extrait le multiplicateur en temps réel sur betpawa.bj."""
        try:
            # Note: JetX est souvent dans une iframe sur les sites de casino
            # On tente de trouver l'élément du multiplicateur (sélecteurs communs pour JetX)
            selectors = [
                ".current-multiplier", 
                ".multiplier-value", 
                "div[class*='multiplier']",
                ".font-weight-bold.text-white" # Sélecteur potentiel dans l'iframe JetX
            ]
            
            for selector in selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for el in elements:
                    text = el.text.replace('x', '').strip()
                    if text and text.replace('.', '').isdigit():
                        return float(text)
            return None
        except Exception as e:
            logging.debug(f"Erreur d'extraction : {e}")
            return None

    def extract_history(self):
        """Extrait l'historique des derniers multiplicateurs."""
        try:
            # Sélecteurs pour la barre latérale d'historique
            history_elements = self.driver.find_elements(By.CSS_SELECTOR, ".history-item, .last-results span")
            history = []
            for el in history_elements[-self.history_size:]:
                try:
                    val = float(el.text.replace('x', '').strip())
                    history.append(val)
                except ValueError:
                    continue
            return history
        except Exception as e:
            logging.error(f"Erreur historique : {e}")
            return []

    def analyze_and_predict(self, history):
        if len(history) < 5:
            return None, None
        mean = np.mean(history)
        std_dev = np.std(history)
        lower_bound = max(1.0, mean - self.margin_factor * std_dev)
        upper_bound = mean + self.margin_factor * std_dev
        return lower_bound, upper_bound

    def run(self):
        logging.info(f"Connexion à {self.url}")
        self.driver.get(self.url)
        
        print("\n--- ATTENTION ---")
        print("Si le jeu est dans une iframe ou nécessite une connexion,")
        print("veuillez vous assurer que la page est bien chargée.")
        print("-----------------\n")

        try:
            last_val = None
            while True:
                # 1. Mise à jour de l'historique
                current_history = self.extract_history()
                if current_history:
                    self.data_history = current_history
                
                # 2. Analyse
                lower, upper = self.analyze_and_predict(self.data_history)
                
                # 3. Temps réel
                current_val = self.extract_multiplier()
                
                if current_val is not None and current_val != last_val:
                    timestamp = self.log_to_csv(current_val)
                    last_val = current_val
                    
                    if lower and upper:
                        if current_val >= upper:
                            logging.info(f"[{timestamp}] SIGNAL: CASH OUT! {current_val}x (Cible: {upper:.2f}x)")
                        else:
                            logging.info(f"[{timestamp}] En vol: {current_val}x | Cible: {upper:.2f}x")
                
                time.sleep(0.5) # Fréquence rapide pour ne rien rater
                
        except KeyboardInterrupt:
            logging.info("Arrêt par l'utilisateur.")
        finally:
            self.driver.quit()

if __name__ == "__main__":
    URL = "https://www.betpawa.bj/casino?gameId=jetx&filter=all"
    bot = JetXBetpawaBot(URL)
    # bot.run() # Décommenter pour lancer
    print("Script configuré pour betpawa.bj avec horodatage.")
    print("Les données sont enregistrées dans 'jetx_data_log.csv'.")
