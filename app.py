# ============================================================
# ULTIMATE SIGNAL BOT V21 - QUANTUM PRO MAX ULTRA
# 10000X STRONGER | FULLY FUNCTIONAL BUTTONS | PERFECT FEEDBACK
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
MIN_CONFIDENCE = 55

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
                win_rate DECIMAL DEFAULT 0
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
                tp4 REAL,
                tp5 REAL,
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
                profit_percent1 DECIMAL DEFAULT 0,
                profit_percent2 DECIMAL DEFAULT 0,
                profit_percent3 DECIMAL DEFAULT 0,
                profit_percent4 DECIMAL DEFAULT 0,
                profit_percent5 DECIMAL DEFAULT 0,
                market_phase TEXT,
                volatility REAL,
                trend_strength REAL
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
            ('min_confidence', '55'),
            ('max_signals', '5'),
            ('payment_enabled', '1'),
            ('min_profit_target', '30'),
            ('risk_reward_ratio', '3.0'),
            ('aggressive_mode', '0'),
            ('broadcast_mode', '0'),
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
                symbol, direction, entry, tp1, tp2, tp3, tp4, tp5, sl, confidence,
                created_at, rsi, macd, ma20, ma50, ma200,
                vwap, atr, support1, support2, resistance1, resistance2,
                score, quality_score, reasons, profit_percent1, profit_percent2,
                profit_percent3, profit_percent4, profit_percent5,
                market_phase, volatility, trend_strength
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            signal_data['symbol'],
            signal_data['signal'],
            signal_data['entry'],
            signal_data.get('tp1', 0),
            signal_data.get('tp2', 0),
            signal_data.get('tp3', 0),
            signal_data.get('tp4', 0),
            signal_data.get('tp5', 0),
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
            signal_data.get('profit_percent1', 0),
            signal_data.get('profit_percent2', 0),
            signal_data.get('profit_percent3', 0),
            signal_data.get('profit_percent4', 0),
            signal_data.get('profit_percent5', 0),
            signal_data.get('market_phase', 'neutral'),
            signal_data.get('volatility', 0),
            signal_data.get('trend_strength', 0)
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
            self.cursor.execute('UPDATE users SET positive_feedback = positive_feedback + 1, feedback_count = feedback_count + 1 WHERE user_id = ?', (user_id,))
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
# 10000X STRONGER INDICATORS
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
        if len(prices) < period:
            return prices[-1] if prices else 0
        y = prices[-period:]
        fft_vals = fft(y)
        fft_vals[5:-5] = 0
        predicted = np.real(ifft(fft_vals))[-1]
        return round(predicted, 8)

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
    'WLDUSDT', 'PEPEUSDT', 'BONKUSDT', 'FLOKIUSDT', 'SHIBUSDT'
]

# ============================================================
# 10000X STRONGER MARKET ANALYSIS
# ============================================================

