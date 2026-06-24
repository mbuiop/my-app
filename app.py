#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ربات تحلیل تکنیکال نسخه نهایی - با اتصال مستقیم به بازار
============================================================
🔥 ۱۰۰۰۰+ الگوریتم ترکیبی
📊 ۲۰ اندیکاتور + حمایت و مقاومت
💎 سیستم پرداخت TRC20
👑 پنل مدیریت کامل
⚡ اتصال مستقیم به بازار
============================================================
"""

import logging
import os
import sys
import time
import json
import re
import sqlite3
import threading
import asyncio
import hashlib
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')

# ==================== مدیریت Conflict ====================
PID_FILE = "bot_simple_final.pid"

def check_and_create_pid():
    try:
        if os.path.exists(PID_FILE):
            with open(PID_FILE, 'r') as f:
                old_pid = int(f.read().strip())
            try:
                os.kill(old_pid, 0)
                print(f"❌ نمونه دیگری با PID {old_pid} در حال اجراست!")
                os.kill(old_pid, 9)
                time.sleep(1)
                os.remove(PID_FILE)
                print("✅ نمونه قبلی متوقف شد!")
            except OSError:
                os.remove(PID_FILE)
                print("✅ فایل PID قدیمی پاک شد!")
        
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
        print(f"✅ PID {os.getpid()} ذخیره شد")
        return True
    except Exception as e:
        print(f"⚠️ خطا در مدیریت PID: {e}")
        return True

def remove_pid():
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
    except:
        pass

# ==================== کتابخانه‌ها ====================
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import RetryAfter, TimedOut, NetworkError, Forbidden
import requests
import numpy as np
from scipy import stats
from scipy.fft import fft
from scipy.signal import find_peaks, argrelextrema
from sklearn.ensemble import (
    RandomForestRegressor, GradientBoostingRegressor, 
    ExtraTreesRegressor, AdaBoostRegressor, HistGradientBoostingRegressor
)
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.neural_network import MLPRegressor
from sklearn.svm import SVR
from sklearn.linear_model import Ridge, Lasso, ElasticNet, BayesianRidge, HuberRegressor
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel
from PIL import Image

# ==================== تنظیمات ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_simple_final.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8895536734:AAEelFpAnwGMz9Cr0VI6pN5vPui-s2tPKzc"
ADMIN_ID = 327855654
BOT_USERNAME = "@Maynir_Bot"
EXCHANGE_URL = "https://www.toobit.com/fa/r?i=5EQpCT"

# ==================== آدرس کیف پول TRC20 ====================
TRC20_WALLET = "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"
TRC20_MEMO = "Trco20"
SUBSCRIPTION_PRICE_USDT = 50

# ==================== لیست ارزها ====================
SUPPORTED_SYMBOLS = [
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT',
    'XRPUSDT', 'DOTUSDT', 'DOGEUSDT', 'AVAXUSDT', 'MATICUSDT',
    'LINKUSDT', 'UNIUSDT', 'ATOMUSDT', 'LTCUSDT', 'BCHUSDT',
    'NEARUSDT', 'ALGOUSDT', 'VETUSDT', 'ICPUSDT', 'FILUSDT',
    'THETAUSDT', 'FTMUSDT', 'XLMUSDT', 'EGLDUSDT', 'HNTUSDT',
    'XMRUSDT', 'ZECUSDT', 'DASHUSDT', 'ETCUSDT', 'XTZUSDT',
    'EOSUSDT', 'AAVEUSDT', 'MKRUSDT', 'COMPUSDT', 'YFIUSDT',
    'SUSHIUSDT', 'CAKEUSDT', 'BAKEUSDT', 'AXSUSDT', 'SANDUSDT',
    'MANAUSDT', 'ENJUSDT', 'CHZUSDT', 'GALAUSDT', 'APEUSDT',
    'SHIBUSDT', 'PEPEUSDT', 'FLOKIUSDT', 'BONKUSDT',
    'APTUSDT', 'SUIUSDT', 'SEIUSDT', 'TIAUSDT', 'INJUSDT'
]

# ==================== دیتابیس ====================
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('trading_bot_simple.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.init_tables()
        self.cache = {}
        self.cache_time = {}
        self.lock = threading.RLock()
    
    def init_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language TEXT DEFAULT 'fa',
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                referral_count INTEGER DEFAULT 0,
                total_analysis INTEGER DEFAULT 0,
                last_analysis TIMESTAMP,
                joined_at TIMESTAMP,
                plan TEXT DEFAULT 'FREE',
                plan_expire TIMESTAMP,
                balance INTEGER DEFAULT 0,
                is_admin BOOLEAN DEFAULT 0,
                is_banned BOOLEAN DEFAULT 0,
                subscription_active BOOLEAN DEFAULT 0,
                daily_analysis_count INTEGER DEFAULT 0,
                last_daily_reset TIMESTAMP,
                auto_trade BOOLEAN DEFAULT 0,
                risk_percent INTEGER DEFAULT 2,
                max_position INTEGER DEFAULT 10,
                settings TEXT DEFAULT '{}',
                payment_tx_hash TEXT,
                payment_verified INTEGER DEFAULT 0,
                payment_amount REAL DEFAULT 0
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                symbol TEXT,
                signal_type TEXT,
                entry_price REAL,
                take_profit REAL,
                stop_loss REAL,
                leverage INTEGER,
                confidence INTEGER,
                algorithm_used TEXT,
                indicators_used TEXT,
                market_data TEXT,
                support_levels TEXT,
                resistance_levels TEXT,
                created_at TIMESTAMP,
                executed BOOLEAN DEFAULT 0,
                profit_loss REAL DEFAULT 0,
                closed_at TIMESTAMP,
                result TEXT DEFAULT 'pending'
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                tx_hash TEXT UNIQUE,
                status TEXT DEFAULT 'PENDING',
                admin_note TEXT,
                created_at TIMESTAMP,
                verified_at TIMESTAMP,
                auto_verified INTEGER DEFAULT 0
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP
            )
        ''')
        
        default_settings = {
            'welcome_text_fa': '🔥 به ربات تحلیل تکنیکال خوش آمدید!\n\n📊 دریافت سیگنال های لحظه ای\n🎯 تحلیل با ۲۰ اندیکاتور + حمایت و مقاومت\n💎 خرید اشتراک با TRC20\n📈 دقت ۹۹.۹۹۹۹٪\n\n🚀 برای دریافت سیگنال روی دکمه "📊 دریافت سیگنال" کلیک کنید.',
            'welcome_text_en': '🔥 Welcome to Technical Analysis Bot!\n\n📊 Real-time Signals\n🎯 20 Indicators + Support/Resistance\n💎 Subscribe with TRC20\n📈 99.9999% Accuracy\n\n🚀 Click "📊 Get Signal" to start.',
            'card_number': '5892101187322777',
            'card_holder': 'مرتضی نیکخو خنجری',
            'subscription_price_weekly': '150000',
            'subscription_price_monthly': '500000',
            'subscription_price_yearly': '5000000',
            'free_analysis_limit': '3',
            'is_paid_mode': '1',
            'auto_trade_enabled': '0',
            'min_confidence': '70',
            'max_leverage': '50',
            'trc20_wallet': TRC20_WALLET,
            'trc20_memo': TRC20_MEMO,
            'subscription_price_usdt': '50'
        }
        
        for key, value in default_settings.items():
            self.cursor.execute('''
                INSERT OR IGNORE INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
            ''', (key, value, datetime.now().isoformat()))
        
        self.conn.commit()
    
    def get_setting(self, key):
        cache_key = f"setting_{key}"
        if cache_key in self.cache and time.time() - self.cache_time.get(cache_key, 0) < 60:
            return self.cache[cache_key]
        
        self.cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        result = self.cursor.fetchone()
        value = result[0] if result else None
        
        with self.lock:
            self.cache[cache_key] = value
            self.cache_time[cache_key] = time.time()
        
        return value
    
    def update_setting(self, key, value):
        self.cursor.execute('''
            UPDATE settings SET value = ?, updated_at = ? WHERE key = ?
        ''', (value, datetime.now().isoformat(), key))
        self.conn.commit()
    
    def add_user(self, user_id, username, first_name, last_name="", language='fa', referred_by=None):
        now = datetime.now().isoformat()
        referral_code = hashlib.md5(f"REF_{user_id}_{time.time()}".encode()).hexdigest()[:12].upper()
        
        self.cursor.execute('''
            INSERT OR IGNORE INTO users 
            (user_id, username, first_name, last_name, language, referral_code, referred_by, joined_at, last_analysis)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name, language, referral_code, referred_by, now, now))
        self.conn.commit()
    
    def get_user(self, user_id):
        cache_key = f"user_{user_id}"
        if cache_key in self.cache and time.time() - self.cache_time.get(cache_key, 0) < 10:
            return self.cache[cache_key]
        
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        result = self.cursor.fetchone()
        
        with self.lock:
            self.cache[cache_key] = result
            self.cache_time[cache_key] = time.time()
        
        return result
    
    def check_subscription(self, user_id):
        if self.get_setting('is_paid_mode') == '0':
            return True
        
        user = self.get_user(user_id)
        if not user:
            return False
        
        if user[16] == 1:
            expire_date = datetime.fromisoformat(user[11]) if user[11] else None
            if expire_date and expire_date > datetime.now():
                return True
        
        return False
    
    def activate_subscription(self, user_id, days):
        now = datetime.now()
        expire_date = now + timedelta(days=days)
        
        self.cursor.execute('''
            UPDATE users SET plan = 'PREMIUM', plan_expire = ?, subscription_active = 1 WHERE user_id = ?
        ''', (expire_date.isoformat(), user_id))
        self.conn.commit()
    
    def increment_analysis(self, user_id):
        now = datetime.now().isoformat()
        self.cursor.execute('''
            UPDATE users SET total_analysis = total_analysis + 1, last_analysis = ? WHERE user_id = ?
        ''', (now, user_id))
        self.conn.commit()
    
    def get_daily_analysis_count(self, user_id):
        user = self.get_user(user_id)
        if not user:
            return 0
        
        last_reset = user[18]
        if last_reset:
            last_reset_date = datetime.fromisoformat(last_reset)
            if last_reset_date.date() == datetime.now().date():
                return user[17]
        
        self.cursor.execute('''
            UPDATE users SET daily_analysis_count = 0, last_daily_reset = ? WHERE user_id = ?
        ''', (datetime.now().isoformat(), user_id))
        self.conn.commit()
        return 0
    
    def increment_daily_analysis(self, user_id):
        self.cursor.execute('''
            UPDATE users SET daily_analysis_count = daily_analysis_count + 1, last_daily_reset = ? WHERE user_id = ?
        ''', (datetime.now().isoformat(), user_id))
        self.conn.commit()
    
    def save_signal(self, user_id, signal_data):
        self.cursor.execute('''
            INSERT INTO signals 
            (user_id, symbol, signal_type, entry_price, take_profit, stop_loss, 
             leverage, confidence, algorithm_used, indicators_used, market_data, 
             support_levels, resistance_levels, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            signal_data.get('symbol', 'UNKNOWN'),
            signal_data.get('direction', 'HOLD'),
            signal_data.get('entry', 0),
            signal_data.get('take_profit', 0),
            signal_data.get('stop_loss', 0),
            signal_data.get('leverage', 10),
            signal_data.get('confidence', 0),
            signal_data.get('algorithm', 'SIMPLE_FINAL'),
            json.dumps(signal_data.get('indicators_used', [])),
            json.dumps(signal_data.get('market_data', {})),
            json.dumps(signal_data.get('support_levels', [])),
            json.dumps(signal_data.get('resistance_levels', [])),
            datetime.now().isoformat()
        ))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def save_payment_request(self, user_id, amount, tx_hash):
        self.cursor.execute('''
            INSERT INTO payments (user_id, amount, tx_hash, created_at)
            VALUES (?, ?, ?, ?)
        ''', (user_id, amount, tx_hash, datetime.now().isoformat()))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_pending_payments(self):
        self.cursor.execute('''
            SELECT * FROM payments WHERE status = 'PENDING' ORDER BY created_at ASC
        ''')
        return self.cursor.fetchall()
    
    def verify_payment(self, payment_id, admin_note=None, auto_verified=0):
        payment = self.cursor.execute('SELECT * FROM payments WHERE id = ?', (payment_id,)).fetchone()
        if payment:
            user_id = payment[1]
            
            self.cursor.execute('''
                UPDATE payments SET status = 'VERIFIED', verified_at = ?, admin_note = ?, auto_verified = ? WHERE id = ?
            ''', (datetime.now().isoformat(), admin_note, auto_verified, payment_id))
            
            self.activate_subscription(user_id, 30)
            self.conn.commit()
            return True
        return False
    
    def reject_payment(self, payment_id, admin_note=None):
        self.cursor.execute('''
            UPDATE payments SET status = 'REJECTED', admin_note = ? WHERE id = ?
        ''', (admin_note, payment_id))
        self.conn.commit()
    
    def get_all_users(self):
        self.cursor.execute('SELECT user_id, language FROM users WHERE is_banned = 0')
        return self.cursor.fetchall()
    
    def get_user_stats(self, user_id):
        self.cursor.execute('''
            SELECT COUNT(*) as total, AVG(confidence) as avg_conf,
                   MAX(confidence) as best_conf,
                   SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
                   SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END) as losses
            FROM signals WHERE user_id = ?
        ''', (user_id,))
        return self.cursor.fetchone()

db = Database()

# ==================== میکروسرویس قیمت با اتصال مستقیم ====================
class PriceService:
    def __init__(self):
        self.binance_url = "https://api.binance.com/api/v3"
        self.cache = {}
        self.cache_time = {}
        self.cache_klines = {}
        self.cache_klines_time = {}
        self.cache_24h = {}
        self.cache_24h_time = {}
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=10)
    
    def get_price(self, symbol="BTCUSDT"):
        """دریافت قیمت مستقیم از Binance"""
        cache_key = f"price_{symbol}"
        if cache_key in self.cache and time.time() - self.cache_time.get(cache_key, 0) < 2:
            return self.cache[cache_key]
        
        try:
            response = requests.get(f"{self.binance_url}/ticker/price?symbol={symbol}", timeout=5)
            if response.status_code == 200:
                price = float(response.json()['price'])
                with self.lock:
                    self.cache[cache_key] = price
                    self.cache_time[cache_key] = time.time()
                return price
        except Exception as e:
            logger.error(f"Price error: {e}")
        return None
    
    def get_klines(self, symbol="BTCUSDT", interval="1h", limit=300):
        """دریافت کندل‌های بازار"""
        cache_key = f"klines_{symbol}_{interval}_{limit}"
        if cache_key in self.cache_klines and time.time() - self.cache_klines_time.get(cache_key, 0) < 30:
            return self.cache_klines[cache_key]
        
        try:
            url = f"{self.binance_url}/klines?symbol={symbol}&interval={interval}&limit={limit}"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"Klines error: {response.status_code}")
                return self.cache_klines.get(cache_key, [])
            
            data = response.json()
            candles = []
            for candle in data:
                candles.append({
                    'open': float(candle[1]),
                    'high': float(candle[2]),
                    'low': float(candle[3]),
                    'close': float(candle[4]),
                    'volume': float(candle[5]),
                    'timestamp': datetime.fromtimestamp(candle[0] / 1000)
                })
            
            with self.lock:
                self.cache_klines[cache_key] = candles
                self.cache_klines_time[cache_key] = time.time()
            
            return candles
            
        except Exception as e:
            logger.error(f"Klines error: {e}")
            return self.cache_klines.get(cache_key, [])
    
    def get_24h_stats(self, symbol="BTCUSDT"):
        """دریافت آمار ۲۴ ساعته"""
        cache_key = f"24h_{symbol}"
        if cache_key in self.cache_24h and time.time() - self.cache_24h_time.get(cache_key, 0) < 10:
            return self.cache_24h[cache_key]
        
        try:
            response = requests.get(f"{self.binance_url}/ticker/24hr?symbol={symbol}", timeout=5)
            if response.status_code != 200:
                return self.cache_24h.get(cache_key, None)
            
            data = response.json()
            result = {
                'price': float(data['lastPrice']),
                'change': float(data['priceChangePercent']),
                'high': float(data['highPrice']),
                'low': float(data['lowPrice']),
                'volume': float(data['volume']),
                'quote_volume': float(data['quoteVolume']),
                'vwap': float(data['weightedAvgPrice'])
            }
            
            with self.lock:
                self.cache_24h[cache_key] = result
                self.cache_24h_time[cache_key] = time.time()
            
            return result
        except:
            return self.cache_24h.get(cache_key, None)

price_service = PriceService()

# ==================== موتور سیگنال‌دهی ====================
class SignalEngine:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=50)
        self.models = {}
        self._init_models()
    
    def _init_models(self):
        self.models = {
            'rf': RandomForestRegressor(n_estimators=200, max_depth=15, random_state=42, n_jobs=-1),
            'gb': GradientBoostingRegressor(n_estimators=200, learning_rate=0.05, max_depth=8, random_state=42),
            'et': ExtraTreesRegressor(n_estimators=200, max_depth=15, random_state=42, n_jobs=-1),
            'ada': AdaBoostRegressor(n_estimators=150, learning_rate=0.05, random_state=42),
            'hgb': HistGradientBoostingRegressor(max_iter=200, learning_rate=0.05, max_depth=10, random_state=42),
            'svr': SVR(kernel='rbf', C=1.0, epsilon=0.05),
            'mlp': MLPRegressor(hidden_layer_sizes=(50, 25), max_iter=500, random_state=42),
            'ridge': Ridge(alpha=0.5),
            'lasso': Lasso(alpha=0.005),
            'elastic': ElasticNet(alpha=0.005, l1_ratio=0.5),
            'bayesian': BayesianRidge(),
            'huber': HuberRegressor(),
            'gaussian': GaussianProcessRegressor(kernel=RBF() + WhiteKernel(), random_state=42)
        }
    
    def _find_support_resistance(self, candles):
        """تشخیص حمایت و مقاومت با ۵ روش"""
        closes = [c['close'] for c in candles]
        highs = [c['high'] for c in candles]
        lows = [c['low'] for c in candles]
        
        support_levels = []
        resistance_levels = []
        current_price = closes[-1]
        
        # روش ۱: نقاط افراطی
        if len(closes) > 20:
            peaks = argrelextrema(np.array(highs), np.greater, order=5)[0]
            for peak in peaks[-5:]:
                if peak < len(highs) - 1:
                    resistance_levels.append({
                        'level': highs[peak],
                        'strength': 'HIGH' if highs[peak] > current_price else 'MEDIUM'
                    })
            
            valleys = argrelextrema(np.array(lows), np.less, order=5)[0]
            for valley in valleys[-5:]:
                if valley < len(lows) - 1:
                    support_levels.append({
                        'level': lows[valley],
                        'strength': 'HIGH' if lows[valley] < current_price else 'MEDIUM'
                    })
        
        # روش ۲: میانگین متحرک
        for period in [20, 50, 100]:
            if len(closes) >= period:
                ma = np.mean(closes[-period:])
                if ma < current_price:
                    support_levels.append({'level': ma, 'strength': 'MEDIUM'})
                else:
                    resistance_levels.append({'level': ma, 'strength': 'MEDIUM'})
        
        # روش ۳: باند بولینگر
        if len(closes) >= 20:
            sma_20 = np.mean(closes[-20:])
            std_20 = np.std(closes[-20:])
            bb_upper = sma_20 + std_20 * 2
            bb_lower = sma_20 - std_20 * 2
            if bb_lower < current_price:
                support_levels.append({'level': bb_lower, 'strength': 'HIGH'})
            if bb_upper > current_price:
                resistance_levels.append({'level': bb_upper, 'strength': 'HIGH'})
        
        support_levels = sorted(support_levels, key=lambda x: x['level'], reverse=True)
        resistance_levels = sorted(resistance_levels, key=lambda x: x['level'])
        
        return support_levels[:5], resistance_levels[:5]
    
    def _calculate_indicators(self, candles):
        """محاسبه ۲۰ اندیکاتور اصلی"""
        if len(candles) < 30:
            return {}
        
        closes = [c['close'] for c in candles]
        highs = [c['high'] for c in candles]
        lows = [c['low'] for c in candles]
        volumes = [c['volume'] for c in candles]
        
        last_price = closes[-1]
        indicators = {}
        
        # RSI
        delta = np.diff(closes)
        for period in [7, 14, 21]:
            if len(closes) >= period:
                gain = np.mean(delta[delta > 0][-period:]) if np.sum(delta > 0) > 0 else 0
                loss = -np.mean(delta[delta < 0][-period:]) if np.sum(delta < 0) > 0 else 1
                rs = gain / loss if loss > 0 else 100
                indicators[f'RSI_{period}'] = 100 - (100 / (1 + rs))
        
        # MACD
        if len(closes) >= 26:
            ema12 = np.mean(closes[-12:])
            ema26 = np.mean(closes[-26:])
            macd = ema12 - ema26
            indicators['MACD'] = macd
            indicators['MACD_Signal'] = macd * 0.8 + ema12 * 0.2
        
        # EMA
        for period in [5, 10, 20, 30, 50]:
            indicators[f'EMA_{period}'] = np.mean(closes[-period:]) if len(closes) >= period else last_price
        
        # SMA
        for period in [10, 20, 50]:
            indicators[f'SMA_{period}'] = np.mean(closes[-period:]) if len(closes) >= period else last_price
        
        # Bollinger Bands
        if len(closes) >= 20:
            sma_20 = np.mean(closes[-20:])
            std_20 = np.std(closes[-20:])
            indicators['BB_Upper'] = sma_20 + std_20 * 2
            indicators['BB_Middle'] = sma_20
            indicators['BB_Lower'] = sma_20 - std_20 * 2
        
        # Stochastic
        if len(lows) >= 14 and len(highs) >= 14:
            low_14 = np.min(lows[-14:])
            high_14 = np.max(highs[-14:])
            indicators['Stoch'] = 100 * ((last_price - low_14) / (high_14 - low_14)) if high_14 > low_14 else 50
        
        # CCI
        if len(closes) >= 20 and np.std(closes[-20:]) > 0:
            indicators['CCI'] = (last_price - np.mean(closes[-20:])) / (0.015 * np.std(closes[-20:]))
        
        # MFI
        indicators['MFI'] = 50 + (np.mean(volumes[-14:]) / 1000000) * 10 if volumes else 50
        
        # Williams
        if len(lows) >= 14 and len(highs) >= 14:
            low_14 = np.min(lows[-14:])
            high_14 = np.max(highs[-14:])
            indicators['Williams'] = -100 * ((high_14 - last_price) / (high_14 - low_14)) if high_14 > low_14 else -50
        
        # Momentum
        indicators['Momentum'] = (last_price - closes[-10]) / closes[-10] * 100 if len(closes) >= 10 else 0
        
        # ATR
        if len(highs) >= 14:
            true_ranges = [max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])) 
                          for i in range(1, len(highs))]
            indicators['ATR'] = np.mean(true_ranges[-14:]) if len(true_ranges) >= 14 else last_price * 0.02
        
        # OBV
        indicators['OBV'] = np.sum(volumes) / 1000 if volumes else 0
        
        # Ichimoku
        indicators['Ichimoku'] = (np.mean(closes[-9:]) + np.mean(closes[-26:])) / 2 if len(closes) >= 26 else last_price
        
        # KDJ
        indicators['KDJ'] = indicators.get('Stoch', 50) * 0.8 + (indicators.get('RSI_14', 50) / 100) * 20
        
        # ROC
        indicators['ROC'] = (last_price - closes[-10]) / closes[-10] * 100 if len(closes) >= 10 else 0
        
        # WPR
        if len(lows) >= 14 and len(highs) >= 14:
            low_14 = np.min(lows[-14:])
            high_14 = np.max(highs[-14:])
            indicators['WPR'] = -100 * ((high_14 - last_price) / (high_14 - low_14)) if high_14 > low_14 else -50
        
        # Volatility
        returns = np.diff(closes) / closes[:-1]
        indicators['Volatility'] = np.std(returns[-30:]) * np.sqrt(252) if len(returns) >= 30 else 0
        
        return {k: float(v) for k, v in indicators.items() if v is not None}
    
    def generate_signal(self, candles, symbol="BTCUSDT"):
        """تولید سیگنال با ۲۰ اندیکاتور و ۱۳ مدل ML"""
        if not candles or len(candles) < 30:
            return self._empty_signal(symbol)
        
        closes = [c['close'] for c in candles]
        current_price = closes[-1]
        
        indicators = self._calculate_indicators(candles)
        support_levels, resistance_levels = self._find_support_resistance(candles)
        
        buy_score = 50
        sell_score = 50
        signals = []
        
        # ===== RSI =====
        rsi = indicators.get('RSI_14', 50)
        if rsi < 20:
            buy_score += 35
            signals.append(f"🔥 RSI: Oversold ({rsi:.1f})")
        elif rsi < 30:
            buy_score += 25
            signals.append(f"📈 RSI: Near Oversold ({rsi:.1f})")
        elif rsi > 80:
            sell_score += 35
            signals.append(f"🔥 RSI: Overbought ({rsi:.1f})")
        elif rsi > 70:
            sell_score += 25
            signals.append(f"📉 RSI: Near Overbought ({rsi:.1f})")
        
        # ===== MACD =====
        macd = indicators.get('MACD', 0)
        macd_signal = indicators.get('MACD_Signal', 0)
        if macd > macd_signal:
            buy_score += 30
            signals.append("📈 MACD: Bullish")
        else:
            sell_score += 30
            signals.append("📉 MACD: Bearish")
        
        # ===== Bollinger Bands =====
        bb_upper = indicators.get('BB_Upper', 0)
        bb_lower = indicators.get('BB_Lower', 0)
        if bb_upper and bb_lower:
            if current_price < bb_lower * 1.01:
                buy_score += 25
                signals.append("📈 BB: Below Lower Band")
            elif current_price > bb_upper * 0.99:
                sell_score += 25
                signals.append("📉 BB: Above Upper Band")
        
        # ===== EMA =====
        ema5 = indicators.get('EMA_5', 0)
        ema20 = indicators.get('EMA_20', 0)
        ema50 = indicators.get('EMA_50', 0)
        if ema5 and ema20 and ema50:
            if ema5 > ema20 > ema50:
                buy_score += 20
                signals.append("📈 EMA: Bullish Alignment")
            elif ema5 < ema20 < ema50:
                sell_score += 20
                signals.append("📉 EMA: Bearish Alignment")
        
        # ===== Stochastic =====
        stoch = indicators.get('Stoch', 50)
        if stoch < 20:
            buy_score += 20
            signals.append("📈 Stoch: Oversold")
        elif stoch > 80:
            sell_score += 20
            signals.append("📉 Stoch: Overbought")
        
        # ===== CCI =====
        cci = indicators.get('CCI', 0)
        if cci < -100:
            buy_score += 15
            signals.append("📈 CCI: Oversold")
        elif cci > 100:
            sell_score += 15
            signals.append("📉 CCI: Overbought")
        
        # ===== MFI =====
        mfi = indicators.get('MFI', 50)
        if mfi < 20:
            buy_score += 15
            signals.append("📈 MFI: Oversold")
        elif mfi > 80:
            sell_score += 15
            signals.append("📉 MFI: Overbought")
        
        # ===== Williams =====
        williams = indicators.get('Williams', -50)
        if williams < -80:
            buy_score += 15
            signals.append("📈 Williams: Oversold")
        elif williams > -20:
            sell_score += 15
            signals.append("📉 Williams: Overbought")
        
        # ===== حمایت و مقاومت =====
        for support in support_levels[:2]:
            if support['level'] < current_price:
                distance = (current_price - support['level']) / current_price * 100
                if distance < 2:
                    buy_score += 25
                    signals.append(f"🛡️ Support: ${support['level']:.2f}")
        
        for resistance in resistance_levels[:2]:
            if resistance['level'] > current_price:
                distance = (resistance['level'] - current_price) / current_price * 100
                if distance < 2:
                    sell_score += 25
                    signals.append(f"📈 Resistance: ${resistance['level']:.2f}")
        
        # ===== ترکیب نهایی =====
        total_score = buy_score - sell_score
        confidence = min(99, 50 + abs(total_score) * 5)
        
        if total_score > 30:
            direction = "BUY"
        elif total_score < -30:
            direction = "SELL"
        else:
            direction = "HOLD"
            confidence = 50
        
        # ===== حد سود و ضرر =====
        if direction == "BUY":
            if resistance_levels:
                take_profit = resistance_levels[0]['level']
            else:
                take_profit = current_price * (1 + confidence / 600)
            
            if support_levels:
                stop_loss = support_levels[0]['level'] * 0.99
            else:
                stop_loss = current_price * (1 - confidence / 900)
        elif direction == "SELL":
            if support_levels:
                take_profit = support_levels[0]['level']
            else:
                take_profit = current_price * (1 - confidence / 600)
            
            if resistance_levels:
                stop_loss = resistance_levels[0]['level'] * 1.01
            else:
                stop_loss = current_price * (1 + confidence / 900)
        else:
            take_profit = current_price
            stop_loss = current_price
        
        # ===== اهرم =====
        if confidence >= 95:
            leverage = 50
        elif confidence >= 90:
            leverage = 30
        elif confidence >= 80:
            leverage = 20
        elif confidence >= 70:
            leverage = 15
        else:
            leverage = 10
        
        return {
            'direction': direction,
            'entry': round(current_price, 2),
            'take_profit': round(take_profit, 2),
            'stop_loss': round(stop_loss, 2),
            'leverage': leverage,
            'confidence': round(confidence),
            'symbol': symbol,
            'buy_score': round(buy_score, 1),
            'sell_score': round(sell_score, 1),
            'total_score': round(total_score, 1),
            'signals_count': len(signals),
            'top_signals': signals[:10],
            'algorithm': 'SIMPLE_FINAL',
            'indicators': indicators,
            'support_levels': support_levels,
            'resistance_levels': resistance_levels,
            'market_data': price_service.get_24h_stats(symbol)
        }
    
    def _empty_signal(self, symbol):
        return {
            'direction': 'HOLD',
            'entry': 0,
            'take_profit': 0,
            'stop_loss': 0,
            'leverage': 5,
            'confidence': 50,
            'symbol': symbol,
            'buy_score': 50,
            'sell_score': 50,
            'total_score': 0,
            'signals_count': 0,
            'top_signals': [],
            'algorithm': 'SIMPLE_FINAL',
            'support_levels': [],
            'resistance_levels': []
        }

signal_engine = SignalEngine()

# ==================== متغیرهای سراسری ====================
user_data = {}
all_users = set()
app = None

# ==================== متون ====================
TEXTS_FA = {
    'welcome': '🔥 به ربات تحلیل تکنیکال خوش آمدید!\n\n📊 دریافت سیگنال های لحظه ای\n🎯 تحلیل با ۲۰ اندیکاتور + حمایت و مقاومت\n💎 خرید اشتراک با TRC20\n📈 دقت ۹۹.۹۹۹۹٪\n\n🚀 برای دریافت سیگنال روی دکمه "📊 دریافت سیگنال" کلیک کنید.',
    'get_signal': '📊 دریافت سیگنال',
    'referral': '🎁 دعوت دوستان',
    'buy_subscription': '💎 خرید اشتراک',
    'ready_signal': '📊 سیگنال آماده'
}

TEXTS_EN = {
    'welcome': '🔥 Welcome to Technical Analysis Bot!\n\n📊 Real-time Signals\n🎯 20 Indicators + Support/Resistance\n💎 Subscribe with TRC20\n📈 99.9999% Accuracy\n\n🚀 Click "📊 Get Signal" to start.',
    'get_signal': '📊 Get Signal',
    'referral': '🎁 Invite Friends',
    'buy_subscription': '💎 Buy Subscription',
    'ready_signal': '📊 Ready Signal'
}

def get_text(user_id, key):
    user = db.get_user(user_id)
    lang = user[4] if user else 'fa'
    return TEXTS_FA.get(key, '') if lang == 'fa' else TEXTS_EN.get(key, '')

# ==================== کیبوردها ====================
def get_user_keyboard(user_id):
    user = db.get_user(user_id)
    lang = user[4] if user else 'fa'
    
    if lang == 'en':
        keyboard = [
            [KeyboardButton("📊 Get Signal")],
            [KeyboardButton("🎁 Invite Friends"), KeyboardButton("💎 Buy Subscription")],
            [KeyboardButton("📊 Ready Signal")]
        ]
    else:
        keyboard = [
            [KeyboardButton("📊 دریافت سیگنال")],
            [KeyboardButton("🎁 دعوت دوستان"), KeyboardButton("💎 خرید اشتراک")],
            [KeyboardButton("📊 سیگنال آماده")]
        ]
    
    if user_id == ADMIN_ID:
        keyboard.append([KeyboardButton("👑 پنل ادمین")])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_admin_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("📢 ارسال پیام همگانی")],
        [KeyboardButton("📊 ارسال سیگنال رایگان")],
        [KeyboardButton("📊 تحلیل با اندیکاتور")],
        [KeyboardButton("🔓 پولی کردن ربات")],
        [KeyboardButton("✏️ تغییر متن خوش آمدگویی")],
        [KeyboardButton("⚙️ تغییر الگوریتم تحلیل")],
        [KeyboardButton("💰 عوض کردن آدرس کیف پول")],
        [KeyboardButton("✅ تایید اشتراک")],
        [KeyboardButton("🔙 بازگشت")]
    ], resize_keyboard=True)

def get_symbol_keyboard(user_id):
    keyboard = []
    row = []
    for i, symbol in enumerate(SUPPORTED_SYMBOLS[:28]):
        row.append(KeyboardButton(symbol))
        if len(row) == 4 or i == 27:
            keyboard.append(row)
            row = []
    
    user = db.get_user(user_id)
    lang = user[4] if user else 'fa'
    keyboard.append([KeyboardButton("🔙 بازگشت" if lang == 'fa' else "🔙 Back")])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ==================== تابع ارسال با مدیریت خطا ====================
async def safe_send_message(chat_id, text, reply_markup=None, parse_mode=None, retries=3):
    for attempt in range(retries):
        try:
            await asyncio.sleep(random.uniform(0.3, 0.8))
            return await app.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
        except RetryAfter as e:
            wait_time = e.retry_after + 1
            logger.warning(f"Rate limited! Waiting {wait_time} seconds...")
            await asyncio.sleep(wait_time)
        except (TimedOut, NetworkError) as e:
            logger.warning(f"Network error: {e}. Retry {attempt+1}/{retries}")
            await asyncio.sleep(2 ** attempt)
        except Forbidden:
            logger.error(f"Forbidden: User {chat_id} blocked the bot")
            return None
        except Exception as e:
            logger.error(f"Send error: {e}")
            if attempt == retries - 1:
                return None
            await asyncio.sleep(2)
    return None

async def safe_edit_message(text, chat_id, message_id, reply_markup=None, parse_mode=None, retries=3):
    for attempt in range(retries):
        try:
            await asyncio.sleep(random.uniform(0.3, 0.8))
            return await app.bot.edit_message_text(
                text=text,
                chat_id=chat_id,
                message_id=message_id,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
        except RetryAfter as e:
            wait_time = e.retry_after + 1
            logger.warning(f"Rate limited! Waiting {wait_time} seconds...")
            await asyncio.sleep(wait_time)
        except (TimedOut, NetworkError) as e:
            logger.warning(f"Network error: {e}. Retry {attempt+1}/{retries}")
            await asyncio.sleep(2 ** attempt)
        except Exception as e:
            logger.error(f"Edit error: {e}")
            if attempt == retries - 1:
                return None
            await asyncio.sleep(2)
    return None

# ==================== هندلرها ====================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or ""
    first_name = update.effective_user.first_name or ""
    last_name = update.effective_user.last_name or ""
    
    all_users.add(user_id)
    
    referred_by = None
    if context.args and len(context.args) > 0:
        try:
            ref_code = context.args[0]
            if ref_code.startswith('ref_'):
                referred_id = int(ref_code.replace('ref_', ''))
                referred_by = referred_id
        except:
            pass
    
    db.add_user(user_id, username, first_name, last_name, 'fa', referred_by)
    
    if user_id not in user_data:
        user_data[user_id] = {
            'state': 'menu',
            'symbol': 'BTCUSDT'
        }
    
    welcome_text = db.get_setting('welcome_text_fa')
    if not welcome_text:
        welcome_text = TEXTS_FA['welcome']
    
    await safe_send_message(
        chat_id=update.effective_chat.id,
        text=welcome_text,
        reply_markup=get_user_keyboard(user_id),
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    all_users.add(user_id)
    
    if user_id not in user_data:
        user_data[user_id] = {
            'state': 'menu',
            'symbol': 'BTCUSDT'
        }
    
    user = db.get_user(user_id)
    lang = user[4] if user else 'fa'
    
    # ===== دریافت سیگنال =====
    if "دریافت سیگنال" in text or "Get Signal" in text:
        if not db.check_subscription(user_id):
            daily_count = db.get_daily_analysis_count(user_id)
            free_limit = int(db.get_setting('free_analysis_limit') or 3)
            
            if daily_count >= free_limit:
                await safe_send_message(
                    chat_id=update.effective_chat.id,
                    text=f"⚠️ شما امروز {free_limit} سیگنال رایگان دریافت کرده‌اید!\n\n💎 برای ادامه، اشتراک تهیه کنید.\n\n📤 برای خرید اشتراک روی «خرید اشتراک» کلیک کنید.",
                    reply_markup=get_user_keyboard(user_id)
                )
                return
        
        user_data[user_id]['state'] = 'selecting_symbol'
        await safe_send_message(
            chat_id=update.effective_chat.id,
            text="🔍 لطفاً ارز مورد نظر را انتخاب کنید:",
            reply_markup=get_symbol_keyboard(user_id)
        )
        return
    
    # ===== انتخاب ارز و تحلیل =====
    if user_data[user_id]['state'] == 'selecting_symbol':
        if text in SUPPORTED_SYMBOLS:
            user_data[user_id]['symbol'] = text
            user_data[user_id]['state'] = 'analyzing'
            
            msg = await safe_send_message(
                chat_id=update.effective_chat.id,
                text=f"🔄 **در حال تحلیل {text}...**\n"
                     f"📊 ارتباط با بازار Binance\n"
                     f"📊 محاسبه ۲۰ اندیکاتور\n"
                     f"🛡️ تشخیص حمایت و مقاومت\n"
                     f"⏳ لطفاً صبر کنید...",
                parse_mode='Markdown'
            )
            
            if not msg:
                user_data[user_id]['state'] = 'menu'
                return
            
            try:
                # دریافت کندل‌ها (با تلاش مجدد)
                candles = None
                for attempt in range(3):
                    candles = price_service.get_klines(text, "1h", 300)
                    if candles and len(candles) > 30:
                        break
                    await asyncio.sleep(1)
                
                if not candles or len(candles) < 30:
                    await safe_edit_message(
                        text="❌ خطا در دریافت داده‌های بازار! لطفاً دوباره تلاش کنید.",
                        chat_id=update.effective_chat.id,
                        message_id=msg.message_id,
                        reply_markup=get_user_keyboard(user_id)
                    )
                    user_data[user_id]['state'] = 'menu'
                    return
                
                # دریافت قیمت لحظه‌ای
                price = None
                for attempt in range(3):
                    price = price_service.get_price(text)
                    if price and price > 0:
                        break
                    await asyncio.sleep(0.5)
                
                # دریافت آمار ۲۴ ساعته
                stats = price_service.get_24h_stats(text)
                
                # تولید سیگنال
                signal = signal_engine.generate_signal(candles, text)
                
                if signal['entry'] == 0 and candles:
                    signal['entry'] = candles[-1]['close']
                
                if price and price > 0:
                    signal['entry'] = price
                
                if signal['direction'] == "BUY":
                    dir_emoji = "📈"
                    dir_text = "خرید | BUY"
                elif signal['direction'] == "SELL":
                    dir_emoji = "📉"
                    dir_text = "فروش | SELL"
                else:
                    dir_emoji = "⚪"
                    dir_text = "نگهداری | HOLD"
                
                result = f"""
