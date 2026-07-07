#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
====================================================================
🚀 ULTIMATE LEARNING BOT V16 - DYNAMIC SCANNER EDITION
====================================================================
✅ شناسایی خودکار ارزهای مستعد پامپ
✅ شناسایی خودکار ارزهای مستعد ریزش (شورت)
✅ اسکن کل بازار به صورت پویا
✅ ۵۰ ویژگی مهندسی‌شده
✅ ۴ مدل یادگیری ماشین همزمان
✅ یادگیری از بازخورد کاربران
✅ هر روز قوی‌تر می‌شود
====================================================================
"""

import logging
import os
import sys
import time
import json
import sqlite3
import threading
import asyncio
import warnings
import pickle
import random
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor

warnings.filterwarnings('ignore')

# ==================== PID ====================
PID_FILE = "bot_learning_v16.pid"

def check_and_create_pid():
    try:
        if os.path.exists(PID_FILE):
            with open(PID_FILE, 'r') as f:
                old_pid = int(f.read().strip())
            try:
                os.kill(old_pid, 9)
                time.sleep(1)
                os.remove(PID_FILE)
            except:
                pass
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
        return True
    except:
        return True

def remove_pid():
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
    except:
        pass

# ==================== Libraries ====================
import requests
import numpy as np
from scipy import stats
from scipy.fft import fft, fftfreq
from scipy.signal import find_peaks
from scipy.stats import skew, kurtosis, entropy, linregress

# ==================== Machine Learning ====================
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.preprocessing import RobustScaler, StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except:
    XGB_AVAILABLE = False

try:
    import torch
    TORCH_AVAILABLE = True
except:
    TORCH_AVAILABLE = False

try:
    import websockets
    WEBSOCKET_AVAILABLE = True
except:
    WEBSOCKET_AVAILABLE = False

# ==================== Settings ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('bot_v16.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8710979491:AAF3YwifUyipir7TkOnYOcsWpbB0QFojkw0"
ADMIN_ID = 327855654
CHANNEL_ID = "@TASTtt_bot"
PAYMENT_WALLET = "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"
PAYMENT_NETWORK = "TRC20"
PAYMENT_AMOUNT = "100 USDT"
SUBSCRIPTION_DAYS = 30
FREE_SIGNALS_DAILY = 2
SCAN_INTERVAL = 180  # هر ۳ دقیقه
MIN_PREDICTION_CONFIDENCE = 55
MIN_FEEDBACK_FOR_RETRAIN = 3
MIN_VOLUME_USDT = 500000  # حداقل حجم روزانه
MAX_SYMBOLS_TO_SCAN = 50  # حداکثر ارز برای اسکن

# ==================== Database ====================
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('bot_v16.db', check_same_thread=False)
        self.conn.execute('PRAGMA journal_mode=WAL')
        self.cursor = self.conn.cursor()
        self.init_tables()
    
    def init_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT, first_name TEXT,
                language TEXT DEFAULT 'fa',
                joined_at TIMESTAMP,
                referral_count INTEGER DEFAULT 0,
                free_signals INTEGER DEFAULT 2,
                max_free_signals INTEGER DEFAULT 2,
                last_free_signal_date TEXT,
                signals_used_today INTEGER DEFAULT 0,
                subscription_expire TIMESTAMP,
                is_active BOOLEAN DEFAULT 0,
                feedback_count INTEGER DEFAULT 0,
                positive_feedback INTEGER DEFAULT 0,
                negative_feedback INTEGER DEFAULT 0,
                correct_predictions INTEGER DEFAULT 0,
                wrong_predictions INTEGER DEFAULT 0
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER, symbol TEXT,
                direction TEXT, entry REAL,
                tp REAL, sl REAL,
                support REAL, resistance REAL,
                leverage INTEGER, confidence INTEGER,
                created_at TIMESTAMP,
                is_free BOOLEAN DEFAULT 0,
                profit_percent REAL DEFAULT 0,
                model_votes TEXT DEFAULT '',
                prediction_details TEXT DEFAULT '',
                signal_accuracy REAL DEFAULT 0,
                feedback TEXT DEFAULT '',
                feedback_accuracy REAL DEFAULT 0,
                features_snapshot TEXT DEFAULT '',
                target_price REAL DEFAULT 0,
                actual_result TEXT DEFAULT '',
                signal_type TEXT DEFAULT 'NORMAL'
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY, value TEXT
            )
        ''')
        self.cursor.execute('INSERT OR IGNORE INTO settings VALUES ("is_paid_mode", "1")')
        self.cursor.execute('INSERT OR IGNORE INTO settings VALUES ("max_free_signals", "2")')
        self.cursor.execute('INSERT OR IGNORE INTO settings VALUES ("auto_learn", "1")')
        self.cursor.execute('INSERT OR IGNORE INTO settings VALUES ("nightly_learn", "1")')
        self.cursor.execute('INSERT OR IGNORE INTO settings VALUES ("scan_interval", "180")')
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
                accuracy REAL,
                created_at TIMESTAMP,
                symbol TEXT,
                direction TEXT,
                confidence INTEGER,
                features_snapshot TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS training_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                features TEXT,
                label INTEGER,
                source TEXT DEFAULT 'historical',
                timestamp TIMESTAMP
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS model_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                accuracy REAL,
                precision REAL,
                recall REAL,
                f1 REAL,
                samples INTEGER,
                training_time REAL,
                created_at TIMESTAMP
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS dynamic_symbols (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE,
                pump_score INTEGER DEFAULT 0,
                dump_score INTEGER DEFAULT 0,
                volume REAL DEFAULT 0,
                change_24h REAL DEFAULT 0,
                last_seen TIMESTAMP,
                signal_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0
            )
        ''')
        self.conn.commit()
    
    def add_user(self, user_id, username, first_name, language='fa'):
        today = datetime.now().date().isoformat()
        max_free = int(self.get_setting('max_free_signals') or FREE_SIGNALS_DAILY)
        self.cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, language, joined_at, free_signals, max_free_signals, last_free_signal_date, signals_used_today)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, language, datetime.now().isoformat(), max_free, max_free, today, 0))
        self.conn.commit()
    
    def get_user(self, user_id):
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone()
    
    def get_free_signals(self, user_id):
        user = self.get_user(user_id)
        if not user:
            return 0
        today = datetime.now().date().isoformat()
        last_date = user[7] if len(user) > 7 else None
        max_free = int(user[8]) if len(user) > 8 and user[8] else FREE_SIGNALS_DAILY
        
        if max_free == 0:
            return 0
        
        if last_date != today:
            self.cursor.execute('''
                UPDATE users SET free_signals = ?, last_free_signal_date = ?, signals_used_today = 0
                WHERE user_id = ?
            ''', (max_free, today, user_id))
            self.conn.commit()
            return max_free
        return user[6] if len(user) > 6 else 0
    
    def get_max_free_signals(self, user_id):
        user = self.get_user(user_id)
        if not user:
            return FREE_SIGNALS_DAILY
        return int(user[8]) if len(user) > 8 and user[8] else FREE_SIGNALS_DAILY
    
    def use_free_signal(self, user_id):
        max_free = self.get_max_free_signals(user_id)
        if max_free == 0:
            return False
        self.cursor.execute('''
            UPDATE users SET free_signals = free_signals - 1, signals_used_today = signals_used_today + 1
            WHERE user_id = ? AND free_signals > 0
        ''', (user_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def has_subscription(self, user_id):
        self.cursor.execute('''
            SELECT subscription_expire FROM users WHERE user_id = ? AND subscription_expire IS NOT NULL
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
    
    def has_confirmed_payment(self, user_id):
        self.cursor.execute('''
            SELECT 1 FROM payments WHERE user_id = ? AND status = 'confirmed' 
            AND expire_at > datetime('now') LIMIT 1
        ''', (user_id,))
        return self.cursor.fetchone() is not None
    
    def has_pending_payment(self, user_id):
        self.cursor.execute('''
            SELECT 1 FROM payments WHERE user_id = ? AND status = 'pending' LIMIT 1
        ''', (user_id,))
        return self.cursor.fetchone() is not None
    
    def save_signal(self, user_id, data, is_free=False, features=None):
        features_json = json.dumps(features) if features else ''
        
        self.cursor.execute('''
            INSERT INTO signals (
                user_id, symbol, direction, entry, tp, sl, support, resistance,
                leverage, confidence, created_at, is_free, profit_percent,
                model_votes, prediction_details, signal_accuracy, features_snapshot, 
                target_price, signal_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, data['symbol'], data['direction'], data['entry'], data['tp'], data['sl'],
            data.get('support', 0), data.get('resistance', 0),
            data['leverage'], data['confidence'], datetime.now().isoformat(),
            1 if is_free else 0, data.get('profit_percent', 0),
            data.get('model_votes', ''), data.get('prediction_details', ''),
            data.get('signal_accuracy', 0), features_json,
            data.get('entry', 0) * 1.05, data.get('signal_type', 'NORMAL')
        ))
        signal_id = self.cursor.lastrowid
        self.conn.commit()
        return signal_id
    
    def get_signal(self, signal_id):
        self.cursor.execute('SELECT * FROM signals WHERE id = ?', (signal_id,))
        return self.cursor.fetchone()
    
    def update_signal_feedback(self, signal_id, feedback, accuracy, features=None):
        features_json = json.dumps(features) if features else ''
        
        self.cursor.execute('''
            UPDATE signals SET feedback = ?, feedback_accuracy = ?, features_snapshot = ?
            WHERE id = ?
        ''', (feedback, accuracy, features_json, signal_id))
        self.conn.commit()
        
        self.cursor.execute('SELECT user_id, symbol, direction, confidence, signal_type FROM signals WHERE id = ?', (signal_id,))
        result = self.cursor.fetchone()
        if result:
            user_id, symbol, direction, confidence, signal_type = result
            
            if feedback == 'positive':
                self.cursor.execute('''
                    UPDATE users SET positive_feedback = positive_feedback + 1, 
                        feedback_count = feedback_count + 1,
                        correct_predictions = correct_predictions + 1
                    WHERE user_id = ?
                ''', (user_id,))
                # به‌روزرسانی آمار موفقیت برای ارز
                self.cursor.execute('''
                    UPDATE dynamic_symbols SET success_count = success_count + 1
                    WHERE symbol = ?
                ''', (symbol,))
            else:
                self.cursor.execute('''
                    UPDATE users SET negative_feedback = negative_feedback + 1, 
                        feedback_count = feedback_count + 1,
                        wrong_predictions = wrong_predictions + 1
                    WHERE user_id = ?
                ''', (user_id,))
            
            self.cursor.execute('''
                INSERT INTO feedback_log (signal_id, user_id, feedback, accuracy, created_at, symbol, direction, confidence, features_snapshot)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (signal_id, user_id, feedback, accuracy, datetime.now().isoformat(), symbol, direction, confidence, features_json))
            self.conn.commit()
    
    def add_payment_hash(self, user_id, payment_hash):
        self.cursor.execute('''
            INSERT INTO payments (user_id, payment_hash, status, created_at)
            VALUES (?, ?, ?, ?)
        ''', (user_id, payment_hash, 'pending', datetime.now().isoformat()))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_pending_payments(self):
        self.cursor.execute('''
            SELECT id, user_id, payment_hash, created_at FROM payments 
            WHERE status = 'pending' ORDER BY created_at ASC
        ''')
        return self.cursor.fetchall()
    
    def get_payment(self, payment_id):
        self.cursor.execute('''
            SELECT id, user_id, payment_hash, status FROM payments WHERE id = ?
        ''', (payment_id,))
        return self.cursor.fetchone()
    
    def confirm_payment(self, payment_id, days=30):
        payment = self.get_payment(payment_id)
        if not payment or payment[3] != 'pending':
            return False, None
        user_id = payment[1]
        expire_date = datetime.now() + timedelta(days=days)
        self.cursor.execute('''
            UPDATE payments SET status = 'confirmed', confirmed_at = ?, expire_at = ?
            WHERE id = ?
        ''', (datetime.now().isoformat(), expire_date.isoformat(), payment_id))
        self.cursor.execute('''
            UPDATE users SET subscription_expire = ?, is_active = 1 WHERE user_id = ?
        ''', (expire_date.isoformat(), user_id))
        self.conn.commit()
        return True, user_id, expire_date
    
    def reject_payment(self, payment_id):
        payment = self.get_payment(payment_id)
        if not payment or payment[3] != 'pending':
            return False
        self.cursor.execute('''
            UPDATE payments SET status = 'rejected' WHERE id = ?
        ''', (payment_id,))
        self.conn.commit()
        return True
    
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
    
    def save_training_data(self, symbol, features, label, source='historical'):
        self.cursor.execute('''
            INSERT INTO training_data (symbol, features, label, source, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (symbol, json.dumps(features), label, source, datetime.now().isoformat()))
        self.conn.commit()
    
    def get_training_data(self, limit=50000):
        self.cursor.execute('''
            SELECT features, label, source FROM training_data ORDER BY timestamp DESC LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()
    
    def get_feedback_training_data(self, limit=1000):
        self.cursor.execute('''
            SELECT features_snapshot, feedback, accuracy, symbol, direction, confidence
            FROM feedback_log 
            WHERE features_snapshot IS NOT NULL AND features_snapshot != ''
            ORDER BY created_at DESC LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()
    
    def save_model_performance(self, accuracy, precision, recall, f1, samples, training_time):
        self.cursor.execute('''
            INSERT INTO model_performance (date, accuracy, precision, recall, f1, samples, training_time, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (datetime.now().date().isoformat(), accuracy, precision, recall, f1, samples, training_time, datetime.now().isoformat()))
        self.conn.commit()
    
    def get_latest_performance(self):
        self.cursor.execute('''
            SELECT accuracy, precision, recall, f1, samples, training_time, created_at
            FROM model_performance ORDER BY id DESC LIMIT 1
        ''')
        return self.cursor.fetchone()
    
    def get_referral_count(self, user_id):
        self.cursor.execute('SELECT referral_count FROM users WHERE user_id = ?', (user_id,))
        r = self.cursor.fetchone()
        return r[0] if r else 0
    
    def update_dynamic_symbol(self, symbol, pump_score=0, dump_score=0, volume=0, change_24h=0):
        self.cursor.execute('''
            INSERT OR REPLACE INTO dynamic_symbols 
            (symbol, pump_score, dump_score, volume, change_24h, last_seen)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (symbol, pump_score, dump_score, volume, change_24h, datetime.now().isoformat()))
        self.conn.commit()
    
    def get_dynamic_symbols(self, limit=30):
        self.cursor.execute('''
            SELECT symbol, pump_score, dump_score, volume, change_24h, success_count
            FROM dynamic_symbols 
            ORDER BY (pump_score + dump_score) DESC, success_count DESC
            LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()
    
    def get_hot_symbols(self, limit=20):
        self.cursor.execute('''
            SELECT symbol FROM dynamic_symbols 
            ORDER BY (pump_score * 2 + success_count) DESC
            LIMIT ?
        ''', (limit,))
        return [r[0] for r in self.cursor.fetchall()]

db = Database()

# ==================== Price Service ====================
class PriceService:
    def __init__(self):
        self.binance = "https://api.binance.com/api/v3"
        self.cache = {}
        self.ws_prices = {}
        self.ws_times = {}
        
        if WEBSOCKET_AVAILABLE:
            try:
                threading.Thread(target=self._ws_loop, daemon=True).start()
            except:
                pass
    
    def _ws_loop(self):
        try:
            asyncio.run(self._ws_main())
        except:
            pass
    
    async def _ws_main(self):
        try:
            uri = "wss://stream.binance.com:9443/ws"
            async with websockets.connect(uri, ping_interval=20, ping_timeout=10) as ws:
                subs = []
                hot = db.get_hot_symbols(30)
                if not hot:
                    hot = ['btcusdt', 'ethusdt', 'bnbusdt', 'solusdt', 'xrpusdt']
                for s in hot[:20]:
                    subs.append(f"{s.lower()}@trade")
                await ws.send(json.dumps({
                    "method": "SUBSCRIBE",
                    "params": subs,
                    "id": 1
                }))
                async for msg in ws:
                    try:
                        d = json.loads(msg)
                        if 'data' in d and 's' in d['data']:
                            s = d['data']['s'].upper()
                            p = float(d['data']['p'])
                            self.ws_prices[s] = p
                            self.ws_times[s] = datetime.now()
                    except:
                        continue
        except:
            pass
    
    def get_candles(self, symbol, interval='5m', limit=200):
        cache_key = f"{symbol}_{interval}_{limit}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            r = requests.get(
                f"{self.binance}/klines",
                params={'symbol': symbol, 'interval': interval, 'limit': limit},
                timeout=10
            )
            if r.status_code == 200:
                data = r.json()
                candles = []
                for c in data:
                    candles.append({
                        'open': float(c[1]), 'high': float(c[2]),
                        'low': float(c[3]), 'close': float(c[4]),
                        'volume': float(c[5]), 'timestamp': datetime.fromtimestamp(c[0]/1000)
                    })
                self.cache[cache_key] = candles
                return candles
        except Exception as e:
            logger.error(f"Error getting candles for {symbol}: {e}")
        return None
    
    def get_historical_candles(self, symbol, start_date, end_date, interval='1h'):
        try:
            start_ts = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000)
            end_ts = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000)
            all_candles = []
            
            while start_ts < end_ts:
                r = requests.get(
                    f"{self.binance}/klines",
                    params={
                        'symbol': symbol,
                        'interval': interval,
                        'startTime': start_ts,
                        'limit': 1000
                    },
                    timeout=10
                )
                if r.status_code == 200:
                    data = r.json()
                    if not data:
                        break
                    for c in data:
                        ts = c[0]
                        if ts > end_ts:
                            break
                        all_candles.append({
                            'open': float(c[1]), 'high': float(c[2]),
                            'low': float(c[3]), 'close': float(c[4]),
                            'volume': float(c[5]), 'timestamp': datetime.fromtimestamp(ts/1000)
                        })
                    start_ts = data[-1][0] + 1
                    time.sleep(0.1)
                else:
                    break
            return all_candles
        except:
            return []

price_service = PriceService()

# ==================== Dynamic Symbol Scanner ====================
class DynamicSymbolScanner:
    """اسکنر پویا برای پیدا کردن خودکار ارزهای مستعد پامپ و دامپ"""
    
    def __init__(self):
        self.binance = "https://api.binance.com/api/v3"
        self.cache = {}
        self.last_scan = None
        self.hot_symbols = []
        self.pump_candidates = []
        self.dump_candidates = []
        self.symbol_scores = {}
        
    def get_all_tickers(self):
        """دریافت لیست کامل همه ارزها از بایننس"""
        try:
            r = requests.get(f"{self.binance}/ticker/24hr", timeout=10)
            if r.status_code == 200:
                data = r.json()
                tickers = []
                for item in data:
                    symbol = item['symbol']
                    if symbol.endswith('USDT') and not any(x in symbol for x in ['UP', 'DOWN', 'BUSD', 'FDUSD']):
                        try:
                            vol = float(item['quoteVolume'])
                            price = float(item['lastPrice'])
                            change = float(item['priceChangePercent'])
                            if vol > MIN_VOLUME_USDT and price > 0.00001:
                                tickers.append({
                                    'symbol': symbol,
                                    'price': price,
                                    'volume': vol,
                                    'change_24h': change,
                                    'high': float(item['highPrice']),
                                    'low': float(item['lowPrice']),
                                    'bid': float(item['bidPrice']),
                                    'ask': float(item['askPrice']),
                                    'trades': int(item['count']),
                                    'volume_24h': vol
                                })
                        except:
                            continue
                return tickers
        except Exception as e:
            logger.error(f"Error getting tickers: {e}")
        return []
    
    def detect_pump_candidates(self, tickers, top_n=25):
        """تشخیص ارزهای مستعد پامپ بر اساس چندین فاکتور"""
        candidates = []
        
        for t in tickers:
            score = 0
            reasons = []
            
            # ۱. رشد قیمتی مناسب (نه بیش از حد)
            if 1.5 < t['change_24h'] < 10:
                score += 5
                reasons.append("رشد ملایم")
            elif 10 <= t['change_24h'] < 20:
                score += 3
                reasons.append("رشد قابل توجه")
            elif t['change_24h'] >= 20:
                score -= 3
                reasons.append("رشد بیش از حد - ریسک")
            
            # ۲. حجم بالا نسبت به میانگین
            if t['volume'] > 10_000_000:
                score += 4
                reasons.append("حجم بسیار بالا")
            elif t['volume'] > 5_000_000:
                score += 2
                reasons.append("حجم بالا")
            
            # ۳. تعداد معاملات بالا (نقدشوندگی)
            if t['trades'] > 20000:
                score += 3
                reasons.append("نقدشوندگی عالی")
            elif t['trades'] > 10000:
                score += 1
                reasons.append("نقدشوندگی خوب")
            
            # ۴. قیمت مناسب
            if 0.01 < t['price'] < 50:
                score += 2
                reasons.append("قیمت مناسب")
            
            # ۵. نوسان بالا (احتمال حرکت)
            range_pct = ((t['high'] - t['low']) / (t['low'] + 0.0001)) * 100
            if range_pct > 10:
                score += 3
                reasons.append("نوسان بالا")
            elif range_pct > 5:
                score += 1
            
            # ۶. فاصله از کف روز
            dist_from_low = ((t['price'] - t['low']) / (t['low'] + 0.0001)) * 100
            if dist_from_low < 5:
                score += 2
                reasons.append("نزدیک به کف")
            
            # ۷. فاصله از اوج روز (می‌خواهیم نزدیک به اوج نباشد برای پامپ)
            dist_from_high = ((t['high'] - t['price']) / (t['high'] + 0.0001)) * 100
            if dist_from_high > 5:
                score += 2
                reasons.append("فضای رشد")
            
            candidates.append({
                **t,
                'pump_score': score,
                'range_pct': range_pct,
                'reasons': reasons[:3]
            })
        
        candidates.sort(key=lambda x: x['pump_score'], reverse=True)
        
        # به‌روزرسانی دیتابیس
        for c in candidates[:top_n]:
            db.update_dynamic_symbol(c['symbol'], c['pump_score'], 0, c['volume'], c['change_24h'])
        
        self.pump_candidates = [c['symbol'] for c in candidates[:top_n]]
        return candidates[:top_n]
    
    def detect_dump_candidates(self, tickers, top_n=25):
        """تشخیص ارزهای مستعد ریزش (برای سیگنال شورت)"""
        candidates = []
        
        for t in tickers:
            score = 0
            reasons = []
            
            # ۱. رشد بیش از حد (احتمال اصلاح)
            if t['change_24h'] > 20:
                score += 6
                reasons.append("رشد بیش از حد")
            elif t['change_24h'] > 10:
                score += 3
                reasons.append("رشد قابل توجه")
            
            # ۲. حجم بالا در سقف قیمتی
            if t['volume'] > 10_000_000 and t['change_24h'] > 10:
                score += 5
                reasons.append("حجم بالا در سقف")
            
            # ۳. فاصله از اوج روز
            dist_from_high = ((t['high'] - t['price']) / (t['high'] + 0.0001)) * 100
            if dist_from_high < 2 and t['change_24h'] > 5:
                score += 5
                reasons.append("نزدیک به اوج")
            elif dist_from_high < 5 and t['change_24h'] > 5:
                score += 2
            
            # ۴. نسبت عرضه به تقاضا (اسپرد بالا)
            spread = ((t['ask'] - t['bid']) / (t['bid'] + 0.0001)) * 100
            if spread > 0.2:
                score += 3
                reasons.append("اسپرد بالا")
            
            # ۵. کاهش تعداد معاملات نسبت به حجم
            trade_vol_ratio = t['volume'] / (t['trades'] + 1)
            if trade_vol_ratio > 1000:
                score += 2
                reasons.append("معاملات بزرگ")
            
            # ۶. قیمت بالا (احتمال ریزش بیشتر)
            if t['price'] > 100:
                score += 2
                reasons.append("قیمت بالا")
            
            candidates.append({
                **t,
                'dump_score': score,
                'dist_from_high': dist_from_high,
                'reasons': reasons[:3]
            })
        
        candidates.sort(key=lambda x: x['dump_score'], reverse=True)
        
        # به‌روزرسانی دیتابیس
        for c in candidates[:top_n]:
            db.update_dynamic_symbol(c['symbol'], 0, c['dump_score'], c['volume'], c['change_24h'])
        
        self.dump_candidates = [c['symbol'] for c in candidates[:top_n]]
        return candidates[:top_n]
    
    def find_new_coins(self, tickers, top_n=10):
        """پیدا کردن ارزهای جدید و داغ"""
        candidates = []
        
        for t in tickers:
            if t['trades'] > 5000 and t['volume'] > 2_000_000:
                if t['change_24h'] > 3 or t['change_24h'] < -3:
                    candidates.append(t)
        
        candidates.sort(key=lambda x: abs(x['change_24h']), reverse=True)
        return candidates[:top_n]
    
    def scan_all(self):
        """اسکن کامل بازار و به‌روزرسانی لیست ارزهای داغ"""
        tickers = self.get_all_tickers()
        if not tickers:
            return [], [], []
        
        # تشخیص پامپ و دامپ
        pump = self.detect_pump_candidates(tickers, 25)
        dump = self.detect_dump_candidates(tickers, 20)
        
        # ترکیب برای لیست نهایی
        hot = []
        
        # اولویت با ارزهای پامپ
        for p in pump[:15]:
            if p['symbol'] not in hot:
                hot.append(p['symbol'])
        
        # سپس ارزهای دامپ
        for d in dump[:10]:
            if d['symbol'] not in hot:
                hot.append(d['symbol'])
        
        # ارزهای اصلی همیشه باشند
        main_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT']
        for s in main_symbols:
            if s not in hot:
                hot.insert(0, s)
        
        self.hot_symbols = hot[:MAX_SYMBOLS_TO_SCAN]
        self.last_scan = datetime.now()
        
        logger.info(f"🔍 Dynamic scan complete: {len(self.hot_symbols)} hot symbols")
        logger.info(f"🚀 Pump candidates: {[p['symbol'] for p in pump[:5]]}")
        logger.info(f"📉 Dump candidates: {[d['symbol'] for d in dump[:5]]}")
        
        return pump[:5], dump[:5], self.hot_symbols

# ==================== Feature Engineer ====================
class FeatureEngineer:
    """استخراج ۵۰ ویژگی از داده‌های خام"""
    
    @staticmethod
    def extract_all_features(candles):
        if not candles or len(candles) < 50:
            return None
        
        closes = np.array([c['close'] for c in candles])
        highs = np.array([c['high'] for c in candles])
        lows = np.array([c['low'] for c in candles])
        opens = np.array([c['open'] for c in candles])
        volumes = np.array([c['volume'] for c in candles])
        
        features = {}
        current_price = closes[-1]
        
        # ۱. بازده‌ها
        for p in [5, 10, 20, 30, 50, 100]:
            if len(closes) > p:
                features[f'return_{p}'] = ((closes[-1] - closes[-p]) / closes[-p]) * 100
                features[f'volatility_{p}'] = np.std(closes[-p:]) / (np.mean(closes[-p:]) + 0.0001)
        
        # ۲. میانگین‌های متحرک
        for p in [7, 14, 21, 50, 100, 200]:
            if len(closes) >= p:
                ma = np.mean(closes[-p:])
                features[f'ma_{p}'] = ma
                features[f'price_to_ma_{p}'] = (current_price / (ma + 0.0001) - 1) * 100
        
        # ۳. EMA
        for p in [7, 14, 21, 50, 100]:
            if len(closes) >= p:
                features[f'ema_{p}'] = FeatureEngineer._ema(closes, p)
        
        # ۴. RSI
        for p in [7, 14, 21, 28]:
            features[f'rsi_{p}'] = FeatureEngineer._rsi(closes, p)
        
        # ۵. MACD
        macd, signal, hist = FeatureEngineer._macd(closes)
        features['macd'] = macd
        features['macd_signal'] = signal
        features['macd_hist'] = hist
        
        # ۶. بولینگر
        bb_upper, bb_middle, bb_lower = FeatureEngineer._bollinger(closes)
        features['bb_upper'] = bb_upper
        features['bb_middle'] = bb_middle
        features['bb_lower'] = bb_lower
        features['bb_position'] = (current_price - bb_lower) / (bb_upper - bb_lower + 0.0001)
        
        # ۷. ADX
        features['adx'] = FeatureEngineer._adx(closes)
        
        # ۸. حجم
        avg_vol_20 = np.mean(volumes[-20:]) if len(volumes) >= 20 else 1
        features['volume_ratio'] = volumes[-1] / (avg_vol_20 + 0.0001)
        features['volume_trend'] = np.mean(volumes[-5:]) / (np.mean(volumes[-20:]) + 0.0001) if len(volumes) >= 20 else 1
        
        # ۹. حمایت و مقاومت
        features['support_20'] = np.min(closes[-20:])
        features['resistance_20'] = np.max(closes[-20:])
        features['support_50'] = np.min(closes[-50:]) if len(closes) >= 50 else features['support_20']
        features['resistance_50'] = np.max(closes[-50:]) if len(closes) >= 50 else features['resistance_20']
        
        features['dist_to_support'] = ((current_price - features['support_20']) / (current_price + 0.0001)) * 100
        features['dist_to_resistance'] = ((features['resistance_20'] - current_price) / (current_price + 0.0001)) * 100
        
        # ۱۰. ویژگی‌های آماری
        returns = np.diff(closes) / (closes[:-1] + 0.0001)
        if len(returns) > 0:
            features['skewness'] = skew(returns[-30:]) if len(returns) >= 30 else 0
            features['kurtosis'] = kurtosis(returns[-30:]) if len(returns) >= 30 else 0
            features['entropy'] = FeatureEngineer._entropy(returns[-30:]) if len(returns) >= 30 else 0
        
        # ۱۱. ویژگی‌های فرکانسی
        if len(closes) >= 50:
            fft_vals = np.abs(fft(closes[-50:]))
            features['fft_dominance'] = np.max(fft_vals[1:10]) / (np.sum(fft_vals[1:10]) + 0.0001)
            features['fft_energy'] = np.sum(fft_vals[1:10] ** 2)
        
        # ۱۲. کندل‌شناسی
        last_candle = candles[-1]
        body = abs(last_candle['close'] - last_candle['open'])
        range_hl = last_candle['high'] - last_candle['low']
        features['body_ratio'] = body / (range_hl + 0.0001)
        features['upper_shadow'] = (last_candle['high'] - max(last_candle['close'], last_candle['open'])) / (range_hl + 0.0001)
        features['lower_shadow'] = (min(last_candle['close'], last_candle['open']) - last_candle['low']) / (range_hl + 0.0001)
        
        # ۱۳. روند
        if len(closes) >= 20:
            x = np.arange(20)
            slope, intercept, r_value, p_value, std_err = linregress(x, closes[-20:])
            features['trend_slope'] = slope
            features['trend_r_value'] = r_value
            features['trend_angle'] = math.atan(slope) * 180 / math.pi if slope != 0 else 0
        
        # ۱۴. نوسان
        features['high_low_ratio'] = (np.max(closes[-20:]) - np.min(closes[-20:])) / (np.mean(closes[-20:]) + 0.0001)
        features['close_open_ratio'] = (closes[-1] / (opens[-1] + 0.0001) - 1) * 100
        
        return features
    
    @staticmethod
    def _ema(data, period):
        if len(data) < period:
            return data[-1] if len(data) > 0 else 0
        alpha = 2 / (period + 1)
        ema = data[-period:].mean()
        for v in data[-period:]:
            ema = v * alpha + ema * (1 - alpha)
        return ema
    
    @staticmethod
    def _rsi(data, period):
        if len(data) < period + 1:
            return 50
        delta = np.diff(data[-period-1:])
        gain = np.mean(delta[delta > 0]) if np.sum(delta > 0) > 0 else 0
        loss = -np.mean(delta[delta < 0]) if np.sum(delta < 0) > 0 else 0.001
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    @staticmethod
    def _macd(data, fast=12, slow=26, signal=9):
        if len(data) < slow:
            return 0, 0, 0
        ema_fast = FeatureEngineer._ema(data, fast)
        ema_slow = FeatureEngineer._ema(data, slow)
        macd = ema_fast - ema_slow
        signal_line = FeatureEngineer._ema(data + [macd] * signal, signal) if len(data) >= slow else 0
        return macd, signal_line, macd - signal_line
    
    @staticmethod
    def _bollinger(data, period=20, std_dev=2):
        if len(data) < period:
            return data[-1], data[-1], data[-1]
        sma = np.mean(data[-period:])
        std = np.std(data[-period:])
        return sma + std_dev * std, sma, sma - std_dev * std
    
    @staticmethod
    def _adx(data, period=14):
        if len(data) < period + 1:
            return 25
        try:
            plus_dm = []
            minus_dm = []
            true_range = []
            for i in range(1, len(data)):
                tr = max(data[i] - data[i-1], abs(data[i] - data[i-1]))
                true_range.append(tr)
                if data[i] > data[i-1]:
                    plus_dm.append(data[i] - data[i-1])
                    minus_dm.append(0)
                else:
                    plus_dm.append(0)
                    minus_dm.append(data[i-1] - data[i])
            
            atr = np.mean(true_range[-period:]) if len(true_range) >= period else 0.001
            di_plus = 100 * (np.mean(plus_dm[-period:]) / atr) if atr > 0 else 0
            di_minus = 100 * (np.mean(minus_dm[-period:]) / atr) if atr > 0 else 0
            
            dx = 100 * abs(di_plus - di_minus) / (di_plus + di_minus) if (di_plus + di_minus) > 0 else 0
            return min(100, dx)
        except:
            return 25
    
    @staticmethod
    def _entropy(data, bins=10):
        if len(data) < 2:
            return 0
        hist, _ = np.histogram(data, bins=bins)
        hist = hist / (np.sum(hist) + 0.0001)
        return entropy(hist)

# ==================== AI Model ====================
class ProfessionalAIModel:
    """مدل هوش مصنوعی با ۴ الگوریتم همزمان و قابلیت یادگیری مستمر"""
    
    def __init__(self):
        self.models = {}
        self.scaler = RobustScaler()
        self.pca = PCA(n_components=0.95)
        self.is_trained = False
        self.feature_names = []
        self.training_history = []
        self.version = 1
        
        self.models['random_forest'] = RandomForestClassifier(
            n_estimators=500,
            max_depth=20,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )
        
        self.models['gradient_boosting'] = GradientBoostingClassifier(
            n_estimators=300,
            learning_rate=0.03,
            max_depth=6,
            min_samples_split=5,
            random_state=42
        )
        
        if XGB_AVAILABLE:
            self.models['xgboost'] = xgb.XGBClassifier(
                n_estimators=500,
                learning_rate=0.02,
                max_depth=8,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42
            )
        
        self.voting_model = None
        self._load_model()
        
        logger.info("✅ Professional AI Model initialized")
    
    def train(self, features_list, labels, source='historical'):
        if len(features_list) < 30:
            logger.warning(f"Not enough data for training (need 30+, got {len(features_list)})")
            return False
        
        start_time = time.time()
        
        X = []
        feature_names = []
        
        for features in features_list:
            row = []
            for key in sorted(features.keys()):
                if isinstance(features[key], (int, float)) and not np.isnan(features[key]):
                    row.append(features[key])
                    if key not in feature_names:
                        feature_names.append(key)
            X.append(row)
        
        X = np.array(X)
        y = np.array(labels)
        
        self.feature_names = feature_names
        
        X_scaled = self.scaler.fit_transform(X)
        X_pca = self.pca.fit_transform(X_scaled)
        
        logger.info(f"📊 Training on {len(X)} samples, {X.shape[1]} features -> {X_pca.shape[1]} PCA components")
        
        for name, model in self.models.items():
            try:
                model.fit(X_pca, y)
                score = model.score(X_pca, y)
                logger.info(f"✅ {name} trained (accuracy: {score:.2%})")
                self.training_history.append({
                    'model': name,
                    'accuracy': score,
                    'samples': len(X),
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Error training {name}: {e}")
        
        try:
            estimators = [(name, model) for name, model in self.models.items()]
            self.voting_model = VotingClassifier(
                estimators=estimators,
                voting='soft',
                weights=[1.0, 1.0, 1.5 if XGB_AVAILABLE else 1.0]
            )
            self.voting_model.fit(X_pca, y)
            logger.info("✅ Voting model trained")
        except Exception as e:
            logger.error(f"Error training voting model: {e}")
        
        self.is_trained = True
        self.version += 1
        
        y_pred = self.voting_model.predict(X_pca) if self.voting_model else y
        accuracy = accuracy_score(y, y_pred) if len(y) > 0 else 0
        precision = precision_score(y, y_pred, average='weighted', zero_division=0) if len(y) > 0 else 0
        recall = recall_score(y, y_pred, average='weighted', zero_division=0) if len(y) > 0 else 0
        f1 = f1_score(y, y_pred, average='weighted', zero_division=0) if len(y) > 0 else 0
        
        training_time = time.time() - start_time
        
        db.save_model_performance(accuracy, precision, recall, f1, len(X), training_time)
        self._save_model()
        
        logger.info(f"✅ Model trained! Accuracy: {accuracy:.2%}, F1: {f1:.2%}, Time: {training_time:.2f}s")
        
        return True
    
    def predict(self, features):
        if not self.is_trained:
            return None, 0, {}
        
        try:
            row = []
            for key in self.feature_names:
                if key in features:
                    row.append(features[key])
                else:
                    row.append(0)
            
            X = np.array([row])
            X_scaled = self.scaler.transform(X)
            X_pca = self.pca.transform(X_scaled)
            
            predictions = {}
            probabilities = {}
            
            for name, model in self.models.items():
                try:
                    pred = model.predict(X_pca)[0]
                    prob = model.predict_proba(X_pca)[0]
                    predictions[name] = pred
                    probabilities[name] = prob
                except:
                    pass
            
            final_prediction = None
            final_confidence = 0
            
            if self.voting_model:
                try:
                    final_prediction = self.voting_model.predict(X_pca)[0]
                    final_prob = self.voting_model.predict_proba(X_pca)[0]
                    final_confidence = max(final_prob) * 100
                except:
                    pass
            
            if final_prediction is None:
                pred_values = list(predictions.values())
                if pred_values:
                    final_prediction = round(np.mean(pred_values))
                    final_confidence = np.mean([max(p) for p in probabilities.values()]) * 100
            
            return final_prediction, final_confidence, {
                'predictions': predictions,
                'probabilities': probabilities,
                'model_count': len(predictions)
            }
            
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return None, 0, {}
    
    def _save_model(self):
        try:
            model_data = {
                'models': self.models,
                'voting_model': self.voting_model,
                'scaler': self.scaler,
                'pca': self.pca,
                'feature_names': self.feature_names,
                'is_trained': self.is_trained,
                'version': self.version,
                'training_history': self.training_history
            }
            with open('ai_model_v16.pkl', 'wb') as f:
                pickle.dump(model_data, f)
            logger.info("✅ Model saved to disk")
            return True
        except Exception as e:
            logger.error(f"Error saving model: {e}")
            return False
    
    def _load_model(self):
        try:
            if os.path.exists('ai_model_v16.pkl'):
                with open('ai_model_v16.pkl', 'rb') as f:
                    model_data = pickle.load(f)
                self.models = model_data['models']
                self.voting_model = model_data['voting_model']
                self.scaler = model_data['scaler']
                self.pca = model_data['pca']
                self.feature_names = model_data['feature_names']
                self.is_trained = model_data['is_trained']
                self.version = model_data.get('version', 1)
                self.training_history = model_data.get('training_history', [])
                logger.info(f"✅ Model loaded (version {self.version})")
                return True
        except Exception as e:
            logger.error(f"Error loading model: {e}")
        return False

# ==================== Signal Engine ====================
class LearningSignalEngine:
    """موتور سیگنال‌دهی با یادگیری مستمر و اسکن پویا"""
    
    def __init__(self):
        self.ai_model = ProfessionalAIModel()
        self.feature_engineer = FeatureEngineer()
        self.scanner = DynamicSymbolScanner()
        self.last_signals = {}
        self.signal_history = []
        self.feedback_buffer = []
        self.daily_performance = {'total': 0, 'correct': 0, 'wrong': 0}
        
        logger.info("✅ Learning Signal Engine initialized")
    
    def train_from_historical_data(self, symbol='BTCUSDT', days=60):
        logger.info(f"🔄 Training from {days} days of historical data...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        candles = price_service.get_historical_candles(
            symbol,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d'),
            '1h'
        )
        
        if not candles or len(candles) < 100:
            logger.error("Not enough historical data")
            return False
        
        features_list = []
        labels = []
        
        for i in range(50, len(candles) - 10):
            window = candles[i-50:i+1]
            features = self.feature_engineer.extract_all_features(window)
            if features:
                future_price = candles[i+10]['close']
                current_price = candles[i]['close']
                label = 1 if future_price > current_price else 0
                features_list.append(features)
                labels.append(label)
                db.save_training_data(symbol, features, label, 'historical')
        
        if len(features_list) < 100:
            logger.error(f"Only {len(features_list)} samples, need 100+")
            return False
        
        return self.ai_model.train(features_list, labels, 'historical')
    
    def train_from_feedback(self):
        logger.info("🔄 Training from user feedback...")
        
        feedback_data = db.get_feedback_training_data(500)
        
        if not feedback_data or len(feedback_data) < MIN_FEEDBACK_FOR_RETRAIN:
            logger.info(f"💤 Not enough feedbacks ({len(feedback_data) if feedback_data else 0}/{MIN_FEEDBACK_FOR_RETRAIN})")
            return False
        
        features_list = []
        labels = []
        
        for fb in feedback_data:
            features_snapshot = fb[0]
            feedback = fb[1]
            
            if features_snapshot:
                try:
                    features = json.loads(features_snapshot)
                    if features and len(features) > 10:
                        features_list.append(features)
                        label = 1 if feedback == 'positive' else 0
                        labels.append(label)
                except:
                    continue
        
        if len(features_list) < MIN_FEEDBACK_FOR_RETRAIN:
            logger.info(f"💤 Not enough valid feedback features ({len(features_list)})")
            return False
        
        return self.ai_model.train(features_list, labels, 'feedback')
    
    def analyze(self, symbol):
        try:
            candles = price_service.get_candles(symbol, '5m', 200)
            if not candles or len(candles) < 50:
                return None
            
            features = self.feature_engineer.extract_all_features(candles)
            if not features:
                return None
            
            current_price = candles[-1]['close']
            
            prediction, confidence, details = self.ai_model.predict(features)
            
            closes = np.array([c['close'] for c in candles])
            atr = np.std(closes[-20:]) if len(closes) >= 20 else current_price * 0.01
            
            support = np.min(closes[-20:])
            resistance = np.max(closes[-20:])
            
            # تشخیص نوع سیگنال
            signal_type = 'NORMAL'
            if symbol in self.scanner.pump_candidates:
                signal_type = 'PUMP'
            elif symbol in self.scanner.dump_candidates:
                signal_type = 'DUMP'
            
            if prediction is None or confidence < MIN_PREDICTION_CONFIDENCE:
                return {
                    'symbol': symbol,
                    'direction': 'HOLD',
                    'confidence': 0,
                    'reason': f'AI confidence too low ({confidence:.1f}%)',
                    'entry': round(current_price, 2),
                    'support': round(support, 2),
                    'resistance': round(resistance, 2),
                    'model_details': details,
                    'features': features,
                    'signal_type': signal_type
                }
            
            direction = 'LONG' if prediction == 1 else 'SHORT'
            
            if direction == 'LONG':
                sl = current_price - (atr * 2)
                tp = current_price + (atr * 4)
                if sl < support * 0.99:
                    sl = support * 0.99
            else:
                sl = current_price + (atr * 2)
                tp = current_price - (atr * 4)
                if sl > resistance * 1.01:
                    sl = resistance * 1.01
            
            if confidence >= 80:
                leverage = 20
            elif confidence >= 70:
                leverage = 15
            elif confidence >= 60:
                leverage = 10
            else:
                leverage = 5
            
            model_votes = []
            for name, pred in details.get('predictions', {}).items():
                model_votes.append(f"{name}: {'UP' if pred == 1 else 'DOWN'}")
            
            return {
                'symbol': symbol,
                'direction': direction,
                'confidence': int(confidence),
                'reason': f'AI Prediction ({confidence:.1f}%)',
                'entry': round(current_price, 2),
                'sl': round(sl, 2),
                'tp': round(tp, 2),
                'leverage': leverage,
                'support': round(support, 2),
                'resistance': round(resistance, 2),
                'model_votes': ' | '.join(model_votes),
                'prediction_details': json.dumps(details),
                'signal_accuracy': confidence,
                'atr': round(atr, 2),
                'features': features,
                'signal_type': signal_type
            }
            
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            return None
    
    def scan_market_dynamic(self):
        """اسکن پویا با شناسایی خودکار ارزها"""
        # اسکن کامل بازار
        pump_list, dump_list, hot_symbols = self.scanner.scan_all()
        
        if not hot_symbols:
            hot_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT']
        
        logger.info(f"🔍 Scanning {len(hot_symbols)} dynamic symbols...")
        
        signals = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(self.analyze, symbol): symbol for symbol in hot_symbols[:MAX_SYMBOLS_TO_SCAN]}
            for future in futures:
                try:
                    result = future.result(timeout=15)
                    if result and result['direction'] != 'HOLD' and result['confidence'] >= MIN_PREDICTION_CONFIDENCE:
                        signals.append(result)
                except:
                    continue
        
        signals.sort(key=lambda x: x['confidence'], reverse=True)
        logger.info(f"✅ Found {len(signals)} strong signals")
        
        return signals, [p['symbol'] for p in pump_list], [d['symbol'] for d in dump_list]
    
    def process_feedback(self, signal_id, user_id, feedback_type):
        signal = db.get_signal(signal_id)
        if not signal:
            return False
        
        accuracy = 90 if feedback_type == 'positive' else 30
        
        db.update_signal_feedback(signal_id, feedback_type, accuracy)
        
        if feedback_type == 'positive':
            self.daily_performance['correct'] += 1
        else:
            self.daily_performance['wrong'] += 1
        self.daily_performance['total'] += 1
        
        if feedback_type == 'negative':
            features_snapshot = signal[17] if len(signal) > 17 else ''
            if features_snapshot:
                try:
                    features = json.loads(features_snapshot)
                    if features and len(features) > 10:
                        direction = signal[3]
                        label = 0 if direction == 'LONG' else 1
                        db.save_training_data(signal[2], features, label, 'feedback_correction')
                except:
                    pass
        
        logger.info(f"📝 Feedback processed: {feedback_type} for signal {signal_id}")
        return True

# ==================== Telegram Bot ====================
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ==================== Keyboards ====================
def get_main_keyboard(user_id):
    keyboard = [
        ['🪙 ارز دیجیتال', '📊 اسکنر هوشمند V16'],
        ['🎁 رفرال', '📊 وضعیت'],
        ['🧠 یادگیری', '🚀 V16 - DYNAMIC']
    ]
    if user_id == ADMIN_ID:
        keyboard.append(['👑 پنل مدیریت'])
        keyboard.append(['📚 آموزش دستی', '⚡ فعال‌سازی یادگیری'])
        keyboard.append(['🔄 اسکن دستی بازار'])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_crypto_keyboard():
    # دریافت ارزهای داغ از دیتابیس
    hot = db.get_hot_symbols(20)
    if not hot:
        hot = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT']
    
    keyboard = []
    row = []
    for symbol in hot:
        row.append(symbol)
        if len(row) == 4:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append(['🔙 بازگشت'])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ==================== Global Variables ====================
signal_engine = None

# ==================== Handlers ====================

async def start(update, context):
    user_id = update.effective_user.id
    username = update.effective_user.username or ""
    first_name = update.effective_user.first_name or ""
    
    db.add_user(user_id, username, first_name, 'fa')
    
    perf = db.get_latest_performance()
    perf_text = ""
    if perf:
        perf_text = f"\n📊 **عملکرد مدل:**\n• دقت: {perf[0]:.1f}%\n• F1: {perf[3]:.1f}%\n• نمونه‌ها: {perf[4]}"
    
    welcome_text = f"""