def ultra_market_analysis(symbol):
    """10000X stronger analysis with all indicators"""
    try:
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
            
            rsi = ui.calculate_rsi(prices, 14)
            macd, macd_signal, macd_hist = ui.calculate_macd(prices, 12, 26, 9)
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
            obv = ui.calculate_obv(prices, volumes)
            slope, r_value = ui.calculate_linear_regression(prices, 20)
            predicted_price = ui.calculate_fourier_prediction(prices, 50)
            
            score = 50
            reasons = []
            signals = []
            
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
            
            if current > vwap:
                score += 20
                reasons.append("✅ Above VWAP")
                signals.append('buy')
            else:
                score -= 20
                reasons.append("❌ Below VWAP")
                signals.append('sell')
            
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
            
            if stoch_k < 20:
                score += 20
                reasons.append(f"📊 Stochastic Oversold")
                signals.append('buy')
            elif stoch_k > 80:
                score -= 20
                reasons.append(f"📊 Stochastic Overbought")
                signals.append('sell')
            
            if cci < -100:
                score += 20
                reasons.append(f"📈 CCI Oversold")
                signals.append('buy')
            elif cci > 100:
                score -= 20
                reasons.append(f"📉 CCI Overbought")
                signals.append('sell')
            
            if williams_r < -80:
                score += 15
                reasons.append(f"📈 Williams Oversold")
                signals.append('buy')
            elif williams_r > -20:
                score -= 15
                reasons.append(f"📉 Williams Overbought")
                signals.append('sell')
            
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
            
            if obv > 0:
                score += 15
                reasons.append("📊 OBV Bullish")
                signals.append('buy')
            else:
                score -= 15
                reasons.append("📊 OBV Bearish")
                signals.append('sell')
            
            if slope > 0 and r_value > 0.3:
                score += 15
                reasons.append(f"📈 Uptrend (R={r_value:.2f})")
                signals.append('buy')
            elif slope < 0 and r_value < -0.3:
                score -= 15
                reasons.append(f"📉 Downtrend (R={r_value:.2f})")
                signals.append('sell')
            
            if predicted_price > current * 1.02:
                score += 15
                reasons.append(f"🔮 FFT Bullish")
                signals.append('buy')
            elif predicted_price < current * 0.98:
                score -= 15
                reasons.append(f"🔮 FFT Bearish")
                signals.append('sell')
            
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
        
        main_data = get_candles(symbol, 200, '5m')
        if not main_data:
            return None
        
        current = main_data['close'][-1]
        atr = QuantumIndicators.calculate_atr(main_data['high'], main_data['low'], main_data['close'], 14)
        
        min_profit = float(db.get_setting('min_profit_target') or 30)
        rr_ratio = float(db.get_setting('risk_reward_ratio') or 3.0)
        
        fib_ratios = [0.618, 1.0, 1.618, 2.618, 4.236]
        
        base_profit = min_profit
        if final_score > 70:
            base_profit = min_profit * 1.3
        elif final_score > 60:
            base_profit = min_profit * 1.15
        
        volatility_factor = 1 + (analysis_results.get('5m', {}).get('volatility', 0) / 100)
        base_profit = base_profit * min(volatility_factor, 1.5)
        
        profit_pcts = []
        for i, ratio in enumerate(fib_ratios[:5]):
            pct = round(base_profit * ratio, 2)
            if i == 0 and pct < 30:
                pct = 30
            profit_pcts.append(pct)
        
        profit_pcts = sorted(set(profit_pcts))
        while len(profit_pcts) < 5:
            profit_pcts.append(profit_pcts[-1] * 1.3)
        profit_pcts = profit_pcts[:5]
        profit_pcts.sort()
        
        if signal == "BUY":
            risk = atr * 1.2
            entry = current * 0.999
            
            support1 = analysis_results.get('5m', {}).get('support1', 0)
            if support1 > 0 and support1 < entry:
                sl = support1 * 0.998
            else:
                sl = entry - risk * 2.0
            
            tp1 = entry * (1 + profit_pcts[0] / 100)
            tp2 = entry * (1 + profit_pcts[1] / 100)
            tp3 = entry * (1 + profit_pcts[2] / 100)
            tp4 = entry * (1 + profit_pcts[3] / 100)
            tp5 = entry * (1 + profit_pcts[4] / 100)
            
            resistance1 = analysis_results.get('5m', {}).get('resistance1', 0)
            if resistance1 > 0:
                levels = [tp1, tp2, tp3, tp4, tp5]
                for i, tp in enumerate(levels):
                    if tp > resistance1:
                        levels[i] = resistance1 * 0.998
                tp1, tp2, tp3, tp4, tp5 = levels
            
            actual_rr = ((tp1 - entry) / abs(entry - sl)) if abs(entry - sl) > 0 else 0
            if actual_rr < rr_ratio:
                tp1 = entry + (abs(entry - sl) * rr_ratio)
                scale = tp1 / (entry * (1 + profit_pcts[0] / 100))
                tp2 = entry * (1 + profit_pcts[1] / 100 * scale)
                tp3 = entry * (1 + profit_pcts[2] / 100 * scale)
                tp4 = entry * (1 + profit_pcts[3] / 100 * scale)
                tp5 = entry * (1 + profit_pcts[4] / 100 * scale)
            
            profit_percent1 = round((tp1 - entry) / entry * 100, 2)
            profit_percent2 = round((tp2 - entry) / entry * 100, 2)
            profit_percent3 = round((tp3 - entry) / entry * 100, 2)
            profit_percent4 = round((tp4 - entry) / entry * 100, 2)
            profit_percent5 = round((tp5 - entry) / entry * 100, 2)
            
        else:
            risk = atr * 1.2
            entry = current * 1.001
            
            resistance1 = analysis_results.get('5m', {}).get('resistance1', 0)
            if resistance1 > 0 and resistance1 > entry:
                sl = resistance1 * 1.002
            else:
                sl = entry + risk * 2.0
            
            tp1 = entry * (1 - profit_pcts[0] / 100)
            tp2 = entry * (1 - profit_pcts[1] / 100)
            tp3 = entry * (1 - profit_pcts[2] / 100)
            tp4 = entry * (1 - profit_pcts[3] / 100)
            tp5 = entry * (1 - profit_pcts[4] / 100)
            
            support1 = analysis_results.get('5m', {}).get('support1', 0)
            if support1 > 0:
                levels = [tp1, tp2, tp3, tp4, tp5]
                for i, tp in enumerate(levels):
                    if tp < support1:
                        levels[i] = support1 * 1.002
                tp1, tp2, tp3, tp4, tp5 = levels
            
            actual_rr = ((entry - tp1) / abs(sl - entry)) if abs(sl - entry) > 0 else 0
            if actual_rr < rr_ratio:
                tp1 = entry - (abs(sl - entry) * rr_ratio)
                scale = tp1 / (entry * (1 - profit_pcts[0] / 100))
                tp2 = entry * (1 - profit_pcts[1] / 100 * scale)
                tp3 = entry * (1 - profit_pcts[2] / 100 * scale)
                tp4 = entry * (1 - profit_pcts[3] / 100 * scale)
                tp5 = entry * (1 - profit_pcts[4] / 100 * scale)
            
            profit_percent1 = round((entry - tp1) / entry * 100, 2)
            profit_percent2 = round((entry - tp2) / entry * 100, 2)
            profit_percent3 = round((entry - tp3) / entry * 100, 2)
            profit_percent4 = round((entry - tp4) / entry * 100, 2)
            profit_percent5 = round((entry - tp5) / entry * 100, 2)
        
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
            'tp4': round(tp4, 8),
            'tp5': round(tp5, 8),
            'sl': round(sl, 8),
            'profit_percent1': profit_percent1,
            'profit_percent2': profit_percent2,
            'profit_percent3': profit_percent3,
            'profit_percent4': profit_percent4,
            'profit_percent5': profit_percent5,
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
# LEARNING SYSTEM
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
    
    p1 = signal.get('profit_percent1', 0)
    p2 = signal.get('profit_percent2', 0)
    p3 = signal.get('profit_percent3', 0)
    p4 = signal.get('profit_percent4', 0)
    p5 = signal.get('profit_percent5', 0)
    
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
<b>🛑 SL:</b> <code>${signal['sl']:.6f}</code>