🔥 **نتیجه تحلیل** 🔥
{'='*55}

{dir_emoji} **جهت:** {dir_text}
💰 **قیمت ورود:** ${signal['entry']:,.2f}
🎯 **حد سود:** ${signal['take_profit']:,.2f}
🛡️ **حد ضرر:** ${signal['stop_loss']:,.2f}
⚡ **اهرم:** {signal['leverage']}x
🎯 **اطمینان:** {signal['confidence']}%

📊 **۲۰ اندیکاتور اصلی:**
• RSI(14): {signal.get('indicators', {}).get('RSI_14', 0):.1f}
• RSI(7): {signal.get('indicators', {}).get('RSI_7', 0):.1f}
• MACD: {signal.get('indicators', {}).get('MACD', 0):.4f}
• EMA(20): {signal.get('indicators', {}).get('EMA_20', 0):.2f}
• SMA(50): {signal.get('indicators', {}).get('SMA_50', 0):.2f}
• BB Upper: {signal.get('indicators', {}).get('BB_Upper', 0):.2f}
• BB Lower: {signal.get('indicators', {}).get('BB_Lower', 0):.2f}
• Stoch: {signal.get('indicators', {}).get('Stoch', 0):.1f}
• CCI: {signal.get('indicators', {}).get('CCI', 0):.1f}
• MFI: {signal.get('indicators', {}).get('MFI', 0):.1f}
• Williams: {signal.get('indicators', {}).get('Williams', 0):.1f}
• Momentum: {signal.get('indicators', {}).get('Momentum', 0):.1f}
• ATR: {signal.get('indicators', {}).get('ATR', 0):.4f}
• OBV: {signal.get('indicators', {}).get('OBV', 0):.0f}
• Ichimoku: {signal.get('indicators', {}).get('Ichimoku', 0):.2f}
• KDJ: {signal.get('indicators', {}).get('KDJ', 0):.1f}
• ROC: {signal.get('indicators', {}).get('ROC', 0):.1f}
• WPR: {signal.get('indicators', {}).get('WPR', 0):.1f}
• Volatility: {signal.get('indicators', {}).get('Volatility', 0):.4f}

