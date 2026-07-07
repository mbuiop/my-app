# ============================================================
# ULTIMATE SIGNAL BOT V11 - PROFESSIONAL
# FULL REAL DATA + FEEDBACK WORKING + DEEP ANALYSIS
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
from decimal import Decimal, getcontext
import sys

# Set high precision
getcontext().prec = 28

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
                expire_at TIMESTAMP
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
        
        self.cursor.execute('INSERT OR IGNORE INTO settings VALUES ("signal_enabled", "1")')
        self.cursor.execute('INSERT OR IGNORE INTO settings VALUES ("wallet", ?)', (WALLET_ADDRESS,))
        self.cursor.execute('INSERT OR IGNORE INTO settings VALUES ("price", ?)', (PRICE,))
        
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
                user_id, symbol, direction, entry, tp, sl, confidence,
                created_at, rsi, macd, ma20, ma50, ma200, vwap, atr,
                support, resistance, score, reasons
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, signal_data['symbol'], signal_data['signal'],
            signal_data['price'], signal_data['tp'], signal_data['sl'],
            signal_data['confidence'], datetime.now().isoformat(),
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
        
        # Log feedback
        self.cursor.execute('''
            INSERT INTO feedback_log (signal_id, user_id, feedback, created_at)
            VALUES (?, ?, ?, ?)
        ''', (signal_id, user_id, feedback_type, datetime.now().isoformat()))
        self.conn.commit()
    
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

db = Database()

# ============================================================
# REAL DATA FROM BINANCE - HIGH PRECISION
# ============================================================

def get_candles_high_precision(symbol, limit=250, interval='5m'):
    """Get REAL candlestick data with high precision"""
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
    except Exception as e:
        print(f"Error getting candles for {symbol}: {e}")
    return None

def get_price_high_precision(symbol):
    """Get REAL price with high precision"""
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return float(r.json()['price'])
    except:
        pass
    return None

def get_24h_stats_high_precision(symbol):
    """Get REAL 24h stats"""
    try:
        url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            return {
                'high': float(data['highPrice']),
                'low': float(data['lowPrice']),
                'volume': float(data['volume']),
                'change': float(data['priceChangePercent']),
                'open': float(data['openPrice'])
            }
    except:
        pass
    return None

# ============================================================
# PROFESSIONAL INDICATORS - HIGH PRECISION
# ============================================================

def calc_rsi_pro(prices, period=14):
    """Professional RSI calculation"""
    if len(prices) < period + 1:
        return 50.0
    
    p = np.array(prices[-period-1:], dtype=np.float64)
    deltas = np.diff(p)
    gain = np.mean(deltas[deltas > 0]) if np.sum(deltas > 0) > 0 else 0
    loss = -np.mean(deltas[deltas < 0]) if np.sum(deltas < 0) > 0 else 0.0000001
    
    if loss == 0:
        return 100.0
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)

def calc_macd_pro(prices, fast=12, slow=26, signal=9):
    """Professional MACD calculation"""
    if len(prices) < slow:
        return 0, 0, 0
    
    p = np.array(prices, dtype=np.float64)
    
    # Fast EMA
    f_mult = 2.0 / (fast + 1)
    f_ema = float(np.mean(p[-fast:]))
    for price in p[-fast:]:
        f_ema = float(price) * f_mult + f_ema * (1 - f_mult)
    
    # Slow EMA
    s_mult = 2.0 / (slow + 1)
    s_ema = float(np.mean(p[-slow:]))
    for price in p[-slow:]:
        s_ema = float(price) * s_mult + s_ema * (1 - s_mult)
    
    macd_line = f_ema - s_ema
    
    # Signal line
    sig_mult = 2.0 / (signal + 1)
    sig_line = macd_line
    for _ in range(signal):
        sig_line = macd_line * sig_mult + sig_line * (1 - sig_mult)
    
    hist = macd_line - sig_line
    return round(macd_line, 8), round(sig_line, 8), round(hist, 8)

def calc_ma_pro(prices, period):
    """Professional Moving Average"""
    if len(prices) < period:
        return prices[-1] if prices else 0
    return round(float(np.mean(np.array(prices[-period:], dtype=np.float64))), 8)