<b>🎯 PROFIT TARGETS:</b>
• TP1: <code>${signal['tp1']:.6f}</code> <i>(+{p1:.1f}%)</i> ⭐
• TP2: <code>${signal['tp2']:.6f}</code> <i>(+{p2:.1f}%)</i>
• TP3: <code>${signal['tp3']:.6f}</code> <i>(+{p3:.1f}%)</i>
• TP4: <code>${signal['tp4']:.6f}</code> <i>(+{p4:.1f}%)</i>
• TP5: <code>${signal['tp5']:.6f}</code> <i>(+{p5:.1f}%)</i> 🚀

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

<b>🛡️ KEY LEVELS:</b>
• S1: ${signal.get('support1', 0):.4f}
• R1: ${signal.get('resistance1', 0):.4f}

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
                {'text': '✅ سود کردم 💰', 'callback_data': f'fb_positive_{signal_id}'},
                {'text': '❌ سود نکردم', 'callback_data': f'fb_negative_{signal_id}'}
            ],
            [
                {'text': '📊 تحلیل کامل', 'callback_data': f'analysis_{signal_id}'}
            ]
        ]
    }
    
    return msg, keyboard

# ============================================================
# ADMIN PANEL - FULLY FUNCTIONAL WITH 10 BUTTONS
# ============================================================

ADMIN_PANEL_BUTTONS = {
    'inline_keyboard': [
        [
            {'text': '🟢 فعال‌سازی سیگنال', 'callback_data': 'admin_signal_on'},
            {'text': '🔴 غیرفعال‌سازی سیگنال', 'callback_data': 'admin_signal_off'}
        ],
        [
            {'text': '💰 فعال‌سازی پرداخت', 'callback_data': 'admin_pay_on'},
            {'text': '💳 غیرفعال‌سازی پرداخت', 'callback_data': 'admin_pay_off'}
        ],
        [
            {'text': '📊 آمار کامل', 'callback_data': 'admin_stats'},
            {'text': '💳 پرداخت‌های در انتظار', 'callback_data': 'admin_payments'}
        ],
        [
            {'text': '⚙️ تنظیمات', 'callback_data': 'admin_settings'},
            {'text': '🔄 ریست یادگیری', 'callback_data': 'admin_reset'}
        ],
        [
            {'text': '📢 ارسال پیام همگانی', 'callback_data': 'admin_broadcast'},
            {'text': '🔄 رفرش پنل', 'callback_data': 'admin_refresh'}
        ]
    ]
}

def show_admin_panel(chat_id=None):
    """نمایش پنل مدیریت با ۱۰ دکمه کاملاً کاربردی"""
    if chat_id is None:
        chat_id = ADMIN_ID
    
    settings = db.get_all_settings()
    stats = db.get_stats()
    
    signal_enabled = settings.get('signal_enabled', '0') == '1'
    payment_enabled = settings.get('payment_enabled', '0') == '1'
    aggressive = settings.get('aggressive_mode', '0') == '1'
    
    msg = f"""
🔐 <b>🚀 پنل مدیریت ربات V21</b>
━━━━━━━━━━━━━━━━━━━━━━

<b>📡 وضعیت سیستم:</b>
• 🤖 ربات: 🟢 فعال
• 📡 ارسال سیگنال: {'🟢 فعال' if signal_enabled else '🔴 غیرفعال'}
• 💳 حالت پولی: {'🟢 فعال' if payment_enabled else '🔴 غیرفعال'}
• ⚡ مود: {'🔥 تهاجمی' if aggressive else '📊 استاندارد'}

<b>📈 آمار:</b>
• 👤 کاربران: {stats.get('users', 0)}
• 🟢 فعال: {stats.get('active', 0)}
• 👑 پریمیوم: {stats.get('premium', 0)}
• 📊 سیگنال امروز: {stats.get('today', 0)}
• 📈 کل سیگنال‌ها: {stats.get('signals', 0)}
• 🎯 نرخ برد: {stats.get('win_rate', 0)}%
• 💳 پرداخت‌های در انتظار: {stats.get('pending', 0)}

<b>⚙️ تنظیمات:</b>
• 🎯 حداقل اطمینان: {settings.get('min_confidence', 55)}%
• 📊 حداکثر سیگنال: {settings.get('max_signals', 5)}
• 💰 قیمت اشتراک: {settings.get('price', PRICE)}
• 📈 حداقل سود: {settings.get('min_profit_target', 30)}%
• 🎯 نسبت ریسک/ریوارد: {settings.get('risk_reward_ratio', 3.0)}

<b>🧠 سیستم یادگیری:</b>
• دقت: {learner.get_accuracy()}%
• ✅ برد: {learner.positive}
• ❌ باخت: {learner.negative}

━━━━━━━━━━━━━━━━━━━━━━
<b>📌 برای مدیریت کلیک کنید:</b>
"""
    
    send_telegram(msg, chat_id, ADMIN_PANEL_BUTTONS)

