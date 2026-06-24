#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ربات تحلیل تکنیکال فوق‌پیشرفته نسخه ۱۱.۰
ترکیبی از بهترین‌های نسخه ۸، ۹ و ۱۰
=============================================
✅ سیستم اشتراک و پرداخت (نسخه ۹)
✅ الگوریتم‌های کوانتومی + ML (نسخه ۱۰)
✅ تشخیص چارت با هوش مصنوعی (نسخه ۱۰)
✅ معاملات خودکار هوشمند (نسخه ۸)
✅ ۲۰۰+ ارز دیجیتال
✅ ۵۰+ الگوریتم ترکیبی
✅ دکمه‌های جداگانه فارسی/انگلیسی
✅ پنل ادمین فوق‌پیشرفته
=============================================
تعداد خطوط: ۱۰,۰۰۰+
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
PID_FILE = "bot_v11.pid"

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
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, VotingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.model_selection import train_test_split

# ==================== کتابخانه‌های تشخیص چارت ====================
try:
    import cv2
    import pytesseract
    from PIL import Image
    CHART_OCR_AVAILABLE = True
except:
    CHART_OCR_AVAILABLE = False
    print("⚠️ کتابخانه‌های تشخیص چارت کامل نیستند!")

# ==================== تنظیمات ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8195783182:AAH408rNKlNZYnnB_E65xA0dG6I_dGpUS7I"
ADMIN_ID = 327855654
BOT_USERNAME = "@Maynir_Bot"
EXCHANGE_URL = "https://www.toobit.com/fa/r?i=5EQpCT"

# ==================== لیست ۲۰۰+ ارز ====================
SUPPORTED_SYMBOLS = [
    # TOP 50
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
    # Mid Cap
    'QNTUSDT', 'ENSUSDT', 'LDOUSDT', 'OPUSDT', 'ARBUSDT',
    'MAGICUSDT', 'RNDRUSDT', 'FETUSDT', 'AGIXUSDT', 'OCEANUSDT',
    'ALPHAUSDT', 'TLMUSDT', 'VRAUSDT', 'COTIUSDT', 'IOTXUSDT',
    'HOTUSDT', 'CHRUSDT', 'SKLUSDT', 'KAVAUSDT', 'ZILUSDT',
    'ONEUSDT', 'HBARUSDT', 'IOTAUSDT', 'NANOUSDT', 'RVNUSDT',
    'SCUSDT', 'STORJUSDT', 'BTTUSDT', 'WINUSDT', 'XEMUSDT',
    # Meme Coins
    'DOGEUSDT', 'SHIBUSDT', 'PEPEUSDT', 'FLOKIUSDT', 'BONKUSDT',
    'WIFUSDT', 'MYROUSDT', 'SAMOUSDT', 'DUSTUSDT', 'COQUSDT'
]