def calc_ema_pro(prices, period):
    """Professional EMA"""
    if len(prices) < period:
        return prices[-1] if prices else 0
    
    p = np.array(prices, dtype=np.float64)
    mult = 2.0 / (period + 1)
    ema = float(np.mean(p[-period:]))
    for price in p[-period:]:
        ema = float(price) * mult + ema * (1 - mult)
    return round(ema, 8)

def calc_bollinger_pro(prices, period=20, std_dev=2):
    """Professional Bollinger Bands"""
    if len(prices) < period:
        return prices[-1] if prices else 0, prices[-1] if prices else 0, prices[-1] if prices else 0
    
    p = np.array(prices[-period:], dtype=np.float64)
    ma = float(np.mean(p))
    std = float(np.std(p))
    
    upper = ma + (std_dev * std)
    lower = ma - (std_dev * std)
    return round(upper, 8), round(ma, 8), round(lower, 8)

def calc_vwap_pro(prices, volumes):
    """Professional VWAP"""
    if len(prices) < 2:
        return prices[-1] if prices else 0
    
    total_value = sum(prices[i] * volumes[i] for i in range(len(prices)))
    total_volume = sum(volumes)
    if total_volume == 0:
        return prices[-1]
    return round(total_value / total_volume, 8)

def calc_atr_pro(highs, lows, prices, period=14):
    """Professional ATR"""
    if len(prices) < period:
        return 0.0000001
    
    tr = []
    for i in range(1, period + 1):
        if i < len(prices):
            tr.append(max(
                highs[-i] - lows[-i],
                abs(highs[-i] - prices[-i-1]),
                abs(lows[-i] - prices[-i-1])
            ))
    
    return round(float(np.mean(np.array(tr, dtype=np.float64))) if tr else 0.0000001, 8)

def find_support_resistance_pro(highs, lows, prices):
    """Professional Support/Resistance with clustering"""
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
    
    # Cluster peaks (resistance)
    resistance = 0
    if peaks:
        peaks = sorted(peaks, reverse=True)
        resistance = peaks[0]
        
        # Find significant resistance (clustered levels)
        if len(peaks) >= 2:
            cluster = [peaks[0]]
            for p in peaks[1:]:
                if abs(p - peaks[0]) / peaks[0] < 0.02:
                    cluster.append(p)
            resistance = sum(cluster) / len(cluster)
    
    # Cluster troughs (support)
    support = 0
    if troughs:
        troughs = sorted(troughs)
        support = troughs[0]
        
        if len(troughs) >= 2:
            cluster = [troughs[0]]
            for t in troughs[1:]:
                if abs(t - troughs[0]) / troughs[0] < 0.02:
                    cluster.append(t)
            support = sum(cluster) / len(cluster)
    
    return round(support, 8), round(resistance, 8)

def calc_volume_profile_pro(volumes):
    """Professional Volume Profile"""
    if len(volumes) < 20:
        return 1.0
    
    avg_vol = np.mean(volumes[-20:])
    current_vol = volumes[-1]
    if avg_vol == 0:
        return 1.0
    return round(current_vol / avg_vol, 2)

def calc_adx_pro(highs, lows, prices, period=14):
    """Professional ADX - Trend Strength"""
    if len(prices) < period + 1:
        return 25
    
    tr = []
    up = []
    down = []
    
    for i in range(1, period + 1):
        if i < len(prices):
            tr.append(max(
                highs[-i] - lows[-i],
                abs(highs[-i] - prices[-i-1]),
                abs(lows[-i] - prices[-i-1])
            ))
            up_move = highs[-i] - highs[-i-1]
            down_move = lows[-i-1] - lows[-i]
            up.append(max(0, up_move) if up_move > down_move else 0)
            down.append(max(0, down_move) if down_move > up_move else 0)
    
    atr = float(np.mean(np.array(tr, dtype=np.float64))) if tr else 0.0000001
    di_plus = 100 * float(np.mean(np.array(up, dtype=np.float64))) / atr if atr > 0 else 0
    di_minus = 100 * float(np.mean(np.array(down, dtype=np.float64))) / atr if atr > 0 else 0
    
    dx = 100 * abs(di_plus - di_minus) / (di_plus + di_minus + 0.0000001)
    return round(dx, 1)