def handle_admin_callback(callback_data):
    """مدیریت تمام دکمه‌های پنل ادمین - کاملاً کاربردی"""
    try:
        # ===== دکمه 1: فعال‌سازی سیگنال =====
        if callback_data == 'admin_signal_on':
            db.update_setting('signal_enabled', '1')
            send_admin("✅ <b>ارسال سیگنال فعال شد</b>\n\n📡 سیگنال‌ها به کانال ارسال می‌شوند.")
            show_admin_panel()
            return True
        
        # ===== دکمه 2: غیرفعال‌سازی سیگنال =====
        elif callback_data == 'admin_signal_off':
            db.update_setting('signal_enabled', '0')
            send_admin("🔴 <b>ارسال سیگنال غیرفعال شد</b>\n\n📡 ارسال سیگنال متوقف شد.")
            show_admin_panel()
            return True
        
        # ===== دکمه 3: فعال‌سازی پرداخت =====
        elif callback_data == 'admin_pay_on':
            db.update_setting('payment_enabled', '1')
            send_admin("💰 <b>حالت پولی فعال شد</b>\n\n💳 کاربران می‌توانند اشتراک خریداری کنند.")
            show_admin_panel()
            return True
        
        # ===== دکمه 4: غیرفعال‌سازی پرداخت =====
        elif callback_data == 'admin_pay_off':
            db.update_setting('payment_enabled', '0')
            send_admin("💳 <b>حالت پولی غیرفعال شد</b>\n\n💰 خرید اشتراک متوقف شد.")
            show_admin_panel()
            return True
        
        # ===== دکمه 5: آمار کامل =====
        elif callback_data == 'admin_stats':
            stats = db.get_stats()
            msg = f"""
📊 <b>آمار کامل سیستم</b>
━━━━━━━━━━━━━━━━━━━━━━

<b>👤 کاربران:</b>
• کل: {stats.get('users', 0)}
• فعال: {stats.get('active', 0)}
• پریمیوم: {stats.get('premium', 0)}

<b>📊 سیگنال‌ها:</b>
• کل: {stats.get('signals', 0)}
• امروز: {stats.get('today', 0)}

<b>💳 پرداخت‌ها:</b>
• در انتظار: {stats.get('pending', 0)}

<b>📝 عملکرد:</b>
• نرخ برد: {stats.get('win_rate', 0)}%
• بردها: {stats.get('wins', 0)}
• میانگین سود: ${stats.get('avg_profit', 0)}

<b>🧠 یادگیری:</b>
• دقت: {learner.get_accuracy()}%
• مثبت: {learner.positive}
• منفی: {learner.negative}
"""
            send_admin(msg)
            return True
        
        # ===== دکمه 6: پرداخت‌های در انتظار =====
        elif callback_data == 'admin_payments':
            payments = db.get_pending_payments()
            if not payments:
                send_admin("💳 <b>هیچ پرداخت در انتظاری وجود ندارد</b>")
                return True
            
            msg = f"💳 <b>پرداخت‌های در انتظار</b> ({len(payments)})\n━━━━━━━━━━━━━━━━━━━━━━\n"
            for payment in payments[:10]:
                payment_id, user_id, payment_hash, amount, created_at = payment
                msg += f"""
📌 <b>#{payment_id}</b>
👤 کاربر: {user_id}
💰 مبلغ: {amount}
🔑 هش: <code>{payment_hash[:30]}...</code>
📅 زمان: {created_at[:16]}
✅ /confirm_{payment_id}
❌ /reject_{payment_id}
━━━━━━━━━━━━━━━━━━━━━━
"""
            send_admin(msg)
            return True
        
        # ===== دکمه 7: تنظیمات =====
        elif callback_data == 'admin_settings':
            settings = db.get_all_settings()
            msg = "⚙️ <b>تنظیمات سیستم</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
            for key, value in settings.items():
                msg += f"\n📌 <b>{key}:</b> <code>{value}</code>"
            msg += """
━━━━━━━━━━━━━━━━━━━━━━
<b>✏️ تغییر تنظیمات:</b>
<code>/set min_confidence 75</code>
<code>/set max_signals 3</code>
<code>/set min_profit_target 40</code>
<code>/set risk_reward_ratio 4</code>
"""
            send_admin(msg)
            return True
        
        # ===== دکمه 8: ریست یادگیری =====
        elif callback_data == 'admin_reset':
            learner.positive = 0
            learner.negative = 0
            for key in learner.weights:
                learner.weights[key] = 1.0
            for key in learner.market_weights:
                learner.market_weights[key] = 1.0
            learner.save()
            send_admin("🔄 <b>سیستم یادگیری ریست شد</b>\n\n🧠 تمام داده‌های یادگیری به حالت اولیه بازگشت.")
            show_admin_panel()
            return True
        
        # ===== دکمه 9: ارسال پیام همگانی =====
        elif callback_data == 'admin_broadcast':
            db.update_setting('broadcast_mode', '1')
            send_admin("📢 <b>حالت ارسال همگانی فعال شد</b>\n\nلطفاً پیام خود را ارسال کنید.\n\n<i>پیام برای همه کاربران ارسال خواهد شد.</i>")
            return True
        
        # ===== دکمه 10: رفرش پنل =====
        elif callback_data == 'admin_refresh':
            show_admin_panel()
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Admin callback error: {e}")
        send_admin(f"❌ <b>خطا:</b> {str(e)}")
        return False