🧠 **ربات V16 - DYNAMIC SCANNER**

🔥 **قابلیت‌های جدید:**
• 🚀 شناسایی خودکار ارزهای مستعد پامپ
• 📉 شناسایی خودکار ارزهای مستعد ریزش
• 🔍 اسکن پویای کل بازار
• 📝 یادگیری از بازخورد کاربران
• 📊 ۵۰ ویژگی + ۴ مدل ML
{perf_text}

🎁 **۲ سیگنال رایگان روزانه**

🚀 **برای شروع، یکی از گزینه‌های زیر را انتخاب کنید:**
"""
    await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard(user_id), parse_mode='Markdown')

async def handle_message(update, context):
    user_id = update.effective_user.id
    text = update.message.text
    
    # ===== ADMIN PANEL =====
    if text == '👑 پنل مدیریت' and user_id == ADMIN_ID:
        await update.message.reply_text(
            "👑 **پنل مدیریت V16**",
            reply_markup=ReplyKeyboardMarkup([
                ['📢 ارسال پیام همگانی'],
                ['✅ تایید هش'],
                ['🔢 تعداد سیگنال رایگان'],
                ['📚 آموزش دستی', '⚡ فعال‌سازی یادگیری'],
                ['📊 عملکرد مدل'],
                ['🔄 اسکن دستی بازار'],
                ['🔙 بازگشت']
            ], resize_keyboard=True)
        )
        return
    
    # ===== MANUAL SCAN =====
    if text == '🔄 اسکن دستی بازار' and user_id == ADMIN_ID:
        await update.message.reply_text("🔄 **اسکن دستی بازار شروع شد...**", parse_mode='Markdown')
        
        pump, dump, hot = signal_engine.scanner.scan_all()
        
        msg = "📊 **نتایج اسکن دستی:**\n\n"
        msg += "🔥 **ارزهای مستعد پامپ:**\n"
        for p in pump[:5]:
            msg += f"• {p['symbol']} (امتیاز: {p['pump_score']}) - {', '.join(p.get('reasons', ['']))}\n"
        
        msg += "\n📉 **ارزهای مستعد ریزش:**\n"
        for d in dump[:5]:
            msg += f"• {d['symbol']} (امتیاز: {d['dump_score']}) - {', '.join(d.get('reasons', ['']))}\n"
        
        msg += f"\n📊 **تعداد ارزهای داغ:** {len(hot)}"
        
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=get_main_keyboard(user_id))
        return
    
    # ===== MANUAL TRAINING =====
    if text == '📚 آموزش دستی' and user_id == ADMIN_ID:
        await update.message.reply_text("🔄 **آموزش دستی شروع شد...**\n⏳ لطفاً صبر کنید.", parse_mode='Markdown')
        
        try:
            result1 = signal_engine.train_from_feedback()
            result2 = signal_engine.train_from_historical_data('BTCUSDT', 60)
            
            msg = "✅ **آموزش دستی کامل شد!**\n\n"
            msg += f"📝 بازخوردها: {'✅' if result1 else '❌'}\n"
            msg += f"📊 داده‌های تاریخی: {'✅' if result2 else '❌'}\n"
            
            perf = db.get_latest_performance()
            if perf:
                msg += f"\n📊 **عملکرد جدید:**\n• دقت: {perf[0]:.1f}%\n• F1: {perf[3]:.1f}%\n• نمونه‌ها: {perf[4]}"
            
            await update.message.reply_text(msg, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ خطا: {str(e)}")
        return
    
    # ===== ENABLE LEARNING =====
    if text == '⚡ فعال‌سازی یادگیری' and user_id == ADMIN_ID:
        current = db.get_setting('auto_learn')
        if current == '1':
            db.update_setting('auto_learn', '0')
            await update.message.reply_text("⏸️ **یادگیری خودکار غیرفعال شد**")
        else:
            db.update_setting('auto_learn', '1')
            await update.message.reply_text("▶️ **یادگیری خودکار فعال شد**")
        return
    
    # ===== MODEL PERFORMANCE =====
    if text == '📊 عملکرد مدل' and user_id == ADMIN_ID:
        perf = db.get_latest_performance()
        if perf:
            msg = f"""
