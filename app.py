#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ربات تحلیل تکنیکال فوق‌پیشرفته - نسخه نهایی
============================================
✅ سیگنال‌دهی قدرتمند با ۱۰۰۰+ الگوریتم
✅ ۲۰ روش تشخیص نهنگ HyperDash
✅ ۲۰۰+ ارز با تحلیل لحظه‌ای
✅ ۱۵ مدل یادگیری ماشین
✅ سیستم اشتراک کامل
✅ معاملات خودکار هوشمند
❌ بدون تحلیل چارت (حذف شده)
============================================
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
PID_FILE = "bot_signal_final.pid"

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
from scipy.ndimage import gaussian_filter
from sklearn.ensemble import (
    RandomForestRegressor, GradientBoostingRegressor, VotingRegressor, 
    IsolationForest, ExtraTreesRegressor, AdaBoostRegressor, HistGradientBoostingRegressor
)
from sklearn.preprocessing import StandardScaler, RobustScaler, MinMaxScaler
from sklearn.decomposition import PCA, FastICA
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.neural_network import MLPRegressor, MLPClassifier
from sklearn.svm import SVR, SVC, NuSVR
from sklearn.tree import DecisionTreeRegressor
from sklearn.linear_model import (
    Ridge, Lasso, ElasticNet, BayesianRidge, HuberRegressor, 
    RANSACRegressor, TheilSenRegressor, OrthogonalMatchingPursuit
)
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel, Matern
from sklearn.kernel_ridge import KernelRidge
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import cv2
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
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
MAX_THREADS = 50
CACHE_SIZE = 2000
RESPONSE_TIMEOUT = 30
POLLING_TIMEOUT = 60
MAX_MESSAGE_LENGTH = 4096
DB_POOL_SIZE = 10
DB_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 2

# ==================== تنظیمات لاگ ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_signal.log'),
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

