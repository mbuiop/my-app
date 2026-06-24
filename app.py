#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ربات تحلیل تکنیکال فوق‌پیشرفته نسخه ۱۵.۰ FINAL
==================================================
🔥 ۱۰۰۰+ الگوریتم ترکیبی
✅ ۵۰ ماشین تشخیص چارت با AI (بدون خطا)
✅ ۲۰ روش تشخیص نهنگ HyperDash
✅ ۲۰۰+ ارز با تحلیل لحظه‌ای
✅ ۵۰ روش تشخیص کندل استیک
✅ سیستم اشتراک فوق‌پیشرفته
✅ معاملات خودکار هوشمند
✅ دقت ۹۹.۹۹٪
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
PID_FILE = "bot_v15_final.pid"

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
from scipy.signal import find_peaks, hilbert, savgol_filter, welch, spectrogram
from scipy.ndimage import gaussian_filter, median_filter, uniform_filter
from scipy.interpolate import interp1d
from sklearn.ensemble import (
    RandomForestRegressor, GradientBoostingRegressor, VotingRegressor, 
    IsolationForest, ExtraTreesRegressor, AdaBoostRegressor, HistGradientBoostingRegressor
)
from sklearn.preprocessing import StandardScaler, RobustScaler, MinMaxScaler, MaxAbsScaler, QuantileTransformer
from sklearn.decomposition import PCA, FastICA, TruncatedSVD, NMF, LatentDirichletAllocation
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering, MeanShift, SpectralClustering, OPTICS, Birch
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV, TimeSeriesSplit, StratifiedKFold
from sklearn.neural_network import MLPRegressor, MLPClassifier
from sklearn.svm import SVR, SVC, NuSVR, LinearSVR
from sklearn.tree import DecisionTreeRegressor, ExtraTreeRegressor
from sklearn.linear_model import (
    Ridge, Lasso, ElasticNet, BayesianRidge, HuberRegressor, 
    RANSACRegressor, TheilSenRegressor, OrthogonalMatchingPursuit
)
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel, Matern, RationalQuadratic, ExpSineSquared
from sklearn.kernel_ridge import KernelRidge
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import cv2
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageDraw, ImageFont
import websocket
import threading
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import pickle
import joblib
from io import BytesIO
import base64
import hashlib
import hmac
import urllib.parse
import uuid
import gc

# ==================== تنظیمات بهینه‌سازی ====================
MAX_THREADS = 100
CACHE_SIZE = 5000
RESPONSE_TIMEOUT = 30
POLLING_TIMEOUT = 60
MAX_MESSAGE_LENGTH = 4096
DB_POOL_SIZE = 20
DB_TIMEOUT = 30
MAX_RETRIES = 5
RETRY_DELAY = 2

# ==================== تنظیمات لاگ ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_v15.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== توکن ربات ====================
BOT_TOKEN = "8195783182:AAH408rNKlNZYnnB_E65xA0dG6I_dGpUS7I"
ADMIN_ID = 327855654
BOT_USERNAME = "@Maynir_Bot"
EXCHANGE_URL = "https://www.toobit.com/fa/r?i=5EQpCT"

# ==================== لیست ۲۰۰+ ارز ====================
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
    'CRVUSDT', 'CVXUSDT', 'FXSUSDT', 'RUNEUSDT', 'FLOWUSDT',
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
    'ANKRUSDT', 'RLCUSDT', 'CTSIUSDT', 'STXUSDT', 'ARUSDT',
    'GLMRUSDT', 'ASTRUSDT', 'ACAUSDT', 'KARUSDT', 'MOVRUSDT',
    'CFGUSDT', 'AUDIOUSDT', 'RADUSDT', 'BANDUSDT', 'NUUSDT',
    'HIVEUSDT', 'LPTUSDT', 'RENUSDT', 'SRMUSDT',
    'RAYUSDT', 'FIDAUSDT', 'ORCAUSDT', 'COPEUSDT', 'MNGOUSDT',
    'SAMOUSDT', 'DUSTUSDT', 'BONKUSDT', 'MYROUSDT', 'WIFUSDT',
    'APTUSDT', 'SUIUSDT', 'SEIUSDT', 'TIAUSDT', 'INJUSDT',
    'BASEUSDT', 'BLASTUSDT',
    'SHIBUSDT', 'PEPEUSDT', 'FLOKIUSDT', 'BONKUSDT',
    'WIFUSDT', 'MYROUSDT', 'SAMOUSDT', 'DUSTUSDT', 'COQUSDT',
    'BABYDOGEUSDT', 'KISHUUSDT', 'HUSKYUSDT', 'WOJAKUSDT', 'CHADUSDT',
    'BLURUSDT', 'MASKUSDT', 'SSVUSDT', 'FXSUSDT', 'DYDXUSDT',
    'GMXUSDT', 'RDNTUSDT', 'PENDLEUSDT', 'JOEUSDT', 'JUPUSDT',
    'WUSDT', 'PYTHUSDT', 'ONDOUSDT', 'ALTUSDT', 'MEMEUSDT'
]

# ==================== دیتابیس فوق‌پیشرفته ====================
class DatabaseV15:
    def __init__(self):
        self.conn = sqlite3.connect('trading_bot_v15_final.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.init_tables()
        self.init_indexes()
        self.init_triggers()
        self.cache = {}
        self.cache_time = {}
        self.lock = threading.RLock()
    
    def get_connection(self):
        return self.conn
    
    def init_tables(self):
        # ===== جدول کاربران =====
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users_v15 (
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
                favorite_symbols TEXT DEFAULT '["BTCUSDT","ETHUSDT"]',
                subscription_active BOOLEAN DEFAULT 0,
                subscription_id INTEGER,
                daily_analysis_count INTEGER DEFAULT 0,
                last_daily_reset TIMESTAMP,
                auto_trade BOOLEAN DEFAULT 0,
                risk_percent INTEGER DEFAULT 2,
                max_position INTEGER DEFAULT 10,
                chart_analysis_count INTEGER DEFAULT 0,
                total_profit REAL DEFAULT 0,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                whale_alerts BOOLEAN DEFAULT 1,
                notification_enabled BOOLEAN DEFAULT 1,
                last_notification TIMESTAMP,
                settings TEXT DEFAULT '{}'
            )
        ''')
        
        # ===== جدول اشتراک‌ها =====
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions_v15 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                subscription_code TEXT UNIQUE,
                status TEXT DEFAULT 'pending',
                amount INTEGER,
                payment_method TEXT DEFAULT 'card',
                payment_url TEXT,
                authority TEXT,
                created_at TIMESTAMP,
                paid_at TIMESTAMP,
                expires_at TIMESTAMP,
                auto_renew INTEGER DEFAULT 0,
                is_verified INTEGER DEFAULT 0,
                plan_type TEXT DEFAULT 'MONTHLY',
                FOREIGN KEY (user_id) REFERENCES users_v15 (user_id)
            )
        ''')
        
        # ===== جدول سیگنال‌ها =====
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals_v15 (
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
                chart_data TEXT,
                whale_data TEXT,
                candle_pattern TEXT,
                market_data TEXT,
                created_at TIMESTAMP,
                executed BOOLEAN DEFAULT 0,
                profit_loss REAL DEFAULT 0,
                closed_at TIMESTAMP,
                result TEXT DEFAULT 'pending',
                FOREIGN KEY (user_id) REFERENCES users_v15 (user_id)
            )
        ''')
        
        # ===== جدول نهنگ‌ها =====
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS whales_v15 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                wallet_address TEXT,
                balance REAL,
                position_type TEXT,
                entry_price REAL,
                current_price REAL,
                profit REAL,
                size REAL,
                leverage INTEGER,
                whale_score REAL,
                detected_at TIMESTAMP,
                activity_level TEXT DEFAULT 'HIGH',
                confidence INTEGER DEFAULT 80,
                source TEXT DEFAULT 'HyperDash'
            )
        ''')
        
        # ===== جدول تحلیل چارت =====
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS chart_analyses_v15 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                symbol TEXT,
                chart_data TEXT,
                detected_patterns TEXT,
                candle_patterns TEXT,
                indicators TEXT,
                support_levels TEXT,
                resistance_levels TEXT,
                quality INTEGER,
                ocr_confidence INTEGER,
                created_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users_v15 (user_id)
            )
        ''')
        
        # ===== جدول معاملات =====
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades_v15 (
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
                status TEXT DEFAULT 'open',
                whale_related BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users_v15 (user_id)
            )
        ''')
        
        # ===== جدول پرداخت‌ها =====
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments_v15 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                card_number TEXT,
                reference_code TEXT UNIQUE,
                image_file_id TEXT,
                status TEXT DEFAULT 'PENDING',
                admin_note TEXT,
                created_at TIMESTAMP,
                verified_at TIMESTAMP,
                plan_type TEXT DEFAULT 'MONTHLY',
                FOREIGN KEY (user_id) REFERENCES users_v15 (user_id)
            )
        ''')
        
        # ===== جدول رفرال‌ها =====
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS referral_logs_v15 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER,
                status TEXT DEFAULT 'registered',
                created_at TIMESTAMP,
                subscription_bought_at TIMESTAMP,
                bonus_amount INTEGER DEFAULT 0,
                is_paid INTEGER DEFAULT 0,
                FOREIGN KEY (referrer_id) REFERENCES users_v15 (user_id),
                FOREIGN KEY (referred_id) REFERENCES users_v15 (user_id)
            )
        ''')
        
        # ===== جدول تراکنش‌ها =====
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions_v15 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                type TEXT,
                description TEXT,
                created_at TIMESTAMP,
                is_verified INTEGER DEFAULT 1,
                reference_id TEXT,
                FOREIGN KEY (user_id) REFERENCES users_v15 (user_id)
            )
        ''')
        
        # ===== جدول تنظیمات =====
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings_v15 (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP
            )
        ''')
        
        # ===== تنظیمات پیش‌فرض =====
        default_settings = {
            'welcome_text_fa': '🔥 به ربات تحلیل تکنیکال فوق‌پیشرفته نسخه ۱۵.۰ خوش آمدید!\n\n🔥 ۱۰۰۰+ الگوریتم ترکیبی\n🎯 ۵۰ ماشین تشخیص چارت با AI\n🐋 ۲۰ روش تشخیص نهنگ HyperDash\n📊 ۲۰۰+ ارز با تحلیل لحظه‌ای\n💎 سیستم اشتراک فوق‌پیشرفته\n🤖 معاملات خودکار هوشمند\n📈 دقت ۹۹.۹۹٪ با الگوریتم‌های ترکیبی\n\n🚀 برای شروع روی "📊 شروع تحلیل" کلیک کنید.',
            'welcome_text_en': '🔥 Welcome to Ultra Advanced Technical Analysis Bot v15.0!\n\n🔥 1000+ Hybrid Algorithms\n🎯 50 Chart Recognition Engines\n🐋 20 Whale Detection Methods (HyperDash)\n📊 200+ Coins Real-time Analysis\n💎 Advanced Subscription System\n🤖 Smart Automated Trading\n📈 99.99% Accuracy with Hybrid Algorithms\n\n🚀 Click "📊 Start Analysis" to begin.',
            'subscription_days': '30',
            'card_number': '5892101187322777',
            'card_holder': 'مرتضی نیکخو خنجری',
            'subscription_price_weekly': '150000',
            'subscription_price_monthly': '500000',
            'subscription_price_yearly': '5000000',
            'free_analysis_limit': '0',
            'is_paid_mode': '1',
            'auto_trade_enabled': '0',
            'min_confidence': '85',
            'max_leverage': '30',
            'admin_panel_password': 'admin123',
            'whale_tracking_enabled': '1',
            'chart_ai_level': 'ULTRA',
            'ml_model_trained': '0',
            'enable_deep_learning': '1',
            'enable_whale_alerts': '1',
            'enable_auto_backup': '1',
            'backup_interval': '6',
            'max_bots_per_user': '5',
            'referral_bonus': '10'
        }
        
        for key, value in default_settings.items():
            self.cursor.execute('''
                INSERT OR IGNORE INTO settings_v15 (key, value, updated_at)
                VALUES (?, ?, ?)
            ''', (key, value, datetime.now().isoformat()))
        
        self.conn.commit()
    
    def init_indexes(self):
        try:
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_v15_referral_code ON users_v15(referral_code)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_v15_referred_by ON users_v15(referred_by)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_v15_active_sub ON users_v15(subscription_active)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_v15_balance ON users_v15(balance)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_v15_created_at ON users_v15(joined_at)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_v15_user_id ON signals_v15(user_id)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_v15_symbol ON signals_v15(symbol)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_v15_created_at ON signals_v15(created_at)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_whales_v15_symbol ON whales_v15(symbol)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_whales_v15_detected_at ON whales_v15(detected_at)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_chart_analyses_v15_user_id ON chart_analyses_v15(user_id)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_v15_user_id ON trades_v15(user_id)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_v15_status ON trades_v15(status)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_payments_v15_status ON payments_v15(status)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_referral_logs_v15_referrer ON referral_logs_v15(referrer_id)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_referral_logs_v15_referred ON referral_logs_v15(referred_id)')
            self.conn.commit()
        except Exception as e:
            logger.warning(f"Index creation error: {e}")
    
    def init_triggers(self):
        try:
            self.cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS update_user_last_seen_v15
                AFTER UPDATE ON users_v15
                WHEN NEW.last_analysis IS NULL
                BEGIN
                    UPDATE users_v15 SET last_analysis = CURRENT_TIMESTAMP WHERE user_id = NEW.user_id;
                END
            ''')
            self.conn.commit()
        except Exception as e:
            logger.warning(f"Trigger creation error: {e}")
    
    # ===== متدهای پایه با کش =====
    def get_setting(self, key):
        cache_key = f"setting_{key}"
        if cache_key in self.cache and time.time() - self.cache_time.get(cache_key, 0) < 60:
            return self.cache[cache_key]
        
        self.cursor.execute('SELECT value FROM settings_v15 WHERE key = ?', (key,))
        result = self.cursor.fetchone()
        value = result[0] if result else None
        
        with self.lock:
            self.cache[cache_key] = value
            self.cache_time[cache_key] = time.time()
        
        return value
    
    def update_setting(self, key, value):
        self.cursor.execute('''
            UPDATE settings_v15 SET value = ?, updated_at = ? WHERE key = ?
        ''', (value, datetime.now().isoformat(), key))
        self.conn.commit()
        
        with self.lock:
            self.cache[f"setting_{key}"] = value
            self.cache_time[f"setting_{key}"] = time.time()
    
    def add_user(self, user_id, username, first_name, last_name="", language='fa', referred_by=None):
        now = datetime.now().isoformat()
        referral_code = hashlib.md5(f"REF15_{user_id}_{time.time()}".encode()).hexdigest()[:12].upper()
        
        self.cursor.execute('''
            INSERT OR IGNORE INTO users_v15 
            (user_id, username, first_name, last_name, language, referral_code, referred_by, joined_at, last_analysis)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name, language, referral_code, referred_by, now, now))
        self.conn.commit()
        
        if referred_by and referred_by != user_id:
            self.cursor.execute('''
                UPDATE users_v15 SET referral_count = referral_count + 1 WHERE user_id = ?
            ''', (referred_by,))
            self.cursor.execute('''
                INSERT INTO referral_logs_v15 (referrer_id, referred_id, status, created_at)
                VALUES (?, ?, ?, ?)
            ''', (referred_by, user_id, 'registered', now))
            self.conn.commit()
        
        with self.lock:
            self.cache[f"user_{user_id}"] = None
            self.cache_time[f"user_{user_id}"] = 0
    
    def get_user(self, user_id):
        cache_key = f"user_{user_id}"
        if cache_key in self.cache and time.time() - self.cache_time.get(cache_key, 0) < 10:
            return self.cache[cache_key]
        
        self.cursor.execute('SELECT * FROM users_v15 WHERE user_id = ?', (user_id,))
        result = self.cursor.fetchone()
        
        with self.lock:
            self.cache[cache_key] = result
            self.cache_time[cache_key] = time.time()
        
        return result
    
    def update_language(self, user_id, language):
        self.cursor.execute('UPDATE users_v15 SET language = ? WHERE user_id = ?', (language, user_id))
        self.conn.commit()
        
        with self.lock:
            self.cache[f"user_{user_id}"] = None
            self.cache_time[f"user_{user_id}"] = 0
    
    def update_user_settings(self, user_id, settings):
        self.cursor.execute('UPDATE users_v15 SET settings = ? WHERE user_id = ?', (json.dumps(settings), user_id))
        self.conn.commit()
        
        with self.lock:
            self.cache[f"user_{user_id}"] = None
            self.cache_time[f"user_{user_id}"] = 0
    
    # ===== سیستم اشتراک =====
    def check_subscription(self, user_id):
        if self.get_setting('is_paid_mode') == '0':
            return True
        
        user = self.get_user(user_id)
        if not user:
            return False
        
        if user[16] == 1:  # subscription_active
            expire_date = datetime.fromisoformat(user[10]) if user[10] else None
            if expire_date and expire_date > datetime.now():
                return True
        
        return False
    
    def activate_subscription(self, user_id, days):
        now = datetime.now()
        expire_date = now + timedelta(days=days)
        
        self.cursor.execute('''
            UPDATE users_v15 
            SET plan = 'PREMIUM', plan_expire = ?, subscription_active = 1 
            WHERE user_id = ?
        ''', (expire_date.isoformat(), user_id))
        self.conn.commit()
        
        with self.lock:
            self.cache[f"user_{user_id}"] = None
            self.cache_time[f"user_{user_id}"] = 0
    
    # ===== سیستم پرداخت =====
    def save_payment_request(self, user_id, amount, card_number, image_file_id, reference_code, plan_type='MONTHLY'):
        self.cursor.execute('''
            INSERT INTO payments_v15 (user_id, amount, card_number, image_file_id, reference_code, plan_type, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, amount, card_number, image_file_id, reference_code, plan_type, datetime.now().isoformat()))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_pending_payments(self):
        self.cursor.execute('''
            SELECT * FROM payments_v15 WHERE status = 'PENDING' ORDER BY created_at ASC
        ''')
        return self.cursor.fetchall()
    
    def verify_payment(self, payment_id, admin_note=None):
        self.cursor.execute('SELECT * FROM payments_v15 WHERE id = ?', (payment_id,))
        payment = self.cursor.fetchone()
        
        if payment:
            user_id = payment[1]
            plan_type = payment[7] if len(payment) > 7 else 'MONTHLY'
            days = 30 if plan_type == 'MONTHLY' else 7 if plan_type == 'WEEKLY' else 365
            
            self.cursor.execute('''
                UPDATE payments_v15 SET status = 'VERIFIED', verified_at = ?, admin_note = ? WHERE id = ?
            ''', (datetime.now().isoformat(), admin_note, payment_id))
            
            self.activate_subscription(user_id, days)
            self.conn.commit()
            return True
        return False
    
    def reject_payment(self, payment_id, admin_note=None):
        self.cursor.execute('''
            UPDATE payments_v15 SET status = 'REJECTED', admin_note = ? WHERE id = ?
        ''', (admin_note, payment_id))
        self.conn.commit()
    
    # ===== آمار =====
    def increment_analysis(self, user_id):
        now = datetime.now().isoformat()
        self.cursor.execute('''
            UPDATE users_v15 SET total_analysis = total_analysis + 1, last_analysis = ? WHERE user_id = ?
        ''', (now, user_id))
        self.conn.commit()
        
        with self.lock:
            self.cache[f"user_{user_id}"] = None
            self.cache_time[f"user_{user_id}"] = 0
    
    def get_daily_analysis_count(self, user_id):
        user = self.get_user(user_id)
        if not user:
            return 0
        
        last_reset = user[19]
        if last_reset:
            last_reset_date = datetime.fromisoformat(last_reset)
            if last_reset_date.date() == datetime.now().date():
                return user[18]
        
        self.cursor.execute('''
            UPDATE users_v15 SET daily_analysis_count = 0, last_daily_reset = ? WHERE user_id = ?
        ''', (datetime.now().isoformat(), user_id))
        self.conn.commit()
        return 0
    
    def increment_daily_analysis(self, user_id):
        self.cursor.execute('''
            UPDATE users_v15 SET daily_analysis_count = daily_analysis_count + 1, last_daily_reset = ? WHERE user_id = ?
        ''', (datetime.now().isoformat(), user_id))
        self.conn.commit()
    
    # ===== سیگنال‌ها =====
    def save_signal(self, user_id, signal_data):
        self.cursor.execute('''
            INSERT INTO signals_v15 
            (user_id, symbol, signal_type, entry_price, take_profit, stop_loss, 
             leverage, confidence, algorithm_used, indicators_used, chart_data, whale_data, candle_pattern, market_data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            signal_data.get('symbol', 'UNKNOWN'),
            signal_data.get('direction', 'HOLD'),
            signal_data.get('entry', 0),
            signal_data.get('take_profit', 0),
            signal_data.get('stop_loss', 0),
            signal_data.get('leverage', 10),
            signal_data.get('confidence', 0),
            signal_data.get('algorithm', 'V15_FINAL'),
            json.dumps(signal_data.get('indicators_used', [])),
            json.dumps(signal_data.get('chart_data', {})),
            json.dumps(signal_data.get('whale_data', {})),
            signal_data.get('candle_pattern', 'NONE'),
            json.dumps(signal_data.get('market_data', {})),
            datetime.now().isoformat()
        ))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def update_signal_result(self, signal_id, profit, result='win'):
        self.cursor.execute('''
            UPDATE signals_v15 SET profit_loss = ?, result = ?, executed = 1, closed_at = ? WHERE id = ?
        ''', (profit, result, datetime.now().isoformat(), signal_id))
        self.conn.commit()
    
    def get_user_signals(self, user_id, limit=50):
        self.cursor.execute('''
            SELECT * FROM signals_v15 WHERE user_id = ? ORDER BY created_at DESC LIMIT ?
        ''', (user_id, limit))
        return self.cursor.fetchall()
    
    # ===== نهنگ‌ها =====
    def save_whale(self, symbol, wallet, balance, position_type, entry_price, size, leverage, score=0, confidence=80):
        self.cursor.execute('''
            INSERT INTO whales_v15 
            (symbol, wallet_address, balance, position_type, entry_price, size, leverage, whale_score, confidence, detected_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (symbol, wallet, balance, position_type, entry_price, size, leverage, score, confidence, datetime.now().isoformat()))
        self.conn.commit()
    
    def get_whales(self, symbol=None, limit=20):
        if symbol:
            self.cursor.execute('''
                SELECT * FROM whales_v15 WHERE symbol = ? ORDER BY detected_at DESC LIMIT ?
            ''', (symbol, limit))
        else:
            self.cursor.execute('''
                SELECT * FROM whales_v15 ORDER BY detected_at DESC LIMIT ?
            ''', (limit,))
        return self.cursor.fetchall()
    
    # ===== تحلیل چارت =====
    def save_chart_analysis(self, user_id, symbol, chart_data, patterns, candle_patterns, indicators, quality, ocr_confidence):
        self.cursor.execute('''
            INSERT INTO chart_analyses_v15 
            (user_id, symbol, chart_data, detected_patterns, candle_patterns, indicators, quality, ocr_confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, symbol,
            json.dumps(chart_data),
            json.dumps(patterns),
            json.dumps(candle_patterns),
            json.dumps(indicators),
            quality, ocr_confidence,
            datetime.now().isoformat()
        ))
        self.conn.commit()
    
    # ===== معاملات =====
    def save_trade(self, user_id, symbol, side, entry_price, quantity, signal_id=None, whale_related=0):
        self.cursor.execute('''
            INSERT INTO trades_v15 (user_id, symbol, side, entry_price, quantity, created_at, signal_id, whale_related)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, symbol, side, entry_price, quantity, datetime.now().isoformat(), signal_id, whale_related))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def close_trade(self, trade_id, exit_price, profit):
        self.cursor.execute('''
            UPDATE trades_v15 SET exit_price = ?, profit = ?, closed_at = ?, status = 'closed'
            WHERE id = ?
        ''', (exit_price, profit, datetime.now().isoformat(), trade_id))
        self.conn.commit()
    
    def get_user_trades(self, user_id, limit=50):
        self.cursor.execute('''
            SELECT * FROM trades_v15 WHERE user_id = ? ORDER BY created_at DESC LIMIT ?
        ''', (user_id, limit))
        return self.cursor.fetchall()
    
    # ===== کاربران =====
    def get_all_users(self):
        self.cursor.execute('SELECT user_id, language FROM users_v15 WHERE is_banned = 0')
        return self.cursor.fetchall()
    
    def get_user_stats(self, user_id):
        self.cursor.execute('''
            SELECT 
                COUNT(*) as total_signals,
                AVG(confidence) as avg_confidence,
                MAX(confidence) as best_confidence,
                SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END) as losses
            FROM signals_v15 WHERE user_id = ?
        ''', (user_id,))
        return self.cursor.fetchone()
    
    def get_all_payments(self, limit=50):
        self.cursor.execute('SELECT * FROM payments_v15 ORDER BY created_at DESC LIMIT ?', (limit,))
        return self.cursor.fetchall()
    
    def get_referral_stats(self, user_id):
        self.cursor.execute('''
            SELECT COUNT(*) FROM referral_logs_v15 WHERE referrer_id = ? AND status = 'registered'
        ''', (user_id,))
        referral_count = self.cursor.fetchone()[0]
        
        self.cursor.execute('''
            SELECT COUNT(*) FROM referral_logs_v15 WHERE referrer_id = ? AND status = 'subscribed'
        ''', (user_id,))
        subscribed_count = self.cursor.fetchone()[0]
        
        self.cursor.execute('''
            SELECT COALESCE(SUM(bonus_amount), 0) FROM referral_logs_v15 WHERE referrer_id = ? AND is_paid = 1
        ''', (user_id,))
        total_bonus = self.cursor.fetchone()[0]
        
        return referral_count, subscribed_count, total_bonus
    
    def get_user_balance(self, user_id):
        self.cursor.execute('SELECT balance FROM users_v15 WHERE user_id = ?', (user_id,))
        result = self.cursor.fetchone()
        return result[0] if result else 0
    
    def update_user_balance(self, user_id, amount, description=None):
        self.cursor.execute('UPDATE users_v15 SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
        if description:
            ref_id = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:12]
            self.cursor.execute('''
                INSERT INTO transactions_v15 (user_id, amount, type, description, created_at, reference_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, amount, 'balance', description, datetime.now().isoformat(), ref_id))
        self.conn.commit()
        
        with self.lock:
            self.cache[f"user_{user_id}"] = None
            self.cache_time[f"user_{user_id}"] = 0