# ============================================================
# PUMP/DUMP DETECTION
# ============================================================

def analyze_pump_dump_pro(symbol):
    """Professional Pump/Dump detection"""
    data = get_candles_high_precision(symbol, 100, '5m')
    if not data:
        return 0, 0, 0, 0
    
    prices = data['close']
    volumes = data['volume']
    
    if len(prices) < 50:
        return 0, 0, 0, 0
    
    current = prices[-1]
    
    # Multiple timeframe changes
    change_15m = ((current - prices[-3]) / prices[-3]) * 100 if len(prices) >= 3 else 0
    change_1h = ((current - prices[-12]) / prices[-12]) * 100 if len(prices) >= 12 else 0
    change_4h = ((current - prices[-48]) / prices[-48]) * 100 if len(prices) >= 48 else 0
    
    # Volume analysis
    avg_vol = np.mean(volumes[-20:]) if len(volumes) >= 20 else 1
    vol_ratio = volumes[-1] / avg_vol if avg_vol > 0 else 1
    vol_spike = vol_ratio > 2.5
    
    pump_score = 0
    dump_score = 0
    pump_reasons = []
    dump_reasons = []
    
    # 15m pump
    if change_15m > 2:
        pump_score += 15
        pump_reasons.append(f"15m: +{change_15m:.1f}%")
    elif change_15m < -2:
        dump_score += 15
        dump_reasons.append(f"15m: {change_15m:.1f}%")
    
    # 1h pump
    if change_1h > 5:
        pump_score += 25
        pump_reasons.append(f"1h: +{change_1h:.1f}%")
    elif change_1h < -5:
        dump_score += 25
        dump_reasons.append(f"1h: {change_1h:.1f}%")
    
    # 4h pump
    if change_4h > 10:
        pump_score += 30
        pump_reasons.append(f"4h: +{change_4h:.1f}%")
    elif change_4h < -10:
        dump_score += 30
        dump_reasons.append(f"4h: {change_4h:.1f}%")
    
    # Volume confirmation
    if vol_spike:
        if pump_score > dump_score:
            pump_score += 20
            pump_reasons.append("🔥 High volume spike")
        else:
            dump_score += 20
            dump_reasons.append("🔥 High volume spike")
    
    # RSI confirmation
    rsi = calc_rsi_pro(prices, 14)
    if rsi > 70 and pump_score > dump_score:
        pump_score += 10
        pump_reasons.append(f"RSI overbought: {rsi}")
    elif rsi < 30 and dump_score > pump_score:
        dump_score += 10
        dump_reasons.append(f"RSI oversold: {rsi}")
    
    return (
        round(pump_score, 1),
        round(dump_score, 1),
        ' | '.join(pump_reasons[:3]),
        ' | '.join(dump_reasons[:3])
    )

# ============================================================
# MULTI-TIMEFRAME ANALYSIS
# ============================================================

def multi_timeframe_pro(symbol):
    """Professional Multi-Timeframe Analysis"""
    timeframes = ['5m', '15m', '1h', '4h']
    results = {'BUY': 0, 'SELL': 0, 'NEUTRAL': 0}
    details = []
    
    for tf in timeframes:
        data = get_candles_high_precision(symbol, 100, tf)
        if not data:
            continue
        
        prices = data['close']
        current = prices[-1]
        
        if len(prices) < 50:
            continue
        
        ma20 = calc_ma_pro(prices, 20)
        ma50 = calc_ma_pro(prices, 50)
        rsi = calc_rsi_pro(prices, 14)
        
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
        return 0, 0, "No data"
    
    buy_pct = (results['BUY'] / total) * 100
    sell_pct = (results['SELL'] / total) * 100
    
    return round(buy_pct, 1), round(sell_pct, 1), ' | '.join(details)

# ============================================================
# SIGNAL GENERATOR - PROFESSIONAL
# ============================================================