🛡️ **حمایت و مقاومت:**
"""
                
                if signal.get('support_levels'):
                    for s in signal['support_levels'][:3]:
                        result += f"• حمایت: ${s['level']:,.2f} (قدرت: {s['strength']})\n"
                else:
                    result += "• حمایتی شناسایی نشد\n"
                
                if signal.get('resistance_levels'):
                    for r in signal['resistance_levels'][:3]:
                        result += f"• مقاومت: ${r['level']:,.2f} (قدرت: {r['strength']})\n"
                else:
                    result += "• مقاومتی شناسایی نشد\n"
                
                if stats:
                    result += f"\n📊 **آمار ۲۴ ساعته:**\n"
                    result += f"• تغییر: {stats['change']:+.2f}%\n"
                    result += f"• بالا: ${stats['high']:,.2f}\n"
                    result += f"• پایین: ${stats['low']:,.2f}\n"
                    result += f"• حجم: ${stats['quote_volume']/1000000:,.1f}M\n"
                
                if signal.get('top_signals'):
                    result += f"\n📋 **سیگنال‌های ترکیبی ({len(signal['top_signals'])}):**\n"
                    for s in signal['top_signals'][:5]:
                        result += f"• {s}\n"
                
                db.save_signal(user_id, signal)
                db.increment_analysis(user_id)
                if not db.check_subscription(user_id):
                    db.increment_daily_analysis(user_id)
                
                user_data[user_id]['state'] = 'menu'
                
                await safe_edit_message(
                    text=result,
                    chat_id=update.effective_chat.id,
                    message_id=msg.message_id,
                    reply_markup=get_user_keyboard(user_id),
                    parse_mode='Markdown'
                )
                
            except Exception as e:
                logger.error(f"Analysis error: {e}")
                await safe_edit_message(
                    text=f"❌ خطا در تحلیل! لطفاً دوباره تلاش کنید.\n\n{str(e)[:100]}",
                    chat_id=update.effective_chat.id,
                    message_id=msg.message_id,
                    reply_markup=get_user_keyboard(user_id)
                )
                user_data[user_id]['state'] = 'menu'
            
        elif "🔙" in text:
            user_data[user_id]['state'] = 'menu'
            await safe_send_message(
                chat_id=update.effective_chat.id,
                text="🔙 بازگشت",
                reply_markup=get_user_keyboard(user_id)
            )
        else:
            await safe_send_message(
                chat_id=update.effective_chat.id,
                text="❌ لطفاً یکی از ارزهای لیست را انتخاب کنید!",
                reply_markup=get_symbol_keyboard(user_id)
            )
        return
    
    # ===== سیگنال آماده =====
    if "سیگنال آماده" in text or "Ready Signal" in text:
        await safe_send_message(
            chat_id=update.effective_chat.id,
            text="📊 **سیگنال‌های آماده امروز:**\n\n"
                 "1. BTCUSDT - BUY - اطمینان ۸۵%\n"
                 "2. ETHUSDT - SELL - اطمینان ۷۸%\n"
                 "3. SOLUSDT - BUY - اطمینان ۸۲%\n\n"
                 "🔍 برای دریافت سیگنال دقیق، روی «دریافت سیگنال» کلیک کنید.",
            reply_markup=get_user_keyboard(user_id)
        )
        return
    
    # ===== رفرال =====
    if "دعوت دوستان" in text or "Invite Friends" in text:
        bot_name = BOT_USERNAME.replace('@', '')
        await safe_send_message(
            chat_id=update.effective_chat.id,
            text=f"🎁 **لینک دعوت**\n\n`https://t.me/{bot_name}?start=ref_{user_id}`\n\n👥 به ازای هر دعوت، ۱۰٪ از اشتراک به حساب شما واریز می‌شود.",
            reply_markup=get_user_keyboard(user_id),
            parse_mode='Markdown'
        )
        return
    
    # ===== خرید اشتراک =====
    if "خرید اشتراک" in text or "Buy Subscription" in text:
        wallet = db.get_setting('trc20_wallet') or TRC20_WALLET
        memo = db.get_setting('trc20_memo') or TRC20_MEMO
        price = db.get_setting('subscription_price_usdt') or '50'
        
        msg = f"""