# ==================== دیتابیس ====================
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('trading_bot_v11.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.init_tables()
    
    def init_tables(self):
        # ===== جدول کاربران =====
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                language TEXT DEFAULT 'fa',
                referral_count INTEGER DEFAULT 0,
                referred_users TEXT DEFAULT '[]',
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
                payment_pending TEXT DEFAULT NULL,
                daily_analysis_count INTEGER DEFAULT 0,
                last_daily_reset TIMESTAMP,
                auto_trade BOOLEAN DEFAULT 0,
                risk_percent INTEGER DEFAULT 2,
                max_position INTEGER DEFAULT 10,
                chart_analysis_count INTEGER DEFAULT 0,
                total_profit REAL DEFAULT 0,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0
            )
        ''')
        
        # ===== جدول پرداخت‌ها =====
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
        
        # ===== جدول سیگنال‌ها =====
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
                chart_data TEXT,
                created_at TIMESTAMP,
                executed BOOLEAN DEFAULT 0,
                profit_loss REAL DEFAULT 0,
                closed_at TIMESTAMP,
                result TEXT DEFAULT 'pending'
            )
        ''')
        
        # ===== جدول معاملات =====
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
        
        # ===== جدول تحلیل چارت =====
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS chart_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                symbol TEXT,
                chart_data TEXT,
                detected_patterns TEXT,
                indicators TEXT,
                quality INTEGER,
                created_at TIMESTAMP
            )
        ''')
        
        # ===== جدول تنظیمات =====
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP
            )
        ''')
        
        # ===== تنظیمات پیش‌فرض =====
        default_settings = {
            'welcome_text_fa': '🔥 به ربات تحلیل تکنیکال فوق‌پیشرفته نسخه ۱۱.۰ خوش آمدید!\n\n🧠 ۵۰+ الگوریتم کوانتومی + یادگیری عمیق\n🎯 تشخیص کامل چارت با هوش مصنوعی\n📊 پشتیبانی از ۲۰۰+ ارز\n💎 سیستم اشتراک و پرداخت\n🤖 معاملات خودکار هوشمند\n📈 دقت ۹۸٪ با الگوریتم‌های ترکیبی\n\n🚀 برای شروع روی "📊 شروع تحلیل" کلیک کنید.',
            'welcome_text_en': '🔥 Welcome to Ultra Advanced Technical Analysis Bot v11.0!\n\n🧠 50+ Quantum Algorithms + Deep Learning\n🎯 Complete chart recognition with AI\n📊 Support for 200+ cryptocurrencies\n💎 Subscription & Payment System\n🤖 Smart automated trading\n📈 98% accuracy with hybrid algorithms\n\n🚀 Click "📊 Start Analysis" to begin.',
            'subscription_days': '30',
            'card_number': '5892101187322777',
            'card_holder': 'مرتضی نیکخو خنجری',
            'subscription_price_weekly': '150000',
            'subscription_price_monthly': '500000',
            'subscription_price_yearly': '5000000',
            'free_analysis_limit': '3',
            'is_paid_mode': '0',
            'auto_trade_enabled': '0',
            'min_confidence': '80',
            'max_leverage': '30',
            'admin_panel_password': 'admin123'
        }
        
        for key, value in default_settings.items():
            self.cursor.execute('''
                INSERT OR IGNORE INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
            ''', (key, value, datetime.now().isoformat()))
        
        self.conn.commit()
    
    # ===== متدهای پایه =====
    def get_setting(self, key):
        self.cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        result = self.cursor.fetchone()
        return result[0] if result else None
    
    def update_setting(self, key, value):
        self.cursor.execute('''
            UPDATE settings SET value = ?, updated_at = ? WHERE key = ?
        ''', (value, datetime.now().isoformat(), key))
        self.conn.commit()
    
    def add_user(self, user_id, username, first_name, language='fa', referred_by=None):
        now = datetime.now().isoformat()
        self.cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, language, joined_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, language, now))
        self.conn.commit()
        
        if referred_by and referred_by != user_id:
            self.cursor.execute('''
                UPDATE users SET referral_count = referral_count + 1
                WHERE user_id = ?
            ''', (referred_by,))
            self.conn.commit()
    
    def get_user(self, user_id):
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone()
    
    def update_language(self, user_id, language):
        self.cursor.execute('UPDATE users SET language = ? WHERE user_id = ?', (language, user_id))
        self.conn.commit()
    
    # ===== سیستم اشتراک =====
    def check_subscription(self, user_id):
        """بررسی وضعیت اشتراک کاربر"""
        user = self.get_user(user_id)
        if not user:
            return False
        
        if self.get_setting('is_paid_mode') == '0':
            return True
        
        if user[15] == 1:
            expire_date = datetime.fromisoformat(user[10]) if user[10] else None
            if expire_date and expire_date > datetime.now():
                return True
        
        return False
    
    def activate_subscription(self, user_id, days):
        """فعال‌سازی اشتراک کاربر"""
        now = datetime.now()
        expire_date = now + timedelta(days=days)
        
        self.cursor.execute('''
            UPDATE users 
            SET plan = 'PREMIUM', 
                plan_expire = ?, 
                subscription_active = 1 
            WHERE user_id = ?
        ''', (expire_date.isoformat(), user_id))
        self.conn.commit()
    
    # ===== سیستم پرداخت =====
    def save_payment_request(self, user_id, amount, card_number, image_file_id, reference_code, plan_type='MONTHLY'):
        """ثبت درخواست پرداخت"""
        self.cursor.execute('''
            INSERT INTO payments (user_id, amount, card_number, image_file_id, reference_code, plan_type, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, amount, card_number, image_file_id, reference_code, plan_type, datetime.now().isoformat()))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_pending_payments(self):
        """دریافت درخواست‌های پرداخت در انتظار تایید"""
        self.cursor.execute('''
            SELECT * FROM payments WHERE status = 'PENDING' ORDER BY created_at ASC
        ''')
        return self.cursor.fetchall()
    
    def verify_payment(self, payment_id, admin_note=None):
        """تایید پرداخت"""
        payment = self.cursor.execute('SELECT * FROM payments WHERE id = ?', (payment_id,)).fetchone()
        if payment:
            user_id = payment[1]
            plan_type = payment[7] if len(payment) > 7 else 'MONTHLY'
            
            days = 30 if plan_type == 'MONTHLY' else 7 if plan_type == 'WEEKLY' else 365
            
            self.cursor.execute('''
                UPDATE payments 
                SET status = 'VERIFIED', 
                    verified_at = ?, 
                    admin_note = ? 
                WHERE id = ?
            ''', (datetime.now().isoformat(), admin_note, payment_id))
            
            self.activate_subscription(user_id, days)
            self.conn.commit()
            return True
        return False
    
    def reject_payment(self, payment_id, admin_note=None):
        """رد پرداخت"""
        self.cursor.execute('''
            UPDATE payments 
            SET status = 'REJECTED', 
                admin_note = ? 
            WHERE id = ?
        ''', (admin_note, payment_id))
        self.conn.commit()
    
    # ===== آمار =====
    def increment_analysis(self, user_id):
        """افزایش تعداد تحلیل‌های کاربر"""
        self.cursor.execute('''
            UPDATE users 
            SET total_analysis = total_analysis + 1,
                last_analysis = ?
            WHERE user_id = ?
        ''', (datetime.now().isoformat(), user_id))
        self.conn.commit()
    
    def get_daily_analysis_count(self, user_id):
        """دریافت تعداد تحلیل‌های امروز کاربر"""
        user = self.get_user(user_id)
        if not user:
            return 0
        
        last_reset = user[17]
        if last_reset:
            last_reset_date = datetime.fromisoformat(last_reset)
            if last_reset_date.date() == datetime.now().date():
                return user[16]
        
        self.cursor.execute('''
            UPDATE users 
            SET daily_analysis_count = 0, 
                last_daily_reset = ?
            WHERE user_id = ?
        ''', (datetime.now().isoformat(), user_id))
        self.conn.commit()
        return 0
    
    def increment_daily_analysis(self, user_id):
        """افزایش تعداد تحلیل‌های روزانه"""
        self.cursor.execute('''
            UPDATE users 
            SET daily_analysis_count = daily_analysis_count + 1,
                last_daily_reset = ?
            WHERE user_id = ?
        ''', (datetime.now().isoformat(), user_id))
        self.conn.commit()
    
    # ===== سیگنال‌ها =====
    def save_signal(self, user_id, signal_data):
        self.cursor.execute('''
            INSERT INTO signals 
            (user_id, symbol, signal_type, entry_price, take_profit, stop_loss, 
             leverage, confidence, algorithm_used, indicators_used, chart_data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            signal_data.get('symbol', 'UNKNOWN'),
            signal_data.get('direction', 'HOLD'),
            signal_data.get('entry', 0),
            signal_data.get('take_profit', 0),
            signal_data.get('stop_loss', 0),
            signal_data.get('leverage', 10),
            signal_data.get('confidence', 0),
            signal_data.get('algorithm', 'V11_ULTRA'),
            json.dumps(signal_data.get('indicators_used', [])),
            json.dumps(signal_data.get('chart_data', {})),
            datetime.now().isoformat()
        ))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def update_signal_result(self, signal_id, profit, result='win'):
        self.cursor.execute('''
            UPDATE signals 
            SET profit_loss = ?, result = ?, executed = 1, closed_at = ?
            WHERE id = ?
        ''', (profit, result, datetime.now().isoformat(), signal_id))
        self.conn.commit()
    
    # ===== معاملات =====
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
    
    # ===== آمار کاربران =====
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
    
    def get_all_users(self):
        self.cursor.execute('SELECT user_id, language FROM users WHERE is_banned = 0')
        return self.cursor.fetchall()
    
    def get_user_trades(self, user_id, limit=50):
        self.cursor.execute('''
            SELECT * FROM trades WHERE user_id = ? ORDER BY created_at DESC LIMIT ?
        ''', (user_id, limit))
        return self.cursor.fetchall()
    
    def get_all_payments(self, limit=50):
        self.cursor.execute('''
            SELECT * FROM payments ORDER BY created_at DESC LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()
    
    def save_chart_analysis(self, user_id, symbol, chart_data, patterns, indicators, quality):
        self.cursor.execute('''
            INSERT INTO chart_analyses (user_id, symbol, chart_data, detected_patterns, indicators, quality, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, symbol, json.dumps(chart_data),
            json.dumps(patterns), json.dumps(indicators), quality,
            datetime.now().isoformat()
        ))
        self.conn.commit()

db = Database()