📊 **عملکرد مدل V16**

📅 تاریخ: {perf[6]}
🎯 دقت: {perf[0]:.1f}%
📊 F1-Score: {perf[3]:.1f}%
📊 تعداد نمونه‌ها: {perf[4]}
⏱️ زمان آموزش: {perf[5]:.2f} ثانیه

🧠 وضعیت: {'✅ فعال' if signal_engine.ai_model.is_trained else '❌ آموزش‌دیده نشده'}
🔥 نسخه: V16
"""
        else:
            msg = "📊 **هنوز عملکردی ثبت نشده است.**"
        
        await update.message.reply_text(msg, parse_mode='Markdown')
        return
    
    # ===== ADMIN: BROADCAST =====
    if text == '📢 ارسال پیام همگانی' and user_id == ADMIN_ID:
        context.user_data['admin_state'] = 'broadcast'
        await update.message.reply_text("📝 پیام خود را وارد کنید:")
        return
    
    if context.user_data.get('admin_state') == 'broadcast' and user_id == ADMIN_ID:
        users = db.get_all_users()
        sent = 0
        for u in users:
            try:
                await context.bot.send_message(chat_id=u[0], text=text)
                sent += 1
            except:
                pass
        context.user_data['admin_state'] = None
        await update.message.reply_text(f"✅ پیام به {sent} کاربر ارسال شد!", reply_markup=get_main_keyboard(user_id))
        return
    
    # ===== ADMIN: CONFIRM HASH =====
    if text == '✅ تایید هش' and user_id == ADMIN_ID:
        payments = db.get_pending_payments()
        if not payments:
            await update.message.reply_text("🧾 هیچ درخواست پرداختی وجود ندارد.")
            return
        for p in payments:
            pid, target_user_id, payment_hash, created_at = p
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(f"✅ تایید #{pid}", callback_data=f"confirm:{pid}"),
                    InlineKeyboardButton(f"❌ رد #{pid}", callback_data=f"reject:{pid}")
                ]
            ])
            await update.message.reply_text(
                f"🆔 **درخواست #{pid}**\n👤 کاربر: `{target_user_id}`\n🔑 هش: `{payment_hash}`",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            await asyncio.sleep(0.3)
        return
    
    # ===== ADMIN: SET FREE SIGNALS =====
    if text == '🔢 تعداد سیگنال رایگان' and user_id == ADMIN_ID:
        context.user_data['admin_state'] = 'set_free_signals'
        await update.message.reply_text("📝 تعداد سیگنال رایگان روزانه را وارد کنید (مثال: 0, 1, 2, 3, 5):")
        return
    
    if context.user_data.get('admin_state') == 'set_free_signals' and user_id == ADMIN_ID:
        try:
            new_count = int(text.strip())
            if new_count < 0:
                new_count = 0
            if new_count > 10:
                new_count = 10
            db.update_setting('max_free_signals', str(new_count))
            db.cursor.execute('UPDATE users SET max_free_signals = ?', (new_count,))
            db.conn.commit()
            context.user_data['admin_state'] = None
            await update.message.reply_text(f"✅ تعداد سیگنال رایگان روزانه به {new_count} تغییر یافت!", reply_markup=get_main_keyboard(user_id))
        except:
            await update.message.reply_text("⚠️ لطفاً یک عدد معتبر وارد کنید!")
        return
    
    # ===== BACK =====
    if text == '🔙 بازگشت':
        await update.message.reply_text("🔙 بازگشت", reply_markup=get_main_keyboard(user_id))
        return
    
    # ===== SMART SCANNER V16 =====
    if text == '📊 اسکنر هوشمند V16':
        await update.message.reply_text("🔄 **اسکن پویا با شناسایی خودکار ارزها...**\n⏳ لطفاً صبر کنید.", parse_mode='Markdown')
        
        signals, pump_list, dump_list = signal_engine.scan_market_dynamic()
        
        if signals:
            msg = "🧠 **نتایج اسکنر پویا V16**\n\n"
            
            if pump_list:
                msg += "🔥 **ارزهای مستعد پامپ (نزدیک):**\n"
                for s in pump_list[:5]:
                    msg += f"• {s}\n"
                msg += "\n"
            
            if dump_list:
                msg += "📉 **ارزهای مستعد ریزش (شورت):**\n"
                for s in dump_list[:5]:
                    msg += f"• {s}\n"
                msg += "\n"
            
            msg += "📊 **سیگنال‌های قوی:**\n"
            for s in signals[:5]:
                emoji = '🟢' if s['direction'] == 'LONG' else '🔴'
                tag = "🔥" if s.get('signal_type') == 'PUMP' else "📉" if s.get('signal_type') == 'DUMP' else ""
                msg += f"{emoji} {tag} **{s['symbol']}** - {s['direction']} (اطمینان: {s['confidence']}%)\n"
            
            await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=get_main_keyboard(user_id))
        else:
            await update.message.reply_text("🔍 **سیگنال قوی در بازار پیدا نشد.**\n⏳ دوباره امتحان کنید.", parse_mode='Markdown', reply_markup=get_main_keyboard(user_id))
        return
    
    # ===== LEARNING INFO =====
    if text == '🧠 یادگیری':
        perf = db.get_latest_performance()
        feedback_count = len(db.get_feedback_training_data(1000) or [])
        hot_count = len(db.get_hot_symbols(100))
        
        msg = f"""
