# ============================================================
# ULTIMATE SIGNAL BOT V9 - FULL SYMBOLS
# ALL CRYPTO SYMBOLS + DEEP ANALYSIS + REAL DATA
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
PRICE = "100 USDT"

INTERVAL = 180  # 3 minutes
MIN_CONFIDENCE = 60
MAX_SIGNALS = 3  # Send 3 signals per cycle

# ============================================================
# ALL CRYPTO SYMBOLS (FULL LIST)
# ============================================================

ALL_SYMBOLS = [
    # TOP 10
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
    'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT', 'MATICUSDT', 'DOTUSDT',
    
    # Layer 1
    'LINKUSDT', 'UNIUSDT', 'ATOMUSDT', 'LTCUSDT', 'BCHUSDT',
    'NEARUSDT', 'ALGOUSDT', 'VETUSDT', 'ICPUSDT', 'FILUSDT',
    'FTMUSDT', 'XLMUSDT', 'EGLDUSDT', 'HNTUSDT', 'XMRUSDT',
    'ZECUSDT', 'DASHUSDT', 'ETCUSDT', 'XTZUSDT', 'EOSUSDT',
    'AAVEUSDT', 'MKRUSDT', 'COMPUSDT', 'YFIUSDT', 'SUSHIUSDT',
    'CAKEUSDT', 'AXSUSDT', 'SANDUSDT', 'APEUSDT', 'CRVUSDT',
    'RUNEUSDT', 'FLOWUSDT', 'QNTUSDT', 'SNXUSDT', 'GRTUSDT',
    'LDOUSDT', 'ARBUSDT', 'OPUSDT', 'INJUSDT', 'SEIUSDT',
    'WLDUSDT', 'PEPEUSDT', 'BONKUSDT', 'FLOKIUSDT', 'SHIBUSDT',
    
    # More Altcoins
    'WIFUSDT', 'RNDRUSDT', 'FETUSDT', 'AGIXUSDT', 'OCEANUSDT',
    'AKTUSDT', 'NOSUSDT', 'CUDOSUSDT', 'PHBUSDT', 'AIOZUSDT',
    'ENSUSDT', 'MASKUSDT', 'LPTUSDT', 'GALAUSDT', 'MANAUSDT',
    'ENJUSDT', 'CHZUSDT', 'BAKEUSDT', 'BATUSDT', 'ZILUSDT',
    'ONEUSDT', 'IOTAUSDT', 'NANOUSDT', 'XEMUSDT', 'WAVESUSDT',
    'KAVAUSDT', 'KSMUSDT', 'MOVRUSDT', 'GLMRUSDT', 'CFGUSDT',
    'KARUSDT', 'PHAUSDT', 'RMRKUSDT', 'HYDRAUSDT', 'PICUSDT',
    'TURUSDT', 'ZTGUSDT', 'BOMEUSDT', 'MEMEUSDT', 'PEPE2USDT',
    'ENAUSDT', 'ETHFIUSDT', 'STRKUSDT', 'JUPUSDT', 'PYTHUSDT',
    'WUSDT', 'ALTUSDT', 'METISUSDT', 'MANTAUSDT', 'ONDOUSDT',
    'DYMUSDT', 'SAGAUSDT', 'TAOUSDT', 'XAIUSDT', 'PENDLEUSDT',
    'BEAMUSDT', 'RATSUSDT', 'SATSUSDT', 'ORDIUSDT', 'MUBIUSDT',
    'RIFUSDT', 'STXUSDT', 'COREUSDT', 'NEXOUSDT', 'ANKRUSDT',
    'BANDUSDT', 'NMRUSDT', 'AGLDUSDT', 'AUDIOUSDT', 'BALUSDT',
    'BNTUSDT', 'CHRUSDT', 'COTIUSDT', 'DENTUSDT', 'DFIUSDT',
    'DGBUSDT', 'DODOUSDT', 'DUSKUSDT', 'ELFUSDT', 'ERGOUSDT',
    'FUNUSDT', 'GALUSDT', 'GTCUSDT', 'HBARUSDT', 'HOTUSDT',
    'ICXUSDT', 'IOSTUSDT', 'KDAUSDT', 'LRCUSDT', 'LSKUSDT',
    'MINAUSDT', 'NEOUSDT', 'OGNUSDT', 'OMGUSDT', 'ONTUSDT',
    'OXTUSDT', 'POLYXUSDT', 'POWRUSDT', 'QKCUSDT', 'QLCUSDT',
    'QTUMUSDT', 'RENUSDT', 'REQUSDT', 'RVNUSDT', 'SCUSDT',
    'SKALEUSDT', 'SLPUSDT', 'SXPUSDT', 'TELUSDT', 'TFUELUSDT',
    'TOMOUSDT', 'TRBUSDT', 'TWTUSDT', 'UMAUSDT', 'WAXPUSDT',
    'WINGUSDT', 'XDCUSDT', 'XECUSDT', 'XNOUSDT', 'XPRUSDT',
    'ZENUSDT', 'ZRXUSDT', 'PUNDIXUSDT', 'QSPUSDT', 'RLCUSDT',
    'STMXUSDT', 'STORJUSDT', 'SUNUSDT', 'SUPERUSDT', 'SYSUSDT',
    'TROYUSDT', 'UNFIUSDT', 'VIDTUSDT', 'VTHOUSDT', 'WRXUSDT',
    'XVSUSDT', 'YGGUSDT', 'ZETAUSDT', 'ZKFUSDT', 'ZROUSDT'
]

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
                negative_feedback INTEGER DEFAULT 0
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
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
                vwap REAL,
                score REAL,
                reasons TEXT,
                feedback TEXT DEFAULT '',
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
                expire_at TIMESTAMP
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        self.cursor.execute('INSERT OR IGNORE INTO settings VALUES ("signal_enabled", "1")')
        self.cursor.execute('INSERT OR IGNORE INTO settings VALUES ("payment_enabled", "1")')
        self.cursor.execute('INSERT OR IGNORE INTO settings VALUES ("wallet", ?)', (WALLET_ADDRESS,))
        self.cursor.execute('INSERT OR IGNORE INTO settings VALUES ("price", ?)', (PRICE,))
        self.cursor.execute('INSERT OR IGNORE INTO settings VALUES ("free_signals", "2")')
        
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
    
    def get_free_signals(self, user_id):
        user = self.get_user(user_id)
        if not user:
            return 2
        return user[4] if len(user) > 4 else 2
    
    def use_free_signal(self, user_id):
        self.cursor.execute('''
            UPDATE users SET free_signals = free_signals - 1
            WHERE user_id = ? AND free_signals > 0
        ''', (user_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
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
    
    def add_payment(self, user_id, payment_hash):
        self.cursor.execute('''
            INSERT INTO payments (user_id, payment_hash, created_at)
            VALUES (?, ?, ?)
        ''', (user_id, payment_hash, datetime.now().isoformat()))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_pending_payments(self):
        self.cursor.execute('''
            SELECT id, user_id, payment_hash, created_at 
            FROM payments WHERE status = 'pending'
            ORDER BY created_at ASC
        ''')
        return self.cursor.fetchall()
    
    def confirm_payment(self, payment_id):
        payment = self.get_payment(payment_id)
        if not payment or payment[3] != 'pending':
            return False, None
        
        user_id = payment[1]
        expire_date = datetime.now() + timedelta(days=30)
        
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
        self.cursor.execute('SELECT id, user_id, payment_hash, status FROM payments WHERE id = ?', (payment_id,))
        return self.cursor.fetchone()
    
    def save_signal(self, user_id, signal_data, is_free=False):
        self.cursor.execute('''
            INSERT INTO signals (
                user_id, symbol, direction, entry, tp, sl, confidence,
                created_at, is_free, rsi, macd, ma20, ma50, vwap, score, reasons
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, signal_data['symbol'], signal_data['signal'],
            signal_data['price'], signal_data['tp'], signal_data['sl'],
            signal_data['confidence'], datetime.now().isoformat(),
            1 if is_free else 0,
            signal_data.get('rsi', 0), signal_data.get('macd', 0),
            signal_data.get('ma20', 0), signal_data.get('ma50', 0),
            signal_data.get('vwap', 0), signal_data.get('score', 0),
            '|'.join(signal_data.get('reasons', []))
        ))
        signal_id = self.cursor.lastrowid
        self.conn.commit()
        return signal_id
    
    def update_feedback(self, signal_id, feedback_type):
        self.cursor.execute('''
            UPDATE signals SET feedback = ? WHERE id = ?
        ''', (feedback_type, signal_id))
        
        self.cursor.execute('SELECT user_id FROM signals WHERE id = ?', (signal_id,))
        r = self.cursor.fetchone()
        if r:
            user_id = r[0]
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
        return r[0] if r else None
    
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
    
    def get_total_signals(self):
        self.cursor.execute('SELECT COUNT(*) FROM signals')
        return self.cursor.fetchone()[0]

db = Database()

# ============================================================
# REAL DATA FROM BINANCE
# ============================================================

def get_candles(symbol, limit=200, interval='5m'):
    """Get REAL candlestick data from Binance"""
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

def get_price(symbol):
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return float(r.json()['price'])
    except:
        pass
    return None

def get_24h_stats(symbol):
    try:
        url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            return {
                'high': float(data['highPrice']),
                'low': float(data['lowPrice']),
                'volume': float(data['volume']),
                'change': float(data['priceChangePercent'])
            }
    except:
        pass
    return None

# ============================================================
# REAL INDICATORS
# ============================================================

def calc_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50.0
    
    p = np.array(prices[-period-1:])
    deltas = np.diff(p)
    gain = np.mean(deltas[deltas > 0]) if np.sum(deltas > 0) > 0 else 0
    loss = -np.mean(deltas[deltas < 0]) if np.sum(deltas < 0) > 0 else 0.001
    
    rs = gain / loss
    return round(100 - (100 / (1 + rs)), 1)

def calc_macd(prices, fast=12, slow=26, signal=9):
    if len(prices) < slow:
        return 0, 0, 0
    
    p = np.array(prices)
    
    f_mult = 2 / (fast + 1)
    f_ema = float(np.mean(p[-fast:]))
    for price in p[-fast:]:
        f_ema = float(price) * f_mult + f_ema * (1 - f_mult)
    
    s_mult = 2 / (slow + 1)
    s_ema = float(np.mean(p[-slow:]))
    for price in p[-slow:]:
        s_ema = float(price) * s_mult + s_ema * (1 - s_mult)
    
    macd_line = f_ema - s_ema
    
    sig_mult = 2 / (signal + 1)
    sig_line = macd_line
    for _ in range(signal):
        sig_line = macd_line * sig_mult + sig_line * (1 - sig_mult)
    
    hist = macd_line - sig_line
    return round(macd_line, 4), round(sig_line, 4), round(hist, 4)

def calc_ma(prices, period):
    if len(prices) < period:
        return prices[-1] if prices else 0
    return round(float(np.mean(np.array(prices[-period:]))), 2)

def calc_bollinger(prices, period=20, std_dev=2):
    if len(prices) < period:
        return prices[-1] if prices else 0, prices[-1] if prices else 0, prices[-1] if prices else 0
    
    p = np.array(prices[-period:])
    ma = float(np.mean(p))
    std = float(np.std(p))
    
    upper = ma + (std_dev * std)
    lower = ma - (std_dev * std)
    return round(upper, 2), round(ma, 2), round(lower, 2)

def calc_vwap(prices, volumes):
    if len(prices) < 2:
        return prices[-1] if prices else 0
    
    total_value = sum(prices[i] * volumes[i] for i in range(len(prices)))
    total_volume = sum(volumes)
    if total_volume == 0:
        return prices[-1]
    return round(total_value / total_volume, 2)

def calc_atr(highs, lows, prices, period=14):
    if len(prices) < period:
        return 0.01
    
    tr = []
    for i in range(1, period + 1):
        if i < len(prices):
            tr.append(max(
                highs[-i] - lows[-i],
                abs(highs[-i] - prices[-i-1]),
                abs(lows[-i] - prices[-i-1])
            ))
    
    return round(float(np.mean(np.array(tr))) if tr else 0.01, 2)

def find_support_resistance(highs, lows, prices):
    if len(prices) < 30:
        return 0, 0
    
    peaks = []
    troughs = []
    
    for i in range(2, len(prices)-2):
        if highs[i] > highs[i-1] and highs[i] > highs[i+1]:
            if highs[i] > highs[i-2] and highs[i] > highs[i+2]:
                peaks.append(highs[i])
        
        if lows[i] < lows[i-1] and lows[i] < lows[i+1]:
            if lows[i] < lows[i-2] and lows[i] < lows[i+2]:
                troughs.append(lows[i])
    
    resistance = max(peaks) if peaks else 0
    support = min(troughs) if troughs else 0
    
    return round(support, 2), round(resistance, 2)

# ============================================================
# PUMP/DUMP DETECTION
# ============================================================

def analyze_pump_dump(symbol):
    data = get_candles(symbol, 100, '5m')
    if not data:
        return 0, 0
    
    prices = data['close']
    volumes = data['volume']
    
    change_1h = ((prices[-1] - prices[-12]) / prices[-12]) * 100 if len(prices) >= 12 else 0
    change_4h = ((prices[-1] - prices[-48]) / prices[-48]) * 100 if len(prices) >= 48 else 0
    
    avg_vol = np.mean(volumes[-20:]) if len(volumes) >= 20 else 1
    vol_ratio = volumes[-1] / avg_vol if avg_vol > 0 else 1
    
    pump_score = 0
    dump_score = 0
    
    if change_1h > 3 and vol_ratio > 2:
        pump_score += 30
        dump_score += 20
    
    if change_4h > 8:
        pump_score += 20
        dump_score += 30
    
    if change_1h < -3 and vol_ratio > 2:
        dump_score += 30
        pump_score += 20
    
    if change_4h < -8:
        dump_score += 20
        pump_score += 30
    
    return round(pump_score, 1), round(dump_score, 1)

# ============================================================
# SIGNAL GENERATOR
# ============================================================

def generate_signal(symbol):
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
    
    # Calculate all indicators
    rsi = calc_rsi(prices, 14)
    macd, macd_sig, macd_hist = calc_macd(prices, 12, 26, 9)
    ma20 = calc_ma(prices, 20)
    ma50 = calc_ma(prices, 50)
    ma200 = calc_ma(prices, 200)
    upper_bb, middle_bb, lower_bb = calc_bollinger(prices, 20, 2)
    vwap = calc_vwap(prices, volumes)
    atr = calc_atr(highs, lows, prices, 14)
    support, resistance = find_support_resistance(highs, lows, prices)
    
    avg_vol = np.mean(volumes[-20:]) if len(volumes) >= 20 else 1
    vol_ratio = volumes[-1] / avg_vol if avg_vol > 0 else 1
    
    pump_score, dump_score = analyze_pump_dump(symbol)
    
    # Scoring
    score = 50
    reasons = []
    
    # RSI (25 points)
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
    else:
        reasons.append(f"⚖️ RSI: {rsi}")
    
    # MACD (20 points)
    if macd > 0 and macd_hist > 0:
        score += 20
        reasons.append(f"🟢 MACD Bullish: {macd}")
    elif macd < 0 and macd_hist < 0:
        score -= 20
        reasons.append(f"🔴 MACD Bearish: {macd}")
    elif macd > 0:
        score += 10
        reasons.append(f"🟡 MACD Positive: {macd}")
    else:
        score -= 10
        reasons.append(f"🟡 MACD Negative: {macd}")
    
    # Moving Averages (20 points)
    if current > ma20 and ma20 > ma50 and ma50 > ma200:
        score += 20
        reasons.append("🚀 Strong Uptrend")
    elif current < ma20 and ma20 < ma50 and ma50 < ma200:
        score -= 20
        reasons.append("💀 Strong Downtrend")
    elif current > ma20 and ma20 > ma50:
        score += 12
        reasons.append("📈 Uptrend")
    elif current < ma20 and ma20 < ma50:
        score -= 12
        reasons.append("📉 Downtrend")
    elif current > ma20:
        score += 5
        reasons.append(f"⬆️ Price above MA20")
    else:
        score -= 5
        reasons.append(f"⬇️ Price below MA20")
    
    # Bollinger (15 points)
    if current < lower_bb:
        score += 15
        reasons.append(f"🎯 Touch Lower Band")
    elif current > upper_bb:
        score -= 15
        reasons.append(f"🎯 Touch Upper Band")
    elif current < middle_bb:
        score += 8
        reasons.append("📊 Lower Half of Band")
    else:
        score -= 8
        reasons.append("📊 Upper Half of Band")
    
    # VWAP (10 points)
    if current > vwap:
        score += 10
        reasons.append(f"✅ Price Above VWAP")
    else:
        score -= 10
        reasons.append(f"❌ Price Below VWAP")
    
    # Volume (5 points)
    if vol_ratio > 2.5:
        score += 5
        reasons.append(f"📊 High Volume: {vol_ratio:.1f}x")
    elif vol_ratio > 1.5:
        score += 3
        reasons.append(f"📊 Good Volume: {vol_ratio:.1f}x")
    elif vol_ratio < 0.5:
        score -= 5
        reasons.append(f"📊 Low Volume: {vol_ratio:.1f}x")
    
    # Support/Resistance (10 points)
    if support > 0:
        dist_support = ((current - support) / current) * 100
        if dist_support < 0.5:
            score += 10
            reasons.append(f"🛡️ Very Near Support")
        elif dist_support < 1.5:
            score += 7
            reasons.append(f"🛡️ Near Support")
    
    if resistance > 0:
        dist_resistance = ((resistance - current) / current) * 100
        if dist_resistance < 0.5:
            score -= 10
            reasons.append(f"🚫 Very Near Resistance")
        elif dist_resistance < 1.5:
            score -= 7
            reasons.append(f"🚫 Near Resistance")
    
    # Pump/Dump (5 points)
    if pump_score > dump_score and pump_score > 20:
        score += 5
        reasons.append(f"🔥 Pump Detected")
    elif dump_score > pump_score and dump_score > 20:
        score -= 5
        reasons.append(f"💀 Dump Detected")
    
    confidence = min(98, 50 + abs(score - 50) * 1.2)
    
    if score > 55:
        signal = "BUY"
    elif score < 45:
        signal = "SELL"
    else:
        signal = "HOLD"
    
    # TP/SL
    if signal == "BUY":
        tp = round(current + (atr * 3), 6)
        sl = round(current - (atr * 2), 6)
        if resistance > 0 and tp > resistance:
            tp = round(resistance * 0.995, 6)
        if support > 0 and sl < support:
            sl = round(support * 0.995, 6)
        if (tp - current) < (current * 0.005):
            tp = round(current * 1.01, 6)
    elif signal == "SELL":
        tp = round(current - (atr * 3), 6)
        sl = round(current + (atr * 2), 6)
        if support > 0 and tp < support:
            tp = round(support * 1.005, 6)
        if resistance > 0 and sl > resistance:
            sl = round(resistance * 1.005, 6)
        if (current - tp) < (current * 0.005):
            tp = round(current * 0.99, 6)
    else:
        tp = current
        sl = current
    
    # Remove duplicates
    unique_reasons = []
    for r in reasons:
        if r not in unique_reasons:
            unique_reasons.append(r)
    
    return {
        'symbol': symbol,
        'price': current,
        'signal': signal,
        'confidence': round(confidence, 1),
        'score': round(score, 1),
        'tp': tp,
        'sl': sl,
        'rsi': rsi,
        'macd': macd,
        'ma20': ma20,
        'ma50': ma50,
        'vwap': vwap,
        'atr': atr,
        'support': support,
        'resistance': resistance,
        'vol_ratio': round(vol_ratio, 2),
        'pump_score': pump_score,
        'dump_score': dump_score,
        'reasons': unique_reasons[:6],
        'time': datetime.now().strftime("%H:%M")
    }

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
                json.dump({
                    'positive': self.positive,
                    'negative': self.negative,
                    'total': self.total
                }, f)
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
        data = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True
        }
        
        if reply_markup:
            data['reply_markup'] = json.dumps(reply_markup)
        
        r = requests.post(url, data=data, timeout=15)
        return r.status_code == 200
    except:
        return False

def send_admin(message):
    return send_telegram(message, ADMIN_ID)

def build_signal_message(signal, signal_id):
    """Build COMPACT signal message"""
    if not signal or signal['signal'] == 'HOLD':
        return None, None
    
    emoji = "🟢" if signal['signal'] == 'BUY' else "🔴"
    direction = "LONG" if signal['signal'] == 'BUY' else "SHORT"
    
    msg = f"""
{emoji} <b>{signal['symbol']}</b> | {direction}
💰 <b>Entry:</b> <code>${signal['price']:,.4f}</code>
🎯 <b>TP:</b> <code>${signal['tp']:,.4f}</code>
🛑 <b>SL:</b> <code>${signal['sl']:,.4f}</code>
📊 <b>Confidence:</b> {signal['confidence']}% | <b>Score:</b> {signal['score']}

📊 <b>Indicators:</b>
RSI: {signal['rsi']:.1f} | MACD: {signal['macd']:.4f}
MA20: ${signal['ma20']:.2f} | MA50: ${signal['ma50']:.2f}
VWAP: ${signal['vwap']:.2f} | ATR: ${signal['atr']:.2f}
Support: ${signal['support']:.2f} | Resistance: ${signal['resistance']:.2f}
Volume: {signal['vol_ratio']:.1f}x | Pump: {signal['pump_score']:.1f}% | Dump: {signal['dump_score']:.1f}%

📝 <b>Reasons:</b>
"""
    
    for i, reason in enumerate(signal['reasons'][:5], 1):
        msg += f"{i}. {reason}\n"
    
    msg += f"""
🧠 <b>Accuracy:</b> {learner.get_accuracy()}%
✅ Positive: {learner.positive} | ❌ Negative: {learner.negative}
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

# ============================================================
# FEEDBACK HANDLER
# ============================================================

def handle_feedback(callback_data):
    try:
        parts = callback_data.split('_')
        if len(parts) != 3:
            return False
        
        feedback_type = parts[1]
        signal_id = int(parts[2])
        
        user_id = db.update_feedback(signal_id, feedback_type)
        
        if user_id:
            learner.add_feedback(feedback_type)
            
            if feedback_type == 'positive':
                msg = "✅ Thank you! Your feedback helps improve accuracy!"
            else:
                msg = "❌ Thank you for feedback! We'll improve!"
            
            send_telegram(msg, user_id)
            return True
        
        return False
    except:
        return False

# ============================================================
# MAIN LOOP
# ============================================================

def signal_loop():
    print("\n" + "="*60)
    print("🚀 ULTIMATE SIGNAL BOT V9")
    print(f"📊 Total Symbols: {len(ALL_SYMBOLS)}")
    print(f"📢 Channel: {CHANNEL_ID}")
    print(f"⏱ Interval: {INTERVAL//60} minutes")
    print("="*60)
    
    send_telegram(f"🚀 Signal Bot V9 started!\n📊 Analyzing {len(ALL_SYMBOLS)} symbols")
    
    cycle = 0
    
    while True:
        try:
            cycle += 1
            
            if db.get_setting('signal_enabled') != '1':
                time.sleep(30)
                continue
            
            print(f"\n🔄 Cycle {cycle} - {datetime.now().strftime('%H:%M:%S')}")
            print(f"🧠 Accuracy: {learner.get_accuracy()}%")
            print(f"📊 Scanning {len(ALL_SYMBOLS)} symbols...")
            
            signals = []
            total_checked = 0
            
            for symbol in ALL_SYMBOLS:
                total_checked += 1
                signal = generate_signal(symbol)
                if signal and signal['signal'] != 'HOLD':
                    if signal['confidence'] >= MIN_CONFIDENCE:
                        signals.append(signal)
                        print(f"✅ {signal['symbol']}: {signal['signal']} ({signal['confidence']}%)")
                time.sleep(0.02)
            
            print(f"📊 Scanned {total_checked} symbols, found {len(signals)} signals")
            
            signals.sort(key=lambda x: x['confidence'], reverse=True)
            signals = signals[:MAX_SIGNALS]
            
            if signals:
                for signal in signals:
                    signal_id = db.save_signal(0, signal, True)
                    msg, keyboard = build_signal_message(signal, signal_id)
                    if msg:
                        if send_telegram(msg, reply_markup=keyboard):
                            print(f"✅ Sent: {signal['symbol']}")
                        time.sleep(1)
            else:
                if cycle % 2 == 0:
                    send_telegram(f"⏳ No signals found (Cycle {cycle})")
            
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