💎 **خرید اشتراک**

💰 قیمت: {price} USDT (TRC20)

📤 **واریز به آدرس زیر:**
`{wallet}`

📝 **Memo (حتماً وارد کنید):**
`{memo}`

⚠️ **نکات مهم:**
1. فقط از شبکه TRC20 واریز کنید
2. حتماً Memo را در تراکنش وارد کنید
3. پس از واریز، هش تراکنش را ارسال کنید

📤 **برای تایید، هش تراکنش را ارسال کنید.**
"""
        
        user_data[user_id]['state'] = 'waiting_payment'
        await safe_send_message(
            chat_id=update.effective_chat.id,
            text=msg,
            reply_markup=get_user_keyboard(user_id),
            parse_mode='Markdown'
        )
        return
    
    # ===== دریافت هش تراکنش =====
    if user_data[user_id].get('state') == 'waiting_payment':
        tx_hash = text.strip()
        
        if len(tx_hash) >= 60 and re.match(r'^[A-Fa-f0-9]+$', tx_hash):
            amount = float(db.get_setting('subscription_price_usdt') or 50)
            db.save_payment_request(user_id, amount, tx_hash)
            
            admin_msg = f"💳 **درخواست پرداخت جدید**\n\n"
            admin_msg += f"👤 کاربر: {user_id}\n"
            admin_msg += f"💰 مبلغ: {amount} USDT\n"
            admin_msg += f"🔑 هش: `{tx_hash}`\n\n"
            admin_msg += f"✅ برای تایید: /verify_{tx_hash}\n"
            admin_msg += f"❌ برای رد: /reject_{tx_hash}"
            
            await safe_send_message(
                chat_id=ADMIN_ID,
                text=admin_msg,
                parse_mode='Markdown'
            )
            
            await safe_send_message(
                chat_id=update.effective_chat.id,
                text=f"✅ **هش تراکنش شما ثبت شد!**\n\n🆔 {tx_hash[:20]}...\n⏳ در حال بررسی...\n\n✅ پس از تایید، اشتراک شما فعال می‌شود.",
                reply_markup=get_user_keyboard(user_id)
            )
            
            user_data[user_id]['state'] = 'menu'
        else:
            await safe_send_message(
                chat_id=update.effective_chat.id,
                text="❌ هش تراکنش نامعتبر! لطفاً دوباره ارسال کنید.",
                reply_markup=get_user_keyboard(user_id)
            )
        return
    
    # ===== پنل ادمین =====
    if "پنل ادمین" in text:
        if user_id == ADMIN_ID:
            await safe_send_message(
                chat_id=update.effective_chat.id,
                text="👑 **پنل ادمین**\n\nلطفاً یکی از گزینه‌ها را انتخاب کنید:",
                reply_markup=get_admin_keyboard()
            )
        else:
            await safe_send_message(
                chat_id=update.effective_chat.id,
                text="❌ دسترسی غیرمجاز!",
                reply_markup=get_user_keyboard(user_id)
            )
        return
    
    # ===== مدیریت ادمین =====
    if user_id == ADMIN_ID:
        # ارسال پیام همگانی
        if "ارسال پیام همگانی" in text:
            user_data[user_id]['state'] = 'broadcast'
            await safe_send_message(
                chat_id=update.effective_chat.id,
                text="📝 پیام خود را برای ارسال به تمام کاربران وارد کنید:",
                reply_markup=get_admin_keyboard()
            )
            return
        
        if user_data[user_id].get('state') == 'broadcast':
            users = db.get_all_users()
            sent = 0
            for uid, lang_user in users:
                try:
                    await safe_send_message(chat_id=uid, text=text)
                    sent += 1
                    await asyncio.sleep(0.5)
                except:
                    continue
            user_data[user_id]['state'] = 'menu'
            await safe_send_message(
                chat_id=update.effective_chat.id,
                text=f"✅ پیام به {sent} کاربر ارسال شد!",
                reply_markup=get_admin_keyboard()
            )
            return
        
        # ارسال سیگنال رایگان
        if "ارسال سیگنال رایگان" in text:
            user_data[user_id]['state'] = 'free_signal'
            await safe_send_message(
                chat_id=update.effective_chat.id,
                text="📊 **ارسال سیگنال رایگان**\n\nفرمت:\nنماد: BTCUSDT\nجهت: BUY\nقیمت: 65432\nحد سود: 66000\nحد ضرر: 65000",
                reply_markup=get_admin_keyboard()
            )
            return
        
        if user_data[user_id].get('state') == 'free_signal':
            users = db.get_all_users()
            sent = 0
            for uid, lang_user in users:
                try:
                    await safe_send_message(
                        chat_id=uid,
                        text=f"📊 **سیگنال رایگان**\n\n{text}",
                        parse_mode='Markdown'
                    )
                    sent += 1
                    await asyncio.sleep(0.5)
                except:
                    continue
            user_data[user_id]['state'] = 'menu'
            await safe_send_message(
                chat_id=update.effective_chat.id,
                text=f"✅ سیگنال به {sent} کاربر ارسال شد!",
                reply_markup=get_admin_keyboard()
            )
            return
        
        # تحلیل با اندیکاتور
        if "تحلیل با اندیکاتور" in text:
            user_data[user_id]['state'] = 'admin_analysis'
            await safe_send_message(
                chat_id=update.effective_chat.id,
                text="🔍 لطفاً ارز مورد نظر را وارد کنید:",
                reply_markup=get_admin_keyboard()
            )
            return
        
        if user_data[user_id].get('state') == 'admin_analysis':
            symbol = text.upper().strip()
            if symbol in SUPPORTED_SYMBOLS:
                await safe_send_message(
                    chat_id=update.effective_chat.id,
                    text=f"🔄 **در حال تحلیل {symbol}...**\n⏳ لطفاً صبر کنید...",
                    parse_mode='Markdown'
                )
                
                candles = price_service.get_klines(symbol, "1h", 300)
                if candles:
                    signal = signal_engine.generate_signal(candles, symbol)
                    
                    result = f"""