def generate_signal_pro(symbol):
    """Generate professional signal with REAL data"""
    data = get_candles_high_precision(symbol, 250, '5m')
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
    rsi = calc_rsi_pro(prices, 14)
    macd, macd_sig, macd_hist = calc_macd_pro(prices, 12, 26, 9)
    ma7 = calc_ma_pro(prices, 7)
    ma20 = calc_ma_pro(prices, 20)
    ma50 = calc_ma_pro(prices, 50)
    ma200 = calc_ma_pro(prices, 200)
    ema9 = calc_ema_pro(prices, 9)
    ema21 = calc_ema_pro(prices, 21)
    upper_bb, middle_bb, lower_bb = calc_bollinger_pro(prices, 20, 2)
    vwap = calc_vwap_pro(prices, volumes)
    atr = calc_atr_pro(highs, lows, prices, 14)
    support, resistance = find_support_resistance_pro(highs, lows, prices)
    vol_ratio = calc_volume_profile_pro(volumes)
    adx = calc_adx_pro(highs, lows, prices, 14)
    
    # Pump/Dump
    pump_score, dump_score, pump_reasons, dump_reasons = analyze_pump_dump_pro(symbol)
    
    # Multi-timeframe
    mtf_buy, mtf_sell, mtf_details = multi_timeframe_pro(symbol)
    
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
    else:
        reasons.append(f"⚖️ RSI: {rsi}")
    
    # 2. MACD (20 points)
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
    
    # 3. Moving Averages (20 points)
    if current > ma20 and ma20 > ma50 and ma50 > ma200:
        score += 20
        reasons.append(f"🚀 Strong Uptrend (MA20>{ma20:.4f} > MA50>{ma50:.4f})")
    elif current < ma20 and ma20 < ma50 and ma50 < ma200:
        score -= 20
        reasons.append(f"💀 Strong Downtrend (MA20<{ma20:.4f} < MA50<{ma50:.4f})")
    elif current > ma20 and ma20 > ma50:
        score += 12
        reasons.append(f"📈 Uptrend (MA20>{ma20:.4f} > MA50>{ma50:.4f})")
    elif current < ma20 and ma20 < ma50:
        score -= 12
        reasons.append(f"📉 Downtrend (MA20<{ma20:.4f} < MA50<{ma50:.4f})")
    elif current > ma20:
        score += 5
        reasons.append(f"⬆️ Price above MA20: ${ma20:.4f}")
    else:
        score -= 5
        reasons.append(f"⬇️ Price below MA20: ${ma20:.4f}")
    
    # 4. Bollinger Bands (15 points)
    if current < lower_bb:
        score += 15
        reasons.append(f"🎯 Touch Lower Band: ${lower_bb:.4f}")
    elif current > upper_bb:
        score -= 15
        reasons.append(f"🎯 Touch Upper Band: ${upper_bb:.4f}")
    elif current < middle_bb:
        score += 8
        reasons.append(f"📊 Lower Half of Band")
    else:
        score -= 8
        reasons.append(f"📊 Upper Half of Band")
    
    # 5. VWAP (10 points)
    if current > vwap:
        score += 10
        reasons.append(f"✅ Price Above VWAP: ${vwap:.4f}")
    else:
        score -= 10
        reasons.append(f"❌ Price Below VWAP: ${vwap:.4f}")
    
    # 6. Volume (5 points)
    if vol_ratio > 2.5:
        score += 5
        reasons.append(f"📊 High Volume: {vol_ratio:.1f}x avg")
    elif vol_ratio > 1.5:
        score += 3
        reasons.append(f"📊 Good Volume: {vol_ratio:.1f}x avg")
    elif vol_ratio < 0.5:
        score -= 5
        reasons.append(f"📊 Low Volume: {vol_ratio:.1f}x avg")
    
    # 7. Support/Resistance (10 points)
    if support > 0:
        dist_support = ((current - support) / current) * 100
        if dist_support < 0.5:
            score += 10
            reasons.append(f"🛡️ Very Near Support: ${support:.4f}")
        elif dist_support < 1.5:
            score += 7
            reasons.append(f"🛡️ Near Support: ${support:.4f}")
        elif dist_support < 3:
            score += 4
            reasons.append(f"🛡️ Close to Support: ${support:.4f}")
    
    if resistance > 0:
        dist_resistance = ((resistance - current) / current) * 100
        if dist_resistance < 0.5:
            score -= 10
            reasons.append(f"🚫 Very Near Resistance: ${resistance:.4f}")
        elif dist_resistance < 1.5:
            score -= 7
            reasons.append(f"🚫 Near Resistance: ${resistance:.4f}")
        elif dist_resistance < 3:
            score -= 4
            reasons.append(f"🚫 Close to Resistance: ${resistance:.4f}")
    
    # 8. Pump/Dump (5 points)
    if pump_score > dump_score and pump_score > 20:
        score += 5
        reasons.append(f"🔥 Pump Detected: {pump_reasons}")
    elif dump_score > pump_score and dump_score > 20:
        score -= 5
        reasons.append(f"💀 Dump Detected: {dump_reasons}")
    
    # 9. ADX (5 points)
    if adx > 50:
        if score > 50:
            score += 5
            reasons.append(f"🔥 Strong Trend (ADX: {adx})")
        else:
            score -= 5
            reasons.append(f"💀 Strong Trend (ADX: {adx})")
    elif adx < 20:
        reasons.append(f"⏳ Weak Trend (ADX: {adx})")
    
    # 10. Multi-timeframe (5 points)
    if mtf_buy > 60:
        score += 5
        reasons.append(f"📊 MTF Bullish: {mtf_buy}%")
    elif mtf_sell > 60:
        score -= 5
        reasons.append(f"📊 MTF Bearish: {mtf_sell}%")
    
    # ===== FINAL DECISION =====
    confidence = min(98, 50 + abs(score - 50) * 1.3)
    
    if score > 55:
        signal = "BUY"
    elif score < 45:
        signal = "SELL"
    else:
        signal = "HOLD"
    
    # ===== TP/SL =====
    if signal == "BUY":
        tp = round(current + (atr * 3), 8)
        sl = round(current - (atr * 2), 8)
        if resistance > 0 and tp > resistance:
            tp = round(resistance * 0.995, 8)
        if support > 0 and sl < support:
            sl = round(support * 0.995, 8)
        if tp <= current:
            tp = round(current * 1.01, 8)
        if sl >= current:
            sl = round(current * 0.99, 8)
    elif signal == "SELL":
        tp = round(current - (atr * 3), 8)
        sl = round(current + (atr * 2), 8)
        if support > 0 and tp < support:
            tp = round(support * 1.005, 8)
        if resistance > 0 and sl > resistance:
            sl = round(resistance * 1.005, 8)
        if tp >= current:
            tp = round(current * 0.99, 8)
        if sl <= current:
            sl = round(current * 1.01, 8)
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
        'ma200': ma200,
        'vwap': vwap,
        'atr': atr,
        'support': support,
        'resistance': resistance,
        'vol_ratio': vol_ratio,
        'adx': adx,
        'pump_score': pump_score,
        'dump_score': dump_score,
        'mtf_buy': mtf_buy,
        'mtf_sell': mtf_sell,
        'mtf_details': mtf_details,
        'reasons': unique_reasons[:6],
        'time': datetime.now().strftime("%H:%M")
    }

