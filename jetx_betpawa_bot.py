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
        chrome_options.add_argument("--window-size=1920,1080") 
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        chrome_bin = os.environ.get("GOOGLE_CHROME_BIN", "/usr/bin/chromium")
        if os.path.exists(chrome_bin):
            chrome_options.binary_location = chrome_bin
        
        try:
            driver_path = os.environ.get("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")
            if os.path.exists(driver_path):
                service = ChromeService(executable_path=driver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                self.driver = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            logging.error(f"Échec Selenium : {e}")
            raise e
            
        self.driver.set_page_load_timeout(120)
        self.wait = WebDriverWait(self.driver, 30)

    def login(self):
        logging.info(f"Navigation vers {self.url}")
        try:
            self.driver.get(self.url)
            time.sleep(10)
            self.driver.save_screenshot("debug_betpawa_initial.png")
            
            # Vérifier si déjà connecté
            if any(word in self.driver.page_source for word in ["Deposit", "Balance", "Account", "Solde"]):
                logging.info("Déjà connecté.")
                return self.navigate_to_jetx()
            
            # 1. Aller à la page de login
            logging.info("Recherche du bouton LOGIN...")
            try:
                login_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/login')] | //button[contains(., 'LOGIN')] | //span[contains(., 'LOGIN')]")))
                login_btn.click()
                time.sleep(5)
                self.driver.save_screenshot("debug_betpawa_login_page.png")
            except:
                logging.info("Bouton login non trouvé, peut-être déjà sur la page.")

            # 2. Saisie des identifiants
            logging.info("Saisie des identifiants...")
            try:
                phone_field = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='phoneNumber'], input[type='tel']")))
                phone_field.clear()
                phone_field.send_keys(self.auth['phone'])
                
                pin_field = self.driver.find_element(By.CSS_SELECTOR, "input[name='pincode'], input[type='password']")
                pin_field.clear()
                pin_field.send_keys(self.auth['pin'])
                
                submit_btn = self.driver.find_element(By.XPATH, "//button[contains(., 'LOG IN')] | //input[@type='submit']")
                submit_btn.click()
                logging.info("Formulaire soumis.")
                time.sleep(10)
                self.driver.save_screenshot("debug_betpawa_after_login.png")
            except Exception as e:
                logging.error(f"Erreur saisie login : {e}")

            return self.navigate_to_jetx()
        except Exception as e:
            logging.error(f"Erreur critique login : {e}")
            return False

    def navigate_to_jetx(self):
        logging.info("Navigation vers Casino > JetX...")
        try:
            # 1. Cliquer sur l'onglet Casino
            try:
                casino_tab = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/casino')] | //span[contains(., 'CASINO')]")))
                casino_tab.click()
                logging.info("Onglet Casino cliqué.")
                time.sleep(5)
            except:
                logging.info("Onglet Casino non trouvé ou déjà actif.")

            # 2. Rechercher et cliquer sur JetX
            try:
                # On tente d'accéder directement via l'URL si possible, sinon on cherche le bouton
                if "gameId=jetx" not in self.driver.current_url:
                    self.driver.get("https://www.betpawa.bj/casino?gameId=jetx")
                    time.sleep(10)
                
                # Vérifier la présence de l'iframe du jeu
                self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
                logging.info("Iframe JetX détectée.")
                self.driver.save_screenshot("debug_betpawa_jetx_loaded.png")
                return True
            except Exception as e:
                logging.error(f"Erreur chargement JetX : {e}")
                # Si on voit "multiplier" dans la source, c'est que c'est bon
                return "multiplier" in self.driver.page_source.lower()
        except Exception as e:
            logging.error(f"Erreur navigation JetX : {e}")
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
            # Si le jeu est dans une iframe, il faut switcher
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
        if not self.login(): 
            logging.error("Échec du login/navigation. Tentative de surveillance...")
        
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
                    logging.warning(f"Erreur mineure : {e}")
                time.sleep(2)
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