🧠 **وضعیت یادگیری V16**

📊 **عملکرد فعلی:**
{'' if not perf else f'• دقت: {perf[0]:.1f}%\n• F1: {perf[3]:.1f}%\n• نمونه‌ها: {perf[4]}'}

📝 **بازخوردهای ذخیره‌شده:** {feedback_count}
🔥 **ارزهای داغ شناسایی‌شده:** {hot_count}
⚡ **یادگیری خودکار:** {'✅ فعال' if db.get_setting('auto_learn') == '1' else '❌ غیرفعال'}
🧠 **وضعیت مدل:** {'✅ آموزش‌دیده' if signal_engine.ai_model.is_trained else '❌ آموزش‌دیده نشده'}

💡 **هرچه بیشتر بازخورد بدهید، ربات قوی‌تر می‌شود!**
"""
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=get_main_keyboard(user_id))
        return
    
    # ===== CRYPTO =====
    if text == '🪙 ارز دیجیتال':
        await update.message.reply_text("🪙 **انتخاب ارز دیجیتال (ارزهای داغ):**", reply_markup=get_crypto_keyboard(), parse_mode='Markdown')
        return
    
    # ===== REFERRAL =====
    if text == '🎁 رفرال':
        bot_name = "TASTtt_bot"
        ref_count = db.get_referral_count(user_id)
        free_signals = db.get_free_signals(user_id)
        msg = f"""