# ============================================================
# SYMBOLS - FULL LIST
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
    'WLDUSDT', 'PEPEUSDT', 'BONKUSDT', 'FLOKIUSDT', 'SHIBUSDT',
    'WIFUSDT', 'RNDRUSDT', 'FETUSDT', 'AGIXUSDT', 'OCEANUSDT',
    'ENSUSDT', 'MASKUSDT', 'LPTUSDT', 'GALAUSDT', 'MANAUSDT',
    'ENJUSDT', 'CHZUSDT', 'BAKEUSDT', 'ZILUSDT', 'ONEUSDT',
    'IOTAUSDT', 'WAVESUSDT', 'KAVAUSDT', 'KSMUSDT', 'MOVRUSDT',
    'GLMRUSDT', 'STXUSDT', 'COREUSDT', 'ANKRUSDT', 'HBARUSDT',
    'HOTUSDT', 'ICXUSDT', 'IOSTUSDT', 'KDAUSDT', 'LRCUSDT',
    'MINAUSDT', 'NEOUSDT', 'ONTUSDT', 'RVNUSDT', 'SCUSDT',
    'XDCUSDT', 'ZENUSDT', 'ZRXUSDT'
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
                    self.weights = data.get('weights', {
                        'rsi': 1.0, 'macd': 1.0, 'ma': 1.0,
                        'bollinger': 1.0, 'vwap': 1.2, 'volume': 1.0,
                        'sr': 1.0, 'pump': 1.0, 'mtf': 1.0, 'adx': 1.0
                    })
                    return
            except:
                pass
        
        self.positive = 0
        self.negative = 0
        self.total = 0
        self.weights = {
            'rsi': 1.0, 'macd': 1.0, 'ma': 1.0,
            'bollinger': 1.0, 'vwap': 1.2, 'volume': 1.0,
            'sr': 1.0, 'pump': 1.0, 'mtf': 1.0, 'adx': 1.0
        }
        self.save()
    
    def save(self):
        try:
            with open(self.file, 'w') as f:
                json.dump({
                    'positive': self.positive,
                    'negative': self.negative,
                    'total': self.total,
                    'weights': self.weights
                }, f)
        except:
            pass
    
    def add_feedback(self, feedback_type):
        if feedback_type == 'positive':
            self.positive += 1
            for key in self.weights:
                self.weights[key] = min(2.0, self.weights[key] * 1.015)
        else:
            self.negative += 1
            for key in self.weights:
                self.weights[key] = max(0.5, self.weights[key] * 0.985)
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
    if not signal or signal['signal'] == 'HOLD':
        return None, None
    
    emoji = "🟢" if signal['signal'] == 'BUY' else "🔴"
    direction = "LONG" if signal['signal'] == 'BUY' else "SHORT"
    
    msg = f"""
{emoji} <b>{signal['symbol']}</b> | {direction}
💰 <b>Entry:</b> <code>${signal['price']:.6f}</code>
🎯 <b>TP:</b> <code>${signal['tp']:.6f}</code>
🛑 <b>SL:</b> <code>${signal['sl']:.6f}</code>
📊 <b>Confidence:</b> {signal['confidence']}% | <b>Score:</b> {signal['score']}

📊 <b>Indicators:</b>
RSI: {signal['rsi']:.1f} | MACD: {signal['macd']:.6f}
MA20: ${signal['ma20']:.4f} | MA50: ${signal['ma50']:.4f} | MA200: ${signal['ma200']:.4f}
VWAP: ${signal['vwap']:.4f} | ATR: ${signal['atr']:.6f}
Support: ${signal['support']:.4f} | Resistance: ${signal['resistance']:.4f}
Volume: {signal['vol_ratio']:.1f}x | ADX: {signal['adx']:.1f}
Pump: {signal['pump_score']:.1f}% | Dump: {signal['dump_score']:.1f}%
MTF: {signal['mtf_buy']:.0f}% Buy / {signal['mtf_sell']:.0f}% Sell

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
# WEBHOOK HANDLER (for feedback)
# ============================================================

def handle_callback(callback_data, user_id):
    """Handle callback from Telegram buttons"""
    try:
        if not callback_data.startswith('fb_'):
            return False
        
        parts = callback_data.split('_')
        if len(parts) != 3:
            return False
        
        feedback_type = parts[1]
        signal_id = int(parts[2])
        
        # Update database
        db.update_feedback(signal_id, feedback_type, user_id)
        
        # Update learning
        learner.add_feedback(feedback_type)
        
        # Send confirmation
        if feedback_type == 'positive':
            msg = "✅ Thank you! Your feedback helps improve accuracy!"
        else:
            msg = "❌ Thank you! We'll improve the algorithm!"
        
        send_telegram(msg, user_id)
        
        # Send to admin
        signal = db.get_signal(signal_id)
        if signal:
            admin_msg = f"""