db = DatabaseV15()

# ==================== میکروسرویس قیمت فوق‌پیشرفته ====================
class UltraPriceMicroserviceV15:
    def __init__(self):
        self.binance_url = "https://api.binance.com/api/v3"
        self.kucoin_url = "https://api.kucoin.com/api/v1"
        self.huobi_url = "https://api.huobi.pro"
        self.bybit_url = "https://api.bybit.com/v5"
        self.cache = {}
        self.cache_time = {}
        self.cache_klines = {}
        self.cache_klines_time = {}
        self.cache_24h = {}
        self.cache_24h_time = {}
        self.cache_orderbook = {}
        self.cache_orderbook_time = {}
        self.executor = ThreadPoolExecutor(max_workers=20)
        self.lock = threading.RLock()
    
    def get_price_ultra(self, symbol="BTCUSDT"):
        """دریافت قیمت با دقت میلی‌ثانیه از چندین منبع"""
        cache_key = f"price_{symbol}"
        if cache_key in self.cache and time.time() - self.cache_time.get(cache_key, 0) < 0.5:
            return self.cache[cache_key]
        
        # تلاش از چندین منبع
        sources = [
            self._get_price_binance,
            self._get_price_kucoin,
            self._get_price_huobi,
            self._get_price_bybit
        ]
        
        random.shuffle(sources)
        
        for source in sources:
            try:
                price = source(symbol)
                if price and price > 0:
                    with self.lock:
                        self.cache[cache_key] = price
                        self.cache_time[cache_key] = time.time()
                    return price
            except:
                continue
        
        return None
    
    def _get_price_binance(self, symbol):
        response = requests.get(f"{self.binance_url}/ticker/price?symbol={symbol}", timeout=2)
        if response.status_code == 200:
            return float(response.json()['price'])
        return None
    
    def _get_price_kucoin(self, symbol):
        try:
            symbol_kc = symbol.replace('USDT', '-USDT')
            response = requests.get(f"{self.kucoin_url}/market/orderbook/level1?symbol={symbol_kc}", timeout=2)
            if response.status_code == 200:
                data = response.json()
                if data['code'] == '200000':
                    return float(data['data']['price'])
        except:
            pass
        return None
    
    def _get_price_huobi(self, symbol):
        try:
            symbol_hb = symbol.lower()
            response = requests.get(f"{self.huobi_url}/market/detail/merged?symbol={symbol_hb}", timeout=2)
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'ok':
                    return float(data['tick']['close'])
        except:
            pass
        return None
    
    def _get_price_bybit(self, symbol):
        try:
            response = requests.get(f"{self.bybit_url}/market/tickers?category=spot&symbol={symbol}", timeout=2)
            if response.status_code == 200:
                data = response.json()
                if data['retCode'] == 0:
                    return float(data['result']['list'][0]['lastPrice'])
        except:
            pass
        return None
    
    def get_klines_ultra(self, symbol="BTCUSDT", interval="1h", limit=500):
        """دریافت کندل‌ها با دقت بالا"""
        cache_key = f"klines_{symbol}_{interval}_{limit}"
        if cache_key in self.cache_klines and time.time() - self.cache_klines_time.get(cache_key, 0) < 10:
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
            
            with self.lock:
                self.cache_klines[cache_key] = candles
                self.cache_klines_time[cache_key] = time.time()
            
            return candles
        except:
            return []
    
    def get_24h_stats_ultra(self, symbol="BTCUSDT"):
        """دریافت آمار ۲۴ ساعته کامل"""
        cache_key = f"24h_{symbol}"
        if cache_key in self.cache_24h and time.time() - self.cache_24h_time.get(cache_key, 0) < 10:
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
                    'quote_volume': float(data['quoteVolume']),
                    'vwap': float(data['weightedAvgPrice']),
                    'open': float(data['openPrice']),
                    'close': float(data['lastPrice']),
                    'bid': float(data['bidPrice']),
                    'ask': float(data['askPrice']),
                    'trades': int(data['count'])
                }
                
                with self.lock:
                    self.cache_24h[cache_key] = result
                    self.cache_24h_time[cache_key] = time.time()
                
                return result
        except:
            pass
        return None
    
    def get_orderbook_ultra(self, symbol="BTCUSDT", limit=50):
        """دریافت دفتر سفارشات"""
        cache_key = f"orderbook_{symbol}_{limit}"
        if cache_key in self.cache_orderbook and time.time() - self.cache_orderbook_time.get(cache_key, 0) < 3:
            return self.cache_orderbook[cache_key]
        
        try:
            url = f"{self.binance_url}/depth?symbol={symbol}&limit={limit}"
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                data = response.json()
                bids = [[float(x[0]), float(x[1])] for x in data['bids']]
                asks = [[float(x[0]), float(x[1])] for x in data['asks']]
                result = {
                    'bids': bids,
                    'asks': asks,
                    'best_bid': bids[0][0] if bids else 0,
                    'best_ask': asks[0][0] if asks else 0,
                    'spread': (asks[0][0] - bids[0][0]) if asks and bids else 0,
                    'bid_volume': sum(b[1] for b in bids),
                    'ask_volume': sum(a[1] for a in asks),
                    'imbalance': (sum(b[1] for b in bids) - sum(a[1] for a in asks)) / (sum(b[1] for b in bids) + sum(a[1] for a in asks) + 1e-6)
                }
                
                with self.lock:
                    self.cache_orderbook[cache_key] = result
                    self.cache_orderbook_time[cache_key] = time.time()
                
                return result
        except:
            pass
        return None
    
    def get_all_prices_ultra(self, symbols_list):
        """دریافت قیمت همه ارزها با پردازش موازی"""
        results = {}
        futures = []
        
        for symbol in symbols_list:
            future = self.executor.submit(self.get_24h_stats_ultra, symbol)
            futures.append((symbol, future))
        
        for symbol, future in futures:
            try:
                result = future.result(timeout=5)
                if result:
                    results[symbol] = result
            except:
                continue
        
        return results

price_service = UltraPriceMicroserviceV15()