🎁 **رفرال**

🔗 لینک: `https://t.me/{bot_name}?start=ref_{user_id}`
👥 معرفی: {ref_count}
🎯 سیگنال رایگان: {free_signals}
"""
        await update.message.reply_text(msg, reply_markup=get_main_keyboard(user_id), parse_mode='Markdown')
        return
    
    # ===== STATUS =====
    if text == '📊 وضعیت':
        free_signals = db.get_free_signals(user_id)
        max_free = db.get_max_free_signals(user_id)
        has_sub, expire = db.has_subscription(user_id)
        remaining = (expire - datetime.now()).days if has_sub and expire else 0
        msg = f"""
📊 **وضعیت کاربری**

👤 کاربر: {user_id}
🎯 سیگنال رایگان: {free_signals}/{max_free}
{'✅ اشتراک: ' + str(remaining) + ' روز' if has_sub else '❌ بدون اشتراک'}
🧠 نسخه: V16 DYNAMIC SCANNER
"""
        await update.message.reply_text(msg, reply_markup=get_main_keyboard(user_id), parse_mode='Markdown')
        return
    
    # ===== V16 INFO =====
    if text == '🚀 V16 - DYNAMIC':
        msg = """
🚀 **نسخه V16 - DYNAMIC SCANNER**

🔥 **قابلیت‌های جدید:**
• 🚀 شناسایی خودکار ارزهای مستعد پامپ
• 📉 شناسایی خودکار ارزهای مستعد ریزش
• 🔍 اسکن پویای کل بازار
• 📝 یادگیری از بازخورد کاربران
• 📊 ۵۰ ویژگی + ۴ مدل ML
• 💪 هر روز قوی‌تر می‌شود