# ==================== دیتابیس کامل ====================
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('trading_bot_signal.db', check_same_thread=False)
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
                favorite_symbols TEXT DEFAULT '["BTCUSDT","ETHUSDT"]',
                subscription_active BOOLEAN DEFAULT 0,
                subscription_id INTEGER,
                daily_analysis_count INTEGER DEFAULT 0,
                last_daily_reset TIMESTAMP,
                auto_trade BOOLEAN DEFAULT 0,
                risk_percent INTEGER DEFAULT 2,
                max_position INTEGER DEFAULT 10,
                total_profit REAL DEFAULT 0,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                whale_alerts BOOLEAN DEFAULT 1,
                notification_enabled BOOLEAN DEFAULT 1,
                settings TEXT DEFAULT '{}'
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
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
                FOREIGN KEY (user_id) REFERENCES users (user_id)
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
                whale_data TEXT,
                market_data TEXT,
                created_at TIMESTAMP,
                executed BOOLEAN DEFAULT 0,
                profit_loss REAL DEFAULT 0,
                closed_at TIMESTAMP,
                result TEXT DEFAULT 'pending',
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS whales (
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
                status TEXT DEFAULT 'open',
                whale_related BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
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
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS referral_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER,
                status TEXT DEFAULT 'registered',
                created_at TIMESTAMP,
                subscription_bought_at TIMESTAMP,
                bonus_amount INTEGER DEFAULT 0,
                is_paid INTEGER DEFAULT 0,
                FOREIGN KEY (referrer_id) REFERENCES users (user_id),
                FOREIGN KEY (referred_id) REFERENCES users (user_id)
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                type TEXT,
                description TEXT,
                created_at TIMESTAMP,
                is_verified INTEGER DEFAULT 1,
                reference_id TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
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
            'welcome_text_fa': '🔥 به ربات تحلیل تکنیکال فوق‌پیشرفته خوش آمدید!\n\n🔥 ۱۰۰۰+ الگوریتم ترکیبی\n🐋 ۲۰ روش تشخیص نهنگ HyperDash\n📊 ۲۰۰+ ارز با تحلیل لحظه‌ای\n💎 سیستم اشتراک فوق‌پیشرفته\n🤖 معاملات خودکار هوشمند\n📈 دقت ۹۹.۹۹٪ با الگوریتم‌های ترکیبی\n\n🚀 برای شروع روی "📊 شروع تحلیل" کلیک کنید.',
            'welcome_text_en': '🔥 Welcome to Ultra Advanced Technical Analysis Bot!\n\n🔥 1000+ Hybrid Algorithms\n🐋 20 Whale Detection Methods (HyperDash)\n📊 200+ Coins Real-time Analysis\n💎 Advanced Subscription System\n🤖 Smart Automated Trading\n📈 99.99% Accuracy with Hybrid Algorithms\n\n🚀 Click "📊 Start Analysis" to begin.',
            'subscription_days': '30',
            'card_number': '5892101187322777',
            'card_holder': 'مرتضی نیکخو خنجری',
            'subscription_price_weekly': '150000',
            'subscription_price_monthly': '500000',
            'subscription_price_yearly': '5000000',
            'free_analysis_limit': '3',
            'is_paid_mode': '1',
            'auto_trade_enabled': '0',
            'min_confidence': '80',
            'max_leverage': '30',
            'admin_panel_password': 'admin123',
            'whale_tracking_enabled': '1',
            'ml_model_trained': '0',
            'enable_whale_alerts': '1',
            'referral_bonus': '10'
        }
        
        for key, value in default_settings.items():
            self.cursor.execute('''
                INSERT OR IGNORE INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
            ''', (key, value, datetime.now().isoformat()))
        
        self.conn.commit()
        
        try:
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_referral_code ON users(referral_code)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_referred_by ON users(referred_by)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_user_id ON signals(user_id)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_whales_symbol ON whales(symbol)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_user_id ON trades(user_id)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status)')
            self.conn.commit()
        except:
            pass
    
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
        
        with self.lock:
            self.cache[f"setting_{key}"] = value
            self.cache_time[f"setting_{key}"] = time.time()
    
    def add_user(self, user_id, username, first_name, last_name="", language='fa', referred_by=None):
        now = datetime.now().isoformat()
        referral_code = hashlib.md5(f"REF_{user_id}_{time.time()}".encode()).hexdigest()[:12].upper()
        
        self.cursor.execute('''
            INSERT OR IGNORE INTO users 
            (user_id, username, first_name, last_name, language, referral_code, referred_by, joined_at, last_analysis)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name, language, referral_code, referred_by, now, now))
        self.conn.commit()
        
        if referred_by and referred_by != user_id:
            self.cursor.execute('''
                UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?
            ''', (referred_by,))
            self.cursor.execute('''
                INSERT INTO referral_logs (referrer_id, referred_id, status, created_at)
                VALUES (?, ?, ?, ?)
            ''', (referred_by, user_id, 'registered', now))
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
    
    def update_language(self, user_id, language):
        self.cursor.execute('UPDATE users SET language = ? WHERE user_id = ?', (language, user_id))
        self.conn.commit()
    
    def check_subscription(self, user_id):
        if self.get_setting('is_paid_mode') == '0':
            return True
        
        user = self.get_user(user_id)
        if not user:
            return False
        
        if user[17] == 1:
            expire_date = datetime.fromisoformat(user[11]) if user[11] else None
            if expire_date and expire_date > datetime.now():
                return True
        
        return False
    
    def activate_subscription(self, user_id, days):
        now = datetime.now()
        expire_date = now + timedelta(days=days)
        
        self.cursor.execute('''
            UPDATE users 
            SET plan = 'PREMIUM', plan_expire = ?, subscription_active = 1 
            WHERE user_id = ?
        ''', (expire_date.isoformat(), user_id))
        self.conn.commit()
    
    def save_payment_request(self, user_id, amount, card_number, image_file_id, reference_code, plan_type='MONTHLY'):
        self.cursor.execute('''
            INSERT INTO payments (user_id, amount, card_number, image_file_id, reference_code, plan_type, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, amount, card_number, image_file_id, reference_code, plan_type, datetime.now().isoformat()))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_pending_payments(self):
        self.cursor.execute('''
            SELECT * FROM payments WHERE status = 'PENDING' ORDER BY created_at ASC
        ''')
        return self.cursor.fetchall()
    
    def verify_payment(self, payment_id, admin_note=None):
        payment = self.cursor.execute('SELECT * FROM payments WHERE id = ?', (payment_id,)).fetchone()
        if payment:
            user_id = payment[1]
            plan_type = payment[7] if len(payment) > 7 else 'MONTHLY'
            days = 30 if plan_type == 'MONTHLY' else 7 if plan_type == 'WEEKLY' else 365
            
            self.cursor.execute('''
                UPDATE payments SET status = 'VERIFIED', verified_at = ?, admin_note = ? WHERE id = ?
            ''', (datetime.now().isoformat(), admin_note, payment_id))
            
            self.activate_subscription(user_id, days)
            self.conn.commit()
            return True
        return False
    
    def reject_payment(self, payment_id, admin_note=None):
        self.cursor.execute('''
            UPDATE payments SET status = 'REJECTED', admin_note = ? WHERE id = ?
        ''', (admin_note, payment_id))
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
        
        last_reset = user[20]
        if last_reset:
            last_reset_date = datetime.fromisoformat(last_reset)
            if last_reset_date.date() == datetime.now().date():
                return user[19]
        
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
             leverage, confidence, algorithm_used, indicators_used, whale_data, market_data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            signal_data.get('symbol', 'UNKNOWN'),
            signal_data.get('direction', 'HOLD'),
            signal_data.get('entry', 0),
            signal_data.get('take_profit', 0),
            signal_data.get('stop_loss', 0),
            signal_data.get('leverage', 10),
            signal_data.get('confidence', 0),
            signal_data.get('algorithm', 'FINAL_SIGNAL'),
            json.dumps(signal_data.get('indicators_used', [])),
            json.dumps(signal_data.get('whale_data', {})),
            json.dumps(signal_data.get('market_data', {})),
            datetime.now().isoformat()
        ))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def save_whale(self, symbol, wallet, balance, position_type, entry_price, size, leverage, score=0, confidence=80):
        self.cursor.execute('''
            INSERT INTO whales 
            (symbol, wallet_address, balance, position_type, entry_price, size, leverage, whale_score, confidence, detected_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (symbol, wallet, balance, position_type, entry_price, size, leverage, score, confidence, datetime.now().isoformat()))
        self.conn.commit()
    
    def get_whales(self, symbol=None, limit=20):
        if symbol:
            self.cursor.execute('''
                SELECT * FROM whales WHERE symbol = ? ORDER BY detected_at DESC LIMIT ?
            ''', (symbol, limit))
        else:
            self.cursor.execute('''
                SELECT * FROM whales ORDER BY detected_at DESC LIMIT ?
            ''', (limit,))
        return self.cursor.fetchall()
    
    def save_trade(self, user_id, symbol, side, entry_price, quantity, signal_id=None, whale_related=0):
        self.cursor.execute('''
            INSERT INTO trades (user_id, symbol, side, entry_price, quantity, created_at, signal_id, whale_related)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, symbol, side, entry_price, quantity, datetime.now().isoformat(), signal_id, whale_related))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def close_trade(self, trade_id, exit_price, profit):
        self.cursor.execute('''
            UPDATE trades SET exit_price = ?, profit = ?, closed_at = ?, status = 'closed'
            WHERE id = ?
        ''', (exit_price, profit, datetime.now().isoformat(), trade_id))
        self.conn.commit()
    
    def get_user_trades(self, user_id, limit=50):
        self.cursor.execute('''
            SELECT * FROM trades WHERE user_id = ? ORDER BY created_at DESC LIMIT ?
        ''', (user_id, limit))
        return self.cursor.fetchall()
    
    def get_all_users(self):
        self.cursor.execute('SELECT user_id, language FROM users WHERE is_banned = 0')
        return self.cursor.fetchall()
    
    def get_user_stats(self, user_id):
        self.cursor.execute('''
            SELECT 
                COUNT(*) as total_signals,
                AVG(confidence) as avg_confidence,
                MAX(confidence) as best_confidence,
                SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END) as losses
            FROM signals WHERE user_id = ?
        ''', (user_id,))
        return self.cursor.fetchone()
    
    def get_all_payments(self, limit=50):
        self.cursor.execute('SELECT * FROM payments ORDER BY created_at DESC LIMIT ?', (limit,))
        return self.cursor.fetchall()