def handle_admin_command(text):
    """مدیریت دستورات متنی ادمین"""
    try:
        if text == '/panel' or text == '/start':
            show_admin_panel()
            return True
        
        elif text == '/on':
            db.update_setting('signal_enabled', '1')
            send_admin("✅ سیگنال فعال شد")
            show_admin_panel()
            return True
        
        elif text == '/off':
            db.update_setting('signal_enabled', '0')
            send_admin("🔴 سیگنال غیرفعال شد")
            show_admin_panel()
            return True
        
        elif text == '/pay_on':
            db.update_setting('payment_enabled', '1')
            send_admin("💰 پرداخت فعال شد")
            show_admin_panel()
            return True
        
        elif text == '/pay_off':
            db.update_setting('payment_enabled', '0')
            send_admin("💳 پرداخت غیرفعال شد")
            show_admin_panel()
            return True
        
        elif text.startswith('/confirm_'):
            try:
                payment_id = int(text.replace('/confirm_', ''))
                success, user_id = db.confirm_payment(payment_id)
                if success:
                    send_admin(f"✅ پرداخت #{payment_id} تایید شد")
                    send_telegram("✅ پرداخت شما تایید شد! اشتراک شما فعال شد.", user_id)
                    show_admin_panel()
                else:
                    send_admin(f"❌ پرداخت #{payment_id} یافت نشد")
            except Exception as e:
                send_admin(f"❌ خطا: {e}")
            return True
        
        elif text.startswith('/reject_'):
            try:
                payment_id = int(text.replace('/reject_', ''))
                success = db.reject_payment(payment_id)
                if success:
                    payment = db.cursor.execute('SELECT user_id FROM payments WHERE id = ?', (payment_id,)).fetchone()
                    if payment:
                        send_telegram("❌ پرداخت شما رد شد. لطفاً با پشتیبانی تماس بگیرید.", payment[0])
                    send_admin(f"❌ پرداخت #{payment_id} رد شد")
                    show_admin_panel()
                else:
                    send_admin(f"❌ پرداخت #{payment_id} یافت نشد")
            except Exception as e:
                send_admin(f"❌ خطا: {e}")
            return True
        
        elif text.startswith('/set '):
            try:
                parts = text[5:].split(' ', 1)
                if len(parts) != 2:
                    send_admin("❌ فرمت: /set کلید مقدار")
                    return True
                key, value = parts
                value = value.strip('"').strip("'")
                db.update_setting(key, value)
                send_admin(f"✅ {key} = {value}")
                show_admin_panel()
            except Exception as e:
                send_admin(f"❌ خطا: {e}")
            return True
        
        elif text == '/payments':
            payments = db.get_pending_payments()
            if not payments:
                send_admin("💳 هیچ پرداخت در انتظاری وجود ندارد")
                return True
            msg = "💳 پرداخت‌های در انتظار\n━━━━━━━━━━━━━━━━━━━━━━\n"
            for payment in payments[:10]:
                payment_id, user_id, payment_hash, amount, created_at = payment
                msg += f"""
#{payment_id} | کاربر: {user_id}
💰 {amount}
🔑 {payment_hash[:30]}...
📅 {created_at[:16]}
/confirm_{payment_id} - تایید
/reject_{payment_id} - رد
━━━━━━━━━━━━━━━━━━━━━━
"""
            send_admin(msg)
            return True
        
        elif text == '/stats':
            stats = db.get_stats()
            msg = f"""
📊 آمار کامل
━━━━━━━━━━━━━━━━━━━━━━
👤 کاربران: {stats.get('users', 0)}
🟢 فعال: {stats.get('active', 0)}
👑 پریمیوم: {stats.get('premium', 0)}
📈 سیگنال‌ها: {stats.get('signals', 0)}
📊 امروز: {stats.get('today', 0)}
💳 در انتظار: {stats.get('pending', 0)}
🎯 نرخ برد: {stats.get('win_rate', 0)}%
🧠 دقت: {learner.get_accuracy()}%
✅ برد: {learner.positive}
❌ باخت: {learner.negative}
"""
            send_admin(msg)
            return True
        
        elif text == '/help':
            msg = """
📚 راهنمای دستورات ادمین
━━━━━━━━━━━━━━━━━━━━━━

<b>📡 کنترل سیگنال:</b>
/panel - نمایش پنل مدیریت
/on - فعال‌سازی سیگنال
/off - غیرفعال‌سازی سیگنال

<b>💰 کنترل پرداخت:</b>
/pay_on - فعال‌سازی پرداخت
/pay_off - غیرفعال‌سازی پرداخت
/payments - مشاهده پرداخت‌ها
/confirm_ID - تایید پرداخت
/reject_ID - رد پرداخت

<b>⚙️ سیستم:</b>
/set کلید مقدار - تغییر تنظیمات
/stats - آمار کامل
/help - این راهنما
"""
            send_admin(msg)
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Admin command error: {e}")
        return False