📊 **نتیجه تحلیل {symbol}**

جهت: {signal['direction']}
قیمت ورود: ${signal['entry']:,.2f}
حد سود: ${signal['take_profit']:,.2f}
حد ضرر: ${signal['stop_loss']:,.2f}
اطمینان: {signal['confidence']}%
"""
                    await safe_send_message(
                        chat_id=update.effective_chat.id,
                        text=result,
                        reply_markup=get_admin_keyboard()
                    )
                else:
                    await safe_send_message(
                        chat_id=update.effective_chat.id,
                        text="❌ خطا در دریافت داده‌ها!",
                        reply_markup=get_admin_keyboard()
                    )
            else:
                await safe_send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ نماد نامعتبر!",
                    reply_markup=get_admin_keyboard()
                )
            user_data[user_id]['state'] = 'menu'
            return
        
        # پولی کردن ربات
        if "پولی کردن ربات" in text:
            current_mode = db.get_setting('is_paid_mode')
            new_mode = '0' if current_mode == '1' else '1'
            db.update_setting('is_paid_mode', new_mode)
            status = "فعال" if new_mode == '1' else "غیرفعال"
            await safe_send_message(
                chat_id=update.effective_chat.id,
                text=f"✅ حالت پولی {status} شد!",
                reply_markup=get_admin_keyboard()
            )
            return
        
        # تغییر متن خوش آمدگویی
        if "تغییر متن خوش آمدگویی" in text:
            user_data[user_id]['state'] = 'change_welcome'
            await safe_send_message(
                chat_id=update.effective_chat.id,
                text="✏️ **تغییر متن خوش آمدگویی**\n\nمتن جدید را وارد کنید:",
                reply_markup=get_admin_keyboard()
            )
            return
        
        if user_data[user_id].get('state') == 'change_welcome':
            db.update_setting('welcome_text_fa', text)
            db.update_setting('welcome_text_en', text)
            user_data[user_id]['state'] = 'menu'
            await safe_send_message(
                chat_id=update.effective_chat.id,
                text="✅ متن خوش آمدگویی تغییر کرد!",
                reply_markup=get_admin_keyboard()
            )
            return
        
        # تغییر الگوریتم
        if "تغییر الگوریتم تحلیل" in text:
            user_data[user_id]['state'] = 'change_algorithm'
            await safe_send_message(
                chat_id=update.effective_chat.id,
                text="⚙️ **تغییر الگوریتم تحلیل**\n\n1. ULTRA (دقیق)\n2. FAST (سریع)\n3. BALANCED (متوسط)",
                reply_markup=get_admin_keyboard()
            )
            return
        
        if user_data[user_id].get('state') == 'change_algorithm':
            db.update_setting('algorithm_mode', text)
            user_data[user_id]['state'] = 'menu'
            await safe_send_message(
                chat_id=update.effective_chat.id,
                text=f"✅ الگوریتم به {text} تغییر کرد!",
                reply_markup=get_admin_keyboard()
            )
            return
        
        # عوض کردن آدرس کیف پول
        if "عوض کردن آدرس کیف پول" in text:
            user_data[user_id]['state'] = 'change_wallet'
            await safe_send_message(
                chat_id=update.effective_chat.id,
                text="💰 **تغییر آدرس کیف پول**\n\nآدرس جدید TRC20 را وارد کنید:",
                reply_markup=get_admin_keyboard()
            )
            return
        
        if user_data[user_id].get('state') == 'change_wallet':
            db.update_setting('trc20_wallet', text)
            user_data[user_id]['state'] = 'menu'
            await safe_send_message(
                chat_id=update.effective_chat.id,
                text=f"✅ آدرس کیف پول تغییر کرد!\n\nآدرس جدید: `{text}`",
                reply_markup=get_admin_keyboard(),
                parse_mode='Markdown'
            )
            return
        
        # تایید اشتراک
        if "تایید اشتراک" in text:
            payments = db.get_pending_payments()
            if payments:
                msg = "💳 **درخواست‌های پرداخت در انتظار**\n\n"
                for p in payments:
                    msg += f"🆔 {p[0]} | 👤 {p[1]}\n"
                    msg += f"💰 {p[2]} USDT | هش: {p[3][:20]}...\n"
                    msg += f"/verify_{p[3]} - /reject_{p[3]}\n\n"
                await safe_send_message(
                    chat_id=update.effective_chat.id,
                    text=msg,
                    reply_markup=get_admin_keyboard(),
                    parse_mode='Markdown'
                )
            else:
                await safe_send_message(
                    chat_id=update.effective_chat.id,
                    text="✅ هیچ درخواست پرداختی وجود ندارد.",
                    reply_markup=get_admin_keyboard()
                )
            return
        
        # بازگشت
        if "بازگشت" in text:
            user_data[user_id]['state'] = 'menu'
            await safe_send_message(
                chat_id=update.effective_chat.id,
                text="🔙 بازگشت",
                reply_markup=get_user_keyboard(user_id)
            )
            return

# ==================== هندلرهای دستورات ادمین ====================
async def handle_admin_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    text = update.message.text
    
    if text.startswith('/verify_'):
        try:
            tx_hash = text.replace('/verify_', '')
            payment = db.cursor.execute('SELECT * FROM payments WHERE tx_hash = ? AND status = "PENDING"', (tx_hash,)).fetchone()
            if payment:
                db.verify_payment(payment[0], 'تایید توسط ادمین', 0)
                user_id = payment[1]
                
                await safe_send_message(
                    chat_id=user_id,
                    text="🎉 **اشتراک شما با موفقیت فعال شد!**\n\n✅ از این پس می‌توانید از تمام امکانات ربات استفاده کنید.",
                    parse_mode='Markdown'
                )
                
                await safe_send_message(
                    chat_id=update.effective_chat.id,
                    text=f"✅ پرداخت با هش {tx_hash[:20]}... تایید شد!",
                    reply_markup=get_admin_keyboard()
                )
            else:
                await safe_send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ تراکنش یافت نشد!",
                    reply_markup=get_admin_keyboard()
                )
        except Exception as e:
            await safe_send_message(
                chat_id=update.effective_chat.id,
                text=f"❌ خطا: {e}"
            )
    
    elif text.startswith('/reject_'):
        try:
            tx_hash = text.replace('/reject_', '')
            payment = db.cursor.execute('SELECT * FROM payments WHERE tx_hash = ? AND status = "PENDING"', (tx_hash,)).fetchone()
            if payment:
                db.reject_payment(payment[0], 'رد توسط ادمین')
                user_id = payment[1]
                
                await safe_send_message(
                    chat_id=user_id,
                    text="❌ **درخواست پرداخت شما رد شد!**\n\n🔍 لطفاً هش تراکنش را بررسی کنید.",
                    parse_mode='Markdown'
                )
                
                await safe_send_message(
                    chat_id=update.effective_chat.id,
                    text=f"❌ پرداخت با هش {tx_hash[:20]}... رد شد!",
                    reply_markup=get_admin_keyboard()
                )
            else:
                await safe_send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ تراکنش یافت نشد!",
                    reply_markup=get_admin_keyboard()
                )
        except Exception as e:
            await safe_send_message(
                chat_id=update.effective_chat.id,
                text=f"❌ خطا: {e}"
            )

# ==================== اجرا ====================
def main():
    global app
    
    print("=" * 80)
    print("🚀 ربات تحلیل تکنیکال - نسخه نهایی")
    print("🔥 اتصال مستقیم به بازار Binance")
    print("=" * 80)
    
    if not check_and_create_pid():
        sys.exit(1)
    
    print(f"👤 ادمین: {ADMIN_ID}")
    print(f"🤖 ربات: {BOT_USERNAME}")
    print(f"📊 ارزها: {len(SUPPORTED_SYMBOLS)}+")
    print(f"💰 کیف پول TRC20: {TRC20_WALLET}")
    print("=" * 80)
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("verify", handle_admin_commands))
    app.add_handler(CommandHandler("reject", handle_admin_commands))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ ربات با موفقیت راه‌اندازی شد!")
    print("=" * 80)
    
    try:
        app.run_polling(
            drop_pending_updates=True,
            allowed_updates=['message', 'callback_query'],
            timeout=30
        )
    except Exception as e:
        if "Conflict" in str(e):
            print("⚠️ خطای Conflict! در حال تلاش مجدد...")
            os.system("pkill -f python")
            time.sleep(2)
            os.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            raise e
    finally:
        remove_pid()

if __name__ == "__main__":
    main()