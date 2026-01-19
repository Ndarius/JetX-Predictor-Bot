import datetime
import numpy as np
import pandas as pd
import logging
import os
import sys
import yaml
import psycopg2
import time
from psycopg2.extras import RealDictCursor

# Ajouter le répertoire courant au chemin de recherche Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from strategies import StatisticalStrategy, MartingaleStrategy

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

class JetXBetpawaBot:
    def __init__(self, config_path=None):
        if config_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(base_dir, "config.yaml")
        
        # Initialisation des variables AVANT le chargement du stockage
        self.full_history = []
        self.df_full = pd.DataFrame()
        self.current_prediction = {"lower": None, "upper": None, "confidence": 0, "next": None}
        
        self.load_config(config_path)
        self.setup_storage()
        self.setup_selenium()

    def load_config(self, path):
        with open(path, 'r') as f:
            self.config = yaml.safe_load(f)
        self.url = self.config.get('url')
        self.margin_factor = self.config.get('margin_factor', 1.5)
        self.selectors = self.config.get('selectors', {})
        self.auth = self.config.get('auth', {})
        
        strat_name = self.config.get('strategy', 'statistical')
        if strat_name == 'martingale':
            self.strategy = MartingaleStrategy()
        else:
            self.strategy = StatisticalStrategy(margin_factor=self.margin_factor)

    def get_db_connection(self):
        # Prioritize DATABASE_URL if provided by Koyeb/Neon
        db_url = os.environ.get('DATABASE_URL')
        if db_url:
            if ("neon.tech" in db_url or "koyeb.app" in db_url) and "options=endpoint%3D" not in db_url:
                separator = "&" if "?" in db_url else "?"
                host = db_url.split("@")[1].split("/")[0]
                endpoint_id = host.split(".")[0]
                db_url += f"{separator}sslmode=require&options=endpoint%3D{endpoint_id}"
            return psycopg2.connect(db_url)

        host = os.environ.get('DATABASE_HOST', '')
        user = os.environ.get('DATABASE_USER', '')
        password = os.environ.get('DATABASE_PASSWORD', '')
        dbname = os.environ.get('DATABASE_NAME', '')
        port = os.environ.get('DATABASE_PORT', '5432')
        endpoint_id = host.split('.')[0] if host else ''
        
        # Direct parameters connection with explicit SSL
        return psycopg2.connect(
            host=host,
            user=user,
            password=password,
            database=dbname,
            port=port,
            sslmode='require',
            options=f"-c endpoint={endpoint_id}"
        )

    def setup_storage(self):
        logging.info("Connexion à PostgreSQL...")
        try:
            conn = self.get_db_connection()
            cur = conn.cursor()
            cur.execute('''
                CREATE TABLE IF NOT EXISTS jetx_logs (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP,
                    multiplier REAL,
                    type TEXT,
                    prediction REAL
                )
            ''')
            conn.commit()
            
            # Charger l'historique existant
            cur.execute("SELECT multiplier FROM jetx_logs WHERE type='result' ORDER BY timestamp ASC")
            rows = cur.fetchall()
            if rows:
                self.full_history = [row[0] for row in rows]
                self.df_full = pd.DataFrame(rows, columns=['multiplier'])
            
            cur.close()
            conn.close()
            logging.info(f"PostgreSQL prêt. Historique : {len(self.full_history)} tours.")
        except Exception as e:
            logging.error(f"Erreur PostgreSQL : {e}")
            raise e

    def setup_selenium(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1280,720")
        
        # Optimisations agressives pour Koyeb (RAM limitée)
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--disable-dev-tools")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--no-default-browser-check")
        chrome_options.add_argument("--memory-pressure-off")
        chrome_options.add_argument("--blink-settings=imagesEnabled=false")
        chrome_options.add_argument("--disable-background-networking")
        chrome_options.add_argument("--disable-sync")
        chrome_options.add_argument("--disable-translate")
        chrome_options.add_argument("--metrics-recording-only")
        chrome_options.add_argument("--safebrowsing-disable-auto-update")
        
        # Forcer le binaire Chromium pour Koyeb
        chrome_bin = os.environ.get("GOOGLE_CHROME_BIN", "/usr/bin/chromium")
        if os.path.exists(chrome_bin):
            chrome_options.binary_location = chrome_bin
            logging.info(f"Utilisation du binaire Chrome : {chrome_bin}")
        
        try:
            # Tenter de démarrer avec le driver spécifié
            driver_path = os.environ.get("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")
            if os.path.exists(driver_path):
                service = ChromeService(executable_path=driver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                logging.info(f"Chrome démarré avec le driver : {driver_path}")
            else:
                self.driver = webdriver.Chrome(options=chrome_options)
                logging.info("Chrome démarré avec le driver par défaut.")
        except Exception as e:
            logging.warning(f"Échec driver système, tentative avec WebDriver Manager : {e}")
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                driver_path = ChromeDriverManager().install()
                service = ChromeService(executable_path=driver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                logging.info("Chrome démarré avec WebDriver Manager.")
            except Exception as e2:
                logging.error(f"Échec critique Selenium : {e2}")
                raise e2
            
        self.driver.set_page_load_timeout(120)
        self.wait = WebDriverWait(self.driver, 60)

    def login(self):
        logging.info(f"Connexion à {self.url}")
        try:
            self.driver.get(self.url)
            time.sleep(15) # Augmenté pour Koyeb
            
            if "Deposit" in self.driver.page_source or "Déposer" in self.driver.page_source:
                logging.info("Déjà connecté.")
                return True
            
            login_trigger = self.selectors['login']['login_trigger']
            self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, login_trigger))).click()
            time.sleep(5)
            
            self.driver.find_element(By.CSS_SELECTOR, self.selectors['login']['phone_input']).send_keys(self.auth['phone'])
            self.driver.find_element(By.CSS_SELECTOR, self.selectors['login']['pin_input']).send_keys(self.auth['pin'])
            self.driver.find_element(By.CSS_SELECTOR, self.selectors['login']['submit_button']).click()
            
            time.sleep(15) # Attente du chargement après login
            return True
        except Exception as e:
            logging.error(f"Erreur login : {e}")
            # On tente quand même de continuer si on voit des éléments du jeu
            if "multiplier" in self.driver.page_source.lower():
                return True
            return False

    def log_data(self, multiplier, data_type="live", prediction=None):
        try:
            conn = self.get_db_connection()
            cur = conn.cursor()
            now = datetime.datetime.now()
            cur.execute('INSERT INTO jetx_logs (timestamp, multiplier, type, prediction) VALUES (%s, %s, %s, %s)', 
                               (now, multiplier, data_type, prediction))
            conn.commit()
            cur.close()
            conn.close()
            return now
        except Exception as e:
            logging.error(f"Erreur log_data : {e}")

    def extract_multiplier(self):
        try:
            for selector in self.selectors.get('multiplier', []):
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for el in elements:
                    text = el.text.replace('x', '').strip()
                    if text and text.replace('.', '').isdigit():
                        return float(text)
            return None
        except: return None

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
        if not self.login(): 
            logging.error("Échec du login. Tentative de surveillance quand même...")
        
        logging.info("Surveillance active...")
        try:
            last_val = None
            while True:
                try:
                    visual_history = self.extract_history()
                    if visual_history and (not self.full_history or visual_history[-1] != self.full_history[-1]):
                        new_result = visual_history[-1]
                        self.full_history.append(new_result)
                        
                        new_row = pd.DataFrame([{'multiplier': new_result}])
                        self.df_full = pd.concat([self.df_full, new_row], ignore_index=True)
                        
                        lower, upper, conf, next_p = self.strategy.predict(self.full_history, self.df_full)
                        self.current_prediction = {"lower": lower, "upper": upper, "confidence": conf, "next": next_p}
                        
                        ts = self.log_data(new_result, "result", next_p)
                        logging.info(f"[{ts}] TOUR : {new_result}x | PROCHAIN : {next_p:.2f}x")
                    
                    current_val = self.extract_multiplier()
                    if current_val is not None and current_val != last_val:
                        last_val = current_val
                        if self.current_prediction['upper'] and current_val >= self.current_prediction['upper']:
                            logging.info(f"SIGNAL: CASH OUT! {current_val}x")
                except Exception as e:
                    logging.warning(f"Erreur mineure dans la boucle : {e}")
                    if "session" in str(e).lower() or "disconnected" in str(e).lower():
                        raise e
                time.sleep(2) # Augmenté pour économiser le CPU sur Koyeb
        finally:
            if hasattr(self, 'driver'):
                try: self.driver.quit()
                except: pass

if __name__ == "__main__":
    while True:
        try:
            bot = JetXBetpawaBot()
            bot.run()
        except Exception as e:
            logging.error(f"Crash : {e}")
            time.sleep(20)