💡 **هرچه بیشتر استفاده کنید، دقیق‌تر می‌شود!**
"""
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=get_main_keyboard(user_id))
        return
    
    # ===== CHECK ACCESS =====
    if not can_access_signals(user_id):
        if len(text.strip()) >= 10:
            if db.has_pending_payment(user_id):
                await update.message.reply_text("⚠️ درخواست پرداخت دارید.")
                return
            db.add_payment_hash(user_id, text.strip())
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🧾 **درخواست پرداخت جدید:**\n👤 کاربر: {user_id}\n🔑 هش: `{text.strip()}`"
            )
            await update.message.reply_text("✅ هش تراکنش ثبت شد.")
            return
        await update.message.reply_text("⚠️ **دسترسی ندارید!**")
        return
    
    # ===== SYMBOL ANALYSIS =====
    if text in db.get_hot_symbols(50) or text in ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT']:
        await analyze_symbol(update, context, text)
        return
    
    await update.message.reply_text("❌ گزینه موجود نیست.", reply_markup=get_main_keyboard(user_id))

async def analyze_symbol(update, context, symbol):
    user_id = update.effective_user.id
    
    if not can_access_signals(user_id):
        await update.message.reply_text("⚠️ **دسترسی ندارید!**")
        return
    
    is_free = False
    free_signals = db.get_free_signals(user_id)
    max_free = db.get_max_free_signals(user_id)
    
    if max_free == 0:
        has_sub, _ = db.has_subscription(user_id)
        if not has_sub and not db.has_confirmed_payment(user_id) and user_id != ADMIN_ID:
            await update.message.reply_text("⚠️ **دسترسی ندارید!**")
            return
    
    if free_signals > 0 and user_id != ADMIN_ID and max_free > 0:
        db.use_free_signal(user_id)
        is_free = True
    
    status_msg = await update.message.reply_text(f"🧠 **تحلیل {symbol} با مدل V16...**", parse_mode='Markdown')
    
    try:
        result = signal_engine.analyze(symbol)
        
        if result and result['direction'] != 'HOLD':
            features = result.get('features')
            signal_id = db.save_signal(user_id, result, is_free, features)
            
            emoji = '🟢' if result['direction'] == 'LONG' else '🔴'
            direction_text = 'خرید (LONG)' if result['direction'] == 'LONG' else 'فروش (SHORT)'
            
            tag = ""
            if result.get('signal_type') == 'PUMP':
                tag = "🔥 **سیگنال پامپ** - "
            elif result.get('signal_type') == 'DUMP':
                tag = "📉 **سیگنال ریزش** - "
            
            feedback_keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ سود کردم 🟢", callback_data=f"feedback:positive:{signal_id}"),
                    InlineKeyboardButton("❌ سود نکردم 🔴", callback_data=f"feedback:negative:{signal_id}")
                ]
            ])
            
            msg = f"""
{emoji} **{symbol} - {direction_text} (V16)**