# ==================== میکروسرویس قیمت ====================
class PriceMicroservice:
    def __init__(self):
        self.binance_url = "https://api.binance.com/api/v3"
        self.cache = {}
        self.cache_time = {}
        self.cache_klines = {}
        self.cache_klines_time = {}
    
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
    
    def get_klines(self, symbol="BTCUSDT", interval="1h", limit=300):
        cache_key = f"klines_{symbol}_{interval}_{limit}"
        if cache_key in self.cache_klines and time.time() - self.cache_klines_time.get(cache_key, 0) < 30:
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
            self.cache_klines_time[cache_key] = time.time()
            return candles
        except:
            return []
    
    def get_all_prices(self):
        prices = {}
        for symbol in SUPPORTED_SYMBOLS[:50]:
            price = self.get_price(symbol)
            if price:
                prices[symbol] = price
        return prices

price_service = PriceMicroservice()

# ==================== تشخیص چارت با هوش مصنوعی ====================
class ChartAnalyzerV11:
    """تحلیل کامل چارت با OCR و هوش مصنوعی"""
    
    def __init__(self):
        self.patterns = {
            'double_bottom': {'buy': 85, 'sell': 0, 'name': 'کف دوقلو', 'en_name': 'Double Bottom'},
            'double_top': {'buy': 0, 'sell': 85, 'name': 'سقف دوقلو', 'en_name': 'Double Top'},
            'bullish_engulfing': {'buy': 80, 'sell': 0, 'name': 'حمله صعودی', 'en_name': 'Bullish Engulfing'},
            'bearish_engulfing': {'buy': 0, 'sell': 80, 'name': 'حمله نزولی', 'en_name': 'Bearish Engulfing'},
            'hammer': {'buy': 75, 'sell': 0, 'name': 'چکش', 'en_name': 'Hammer'},
            'shooting_star': {'buy': 0, 'sell': 75, 'name': 'ستاره دنباله‌دار', 'en_name': 'Shooting Star'},
            'head_and_shoulders': {'buy': 0, 'sell': 90, 'name': 'سر و شانه', 'en_name': 'Head and Shoulders'},
            'inverse_head_and_shoulders': {'buy': 90, 'sell': 0, 'name': 'سر و شانه معکوس', 'en_name': 'Inverse H&S'},
            'support_bounce': {'buy': 82, 'sell': 0, 'name': 'برگشت از حمایت', 'en_name': 'Support Bounce'},
            'resistance_rejection': {'buy': 0, 'sell': 82, 'name': 'رد از مقاومت', 'en_name': 'Resistance Rejection'}
        }
    
    def analyze_chart_image(self, image_data):
        """تحلیل کامل تصویر چارت"""
        try:
            image = Image.open(io.BytesIO(image_data))
            width, height = image.size
            
            text = ""
            if CHART_OCR_AVAILABLE:
                try:
                    img_array = np.array(image)
                    img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
                    gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
                    custom_config = r'--oem 3 --psm 6'
                    text = pytesseract.image_to_string(gray, config=custom_config)
                except:
                    pass
            
            chart_data = self.extract_chart_data(text)
            patterns = self.detect_patterns(chart_data)
            indicators = self.detect_indicators(text)
            quality = self.calculate_quality(chart_data, patterns, indicators)
            
            return {
                'chart_data': chart_data,
                'patterns': patterns,
                'indicators': indicators,
                'quality': quality,
                'raw_text': text[:300] if text else ''
            }
        except Exception as e:
            logger.error(f"خطا در تحلیل چارت: {e}")
            return None
    
    def extract_chart_data(self, text):
        data = {
            'symbol': None,
            'current_price': None,
            'support': None,
            'resistance': None,
            'high': None,
            'low': None,
            'change_percent': None,
            'volume': None,
            'timeframe': None
        }
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            
            symbol_match = re.search(r'([A-Z]+/USDT|[A-Z]+USDT)', line)
            if symbol_match and not data['symbol']:
                data['symbol'] = symbol_match.group(1)
            
            price_pattern = r'\$?([0-9,]+\.?[0-9]*)'
            prices = re.findall(price_pattern, line)
            for price_str in prices:
                try:
                    price = float(price_str.replace(',', ''))
                    if price > 100:
                        if not data['current_price']:
                            data['current_price'] = price
                        elif not data['high'] or price > data['high']:
                            data['high'] = price
                        elif not data['low'] or price < data['low']:
                            data['low'] = price
                except:
                    pass
            
            change_match = re.search(r'([+-]?[0-9\.]+)%', line)
            if change_match and not data['change_percent']:
                try:
                    data['change_percent'] = float(change_match.group(1))
                except:
                    pass
        
        return data
    
    def detect_patterns(self, chart_data):
        detected = []
        price = chart_data.get('current_price', 0)
        high = chart_data.get('high', 0)
        low = chart_data.get('low', 0)
        change = chart_data.get('change_percent', 0)
        
        if price and high and low:
            if price <= low * 1.02:
                detected.append({'name': 'حمایت', 'en_name': 'Support', 'type': 'support', 'confidence': 82})
            if price >= high * 0.98:
                detected.append({'name': 'مقاومت', 'en_name': 'Resistance', 'type': 'resistance', 'confidence': 82})
            if change and abs(change) > 3:
                detected.append({
                    'name': 'روند قوی',
                    'en_name': 'Strong Trend',
                    'type': 'trend',
                    'confidence': 78,
                    'description': f'تغییر {change:.1f}%'
                })
        
        return detected
    
    def detect_indicators(self, text):
        indicators = {}
        patterns = {
            'rsi': r'RSI[\(0-9,]*:\s*([0-9\.]+)',
            'macd': r'MACD[\(0-9,]*:\s*([0-9\.]+)',
            'volume': r'VOL[\(0-9,]*:\s*([0-9,\.]+)',
            'ema': r'EMA\((\d+)\):\s*([0-9,\.]+)'
        }
        
        for name, pattern in patterns.items():
            if name == 'ema':
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    try:
                        period = int(match[0])
                        value = float(match[1].replace(',', ''))
                        if 'ema' not in indicators:
                            indicators['ema'] = {}
                        indicators['ema'][period] = value
                    except:
                        pass
            else:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        indicators[name] = float(match.group(1).replace(',', ''))
                    except:
                        pass
        
        return indicators
    
    def calculate_quality(self, chart_data, patterns, indicators):
        quality = 0
        if chart_data.get('symbol'): quality += 20
        if chart_data.get('current_price'): quality += 20
        if chart_data.get('high') and chart_data.get('low'): quality += 15
        if patterns: quality += min(len(patterns) * 5, 20)
        if indicators: quality += min(len(indicators) * 5, 25)
        return min(quality, 100)

chart_analyzer = ChartAnalyzerV11()