def handle_broadcast_message(user_id, text):
    """مدیریت ارسال پیام همگانی"""
    try:
        users = db.cursor.execute('SELECT user_id FROM users').fetchall()
        
        if not users:
            send_admin("⚠️ <b>هیچ کاربری برای ارسال پیام وجود ندارد</b>")
            db.update_setting('broadcast_mode', '0')
            return
        
        sent = 0
        for user in users:
            try:
                send_telegram(f"📢 <b>پیام همگانی از ادمین</b>\n━━━━━━━━━━━━━━━━━━━━━━\n\n{text}", user[0])
                sent += 1
                time.sleep(0.1)
            except:
                pass
        
        send_admin(f"✅ <b>پیام همگانی ارسال شد</b>\n\n📨 تعداد دریافت‌کنندگان: {sent}")
        db.update_setting('broadcast_mode', '0')
        
    except Exception as e:
        logger.error(f"Broadcast error: {e}")
        send_admin(f"❌ <b>خطا در ارسال پیام همگانی:</b> {str(e)}")
        db.update_setting('broadcast_mode', '0')

# ============================================================
# HANDLE FEEDBACK BUTTONS - FULLY FUNCTIONAL
# ============================================================

def handle_feedback_callback(callback_data, user_id):
    """Handle feedback button clicks - FULLY FUNCTIONAL with immediate response"""
    try:
        if not callback_data.startswith('fb_'):
            return False
        
        parts = callback_data.split('_')
        if len(parts) != 3:
            return False
        
        feedback_type = parts[1]
        signal_id = int(parts[2])
        
        db.add_user(user_id)
        
        signal = db.get_signal(signal_id)
        
        success, message = db.update_feedback(signal_id, feedback_type, user_id)
        
        if not success:
            send_telegram(f"⚠️ {message}", user_id)
            return False
        
        market_phase = signal['market_phase'] if signal else 'neutral'
        profit_pct = signal['profit_percent1'] if signal else 0
        learner.add_feedback(feedback_type, market_phase, profit_pct)
        
        if feedback_type == 'positive':
            response_msg = f"""
✅ <b>تبریک! سود کردید! 💰</b>
━━━━━━━━━━━━━━━━━━━━━━

📊 <b>نتیجه:</b> سود ✅
🎯 <b>دقت سیستم:</b> {learner.get_accuracy()}%
✅ <b>کل بردها:</b> {learner.positive}
❌ <b>کل باخت‌ها:</b> {learner.negative}

<i>🌟 بازخورد شما به بهبود الگوریتم کمک می‌کند!</i>

🚀 <b>به سوددهی ادامه دهید!</b>
"""
        else:
            response_msg = f"""
❌ <b>متاسفم! دفعه بعد حتماً موفق می‌شوید!</b>
━━━━━━━━━━━━━━━━━━━━━━

📊 <b>نتیجه:</b> باخت ❌
🎯 <b>دقت سیستم:</b> {learner.get_accuracy()}%
✅ <b>کل بردها:</b> {learner.positive}
❌ <b>کل باخت‌ها:</b> {learner.negative}

<i>🔧 بازخورد شما به بهبود الگوریتم کمک می‌کند!</i>

💪 <b>به تلاش ادامه دهید!</b>
"""
        
        send_telegram(response_msg, user_id)
        
        admin_msg = f"""
📊 <b>بازخورد جدید</b>
━━━━━━━━━━━━━━━━━━━━━━
👤 کاربر: {user_id}
📈 نماد: {signal['symbol'] if signal else 'N/A'}
📝 بازخورد: {'✅ سود کردم' if feedback_type == 'positive' else '❌ سود نکردم'}
🎯 دقت سیستم: {learner.get_accuracy()}%
✅ برد: {learner.positive}
❌ باخت: {learner.negative}
"""
        send_admin(admin_msg)
        
        return True
        
    except Exception as e:
        logger.error(f"Feedback callback error: {e}")
        send_telegram(f"❌ <b>خطا:</b> {str(e)}", user_id)
        return False

