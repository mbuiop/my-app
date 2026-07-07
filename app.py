# ============================================================
# ULTIMATE SIGNAL BOT V23 - FINAL EDITION
# SMART TREND FILTER | MULTI-FACTOR CONFIDENCE | REAL LEARNING
# PROFESSIONAL WALLET STREET LEVEL ANALYSIS
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
                trend_strength REAL,
                adx REAL,
                volume_trend REAL,
                bullish_timeframes INTEGER DEFAULT 0,
                smc_score REAL DEFAULT 0,
                has_order_block INTEGER DEFAULT 0,
                has_fvg INTEGER DEFAULT 0,
                has_divergence INTEGER DEFAULT 0,
                has_bos INTEGER DEFAULT 0,
                candle_pattern TEXT,
                rr_ratio REAL DEFAULT 0,
                trend_filter_score REAL DEFAULT 0
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
            ('broadcast_mode', '0'),
            ('learning_enabled', '1'),
            ('min_adx', '25'),
            ('min_volume_spike', '1.5'),
            ('min_bullish_timeframes', '7'),
            ('min_rr_ratio', '2.0'),
            ('enable_smc', '1'),
            ('enable_divergence', '1'),
            ('enable_order_block', '1'),
            ('enable_fvg', '1'),
            ('enable_bos', '1'),
            ('enable_candle_patterns', '1'),
            ('adaptive_scoring', '1'),
            ('trend_filter_strict', '1')
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
                market_phase, volatility, trend_strength, adx, volume_trend,
                bullish_timeframes, smc_score, has_order_block, has_fvg,
                has_divergence, has_bos, candle_pattern, rr_ratio,
                trend_filter_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            signal_data.get('trend_strength', 0),
            signal_data.get('adx', 0),
            signal_data.get('volume_trend', 0),
            signal_data.get('bullish_timeframes', 0),
            signal_data.get('smc_score', 0),
            1 if signal_data.get('order_block') else 0,
            1 if signal_data.get('fvg') else 0,
            1 if signal_data.get('divergence') else 0,
            1 if signal_data.get('bos') else 0,
            signal_data.get('candle_pattern', 'none'),
            signal_data.get('rr_ratio', 0),
            signal_data.get('trend_filter_score', 0)
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
    
    def get_signals_with_feedback(self, limit=100):
        """دریافت سیگنال‌های دارای بازخورد برای یادگیری"""
        self.cursor.execute('''
            SELECT s.*, f.feedback, f.profit_amount 
            FROM signals s
            JOIN feedback_log f ON s.id = f.signal_id
            ORDER BY f.created_at DESC
            LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()
    
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
        
        # به‌روزرسانی سیستم یادگیری
        signal = self.get_signal(signal_id)
        if signal:
            update_learning_weights(signal, feedback_type)
        
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
# CANDLE DATA FETCH
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

# ============================================================
# ADVANCED INDICATORS
# ============================================================

class AdvancedIndicators:
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
    def calculate_supertrend(highs, lows, closes, period=10, multiplier=3):
        if len(closes) < period:
            return None, None
        atr = AdvancedIndicators.calculate_atr(highs, lows, closes, period)
        hl2 = (highs[-1] + lows[-1]) / 2
        upper = hl2 + multiplier * atr
        lower = hl2 - multiplier * atr
        return upper, lower
    
    @staticmethod
    def calculate_ichimoku(highs, lows, closes):
        if len(closes) < 52:
            return None
        tenkan = (max(highs[-9:]) + min(lows[-9:])) / 2
        kijun = (max(highs[-26:]) + min(lows[-26:])) / 2
        senkou_a = (tenkan + kijun) / 2
        senkou_b = (max(highs[-52:]) + min(lows[-52:])) / 2
        return {
            'tenkan': round(tenkan, 8),
            'kijun': round(kijun, 8),
            'senkou_a': round(senkou_a, 8),
            'senkou_b': round(senkou_b, 8)
        }
    
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
    def calculate_mfi(highs, lows, closes, volumes, period=14):
        if len(closes) < period:
            return 50
        typical = [(highs[i] + lows[i] + closes[i]) / 3 for i in range(len(closes))]
        money_flow = [typical[i] * volumes[i] for i in range(len(closes))]
        positive = 0
        negative = 0
        for i in range(-period, 0):
            if i > -period:
                if typical[i] > typical[i-1]:
                    positive += money_flow[i]
                else:
                    negative += money_flow[i]
        if negative == 0:
            return 100
        mfi = 100 - (100 / (1 + positive / negative))
        return round(mfi, 2)
    
    @staticmethod
    def calculate_cmf(highs, lows, closes, volumes, period=20):
        if len(closes) < period:
            return 0
        cmf = 0
        for i in range(-period, 0):
            if i >= -len(closes):
                mf = ((closes[i] - lows[i]) - (highs[i] - closes[i])) / (highs[i] - lows[i] + 0.0000001)
                cmf += mf * volumes[i]
        total_vol = sum(volumes[-period:])
        if total_vol == 0:
            return 0
        return round(cmf / total_vol, 4)
    
    @staticmethod
    def calculate_stochastic_rsi(prices, period=14):
        rsi = AdvancedIndicators.calculate_rsi(prices, period)
        if len(prices) < period:
            return 50
        min_rsi = min(prices[-period:])
        max_rsi = max(prices[-period:])
        if max_rsi == min_rsi:
            return 50
        stoch_rsi = (rsi - min_rsi) / (max_rsi - min_rsi) * 100
        return round(stoch_rsi, 2)
    
    @staticmethod
    def calculate_roc(prices, period=14):
        if len(prices) < period:
            return 0
        return round((prices[-1] - prices[-period]) / prices[-period] * 100, 4)
    
    @staticmethod
    def calculate_volume_spike(volumes, period=20):
        if len(volumes) < period:
            return 0
        avg_vol = np.mean(volumes[-period:])
        current_vol = volumes[-1]
        if avg_vol == 0:
            return 0
        return round(current_vol / avg_vol, 2)
    
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

# ============================================================
# SMC (SMART MONEY CONCEPTS) DETECTOR
# ============================================================

class SMCDetector:
    def __init__(self, highs, lows, closes):
        self.highs = highs
        self.lows = lows
        self.closes = closes
    
    def detect_order_block(self, lookback=20):
        """تشخیص Order Block"""
        if len(self.highs) < lookback:
            return False
        
        for i in range(lookback - 10, lookback):
            if i < 2:
                continue
            body = abs(self.closes[i] - self.closes[i-1])
            avg_body = np.mean([abs(self.closes[j] - self.closes[j-1]) for j in range(i-10, i)])
            if body > avg_body * 1.5:
                if self.closes[i] > self.closes[i-1] and self.closes[i] > self.highs[i-1]:
                    return True
                if self.closes[i] < self.closes[i-1] and self.closes[i] < self.lows[i-1]:
                    return True
        return False
    
    def detect_fvg(self, lookback=30):
        """تشخیص Fair Value Gap"""
        if len(self.highs) < lookback:
            return False
        
        for i in range(lookback - 15, lookback):
            if i < 2:
                continue
            if self.lows[i] > self.highs[i-2]:
                return True
            if self.highs[i] < self.lows[i-2]:
                return True
        return False
    
    def detect_divergence(self, indicator_values, price, lookback=20):
        """تشخیص دیورژنس"""
        if len(indicator_values) < lookback or len(price) < lookback:
            return False, 'none'
        
        peaks = []
        troughs = []
        
        for i in range(2, lookback - 2):
            if indicator_values[i] > indicator_values[i-1] and indicator_values[i] > indicator_values[i+1]:
                peaks.append(i)
            if indicator_values[i] < indicator_values[i-1] and indicator_values[i] < indicator_values[i+1]:
                troughs.append(i)
        
        # دیورژنس مثبت (صعودی)
        if len(troughs) >= 2:
            idx1 = troughs[-2]
            idx2 = troughs[-1]
            if indicator_values[idx2] > indicator_values[idx1] and price[idx2] < price[idx1]:
                return True, 'bullish'
        
        # دیورژنس منفی (نزولی)
        if len(peaks) >= 2:
            idx1 = peaks[-2]
            idx2 = peaks[-1]
            if indicator_values[idx2] < indicator_values[idx1] and price[idx2] > price[idx1]:
                return True, 'bearish'
        
        return False, 'none'
    
    def detect_bos(self, lookback=30):
        """تشخیص Break of Structure"""
        if len(self.highs) < lookback:
            return False
        
        for i in range(lookback - 10, lookback):
            if i < 5:
                continue
            if self.highs[i] > max(self.highs[max(0, i-5):i]):
                return True
            if self.lows[i] < min(self.lows[max(0, i-5):i]):
                return True
        return False
    
    def detect_liquidity_sweep(self, lookback=20):
        """تشخیص Liquidity Sweep"""
        if len(self.highs) < lookback:
            return False
        
        recent_high = max(self.highs[-lookback:-2])
        recent_low = min(self.lows[-lookback:-2])
        
        if self.highs[-1] > recent_high and self.closes[-1] < recent_high:
            return True
        if self.lows[-1] < recent_low and self.closes[-1] > recent_low:
            return True
        return False
    
    def detect_candle_pattern(self):
        """تشخیص الگوهای کندلی"""
        if len(self.closes) < 3:
            return 'none'
        
        open_ = self.closes[-2]
        high = self.highs[-1]
        low = self.lows[-1]
        close = self.closes[-1]
        body = abs(close - open_)
        upper_wick = high - max(close, open_)
        lower_wick = min(close, open_) - low
        total_range = high - low
        
        if total_range == 0:
            return 'none'
        
        if upper_wick > body * 2 and lower_wick < body * 0.5:
            return 'pin_bar_bearish'
        if lower_wick > body * 2 and upper_wick < body * 0.5:
            return 'pin_bar_bullish'
        
        if len(self.closes) >= 2:
            prev_body = abs(self.closes[-2] - self.closes[-3])
            if body > prev_body * 1.5 and close > self.closes[-2] and open_ < self.closes[-3]:
                return 'bullish_engulfing'
            if body > prev_body * 1.5 and close < self.closes[-2] and open_ > self.closes[-3]:
                return 'bearish_engulfing'
        
        if body < total_range * 0.1:
            return 'doji'
        
        if lower_wick > body * 2 and upper_wick < body * 0.5 and close > open_:
            return 'hammer'
        
        if upper_wick > body * 2 and lower_wick < body * 0.5 and close < open_:
            return 'shooting_star'
        
        return 'none'
    
    def detect_market_phase(self, adx, score):
        """تشخیص فاز بازار"""
        if adx > 35 and score > 55:
            return 'bullish_trend'
        elif adx > 35 and score < 45:
            return 'bearish_trend'
        elif adx < 20:
            return 'ranging'
        elif score > 60:
            return 'accumulation'
        elif score < 40:
            return 'distribution'
        return 'neutral'

# ============================================================
# REAL LEARNING SYSTEM - WEIGHT ADJUSTMENT
# ============================================================

class RealLearningSystem:
    def __init__(self):
        self.file = "real_learning_weights.json"
        self.load()
    
    def load(self):
        if os.path.exists(self.file):
            try:
                with open(self.file, 'r') as f:
                    data = json.load(f)
                    self.positive = data.get('positive', 0)
                    self.negative = data.get('negative', 0)
                    self.indicator_weights = data.get('indicator_weights', {
                        'ema200': 1.0, 'supertrend': 1.0, 'volume_spike': 1.0,
                        'obv': 1.0, 'divergence': 1.3, 'bos': 1.0,
                        'order_block': 1.5, 'fvg': 1.3, 'candle_pattern': 1.0,
                        'support': 1.0, 'adx': 1.0, 'mfi': 1.0,
                        'cmf': 1.0, 'ichimoku': 1.0, 'bollinger': 1.0,
                        'vwap': 1.0, 'ma_structure': 1.2, 'liquidity_sweep': 1.4,
                        'rsi': 1.0, 'macd': 1.0, 'stoch_rsi': 1.0,
                        'roc': 1.0, 'volume_trend': 1.0
                    })
                    self.phase_weights = data.get('phase_weights', {
                        'bullish_trend': 1.0,
                        'bearish_trend': 0.6,
                        'ranging': 0.8,
                        'accumulation': 1.2,
                        'distribution': 0.7,
                        'neutral': 1.0
                    })
                    self.smc_weights = data.get('smc_weights', {
                        'order_block': 1.5,
                        'fvg': 1.3,
                        'liquidity_sweep': 1.4,
                        'bos': 1.2,
                        'divergence': 1.3
                    })
                    self.indicator_success = data.get('indicator_success', {})
                    self.total_trades = data.get('total_trades', 0)
                    self.winning_trades = data.get('winning_trades', 0)
                    return
            except:
                pass
        
        self.positive = 0
        self.negative = 0
        self.total_trades = 0
        self.winning_trades = 0
        
        self.indicator_weights = {
            'ema200': 1.0, 'supertrend': 1.0, 'volume_spike': 1.0,
            'obv': 1.0, 'divergence': 1.3, 'bos': 1.0,
            'order_block': 1.5, 'fvg': 1.3, 'candle_pattern': 1.0,
            'support': 1.0, 'adx': 1.0, 'mfi': 1.0,
            'cmf': 1.0, 'ichimoku': 1.0, 'bollinger': 1.0,
            'vwap': 1.0, 'ma_structure': 1.2, 'liquidity_sweep': 1.4,
            'rsi': 1.0, 'macd': 1.0, 'stoch_rsi': 1.0,
            'roc': 1.0, 'volume_trend': 1.0
        }
        
        self.phase_weights = {
            'bullish_trend': 1.0,
            'bearish_trend': 0.6,
            'ranging': 0.8,
            'accumulation': 1.2,
            'distribution': 0.7,
            'neutral': 1.0
        }
        
        self.smc_weights = {
            'order_block': 1.5,
            'fvg': 1.3,
            'liquidity_sweep': 1.4,
            'bos': 1.2,
            'divergence': 1.3
        }
        
        self.indicator_success = {}
        self.save()
    
    def save(self):
        try:
            with open(self.file, 'w') as f:
                json.dump({
                    'positive': self.positive,
                    'negative': self.negative,
                    'indicator_weights': self.indicator_weights,
                    'phase_weights': self.phase_weights,
                    'smc_weights': self.smc_weights,
                    'indicator_success': self.indicator_success,
                    'total_trades': self.total_trades,
                    'winning_trades': self.winning_trades
                }, f, indent=2)
        except:
            pass
    
    def update_weights_from_feedback(self, signal_data, feedback_type):
        """به‌روزرسانی وزن‌ها بر اساس بازخورد"""
        self.total_trades += 1
        
        if feedback_type == 'positive':
            self.positive += 1
            self.winning_trades += 1
            
            # افزایش وزن اندیکاتورهایی که در سیگنال موفق حضور داشتند
            indicators_present = self._extract_indicators(signal_data)
            for indicator in indicators_present:
                if indicator in self.indicator_weights:
                    self.indicator_weights[indicator] = min(2.0, self.indicator_weights[indicator] * 1.03)
                # ثبت موفقیت اندیکاتور
                if indicator not in self.indicator_success:
                    self.indicator_success[indicator] = {'wins': 0, 'losses': 0}
                self.indicator_success[indicator]['wins'] += 1
            
            # افزایش وزن فاز بازار
            phase = signal_data.get('market_phase', 'neutral')
            if phase in self.phase_weights:
                self.phase_weights[phase] = min(1.8, self.phase_weights[phase] * 1.02)
            
            # افزایش وزن SMC
            if signal_data.get('order_block'):
                self.smc_weights['order_block'] = min(2.0, self.smc_weights['order_block'] * 1.02)
            if signal_data.get('fvg'):
                self.smc_weights['fvg'] = min(2.0, self.smc_weights['fvg'] * 1.02)
            if signal_data.get('divergence'):
                self.smc_weights['divergence'] = min(2.0, self.smc_weights['divergence'] * 1.02)
            if signal_data.get('bos'):
                self.smc_weights['bos'] = min(2.0, self.smc_weights['bos'] * 1.02)
            
        else:
            self.negative += 1
            
            # کاهش وزن اندیکاتورهایی که در سیگنال ناموفق حضور داشتند
            indicators_present = self._extract_indicators(signal_data)
            for indicator in indicators_present:
                if indicator in self.indicator_weights:
                    self.indicator_weights[indicator] = max(0.3, self.indicator_weights[indicator] * 0.97)
                if indicator not in self.indicator_success:
                    self.indicator_success[indicator] = {'wins': 0, 'losses': 0}
                self.indicator_success[indicator]['losses'] += 1
            
            # کاهش وزن فاز بازار
            phase = signal_data.get('market_phase', 'neutral')
            if phase in self.phase_weights:
                self.phase_weights[phase] = max(0.3, self.phase_weights[phase] * 0.98)
            
            # کاهش وزن SMC
            if signal_data.get('order_block'):
                self.smc_weights['order_block'] = max(0.3, self.smc_weights['order_block'] * 0.98)
            if signal_data.get('fvg'):
                self.smc_weights['fvg'] = max(0.3, self.smc_weights['fvg'] * 0.98)
            if signal_data.get('divergence'):
                self.smc_weights['divergence'] = max(0.3, self.smc_weights['divergence'] * 0.98)
            if signal_data.get('bos'):
                self.smc_weights['bos'] = max(0.3, self.smc_weights['bos'] * 0.98)
        
        self.save()
    
    def _extract_indicators(self, signal_data):
        """استخراج اندیکاتورهای حاضر در سیگنال"""
        indicators = []
        
        if signal_data.get('rsi', 50) < 70 and signal_data.get('rsi', 50) > 30:
            indicators.append('rsi')
        if signal_data.get('macd', 0) > 0:
            indicators.append('macd')
        if signal_data.get('adx', 0) > 25:
            indicators.append('adx')
        if signal_data.get('volume_spike', 0) > 1.5:
            indicators.append('volume_spike')
        if signal_data.get('obv', 0) > 0:
            indicators.append('obv')
        if signal_data.get('divergence'):
            indicators.append('divergence')
        if signal_data.get('bos'):
            indicators.append('bos')
        if signal_data.get('order_block'):
            indicators.append('order_block')
        if signal_data.get('fvg'):
            indicators.append('fvg')
        if signal_data.get('liquidity_sweep'):
            indicators.append('liquidity_sweep')
        if signal_data.get('candle_pattern') != 'none':
            indicators.append('candle_pattern')
        if signal_data.get('support1', 0) > 0:
            indicators.append('support')
        if signal_data.get('ma_structure', False):
            indicators.append('ma_structure')
        if signal_data.get('mfi', 50) < 30:
            indicators.append('mfi')
        if signal_data.get('cmf', 0) > 0:
            indicators.append('cmf')
        if signal_data.get('ichimoku', False):
            indicators.append('ichimoku')
        if signal_data.get('bollinger', False):
            indicators.append('bollinger')
        if signal_data.get('vwap', 0) > 0:
            indicators.append('vwap')
        if signal_data.get('stoch_rsi', 50) < 30:
            indicators.append('stoch_rsi')
        if signal_data.get('roc', 0) > 0:
            indicators.append('roc')
        if signal_data.get('volume_trend', 0) > 5:
            indicators.append('volume_trend')
        if signal_data.get('supertrend', False):
            indicators.append('supertrend')
        if signal_data.get('ema200', 0) > 0:
            indicators.append('ema200')
        
        return list(set(indicators))
    
    def get_indicator_weight(self, indicator):
        return self.indicator_weights.get(indicator, 1.0)
    
    def get_phase_weight(self, phase):
        return self.phase_weights.get(phase, 1.0)
    
    def get_smc_weight(self, smc_type):
        return self.smc_weights.get(smc_type, 1.0)
    
    def get_accuracy(self):
        total = self.positive + self.negative
        if total == 0:
            return 50.0
        return round((self.positive / total) * 100, 2)
    
    def get_best_indicators(self, top_n=5):
        """دریافت بهترین اندیکاتورها بر اساس عملکرد"""
        if not self.indicator_success:
            return []
        
        scores = {}
        for indicator, data in self.indicator_success.items():
            wins = data.get('wins', 0)
            losses = data.get('losses', 0)
            total = wins + losses
            if total > 0:
                scores[indicator] = round((wins / total) * 100, 2)
            else:
                scores[indicator] = 50
        
        sorted_indicators = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_indicators[:top_n]

learner = RealLearningSystem()

def update_learning_weights(signal, feedback_type):
    """به‌روزرسانی وزن‌های یادگیری"""
    signal_data = dict(signal)
    learner.update_weights_from_feedback(signal_data, feedback_type)

# ============================================================
# SYMBOLS
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
# ULTRA SMART MONEY ANALYSIS WITH REAL LEARNING
# ============================================================

def ultra_smart_analysis(symbol):
    """Complete Smart Money Analysis with Real Learning"""
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
        ai = AdvancedIndicators()
        
        for tf in timeframes:
            data = get_candles(symbol, tf['limit'], tf['name'])
            if not data or len(data['close']) < 50:
                continue
            
            prices = data['close']
            highs = data['high']
            lows = data['low']
            volumes = data['volume']
            current = prices[-1]
            
            # ===== TRADITIONAL INDICATORS =====
            rsi = ai.calculate_rsi(prices, 14)
            macd, macd_signal, macd_hist = ai.calculate_macd(prices, 12, 26, 9)
            ma20 = ai.calculate_ma(prices, 20)
            ma50 = ai.calculate_ma(prices, 50)
            ma100 = ai.calculate_ma(prices, 100)
            ma200 = ai.calculate_ma(prices, 200)
            upper_bb, middle_bb, lower_bb = ai.calculate_bollinger(prices, 20, 2)
            vwap = ai.calculate_vwap(prices, volumes)
            atr = ai.calculate_atr(highs, lows, prices, 14)
            adx = ai.calculate_adx(highs, lows, prices, 14)
            obv = ai.calculate_obv(prices, volumes)
            volume_spike = ai.calculate_volume_spike(volumes, 20)
            mfi = ai.calculate_mfi(highs, lows, prices, volumes, 14)
            cmf = ai.calculate_cmf(highs, lows, prices, volumes, 20)
            stoch_rsi = ai.calculate_stochastic_rsi(prices, 14)
            roc = ai.calculate_roc(prices, 14)
            volume_trend = ai.calculate_volume_trend(volumes)
            volatility = ai.calculate_volatility(highs, lows, prices, 20)
            
            # ===== ADVANCED INDICATORS =====
            supertrend = ai.calculate_supertrend(highs, lows, prices, 10, 3)
            ichimoku = ai.calculate_ichimoku(highs, lows, prices)
            
            # ===== SMC DETECTION =====
            smc = SMCDetector(highs, lows, prices)
            order_block = smc.detect_order_block()
            fvg = smc.detect_fvg()
            divergence, divergence_type = smc.detect_divergence([rsi] * len(prices), prices, 20)
            bos = smc.detect_bos()
            liquidity_sweep = smc.detect_liquidity_sweep()
            candle_pattern = smc.detect_candle_pattern()
            
            # ===== SUPPORT/RESISTANCE =====
            support1, support2, resistance1, resistance2 = find_support_resistance(highs, lows, prices)
            
            # ===== WEIGHTED SCORING =====
            score = 50
            reasons = []
            smc_score = 0
            trend_filter_score = 0
            
            # ===== 1. TREND FILTER =====
            market_phase = smc.detect_market_phase(adx, score)
            
            # ===== 2. REAL LEARNING WEIGHTS =====
            rsi_weight = learner.get_indicator_weight('rsi')
            macd_weight = learner.get_indicator_weight('macd')
            adx_weight = learner.get_indicator_weight('adx')
            volume_weight = learner.get_indicator_weight('volume_spike')
            obv_weight = learner.get_indicator_weight('obv')
            divergence_weight = learner.get_indicator_weight('divergence')
            bos_weight = learner.get_indicator_weight('bos')
            order_block_weight = learner.get_indicator_weight('order_block')
            fvg_weight = learner.get_indicator_weight('fvg')
            candle_weight = learner.get_indicator_weight('candle_pattern')
            support_weight = learner.get_indicator_weight('support')
            ma_weight = learner.get_indicator_weight('ma_structure')
            
            phase_weight = learner.get_phase_weight(market_phase)
            
            # ===== 3. INDICATOR SCORING WITH WEIGHTS =====
            
            # EMA200 + SuperTrend
            if current > ma200:
                score += 10 * rsi_weight
                reasons.append(f"✅ Price above EMA200")
                if supertrend:
                    upper, lower = supertrend
                    if current > upper:
                        score += 5 * rsi_weight
                        reasons.append("✅ SuperTrend Bullish")
                        smc_score += 3
            else:
                score -= 5 * rsi_weight
                reasons.append("❌ Price below EMA200")
            
            # Volume Spike + OBV
            if volume_spike > float(db.get_setting('min_volume_spike') or 1.5):
                score += 8 * volume_weight
                reasons.append(f"✅ Volume Spike: {volume_spike}x")
                smc_score += 4
            if obv > 0:
                score += 5 * obv_weight
                reasons.append("✅ OBV Bullish")
                smc_score += 2
            
            # Divergence
            if divergence:
                score += 15 * divergence_weight
                reasons.append(f"✅ RSI Divergence ({divergence_type})")
                smc_score += 8
                trend_filter_score += 10  # سیگنال برگشت قوی
            
            # BOS
            if bos:
                score += 10 * bos_weight
                reasons.append("✅ Break of Structure (BOS)")
                smc_score += 5
                trend_filter_score += 5
            
            # Order Block + FVG
            if order_block:
                score += 15 * order_block_weight
                reasons.append("✅ Order Block Detected")
                smc_score += 10
                trend_filter_score += 8
            if fvg:
                score += 12 * fvg_weight
                reasons.append("✅ Fair Value Gap (FVG)")
                smc_score += 8
                trend_filter_score += 5
            
            # Candle Patterns
            if candle_pattern in ['bullish_engulfing', 'pin_bar_bullish', 'hammer']:
                score += 10 * candle_weight
                reasons.append(f"✅ Bullish Candle: {candle_pattern}")
                smc_score += 5
                trend_filter_score += 5
            elif candle_pattern in ['doji']:
                score += 5 * candle_weight
                reasons.append("✅ Doji - Reversal Signal")
                smc_score += 3
                trend_filter_score += 3
            
            # Support
            if support1 > 0:
                dist_to_support = ((current - support1) / current) * 100
                if dist_to_support < 0.5:
                    score += 12 * support_weight
                    reasons.append("🛡️ Near Strong Support")
                    smc_score += 6
                    trend_filter_score += 5
                elif dist_to_support < 1.0:
                    score += 8 * support_weight
                    reasons.append("🛡️ Close to Support")
                    smc_score += 4
            
            # Resistance (avoid)
            if resistance1 > 0:
                dist_to_resistance = ((resistance1 - current) / current) * 100
                if dist_to_resistance < 0.5:
                    score -= 10 * support_weight
                    reasons.append("🚫 Near Resistance - Wait")
                    smc_score -= 5
            
            # ADX
            if adx > 35:
                score += 8 * adx_weight
                reasons.append(f"🔥 Strong Trend (ADX: {adx:.1f})")
                smc_score += 3
            elif adx > 25:
                score += 4 * adx_weight
                reasons.append(f"✅ Trend (ADX: {adx:.1f})")
                smc_score += 2
            
            # MFI & CMF
            if mfi < 20:
                score += 5
                reasons.append(f"✅ MFI Oversold: {mfi:.1f}")
            if cmf > 0:
                score += 4
                reasons.append(f"✅ CMF Bullish: {cmf:.2f}")
            
            # ROC
            if roc > 0:
                score += 3
                reasons.append(f"✅ Positive ROC: {roc:.2f}%")
            
            # Ichimoku
            if ichimoku:
                if current > ichimoku['senkou_a'] and current > ichimoku['senkou_b']:
                    score += 5
                    reasons.append("☁️ Above Ichimoku Cloud")
                    smc_score += 3
                elif current < ichimoku['senkou_a'] and current < ichimoku['senkou_b']:
                    score -= 5
                    reasons.append("☁️ Below Ichimoku Cloud")
                    smc_score -= 3
            
            # Bollinger
            if current < lower_bb:
                score += 8
                reasons.append("🎯 Below Lower BB - Oversold")
                smc_score += 4
            elif current > upper_bb:
                score -= 8
                reasons.append("🎯 Above Upper BB - Overbought")
                smc_score -= 4
            
            # MACD
            if macd > 0 and macd_hist > 0:
                score += 10 * macd_weight
                reasons.append("🟢 MACD Bullish Cross")
                smc_score += 5
            elif macd > 0:
                score += 5 * macd_weight
                reasons.append("🟡 MACD Positive")
                smc_score += 2
            
            # VWAP
            if current > vwap:
                score += 5
                reasons.append("✅ Above VWAP")
                smc_score += 3
            else:
                score -= 5
                reasons.append("❌ Below VWAP")
                smc_score -= 3
            
            # MA Structure
            if current > ma20 > ma50 > ma100 > ma200:
                score += 12 * ma_weight
                reasons.append("🚀 Perfect MA Structure")
                smc_score += 8
            
            # RSI
            if 30 < rsi < 70:
                score += 5 * rsi_weight
                reasons.append(f"✅ RSI Healthy: {rsi:.1f}")
            elif rsi < 30:
                score += 10 * rsi_weight
                reasons.append(f"🔥 RSI Oversold: {rsi:.1f}")
                smc_score += 5
            elif rsi > 70:
                score -= 10 * rsi_weight
                reasons.append(f"🔥 RSI Overbought: {rsi:.1f}")
                smc_score -= 5
            
            # Volume Trend
            if volume_trend > 10:
                score += 5
                reasons.append(f"📊 Volume Trend: {volume_trend:.1f}%")
                smc_score += 3
            
            # Stochastic RSI
            if stoch_rsi < 20:
                score += 5
                reasons.append(f"✅ Stoch RSI Oversold: {stoch_rsi:.1f}")
            
            # Liquidity Sweep
            if liquidity_sweep:
                score += 8
                reasons.append("✅ Liquidity Sweep Detected")
                smc_score += 5
                trend_filter_score += 5
            
            # ===== APPLY PHASE WEIGHT =====
            score = score * phase_weight
            
            # ===== TREND FILTER - برای روند نزولی =====
            if market_phase == 'bearish_trend':
                # در روند نزولی، فقط با نشانه‌های قوی برگشت سیگنال بده
                if trend_filter_score < 15:
                    # سیگنال برگشت قوی نیست
                    score = score * 0.3
                    reasons.append("⚠️ Bearish Trend - Weak Reversal Signs")
            
            analysis_results[tf['name']] = {
                'score': score,
                'smc_score': smc_score,
                'trend_filter_score': trend_filter_score,
                'rsi': rsi,
                'macd': macd,
                'macd_signal': macd_signal,
                'ma20': ma20,
                'ma50': ma50,
                'ma200': ma200,
                'vwap': vwap,
                'atr': atr,
                'adx': adx,
                'volume_spike': volume_spike,
                'obv': obv,
                'mfi': mfi,
                'cmf': cmf,
                'stoch_rsi': stoch_rsi,
                'roc': roc,
                'order_block': order_block,
                'fvg': fvg,
                'divergence': divergence,
                'divergence_type': divergence_type,
                'bos': bos,
                'liquidity_sweep': liquidity_sweep,
                'candle_pattern': candle_pattern,
                'market_phase': market_phase,
                'weight': tf['weight'],
                'reasons': reasons[:5],
                'support1': support1,
                'support2': support2,
                'resistance1': resistance1,
                'resistance2': resistance2,
                'volume_trend': volume_trend,
                'supertrend': supertrend,
                'ichimoku': ichimoku,
                'upper_bb': upper_bb,
                'lower_bb': lower_bb,
                'volatility': volatility
            }
            
            all_scores.append(score)
        
        if not analysis_results:
            return None
        
        # ===== WEIGHTED SCORE =====
        weighted_score = 0
        weighted_smc = 0
        weighted_trend_filter = 0
        total_weight = 0
        
        for tf_name, data in analysis_results.items():
            weighted_score += data['score'] * data['weight']
            weighted_smc += data['smc_score'] * data['weight']
            weighted_trend_filter += data['trend_filter_score'] * data['weight']
            total_weight += data['weight']
        
        if total_weight == 0:
            return None
        
        final_score = weighted_score / total_weight
        final_smc = weighted_smc / total_weight
        final_trend_filter = weighted_trend_filter / total_weight
        
        # ===== FILTERS =====
        # 1. هم‌جهت بودن تایم‌فریم‌ها
        bullish_timeframes = sum(1 for x in analysis_results.values() if x["score"] > 55)
        min_bullish = int(db.get_setting('min_bullish_timeframes') or 7)
        
        if bullish_timeframes < min_bullish:
            logger.info(f"❌ {symbol}: فقط {bullish_timeframes} تایم‌فریم صعودی")
            return None
        
        # 2. ADX
        main_adx = analysis_results.get('5m', {}).get('adx', 0)
        min_adx = float(db.get_setting('min_adx') or 25)
        
        if main_adx < min_adx:
            logger.info(f"❌ {symbol}: ADX ضعیف ({main_adx:.1f})")
            return None
        
        # 3. Volume Spike
        main_volume_spike = analysis_results.get('5m', {}).get('volume_spike', 0)
        min_spike = float(db.get_setting('min_volume_spike') or 1.5)
        
        if main_volume_spike < min_spike:
            logger.info(f"❌ {symbol}: حجم کم ({main_volume_spike:.1f}x)")
            return None
        
        # 4. حداقل ۲ سیگنال SMC
        smc_count = 0
        if analysis_results.get('5m', {}).get('order_block'):
            smc_count += 1
        if analysis_results.get('5m', {}).get('fvg'):
            smc_count += 1
        if analysis_results.get('5m', {}).get('divergence'):
            smc_count += 1
        if analysis_results.get('5m', {}).get('bos'):
            smc_count += 1
        if analysis_results.get('5m', {}).get('liquidity_sweep'):
            smc_count += 1
        
        if smc_count < 2:
            logger.info(f"❌ {symbol}: فقط {smc_count} سیگنال SMC")
            return None
        
        # 5. Trend Filter - Bearish Trend Check
        market_phase = analysis_results.get('5m', {}).get('market_phase', 'neutral')
        if market_phase == 'bearish_trend' and final_trend_filter < 15:
            logger.info(f"❌ {symbol}: Bearish Trend with weak reversal ({final_trend_filter:.1f})")
            return None
        
        # 6. نه نزدیک مقاومت باشد
        current_price = analysis_results.get('5m', {}).get('ma20', 0)
        resistance1 = analysis_results.get('5m', {}).get('resistance1', 0)
        if resistance1 > 0:
            dist_to_resistance = ((resistance1 - current_price) / current_price) * 100
            if dist_to_resistance < 0.5:
                logger.info(f"❌ {symbol}: نزدیک مقاومت ({dist_to_resistance:.2f}%)")
                return None
        
        # 7. حداقل ۷۰٪ امتیاز SMC
        if final_smc < 25:
            logger.info(f"❌ {symbol}: SMC Score پایین ({final_smc:.1f})")
            return None
        
        # ===== DETERMINE SIGNAL =====
        if final_score >= 55:
            signal = "BUY"
        else:
            return None
        
        # ===== MULTI-FACTOR CONFIDENCE =====
        # محاسبه Confidence بر اساس چند عامل
        base_confidence = 50 + abs(final_score - 50) * 0.6
        
        # فاکتور SMC
        smc_factor = min(20, final_smc * 0.3)
        
        # فاکتور تایم‌فریم‌های هم‌جهت
        tf_factor = min(15, (bullish_timeframes / 10) * 15)
        
        # فاکتور RR (بعداً محاسبه می‌شود)
        rr_factor = 0
        
        # فاکتور روند (اگر bullish_trend باشد امتیاز بیشتر)
        phase_bonus = 0
        if market_phase == 'bullish_trend':
            phase_bonus = 10
        elif market_phase == 'accumulation':
            phase_bonus = 8
        elif market_phase == 'ranging':
            phase_bonus = 3
        
        confidence = base_confidence + smc_factor + tf_factor + rr_factor + phase_bonus
        confidence = max(55, min(98, confidence))
        
        # ===== CALCULATE TP/SL =====
        main_data = get_candles(symbol, 200, '5m')
        if not main_data:
            return None
        
        current_price = main_data['close'][-1]
        atr = AdvancedIndicators.calculate_atr(main_data['high'], main_data['low'], main_data['close'], 14)
        
        risk = atr * 1.2
        entry = current_price * 0.999
        
        support1 = analysis_results.get('5m', {}).get('support1', 0)
        if support1 > 0 and support1 < entry:
            sl = support1 * 0.998
        else:
            sl = entry - risk * 1.5
        
        tp1 = entry + risk * 2
        tp2 = entry + risk * 3
        tp3 = entry + risk * 5
        tp4 = entry + risk * 8
        tp5 = entry + risk * 13
        
        # محاسبه RR
        rr_ratio = (tp1 - entry) / (entry - sl)
        min_rr = float(db.get_setting('min_rr_ratio') or 2.0)
        
        if rr_ratio < min_rr:
            logger.info(f"❌ {symbol}: RR پایین ({rr_ratio:.2f})")
            return None
        
        # اضافه کردن RR به Confidence
        rr_factor = min(10, (rr_ratio / min_rr) * 5)
        confidence = min(98, confidence + rr_factor)
        
        profit_percent1 = round((tp1 - entry) / entry * 100, 2)
        profit_percent2 = round((tp2 - entry) / entry * 100, 2)
        profit_percent3 = round((tp3 - entry) / entry * 100, 2)
        profit_percent4 = round((tp4 - entry) / entry * 100, 2)
        profit_percent5 = round((tp5 - entry) / entry * 100, 2)
        
        quality_score = min(100, confidence + final_smc * 0.2)
        
        # ===== COLLECT REASONS =====
        all_reasons = []
        for tf_name, data in analysis_results.items():
            all_reasons.extend(data['reasons'][:2])
        
        # Add SMC signals
        if analysis_results.get('5m', {}).get('order_block'):
            all_reasons.append("🏛️ Order Block Detected")
        if analysis_results.get('5m', {}).get('fvg'):
            all_reasons.append("📉 Fair Value Gap (FVG)")
        if analysis_results.get('5m', {}).get('divergence'):
            div_type = analysis_results.get('5m', {}).get('divergence_type', '')
            all_reasons.append(f"🔄 RSI Divergence ({div_type})")
        if analysis_results.get('5m', {}).get('bos'):
            all_reasons.append("📊 Break of Structure (BOS)")
        if analysis_results.get('5m', {}).get('liquidity_sweep'):
            all_reasons.append("💧 Liquidity Sweep")
        
        candle_pattern = analysis_results.get('5m', {}).get('candle_pattern', 'none')
        if candle_pattern != 'none':
            all_reasons.append(f"🕯️ {candle_pattern}")
        
        all_reasons.append(f"✅ SMC Score: {final_smc:.1f}")
        all_reasons.append(f"✅ {bullish_timeframes}/10 Timeframes Bullish")
        all_reasons.append(f"✅ RR Ratio: {rr_ratio:.2f}:1")
        all_reasons.append(f"✅ Market Phase: {market_phase}")
        
        # اضافه کردن بهترین اندیکاتورها از سیستم یادگیری
        best_indicators = learner.get_best_indicators(3)
        if best_indicators:
            best_str = ", ".join([f"{ind} ({acc}%)" for ind, acc in best_indicators])
            all_reasons.append(f"🧠 Best Indicators: {best_str}")
        
        return {
            'symbol': symbol,
            'entry': round(entry, 8),
            'signal': signal,
            'confidence': round(confidence, 1),
            'score': round(final_score, 1),
            'quality_score': round(quality_score, 1),
            'smc_score': round(final_smc, 1),
            'trend_filter_score': round(final_trend_filter, 1),
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
            'adx': main_adx,
            'volatility': analysis_results.get('5m', {}).get('volatility', 0),
            'trend_strength': main_adx / 100,
            'market_phase': market_phase,
            'reasons': all_reasons[:12],
            'time': datetime.now().strftime("%H:%M"),
            'timeframes': {k: {'score': v['score'], 'smc_score': v.get('smc_score', 0), 'phase': v.get('market_phase', 'neutral')} 
                          for k, v in analysis_results.items()},
            'volume_trend': analysis_results.get('5m', {}).get('volume_trend', 0),
            'bullish_timeframes': bullish_timeframes,
            'order_block': analysis_results.get('5m', {}).get('order_block', False),
            'fvg': analysis_results.get('5m', {}).get('fvg', False),
            'divergence': analysis_results.get('5m', {}).get('divergence', False),
            'bos': analysis_results.get('5m', {}).get('bos', False),
            'candle_pattern': candle_pattern,
            'rr_ratio': round(rr_ratio, 2),
            'divergence_type': analysis_results.get('5m', {}).get('divergence_type', 'none'),
            'liquidity_sweep': analysis_results.get('5m', {}).get('liquidity_sweep', False),
            'stoch_rsi': analysis_results.get('5m', {}).get('stoch_rsi', 50),
            'mfi': analysis_results.get('5m', {}).get('mfi', 50),
            'cmf': analysis_results.get('5m', {}).get('cmf', 0),
            'roc': analysis_results.get('5m', {}).get('roc', 0)
        }
        
    except Exception as e:
        logger.error(f"Analysis error for {symbol}: {e}")
        return None

def find_support_resistance(highs, lows, closes):
    """Find support and resistance levels"""
    if len(closes) < 50:
        return 0, 0, 0, 0
    
    highs_array = np.array(highs[-50:])
    lows_array = np.array(lows[-50:])
    
    peaks_idx = argrelextrema(highs_array, np.greater, order=5)[0]
    troughs_idx = argrelextrema(lows_array, np.less, order=5)[0]
    
    peaks = highs_array[peaks_idx] if len(peaks_idx) > 0 else []
    troughs = lows_array[troughs_idx] if len(troughs_idx) > 0 else []
    
    resistance_levels = sorted(peaks, reverse=True)[:2] if len(peaks) > 0 else [0, 0]
    support_levels = sorted(troughs)[:2] if len(troughs) > 0 else [0, 0]
    
    support1 = support_levels[0] if support_levels else 0
    support2 = support_levels[1] if len(support_levels) > 1 else 0
    resistance1 = resistance_levels[0] if resistance_levels else 0
    resistance2 = resistance_levels[1] if len(resistance_levels) > 1 else 0
    
    return round(support1, 8), round(support2, 8), round(resistance1, 8), round(resistance2, 8)

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
    
    # SMC Badges
    smc_badges = []
    if signal.get('order_block'):
        smc_badges.append("🏛️ OB")
    if signal.get('fvg'):
        smc_badges.append("📉 FVG")
    if signal.get('divergence'):
        smc_badges.append(f"🔄 DIV")
    if signal.get('bos'):
        smc_badges.append("📊 BOS")
    if signal.get('liquidity_sweep'):
        smc_badges.append("💧 LS")
    if signal.get('candle_pattern') != 'none':
        smc_badges.append(f"🕯️ {signal.get('candle_pattern')}")
    
    smc_text = " | ".join(smc_badges) if smc_badges else "No SMC Signals"
    
    # Best Indicators
    best_indicators = learner.get_best_indicators(3)
    best_text = ""
    if best_indicators:
        best_text = " | ".join([f"{ind} ({acc}%)" for ind, acc in best_indicators[:3]])
    
    phase_emoji = {
        'bullish_trend': '🚀',
        'bearish_trend': '📉',
        'ranging': '⬆️⬇️',
        'accumulation': '🏗️',
        'distribution': '📤',
        'neutral': '⚖️'
    }.get(signal.get('market_phase', 'neutral'), '⚖️')
    
    msg = f"""
{emoji} <b>{signal['symbol']}</b> | {direction}
{phase_emoji} <b>Phase:</b> {signal.get('market_phase', 'neutral').upper()}
🧠 <b>SMC Score:</b> {signal.get('smc_score', 0):.1f}/100
🎯 <b>RR Ratio:</b> {signal.get('rr_ratio', 0):.2f}:1
🏷️ <b>SMC Signals:</b> {smc_text}
📈 <b>Bullish TFs:</b> {signal.get('bullish_timeframes', 0)}/10

<b>📊 ENTRY:</b> <code>${signal['entry']:.6f}</code>
<b>🛑 SL:</b> <code>${signal['sl']:.6f}</code>

<b>🎯 PROFIT TARGETS (ATR-Based):</b>
• TP1: <code>${signal['tp1']:.6f}</code> <i>(+{p1:.1f}%)</i> ⭐
• TP2: <code>${signal['tp2']:.6f}</code> <i>(+{p2:.1f}%)</i>
• TP3: <code>${signal['tp3']:.6f}</code> <i>(+{p3:.1f}%)</i>
• TP4: <code>${signal['tp4']:.6f}</code> <i>(+{p4:.1f}%)</i>
• TP5: <code>${signal['tp5']:.6f}</code> <i>(+{p5:.1f}%)</i> 🚀

<b>📊 Confidence:</b> {signal['confidence']}%
<b>⭐ Quality:</b> {signal.get('quality_score', 0)}/100
<b>🔍 Trend Filter:</b> {signal.get('trend_filter_score', 0):.1f}

<b>📈 INDICATORS:</b>
• RSI: {signal['rsi']:.1f}
• MACD: {signal['macd']:.6f}
• ADX: {signal.get('adx', 0):.1f}
• ATR: ${signal['atr']:.6f}
• Volume Spike: {signal.get('volume_trend', 0):.1f}x
• Stoch RSI: {signal.get('stoch_rsi', 50):.1f}
• MFI: {signal.get('mfi', 50):.1f}
• CMF: {signal.get('cmf', 0):.3f}

<b>🛡️ KEY LEVELS:</b>
• S1: ${signal.get('support1', 0):.4f}
• R1: ${signal.get('resistance1', 0):.4f}

<b>📝 ANALYSIS:</b>
"""
    reasons = signal.get('reasons', [])
    for i, reason in enumerate(reasons[:10], 1):
        msg += f"{i}. {reason}\n"
    
    if 'timeframes' in signal:
        msg += "\n<b>⏱️ TIMEFRAMES:</b>\n"
        for tf, data in signal['timeframes'].items():
            score_emoji = "🟢" if data['score'] > 55 else "🔴" if data['score'] < 45 else "🟡"
            msg += f"• {tf}: {score_emoji} S:{data['score']:.0f} | SMC:{data.get('smc_score', 0):.0f}\n"
    
    if best_text:
        msg += f"\n🧠 <b>Best Indicators:</b> {best_text}"
    
    msg += f"""
━━━━━━━━━━━━━━━━━━━━━━
<b>🧠 REAL LEARNING SYSTEM:</b>
• Win Rate: {learner.get_accuracy()}%
• ✅ Wins: {learner.positive} | ❌ Losses: {learner.negative}
• 📊 Total Trades: {learner.total_trades}
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
                {'text': '📊 تحلیل کامل SMC', 'callback_data': f'analysis_{signal_id}'},
                {'text': '🧠 بهترین اندیکاتورها', 'callback_data': f'best_indicators'}
            ]
        ]
    }
    
    return msg, keyboard

# ============================================================
# ADMIN PANEL
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
            {'text': '⚙️ تنظیمات SMC', 'callback_data': 'admin_settings'},
            {'text': '🔄 ریست یادگیری', 'callback_data': 'admin_reset'}
        ],
        [
            {'text': '📢 ارسال پیام همگانی', 'callback_data': 'admin_broadcast'},
            {'text': '🔄 رفرش پنل', 'callback_data': 'admin_refresh'}
        ]
    ]
}

def show_admin_panel(chat_id=None):
    if chat_id is None:
        chat_id = ADMIN_ID
    
    settings = db.get_all_settings()
    stats = db.get_stats()
    
    signal_enabled = settings.get('signal_enabled', '0') == '1'
    payment_enabled = settings.get('payment_enabled', '0') == '1'
    
    best_indicators = learner.get_best_indicators(5)
    best_text = "\n".join([f"  • {ind}: {acc}%" for ind, acc in best_indicators]) if best_indicators else "  • No data yet"
    
    msg = f"""
🔐 <b>🚀 پنل مدیریت V23 - FINAL EDITION</b>
━━━━━━━━━━━━━━━━━━━━━━

<b>📡 وضعیت سیستم:</b>
• 🤖 ربات: 🟢 فعال
• 📡 ارسال سیگنال: {'🟢 فعال' if signal_enabled else '🔴 غیرفعال'}
• 💳 حالت پولی: {'🟢 فعال' if payment_enabled else '🔴 غیرفعال'}

<b>📈 آمار:</b>
• 👤 کاربران: {stats.get('users', 0)}
• 🟢 فعال: {stats.get('active', 0)}
• 👑 پریمیوم: {stats.get('premium', 0)}
• 📊 سیگنال امروز: {stats.get('today', 0)}
• 📈 کل سیگنال‌ها: {stats.get('signals', 0)}
• 🎯 نرخ برد: {stats.get('win_rate', 0)}%
• 💳 پرداخت‌های در انتظار: {stats.get('pending', 0)}

<b>⚙️ تنظیمات SMC:</b>
• 📈 تایم‌فریم صعودی: {settings.get('min_bullish_timeframes', 7)}/10
• 📊 حداقل ADX: {settings.get('min_adx', 25)}
• 💥 حجم اسپایک: {settings.get('min_volume_spike', 1.5)}x
• 🎯 حداقل RR: {settings.get('min_rr_ratio', 2.0)}:1
• 🔍 فیلتر روند: {'🟢 فعال' if settings.get('trend_filter_strict', '1') == '1' else '🔴 غیرفعال'}

<b>🧠 REAL LEARNING SYSTEM:</b>
• دقت: {learner.get_accuracy()}%
• ✅ برد: {learner.positive}
• ❌ باخت: {learner.negative}
• 📊 کل معاملات: {learner.total_trades}

<b>🏆 بهترین اندیکاتورها:</b>
{best_text}

━━━━━━━━━━━━━━━━━━━━━━
<b>📌 برای مدیریت کلیک کنید:</b>
"""
    
    send_telegram(msg, chat_id, ADMIN_PANEL_BUTTONS)

def handle_admin_callback(callback_data):
    try:
        logger.info(f"📌 Admin callback: {callback_data}")
        
        if callback_data == 'admin_signal_on':
            db.update_setting('signal_enabled', '1')
            send_admin("✅ ارسال سیگنال فعال شد")
            show_admin_panel()
            return True
        
        elif callback_data == 'admin_signal_off':
            db.update_setting('signal_enabled', '0')
            send_admin("🔴 ارسال سیگنال غیرفعال شد")
            show_admin_panel()
            return True
        
        elif callback_data == 'admin_pay_on':
            db.update_setting('payment_enabled', '1')
            send_admin("💰 حالت پولی فعال شد")
            show_admin_panel()
            return True
        
        elif callback_data == 'admin_pay_off':
            db.update_setting('payment_enabled', '0')
            send_admin("💳 حالت پولی غیرفعال شد")
            show_admin_panel()
            return True
        
        elif callback_data == 'admin_stats':
            stats = db.get_stats()
            best_indicators = learner.get_best_indicators(5)
            best_text = "\n".join([f"• {ind}: {acc}%" for ind, acc in best_indicators]) if best_indicators else "• No data"
            msg = f"""
📊 <b>آمار کامل</b>
━━━━━━━━━━━━━━━━━━━━━━
👤 کاربران: {stats.get('users', 0)}
🟢 فعال: {stats.get('active', 0)}
👑 پریمیوم: {stats.get('premium', 0)}
📈 سیگنال‌ها: {stats.get('signals', 0)}
🎯 نرخ برد: {stats.get('win_rate', 0)}%

🧠 <b>سیستم یادگیری:</b>
دقت: {learner.get_accuracy()}%
برد: {learner.positive}
باخت: {learner.negative}
کل معاملات: {learner.total_trades}

🏆 <b>بهترین اندیکاتورها:</b>
{best_text}
"""
            send_admin(msg)
            show_admin_panel()
            return True
        
        elif callback_data == 'admin_payments':
            payments = db.get_pending_payments()
            if not payments:
                send_admin("💳 هیچ پرداخت در انتظاری وجود ندارد")
                show_admin_panel()
                return True
            
            msg = f"💳 پرداخت‌های در انتظار ({len(payments)})\n"
            for payment in payments[:10]:
                payment_id, user_id, payment_hash, amount, created_at = payment
                msg += f"#{payment_id} | کاربر: {user_id} | {amount} | {created_at[:16]}\n"
            send_admin(msg)
            show_admin_panel()
            return True
        
        elif callback_data == 'admin_settings':
            settings = db.get_all_settings()
            msg = "⚙️ <b>تنظیمات SMC</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
            for key, value in settings.items():
                msg += f"\n📌 {key}: {value}"
            msg += """
━━━━━━━━━━━━━━━━━━━━━━
<b>✏️ تغییر تنظیمات:</b>
<code>/set min_bullish_timeframes 8</code>
<code>/set min_adx 30</code>
<code>/set min_volume_spike 2</code>
<code>/set min_rr_ratio 2.5</code>
<code>/set trend_filter_strict 1</code>
"""
            send_admin(msg)
            show_admin_panel()
            return True
        
        elif callback_data == 'admin_reset':
            learner.positive = 0
            learner.negative = 0
            learner.total_trades = 0
            learner.winning_trades = 0
            for key in learner.indicator_weights:
                learner.indicator_weights[key] = 1.0
            for key in learner.phase_weights:
                learner.phase_weights[key] = 1.0
            for key in learner.smc_weights:
                learner.smc_weights[key] = 1.0
            learner.indicator_success = {}
            learner.save()
            send_admin("🔄 سیستم یادگیری ریست شد")
            show_admin_panel()
            return True
        
        elif callback_data == 'admin_broadcast':
            db.update_setting('broadcast_mode', '1')
            send_admin("📢 حالت ارسال همگانی فعال شد\nلطفاً پیام خود را ارسال کنید.")
            return True
        
        elif callback_data == 'admin_refresh':
            show_admin_panel()
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Admin callback error: {e}")
        send_admin(f"❌ خطا: {str(e)}")
        return False

def handle_feedback_callback(callback_data, user_id):
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
        
        # پاسخ به کاربر
        if feedback_type == 'positive':
            msg = f"""
✅ <b>تبریک! سود کردید! 💰</b>
━━━━━━━━━━━━━━━━━━━━━━
🎯 دقت سیستم: {learner.get_accuracy()}%
✅ کل بردها: {learner.positive}
❌ کل باخت‌ها: {learner.negative}
📊 کل معاملات: {learner.total_trades}

🌟 بازخورد شما به بهبود الگوریتم کمک می‌کند!
🚀 به سوددهی ادامه دهید!
"""
        else:
            msg = f"""
❌ <b>دفعه بعد موفق می‌شوید!</b>
━━━━━━━━━━━━━━━━━━━━━━
🎯 دقت سیستم: {learner.get_accuracy()}%
✅ کل بردها: {learner.positive}
❌ کل باخت‌ها: {learner.negative}
📊 کل معاملات: {learner.total_trades}

🔧 بازخورد شما به بهبود الگوریتم کمک می‌کند!
💪 به تلاش ادامه دهید!
"""
        
        send_telegram(msg, user_id)
        
        # اطلاع به ادمین
        admin_msg = f"""
📊 بازخورد جدید
👤 کاربر: {user_id}
📈 نماد: {signal['symbol'] if signal else 'N/A'}
📝 بازخورد: {'✅ سود' if feedback_type == 'positive' else '❌ ضرر'}
🎯 دقت سیستم: {learner.get_accuracy()}%
"""
        send_admin(admin_msg)
        return True
        
    except Exception as e:
        logger.error(f"Feedback callback error: {e}")
        return False

def handle_best_indicators_callback(user_id):
    """نمایش بهترین اندیکاتورها به کاربر"""
    best_indicators = learner.get_best_indicators(10)
    if not best_indicators:
        send_telegram("🧠 <b>هنوز داده‌ای برای نمایش وجود ندارد</b>\n\nپس از چند معامله، بهترین اندیکاتورها نمایش داده می‌شوند.", user_id)
        return True
    
    msg = "🏆 <b>بهترین اندیکاتورها بر اساس عملکرد</b>\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, (indicator, accuracy) in enumerate(best_indicators, 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📊"
        msg += f"{emoji} <b>{indicator}</b>: {accuracy}%\n"
    
    msg += f"\n📊 <b>دقت کلی سیستم:</b> {learner.get_accuracy()}%"
    msg += f"\n✅ <b>معاملات موفق:</b> {learner.positive}"
    msg += f"\n❌ <b>معاملات ناموفق:</b> {learner.negative}"
    
    send_telegram(msg, user_id)
    return True

def handle_callback(callback_data, user_id):
    try:
        if callback_data.startswith('admin_'):
            return handle_admin_callback(callback_data)
        elif callback_data.startswith('fb_'):
            return handle_feedback_callback(callback_data, user_id)
        elif callback_data == 'best_indicators':
            return handle_best_indicators_callback(user_id)
        elif callback_data.startswith('analysis_'):
            signal_id = int(callback_data.replace('analysis_', ''))
            signal = db.get_signal(signal_id)
            if signal:
                msg = f"""
📊 <b>تحلیل کامل SMC</b>
━━━━━━━━━━━━━━━━━━━━━━
<b>نماد:</b> {signal['symbol']}
<b>جهت:</b> {signal['direction']}
<b>اطمینان:</b> {signal['confidence']}%
<b>SMC Score:</b> {signal.get('smc_score', 0):.1f}
<b>Trend Filter:</b> {signal.get('trend_filter_score', 0):.1f}

<b>📈 اندیکاتورها:</b>
• RSI: {signal['rsi']:.1f}
• ADX: {signal.get('adx', 0):.1f}
• ATR: ${signal['atr']:.6f}
• RR Ratio: {signal.get('rr_ratio', 0):.2f}:1

<b>🛡️ سطوح کلیدی:</b>
• S1: ${signal.get('support1', 0):.4f}
• R1: ${signal.get('resistance1', 0):.4f}

<b>📊 فاز بازار:</b> {signal.get('market_phase', 'خنثی').upper()}
<b>📈 تایم‌فریم صعودی:</b> {signal.get('bullish_timeframes', 0)}/10
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
        send_telegram("❌ هش تراکنش نامعتبر", user_id)
        return False
    
    payment_hash = match.group()
    
    existing = db.get_payment_by_hash(payment_hash)
    if existing:
        send_telegram("⚠️ این هش قبلاً ثبت شده است.", user_id)
        return False
    
    payment_id = db.add_payment(user_id, payment_hash)
    if payment_id:
        admin_msg = f"""
💳 پرداخت جدید
👤 کاربر: {user_id}
💰 مبلغ: {db.get_setting('price') or PRICE}
🔑 هش: {payment_hash}
✅ /confirm_{payment_id}
❌ /reject_{payment_id}
"""
        send_admin(admin_msg)
        send_telegram("✅ هش پرداخت ثبت شد! در انتظار تایید.", user_id)
        return True
    
    return False

def handle_subscribe(user_id):
    user = db.get_user(user_id)
    if user and user['is_active'] == 1:
        expire = user['subscription_expire']
        if expire:
            days_left = (datetime.fromisoformat(expire) - datetime.now()).days
            if days_left > 0:
                send_telegram(f"✅ اشتراک فعال - {days_left} روز باقی مانده", user_id)
                return True
    
    wallet = db.get_setting('wallet') or WALLET_ADDRESS
    price = db.get_setting('price') or PRICE
    
    msg = f"""
💳 <b>اشتراک</b>
━━━━━━━━━━━━━━━━━━━━━━
💰 مبلغ: {price}
📡 شبکه: TRC20 (USDT)
🏦 آدرس: <code>{wallet}</code>

📝 مراحل:
1. ارسال {price} USDT (TRC20)
2. کپی هش تراکنش
3. ارسال هش به ربات
4. منتظر تایید ادمین
"""
    send_telegram(msg, user_id)
    return True

# ============================================================
# MAIN LOOP
# ============================================================

def main_loop():
    logger.info("🚀 Starting ULTIMATE SIGNAL BOT V23 - FINAL EDITION...")
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
            
            logger.info(f"🔄 Cycle {cycle} - Scanning {len(SYMBOLS)} symbols with SMC + Real Learning")
            
            signals = []
            for symbol in SYMBOLS:
                try:
                    signal = ultra_smart_analysis(symbol)
                    if signal and signal.get('confidence', 0) >= min_confidence:
                        signals.append(signal)
                        logger.info(f"✅ {signal['symbol']}: {signal['signal']} ({signal['confidence']}%) - SMC: {signal.get('smc_score', 0):.1f}")
                except Exception as e:
                    logger.error(f"Error processing {symbol}: {e}")
                time.sleep(0.03)
            
            signals.sort(key=lambda x: (x.get('quality_score', 0), x.get('smc_score', 0)), reverse=True)
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
                    logger.info("⏳ No signals passed SMC + Learning filters")
            
            if cycle % 3 == 0:
                payments = db.get_pending_payments()
                if payments:
                    send_admin(f"💳 {len(payments)} پرداخت در انتظار")
            
            if cycle % 20 == 0:
                stats = db.get_stats()
                best_indicators = learner.get_best_indicators(3)
                best_text = ", ".join([f"{ind} ({acc}%)" for ind, acc in best_indicators]) if best_indicators else "No data"
                send_admin(f"""
🔄 بروزرسانی
📊 امروز: {stats.get('today', 0)}
📈 کل: {stats.get('signals', 0)}
🎯 نرخ برد: {stats.get('win_rate', 0)}%
🧠 دقت: {learner.get_accuracy()}%
🏆 بهترین: {best_text}
""")
            
            logger.info(f"⏱ Waiting {INTERVAL//60} minutes...")
            time.sleep(INTERVAL)
            
        except Exception as e:
            logger.error(f"❌ Main loop error: {e}")
            send_admin(f"❌ خطا: {str(e)}")
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
            users = db.cursor.execute('SELECT user_id FROM users').fetchall()
            sent = 0
            for user in users:
                try:
                    send_telegram(f"📢 پیام از ادمین\n\n{text}", user[0])
                    sent += 1
                    time.sleep(0.1)
                except:
                    pass
            send_admin(f"✅ پیام به {sent} کاربر ارسال شد")
            db.update_setting('broadcast_mode', '0')
            return
        
        if text.startswith('/'):
            if user_id == ADMIN_ID:
                handle_admin_command(text)
            else:
                if text == '/start':
                    send_telegram("""
🚀 <b>ربات سیگنال SMC - FINAL EDITION</b>
🤖 <b>نسخه V23 با یادگیری واقعی</b>

📊 دریافت سیگنال‌های حرفه‌ای با مفاهیم SMC

<b>📌 دستورات:</b>
/subscribe - خرید اشتراک
/help - راهنما
/status - وضعیت اشتراک

<b>🔐 ویژگی‌ها:</b>
• Order Block + FVG
• Divergence Detection
• Break of Structure (BOS)
• Real Learning System
• Multi-Factor Confidence
""", user_id)
                elif text == '/subscribe':
                    handle_subscribe(user_id)
                elif text == '/help':
                    send_telegram("""
📚 راهنما
/subscribe - خرید اشتراک
/status - وضعیت اشتراک
""", user_id)
                elif text == '/status':
                    user = db.get_user(user_id)
                    if user and user['is_active'] == 1:
                        expire = user['subscription_expire']
                        if expire:
                            days_left = (datetime.fromisoformat(expire) - datetime.now()).days
                            if days_left > 0:
                                send_telegram(f"✅ اشتراک فعال - {days_left} روز باقی مانده", user_id)
                            else:
                                send_telegram("⏰ اشتراک منقضی شد", user_id)
                        else:
                            send_telegram("⚠️ اشتراک فعال نیست", user_id)
                    else:
                        send_telegram("⚠️ اشتراک فعال نیست", user_id)
            return
        
        if user_id != ADMIN_ID and db.get_setting('payment_enabled') == '1':
            hash_pattern = r'[0-9a-fA-F]{64}|0x[0-9a-fA-F]{64}|[A-Za-z0-9]{50,}'
            if re.search(hash_pattern, text):
                handle_payment_hash(user_id, text)
        
    except Exception as e:
        logger.error(f"Message error: {e}")

def handle_admin_command(text):
    try:
        if text == '/panel':
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
                    send_telegram("✅ پرداخت تایید شد!", user_id)
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
                        send_telegram("❌ پرداخت رد شد", payment[0])
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
            msg = "💳 پرداخت‌های در انتظار\n"
            for payment in payments[:10]:
                payment_id, user_id, payment_hash, amount, created_at = payment
                msg += f"#{payment_id} | کاربر: {user_id} | {amount} | {created_at[:16]}\n"
            send_admin(msg)
            return True
        elif text == '/stats':
            stats = db.get_stats()
            best_indicators = learner.get_best_indicators(5)
            best_text = ", ".join([f"{ind} ({acc}%)" for ind, acc in best_indicators]) if best_indicators else "No data"
            msg = f"""
📊 آمار کامل
👤 کاربران: {stats.get('users', 0)}
🟢 فعال: {stats.get('active', 0)}
👑 پریمیوم: {stats.get('premium', 0)}
📈 سیگنال‌ها: {stats.get('signals', 0)}
🎯 نرخ برد: {stats.get('win_rate', 0)}%
🧠 دقت: {learner.get_accuracy()}%
🏆 بهترین: {best_text}
"""
            send_admin(msg)
            return True
        elif text == '/help':
            msg = """
📚 راهنمای دستورات
/panel - پنل مدیریت
/on - فعال‌سازی سیگنال
/off - غیرفعال‌سازی سیگنال
/pay_on - فعال‌سازی پرداخت
/pay_off - غیرفعال‌سازی پرداخت
/payments - پرداخت‌ها
/stats - آمار
/set key value - تغییر تنظیمات
/confirm_ID - تایید پرداخت
/reject_ID - رد پرداخت
"""
            send_admin(msg)
            return True
        return False
    except Exception as e:
        logger.error(f"Admin command error: {e}")
        return False

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
        print("🚀 ULTIMATE SIGNAL BOT V23 - FINAL EDITION")
        print("="*70)
        print("📊 PROFESSIONAL SMC + REAL LEARNING")
        print("="*70)
        print("🧠 KEY FEATURES:")
        print("  ✅ Order Block + FVG Detection")
        print("  ✅ RSI/MACD Divergence")
        print("  ✅ Break of Structure (BOS)")
        print("  ✅ Liquidity Sweep")
        print("  ✅ Candle Pattern Recognition")
        print("  ✅ Multi-Factor Confidence")
        print("  ✅ Trend Filter for Bearish Markets")
        print("  ✅ Real Learning System (Weight Adjustment)")
        print("="*70)
        print("📈 INDICATORS:")
        print("  ✅ EMA 20/50/100/200 + SuperTrend")
        print("  ✅ Bollinger Bands + Ichimoku")
        print("  ✅ Volume Spike + OBV + CMF + MFI")
        print("  ✅ Stochastic RSI + ROC")
        print("="*70)
        print("🎯 TP Based on ATR: risk * 2,3,5,8,13")
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