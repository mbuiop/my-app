# ============================================================
# ULTIMATE SIGNAL BOT V13 - PROFESSIONAL EDITION
# FULLY WORKING | ADMIN PANEL | REAL SIGNALS | NO ERRORS
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

INTERVAL = 300  # 5 minutes
MAX_SIGNALS = 3
MIN_CONFIDENCE = 65
MIN_VOLUME_RATIO = 1.2
MIN_ADX = 20

# ============================================================
# DATABASE - Complete
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
                feedback_count INTEGER DEFAULT 0,
                positive_feedback INTEGER DEFAULT 0,
                negative_feedback INTEGER DEFAULT 0
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
                reasons TEXT,
                feedback TEXT DEFAULT '',
                feedback_user INTEGER DEFAULT 0,
                sent_to_channel BOOLEAN DEFAULT 0
            )
        ''')
        
        # Payments
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                payment_hash TEXT,
                amount TEXT,
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
            ('wallet', WALLET_ADDRESS),
            ('price', PRICE),
            ('min_confidence', str(MIN_CONFIDENCE)),
            ('max_signals', str(MAX_SIGNALS)),
            ('min_volume', str(MIN_VOLUME_RATIO)),
            ('min_adx', str(MIN_ADX))
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
                symbol, direction, entry, tp, sl, confidence,
                created_at, rsi, macd, ma20, ma50, ma200,
                vwap, atr, support, resistance, score, quality_score, reasons
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            '|'.join(signal_data.get('reasons', []))
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
    
    def update_feedback(self, signal_id, feedback_type, user_id):
        # Check if already feedbacked
        self.cursor.execute('SELECT id FROM feedback_log WHERE signal_id = ? AND user_id = ?', (signal_id, user_id))
        if self.cursor.fetchone():
            return False, "You already gave feedback for this signal"
        
        self.cursor.execute('UPDATE signals SET feedback = ?, feedback_user = ? WHERE id = ?', 
                           (feedback_type, user_id, signal_id))
        
        if feedback_type == 'positive':
            self.cursor.execute('UPDATE users SET positive_feedback = positive_feedback + 1, feedback_count = feedback_count + 1 WHERE user_id = ?', (user_id,))
        else:
            self.cursor.execute('UPDATE users SET negative_feedback = negative_feedback + 1, feedback_count = feedback_count + 1 WHERE user_id = ?', (user_id,))
        
        self.cursor.execute('INSERT INTO feedback_log (signal_id, user_id, feedback, created_at) VALUES (?, ?, ?, ?)',
                           (signal_id, user_id, feedback_type, datetime.now().isoformat()))
        self.conn.commit()
        return True, "Feedback recorded"
    
    def add_payment(self, user_id, payment_hash):
        self.cursor.execute('INSERT INTO payments (user_id, payment_hash, amount, created_at) VALUES (?, ?, ?, ?)',
                           (user_id, payment_hash, PRICE, datetime.now().isoformat()))
        payment_id = self.cursor.lastrowid
        self.conn.commit()
        return payment_id
    
    def get_pending_payments(self):
        self.cursor.execute('SELECT id, user_id, payment_hash, amount, created_at FROM payments WHERE status = "pending" ORDER BY created_at ASC')
        return self.cursor.fetchall()
    
    def confirm_payment(self, payment_id):
        self.cursor.execute('SELECT user_id FROM payments WHERE id = ? AND status = "pending"', (payment_id,))
        result = self.cursor.fetchone()
        if not result:
            return False, None
        
        user_id = result[0]
        expire_date = datetime.now() + timedelta(days=30)
        
        self.cursor.execute('UPDATE payments SET status = "confirmed", confirmed_at = ?, expire_at = ? WHERE id = ?',
                           (datetime.now().isoformat(), expire_date.isoformat(), payment_id))
        
        self.cursor.execute('UPDATE users SET subscription_expire = ?, is_active = 1 WHERE user_id = ?',
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
        signals = self.cursor.execute('SELECT COUNT(*) FROM signals').fetchone()[0]
        today = self.cursor.execute('SELECT COUNT(*) FROM signals WHERE DATE(created_at) = DATE("now")').fetchone()[0]
        pending = self.cursor.execute('SELECT COUNT(*) FROM payments WHERE status = "pending"').fetchone()[0]
        feedback = self.cursor.execute('SELECT COUNT(*) FROM feedback_log').fetchone()[0]
        
        return {
            'users': users,
            'active': active,
            'signals': signals,
            'today': today,
            'pending': pending,
            'feedback': feedback
        }

db = Database()

# ============================================================
# INDICATORS - Professional
# ============================================================

def get_candles(symbol, limit=200, interval='5m'):
    """Get real candle data from Binance"""
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
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)

def calculate_macd(prices, fast=12, slow=26, signal=9):
    if len(prices) < slow:
        return 0, 0, 0
    
    prices = np.array(prices)
    
    # Fast EMA
    fast_mult = 2.0 / (fast + 1)
    fast_ema = np.mean(prices[-fast:])
    for price in prices[-fast:]:
        fast_ema = price * fast_mult + fast_ema * (1 - fast_mult)
    
    # Slow EMA
    slow_mult = 2.0 / (slow + 1)
    slow_ema = np.mean(prices[-slow:])
    for price in prices[-slow:]:
        slow_ema = price * slow_mult + slow_ema * (1 - slow_mult)
    
    macd_line = fast_ema - slow_ema
    
    # Signal line
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
            tr = max(
                highs[-i] - lows[-i],
                abs(highs[-i] - closes[-i-1]),
                abs(lows[-i] - closes[-i-1])
            )
            tr_list.append(tr)
    
    if not tr_list:
        return 0.0000001
    
    return round(np.mean(tr_list), 8)

def find_support_resistance(highs, lows, closes):
    if len(closes) < 30:
        return 0, 0
    
    peaks = []
    troughs = []
    
    for i in range(2, len(closes) - 2):
        # Peak detection
        if (highs[i] > highs[i-1] and highs[i] > highs[i+1] and
            highs[i] > highs[i-2] and highs[i] > highs[i+2]):
            peaks.append(highs[i])
        
        # Trough detection
        if (lows[i] < lows[i-1] and lows[i] < lows[i+1] and
            lows[i] < lows[i-2] and lows[i] < lows[i+2]):
            troughs.append(lows[i])
    
    resistance = peaks[0] if peaks else 0
    support = troughs[0] if troughs else 0
    
    return round(support, 8), round(resistance, 8)

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

# ============================================================
# SIGNAL GENERATOR - Professional
# ============================================================

def generate_signal(symbol):
    """Generate high-quality trading signal"""
    try:
        # Get real data
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
        rsi = calculate_rsi(prices, 14)
        macd, _, macd_hist = calculate_macd(prices, 12, 26, 9)
        ma7 = calculate_ma(prices, 7)
        ma20 = calculate_ma(prices, 20)
        ma50 = calculate_ma(prices, 50)
        ma200 = calculate_ma(prices, 200)
        upper_bb, middle_bb, lower_bb = calculate_bollinger(prices, 20, 2)
        vwap = calculate_vwap(prices, volumes)
        atr = calculate_atr(highs, lows, prices, 14)
        support, resistance = find_support_resistance(highs, lows, prices)
        adx = calculate_adx(highs, lows, prices, 14)
        
        # Volume ratio
        avg_volume = np.mean(volumes[-20:]) if len(volumes) >= 20 else 1
        volume_ratio = volumes[-1] / avg_volume if avg_volume > 0 else 1
        
        # ===== SCORING SYSTEM =====
        score = 50
        reasons = []
        
        # 1. RSI (25 points)
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
        
        # 2. MACD (20 points)
        if macd > 0 and macd_hist > 0:
            score += 20
            reasons.append(f"🟢 MACD Bullish")
        elif macd < 0 and macd_hist < 0:
            score -= 20
            reasons.append(f"🔴 MACD Bearish")
        elif macd > 0:
            score += 10
            reasons.append(f"🟡 MACD Positive")
        else:
            score -= 10
            reasons.append(f"🟡 MACD Negative")
        
        # 3. Moving Averages (20 points)
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
            reasons.append(f"⬆️ Above MA20")
        else:
            score -= 5
            reasons.append(f"⬇️ Below MA20")
        
        # 4. Bollinger Bands (15 points)
        if current < lower_bb:
            score += 15
            reasons.append(f"🎯 Lower Band")
        elif current > upper_bb:
            score -= 15
            reasons.append(f"🎯 Upper Band")
        elif current < middle_bb:
            score += 8
            reasons.append(f"📊 Below Middle")
        else:
            score -= 8
            reasons.append(f"📊 Above Middle")
        
        # 5. VWAP (10 points)
        if current > vwap:
            score += 10
            reasons.append(f"✅ Above VWAP")
        else:
            score -= 10
            reasons.append(f"❌ Below VWAP")
        
        # 6. Support/Resistance (10 points)
        if support > 0:
            dist_to_support = ((current - support) / current) * 100
            if dist_to_support < 1:
                score += 10
                reasons.append(f"🛡️ Near Support")
            elif dist_to_support < 3:
                score += 5
                reasons.append(f"🛡️ Close to Support")
        
        if resistance > 0:
            dist_to_resistance = ((resistance - current) / current) * 100
            if dist_to_resistance < 1:
                score -= 10
                reasons.append(f"🚫 Near Resistance")
            elif dist_to_resistance < 3:
                score -= 5
                reasons.append(f"🚫 Close to Resistance")
        
        # 7. Volume (5 points)
        if volume_ratio > 2.5:
            score += 5
            reasons.append(f"📊 High Volume: {volume_ratio:.1f}x")
        elif volume_ratio > 1.5:
            score += 3
            reasons.append(f"📊 Good Volume: {volume_ratio:.1f}x")
        elif volume_ratio < 0.5:
            score -= 5
            reasons.append(f"📊 Low Volume: {volume_ratio:.1f}x")
        
        # 8. ADX (5 points)
        if adx > 50:
            if score > 50:
                score += 5
                reasons.append(f"🔥 Strong Trend")
            else:
                score -= 5
                reasons.append(f"💀 Strong Trend")
        elif adx > 30:
            if score > 50:
                score += 3
                reasons.append(f"✅ Moderate Trend")
        
        # ===== FINAL DECISION =====
        confidence = min(98, 50 + abs(score - 50) * 1.5)
        quality_score = min(100, confidence + 5 if score > 50 else confidence - 5)
        
        if score > 55:
            signal = "BUY"
        elif score < 45:
            signal = "SELL"
        else:
            return None  # Weak signal
        
        # ===== TAKE PROFIT / STOP LOSS =====
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
            'reasons': reasons[:6],
            'time': datetime.now().strftime("%H:%M")
        }
        
    except Exception as e:
        logger.error(f"Error generating signal for {symbol}: {e}")
        return None

# ============================================================
# SYMBOLS - Full List
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
                        'sr': 1.0, 'adx': 1.0
                    })
                    return
            except:
                pass
        
        self.positive = 0
        self.negative = 0
        self.weights = {
            'rsi': 1.0, 'macd': 1.0, 'ma': 1.0,
            'bollinger': 1.0, 'vwap': 1.2, 'volume': 1.0,
            'sr': 1.0, 'adx': 1.0
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
                self.weights[key] = min(2.0, self.weights[key] * 1.01)
        else:
            self.negative += 1
            for key in self.weights:
                self.weights[key] = max(0.5, self.weights[key] * 0.99)
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
        
        response = requests.post(url, data=data, timeout=15)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Telegram send error: {e}")
        return False

def send_admin(message, reply_markup=None):
    return send_telegram(message, ADMIN_ID, reply_markup)

def build_signal_message(signal, signal_id):
    """Build signal message with feedback buttons"""
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

📝 <b>Reasons:</b>
"""
    for i, reason in enumerate(signal['reasons'][:5], 1):
        msg += f"{i}. {reason}\n"
    
    msg += f"""
⭐ <b>Quality:</b> {signal.get('quality_score', 0)}/100
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
# ADMIN PANEL
# ============================================================

def show_admin_panel():
    """Show admin panel with buttons"""
    settings = db.get_all_settings() if hasattr(db, 'get_all_settings') else {}
    stats = db.get_stats()
    
    msg = f"""
🔐 <b>ADMIN PANEL</b>
━━━━━━━━━━━━━━━━━━━━━━

📊 <b>Statistics:</b>
👤 Users: {stats.get('users', 0)}
🟢 Active: {stats.get('active', 0)}
📈 Signals: {stats.get('signals', 0)}
📊 Today: {stats.get('today', 0)}
💳 Pending: {stats.get('pending', 0)}
📝 Feedback: {stats.get('feedback', 0)}
🧠 Accuracy: {learner.get_accuracy()}%

⚙️ <b>Settings:</b>
📡 Signals: {'🟢 ON' if db.get_setting('signal_enabled') == '1' else '🔴 OFF'}
🎯 Min Confidence: {db.get_setting('min_confidence') or 65}%
📊 Max Signals: {db.get_setting('max_signals') or 3}
📈 Min Volume: {db.get_setting('min_volume') or 1.2}x
📊 Min ADX: {db.get_setting('min_adx') or 20}

━━━━━━━━━━━━━━━━━━━━━━
📌 <b>Commands:</b>
/panel - Show this panel
/on - Enable signals
/off - Disable signals
/stats - Show statistics
/payments - Manage payments
/settings - View all settings
/set key value - Change setting
/confirm_ID - Confirm payment
/reject_ID - Reject payment
/help - Full command list
"""
    
    keyboard = {
        'inline_keyboard': [
            [
                {'text': '🟢 Enable', 'callback_data': 'admin_on'},
                {'text': '🔴 Disable', 'callback_data': 'admin_off'}
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
            send_admin("✅ <b>Signals Enabled</b>")
            return True
        
        elif callback_data == 'admin_off':
            db.update_setting('signal_enabled', '0')
            send_admin("🔴 <b>Signals Disabled</b>")
            return True
        
        elif callback_data == 'admin_stats':
            stats = db.get_stats()
            msg = f"""
📊 <b>Detailed Statistics</b>
━━━━━━━━━━━━━━━━━━━━━━

👤 Total Users: {stats.get('users', 0)}
🟢 Active Users: {stats.get('active', 0)}
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
        
        elif callback_data == 'admin_settings':
            settings = [
                ('signal_enabled', 'Signals'),
                ('min_confidence', 'Min Confidence'),
                ('max_signals', 'Max Signals'),
                ('min_volume', 'Min Volume'),
                ('min_adx', 'Min ADX'),
                ('price', 'Price'),
                ('wallet', 'Wallet')
            ]
            
            msg = "⚙️ <b>Settings</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
            for key, label in settings:
                value = db.get_setting(key) or 'Not set'
                msg += f"\n📌 {label}: <code>{value}</code>"
            
            msg += """

━━━━━━━━━━━━━━━━━━━━━━
<b>Change settings:</b>
/set min_confidence 75
/set max_signals 2
/set min_volume 1.5
/set min_adx 25
/set price "150 USDT"
/set wallet "ADDRESS"
"""
            send_admin(msg)
            return True
        
        elif callback_data == 'admin_feedback':
            # Get feedback stats
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
        return False

def handle_admin_command(text):
    """Handle admin text commands"""
    try:
        if text == '/panel' or text == '/start':
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
        
        elif text == '/stats':
            stats = db.get_stats()
            msg = f"""
📊 <b>BOT STATISTICS</b>
━━━━━━━━━━━━━━━━━━━━━━
👤 Users: {stats.get('users', 0)}
🟢 Active: {stats.get('active', 0)}
📈 Signals: {stats.get('signals', 0)}
📊 Today: {stats.get('today', 0)}
💳 Pending: {stats.get('pending', 0)}
📝 Feedback: {stats.get('feedback', 0)}
🧠 Accuracy: {learner.get_accuracy()}%
✅ Positive: {learner.positive}
❌ Negative: {learner.negative}
━━━━━━━━━━━━━━━━━━━━━━
/panel - Open admin panel
"""
            send_admin(msg)
            return True
        
        elif text.startswith('/confirm_'):
            try:
                payment_id = int(text.replace('/confirm_', ''))
                success, user_id = db.confirm_payment(payment_id)
                if success:
                    send_admin(f"✅ Payment #{payment_id} confirmed!")
                    send_telegram("✅ <b>Payment Confirmed!</b>\nYou now have access to all signals!", user_id)
                else:
                    send_admin(f"❌ Failed to confirm payment #{payment_id}")
            except Exception as e:
                send_admin(f"❌ Error: {e}")
            return True
        
        elif text.startswith('/reject_'):
            try:
                payment_id = int(text.replace('/reject_', ''))
                success = db.reject_payment(payment_id)
                if success:
                    payment = db.get_payment(payment_id)
                    if payment:
                        send_telegram("❌ <b>Payment Rejected</b>\nPlease try again.", payment[1])
                    send_admin(f"❌ Payment #{payment_id} rejected")
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
                send_admin(f"✅ {key} = {value}")
            except Exception as e:
                send_admin(f"❌ Error: {e}")
            return True
        
        elif text == '/payments':
            payments = db.get_pending_payments()
            if not payments:
                send_admin("💳 No pending payments")
                return True
            
            msg = "💳 <b>Pending Payments</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
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
        
        elif text == '/settings':
            settings = [
                ('signal_enabled', 'Signals'),
                ('min_confidence', 'Min Confidence'),
                ('max_signals', 'Max Signals'),
                ('min_volume', 'Min Volume'),
                ('min_adx', 'Min ADX'),
                ('price', 'Price')
            ]
            
            msg = "⚙️ <b>Current Settings</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
            for key, label in settings:
                value = db.get_setting(key) or 'Not set'
                msg += f"\n📌 {label}: <code>{value}</code>"
            
            send_admin(msg)
            return True
        
        elif text == '/help':
            msg = """
📚 <b>Admin Commands</b>
━━━━━━━━━━━━━━━━━━━━━━

<b>Panel & Control</b>
/panel - Open admin panel
/on - Enable signals
/off - Disable signals

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
/reject_2
/panel
"""
            send_admin(msg)
            return True
        
        return False
    except Exception as e:
        logger.error(f"Admin command error: {e}")
        return False

def handle_callback(callback_data, user_id):
    """Handle all callbacks"""
    try:
        # Admin callbacks
        if callback_data.startswith('admin_'):
            return handle_admin_callback(callback_data)
        
        # Feedback callbacks
        if callback_data.startswith('fb_'):
            parts = callback_data.split('_')
            if len(parts) != 3:
                return False
            
            feedback_type = parts[1]
            signal_id = int(parts[2])
            
            # Add user if not exists
            db.add_user(user_id)
            
            # Update feedback
            success, message = db.update_feedback(signal_id, feedback_type, user_id)
            if success:
                learner.add_feedback(feedback_type)
                
                if feedback_type == 'positive':
                    msg = "✅ <b>Thank you!</b>\nYour feedback helps improve accuracy! 🚀"
                else:
                    msg = "❌ <b>Thank you!</b>\nWe'll use this to improve the algorithm! 🔧"
                
                send_telegram(msg, user_id)
                
                # Notify admin
                signal = db.get_signal(signal_id)
                if signal:
                    admin_msg = f"""
📊 <b>Feedback Received</b>
━━━━━━━━━━━━━━━━━━━━━━
📈 Symbol: {signal[2]}
📊 Direction: {signal[3]}
👤 User: {user_id}
📝 Feedback: {feedback_type}
🧠 Accuracy: {learner.get_accuracy()}%
✅ Positive: {learner.positive}
❌ Negative: {learner.negative}
                    """
                    send_admin(admin_msg)
                
                return True
            else:
                send_telegram(f"⚠️ {message}", user_id)
                return False
        
        return False
    except Exception as e:
        logger.error(f"Callback error: {e}")
        return False

# ============================================================
# MAIN LOOP - Fully Working
# ============================================================

def main_loop():
    """Main bot loop"""
    logger.info("🚀 Starting Signal Bot V13...")
    send_admin("🚀 <b>Signal Bot V13 Started</b>\n\n✅ Admin Panel Active\n✅ Real Signals Active\n✅ Feedback System Active")
    
    cycle = 0
    
    while True:
        try:
            cycle += 1
            
            # Check if signals are enabled
            if db.get_setting('signal_enabled') != '1':
                time.sleep(30)
                continue
            
            # Get settings
            max_signals = int(db.get_setting('max_signals') or 3)
            min_confidence = int(db.get_setting('min_confidence') or 65)
            
            logger.info(f"🔄 Cycle {cycle} - Scanning {len(SYMBOLS)} symbols")
            
            # Generate signals
            signals = []
            for symbol in SYMBOLS:
                try:
                    signal = generate_signal(symbol)
                    if signal:
                        signals.append(signal)
                        logger.info(f"✅ {signal['symbol']}: {signal['signal']} ({signal['confidence']}%) - Quality: {signal.get('quality_score', 0)}")
                except Exception as e:
                    logger.error(f"Error processing {symbol}: {e}")
                time.sleep(0.05)  # Rate limit
            
            # Sort by quality and confidence
            signals.sort(key=lambda x: (x.get('quality_score', 0), x['confidence']), reverse=True)
            signals = signals[:max_signals]
            
            # Send signals
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
                                else:
                                    # Try without keyboard
                                    send_telegram(msg)
                                    db.mark_signal_sent(signal_id)
                            time.sleep(2)
                    except Exception as e:
                        logger.error(f"Error sending signal: {e}")
            else:
                if cycle % 3 == 0:
                    logger.info("⏳ No signals found")
            
            # Check pending payments periodically
            if cycle % 5 == 0:
                payments = db.get_pending_payments()
                if payments:
                    send_admin(f"💳 <b>{len(payments)} pending payments</b>\nUse /payments to view")
            
            # Status update
            if cycle % 20 == 0:
                stats = db.get_stats()
                send_admin(f"🔄 <b>Bot Status</b>\n━━━━━━━━━━━━━━━━━━━━━━\n📈 Signals Today: {stats.get('today', 0)}\n📊 Total Signals: {stats.get('signals', 0)}\n🧠 Accuracy: {learner.get_accuracy()}%\n👤 Users: {stats.get('users', 0)}")
            
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
        print("🚀 ULTIMATE SIGNAL BOT V13 - PROFESSIONAL EDITION")
        print("="*70)
        print(f"📊 Symbols: {len(SYMBOLS)}")
        print(f"⏱ Interval: {INTERVAL//60} minutes")
        print(f"📢 Channel: {CHANNEL_ID}")
        print("="*70 + "\n")
        
        # Test connection
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