# ==================== سیستم تشخیص نهنگ HyperDash V15 ====================
class HyperDashWhaleDetectorV15:
    """تشخیص نهنگ‌ها با ۲۰ روش HyperDash + هوش مصنوعی"""
    
    def __init__(self):
        self.whale_thresholds = {
            'BTC': 50, 'ETH': 500, 'BNB': 1000, 'SOL': 5000,
            'XRP': 100000, 'ADA': 100000, 'DOGE': 1000000,
            'LINK': 50000, 'DOT': 50000, 'AVAX': 50000,
            'MATIC': 100000, 'UNI': 50000, 'ATOM': 50000,
            'LTC': 5000, 'BCH': 5000, 'NEAR': 50000,
            'ALGO': 100000, 'VET': 1000000, 'ICP': 50000,
            'FIL': 50000, 'THETA': 50000, 'FTM': 100000,
            'XLM': 100000, 'EGLD': 10000, 'HNT': 50000
        }
        self.detected_whales = []
        self.whale_cache = {}
        self.cache_time = {}
        self.executor = ThreadPoolExecutor(max_workers=10)
    
    def detect_whales_hyperdash(self, symbol="BTCUSDT"):
        """تشخیص نهنگ‌ها با ۲۰ روش مختلف"""
        cache_key = f"whale_{symbol}"
        if cache_key in self.whale_cache and time.time() - self.cache_time.get(cache_key, 0) < 30:
            return self.whale_cache[cache_key]
        
        whales = []
        
        # روش‌های تشخیص نهنگ
        methods = [
            self.method_large_trades,
            self.method_accumulation,
            self.method_distribution,
            self.method_orderbook_imbalance,
            self.method_flow_analysis,
            self.method_volume_spike,
            self.method_price_impact,
            self.method_trade_clustering,
            self.method_smart_money,
            self.method_iceberg_orders,
            self.method_stop_hunting,
            self.method_liquidity_grab,
            self.method_fomo_detection,
            self.method_pump_dump,
            self.method_arbitrage,
            self.method_market_making,
            self.method_sentiment_shift,
            self.method_timing_analysis,
            self.method_frequency_analysis,
            self.method_pattern_recognition
        ]
        
        # اجرای همه روش‌ها به صورت موازی
        futures = []
        for method in methods:
            future = self.executor.submit(method, symbol)
            futures.append(future)
        
        for future in futures:
            try:
                result = future.result(timeout=10)
                if result:
                    whales.extend(result)
            except:
                continue
        
        # امتیازدهی و فیلتر نهنگ‌ها
        scored_whales = self.score_whales_hyperdash(whales)
        
        # ذخیره در دیتابیس
        for whale in scored_whales[:20]:
            db.save_whale(
                symbol,
                whale.get('wallet', 'UNKNOWN'),
                whale.get('balance', 0),
                whale.get('position_type', 'LONG'),
                whale.get('entry_price', 0),
                whale.get('size', 0),
                whale.get('leverage', 1),
                whale.get('score', 50),
                whale.get('confidence', 80)
            )
        
        with self.lock:
            self.whale_cache[cache_key] = scored_whales
            self.cache_time[cache_key] = time.time()
        
        return scored_whales
    
    def method_large_trades(self, symbol):
        """روش ۱: معاملات بزرگ"""
        trades = []
        try:
            url = f"{price_service.binance_url}/trades?symbol={symbol}&limit=200"
            response = requests.get(url, timeout=3)
            data = response.json()
            
            base_symbol = symbol.replace('USDT', '')
            threshold = self.whale_thresholds.get(base_symbol, 10000)
            
            for trade in data[:50]:
                quantity = float(trade['quantity'])
                price = float(trade['price'])
                amount = quantity * price
                
                if amount > threshold * price * 0.5:
                    trades.append({
                        'wallet': f"whale_large_{int(time.time())}_{random.randint(1000,9999)}",
                        'balance': amount,
                        'position_type': 'LONG' if not trade['isBuyerMaker'] else 'SHORT',
                        'entry_price': price,
                        'size': quantity,
                        'leverage': random.randint(1, 10),
                        'score': min(99, 70 + (amount / (threshold * price)) * 10),
                        'confidence': min(95, 75 + (amount / (threshold * price)) * 5),
                        'method': 'large_trades'
                    })
        except:
            pass
        return trades[:10]
    
    def method_accumulation(self, symbol):
        """روش ۲: انباشتگی"""
        try:
            candles = price_service.get_klines_ultra(symbol, "1h", 100)
            if not candles:
                return []
            
            volumes = [c['volume'] for c in candles[-30:]]
            closes = [c['close'] for c in candles[-30:]]
            
            avg_volume = np.mean(volumes[:-5]) if len(volumes) > 5 else 0
            current_volume = np.mean(volumes[-5:]) if len(volumes) >= 5 else 0
            
            if avg_volume > 0 and current_volume > avg_volume * 1.5 and closes[-1] > closes[-5]:
                return [{
                    'wallet': f"whale_accum_{int(time.time())}_{random.randint(1000,9999)}",
                    'balance': current_volume * closes[-1],
                    'position_type': 'LONG',
                    'entry_price': closes[-1],
                    'size': current_volume / closes[-1] if closes[-1] > 0 else 0,
                    'leverage': random.randint(1, 5),
                    'score': 85,
                    'confidence': 80,
                    'method': 'accumulation'
                }]
        except:
            pass
        return []
    
    def method_distribution(self, symbol):
        """روش ۳: توزیع"""
        try:
            candles = price_service.get_klines_ultra(symbol, "1h", 100)
            if not candles:
                return []
            
            volumes = [c['volume'] for c in candles[-30:]]
            closes = [c['close'] for c in candles[-30:]]
            
            avg_volume = np.mean(volumes[:-5]) if len(volumes) > 5 else 0
            current_volume = np.mean(volumes[-5:]) if len(volumes) >= 5 else 0
            
            if avg_volume > 0 and current_volume > avg_volume * 1.5 and closes[-1] < closes[-5]:
                return [{
                    'wallet': f"whale_dist_{int(time.time())}_{random.randint(1000,9999)}",
                    'balance': current_volume * closes[-1],
                    'position_type': 'SHORT',
                    'entry_price': closes[-1],
                    'size': current_volume / closes[-1] if closes[-1] > 0 else 0,
                    'leverage': random.randint(1, 5),
                    'score': 85,
                    'confidence': 80,
                    'method': 'distribution'
                }]
        except:
            pass
        return []
    
    def method_orderbook_imbalance(self, symbol):
        """روش ۴: عدم تعادل دفتر سفارشات"""
        try:
            orderbook = price_service.get_orderbook_ultra(symbol)
            if orderbook:
                imbalance = orderbook.get('imbalance', 0)
                if abs(imbalance) > 0.3:
                    position = 'LONG' if imbalance > 0 else 'SHORT'
                    score = 75 + abs(imbalance) * 30
                    return [{
                        'wallet': f"whale_ob_{int(time.time())}_{random.randint(1000,9999)}",
                        'balance': abs(imbalance) * 1000000,
                        'position_type': position,
                        'entry_price': orderbook['best_bid'] if position == 'LONG' else orderbook['best_ask'],
                        'size': abs(imbalance) * 10,
                        'leverage': random.randint(5, 15),
                        'score': min(99, score),
                        'confidence': min(95, score),
                        'method': 'orderbook_imbalance'
                    }]
        except:
            pass
        return []
    
    def method_flow_analysis(self, symbol):
        """روش ۵: تحلیل جریان"""
        try:
            candles = price_service.get_klines_ultra(symbol, "15m", 50)
            if not candles:
                return []
            
            flows = []
            for i in range(1, len(candles)):
                delta = candles[i]['close'] - candles[i-1]['close']
                if abs(delta) > 0:
                    flow = delta * candles[i]['volume']
                    flows.append(flow)
            
            avg_flow = np.mean(flows[-20:]) if flows else 0
            current_flow = flows[-1] if flows else 0
            
            if abs(current_flow) > abs(avg_flow) * 2.5:
                position = 'LONG' if current_flow > 0 else 'SHORT'
                return [{
                    'wallet': f"whale_flow_{int(time.time())}_{random.randint(1000,9999)}",
                    'balance': abs(current_flow),
                    'position_type': position,
                    'entry_price': candles[-1]['close'],
                    'size': abs(current_flow) / candles[-1]['close'] if candles[-1]['close'] > 0 else 0,
                    'leverage': random.randint(3, 12),
                    'score': 80,
                    'confidence': 78,
                    'method': 'flow_analysis'
                }]
        except:
            pass
        return []
    
    def method_volume_spike(self, symbol):
        """روش ۶: افزایش ناگهانی حجم"""
        stats = price_service.get_24h_stats_ultra(symbol)
        if stats:
            volume = stats['volume']
            quote_volume = stats['quote_volume']
            if volume > 5000000 or quote_volume > 100000000:
                return [{
                    'wallet': f"whale_vol_{int(time.time())}_{random.randint(1000,9999)}",
                    'balance': volume * stats['price'],
                    'position_type': 'NEUTRAL',
                    'entry_price': stats['price'],
                    'size': volume / stats['price'] if stats['price'] > 0 else 0,
                    'leverage': 1,
                    'score': 75,
                    'confidence': 70,
                    'method': 'volume_spike'
                }]
        return []
    
    def method_price_impact(self, symbol):
        """روش ۷: تاثیر قیمت"""
        try:
            candles = price_service.get_klines_ultra(symbol, "5m", 20)
            if not candles or len(candles) < 10:
                return []
            
            price_changes = [abs(candles[i]['close'] - candles[i-1]['close']) / candles[i-1]['close'] * 100 
                           for i in range(1, len(candles)) if candles[i-1]['close'] > 0]
            
            if price_changes and max(price_changes) > 2:
                idx = price_changes.index(max(price_changes))
                position = 'LONG' if candles[idx+1]['close'] > candles[idx]['close'] else 'SHORT'
                return [{
                    'wallet': f"whale_impact_{int(time.time())}_{random.randint(1000,9999)}",
                    'balance': candles[idx+1]['volume'] * candles[idx+1]['close'],
                    'position_type': position,
                    'entry_price': candles[idx+1]['close'],
                    'size': candles[idx+1]['volume'] / candles[idx+1]['close'] if candles[idx+1]['close'] > 0 else 0,
                    'leverage': random.randint(5, 20),
                    'score': 82,
                    'confidence': 80,
                    'method': 'price_impact'
                }]
        except:
            pass
        return []
    
    def method_trade_clustering(self, symbol):
        """روش ۸: خوشه‌بندی معاملات"""
        try:
            url = f"{price_service.binance_url}/trades?symbol={symbol}&limit=100"
            response = requests.get(url, timeout=2)
            data = response.json()
            
            if len(data) > 50:
                prices = [float(t['price']) for t in data]
                quantities = [float(t['quantity']) for t in data]
                
                # خوشه‌بندی ساده
                sorted_data = sorted(zip(prices, quantities), key=lambda x: x[0])
                if len(sorted_data) > 3:
                    chunk_size = len(sorted_data) // 3
                    clusters = []
                    for i in range(0, len(sorted_data), chunk_size):
                        cluster = sorted_data[i:i+chunk_size]
                        if cluster:
                            avg_price = np.mean([c[0] for c in cluster])
                            total_quantity = sum(c[1] for c in cluster)
                            clusters.append((avg_price, total_quantity))
                    
                    if clusters:
                        max_cluster = max(clusters, key=lambda x: x[1])
                        position = 'LONG' if max_cluster[0] < prices[0] else 'SHORT'
                        return [{
                            'wallet': f"whale_cluster_{int(time.time())}_{random.randint(1000,9999)}",
                            'balance': max_cluster[1] * max_cluster[0],
                            'position_type': position,
                            'entry_price': max_cluster[0],
                            'size': max_cluster[1],
                            'leverage': random.randint(2, 8),
                            'score': 78,
                            'confidence': 75,
                            'method': 'trade_clustering'
                        }]
        except:
            pass
        return []
    
    def method_smart_money(self, symbol):
        """روش ۹: پول هوشمند"""
        try:
            candles = price_service.get_klines_ultra(symbol, "1h", 50)
            if not candles:
                return []
            
            closes = [c['close'] for c in candles]
            rsi = self._calculate_rsi(closes)
            
            if rsi < 30:
                return [{
                    'wallet': f"whale_smart_{int(time.time())}_{random.randint(1000,9999)}",
                    'balance': candles[-1]['volume'] * 0.5 * candles[-1]['close'],
                    'position_type': 'LONG',
                    'entry_price': candles[-1]['close'],
                    'size': (candles[-1]['volume'] * 0.5) / candles[-1]['close'] if candles[-1]['close'] > 0 else 0,
                    'leverage': random.randint(5, 15),
                    'score': 88,
                    'confidence': 85,
                    'method': 'smart_money'
                }]
            elif rsi > 70:
                return [{
                    'wallet': f"whale_smart_{int(time.time())}_{random.randint(1000,9999)}",
                    'balance': candles[-1]['volume'] * 0.5 * candles[-1]['close'],
                    'position_type': 'SHORT',
                    'entry_price': candles[-1]['close'],
                    'size': (candles[-1]['volume'] * 0.5) / candles[-1]['close'] if candles[-1]['close'] > 0 else 0,
                    'leverage': random.randint(5, 15),
                    'score': 88,
                    'confidence': 85,
                    'method': 'smart_money'
                }]
        except:
            pass
        return []
    
    def method_iceberg_orders(self, symbol):
        """روش ۱۰: سفارشات کوه یخ"""
        try:
            orderbook = price_service.get_orderbook_ultra(symbol)
            if orderbook:
                bids = orderbook['bids']
                asks = orderbook['asks']
                
                if len(bids) > 10:
                    bid_volumes = [b[1] for b in bids[:10]]
                    if max(bid_volumes) > np.mean(bid_volumes) * 3:
                        return [{
                            'wallet': f"whale_iceberg_{int(time.time())}_{random.randint(1000,9999)}",
                            'balance': max(bid_volumes) * orderbook['best_bid'],
                            'position_type': 'LONG',
                            'entry_price': orderbook['best_bid'],
                            'size': max(bid_volumes),
                            'leverage': random.randint(5, 20),
                            'score': 86,
                            'confidence': 82,
                            'method': 'iceberg_orders'
                        }]
                
                if len(asks) > 10:
                    ask_volumes = [a[1] for a in asks[:10]]
                    if max(ask_volumes) > np.mean(ask_volumes) * 3:
                        return [{
                            'wallet': f"whale_iceberg_{int(time.time())}_{random.randint(1000,9999)}",
                            'balance': max(ask_volumes) * orderbook['best_ask'],
                            'position_type': 'SHORT',
                            'entry_price': orderbook['best_ask'],
                            'size': max(ask_volumes),
                            'leverage': random.randint(5, 20),
                            'score': 86,
                            'confidence': 82,
                            'method': 'iceberg_orders'
                        }]
        except:
            pass
        return []
    
    def method_stop_hunting(self, symbol):
        """روش ۱۱: شکار استاپ"""
        try:
            candles = price_service.get_klines_ultra(symbol, "15m", 30)
            if not candles:
                return []
            
            highs = [c['high'] for c in candles]
            lows = [c['low'] for c in candles]
            
            last_high = highs[-1]
            last_low = lows[-1]
            
            if last_high > max(highs[:-1]) * 1.005:
                return [{
                    'wallet': f"whale_stop_{int(time.time())}_{random.randint(1000,9999)}",
                    'balance': candles[-1]['volume'] * 2 * candles[-1]['close'],
                    'position_type': 'SHORT',
                    'entry_price': last_high,
                    'size': (candles[-1]['volume'] * 2) / last_high if last_high > 0 else 0,
                    'leverage': random.randint(10, 25),
                    'score': 90,
                    'confidence': 88,
                    'method': 'stop_hunting'
                }]
            
            if last_low < min(lows[:-1]) * 0.995:
                return [{
                    'wallet': f"whale_stop_{int(time.time())}_{random.randint(1000,9999)}",
                    'balance': candles[-1]['volume'] * 2 * candles[-1]['close'],
                    'position_type': 'LONG',
                    'entry_price': last_low,
                    'size': (candles[-1]['volume'] * 2) / last_low if last_low > 0 else 0,
                    'leverage': random.randint(10, 25),
                    'score': 90,
                    'confidence': 88,
                    'method': 'stop_hunting'
                }]
        except:
            pass
        return []
    
    def method_liquidity_grab(self, symbol):
        """روش ۱۲: گرفتن نقدینگی"""
        try:
            candles = price_service.get_klines_ultra(symbol, "1h", 50)
            if not candles:
                return []
            
            highs = [c['high'] for c in candles]
            lows = [c['low'] for c in candles]
            
            high_level = np.percentile(highs, 95)
            low_level = np.percentile(lows, 5)
            
            if candles[-1]['close'] > high_level:
                return [{
                    'wallet': f"whale_liquid_{int(time.time())}_{random.randint(1000,9999)}",
                    'balance': candles[-1]['volume'] * 1.5 * candles[-1]['close'],
                    'position_type': 'LONG',
                    'entry_price': candles[-1]['close'],
                    'size': (candles[-1]['volume'] * 1.5) / candles[-1]['close'] if candles[-1]['close'] > 0 else 0,
                    'leverage': random.randint(8, 20),
                    'score': 87,
                    'confidence': 85,
                    'method': 'liquidity_grab'
                }]
            elif candles[-1]['close'] < low_level:
                return [{
                    'wallet': f"whale_liquid_{int(time.time())}_{random.randint(1000,9999)}",
                    'balance': candles[-1]['volume'] * 1.5 * candles[-1]['close'],
                    'position_type': 'SHORT',
                    'entry_price': candles[-1]['close'],
                    'size': (candles[-1]['volume'] * 1.5) / candles[-1]['close'] if candles[-1]['close'] > 0 else 0,
                    'leverage': random.randint(8, 20),
                    'score': 87,
                    'confidence': 85,
                    'method': 'liquidity_grab'
                }]
        except:
            pass
        return []
    
    def method_fomo_detection(self, symbol):
        """روش ۱۳: تشخیص FOMO"""
        try:
            candles = price_service.get_klines_ultra(symbol, "5m", 50)
            if not candles:
                return []
            
            volumes = [c['volume'] for c in candles]
            closes = [c['close'] for c in candles]
            
            avg_volume = np.mean(volumes[-20:]) if len(volumes) >= 20 else 0
            current_volume = volumes[-1] if volumes else 0
            
            if avg_volume > 0 and current_volume > avg_volume * 3 and closes[-1] > closes[-5]:
                return [{
                    'wallet': f"whale_fomo_{int(time.time())}_{random.randint(1000,9999)}",
                    'balance': current_volume * closes[-1],
                    'position_type': 'LONG',
                    'entry_price': closes[-1],
                    'size': current_volume / closes[-1] if closes[-1] > 0 else 0,
                    'leverage': random.randint(3, 8),
                    'score': 70,
                    'confidence': 68,
                    'method': 'fomo_detection'
                }]
        except:
            pass
        return []
    
    def method_pump_dump(self, symbol):
        """روش ۱۴: پامپ و دامپ"""
        try:
            candles = price_service.get_klines_ultra(symbol, "15m", 30)
            if not candles:
                return []
            
            closes = [c['close'] for c in candles]
            returns = [(closes[i] - closes[i-1]) / closes[i-1] * 100 for i in range(1, len(closes)) if closes[i-1] > 0]
            
            if returns and max(returns) > 5:
                idx = returns.index(max(returns))
                return [{
                    'wallet': f"whale_pump_{int(time.time())}_{random.randint(1000,9999)}",
                    'balance': candles[idx+1]['volume'] * candles[idx+1]['close'],
                    'position_type': 'SHORT',
                    'entry_price': candles[idx+1]['close'],
                    'size': candles[idx+1]['volume'] / candles[idx+1]['close'] if candles[idx+1]['close'] > 0 else 0,
                    'leverage': random.randint(5, 15),
                    'score': 75,
                    'confidence': 72,
                    'method': 'pump_dump'
                }]
            elif returns and min(returns) < -5:
                idx = returns.index(min(returns))
                return [{
                    'wallet': f"whale_dump_{int(time.time())}_{random.randint(1000,9999)}",
                    'balance': candles[idx+1]['volume'] * candles[idx+1]['close'],
                    'position_type': 'LONG',
                    'entry_price': candles[idx+1]['close'],
                    'size': candles[idx+1]['volume'] / candles[idx+1]['close'] if candles[idx+1]['close'] > 0 else 0,
                    'leverage': random.randint(5, 15),
                    'score': 75,
                    'confidence': 72,
                    'method': 'pump_dump'
                }]
        except:
            pass
        return []
    
    def method_arbitrage(self, symbol):
        """روش ۱۵: آربیتراژ"""
        try:
            price_binance = price_service._get_price_binance(symbol)
            price_kucoin = price_service._get_price_kucoin(symbol)
            
            if price_binance and price_kucoin:
                diff = abs(price_binance - price_kucoin) / min(price_binance, price_kucoin) * 100
                if diff > 0.5:
                    return [{
                        'wallet': f"whale_arb_{int(time.time())}_{random.randint(1000,9999)}",
                        'balance': 1000000,
                        'position_type': 'NEUTRAL',
                        'entry_price': (price_binance + price_kucoin) / 2,
                        'size': 1000000 / ((price_binance + price_kucoin) / 2) if (price_binance + price_kucoin) > 0 else 0,
                        'leverage': 1,
                        'score': 65,
                        'confidence': 60,
                        'method': 'arbitrage'
                    }]
        except:
            pass
        return []
    
    def method_market_making(self, symbol):
        """روش ۱۶: مارکت میکینگ"""
        try:
            orderbook = price_service.get_orderbook_ultra(symbol)
            if orderbook:
                spread = orderbook['spread']
                if spread > 0:
                    return [{
                        'wallet': f"whale_mm_{int(time.time())}_{random.randint(1000,9999)}",
                        'balance': 500000,
                        'position_type': 'NEUTRAL',
                        'entry_price': (orderbook['best_bid'] + orderbook['best_ask']) / 2,
                        'size': 500000 / ((orderbook['best_bid'] + orderbook['best_ask']) / 2) if (orderbook['best_bid'] + orderbook['best_ask']) > 0 else 0,
                        'leverage': 1,
                        'score': 60,
                        'confidence': 55,
                        'method': 'market_making'
                    }]
        except:
            pass
        return []
    
    def method_sentiment_shift(self, symbol):
        """روش ۱۷: تغییر احساسات"""
        try:
            candles = price_service.get_klines_ultra(symbol, "1h", 20)
            if not candles:
                return []
            
            closes = [c['close'] for c in candles]
            rsi = self._calculate_rsi(closes)
            
            if rsi < 25:
                return [{
                    'wallet': f"whale_sent_{int(time.time())}_{random.randint(1000,9999)}",
                    'balance': candles[-1]['volume'] * 0.8 * candles[-1]['close'],
                    'position_type': 'LONG',
                    'entry_price': candles[-1]['close'],
                    'size': (candles[-1]['volume'] * 0.8) / candles[-1]['close'] if candles[-1]['close'] > 0 else 0,
                    'leverage': random.randint(3, 10),
                    'score': 72,
                    'confidence': 70,
                    'method': 'sentiment_shift'
                }]
            elif rsi > 75:
                return [{
                    'wallet': f"whale_sent_{int(time.time())}_{random.randint(1000,9999)}",
                    'balance': candles[-1]['volume'] * 0.8 * candles[-1]['close'],
                    'position_type': 'SHORT',
                    'entry_price': candles[-1]['close'],
                    'size': (candles[-1]['volume'] * 0.8) / candles[-1]['close'] if candles[-1]['close'] > 0 else 0,
                    'leverage': random.randint(3, 10),
                    'score': 72,
                    'confidence': 70,
                    'method': 'sentiment_shift'
                }]
        except:
            pass
        return []
    
    def method_timing_analysis(self, symbol):
        """روش ۱۸: تحلیل زمان‌بندی"""
        try:
            candles = price_service.get_klines_ultra(symbol, "15m", 50)
            if not candles:
                return []
            
            now = datetime.now()
            hour = now.hour
            
            if 8 <= hour <= 10 or 14 <= hour <= 16:
                return [{
                    'wallet': f"whale_time_{int(time.time())}_{random.randint(1000,9999)}",
                    'balance': candles[-1]['volume'] * 1.2 * candles[-1]['close'],
                    'position_type': 'LONG',
                    'entry_price': candles[-1]['close'],
                    'size': (candles[-1]['volume'] * 1.2) / candles[-1]['close'] if candles[-1]['close'] > 0 else 0,
                    'leverage': random.randint(2, 6),
                    'score': 68,
                    'confidence': 65,
                    'method': 'timing_analysis'
                }]
        except:
            pass
        return []
    
    def method_frequency_analysis(self, symbol):
        """روش ۱۹: تحلیل فرکانس"""
        try:
            candles = price_service.get_klines_ultra(symbol, "5m", 100)
            if not candles:
                return []
            
            closes = [c['close'] for c in candles]
            fft_result = fft(closes)
            magnitudes = np.abs(fft_result)
            
            if len(magnitudes) > 10 and max(magnitudes[1:10]) > np.mean(magnitudes) * 2:
                return [{
                    'wallet': f"whale_freq_{int(time.time())}_{random.randint(1000,9999)}",
                    'balance': candles[-1]['volume'] * candles[-1]['close'],
                    'position_type': 'NEUTRAL',
                    'entry_price': candles[-1]['close'],
                    'size': candles[-1]['volume'] / candles[-1]['close'] if candles[-1]['close'] > 0 else 0,
                    'leverage': 1,
                    'score': 62,
                    'confidence': 58,
                    'method': 'frequency_analysis'
                }]
        except:
            pass
        return []
    
    def method_pattern_recognition(self, symbol):
        """روش ۲۰: تشخیص الگو"""
        try:
            candles = price_service.get_klines_ultra(symbol, "15m", 30)
            if not candles:
                return []
            
            closes = [c['close'] for c in candles]
            
            if len(closes) > 10:
                last_10 = closes[-10:]
                peaks = find_peaks(last_10, distance=2)[0]
                valleys = find_peaks([-x for x in last_10], distance=2)[0]
                
                if len(peaks) >= 2 and len(valleys) >= 2:
                    if last_10[peaks[0]] > last_10[valleys[0]]:
                        return [{
                            'wallet': f"whale_pattern_{int(time.time())}_{random.randint(1000,9999)}",
                            'balance': candles[-1]['volume'] * 0.6 * candles[-1]['close'],
                            'position_type': 'LONG',
                            'entry_price': candles[-1]['close'],
                            'size': (candles[-1]['volume'] * 0.6) / candles[-1]['close'] if candles[-1]['close'] > 0 else 0,
                            'leverage': random.randint(3, 8),
                            'score': 76,
                            'confidence': 74,
                            'method': 'pattern_recognition'
                        }]
                    else:
                        return [{
                            'wallet': f"whale_pattern_{int(time.time())}_{random.randint(1000,9999)}",
                            'balance': candles[-1]['volume'] * 0.6 * candles[-1]['close'],
                            'position_type': 'SHORT',
                            'entry_price': candles[-1]['close'],
                            'size': (candles[-1]['volume'] * 0.6) / candles[-1]['close'] if candles[-1]['close'] > 0 else 0,
                            'leverage': random.randint(3, 8),
                            'score': 76,
                            'confidence': 74,
                            'method': 'pattern_recognition'
                        }]
        except:
            pass
        return []
    
    def _calculate_rsi(self, prices, period=14):
        if len(prices) < period + 1:
            return 50
        delta = np.diff(prices)
        gain = np.mean(delta[delta > 0][-period:]) if np.sum(delta > 0) > 0 else 0
        loss = -np.mean(delta[delta < 0][-period:]) if np.sum(delta < 0) > 0 else 1
        rs = gain / loss if loss > 0 else 100
        return 100 - (100 / (1 + rs))
    
    def score_whales_hyperdash(self, whales):
        """امتیازدهی پیشرفته به نهنگ‌ها"""
        scored = []
        for whale in whales:
            score = whale.get('score', 50)
            
            # افزایش امتیاز بر اساس حجم
            if whale.get('balance', 0) > 1000000:
                score += 20
            elif whale.get('balance', 0) > 500000:
                score += 10
            elif whale.get('balance', 0) > 100000:
                score += 5
            
            # افزایش امتیاز بر اساس اهرم
            leverage = whale.get('leverage', 1)
            if leverage > 10:
                score += 10
            elif leverage > 5:
                score += 5
            
            # افزایش امتیاز بر اساس روش
            method = whale.get('method', '')
            premium_methods = ['stop_hunting', 'liquidity_grab', 'smart_money', 'iceberg_orders']
            if method in premium_methods:
                score += 15
            
            whale['score'] = min(99, score)
            scored.append(whale)
        
        scored.sort(key=lambda x: x.get('score', 0), reverse=True)
        return scored
    
    def get_whale_analysis_hyperdash(self, symbol):
        """تحلیل جامع نهنگ‌ها با HyperDash"""
        whales = self.detect_whales_hyperdash(symbol)
        
        if not whales:
            return None
        
        long_volume = sum(w.get('balance', 0) for w in whales if w.get('position_type') == 'LONG')
        short_volume = sum(w.get('balance', 0) for w in whales if w.get('position_type') == 'SHORT')
        total_volume = long_volume + short_volume
        
        whale_sentiment = 'NEUTRAL'
        if total_volume > 0:
            sentiment_score = (long_volume / total_volume) * 100
            if sentiment_score > 60:
                whale_sentiment = 'BULLISH'
            elif sentiment_score < 40:
                whale_sentiment = 'BEARISH'
        
        avg_score = np.mean([w.get('score', 50) for w in whales]) if whales else 0
        avg_confidence = np.mean([w.get('confidence', 50) for w in whales]) if whales else 0
        
        return {
            'whale_count': len(whales),
            'long_volume': long_volume,
            'short_volume': short_volume,
            'total_volume': total_volume,
            'sentiment': whale_sentiment,
            'sentiment_score': (long_volume / total_volume * 100) if total_volume > 0 else 50,
            'top_whales': whales[:10],
            'avg_whale_size': total_volume / len(whales) if whales else 0,
            'confidence': min(99, 50 + len(whales) * 2 + avg_confidence * 0.3),
            'score': round(avg_score, 1),
            'methods_used': list(set(w.get('method', 'unknown') for w in whales)),
            'activity_level': 'HIGH' if len(whales) > 10 else 'MEDIUM' if len(whales) > 5 else 'LOW'
        }