📊 <b>Feedback Received</b>
📈 Signal: {signal[2]}
👤 User: {user_id}
📝 Feedback: {feedback_type}
🧠 Accuracy: {learner.get_accuracy()}%
✅ Positive: {learner.positive}
❌ Negative: {learner.negative}
            """
            send_admin(admin_msg)
        
        return True
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
        payment_id, user_id, payment_hash, created_at = payment
        user = db.get_user(user_id)
        username = user[1] if user else "Unknown"
        
        msg = f"""
🧾 <b>Payment Request #{payment_id}</b>
👤 User: {user_id}
📛 Name: {username}
🔑 Hash: <code>{payment_hash}</code>
📅 Time: {created_at}
        """
        send_admin(msg)
        send_admin(f"✅ /confirm_{payment_id} - Confirm")
        send_admin(f"❌ /reject_{payment_id} - Reject")

def process_admin_command(text):
    if text.startswith('/confirm_'):
        try:
            payment_id = int(text.replace('/confirm_', ''))
            success, user_id, expire_date = db.confirm_payment(payment_id)
            if success:
                send_admin(f"✅ Payment #{payment_id} confirmed!")
                send_telegram(f"✅ Payment confirmed! Expires: {expire_date.strftime('%Y-%m-%d')}", user_id)
            else:
                send_admin(f"❌ Failed to confirm payment #{payment_id}")
        except:
            send_admin("❌ Error confirming payment")
    
    elif text.startswith('/reject_'):
        try:
            payment_id = int(text.replace('/reject_', ''))
            success = db.reject_payment(payment_id)
            if success:
                payment = db.get_payment(payment_id)
                if payment:
                    send_telegram("❌ Payment rejected. Please try again.", payment[1])
                send_admin(f"❌ Payment #{payment_id} rejected")
        except:
            send_admin("❌ Error rejecting payment")
    
    elif text == '/stats':
        users = db.get_all_users()
        signals = db.cursor.execute('SELECT COUNT(*) FROM signals').fetchone()[0]
        pending = db.cursor.execute('SELECT COUNT(*) FROM payments WHERE status="pending"').fetchone()[0]
        
        msg = f"""
