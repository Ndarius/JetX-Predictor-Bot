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
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
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
        
        self.full_history = []
        self.df_full = pd.DataFrame()
        self.current_prediction = {"lower": None, "upper": None, "confidence": 0, "next": None}
        
        self.load_config(config_path)
        self.setup_storage()
        self.setup_selenium()

    def load_config(self, path):
        with open(path, 'r') as f:
            self.config = yaml.safe_load(f)
        self.url = "https://www.betpawa.bj/login"
        self.margin_factor = self.config.get('margin_factor', 1.5)
        self.selectors = self.config.get('selectors', {})
        self.auth = self.config.get('auth', {})
        
        strat_name = self.config.get('strategy', 'statistical')
        if strat_name == 'martingale':
            self.strategy = MartingaleStrategy()
        else:
            self.strategy = StatisticalStrategy(margin_factor=self.margin_factor)

    def get_db_connection(self):
        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            return None
        try:
            if "sslmode=" not in db_url:
                separator = "&" if "?" in db_url else "?"
                db_url += f"{separator}sslmode=require"
            return psycopg2.connect(db_url)
        except Exception as e:
            logging.warning(f"Impossible de se connecter à la DB : {e}")
            return None

    def setup_storage(self):
        logging.info("Initialisation du stockage...")
        conn = self.get_db_connection()
        if conn:
            try:
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
                cur.execute("SELECT multiplier FROM jetx_logs WHERE type='result' ORDER BY timestamp ASC")
                rows = cur.fetchall()
                if rows:
                    self.full_history = [row[0] for row in rows]
                    self.df_full = pd.DataFrame(rows, columns=['multiplier'])
                cur.close()
                conn.close()
                logging.info(f"PostgreSQL prêt. Historique : {len(self.full_history)} tours.")
            except Exception as e:
                logging.error(f"Erreur lors de la configuration DB : {e}")
        else:
            logging.warning("Mode sans base de données activé.")

    def setup_selenium(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        chrome_bin = os.environ.get("GOOGLE_CHROME_BIN", "/usr/bin/chromium")
        driver_path = os.environ.get("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")
        
        if os.path.exists(chrome_bin):
            chrome_options.binary_location = chrome_bin
        
        try:
            service = ChromeService(executable_path=driver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logging.info("Chrome démarré avec succès.")
        except Exception as e:
            logging.error(f"Échec Selenium : {e}")
            try:
                self.driver = webdriver.Chrome(options=chrome_options)
            except Exception as e2:
                logging.error(f"Échec total Selenium : {e2}")
                raise e2
            
        self.driver.set_page_load_timeout(60)
        self.wait = WebDriverWait(self.driver, 30)

    def human_type(self, element, text):
        """Simule une saisie humaine touche par touche"""
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.5)
            element.click()
            time.sleep(0.5)
            element.clear()
            for char in text:
                element.send_keys(char)
                time.sleep(0.1)
        except Exception as e:
            logging.warning(f"Erreur saisie humaine, fallback JS: {e}")
            self.driver.execute_script(f"arguments[0].value = '{text}';", element)

    def human_click(self, element):
        """Simule un mouvement de souris et un clic physique avec sécurité"""
        try:
            # Faire défiler jusqu'à l'élément pour éviter 'out of bounds'
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.8)
            
            actions = ActionChains(self.driver)
            actions.move_to_element(element).pause(0.5).click().perform()
        except Exception as e:
            logging.warning(f"Erreur clic physique, fallback JS: {e}")
            self.driver.execute_script("arguments[0].click();", element)

    def login(self):
        logging.info(f"Navigation directe vers la page de login : {self.url}")
        try:
            self.driver.get(self.url)
            time.sleep(12)
            self.driver.save_screenshot("debug_betpawa_login_page.png")
            
            if any(word in self.driver.page_source for word in ["Deposit", "Balance", "Account"]):
                logging.info("Déjà connecté.")
                return self.navigate_to_jetx()
            
            # --- LOGIQUE DE CONNEXION SÉCURISÉE ---
            logging.info("Tentative de connexion...")
            
            if len(self.driver.find_elements(By.TAG_NAME, "iframe")) > 0:
                self.driver.switch_to.frame(0)

            # Recherche du champ téléphone
            phone_field = None
            for by, sel in [(By.NAME, "phoneNumber"), (By.CSS_SELECTOR, "input[type='tel']"), (By.XPATH, "//input[contains(@name, 'phone')]")]:
                try:
                    phone_field = self.wait.until(EC.presence_of_element_located((by, sel)))
                    if phone_field: break
                except: continue
            
            if phone_field:
                logging.info("Saisie du téléphone...")
                self.human_type(phone_field, self.auth['phone'])
            
            # Recherche du champ PIN
            pin_field = None
            for by, sel in [(By.NAME, "pincode"), (By.CSS_SELECTOR, "input[type='password']"), (By.XPATH, "//input[contains(@name, 'pin')]")]:
                try:
                    pin_field = self.driver.find_element(by, sel)
                    if pin_field: break
                except: continue
            
            if pin_field:
                logging.info("Saisie du PIN...")
                self.human_type(pin_field, self.auth['pin'])

            # Clic sur le bouton de validation
            try:
                submit_btn = self.driver.find_element(By.XPATH, "//button[contains(., 'LOG IN')] | //input[@type='submit'] | //button[@type='submit']")
                logging.info("Clic sur le bouton de login...")
                self.human_click(submit_btn)
            except:
                logging.error("Bouton submit non trouvé, validation via Enter...")
                if pin_field: pin_field.send_keys(Keys.ENTER)

            self.driver.switch_to.default_content()
            time.sleep(12)
            self.driver.save_screenshot("debug_betpawa_after_login.png")

            return self.navigate_to_jetx()
        except Exception as e:
            logging.error(f"Erreur critique login : {e}")
            self.driver.switch_to.default_content()
            return False

    def navigate_to_jetx(self):
        logging.info("Accès JetX...")
        try:
            self.driver.get("https://www.betpawa.bj/casino?gameId=jetx")
            time.sleep(15)
            self.driver.save_screenshot("debug_betpawa_jetx_loaded.png")
            return True
        except:
            return False

    def log_data(self, multiplier, data_type="live", prediction=None):
        conn = self.get_db_connection()
        if not conn: return datetime.datetime.now()
        try:
            cur = conn.cursor()
            now = datetime.datetime.now()
            cur.execute('INSERT INTO jetx_logs (timestamp, multiplier, type, prediction) VALUES (%s, %s, %s, %s)', 
                               (now, multiplier, data_type, prediction))
            conn.commit()
            cur.close()
            conn.close()
            return now
        except: return datetime.datetime.now()

    def extract_multiplier(self):
        try:
            if len(self.driver.find_elements(By.TAG_NAME, "iframe")) > 0:
                self.driver.switch_to.frame(0)
            
            val = None
            for selector in self.selectors.get('multiplier', []):
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for el in elements:
                    text = el.text.replace('x', '').strip()
                    if text and text.replace('.', '').isdigit():
                        val = float(text)
                        break
                if val: break
            
            self.driver.switch_to.default_content()
            return val
        except: 
            self.driver.switch_to.default_content()
            return None

    def extract_history(self):
        try:
            if len(self.driver.find_elements(By.TAG_NAME, "iframe")) > 0:
                self.driver.switch_to.frame(0)
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
            self.driver.switch_to.default_content()
            return history
        except: 
            self.driver.switch_to.default_content()
            return []

    def run(self):
        self.login()
        logging.info("Surveillance active...")
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
                if current_val is not None:
                    if self.current_prediction['upper'] and current_val >= self.current_prediction['upper']:
                        logging.info(f"SIGNAL: CASH OUT! {current_val}x")
            except Exception as e:
                logging.warning(f"Boucle : {e}")
            time.sleep(3)

if __name__ == "__main__":
    while True:
        try:
            bot = JetXBetpawaBot()
            bot.run()
        except Exception as e:
            logging.error(f"Crash : {e}")
            time.sleep(20)
