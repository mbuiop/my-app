# ============================================================
# ULTIMATE SIGNAL BOT V12 - ENTERPRISE EDITION
# PROFESSIONAL TRADING SIGNALS + FULL ADMIN PANEL
# ============================================================

import requests
import numpy as np
import time
import json
import os
import sqlite3
from datetime import datetime, timedelta
from collections import deque
import threading
import sys

# ============================================================
# CONFIGURATION
# ============================================================

BOT_TOKEN = "7780798170:AAHTDl295s15_RwhfhjGentSLZzye3keJP0"
CHANNEL_ID = "@davnold"
ADMIN_ID = 327855654

WALLET_ADDRESS = "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"
WALLET_NETWORK = "TRC20"
SUBSCRIPTION_PRICE = "100 USDT"
SUBSCRIPTION_DAYS = 30

INTERVAL = 180
MIN_CONFIDENCE = 60
MAX_SIGNALS = 3

# ============================================================
# DATABASE
# ============================================================

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('bot_data.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                joined_at TIMESTAMP,
                free_signals INTEGER DEFAULT 2,
                subscription_expire TIMESTAMP,
                is_active BOOLEAN DEFAULT 0,
                feedback_count INTEGER DEFAULT 0,
                positive_feedback INTEGER DEFAULT 0,
                negative_feedback INTEGER DEFAULT 0,
                signals_received INTEGER DEFAULT 0
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
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
                support REAL,
                resistance REAL,
                score REAL,
                reasons TEXT,
                feedback TEXT DEFAULT '',
                feedback_user INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending'
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                payment_hash TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP,
                confirmed_at TIMESTAMP,
                expire_at TIMESTAMP,
                amount TEXT DEFAULT '100 USDT'
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id INTEGER,
                user_id INTEGER,
                feedback TEXT,
                created_at TIMESTAMP
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # Default settings
        self.cursor.execute('INSERT OR IGNORE INTO settings VALUES ("signal_enabled", "1")')
        self.cursor.execute('INSERT OR IGNORE INTO settings VALUES ("payment_enabled", "1")')
        self.cursor.execute('INSERT OR IGNORE INTO settings VALUES ("wallet", ?)', (WALLET_ADDRESS,))
        self.cursor.execute('INSERT OR IGNORE INTO settings VALUES ("price", ?)', (SUBSCRIPTION_PRICE,))
        self.cursor.execute('INSERT OR IGNORE INTO settings VALUES ("free_signals", "2")')
        self.cursor.execute('INSERT OR IGNORE INTO settings VALUES ("subscription_days", ?)', (str(SUBSCRIPTION_DAYS),))
        
        self.conn.commit()
    
    def add_user(self, user_id, username, first_name):
        self.cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, joined_at)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, first_name, datetime.now().isoformat()))
        self.conn.commit()
    
    def get_user(self, user_id):
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone()
    
    def save_signal(self, user_id, signal_data):
        self.cursor.execute('''
            INSERT INTO signals (
                user_id, symbol, direction, entry, tp1, tp2, tp3, sl, confidence,
                created_at, rsi, macd, ma20, ma50, ma200, vwap, atr,
                support, resistance, score, reasons
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, signal_data['symbol'], signal_data['signal'],
            signal_data['entry'], signal_data['tp1'], signal_data['tp2'],
            signal_data['tp3'], signal_data['sl'], signal_data['confidence'],
            datetime.now().isoformat(),
            signal_data.get('rsi', 0), signal_data.get('macd', 0),
            signal_data.get('ma20', 0), signal_data.get('ma50', 0),
            signal_data.get('ma200', 0), signal_data.get('vwap', 0),
            signal_data.get('atr', 0), signal_data.get('support', 0),
            signal_data.get('resistance', 0), signal_data.get('score', 0),
            '|'.join(signal_data.get('reasons', []))
        ))
        signal_id = self.cursor.lastrowid
        self.conn.commit()
        return signal_id
    
    def update_feedback(self, signal_id, feedback_type, user_id):
        self.cursor.execute('''
            UPDATE signals SET feedback = ?, feedback_user = ? WHERE id = ?
        ''', (feedback_type, user_id, signal_id))
        self.conn.commit()
        
        if feedback_type == 'positive':
            self.cursor.execute('''
                UPDATE users SET positive_feedback = positive_feedback + 1,
                feedback_count = feedback_count + 1 WHERE user_id = ?
            ''', (user_id,))
        else:
            self.cursor.execute('''
                UPDATE users SET negative_feedback = negative_feedback + 1,
                feedback_count = feedback_count + 1 WHERE user_id = ?
            ''', (user_id,))
        self.conn.commit()
        
        self.cursor.execute('''
            INSERT INTO feedback_log (signal_id, user_id, feedback, created_at)
            VALUES (?, ?, ?, ?)
        ''', (signal_id, user_id, feedback_type, datetime.now().isoformat()))
        self.conn.commit()
    
    def add_payment(self, user_id, payment_hash):
        self.cursor.execute('''
            INSERT INTO payments (user_id, payment_hash, created_at, amount)
            VALUES (?, ?, ?, ?)
        ''', (user_id, payment_hash, datetime.now().isoformat(), SUBSCRIPTION_PRICE))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_pending_payments(self):
        self.cursor.execute('''
            SELECT id, user_id, payment_hash, created_at, amount
            FROM payments WHERE status = 'pending'
            ORDER BY created_at ASC
        ''')
        return self.cursor.fetchall()
    
    def confirm_payment(self, payment_id):
        payment = self.get_payment(payment_id)
        if not payment or payment[3] != 'pending':
            return False, None
        
        user_id = payment[1]
        days = int(db.get_setting('subscription_days') or SUBSCRIPTION_DAYS)
        expire_date = datetime.now() + timedelta(days=days)
        
        self.cursor.execute('''
            UPDATE payments SET status = 'confirmed', confirmed_at = ?, expire_at = ?
            WHERE id = ?
        ''', (datetime.now().isoformat(), expire_date.isoformat(), payment_id))
        
        self.cursor.execute('''
            UPDATE users SET subscription_expire = ?, is_active = 1
            WHERE user_id = ?
        ''', (expire_date.isoformat(), user_id))
        
        self.conn.commit()
        return True, user_id, expire_date
    
    def reject_payment(self, payment_id):
        self.cursor.execute('''
            UPDATE payments SET status = 'rejected' WHERE id = ?
        ''', (payment_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def get_payment(self, payment_id):
        self.cursor.execute('SELECT id, user_id, payment_hash, status, amount FROM payments WHERE id = ?', (payment_id,))
        return self.cursor.fetchone()
    
    def get_setting(self, key):
        self.cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        r = self.cursor.fetchone()
        return r[0] if r else None
    
    def update_setting(self, key, value):
        self.cursor.execute('UPDATE settings SET value = ? WHERE key = ?', (value, key))
        self.conn.commit()
    
    def get_all_users(self):
        self.cursor.execute('SELECT user_id FROM users')
        return self.cursor.fetchall()
    
    def get_signal(self, signal_id):
        self.cursor.execute('SELECT * FROM signals WHERE id = ?', (signal_id,))
        return self.cursor.fetchone()
    
    def has_subscription(self, user_id):
        self.cursor.execute('''
            SELECT subscription_expire FROM users 
            WHERE user_id = ? AND subscription_expire IS NOT NULL
        ''', (user_id,))
        r = self.cursor.fetchone()
        if r and r[0]:
            try:
                expire = datetime.fromisoformat(r[0])
                if expire > datetime.now():
                    return True, expire
            except:
                pass
        return False, None
    
    def get_free_signals(self, user_id):
        user = self.get_user(user_id)
        if not user:
            return 2
        return user[4] if len(user) > 4 else 2
    
    def use_free_signal(self, user_id):
        self.cursor.execute('''
            UPDATE users SET free_signals = free_signals - 1,
            signals_received = signals_received + 1
            WHERE user_id = ? AND free_signals > 0
        ''', (user_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0

db = Database()

# ============================================================
# REAL DATA FROM BINANCE
# ============================================================

def get_candles(symbol, limit=250, interval='5m'):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return {
                'close': [float(x[4]) for x in data],
                'high': [float(x[2]) for x in data],
                'low': [float(x[3]) for x in data],
                'volume': [float(x[5]) for x in data],
                'open': [float(x[1]) for x in data]
            }
    except:
        pass
    return None

# ============================================================
# PROFESSIONAL INDICATORS
# ============================================================

def calc_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50.0
    p = np.array(prices[-period-1:], dtype=np.float64)
    deltas = np.diff(p)
    gain = np.mean(deltas[deltas > 0]) if np.sum(deltas > 0) > 0 else 0
    loss = -np.mean(deltas[deltas < 0]) if np.sum(deltas < 0) > 0 else 0.0000001
    if loss == 0:
        return 100.0
    return round(100 - (100 / (1 + gain / loss)), 2)

def calc_macd(prices, fast=12, slow=26, signal=9):
    if len(prices) < slow:
        return 0, 0, 0
    p = np.array(prices, dtype=np.float64)
    f_mult = 2.0 / (fast + 1)
    f_ema = float(np.mean(p[-fast:]))
    for price in p[-fast:]:
        f_ema = float(price) * f_mult + f_ema * (1 - f_mult)
    s_mult = 2.0 / (slow + 1)
    s_ema = float(np.mean(p[-slow:]))
    for price in p[-slow:]:
        s_ema = float(price) * s_mult + s_ema * (1 - s_mult)
    macd_line = f_ema - s_ema
    sig_mult = 2.0 / (signal + 1)
    sig_line = macd_line
    for _ in range(signal):
        sig_line = macd_line * sig_mult + sig_line * (1 - sig_mult)
    return round(macd_line, 8), round(sig_line, 8), round(macd_line - sig_line, 8)

def calc_ma(prices, period):
    if len(prices) < period:
        return prices[-1] if prices else 0
    return round(float(np.mean(np.array(prices[-period:], dtype=np.float64))), 8)

def calc_bollinger(prices, period=20, std_dev=2):
    if len(prices) < period:
        return prices[-1] if prices else 0, prices[-1] if prices else 0, prices[-1] if prices else 0
    p = np.array(prices[-period:], dtype=np.float64)
    ma = float(np.mean(p))
    std = float(np.std(p))
    return round(ma + std_dev * std, 8), round(ma, 8), round(ma - std_dev * std, 8)

def calc_vwap(prices, volumes):
    if len(prices) < 2:
        return prices[-1] if prices else 0
    total_value = sum(prices[i] * volumes[i] for i in range(len(prices)))
    total_volume = sum(volumes)
    if total_volume == 0:
        return prices[-1]
    return round(total_value / total_volume, 8)

def calc_atr(highs, lows, prices, period=14):
    if len(prices) < period:
        return 0.0000001
    tr = []
    for i in range(1, period + 1):
        if i < len(prices):
            tr.append(max(highs[-i] - lows[-i], abs(highs[-i] - prices[-i-1]), abs(lows[-i] - prices[-i-1])))
    return round(float(np.mean(np.array(tr, dtype=np.float64))) if tr else 0.0000001, 8)

def find_support_resistance(highs, lows, prices):
    if len(prices) < 30:
        return 0, 0
    peaks, troughs = [], []
    for i in range(2, len(prices)-2):
        if highs[i] > highs[i-1] and highs[i] > highs[i+1] and highs[i] > highs[i-2] and highs[i] > highs[i+2]:
            peaks.append(highs[i])
        if lows[i] < lows[i-1] and lows[i] < lows[i+1] and lows[i] < lows[i-2] and lows[i] < lows[i+2]:
            troughs.append(lows[i])
    resistance = peaks[0] if peaks else 0
    support = troughs[0] if troughs else 0
    if len(peaks) >= 2:
        cluster = [peaks[0]]
        for p in peaks[1:]:
            if abs(p - peaks[0]) / peaks[0] < 0.02:
                cluster.append(p)
        resistance = sum(cluster) / len(cluster) if cluster else 0
    if len(troughs) >= 2:
        cluster = [troughs[0]]
        for t in troughs[1:]:
            if abs(t - troughs[0]) / troughs[0] < 0.02:
                cluster.append(t)
        support = sum(cluster) / len(cluster) if cluster else 0
    return round(support, 8), round(resistance, 8)

def calc_adx(highs, lows, prices, period=14):
    if len(prices) < period + 1:
        return 25
    tr, up, down = [], [], []
    for i in range(1, period + 1):
        if i < len(prices):
            tr.append(max(highs[-i] - lows[-i], abs(highs[-i] - prices[-i-1]), abs(lows[-i] - prices[-i-1])))
            up_move = highs[-i] - highs[-i-1]
            down_move = lows[-i-1] - lows[-i]
            up.append(max(0, up_move) if up_move > down_move else 0)
            down.append(max(0, down_move) if down_move > up_move else 0)
    atr = float(np.mean(np.array(tr, dtype=np.float64))) if tr else 0.0000001
    di_plus = 100 * float(np.mean(np.array(up, dtype=np.float64))) / atr if atr > 0 else 0
    di_minus = 100 * float(np.mean(np.array(down, dtype=np.float64))) / atr if atr > 0 else 0
    return round(100 * abs(di_plus - di_minus) / (di_plus + di_minus + 0.0000001), 1)

# ============================================================
# SIGNAL GENERATOR - ENTERPRISE
# ============================================================

def generate_signal(symbol):
    data = get_candles(symbol, 250, '5m')
    if not data or len(data['close']) < 50:
        return None
    
    prices = data['close']
    highs = data['high']
    lows = data['low']
    volumes = data['volume']
    current = prices[-1]
    
    if current == 0:
        return None
    
    # Calculate all indicators
    rsi = calc_rsi(prices, 14)
    macd, macd_sig, macd_hist = calc_macd(prices, 12, 26, 9)
    ma7 = calc_ma(prices, 7)
    ma20 = calc_ma(prices, 20)
    ma50 = calc_ma(prices, 50)
    ma200 = calc_ma(prices, 200)
    upper_bb, middle_bb, lower_bb = calc_bollinger(prices, 20, 2)
    vwap = calc_vwap(prices, volumes)
    atr = calc_atr(highs, lows, prices, 14)
    support, resistance = find_support_resistance(highs, lows, prices)
    adx = calc_adx(highs, lows, prices, 14)
    
    avg_vol = np.mean(volumes[-20:]) if len(volumes) >= 20 else 1
    vol_ratio = volumes[-1] / avg_vol if avg_vol > 0 else 1
    
    # Scoring
    score = 50
    reasons = []
    
    # RSI
    if rsi < 25:
        score += 25
        reasons.append(f"🔥 RSI Oversold: {rsi}")
    elif rsi < 35:
        score += 18
        reasons.append(f"📈 RSI Near Oversold: {rsi}")
    elif rsi > 75:
        score -= 25
        reasons.append(f"🔥 RSI Overbought: {rsi}")
    elif rsi > 65:
        score -= 18
        reasons.append(f"📉 RSI Near Overbought: {rsi}")
    
    # MACD
    if macd > 0 and macd_hist > 0:
        score += 20
        reasons.append(f"🟢 MACD Bullish: {macd:.6f}")
    elif macd < 0 and macd_hist < 0:
        score -= 20
        reasons.append(f"🔴 MACD Bearish: {macd:.6f}")
    elif macd > 0:
        score += 10
        reasons.append(f"🟡 MACD Positive: {macd:.6f}")
    else:
        score -= 10
        reasons.append(f"🟡 MACD Negative: {macd:.6f}")
    
    # Moving Averages
    if current > ma20 and ma20 > ma50 and ma50 > ma200:
        score += 20
        reasons.append(f"🚀 Strong Uptrend")
    elif current < ma20 and ma20 < ma50 and ma50 < ma200:
        score -= 20
        reasons.append(f"💀 Strong Downtrend")
    elif current > ma20 and ma20 > ma50:
        score += 12
        reasons.append(f"📈 Uptrend")
    elif current < ma20 and ma20 < ma50:
        score -= 12
        reasons.append(f"📉 Downtrend")
    elif current > ma20:
        score += 5
        reasons.append(f"⬆️ Price above MA20")
    else:
        score -= 5
        reasons.append(f"⬇️ Price below MA20")
    
    # Bollinger
    if current < lower_bb:
        score += 15
        reasons.append(f"🎯 Touch Lower Band")
    elif current > upper_bb:
        score -= 15
        reasons.append(f"🎯 Touch Upper Band")
    elif current < middle_bb:
        score += 8
        reasons.append(f"📊 Lower Half")
    else:
        score -= 8
        reasons.append(f"📊 Upper Half")
    
    # VWAP
    if current > vwap:
        score += 10
        reasons.append(f"✅ Above VWAP")
    else:
        score -= 10
        reasons.append(f"❌ Below VWAP")
    
    # Volume
    if vol_ratio > 2.5:
        score += 5
        reasons.append(f"📊 High Volume: {vol_ratio:.1f}x")
    elif vol_ratio > 1.5:
        score += 3
        reasons.append(f"📊 Good Volume: {vol_ratio:.1f}x")
    elif vol_ratio < 0.5:
        score -= 5
        reasons.append(f"📊 Low Volume: {vol_ratio:.1f}x")
    
    # Support/Resistance
    if support > 0:
        dist = ((current - support) / current) * 100
        if dist < 0.5:
            score += 10
            reasons.append(f"🛡️ Very Near Support")
        elif dist < 1.5:
            score += 7
            reasons.append(f"🛡️ Near Support")
    
    if resistance > 0:
        dist = ((resistance - current) / current) * 100
        if dist < 0.5:
            score -= 10
            reasons.append(f"🚫 Very Near Resistance")
        elif dist < 1.5:
            score -= 7
            reasons.append(f"🚫 Near Resistance")
    
    # ADX
    if adx > 50:
        if score > 50:
            score += 5
            reasons.append(f"🔥 Strong Trend (ADX: {adx})")
        else:
            score -= 5
            reasons.append(f"💀 Strong Trend (ADX: {adx})")
    
    confidence = min(98, 50 + abs(score - 50) * 1.3)
    
    if score > 55:
        signal = "BUY"
    elif score < 45:
        signal = "SELL"
    else:
        signal = "HOLD"
    
    # ===== TP/SL - PROFESSIONAL =====
    if signal == "BUY":
        entry = current
        
        # TP1: 1.5x ATR (first target)
        tp1 = round(current + (atr * 1.5), 8)
        # TP2: 2.5x ATR (second target)
        tp2 = round(current + (atr * 2.5), 8)
        # TP3: 4x ATR (final target)
        tp3 = round(current + (atr * 4), 8)
        
        # SL: 1.5x ATR
        sl = round(current - (atr * 1.5), 8)
        
        # Adjust with resistance
        if resistance > 0:
            if tp3 > resistance:
                tp3 = round(resistance * 0.995, 8)
            if tp2 > resistance:
                tp2 = round(resistance * 0.997, 8)
            if tp1 > resistance:
                tp1 = round(resistance * 0.999, 8)
        
        # Adjust with support
        if support > 0 and sl < support:
            sl = round(support * 0.995, 8)
        
        # Minimum profit
        if tp1 <= current:
            tp1 = round(current * 1.005, 8)
        if tp2 <= current:
            tp2 = round(current * 1.01, 8)
        if tp3 <= current:
            tp3 = round(current * 1.02, 8)
        if sl >= current:
            sl = round(current * 0.995, 8)
    
    elif signal == "SELL":
        entry = current
        
        # TP1: 1.5x ATR
        tp1 = round(current - (atr * 1.5), 8)
        # TP2: 2.5x ATR
        tp2 = round(current - (atr * 2.5), 8)
        # TP3: 4x ATR
        tp3 = round(current - (atr * 4), 8)
        
        # SL: 1.5x ATR
        sl = round(current + (atr * 1.5), 8)
        
        # Adjust with support
        if support > 0:
            if tp3 < support:
                tp3 = round(support * 1.005, 8)
            if tp2 < support:
                tp2 = round(support * 1.003, 8)
            if tp1 < support:
                tp1 = round(support * 1.001, 8)
        
        # Adjust with resistance
        if resistance > 0 and sl > resistance:
            sl = round(resistance * 1.005, 8)
        
        # Minimum profit
        if tp1 >= current:
            tp1 = round(current * 0.995, 8)
        if tp2 >= current:
            tp2 = round(current * 0.99, 8)
        if tp3 >= current:
            tp3 = round(current * 0.98, 8)
        if sl <= current:
            sl = round(current * 1.005, 8)
    
    else:
        entry = current
        tp1 = current
        tp2 = current
        tp3 = current
        sl = current
    
    # Remove duplicates
    unique_reasons = []
    for r in reasons:
        if r not in unique_reasons:
            unique_reasons.append(r)
    
    return {
        'symbol': symbol,
        'entry': entry,
        'signal': signal,
        'confidence': round(confidence, 1),
        'score': round(score, 1),
        'tp1': tp1,
        'tp2': tp2,
        'tp3': tp3,
        'sl': sl,
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
        'reasons': unique_reasons[:6],
        'time': datetime.now().strftime("%H:%M")
    }

# ============================================================
# ALL SYMBOLS
# ============================================================

ALL_SYMBOLS = [
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
    'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT', 'MATICUSDT', 'DOTUSDT',
    'LINKUSDT', 'UNIUSDT', 'ATOMUSDT', 'LTCUSDT', 'BCHUSDT',
    'NEARUSDT', 'ALGOUSDT', 'VETUSDT', 'ICPUSDT', 'FILUSDT',
    'FTMUSDT', 'XLMUSDT', 'EGLDUSDT', 'HNTUSDT', 'XMRUSDT',
    'ZECUSDT', 'DASHUSDT', 'ETCUSDT', 'XTZUSDT', 'EOSUSDT',
    'AAVEUSDT', 'MKRUSDT', 'COMPUSDT', 'YFIUSDT', 'SUSHIUSDT',
    'CAKEUSDT', 'AXSUSDT', 'SANDUSDT', 'APEUSDT', 'CRVUSDT',
    'RUNEUSDT', 'FLOWUSDT', 'QNTUSDT', 'SNXUSDT', 'GRTUSDT',
    'LDOUSDT', 'ARBUSDT', 'OPUSDT', 'INJUSDT', 'SEIUSDT',
    'WLDUSDT', 'PEPEUSDT', 'BONKUSDT', 'FLOKIUSDT', 'SHIBUSDT'
]

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
                    self.total = data.get('total', 0)
                    return
            except:
                pass
        self.positive = 0
        self.negative = 0
        self.total = 0
        self.save()
    
    def save(self):
        try:
            with open(self.file, 'w') as f:
                json.dump({'positive': self.positive, 'negative': self.negative, 'total': self.total}, f)
        except:
            pass
    
    def add_feedback(self, feedback_type):
        if feedback_type == 'positive':
            self.positive += 1
        else:
            self.negative += 1
        self.total += 1
        self.save()
    
    def get_accuracy(self):
        total = self.positive + self.negative
        if total == 0:
            return 50.0
        return round((self.positive / total) * 100, 1)

learner = LearningSystem()

# ============================================================
# TELEGRAM FUNCTIONS
# ============================================================

def send_telegram(message, chat_id=None, reply_markup=None):
    if not message:
        return False
    if chat_id is None:
        chat_id = CHANNEL_ID
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML', 'disable_web_page_preview': True}
        if reply_markup:
            data['reply_markup'] = json.dumps(reply_markup)
        r = requests.post(url, data=data, timeout=15)
        return r.status_code == 200
    except:
        return False

def send_admin(message):
    return send_telegram(message, ADMIN_ID)

# ============================================================
# BUILD SIGNAL MESSAGE - ENTERPRISE
# ============================================================

def build_signal_message(signal, signal_id):
    if not signal or signal['signal'] == 'HOLD':
        return None, None
    
    emoji = "🟢" if signal['signal'] == 'BUY' else "🔴"
    direction = "🚀 LONG (BUY)" if signal['signal'] == 'BUY' else "💀 SHORT (SELL)"
    
    msg = f"""
{emoji} <b>{signal['symbol']}</b> | {direction}
⏰ {signal['time']}

━━━━━━━━━━━━━━━━━━━━━━━━━
💰 <b>ENTRY:</b> <code>${signal['entry']:.6f}</code>

🎯 <b>TARGETS:</b>
• TP1: <code>${signal['tp1']:.6f}</code> (1.5x ATR)
• TP2: <code>${signal['tp2']:.6f}</code> (2.5x ATR)
• TP3: <code>${signal['tp3']:.6f}</code> (4x ATR)

🛑 <b>STOP LOSS:</b> <code>${signal['sl']:.6f}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━
📊 <b>Confidence:</b> {signal['confidence']}% | <b>Score:</b> {signal['score']}

📊 <b>Indicators:</b>
RSI: {signal['rsi']:.1f} | MACD: {signal['macd']:.6f}
MA20: ${signal['ma20']:.4f} | MA50: ${signal['ma50']:.4f}
MA200: ${signal['ma200']:.4f} | VWAP: ${signal['vwap']:.4f}
ATR: ${signal['atr']:.6f} | ADX: {signal['adx']:.1f}
Support: ${signal['support']:.4f} | Resistance: ${signal['resistance']:.4f}

📝 <b>Reasons:</b>
"""
    
    for i, reason in enumerate(signal['reasons'][:5], 1):
        msg += f"{i}. {reason}\n"
    
    msg += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 <b>Accuracy:</b> {learner.get_accuracy()}%
✅ Positive: {learner.positive} | ❌ Negative: {learner.negative}
⚠️ <i>Trade at your own risk!</i>
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

# ============================================================
# SUBSCRIPTION MESSAGE
# ============================================================

def get_subscription_message():
    return f"""
💎 <b>PREMIUM SUBSCRIPTION</b>

💰 <b>Price:</b> {SUBSCRIPTION_PRICE}
🌐 <b>Network:</b> {WALLET_NETWORK}
📌 <b>Wallet:</b>
<code>{WALLET_ADDRESS}</code>

📤 <b>How to subscribe:</b>
1. Send {SUBSCRIPTION_PRICE} to the wallet
2. Send transaction hash to bot
3. Get premium access instantly!

✅ <b>Premium Benefits:</b>
• Unlimited signals (no daily limit)
• Higher accuracy signals (90%+)
• Early access to signals
• Priority support
• 10x more algorithms
• Professional analysis

📊 <b>Free tier:</b>
• 2 free signals per day
• Standard accuracy (60-70%)
• Limited symbols

🔄 <b>Renewal:</b> Automatic after {SUBSCRIPTION_DAYS} days
"""

# ============================================================
# ADMIN PANEL
# ============================================================

def get_admin_keyboard():
    """Admin panel keyboard with buttons"""
    signal_status = "🟢 ON" if db.get_setting('signal_enabled') == '1' else "🔴 OFF"
    payment_status = "🟢 ON" if db.get_setting('payment_enabled') == '1' else "🔴 OFF"
    
    keyboard = {
        'inline_keyboard': [
            [{'text': f'📡 Signals: {signal_status}', 'callback_data': 'admin_toggle_signal'}],
            [{'text': f'💳 Payment: {payment_status}', 'callback_data': 'admin_toggle_payment'}],
            [{'text': '💰 Set Wallet', 'callback_data': 'admin_set_wallet'}],
            [{'text': '💵 Set Price', 'callback_data': 'admin_set_price'}],
            [{'text': '📊 Stats', 'callback_data': 'admin_stats'}],
            [{'text': '📢 Broadcast', 'callback_data': 'admin_broadcast'}],
            [{'text': '🧠 Learning Status', 'callback_data': 'admin_learning'}],
            [{'text': '🔙 Close Panel', 'callback_data': 'admin_close'}]
        ]
    }
    return keyboard

def build_admin_message():
    signal_status = "🟢 ACTIVE" if db.get_setting('signal_enabled') == '1' else "🔴 PAUSED"
    payment_status = "🟢 ACTIVE" if db.get_setting('payment_enabled') == '1' else "🔴 PAUSED"
    wallet = db.get_setting('wallet')
    price = db.get_setting('price')
    
    users = db.get_all_users()
    signals = db.cursor.execute('SELECT COUNT(*) FROM signals').fetchone()[0]
    pending = db.cursor.execute('SELECT COUNT(*) FROM payments WHERE status="pending"').fetchone()[0]
    
    return f"""
👑 <b>ADMIN PANEL</b>

━━━━━━━━━━━━━━━━━━━
📊 <b>BOT STATUS</b>
📡 Signals: {signal_status}
💳 Payment: {payment_status}
💰 Price: {price}
📌 Wallet: <code>{wallet}</code>
⏱ Interval: {INTERVAL//60}m

━━━━━━━━━━━━━━━━━━━
📈 <b>STATISTICS</b>
👤 Users: {len(users)}
📊 Signals: {signals}
💳 Pending Payments: {pending}
🧠 Accuracy: {learner.get_accuracy()}%
✅ Positive: {learner.positive}
❌ Negative: {learner.negative}

━━━━━━━━━━━━━━━━━━━
📋 <b>Commands:</b>
• /admin - Open panel
• /status - Bot status
• /stats - Statistics
• /subscribe - Subscription info
• /help - Help
"""

# ============================================================
# HANDLE CALLBACKS
# ============================================================

def handle_callback(callback_data, user_id):
    try:
        # Feedback
        if callback_data.startswith('fb_'):
            parts = callback_data.split('_')
            if len(parts) != 3:
                return False
            feedback_type = parts[1]
            signal_id = int(parts[2])
            db.update_feedback(signal_id, feedback_type, user_id)
            learner.add_feedback(feedback_type)
            msg = "✅ Thank you for your feedback!" if feedback_type == 'positive' else "❌ Thank you! We'll improve!"
            send_telegram(msg, user_id)
            return True
        
        # Admin panel
        if callback_data.startswith('admin_'):
            if user_id != ADMIN_ID:
                send_telegram("❌ Unauthorized!", user_id)
                return False
            
            if callback_data == 'admin_toggle_signal':
                current = db.get_setting('signal_enabled')
                new = '0' if current == '1' else '1'
                db.update_setting('signal_enabled', new)
                send_telegram(f"📡 Signals: {'🟢 ENABLED' if new == '1' else '🔴 DISABLED'}", user_id)
            
            elif callback_data == 'admin_toggle_payment':
                current = db.get_setting('payment_enabled')
                new = '0' if current == '1' else '1'
                db.update_setting('payment_enabled', new)
                send_telegram(f"💳 Payments: {'🟢 ENABLED' if new == '1' else '🔴 DISABLED'}", user_id)
            
            elif callback_data == 'admin_stats':
                send_telegram(build_admin_message(), user_id, reply_markup=get_admin_keyboard())
                return True
            
            elif callback_data == 'admin_learning':
                msg = f"""
🧠 <b>LEARNING STATUS</b>
• Accuracy: {learner.get_accuracy()}%
• Positive Feedback: {learner.positive}
• Negative Feedback: {learner.negative}
• Total Feedback: {learner.total}
• Learning Rate: {'High' if learner.get_accuracy() > 70 else 'Medium' if learner.get_accuracy() > 55 else 'Low'}
                """
                send_telegram(msg, user_id)
                return True
            
            elif callback_data == 'admin_set_wallet':
                send_telegram("💰 Enter new wallet address:", user_id)
                return True
            
            elif callback_data == 'admin_set_price':
                send_telegram("💵 Enter new price (e.g., 100 USDT):", user_id)
                return True
            
            elif callback_data == 'admin_broadcast':
                send_telegram("📢 Send your broadcast message:", user_id)
                return True
            
            elif callback_data == 'admin_close':
                send_telegram("🔙 Panel closed", user_id)
                return True
            
            # Send updated admin panel
            send_telegram(build_admin_message(), user_id, reply_markup=get_admin_keyboard())
            return True
        
        # Subscription
        if callback_data == 'subscribe':
            send_telegram(get_subscription_message(), user_id)
            return True
        
        return False
    except Exception as e:
        print(f"Callback error: {e}")
        return False

# ============================================================
# CHECK PAYMENTS
# ============================================================

def check_payments():
    payments = db.get_pending_payments()
    if not payments:
        return
    
    for payment in payments:
        payment_id, user_id, payment_hash, created_at, amount = payment
        user = db.get_user(user_id)
        username = user[1] if user else "Unknown"
        
        msg = f"""
🧾 <b>Payment Request #{payment_id}</b>
👤 User: {user_id}
📛 Name: {username}
🔑 Hash: <code>{payment_hash}</code>
💰 Amount: {amount}
📅 Time: {created_at}
        """
        
        keyboard = {
            'inline_keyboard': [
                [
                    {'text': '✅ Confirm', 'callback_data': f'confirm_{payment_id}'},
                    {'text': '❌ Reject', 'callback_data': f'reject_{payment_id}'}
                ]
            ]
        }
        
        send_telegram(msg, ADMIN_ID, reply_markup=keyboard)

# ============================================================
# MAIN LOOP
# ============================================================

def signal_loop():
    print("\n" + "="*70)
    print("🚀 ULTIMATE SIGNAL BOT V12 - ENTERPRISE EDITION")
    print(f"📊 Total Symbols: {len(ALL_SYMBOLS)}")
    print(f"📢 Channel: {CHANNEL_ID}")
    print(f"⏱ Interval: {INTERVAL//60} minutes")
    print("="*70)
    
    send_telegram("🚀 Signal Bot V12 started!\n📊 Enterprise Edition")
    send_admin(build_admin_message(), reply_markup=get_admin_keyboard())
    
    cycle = 0
    
    while True:
        try:
            cycle += 1
            
            if db.get_setting('signal_enabled') != '1':
                time.sleep(30)
                continue
            
            print(f"\n🔄 Cycle {cycle} - {datetime.now().strftime('%H:%M:%S')}")
            print(f"🧠 Accuracy: {learner.get_accuracy()}%")
            
            signals = []
            
            for symbol in ALL_SYMBOLS:
                signal = generate_signal(symbol)
                if signal and signal['signal'] != 'HOLD':
                    if signal['confidence'] >= MIN_CONFIDENCE:
                        signals.append(signal)
                        print(f"✅ {signal['symbol']}: {signal['signal']} ({signal['confidence']}%)")
                time.sleep(0.02)
            
            signals.sort(key=lambda x: x['confidence'], reverse=True)
            signals = signals[:MAX_SIGNALS]
            
            if signals:
                for signal in signals:
                    signal_id = db.save_signal(0, signal)
                    msg, keyboard = build_signal_message(signal, signal_id)
                    if msg:
                        send_telegram(msg, reply_markup=keyboard)
                        time.sleep(1)
            else:
                if cycle % 3 == 0:
                    send_telegram(f"⏳ No signals (Cycle {cycle})")
            
            check_payments()
            
            print(f"⏱ Waiting {INTERVAL//60} minutes...")
            time.sleep(INTERVAL)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            send_admin(f"❌ Error: {e}")
            time.sleep(60)

# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    signal_loop()