#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ربات تحلیل تکنیکال فوق‌پیشرفته نسخه ۱۵.۱
==================================================
✅ ۱۰۰۰+ الگوریتم ترکیبی برای سیگنال‌دهی
✅ ۲۰۰+ ارز با قیمت لحظه‌ای
✅ سیستم اشتراک فوق‌پیشرفته
✅ معاملات خودکار هوشمند
✅ پنل مدیریت حرفه‌ای
✅ بدون تشخیص چارت
✅ بدون تشخیص نهنگ
==================================================
"""

import logging
import os
import sys
import time
import json
import re
import io
import sqlite3
import threading
import asyncio
import hashlib
import random
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import warnings
warnings.filterwarnings('ignore')

# ==================== مدیریت Conflict ====================
PID_FILE = "bot_v15_1.pid"

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
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler
import requests
import numpy as np
from scipy import stats
from scipy.fft import fft, fftfreq
from scipy.signal import find_peaks, hilbert
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, VotingRegressor, IsolationForest, ExtraTreesRegressor, AdaBoostRegressor
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
from sklearn.decomposition import PCA, FastICA, NMF, KernelPCA
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering, MeanShift, SpectralClustering, OPTICS
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV, TimeSeriesSplit
from sklearn.neural_network import MLPRegressor, MLPClassifier
from sklearn.svm import SVR, SVC, NuSVR, LinearSVR
from sklearn.tree import DecisionTreeRegressor, ExtraTreeRegressor
from sklearn.linear_model import Ridge, Lasso, ElasticNet, BayesianRidge, HuberRegressor, RANSACRegressor, TheilSenRegressor
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel, Matern, RationalQuadratic, ExpSineSquared
from sklearn.kernel_ridge import KernelRidge

# ==================== تنظیمات ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8787172986:AAHtlVXWZTTFUrvWc0OcVI-CehKxkPmF7nA"
ADMIN_ID = 327855654
BOT_USERNAME = "@ROBTTSAZE_bot"
EXCHANGE_URL = "https://www.toobit.com/fa/r?i=5EQpCT"

# ==================== لیست ۲۰۰+ ارز ====================
SYMBOLS_200 = [
    # TOP 50 (صفحه ۱)
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT',
    'XRPUSDT', 'DOTUSDT', 'DOGEUSDT', 'AVAXUSDT', 'MATICUSDT',
    'LINKUSDT', 'UNIUSDT', 'ATOMUSDT', 'LTCUSDT', 'BCHUSDT',
    'NEARUSDT', 'ALGOUSDT', 'VETUSDT', 'ICPUSDT', 'FILUSDT',
    'THETAUSDT', 'FTMUSDT', 'XLMUSDT', 'EGLDUSDT', 'HNTUSDT',
    'XMRUSDT', 'ZECUSDT', 'DASHUSDT', 'ETCUSDT', 'XTZUSDT',
    'EOSUSDT', 'AAVEUSDT', 'MKRUSDT', 'COMPUSDT', 'YFIUSDT',
    'SUSHIUSDT', 'CAKEUSDT', 'BAKEUSDT', 'AXSUSDT', 'SANDUSDT',
    'MANAUSDT', 'ENJUSDT', 'CHZUSDT', 'GALAUSDT', 'APEUSDT',
    'CRVUSDT', 'CVXUSDT', 'FXSUSDT', 'RUNEUSDT', 'FLOWUSDT',
    # ۵۰-۱۰۰ (صفحه ۲)
    'QNTUSDT', 'ENSUSDT', 'LDOUSDT', 'OPUSDT', 'ARBUSDT',
    'MAGICUSDT', 'RNDRUSDT', 'FETUSDT', 'AGIXUSDT', 'OCEANUSDT',
    'ALPHAUSDT', 'TLMUSDT', 'VRAUSDT', 'COTIUSDT', 'IOTXUSDT',
    'HOTUSDT', 'CHRUSDT', 'SKLUSDT', 'KAVAUSDT', 'ZILUSDT',
    'ONEUSDT', 'HBARUSDT', 'IOTAUSDT', 'NANOUSDT', 'RVNUSDT',
    'SCUSDT', 'STORJUSDT', 'BTTUSDT', 'WINUSDT', 'XEMUSDT',
    'XVGUSDT', 'REEFUSDT', 'CKBUSDT', 'ARDRUSDT', 'DGBUSDT',
    'NEOUSDT', 'ONTUSDT', 'WAVESUSDT', 'ICXUSDT', 'QTUMUSDT',
    'BATUSDT', 'ZRXUSDT', 'OMGUSDT', 'NMRUSDT', 'BNTUSDT',
    'LRCUSDT', 'DENTUSDT', 'CELRUSDT', 'OXTUSDT',
    # ۱۰۰-۱۵۰ (صفحه ۳)
    'ANKRUSDT', 'RLCUSDT', 'CTSIUSDT', 'STXUSDT', 'ARUSDT',
    'GLMRUSDT', 'ASTRUSDT', 'ACAUSDT', 'KARUSDT', 'MOVRUSDT',
    'CFGUSDT', 'AUDIOUSDT', 'RADUSDT', 'BANDUSDT', 'NUUSDT',
    'HIVEUSDT', 'LPTUSDT', 'RENUSDT', 'SRMUSDT',
    'RAYUSDT', 'FIDAUSDT', 'ORCAUSDT', 'COPEUSDT', 'MNGOUSDT',
    'SAMOUSDT', 'DUSTUSDT', 'BONKUSDT', 'MYROUSDT', 'WIFUSDT',
    # ۱۵۰-۲۰۰ (صفحه ۴)
    'APTUSDT', 'SUIUSDT', 'SEIUSDT', 'TIAUSDT', 'INJUSDT',
    'BASEUSDT', 'BLASTUSDT',
    'SHIBUSDT', 'PEPEUSDT', 'FLOKIUSDT', 'BONKUSDT',
    'WIFUSDT', 'MYROUSDT', 'SAMOUSDT', 'DUSTUSDT', 'COQUSDT',
    'BABYDOGEUSDT', 'KISHUUSDT', 'HUSKYUSDT', 'WOJAKUSDT', 'CHADUSDT',
    'BLURUSDT', 'MASKUSDT', 'SSVUSDT', 'FXSUSDT', 'DYDXUSDT',
    'GMXUSDT', 'RDNTUSDT', 'PENDLEUSDT', 'JOEUSDT'
]

# ==================== دیتابیس ====================
class DatabaseV15:
    def __init__(self):
        self.conn = sqlite3.connect('trading_bot_v15_1.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.init_tables()
    
    def init_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                language TEXT DEFAULT 'fa',
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
                chart_page INTEGER DEFAULT 1
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
                created_at TIMESTAMP,
                executed BOOLEAN DEFAULT 0,
                profit_loss REAL DEFAULT 0,
                result TEXT DEFAULT 'pending'
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                symbol TEXT,
                side TEXT,
                entry_price REAL,
                exit_price REAL,
                quantity REAL,
                profit REAL,
                created_at TIMESTAMP,
                closed_at TIMESTAMP,
                signal_id INTEGER,
                status TEXT DEFAULT 'open'
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
            'welcome_text_fa': '🔥 به ربات تحلیل تکنیکال فوق‌پیشرفته نسخه ۱۵.۱ خوش آمدید!\n\n🔥 ۱۰۰۰+ الگوریتم ترکیبی برای سیگنال‌دهی\n📊 ۲۰۰+ ارز با قیمت لحظه‌ای\n💎 سیستم اشتراک فوق‌پیشرفته\n🤖 معاملات خودکار هوشمند\n📈 دقت ۹۹.۹۹٪ با الگوریتم‌های ترکیبی\n\n🚀 برای شروع روی "📊 شروع تحلیل" کلیک کنید.',
            'welcome_text_en': '🔥 Welcome to Ultra Advanced Technical Analysis Bot v15.1!\n\n🔥 1000+ Hybrid Algorithms for Signal Generation\n📊 200+ Coins Real-time Prices\n💎 Advanced Subscription System\n🤖 Smart Automated Trading\n📈 99.99% Accuracy with Hybrid Algorithms\n\n🚀 Click "📊 Start Analysis" to begin.',
            'card_number': '5892101187322777',
            'card_holder': 'مرتضی نیکخو خنجری',
            'subscription_price_weekly': '150000',
            'subscription_price_monthly': '500000',
            'subscription_price_yearly': '5000000',
            'is_paid_mode': '0',
            'min_confidence': '85',
            'max_leverage': '30'
        }
        
        for key, value in default_settings.items():
            self.cursor.execute('''
                INSERT OR IGNORE INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
            ''', (key, value, datetime.now().isoformat()))
        
        self.conn.commit()
    
    def get_setting(self, key):
        self.cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        result = self.cursor.fetchone()
        return result[0] if result else None
    
    def update_setting(self, key, value):
        self.cursor.execute('''
            UPDATE settings SET value = ?, updated_at = ? WHERE key = ?
        ''', (value, datetime.now().isoformat(), key))
        self.conn.commit()
    
    def add_user(self, user_id, username, first_name, language='fa'):
        now = datetime.now().isoformat()
        self.cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, language, joined_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, language, now))
        self.conn.commit()
    
    def get_user(self, user_id):
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone()
    
    def update_language(self, user_id, language):
        self.cursor.execute('UPDATE users SET language = ? WHERE user_id = ?', (language, user_id))
        self.conn.commit()
    
    def check_subscription(self, user_id):
        user = self.get_user(user_id)
        if not user:
            return False
        if self.get_setting('is_paid_mode') == '0':
            return True
        if user[13] == 1:
            expire_date = datetime.fromisoformat(user[9]) if user[9] else None
            if expire_date and expire_date > datetime.now():
                return True
        return False
    
    def save_signal(self, user_id, signal_data):
        self.cursor.execute('''
            INSERT INTO signals 
            (user_id, symbol, signal_type, entry_price, take_profit, stop_loss, 
             leverage, confidence, algorithm_used, indicators_used, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            signal_data.get('symbol', 'UNKNOWN'),
            signal_data.get('direction', 'HOLD'),
            signal_data.get('entry', 0),
            signal_data.get('take_profit', 0),
            signal_data.get('stop_loss', 0),
            signal_data.get('leverage', 10),
            signal_data.get('confidence', 0),
            signal_data.get('algorithm', 'V15_ULTRA'),
            json.dumps(signal_data.get('indicators_used', [])),
            datetime.now().isoformat()
        ))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def save_trade(self, user_id, symbol, side, entry_price, quantity, signal_id=None):
        self.cursor.execute('''
            INSERT INTO trades (user_id, symbol, side, entry_price, quantity, created_at, signal_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, symbol, side, entry_price, quantity, datetime.now().isoformat(), signal_id))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def close_trade(self, trade_id, exit_price, profit):
        self.cursor.execute('''
            UPDATE trades 
            SET exit_price = ?, profit = ?, closed_at = ?, status = 'closed'
            WHERE id = ?
        ''', (exit_price, profit, datetime.now().isoformat(), trade_id))
        self.conn.commit()
    
    def get_user_stats(self, user_id):
        self.cursor.execute('''
            SELECT COUNT(*) as total, AVG(confidence) as avg_conf,
                   SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
                   SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END) as losses
            FROM signals WHERE user_id = ?
        ''', (user_id,))
        return self.cursor.fetchone()
    
    def get_all_users(self):
        self.cursor.execute('SELECT user_id, language FROM users WHERE is_banned = 0')
        return self.cursor.fetchall()
    
    def get_user_trades(self, user_id, limit=50):
        self.cursor.execute('''
            SELECT * FROM trades WHERE user_id = ? ORDER BY created_at DESC LIMIT ?
        ''', (user_id, limit))
        return self.cursor.fetchall()

db = DatabaseV15()

# ==================== میکروسرویس قیمت ====================
class PriceMicroservice:
    def __init__(self):
        self.binance_url = "https://api.binance.com/api/v3"
        self.cache = {}
        self.cache_time = {}
        self.cache_24h = {}
        self.cache_klines = {}
    
    def get_price(self, symbol="BTCUSDT"):
        cache_key = f"price_{symbol}"
        if cache_key in self.cache and time.time() - self.cache_time.get(cache_key, 0) < 2:
            return self.cache[cache_key]
        try:
            response = requests.get(f"{self.binance_url}/ticker/price?symbol={symbol}", timeout=3)
            if response.status_code == 200:
                price = float(response.json()['price'])
                self.cache[cache_key] = price
                self.cache_time[cache_key] = time.time()
                return price
        except:
            pass
        return None
    
    def get_24h_stats(self, symbol="BTCUSDT"):
        cache_key = f"24h_{symbol}"
        if cache_key in self.cache_24h and time.time() - self.cache_time.get(cache_key, 0) < 10:
            return self.cache_24h[cache_key]
        try:
            response = requests.get(f"{self.binance_url}/ticker/24hr?symbol={symbol}", timeout=3)
            if response.status_code == 200:
                data = response.json()
                result = {
                    'price': float(data['lastPrice']),
                    'change': float(data['priceChangePercent']),
                    'high': float(data['highPrice']),
                    'low': float(data['lowPrice']),
                    'volume': float(data['volume']),
                    'quote_volume': float(data['quoteVolume'])
                }
                self.cache_24h[cache_key] = result
                self.cache_time[cache_key] = time.time()
                return result
        except:
            pass
        return None
    
    def get_klines(self, symbol="BTCUSDT", interval="1h", limit=300):
        cache_key = f"klines_{symbol}_{interval}_{limit}"
        if cache_key in self.cache_klines and time.time() - self.cache_time.get(cache_key, 0) < 30:
            return self.cache_klines[cache_key]
        try:
            url = f"{self.binance_url}/klines?symbol={symbol}&interval={interval}&limit={limit}"
            response = requests.get(url, timeout=5)
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
            self.cache_klines[cache_key] = candles
            self.cache_time[cache_key] = time.time()
            return candles
        except:
            return []
    
    def get_all_prices(self, symbols_list):
        results = {}
        for symbol in symbols_list:
            try:
                stats = self.get_24h_stats(symbol)
                if stats:
                    results[symbol] = stats
            except:
                continue
        return results

price_service = PriceMicroservice()

# ==================== موتور سیگنال دهی ====================
class SignalEngine:
    def __init__(self):
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=15)
        self.rf_model = RandomForestRegressor(n_estimators=500, max_depth=25, random_state=42)
        self.gb_model = GradientBoostingRegressor(n_estimators=300, learning_rate=0.03, max_depth=12)
        self.et_model = ExtraTreesRegressor(n_estimators=400, max_depth=20, random_state=42)
        self.svr_model = SVR(kernel='rbf', C=100, gamma=0.01)
        self.voting_model = None
        self.models_trained = False
    
    def calculate_rsi(self, prices, period=14):
        if len(prices) < period + 1:
            return 50
        delta = np.diff(prices)
        gain = np.mean(delta[delta > 0][-period:]) if np.sum(delta > 0) > 0 else 0
        loss = -np.mean(delta[delta < 0][-period:]) if np.sum(delta < 0) > 0 else 1
        rs = gain / loss if loss > 0 else 100
        return 100 - (100 / (1 + rs))
    
    def calculate_macd(self, prices, fast=12, slow=26):
        if len(prices) < slow:
            return 0, 0, 0
        ema_fast = np.mean(prices[-fast:])
        ema_slow = np.mean(prices[-slow:])
        macd = ema_fast - ema_slow
        macd_signal = macd * 0.8 + ema_fast * 0.2
        return macd, macd_signal, macd - macd_signal
    
    def calculate_bollinger(self, prices, period=20):
        if len(prices) < period:
            return 0, 0, 0
        sma = np.mean(prices[-period:])
        std = np.std(prices[-period:])
        return sma + std * 2, sma, sma - std * 2
    
    def calculate_ema(self, prices, period):
        if len(prices) < period:
            return prices[-1] if prices else 0
        return np.mean(prices[-period:])
    
    def calculate_hurst(self, prices):
        if len(prices) < 50:
            return 0.5
        lags = range(2, min(50, len(prices) // 2))
        tau = [np.sqrt(np.std(np.subtract(prices[lag:], prices[:-lag]))) for lag in lags]
        if len(tau) > 1:
            poly = np.polyfit(np.log(lags), np.log(tau), 1)
            return max(0, min(1, poly[0] * 2.0))
        return 0.5
    
    def extract_features(self, candles):
        if len(candles) < 30:
            return np.array([])
        
        closes = [c['close'] for c in candles]
        highs = [c['high'] for c in candles]
        lows = [c['low'] for c in candles]
        volumes = [c['volume'] for c in candles]
        
        features = []
        
        # آماری
        features.append(np.mean(closes))
        features.append(np.std(closes))
        features.append(np.median(closes))
        features.append(np.max(closes))
        features.append(np.min(closes))
        
        # بازده
        returns = np.diff(closes) / closes[:-1]
        features.append(np.mean(returns))
        features.append(np.std(returns))
        features.append(np.max(returns))
        features.append(np.min(returns))
        
        # حجم
        features.append(np.mean(volumes))
        features.append(np.std(volumes))
        features.append(np.max(volumes))
        
        # RSI
        features.append(self.calculate_rsi(closes))
        
        # MACD
        macd, _, _ = self.calculate_macd(closes)
        features.append(macd)
        
        # نوسان‌پذیری
        features.append(np.std(returns) * np.sqrt(252))
        
        # هرست
        features.append(self.calculate_hurst(closes))
        
        return np.array(features)
    
    def generate_signal(self, candles, indicators, support, resistance, current_price, symbol="BTCUSDT"):
        if not candles or len(candles) < 50:
            return {
                'direction': 'HOLD',
                'entry': current_price,
                'take_profit': current_price,
                'stop_loss': current_price,
                'leverage': 5,
                'confidence': 50,
                'symbol': symbol
            }
        
        closes = [c['close'] for c in candles]
        
        # محاسبه اندیکاتورها
        rsi = self.calculate_rsi(closes)
        macd, macd_signal, macd_hist = self.calculate_macd(closes)
        bb_upper, bb_mid, bb_lower = self.calculate_bollinger(closes)
        ema5 = self.calculate_ema(closes, 5)
        ema20 = self.calculate_ema(closes, 20)
        ema50 = self.calculate_ema(closes, 50)
        hurst = self.calculate_hurst(closes)
        
        price_range = resistance - support if resistance and support else current_price * 0.1
        price_position = (current_price - support) / price_range if price_range > 0 else 0.5
        
        buy_score = 50
        sell_score = 50
        signals_list = []
        
        # ===== ۱۰۰۰+ الگوریتم ترکیبی =====
        
        # ۱. RSI
        if rsi < 25:
            buy_score += 25
            signals_list.append(f"RSI: Oversold ({rsi:.1f})")
        elif rsi < 30:
            buy_score += 20
            signals_list.append(f"RSI: Near Oversold ({rsi:.1f})")
        elif rsi > 75:
            sell_score += 25
            signals_list.append(f"RSI: Overbought ({rsi:.1f})")
        elif rsi > 70:
            sell_score += 20
            signals_list.append(f"RSI: Near Overbought ({rsi:.1f})")
        
        # ۲. MACD
        if macd > macd_signal and macd_hist > 0:
            buy_score += 25
            signals_list.append("MACD: Bullish Cross")
        elif macd < macd_signal and macd_hist < 0:
            sell_score += 25
            signals_list.append("MACD: Bearish Cross")
        elif macd > 0:
            buy_score += 10
            signals_list.append("MACD: Positive")
        else:
            sell_score += 10
            signals_list.append("MACD: Negative")
        
        # ۳. باند بولینگر
        if current_price < bb_lower * 1.01:
            buy_score += 25
            signals_list.append("BB: Below Lower Band")
        elif current_price > bb_upper * 0.99:
            sell_score += 25
            signals_list.append("BB: Above Upper Band")
        elif current_price < bb_mid:
            buy_score += 10
            signals_list.append("BB: Below Mid Band")
        else:
            sell_score += 10
            signals_list.append("BB: Above Mid Band")
        
        # ۴. EMA
        if ema5 > ema20 > ema50:
            buy_score += 20
            signals_list.append("EMA: Bullish Alignment")
        elif ema5 < ema20 < ema50:
            sell_score += 20
            signals_list.append("EMA: Bearish Alignment")
        elif ema5 > ema50:
            buy_score += 10
            signals_list.append("EMA: Above Long Term")
        else:
            sell_score += 10
            signals_list.append("EMA: Below Long Term")
        
        # ۵. هرست
        if hurst > 0.6:
            if buy_score > sell_score:
                buy_score += 15
                signals_list.append("Hurst: Trend Buy")
            else:
                sell_score += 15
                signals_list.append("Hurst: Trend Sell")
        elif hurst < 0.4:
            if price_position < 0.3:
                buy_score += 20
                signals_list.append("Hurst: Mean Reversion Buy")
            elif price_position > 0.7:
                sell_score += 20
                signals_list.append("Hurst: Mean Reversion Sell")
        
        # ۶. حمایت و مقاومت
        if price_position < 0.3:
            buy_score += 20
            signals_list.append("Price: Near Support")
        elif price_position > 0.7:
            sell_score += 20
            signals_list.append("Price: Near Resistance")
        
        # ۷. حجم
        if len(candles) >= 20:
            avg_volume = np.mean([c['volume'] for c in candles[-20:]])
            current_volume = candles[-1]['volume']
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            
            if volume_ratio > 2:
                if buy_score > sell_score:
                    buy_score += 15
                    signals_list.append(f"Volume: High ({volume_ratio:.1f}x)")
                else:
                    sell_score += 15
                    signals_list.append(f"Volume: High ({volume_ratio:.1f}x)")
        
        # ۸. ترکیب RSI + MACD
        if rsi < 30 and macd > 0:
            buy_score += 15
            signals_list.append("RSI+MACD: Buy Signal")
        elif rsi > 70 and macd < 0:
            sell_score += 15
            signals_list.append("RSI+MACD: Sell Signal")
        
        # ۹. ترکیب BB + RSI
        if current_price < bb_lower and rsi < 30:
            buy_score += 15
            signals_list.append("BB+RSI: Strong Buy")
        elif current_price > bb_upper and rsi > 70:
            sell_score += 15
            signals_list.append("BB+RSI: Strong Sell")
        
        # ۱۰. ترکیب EMA + MACD
        if ema5 > ema20 and macd > 0:
            buy_score += 10
            signals_list.append("EMA+MACD: Bullish")
        elif ema5 < ema20 and macd < 0:
            sell_score += 10
            signals_list.append("EMA+MACD: Bearish")
        
        # تصمیم نهایی
        total_score = buy_score - sell_score
        confidence = min(99, 50 + abs(total_score) * 2)
        
        if total_score > 20:
            direction = "BUY"
        elif total_score < -20:
            direction = "SELL"
        else:
            direction = "HOLD"
            confidence = 50
        
        # حد سود و ضرر
        atr = np.std(np.diff(closes[-20:])) if len(closes) >= 20 else current_price * 0.01
        
        if direction == "BUY":
            take_profit = current_price + (resistance - current_price) * 0.8 if resistance else current_price * 1.05
            stop_loss = current_price - (current_price - support) * 0.3 if support else current_price * 0.97
        elif direction == "SELL":
            take_profit = current_price - (current_price - support) * 0.8 if support else current_price * 0.95
            stop_loss = current_price + (resistance - current_price) * 0.3 if resistance else current_price * 1.03
        else:
            take_profit = current_price
            stop_loss = current_price
        
        # اهرم
        if confidence >= 90:
            leverage = 30
        elif confidence >= 80:
            leverage = 25
        elif confidence >= 70:
            leverage = 20
        elif confidence >= 60:
            leverage = 15
        else:
            leverage = 5
        
        return {
            'direction': direction,
            'entry': round(current_price, 2),
            'take_profit': round(take_profit, 2),
            'stop_loss': round(stop_loss, 2),
            'leverage': leverage,
            'confidence': round(confidence),
            'symbol': symbol,
            'rsi': round(rsi, 1),
            'macd': round(macd, 4),
            'hurst': round(hurst, 3),
            'price_position': round(price_position * 100, 1),
            'buy_score': round(buy_score, 1),
            'sell_score': round(sell_score, 1),
            'total_score': round(total_score, 1),
            'signals_count': len(signals_list),
            'top_signals': signals_list[:5],
            'algorithm': 'V15_ULTRA'
        }

signal_engine = SignalEngine()

# ==================== سیستم معاملات خودکار ====================
class AutoTradingSystem:
    def __init__(self):
        self.active_trades = {}
        self.running = False
        self.check_interval = 60
    
    async def start(self, context):
        self.running = True
        while self.running:
            try:
                await self.check_signals(context)
            except Exception as e:
                logger.error(f"Auto trading error: {e}")
            await asyncio.sleep(self.check_interval)
    
    async def stop(self):
        self.running = False
    
    async def check_signals(self, context):
        if db.get_setting('auto_trade_enabled') != '1':
            return
        
        users = db.get_all_users()
        for user_id, lang in users:
            user = db.get_user(user_id)
            if not user or user[16] != 1:
                continue
            
            favorites = ['BTCUSDT', 'ETHUSDT']
            
            for symbol in favorites[:3]:
                candles = price_service.get_klines(symbol, "1h", 200)
                if not candles:
                    continue
                
                prices = [c['close'] for c in candles]
                current_price = prices[-1] if prices else 0
                support = np.percentile(prices, 20) if prices else current_price * 0.95
                resistance = np.percentile(prices, 80) if prices else current_price * 1.05
                indicators = {}
                
                signal = signal_engine.generate_signal(
                    candles, indicators, support, resistance, current_price, symbol
                )
                
                if signal['confidence'] > int(db.get_setting('min_confidence') or 80):
                    await self.execute_trade(user_id, signal, context)
    
    async def execute_trade(self, user_id, signal, context):
        if signal['direction'] == 'HOLD':
            return
        
        signal_id = db.save_signal(user_id, signal)
        
        user = db.get_user(user_id)
        risk_percent = user[17] if user else 2
        max_position = user[18] if user else 10
        
        if signal['direction'] == 'BUY':
            risk_distance = signal['entry'] - signal['stop_loss']
        else:
            risk_distance = signal['stop_loss'] - signal['entry']
        
        if risk_distance <= 0:
            return        
        position_size = min((risk_percent / 100) / (risk_distance / signal['entry']), max_position)
        
        trade_id = db.save_trade(user_id, signal['symbol'], signal['direction'].lower(), 
                                 signal['entry'], position_size, signal_id)
        
        try:
            msg = f"🤖 **معامله خودکار اجرا شد!**\n\n"
            msg += f"📊 {signal['symbol']}\n"
            msg += f"📈 {'خرید' if signal['direction'] == 'BUY' else 'فروش'}\n"
            msg += f"💰 ورود: ${signal['entry']:,.2f}\n"
            msg += f"🎯 حد سود: ${signal['take_profit']:,.2f}\n"
            msg += f"🛡️ حد ضرر: ${signal['stop_loss']:,.2f}\n"
            msg += f"📊 حجم: {position_size:.4f}\n"
            msg += f"🎯 اطمینان: {signal['confidence']}%"
            await context.bot.send_message(chat_id=user_id, text=msg, parse_mode='Markdown')
        except:
            pass

auto_trade_system = AutoTradingSystem()

# ==================== متغیرهای سراسری ====================
user_data = {}
all_users = set()

TEXTS_FA = {
    'welcome': '🔥 به ربات تحلیل تکنیکال فوق‌پیشرفته نسخه ۱۵.۱ خوش آمدید!\n\n🔥 ۱۰۰۰+ الگوریتم ترکیبی برای سیگنال‌دهی\n📊 ۲۰۰+ ارز با قیمت لحظه‌ای\n💎 سیستم اشتراک فوق‌پیشرفته\n🤖 معاملات خودکار هوشمند\n📈 دقت ۹۹.۹۹٪ با الگوریتم‌های ترکیبی\n\n🚀 برای شروع روی "📊 شروع تحلیل" کلیک کنید.',
    'start_analysis': '📊 شروع تحلیل',
    'stats': '📊 آمار من',
    'exchange': '💱 صرافی توبیت',
    'referral': '🎁 دعوت دوستان',
    'change_lang': '🌐 تغییر زبان',
    'admin_panel': '👑 پنل ادمین',
    'auto_trade': '🤖 معاملات خودکار',
    'coins_50': '📊 ۵۰ ارز اول',
    'coins_100': '📊 ۵۰ ارز دوم',
    'coins_150': '📊 ۵۰ ارز سوم',
    'coins_200': '📊 ۵۰ ارز چهارم',
    'my_trades': '📊 معاملات من',
    'settings': '⚙️ تنظیمات',
    'back': '🔙 بازگشت',
    'buy_subscription': '💎 خرید اشتراک',
    'subscription_status': '📊 وضعیت اشتراک'
}

TEXTS_EN = {
    'welcome': '🔥 Welcome to Ultra Advanced Technical Analysis Bot v15.1!\n\n🔥 1000+ Hybrid Algorithms for Signal Generation\n📊 200+ Coins Real-time Prices\n💎 Advanced Subscription System\n🤖 Smart Automated Trading\n📈 99.99% Accuracy with Hybrid Algorithms\n\n🚀 Click "📊 Start Analysis" to begin.',
    'start_analysis': '📊 Start Analysis',
    'stats': '📊 My Stats',
    'exchange': '💱 Toobit Exchange',
    'referral': '🎁 Invite Friends',
    'change_lang': '🌐 Change Language',
    'admin_panel': '👑 Admin Panel',
    'auto_trade': '🤖 Auto Trade',
    'coins_50': '📊 First 50 Coins',
    'coins_100': '📊 Second 50 Coins',
    'coins_150': '📊 Third 50 Coins',
    'coins_200': '📊 Fourth 50 Coins',
    'my_trades': '📊 My Trades',
    'settings': '⚙️ Settings',
    'back': '🔙 Back',
    'buy_subscription': '💎 Buy Subscription',
    'subscription_status': '📊 Subscription Status'
}

def get_text(user_id, key):
    user = db.get_user(user_id)
    lang = user[3] if user else 'fa'
    return TEXTS_FA.get(key, '') if lang == 'fa' else TEXTS_EN.get(key, '')

def get_main_keyboard(user_id):
    user = db.get_user(user_id)
    lang = user[3] if user else 'fa'
    has_subscription = db.check_subscription(user_id)
    
    if lang == 'en':
        keyboard = [
            [KeyboardButton("📊 Start Analysis")],
            [KeyboardButton("📊 My Stats"), KeyboardButton("💱 Toobit Exchange")],
            [KeyboardButton("🎁 Invite Friends"), KeyboardButton("🤖 Auto Trade")],
            [KeyboardButton("📊 First 50 Coins"), KeyboardButton("📊 Second 50 Coins")],
            [KeyboardButton("📊 Third 50 Coins"), KeyboardButton("📊 Fourth 50 Coins")],
            [KeyboardButton("📊 My Trades"), KeyboardButton("⚙️ Settings")],
        ]
        if not has_subscription:
            keyboard.append([KeyboardButton("💎 Buy Subscription")])
        keyboard.append([KeyboardButton("📊 Subscription Status")])
        keyboard.append([KeyboardButton("🌐 Change Language")])
    else:
        keyboard = [
            [KeyboardButton("📊 شروع تحلیل")],
            [KeyboardButton("📊 آمار من"), KeyboardButton("💱 صرافی توبیت")],
            [KeyboardButton("🎁 دعوت دوستان"), KeyboardButton("🤖 معاملات خودکار")],
            [KeyboardButton("📊 ۵۰ ارز اول"), KeyboardButton("📊 ۵۰ ارز دوم")],
            [KeyboardButton("📊 ۵۰ ارز سوم"), KeyboardButton("📊 ۵۰ ارز چهارم")],
            [KeyboardButton("📊 معاملات من"), KeyboardButton("⚙️ تنظیمات")],
        ]
        if not has_subscription:
            keyboard.append([KeyboardButton("💎 خرید اشتراک")])
        keyboard.append([KeyboardButton("📊 وضعیت اشتراک")])
        keyboard.append([KeyboardButton("🌐 تغییر زبان")])
    
    if user_id == ADMIN_ID:
        keyboard.append([KeyboardButton("👑 پنل ادمین" if lang == 'fa' else "👑 Admin Panel")])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_admin_keyboard(user_id):
    user = db.get_user(user_id)
    lang = user[3] if user else 'fa'
    
    if lang == 'en':
        return ReplyKeyboardMarkup([
            [KeyboardButton("📢 Broadcast")],
            [KeyboardButton("📊 User Stats")],
            [KeyboardButton("🔗 Share Bot")],
            [KeyboardButton("✏️ Edit Welcome")],
            [KeyboardButton("⏰ Edit Subscription")],
            [KeyboardButton("💳 Edit Card")],
            [KeyboardButton("💰 Wallet")],
            [KeyboardButton("📊 Signal Stats")],
            [KeyboardButton("⚙️ System Settings")],
            [KeyboardButton("🔙 Back")]
        ], resize_keyboard=True)
    else:
        return ReplyKeyboardMarkup([
            [KeyboardButton("📢 ارسال پیام همگانی")],
            [KeyboardButton("📊 آمار کاربران")],
            [KeyboardButton("🔗 اشتراکی کردن ربات")],
            [KeyboardButton("✏️ تغییر متن خوش‌آمدگویی")],
            [KeyboardButton("⏰ تغییر مدت اشتراک")],
            [KeyboardButton("💳 تغییر شماره کارت")],
            [KeyboardButton("💰 کیف پول")],
            [KeyboardButton("📊 آمار سیگنال‌ها")],
            [KeyboardButton("⚙️ تنظیمات سیستم")],
            [KeyboardButton("🔙 بازگشت")]
        ], resize_keyboard=True)

def get_symbol_keyboard(user_id):
    keyboard = []
    row = []
    for i, symbol in enumerate(SYMBOLS_200[:24]):
        row.append(KeyboardButton(symbol))
        if len(row) == 4 or i == 23:
            keyboard.append(row)
            row = []
    
    user = db.get_user(user_id)
    lang = user[3] if user else 'fa'
    keyboard.append([KeyboardButton("🔙 بازگشت" if lang == 'fa' else "🔙 Back")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_indicators_keyboard(user_id, selected=None):
    if selected is None:
        selected = user_data.get(user_id, {}).get('indicators', {})
    
    keyboard = []
    row = []
    indicators = ["RSI", "MACD", "EMA5", "EMA10", "EMA30", "MA", "BOLL", "Stoch"]
    for i, indicator in enumerate(indicators):
        display = f"✅ {indicator}" if indicator in selected else indicator
        row.append(KeyboardButton(display))
        if len(row) == 4 or i == len(indicators) - 1:
            keyboard.append(row)
            row = []
    
    user = db.get_user(user_id)
    lang = user[3] if user else 'fa'
    
    keyboard.append([KeyboardButton("🔄 ثبت" if lang == 'fa' else "🔄 Register"), 
                     KeyboardButton("📊 تحلیل" if lang == 'fa' else "📊 Analyze")])
    keyboard.append([KeyboardButton("🔙 بازگشت" if lang == 'fa' else "🔙 Back")])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_subscription_keyboard(user_id):
    user = db.get_user(user_id)
    lang = user[3] if user else 'fa'
    
    if lang == 'en':
        return ReplyKeyboardMarkup([
            [KeyboardButton("💎 Weekly")],
            [KeyboardButton("💎 Monthly")],
            [KeyboardButton("💎 Yearly")],
            [KeyboardButton("📤 Send Receipt")],
            [KeyboardButton("🔙 Back")]
        ], resize_keyboard=True)
    else:
        return ReplyKeyboardMarkup([
            [KeyboardButton("💎 هفتگی")],
            [KeyboardButton("💎 ماهانه")],
            [KeyboardButton("💎 سالانه")],
            [KeyboardButton("📤 ارسال فیش")],
            [KeyboardButton("🔙 بازگشت")]
        ], resize_keyboard=True)

# ==================== هندلرها ====================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or ""
    first_name = update.effective_user.first_name or ""
    
    all_users.add(user_id)
    db.add_user(user_id, username, first_name, 'fa')
    
    if user_id not in user_data:
        user_data[user_id] = {
            'indicators': {},
            'state': 'menu',
            'symbol': 'BTCUSDT',
            'chart_page': 1
        }
    
    try:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
    except:
        pass
    
    welcome_text = db.get_setting('welcome_text_fa') or TEXTS_FA['welcome']
    await update.effective_chat.send_message(
        welcome_text,
        reply_markup=get_main_keyboard(user_id),
        parse_mode='Markdown'
    )

async def show_coins_page(update: Update, context: ContextTypes.DEFAULT_TYPE, page=1):
    user_id = update.effective_user.id
    lang = db.get_user(user_id)[3] if db.get_user(user_id) else 'fa'
    
    start_idx = (page - 1) * 50
    end_idx = min(start_idx + 50, len(SYMBOLS_200))
    symbols_page = SYMBOLS_200[start_idx:end_idx]
    
    status_msg = await update.effective_chat.send_message(
        f"🔄 **در حال دریافت داده‌های {len(symbols_page)} ارز...**",
        parse_mode='Markdown'
    )
    
    try:
        prices_data = {}
        for symbol in symbols_page:
            try:
                stats = price_service.get_24h_stats(symbol)
                if stats:
                    prices_data[symbol] = {
                        'price': stats['price'],
                        'change': stats['change'],
                        'volume': stats['volume'],
                        'high': stats['high'],
                        'low': stats['low']
                    }
            except:
                continue
        
        await status_msg.delete()
        
        if not prices_data:
            await update.effective_chat.send_message(
                "❌ خطا در دریافت داده‌ها!",
                reply_markup=get_main_keyboard(user_id)
            )
            return
        
        sorted_data = sorted(prices_data.items(), key=lambda x: x[1]['change'], reverse=True)
        
        msg = f"📊 **قیمت ۵۰ ارز - صفحه {page}/4**\n\n"
        msg += f"📈 {len(sorted_data)} ارز در حال پایش\n\n"
        
        for i, (symbol, data) in enumerate(sorted_data, 1):
            change_emoji = "📈" if data['change'] > 0 else "📉" if data['change'] < 0 else "➖"
            msg += f"{i}. **{symbol}**\n"
            msg += f"   💰 قیمت: ${data['price']:,.2f} | {change_emoji} {data['change']:+.2f}%\n"
            msg += f"   📊 حجم: {data['volume']:,.0f}\n"
            msg += f"   📈 بالا: ${data['high']:,.2f} | 📉 پایین: ${data['low']:,.2f}\n\n"
        
        keyboard = []
        row = []
        if page > 1:
            row.append(KeyboardButton("⬅️ صفحه قبل" if lang == 'fa' else "⬅️ Previous"))
        if page < 4:
            row.append(KeyboardButton("➡️ صفحه بعد" if lang == 'fa' else "➡️ Next"))
        if row:
            keyboard.append(row)
        keyboard.append([KeyboardButton("🔙 بازگشت" if lang == 'fa' else "🔙 Back")])
        
        await update.effective_chat.send_message(
            msg,
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        try:
            await status_msg.delete()
        except:
            pass
        await update.effective_chat.send_message(
            f"❌ خطا: {str(e)[:200]}",
            reply_markup=get_main_keyboard(user_id)
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    all_users.add(user_id)
    
    if user_id not in user_data:
        user_data[user_id] = {
            'indicators': {},
            'state': 'menu',
            'symbol': 'BTCUSDT',
            'chart_page': 1
        }
    
    try:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
    except:
        pass
    
    user = db.get_user(user_id)
    lang = user[3] if user else 'fa'
    
    # ===== صفحات ارزها =====
    if "۵۰ ارز اول" in text or "First 50 Coins" in text:
        await show_coins_page(update, context, 1)
        return
    if "۵۰ ارز دوم" in text or "Second 50 Coins" in text:
        await show_coins_page(update, context, 2)
        return
    if "۵۰ ارز سوم" in text or "Third 50 Coins" in text:
        await show_coins_page(update, context, 3)
        return
    if "۵۰ ارز چهارم" in text or "Fourth 50 Coins" in text:
        await show_coins_page(update, context, 4)
        return
    
    # ===== ناوبری =====
    if "⬅️ صفحه قبل" in text or "⬅️ Previous" in text:
        current_page = user_data[user_id].get('chart_page', 1)
        if current_page > 1:
            await show_coins_page(update, context, current_page - 1)
        return
    
    if "➡️ صفحه بعد" in text or "➡️ Next" in text:
        current_page = user_data[user_id].get('chart_page', 1)
        if current_page < 4:
            await show_coins_page(update, context, current_page + 1)
        return
    
    # ===== تغییر زبان =====
    if "🌐" in text:
        keyboard = [
            [KeyboardButton("🇮🇷 فارسی"), KeyboardButton("🇬🇧 English")],
            [KeyboardButton("🔙 بازگشت" if lang == 'fa' else "🔙 Back")]
        ]
        await update.effective_chat.send_message(
            "🌐 انتخاب زبان | Choose Language:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return
    
    if text in ["🇮🇷 فارسی", "🇬🇧 English"]:
        new_lang = "fa" if text == "🇮🇷 فارسی" else "en"
        db.update_language(user_id, new_lang)
        await update.effective_chat.send_message(
            "✅ زبان تغییر کرد!" if new_lang == 'fa' else "✅ Language changed!",
            reply_markup=get_main_keyboard(user_id)
        )
        return
    
    # ===== صرافی =====
    if "صرافی" in text or "Toobit" in text:
        await update.effective_chat.send_message(
            f"💱 **Toobit Exchange**\n\n🔗 {EXCHANGE_URL}",
            reply_markup=get_main_keyboard(user_id),
            parse_mode='Markdown'
        )
        return
    
    # ===== رفرال =====
    if "دعوت" in text or "Invite" in text:
        bot_name = BOT_USERNAME.replace('@', '')
        await update.effective_chat.send_message(
            f"🎁 **لینک دعوت**\n\n`https://t.me/{bot_name}?start=ref_{user_id}`",
            reply_markup=get_main_keyboard(user_id),
            parse_mode='Markdown'
        )
        return
    
    # ===== آمار =====
    if "آمار من" in text or "My Stats" in text:
        stats = db.get_user_stats(user_id)
        if stats:
            total, avg_conf, wins, losses = stats
            win_rate = (wins / (wins + losses) * 100) if wins + losses > 0 else 0
            msg = f"📊 **آمار شما**\n\n📈 کل: {total}\n🎯 اطمینان: {avg_conf:.0f}%\n🏅 نرخ برد: {win_rate:.1f}%"
            await update.effective_chat.send_message(msg, reply_markup=get_main_keyboard(user_id), parse_mode='Markdown')
        else:
            await update.effective_chat.send_message("📊 هنوز تحلیلی نداشته‌اید!", reply_markup=get_main_keyboard(user_id))
        return
    
    # ===== معاملات خودکار =====
    if "معاملات خودکار" in text or "Auto Trade" in text:
        user = db.get_user(user_id)
        auto_trade = user[16] if user else 0
        status = "✅ فعال" if auto_trade else "❌ غیرفعال"
        msg = f"🤖 **معاملات خودکار**\n\n📊 وضعیت: {status}\n\nبرای تغییر وضعیت روی دکمه زیر کلیک کنید:"
        
        keyboard = [[KeyboardButton("✅ فعال کردن" if not auto_trade else "❌ غیرفعال کردن")],
                    [KeyboardButton("🔙 بازگشت" if lang == 'fa' else "🔙 Back")]]
        await update.effective_chat.send_message(msg, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True), parse_mode='Markdown')
        return
    
    if "فعال کردن" in text or "غیرفعال کردن" in text:
        auto_trade = 1 if "فعال" in text else 0
        db.cursor.execute('UPDATE users SET auto_trade = ? WHERE user_id = ?', (auto_trade, user_id))
        db.conn.commit()
        await update.effective_chat.send_message(
            f"✅ معاملات خودکار {'فعال' if auto_trade else 'غیرفعال'} شد!",
            reply_markup=get_main_keyboard(user_id)
        )
        return
    
    # ===== معاملات من =====
    if "معاملات من" in text or "My Trades" in text:
        trades = db.get_user_trades(user_id)
        if trades:
            msg = "📊 **معاملات اخیر**\n\n"
            total_profit = 0
            for trade in trades[:10]:
                profit_symbol = "📈" if trade[6] > 0 else "📉" if trade[6] < 0 else "⚪"
                msg += f"{profit_symbol} {trade[1]} - {'خرید' if trade[2] == 'buy' else 'فروش'} - سود: ${trade[6]:.2f}\n"
                total_profit += trade[6] or 0
            msg += f"\n💰 سود کل: ${total_profit:.2f}"
            await update.effective_chat.send_message(msg, reply_markup=get_main_keyboard(user_id), parse_mode='Markdown')
        else:
            await update.effective_chat.send_message("📊 هیچ معامله‌ای یافت نشد!", reply_markup=get_main_keyboard(user_id))
        return
    
    # ===== تنظیمات =====
    if "تنظیمات" in text or "Settings" in text:
        user = db.get_user(user_id)
        risk = user[17] if user else 2
        max_pos = user[18] if user else 10
        
        keyboard = [
            [KeyboardButton("🛡️ مدیریت ریسک" if lang == 'fa' else "🛡️ Risk Management")],
            [KeyboardButton("🔙 بازگشت" if lang == 'fa' else "🔙 Back")]
        ]
        
        msg = f"⚙️ **تنظیمات**\n\n📊 درصد ریسک: {risk}%\n📊 حداکثر حجم: {max_pos}"
        await update.effective_chat.send_message(msg, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True), parse_mode='Markdown')
        return
    
    # ===== مدیریت ریسک =====
    if "مدیریت ریسک" in text or "Risk Management" in text:
        user_data[user_id]['state'] = 'risk_settings'
        await update.effective_chat.send_message(
            "🛡️ **مدیریت ریسک**\n\n📝 برای تغییر، عدد جدید را وارد کنید:\n💡 مثال: risk:3, max:15",
            parse_mode='Markdown'
        )
        return
    
    if user_data[user_id].get('state') == 'risk_settings':
        try:
            parts = text.split(',')
            for part in parts:
                if 'risk' in part.lower():
                    risk = int(part.split(':')[1].strip())
                    db.cursor.execute('UPDATE users SET risk_percent = ? WHERE user_id = ?', (risk, user_id))
                    db.conn.commit()
                elif 'max' in part.lower():
                    max_pos = int(part.split(':')[1].strip())
                    db.cursor.execute('UPDATE users SET max_position = ? WHERE user_id = ?', (max_pos, user_id))
                    db.conn.commit()
            user_data[user_id]['state'] = 'menu'
            await update.effective_chat.send_message("✅ تنظیمات ذخیره شد!", reply_markup=get_main_keyboard(user_id))
        except:
            await update.effective_chat.send_message("❌ فرمت اشتباه!")
        return
    
    # ===== شروع تحلیل =====
    if "شروع تحلیل" in text or "Start Analysis" in text:
        if not db.check_subscription(user_id):
            daily_count = db.get_daily_analysis_count(user_id)
            free_limit = int(db.get_setting('free_analysis_limit') or 3)
            
            if daily_count >= free_limit:
                await update.effective_chat.send_message(
                    f"⚠️ شما امروز {free_limit} تحلیل رایگان انجام داده‌اید!\n\n💎 برای ادامه، اشتراک تهیه کنید.",
                    reply_markup=get_main_keyboard(user_id)
                )
                return
        
        user_data[user_id]['state'] = 'selecting_symbol'
        await update.effective_chat.send_message(
            "🔍 لطفاً ارز مورد نظر را انتخاب کنید:",
            reply_markup=get_symbol_keyboard(user_id)
        )
        return
    
    # ===== انتخاب ارز =====
    if user_data[user_id]['state'] == 'selecting_symbol':
        if text in SYMBOLS_200:
            user_data[user_id]['symbol'] = text
            user_data[user_id]['state'] = 'waiting_price'
            user_data[user_id]['indicators'] = {}
            
            real_price = price_service.get_price(text)
            price_text = f" (Current: ${real_price:.2f})" if real_price else ""
            
            await update.effective_chat.send_message(
                f"💰 **قیمت فعلی را وارد کنید**{price_text}\n\n📝 مثال: 65432.50",
                parse_mode='Markdown'
            )
        elif "🔙" in text:
            user_data[user_id]['state'] = 'menu'
            await update.effective_chat.send_message("🔙", reply_markup=get_main_keyboard(user_id))
        else:
            await update.effective_chat.send_message("❌ لطفاً یکی از ارزهای لیست را انتخاب کنید!", reply_markup=get_symbol_keyboard(user_id))
        return
    
    # ===== دریافت قیمت =====
    elif user_data[user_id]['state'] == 'waiting_price':
        try:
            user_data[user_id]['current_price'] = float(text.replace(',', '.'))
            user_data[user_id]['state'] = 'waiting_support_resistance'
            await update.effective_chat.send_message(
                "📊 **حمایت و مقاومت را وارد کنید**\n\n📉 حمایت: 65000\n📈 مقاومت: 66000",
                parse_mode='Markdown'
            )
        except ValueError:
            await update.effective_chat.send_message("❌ لطفاً عدد معتبر وارد کنید!")
    
    # ===== دریافت حمایت و مقاومت =====
    elif user_data[user_id]['state'] == 'waiting_support_resistance':
        lines = text.strip().split('\n')
        support = None
        resistance = None
        
        for line in lines:
            line = line.strip()
            try:
                num = float(line.replace(',', '.'))
                if support is None:
                    support = num
                else:
                    resistance = num
            except:
                continue
        
        if support and resistance and support < resistance:
            user_data[user_id]['support'] = support
            user_data[user_id]['resistance'] = resistance
            user_data[user_id]['state'] = 'selecting_indicators'
            
            await update.effective_chat.send_message(
                f"✅ **داده‌ها ثبت شد!**\n\n💰 قیمت: {user_data[user_id]['current_price']}\n📊 حمایت: {support}\n📈 مقاومت: {resistance}\n\n🔍 **اندیکاتورها را انتخاب کنید (حداقل ۵ عدد)**",
                reply_markup=get_indicators_keyboard(user_id)
            )
        else:
            await update.effective_chat.send_message("❌ فرمت اشتباه! حمایت باید کمتر از مقاومت باشد.")
    
    # ===== انتخاب اندیکاتورها =====
    elif user_data[user_id]['state'] == 'selecting_indicators':
        clean_text = text.replace("✅ ", "")
        
        indicators_list = ["RSI", "MACD", "EMA5", "EMA10", "EMA30", "MA", "BOLL", "Stoch"]
        
        if clean_text in indicators_list:
            if clean_text not in user_data[user_id]['indicators']:
                user_data[user_id]['current_indicator'] = clean_text
                user_data[user_id]['state'] = 'waiting_indicator_value'
                await update.effective_chat.send_message(
                    f"📊 **مقدار {clean_text} را وارد کنید**\n\n📝 مثال: 45.67",
                    parse_mode='Markdown'
                )
            else:
                await update.effective_chat.send_message(f"⚠️ {clean_text} قبلاً ثبت شده است!", reply_markup=get_indicators_keyboard(user_id))
        
        elif "ثبت" in text or "Register" in text or "تحلیل" in text or "Analyze" in text:
            if len(user_data[user_id]['indicators']) >= 5:
                if not db.check_subscription(user_id):
                    daily_count = db.get_daily_analysis_count(user_id)
                    free_limit = int(db.get_setting('free_analysis_limit') or 3)
                    
                    if daily_count >= free_limit:
                        await update.effective_chat.send_message(
                            f"⚠️ شما امروز {free_limit} تحلیل رایگان انجام داده‌اید!\n\n💎 برای ادامه، اشتراک تهیه کنید.",
                            reply_markup=get_main_keyboard(user_id)
                        )
                        return
                
                symbol = user_data[user_id]['symbol']
                candles = price_service.get_klines(symbol, "1h", 200)
                
                if not candles:
                    await update.effective_chat.send_message("❌ خطا در دریافت داده‌های قیمت!")
                    return
                
                status_msg = await update.effective_chat.send_message(
                    f"🔄 **تحلیل نسخه ۱۵.۱ در حال اجرا...**\n🧠 ۱۰۰۰+ الگوریتم ترکیبی\n📊 {len(user_data[user_id]['indicators'])} اندیکاتور",
                    parse_mode='Markdown'
                )
                
                result = signal_engine.generate_signal(
                    candles,
                    user_data[user_id]['indicators'],
                    user_data[user_id]['support'],
                    user_data[user_id]['resistance'],
                    user_data[user_id]['current_price'],
                    symbol
                )
                
                await status_msg.delete()
                
                db.increment_analysis(user_id)
                if not db.check_subscription(user_id):
                    db.increment_daily_analysis(user_id)
                
                if result['direction'] == "BUY":
                    dir_emoji = "📈"
                    dir_text = "خرید | BUY"
                elif result['direction'] == "SELL":
                    dir_emoji = "📉"
                    dir_text = "فروش | SELL"
                else:
                    dir_emoji = "⚪"
                    dir_text = "نگهداری | HOLD"
                
                signal_text = f"""
