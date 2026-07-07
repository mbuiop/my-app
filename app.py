# ============================================================
# ULTIMATE SIGNAL BOT V18 - QUANTUM PRO MAX ULTRA
# 5000X STRONGER ANALYSIS | FULL ADMIN PANEL WITH BUTTONS
# ============================================================

import requests
import numpy as np
import time
import json
import os
import sqlite3
from datetime import datetime, timedelta
import threading
import logging
from collections import deque
import hashlib
import re
import math
from scipy import stats
from scipy.signal import find_peaks, argrelextrema
from scipy.optimize import minimize
from scipy.fft import fft, ifft
from scipy.stats import linregress
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURATION
# ============================================================

BOT_TOKEN = "7780798170:AAHTDl295s15_RwhfhjGentSLZzye3keJP0"
CHANNEL_ID = "@davnold"
ADMIN_ID = 327855654

WALLET_ADDRESS = "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"
PRICE = "100 USDT"

INTERVAL = 300
MAX_SIGNALS = 5
MIN_CONFIDENCE = 60

# ============================================================
# DATABASE
# ============================================================

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('bot_data.db', check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.create_tables()
        logger.info("✅ Database initialized")
    
    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                joined_at TIMESTAMP,
                subscription_expire TIMESTAMP,
                is_active BOOLEAN DEFAULT 0,
                is_premium BOOLEAN DEFAULT 0,
                feedback_count INTEGER DEFAULT 0,
                positive_feedback INTEGER DEFAULT 0,
                negative_feedback INTEGER DEFAULT 0,
                total_profit DECIMAL DEFAULT 0,
                total_loss DECIMAL DEFAULT 0,
                win_rate DECIMAL DEFAULT 0,
                signals_received INTEGER DEFAULT 0
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                direction TEXT,
                entry REAL,
                tp1 REAL,
                tp2 REAL,
                tp3 REAL,
                sl REAL,
                confidence INTEGER,
                created_at TIMESTAMP,
                rsi REAL,
                macd REAL,
                ma20 REAL,
                ma50 REAL,
                ma200 REAL,
                vwap REAL,
                atr REAL,
                support1 REAL,
                support2 REAL,
                resistance1 REAL,
                resistance2 REAL,
                score REAL,
                quality_score REAL,
                reasons TEXT,
                feedback TEXT DEFAULT '',
                feedback_user INTEGER DEFAULT 0,
                sent_to_channel BOOLEAN DEFAULT 0,
                profit_percent DECIMAL DEFAULT 0,
                market_phase TEXT,
                volatility REAL,
                trend_strength REAL,
                momentum_score REAL,
                predicted_price REAL
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                payment_hash TEXT UNIQUE,
                amount TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP,
                confirmed_at TIMESTAMP,
                expire_at TIMESTAMP
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id INTEGER,
                user_id INTEGER,
                feedback TEXT,
                created_at TIMESTAMP,
                profit_amount DECIMAL DEFAULT 0
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT,
                details TEXT,
                created_at TIMESTAMP
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        defaults = [
            ('signal_enabled', '1'),
            ('wallet', WALLET_ADDRESS),
            ('price', PRICE),
            ('min_confidence', '60'),
            ('max_signals', '5'),
            ('payment_enabled', '1'),
            ('min_profit_target', '30'),
            ('risk_reward_ratio', '3.0'),
            ('aggressive_mode', '0'),
            ('ultra_analysis', '1'),
            ('learning_enabled', '1')
        ]
        
        for key, value in defaults:
            self.cursor.execute('INSERT OR IGNORE INTO settings VALUES (?, ?)', (key, value))
        
        self.conn.commit()
    
    def get_setting(self, key):
        self.cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        r = self.cursor.fetchone()
        return r[0] if r else None
    
    def update_setting(self, key, value):
        self.cursor.execute('UPDATE settings SET value = ? WHERE key = ?', (value, key))
        self.conn.commit()
        self.add_admin_log(f"Setting changed: {key} = {value}")
    
    def get_all_settings(self):
        self.cursor.execute('SELECT key, value FROM settings')
        return {row['key']: row['value'] for row in self.cursor.fetchall()}
    
    def add_user(self, user_id, username=None, first_name=None):
        self.cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, joined_at)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, first_name, datetime.now().isoformat()))
        self.conn.commit()
    
    def get_user(self, user_id):
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone()
    
    def save_signal(self, signal_data):
        self.cursor.execute('''
            INSERT INTO signals (
                symbol, direction, entry, tp1, tp2, tp3, sl, confidence,
                created_at, rsi, macd, ma20, ma50, ma200,
                vwap, atr, support1, support2, resistance1, resistance2,
                score, quality_score, reasons, profit_percent,
                market_phase, volatility, trend_strength, momentum_score,
                predicted_price
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            signal_data['symbol'],
            signal_data['signal'],
            signal_data['entry'],
            signal_data.get('tp1', 0),
            signal_data.get('tp2', 0),
            signal_data.get('tp3', 0),
            signal_data.get('sl', 0),
            signal_data['confidence'],
            datetime.now().isoformat(),
            signal_data.get('rsi', 0),
            signal_data.get('macd', 0),
            signal_data.get('ma20', 0),
            signal_data.get('ma50', 0),
            signal_data.get('ma200', 0),
            signal_data.get('vwap', 0),
            signal_data.get('atr', 0),
            signal_data.get('support1', 0),
            signal_data.get('support2', 0),
            signal_data.get('resistance1', 0),
            signal_data.get('resistance2', 0),
            signal_data.get('score', 0),
            signal_data.get('quality_score', 0),
            '|'.join(signal_data.get('reasons', [])),
            signal_data.get('profit_percent', 0),
            signal_data.get('market_phase', 'neutral'),
            signal_data.get('volatility', 0),
            signal_data.get('trend_strength', 0),
            signal_data.get('momentum_score', 0),
            signal_data.get('predicted_price', 0)
        ))
        signal_id = self.cursor.lastrowid
        self.conn.commit()
        return signal_id
    
    def mark_signal_sent(self, signal_id):
        self.cursor.execute('UPDATE signals SET sent_to_channel = 1 WHERE id = ?', (signal_id,))
        self.conn.commit()
    
    def get_signal(self, signal_id):
        self.cursor.execute('SELECT * FROM signals WHERE id = ?', (signal_id,))
        return self.cursor.fetchone()
    
    def update_feedback(self, signal_id, feedback_type, user_id, profit_amount=0):
        self.cursor.execute('SELECT id FROM feedback_log WHERE signal_id = ? AND user_id = ?', (signal_id, user_id))
        if self.cursor.fetchone():
            return False, "شما قبلاً به این سیگنال بازخورد داده‌اید"
        
        self.cursor.execute('UPDATE signals SET feedback = ?, feedback_user = ? WHERE id = ?', 
                           (feedback_type, user_id, signal_id))
        
        if feedback_type == 'positive':
            self.cursor.execute('UPDATE users SET positive_feedback = positive_feedback + 1, feedback_count = feedback_count + 1, signals_received = signals_received + 1 WHERE user_id = ?', (user_id,))
            self.cursor.execute('UPDATE users SET total_profit = total_profit + ? WHERE user_id = ?', (profit_amount, user_id))
        else:
            self.cursor.execute('UPDATE users SET negative_feedback = negative_feedback + 1, feedback_count = feedback_count + 1 WHERE user_id = ?', (user_id,))
            self.cursor.execute('UPDATE users SET total_loss = total_loss + ? WHERE user_id = ?', (abs(profit_amount), user_id))
        
        self.cursor.execute('''
            UPDATE users SET win_rate = 
                ROUND(CAST(positive_feedback AS FLOAT) / NULLIF(feedback_count, 0) * 100, 2)
            WHERE user_id = ?
        ''', (user_id,))
        
        self.cursor.execute('INSERT INTO feedback_log (signal_id, user_id, feedback, created_at, profit_amount) VALUES (?, ?, ?, ?, ?)',
                           (signal_id, user_id, feedback_type, datetime.now().isoformat(), profit_amount))
        self.conn.commit()
        return True, "بازخورد ثبت شد"
    
    def add_payment(self, user_id, payment_hash):
        self.cursor.execute('INSERT INTO payments (user_id, payment_hash, amount, created_at) VALUES (?, ?, ?, ?)',
                           (user_id, payment_hash, PRICE, datetime.now().isoformat()))
        payment_id = self.cursor.lastrowid
        self.conn.commit()
        return payment_id
    
    def get_pending_payments(self):
        self.cursor.execute('SELECT id, user_id, payment_hash, amount, created_at FROM payments WHERE status = "pending" ORDER BY created_at ASC')
        return self.cursor.fetchall()
    
    def get_payment_by_hash(self, payment_hash):
        self.cursor.execute('SELECT * FROM payments WHERE payment_hash = ?', (payment_hash,))
        return self.cursor.fetchone()
    
    def confirm_payment(self, payment_id):
        self.cursor.execute('SELECT user_id FROM payments WHERE id = ? AND status = "pending"', (payment_id,))
        result = self.cursor.fetchone()
        if not result:
            return False, None
        
        user_id = result[0]
        expire_date = datetime.now() + timedelta(days=30)
        
        self.cursor.execute('UPDATE payments SET status = "confirmed", confirmed_at = ?, expire_at = ? WHERE id = ?',
                           (datetime.now().isoformat(), expire_date.isoformat(), payment_id))
        
        self.cursor.execute('UPDATE users SET subscription_expire = ?, is_active = 1, is_premium = 1 WHERE user_id = ?',
                           (expire_date.isoformat(), user_id))
        self.conn.commit()
        self.add_admin_log(f"Payment #{payment_id} confirmed for user {user_id}")
        return True, user_id
    
    def reject_payment(self, payment_id):
        self.cursor.execute('UPDATE payments SET status = "rejected" WHERE id = ? AND status = "pending"', (payment_id,))
        self.conn.commit()
        if self.cursor.rowcount > 0:
            self.add_admin_log(f"Payment #{payment_id} rejected")
            return True
        return False
    
    def add_admin_log(self, details):
        self.cursor.execute('INSERT INTO admin_logs (action, details, created_at) VALUES (?, ?, ?)',
                           ('admin_action', details, datetime.now().isoformat()))
        self.conn.commit()
    
    def get_stats(self):
        users = self.cursor.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        active = self.cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1').fetchone()[0]
        premium = self.cursor.execute('SELECT COUNT(*) FROM users WHERE is_premium = 1').fetchone()[0]
        signals = self.cursor.execute('SELECT COUNT(*) FROM signals').fetchone()[0]
        today = self.cursor.execute('SELECT COUNT(*) FROM signals WHERE DATE(created_at) = DATE("now")').fetchone()[0]
        pending = self.cursor.execute('SELECT COUNT(*) FROM payments WHERE status = "pending"').fetchone()[0]
        
        wins = self.cursor.execute('SELECT COUNT(*) FROM feedback_log WHERE feedback = "positive"').fetchone()[0]
        total_feedback = self.cursor.execute('SELECT COUNT(*) FROM feedback_log').fetchone()[0]
        win_rate = round((wins / total_feedback * 100) if total_feedback > 0 else 0, 2)
        
        avg_profit = self.cursor.execute('SELECT AVG(profit_amount) FROM feedback_log WHERE feedback = "positive"').fetchone()[0] or 0
        
        return {
            'users': users,
            'active': active,
            'premium': premium,
            'signals': signals,
            'today': today,
            'pending': pending,
            'win_rate': win_rate,
            'wins': wins,
            'avg_profit': round(avg_profit, 2)
        }

db = Database()

# ============================================================
# 5000X STRONGER INDICATORS WITH SCIPY
# ============================================================

def get_candles(symbol, limit=500, interval='5m'):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                'open': [float(x[1]) for x in data],
                'high': [float(x[2]) for x in data],
                'low': [float(x[3]) for x in data],
                'close': [float(x[4]) for x in data],
                'volume': [float(x[5]) for x in data],
                'timestamp': [x[0] for x in data]
            }
    except Exception as e:
        logger.error(f"Error fetching {symbol}: {e}")
    return None

class QuantumIndicators:
    """5000X Stronger Quantum Indicators with Scipy"""
    
    @staticmethod
    def calculate_rsi(prices, period=14):
        if len(prices) < period + 1:
            return 50.0
        prices = np.array(prices[-period-1:])
        deltas = np.diff(prices)
        gains = deltas[deltas > 0]
        losses = -deltas[deltas < 0]
        avg_gain = np.mean(gains) if len(gains) > 0 else 0
        avg_loss = np.mean(losses) if len(losses) > 0 else 0.0000001
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return round(rsi, 2)
    
    @staticmethod
    def calculate_macd(prices, fast=12, slow=26, signal=9):
        if len(prices) < slow:
            return 0, 0, 0
        prices = np.array(prices)
        fast_mult = 2.0 / (fast + 1)
        fast_ema = np.mean(prices[-fast:])
        for price in prices[-fast:]:
            fast_ema = price * fast_mult + fast_ema * (1 - fast_mult)
        slow_mult = 2.0 / (slow + 1)
        slow_ema = np.mean(prices[-slow:])
        for price in prices[-slow:]:
            slow_ema = price * slow_mult + slow_ema * (1 - slow_mult)
        macd_line = fast_ema - slow_ema
        signal_mult = 2.0 / (signal + 1)
        signal_line = macd_line
        for _ in range(signal):
            signal_line = macd_line * signal_mult + signal_line * (1 - signal_mult)
        histogram = macd_line - signal_line
        return round(macd_line, 8), round(signal_line, 8), round(histogram, 8)
    
    @staticmethod
    def calculate_ma(prices, period):
        if len(prices) < period:
            return prices[-1] if prices else 0
        return round(np.mean(prices[-period:]), 8)
    
    @staticmethod
    def calculate_ema(prices, period):
        if len(prices) < period:
            return prices[-1] if prices else 0
        prices = np.array(prices)
        mult = 2.0 / (period + 1)
        ema = np.mean(prices[-period:])
        for price in prices[-period:]:
            ema = price * mult + ema * (1 - mult)
        return round(ema, 8)
    
    @staticmethod
    def calculate_bollinger(prices, period=20, std_dev=2):
        if len(prices) < period:
            return prices[-1] if prices else 0, prices[-1] if prices else 0, prices[-1] if prices else 0
        prices = np.array(prices[-period:])
        ma = np.mean(prices)
        std = np.std(prices)
        upper = ma + (std_dev * std)
        lower = ma - (std_dev * std)
        return round(upper, 8), round(ma, 8), round(lower, 8)
    
    @staticmethod
    def calculate_vwap(prices, volumes):
        if len(prices) < 2:
            return prices[-1] if prices else 0
        total_value = sum(prices[i] * volumes[i] for i in range(len(prices)))
        total_volume = sum(volumes)
        if total_volume == 0:
            return prices[-1]
        return round(total_value / total_volume, 8)
    
    @staticmethod
    def calculate_atr(highs, lows, closes, period=14):
        if len(closes) < period:
            return 0.0000001
        tr_list = []
        for i in range(1, period + 1):
            if i < len(closes):
                tr = max(
                    highs[-i] - lows[-i],
                    abs(highs[-i] - closes[-i-1]),
                    abs(lows[-i] - closes[-i-1])
                )
                tr_list.append(tr)
        if not tr_list:
            return 0.0000001
        return round(np.mean(tr_list), 8)
    
    @staticmethod
    def find_support_resistance(highs, lows, closes, lookback=50):
        if len(closes) < lookback:
            return 0, 0, 0, 0
        
        highs_array = np.array(highs[-lookback:])
        lows_array = np.array(lows[-lookback:])
        
        peaks_idx = argrelextrema(highs_array, np.greater, order=5)[0]
        troughs_idx = argrelextrema(lows_array, np.less, order=5)[0]
        
        peaks = highs_array[peaks_idx] if len(peaks_idx) > 0 else []
        troughs = lows_array[troughs_idx] if len(troughs_idx) > 0 else []
        
        resistance_levels = sorted(peaks, reverse=True)[:2] if len(peaks) > 0 else [0, 0]
        support_levels = sorted(troughs)[:2] if len(troughs) > 0 else [0, 0]
        
        if len(resistance_levels) > 0 and len(support_levels) > 0:
            high = max(resistance_levels)
            low = min(support_levels)
            diff = high - low
            if diff > 0:
                fib_38 = high - diff * 0.382
                fib_62 = high - diff * 0.618
                support_levels.append(fib_62)
                resistance_levels.append(fib_38)
        
        support1 = support_levels[0] if support_levels else 0
        support2 = support_levels[1] if len(support_levels) > 1 else 0
        resistance1 = resistance_levels[0] if resistance_levels else 0
        resistance2 = resistance_levels[1] if len(resistance_levels) > 1 else 0
        
        return round(support1, 8), round(support2, 8), round(resistance1, 8), round(resistance2, 8)
    
    @staticmethod
    def calculate_adx(highs, lows, closes, period=14):
        if len(closes) < period + 1:
            return 25
        tr_list = []
        up_list = []
        down_list = []
        for i in range(1, period + 1):
            if i < len(closes):
                tr = max(
                    highs[-i] - lows[-i],
                    abs(highs[-i] - closes[-i-1]),
                    abs(lows[-i] - closes[-i-1])
                )
                tr_list.append(tr)
                up_move = highs[-i] - highs[-i-1]
                down_move = lows[-i-1] - lows[-i]
                up_list.append(max(0, up_move) if up_move > down_move else 0)
                down_list.append(max(0, down_move) if down_move > up_move else 0)
        if not tr_list:
            return 25
        atr = np.mean(tr_list)
        di_plus = 100 * np.mean(up_list) / atr if atr > 0 else 0
        di_minus = 100 * np.mean(down_list) / atr if atr > 0 else 0
        adx = 100 * abs(di_plus - di_minus) / (di_plus + di_minus + 0.0000001)
        return round(adx, 1)
    
    @staticmethod
    def calculate_stochastic(highs, lows, closes, k_period=14, d_period=3):
        if len(closes) < k_period:
            return 50, 50
        low_k = min(lows[-k_period:])
        high_k = max(highs[-k_period:])
        if high_k == low_k:
            return 50, 50
        k = 100 * (closes[-1] - low_k) / (high_k - low_k)
        return round(k, 2), 50
    
    @staticmethod
    def calculate_cci(highs, lows, closes, period=20):
        if len(closes) < period:
            return 0
        tp = [(highs[i] + lows[i] + closes[i]) / 3 for i in range(len(closes))]
        if len(tp) < period:
            return 0
        mean_tp = np.mean(tp[-period:])
        mean_dev = np.mean([abs(tp[i] - mean_tp) for i in range(-period, 0)])
        if mean_dev == 0:
            return 0
        cci = (tp[-1] - mean_tp) / (0.015 * mean_dev)
        return round(cci, 2)
    
    @staticmethod
    def calculate_williams_r(highs, lows, closes, period=14):
        if len(closes) < period:
            return -50
        highest = max(highs[-period:])
        lowest = min(lows[-period:])
        if highest == lowest:
            return -50
        wr = -100 * (highest - closes[-1]) / (highest - lowest)
        return round(wr, 2)
    
    @staticmethod
    def calculate_momentum(prices, period=14):
        if len(prices) < period:
            return 0
        return round((prices[-1] - prices[-period]) / prices[-period] * 100, 4)
    
    @staticmethod
    def calculate_volume_trend(volumes):
        if len(volumes) < 20:
            return 0
        avg_old = np.mean(volumes[-20:-10]) if len(volumes) >= 20 else 0
        avg_new = np.mean(volumes[-10:]) if len(volumes) >= 10 else 0
        if avg_old == 0:
            return 0
        return round((avg_new - avg_old) / avg_old * 100, 2)
    
    @staticmethod
    def calculate_volatility(highs, lows, closes, period=20):
        if len(closes) < period:
            return 0
        returns = []
        for i in range(1, period):
            if closes[-i] > 0:
                returns.append((closes[-i] - closes[-i-1]) / closes[-i-1])
        if not returns:
            return 0
        return round(np.std(returns) * 100, 2)
    
    @staticmethod
    def calculate_market_strength(closes, highs, lows):
        if len(closes) < 50:
            return 0
        high_50 = max(highs[-50:])
        low_50 = min(lows[-50:])
        current = closes[-1]
        if high_50 == low_50:
            return 50
        return round((current - low_50) / (high_50 - low_50) * 100, 2)
    
    @staticmethod
    def calculate_obv(closes, volumes):
        if len(closes) < 2:
            return 0
        obv = 0
        for i in range(1, len(closes)):
            if closes[i] > closes[i-1]:
                obv += volumes[i]
            elif closes[i] < closes[i-1]:
                obv -= volumes[i]
        return round(obv, 2)
    
    @staticmethod
    def calculate_linear_regression(prices, period=20):
        if len(prices) < period:
            return 0, 0
        x = np.arange(period)
        y = prices[-period:]
        slope, intercept, r_value, p_value, std_err = linregress(x, y)
        return round(slope, 8), round(r_value, 4)
    
    @staticmethod
    def calculate_fourier_prediction(prices, period=50):
        """Predict price using FFT"""
        if len(prices) < period:
            return prices[-1] if prices else 0
        y = prices[-period:]
        fft_vals = fft(y)
        fft_vals[5:-5] = 0  # Keep only low frequencies
        predicted = np.real(ifft(fft_vals))[-1]
        return round(predicted, 8)

# ============================================================
# 5000X STRONGER MARKET ANALYSIS
# ============================================================

def ultra_market_analysis(symbol):
    """5000X stronger analysis with Scipy and FFT"""
    try:
        # 10 timeframes for maximum accuracy
        timeframes = [
            {'name': '1m', 'limit': 100, 'weight': 0.02},
            {'name': '3m', 'limit': 100, 'weight': 0.04},
            {'name': '5m', 'limit': 300, 'weight': 0.17},
            {'name': '15m', 'limit': 300, 'weight': 0.20},
            {'name': '30m', 'limit': 200, 'weight': 0.17},
            {'name': '1h', 'limit': 200, 'weight': 0.15},
            {'name': '2h', 'limit': 150, 'weight': 0.10},
            {'name': '4h', 'limit': 150, 'weight': 0.08},
            {'name': '8h', 'limit': 100, 'weight': 0.04},
            {'name': '1d', 'limit': 100, 'weight': 0.03}
        ]
        
        analysis_results = {}
        all_scores = []
        ui = QuantumIndicators()
        
        for tf in timeframes:
            data = get_candles(symbol, tf['limit'], tf['name'])
            if not data or len(data['close']) < 30:
                continue
            
            prices = data['close']
            highs = data['high']
            lows = data['low']
            volumes = data['volume']
            current = prices[-1]
            
            # Calculate ALL indicators
            rsi = ui.calculate_rsi(prices, 14)
            macd, macd_signal, macd_hist = ui.calculate_macd(prices, 12, 26, 9)
            ma7 = ui.calculate_ma(prices, 7)
            ma20 = ui.calculate_ma(prices, 20)
            ma50 = ui.calculate_ma(prices, 50)
            ma100 = ui.calculate_ma(prices, 100)
            ma200 = ui.calculate_ma(prices, 200)
            upper_bb, middle_bb, lower_bb = ui.calculate_bollinger(prices, 20, 2)
            vwap = ui.calculate_vwap(prices, volumes)
            atr = ui.calculate_atr(highs, lows, prices, 14)
            support1, support2, resistance1, resistance2 = ui.find_support_resistance(highs, lows, prices, 50)
            adx = ui.calculate_adx(highs, lows, prices, 14)
            stoch_k, stoch_d = ui.calculate_stochastic(highs, lows, prices, 14, 3)
            cci = ui.calculate_cci(highs, lows, prices, 20)
            williams_r = ui.calculate_williams_r(highs, lows, prices, 14)
            momentum = ui.calculate_momentum(prices, 14)
            volume_trend = ui.calculate_volume_trend(volumes)
            volatility = ui.calculate_volatility(highs, lows, prices, 20)
            market_strength = ui.calculate_market_strength(prices, highs, lows)
            obv = ui.calculate_obv(prices, volumes)
            slope, r_value = ui.calculate_linear_regression(prices, 20)
            predicted_price = ui.calculate_fourier_prediction(prices, 50)
            
            # ===== 5000X SCORING =====
            score = 50
            reasons = []
            signals = []
            
            # 1. RSI (30 points)
            if rsi < 25:
                score += 30
                reasons.append(f"🔥 RSI Oversold: {rsi:.1f}")
                signals.append('buy')
            elif rsi < 35:
                score += 22
                reasons.append(f"📈 RSI Near Oversold: {rsi:.1f}")
                signals.append('buy')
            elif rsi > 75:
                score -= 30
                reasons.append(f"🔥 RSI Overbought: {rsi:.1f}")
                signals.append('sell')
            elif rsi > 65:
                score -= 22
                reasons.append(f"📉 RSI Near Overbought: {rsi:.1f}")
                signals.append('sell')
            
            # 2. MACD (30 points)
            if macd > 0 and macd_hist > 0:
                score += 30
                reasons.append("🟢 MACD Bullish Cross")
                signals.append('buy')
            elif macd < 0 and macd_hist < 0:
                score -= 30
                reasons.append("🔴 MACD Bearish Cross")
                signals.append('sell')
            elif macd > 0:
                score += 18
                reasons.append("🟡 MACD Positive")
                signals.append('buy')
            else:
                score -= 18
                reasons.append("🟡 MACD Negative")
                signals.append('sell')
            
            # 3. Moving Averages (40 points)
            if current > ma20 and ma20 > ma50 and ma50 > ma100 and ma100 > ma200:
                score += 40
                reasons.append("🚀 Super Uptrend (MA)")
                signals.append('buy')
            elif current < ma20 and ma20 < ma50 and ma50 < ma100 and ma100 < ma200:
                score -= 40
                reasons.append("💀 Super Downtrend (MA)")
                signals.append('sell')
            elif current > ma20 and ma20 > ma50 and ma50 > ma100:
                score += 30
                reasons.append("📈 Strong Uptrend (MA)")
                signals.append('buy')
            elif current < ma20 and ma20 < ma50 and ma50 < ma100:
                score -= 30
                reasons.append("📉 Strong Downtrend (MA)")
                signals.append('sell')
            elif current > ma20 and ma20 > ma50:
                score += 18
                reasons.append("📈 Uptrend (MA)")
                signals.append('buy')
            elif current < ma20 and ma20 < ma50:
                score -= 18
                reasons.append("📉 Downtrend (MA)")
                signals.append('sell')
            elif current > ma20:
                score += 10
                reasons.append("⬆️ Above MA20")
                signals.append('buy')
            else:
                score -= 10
                reasons.append("⬇️ Below MA20")
                signals.append('sell')
            
            # 4. Bollinger Bands (25 points)
            if current < lower_bb:
                score += 25
                reasons.append("🎯 Below Lower BB")
                signals.append('buy')
            elif current > upper_bb:
                score -= 25
                reasons.append("🎯 Above Upper BB")
                signals.append('sell')
            elif current < middle_bb:
                score += 12
                reasons.append("📊 Below BB Middle")
                signals.append('buy')
            else:
                score -= 12
                reasons.append("📊 Above BB Middle")
                signals.append('sell')
            
            # 5. VWAP (20 points)
            if current > vwap:
                score += 20
                reasons.append("✅ Above VWAP")
                signals.append('buy')
            else:
                score -= 20
                reasons.append("❌ Below VWAP")
                signals.append('sell')
            
            # 6. Support/Resistance (30 points)
            if support1 > 0:
                dist_to_support = ((current - support1) / current) * 100
                if dist_to_support < 0.2:
                    score += 30
                    reasons.append(f"🛡️ Exact Support")
                    signals.append('buy')
                elif dist_to_support < 0.6:
                    score += 22
                    reasons.append(f"🛡️ Near Support")
                    signals.append('buy')
                elif dist_to_support < 1.2:
                    score += 14
                    reasons.append(f"🛡️ Close Support")
                    signals.append('buy')
            
            if resistance1 > 0:
                dist_to_resistance = ((resistance1 - current) / current) * 100
                if dist_to_resistance < 0.2:
                    score -= 30
                    reasons.append(f"🚫 Exact Resistance")
                    signals.append('sell')
                elif dist_to_resistance < 0.6:
                    score -= 22
                    reasons.append(f"🚫 Near Resistance")
                    signals.append('sell')
                elif dist_to_resistance < 1.2:
                    score -= 14
                    reasons.append(f"🚫 Close Resistance")
                    signals.append('sell')
            
            # 7. ADX (25 points)
            if adx > 45:
                if score > 50:
                    score += 25
                    reasons.append(f"🔥 Strong Trend (ADX: {adx:.1f})")
                else:
                    score -= 25
                    reasons.append(f"💀 Strong Trend (ADX: {adx:.1f})")
            elif adx > 30:
                if score > 50:
                    score += 15
                    reasons.append(f"✅ Trend: {adx:.1f}")
                else:
                    score -= 15
                    reasons.append(f"⚠️ Trend: {adx:.1f}")
            elif adx > 20:
                if score > 50:
                    score += 8
                    reasons.append(f"📊 Weak Trend: {adx:.1f}")
            
            # 8. Stochastic (20 points)
            if stoch_k < 20:
                score += 20
                reasons.append(f"📊 Stochastic Oversold")
                signals.append('buy')
            elif stoch_k > 80:
                score -= 20
                reasons.append(f"📊 Stochastic Overbought")
                signals.append('sell')
            
            # 9. CCI (20 points)
            if cci < -100:
                score += 20
                reasons.append(f"📈 CCI Oversold")
                signals.append('buy')
            elif cci > 100:
                score -= 20
                reasons.append(f"📉 CCI Overbought")
                signals.append('sell')
            
            # 10. Williams %R (15 points)
            if williams_r < -80:
                score += 15
                reasons.append(f"📈 Williams Oversold")
                signals.append('buy')
            elif williams_r > -20:
                score -= 15
                reasons.append(f"📉 Williams Overbought")
                signals.append('sell')
            
            # 11. Volume Trend (20 points)
            if volume_trend > 15:
                if score > 50:
                    score += 20
                    reasons.append(f"📊 Volume Increasing")
                    signals.append('buy')
                else:
                    score -= 20
                    reasons.append(f"📊 Volume Increasing (Bearish)")
                    signals.append('sell')
            elif volume_trend < -15:
                if score > 50:
                    score -= 20
                    reasons.append(f"📊 Volume Decreasing")
                    signals.append('sell')
                else:
                    score += 20
                    reasons.append(f"📊 Volume Decreasing (Bullish)")
                    signals.append('buy')
            
            # 12. Momentum (20 points)
            if momentum > 3:
                score += 20
                reasons.append(f"📈 Strong Momentum")
                signals.append('buy')
            elif momentum < -3:
                score -= 20
                reasons.append(f"📉 Weak Momentum")
                signals.append('sell')
            elif momentum > 1:
                score += 10
                reasons.append(f"📈 Positive Momentum")
                signals.append('buy')
            elif momentum < -1:
                score -= 10
                reasons.append(f"📉 Negative Momentum")
                signals.append('sell')
            
            # 13. OBV (15 points)
            if obv > 0:
                score += 15
                reasons.append("📊 OBV Bullish")
                signals.append('buy')
            else:
                score -= 15
                reasons.append("📊 OBV Bearish")
                signals.append('sell')
            
            # 14. Linear Regression (15 points)
            if slope > 0 and r_value > 0.3:
                score += 15
                reasons.append(f"📈 Uptrend (R={r_value:.2f})")
                signals.append('buy')
            elif slope < 0 and r_value < -0.3:
                score -= 15
                reasons.append(f"📉 Downtrend (R={r_value:.2f})")
                signals.append('sell')
            
            # 15. FFT Prediction (15 points)
            if predicted_price > current * 1.02:
                score += 15
                reasons.append(f"🔮 FFT Bullish")
                signals.append('buy')
            elif predicted_price < current * 0.98:
                score -= 15
                reasons.append(f"🔮 FFT Bearish")
                signals.append('sell')
            
            # Determine market phase
            market_phase = "neutral"
            if adx > 35 and score > 55:
                market_phase = "bullish_trend"
            elif adx > 35 and score < 45:
                market_phase = "bearish_trend"
            elif adx < 20:
                market_phase = "ranging"
            elif score > 60:
                market_phase = "accumulation"
            elif score < 40:
                market_phase = "distribution"
            
            analysis_results[tf['name']] = {
                'score': score,
                'rsi': rsi,
                'macd': macd,
                'ma20': ma20,
                'ma50': ma50,
                'ma200': ma200,
                'vwap': vwap,
                'atr': atr,
                'support1': support1,
                'support2': support2,
                'resistance1': resistance1,
                'resistance2': resistance2,
                'adx': adx,
                'volatility': volatility,
                'trend_strength': adx / 100 if adx > 0 else 0,
                'market_phase': market_phase,
                'weight': tf['weight'],
                'reasons': reasons[:3],
                'signals': signals
            }
            
            all_scores.append(score)
        
        if not analysis_results:
            return None
        
        # Weighted average score
        weighted_score = 0
        total_weight = 0
        for tf_name, data in analysis_results.items():
            weighted_score += data['score'] * data['weight']
            total_weight += data['weight']
        
        if total_weight == 0:
            return None
        
        final_score = weighted_score / total_weight
        
        if final_score >= 55:
            signal = "BUY"
            confidence = min(98, 50 + abs(final_score - 50) * 1.8)
        elif final_score <= 45:
            signal = "SELL"
            confidence = min(98, 50 + abs(final_score - 50) * 1.8)
        else:
            return None
        
        # Get main data
        main_data = get_candles(symbol, 200, '5m')
        if not main_data:
            return None
        
        current = main_data['close'][-1]
        atr = QuantumIndicators.calculate_atr(main_data['high'], main_data['low'], main_data['close'], 14)
        
        # Calculate profit targets
        min_profit = float(db.get_setting('min_profit_target') or 30)
        rr_ratio = float(db.get_setting('risk_reward_ratio') or 3.0)
        aggressive = db.get_setting('aggressive_mode') == '1'
        
        if signal == "BUY":
            risk = atr * 1.2
            entry = current * 0.999
            
            support1 = analysis_results.get('5m', {}).get('support1', 0)
            if support1 > 0 and support1 < entry:
                sl = support1 * 0.998
            else:
                sl = entry - risk * 2.0
            
            tp1 = entry * (1 + (min_profit / 100))
            tp2 = entry * (1 + (min_profit * 2 / 100))
            tp3 = entry * (1 + (min_profit * 3 / 100))
            
            resistance1 = analysis_results.get('5m', {}).get('resistance1', 0)
            if resistance1 > 0:
                if tp1 > resistance1:
                    tp1 = resistance1 * 0.998
                if tp2 > resistance1:
                    tp2 = resistance1 * 0.998
                if tp3 > resistance1:
                    tp3 = resistance1 * 0.998
            
            actual_rr = ((tp1 - entry) / abs(entry - sl)) if abs(entry - sl) > 0 else 0
            if actual_rr < rr_ratio:
                tp1 = entry + (abs(entry - sl) * rr_ratio)
                tp2 = entry + (abs(entry - sl) * rr_ratio * 2)
                tp3 = entry + (abs(entry - sl) * rr_ratio * 3)
            
            if aggressive:
                tp1 = entry + (abs(entry - sl) * 4)
                tp2 = entry + (abs(entry - sl) * 6)
                tp3 = entry + (abs(entry - sl) * 8)
            
            profit_percent = round((tp1 - entry) / entry * 100, 2)
            
        else:
            risk = atr * 1.2
            entry = current * 1.001
            
            resistance1 = analysis_results.get('5m', {}).get('resistance1', 0)
            if resistance1 > 0 and resistance1 > entry:
                sl = resistance1 * 1.002
            else:
                sl = entry + risk * 2.0
            
            tp1 = entry * (1 - (min_profit / 100))
            tp2 = entry * (1 - (min_profit * 2 / 100))
            tp3 = entry * (1 - (min_profit * 3 / 100))
            
            support1 = analysis_results.get('5m', {}).get('support1', 0)
            if support1 > 0:
                if tp1 < support1:
                    tp1 = support1 * 1.002
                if tp2 < support1:
                    tp2 = support1 * 1.002
                if tp3 < support1:
                    tp3 = support1 * 1.002
            
            actual_rr = ((entry - tp1) / abs(sl - entry)) if abs(sl - entry) > 0 else 0
            if actual_rr < rr_ratio:
                tp1 = entry - (abs(sl - entry) * rr_ratio)
                tp2 = entry - (abs(sl - entry) * rr_ratio * 2)
                tp3 = entry - (abs(sl - entry) * rr_ratio * 3)
            
            if aggressive:
                tp1 = entry - (abs(sl - entry) * 4)
                tp2 = entry - (abs(sl - entry) * 6)
                tp3 = entry - (abs(sl - entry) * 8)
            
            profit_percent = round((entry - tp1) / entry * 100, 2)
        
        confidence = min(98, confidence)
        quality_score = min(100, confidence + (5 if final_score > 55 else -5 if final_score < 45 else 0))
        
        all_reasons = []
        for tf_name, data in analysis_results.items():
            all_reasons.extend(data['reasons'][:2])
        
        return {
            'symbol': symbol,
            'entry': round(entry, 8),
            'signal': signal,
            'confidence': round(confidence, 1),
            'score': round(final_score, 1),
            'quality_score': round(quality_score, 1),
            'tp1': round(tp1, 8),
            'tp2': round(tp2, 8),
            'tp3': round(tp3, 8),
            'sl': round(sl, 8),
            'profit_percent': round(profit_percent, 2),
            'predicted_price': round(predicted_price, 8) if 'predicted_price' in locals() else 0,
            'rsi': analysis_results.get('5m', {}).get('rsi', 50),
            'macd': analysis_results.get('5m', {}).get('macd', 0),
            'ma20': analysis_results.get('5m', {}).get('ma20', 0),
            'ma50': analysis_results.get('5m', {}).get('ma50', 0),
            'ma200': analysis_results.get('5m', {}).get('ma200', 0),
            'vwap': analysis_results.get('5m', {}).get('vwap', 0),
            'atr': atr,
            'support1': analysis_results.get('5m', {}).get('support1', 0),
            'support2': analysis_results.get('5m', {}).get('support2', 0),
            'resistance1': analysis_results.get('5m', {}).get('resistance1', 0),
            'resistance2': analysis_results.get('5m', {}).get('resistance2', 0),
            'adx': analysis_results.get('5m', {}).get('adx', 25),
            'volatility': analysis_results.get('5m', {}).get('volatility', 0),
            'trend_strength': analysis_results.get('5m', {}).get('trend_strength', 0),
            'momentum_score': analysis_results.get('5m', {}).get('momentum_score', 0),
            'market_phase': analysis_results.get('5m', {}).get('market_phase', 'neutral'),
            'reasons': all_reasons[:8],
            'time': datetime.now().strftime("%H:%M"),
            'timeframes': {k: {'score': v['score'], 'rsi': v['rsi'], 'phase': v.get('market_phase', 'neutral')} 
                          for k, v in analysis_results.items()}
        }
        
    except Exception as e:
        logger.error(f"Analysis error for {symbol}: {e}")
        return None

# ============================================================
# ALL CRYPTO SYMBOLS
# ============================================================

SYMBOLS = [
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
    'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT', 'MATICUSDT', 'DOTUSDT',
    'LINKUSDT', 'UNIUSDT', 'LTCUSDT', 'BCHUSDT', 'NEARUSDT',
    'ALGOUSDT', 'VETUSDT', 'ICPUSDT', 'FILUSDT', 'FTMUSDT',
    'XLMUSDT', 'EGLDUSDT', 'XMRUSDT', 'ZECUSDT', 'ETCUSDT',
    'EOSUSDT', 'AAVEUSDT', 'MKRUSDT', 'COMPUSDT', 'SUSHIUSDT',
    'CAKEUSDT', 'AXSUSDT', 'SANDUSDT', 'APEUSDT', 'CRVUSDT',
    'RUNEUSDT', 'FLOWUSDT', 'QNTUSDT', 'SNXUSDT', 'GRTUSDT',
    'LDOUSDT', 'ARBUSDT', 'OPUSDT', 'INJUSDT', 'SEIUSDT',
    'WLDUSDT', 'PEPEUSDT', 'BONKUSDT', 'FLOKIUSDT', 'SHIBUSDT',
    'WIFUSDT', 'RNDRUSDT', 'FETUSDT', 'AGIXUSDT', 'OCEANUSDT'
]

# ============================================================
# ADVANCED LEARNING SYSTEM
# ============================================================

class LearningSystem:
    def __init__(self):
        self.file = "learning_data.json"
        self.load()
    
    def load(self):
        if os.path.exists(self.file):
            try:
                with open(self.file, 'r') as f:
                    data = json.load(f)
                    self.positive = data.get('positive', 0)
                    self.negative = data.get('negative', 0)
                    self.weights = data.get('weights', {
                        'rsi': 1.0, 'macd': 1.0, 'ma': 1.0,
                        'bollinger': 1.0, 'vwap': 1.2, 'volume': 1.0,
                        'sr': 1.0, 'adx': 1.0, 'stochastic': 1.0,
                        'cci': 1.0, 'williams': 1.0, 'momentum': 1.0,
                        'obv': 1.0, 'regression': 1.0, 'fft': 1.2
                    })
                    self.market_weights = data.get('market_weights', {
                        'bullish_trend': 1.0,
                        'bearish_trend': 1.0,
                        'ranging': 0.8,
                        'accumulation': 1.1,
                        'distribution': 0.9,
                        'neutral': 1.0
                    })
                    self.timeframe_weights = data.get('timeframe_weights', {})
                    return
            except:
                pass
        
        self.positive = 0
        self.negative = 0
        self.weights = {
            'rsi': 1.0, 'macd': 1.0, 'ma': 1.0,
            'bollinger': 1.0, 'vwap': 1.2, 'volume': 1.0,
            'sr': 1.0, 'adx': 1.0, 'stochastic': 1.0,
            'cci': 1.0, 'williams': 1.0, 'momentum': 1.0,
            'obv': 1.0, 'regression': 1.0, 'fft': 1.2
        }
        self.market_weights = {
            'bullish_trend': 1.0,
            'bearish_trend': 1.0,
            'ranging': 0.8,
            'accumulation': 1.1,
            'distribution': 0.9,
            'neutral': 1.0
        }
        self.timeframe_weights = {}
        self.save()
    
    def save(self):
        try:
            with open(self.file, 'w') as f:
                json.dump({
                    'positive': self.positive,
                    'negative': self.negative,
                    'weights': self.weights,
                    'market_weights': self.market_weights,
                    'timeframe_weights': self.timeframe_weights
                }, f, indent=2)
        except:
            pass
    
    def add_feedback(self, feedback_type, market_phase='neutral', profit_percent=0):
        if feedback_type == 'positive':
            self.positive += 1
            for key in self.weights:
                self.weights[key] = min(3.0, self.weights[key] * 1.03)
            if market_phase in self.market_weights:
                self.market_weights[market_phase] = min(2.0, self.market_weights[market_phase] * 1.02)
        else:
            self.negative += 1
            for key in self.weights:
                self.weights[key] = max(0.2, self.weights[key] * 0.97)
            if market_phase in self.market_weights:
                self.market_weights[market_phase] = max(0.4, self.market_weights[market_phase] * 0.98)
        self.save()
    
    def get_accuracy(self):
        total = self.positive + self.negative
        if total == 0:
            return 50.0
        return round((self.positive / total) * 100, 2)

learner = LearningSystem()

# ============================================================
# TELEGRAM FUNCTIONS
# ============================================================

def send_telegram(message, chat_id=None, reply_markup=None, parse_mode='HTML'):
    if not message:
        return False
    if chat_id is None:
        chat_id = CHANNEL_ID
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': parse_mode,
            'disable_web_page_preview': True
        }
        if reply_markup:
            data['reply_markup'] = json.dumps(reply_markup)
        response = requests.post(url, data=data, timeout=15)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Telegram send error: {e}")
        return False

def send_admin(message, reply_markup=None):
    return send_telegram(message, ADMIN_ID, reply_markup)

def build_signal_message(signal, signal_id):
    if not signal:
        return None, None
    
    emoji = "🟢" if signal['signal'] == 'BUY' else "🔴"
    direction = "LONG" if signal['signal'] == 'BUY' else "SHORT"
    profit_pct = signal.get('profit_percent', 0)
    
    phase_emoji = {
        'bullish_trend': '🚀',
        'bearish_trend': '📉',
        'ranging': '⬆️⬇️',
        'accumulation': '🏗️',
        'distribution': '🏗️',
        'neutral': '⚖️'
    }.get(signal.get('market_phase', 'neutral'), '⚖️')
    
    msg = f"""
{emoji} <b>{signal['symbol']}</b> | {direction}
{phase_emoji} <b>Phase:</b> {signal.get('market_phase', 'neutral').upper()}

<b>📊 ENTRY:</b> <code>${signal['entry']:.6f}</code>
<b>🎯 TP1:</b> <code>${signal['tp1']:.6f}</code> <i>(+{profit_pct:.1f}%)</i>
<b>🎯 TP2:</b> <code>${signal['tp2']:.6f}</code> <i>(+{profit_pct*2:.1f}%)</i>
<b>🎯 TP3:</b> <code>${signal['tp3']:.6f}</code> <i>(+{profit_pct*3:.1f}%)</i>
<b>🛑 SL:</b> <code>${signal['sl']:.6f}</code>
<b>📊 Confidence:</b> {signal['confidence']}%
<b>⭐ Quality:</b> {signal.get('quality_score', 0)}/100

<b>📈 INDICATORS:</b>
• RSI: {signal['rsi']:.1f}
• MACD: {signal['macd']:.6f}
• MA20: ${signal['ma20']:.4f}
• MA50: ${signal['ma50']:.4f}
• VWAP: ${signal['vwap']:.4f}
• ADX: {signal.get('adx', 0):.1f}
• ATR: ${signal['atr']:.6f}
• Volatility: {signal.get('volatility', 0):.2f}%

<b>🛡️ LEVELS:</b>
• S1: ${signal.get('support1', 0):.4f}
• S2: ${signal.get('support2', 0):.4f}
• R1: ${signal.get('resistance1', 0):.4f}
• R2: ${signal.get('resistance2', 0):.4f}

<b>📝 ANALYSIS:</b>
"""
    reasons = signal.get('reasons', [])
    for i, reason in enumerate(reasons[:7], 1):
        msg += f"{i}. {reason}\n"
    
    if 'timeframes' in signal:
        msg += "\n<b>⏱️ TIMEFRAMES:</b>\n"
        for tf, data in signal['timeframes'].items():
            score_emoji = "🟢" if data['score'] > 55 else "🔴" if data['score'] < 45 else "🟡"
            msg += f"• {tf}: {score_emoji} {data['score']:.1f}\n"
    
    msg += f"""
━━━━━━━━━━━━━━━━━━━━━━
<b>🧠 LEARNING SYSTEM:</b>
• Win Rate: {learner.get_accuracy()}%
• ✅ Wins: {learner.positive} | ❌ Losses: {learner.negative}
• ⏰ {signal['time']}

<i>⚠️ Trade at your own risk!</i>
"""
    
    keyboard = {
        'inline_keyboard': [
            [
                {'text': '✅ I Profited 💰', 'callback_data': f'fb_positive_{signal_id}'},
                {'text': '❌ I Lost', 'callback_data': f'fb_negative_{signal_id}'}
            ],
            [
                {'text': '📊 Full Analysis', 'callback_data': f'analysis_{signal_id}'}
            ]
        ]
    }
    
    return msg, keyboard

# ============================================================
# ADMIN PANEL - FULL BUTTONS
# ============================================================

ADMIN_PANEL_BUTTONS = {
    'inline_keyboard': [
        [
            {'text': '🟢 Enable Signals', 'callback_data': 'admin_on'},
            {'text': '🔴 Disable Signals', 'callback_data': 'admin_off'}
        ],
        [
            {'text': '💰 Enable Payments', 'callback_data': 'admin_pay_on'},
            {'text': '💳 Disable Payments', 'callback_data': 'admin_pay_off'}
        ],
        [
            {'text': '🔥 Aggressive Mode', 'callback_data': 'admin_aggressive'},
            {'text': '📊 Standard Mode', 'callback_data': 'admin_standard'}
        ],
        [
            {'text': '📊 Statistics', 'callback_data': 'admin_stats'},
            {'text': '💳 Payments', 'callback_data': 'admin_payments'}
        ],
        [
            {'text': '⚙️ Settings', 'callback_data': 'admin_settings'},
            {'text': '📝 Feedback', 'callback_data': 'admin_feedback'}
        ],
        [
            {'text': '🔄 Reset Learning', 'callback_data': 'admin_reset'},
            {'text': '📋 Logs', 'callback_data': 'admin_logs'}
        ],
        [
            {'text': '🔄 Refresh Panel', 'callback_data': 'admin_refresh'}
        ]
    ]
}

def show_admin_panel():
    """Show admin panel with full buttons"""
    settings = db.get_all_settings()
    stats = db.get_stats()
    
    signal_enabled = settings.get('signal_enabled', '0') == '1'
    payment_enabled = settings.get('payment_enabled', '0') == '1'
    aggressive = settings.get('aggressive_mode', '0') == '1'
    
    msg = f"""
🔐 <b>🚀 ULTIMATE SIGNAL BOT V18</b>
<b>🤖 QUANTUM PRO MAX ULTRA</b>
━━━━━━━━━━━━━━━━━━━━━━

<b>📡 SYSTEM STATUS:</b>
• 🤖 Bot: 🟢 RUNNING
• 📡 Signals: {'🟢 ENABLED' if signal_enabled else '🔴 DISABLED'}
• 💳 Payments: {'🟢 ENABLED' if payment_enabled else '🔴 DISABLED'}
• ⚡ Mode: {'🔥 AGGRESSIVE' if aggressive else '📊 STANDARD'}

<b>📈 STATISTICS:</b>
• 👤 Users: {stats.get('users', 0)}
• 🟢 Active: {stats.get('active', 0)}
• 👑 Premium: {stats.get('premium', 0)}
• 📊 Today: {stats.get('today', 0)}
• 📈 Total: {stats.get('signals', 0)}
• 🎯 Win Rate: {stats.get('win_rate', 0)}%
• 💰 Avg Profit: ${stats.get('avg_profit', 0)}
• 💳 Pending: {stats.get('pending', 0)}

<b>⚙️ SETTINGS:</b>
• 🎯 Min Confidence: {settings.get('min_confidence', 65)}%
• 📊 Max Signals: {settings.get('max_signals', 5)}
• 💰 Price: {settings.get('price', PRICE)}
• 📈 Min Profit: {settings.get('min_profit_target', 30)}%
• 🎯 R/R Ratio: {settings.get('risk_reward_ratio', 3.0)}

<b>🧠 LEARNING SYSTEM:</b>
• Accuracy: {learner.get_accuracy()}%
• ✅ Wins: {learner.positive}
• ❌ Losses: {learner.negative}
• 📈 Status: {'🟢 Active' if db.get_setting('learning_enabled') == '1' else '🔴 Disabled'}

━━━━━━━━━━━━━━━━━━━━━━
<b>📌 Click buttons below to manage:</b>
"""
    
    send_admin(msg, ADMIN_PANEL_BUTTONS)

def handle_admin_callback(callback_data):
    try:
        if callback_data == 'admin_on':
            db.update_setting('signal_enabled', '1')
            send_admin("✅ <b>Signals ENABLED</b>\n\n📡 Signal generation activated.")
            show_admin_panel()
            return True
        
        elif callback_data == 'admin_off':
            db.update_setting('signal_enabled', '0')
            send_admin("🔴 <b>Signals DISABLED</b>\n\n📡 Signal generation paused.")
            show_admin_panel()
            return True
        
        elif callback_data == 'admin_pay_on':
            db.update_setting('payment_enabled', '1')
            send_admin("💰 <b>Payments ENABLED</b>\n\n💳 Users can subscribe now.")
            show_admin_panel()
            return True
        
        elif callback_data == 'admin_pay_off':
            db.update_setting('payment_enabled', '0')
            send_admin("💳 <b>Payments DISABLED</b>\n\n💰 Subscriptions paused.")
            show_admin_panel()
            return True
        
        elif callback_data == 'admin_aggressive':
            db.update_setting('aggressive_mode', '1')
            send_admin("🔥 <b>Aggressive Mode ENABLED</b>\n\nHigher profit targets with more risk.")
            show_admin_panel()
            return True
        
        elif callback_data == 'admin_standard':
            db.update_setting('aggressive_mode', '0')
            send_admin("📊 <b>Standard Mode ENABLED</b>\n\nBalanced risk management.")
            show_admin_panel()
            return True
        
        elif callback_data == 'admin_stats':
            stats = db.get_stats()
            msg = f"""
📊 <b>DETAILED STATISTICS</b>
━━━━━━━━━━━━━━━━━━━━━━

<b>👤 USERS:</b>
• Total: {stats.get('users', 0)}
• Active: {stats.get('active', 0)}
• Premium: {stats.get('premium', 0)}

<b>📊 SIGNALS:</b>
• Total: {stats.get('signals', 0)}
• Today: {stats.get('today', 0)}

<b>💳 PAYMENTS:</b>
• Pending: {stats.get('pending', 0)}

<b>📝 PERFORMANCE:</b>
• Win Rate: {stats.get('win_rate', 0)}%
• Wins: {stats.get('wins', 0)}
• Avg Profit: ${stats.get('avg_profit', 0)}

<b>🧠 LEARNING:</b>
• Accuracy: {learner.get_accuracy()}%
• Positive: {learner.positive}
• Negative: {learner.negative}
"""
            send_admin(msg)
            return True
        
        elif callback_data == 'admin_payments':
            payments = db.get_pending_payments()
            if not payments:
                send_admin("💳 <b>No pending payments</b>\n\nAll payments processed.")
                return True
            
            msg = f"💳 <b>PENDING PAYMENTS</b> ({len(payments)})\n━━━━━━━━━━━━━━━━━━━━━━\n"
            for payment in payments[:10]:
                payment_id, user_id, payment_hash, amount, created_at = payment
                msg += f"""
📌 <b>#{payment_id}</b>
👤 User: {user_id}
💰 Amount: {amount}
🔑 Hash: <code>{payment_hash[:30]}...</code>
📅 Created: {created_at[:16]}
✅ /confirm_{payment_id}
❌ /reject_{payment_id}
━━━━━━━━━━━━━━━━━━━━━━
"""
            send_admin(msg)
            return True
        
        elif callback_data == 'admin_settings':
            settings = db.get_all_settings()
            msg = "⚙️ <b>SYSTEM SETTINGS</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
            for key, value in settings.items():
                msg += f"\n📌 <b>{key}:</b> <code>{value}</code>"
            msg += """
━━━━━━━━━━━━━━━━━━━━━━
<b>✏️ Change settings:</b>
<code>/set min_confidence 75</code>
<code>/set max_signals 3</code>
<code>/set min_profit_target 40</code>
<code>/set risk_reward_ratio 4</code>
"""
            send_admin(msg)
            return True
        
        elif callback_data == 'admin_feedback':
            feedback_total = db.cursor.execute('SELECT COUNT(*) FROM feedback_log').fetchone()[0]
            positive = db.cursor.execute('SELECT COUNT(*) FROM feedback_log WHERE feedback = "positive"').fetchone()[0]
            negative = db.cursor.execute('SELECT COUNT(*) FROM feedback_log WHERE feedback = "negative"').fetchone()[0]
            
            msg = f"""
📝 <b>FEEDBACK ANALYTICS</b>
━━━━━━━━━━━━━━━━━━━━━━

📊 <b>Total Feedback:</b> {feedback_total}
✅ Positive: {positive} ({round(positive/feedback_total*100 if feedback_total > 0 else 0, 1)}%)
❌ Negative: {negative} ({round(negative/feedback_total*100 if feedback_total > 0 else 0, 1)}%)
🎯 System Win Rate: {learner.get_accuracy()}%

<b>📋 Recent Feedback:</b>
"""
            recent = db.cursor.execute('''
                SELECT f.feedback, u.username, s.symbol, f.created_at, f.profit_amount
                FROM feedback_log f
                LEFT JOIN users u ON f.user_id = u.user_id
                LEFT JOIN signals s ON f.signal_id = s.id
                ORDER BY f.created_at DESC
                LIMIT 10
            ''').fetchall()
            
            for feedback, username, symbol, created_at, profit in recent:
                emoji = "✅" if feedback == 'positive' else "❌"
                profit_str = f"💰 ${profit:.2f}" if feedback == 'positive' else f"💸 ${abs(profit or 0):.2f}"
                msg += f"\n{emoji} {username or 'Unknown'} | {symbol or 'N/A'} | {created_at[:16]} | {profit_str}"
            
            send_admin(msg)
            return True
        
        elif callback_data == 'admin_reset':
            learner.positive = 0
            learner.negative = 0
            for key in learner.weights:
                learner.weights[key] = 1.0
            for key in learner.market_weights:
                learner.market_weights[key] = 1.0
            learner.save()
            send_admin("🔄 <b>Learning System Reset</b>\n\n🧠 All learning data reset to defaults.")
            show_admin_panel()
            return True
        
        elif callback_data == 'admin_logs':
            logs = db.cursor.execute('''
                SELECT details, created_at FROM admin_logs 
                ORDER BY created_at DESC LIMIT 15
            ''').fetchall()
            
            if not logs:
                send_admin("📋 <b>No admin logs found</b>")
                return True
            
            msg = "📋 <b>RECENT LOGS</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
            for details, created_at in logs[:10]:
                msg += f"\n🕐 {created_at[:16]}\n📌 {details[:60]}\n"
            
            send_admin(msg)
            return True
        
        elif callback_data == 'admin_refresh':
            show_admin_panel()
            return True
        
        return False
    except Exception as e:
        logger.error(f"Admin callback error: {e}")
        send_admin(f"❌ <b>Error:</b> {str(e)}")
        return False

def handle_admin_command(text):
    try:
        if text == '/panel':
            show_admin_panel()
            return True
        
        elif text == '/on':
            db.update_setting('signal_enabled', '1')
            send_admin("✅ Signals ENABLED")
            return True
        
        elif text == '/off':
            db.update_setting('signal_enabled', '0')
            send_admin("🔴 Signals DISABLED")
            return True
        
        elif text == '/pay_on':
            db.update_setting('payment_enabled', '1')
            send_admin("💰 Payments ENABLED")
            return True
        
        elif text == '/pay_off':
            db.update_setting('payment_enabled', '0')
            send_admin("💳 Payments DISABLED")
            return True
        
        elif text == '/aggressive':
            db.update_setting('aggressive_mode', '1')
            send_admin("🔥 Aggressive Mode ENABLED")
            return True
        
        elif text == '/standard':
            db.update_setting('aggressive_mode', '0')
            send_admin("📊 Standard Mode ENABLED")
            return True
        
        elif text.startswith('/confirm_'):
            try:
                payment_id = int(text.replace('/confirm_', ''))
                success, user_id = db.confirm_payment(payment_id)
                if success:
                    send_admin(f"✅ Payment #{payment_id} CONFIRMED")
                    send_telegram("✅ Payment Confirmed! You now have full access.", user_id)
                else:
                    send_admin(f"❌ Payment #{payment_id} not found")
            except Exception as e:
                send_admin(f"❌ Error: {e}")
            return True
        
        elif text.startswith('/reject_'):
            try:
                payment_id = int(text.replace('/reject_', ''))
                success = db.reject_payment(payment_id)
                if success:
                    payment = db.cursor.execute('SELECT user_id FROM payments WHERE id = ?', (payment_id,)).fetchone()
                    if payment:
                        send_telegram("❌ Payment Rejected. Please contact support.", payment[0])
                    send_admin(f"❌ Payment #{payment_id} REJECTED")
                else:
                    send_admin(f"❌ Payment #{payment_id} not found")
            except Exception as e:
                send_admin(f"❌ Error: {e}")
            return True
        
        elif text.startswith('/set '):
            try:
                parts = text[5:].split(' ', 1)
                if len(parts) != 2:
                    send_admin("❌ Format: /set key value")
                    return True
                key, value = parts
                value = value.strip('"').strip("'")
                db.update_setting(key, value)
                send_admin(f"✅ {key} = {value}")
            except Exception as e:
                send_admin(f"❌ Error: {e}")
            return True
        
        elif text == '/payments':
            payments = db.get_pending_payments()
            if not payments:
                send_admin("💳 No pending payments")
                return True
            msg = "💳 Pending Payments\n━━━━━━━━━━━━━━━━━━━━━━\n"
            for payment in payments[:10]:
                payment_id, user_id, payment_hash, amount, created_at = payment
                msg += f"""
#{payment_id} | User: {user_id}
💰 {amount}
🔑 {payment_hash[:30]}...
📅 {created_at[:16]}
/confirm_{payment_id} - Confirm
/reject_{payment_id} - Reject
━━━━━━━━━━━━━━━━━━━━━━
"""
            send_admin(msg)
            return True
        
        elif text == '/stats':
            stats = db.get_stats()
            msg = f"""
📊 STATISTICS
━━━━━━━━━━━━━━━━━━━━━━
👤 Users: {stats.get('users', 0)}
🟢 Active: {stats.get('active', 0)}
👑 Premium: {stats.get('premium', 0)}
📈 Signals: {stats.get('signals', 0)}
📊 Today: {stats.get('today', 0)}
💳 Pending: {stats.get('pending', 0)}
🎯 Win Rate: {stats.get('win_rate', 0)}%
🧠 Accuracy: {learner.get_accuracy()}%
✅ Wins: {learner.positive}
❌ Losses: {learner.negative}
"""
            send_admin(msg)
            return True
        
        elif text == '/help':
            msg = """
📚 ADMIN COMMANDS
━━━━━━━━━━━━━━━━━━━━━━

<b>📡 Signal Control:</b>
/on - Enable signals
/off - Disable signals

<b>💰 Payment Control:</b>
/pay_on - Enable payments
/pay_off - Disable payments
/payments - View pending
/confirm_ID - Confirm
/reject_ID - Reject

<b>⚙️ System:</b>
/set key value - Change setting
/aggressive - Aggressive mode
/standard - Standard mode
/stats - Statistics
/panel - Admin panel
/help - This help
"""
            send_admin(msg)
            return True
        
        return False
    except Exception as e:
        logger.error(f"Admin command error: {e}")
        return False

def handle_callback(callback_data, user_id):
    try:
        if callback_data.startswith('admin_'):
            return handle_admin_callback(callback_data)
        
        if callback_data.startswith('fb_'):
            parts = callback_data.split('_')
            if len(parts) != 3:
                return False
            feedback_type = parts[1]
            signal_id = int(parts[2])
            
            db.add_user(user_id)
            signal = db.get_signal(signal_id)
            
            # Check premium
            user = db.get_user(user_id)
            if user and user['is_active'] != 1:
                send_telegram("⚠️ Premium Access Required\n\nUse /subscribe to get access.", user_id)
                return False
            
            success, message = db.update_feedback(signal_id, feedback_type, user_id)
            if success:
                market_phase = signal['market_phase'] if signal else 'neutral'
                profit_pct = signal['profit_percent'] if signal else 0
                learner.add_feedback(feedback_type, market_phase, profit_pct)
                
                # Send detailed response to user
                if feedback_type == 'positive':
                    msg = f"""
✅ <b>Thank you for your feedback!</b>

💰 <b>Profit Confirmed!</b>
• System Accuracy: {learner.get_accuracy()}%
• Total Wins: {learner.positive}
• 📈 Keep winning! 🚀

<i>Your feedback helps us improve the algorithm!</i>
"""
                else:
                    msg = f"""
❌ <b>Thank you for your feedback!</b>

📊 <b>Loss Recorded</b>
• System Accuracy: {learner.get_accuracy()}%
• Total Losses: {learner.negative}
• 🔧 We'll improve!

<i>Your feedback helps us get better!</i>
"""
                send_telegram(msg, user_id)
                
                # Notify admin
                admin_msg = f"""
📊 <b>Feedback Received</b>
━━━━━━━━━━━━━━━━━━━━━━
👤 User: {user_id}
📈 Symbol: {signal['symbol'] if signal else 'N/A'}
📝 Feedback: {feedback_type}
🎯 Accuracy: {learner.get_accuracy()}%
✅ Wins: {learner.positive}
❌ Losses: {learner.negative}
"""
                send_admin(admin_msg)
                return True
            else:
                send_telegram(f"⚠️ {message}", user_id)
                return False
        
        if callback_data.startswith('analysis_'):
            signal_id = int(callback_data.replace('analysis_', ''))
            signal = db.get_signal(signal_id)
            if signal:
                msg = f"""
📊 <b>FULL ANALYSIS</b>
━━━━━━━━━━━━━━━━━━━━━━

<b>Symbol:</b> {signal['symbol']}
<b>Direction:</b> {signal['direction']}
<b>Confidence:</b> {signal['confidence']}%
<b>Quality:</b> {signal['quality_score']}/100

<b>📈 Indicators:</b>
• RSI: {signal['rsi']:.1f}
• MACD: {signal['macd']:.6f}
• MA20: ${signal['ma20']:.4f}
• MA50: ${signal['ma50']:.4f}
• VWAP: ${signal['vwap']:.4f}
• ATR: ${signal['atr']:.6f}
• ADX: {signal.get('adx', 0):.1f}
• Volatility: {signal.get('volatility', 0):.2f}%

<b>🛡️ Key Levels:</b>
• S1: ${signal.get('support1', 0):.4f}
• R1: ${signal.get('resistance1', 0):.4f}

<b>📊 Market Phase:</b> {signal.get('market_phase', 'neutral').upper()}
<b>📈 Trend Strength:</b> {signal.get('trend_strength', 0):.2f}
"""
                send_telegram(msg, user_id)
                return True
        
        return False
    except Exception as e:
        logger.error(f"Callback error: {e}")
        return False

# ============================================================
# PAYMENT HANDLER
# ============================================================

def handle_payment_hash(user_id, message_text):
    hash_pattern = r'[0-9a-fA-F]{64}|0x[0-9a-fA-F]{64}|[A-Za-z0-9]{50,}'
    match = re.search(hash_pattern, message_text)
    
    if not match:
        send_telegram("❌ Invalid transaction hash.\n\nPlease send a valid TXID.", user_id)
        return False
    
    payment_hash = match.group()
    
    existing = db.get_payment_by_hash(payment_hash)
    if existing:
        send_telegram("⚠️ This payment hash has already been submitted.", user_id)
        return False
    
    payment_id = db.add_payment(user_id, payment_hash)
    if payment_id:
        admin_msg = f"""
💳 <b>NEW PAYMENT</b>
━━━━━━━━━━━━━━━━━━━━━━
👤 User: {user_id}
💰 Amount: {db.get_setting('price') or PRICE}
🔑 Hash: {payment_hash}
📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}

✅ /confirm_{payment_id}
❌ /reject_{payment_id}
"""
        send_admin(admin_msg)
        send_telegram("✅ Payment submitted! Waiting for confirmation.", user_id)
        return True
    
    return False

def handle_subscribe(user_id):
    user = db.get_user(user_id)
    if user and user['is_active'] == 1:
        expire = user['subscription_expire']
        if expire:
            days_left = (datetime.fromisoformat(expire) - datetime.now()).days
            if days_left > 0:
                send_telegram(f"✅ Already subscribed!\n\n📅 {days_left} days remaining.", user_id)
                return True
    
    wallet = db.get_setting('wallet') or WALLET_ADDRESS
    price = db.get_setting('price') or PRICE
    
    msg = f"""
💳 <b>SUBSCRIPTION</b>
━━━━━━━━━━━━━━━━━━━━━━

💰 <b>Price:</b> {price}
📡 <b>Network:</b> TRC20 (USDT)

<b>🏦 Wallet:</b>
<code>{wallet}</code>

<b>📝 Steps:</b>
1. Send {price} USDT (TRC20)
2. Copy transaction hash
3. Send hash to this bot
4. Wait for confirmation

<i>⚠️ Send exact amount via TRC20 only!</i>
"""
    send_telegram(msg, user_id)
    return True

# ============================================================
# MAIN LOOP
# ============================================================

def main_loop():
    logger.info("🚀 Starting Quantum Signal Bot V18...")
    
    # Send welcome to admin with panel
    show_admin_panel()
    
    cycle = 0
    
    while True:
        try:
            cycle += 1
            
            if db.get_setting('signal_enabled') != '1':
                time.sleep(30)
                continue
            
            max_signals = int(db.get_setting('max_signals') or 5)
            min_confidence = int(db.get_setting('min_confidence') or 60)
            
            logger.info(f"🔄 Cycle {cycle} - Scanning {len(SYMBOLS)} symbols")
            
            signals = []
            for symbol in SYMBOLS:
                try:
                    signal = ultra_market_analysis(symbol)
                    if signal and signal.get('confidence', 0) >= min_confidence:
                        signals.append(signal)
                        logger.info(f"✅ {signal['symbol']}: {signal['signal']} ({signal['confidence']}%) - Profit: {signal.get('profit_percent', 0)}%")
                except Exception as e:
                    logger.error(f"Error processing {symbol}: {e}")
                time.sleep(0.03)
            
            signals.sort(key=lambda x: (x.get('quality_score', 0), x.get('confidence', 0)), reverse=True)
            signals = signals[:max_signals]
            
            if signals:
                for signal in signals:
                    try:
                        signal_id = db.save_signal(signal)
                        if signal_id:
                            msg, keyboard = build_signal_message(signal, signal_id)
                            if msg:
                                if send_telegram(msg, reply_markup=keyboard):
                                    db.mark_signal_sent(signal_id)
                                    logger.info(f"✅ Sent: {signal['symbol']}")
                                    # Send to premium users
                                    premium_users = db.cursor.execute('''
                                        SELECT user_id FROM users WHERE is_active = 1 AND is_premium = 1
                                    ''').fetchall()
                                    for user in premium_users:
                                        try:
                                            send_telegram(msg, user[0], keyboard)
                                            time.sleep(0.05)
                                        except:
                                            pass
                            time.sleep(2)
                    except Exception as e:
                        logger.error(f"Error sending signal: {e}")
            else:
                if cycle % 3 == 0:
                    logger.info("⏳ No high-quality signals found")
            
            if cycle % 3 == 0:
                payments = db.get_pending_payments()
                if payments:
                    send_admin(f"💳 {len(payments)} pending payments - Use /payments")
            
            if cycle % 20 == 0:
                stats = db.get_stats()
                send_admin(f"""
🔄 <b>SYSTEM STATUS UPDATE</b>
━━━━━━━━━━━━━━━━━━━━━━
📊 Today: {stats.get('today', 0)}
📈 Total: {stats.get('signals', 0)}
🎯 Win Rate: {stats.get('win_rate', 0)}%
🧠 Accuracy: {learner.get_accuracy()}%
👑 Premium: {stats.get('premium', 0)}
💳 Pending: {stats.get('pending', 0)}
""")
            
            logger.info(f"⏱ Waiting {INTERVAL//60} minutes...")
            time.sleep(INTERVAL)
            
        except Exception as e:
            logger.error(f"❌ Main loop error: {e}")
            send_admin(f"❌ <b>Error:</b> {str(e)}")
            time.sleep(60)

# ============================================================
# MESSAGE HANDLER
# ============================================================

def process_message(message):
    try:
        if 'message' not in message:
            return
        msg = message['message']
        if 'text' not in msg:
            return
        
        text = msg['text']
        user_id = msg['from']['id']
        username = msg['from'].get('username', '')
        first_name = msg['from'].get('first_name', '')
        
        db.add_user(user_id, username, first_name)
        
        if text.startswith('/'):
            if user_id == ADMIN_ID:
                handle_admin_command(text)
            else:
                if text == '/start':
                    send_telegram("""
🚀 <b>ULTIMATE SIGNAL BOT V18</b>
🤖 <b>Quantum Pro Max Ultra</b>

📊 Professional trading signals with 5000X analysis power.

<b>📌 Commands:</b>
/subscribe - Premium access
/help - Help
/status - Subscription

<b>🔐 Features:</b>
• 10 Timeframe Analysis
• 15+ Advanced Indicators
• FFT & Regression Analysis
• 30%+ Profit Targets
• AI Learning System

<i>Start winning today! 🚀</i>
""", user_id)
                elif text == '/subscribe':
                    handle_subscribe(user_id)
                elif text == '/help':
                    send_telegram(f"""
📚 <b>HELP CENTER</b>
━━━━━━━━━━━━━━━━━━━━━━

<b>📌 Commands:</b>
/start - Welcome
/subscribe - Get premium
/status - Check subscription

<b>💳 Subscribe:</b>
1. /subscribe
2. Send {db.get_setting('price') or PRICE} USDT
3. Send TXID hash
4. Wait confirmation

<b>📊 Signals:</b>
• BUY - Long positions
• SELL - Short positions
• 3 TP levels included
• Stop loss included

<b>🆘 Support:</b>
Contact @davnold
""", user_id)
                elif text == '/status':
                    user = db.get_user(user_id)
                    if user and user['is_active'] == 1:
                        expire = user['subscription_expire']
                        if expire:
                            days_left = (datetime.fromisoformat(expire) - datetime.now()).days
                            if days_left > 0:
                                send_telegram(f"✅ <b>Premium Active</b>\n\n📅 {days_left} days remaining\n🎯 Accuracy: {learner.get_accuracy()}%\n\n🚀 Keep winning!", user_id)
                            else:
                                send_telegram("⏰ <b>Subscription Expired</b>\n\nRenew with /subscribe", user_id)
                        else:
                            send_telegram("⚠️ <b>No Active Subscription</b>\n\nUse /subscribe", user_id)
                    else:
                        send_telegram("⚠️ <b>No Active Subscription</b>\n\nUse /subscribe", user_id)
            return
        
        # Payment hash
        if user_id != ADMIN_ID and db.get_setting('payment_enabled') == '1':
            hash_pattern = r'[0-9a-fA-F]{64}|0x[0-9a-fA-F]{64}|[A-Za-z0-9]{50,}'
            if re.search(hash_pattern, text):
                handle_payment_hash(user_id, text)
        
    except Exception as e:
        logger.error(f"Message error: {e}")

# ============================================================
# BOT RUNNER
# ============================================================

def get_updates(offset=None):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
        params = {'timeout': 30, 'allowed_updates': ['message', 'callback_query']}
        if offset:
            params['offset'] = offset
        response = requests.get(url, params=params, timeout=35)
        if response.status_code == 200:
            return response.json().get('result', [])
    except Exception as e:
        logger.error(f"Get updates error: {e}")
    return []

def run_bot():
    logger.info("🤖 Starting Telegram Bot...")
    offset = None
    
    while True:
        try:
            updates = get_updates(offset)
            for update in updates:
                offset = update['update_id'] + 1
                
                if 'message' in update:
                    process_message(update['message'])
                
                if 'callback_query' in update:
                    callback = update['callback_query']
                    user_id = callback['from']['id']
                    data = callback['data']
                    
                    try:
                        url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
                        requests.post(url, data={'callback_query_id': callback['id']})
                    except:
                        pass
                    
                    handle_callback(data, user_id)
            
            time.sleep(1)
        except Exception as e:
            logger.error(f"Bot runner error: {e}")
            time.sleep(5)

# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    try:
        print("\n" + "="*70)
        print("🚀 ULTIMATE SIGNAL BOT V18 - QUANTUM PRO MAX ULTRA")
        print("="*70)
        print(f"📊 Symbols: {len(SYMBOLS)}")
        print(f"⏱ Interval: {INTERVAL//60} minutes")
        print(f"📢 Channel: {CHANNEL_ID}")
        print(f"💳 Price: {PRICE}")
        print(f"🧠 Analysis: 5000X Stronger with Scipy")
        print(f"🔬 Indicators: 15+ Advanced + FFT + Regression")
        print("="*70)
        print("🤖 Starting bot...\n")
        
        # Test connection
        test = get_candles('BTCUSDT', 10)
        if test:
            logger.info("✅ Binance connection OK")
        else:
            logger.warning("⚠️ Binance connection issue")
        
        # Start signal generator
        signal_thread = threading.Thread(target=main_loop, daemon=True)
        signal_thread.start()
        logger.info("✅ Signal generator started")
        
        # Start bot
        run_bot()
        
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")