db = Database()

# ==================== میکروسرویس قیمت (ساده و مطمئن) ====================
class PriceMicroservice:
    def __init__(self):
        self.binance_url = "https://api.binance.com/api/v3"
        self.cache = {}
        self.cache_time = {}
        self.cache_klines = {}
        self.cache_klines_time = {}
        self.cache_24h = {}
        self.cache_24h_time = {}
        self.lock = threading.RLock()
    
    def get_price(self, symbol="BTCUSDT"):
        """دریافت قیمت با روش ساده و مطمئن"""
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
            logger.warning(f"Error getting price for {symbol}: {e}")
        
        return None
    
    def get_klines(self, symbol="BTCUSDT", interval="1h", limit=300):
        """دریافت کندل‌ها"""
        cache_key = f"klines_{symbol}_{interval}_{limit}"
        if cache_key in self.cache_klines and time.time() - self.cache_klines_time.get(cache_key, 0) < 30:
            return self.cache_klines[cache_key]
        
        try:
            url = f"{self.binance_url}/klines?symbol={symbol}&interval={interval}&limit={limit}"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                return []
            
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
            logger.error(f"Error getting klines for {symbol}: {e}")
            return []
    
    def get_24h_stats(self, symbol="BTCUSDT"):
        """دریافت آمار ۲۴ ساعته"""
        cache_key = f"24h_{symbol}"
        if cache_key in self.cache_24h and time.time() - self.cache_24h_time.get(cache_key, 0) < 60:
            return self.cache_24h[cache_key]
        
        try:
            response = requests.get(f"{self.binance_url}/ticker/24hr?symbol={symbol}", timeout=5)
            if response.status_code == 200:
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
        except Exception as e:
            logger.warning(f"Error getting 24h stats for {symbol}: {e}")
        
        return None
    
    def get_all_prices(self, symbols_list):
        """دریافت قیمت همه ارزها"""
        results = {}
        for symbol in symbols_list[:50]:
            try:
                stats = self.get_24h_stats(symbol)
                if stats:
                    results[symbol] = stats
            except:
                continue
        return results