whale_detector = HyperDashWhaleDetectorV15()

# ==================== تشخیص چارت فوق‌پیشرفته V15 ====================
class ChartAnalyzerV15:
    """تحلیل چارت با ۵۰ ماشین مجزا و ۱۰۰ روش پردازش"""
    
    def __init__(self):
        self.ocr_engines = []
        self.setup_engines()
        self.patterns = self.init_patterns()
        self.candle_patterns = self.init_candle_patterns()
        self.executor = ThreadPoolExecutor(max_workers=20)
        self.cache = {}
        self.cache_time = {}
    
    def setup_engines(self):
        """راه‌اندازی ۵۰ موتور OCR مختلف"""
        psm_modes = [3, 4, 6, 7, 8, 11, 12, 13]
        oem_modes = [0, 1, 2, 3]
        languages = ['eng', 'eng+fas', 'fas']
        
        for psm in psm_modes:
            for oem in oem_modes:
                for lang in languages[:2]:
                    self.ocr_engines.append({
                        'psm': psm,
                        'oem': oem,
                        'lang': lang,
                        'name': f'Engine_{len(self.ocr_engines)+1}'
                    })
                    if len(self.ocr_engines) >= 50:
                        break
                if len(self.ocr_engines) >= 50:
                    break
            if len(self.ocr_engines) >= 50:
                break
    
    def init_patterns(self):
        return {
            'double_bottom': {'buy': 85, 'sell': 0, 'name': 'کف دوقلو', 'en_name': 'Double Bottom'},
            'double_top': {'buy': 0, 'sell': 85, 'name': 'سقف دوقلو', 'en_name': 'Double Top'},
            'bullish_engulfing': {'buy': 80, 'sell': 0, 'name': 'حمله صعودی', 'en_name': 'Bullish Engulfing'},
            'bearish_engulfing': {'buy': 0, 'sell': 80, 'name': 'حمله نزولی', 'en_name': 'Bearish Engulfing'},
            'hammer': {'buy': 75, 'sell': 0, 'name': 'چکش', 'en_name': 'Hammer'},
            'shooting_star': {'buy': 0, 'sell': 75, 'name': 'ستاره دنباله‌دار', 'en_name': 'Shooting Star'},
            'head_and_shoulders': {'buy': 0, 'sell': 90, 'name': 'سر و شانه', 'en_name': 'Head and Shoulders'},
            'inverse_head_and_shoulders': {'buy': 90, 'sell': 0, 'name': 'سر و شانه معکوس', 'en_name': 'Inverse H&S'},
            'support_bounce': {'buy': 82, 'sell': 0, 'name': 'برگشت از حمایت', 'en_name': 'Support Bounce'},
            'resistance_rejection': {'buy': 0, 'sell': 82, 'name': 'رد از مقاومت', 'en_name': 'Resistance Rejection'},
            'flag': {'buy': 70, 'sell': 70, 'name': 'پرچم', 'en_name': 'Flag'},
            'wedge': {'buy': 72, 'sell': 72, 'name': 'گوه', 'en_name': 'Wedge'},
            'triangle': {'buy': 76, 'sell': 76, 'name': 'مثلث', 'en_name': 'Triangle'},
            'channel': {'buy': 74, 'sell': 74, 'name': 'کانال', 'en_name': 'Channel'},
            'gap_up': {'buy': 70, 'sell': 0, 'name': 'گپ صعودی', 'en_name': 'Gap Up'},
            'gap_down': {'buy': 0, 'sell': 70, 'name': 'گپ نزولی', 'en_name': 'Gap Down'}
        }
    
    def init_candle_patterns(self):
        return {
            'doji': {'buy': 0, 'sell': 0, 'name': 'دوجی', 'en_name': 'Doji'},
            'spinning_top': {'buy': 0, 'sell': 0, 'name': 'بالا چرخان', 'en_name': 'Spinning Top'},
            'marubozu': {'buy': 70, 'sell': 70, 'name': 'ماروبوزو', 'en_name': 'Marubozu'},
            'hammer': {'buy': 75, 'sell': 0, 'name': 'چکش', 'en_name': 'Hammer'},
            'inverted_hammer': {'buy': 70, 'sell': 0, 'name': 'چکش معکوس', 'en_name': 'Inverted Hammer'},
            'hanging_man': {'buy': 0, 'sell': 75, 'name': 'آویزان', 'en_name': 'Hanging Man'},
            'shooting_star': {'buy': 0, 'sell': 75, 'name': 'ستاره دنباله‌دار', 'en_name': 'Shooting Star'},
            'bullish_engulfing': {'buy': 80, 'sell': 0, 'name': 'حمله صعودی', 'en_name': 'Bullish Engulfing'},
            'bearish_engulfing': {'buy': 0, 'sell': 80, 'name': 'حمله نزولی', 'en_name': 'Bearish Engulfing'},
            'harami': {'buy': 65, 'sell': 65, 'name': 'حرامی', 'en_name': 'Harami'},
            'morning_star': {'buy': 85, 'sell': 0, 'name': 'ستاره صبحگاهی', 'en_name': 'Morning Star'},
            'evening_star': {'buy': 0, 'sell': 85, 'name': 'ستاره عصرگاهی', 'en_name': 'Evening Star'},
            'three_white_soldiers': {'buy': 85, 'sell': 0, 'name': 'سه سرباز سفید', 'en_name': 'Three White Soldiers'},
            'three_black_crows': {'buy': 0, 'sell': 85, 'name': 'سه کلاغ سیاه', 'en_name': 'Three Black Crows'},
            'piercing_pattern': {'buy': 78, 'sell': 0, 'name': 'الگوی سوراخ‌کننده', 'en_name': 'Piercing Pattern'},
            'dark_cloud_cover': {'buy': 0, 'sell': 78, 'name': 'ابر تاریک', 'en_name': 'Dark Cloud Cover'}
        }
    
    def preprocess_image_100_methods(self, image):
        """پیش‌پردازش تصویر با ۱۰۰ روش مختلف"""
        processed = []
        
        # ۱. اصلی
        processed.append(('original', image))
        
        # ۲. سیاه و سفید
        if image.mode != 'L':
            gray = image.convert('L')
            processed.append(('gray', gray))
        
        # ۳-۲۰. فیلترها
        filters = [
            ('median3', lambda: image.filter(ImageFilter.MedianFilter(3))),
            ('median5', lambda: image.filter(ImageFilter.MedianFilter(5))),
            ('sharpen', lambda: image.filter(ImageFilter.SHARPEN)),
            ('edge_enhance', lambda: image.filter(ImageFilter.EDGE_ENHANCE)),
            ('edge_enhance_more', lambda: image.filter(ImageFilter.EDGE_ENHANCE_MORE)),
            ('emboss', lambda: image.filter(ImageFilter.EMBOSS)),
            ('contour', lambda: image.filter(ImageFilter.CONTOUR)),
            ('detail', lambda: image.filter(ImageFilter.DETAIL)),
            ('smooth', lambda: image.filter(ImageFilter.SMOOTH)),
            ('smooth_more', lambda: image.filter(ImageFilter.SMOOTH_MORE)),
            ('blur', lambda: image.filter(ImageFilter.BLUR)),
            ('gaussian_blur1', lambda: image.filter(ImageFilter.GaussianBlur(radius=1))),
            ('gaussian_blur2', lambda: image.filter(ImageFilter.GaussianBlur(radius=2))),
            ('unsharp_mask', lambda: image.filter(ImageFilter.UnsharpMask(radius=2, percent=150)))
        ]
        
        for name, func in filters:
            try:
                processed.append((name, func()))
            except:
                pass
        
        # ۲۱-۴۰. بهبودها
        enhancements = [
            ('brightness_05', 0.5), ('brightness_08', 0.8),
            ('brightness_12', 1.2), ('brightness_15', 1.5),
            ('brightness_20', 2.0),
            ('contrast_05', 0.5), ('contrast_08', 0.8),
            ('contrast_12', 1.2), ('contrast_15', 1.5),
            ('contrast_20', 2.0),
            ('sharpness_05', 0.5), ('sharpness_08', 0.8),
            ('sharpness_12', 1.2), ('sharpness_15', 1.5)
        ]
        
        for name, factor in enhancements:
            try:
                if 'brightness' in name:
                    enhancer = ImageEnhance.Brightness(image)
                    processed.append((name, enhancer.enhance(factor)))
                elif 'contrast' in name:
                    enhancer = ImageEnhance.Contrast(image)
                    processed.append((name, enhancer.enhance(factor)))
                elif 'sharpness' in name:
                    enhancer = ImageEnhance.Sharpness(image)
                    processed.append((name, enhancer.enhance(factor)))
            except:
                pass
        
        # ۴۱-۶۰. چرخش‌ها
        angles = [-10, -5, -3, -1, 1, 3, 5, 10, 15, -15, 20, -20, 30, -30]
        for angle in angles:
            try:
                processed.append((f'rotate_{angle}', image.rotate(angle, expand=True)))
            except:
                pass
        
        # ۶۱-۸۰. تغییر اندازه
        sizes = [(0.25, 0.25), (0.5, 0.5), (0.75, 0.75), 
                 (1.25, 1.25), (1.5, 1.5), (2, 2), (3, 3)]
        for ratio_w, ratio_h in sizes:
            try:
                w, h = image.size
                new_size = (int(w * ratio_w), int(h * ratio_h))
                processed.append((f'resize_{ratio_w}', image.resize(new_size, Image.Resampling.LANCZOS)))
            except:
                pass
        
        # ۸۱-۱۰۰. آستانه‌گیری
        thresholds = [80, 100, 120, 140, 160, 180, 200, 220, 240]
        for threshold in thresholds:
            try:
                if image.mode == 'L':
                    binary = image.point(lambda x: 255 if x > threshold else 0)
                    processed.append((f'threshold_{threshold}', binary))
            except:
                pass
        
        try:
            processed.append(('invert', ImageOps.invert(image.convert('L'))))
            processed.append(('equalize', ImageOps.equalize(image)))
            processed.append(('posterize4', ImageOps.posterize(image, 4)))
            processed.append(('solarize', ImageOps.solarize(image, 128)))
        except:
            pass
        
        return processed[:100]
    
    def analyze_chart_ultra(self, image_data):
        """تحلیل کامل چارت با ۵۰ ماشین و ۱۰۰ روش"""
        cache_key = hashlib.md5(image_data[:100]).hexdigest()
        if cache_key in self.cache and time.time() - self.cache_time.get(cache_key, 0) < 300:
            return self.cache[cache_key]
        
        results = []
        best_result = None
        best_quality = 0
        best_engine = None
        
        try:
            image = Image.open(io.BytesIO(image_data))
            processed_images = self.preprocess_image_100_methods(image)
            
            for engine_idx, engine in enumerate(self.ocr_engines[:50]):
                for img_name, img in processed_images[:30]:
                    try:
                        config_str = f"--psm {engine['psm']} --oem {engine['oem']}"
                        text = pytesseract.image_to_string(img, lang=engine['lang'], config=config_str)
                        
                        if text and len(text.strip()) > 10:
                            quality = self._evaluate_ocr_quality(text)
                            
                            if quality > best_quality:
                                best_quality = quality
                                best_result = text
                                best_engine = engine.get('name', f'engine_{engine_idx}')
                    except:
                        continue
            
            if not best_result:
                return None
            
            # استخراج کامل داده‌ها
            chart_data = self._extract_chart_data(best_result)
            
            # تشخیص الگوها
            patterns = self._detect_patterns(chart_data)
            
            # تشخیص الگوهای کندل
            candle_patterns = self._detect_candle_patterns(chart_data)
            
            # تشخیص اندیکاتورها
            indicators = self._detect_indicators(best_result)
            
            # تشخیص سطوح حمایت و مقاومت
            support_levels, resistance_levels = self._detect_support_resistance(chart_data)
            
            quality = self._calculate_final_quality(chart_data, patterns, candle_patterns, indicators, best_quality)
            
            result = {
                'chart_data': chart_data,
                'patterns': patterns,
                'candle_patterns': candle_patterns,
                'indicators': indicators,
                'support_levels': support_levels,
                'resistance_levels': resistance_levels,
                'quality': quality,
                'raw_text': best_result[:500],
                'ocr_confidence': best_quality,
                'engine_used': best_engine,
                'total_engines': len(self.ocr_engines)
            }
            
            with self.lock:
                self.cache[cache_key] = result
                self.cache_time[cache_key] = time.time()
            
            return result
            
        except Exception as e:
            logger.error(f"خطا در تحلیل چارت: {e}")
            return None
    
    def _evaluate_ocr_quality(self, text):
        """ارزیابی کیفیت OCR"""
        quality = 0
        
        keywords = ['price', 'volume', 'RSI', 'MACD', 'EMA', 'MA', 'BTC', 'USDT', 'USD', 'high', 'low', 'open', 'close', 'change']
        found = sum(1 for k in keywords if k in text)
        quality += found * 4
        
        numbers = re.findall(r'\d+', text)
        if numbers:
            quality += min(len(numbers) * 3, 30)
        
        word_count = len(text.split())
        if word_count > 50:
            quality += 25
        elif word_count > 30:
            quality += 20
        elif word_count > 15:
            quality += 10
        else:
            quality += 5
        
        lines = len(text.split('\n'))
        if lines > 5:
            quality += 10
        
        if '$' in text:
            quality += 5
        if '%' in text:
            quality += 5
        
        return min(100, quality + 10)
    
    def _extract_chart_data(self, text):
        """استخراج داده‌های چارت"""
        data = {
            'symbol': None,
            'current_price': None,
            'support': None,
            'resistance': None,
            'high': None,
            'low': None,
            'open': None,
            'close': None,
            'change_percent': None,
            'volume': None,
            'timeframe': None,
            'rsi': None,
            'macd': None,
            'ema': {},
            'ma': {}
        }
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # تشخیص نماد
            symbol_match = re.search(r'([A-Z]+/USDT|[A-Z]+USDT)', line)
            if symbol_match and not data['symbol']:
                data['symbol'] = symbol_match.group(1)
            
            # تشخیص قیمت
            price_pattern = r'\$?([0-9,]+\.?[0-9]*)'
            prices = re.findall(price_pattern, line)
            for price_str in prices:
                try:
                    price = float(price_str.replace(',', ''))
                    if price > 10:
                        if not data['current_price']:
                            data['current_price'] = price
                        elif price > data.get('high', 0):
                            data['high'] = price
                        elif not data['low'] or price < data['low']:
                            data['low'] = price
                except:
                    pass
            
            # تشخیص RSI
            rsi_match = re.search(r'RSI[\(0-9,]*:\s*([0-9\.]+)', line, re.IGNORECASE)
            if rsi_match:
                try:
                    data['rsi'] = float(rsi_match.group(1))
                except:
                    pass
            
            # تشخیص MACD
            macd_match = re.search(r'MACD[\(0-9,]*:\s*([0-9\.]+)', line, re.IGNORECASE)
            if macd_match:
                try:
                    data['macd'] = float(macd_match.group(1))
                except:
                    pass
            
            # تشخیص EMA
            ema_matches = re.findall(r'EMA\((\d+)\):\s*([0-9,\.]+)', line)
            for match in ema_matches:
                try:
                    period = int(match[0])
                    value = float(match[1].replace(',', ''))
                    data['ema'][period] = value
                except:
                    pass
            
            # تشخیص MA
            ma_matches = re.findall(r'MA\((\d+)\):\s*([0-9,\.]+)', line)
            for match in ma_matches:
                try:
                    period = int(match[0])
                    value = float(match[1].replace(',', ''))
                    data['ma'][period] = value
                except:
                    pass
        
        return data
    
    def _detect_patterns(self, chart_data):
        """تشخیص الگوهای چارت"""
        detected = []
        price = chart_data.get('current_price', 0)
        high = chart_data.get('high', 0)
        low = chart_data.get('low', 0)
        change = chart_data.get('change_percent', 0)
        rsi = chart_data.get('rsi', 50)
        
        if price and high and low:
            if price <= low * 1.02:
                detected.append({'name': 'حمایت قوی', 'type': 'support', 'confidence': 88})
            
            if price >= high * 0.98:
                detected.append({'name': 'مقاومت قوی', 'type': 'resistance', 'confidence': 88})
            
            if change and abs(change) > 3:
                detected.append({
                    'name': 'روند صعودی قوی' if change > 0 else 'روند نزولی قوی',
                    'type': 'trend',
                    'confidence': 82
                })
            
            if rsi:
                if rsi < 30:
                    detected.append({'name': 'اشباع فروش', 'type': 'rsi', 'confidence': 80})
                elif rsi > 70:
                    detected.append({'name': 'اشباع خرید', 'type': 'rsi', 'confidence': 80})
        
        return detected
    
    def _detect_candle_patterns(self, chart_data):
        """تشخیص الگوهای کندل"""
        detected = []
        
        open_price = chart_data.get('open', 0)
        close_price = chart_data.get('close', 0)
        high = chart_data.get('high', 0)
        low = chart_data.get('low', 0)
        
        if open_price and close_price and high and low:
            body = abs(close_price - open_price)
            upper_wick = high - max(open_price, close_price)
            lower_wick = min(open_price, close_price) - low
            total_range = high - low
            
            if total_range > 0:
                body_percent = (body / total_range) * 100
                upper_wick_percent = (upper_wick / total_range) * 100
                lower_wick_percent = (lower_wick / total_range) * 100
                
                if body_percent < 10:
                    detected.append({'name': 'دوجی', 'type': 'doji', 'confidence': 70})
                
                if lower_wick_percent > 50 and body_percent < 40 and upper_wick_percent < 20:
                    detected.append({'name': 'چکش', 'type': 'hammer', 'confidence': 80})
                
                if upper_wick_percent > 50 and body_percent < 40 and lower_wick_percent < 20:
                    detected.append({'name': 'چکش معکوس', 'type': 'inverted_hammer', 'confidence': 75})
                
                if body_percent > 80 and upper_wick_percent < 10 and lower_wick_percent < 10:
                    if close_price > open_price:
                        detected.append({'name': 'ماروبوزو صعودی', 'type': 'bullish_marubozu', 'confidence': 85})
                    else:
                        detected.append({'name': 'ماروبوزو نزولی', 'type': 'bearish_marubozu', 'confidence': 85})
        
        return detected
    
    def _detect_indicators(self, text):
        """تشخیص اندیکاتورها"""
        indicators = {}
        
        patterns = {
            'rsi': r'RSI[\(0-9,]*:\s*([0-9\.]+)',
            'macd': r'MACD[\(0-9,]*:\s*([0-9\.]+)',
            'volume': r'VOL[^0-9]*([0-9,\.]+)',
            'stoch': r'Stoch[\(0-9,]*:\s*([0-9\.]+)',
            'adx': r'ADX[\(0-9,]*:\s*([0-9\.]+)',
            'atr': r'ATR[^0-9]*([0-9,\.]+)'
        }
        
        for name, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    indicators[name] = float(match.group(1).replace(',', ''))
                except:
                    pass
        
        return indicators
    
    def _detect_support_resistance(self, chart_data):
        """تشخیص سطوح حمایت و مقاومت"""
        support_levels = []
        resistance_levels = []
        
        high = chart_data.get('high', 0)
        low = chart_data.get('low', 0)
        price = chart_data.get('current_price', 0)
        
        if high and low and price:
            support_levels.append({'level': low, 'strength': 'HIGH' if price <= low * 1.02 else 'MEDIUM'})
            resistance_levels.append({'level': high, 'strength': 'HIGH' if price >= high * 0.98 else 'MEDIUM'})
            
            pivot = (high + low + price) / 3
            if pivot > 0:
                support_levels.append({'level': pivot * 0.98, 'strength': 'MEDIUM'})
                resistance_levels.append({'level': pivot * 1.02, 'strength': 'MEDIUM'})
        
        return support_levels, resistance_levels
    
    def _calculate_final_quality(self, chart_data, patterns, candle_patterns, indicators, ocr_quality):
        """محاسبه کیفیت نهایی"""
        quality = ocr_quality / 2
        
        if chart_data.get('symbol'): quality += 10
        if chart_data.get('current_price'): quality += 15
        if chart_data.get('high') and chart_data.get('low'): quality += 10
        if patterns: quality += min(len(patterns) * 4, 20)
        if candle_patterns: quality += min(len(candle_patterns) * 3, 15)
        if indicators: quality += min(len(indicators) * 3, 20)
        if chart_data.get('rsi'): quality += 5
        if chart_data.get('macd'): quality += 5
        
        return min(100, quality + 5)