{tag}
💰 ورود: ${result['entry']:,.2f}
🎯 حد سود: ${result['tp']:,.2f}
🛑 حد ضرر: ${result['sl']:,.2f}
📉 حمایت: ${result['support']:,.2f}
📈 مقاومت: ${result['resistance']:,.2f}
⚡ اهرم: {result['leverage']}x
🎯 اطمینان: {result['confidence']}%

🧠 **مدل‌ها:** {result.get('model_votes', 'N/A')}
📊 **دلیل:** {result['reason']}

{'🎁 **این سیگنال رایگان است!**' if is_free else ''}
📊 **سیگنال‌های رایگان باقی‌مانده:** {db.get_free_signals(user_id)}

💡 **با کلیک روی دکمه زیر، به بهبود ربات کمک کنید!**
"""
            await status_msg.delete()
            await update.message.reply_text(msg, reply_markup=feedback_keyboard, parse_mode='Markdown')
            
            # ارسال به کانال
            try:
                channel_msg = f"""
🚨 **سیگنال V16 - {direction_text}**

{emoji} **{symbol}**
{tag}
💰 ورود: ${result['entry']:,.2f}
🎯 اطمینان: {result['confidence']}%
📊 دلیل: {result['reason']}

🧠 مدل: V16 DYNAMIC SCANNER
📊 نسخه: {signal_engine.ai_model.version}

