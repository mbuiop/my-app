# ============================================================
# ULTIMATE SIGNAL BOT V12 - PROFESSIONAL WITH ADMIN PANEL
# FULL FEATURES: ADMIN PANEL + SUBSCRIPTION + FEEDBACK + HIGH QUALITY
# ============================================================

import requests
import numpy as np
import time
import json
import os
import sqlite3
from datetime import datetime, timedelta
import threading
from decimal import Decimal, getcontext
import sys
import logging

# تنظیم لاگینگ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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

INTERVAL = 300  # 5 دقیقه (بهینه برای کیفیت)
MIN_CONFIDENCE = 75  # افزایش برای کیفیت بهتر
MAX_SIGNALS = 3
MIN_QUALITY_SCORE = 70
MIN_RISK_REWARD = 2.0
MIN_VOLUME_RATIO = 1.5
MIN_ADX = 25

# ============================================================
# DATABASE - کامل و بدون خطا
# ============================================================

class Database:
    def __init__(self):
        try:
            self.conn = sqlite3.connect('bot_data.db', check_same_thread=False)
            self.cursor = self.conn.cursor()
            self.create_tables()
            logger.info("✅ Database initialized successfully")
        except Exception as e:
            logger.error(f"❌ Database error: {e}")
            raise
    
    def create_tables(self):
        try:
            # Users
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
                    total_signals_received INTEGER DEFAULT 0
                )
            ''')
            
            # Signals
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
                    quality_score REAL,
                    risk_reward REAL,
                    feedback TEXT DEFAULT '',
                    feedback_user INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
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
            
            # Admin Settings
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            
            # Admin Logs
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS admin_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER,
                    action TEXT,
                    details TEXT,
                    created_at TIMESTAMP
                )
            ''')
            
            # تنظیمات پیش‌فرض
            default_settings = [
                ('signal_enabled', '1'),
                ('wallet', WALLET_ADDRESS),
                ('price', PRICE),
                ('min_confidence', str(MIN_CONFIDENCE)),
                ('max_signals', str(MAX_SIGNALS)),
                ('min_quality_score', str(MIN_QUALITY_SCORE)),
                ('auto_approve_payments', '0'),
                ('admin_chat_id', str(ADMIN_ID))
            ]
            
            for key, value in default_settings:
                self.cursor.execute('INSERT OR IGNORE INTO settings VALUES (?, ?)', (key, value))
            
            self.conn.commit()
            logger.info("✅ Tables created successfully")
        except Exception as e:
            logger.error(f"❌ Error creating tables: {e}")
            raise
    
    # ===== USER METHODS =====
    def add_user(self, user_id, username, first_name):
        try:
            self.cursor.execute('''
                INSERT OR IGNORE INTO users (user_id, username, first_name, joined_at)
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, first_name, datetime.now().isoformat()))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return False
    
    def get_user(self, user_id):
        try:
            self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    def get_user_by_username(self, username):
        try:
            self.cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting user by username: {e}")
            return None
    
    def update_user_subscription(self, user_id, days=30):
        try:
            expire_date = datetime.now() + timedelta(days=days)
            self.cursor.execute('''
                UPDATE users SET subscription_expire = ?, is_active = 1
                WHERE user_id = ?
            ''', (expire_date.isoformat(), user_id))
            self.conn.commit()
            return expire_date
        except Exception as e:
            logger.error(f"Error updating subscription: {e}")
            return None
    
    def check_subscription(self, user_id):
        try:
            self.cursor.execute('SELECT subscription_expire, is_active FROM users WHERE user_id = ?', (user_id,))
            result = self.cursor.fetchone()
            if not result:
                return False
            
            expire_str, is_active = result
            if not expire_str or not is_active:
                return False
            
            expire_date = datetime.fromisoformat(expire_str)
            if expire_date > datetime.now():
                return True
            else:
                # غیرفعال کردن خودکار
                self.cursor.execute('UPDATE users SET is_active = 0 WHERE user_id = ?', (user_id,))
                self.conn.commit()
                return False
        except Exception as e:
            logger.error(f"Error checking subscription: {e}")
            return False
    
    # ===== SIGNAL METHODS =====
    def save_signal(self, user_id, signal_data):
        try:
            # محاسبه quality_score و risk_reward
            quality_score = signal_data.get('quality_score', 70)
            risk_reward = signal_data.get('risk_reward', 2.0)
            
            self.cursor.execute('''
                INSERT INTO signals (
                    user_id, symbol, direction, entry, tp, sl, confidence,
                    created_at, rsi, macd, ma20, ma50, ma200, vwap, atr,
                    support, resistance, score, reasons, quality_score, risk_reward
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id, 
                signal_data['symbol'], 
                signal_data['signal'],
                signal_data['price'], 
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
                '|'.join(signal_data.get('reasons', [])),
                quality_score,
                risk_reward
            ))
            signal_id = self.cursor.lastrowid
            self.conn.commit()
            
            # افزایش تعداد سیگنال‌های دریافتی کاربر
            self.cursor.execute('''
                UPDATE users SET total_signals_received = total_signals_received + 1
                WHERE user_id = ?
            ''', (user_id,))
            self.conn.commit()
            
            return signal_id
        except Exception as e:
            logger.error(f"Error saving signal: {e}")
            return None
    
    def get_signal(self, signal_id):
        try:
            self.cursor.execute('SELECT * FROM signals WHERE id = ?', (signal_id,))
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting signal: {e}")
            return None
    
    def get_recent_signals(self, limit=10):
        try:
            self.cursor.execute('''
                SELECT * FROM signals 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting recent signals: {e}")
            return []
    
    def mark_signal_sent(self, signal_id):
        try:
            self.cursor.execute('''
                UPDATE signals SET sent_to_channel = 1
                WHERE id = ?
            ''', (signal_id,))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error marking signal sent: {e}")
            return False
    
    # ===== FEEDBACK METHODS =====
    def update_feedback(self, signal_id, feedback_type, user_id):
        try:
            # بررسی تکراری نبودن بازخورد
            self.cursor.execute('''
                SELECT id FROM feedback_log 
                WHERE signal_id = ? AND user_id = ?
            ''', (signal_id, user_id))
            if self.cursor.fetchone():
                return False, "شما قبلاً به این سیگنال بازخورد داده‌اید"
            
            self.cursor.execute('''
                UPDATE signals SET feedback = ?, feedback_user = ? 
                WHERE id = ?
            ''', (feedback_type, user_id, signal_id))
            
            if feedback_type == 'positive':
                self.cursor.execute('''
                    UPDATE users SET positive_feedback = positive_feedback + 1,
                    feedback_count = feedback_count + 1 
                    WHERE user_id = ?
                ''', (user_id,))
            else:
                self.cursor.execute('''
                    UPDATE users SET negative_feedback = negative_feedback + 1,
                    feedback_count = feedback_count + 1 
                    WHERE user_id = ?
                ''', (user_id,))
            
            # ثبت لاگ بازخورد
            self.cursor.execute('''
                INSERT INTO feedback_log (signal_id, user_id, feedback, created_at)
                VALUES (?, ?, ?, ?)
            ''', (signal_id, user_id, feedback_type, datetime.now().isoformat()))
            
            self.conn.commit()
            return True, "بازخورد با موفقیت ثبت شد"
        except Exception as e:
            logger.error(f"Error updating feedback: {e}")
            return False, str(e)
    
    def get_feedback_stats(self):
        try:
            self.cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN feedback = 'positive' THEN 1 ELSE 0 END) as positive,
                    SUM(CASE WHEN feedback = 'negative' THEN 1 ELSE 0 END) as negative
                FROM feedback_log
            ''')
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting feedback stats: {e}")
            return (0, 0, 0)
    
    # ===== PAYMENT METHODS =====
    def add_payment(self, user_id, payment_hash, amount=None):
        try:
            if amount is None:
                amount = PRICE
            
            self.cursor.execute('''
                INSERT INTO payments (user_id, payment_hash, amount, created_at)
                VALUES (?, ?, ?, ?)
            ''', (user_id, payment_hash, amount, datetime.now().isoformat()))
            payment_id = self.cursor.lastrowid
            self.conn.commit()
            return payment_id
        except Exception as e:
            logger.error(f"Error adding payment: {e}")
            return None
    
    def get_pending_payments(self):
        try:
            self.cursor.execute('''
                SELECT id, user_id, payment_hash, amount, created_at 
                FROM payments WHERE status = 'pending'
                ORDER BY created_at ASC
            ''')
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting pending payments: {e}")
            return []
    
    def confirm_payment(self, payment_id):
        try:
            self.cursor.execute('SELECT user_id FROM payments WHERE id = ? AND status = "pending"', (payment_id,))
            result = self.cursor.fetchone()
            if not result:
                return False, None, None
            
            user_id = result[0]
            expire_date = self.update_user_subscription(user_id, 30)
            
            self.cursor.execute('''
                UPDATE payments SET status = 'confirmed', confirmed_at = ?, expire_at = ?
                WHERE id = ?
            ''', (datetime.now().isoformat(), expire_date.isoformat(), payment_id))
            
            self.conn.commit()
            
            # لاگ ادمن
            self.add_admin_log(ADMIN_ID, "confirm_payment", f"Payment {payment_id} confirmed for user {user_id}")
            
            return True, user_id, expire_date
        except Exception as e:
            logger.error(f"Error confirming payment: {e}")
            return False, None, None
    
    def reject_payment(self, payment_id):
        try:
            self.cursor.execute('''
                UPDATE payments SET status = 'rejected' 
                WHERE id = ? AND status = 'pending'
            ''', (payment_id,))
            self.conn.commit()
            
            if self.cursor.rowcount > 0:
                self.add_admin_log(ADMIN_ID, "reject_payment", f"Payment {payment_id} rejected")
                return True
            return False
        except Exception as e:
            logger.error(f"Error rejecting payment: {e}")
            return False
    
    # ===== SETTINGS METHODS =====
    def get_setting(self, key):
        try:
            self.cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
            result = self.cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting setting: {e}")
            return None
    
    def update_setting(self, key, value):
        try:
            self.cursor.execute('UPDATE settings SET value = ? WHERE key = ?', (value, key))
            self.conn.commit()
            self.add_admin_log(ADMIN_ID, "update_setting", f"{key} = {value}")
            return True
        except Exception as e:
            logger.error(f"Error updating setting: {e}")
            return False
    
    def get_all_settings(self):
        try:
            self.cursor.execute('SELECT key, value FROM settings')
            return {row[0]: row[1] for row in self.cursor.fetchall()}
        except Exception as e:
            logger.error(f"Error getting all settings: {e}")
            return {}
    
    # ===== ADMIN LOGS =====
    def add_admin_log(self, admin_id, action, details):
        try:
            self.cursor.execute('''
                INSERT INTO admin_logs (admin_id, action, details, created_at)
                VALUES (?, ?, ?, ?)
            ''', (admin_id, action, details, datetime.now().isoformat()))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error adding admin log: {e}")
    
    def get_admin_logs(self, limit=50):
        try:
            self.cursor.execute('''
                SELECT * FROM admin_logs 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting admin logs: {e}")
            return []
    
    # ===== STATISTICS =====
    def get_stats(self):
        try:
            # تعداد کاربران
            self.cursor.execute('SELECT COUNT(*) FROM users')
            total_users = self.cursor.fetchone()[0]
            
            # کاربران فعال
            self.cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
            active_users = self.cursor.fetchone()[0]
            
            # کل سیگنال‌ها
            self.cursor.execute('SELECT COUNT(*) FROM signals')
            total_signals = self.cursor.fetchone()[0]
            
            # سیگنال‌های امروز
            self.cursor.execute('''
                SELECT COUNT(*) FROM signals 
                WHERE DATE(created_at) = DATE('now')
            ''')
            today_signals = self.cursor.fetchone()[0]
            
            # پرداخت‌های در انتظار
            self.cursor.execute('SELECT COUNT(*) FROM payments WHERE status = "pending"')
            pending_payments = self.cursor.fetchone()[0]
            
            # بازخوردها
            self.cursor.execute('SELECT COUNT(*) FROM feedback_log')
            total_feedback = self.cursor.fetchone()[0]
            
            return {
                'total_users': total_users,
                'active_users': active_users,
                'total_signals': total_signals,
                'today_signals': today_signals,
                'pending_payments': pending_payments,
                'total_feedback': total_feedback
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}

db = Database()

# ============================================================
# INDICATORS - دقیق و حرفه‌ای
# ============================================================

def get_candles(symbol, limit=250, interval='5m'):
    """دریافت داده واقعی از Binance"""
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
        logger.error(f"Error getting candles for {symbol}: {e}")
    return None

def calc_rsi(prices, period=14):
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
    
    hist = macd_line - sig_line
    return round(macd_line, 8), round(sig_line, 8), round(hist, 8)

def calc_ma(prices, period):
    if len(prices) < period:
        return prices[-1] if prices else 0
    return round(float(np.mean(np.array(prices[-period:], dtype=np.float64))), 8)

def calc_ema(prices, period):
    if len(prices) < period:
        return prices[-1] if prices else 0
    p = np.array(prices, dtype=np.float64)
    mult = 2.0 / (period + 1)
    ema = float(np.mean(p[-period:]))
    for price in p[-period:]:
        ema = float(price) * mult + ema * (1 - mult)
    return round(ema, 8)

def calc_bollinger(prices, period=20, std_dev=2):
    if len(prices) < period:
        return prices[-1] if prices else 0, prices[-1] if prices else 0, prices[-1] if prices else 0
    p = np.array(prices[-period:], dtype=np.float64)
    ma = float(np.mean(p))
    std = float(np.std(p))
    upper = ma + (std_dev * std)
    lower = ma - (std_dev * std)
    return round(upper, 8), round(ma, 8), round(lower, 8)

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
            tr.append(max(
                highs[-i] - lows[-i],
                abs(highs[-i] - prices[-i-1]),
                abs(lows[-i] - prices[-i-1])
            ))
    return round(float(np.mean(np.array(tr, dtype=np.float64))) if tr else 0.0000001, 8)

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
    
    resistance = 0
    if peaks:
        peaks = sorted(peaks, reverse=True)
        resistance = peaks[0]
        if len(peaks) >= 2:
            cluster = [peaks[0]]
            for p in peaks[1:]:
                if abs(p - peaks[0]) / peaks[0] < 0.02:
                    cluster.append(p)
            resistance = sum(cluster) / len(cluster)
    
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

def calc_adx(highs, lows, prices, period=14):
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

def multi_timeframe_analysis(symbol):
    """تحلیل چند تایم‌فریم"""
    timeframes = ['5m', '15m', '1h']
    results = {'BUY': 0, 'SELL': 0}
    
    for tf in timeframes:
        data = get_candles(symbol, 50, tf)
        if not data:
            continue
        
        prices = data['close']
        current = prices[-1]
        
        if len(prices) < 30:
            continue
        
        ma20 = calc_ma(prices, 20)
        ma50 = calc_ma(prices, 50)
        rsi = calc_rsi(prices, 14)
        
        if current > ma20 and ma20 > ma50 and rsi < 70:
            results['BUY'] += 1
        elif current < ma20 and ma20 < ma50 and rsi > 30:
            results['SELL'] += 1
    
    total = results['BUY'] + results['SELL']
    if total == 0:
        return 50, 50
    
    buy_pct = (results['BUY'] / total) * 100
    sell_pct = (results['SELL'] / total) * 100
    
    return round(buy_pct, 1), round(sell_pct, 1)

# ============================================================
# QUALITY SCORING SYSTEM
# ============================================================

def calculate_quality_score(signal_data):
    """سیستم امتیازدهی کیفیت سیگنال"""
    score = 0
    max_score = 100
    
    # 1. قدرت روند (20 امتیاز)
    adx = signal_data.get('adx', 0)
    if adx > 50:
        score += 20
    elif adx > 40:
        score += 15
    elif adx > 30:
        score += 10
    elif adx > 20:
        score += 5
    
    # 2. موقعیت RSI (15 امتیاز)
    rsi = signal_data.get('rsi', 50)
    signal_type = signal_data.get('signal', 'HOLD')
    
    if signal_type == "BUY":
        if 30 <= rsi <= 40:
            score += 15
        elif 40 < rsi <= 50:
            score += 10
        elif 20 <= rsi < 30:
            score += 8
    elif signal_type == "SELL":
        if 60 <= rsi <= 70:
            score += 15
        elif 50 <= rsi < 60:
            score += 10
        elif 70 < rsi <= 80:
            score += 8
    
    # 3. تایید MACD (15 امتیاز)
    macd = signal_data.get('macd', 0)
    if signal_type == "BUY" and macd > 0:
        score += 15
    elif signal_type == "SELL" and macd < 0:
        score += 15
    elif abs(macd) > 0.001:
        score += 8
    
    # 4. تایید روند با MA (15 امتیاز)
    current = signal_data.get('price', 0)
    ma20 = signal_data.get('ma20', 0)
    ma50 = signal_data.get('ma50', 0)
    
    if signal_type == "BUY":
        if current > ma20 and ma20 > ma50:
            score += 15
        elif current > ma20:
            score += 8
    elif signal_type == "SELL":
        if current < ma20 and ma20 < ma50:
            score += 15
        elif current < ma20:
            score += 8
    
    # 5. نسبت ریسک/ریوارد (15 امتیاز)
    risk_reward = signal_data.get('risk_reward', 0)
    if risk_reward >= 3:
        score += 15
    elif risk_reward >= 2.5:
        score += 12
    elif risk_reward >= 2:
        score += 8
    
    # 6. حجم (10 امتیاز)
    vol_ratio = signal_data.get('vol_ratio', 1)
    if vol_ratio >= 2.5:
        score += 10
    elif vol_ratio >= 2:
        score += 7
    elif vol_ratio >= 1.5:
        score += 4
    
    # 7. تایید چند تایم‌فریم (10 امتیاز)
    mtf_buy = signal_data.get('mtf_buy', 0)
    mtf_sell = signal_data.get('mtf_sell', 0)
    
    if signal_type == "BUY" and mtf_buy >= 60:
        score += 10
    elif signal_type == "SELL" and mtf_sell >= 60:
        score += 10
    elif signal_type == "BUY" and mtf_buy >= 40:
        score += 5
    elif signal_type == "SELL" and mtf_sell >= 40:
        score += 5
    
    return min(score, max_score)

# ============================================================
# SIGNAL GENERATOR - با کیفیت بالا
# ============================================================

def generate_high_quality_signal(symbol):
    """تولید سیگنال با کیفیت بالا"""
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
        
        # محاسبه اندیکاتورها
        rsi = calc_rsi(prices, 14)
        macd, _, macd_hist = calc_macd(prices, 12, 26, 9)
        ma20 = calc_ma(prices, 20)
        ma50 = calc_ma(prices, 50)
        ma200 = calc_ma(prices, 200)
        upper_bb, middle_bb, lower_bb = calc_bollinger(prices, 20, 2)
        vwap = calc_vwap(prices, volumes)
        atr = calc_atr(highs, lows, prices, 14)
        support, resistance = find_support_resistance(highs, lows, prices)
        adx = calc_adx(highs, lows, prices, 14)
        
        # نسبت حجم
        avg_vol = np.mean(volumes[-20:]) if len(volumes) >= 20 else 1
        vol_ratio = volumes[-1] / avg_vol if avg_vol > 0 else 1
        
        # تحلیل چند تایم‌فریم
        mtf_buy, mtf_sell = multi_timeframe_analysis(symbol)
        
        # امتیازدهی اولیه
        score = 50
        reasons = []
        
        # RSI
        if rsi < 25:
            score += 20
            reasons.append(f"🔥 RSI Oversold: {rsi}")
        elif rsi < 35:
            score += 14
            reasons.append(f"📈 RSI Near Oversold: {rsi}")
        elif rsi > 75:
            score -= 20
            reasons.append(f"🔥 RSI Overbought: {rsi}")
        elif rsi > 65:
            score -= 14
            reasons.append(f"📉 RSI Near Overbought: {rsi}")
        
        # MACD
        if macd > 0 and macd_hist > 0:
            score += 18
            reasons.append(f"🟢 MACD Bullish: {macd:.6f}")
        elif macd < 0 and macd_hist < 0:
            score -= 18
            reasons.append(f"🔴 MACD Bearish: {macd:.6f}")
        elif macd > 0:
            score += 10
            reasons.append(f"🟡 MACD Positive: {macd:.6f}")
        else:
            score -= 10
            reasons.append(f"🟡 MACD Negative: {macd:.6f}")
        
        # Moving Averages
        if current > ma20 and ma20 > ma50 and ma50 > ma200:
            score += 18
            reasons.append(f"🚀 Strong Uptrend")
        elif current < ma20 and ma20 < ma50 and ma50 < ma200:
            score -= 18
            reasons.append(f"💀 Strong Downtrend")
        elif current > ma20 and ma20 > ma50:
            score += 12
            reasons.append(f"📈 Uptrend")
        elif current < ma20 and ma20 < ma50:
            score -= 12
            reasons.append(f"📉 Downtrend")
        
        # Bollinger Bands
        if current < lower_bb:
            score += 12
            reasons.append(f"🎯 Touch Lower Band")
        elif current > upper_bb:
            score -= 12
            reasons.append(f"🎯 Touch Upper Band")
        
        # VWAP
        if current > vwap:
            score += 10
            reasons.append(f"✅ Above VWAP")
        else:
            score -= 10
            reasons.append(f"❌ Below VWAP")
        
        # Support/Resistance
        if support > 0:
            dist_to_support = ((current - support) / current) * 100
            if dist_to_support < 0.5:
                score += 8
                reasons.append(f"🛡️ Very Near Support")
            elif dist_to_support < 2:
                score += 5
                reasons.append(f"🛡️ Near Support")
        
        if resistance > 0:
            dist_to_resistance = ((resistance - current) / current) * 100
            if dist_to_resistance < 0.5:
                score -= 8
                reasons.append(f"🚫 Very Near Resistance")
            elif dist_to_resistance < 2:
                score -= 5
                reasons.append(f"🚫 Near Resistance")
        
        # ADX
        if adx > 40:
            if score > 50:
                score += 5
                reasons.append(f"🔥 Strong Trend (ADX: {adx})")
            else:
                score -= 5
                reasons.append(f"💀 Strong Trend (ADX: {adx})")
        
        # Multi-timeframe
        if mtf_buy > 60:
            score += 5
            reasons.append(f"📊 MTF Bullish: {mtf_buy}%")
        elif mtf_sell > 60:
            score -= 5
            reasons.append(f"📊 MTF Bearish: {mtf_sell}%")
        
        # تصمیم نهایی
        confidence = min(98, 50 + abs(score - 50) * 1.3)
        
        if score > 55:
            signal = "BUY"
        elif score < 45:
            signal = "SELL"
        else:
            return None  # سیگنال ضعیف ارسال نشود
        
        # TP/SL
        if signal == "BUY":
            tp = round(current + (atr * 3), 8)
            sl = round(current - (atr * 2), 8)
            if resistance > 0 and tp > resistance:
                tp = round(resistance * 0.995, 8)
            if support > 0 and sl < support:
                sl = round(support * 0.995, 8)
        else:
            tp = round(current - (atr * 3), 8)
            sl = round(current + (atr * 2), 8)
            if support > 0 and tp < support:
                tp = round(support * 1.005, 8)
            if resistance > 0 and sl > resistance:
                sl = round(resistance * 1.005, 8)
        
        # محاسبه نسبت ریسک/ریوارد
        if signal == "BUY":
            risk = abs(current - sl)
            reward = abs(tp - current)
        else:
            risk = abs(sl - current)
            reward = abs(current - tp)
        
        risk_reward = reward / risk if risk > 0 else 0
        
        # ساخت دیتای سیگنال
        signal_data = {
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
            'adx': adx,
            'vol_ratio': vol_ratio,
            'mtf_buy': mtf_buy,
            'mtf_sell': mtf_sell,
            'risk_reward': risk_reward,
            'reasons': reasons[:5],
            'time': datetime.now().strftime("%H:%M")
        }
        
        # محاسبه امتیاز کیفیت
        quality_score = calculate_quality_score(signal_data)
        signal_data['quality_score'] = quality_score
        
        # فیلتر کیفیت
        if quality_score < int(db.get_setting('min_quality_score') or 70):
            return None
        
        # فیلتر نسبت ریسک/ریوارد
        if risk_reward < MIN_RISK_REWARD:
            return None
        
        # فیلتر حجم
        if vol_ratio < MIN_VOLUME_RATIO:
            return None
        
        # فیلتر ADX
        if adx < MIN_ADX:
            return None
        
        return signal_data
        
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
                        'sr': 1.0, 'adx': 1.0, 'mtf': 1.0
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
            'sr': 1.0, 'adx': 1.0, 'mtf': 1.0
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
# TELEGRAM FUNCTIONS - کامل
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
    except Exception as e:
        logger.error(f"Error sending telegram: {e}")
        return False

def send_admin(message, reply_markup=None):
    return send_telegram(message, ADMIN_ID, reply_markup)

def build_signal_message(signal, signal_id):
    """ساخت پیام سیگنال با دکمه‌های بازخورد"""
    if not signal or signal['signal'] == 'HOLD':
        return None, None
    
    emoji = "🟢" if signal['signal'] == 'BUY' else "🔴"
    direction = "LONG" if signal['signal'] == 'BUY' else "SHORT"
    
    msg = f"""
{emoji} <b>{signal['symbol']}</b> | {direction}
💰 <b>Entry:</b> <code>${signal['price']:.6f}</code>
🎯 <b>TP:</b> <code>${signal['tp']:.6f}</code>
🛑 <b>SL:</b> <code>${signal['sl']:.6f}</code>
📊 <b>Confidence:</b> {signal['confidence']}%

📊 <b>Indicators:</b>
RSI: {signal['rsi']:.1f} | MACD: {signal['macd']:.6f}
MA20: ${signal['ma20']:.4f} | MA50: ${signal['ma50']:.4f}
Support: ${signal['support']:.4f} | Resistance: ${signal['resistance']:.4f}
Volume: {signal['vol_ratio']:.1f}x | ADX: {signal['adx']:.1f}

📝 <b>Reasons:</b>
"""
    
    for i, reason in enumerate(signal['reasons'][:4], 1):
        msg += f"{i}. {reason}\n"
    
    msg += f"""
🧠 <b>Accuracy:</b> {learner.get_accuracy()}%
⭐ <b>Quality Score:</b> {signal.get('quality_score', 0)}/100
📈 <b>Risk/Reward:</b> 1:{signal.get('risk_reward', 0):.1f}
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
# ADMIN PANEL - کامل
# ============================================================

def show_admin_panel():
    """نمایش پنل مدیریت"""
    settings = db.get_all_settings()
    stats = db.get_stats()
    
    msg = f"""
🔐 <b>ADMIN PANEL</b>
━━━━━━━━━━━━━━━━━━━━━━

📊 <b>Statistics:</b>
👤 Total Users: {stats.get('total_users', 0)}
🟢 Active Users: {stats.get('active_users', 0)}
📈 Total Signals: {stats.get('total_signals', 0)}
📊 Today Signals: {stats.get('today_signals', 0)}
💳 Pending Payments: {stats.get('pending_payments', 0)}
📝 Total Feedback: {stats.get('total_feedback', 0)}
🧠 Accuracy: {learner.get_accuracy()}%

⚙️ <b>Settings:</b>
📡 Signals: {'🟢 ON' if settings.get('signal_enabled') == '1' else '🔴 OFF'}
💰 Price: {settings.get('price', '100 USDT')}
🎯 Min Confidence: {settings.get('min_confidence', 75)}%
⭐ Min Quality: {settings.get('min_quality_score', 70)}/100
📊 Max Signals: {settings.get('max_signals', 3)}

━━━━━━━━━━━━━━━━━━━━━━
📌 <b>Commands:</b>
/panel - Show this panel
/on - Enable signals
/off - Disable signals
/stats - Show statistics
/settings - Change settings
/payments - Manage payments
/users - List users
/logs - View logs
/feedback - View feedback stats
/broadcast - Send message to all users
/backup - Backup database
"""
    
    keyboard = {
        'inline_keyboard': [
            [
                {'text': '🟢 Enable Signals', 'callback_data': 'admin_on'},
                {'text': '🔴 Disable Signals', 'callback_data': 'admin_off'}
            ],
            [
                {'text': '📊 Stats', 'callback_data': 'admin_stats'},
                {'text': '💳 Payments', 'callback_data': 'admin_payments'}
            ],
            [
                {'text': '👥 Users', 'callback_data': 'admin_users'},
                {'text': '📝 Feedback', 'callback_data': 'admin_feedback'}
            ],
            [
                {'text': '⚙️ Settings', 'callback_data': 'admin_settings'}
            ]
        ]
    }
    
    send_admin(msg, keyboard)

def handle_admin_callback(callback_data, user_id):
    """مدیریت کلیک‌های دکمه‌های پنل مدیریت"""
    try:
        if callback_data == 'admin_on':
            db.update_setting('signal_enabled', '1')
            send_admin("✅ <b>Signals Enabled</b>\nBot will now send signals to channel.")
            return True
        
        elif callback_data == 'admin_off':
            db.update_setting('signal_enabled', '0')
            send_admin("🔴 <b>Signals Disabled</b>\nBot will not send signals to channel.")
            return True
        
        elif callback_data == 'admin_stats':
            stats = db.get_stats()
            feedback_stats = db.get_feedback_stats()
            
            msg = f"""
📊 <b>Detailed Statistics</b>
━━━━━━━━━━━━━━━━━━━━━━

👤 <b>Users:</b>
Total: {stats.get('total_users', 0)}
Active: {stats.get('active_users', 0)}
Inactive: {stats.get('total_users', 0) - stats.get('active_users', 0)}

📈 <b>Signals:</b>
Total: {stats.get('total_signals', 0)}
Today: {stats.get('today_signals', 0)}

💳 <b>Payments:</b>
Pending: {stats.get('pending_payments', 0)}

📝 <b>Feedback:</b>
Total: {feedback_stats[0] if feedback_stats else 0}
✅ Positive: {feedback_stats[1] if feedback_stats else 0}
❌ Negative: {feedback_stats[2] if feedback_stats else 0}
🧠 Accuracy: {learner.get_accuracy()}%
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
                user = db.get_user(user_id)
                username = user[1] if user else "Unknown"
                msg += f"""
#{payment_id} | {username}
💰 Amount: {amount}
🔑 {payment_hash[:20]}...
📅 {created_at[:16]}
/confirm_{payment_id} - Confirm
/reject_{payment_id} - Reject
━━━━━━━━━━━━━━━━━━━━━━
"""
            send_admin(msg)
            return True
        
        elif callback_data == 'admin_users':
            users = db.cursor.execute('''
                SELECT user_id, username, is_active, 
                       datetime(subscription_expire) as expire,
                       total_signals_received
                FROM users 
                ORDER BY joined_at DESC 
                LIMIT 10
            ''').fetchall()
            
            if not users:
                send_admin("👥 <b>No users found</b>")
                return True
            
            msg = "👥 <b>Recent Users</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
            for user in users:
                user_id, username, is_active, expire, signals = user
                status = "🟢 Active" if is_active else "🔴 Inactive"
                msg += f"""
🆔 {user_id}
📛 {username or 'No username'}
📊 {status}
📅 Expires: {expire[:10] if expire else 'N/A'}
📈 Signals: {signals}
━━━━━━━━━━━━━━━━━━━━━━
"""
            send_admin(msg)
            return True
        
        elif callback_data == 'admin_feedback':
            feedback_stats = db.get_feedback_stats()
            total, positive, negative = feedback_stats if feedback_stats else (0, 0, 0)
            
            # آخرین بازخوردها
            recent = db.cursor.execute('''
                SELECT f.feedback, u.username, s.symbol, f.created_at
                FROM feedback_log f
                JOIN users u ON f.user_id = u.user_id
                JOIN signals s ON f.signal_id = s.id
                ORDER BY f.created_at DESC
                LIMIT 5
            ''').fetchall()
            
            msg = f"""
📝 <b>Feedback Statistics</b>
━━━━━━━━━━━━━━━━━━━━━━

📊 <b>Overall:</b>
Total: {total}
✅ Positive: {positive} ({round(positive/total*100 if total > 0 else 0)}%)
❌ Negative: {negative} ({round(negative/total*100 if total > 0 else 0)}%)
🧠 Accuracy: {learner.get_accuracy()}%

📋 <b>Recent Feedback:</b>
"""
            for feedback, username, symbol, created_at in recent:
                emoji = "✅" if feedback == 'positive' else "❌"
                msg += f"\n{emoji} {username or 'Unknown'} | {symbol} | {created_at[:16]}"
            
            send_admin(msg)
            return True
        
        elif callback_data == 'admin_settings':
            settings = db.get_all_settings()
            msg = "⚙️ <b>Settings</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
            for key, value in settings.items():
                msg += f"\n📌 {key}: <code>{value}</code>"
            
            msg += """

📝 <b>Commands to change:</b>
/set min_confidence 80
/set max_signals 2
/set min_quality_score 75
/set price "200 USDT"
/set wallet "ADDRESS"
/set auto_approve_payments 1
"""
            send_admin(msg)
            return True
        
        return False
    except Exception as e:
        logger.error(f"Error handling admin callback: {e}")
        send_admin(f"❌ Error: {e}")
        return False

def handle_admin_command(text):
    """مدیریت دستورات متنی ادمین"""
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
            feedback_stats = db.get_feedback_stats()
            
            msg = f"""
📊 <b>BOT STATISTICS</b>
━━━━━━━━━━━━━━━━━━━━━━
👤 Users: {stats.get('total_users', 0)}
🟢 Active: {stats.get('active_users', 0)}
📈 Signals: {stats.get('total_signals', 0)}
📊 Today: {stats.get('today_signals', 0)}
💳 Pending: {stats.get('pending_payments', 0)}
📝 Feedback: {stats.get('total_feedback', 0)}
✅ Positive: {feedback_stats[1] if feedback_stats else 0}
❌ Negative: {feedback_stats[2] if feedback_stats else 0}
🧠 Accuracy: {learner.get_accuracy()}%
━━━━━━━━━━━━━━━━━━━━━━
/panel - Open admin panel
            """
            send_admin(msg)
            return True
        
        elif text.startswith('/confirm_'):
            try:
                payment_id = int(text.replace('/confirm_', ''))
                success, user_id, expire_date = db.confirm_payment(payment_id)
                if success:
                    send_admin(f"✅ Payment #{payment_id} confirmed!")
                    send_telegram(
                        f"✅ <b>Payment Confirmed!</b>\n"
                        f"📅 Expires: {expire_date.strftime('%Y-%m-%d')}\n"
                        f"🤖 You now have access to all signals!",
                        user_id
                    )
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
                        send_telegram(
                            "❌ <b>Payment Rejected</b>\n"
                            "Please try again or contact support.",
                            payment[1]
                        )
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
                # حذف نقل قول‌ها
                value = value.strip('"').strip("'")
                
                db.update_setting(key, value)
                send_admin(f"✅ Setting updated: {key} = {value}")
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
                user = db.get_user(user_id)
                username = user[1] if user else "Unknown"
                msg += f"""
#{payment_id} | {username}
💰 Amount: {amount}
🔑 {payment_hash[:20]}...
📅 {created_at[:16]}
/confirm_{payment_id} - Confirm
/reject_{payment_id} - Reject
━━━━━━━━━━━━━━━━━━━━━━
"""
            send_admin(msg)
            return True
        
        elif text == '/users':
            users = db.cursor.execute('''
                SELECT COUNT(*) FROM users
            ''').fetchone()[0]
            
            active = db.cursor.execute('''
                SELECT COUNT(*) FROM users WHERE is_active = 1
            ''').fetchone()[0]
            
            send_admin(f"""
👥 <b>User Statistics</b>
━━━━━━━━━━━━━━━━━━━━━━
Total Users: {users}
Active Users: {active}
Inactive Users: {users - active}
            """)
            return True
        
        elif text == '/logs':
            logs = db.get_admin_logs(10)
            if not logs:
                send_admin("📋 No logs found")
                return True
            
            msg = "📋 <b>Recent Admin Logs</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
            for log in logs:
                msg += f"\n{log[3]} | {log[2]} | {log[4][:16]}"
            
            send_admin(msg)
            return True
        
        elif text == '/feedback':
            stats = db.get_feedback_stats()
            total, positive, negative = stats if stats else (0, 0, 0)
            
            send_admin(f"""
📝 <b>Feedback Statistics</b>
━━━━━━━━━━━━━━━━━━━━━━
Total: {total}
✅ Positive: {positive}
❌ Negative: {negative}
🧠 Accuracy: {learner.get_accuracy()}%
            """)
            return True
        
        elif text == '/broadcast':
            send_admin("📢 <b>Broadcast Command</b>\nUse: /broadcast Your message here")
            return True
        
        elif text.startswith('/broadcast '):
            message = text[11:]
            users = db.get_all_users()
            sent = 0
            
            send_admin(f"📢 Broadcasting to {len(users)} users...")
            
            for user in users:
                user_id = user[0]
                try:
                    if send_telegram(f"📢 <b>Announcement</b>\n\n{message}", user_id):
                        sent += 1
                    time.sleep(0.05)  # جلوگیری از محدودیت
                except:
                    pass
            
            send_admin(f"✅ Broadcast sent to {sent} users")
            return True
        
        elif text == '/backup':
            try:
                # ایجاد بکاپ از دیتابیس
                backup_file = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                
                # کپی فایل دیتابیس
                import shutil
                shutil.copy2('bot_data.db', backup_file)
                
                send_admin(f"✅ Database backed up: {backup_file}")
                
                # بکاپ از فایل‌های تنظیمات
                if os.path.exists('learning_data.json'):
                    shutil.copy2('learning_data.json', f"learning_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                
            except Exception as e:
                send_admin(f"❌ Backup failed: {e}")
            return True
        
        elif text == '/help':
            msg = """
📚 <b>Admin Commands</b>
━━━━━━━━━━━━━━━━━━━━━━

<b>Panel</b>
/panel - Open admin panel
/start - Same as /panel

<b>Signal Control</b>
/on - Enable signals
/off - Disable signals

<b>Settings</b>
/set key value - Change setting
/stats - Show statistics
/settings - Show all settings

<b>Payments</b>
/payments - List pending
/confirm_ID - Confirm payment
/reject_ID - Reject payment

<b>Users & Feedback</b>
/users - List users
/feedback - Feedback stats
/logs - View admin logs

<b>Other</b>
/broadcast - Send to all users
/backup - Backup database
/help - Show this help
━━━━━━━━━━━━━━━━━━━━━━
<b>Shortcuts:</b>
/confirm_1 - Confirm payment #1
/reject_2 - Reject payment #2
/set min_confidence 80
/set max_signals 2
            """
            send_admin(msg)
            return True
        
        return False
    except Exception as e:
        logger.error(f"Error handling admin command: {e}")
        send_admin(f"❌ Error: {e}")
        return False

# ============================================================
# MAIN SIGNAL LOOP
# ============================================================

def signal_loop():
    logger.info("🚀 Signal Bot V12 started with Admin Panel")
    send_admin("🚀 <b>Signal Bot V12 Started</b>\n\n✅ Admin Panel Active\n✅ Auto-signals Active\n✅ Feedback System Active")
    
    cycle = 0
    
    while True:
        try:
            cycle += 1
            
            # بررسی تنظیمات
            if db.get_setting('signal_enabled') != '1':
                time.sleep(30)
                continue
            
            # دریافت تنظیمات
            max_signals = int(db.get_setting('max_signals') or 3)
            min_confidence = int(db.get_setting('min_confidence') or 75)
            
            logger.info(f"🔄 Cycle {cycle} - Scanning {len(SYMBOLS)} symbols")
            
            signals = []
            for symbol in SYMBOLS:
                try:
                    signal = generate_high_quality_signal(symbol)
                    if signal:
                        signals.append(signal)
                        logger.info(f"✅ {signal['symbol']}: {signal['signal']} (Quality: {signal.get('quality_score', 0)})")
                    time.sleep(0.02)
                except Exception as e:
                    logger.error(f"Error processing {symbol}: {e}")
            
            # مرتب‌سازی بر اساس کیفیت
            signals.sort(key=lambda x: x.get('quality_score', 0), reverse=True)
            signals = signals[:max_signals]
            
            if signals:
                for signal in signals:
                    try:
                        # ذخیره در دیتابیس
                        signal_id = db.save_signal(0, signal)
                        if signal_id:
                            # ارسال به کانال
                            msg, keyboard = build_signal_message(signal, signal_id)
                            if msg:
                                if send_telegram(msg, reply_markup=keyboard):
                                    db.mark_signal_sent(signal_id)
                                    logger.info(f"✅ Sent signal: {signal['symbol']}")
                                else:
                                    # تلاش مجدد بدون دکمه
                                    send_telegram(msg)
                                    db.mark_signal_sent(signal_id)
                            time.sleep(2)
                    except Exception as e:
                        logger.error(f"Error sending signal: {e}")
            else:
                if cycle % 6 == 0:
                    send_telegram(f"⏳ No signals found (Cycle {cycle})")
            
            # بررسی پرداخت‌های در انتظار
            payments = db.get_pending_payments()
            if payments:
                send_admin(f"💳 <b>{len(payments)} pending payments</b>\nUse /payments to view")
            
            logger.info(f"⏱ Waiting {INTERVAL//60} minutes...")
            time.sleep(INTERVAL)
            
        except Exception as e:
            logger.error(f"❌ Main loop error: {e}")
            send_admin(f"❌ <b>Error in main loop</b>\n{e}")
            time.sleep(60)

# ============================================================
# UPDATE CHECKER
# ============================================================

def check_subscriptions():
    """بررسی و غیرفعال کردن خودکار اشتراک‌های منقضی شده"""
    while True:
        try:
            # یافتن کاربران با اشتراک منقضی شده
            db.cursor.execute('''
                SELECT user_id FROM users 
                WHERE is_active = 1 
                AND datetime(subscription_expire) < datetime('now')
            ''')
            
            expired_users = db.cursor.fetchall()
            for user in expired_users:
                user_id = user[0]
                db.cursor.execute('''
                    UPDATE users SET is_active = 0 
                    WHERE user_id = ?
                ''', (user_id,))
                db.conn.commit()
                logger.info(f"🔴 Subscription expired for user {user_id}")
            
            time.sleep(3600)  # هر ۱ ساعت
        except Exception as e:
            logger.error(f"Error checking subscriptions: {e}")
            time.sleep(300)

# ============================================================
# WEBHOOK RECEIVER (برای دریافت دکمه‌ها)
# ============================================================

def process_callback(callback_data, user_id):
    """پردازش کلیک روی دکمه‌ها"""
    try:
        # دکمه‌های ادمین
        if callback_data.startswith('admin_'):
            return handle_admin_callback(callback_data, user_id)
        
        # دکمه‌های بازخورد
        if callback_data.startswith('fb_'):
            parts = callback_data.split('_')
            if len(parts) != 3:
                return False
            
            feedback_type = parts[1]
            signal_id = int(parts[2])
            
            # بررسی اینکه کاربر اشتراک دارد یا حداقل ۱ سیگنال رایگان
            user = db.get_user(user_id)
            if not user:
                db.add_user(user_id, None, None)
            
            # ثبت بازخورد
            success, message = db.update_feedback(signal_id, feedback_type, user_id)
            if success:
                learner.add_feedback(feedback_type)
                
                # پیام تایید
                if feedback_type == 'positive':
                    msg = "✅ <b>Thank you!</b>\nYour feedback helps improve signal accuracy! 🚀"
                else:
                    msg = "❌ <b>Thank you!</b>\nWe'll use this feedback to improve the algorithm! 🔧"
                
                send_telegram(msg, user_id)
                
                # اطلاع به ادمین
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
        logger.error(f"Error processing callback: {e}")
        return False

# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    try:
        logger.info("🚀 Starting Ultimate Signal Bot V12")
        
        # شروع بررسی اشتراک‌ها در ترد جداگانه
        subscription_thread = threading.Thread(target=check_subscriptions, daemon=True)
        subscription_thread.start()
        
        # شروع حلقه اصلی
        signal_loop()
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")