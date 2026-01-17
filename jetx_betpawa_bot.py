import time
import datetime
import numpy as np
import pandas as pd
import logging
import os
import sys
import yaml
import sqlite3

# Ajouter le répertoire courant au chemin de recherche Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# Selenium configuration for Koyeb
from strategies import StatisticalStrategy, MartingaleStrategy

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
    def __init__(self, config_path=None):
        if config_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(base_dir, "config.yaml")
        self.load_config(config_path)
        self.setup_storage()
        self.setup_selenium()
        self.full_history = []
        self.df_full = pd.DataFrame()
        self.current_prediction = {"lower": None, "upper": None, "confidence": 0, "next": None}

    def load_config(self, path):
        with open(path, 'r') as f:
            self.config = yaml.safe_load(f)
        self.url = self.config.get('url')
        self.margin_factor = self.config.get('margin_factor', 1.5)
        self.history_size = self.config.get('history_size', 2000)
        self.db_file = self.config.get('db_file', 'jetx_data.db')
        self.selectors = self.config.get('selectors', {})
        self.auth = self.config.get('auth', {})
        
        strat_name = self.config.get('strategy', 'statistical')
        if strat_name == 'martingale':
            self.strategy = MartingaleStrategy()
        else:
            self.strategy = StatisticalStrategy(margin_factor=self.margin_factor)

    def setup_storage(self):
        # Sur Koyeb/Heroku, le système de fichiers est souvent en lecture seule.
        # On utilise /tmp pour la base de données SQLite.
        # Sur Koyeb, on utilise le volume monté sur /bot pour la persistance.
        if os.path.exists("/bot"):
            self.db_file = os.path.join("/bot", "jetx_data.db")
            logging.info(f"Volume Koyeb détecté, utilisation de : {self.db_file}")
        elif os.environ.get('KOYEB_APP_ID') or os.environ.get('PORT'):
            self.db_file = os.path.join("/tmp", "jetx_data.db")
            logging.info(f"Environnement serveur détecté (sans volume), utilisation de : {self.db_file}")
        elif not os.path.isabs(self.db_file):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.db_file = os.path.join(base_dir, self.db_file)
            
        self.conn = sqlite3.connect(self.db_file, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS jetx_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                multiplier REAL,
                type TEXT,
                prediction REAL
            )
        ''')
        self.conn.commit()
        
        try:
            self.df_full = pd.read_sql_query("SELECT * FROM jetx_logs WHERE type='result'", self.conn)
            self.full_history = self.df_full['multiplier'].tolist()
            logging.info(f"Historique chargé : {len(self.full_history)} tours récupérés.")
        except:
            logging.warning("Nouvelle base de données initialisée.")

    def setup_selenium(self):
        chrome_options = Options()
        sel_config = self.config.get('selenium', {})
        
        # Détection automatique du binaire Chrome (Buildpacks Heroku/Koyeb)
        chrome_bin = os.environ.get("GOOGLE_CHROME_BIN") or sel_config.get('binary_location')
        chromedriver_path = os.environ.get("CHROMEDRIVER_PATH")
        
        # Chemins par défaut courants sur Koyeb/Heroku avec buildpacks
        default_chrome_paths = [
            "/app/.apt/usr/bin/google-chrome",
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable"
        ]
        default_driver_paths = [
            "/app/.chromedriver/bin/chromedriver",
            "/usr/local/bin/chromedriver",
            "/usr/bin/chromedriver"
        ]

        if not chrome_bin:
            for path in default_chrome_paths:
                if os.path.exists(path):
                    chrome_bin = path
                    break
        
        if not chromedriver_path:
            for path in default_driver_paths:
                if os.path.exists(path):
                    chromedriver_path = path
                    break

        if chrome_bin:
            logging.info(f"Utilisation du binaire Chrome : {chrome_bin}")
            chrome_options.binary_location = chrome_bin
        else:
            logging.warning("Binaire Chrome non trouvé explicitement, Selenium tentera la détection automatique.")
            
        if sel_config.get('headless', True):
            chrome_options.add_argument("--headless=new")
            
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--proxy-server='direct://'")
        chrome_options.add_argument("--proxy-bypass-list=*")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--remote-debugging-port=9222")
        
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            from webdriver_manager.core.os_manager import ChromeType
            
            if chromedriver_path and os.path.exists(chromedriver_path):
                logging.info(f"Utilisation du ChromeDriver : {chromedriver_path}")
                service = ChromeService(executable_path=chromedriver_path)
            elif os.path.exists("/usr/bin/chromedriver"):
                logging.info("Utilisation du ChromeDriver système : /usr/bin/chromedriver")
                service = ChromeService(executable_path="/usr/bin/chromedriver")
            else:
                logging.info("Installation automatique du ChromeDriver via webdriver-manager...")
                driver_path = ChromeDriverManager(chrome_type=ChromeType.GOOGLE).install()
                service = ChromeService(executable_path=driver_path)
            
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logging.info("Navigateur Chrome démarré avec succès.")
        except Exception as e:
            logging.error(f"Échec de l'initialisation de Selenium : {e}")
            # Tentative de secours ultime
            try:
                logging.info("Tentative de secours sans service explicite...")
                self.driver = webdriver.Chrome(options=chrome_options)
            except Exception as e2:
                logging.error(f"Échec de la tentative de secours : {e2}")
                raise e2
            
        self.wait = WebDriverWait(self.driver, sel_config.get('wait_timeout', 30))

    def login(self):
        logging.info(f"Tentative de connexion à : {self.url}")
        try:
            self.driver.get(self.url)
            time.sleep(10) # Augmenté pour laisser le temps au chargement
            
            # Vérification si déjà connecté
            if "Deposit" in self.driver.page_source or "Déposer" in self.driver.page_source:
                logging.info("Déjà connecté (bouton Deposit trouvé).")
                return True
            
            logging.info("Recherche du bouton de connexion...")
            login_trigger = self.selectors['login']['login_trigger']
            try:
                self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, login_trigger))).click()
                logging.info("Bouton de connexion cliqué.")
            except Exception as e:
                logging.warning(f"Bouton de connexion non trouvé ou non cliquable : {e}")
                # On continue quand même, peut-être que le formulaire est déjà visible
            
            time.sleep(3)
            logging.info("Remplissage du formulaire...")
            self.driver.find_element(By.CSS_SELECTOR, self.selectors['login']['phone_input']).send_keys(self.auth['phone'])
            self.driver.find_element(By.CSS_SELECTOR, self.selectors['login']['pin_input']).send_keys(self.auth['pin'])
            self.driver.find_element(By.CSS_SELECTOR, self.selectors['login']['submit_button']).click()
            
            logging.info("Formulaire soumis, attente de redirection...")
            time.sleep(10)
            
            if "Deposit" in self.driver.page_source or "Déposer" in self.driver.page_source:
                logging.info("Connexion réussie !")
                return True
            else:
                logging.warning("Connexion incertaine (bouton Deposit non trouvé après login).")
                # On retourne True quand même pour tenter la suite
                return True
        except Exception as e:
            logging.error(f"Erreur critique lors du login : {e}")
            # On prend une capture d'écran pour le debug si possible (sauvegardée localement dans le conteneur)
            try: self.driver.save_screenshot("login_error.png")
            except: pass
            return False

    def log_data(self, multiplier, data_type="live", prediction=None):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        self.cursor.execute('INSERT INTO jetx_logs (timestamp, multiplier, type, prediction) VALUES (?, ?, ?, ?)', 
                           (now, multiplier, data_type, prediction))
        self.conn.commit()
        return now

    def extract_multiplier(self):
        try:
            for selector in self.selectors.get('multiplier', []):
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for el in elements:
                    text = el.text.replace('x', '').strip()
                    if text and text.replace('.', '').isdigit():
                        return float(text)
            return None
        except:
            return None

    def extract_history(self):
        try:
            history = []
            for selector in self.selectors.get('history', []):
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    for el in elements:
                        try:
                            val = float(el.text.replace('x', '').strip())
                            history.append(val)
                        except: continue
                    if history: break
            return history
        except: return []

    def run(self):
        if not self.login(): return
        logging.info("Surveillance active...")
        try:
            last_val = None
            last_heartbeat = time.time()
            logging.info("Connexion réussie, début de la surveillance...")
            while True:
                # Heartbeat toutes les 60 secondes pour confirmer que le bot tourne
                if time.time() - last_heartbeat > 60:
                    logging.info("Bot en cours d'exécution... Recherche de nouvelles données JetX.")
                    last_heartbeat = time.time()

                visual_history = self.extract_history()
                if visual_history and (not self.full_history or visual_history[-1] != self.full_history[-1]):
                    new_result = visual_history[-1]
                    self.full_history.append(new_result)
                    
                    new_row = pd.DataFrame([{'timestamp': datetime.datetime.now(), 'multiplier': new_result}])
                    self.df_full = pd.concat([self.df_full, new_row], ignore_index=True)
                    
                    lower, upper, conf, next_p = self.strategy.predict(self.full_history, self.df_full)
                    self.current_prediction = {"lower": lower, "upper": upper, "confidence": conf, "next": next_p}
                    
                    timestamp = self.log_data(new_result, "result", next_p)
                    logging.info(f"[{timestamp}] TOUR : {new_result}x | PROCHAIN : {next_p:.2f}x")
                
                current_val = self.extract_multiplier()
                if current_val is not None and current_val != last_val:
                    last_val = current_val
                    if self.current_prediction['upper'] and current_val >= self.current_prediction['upper']:
                        logging.info(f"SIGNAL: CASH OUT! {current_val}x")
                time.sleep(0.3)
        except KeyboardInterrupt:
            logging.info("Arrêt.")
        finally:
            if hasattr(self, 'driver'):
                self.driver.quit()

if __name__ == "__main__":
    print("--- BOT STARTUP ---", flush=True)
    while True:
        try:
            logging.info("Initialisation du bot...")
            bot = JetXBetpawaBot()
            bot.run()
        except Exception as e:
            print(f"CRITICAL ERROR: {e}", flush=True)
            logging.error(f"Erreur critique dans la boucle principale : {e}")
            time.sleep(10)
            # On ne quitte pas pour éviter le code 255, on boucle
            continue