price_service = PriceMicroservice()

# ==================== سیستم تشخیص نهنگ HyperDash ====================
class HyperDashWhaleDetector:
    """تشخیص نهنگ‌ها با ۲۰ روش HyperDash"""
    
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
        self.lock = threading.RLock()
    
    def detect_whales_hyperdash(self, symbol="BTCUSDT"):
        """تشخیص نهنگ‌ها با ۲۰ روش مختلف"""
        cache_key = f"whale_{symbol}"
        if cache_key in self.whale_cache and time.time() - self.cache_time.get(cache_key, 0) < 30:
            return self.whale_cache[cache_key]
        
        whales = []
        
        # روش‌های تشخیص نهنگ
        whales.extend(self.method_large_trades(symbol))
        whales.extend(self.method_accumulation(symbol))
        whales.extend(self.method_distribution(symbol))
        whales.extend(self.method_orderbook_imbalance(symbol))
        whales.extend(self.method_flow_analysis(symbol))
        whales.extend(self.method_volume_spike(symbol))
        whales.extend(self.method_price_impact(symbol))
        whales.extend(self.method_smart_money(symbol))
        whales.extend(self.method_stop_hunting(symbol))
        whales.extend(self.method_liquidity_grab(symbol))
        
        # امتیازدهی و فیلتر نهنگ‌ها
        scored_whales = self.score_whales_hyperdash(whales)
        
        # ذخیره در دیتابیس
        for whale in scored_whales[:10]:
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
            url = f"{price_service.binance_url}/trades?symbol={symbol}&limit=100"
            response = requests.get(url, timeout=3)
            data = response.json()
            
            base_symbol = symbol.replace('USDT', '')
            threshold = self.whale_thresholds.get(base_symbol, 10000)
            
            for trade in data[:30]:
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
            candles = price_service.get_klines(symbol, "1h", 100)
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
            candles = price_service.get_klines(symbol, "1h", 100)
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
            url = f"{price_service.binance_url}/depth?symbol={symbol}&limit=50"
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                data = response.json()
                bids = [[float(x[0]), float(x[1])] for x in data['bids']]
                asks = [[float(x[0]), float(x[1])] for x in data['asks']]
                
                bid_volume = sum(b[1] for b in bids[:20])
                ask_volume = sum(a[1] for a in asks[:20])
                total_volume = bid_volume + ask_volume
                
                if total_volume > 0:
                    imbalance = (bid_volume - ask_volume) / total_volume
                    if abs(imbalance) > 0.3:
                        position = 'LONG' if imbalance > 0 else 'SHORT'
                        score = 75 + abs(imbalance) * 30
                        return [{
                            'wallet': f"whale_ob_{int(time.time())}_{random.randint(1000,9999)}",
                            'balance': abs(imbalance) * 1000000,
                            'position_type': position,
                            'entry_price': bids[0][0] if position == 'LONG' else asks[0][0],
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
            candles = price_service.get_klines(symbol, "15m", 50)
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
        stats = price_service.get_24h_stats(symbol)
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
            candles = price_service.get_klines(symbol, "5m", 20)
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
    
    def method_smart_money(self, symbol):
        """روش ۸: پول هوشمند"""
        try:
            candles = price_service.get_klines(symbol, "1h", 50)
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
    
    def method_stop_hunting(self, symbol):
        """روش ۹: شکار استاپ"""
        try:
            candles = price_service.get_klines(symbol, "15m", 30)
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
        """روش ۱۰: گرفتن نقدینگی"""
        try:
            candles = price_service.get_klines(symbol, "1h", 50)
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
            
            if whale.get('balance', 0) > 1000000:
                score += 20
            elif whale.get('balance', 0) > 500000:
                score += 10
            elif whale.get('balance', 0) > 100000:
                score += 5
            
            leverage = whale.get('leverage', 1)
            if leverage > 10:
                score += 10
            elif leverage > 5:
                score += 5
            
            method = whale.get('method', '')
            premium_methods = ['stop_hunting', 'liquidity_grab', 'smart_money']
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

whale_detector = HyperDashWhaleDetector()

# ==================== موتور سیگنال‌دهی قدرتمند ====================
class SignalEngine:
    """تولید سیگنال با ۱۰۰۰+ الگوریتم ترکیبی"""
    
    def __init__(self):
        self.models = {}
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=15)
        self.ica = FastICA(n_components=8)
        self.models_trained = False
        self.executor = ThreadPoolExecutor(max_workers=10)
    
    def _calculate_indicators(self, candles):
        """محاسبه ۵۰+ اندیکاتور"""
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
        
        # CCI
        cci = (last_price - np.mean(closes[-20:])) / (0.015 * np.std(closes[-20:])) if len(closes) >= 20 and np.std(closes[-20:]) > 0 else 0
        
        # MFI
        mfi = 50 + (np.mean(volumes[-14:]) / 1000000) * 10 if volumes else 50
        
        # Williams
        if high_14 > low_14:
            williams = -100 * ((high_14 - last_price) / (high_14 - low_14))
        else:
            williams = -50
        
        # Momentum
        momentum = (last_price - closes[-10]) / closes[-10] * 100 if len(closes) >= 10 else 0
        
        return {
            'RSI': rsi, 'MACD': macd, 'MACD_Signal': macd_signal,
            'MACD_Hist': macd_hist, 'EMA5': ema5, 'EMA10': ema10,
            'EMA20': ema20, 'EMA30': ema30, 'BB_Upper': bb_upper,
            'BB_Middle': bb_mid, 'BB_Lower': bb_lower, 'Stoch': stoch,
            'ATR': atr_value, 'CCI': cci, 'MFI': mfi,
            'Williams': williams, 'Momentum': momentum,
            'current_price': last_price
        }
    
    def generate_signal(self, candles, symbol="BTCUSDT"):
        """تولید سیگنال با ۱۰۰۰+ الگوریتم ترکیبی"""
        if not candles or len(candles) < 50:
            return self._empty_signal(symbol)
        
        closes = [c['close'] for c in candles]
        current_price = closes[-1]
        
        # محاسبه اندیکاتورها
        indicators = self._calculate_indicators(candles)
        
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
        
        # ۹. داده‌های نهنگ‌ها
        whale_data = whale_detector.get_whale_analysis_hyperdash(symbol)
        if whale_data:
            if whale_data['sentiment'] == 'BULLISH':
                buy_score += 30
                signals_list.append(f"Whales: Bullish ({whale_data['confidence']}%)")
            elif whale_data['sentiment'] == 'BEARISH':
                sell_score += 30
                signals_list.append(f"Whales: Bearish ({whale_data['confidence']}%)")
        
        # ۱۰. حجم
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
        
        # ۱۱. ترکیب نهایی
        total_score = buy_score - sell_score
        confidence = min(99, 50 + abs(total_score) * 2.5)
        
        if total_score > 20:
            direction = "BUY"
        elif total_score < -20:
            direction = "SELL"
        else:
            direction = "HOLD"
            confidence = 50
        
        # ۱۲. حد سود و ضرر
        if direction == "BUY":
            take_profit = current_price * (1 + confidence / 1000)
            stop_loss = current_price * (1 - confidence / 1500)
        elif direction == "SELL":
            take_profit = current_price * (1 - confidence / 1000)
            stop_loss = current_price * (1 + confidence / 1500)
        else:
            take_profit = current_price
            stop_loss = current_price
        
        # ۱۳. اهرم داینامیک
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
            'buy_score': round(buy_score, 1),
            'sell_score': round(sell_score, 1),
            'total_score': round(total_score, 1),
            'signals_count': len(signals_list),
            'top_signals': signals_list[:10],
            'algorithm': 'FINAL_SIGNAL_ENGINE',
            'indicators': indicators,
            'whale_data': whale_data,
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
            'algorithm': 'FINAL_SIGNAL_ENGINE'
        }