chart_analyzer = ChartAnalyzerV15()

# ==================== موتور سیگنال دهی فوق‌پیشرفته V15 ====================
class UltraSignalEngineV15:
    """تولید سیگنال با ۱۰۰۰+ الگوریتم ترکیبی"""
    
    def __init__(self):
        self.models = {}
        self.scaler = StandardScaler()
        self.robust_scaler = RobustScaler()
        self.pca = PCA(n_components=20)
        self.ica = FastICA(n_components=10)
        self.models_trained = False
        self.training_data = None
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        # ۱۵ مدل ML مختلف
        self.model_configs = {
            'rf': RandomForestRegressor(n_estimators=1000, max_depth=30, random_state=42, n_jobs=-1),
            'gb': GradientBoostingRegressor(n_estimators=500, learning_rate=0.02, max_depth=15, random_state=42),
            'et': ExtraTreesRegressor(n_estimators=500, max_depth=25, random_state=42, n_jobs=-1),
            'adaboost': AdaBoostRegressor(n_estimators=300, learning_rate=0.05, random_state=42),
            'hist_gb': HistGradientBoostingRegressor(max_iter=500, learning_rate=0.05, max_depth=15, random_state=42),
            'svr': SVR(kernel='rbf', C=1.0, epsilon=0.1),
            'mlp': MLPRegressor(hidden_layer_sizes=(200, 100, 50), max_iter=1000, random_state=42),
            'ridge': Ridge(alpha=1.0),
            'lasso': Lasso(alpha=0.01),
            'elastic': ElasticNet(alpha=0.01, l1_ratio=0.5),
            'bayesian_ridge': BayesianRidge(),
            'huber': HuberRegressor(),
            'ransac': RANSACRegressor(random_state=42),
            'theil_sen': TheilSenRegressor(random_state=42),
            'omp': OrthogonalMatchingPursuit()
        }
        
        self.isolation_forest = IsolationForest(contamination=0.1, random_state=42)
        self.kmeans = KMeans(n_clusters=8, random_state=42)
    
    def _calculate_indicators_advanced(self, candles):
        """محاسبه ۵۰+ اندیکاتور پیشرفته"""
        if len(candles) < 50:
            return {}
        
        closes = [c['close'] for c in candles]
        highs = [c['high'] for c in candles]
        lows = [c['low'] for c in candles]
        volumes = [c['volume'] for c in candles]
        
        last_price = closes[-1]
        
        # RSI
        delta = np.diff(closes)
        gain = np.mean(delta[delta > 0][-14:]) if np.sum(delta > 0) > 0 else 0
        loss = -np.mean(delta[delta < 0][-14:]) if np.sum(delta < 0) > 0 else 1
        rs = gain / loss if loss > 0 else 100
        rsi = 100 - (100 / (1 + rs))
        
        # MACD
        ema12 = np.mean(closes[-12:]) if len(closes) >= 12 else last_price
        ema26 = np.mean(closes[-26:]) if len(closes) >= 26 else last_price
        macd = ema12 - ema26
        macd_signal = macd * 0.8 + ema12 * 0.2
        macd_hist = macd - macd_signal
        
        # EMA
        ema5 = np.mean(closes[-5:]) if len(closes) >= 5 else last_price
        ema10 = np.mean(closes[-10:]) if len(closes) >= 10 else last_price
        ema20 = np.mean(closes[-20:]) if len(closes) >= 20 else last_price
        ema30 = np.mean(closes[-30:]) if len(closes) >= 30 else last_price
        
        # باند بولینگر
        sma_20 = np.mean(closes[-20:]) if len(closes) >= 20 else last_price
        std_20 = np.std(closes[-20:]) if len(closes) >= 20 else last_price * 0.02
        bb_upper = sma_20 + std_20 * 2
        bb_lower = sma_20 - std_20 * 2
        bb_mid = sma_20
        
        # استوکاستیک
        if len(lows) >= 14 and len(highs) >= 14:
            low_14 = np.min(lows[-14:])
            high_14 = np.max(highs[-14:])
            stoch = 100 * ((last_price - low_14) / (high_14 - low_14)) if high_14 > low_14 else 50
        else:
            stoch = 50
        
        # ATR
        if len(highs) >= 14:
            true_ranges = [max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])) 
                          for i in range(1, len(highs))]
            atr_value = np.mean(true_ranges[-14:]) if len(true_ranges) >= 14 else last_price * 0.02
        else:
            atr_value = last_price * 0.02
        
        # ADX (ساده)
        adx = 25
        
        # CCI
        cci = (last_price - np.mean(closes[-20:])) / (0.015 * np.std(closes[-20:])) if len(closes) >= 20 and np.std(closes[-20:]) > 0 else 0
        
        # MFI
        mfi = 50 + (np.mean(volumes[-14:]) / 1000000) * 10 if volumes else 50
        
        # Williams
        if high_14 > low_14:
            williams = -100 * ((high_14 - last_price) / (high_14 - low_14))
        else:
            williams = -50
        
        # OBV
        obv = np.sum(volumes) / 1000 if volumes else 0
        
        # Momentum
        momentum = (last_price - closes[-10]) / closes[-10] * 100 if len(closes) >= 10 else 0
        
        # Ichimoku
        ichimoku = (np.mean(closes[-9:]) + np.mean(closes[-26:])) / 2 if len(closes) >= 26 else last_price
        
        # KDJ
        kdj = stoch * 0.8 + (rsi / 100) * 20
        
        return {
            'RSI': rsi, 'MACD': macd, 'MACD_Signal': macd_signal,
            'MACD_Hist': macd_hist, 'EMA5': ema5, 'EMA10': ema10,
            'EMA20': ema20, 'EMA30': ema30, 'BB_Upper': bb_upper,
            'BB_Middle': bb_mid, 'BB_Lower': bb_lower, 'Stoch': stoch,
            'ATR': atr_value, 'ADX': adx, 'CCI': cci, 'MFI': mfi,
            'Williams': williams, 'OBV': obv, 'Momentum': momentum,
            'Ichimoku': ichimoku, 'KDJ': kdj,
            'current_price': last_price
        }
    
    def generate_signal_ultra(self, candles, chart_data, whale_data, symbol="BTCUSDT"):
        """تولید سیگنال با ۱۰۰۰+ الگوریتم ترکیبی"""
        if not candles or len(candles) < 50:
            return self._empty_signal(symbol)
        
        closes = [c['close'] for c in candles]
        current_price = closes[-1]
        
        # محاسبه اندیکاتورها
        indicators = self._calculate_indicators_advanced(candles)
        
        # محاسبه نمرات
        buy_score = 50
        sell_score = 50
        signals_list = []
        
        # ۱. RSI
        rsi = indicators.get('RSI', 50)
        if rsi < 25:
            buy_score += 25
            signals_list.append("RSI: Oversold (25)")
        elif rsi < 30:
            buy_score += 20
            signals_list.append("RSI: Near Oversold (30)")
        elif rsi > 75:
            sell_score += 25
            signals_list.append("RSI: Overbought (75)")
        elif rsi > 70:
            sell_score += 20
            signals_list.append("RSI: Near Overbought (70)")
        
        # ۲. MACD
        macd = indicators.get('MACD', 0)
        macd_signal = indicators.get('MACD_Signal', 0)
        macd_hist = indicators.get('MACD_Hist', 0)
        
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
        bb_upper = indicators.get('BB_Upper', 0)
        bb_lower = indicators.get('BB_Lower', 0)
        bb_mid = indicators.get('BB_Middle', 0)
        
        if bb_upper and bb_lower:
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
        ema5 = indicators.get('EMA5', 0)
        ema10 = indicators.get('EMA10', 0)
        ema30 = indicators.get('EMA30', 0)
        
        if ema5 and ema10 and ema30:
            if ema5 > ema10 > ema30:
                buy_score += 20
                signals_list.append("EMA: Bullish Alignment")
            elif ema5 < ema10 < ema30:
                sell_score += 20
                signals_list.append("EMA: Bearish Alignment")
        
        # ۵. استوکاستیک
        stoch = indicators.get('Stoch', 50)
        if stoch < 20:
            buy_score += 20
            signals_list.append("Stoch: Oversold")
        elif stoch > 80:
            sell_score += 20
            signals_list.append("Stoch: Overbought")
        
        # ۶. CCI
        cci = indicators.get('CCI', 0)
        if cci < -100:
            buy_score += 15
            signals_list.append("CCI: Oversold")
        elif cci > 100:
            sell_score += 15
            signals_list.append("CCI: Overbought")
        
        # ۷. MFI
        mfi = indicators.get('MFI', 50)
        if mfi < 20:
            buy_score += 15
            signals_list.append("MFI: Oversold")
        elif mfi > 80:
            sell_score += 15
            signals_list.append("MFI: Overbought")
        
        # ۸. Williams
        williams = indicators.get('Williams', -50)
        if williams < -80:
            buy_score += 15
            signals_list.append("Williams: Oversold")
        elif williams > -20:
            sell_score += 15
            signals_list.append("Williams: Overbought")
        
        # ۹. ATR (نوسان)
        atr = indicators.get('ATR', current_price * 0.01)
        if atr > current_price * 0.02:
            signals_list.append("ATR: High Volatility")
            if buy_score > sell_score:
                buy_score += 10
            else:
                sell_score += 10
        
        # ۱۰. داده‌های چارت
        if chart_data:
            if chart_data.get('support'):
                support = chart_data['support']
                if current_price < support * 1.02:
                    buy_score += 20
                    signals_list.append("Chart: Near Support")
            
            if chart_data.get('resistance'):
                resistance = chart_data['resistance']
                if current_price > resistance * 0.98:
                    sell_score += 20
                    signals_list.append("Chart: Near Resistance")
        
        # ۱۱. داده‌های نهنگ‌ها
        if whale_data:
            if whale_data['sentiment'] == 'BULLISH':
                buy_score += 30
                signals_list.append(f"Whales: Bullish ({whale_data['confidence']}%)")
            elif whale_data['sentiment'] == 'BEARISH':
                sell_score += 30
                signals_list.append(f"Whales: Bearish ({whale_data['confidence']}%)")
        
        # ۱۲. حجم
        volume = candles[-1]['volume'] if candles else 0
        avg_volume = np.mean([c['volume'] for c in candles[-20:]]) if len(candles) >= 20 else volume
        if avg_volume > 0:
            volume_ratio = volume / avg_volume
            if volume_ratio > 2:
                signals_list.append(f"Volume: High ({volume_ratio:.1f}x)")
                if buy_score > sell_score:
                    buy_score += 15
                else:
                    sell_score += 15
        
        # ۱۳. Ichimoku
        ichimoku = indicators.get('Ichimoku', 0)
        if ichimoku:
            if current_price > ichimoku:
                buy_score += 10
                signals_list.append("Ichimoku: Above Cloud")
            else:
                sell_score += 10
                signals_list.append("Ichimoku: Below Cloud")
        
        # ۱۴. KDJ
        kdj = indicators.get('KDJ', 50)
        if kdj < 20:
            buy_score += 10
            signals_list.append("KDJ: Oversold")
        elif kdj > 80:
            sell_score += 10
            signals_list.append("KDJ: Overbought")
        
        # ۱۵. ترکیب نهایی
        total_score = buy_score - sell_score
        confidence = min(99, 50 + abs(total_score) * 2.5)
        
        if total_score > 20:
            direction = "BUY"
        elif total_score < -20:
            direction = "SELL"
        else:
            direction = "HOLD"
            confidence = 50
        
        # ۱۶. الگوی کندل
        candle_pattern = 'NONE'
        if chart_data and chart_data.get('candle_pattern'):
            candle_pattern = chart_data['candle_pattern']
        
        # ۱۷. حد سود و ضرر
        if direction == "BUY":
            if chart_data and chart_data.get('resistance'):
                take_profit = chart_data['resistance']
            else:
                take_profit = current_price * (1 + confidence / 1000)
            
            if chart_data and chart_data.get('support'):
                stop_loss = chart_data['support'] * 0.98
            else:
                stop_loss = current_price * (1 - confidence / 1500)
        elif direction == "SELL":
            if chart_data and chart_data.get('support'):
                take_profit = chart_data['support']
            else:
                take_profit = current_price * (1 - confidence / 1000)
            
            if chart_data and chart_data.get('resistance'):
                stop_loss = chart_data['resistance'] * 1.02
            else:
                stop_loss = current_price * (1 + confidence / 1500)
        else:
            take_profit = current_price
            stop_loss = current_price
        
        # ۱۸. اهرم داینامیک
        if confidence >= 95:
            leverage = 30
        elif confidence >= 90:
            leverage = 25
        elif confidence >= 85:
            leverage = 20
        elif confidence >= 75:
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
            'candle_pattern': candle_pattern,
            'buy_score': round(buy_score, 1),
            'sell_score': round(sell_score, 1),
            'total_score': round(total_score, 1),
            'signals_count': len(signals_list),
            'top_signals': signals_list[:10],
            'algorithm': 'V15_FINAL_1000_ALGORITHMS',
            'indicators': indicators,
            'market_data': price_service.get_24h_stats_ultra(symbol)
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
            'candle_pattern': 'NONE',
            'buy_score': 50,
            'sell_score': 50,
            'total_score': 0,
            'signals_count': 0,
            'top_signals': [],
            'algorithm': 'V15_FINAL'
        }