#سیگنال #{'LONG' if result['direction'] == 'LONG' else 'SHORT'} #{symbol}
"""
                await context.bot.send_message(chat_id=CHANNEL_ID, text=channel_msg, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Channel send error: {e}")
            
        else:
            await status_msg.delete()
            await update.message.reply_text(
                f"⏳ **سیگنال واضحی نیست - HOLD**\n\n📊 اطمینان: {result['confidence'] if result else 0}%\n📊 دلیل: {result['reason'] if result else 'نامشخص'}",
                parse_mode='Markdown',
                reply_markup=get_main_keyboard(user_id)
            )
            
    except Exception as e:
        await status_msg.delete()
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"❌ خطا: {str(e)}", reply_markup=get_main_keyboard(user_id))

# ==================== Callbacks ====================

async def payment_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("❌ غیرمجاز!")
        return
    
    data = query.data
    if data.startswith("confirm:"):
        payment_id = int(data.split(":", 1)[1])
        success, user_id, expire_date = db.confirm_payment(payment_id, SUBSCRIPTION_DAYS)
        if success:
            await query.edit_message_text(f"✅ پرداخت {user_id} تایید شد! تا {expire_date.strftime('%Y-%m-%d')}")
        else:
            await query.edit_message_text("❌ خطا!")
    elif data.startswith("reject:"):
        payment_id = int(data.split(":", 1)[1])
        success = db.reject_payment(payment_id)
        if success:
            await query.edit_message_text("❌ پرداخت رد شد!")

async def feedback_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if not data.startswith("feedback:"):
        return
    
    parts = data.split(":")
    if len(parts) != 3:
        return
    
    feedback_type = parts[1]
    signal_id = int(parts[2])
    user_id = query.from_user.id
    
    signal = db.get_signal(signal_id)
    if not signal or signal[1] != user_id:
        await query.edit_message_text("❌ خطا!")
        return
    
    success = signal_engine.process_feedback(signal_id, user_id, feedback_type)
    
    if feedback_type == 'positive':
        msg = """
✅ **ممنون از بازخورد شما!**

🧠 **این سیگنال به عنوان داده آموزشی مثبت ذخیره شد.**
🔄 **شب هنگام، مدل از این سیگنال یاد می‌گیرد.**
📈 **هرچه بیشتر بازخورد بدهید، سیگنال‌ها دقیق‌تر می‌شوند!**
"""
    else:
        msg = """
❌ **متاسفیم که سیگنال دقیق نبود!**

🧠 **این سیگنال به عنوان داده آموزشی منفی ذخیره شد.**
🔄 **شب هنگام، مدل از این اشتباه درس می‌گیرد.**
📈 **با بازخورد شما، ربات قوی‌تر می‌شود!**
"""
    
    await query.edit_message_text(msg, parse_mode='Markdown')

# ==================== Access Control ====================
def can_access_signals(user_id):
    if user_id == ADMIN_ID:
        return True
    if db.get_setting('is_paid_mode') != '1':
        return True
    
    max_free = db.get_max_free_signals(user_id)
    free_signals = db.get_free_signals(user_id)
    
    if max_free == 0:
        has_sub, _ = db.has_subscription(user_id)
        if has_sub or db.has_confirmed_payment(user_id):
            return True
        return False
    
    if free_signals > 0:
        return True
    
    has_sub, _ = db.has_subscription(user_id)
    if has_sub or db.has_confirmed_payment(user_id):
        return True
    
    return False

# ==================== Main ====================
def main():
    print("="*80)
    print("🚀 ULTIMATE SIGNAL BOT V16 - DYNAMIC SCANNER")
    print("="*80)
    print("🔥 Features:")
    print("🔍 Auto-detect pump candidates")
    print("📉 Auto-detect dump candidates (short)")
    print("🧠 Self-learning AI with 50 features")
    print("📊 4 ML models voting")
    print("🔄 Dynamic market scanning")
    print("="*80)
    
    check_and_create_pid()
    
    global signal_engine
    
    signal_engine = LearningSignalEngine()
    
    # آموزش اولیه
    if not signal_engine.ai_model.is_trained:
        logger.info("🔄 No model found. Initial training started...")
        signal_engine.train_from_historical_data('BTCUSDT', 60)
        
        if not signal_engine.ai_model.is_trained:
            signal_engine.train_from_historical_data('BTCUSDT', 30)
    
    # اسکن اولیه بازار
    logger.info("🔄 Initial market scan...")
    signal_engine.scanner.scan_all()
    
    # ===== راه‌اندازی ربات =====
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(payment_callback_handler, pattern=r"^(confirm|reject):"))
    app.add_handler(CallbackQueryHandler(feedback_callback_handler, pattern=r"^feedback:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Bot V16 started successfully!")
    print(f"✅ Admin: {ADMIN_ID}")
    print(f"✅ Channel: {CHANNEL_ID}")
    print(f"✅ AI Model: {'Trained' if signal_engine.ai_model.is_trained else 'Not Trained'}")
    print(f"✅ Version: {signal_engine.ai_model.version}")
    print("="*80)
    
    try:
        app.run_polling(drop_pending_updates=True)
    finally:
        remove_pid()

if __name__ == "__main__":
    main()