# ============================================================
# MAIN CALLBACK HANDLER
# ============================================================

def handle_callback(callback_data, user_id):
    """Main callback handler - routes to appropriate handler"""
    try:
        if callback_data.startswith('admin_'):
            return handle_admin_callback(callback_data)
        
        if callback_data.startswith('fb_'):
            return handle_feedback_callback(callback_data, user_id)
        
        if callback_data.startswith('analysis_'):
            signal_id = int(callback_data.replace('analysis_', ''))
            signal = db.get_signal(signal_id)
            if signal:
                msg = f"""
📊 <b>تحلیل کامل</b>
━━━━━━━━━━━━━━━━━━━━━━

<b>نماد:</b> {signal['symbol']}
<b>جهت:</b> {signal['direction']}
<b>اطمینان:</b> {signal['confidence']}%
<b>کیفیت:</b> {signal['quality_score']}/100

<b>📈 اندیکاتورها:</b>
• RSI: {signal['rsi']:.1f}
• MACD: {signal['macd']:.6f}
• MA20: ${signal['ma20']:.4f}
• MA50: ${signal['ma50']:.4f}
• VWAP: ${signal['vwap']:.4f}
• ATR: ${signal['atr']:.6f}
• ADX: {signal.get('adx', 0):.1f}
• نوسان: {signal.get('volatility', 0):.2f}%

<b>🛡️ سطوح کلیدی:</b>
• S1: ${signal.get('support1', 0):.4f}
• R1: ${signal.get('resistance1', 0):.4f}

<b>📊 فاز بازار:</b> {signal.get('market_phase', 'خنثی').upper()}
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
        send_telegram("❌ هش تراکنش نامعتبر\n\nلطفاً یک هش معتبر ارسال کنید.", user_id)
        return False
    
    payment_hash = match.group()
    
    existing = db.get_payment_by_hash(payment_hash)
    if existing:
        send_telegram("⚠️ این هش قبلاً ثبت شده است.", user_id)
        return False
    
    payment_id = db.add_payment(user_id, payment_hash)
    if payment_id:
        admin_msg = f"""
💳 <b>پرداخت جدید</b>
━━━━━━━━━━━━━━━━━━━━━━
👤 کاربر: {user_id}
💰 مبلغ: {db.get_setting('price') or PRICE}
🔑 هش: {payment_hash}
📅 زمان: {datetime.now().strftime('%Y-%m-%d %H:%M')}

✅ /confirm_{payment_id}
❌ /reject_{payment_id}
"""
        send_admin(admin_msg)
        send_telegram("✅ هش پرداخت ثبت شد!\n\n⏳ در انتظار تایید ادمین.", user_id)
        return True
    
    return False

def handle_subscribe(user_id):
    user = db.get_user(user_id)
    if user and user['is_active'] == 1:
        expire = user['subscription_expire']
        if expire:
            days_left = (datetime.fromisoformat(expire) - datetime.now()).days
            if days_left > 0:
                send_telegram(f"✅ قبلاً اشتراک دارید!\n\n📅 {days_left} روز باقی مانده.", user_id)
                return True
    
    wallet = db.get_setting('wallet') or WALLET_ADDRESS
    price = db.get_setting('price') or PRICE
    
    msg = f"""
💳 <b>اشتراک</b>
━━━━━━━━━━━━━━━━━━━━━━

💰 <b>مبلغ:</b> {price}
📡 <b>شبکه:</b> TRC20 (USDT)

<b>🏦 آدرس کیف پول:</b>
<code>{wallet}</code>

<b>📝 مراحل:</b>
1. ارسال {price} USDT (TRC20)
2. کپی هش تراکنش
3. ارسال هش به این ربات
4. منتظر تایید ادمین

<i>⚠️ فقط از طریق TRC20 ارسال کنید!</i>
"""
    send_telegram(msg, user_id)
    return True

# ============================================================
# MAIN LOOP
# ============================================================

def main_loop():
    logger.info("🚀 Starting Quantum Signal Bot V21...")
    
    # نمایش پنل ادمین در ابتدا
    show_admin_panel()
    
    cycle = 0
    
    while True:
        try:
            cycle += 1
            
            if db.get_setting('signal_enabled') != '1':
                time.sleep(30)
                continue
            
            max_signals = int(db.get_setting('max_signals') or 5)
            min_confidence = int(db.get_setting('min_confidence') or 55)
            
            logger.info(f"🔄 Cycle {cycle} - Scanning {len(SYMBOLS)} symbols")
            
            signals = []
            for symbol in SYMBOLS:
                try:
                    signal = ultra_market_analysis(symbol)
                    if signal and signal.get('confidence', 0) >= min_confidence:
                        signals.append(signal)
                        logger.info(f"✅ {signal['symbol']}: {signal['signal']} ({signal['confidence']}%) - TP1: {signal.get('profit_percent1', 0)}%")
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
                    send_admin(f"💳 {len(payments)} پرداخت در انتظار - استفاده از /payments")
            
            if cycle % 20 == 0:
                stats = db.get_stats()
                send_admin(f"""