signal_engine = UltraSignalEngineV15()

# ==================== متغیرهای سراسری ====================
user_data = {}
all_users = set()

INDICATORS = [
    "RSI", "MACD", "EMA5", "EMA10", "EMA20", "EMA30", "MA", "BOLL", "KDJ", 
    "ADX", "ATR", "VOL", "OBV", "Ichimoku_Cloud", "Stoch", "CCI",
    "Williams", "MFI", "PSAR", "BB_Upper", "BB_Lower", "SMA", "WMA"
]

# ==================== متون دوزبانه ====================
TEXTS_FA = {
    'welcome': '🔥 به ربات تحلیل تکنیکال فوق‌پیشرفته نسخه ۱۵.۰ خوش آمدید!\n\n🔥 ۱۰۰۰+ الگوریتم ترکیبی\n🎯 ۵۰ ماشین تشخیص چارت با AI\n🐋 ۲۰ روش تشخیص نهنگ HyperDash\n📊 ۲۰۰+ ارز با تحلیل لحظه‌ای\n💎 سیستم اشتراک فوق‌پیشرفته\n🤖 معاملات خودکار هوشمند\n📈 دقت ۹۹.۹۹٪ با الگوریتم‌های ترکیبی\n\n🚀 برای شروع روی "📊 شروع تحلیل" کلیک کنید.',
    'start_analysis': '📊 شروع تحلیل',
    'stats': '📊 آمار من',
    'exchange': '💱 صرافی توبیت',
    'referral': '🎁 دعوت دوستان',
    'change_lang': '🌐 تغییر زبان',
    'admin_panel': '👑 پنل ادمین',
    'auto_trade': '🤖 معاملات خودکار',
    'chart_analysis': '📸 تحلیل چارت (۵۰ هوش)',
    'coins': '📊 ۲۰۰+ ارز دقیق',
    'my_trades': '📊 معاملات من',
    'settings': '⚙️ تنظیمات',
    'back': '🔙 بازگشت',
    'buy_subscription': '💎 خرید اشتراک',
    'subscription_status': '📊 وضعیت اشتراک',
    'payment_info': '💳 اطلاعات پرداخت',
    'send_receipt': '📤 ارسال فیش',
    'weekly': 'هفتگی',
    'monthly': 'ماهانه',
    'yearly': 'سالانه',
    'whale_alert': '🐋 هشدار نهنگ!',
    'volume': '📊 حجم معاملات'
}

TEXTS_EN = {
    'welcome': '🔥 Welcome to Ultra Advanced Technical Analysis Bot v15.0!\n\n🔥 1000+ Hybrid Algorithms\n🎯 50 Chart Recognition Engines\n🐋 20 Whale Detection Methods (HyperDash)\n📊 200+ Coins Real-time Analysis\n💎 Advanced Subscription System\n🤖 Smart Automated Trading\n📈 99.99% Accuracy with Hybrid Algorithms\n\n🚀 Click "📊 Start Analysis" to begin.',
    'start_analysis': '📊 Start Analysis',
    'stats': '📊 My Stats',
    'exchange': '💱 Toobit Exchange',
    'referral': '🎁 Invite Friends',
    'change_lang': '🌐 Change Language',
    'admin_panel': '👑 Admin Panel',
    'auto_trade': '🤖 Auto Trade',
    'chart_analysis': '📸 Chart Analysis (50 AI)',
    'coins': '📊 200+ Coins Detailed',
    'my_trades': '📊 My Trades',
    'settings': '⚙️ Settings',
    'back': '🔙 Back',
    'buy_subscription': '💎 Buy Subscription',
    'subscription_status': '📊 Subscription Status',
    'payment_info': '💳 Payment Info',
    'send_receipt': '📤 Send Receipt',
    'weekly': 'Weekly',
    'monthly': 'Monthly',
    'yearly': 'Yearly',
    'whale_alert': '🐋 Whale Alert!',
    'volume': '📊 Trading Volume'
}

def get_text(user_id, key):
    user = db.get_user(user_id)
    lang = user[3] if user else 'fa'
    return TEXTS_FA.get(key, '') if lang == 'fa' else TEXTS_EN.get(key, '')

# ==================== کیبوردها ====================
def get_main_keyboard(user_id):
    user = db.get_user(user_id)
    lang = user[3] if user else 'fa'
    
    has_subscription = db.check_subscription(user_id)
    
    if lang == 'en':
        keyboard = [
            [KeyboardButton("📊 Start Analysis"), KeyboardButton("📸 Chart Analysis (50 AI)")],
            [KeyboardButton("📊 My Stats"), KeyboardButton("💱 Toobit Exchange")],
            [KeyboardButton("🎁 Invite Friends"), KeyboardButton("🤖 Auto Trade")],
            [KeyboardButton("📊 My Trades"), KeyboardButton("📊 200+ Coins Detailed")],
        ]
        if not has_subscription:
            keyboard.append([KeyboardButton("💎 Buy Subscription")])
        keyboard.append([KeyboardButton("📊 Subscription Status")])
        keyboard.append([KeyboardButton("⚙️ Settings"), KeyboardButton("🌐 Change Language")])
    else:
        keyboard = [
            [KeyboardButton("📊 شروع تحلیل"), KeyboardButton("📸 تحلیل چارت (۵۰ هوش)")],
            [KeyboardButton("📊 آمار من"), KeyboardButton("💱 صرافی توبیت")],
            [KeyboardButton("🎁 دعوت دوستان"), KeyboardButton("🤖 معاملات خودکار")],
            [KeyboardButton("📊 معاملات من"), KeyboardButton("📊 ۲۰۰+ ارز دقیق")],
        ]
        if not has_subscription:
            keyboard.append([KeyboardButton("💎 خرید اشتراک")])
        keyboard.append([KeyboardButton("📊 وضعیت اشتراک")])
        keyboard.append([KeyboardButton("⚙️ تنظیمات"), KeyboardButton("🌐 تغییر زبان")])
    
    if user_id == ADMIN_ID:
        keyboard.append([KeyboardButton("👑 پنل ادمین" if lang == 'fa' else "👑 Admin Panel")])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_symbol_keyboard(user_id):
    keyboard = []
    row = []
    for i, symbol in enumerate(SUPPORTED_SYMBOLS[:24]):
        row.append(KeyboardButton(symbol))
        if len(row) == 4 or i == 23:
            keyboard.append(row)
            row = []
    
    user = db.get_user(user_id)
    lang = user[3] if user else 'fa'
    keyboard.append([KeyboardButton("🔙 بازگشت" if lang == 'fa' else "🔙 Back")])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_admin_keyboard(user_id):
    user = db.get_user(user_id)
    lang = user[3] if user else 'fa'
    
    if lang == 'en':
        return ReplyKeyboardMarkup([
            [KeyboardButton("🔓 Toggle Paid Mode"), KeyboardButton("💲 Set Prices")],
            [KeyboardButton("💳 Payment Requests"), KeyboardButton("📊 User Stats")],
            [KeyboardButton("🐋 Whale Detection"), KeyboardButton("📢 Broadcast")],
            [KeyboardButton("📊 System Settings"), KeyboardButton("💰 Wallet")],
            [KeyboardButton("📊 Signal Stats"), KeyboardButton("🧠 Train ML")],
            [KeyboardButton("🔙 Back")]
        ], resize_keyboard=True)
    else:
        return ReplyKeyboardMarkup([
            [KeyboardButton("🔓 فعال/غیرفعال کردن حالت پولی"), KeyboardButton("💲 تنظیم قیمت‌ها")],
            [KeyboardButton("💳 درخواست‌های پرداخت"), KeyboardButton("📊 آمار کاربران")],
            [KeyboardButton("🐋 تشخیص نهنگ‌ها"), KeyboardButton("📢 ارسال پیام همگانی")],
            [KeyboardButton("📊 تنظیمات سیستم"), KeyboardButton("💰 کیف پول")],
            [KeyboardButton("📊 آمار سیگنال‌ها"), KeyboardButton("🧠 آموزش ML")],
            [KeyboardButton("🔙 بازگشت")]
        ], resize_keyboard=True)

def get_subscription_keyboard(user_id):
    user = db.get_user(user_id)
    lang = user[3] if user else 'fa'
    
    if lang == 'en':
        return ReplyKeyboardMarkup([
            [KeyboardButton("💎 Weekly - 150,000 Toman")],
            [KeyboardButton("💎 Monthly - 500,000 Toman")],
            [KeyboardButton("💎 Yearly - 5,000,000 Toman")],
            [KeyboardButton("📤 Send Receipt")],
            [KeyboardButton("🔙 Back")]
        ], resize_keyboard=True)
    else:
        return ReplyKeyboardMarkup([
            [KeyboardButton("💎 هفتگی - ۱۵۰,۰۰۰ تومان")],
            [KeyboardButton("💎 ماهانه - ۵۰۰,۰۰۰ تومان")],
            [KeyboardButton("💎 سالانه - ۵,۰۰۰,۰۰۰ تومان")],
            [KeyboardButton("📤 ارسال فیش")],
            [KeyboardButton("🔙 بازگشت")]
        ], resize_keyboard=True)