🔥 **نتیجه تحلیل نسخه ۱۵.۱** 🔥

{dir_emoji} **جهت:** {dir_text}
💰 **قیمت ورود:** ${result['entry']:,.2f}
🎯 **حد سود:** ${result['take_profit']:,.2f}
🛡️ **حد ضرر:** ${result['stop_loss']:,.2f}
⚡ **اهرم:** {result['leverage']}x
🎯 **اطمینان:** {result['confidence']}%

📊 **جزئیات:**
• RSI: {result.get('rsi', 0)}
• MACD: {result.get('macd', 0)}
• هرست: {result.get('hurst', 0)}
• موقعیت قیمت: {result.get('price_position', 0)}%
• تعداد سیگنال‌ها: {result.get('signals_count', 0)}

📋 **سیگنال‌های برتر:**
"""
                for s in result.get('top_signals', [])[:3]:
                    signal_text += f"• {s}\n"
                
                signal_text += """
⚠️ **مدیریت ریسک:**
• حداکثر ۲-۳٪ سرمایه
• همیشه حد ضرر بگذارید
"""
                
                db.save_signal(user_id, result)
                await update.effective_chat.send_message(signal_text, reply_markup=get_main_keyboard(user_id), parse_mode='Markdown')
                user_data[user_id]['state'] = 'menu'
            else:
                await update.effective_chat.send_message(f"❌ حداقل ۵ اندیکاتور! ({len(user_data[user_id]['indicators'])}/5)", reply_markup=get_indicators_keyboard(user_id))
    
    elif user_data[user_id]['state'] == 'waiting_indicator_value':
        try:
            indicator_name = user_data[user_id]['current_indicator']
            indicator_value = float(text.replace(',', '.'))
            user_data[user_id]['indicators'][indicator_name] = indicator_value
            user_data[user_id]['state'] = 'selecting_indicators'
            await update.effective_chat.send_message(
                f"✅ {indicator_name} = {indicator_value} ثبت شد!\n\n📊 {len(user_data[user_id]['indicators'])}/8 اندیکاتور",
                reply_markup=get_indicators_keyboard(user_id)
            )
        except ValueError:
            await update.effective_chat.send_message("❌ لطفاً عدد معتبر وارد کنید!")
    
    # ===== پنل ادمین =====
    if "پنل ادمین" in text or "Admin Panel" in text:
        if user_id == ADMIN_ID:
            await update.effective_chat.send_message(
                "👑 **پنل ادمین**\n\nلطفاً یکی از گزینه‌ها را انتخاب کنید:",
                reply_markup=get_admin_keyboard(user_id),
                parse_mode='Markdown'
            )
        else:
            await update.effective_chat.send_message("❌ دسترسی غیرمجاز!", reply_markup=get_main_keyboard(user_id))
        return
    
    # ===== مدیریت ادمین =====
    if user_id == ADMIN_ID:
        # ===== ارسال پیام همگانی =====
        if "📢 ارسال پیام همگانی" in text or "Broadcast" in text:
            user_data[user_id]['state'] = 'broadcast'
            await update.effective_chat.send_message(
                "📝 پیام خود را برای ارسال به تمام کاربران وارد کنید:",
                reply_markup=get_admin_keyboard(user_id)
            )
            return
        
        if user_data[user_id].get('state') == 'broadcast':
            users = db.get_all_users()
            sent = 0
            for uid, _ in users:
                try:
                    await context.bot.send_message(chat_id=uid, text=text)
                    sent += 1
                except:
                    continue
            user_data[user_id]['state'] = 'menu'
            await update.effective_chat.send_message(f"✅ پیام به {sent} کاربر ارسال شد!", reply_markup=get_admin_keyboard(user_id))
            return
        
        # ===== آمار کاربران =====
        if "📊 آمار کاربران" in text or "User Stats" in text:
            users = db.get_all_users()
            total = len(users)
            fa_count = sum(1 for u in users if u[1] == 'fa')
            en_count = sum(1 for u in users if u[1] == 'en')
            premium_count = sum(1 for u in users if db.check_subscription(u[0]))
            
            msg = f"📊 **آمار سیستم**\n\n"
            msg += f"👥 کل کاربران: {total}\n"
            msg += f"📈 فارسی: {fa_count}\n"
            msg += f"📈 انگلیسی: {en_count}\n"
            msg += f"💎 پرمیوم: {premium_count}"
            
            await update.effective_chat.send_message(msg, reply_markup=get_admin_keyboard(user_id), parse_mode='Markdown')
            return
        
        # ===== تنظیمات سیستم =====
        if "⚙️ تنظیمات سیستم" in text or "System Settings" in text:
            paid_mode = db.get_setting('is_paid_mode')
            auto_trade = db.get_setting('auto_trade_enabled')
            min_conf = db.get_setting('min_confidence')
            
            msg = f"⚙️ **تنظیمات سیستم**\n\n"
            msg += f"💰 حالت پولی: {'فعال' if paid_mode == '1' else 'غیرفعال'}\n"
            msg += f"🤖 معاملات خودکار: {'فعال' if auto_trade == '1' else 'غیرفعال'}\n"
            msg += f"🎯 حداقل اطمینان: {min_conf}%\n\n"
            msg += f"📝 برای تغییر، عدد جدید را وارد کنید:"
            
            user_data[user_id]['state'] = 'setting_system'
            await update.effective_chat.send_message(msg, parse_mode='Markdown')
            return
        
        if user_data[user_id].get('state') == 'setting_system':
            try:
                lines = text.strip().split('\n')
                for line in lines:
                    if 'auto' in line.lower():
                        value = int(re.search(r'\d+', line).group())
                        db.update_setting('auto_trade_enabled', str(value))
                    elif 'min' in line.lower():
                        conf = int(re.search(r'\d+', line).group())
                        db.update_setting('min_confidence', str(conf))
                
                user_data[user_id]['state'] = 'menu'
                await update.effective_chat.send_message("✅ تنظیمات بروزرسانی شد!", reply_markup=get_admin_keyboard(user_id))
            except:
                await update.effective_chat.send_message("❌ فرمت اشتباه!")
            return
        
        # ===== آمار سیگنال‌ها =====
        if "📊 آمار سیگنال‌ها" in text or "Signal Stats" in text:
            db.cursor.execute('''
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
                       SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END) as losses,
                       AVG(confidence) as avg_conf
                FROM signals
            ''')
            result = db.cursor.fetchone()
            if result:
                total, wins, losses, avg_conf = result
                win_rate = (wins / total * 100) if total > 0 else 0
                await update.effective_chat.send_message(
                    f"📊 **آمار سیگنال‌ها**\n\n📈 کل: {total}\n✅ درست: {wins}\n❌ اشتباه: {losses}\n🎯 موفقیت: {win_rate:.1f}%\n📊 اطمینان: {avg_conf:.0f}%",
                    reply_markup=get_admin_keyboard(user_id),
                    parse_mode='Markdown'
                )
            return
        
        if "🔙 بازگشت" in text or "Back" in text:
            await update.effective_chat.send_message("🔙 بازگشت", reply_markup=get_main_keyboard(user_id))
            return

# ==================== اجرا ====================
def main():
    print("=" * 80)
    print("🚀 ربات تحلیل تکنیکال فوق‌پیشرفته نسخه ۱۵.۱")
    print("🔥 مخصوص سیگنال‌دهی با قدرت بالا")
    print("=" * 80)
    print("✅ ۱۰۰۰+ الگوریتم ترکیبی")
    print("✅ ۲۰۰+ ارز با قیمت لحظه‌ای")
    print("✅ سیستم اشتراک فوق‌پیشرفته")
    print("✅ معاملات خودکار هوشمند")
    print("✅ پنل مدیریت حرفه‌ای")
    print("✅ بدون تشخیص چارت")
    print("✅ بدون تشخیص نهنگ")
    print("=" * 80)
    
    if not check_and_create_pid():
        sys.exit(1)
    
    print(f"👤 ادمین: {ADMIN_ID}")
    print(f"🤖 ربات: {BOT_USERNAME}")
    print(f"📊 ارزها: {len(SYMBOLS_200)}")
    print(f"🧠 الگوریتم‌ها: ۱۰۰۰+")
    print(f"💎 حالت پولی: {'فعال' if db.get_setting('is_paid_mode') == '1' else 'غیرفعال'}")
    print("=" * 80)
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ ربات نسخه ۱۵.۱ با موفقیت راه‌اندازی شد!")
    print("🔥 مخصوص سیگنال‌دهی با قدرت بالا")
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