import numpy as np
import pandas as pd
from datetime import datetime

class BaseStrategy:
    def predict(self, history, df_full=None):
        raise NotImplementedError

class StatisticalStrategy(BaseStrategy):
    def __init__(self, margin_factor=1.5):
        self.margin_factor = margin_factor

    def predict(self, history, df_full=None):
        """
        Analyse l'historique complet, la tendance récente et les statistiques horaires.
        """
        if len(history) < 5:
            return None, None, 0, None
            
        series = pd.Series(history)
        current_hour = datetime.now().hour
        
        # 1. Analyse globale & EMA
        global_mean = series.mean()
        global_std = series.std()
        ema = series.ewm(alpha=0.1).mean().iloc[-1]
        
        # 2. Analyse Horaires (si les données complètes sont fournies)
        hour_factor = 1.0
        if df_full is not None and not df_full.empty:
            try:
                df_full['timestamp'] = pd.to_datetime(df_full['timestamp'])
                df_full['hour'] = df_full['timestamp'].dt.hour
                
                # Moyenne spécifique à cette heure de la journée
                hour_data = df_full[df_full['hour'] == current_hour]
                if len(hour_data) >= 10:
                    hour_mean = hour_data['multiplier'].mean()
                    hour_factor = hour_mean / global_mean if global_mean > 0 else 1.0
            except:
                pass

        # 3. Analyse de tendance court terme
        recent_window = min(10, len(history))
        recent_mean = series.tail(recent_window).mean()
        trend_factor = recent_mean / global_mean if global_mean > 0 else 1
        
        # 4. Calcul de la prédiction finale
        # On combine EMA (70%), Tendance (20%) et Facteur Horaire (10%)
        next_pred = (ema * 0.7) + (global_mean * trend_factor * 0.2) + (global_mean * hour_factor * 0.1)
        
        # 5. Bornes et Confiance
        lower_bound = max(1.0, next_pred - (self.margin_factor * global_std * 0.4))
        upper_bound = next_pred + (self.margin_factor * global_std * 0.4)
        
        volatility = global_std / global_mean if global_mean > 0 else 1
        confidence = min(95, max(10, 100 - (volatility * 45)))
        
        return lower_bound, upper_bound, confidence, next_pred

class MartingaleStrategy(BaseStrategy):
    def predict(self, history, df_full=None):
        if not history:
            return 1.2, 2.0, 50, 1.5
        recent_lows = sum(1 for x in history[-5:] if x < 1.5)
        if recent_lows >= 3:
            return 1.1, 1.4, 75, 1.25
        else:
            return 1.5, 3.0, 40, 2.1