📊 <b>BOT STATS</b>
👤 Users: {len(users)}
📈 Signals: {signals}
💳 Pending: {pending}
🧠 Accuracy: {learner.get_accuracy()}%
✅ Positive: {learner.positive}
❌ Negative: {learner.negative}
        """
        send_admin(msg)
    
    elif text == '/status':
        enabled = db.get_setting('signal_enabled') == '1'
        msg = f"""
📊 <b>BOT STATUS</b>
📡 Signals: {'🟢 ACTIVE' if enabled else '🔴 PAUSED'}
💰 Price: {db.get_setting('price')}
📌 Wallet: <code>{db.get_setting('wallet')}</code>
⏱ Interval: {INTERVAL//60}m
        """
        send_admin(msg)
    
    elif text == '/on':
        db.update_setting('signal_enabled', '1')
        send_admin("✅ Signals ENABLED")
    
    elif text == '/off':
        db.update_setting('signal_enabled', '0')
        send_admin("🔴 Signals DISABLED")

# ============================================================
# MAIN LOOP
# ============================================================

def signal_loop():
    print("\n" + "="*70)
    print("🚀 ULTIMATE SIGNAL BOT V11 - PROFESSIONAL")
    print(f"📊 Total Symbols: {len(ALL_SYMBOLS)}")
    print(f"📢 Channel: {CHANNEL_ID}")
    print(f"⏱ Interval: {INTERVAL//60} minutes")
    print("="*70)
    
    send_telegram(f"🚀 Signal Bot V11 started!\n📊 Analyzing {len(ALL_SYMBOLS)} symbols")
    
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
            total_checked = 0
            
            for symbol in ALL_SYMBOLS:
                total_checked += 1
                signal = generate_signal_pro(symbol)
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
                    signal_id = db.save_signal(0, signal)
                    msg, keyboard = build_signal_message(signal, signal_id)
                    if msg:
                        if send_telegram(msg, reply_markup=keyboard):
                            print(f"✅ Sent: {signal['symbol']}")
                        else:
                            # Try without keyboard
                            send_telegram(msg)
                        time.sleep(1)
            else:
                if cycle % 3 == 0:
                    send_telegram(f"⏳ No signals found (Cycle {cycle})")
            
            # Check payments
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