import time
import datetime
import numpy as np
import pandas as pd
import logging
import os
import yaml
import sqlite3
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
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
    def __init__(self, config_path="config.yaml"):
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
        
        # Détection automatique du binaire Chrome
        chrome_bin = os.environ.get("GOOGLE_CHROME_BIN") or sel_config.get('binary_location')
        
        # Chemins communs pour Chrome sur Linux
        common_chrome_paths = [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/local/bin/google-chrome"
        ]
        
        if not chrome_bin:
            for path in common_chrome_paths:
                if os.path.exists(path):
                    chrome_bin = path
                    break
        
        if chrome_bin:
            logging.info(f"Utilisation du binaire Chrome : {chrome_bin}")
            chrome_options.binary_location = chrome_bin
            
        if sel_config.get('headless', True):
            chrome_options.add_argument("--headless=new")
            
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        try:
            # Tentative directe d'abord (recommandé pour les environnements Docker/Koyeb)
            self.driver = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            logging.warning(f"Échec tentative directe, essai avec WebDriverManager : {e}")
            try:
                service = ChromeService(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            except Exception as e2:
                logging.error(f"Échec total de l'initialisation de Selenium : {e2}")
                raise e2
            
        self.wait = WebDriverWait(self.driver, sel_config.get('wait_timeout', 30))

    def login(self):
        logging.info("Tentative de connexion...")
        try:
            self.driver.get(self.url)
            time.sleep(5)
            if "Deposit" in self.driver.page_source:
                return True
            login_trigger = self.selectors['login']['login_trigger']
            self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, login_trigger))).click()
            time.sleep(2)
            self.driver.find_element(By.CSS_SELECTOR, self.selectors['login']['phone_input']).send_keys(self.auth['phone'])
            self.driver.find_element(By.CSS_SELECTOR, self.selectors['login']['pin_input']).send_keys(self.auth['pin'])
            self.driver.find_element(By.CSS_SELECTOR, self.selectors['login']['submit_button']).click()
            time.sleep(5)
            return True
        except Exception as e:
            logging.error(f"Erreur login : {e}")
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
            while True:
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
    bot = JetXBetpawaBot()
    bot.run()
