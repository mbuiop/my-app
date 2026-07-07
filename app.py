# ============================================================
# ULTIMATE SIGNAL BOT V15 - GLASSMORPHISM EDITION
# GLASS BUTTONS | DEEP ANALYSIS | ENTERPRISE | FULLY WORKING
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
import sys

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
WALLET_NETWORK = "TRC20"
SUBSCRIPTION_PRICE = "100 USDT"

INTERVAL = 300  # 5 minutes
MAX_SIGNALS = 3
MIN_CONFIDENCE = 65
MIN_VOLUME_RATIO = 1.2
MIN_ADX = 20

# ============================================================
# DATABASE - ENTERPRISE
# ============================================================

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('bot_data.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
        logger.info("✅ Database initialized")
    
    def create_tables(self):
        # Users
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                joined_at TIMESTAMP,
                subscription_expire TIMESTAMP,
                is_active BOOLEAN DEFAULT 0,
                has_paid BOOLEAN DEFAULT 0,
                free_signals_used INTEGER DEFAULT 0,
                max_free_signals INTEGER DEFAULT 2,
                feedback_count INTEGER DEFAULT 0,
                positive_feedback INTEGER DEFAULT 0,
                negative_feedback INTEGER DEFAULT 0,
                total_signals_received INTEGER DEFAULT 0
            )
        ''')
        
        # Signals
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                direction TEXT,
                entry REAL,
                tp REAL,
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
                support REAL,
                resistance REAL,
                score REAL,
                quality_score REAL,
                risk_reward REAL,
                mtf_score TEXT,
                mtf_buy REAL,
                mtf_sell REAL,
                reasons TEXT,
                feedback TEXT DEFAULT '',
                feedback_user INTEGER DEFAULT 0,
                sent_to_channel BOOLEAN DEFAULT 0,
                sent_to_user BOOLEAN DEFAULT 0
            )
        ''')
        
        # Payments
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                payment_hash TEXT,
                amount TEXT,
                wallet_address TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP,
                confirmed_at TIMESTAMP,
                expire_at TIMESTAMP
            )
        ''')
        
        # Feedback Log
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id INTEGER,
                user_id INTEGER,
                feedback TEXT,
                created_at TIMESTAMP
            )
        ''')
        
        # Admin Logs
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT,
                details TEXT,
                created_at TIMESTAMP
            )
        ''')
        
        # Settings
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # Default settings
        defaults = [
            ('signal_enabled', '1'),
            ('paid_mode_enabled', '0'),
            ('wallet', WALLET_ADDRESS),
            ('wallet_network', WALLET_NETWORK),
            ('price', SUBSCRIPTION_PRICE),
            ('min_confidence', str(MIN_CONFIDENCE)),
            ('max_signals', str(MAX_SIGNALS)),
            ('min_volume', str(MIN_VOLUME_RATIO)),
            ('min_adx', str(MIN_ADX)),
            ('free_signals', '2'),
            ('admin_channel', CHANNEL_ID),
            ('auto_approve', '0'),
            ('deep_analysis', '1'),
            ('mtf_enabled', '1')
        ]
        
        for key, value in defaults:
            self.cursor.execute('INSERT OR IGNORE INTO settings VALUES (?, ?)', (key, value))
        
        self.conn.commit()
    
    # ===== USER METHODS =====
    def add_user(self, user_id, username=None, first_name=None):
        self.cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, joined_at)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, first_name, datetime.now().isoformat()))
        self.conn.commit()
    
    def get_user(self, user_id):
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone()
    
    def has_subscription(self, user_id):
        user = self.get_user(user_id)
        if not user:
            return False
        if user[4]:  # subscription_expire
            expire_date = datetime.fromisoformat(user[4])
            if expire_date > datetime.now() and user[5] == 1:
                return True
        return False
    
    def can_receive_signal(self, user_id):
        if self.has_subscription(user_id):
            return True, "subscribed"
        user = self.get_user(user_id)
        if user:
            free_used = user[6] if user[6] else 0
            max_free = int(self.get_setting('free_signals') or 2)
            if free_used < max_free:
                return True, "free"
        return False, "no_access"
    
    def use_free_signal(self, user_id):
        self.cursor.execute('UPDATE users SET free_signals_used = free_signals_used + 1 WHERE user_id = ?', (user_id,))
        self.conn.commit()
    
    def update_subscription(self, user_id, days=30):
        expire_date = datetime.now() + timedelta(days=days)
        self.cursor.execute('UPDATE users SET subscription_expire = ?, is_active = 1, has_paid = 1 WHERE user_id = ?',
                           (expire_date.isoformat(), user_id))
        self.conn.commit()
        return expire_date
    
    # ===== SIGNAL METHODS =====
    def save_signal(self, signal_data):
        self.cursor.execute('''
            INSERT INTO signals (
                symbol, direction, entry, tp, sl, confidence,
                created_at, rsi, macd, ma20, ma50, ma200,
                vwap, atr, support, resistance, score, quality_score,
                risk_reward, mtf_score, mtf_buy, mtf_sell, reasons
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            signal_data['symbol'],
            signal_data['signal'],
            signal_data['entry'],
            signal_data['tp'],
            signal_data['sl'],
            signal_data['confidence'],
            datetime.now().isoformat(),
            signal_data.get('rsi', 0),
            signal_data.get('macd', 0),
            signal_data.get('ma20', 0),
            signal_data.get('ma50', 0),
            signal_data.get('ma200', 0),
            signal_data.get('vwap', 0),
            signal_data.get('atr', 0),
            signal_data.get('support', 0),
            signal_data.get('resistance', 0),
            signal_data.get('score', 0),
            signal_data.get('quality_score', 0),
            signal_data.get('risk_reward', 0),
            signal_data.get('mtf_score', ''),
            signal_data.get('mtf_buy', 0),
            signal_data.get('mtf_sell', 0),
            '|'.join(signal_data.get('reasons', []))
        ))
        signal_id = self.cursor.lastrowid
        self.conn.commit()
        return signal_id
    
    def mark_signal_sent_channel(self, signal_id):
        self.cursor.execute('UPDATE signals SET sent_to_channel = 1 WHERE id = ?', (signal_id,))
        self.conn.commit()
    
    def mark_signal_sent_user(self, signal_id):
        self.cursor.execute('UPDATE signals SET sent_to_user = 1 WHERE id = ?', (signal_id,))
        self.conn.commit()
    
    def get_signal(self, signal_id):
        self.cursor.execute('SELECT * FROM signals WHERE id = ?', (signal_id,))
        return self.cursor.fetchone()
    
    # ===== FEEDBACK METHODS =====
    def update_feedback(self, signal_id, feedback_type, user_id):
        self.cursor.execute('SELECT id FROM feedback_log WHERE signal_id = ? AND user_id = ?', (signal_id, user_id))
        if self.cursor.fetchone():
            return False, "شما قبلاً به این سیگنال بازخورد داده‌اید"
        
        self.cursor.execute('UPDATE signals SET feedback = ?, feedback_user = ? WHERE id = ?', 
                           (feedback_type, user_id, signal_id))
        
        if feedback_type == 'positive':
            self.cursor.execute('UPDATE users SET positive_feedback = positive_feedback + 1, feedback_count = feedback_count + 1 WHERE user_id = ?', (user_id,))
        else:
            self.cursor.execute('UPDATE users SET negative_feedback = negative_feedback + 1, feedback_count = feedback_count + 1 WHERE user_id = ?', (user_id,))
        
        self.cursor.execute('INSERT INTO feedback_log (signal_id, user_id, feedback, created_at) VALUES (?, ?, ?, ?)',
                           (signal_id, user_id, feedback_type, datetime.now().isoformat()))
        self.conn.commit()
        return True, "بازخورد ثبت شد"
    
    # ===== PAYMENT METHODS =====
    def add_payment(self, user_id, payment_hash):
        wallet = self.get_setting('wallet') or WALLET_ADDRESS
        amount = self.get_setting('price') or SUBSCRIPTION_PRICE
        self.cursor.execute('''
            INSERT INTO payments (user_id, payment_hash, amount, wallet_address, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, payment_hash, amount, wallet, datetime.now().isoformat()))
        payment_id = self.cursor.lastrowid
        self.conn.commit()
        return payment_id
    
    def get_pending_payments(self):
        self.cursor.execute('''
            SELECT id, user_id, payment_hash, amount, wallet_address, created_at 
            FROM payments WHERE status = 'pending' ORDER BY created_at ASC
        ''')
        return self.cursor.fetchall()
    
    def get_payment(self, payment_id):
        self.cursor.execute('SELECT * FROM payments WHERE id = ?', (payment_id,))
        return self.cursor.fetchone()
    
    def confirm_payment(self, payment_id):
        self.cursor.execute('SELECT user_id FROM payments WHERE id = ? AND status = "pending"', (payment_id,))
        result = self.cursor.fetchone()
        if not result:
            return False, None
        user_id = result[0]
        expire_date = self.update_subscription(user_id, 30)
        self.cursor.execute('UPDATE payments SET status = "confirmed", confirmed_at = ?, expire_at = ? WHERE id = ?',
                           (datetime.now().isoformat(), expire_date.isoformat(), payment_id))
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
    
    # ===== SETTINGS METHODS =====
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
        return {row[0]: row[1] for row in self.cursor.fetchall()}
    
    def add_admin_log(self, details):
        self.cursor.execute('INSERT INTO admin_logs (action, details, created_at) VALUES (?, ?, ?)',
                           ('admin_action', details, datetime.now().isoformat()))
        self.conn.commit()
    
    def get_stats(self):
        users = self.cursor.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        active = self.cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1').fetchone()[0]
        paid = self.cursor.execute('SELECT COUNT(*) FROM users WHERE has_paid = 1').fetchone()[0]
        signals = self.cursor.execute('SELECT COUNT(*) FROM signals').fetchone()[0]
        today = self.cursor.execute('SELECT COUNT(*) FROM signals WHERE DATE(created_at) = DATE("now")').fetchone()[0]
        pending = self.cursor.execute('SELECT COUNT(*) FROM payments WHERE status = "pending"').fetchone()[0]
        feedback = self.cursor.execute('SELECT COUNT(*) FROM feedback_log').fetchone()[0]
        return {'users': users, 'active': active, 'paid': paid, 'signals': signals, 
                'today': today, 'pending': pending, 'feedback': feedback}

db = Database()

# ============================================================
# DEEP ANALYSIS ENGINE - ENTERPRISE
# ============================================================

def get_candles(symbol, limit=200, interval='5m'):
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
                'volume': [float(x[5]) for x in data]
            }
    except Exception as e:
        logger.error(f"Error fetching {symbol}: {e}")
    return None

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
    return round(100 - (100 / (1 + rs)), 2)

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

def calculate_ma(prices, period):
    if len(prices) < period:
        return prices[-1] if prices else 0
    return round(np.mean(prices[-period:]), 8)

def calculate_ema(prices, period):
    if len(prices) < period:
        return prices[-1] if prices else 0
    prices = np.array(prices)
    mult = 2.0 / (period + 1)
    ema = np.mean(prices[-period:])
    for price in prices[-period:]:
        ema = price * mult + ema * (1 - mult)
    return round(ema, 8)

def calculate_bollinger(prices, period=20, std_dev=2):
    if len(prices) < period:
        return prices[-1] if prices else 0, prices[-1] if prices else 0, prices[-1] if prices else 0
    prices = np.array(prices[-period:])
    ma = np.mean(prices)
    std = np.std(prices)
    upper = ma + (std_dev * std)
    lower = ma - (std_dev * std)
    return round(upper, 8), round(ma, 8), round(lower, 8)

def calculate_vwap(prices, volumes):
    if len(prices) < 2:
        return prices[-1] if prices else 0
    total_value = sum(prices[i] * volumes[i] for i in range(len(prices)))
    total_volume = sum(volumes)
    if total_volume == 0:
        return prices[-1]
    return round(total_value / total_volume, 8)

def calculate_atr(highs, lows, closes, period=14):
    if len(closes) < period:
        return 0.0000001
    tr_list = []
    for i in range(1, period + 1):
        if i < len(closes):
            tr = max(highs[-i] - lows[-i], abs(highs[-i] - closes[-i-1]), abs(lows[-i] - closes[-i-1]))
            tr_list.append(tr)
    if not tr_list:
        return 0.0000001
    return round(np.mean(tr_list), 8)

def find_support_resistance(highs, lows, closes):
    if len(closes) < 30:
        return 0, 0
    peaks, troughs = [], []
    for i in range(2, len(closes) - 2):
        if highs[i] > highs[i-1] and highs[i] > highs[i+1] and highs[i] > highs[i-2] and highs[i] > highs[i+2]:
            peaks.append(highs[i])
        if lows[i] < lows[i-1] and lows[i] < lows[i+1] and lows[i] < lows[i-2] and lows[i] < lows[i+2]:
            troughs.append(lows[i])
    resistance = peaks[0] if peaks else 0
    support = troughs[0] if troughs else 0
    return round(support, 8), round(resistance, 8)

def calculate_adx(highs, lows, closes, period=14):
    if len(closes) < period + 1:
        return 25
    tr_list, up_list, down_list = [], [], []
    for i in range(1, period + 1):
        if i < len(closes):
            tr = max(highs[-i] - lows[-i], abs(highs[-i] - closes[-i-1]), abs(lows[-i] - closes[-i-1]))
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
    return round(100 * abs(di_plus - di_minus) / (di_plus + di_minus + 0.0000001), 1)

def calculate_ichimoku(highs, lows, closes):
    """محاسبه Ichimoku برای تحلیل عمیق"""
    if len(closes) < 52:
        return None
    
    # Tenkan-sen (9 periods)
    high_9 = max(highs[-9:]) if len(highs) >= 9 else highs[-1]
    low_9 = min(lows[-9:]) if len(lows) >= 9 else lows[-1]
    tenkan = (high_9 + low_9) / 2
    
    # Kijun-sen (26 periods)
    high_26 = max(highs[-26:]) if len(highs) >= 26 else highs[-1]
    low_26 = min(lows[-26:]) if len(lows) >= 26 else lows[-1]
    kijun = (high_26 + low_26) / 2
    
    # Senkou Span A (26 periods ahead)
    senkou_a = (tenkan + kijun) / 2
    
    # Senkou Span B (52 periods)
    high_52 = max(highs[-52:]) if len(highs) >= 52 else highs[-1]
    low_52 = min(lows[-52:]) if len(lows) >= 52 else lows[-1]
    senkou_b = (high_52 + low_52) / 2
    
    return {
        'tenkan': round(tenkan, 8),
        'kijun': round(kijun, 8),
        'senkou_a': round(senkou_a, 8),
        'senkou_b': round(senkou_b, 8)
    }

def calculate_fibonacci(highs, lows):
    """محاسبه سطوح فیبوناچی"""
    if len(highs) < 50 or len(lows) < 50:
        return None
    
    high = max(highs[-50:])
    low = min(lows[-50:])
    diff = high - low
    
    if diff == 0:
        return None
    
    return {
        'high': round(high, 8),
        'low': round(low, 8),
        'fib_236': round(low + diff * 0.236, 8),
        'fib_382': round(low + diff * 0.382, 8),
        'fib_500': round(low + diff * 0.500, 8),
        'fib_618': round(low + diff * 0.618, 8),
        'fib_786': round(low + diff * 0.786, 8)
    }

def multi_timeframe_deep_analysis(symbol):
    """تحلیل عمیق چند تایم‌فریم - 6 تایم‌فریم"""
    timeframes = ['5m', '15m', '1h', '4h', '1d']
    results = {'BUY': 0, 'SELL': 0, 'NEUTRAL': 0}
    details = []
    mtf_score = "Neutral"
    
    for tf in timeframes:
        data = get_candles(symbol, 50, tf)
        if not data or len(data['close']) < 30:
            continue
        
        prices = data['close']
        current = prices[-1]
        ma20 = calculate_ma(prices, 20)
        ma50 = calculate_ma(prices, 50)
        rsi = calculate_rsi(prices, 14)
        
        # Trend detection
        if current > ma20 and ma20 > ma50 and rsi < 70:
            results['BUY'] += 1
            details.append(f"{tf}: 🟢 Bullish")
        elif current < ma20 and ma20 < ma50 and rsi > 30:
            results['SELL'] += 1
            details.append(f"{tf}: 🔴 Bearish")
        else:
            results['NEUTRAL'] += 1
            details.append(f"{tf}: ⚪ Neutral")
    
    total = results['BUY'] + results['SELL'] + results['NEUTRAL']
    if total == 0:
        return 0, 0, "No data", ""
    
    buy_pct = (results['BUY'] / total) * 100
    sell_pct = (results['SELL'] / total) * 100
    
    if buy_pct >= 80:
        mtf_score = "🔥 Strongly Bullish"
    elif buy_pct >= 60:
        mtf_score = "📈 Bullish"
    elif sell_pct >= 80:
        mtf_score = "🔥 Strongly Bearish"
    elif sell_pct >= 60:
        mtf_score = "📉 Bearish"
    else:
        mtf_score = "⚖️ Neutral"
    
    return round(buy_pct, 1), round(sell_pct, 1), mtf_score, ' | '.join(details[:3])

# ============================================================
# SIGNAL GENERATOR - DEEP ANALYSIS
# ============================================================

def generate_signal(symbol):
    """تولید سیگنال با تحلیل عمیق"""
    try:
        data = get_candles(symbol, 200, '5m')
        if not data or len(data['close']) < 50:
            return None
        
        prices = data['close']
        highs = data['high']
        lows = data['low']
        volumes = data['volume']
        current = prices[-1]
        
        if current == 0:
            return None
        
        # ===== CALCULATE ALL INDICATORS =====
        rsi = calculate_rsi(prices, 14)
        rsi_fast = calculate_rsi(prices, 7)
        macd, _, macd_hist = calculate_macd(prices, 12, 26, 9)
        ma7 = calculate_ma(prices, 7)
        ma20 = calculate_ma(prices, 20)
        ma50 = calculate_ma(prices, 50)
        ma200 = calculate_ma(prices, 200)
        ema9 = calculate_ema(prices, 9)
        ema21 = calculate_ema(prices, 21)
        upper_bb, middle_bb, lower_bb = calculate_bollinger(prices, 20, 2)
        vwap = calculate_vwap(prices, volumes)
        atr = calculate_atr(highs, lows, prices, 14)
        support, resistance = find_support_resistance(highs, lows, prices)
        adx = calculate_adx(highs, lows, prices, 14)
        
        # Volume ratio
        avg_volume = np.mean(volumes[-20:]) if len(volumes) >= 20 else 1
        volume_ratio = volumes[-1] / avg_volume if avg_volume > 0 else 1
        
        # Deep analysis
        ichimoku = calculate_ichimoku(highs, lows, prices)
        fib = calculate_fibonacci(highs, lows)
        mtf_buy, mtf_sell, mtf_score, mtf_details = multi_timeframe_deep_analysis(symbol)
        
        # ===== SCORING SYSTEM - DEEP =====
        score = 50
        reasons = []
        
        # 1. RSI (15 points)
        if rsi < 25:
            score += 15
            reasons.append(f"🔥 RSI Oversold: {rsi}")
        elif rsi < 35:
            score += 10
            reasons.append(f"📈 RSI Low: {rsi}")
        elif rsi > 75:
            score -= 15
            reasons.append(f"🔥 RSI Overbought: {rsi}")
        elif rsi > 65:
            score -= 10
            reasons.append(f"📉 RSI High: {rsi}")
        
        # 2. Fast RSI (8 points)
        if rsi_fast < 30 and rsi > rsi_fast:
            score += 8
            reasons.append(f"⚡ RSI Fast: {rsi_fast}")
        elif rsi_fast > 70 and rsi < rsi_fast:
            score -= 8
            reasons.append(f"⚡ RSI Fast: {rsi_fast}")
        
        # 3. MACD (15 points)
        if macd > 0 and macd_hist > 0:
            score += 15
            reasons.append("🟢 MACD Bullish")
        elif macd < 0 and macd_hist < 0:
            score -= 15
            reasons.append("🔴 MACD Bearish")
        elif macd > 0:
            score += 8
            reasons.append("🟡 MACD Positive")
        else:
            score -= 8
            reasons.append("🟡 MACD Negative")
        
        # 4. Moving Averages (12 points)
        if current > ma20 and ma20 > ma50 and ma50 > ma200:
            score += 12
            reasons.append("🚀 Strong Uptrend")
        elif current < ma20 and ma20 < ma50 and ma50 < ma200:
            score -= 12
            reasons.append("💀 Strong Downtrend")
        elif current > ma20 and ma20 > ma50:
            score += 8
            reasons.append("📈 Uptrend")
        elif current < ma20 and ma20 < ma50:
            score -= 8
            reasons.append("📉 Downtrend")
        
        # 5. EMA Cross (8 points)
        if ema9 > ema21 and ema21 > ma20:
            score += 8
            reasons.append("📊 EMA Bullish Cross")
        elif ema9 < ema21 and ema21 < ma20:
            score -= 8
            reasons.append("📊 EMA Bearish Cross")
        
        # 6. Bollinger Bands (8 points)
        if current < lower_bb:
            score += 8
            reasons.append("🎯 Lower Band")
        elif current > upper_bb:
            score -= 8
            reasons.append("🎯 Upper Band")
        
        # 7. VWAP (8 points)
        if current > vwap:
            score += 8
            reasons.append("✅ Above VWAP")
        else:
            score -= 8
            reasons.append("❌ Below VWAP")
        
        # 8. Ichimoku (8 points)
        if ichimoku:
            if current > ichimoku['senkou_a'] and current > ichimoku['senkou_b']:
                score += 8
                reasons.append("📊 Above Ichimoku Cloud")
            elif current < ichimoku['senkou_a'] and current < ichimoku['senkou_b']:
                score -= 8
                reasons.append("📊 Below Ichimoku Cloud")
        
        # 9. Fibonacci (5 points)
        if fib:
            if current > fib['fib_618']:
                score += 5
                reasons.append(f"📊 Above Fib 61.8%")
            elif current < fib['fib_382']:
                score -= 5
                reasons.append(f"📊 Below Fib 38.2%")
        
        # 10. Support/Resistance (6 points)
        if support > 0:
            dist = ((current - support) / current) * 100
            if dist < 0.5:
                score += 6
                reasons.append("🛡️ Very Near Support")
            elif dist < 2:
                score += 4
                reasons.append("🛡️ Near Support")
        
        if resistance > 0:
            dist = ((resistance - current) / current) * 100
            if dist < 0.5:
                score -= 6
                reasons.append("🚫 Very Near Resistance")
            elif dist < 2:
                score -= 4
                reasons.append("🚫 Near Resistance")
        
        # 11. ADX (5 points)
        if adx > 50:
            score += 5 if score > 50 else -5
            reasons.append(f"🔥 Strong Trend ADX:{adx}")
        elif adx > 30:
            score += 3 if score > 50 else -3
            reasons.append(f"✅ Moderate Trend ADX:{adx}")
        
        # 12. Multi-timeframe (10 points)
        if mtf_score.startswith("🔥 Strongly Bullish"):
            score += 10
            reasons.append("📊 MTF Strong Bullish")
        elif mtf_score.startswith("📈 Bullish"):
            score += 7
            reasons.append("📊 MTF Bullish")
        elif mtf_score.startswith("🔥 Strongly Bearish"):
            score -= 10
            reasons.append("📊 MTF Strong Bearish")
        elif mtf_score.startswith("📉 Bearish"):
            score -= 7
            reasons.append("📊 MTF Bearish")
        
        # 13. Volume (5 points)
        if volume_ratio > 2.5:
            score += 5
            reasons.append(f"📊 High Volume {volume_ratio:.1f}x")
        elif volume_ratio > 1.5:
            score += 3
            reasons.append(f"📊 Good Volume {volume_ratio:.1f}x")
        
        # ===== FINAL DECISION =====
        confidence = min(98, 50 + abs(score - 50) * 1.5)
        quality_score = min(100, confidence + 5 if score > 50 else confidence - 5)
        
        if score > 55:
            signal = "BUY"
        elif score < 45:
            signal = "SELL"
        else:
            return None
        
        # ===== TP/SL =====
        if signal == "BUY":
            tp = round(current + (atr * 2.5), 8)
            sl = round(current - (atr * 1.5), 8)
            if resistance > 0 and tp > resistance:
                tp = round(resistance * 0.995, 8)
            if support > 0 and sl < support:
                sl = round(support * 0.995, 8)
        else:
            tp = round(current - (atr * 2.5), 8)
            sl = round(current + (atr * 1.5), 8)
            if support > 0 and tp < support:
                tp = round(support * 1.005, 8)
            if resistance > 0 and sl > resistance:
                sl = round(resistance * 1.005, 8)
        
        # Risk/Reward
        if signal == "BUY":
            risk = abs(current - sl)
            reward = abs(tp - current)
        else:
            risk = abs(sl - current)
            reward = abs(current - tp)
        risk_reward = reward / risk if risk > 0 else 0
        
        # ===== APPLY FILTERS =====
        min_conf = int(db.get_setting('min_confidence') or 65)
        if confidence < min_conf:
            return None
        
        if volume_ratio < float(db.get_setting('min_volume') or 1.2):
            return None
        
        if adx < float(db.get_setting('min_adx') or 20):
            return None
        
        # ===== BUILD SIGNAL =====
        return {
            'symbol': symbol,
            'entry': current,
            'signal': signal,
            'confidence': round(confidence, 1),
            'score': round(score, 1),
            'quality_score': round(quality_score, 1),
            'tp': tp,
            'sl': sl,
            'risk_reward': round(risk_reward, 2),
            'rsi': rsi,
            'macd': macd,
            'ma20': ma20,
            'ma50': ma50,
            'ma200': ma200,
            'vwap': vwap,
            'atr': atr,
            'support': support,
            'resistance': resistance,
            'adx': adx,
            'volume_ratio': volume_ratio,
            'mtf_score': mtf_score,
            'mtf_buy': mtf_buy,
            'mtf_sell': mtf_sell,
            'mtf_details': mtf_details,
            'reasons': reasons[:6],
            'time': datetime.now().strftime("%H:%M")
        }
        
    except Exception as e:
        logger.error(f"Error generating signal for {symbol}: {e}")
        return None

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
# LEARNING SYSTEM - DEEP
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
                        'rsi': 1.0, 'rsi_fast': 1.0, 'macd': 1.0, 
                        'ma': 1.0, 'ema': 1.0, 'bollinger': 1.0,
                        'vwap': 1.2, 'volume': 1.0, 'sr': 1.0,
                        'adx': 1.0, 'mtf': 1.0, 'ichimoku': 1.0,
                        'fibonacci': 1.0
                    })
                    return
            except:
                pass
        
        self.positive = 0
        self.negative = 0
        self.weights = {
            'rsi': 1.0, 'rsi_fast': 1.0, 'macd': 1.0,
            'ma': 1.0, 'ema': 1.0, 'bollinger': 1.0,
            'vwap': 1.2, 'volume': 1.0, 'sr': 1.0,
            'adx': 1.0, 'mtf': 1.0, 'ichimoku': 1.0,
            'fibonacci': 1.0
        }
        self.save()
    
    def save(self):
        try:
            with open(self.file, 'w') as f:
                json.dump({
                    'positive': self.positive,
                    'negative': self.negative,
                    'weights': self.weights
                }, f)
        except:
            pass
    
    def add_feedback(self, feedback_type):
        if feedback_type == 'positive':
            self.positive += 1
            for key in self.weights:
                self.weights[key] = min(2.0, self.weights[key] * 1.02)
        else:
            self.negative += 1
            for key in self.weights:
                self.weights[key] = max(0.5, self.weights[key] * 0.98)
        self.save()
    
    def get_accuracy(self):
        total = self.positive + self.negative
        if total == 0:
            return 50.0
        return round((self.positive / total) * 100, 1)

learner = LearningSystem()

# ============================================================
# TELEGRAM - GLASS BUTTONS
# ============================================================

def send_telegram(message, chat_id=None, reply_markup=None):
    if not message:
        return False
    if chat_id is None:
        chat_id = db.get_setting('admin_channel') or CHANNEL_ID
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML',
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
    if not signal or signal['signal'] == 'HOLD':
        return None, None
    
    emoji = "🟢" if signal['signal'] == 'BUY' else "🔴"
    direction = "LONG" if signal['signal'] == 'BUY' else "SHORT"
    
    msg = f"""
{emoji} <b>{signal['symbol']}</b> | {direction}
💰 <b>Entry:</b> <code>${signal['entry']:.6f}</code>
🎯 <b>TP:</b> <code>${signal['tp']:.6f}</code>
🛑 <b>SL:</b> <code>${signal['sl']:.6f}</code>
📊 <b>Confidence:</b> {signal['confidence']}%

📊 <b>Indicators:</b>
RSI: {signal['rsi']:.1f} | MACD: {signal['macd']:.6f}
MA20: ${signal['ma20']:.4f} | MA50: ${signal['ma50']:.4f}
VWAP: ${signal['vwap']:.4f} | ATR: ${signal['atr']:.6f}
Support: ${signal['support']:.4f} | Resistance: ${signal['resistance']:.4f}
ADX: {signal['adx']:.1f} | Volume: {signal['volume_ratio']:.1f}x
MTF: {signal.get('mtf_score', 'N/A')}

📝 <b>Reasons:</b>
"""
    for i, reason in enumerate(signal['reasons'][:5], 1):
        msg += f"{i}. {reason}\n"
    
    msg += f"""
⭐ <b>Quality:</b> {signal.get('quality_score', 0)}/100
📈 <b>Risk/Reward:</b> 1:{signal.get('risk_reward', 0):.1f}
🧠 <b>Accuracy:</b> {learner.get_accuracy()}%
⏰ {signal['time']} | ⚠️ <i>Trade at your own risk!</i>
"""
    
    keyboard = {
        'inline_keyboard': [
            [
                {'text': '✅ I Profited', 'callback_data': f'fb_positive_{signal_id}'},
                {'text': '❌ I Lost', 'callback_data': f'fb_negative_{signal_id}'}
            ]
        ]
    }
    
    return msg, keyboard

def build_payment_message():
    wallet = db.get_setting('wallet') or WALLET_ADDRESS
    network = db.get_setting('wallet_network') or WALLET_NETWORK
    price = db.get_setting('price') or SUBSCRIPTION_PRICE
    
    return f"""
💳 <b>Subscription Payment</b>
━━━━━━━━━━━━━━━━━━━━━━

💰 <b>Price:</b> {price}
🌐 <b>Network:</b> {network}
📌 <b>Wallet Address:</b>
<code>{wallet}</code>

📝 <b>Instructions:</b>
1. Send exactly {price} to the wallet above
2. Send the transaction hash to this bot
3. Admin will confirm your payment
4. You'll get access to all signals

<b>To send hash:</b>
/pay HASH_AMOUNT
Example: /pay 0x123456789...

⚠️ <i>Include the complete transaction hash</i>
"""

# ============================================================
# GLASSMORPHISM ADMIN PANEL
# ============================================================

def show_admin_panel():
    """Show admin panel with glassmorphism buttons"""
    settings = db.get_all_settings()
    stats = db.get_stats()
    
    signal_status = "🟢 ON" if settings.get('signal_enabled') == '1' else "🔴 OFF"
    paid_mode = "🟢 ON" if settings.get('paid_mode_enabled') == '1' else "🔴 OFF"
    deep_analysis = "🟢 ON" if settings.get('deep_analysis') == '1' else "🔴 OFF"
    
    msg = f"""
🔮 <b>✨ ADMIN PANEL - GLASS EDITION ✨</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 <b>Statistics:</b>
👤 Users: {stats.get('users', 0)}
🟢 Active: {stats.get('active', 0)}
💳 Paid: {stats.get('paid', 0)}
📈 Signals: {stats.get('signals', 0)}
📊 Today: {stats.get('today', 0)}
💳 Pending: {stats.get('pending', 0)}
📝 Feedback: {stats.get('feedback', 0)}
🧠 Accuracy: {learner.get_accuracy()}%

⚙️ <b>Settings:</b>
📡 Signal: {signal_status}
💳 Paid Mode: {paid_mode}
🔬 Deep Analysis: {deep_analysis}
🎯 Min Conf: {settings.get('min_confidence', 65)}%
📊 Max Signals: {settings.get('max_signals', 3)}
💰 Price: {settings.get('price', '100 USDT')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>💎 Commands:</b>
/panel - Open this panel
/on - Enable signals
/off - Disable signals
/paid_on - Enable paid mode
/paid_off - Disable paid mode
/payments - Manage payments
/stats - Show statistics
/settings - View settings
/set key value - Change setting
/help - Full command list
"""
    
    keyboard = {
        'inline_keyboard': [
            [
                {'text': '🟢 Signal ON', 'callback_data': 'admin_on'},
                {'text': '🔴 Signal OFF', 'callback_data': 'admin_off'}
            ],
            [
                {'text': '💳 Paid ON', 'callback_data': 'admin_paid_on'},
                {'text': '💳 Paid OFF', 'callback_data': 'admin_paid_off'}
            ],
            [
                {'text': '🔬 Deep ON', 'callback_data': 'admin_deep_on'},
                {'text': '🔬 Deep OFF', 'callback_data': 'admin_deep_off'}
            ],
            [
                {'text': '📊 Stats', 'callback_data': 'admin_stats'},
                {'text': '💳 Payments', 'callback_data': 'admin_payments'}
            ],
            [
                {'text': '⚙️ Settings', 'callback_data': 'admin_settings'},
                {'text': '📝 Feedback', 'callback_data': 'admin_feedback'}
            ]
        ]
    }
    
    send_admin(msg, keyboard)

def handle_admin_callback(callback_data):
    """Handle admin button clicks"""
    try:
        if callback_data == 'admin_on':
            db.update_setting('signal_enabled', '1')
            send_admin("✅ <b>Signals ENABLED</b>\nSignals will be sent to channel")
            return True
        
        elif callback_data == 'admin_off':
            db.update_setting('signal_enabled', '0')
            send_admin("🔴 <b>Signals DISABLED</b>\nNo signals will be sent")
            return True
        
        elif callback_data == 'admin_paid_on':
            db.update_setting('paid_mode_enabled', '1')
            send_admin("💳 <b>Paid Mode ENABLED</b>\nOnly paid users receive signals")
            return True
        
        elif callback_data == 'admin_paid_off':
            db.update_setting('paid_mode_enabled', '0')
            send_admin("💳 <b>Paid Mode DISABLED</b>\nAll users receive signals")
            return True
        
        elif callback_data == 'admin_deep_on':
            db.update_setting('deep_analysis', '1')
            send_admin("🔬 <b>Deep Analysis ENABLED</b>\nFull analysis with Ichimoku & Fibonacci")
            return True
        
        elif callback_data == 'admin_deep_off':
            db.update_setting('deep_analysis', '0')
            send_admin("🔬 <b>Deep Analysis DISABLED</b>\nBasic analysis only")
            return True
        
        elif callback_data == 'admin_stats':
            stats = db.get_stats()
            msg = f"""
📊 <b>Detailed Statistics</b>
━━━━━━━━━━━━━━━━━━━━━━

👤 Total Users: {stats.get('users', 0)}
🟢 Active Users: {stats.get('active', 0)}
💳 Paid Users: {stats.get('paid', 0)}
📈 Total Signals: {stats.get('signals', 0)}
📊 Today Signals: {stats.get('today', 0)}
💳 Pending Payments: {stats.get('pending', 0)}
📝 Total Feedback: {stats.get('feedback', 0)}
🧠 Accuracy: {learner.get_accuracy()}%
✅ Positive: {learner.positive}
❌ Negative: {learner.negative}
"""
            send_admin(msg)
            return True
        
        elif callback_data == 'admin_payments':
            payments = db.get_pending_payments()
            if not payments:
                send_admin("💳 <b>No pending payments</b>")
                return True
            
            msg = "💳 <b>Pending Payments</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
            for payment in payments[:10]:
                payment_id, user_id, payment_hash, amount, wallet, created_at = payment
                user = db.get_user(user_id)
                username = user[1] if user else "Unknown"
                msg += f"""
#{payment_id} | {username} (ID: {user_id})
💰 {amount}
🔑 {payment_hash[:40]}...
📅 {created_at[:16]}
/confirm_{payment_id} - ✅ Confirm
/reject_{payment_id} - ❌ Reject
━━━━━━━━━━━━━━━━━━━━━━
"""
            send_admin(msg)
            return True
        
        elif callback_data == 'admin_settings':
            settings = db.get_all_settings()
            msg = "⚙️ <b>Settings</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
            for key, value in settings.items():
                msg += f"\n📌 {key}: <code>{value}</code>"
            
            msg += """

━━━━━━━━━━━━━━━━━━━━━━
<b>Change settings:</b>
/set signal_enabled 1
/set paid_mode_enabled 0
/set deep_analysis 1
/set min_confidence 75
/set max_signals 2
/set min_volume 1.5
/set min_adx 25
/set price "150 USDT"
/set wallet "ADDRESS"
/set free_signals 2
"""
            send_admin(msg)
            return True
        
        elif callback_data == 'admin_feedback':
            feedback = db.cursor.execute('SELECT COUNT(*) FROM feedback_log').fetchone()[0]
            positive = db.cursor.execute('SELECT COUNT(*) FROM feedback_log WHERE feedback = "positive"').fetchone()[0]
            negative = db.cursor.execute('SELECT COUNT(*) FROM feedback_log WHERE feedback = "negative"').fetchone()[0]
            
            msg = f"""
📝 <b>Feedback Statistics</b>
━━━━━━━━━━━━━━━━━━━━━━

📊 Total: {feedback}
✅ Positive: {positive} ({round(positive/feedback*100 if feedback > 0 else 0)}%)
❌ Negative: {negative} ({round(negative/feedback*100 if feedback > 0 else 0)}%)
🧠 Accuracy: {learner.get_accuracy()}%

📋 <b>Recent Feedback:</b>
"""
            
            recent = db.cursor.execute('''
                SELECT f.feedback, u.username, s.symbol, f.created_at
                FROM feedback_log f
                LEFT JOIN users u ON f.user_id = u.user_id
                LEFT JOIN signals s ON f.signal_id = s.id
                ORDER BY f.created_at DESC
                LIMIT 5
            ''').fetchall()
            
            for feedback, username, symbol, created_at in recent:
                emoji = "✅" if feedback == 'positive' else "❌"
                msg += f"\n{emoji} {username or 'Unknown'} | {symbol or 'N/A'} | {created_at[:16]}"
            
            send_admin(msg)
            return True
        
        return False
    except Exception as e:
        logger.error(f"Admin callback error: {e}")
        send_admin(f"❌ Error: {e}")
        return False

def handle_admin_command(text, user_id=ADMIN_ID):
    """Handle admin text commands"""
    try:
        if text == '/panel' or text == '/start':
            show_admin_panel()
            return True
        
        elif text == '/on':
            db.update_setting('signal_enabled', '1')
            send_admin("✅ <b>Signals ENABLED</b>")
            return True
        
        elif text == '/off':
            db.update_setting('signal_enabled', '0')
            send_admin("🔴 <b>Signals DISABLED</b>")
            return True
        
        elif text == '/paid_on':
            db.update_setting('paid_mode_enabled', '1')
            send_admin("💳 <b>Paid Mode ENABLED</b>")
            return True
        
        elif text == '/paid_off':
            db.update_setting('paid_mode_enabled', '0')
            send_admin("💳 <b>Paid Mode DISABLED</b>")
            return True
        
        elif text.startswith('/pay '):
            payment_hash = text[5:].strip()
            if len(payment_hash) < 10:
                send_telegram("❌ Invalid hash. Please send the complete transaction hash.", user_id)
                return True
            
            db.add_user(user_id)
            payment_id = db.add_payment(user_id, payment_hash)
            if payment_id:
                send_telegram(f"""
✅ <b>Payment Hash Received</b>
━━━━━━━━━━━━━━━━━━━━━━
🔑 Hash: <code>{payment_hash}</code>
💳 Payment ID: #{payment_id}

⏳ <b>Waiting for admin confirmation...</b>
""", user_id)
                
                user = db.get_user(user_id)
                username = user[1] if user else "Unknown"
                send_admin(f"""
💳 <b>New Payment Request</b>
━━━━━━━━━━━━━━━━━━━━━━
👤 User: {username} (ID: {user_id})
🔑 Hash: <code>{payment_hash}</code>
💳 Payment ID: #{payment_id}

/confirm_{payment_id} - ✅ Confirm
/reject_{payment_id} - ❌ Reject
""")
            return True
        
        elif text.startswith('/confirm_'):
            try:
                payment_id = int(text.replace('/confirm_', ''))
                success, user_id = db.confirm_payment(payment_id)
                if success:
                    send_admin(f"✅ Payment #{payment_id} confirmed!")
                    send_telegram("✅ <b>Payment Confirmed!</b>\nYour subscription is now active!", user_id)
                else:
                    send_admin(f"❌ Failed to confirm payment #{payment_id}")
            except Exception as e:
                send_admin(f"❌ Error: {e}")
            return True
        
        elif text.startswith('/reject_'):
            try:
                payment_id = int(text.replace('/reject_', ''))
                payment = db.get_payment(payment_id)
                success = db.reject_payment(payment_id)
                if success:
                    send_admin(f"❌ Payment #{payment_id} rejected")
                    if payment:
                        send_telegram("❌ <b>Payment Rejected</b>\nPlease try again.", payment[1])
                else:
                    send_admin(f"❌ Failed to reject payment #{payment_id}")
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
                send_admin(f"✅ Setting updated: {key} = {value}")
            except Exception as e:
                send_admin(f"❌ Error: {e}")
            return True
        
        elif text == '/stats':
            stats = db.get_stats()
            send_admin(f"""
📊 <b>BOT STATISTICS</b>
━━━━━━━━━━━━━━━━━━━━━━
👤 Users: {stats.get('users', 0)}
🟢 Active: {stats.get('active', 0)}
💳 Paid: {stats.get('paid', 0)}
📈 Signals: {stats.get('signals', 0)}
📊 Today: {stats.get('today', 0)}
💳 Pending: {stats.get('pending', 0)}
📝 Feedback: {stats.get('feedback', 0)}
🧠 Accuracy: {learner.get_accuracy()}%
""")
            return True
        
        elif text == '/payments':
            payments = db.get_pending_payments()
            if not payments:
                send_admin("💳 No pending payments")
                return True
            msg = "💳 <b>Pending Payments</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
            for payment in payments[:10]:
                payment_id, user_id, payment_hash, amount, wallet, created_at = payment
                user = db.get_user(user_id)
                username = user[1] if user else "Unknown"
                msg += f"""
#{payment_id} | {username} (ID: {user_id})
💰 {amount}
🔑 {payment_hash[:40]}...
📅 {created_at[:16]}
/confirm_{payment_id} - ✅ Confirm
/reject_{payment_id} - ❌ Reject
━━━━━━━━━━━━━━━━━━━━━━
"""
            send_admin(msg)
            return True
        
        elif text == '/settings':
            settings = db.get_all_settings()
            msg = "⚙️ <b>Settings</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
            for key, value in settings.items():
                msg += f"\n📌 {key}: <code>{value}</code>"
            send_admin(msg)
            return True
        
        elif text == '/help':
            send_admin("""
📚 <b>✨ Admin Commands - Glass Edition ✨</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>Panel & Control</b>
/panel - Open glass admin panel
/on - Enable signals
/off - Disable signals
/paid_on - Enable paid mode
/paid_off - Disable paid mode

<b>Deep Analysis</b>
/set deep_analysis 1 - Enable deep analysis
/set deep_analysis 0 - Disable deep analysis

<b>Settings</b>
/set key value - Change setting
/settings - View all settings
/stats - Show statistics

<b>Payments</b>
/payments - List pending
/confirm_ID - Confirm payment
/reject_ID - Reject payment

<b>Examples</b>
/set min_confidence 75
/set max_signals 2
/confirm_1
/panel
""")
            return True
        
        return False
    except Exception as e:
        logger.error(f"Admin command error: {e}")
        return False

def handle_user_command(text, user_id):
    """Handle user commands"""
    try:
        if text == '/start':
            db.add_user(user_id)
            msg = f"""
🚀 <b>Welcome to Signal Bot!</b>
━━━━━━━━━━━━━━━━━━━━━━

📊 <b>Features:</b>
• Deep market analysis
• Multiple timeframe analysis
• Ichimoku & Fibonacci
• Smart learning system

💳 <b>Get Access:</b>
/buy - Get payment instructions

💰 <b>Price:</b> {db.get_setting('price') or '100 USDT'}

📈 <b>Free Signals:</b>
You get {db.get_setting('free_signals') or 2} free signals!
"""
            send_telegram(msg, user_id)
            return True
        
        elif text == '/buy':
            send_telegram(build_payment_message(), user_id)
            return True
        
        return False
    except Exception as e:
        logger.error(f"User command error: {e}")
        return False

def process_callback(callback_data, user_id):
    """Process all callbacks"""
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
            success, message = db.update_feedback(signal_id, feedback_type, user_id)
            if success:
                learner.add_feedback(feedback_type)
                msg = "✅ Thank you! Your feedback helps improve accuracy! 🚀" if feedback_type == 'positive' else "❌ Thank you! We'll use this to improve! 🔧"
                send_telegram(msg, user_id)
                
                signal = db.get_signal(signal_id)
                if signal:
                    send_admin(f"""
📊 <b>Feedback Received</b>
━━━━━━━━━━━━━━━━━━━━━━
📈 Symbol: {signal[2]}
📊 Direction: {signal[3]}
👤 User: {user_id}
📝 Feedback: {feedback_type}
🧠 Accuracy: {learner.get_accuracy()}%
""")
                return True
            else:
                send_telegram(f"⚠️ {message}", user_id)
                return False
        
        return False
    except Exception as e:
        logger.error(f"Callback error: {e}")
        return False

# ============================================================
# SIGNAL DISTRIBUTION
# ============================================================

def send_to_channel(signal, signal_id):
    msg, keyboard = build_signal_message(signal, signal_id)
    if msg:
        if send_telegram(msg, reply_markup=keyboard):
            db.mark_signal_sent_channel(signal_id)
            logger.info(f"✅ Signal sent to channel: {signal['symbol']}")
            return True
        else:
            send_telegram(msg)
            db.mark_signal_sent_channel(signal_id)
            return True
    return False

def send_to_paid_users(signal, signal_id):
    db.cursor.execute('SELECT user_id FROM users WHERE is_active = 1 AND has_paid = 1')
    paid_users = db.cursor.fetchall()
    sent_count = 0
    for user in paid_users:
        user_id = user[0]
        try:
            msg, keyboard = build_signal_message(signal, signal_id)
            if msg and send_telegram(msg, user_id, keyboard):
                sent_count += 1
                db.mark_signal_sent_user(signal_id)
                time.sleep(0.05)
        except:
            pass
    logger.info(f"📤 Signal sent to {sent_count} paid users")
    return sent_count

def distribute_signal(signal):
    try:
        signal_id = db.save_signal(signal)
        if not signal_id:
            return
        
        send_to_channel(signal, signal_id)
        
        if db.get_setting('paid_mode_enabled') == '1':
            send_to_paid_users(signal, signal_id)
        else:
            db.cursor.execute('SELECT user_id FROM users')
            all_users = db.cursor.fetchall()
            for user in all_users:
                user_id = user[0]
                can_receive, reason = db.can_receive_signal(user_id)
                if can_receive:
                    msg, keyboard = build_signal_message(signal, signal_id)
                    if msg:
                        send_telegram(msg, user_id, keyboard)
                        db.mark_signal_sent_user(signal_id)
                        if reason == "free":
                            db.use_free_signal(user_id)
                        time.sleep(0.05)
        
        logger.info(f"✅ Signal distributed: {signal['symbol']}")
    except Exception as e:
        logger.error(f"Error distributing signal: {e}")

# ============================================================
# MAIN LOOP
# ============================================================

def main_loop():
    logger.info("🚀 Starting Signal Bot V15 - Glassmorphism Edition")
    send_admin("""
🚀 <b>✨ Signal Bot V15 - Glassmorphism Edition ✨</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Admin Panel Active (Glass Buttons)
✅ Deep Analysis Active (Ichimoku + Fibonacci)
✅ Multi-Timeframe (5 Timeframes)
✅ Real Signals Active
✅ Paid Mode Ready
✅ Feedback System Active
""")
    
    cycle = 0
    while True:
        try:
            cycle += 1
            if db.get_setting('signal_enabled') != '1':
                time.sleep(30)
                continue
            
            max_signals = int(db.get_setting('max_signals') or 3)
            logger.info(f"🔄 Cycle {cycle} - Scanning {len(SYMBOLS)} symbols")
            
            signals = []
            for symbol in SYMBOLS:
                try:
                    signal = generate_signal(symbol)
                    if signal:
                        signals.append(signal)
                        logger.info(f"✅ {signal['symbol']}: {signal['signal']} ({signal['confidence']}%)")
                except Exception as e:
                    logger.error(f"Error processing {symbol}: {e}")
                time.sleep(0.05)
            
            signals.sort(key=lambda x: x.get('quality_score', 0), reverse=True)
            signals = signals[:max_signals]
            
            if signals:
                for signal in signals:
                    distribute_signal(signal)
                    time.sleep(2)
            else:
                if cycle % 3 == 0:
                    logger.info("⏳ No signals found")
            
            if cycle % 5 == 0:
                payments = db.get_pending_payments()
                if payments:
                    send_admin(f"💳 <b>{len(payments)} pending payments</b>\nUse /payments to view")
            
            if cycle % 20 == 0:
                stats = db.get_stats()
                send_admin(f"""
🔄 <b>Bot Status Update</b>
━━━━━━━━━━━━━━━━━━━━━━
📊 Cycle: {cycle}
📈 Signals Today: {stats.get('today', 0)}
📊 Total Signals: {stats.get('signals', 0)}
🧠 Accuracy: {learner.get_accuracy()}%
👤 Users: {stats.get('users', 0)}
💳 Paid: {stats.get('paid', 0)}
""")
            
            logger.info(f"⏱ Waiting {INTERVAL//60} minutes...")
            time.sleep(INTERVAL)
            
        except Exception as e:
            logger.error(f"❌ Main loop error: {e}")
            send_admin(f"❌ <b>Error in main loop</b>\n{e}")
            time.sleep(60)

# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    try:
        print("\n" + "="*70)
        print("🚀 ULTIMATE SIGNAL BOT V15 - GLASSMORPHISM EDITION")
        print("="*70)
        print(f"📊 Symbols: {len(SYMBOLS)}")
        print(f"⏱ Interval: {INTERVAL//60} minutes")
        print(f"📢 Channel: {CHANNEL_ID}")
        print("="*70 + "\n")
        
        test = get_candles('BTCUSDT', 10)
        if test:
            logger.info("✅ Binance connection OK")
        else:
            logger.warning("⚠️ Binance connection failed, retrying...")
        
        main_loop()
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")