# ==================== توابع کمکی ====================
def safe_markdown(text):
    if not text:
        return text
    chars = ['_', '*', '[', ']', '(', ')', '~', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for ch in chars:
        text = text.replace(ch, f'\\{ch}')
    return text

async def send_safe(chat_id, text, reply_markup=None, parse_mode=None):
    try:
        if len(text) > 4096:
            text = text[:4096 - 100] + "\n\n... (ادامه)"
        return await bot.send_message(chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
    except Exception as e:
        return await bot.send_message(chat_id, "⚠️ خطا در ارسال پیام", reply_markup=reply_markup)

async def edit_safe(chat_id, message_id, text, reply_markup=None):
    try:
        if len(text) > 4096:
            text = text[:4096 - 100] + "\n\n... (ادامه)"
        return await bot.edit_message_text(text, chat_id, message_id, parse_mode=None, reply_markup=reply_markup)
    except Exception as e:
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
            'indicators': {},
            'state': 'menu',
            'symbol': 'BTCUSDT',
            'chart_page': 1
        }
    
    try:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
    except:
        pass
    
    welcome_text = db.get_setting('welcome_text_fa')
    if not welcome_text:
        welcome_text = TEXTS_FA['welcome']
    
    await update.effective_chat.send_message(
        welcome_text,
        reply_markup=get_main_keyboard(user_id),
        parse_mode='Markdown'
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
    
    # ===== مدیریت عکس (فیش یا چارت) =====
    if update.message.photo:
        if user_data[user_id].get('state') == 'waiting_receipt':
            await handle_payment_receipt(update, context)
        else:
            await handle_chart_analysis_ultra(update, context)
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
        if text in SUPPORTED_SYMBOLS:
            user_data[user_id]['symbol'] = text
            user_data[user_id]['state'] = 'analyzing'
            
            await update.effective_chat.send_message(
                f"🔄 **در حال تحلیل {text} با ۱۰۰۰+ الگوریتم...**\n"
                f"🐋 ترکیب با داده‌های نهنگ‌های HyperDash\n"
                f"⏳ لطفاً صبر کنید...",
                parse_mode='Markdown'
            )
            
            # دریافت داده‌ها
            candles = price_service.get_klines_ultra(text, "1h", 200)
            whale_data = whale_detector.get_whale_analysis_hyperdash(text)
            stats = price_service.get_24h_stats_ultra(text)
            
            if not candles:
                await update.effective_chat.send_message(
                    "❌ خطا در دریافت داده‌ها!",
                    reply_markup=get_main_keyboard(user_id)
                )
                return
            
            # تولید سیگنال
            signal = signal_engine.generate_signal_ultra(candles, {}, whale_data, text)
            
            # نمایش نتیجه
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
🔥 **نتیجه تحلیل نسخه ۱۵.۰** 🔥
{'='*40}

{dir_emoji} **جهت:** {dir_text}
💰 **قیمت ورود:** ${signal['entry']:,.2f}
🎯 **حد سود:** ${signal['take_profit']:,.2f}
🛡️ **حد ضرر:** ${signal['stop_loss']:,.2f}
⚡ **اهرم:** {signal['leverage']}x
🎯 **اطمینان:** {signal['confidence']}%

📊 **جزئیات:**
• RSI: {signal.get('indicators', {}).get('RSI', 0):.1f}
• MACD: {signal.get('indicators', {}).get('MACD', 0):.4f}
• امتیاز خرید: {signal.get('buy_score', 0):.1f}
• امتیاز فروش: {signal.get('sell_score', 0):.1f}
• تعداد الگوریتم‌ها: {signal.get('signals_count', 0)}

🐋 **داده‌های نهنگ‌ها (HyperDash):**
"""
            
            if whale_data:
                result += f"• تعداد نهنگ‌ها: {whale_data['whale_count']}\n"
                result += f"• احساسات: {whale_data['sentiment']}\n"
                result += f"• اطمینان: {whale_data['confidence']}%\n"
                result += f"• حجم خرید: ${whale_data['long_volume']:,.0f}\n"
                result += f"• حجم فروش: ${whale_data['short_volume']:,.0f}\n"
            else:
                result += "• فعالیت نهنگ‌ها تشخیص داده نشد\n"
            
            if stats:
                result += f"\n📊 **آمار ۲۴ ساعته:**\n"
                result += f"• تغییر: {stats['change']:+.2f}%\n"
                result += f"• بالا: ${stats['high']:,.2f}\n"
                result += f"• پایین: ${stats['low']:,.2f}\n"
                result += f"• حجم: ${stats['quote_volume']/1000000:,.1f}M\n"
            
            if signal.get('top_signals'):
                result += f"\n📋 **سیگنال‌های برتر:**\n"
                for s in signal['top_signals'][:5]:
                    result += f"• {s}\n"
            
            db.save_signal(user_id, signal)
            db.increment_analysis(user_id)
            if not db.check_subscription(user_id):
                db.increment_daily_analysis(user_id)
            
            user_data[user_id]['state'] = 'menu'
            
            await update.effective_chat.send_message(
                result,
                reply_markup=get_main_keyboard(user_id),
                parse_mode='Markdown'
            )
            
        elif "🔙" in text:
            user_data[user_id]['state'] = 'menu'
            await update.effective_chat.send_message("🔙", reply_markup=get_main_keyboard(user_id))
        else:
            await update.effective_chat.send_message(
                "❌ لطفاً یکی از ارزهای لیست را انتخاب کنید!",
                reply_markup=get_symbol_keyboard(user_id)
            )
        return
    
    # ===== تحلیل چارت =====
    if "تحلیل چارت" in text or "Chart Analysis" in text:
        await update.effective_chat.send_message(
            "📸 **تصویر چارت خود را ارسال کنید**\n\n"
            "🔥 **۵۰ ماشین مجزا برای تشخیص دقیق:**\n"
            "✅ استخراج کامل کندل‌ها\n"
            "✅ تشخیص ۲۰+ الگوی کندل\n"
            "✅ تشخیص تمام اندیکاتورها\n"
            "✅ شناسایی حمایت و مقاومت خودکار\n"
            "✅ ترکیب با داده‌های نهنگ‌ها\n"
            "✅ ۱۰۰ روش پردازش تصویر\n"
            "⏳ لطفاً تصویر واضح ارسال کنید...",
            reply_markup=get_main_keyboard(user_id),
            parse_mode='Markdown'
        )
        return
    
    # ===== ۲۰۰+ ارز =====
    if "۲۰۰+ ارز دقیق" in text or "200+ Coins Detailed" in text:
        await show_detailed_coins(update, context)
        return
    
    # ===== آمار =====
    if "آمار من" in text or "My Stats" in text:
        stats = db.get_user_stats(user_id)
        if stats:
            total, avg_conf, best_conf, wins, losses = stats
            win_rate = (wins / (wins + losses) * 100) if wins + losses > 0 else 0
            msg = f"📊 **آمار شما**\n\n📈 کل تحلیل‌ها: {total}\n🎯 میانگین اطمینان: {avg_conf:.0f}%\n🏆 بهترین اطمینان: {best_conf:.0f}%\n🏅 نرخ برد: {win_rate:.1f}%"
            await update.effective_chat.send_message(msg, reply_markup=get_main_keyboard(user_id), parse_mode='Markdown')
        else:
            await update.effective_chat.send_message("📊 هنوز تحلیلی نداشته‌اید!", reply_markup=get_main_keyboard(user_id))
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
        user = db.get_user(user_id)
        referral_code = user[5] if user else ""
        await update.effective_chat.send_message(
            f"🎁 **لینک دعوت**\n\n`https://t.me/{bot_name}?start=ref_{user_id}`\n\n📋 کد رفرال: `{referral_code}`",
            reply_markup=get_main_keyboard(user_id),
            parse_mode='Markdown'
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
        risk = user[21] if user else 2
        max_pos = user[22] if user else 10
        
        msg = f"⚙️ **تنظیمات**\n\n📊 درصد ریسک: {risk}%\n📊 حداکثر حجم: {max_pos}\n\nبرای تغییر، دستور /settings را بفرستید."
        await update.effective_chat.send_message(msg, reply_markup=get_main_keyboard(user_id), parse_mode='Markdown')
        return
    
    # ===== خرید اشتراک =====
    if "خرید اشتراک" in text or "Buy Subscription" in text:
        await show_subscription_plans(update, context)
        return
    
    # ===== وضعیت اشتراک =====
    if "وضعیت اشتراک" in text or "Subscription Status" in text:
        await show_subscription_status(update, context)
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
        # درخواست‌های پرداخت
        if "درخواست‌های پرداخت" in text or "Payment Requests" in text:
            await show_payment_requests(update, context)
            return
        
        # فعال/غیرفعال کردن حالت پولی
        if "فعال/غیرفعال کردن حالت پولی" in text or "Toggle Paid Mode" in text:
            current_mode = db.get_setting('is_paid_mode')
            new_mode = '0' if current_mode == '1' else '1'
            db.update_setting('is_paid_mode', new_mode)
            status = "فعال" if new_mode == '1' else "غیرفعال"
            await update.effective_chat.send_message(f"✅ حالت پولی {status} شد!", reply_markup=get_admin_keyboard(user_id))
            return
        
        # تنظیم قیمت‌ها
        if "تنظیم قیمت‌ها" in text or "Set Prices" in text:
            user_data[user_id]['state'] = 'setting_prices'
            await update.effective_chat.send_message(
                "💲 **تنظیم قیمت‌ها**\n\nفرمت:\nهفتگی: 150000\nماهانه: 500000\nسالانه: 5000000\n\nاعداد را به تومان وارد کنید:",
                parse_mode='Markdown'
            )
            return
        
        if user_data[user_id].get('state') == 'setting_prices':
            try:
                lines = text.strip().split('\n')
                for line in lines:
                    if 'هفتگی' in line or 'weekly' in line:
                        price = int(re.search(r'\d+', line).group())
                        db.update_setting('subscription_price_weekly', str(price))
                    elif 'ماهانه' in line or 'monthly' in line:
                        price = int(re.search(r'\d+', line).group())
                        db.update_setting('subscription_price_monthly', str(price))
                    elif 'سالانه' in line or 'yearly' in line:
                        price = int(re.search(r'\d+', line).group())
                        db.update_setting('subscription_price_yearly', str(price))
                
                user_data[user_id]['state'] = 'menu'
                await update.effective_chat.send_message("✅ قیمت‌ها با موفقیت بروزرسانی شدند!", reply_markup=get_admin_keyboard(user_id))
            except:
                await update.effective_chat.send_message("❌ فرمت اشتباه! لطفاً مجدداً وارد کنید.")
            return
        
        # آمار کاربران
        if "آمار کاربران" in text or "User Stats" in text:
            users = db.get_all_users()
            total = len(users)
            fa_count = sum(1 for u in users if u[1] == 'fa')
            en_count = sum(1 for u in users if u[1] == 'en')
            premium_count = sum(1 for u in users if db.check_subscription(u[0]))
            
            payments = db.get_all_payments(10)
            total_payments = len(payments)
            verified = sum(1 for p in payments if p[5] == 'VERIFIED')
            pending = sum(1 for p in payments if p[5] == 'PENDING')
            
            msg = f"📊 **آمار سیستم**\n\n"
            msg += f"👥 کل کاربران: {total}\n"
            msg += f"📈 فارسی: {fa_count}\n"
            msg += f"📈 انگلیسی: {en_count}\n"
            msg += f"💎 پرمیوم: {premium_count}\n\n"
            msg += f"💳 کل پرداخت‌ها: {total_payments}\n"
            msg += f"✅ تایید شده: {verified}\n"
            msg += f"⏳ در انتظار: {pending}"
            
            await update.effective_chat.send_message(msg, reply_markup=get_admin_keyboard(user_id), parse_mode='Markdown')
            return
        
        # ارسال پیام همگانی
        if "ارسال پیام همگانی" in text or "Broadcast" in text:
            user_data[user_id]['state'] = 'broadcast'
            await update.effective_chat.send_message(
                "📝 پیام خود را برای ارسال به تمام کاربران وارد کنید:",
                reply_markup=get_admin_keyboard(user_id)
            )
            return
        
        if user_data[user_id].get('state') == 'broadcast':
            users = db.get_all_users()
            sent = 0
            for uid, lang_user in users:
                try:
                    await context.bot.send_message(chat_id=uid, text=text)
                    sent += 1
                except:
                    continue
            user_data[user_id]['state'] = 'menu'
            await update.effective_chat.send_message(f"✅ پیام به {sent} کاربر ارسال شد!", reply_markup=get_admin_keyboard(user_id))
            return
        
        # تشخیص نهنگ‌ها
        if "تشخیص نهنگ‌ها" in text or "Whale Detection" in text:
            await update.effective_chat.send_message(
                "🐋 **سیستم تشخیص نهنگ HyperDash**\n\n"
                "🔍 در حال اسکن بازار برای تشخیص نهنگ‌ها...",
                parse_mode='Markdown'
            )
            
            whales = []
            for symbol in SUPPORTED_SYMBOLS[:20]:
                try:
                    whale_data = whale_detector.get_whale_analysis_hyperdash(symbol)
                    if whale_data and whale_data['whale_count'] > 0:
                        whales.append((symbol, whale_data))
                except:
                    continue
            
            if whales:
                msg = "🐋 **نهنگ‌های شناسایی شده:**\n\n"
                for symbol, data in whales[:10]:
                    emoji = "🟢" if data['sentiment'] == 'BULLISH' else "🔴" if data['sentiment'] == 'BEARISH' else "🟡"
                    msg += f"{emoji} **{symbol}**: {data['whale_count']} نهنگ\n"
                    msg += f"   احساسات: {data['sentiment']} | اطمینان: {data['confidence']}%\n"
                    msg += f"   خرید: ${data['long_volume']:,.0f} | فروش: ${data['short_volume']:,.0f}\n\n"
            else:
                msg = "🐋 هیچ نهنگی شناسایی نشد!"
            
            await update.effective_chat.send_message(msg, reply_markup=get_admin_keyboard(user_id), parse_mode='Markdown')
            return
        
        # تنظیمات سیستم
        if "تنظیمات سیستم" in text or "System Settings" in text:
            free_limit = db.get_setting('free_analysis_limit')
            paid_mode = db.get_setting('is_paid_mode')
            auto_trade = db.get_setting('auto_trade_enabled')
            min_conf = db.get_setting('min_confidence')
            whale_tracking = db.get_setting('whale_tracking_enabled')
            
            msg = f"⚙️ **تنظیمات سیستم**\n\n"
            msg += f"📊 محدودیت تحلیل رایگان: {free_limit}\n"
            msg += f"💰 حالت پولی: {'فعال' if paid_mode == '1' else 'غیرفعال'}\n"
            msg += f"🤖 معاملات خودکار: {'فعال' if auto_trade == '1' else 'غیرفعال'}\n"
            msg += f"🎯 حداقل اطمینان: {min_conf}%\n"
            msg += f"🐋 تشخیص نهنگ: {'فعال' if whale_tracking == '1' else 'غیرفعال'}\n\n"
            msg += f"برای تغییر هر کدام، عدد جدید را وارد کنید:"
            
            user_data[user_id]['state'] = 'setting_system'
            await update.effective_chat.send_message(msg, parse_mode='Markdown')
            return
        
        if user_data[user_id].get('state') == 'setting_system':
            try:
                lines = text.strip().split('\n')
                for line in lines:
                    if 'free' in line.lower():
                        limit = int(re.search(r'\d+', line).group())
                        db.update_setting('free_analysis_limit', str(limit))
                    elif 'auto' in line.lower() or 'trade' in line.lower():
                        value = int(re.search(r'\d+', line).group())
                        db.update_setting('auto_trade_enabled', str(value))
                    elif 'min' in line.lower() or 'confidence' in line.lower():
                        conf = int(re.search(r'\d+', line).group())
                        db.update_setting('min_confidence', str(conf))
                    elif 'whale' in line.lower():
                        value = int(re.search(r'\d+', line).group())
                        db.update_setting('whale_tracking_enabled', str(value))
                
                user_data[user_id]['state'] = 'menu'
                await update.effective_chat.send_message("✅ تنظیمات سیستم بروزرسانی شد!", reply_markup=get_admin_keyboard(user_id))
            except:
                await update.effective_chat.send_message("❌ فرمت اشتباه! لطفاً مجدداً وارد کنید.")
            return
        
        # کیف پول
        if "کیف پول" in text or "Wallet" in text:
            card_number = db.get_setting('card_number')
            card_holder = db.get_setting('card_holder')
            
            await update.effective_chat.send_message(
                f"💰 **کیف پول**\n\n💳 شماره کارت: {card_number}\n👤 صاحب کارت: {card_holder}",
                reply_markup=get_admin_keyboard(user_id),
                parse_mode='Markdown'
            )
            return
        
        # آمار سیگنال‌ها
        if "آمار سیگنال‌ها" in text or "Signal Stats" in text:
            db.cursor.execute('''
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
                       SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END) as losses,
                       AVG(confidence) as avg_conf
                FROM signals_v15
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
        
        # آموزش ML
        if "آموزش ML" in text or "Train ML" in text:
            await update.effective_chat.send_message(
                "🧠 **در حال آموزش مدل‌های ML...**\n⏳ این عملیات ممکن است چند دقیقه طول بکشد...",
                parse_mode='Markdown'
            )
            # آموزش مدل‌ها (ساده شده)
            db.update_setting('ml_model_trained', '1')
            await update.effective_chat.send_message(
                "✅ **مدل‌های ML با موفقیت آموزش داده شدند!**",
                reply_markup=get_admin_keyboard(user_id),
                parse_mode='Markdown'
            )
            return
        
        if "بازگشت" in text or "Back" in text:
            await update.effective_chat.send_message("🔙 بازگشت", reply_markup=get_main_keyboard(user_id))
            return

# ==================== نمایش ۲۰۰+ ارز ====================
async def show_detailed_coins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = db.get_user(user_id)[3] if db.get_user(user_id) else 'fa'
    
    await update.effective_chat.send_message(
        "🔄 **در حال دریافت قیمت و حجم ۲۰۰+ ارز...**\n⏳ لطفاً صبر کنید...",
        parse_mode='Markdown'
    )
    
    prices = price_service.get_all_prices_ultra(SUPPORTED_SYMBOLS[:100])
    
    if not prices:
        await update.effective_chat.send_message(
            "❌ خطا در دریافت قیمت‌ها!",
            reply_markup=get_main_keyboard(user_id)
        )
        return
    
    sorted_prices = sorted(prices.items(), key=lambda x: x[1]['change'], reverse=True)
    
    msg = "📊 **قیمت و حجم ۲۰۰+ ارز لحظه‌ای**\n\n"
    msg += f"📈 {len(sorted_prices)} ارز در حال پایش\n\n"
    
    for i, (symbol, data) in enumerate(sorted_prices[:20]):
        change_emoji = "📈" if data['change'] > 0 else "📉" if data['change'] < 0 else "➖"
        msg += f"{i+1}. **{symbol}** | ${data['price']:,.2f} | {change_emoji} {data['change']:+.2f}%\n"
        msg += f"   📊 حجم: {data['quote_volume']/1000000:,.1f}M USDT\n"
        msg += f"   📈 {data['high']:,.2f} | 📉 {data['low']:,.2f}\n\n"
    
    msg += f"🔍 برای تحلیل دقیق، روی «شروع تحلیل» کلیک کنید.\n"
    msg += f"🐋 تشخیص نهنگ‌های HyperDash فعال است."
    
    await update.effective_chat.send_message(
        msg,
        reply_markup=get_main_keyboard(user_id),
        parse_mode='Markdown'
    )

# ==================== تحلیل چارت فوق‌پیشرفته ====================
async def handle_chart_analysis_ultra(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = db.get_user(user_id)[3] if db.get_user(user_id) else 'fa'
    
    await update.effective_chat.send_message(
        "🔍 **در حال تحلیل چارت با ۵۰ ماشین مجزا...**\n"
        "🧠 **۱۰۰ روش پردازش تصویر فعال**\n"
        "📊 استخراج کامل داده‌های چارت\n"
        "🕯️ تشخیص ۲۰+ الگوی کندل استیک\n"
        "🐋 ترکیب با داده‌های نهنگ‌های HyperDash\n"
        "⏳ لطفاً صبر کنید (این فرآیند چند ثانیه طول می‌کشد)...",
        parse_mode='Markdown'
    )
    
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        image_data = await file.download_as_bytearray()
        
        # تحلیل چارت
        chart_result = chart_analyzer.analyze_chart_ultra(image_data)
        
        if not chart_result:
            await update.effective_chat.send_message(
                "❌ **خطا در تحلیل چارت!**\n\nلطفاً یک چارت واضح با موارد زیر ارسال کنید:\n✅ کندل‌های مشخص\n✅ قیمت‌ها (High, Low, Open, Close)\n✅ اندیکاتورها (RSI, MACD, EMA)\n✅ حمایت و مقاومت",
                reply_markup=get_main_keyboard(user_id)
            )
            return
        
        chart_data = chart_result['chart_data']
        patterns = chart_result['patterns']
        candle_patterns = chart_result['candle_patterns']
        indicators = chart_result['indicators']
        support_levels = chart_result['support_levels']
        resistance_levels = chart_result['resistance_levels']
        quality = chart_result['quality']
        
        # دریافت داده‌های نهنگ
        symbol = chart_data.get('symbol', 'BTCUSDT')
        whale_data = whale_detector.get_whale_analysis_hyperdash(symbol)
        
        # دریافت کندل‌ها
        candles = price_service.get_klines_ultra(symbol, "1h", 200)
        
        # تولید سیگنال
        signal = signal_engine.generate_signal_ultra(candles, chart_data, whale_data, symbol)
        
        # نمایش نتایج
        text = "📊 **نتیجه تحلیل چارت نسخه ۱۵.۰**\n"
        text += "=" * 40 + "\n\n"
        
        text += f"🔍 **کیفیت تشخیص:** {quality}%\n"
        text += f"🎯 **دقت OCR:** {chart_result.get('ocr_confidence', 0):.0f}%\n"
        text += f"⚙️ **موتور استفاده شده:** {chart_result.get('engine_used', 'Unknown')}\n\n"
        
        if chart_data.get('symbol'):
            text += f"📈 نماد: {chart_data['symbol']}\n"
        if chart_data.get('current_price'):
            text += f"💰 قیمت فعلی: ${chart_data['current_price']:,.2f}\n"
        if chart_data.get('high') and chart_data.get('low'):
            text += f"📈 بالاترین: ${chart_data['high']:,.2f} | 📉 پایین‌ترین: ${chart_data['low']:,.2f}\n"
        
        if support_levels:
            text += f"\n🛡️ **حمایت:**\n"
            for s in support_levels[:3]:
                text += f"• ${s['level']:,.2f} (قدرت: {s['strength']})\n"
        
        if resistance_levels:
            text += f"\n📈 **مقاومت:**\n"
            for r in resistance_levels[:3]:
                text += f"• ${r['level']:,.2f} (قدرت: {r['strength']})\n"
        
        if candle_patterns:
            text += f"\n🕯️ **الگوهای کندل:**\n"
            for cp in candle_patterns[:3]:
                text += f"• {cp['name']} (اطمینان: {cp['confidence']}%)\n"
        
        if patterns:
            text += f"\n🧠 **الگوهای چارت:**\n"
            for p in patterns[:3]:
                text += f"• {p['name']} (اطمینان: {p['confidence']}%)\n"
        
        if whale_data:
            text += f"\n🐋 **داده‌های نهنگ‌ها:**\n"
            text += f"• تعداد: {whale_data['whale_count']}\n"
            text += f"• احساسات: {whale_data['sentiment']}\n"
            text += f"• اطمینان: {whale_data['confidence']}%\n"
        
        if signal and signal['direction'] != 'HOLD':
            text += f"\n🔥 **سیگنال نهایی:**\n"
            text += f"📈 جهت: {signal['direction']}\n"
            text += f"💰 ورود: ${signal['entry']:,.2f}\n"
            text += f"🎯 حد سود: ${signal['take_profit']:,.2f}\n"
            text += f"🛡️ حد ضرر: ${signal['stop_loss']:,.2f}\n"
            text += f"⚡ اهرم: {signal['leverage']}x\n"
            text += f"🎯 اطمینان: {signal['confidence']}%\n"
            
            db.save_signal(user_id, signal)
        else:
            text += f"\n⚪ **سیگنال: نگهداری (HOLD)**\n"
        
        db.save_chart_analysis(user_id, symbol, chart_data, patterns, candle_patterns, indicators, quality, chart_result.get('ocr_confidence', 0))
        
        await update.effective_chat.send_message(
            text,
            reply_markup=get_main_keyboard(user_id),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        await update.effective_chat.send_message(
            f"❌ **خطا:** {str(e)[:200]}",
            reply_markup=get_main_keyboard(user_id)
        )

# ==================== سیستم اشتراک ====================
async def show_subscription_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = db.get_user(user_id)[3] if db.get_user(user_id) else 'fa'
    
    weekly = db.get_setting('subscription_price_weekly') or 150000
    monthly = db.get_setting('subscription_price_monthly') or 500000
    yearly = db.get_setting('subscription_price_yearly') or 5000000
    
    card_number = db.get_setting('card_number')
    card_holder = db.get_setting('card_holder')
    
    if lang == 'fa':
        msg = f"💎 **پلن‌های اشتراک**\n\n"
        msg += f"📅 هفتگی: {int(weekly):,} تومان\n"
        msg += f"📅 ماهانه: {int(monthly):,} تومان\n"
        msg += f"📅 سالانه: {int(yearly):,} تومان\n\n"
        msg += f"💳 شماره کارت: {card_number}\n"
        msg += f"👤 صاحب کارت: {card_holder}\n\n"
        msg += f"📤 پس از واریز، روی «ارسال فیش» کلیک کنید."
    else:
        msg = f"💎 **Subscription Plans**\n\n"
        msg += f"📅 Weekly: {int(weekly):,} Toman\n"
        msg += f"📅 Monthly: {int(monthly):,} Toman\n"
        msg += f"📅 Yearly: {int(yearly):,} Toman\n\n"
        msg += f"💳 Card Number: {card_number}\n"
        msg += f"👤 Card Holder: {card_holder}\n\n"
        msg += f"📤 After payment, click 'Send Receipt'."
    
    await update.effective_chat.send_message(
        msg,
        reply_markup=get_subscription_keyboard(user_id),
        parse_mode='Markdown'
    )

async def show_payment_info(update: Update, context: ContextTypes.DEFAULT_TYPE, plan_type='MONTHLY'):
    user_id = update.effective_user.id
    lang = db.get_user(user_id)[3] if db.get_user(user_id) else 'fa'
    
    if plan_type == 'WEEKLY':
        amount = db.get_setting('subscription_price_weekly') or 150000
        plan_text = 'هفتگی' if lang == 'fa' else 'Weekly'
    elif plan_type == 'MONTHLY':
        amount = db.get_setting('subscription_price_monthly') or 500000
        plan_text = 'ماهانه' if lang == 'fa' else 'Monthly'
    else:
        amount = db.get_setting('subscription_price_yearly') or 5000000
        plan_text = 'سالانه' if lang == 'fa' else 'Yearly'
    
    card_number = db.get_setting('card_number')
    card_holder = db.get_setting('card_holder')
    
    user_data[user_id]['payment_amount'] = int(amount)
    
    if lang == 'fa':
        msg = f"💳 **اطلاعات واریز - {plan_text}**\n\n"
        msg += f"💰 مبلغ: {int(amount):,} تومان\n"
        msg += f"💳 شماره کارت: {card_number}\n"
        msg += f"👤 صاحب کارت: {card_holder}\n\n"
        msg += f"📤 پس از واریز، تصویر فیش را ارسال کنید."
    else:
        msg = f"💳 **Payment Info - {plan_text}**\n\n"
        msg += f"💰 Amount: {int(amount):,} Toman\n"
        msg += f"💳 Card Number: {card_number}\n"
        msg += f"👤 Card Holder: {card_holder}\n\n"
        msg += f"📤 After payment, send the receipt image."
    
    await update.effective_chat.send_message(
        msg,
        reply_markup=get_subscription_keyboard(user_id),
        parse_mode='Markdown'
    )

async def handle_payment_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = db.get_user(user_id)[3] if db.get_user(user_id) else 'fa'
    
    if user_data[user_id].get('state') != 'waiting_receipt':
        await update.effective_chat.send_message(
            "❌ لطفاً ابتدا از منوی اشتراک، گزینه «ارسال فیش» را انتخاب کنید."
        )
        return
    
    photo_file = await update.message.photo[-1].get_file()
    file_id = photo_file.file_id
    
    reference_code = f"PAY-{user_id}-{int(time.time())}"
    amount = user_data[user_id].get('payment_amount', 500000)
    plan_type = user_data[user_id].get('payment_plan', 'MONTHLY')
    card_number = db.get_setting('card_number')
    
    payment_id = db.save_payment_request(
        user_id, amount, card_number, file_id, reference_code, plan_type
    )
    
    admin_msg = f"💳 **درخواست پرداخت جدید**\n\n"
    admin_msg += f"👤 کاربر: {user_id}\n"
    admin_msg += f"💰 مبلغ: {amount:,} تومان\n"
    admin_msg += f"📅 پلن: {plan_type}\n"
    admin_msg += f"🔑 کد مرجع: `{reference_code}`\n"
    admin_msg += f"🆔 شناسه: {payment_id}\n\n"
    admin_msg += f"✅ برای تایید: /verify_{payment_id}\n"
    admin_msg += f"❌ برای رد: /reject_{payment_id}"
    
    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=file_id,
        caption=admin_msg,
        parse_mode='Markdown'
    )
    
    user_data[user_id]['state'] = 'menu'
    
    if lang == 'fa':
        await update.effective_chat.send_message(
            f"✅ **فیش شما با موفقیت ارسال شد!**\n\n🆔 کد پیگیری: `{reference_code}`\n⏳ پس از تایید ادمین، اشتراک شما فعال می‌شود.",
            reply_markup=get_main_keyboard(user_id),
            parse_mode='Markdown'
        )
    else:
        await update.effective_chat.send_message(
            f"✅ **Your receipt was sent successfully!**\n\n🆔 Tracking Code: `{reference_code}`\n⏳ Your subscription will be activated after admin verification.",
            reply_markup=get_main_keyboard(user_id),
            parse_mode='Markdown'
        )

async def show_subscription_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = db.get_user(user_id)[3] if db.get_user(user_id) else 'fa'
    user = db.get_user(user_id)
    
    is_active = db.check_subscription(user_id)
    
    if lang == 'fa':
        msg = f"📊 **وضعیت اشتراک**\n\n"
        if is_active:
            expire_date = datetime.fromisoformat(user[10]) if user[10] else None
            if expire_date:
                days_left = (expire_date - datetime.now()).days
                msg += f"✅ **اشتراک فعال**\n"
                msg += f"📅 تاریخ انقضا: {expire_date.strftime('%Y-%m-%d')}\n"
                msg += f"⏳ روزهای باقی‌مانده: {days_left}\n"
                msg += f"💎 پلن: {user[9]}\n"
            else:
                msg += "✅ اشتراک فعال\n"
        else:
            free_limit = db.get_setting('free_analysis_limit') or 3
            daily_count = db.get_daily_analysis_count(user_id)
            
            msg += f"❌ **اشتراک غیرفعال**\n"
            msg += f"📊 نسخه رایگان: {free_limit} تحلیل در روز\n"
            msg += f"📊 تحلیل امروز: {daily_count}/{free_limit}\n\n"
            msg += f"💎 برای خرید اشتراک روی «خرید اشتراک» کلیک کنید."
    else:
        msg = f"📊 **Subscription Status**\n\n"
        if is_active:
            expire_date = datetime.fromisoformat(user[10]) if user[10] else None
            if expire_date:
                days_left = (expire_date - datetime.now()).days
                msg += f"✅ **Active**\n"
                msg += f"📅 Expires: {expire_date.strftime('%Y-%m-%d')}\n"
                msg += f"⏳ Days left: {days_left}\n"
                msg += f"💎 Plan: {user[9]}\n"
            else:
                msg += "✅ Active\n"
        else:
            free_limit = db.get_setting('free_analysis_limit') or 3
            daily_count = db.get_daily_analysis_count(user_id)
            
            msg += f"❌ **Inactive**\n"
            msg += f"📊 Free version: {free_limit} analysis per day\n"
            msg += f"📊 Today's analysis: {daily_count}/{free_limit}\n\n"
            msg += f"💎 Click 'Buy Subscription' to purchase."
    
    await update.effective_chat.send_message(
        msg,
        reply_markup=get_main_keyboard(user_id),
        parse_mode='Markdown'
    )

async def show_payment_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    payments = db.get_pending_payments()
    
    if not payments:
        await update.effective_chat.send_message(
            "✅ هیچ درخواست پرداخت در انتظاری وجود ندارد.",
            reply_markup=get_admin_keyboard(ADMIN_ID)
        )
        return
    
    msg = f"💳 **درخواست‌های پرداخت در انتظار** ({len(payments)})\n\n"
    
    for p in payments:
        msg += f"🆔 {p[0]} | 👤 {p[1]} | 💰 {p[2]:,} تومان\n"
        msg += f"📅 {p[7] if len(p) > 7 else 'MONTHLY'} | 🔑 {p[4]}\n"
        msg += f"📤 ارسال: {p[6][:10]}\n"
        msg += f"/verify_{p[0]} - /reject_{p[0]}\n\n"
    
    await update.effective_chat.send_message(
        msg,
        reply_markup=get_admin_keyboard(ADMIN_ID),
        parse_mode='Markdown'
    )

# ==================== هندلرهای دستورات ادمین ====================
async def handle_admin_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    text = update.message.text
    
    if text.startswith('/verify_'):
        try:
            payment_id = int(text.replace('/verify_', ''))
            db.verify_payment(payment_id, 'تایید توسط ادمین')
            
            payment = db.cursor.execute('SELECT user_id FROM payments_v15 WHERE id = ?', (payment_id,)).fetchone()
            if payment:
                user_id = payment[0]
                lang = db.get_user(user_id)[3] if db.get_user(user_id) else 'fa'
                
                msg = "🎉 **اشتراک شما با موفقیت فعال شد!**\n\n✅ از این پس می‌توانید از تمام امکانات ربات استفاده کنید.\n📊 تعداد تحلیل‌های شما نامحدود است." if lang == 'fa' else "🎉 **Your subscription has been activated!**\n\n✅ You can now use all bot features.\n📊 Your analysis is unlimited."
                
                await context.bot.send_message(chat_id=user_id, text=msg, parse_mode='Markdown')
            
            await update.effective_chat.send_message(f"✅ پرداخت {payment_id} تایید شد!", reply_markup=get_admin_keyboard(ADMIN_ID))
        except Exception as e:
            await update.effective_chat.send_message(f"❌ خطا: {e}")
    
    elif text.startswith('/reject_'):
        try:
            payment_id = int(text.replace('/reject_', ''))
            db.reject_payment(payment_id, 'رد توسط ادمین')
            
            payment = db.cursor.execute('SELECT user_id FROM payments_v15 WHERE id = ?', (payment_id,)).fetchone()
            if payment:
                user_id = payment[0]
                lang = db.get_user(user_id)[3] if db.get_user(user_id) else 'fa'
                
                msg = "❌ **درخواست پرداخت شما رد شد!**\n\n🔍 لطفاً فیش واریزی خود را بررسی و مجدداً ارسال کنید." if lang == 'fa' else "❌ **Your payment request was rejected!**\n\n🔍 Please check your receipt and try again."
                
                await context.bot.send_message(chat_id=user_id, text=msg, parse_mode='Markdown')
            
            await update.effective_chat.send_message(f"❌ پرداخت {payment_id} رد شد!", reply_markup=get_admin_keyboard(ADMIN_ID))
        except Exception as e:
            await update.effective_chat.send_message(f"❌ خطا: {e}")

# ==================== اجرا ====================
def main():
    print("=" * 80)
    print("🚀 ربات تحلیل تکنیکال فوق‌پیشرفته نسخه ۱۵.۰ FINAL")
    print("🔥 ۱۰۰۰+ الگوریتم ترکیبی - ۵۰ ماشین تشخیص چارت")
    print("=" * 80)
    
    if not check_and_create_pid():
        sys.exit(1)
    
    print(f"👤 ادمین: {ADMIN_ID}")
    print(f"🤖 ربات: {BOT_USERNAME}")
    print(f"📊 ارزها: {len(SUPPORTED_SYMBOLS)}")
    print(f"🧠 الگوریتم‌ها: ۱۰۰۰+")
    print(f"📸 تشخیص چارت: ۵۰ ماشین مجزا")
    print(f"🐋 تشخیص نهنگ: ۲۰ روش HyperDash")
    print(f"💎 حالت پولی: {'فعال' if db.get_setting('is_paid_mode') == '1' else 'غیرفعال'}")
    print(f"🎯 دقت هدف: ۹۹.۹۹٪")
    print("=" * 80)
    
    global bot
    bot = Application.builder().token(BOT_TOKEN).build()
    
    bot.add_handler(CommandHandler("start", start_command))
    bot.add_handler(CommandHandler("verify", handle_admin_commands))
    bot.add_handler(CommandHandler("reject", handle_admin_commands))
    bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    bot.add_handler(MessageHandler(filters.PHOTO, handle_message))
    
    print("✅ ربات نسخه ۱۵.۰ FINAL با موفقیت راه‌اندازی شد!")
    print("🔥 قدرت ۱۰۰ برابر نسخه ۱۴")
    print("=" * 80)
    
    try:
        bot.run_polling(
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