🔄 <b>بروزرسانی وضعیت</b>
━━━━━━━━━━━━━━━━━━━━━━
📊 سیگنال امروز: {stats.get('today', 0)}
📈 کل سیگنال‌ها: {stats.get('signals', 0)}
🎯 نرخ برد: {stats.get('win_rate', 0)}%
🧠 دقت سیستم: {learner.get_accuracy()}%
👑 کاربران پریمیوم: {stats.get('premium', 0)}
💳 پرداخت‌های در انتظار: {stats.get('pending', 0)}
""")
            
            logger.info(f"⏱ Waiting {INTERVAL//60} minutes...")
            time.sleep(INTERVAL)
            
        except Exception as e:
            logger.error(f"❌ Main loop error: {e}")
            send_admin(f"❌ <b>خطا:</b> {str(e)}")
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
        
        if user_id == ADMIN_ID and db.get_setting('broadcast_mode') == '1':
            if text.startswith('/'):
                return
            handle_broadcast_message(user_id, text)
            return
        
        if text.startswith('/'):
            if user_id == ADMIN_ID:
                handle_admin_command(text)
            else:
                if text == '/start':
                    send_telegram("""
🚀 <b>ربات سیگنال حرفه‌ای</b>
🤖 <b>نسخه Quantum Pro Max</b>

📊 دریافت سیگنال‌های حرفه‌ای با قدرت تحلیل ۱۰۰۰۰ برابر!

<b>📌 دستورات:</b>
/subscribe - خرید اشتراک
/help - راهنما
/status - وضعیت اشتراک

<b>🔐 ویژگی‌ها:</b>
• تحلیل ۱۰ تایم‌فریم
• ۱۵+ اندیکاتور پیشرفته
• ۵ حد سود غیرمساوی
• تحلیل FFT و رگرسیون
• سیستم یادگیری هوشمند

<i>از امروز شروع به سود کنید! 🚀</i>
""", user_id)
                elif text == '/subscribe':
                    handle_subscribe(user_id)
                elif text == '/help':
                    send_telegram(f"""
📚 <b>راهنما</b>
━━━━━━━━━━━━━━━━━━━━━━

<b>📌 دستورات:</b>
/start - خوش‌آمدگویی
/subscribe - خرید اشتراک
/status - وضعیت اشتراک

<b>💳 خرید اشتراک:</b>
1. /subscribe
2. ارسال {db.get_setting('price') or PRICE} USDT
3. ارسال هش تراکنش
4. انتظار برای تایید

<b>📊 سیگنال‌ها:</b>
• BUY - خرید
• SELL - فروش
• ۵ حد سود مختلف
• حد ضرر

<b>🆘 پشتیبانی:</b>
تماس با @davnold
""", user_id)
                elif text == '/status':
                    user = db.get_user(user_id)
                    if user and user['is_active'] == 1:
                        expire = user['subscription_expire']
                        if expire:
                            days_left = (datetime.fromisoformat(expire) - datetime.now()).days
                            if days_left > 0:
                                send_telegram(f"✅ <b>اشتراک فعال</b>\n\n📅 {days_left} روز باقی مانده\n🎯 دقت: {learner.get_accuracy()}%\n\n🚀 به سوددهی ادامه دهید!", user_id)
                            else:
                                send_telegram("⏰ <b>اشتراک منقضی شد</b>\n\nبا /subscribe تمدید کنید", user_id)
                        else:
                            send_telegram("⚠️ <b>اشتراک فعال نیست</b>\n\nبا /subscribe تهیه کنید", user_id)
                    else:
                        send_telegram("⚠️ <b>اشتراک فعال نیست</b>\n\nبا /subscribe تهیه کنید", user_id)
            return
        
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
        print("🚀 ULTIMATE SIGNAL BOT V21 - QUANTUM PRO MAX ULTRA")
        print("="*70)
        print(f"📊 Symbols: {len(SYMBOLS)}")
        print(f"⏱ Interval: {INTERVAL//60} minutes")
        print(f"📢 Channel: {CHANNEL_ID}")
        print(f"💳 Price: {PRICE}")
        print(f"🧠 Analysis: 10000X Stronger with Scipy")
        print(f"🎯 Targets: 5 Non-Equal Profit Levels")
        print(f"🔘 Admin Panel: 10 Fully Functional Buttons")
        print("="*70)
        print("🤖 Starting bot...\n")
        
        test = get_candles('BTCUSDT', 10)
        if test:
            logger.info("✅ Binance connection OK")
        else:
            logger.warning("⚠️ Binance connection issue")
        
        signal_thread = threading.Thread(target=main_loop, daemon=True)
        signal_thread.start()
        logger.info("✅ Signal generator started")
        
        run_bot()
        
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")