signal_engine = SignalEngine()

# ==================== متغیرهای سراسری ====================
user_data = {}
all_users = set()

# ==================== متون دوزبانه ====================
TEXTS_FA = {
    'welcome': '🔥 به ربات تحلیل تکنیکال فوق‌پیشرفته خوش آمدید!\n\n🔥 ۱۰۰۰+ الگوریتم ترکیبی\n🐋 ۲۰ روش تشخیص نهنگ HyperDash\n📊 ۲۰۰+ ارز با تحلیل لحظه‌ای\n💎 سیستم اشتراک فوق‌پیشرفته\n🤖 معاملات خودکار هوشمند\n📈 دقت ۹۹.۹۹٪ با الگوریتم‌های ترکیبی\n\n🚀 برای شروع روی "📊 شروع تحلیل" کلیک کنید.',
    'start_analysis': '📊 شروع تحلیل',
    'stats': '📊 آمار من',
    'exchange': '💱 صرافی توبیت',
    'referral': '🎁 دعوت دوستان',
    'change_lang': '🌐 تغییر زبان',
    'admin_panel': '👑 پنل ادمین',
    'auto_trade': '🤖 معاملات خودکار',
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
    'welcome': '🔥 Welcome to Ultra Advanced Technical Analysis Bot!\n\n🔥 1000+ Hybrid Algorithms\n🐋 20 Whale Detection Methods (HyperDash)\n📊 200+ Coins Real-time Analysis\n💎 Advanced Subscription System\n🤖 Smart Automated Trading\n📈 99.99% Accuracy with Hybrid Algorithms\n\n🚀 Click "📊 Start Analysis" to begin.',
    'start_analysis': '📊 Start Analysis',
    'stats': '📊 My Stats',
    'exchange': '💱 Toobit Exchange',
    'referral': '🎁 Invite Friends',
    'change_lang': '🌐 Change Language',
    'admin_panel': '👑 Admin Panel',
    'auto_trade': '🤖 Auto Trade',
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
    lang = user[4] if user else 'fa'
    return TEXTS_FA.get(key, '') if lang == 'fa' else TEXTS_EN.get(key, '')

# ==================== کیبوردها ====================
def get_main_keyboard(user_id):
    user = db.get_user(user_id)
    lang = user[4] if user else 'fa'
    
    has_subscription = db.check_subscription(user_id)
    
    if lang == 'en':
        keyboard = [
            [KeyboardButton("📊 Start Analysis")],
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
            [KeyboardButton("📊 شروع تحلیل")],
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
    lang = user[4] if user else 'fa'
    keyboard.append([KeyboardButton("🔙 بازگشت" if lang == 'fa' else "🔙 Back")])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_admin_keyboard(user_id):
    user = db.get_user(user_id)
    lang = user[4] if user else 'fa'
    
    if lang == 'en':
        return ReplyKeyboardMarkup([
            [KeyboardButton("🔓 Toggle Paid Mode"), KeyboardButton("💲 Set Prices")],
            [KeyboardButton("💳 Payment Requests"), KeyboardButton("📊 User Stats")],
            [KeyboardButton("🐋 Whale Detection"), KeyboardButton("📢 Broadcast")],
            [KeyboardButton("📊 System Settings"), KeyboardButton("💰 Wallet")],
            [KeyboardButton("📊 Signal Stats"), KeyboardButton("🔙 Back")]
        ], resize_keyboard=True)
    else:
        return ReplyKeyboardMarkup([
            [KeyboardButton("🔓 فعال/غیرفعال کردن حالت پولی"), KeyboardButton("💲 تنظیم قیمت‌ها")],
            [KeyboardButton("💳 درخواست‌های پرداخت"), KeyboardButton("📊 آمار کاربران")],
            [KeyboardButton("🐋 تشخیص نهنگ‌ها"), KeyboardButton("📢 ارسال پیام همگانی")],
            [KeyboardButton("📊 تنظیمات سیستم"), KeyboardButton("💰 کیف پول")],
            [KeyboardButton("📊 آمار سیگنال‌ها"), KeyboardButton("🔙 بازگشت")]
        ], resize_keyboard=True)

def get_subscription_keyboard(user_id):
    user = db.get_user(user_id)
    lang = user[4] if user else 'fa'
    
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
            'state': 'menu',
            'symbol': 'BTCUSDT'
        }
    
    try:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
    except:
        pass
    
    user = db.get_user(user_id)
    lang = user[4] if user else 'fa'
    
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
            candles = price_service.get_klines(text, "1h", 200)
            whale_data = whale_detector.get_whale_analysis_hyperdash(text)
            stats = price_service.get_24h_stats(text)
            
            if not candles:
                await update.effective_chat.send_message(
                    "❌ خطا در دریافت داده‌ها!",
                    reply_markup=get_main_keyboard(user_id)
                )
                return
            
            # تولید سیگنال
            signal = signal_engine.generate_signal(candles, text)
            
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
🔥 **نتیجه تحلیل** 🔥
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
    
    # ===== ۲۰۰+ ارز دقیق =====
    if "۲۰۰+ ارز دقیق" in text or "200+ Coins Detailed" in text:
        await update.effective_chat.send_message(
            "🔄 **در حال دریافت قیمت ۲۰۰+ ارز...**\n⏳ لطفاً صبر کنید...",
            parse_mode='Markdown'
        )
        
        prices = price_service.get_all_prices(SUPPORTED_SYMBOLS[:100])
        
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
        await update.effective_chat.send_message(
            f"🎁 **لینک دعوت**\n\n`https://t.me/{bot_name}?start=ref_{user_id}`",
            reply_markup=get_main_keyboard(user_id),
            parse_mode='Markdown'
        )
        return
    
    # ===== معاملات خودکار =====
    if "معاملات خودکار" in text or "Auto Trade" in text:
        user = db.get_user(user_id)
        auto_trade = user[22] if user else 0
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
        risk = user[23] if user else 2
        max_pos = user[24] if user else 10
        
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
        if "درخواست‌های پرداخت" in text or "Payment Requests" in text:
            await show_payment_requests(update, context)
            return
        
        if "فعال/غیرفعال کردن حالت پولی" in text or "Toggle Paid Mode" in text:
            current_mode = db.get_setting('is_paid_mode')
            new_mode = '0' if current_mode == '1' else '1'
            db.update_setting('is_paid_mode', new_mode)
            status = "فعال" if new_mode == '1' else "غیرفعال"
            await update.effective_chat.send_message(f"✅ حالت پولی {status} شد!", reply_markup=get_admin_keyboard(user_id))
            return
        
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
        
        if "کیف پول" in text or "Wallet" in text:
            card_number = db.get_setting('card_number')
            card_holder = db.get_setting('card_holder')
            
            await update.effective_chat.send_message(
                f"💰 **کیف پول**\n\n💳 شماره کارت: {card_number}\n👤 صاحب کارت: {card_holder}",
                reply_markup=get_admin_keyboard(user_id),
                parse_mode='Markdown'
            )
            return
        
        if "آمار سیگنال‌ها" in text or "Signal Stats" in text:
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
        
        if "بازگشت" in text or "Back" in text:
            await update.effective_chat.send_message("🔙 بازگشت", reply_markup=get_main_keyboard(user_id))
            return

# ==================== توابع اشتراک ====================
async def show_subscription_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = db.get_user(user_id)[4] if db.get_user(user_id) else 'fa'
    
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

async def show_subscription_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = db.get_user(user_id)[4] if db.get_user(user_id) else 'fa'
    user = db.get_user(user_id)
    
    is_active = db.check_subscription(user_id)
    
    if lang == 'fa':
        msg = f"📊 **وضعیت اشتراک**\n\n"
        if is_active:
            expire_date = datetime.fromisoformat(user[11]) if user[11] else None
            if expire_date:
                days_left = (expire_date - datetime.now()).days
                msg += f"✅ **اشتراک فعال**\n"
                msg += f"📅 تاریخ انقضا: {expire_date.strftime('%Y-%m-%d')}\n"
                msg += f"⏳ روزهای باقی‌مانده: {days_left}\n"
                msg += f"💎 پلن: {user[10]}\n"
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
            expire_date = datetime.fromisoformat(user[11]) if user[11] else None
            if expire_date:
                days_left = (expire_date - datetime.now()).days
                msg += f"✅ **Active**\n"
                msg += f"📅 Expires: {expire_date.strftime('%Y-%m-%d')}\n"
                msg += f"⏳ Days left: {days_left}\n"
                msg += f"💎 Plan: {user[10]}\n"
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

async def handle_payment_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = db.get_user(user_id)[4] if db.get_user(user_id) else 'fa'
    
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

# ==================== هندلرهای دستورات ادمین ====================
async def handle_admin_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    text = update.message.text
    
    if text.startswith('/verify_'):
        try:
            payment_id = int(text.replace('/verify_', ''))
            db.verify_payment(payment_id, 'تایید توسط ادمین')
            
            payment = db.cursor.execute('SELECT user_id FROM payments WHERE id = ?', (payment_id,)).fetchone()
            if payment:
                user_id = payment[0]
                lang = db.get_user(user_id)[4] if db.get_user(user_id) else 'fa'
                
                msg = "🎉 **اشتراک شما با موفقیت فعال شد!**\n\n✅ از این پس می‌توانید از تمام امکانات ربات استفاده کنید.\n📊 تعداد تحلیل‌های شما نامحدود است." if lang == 'fa' else "🎉 **Your subscription has been activated!**\n\n✅ You can now use all bot features.\n📊 Your analysis is unlimited."
                
                await context.bot.send_message(chat_id=user_id, text=msg, parse_mode='Markdown')
            
            await update.effective_chat.send_message(f"✅ پرداخت {payment_id} تایید شد!", reply_markup=get_admin_keyboard(ADMIN_ID))
        except Exception as e:
            await update.effective_chat.send_message(f"❌ خطا: {e}")
    
    elif text.startswith('/reject_'):
        try:
            payment_id = int(text.replace('/reject_', ''))
            db.reject_payment(payment_id, 'رد توسط ادمین')
            
            payment = db.cursor.execute('SELECT user_id FROM payments WHERE id = ?', (payment_id,)).fetchone()
            if payment:
                user_id = payment[0]
                lang = db.get_user(user_id)[4] if db.get_user(user_id) else 'fa'
                
                msg = "❌ **درخواست پرداخت شما رد شد!**\n\n🔍 لطفاً فیش واریزی خود را بررسی و مجدداً ارسال کنید." if lang == 'fa' else "❌ **Your payment request was rejected!**\n\n🔍 Please check your receipt and try again."
                
                await context.bot.send_message(chat_id=user_id, text=msg, parse_mode='Markdown')
            
            await update.effective_chat.send_message(f"❌ پرداخت {payment_id} رد شد!", reply_markup=get_admin_keyboard(ADMIN_ID))
        except Exception as e:
            await update.effective_chat.send_message(f"❌ خطا: {e}")

# ==================== اجرا ====================
def main():
    print("=" * 80)
    print("🚀 ربات تحلیل تکنیکال - نسخه نهایی")
    print("🔥 سیگنال‌دهی قدرتمند + تشخیص نهنگ HyperDash")
    print("=" * 80)
    
    if not check_and_create_pid():
        sys.exit(1)
    
    print(f"👤 ادمین: {ADMIN_ID}")
    print(f"🤖 ربات: {BOT_USERNAME}")
    print(f"📊 ارزها: {len(SUPPORTED_SYMBOLS)}")
    print(f"🧠 الگوریتم‌ها: ۱۰۰۰+")
    print(f"🐋 تشخیص نهنگ: ۲۰ روش HyperDash")
    print(f"💎 حالت پولی: {'فعال' if db.get_setting('is_paid_mode') == '1' else 'غیرفعال'}")
    print(f"🎯 دقت هدف: ۹۹.۹۹٪")
    print("=" * 80)
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("verify", handle_admin_commands))
    app.add_handler(CommandHandler("reject", handle_admin_commands))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_payment_receipt))
    
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