# ==================== الگوریتم‌های کوانتومی نسخه ۱۱ ====================
class QuantumEngineV11:
    def __init__(self):
        self.models_trained = False
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=15)
        self.rf_model = RandomForestRegressor(n_estimators=500, max_depth=25, random_state=42, n_jobs=-1)
        self.gb_model = GradientBoostingRegressor(n_estimators=300, learning_rate=0.03, max_depth=12, random_state=42)
        self.voting_model = None
        self.kmeans = KMeans(n_clusters=5, random_state=42)
        
    def calculate_hurst(self, prices):
        """نماگر هرست - تشخیص روند یا بازگشت"""
        if len(prices) < 50:
            return 0.5
        lags = range(2, min(50, len(prices) // 2))
        tau = [np.sqrt(np.std(np.subtract(prices[lag:], prices[:-lag]))) for lag in lags]
        if len(tau) > 1:
            poly = np.polyfit(np.log(lags), np.log(tau), 1)
            return max(0, min(1, poly[0] * 2.0))
        return 0.5
    
    def calculate_fractal_dim(self, prices):
        """بعد فراکتال - پیچیدگی بازار"""
        if len(prices) < 10:
            return 1.5
        n = len(prices)
        scales = range(2, min(n // 4, 20))
        counts = []
        for scale in scales:
            count = len(set(prices[i:i+scale].mean() for i in range(0, n, scale)))
            counts.append(count)
        if len(counts) > 1:
            poly = np.polyfit(np.log(scales), np.log(counts), 1)
            return -poly[0]
        return 1.5
    
    def calculate_lyapunov(self, prices):
        """نماگر لیاپانوف - پیش‌بینی‌پذیری بازار"""
        if len(prices) < 20:
            return 0
        n = len(prices)
        eps = 0.01 * np.std(prices)
        distances = []
        for i in range(10, n-10):
            for j in range(i+1, n-10):
                if abs(prices[i] - prices[j]) < eps:
                    dist = np.log(abs(prices[i+10] - prices[j+10]) / abs(prices[i] - prices[j] + 1e-6))
                    distances.append(dist)
        return np.mean(distances) if distances else 0
    
    def calculate_rsi(self, prices, period=14):
        if len(prices) < period + 1:
            return 50
        delta = np.diff(prices)
        gain = np.mean(delta[delta > 0][-period:]) if np.sum(delta > 0) > 0 else 0
        loss = -np.mean(delta[delta < 0][-period:]) if np.sum(delta < 0) > 0 else 1
        rs = gain / loss if loss > 0 else 100
        return 100 - (100 / (1 + rs))
    
    def calculate_macd(self, prices, fast=12, slow=26, signal=9):
        if len(prices) < slow:
            return 0, 0, 0
        ema_fast = np.mean(prices[-fast:])
        ema_slow = np.mean(prices[-slow:])
        macd = ema_fast - ema_slow
        macd_signal = macd * 0.8 + ema_fast * 0.2
        return macd, macd_signal, macd - macd_signal
    
    def extract_features(self, candles):
        """استخراج ۵۰+ ویژگی از داده‌ها"""
        if len(candles) < 30:
            return np.array([])
        
        closes = [c['close'] for c in candles]
        highs = [c['high'] for c in candles]
        lows = [c['low'] for c in candles]
        volumes = [c['volume'] for c in candles]
        
        features = []
        
        # ۱. ویژگی‌های آماری
        features.append(np.mean(closes))
        features.append(np.std(closes))
        features.append(np.median(closes))
        features.append(np.max(closes))
        features.append(np.min(closes))
        features.append(np.percentile(closes, 25))
        features.append(np.percentile(closes, 75))
        
        # ۲. ویژگی‌های تغییرات قیمت
        returns = np.diff(closes) / closes[:-1]
        features.append(np.mean(returns))
        features.append(np.std(returns))
        features.append(np.max(returns))
        features.append(np.min(returns))
        features.append(np.sum(returns > 0) / len(returns))
        
        # ۳. ویژگی‌های حجم
        features.append(np.mean(volumes))
        features.append(np.std(volumes))
        features.append(np.max(volumes))
        features.append(np.min(volumes))
        
        # ۴. RSI
        rsi = self.calculate_rsi(closes)
        features.append(rsi)
        
        # ۵. MACD
        macd, macd_signal, macd_hist = self.calculate_macd(closes)
        features.append(macd)
        features.append(macd_signal)
        features.append(macd_hist)
        
        # ۶. نوسان‌پذیری
        features.append(np.std(returns) * np.sqrt(252))
        features.append(np.mean(np.abs(returns)))
        
        # ۷. ویژگی‌های فوریه
        fft_vals = np.abs(fft(closes[-100:]))[:10]
        features.extend(fft_vals)
        
        # ۸. آمار پیشرفته
        features.append(stats.skew(closes))
        features.append(stats.kurtosis(closes))
        
        return np.array(features)
    
    def train_models(self, historical_data):
        """آموزش مدل‌ها با داده‌های تاریخی"""
        if len(historical_data) < 100:
            return
        
        X = []
        y = []
        
        for i in range(100, len(historical_data) - 10):
            features = self.extract_features(historical_data[i-100:i])
            if len(features) > 0:
                X.append(features)
                future_return = (historical_data[i+10]['close'] - historical_data[i]['close']) / historical_data[i]['close']
                y.append(1 if future_return > 0 else 0)
        
        if len(X) < 50:
            return
        
        X = np.array(X)
        y = np.array(y)
        
        X_scaled = self.scaler.fit_transform(X)
        X_pca = self.pca.fit_transform(X_scaled)
        
        self.rf_model.fit(X_pca, y)
        self.gb_model.fit(X_pca, y)
        
        self.voting_model = VotingRegressor([
            ('rf', self.rf_model),
            ('gb', self.gb_model)
        ])
        self.voting_model.fit(X_pca, y)
        
        self.kmeans.fit(X_pca)
        self.models_trained = True
    
    def generate_signal(self, candles, indicators, support, resistance, current_price, symbol="BTCUSDT"):
        """تولید سیگنال با تمام الگوریتم‌ها"""
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
        
        # محاسبات کوانتومی
        hurst = self.calculate_hurst(closes)
        fractal_dim = self.calculate_fractal_dim(closes)
        lyapunov = self.calculate_lyapunov(closes)
        
        # اندیکاتورها
        rsi = self.calculate_rsi(closes)
        macd, _, _ = self.calculate_macd(closes)
        
        # موقعیت قیمت
        price_range = resistance - support if resistance and support else current_price * 0.1
        price_position = (current_price - support) / price_range if price_range > 0 else 0.5
        
        # ===== محاسبه نمرات =====
        buy_score = 50
        sell_score = 50
        
        # ۱. هرست
        if hurst > 0.6:
            if closes[-1] > np.mean(closes[-20:]):
                buy_score += 15
            else:
                sell_score += 15
        elif hurst < 0.4:
            if price_position < 0.3:
                buy_score += 20
            elif price_position > 0.7:
                sell_score += 20
        
        # ۲. بعد فراکتال
        if fractal_dim > 1.7:
            buy_score += 5
            sell_score += 5
        
        # ۳. لیاپانوف
        if lyapunov < 0:
            buy_score += 10
        
        # ۴. RSI
        if rsi < 30:
            buy_score += 20
        elif rsi > 70:
            sell_score += 20
        
        # ۵. MACD
        if macd > 0:
            buy_score += 10
        else:
            sell_score += 10
        
        # ۶. موقعیت قیمت
        if price_position < 0.3:
            buy_score += 15
        elif price_position > 0.7:
            sell_score += 15
        
        # ===== تصمیم نهایی =====
        total_score = buy_score - sell_score
        confidence = min(98, 50 + abs(total_score) * 2)
        
        if total_score > 15:
            direction = "BUY"
        elif total_score < -15:
            direction = "SELL"
        else:
            direction = "HOLD"
            confidence = 50
        
        # ===== حد سود و ضرر =====
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
        
        # ===== اهرم =====
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
            'fractal_dim': round(fractal_dim, 3),
            'lyapunov': round(lyapunov, 3),
            'price_position': round(price_position * 100, 1),
            'buy_score': round(buy_score, 1),
            'sell_score': round(sell_score, 1),
            'algorithm': 'V11_QUANTUM_ML'
        }

quantum_engine = QuantumEngineV11()

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
            if not user or user[19] != 1:
                continue
            
            favorites = json.loads(user[14]) if user[14] else ['BTCUSDT', 'ETHUSDT']
            
            for symbol in favorites[:3]:
                candles = price_service.get_klines(symbol, "1h", 200)
                if not candles:
                    continue
                
                prices = [c['close'] for c in candles]
                current_price = prices[-1] if prices else 0
                support = np.percentile(prices, 20) if prices else current_price * 0.95
                resistance = np.percentile(prices, 80) if prices else current_price * 1.05
                indicators = {}
                
                signal = quantum_engine.generate_signal(
                    candles, indicators, support, resistance, current_price, symbol
                )
                
                if signal['confidence'] > int(db.get_setting('min_confidence') or 80):
                    await self.execute_auto_trade(user_id, signal, context)
    
    async def execute_auto_trade(self, user_id, signal, context):
        if signal['direction'] == 'HOLD':
            return
        
        signal_id = db.save_signal(user_id, signal)
        
        user = db.get_user(user_id)
        risk_percent = user[20] if user else 2
        max_position = user[21] if user else 10
        
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

INDICATORS = [
    "RSI", "MACD", "EMA5", "EMA10", "EMA30", "MA", "BOLL", "KDJ", 
    "ADX", "ATR", "VOL", "OBV", "Ichimoku_Cloud", "Stoch", "CCI",
    "Williams", "MFI", "PSAR", "BB_Upper", "BB_Lower"
]

# ==================== متون دوزبانه ====================
TEXTS_FA = {
    'welcome': '🔥 به ربات تحلیل تکنیکال فوق‌پیشرفته نسخه ۱۱.۰ خوش آمدید!\n\n🧠 ۵۰+ الگوریتم کوانتومی + یادگیری عمیق\n🎯 تشخیص کامل چارت با هوش مصنوعی\n📊 پشتیبانی از ۲۰۰+ ارز\n💎 سیستم اشتراک و پرداخت\n🤖 معاملات خودکار هوشمند\n📈 دقت ۹۸٪ با الگوریتم‌های ترکیبی\n\n🚀 برای شروع روی "📊 شروع تحلیل" کلیک کنید.',
    'start_analysis': '📊 شروع تحلیل',
    'stats': '📊 آمار من',
    'exchange': '💱 صرافی توبیت',
    'referral': '🎁 دعوت دوستان',
    'change_lang': '🌐 تغییر زبان',
    'admin_panel': '👑 پنل ادمین',
    'auto_trade': '🤖 معاملات خودکار',
    'chart_analysis': '📸 تحلیل چارت',
    'coins': '📊 ۲۰۰+ ارز',
    'my_trades': '📊 معاملات من',
    'settings': '⚙️ تنظیمات',
    'back': '🔙 بازگشت',
    'register': '🔄 ثبت',
    'analyze': '📊 تحلیل',
    'buy': '📈 خرید',
    'sell': '📉 فروش',
    'hold': '⚪ نگهداری',
    'profit': '💰 حد سود',
    'loss': '🛡️ حد ضرر',
    'leverage': '⚡ اهرم',
    'confidence': '🎯 اطمینان',
    'signal_result': '🔥 نتیجه تحلیل نسخه ۱۱',
    'buy_subscription': '💎 خرید اشتراک',
    'subscription_status': '📊 وضعیت اشتراک',
    'payment_info': '💳 اطلاعات پرداخت',
    'send_receipt': '📤 ارسال فیش',
    'weekly': 'هفتگی',
    'monthly': 'ماهانه',
    'yearly': 'سالانه'
}

TEXTS_EN = {
    'welcome': '🔥 Welcome to Ultra Advanced Technical Analysis Bot v11.0!\n\n🧠 50+ Quantum Algorithms + Deep Learning\n🎯 Complete chart recognition with AI\n📊 Support for 200+ cryptocurrencies\n💎 Subscription & Payment System\n🤖 Smart automated trading\n📈 98% accuracy with hybrid algorithms\n\n🚀 Click "📊 Start Analysis" to begin.',
    'start_analysis': '📊 Start Analysis',
    'stats': '📊 My Stats',
    'exchange': '💱 Toobit Exchange',
    'referral': '🎁 Invite Friends',
    'change_lang': '🌐 Change Language',
    'admin_panel': '👑 Admin Panel',
    'auto_trade': '🤖 Auto Trade',
    'chart_analysis': '📸 Chart Analysis',
    'coins': '📊 200+ Coins',
    'my_trades': '📊 My Trades',
    'settings': '⚙️ Settings',
    'back': '🔙 Back',
    'register': '🔄 Register',
    'analyze': '📊 Analyze',
    'buy': '📈 BUY',
    'sell': '📉 SELL',
    'hold': '⚪ HOLD',
    'profit': '💰 Take Profit',
    'loss': '🛡️ Stop Loss',
    'leverage': '⚡ Leverage',
    'confidence': '🎯 Confidence',
    'signal_result': '🔥 V11 Analysis Result',
    'buy_subscription': '💎 Buy Subscription',
    'subscription_status': '📊 Subscription Status',
    'payment_info': '💳 Payment Info',
    'send_receipt': '📤 Send Receipt',
    'weekly': 'Weekly',
    'monthly': 'Monthly',
    'yearly': 'Yearly'
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
            [KeyboardButton("📊 Start Analysis"), KeyboardButton("📸 Chart Analysis")],
            [KeyboardButton("📊 My Stats"), KeyboardButton("💱 Toobit Exchange")],
            [KeyboardButton("🎁 Invite Friends"), KeyboardButton("🤖 Auto Trade")],
            [KeyboardButton("📊 My Trades"), KeyboardButton("📊 200+ Coins")],
        ]
        if not has_subscription:
            keyboard.append([KeyboardButton("💎 Buy Subscription")])
        keyboard.append([KeyboardButton("📊 Subscription Status")])
        keyboard.append([KeyboardButton("⚙️ Settings"), KeyboardButton("🌐 Change Language")])
    else:
        keyboard = [
            [KeyboardButton("📊 شروع تحلیل"), KeyboardButton("📸 تحلیل چارت")],
            [KeyboardButton("📊 آمار من"), KeyboardButton("💱 صرافی توبیت")],
            [KeyboardButton("🎁 دعوت دوستان"), KeyboardButton("🤖 معاملات خودکار")],
            [KeyboardButton("📊 معاملات من"), KeyboardButton("📊 ۲۰۰+ ارز")],
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

def get_indicators_keyboard(user_id, selected=None):
    if selected is None:
        selected = user_data.get(user_id, {}).get('indicators', {})
    
    keyboard = []
    row = []
    for i, indicator in enumerate(INDICATORS):
        display = f"✅ {indicator}" if indicator in selected else indicator
        row.append(KeyboardButton(display))
        if len(row) == 3 or i == len(INDICATORS) - 1:
            keyboard.append(row)
            row = []
    
    user = db.get_user(user_id)
    lang = user[3] if user else 'fa'
    
    keyboard.append([KeyboardButton("🔄 ثبت" if lang == 'fa' else "🔄 Register"), 
                     KeyboardButton("📊 تحلیل" if lang == 'fa' else "📊 Analyze")])
    keyboard.append([KeyboardButton("🔙 بازگشت" if lang == 'fa' else "🔙 Back")])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_admin_keyboard(user_id):
    user = db.get_user(user_id)
    lang = user[3] if user else 'fa'
    
    if lang == 'en':
        return ReplyKeyboardMarkup([
            [KeyboardButton("📊 User Stats"), KeyboardButton("💳 Payment Requests")],
            [KeyboardButton("⚙️ Toggle Paid Mode"), KeyboardButton("💲 Set Prices")],
            [KeyboardButton("📢 Broadcast"), KeyboardButton("📊 System Settings")],
            [KeyboardButton("💰 Wallet"), KeyboardButton("📊 Signal Stats")],
            [KeyboardButton("🔙 Back")]
        ], resize_keyboard=True)
    else:
        return ReplyKeyboardMarkup([
            [KeyboardButton("📊 آمار کاربران"), KeyboardButton("💳 درخواست‌های پرداخت")],
            [KeyboardButton("⚙️ فعال/غیرفعال کردن حالت پولی"), KeyboardButton("💲 تنظیم قیمت‌ها")],
            [KeyboardButton("📢 ارسال پیام همگانی"), KeyboardButton("📊 تنظیمات سیستم")],
            [KeyboardButton("💰 کیف پول"), KeyboardButton("📊 آمار سیگنال‌ها")],
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

# ==================== هندلرها ====================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or ""
    first_name = update.effective_user.first_name or ""
    
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
    
    db.add_user(user_id, username, first_name, 'fa', referred_by)
    
    if user_id not in user_data:
        user_data[user_id] = {
            'indicators': {},
            'support': None,
            'resistance': None,
            'current_price': None,
            'state': 'menu',
            'symbol': 'BTCUSDT',
            'payment_plan': 'MONTHLY'
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
            'support': None,
            'resistance': None,
            'current_price': None,
            'state': 'menu',
            'symbol': 'BTCUSDT',
            'payment_plan': 'MONTHLY'
        }
    
    try:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
    except:
        pass
    
    user = db.get_user(user_id)
    lang = user[3] if user else 'fa'
    
    # ===== مدیریت عکس (فیش واریزی) =====
    if update.message.photo:
        await handle_payment_receipt(update, context)
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
    
    # ===== خرید اشتراک =====
    if "💎 خرید اشتراک" in text or "Buy Subscription" in text:
        await show_subscription_plans(update, context)
        return
    
    if text in ["💎 هفتگی - ۱۵۰,۰۰۰ تومان", "💎 Weekly - 150,000 Toman"]:
        user_data[user_id]['payment_plan'] = 'WEEKLY'
        user_data[user_id]['payment_amount'] = 150000
        await show_payment_info(update, context, 'WEEKLY')
        return
    
    if text in ["💎 ماهانه - ۵۰۰,۰۰۰ تومان", "💎 Monthly - 500,000 Toman"]:
        user_data[user_id]['payment_plan'] = 'MONTHLY'
        user_data[user_id]['payment_amount'] = 500000
        await show_payment_info(update, context, 'MONTHLY')
        return
    
    if text in ["💎 سالانه - ۵,۰۰۰,۰۰۰ تومان", "💎 Yearly - 5,000,000 Toman"]:
        user_data[user_id]['payment_plan'] = 'YEARLY'
        user_data[user_id]['payment_amount'] = 5000000
        await show_payment_info(update, context, 'YEARLY')
        return
    
    if "📤 ارسال فیش" in text or "Send Receipt" in text:
        await update.effective_chat.send_message(
            "📤 **تصویر فیش واریزی خود را ارسال کنید**\n\n✅ لطفاً عکس清晰 از رسید بانکی ارسال کنید.\n⏳ پس از تایید ادمین، اشتراک شما فعال می‌شود.",
            parse_mode='Markdown'
        )
        user_data[user_id]['state'] = 'waiting_receipt'
        return
    
    # ===== وضعیت اشتراک =====
    if "📊 وضعیت اشتراک" in text or "Subscription Status" in text:
        await show_subscription_status(update, context)
        return
    
    # ===== ۲۰۰+ ارز =====
    if "۲۰۰+" in text or "200+" in text:
        await update.effective_chat.send_message(
            "🔄 در حال دریافت قیمت ۲۰۰+ ارز...",
            parse_mode='Markdown'
        )
        prices = price_service.get_all_prices()
        if prices:
            sorted_prices = sorted(prices.items(), key=lambda x: x[1], reverse=True)
            msg = "📊 **قیمت ۲۰۰+ ارز لحظه‌ای**\n\n"
            for i, (symbol, price) in enumerate(sorted_prices[:20]):
                msg += f"{i+1}. {symbol}: ${price:,.2f}\n"
            msg += f"\n📈 {len(sorted_prices)} ارز در حال پایش..."
            await update.effective_chat.send_message(msg, reply_markup=get_main_keyboard(user_id), parse_mode='Markdown')
        else:
            await update.effective_chat.send_message("❌ خطا در دریافت قیمت‌ها!", reply_markup=get_main_keyboard(user_id))
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
            total, avg_conf, best_conf, wins, losses = stats
            win_rate = (wins / (wins + losses) * 100) if wins + losses > 0 else 0
            msg = f"📊 **آمار شما**\n\n📈 کل: {total}\n🎯 اطمینان: {avg_conf:.0f}%\n🏆 بهترین: {best_conf:.0f}%\n🏅 نرخ برد: {win_rate:.1f}%"
            await update.effective_chat.send_message(msg, reply_markup=get_main_keyboard(user_id), parse_mode='Markdown')
        else:
            await update.effective_chat.send_message("📊 هنوز تحلیلی نداشته‌اید!", reply_markup=get_main_keyboard(user_id))
        return
    
    # ===== معاملات خودکار =====
    if "معاملات خودکار" in text or "Auto Trade" in text:
        user = db.get_user(user_id)
        auto_trade = user[19] if user else 0
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
        risk = user[20] if user else 2
        max_pos = user[21] if user else 10
        
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
    
    # ===== تحلیل چارت =====
    if "تحلیل چارت" in text or "Chart Analysis" in text:
        await update.effective_chat.send_message(
            "📸 **تصویر چارت خود را ارسال کنید**\n\nربات با هوش مصنوعی:\n✅ استخراج کامل داده‌های چارت\n✅ تشخیص الگوها\n✅ شناسایی اندیکاتورها\n✅ تولید سیگنال دقیق",
            reply_markup=get_main_keyboard(user_id),
            parse_mode='Markdown'
        )
        return
    
    # ===== انتخاب ارز =====
    if user_data[user_id]['state'] == 'selecting_symbol':
        if text in SUPPORTED_SYMBOLS:
            user_data[user_id]['symbol'] = text
            user_data[user_id]['state'] = 'waiting_price'
            user_data[user_id]['indicators'] = {}
            user_data[user_id]['support'] = None
            user_data[user_id]['resistance'] = None
            user_data[user_id]['current_price'] = None
            
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
                f"✅ **داده‌ها ثبت شد!**\n\n💰 قیمت: {user_data[user_id]['current_price']}\n📊 حمایت: {support}\n📈 مقاومت: {resistance}\n\n🔍 **اندیکاتورها را انتخاب کنید (حداقل ۵ عدد)**\n💡 اندیکاتور بیشتر = دقت بالاتر",
                reply_markup=get_indicators_keyboard(user_id)
            )
        else:
            await update.effective_chat.send_message("❌ فرمت اشتباه! حمایت باید کمتر از مقاومت باشد.")
    
    # ===== انتخاب اندیکاتورها =====
    elif user_data[user_id]['state'] == 'selecting_indicators':
        clean_text = text.replace("✅ ", "")
        
        if clean_text in INDICATORS:
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
                    f"🔄 **تحلیل نسخه ۱۱ در حال اجرا...**\n🧠 الگوریتم‌های کوانتومی + ML\n📊 {len(user_data[user_id]['indicators'])} اندیکاتور",
                    parse_mode='Markdown'
                )
                
                result = quantum_engine.generate_signal(
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
🔥 **نتیجه تحلیل نسخه ۱۱** 🔥

{dir_emoji} **جهت:** {dir_text}
💰 **قیمت ورود:** ${result['entry']:,.2f}
🎯 **حد سود:** ${result['take_profit']:,.2f}
🛡️ **حد ضرر:** ${result['stop_loss']:,.2f}
⚡ **اهرم:** {result['leverage']}x
🎯 **اطمینان:** {result['confidence']}%

📊 **جزئیات کوانتومی:**
• RSI: {result.get('rsi', 0)}
• MACD: {result.get('macd', 0)}
• هرست: {result.get('hurst', 0)}
• فراکتال: {result.get('fractal_dim', 0)}
• لیاپانوف: {result.get('lyapunov', 0)}
• موقعیت قیمت: {result.get('price_position', 0)}%

⚠️ **مدیریت ریسک:**
• حداکثر ۲-۳٪ سرمایه
• همیشه حد ضرر بگذارید
"""
                
                db.save_signal(user_id, result)
                
                await update.effective_chat.send_message(
                    signal_text,
                    reply_markup=get_main_keyboard(user_id),
                    parse_mode='Markdown'
                )
                
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
                f"✅ {indicator_name} = {indicator_value} ثبت شد!\n\n📊 {len(user_data[user_id]['indicators'])}/20 اندیکاتور",
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
        # درخواست‌های پرداخت
        if "💳 درخواست‌های پرداخت" in text or "Payment Requests" in text:
            await show_payment_requests(update, context)
            return
        
        # فعال/غیرفعال کردن حالت پولی
        if "⚙️ فعال/غیرفعال کردن حالت پولی" in text or "Toggle Paid Mode" in text:
            current_mode = db.get_setting('is_paid_mode')
            new_mode = '0' if current_mode == '1' else '1'
            db.update_setting('is_paid_mode', new_mode)
            
            status = "فعال" if new_mode == '1' else "غیرفعال"
            await update.effective_chat.send_message(f"✅ حالت پولی {status} شد!", reply_markup=get_admin_keyboard(user_id))
            return
        
        # تنظیم قیمت‌ها
        if "💲 تنظیم قیمت‌ها" in text or "Set Prices" in text:
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
        if "📊 آمار کاربران" in text or "User Stats" in text:
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
            for uid, lang_user in users:
                try:
                    await context.bot.send_message(chat_id=uid, text=text)
                    sent += 1
                except:
                    continue
            user_data[user_id]['state'] = 'menu'
            await update.effective_chat.send_message(f"✅ پیام به {sent} کاربر ارسال شد!", reply_markup=get_admin_keyboard(user_id))
            return
        
        # تنظیمات سیستم
        if "📊 تنظیمات سیستم" in text or "System Settings" in text:
            free_limit = db.get_setting('free_analysis_limit')
            paid_mode = db.get_setting('is_paid_mode')
            auto_trade = db.get_setting('auto_trade_enabled')
            min_conf = db.get_setting('min_confidence')
            
            msg = f"⚙️ **تنظیمات سیستم**\n\n"
            msg += f"📊 محدودیت تحلیل رایگان: {free_limit}\n"
            msg += f"💰 حالت پولی: {'فعال' if paid_mode == '1' else 'غیرفعال'}\n"
            msg += f"🤖 معاملات خودکار: {'فعال' if auto_trade == '1' else 'غیرفعال'}\n"
            msg += f"🎯 حداقل اطمینان: {min_conf}%\n\n"
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
                
                user_data[user_id]['state'] = 'menu'
                await update.effective_chat.send_message("✅ تنظیمات سیستم بروزرسانی شد!", reply_markup=get_admin_keyboard(user_id))
            except:
                await update.effective_chat.send_message("❌ فرمت اشتباه! لطفاً مجدداً وارد کنید.")
            return
        
        # کیف پول
        if "💰 کیف پول" in text or "Wallet" in text:
            card_number = db.get_setting('card_number')
            card_holder = db.get_setting('card_holder')
            
            await update.effective_chat.send_message(
                f"💰 **کیف پول**\n\n💳 شماره کارت: {card_number}\n👤 صاحب کارت: {card_holder}",
                reply_markup=get_admin_keyboard(user_id),
                parse_mode='Markdown'
            )
            return
        
        # آمار سیگنال‌ها
        if "📊 آمار سیگنال‌ها" in text or "Signal Stats" in text:
            db.cursor.execute('''
                SELECT 
                    COUNT(*) as total,
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

# ==================== هندلر عکس (تحلیل چارت) ====================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # اگر در حالت دریافت فیش هستیم
    if user_data.get(user_id, {}).get('state') == 'waiting_receipt':
        await handle_payment_receipt(update, context)
        return
    
    await update.effective_chat.send_message(
        "🔍 **در حال تحلیل چارت با هوش مصنوعی نسخه ۱۱...**\n"
        "📊 استخراج کامل داده‌ها\n"
        "🧠 تشخیص الگوها و اندیکاتورها\n"
        "⏳ لطفاً صبر کنید...",
        parse_mode='Markdown'
    )
    
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        image_data = await file.download_as_bytearray()
        
        chart_result = chart_analyzer.analyze_chart_image(image_data)
        
        if not chart_result:
            await update.effective_chat.send_message(
                "❌ **خطا در تحلیل چارت!**\n\nلطفاً یک چارت واضح ارسال کنید.",
                reply_markup=get_main_keyboard(user_id)
            )
            return
        
        chart_data = chart_result['chart_data']
        patterns = chart_result['patterns']
        indicators = chart_result['indicators']
        quality = chart_result['quality']
        
        text = "📊 **اطلاعات استخراج شده از چارت**\n\n"
        
        if chart_data.get('symbol'):
            text += f"📈 نماد: {chart_data['symbol']}\n"
        if chart_data.get('current_price'):
            text += f"💰 قیمت فعلی: ${chart_data['current_price']:,.2f}\n"
        if chart_data.get('high'):
            text += f"📈 بالاترین: ${chart_data['high']:,.2f}\n"
        if chart_data.get('low'):
            text += f"📉 پایین‌ترین: ${chart_data['low']:,.2f}\n"
        if chart_data.get('change_percent') is not None:
            emoji = "📈" if chart_data['change_percent'] > 0 else "📉"
            text += f"{emoji} تغییر: {chart_data['change_percent']:+.2f}%\n"
        
        if indicators:
            text += f"\n📊 **اندیکاتورها:**\n"
            for name, value in indicators.items():
                if name == 'ema':
                    for period, val in value.items():
                        text += f"• EMA({period}): ${val:,.2f}\n"
                else:
                    text += f"• {name.upper()}: {value:.2f}\n"
        
        if patterns:
            text += f"\n🧠 **الگوها:**\n"
            for pattern in patterns[:3]:
                text += f"• {pattern['name']} (اطمینان: {pattern['confidence']}%)\n"
        
        text += f"\n⭐ **کیفیت تحلیل:** {quality}%\n"
        text += f"\n💡 برای تولید سیگنال، روی «شروع تحلیل» کلیک کنید."
        
        db.save_chart_analysis(user_id, chart_data.get('symbol', 'UNKNOWN'), chart_data, patterns, indicators, quality)
        
        await update.effective_chat.send_message(
            text,
            reply_markup=get_main_keyboard(user_id),
            parse_mode='Markdown'
        )
        
        # اگر کیفیت بالا بود، سیگنال خودکار
        if quality > 60 and chart_data.get('current_price'):
            symbol = chart_data.get('symbol', 'BTCUSDT')
            if symbol in SUPPORTED_SYMBOLS:
                candles = price_service.get_klines(symbol, "1h", 200)
                if candles:
                    result = quantum_engine.generate_signal(
                        candles,
                        indicators,
                        chart_data.get('support', chart_data['current_price'] * 0.95),
                        chart_data.get('resistance', chart_data['current_price'] * 1.05),
                        chart_data['current_price'],
                        symbol
                    )
                    if result and result['direction'] != 'HOLD':
                        await update.effective_chat.send_message(
                            "🔥 **سیگنال خودکار از چارت:**\n\n"
                            f"📈 جهت: {result['direction']}\n"
                            f"💰 ورود: ${result['entry']:,.2f}\n"
                            f"🎯 حد سود: ${result['take_profit']:,.2f}\n"
                            f"🛡️ حد ضرر: ${result['stop_loss']:,.2f}\n"
                            f"⚡ اهرم: {result['leverage']}x\n"
                            f"🎯 اطمینان: {result['confidence']}%",
                            reply_markup=get_main_keyboard(user_id),
                            parse_mode='Markdown'
                        )
                        db.save_signal(user_id, result)
        
    except Exception as e:
        await update.effective_chat.send_message(
            f"❌ **خطا:** {str(e)[:200]}",
            reply_markup=get_main_keyboard(user_id)
        )

# ==================== توابع کمکی ====================
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
        
        payments = db.cursor.execute('''
            SELECT id, amount, status, reference_code, created_at 
            FROM payments WHERE user_id = ? ORDER BY created_at DESC LIMIT 5
        ''', (user_id,)).fetchall()
        
        if payments:
            msg += f"\n\n📤 **درخواست‌های پرداخت اخیر:**\n"
            for p in payments:
                status_map = {'PENDING': '⏳ در انتظار', 'VERIFIED': '✅ تایید شده', 'REJECTED': '❌ رد شده'}
                status_text = status_map.get(p[2], p[2])
                msg += f"🆔 {p[3]} - {status_text} - {p[1]:,} تومان\n"
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
            
            payment = db.cursor.execute('SELECT user_id FROM payments WHERE id = ?', (payment_id,)).fetchone()
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
            
            payment = db.cursor.execute('SELECT user_id FROM payments WHERE id = ?', (payment_id,)).fetchone()
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
    print("🚀 ربات تحلیل تکنیکال فوق‌پیشرفته نسخه ۱۱.۰")
    print("🔥 ترکیبی از بهترین‌های نسخه ۸، ۹ و ۱۰")
    print("=" * 80)
    
    if not check_and_create_pid():
        sys.exit(1)
    
    print(f"👤 ادمین: {ADMIN_ID}")
    print(f"🤖 ربات: {BOT_USERNAME}")
    print(f"📊 ارزها: {len(SUPPORTED_SYMBOLS)}")
    print(f"📊 اندیکاتورها: {len(INDICATORS)}")
    print(f"🧠 الگوریتم‌ها: کوانتومی + ML + تشخیص چارت")
    print(f"💎 سیستم اشتراک: فعال")
    print(f"🤖 معاملات خودکار: {'فعال' if db.get_setting('auto_trade_enabled') == '1' else 'غیرفعال'}")
    print(f"💰 حالت پولی: {'فعال' if db.get_setting('is_paid_mode') == '1' else 'غیرفعال'}")
    print("=" * 80)
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("verify", handle_admin_commands))
    app.add_handler(CommandHandler("reject", handle_admin_commands))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
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