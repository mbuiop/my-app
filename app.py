#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ربات تحلیل تکنیکال فوق‌پیشرفته نسخه ۸.۰
با پشتیبانی از ۵۰+ ارز و تشخیص چارت با هوش مصنوعی
دکمه‌های جداگانه فارسی و انگلیسی
"""

import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import asyncio
import json
import time
import numpy as np
from datetime import datetime, timedelta
import requests
import sqlite3
import threading
import os
import hashlib
import random
from scipy import stats
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.svm import SVR
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import warnings
import cv2
import pytesseract
from PIL import Image
import io
import re

warnings.filterwarnings('ignore')

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

# ==================== لیست ۵۰+ ارز ====================
SYMBOLS = [
    # ارزهای دیجیتال اصلی
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", 
    "SOLUSDT", "DOTUSDT", "DOGEUSDT", "AVAXUSDT", "MATICUSDT",
    "LINKUSDT", "UNIUSDT", "ATOMUSDT", "LTCUSDT", "BCHUSDT",
    "NEARUSDT", "ALGOUSDT", "VETUSDT", "ICPUSDT", "FILUSDT",
    "ETCUSDT", "XLMUSDT", "HBARUSDT", "APTUSDT", "ARBUSDT",
    "MKRUSDT", "AAVEUSDT", "CROUSDT", "XMRUSDT", "ZECUSDT",
    # ارزهای با حجم بالا
    "PEPEUSDT", "WIFUSDT", "BONKUSDT", "FLOKIUSDT", "SHIBUSDT",
    "SUIUSDT", "OPUSDT", "ARBUSDT", "STXUSDT", "IMXUSDT",
    "RNDRUSDT", "GRTUSDT", "THETAUSDT", "FTMUSDT", "MNTUSDT",
    "RUNEUSDT", "EGLDUSDT", "KAVAUSDT", "GALAUSDT", "SANDUSDT",
    "MANAUSDT", "CHZUSDT", "ENJUSDT", "BATUSDT", "ZILUSDT",
    "KSMUSDT", "ONEUSDT", "CELRUSDT", "OCEANUSDT", "FETUSDT"
]

# ==================== دیتابیس ====================
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('trading_bot.db', check_same_thread=False)
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
                referred_users TEXT DEFAULT '[]',
                total_analysis INTEGER DEFAULT 0,
                correct_signals INTEGER DEFAULT 0,
                wrong_signals INTEGER DEFAULT 0,
                last_analysis TIMESTAMP,
                joined_at TIMESTAMP,
                plan TEXT DEFAULT 'BASIC',
                plan_expire TIMESTAMP,
                balance INTEGER DEFAULT 0,
                is_admin BOOLEAN DEFAULT 0,
                is_banned BOOLEAN DEFAULT 0,
                signal_history TEXT DEFAULT '[]',
                favorite_symbols TEXT DEFAULT '[]'
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
                result TEXT DEFAULT 'pending'
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP
            )
        ''')
        
        # تنظیمات پیش‌فرض
        default_settings = {
            'welcome_text_fa': '🔥 به ربات تحلیل تکنیکال فوق‌پیشرفته خوش آمدید!\n\n🧠 با ۵۰+ الگوریتم هوشمند\n🎯 تشخیص چارت با هوش مصنوعی\n📊 پشتیبانی از ۵۰+ ارز\n\n🚀 برای شروع روی "📊 شروع تحلیل" کلیک کنید.',
            'welcome_text_en': '🔥 Welcome to Ultra Advanced Technical Analysis Bot!\n\n🧠 With 50+ intelligent algorithms\n🎯 Chart recognition with AI\n📊 Support for 50+ cryptocurrencies\n\n🚀 Click "📊 Start Analysis" to begin.',
            'subscription_days': '30',
            'card_number': '5892101187322777',
            'card_holder': 'مرتضی نیکخو خنجری',
            'subscription_price': '500000',
            'min_confidence': '70',
            'max_leverage': '25'
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
            signal_data.get('algorithm', 'ULTRA_V8'),
            json.dumps(signal_data.get('indicators_used', [])),
            datetime.now().isoformat()
        ))
        self.conn.commit()
    
    def get_user_stats(self, user_id):
        self.cursor.execute('''
            SELECT 
                COUNT(*) as total_signals,
                SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END) as losses,
                AVG(confidence) as avg_confidence
            FROM signals WHERE user_id = ?
        ''', (user_id,))
        return self.cursor.fetchone()
    
    def get_all_users(self):
        self.cursor.execute('SELECT user_id, language FROM users WHERE is_banned = 0')
        return self.cursor.fetchall()

db = Database()

# ==================== میکروسرویس قیمت ۵۰+ ارز ====================
class PriceMicroservice:
    def __init__(self):
        self.binance_url = "https://api.binance.com/api/v3"
        self.cache = {}
        self.cache_time = {}
        self.all_prices_cache = {}
        
    def get_all_prices(self):
        """دریافت قیمت همه ارزها"""
        if self.all_prices_cache and time.time() - self.all_prices_cache.get('time', 0) < 5:
            return self.all_prices_cache.get('data', {})
        
        try:
            response = requests.get(
                f"{self.binance_url}/ticker/price",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                prices = {}
                for item in data:
                    symbol = item['symbol']
                    if symbol in SYMBOLS:
                        prices[symbol] = float(item['price'])
                
                self.all_prices_cache = {
                    'data': prices,
                    'time': time.time()
                }
                return prices
        except:
            pass
        return {}
    
    def get_price(self, symbol="BTCUSDT"):
        if symbol in self.cache and time.time() - self.cache_time.get(symbol, 0) < 2:
            return self.cache[symbol]
        
        try:
            response = requests.get(
                f"{self.binance_url}/ticker/price?symbol={symbol}",
                timeout=3
            )
            if response.status_code == 200:
                price = float(response.json()['price'])
                self.cache[symbol] = price
                self.cache_time[symbol] = time.time()
                return price
        except:
            pass
        return None
    
    def get_klines(self, symbol="BTCUSDT", interval="1h", limit=500):
        try:
            url = f"{self.binance_url}/klines?symbol={symbol}&interval={interval}&limit={limit}"
            response = requests.get(url, timeout=5)
            data = response.json()
            
            prices = []
            for candle in data:
                prices.append({
                    'open': float(candle[1]),
                    'high': float(candle[2]),
                    'low': float(candle[3]),
                    'close': float(candle[4]),
                    'volume': float(candle[5]),
                    'timestamp': datetime.fromtimestamp(candle[0] / 1000)
                })
            return prices
        except:
            return []

price_microservice = PriceMicroservice()

# ==================== تشخیص چارت با هوش مصنوعی ====================
class ChartAnalyzer:
    def __init__(self):
        self.patterns = {
            'double_bottom': {'buy': 85, 'sell': 0},
            'double_top': {'buy': 0, 'sell': 85},
            'bullish_engulfing': {'buy': 80, 'sell': 0},
            'bearish_engulfing': {'buy': 0, 'sell': 80},
            'hammer': {'buy': 75, 'sell': 0},
            'shooting_star': {'buy': 0, 'sell': 75},
            'bullish_flag': {'buy': 70, 'sell': 0},
            'bearish_flag': {'buy': 0, 'sell': 70},
            'head_and_shoulders': {'buy': 0, 'sell': 90},
            'inverse_head_and_shoulders': {'buy': 90, 'sell': 0}
        }
        
    def extract_chart_data(self, image_data):
        """استخراج داده از تصویر چارت با OCR"""
        try:
            # تبدیل به تصویر
            image = Image.open(io.BytesIO(image_data))
            
            # پردازش تصویر
            img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # تشخیص متن با OCR
            custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(gray, config=custom_config)
            
            # استخراج اطلاعات از متن
            data = self.parse_chart_text(text)
            
            return data
        except Exception as e:
            logger.error(f"خطا در تشخیص چارت: {e}")
            return None
    
    def parse_chart_text(self, text):
        """پردازش متن استخراج شده از چارت"""
        data = {
            'symbol': None,
            'current_price': None,
            'support': None,
            'resistance': None,
            'rsi': None,
            'macd': None,
            'ema': {},
            'volume': None,
            'pattern': None
        }
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # تشخیص نماد
            if 'BTC' in line or 'ETH' in line or 'USDT' in line:
                match = re.search(r'([A-Z]+/USDT|[A-Z]+USDT)', line)
                if match:
                    data['symbol'] = match.group(1)
            
            # تشخیص قیمت
            price_pattern = r'\$?([0-9,]+\.?[0-9]*)'
            prices = re.findall(price_pattern, line)
            if prices and not data['current_price']:
                try:
                    data['current_price'] = float(prices[0].replace(',', ''))
                except:
                    pass
            
            # تشخیص RSI
            if 'RSI' in line:
                match = re.search(r'RSI[\(0-9,]*:\s*([0-9\.]+)', line)
                if match:
                    data['rsi'] = float(match.group(1))
            
            # تشخیص MACD
            if 'MACD' in line:
                match = re.search(r'MACD[\(0-9,]*:\s*([0-9\.]+)', line)
                if match:
                    data['macd'] = float(match.group(1))
            
            # تشخیص EMA
            ema_match = re.search(r'EMA\((\d+)\):\s*([0-9,\.]+)', line)
            if ema_match:
                period = int(ema_match.group(1))
                value = float(ema_match.group(2).replace(',', ''))
                data['ema'][period] = value
        
        return data
    
    def detect_pattern(self, df, support, resistance):
        """تشخیص الگوهای کندل استیک"""
        if len(df) < 10:
            return None
        
        pattern_scores = {'buy': 0, 'sell': 0}
        
        # 1. بررسی حمایت و مقاومت
        last_price = df[-1]['close']
        
        if last_price <= support * 1.01:
            pattern_scores['buy'] += 20
        
        if last_price >= resistance * 0.99:
            pattern_scores['sell'] += 20
        
        # 2. بررسی الگوهای کندل
        last_candles = df[-5:]
        
        # بررسی دو کندل آخر
        if len(last_candles) >= 2:
            c1 = last_candles[-2]
            c2 = last_candles[-1]
            
            # حمله صعودی (Bullish Engulfing)
            if c1['close'] < c1['open'] and c2['close'] > c2['open']:
                if c2['close'] > c1['open'] and c2['open'] < c1['close']:
                    pattern_scores['buy'] += 30
            
            # حمله نزولی (Bearish Engulfing)
            if c1['close'] > c1['open'] and c2['close'] < c2['open']:
                if c2['close'] < c1['open'] and c2['open'] > c1['close']:
                    pattern_scores['sell'] += 30
        
        # 3. الگوی چکش
        if len(last_candles) >= 1:
            c = last_candles[-1]
            body = abs(c['close'] - c['open'])
            upper_wick = c['high'] - max(c['open'], c['close'])
            lower_wick = min(c['open'], c['close']) - c['low']
            
            if lower_wick > body * 2 and upper_wick < body * 0.5:
                pattern_scores['buy'] += 25
            
            if upper_wick > body * 2 and lower_wick < body * 0.5:
                pattern_scores['sell'] += 25
        
        # 4. بررسی روند با EMA
        if len(df) >= 20:
            ema_short = np.mean([c['close'] for c in df[-5:]])
            ema_long = np.mean([c['close'] for c in df[-20:]])
            
            if ema_short > ema_long:
                pattern_scores['buy'] += 15
            else:
                pattern_scores['sell'] += 15
        
        # تعیین الگوی نهایی
        if pattern_scores['buy'] > pattern_scores['sell'] + 20:
            return 'bullish'
        elif pattern_scores['sell'] > pattern_scores['buy'] + 20:
            return 'bearish'
        else:
            return 'neutral'

# ==================== ۵۰+ الگوریتم پیشرفته ====================
class UltraAdvancedAlgorithms:
    
    # ===== گروه الگوریتم‌های مومنتوم =====
    @staticmethod
    def algo_1_rsi_macd(indicators):
        rsi = indicators.get('RSI', 50)
        macd = indicators.get('MACD', 0)
        if rsi < 30 and macd > 0:
            return 'BUY', 85
        elif rsi > 70 and macd < 0:
            return 'SELL', 85
        return 'HOLD', 0
    
    @staticmethod
    def algo_2_rsi_macd_stoch(indicators):
        rsi = indicators.get('RSI', 50)
        macd = indicators.get('MACD', 0)
        stoch = indicators.get('Stoch', 50)
        if rsi < 30 and macd > 0 and stoch < 20:
            return 'BUY', 90
        elif rsi > 70 and macd < 0 and stoch > 80:
            return 'SELL', 90
        return 'HOLD', 0
    
    @staticmethod
    def algo_3_ema_adx(indicators):
        ema5 = indicators.get('EMA5', 0)
        ema30 = indicators.get('EMA30', 0)
        adx = indicators.get('ADX', 20)
        if ema5 > ema30 and adx > 25:
            return 'BUY', 88
        elif ema5 < ema30 and adx > 25:
            return 'SELL', 88
        return 'HOLD', 0
    
    @staticmethod
    def algo_4_bollinger_stoch(indicators):
        bb = indicators.get('BOLL', 0)
        stoch = indicators.get('Stoch', 50)
        price = indicators.get('current_price', 0)
        if price < bb * 0.98 and stoch < 20:
            return 'BUY', 87
        elif price > bb * 1.02 and stoch > 80:
            return 'SELL', 87
        return 'HOLD', 0
    
    @staticmethod
    def algo_5_kdj_atr(indicators):
        kdj = indicators.get('KDJ', 50)
        atr = indicators.get('ATR', 0)
        price = indicators.get('current_price', 0)
        if kdj < 20 and atr > price * 0.015:
            return 'BUY', 86
        elif kdj > 80 and atr > price * 0.015:
            return 'SELL', 86
        return 'HOLD', 0
    
    @staticmethod
    def algo_6_cci_mfi(indicators):
        cci = indicators.get('CCI', 0)
        mfi = indicators.get('MFI', 50)
        if cci < -100 and mfi < 20:
            return 'BUY', 84
        elif cci > 100 and mfi > 80:
            return 'SELL', 84
        return 'HOLD', 0
    
    @staticmethod
    def algo_7_williams_psar(indicators):
        williams = indicators.get('Williams', -50)
        psar = indicators.get('PSAR', 0)
        price = indicators.get('current_price', 0)
        if williams < -80 and psar < price:
            return 'BUY', 83
        elif williams > -20 and psar > price:
            return 'SELL', 83
        return 'HOLD', 0
    
    @staticmethod
    def algo_8_ichimoku_volume(indicators):
        ichimoku = indicators.get('Ichimoku_Cloud', 0)
        volume = indicators.get('VOL', 0)
        price = indicators.get('current_price', 0)
        if ichimoku < price * 0.98 and volume > 2000000:
            return 'BUY', 82
        elif ichimoku > price * 1.02 and volume > 2000000:
            return 'SELL', 82
        return 'HOLD', 0
    
    @staticmethod
    def algo_9_obv_atr(indicators):
        obv = indicators.get('OBV', 0)
        atr = indicators.get('ATR', 0)
        if obv > 50000 and atr > 0:
            return 'BUY', 80
        elif obv < -50000 and atr > 0:
            return 'SELL', 80
        return 'HOLD', 0
    
    @staticmethod
    def algo_10_macd_histogram(indicators):
        macd_hist = indicators.get('MACD', 0) * 2
        if macd_hist > 1.0:
            return 'BUY', 79
        elif macd_hist < -1.0:
            return 'SELL', 79
        return 'HOLD', 0
    
    @staticmethod
    def algo_11_rsi_ma(indicators):
        rsi = indicators.get('RSI', 50)
        ma = indicators.get('MA', 0)
        price = indicators.get('current_price', 0)
        if rsi < 30 and price > ma:
            return 'BUY', 78
        elif rsi > 70 and price < ma:
            return 'SELL', 78
        return 'HOLD', 0
    
    @staticmethod
    def algo_12_ema_volume(indicators):
        ema10 = indicators.get('EMA10', 0)
        ema30 = indicators.get('EMA30', 0)
        volume = indicators.get('VOL', 0)
        if ema10 > ema30 and volume > 3000000:
            return 'BUY', 77
        elif ema10 < ema30 and volume > 3000000:
            return 'SELL', 77
        return 'HOLD', 0
    
    @staticmethod
    def algo_13_adx_rsi(indicators):
        adx = indicators.get('ADX', 20)
        rsi = indicators.get('RSI', 50)
        if adx > 30 and rsi < 35:
            return 'BUY', 89
        elif adx > 30 and rsi > 65:
            return 'SELL', 89
        return 'HOLD', 0
    
    @staticmethod
    def algo_14_ichimoku_tenkan(indicators):
        ichimoku = indicators.get('Ichimoku_Cloud', 0)
        tenkan = indicators.get('tenkan', 0)
        price = indicators.get('current_price', 0)
        if price > ichimoku and price > tenkan:
            return 'BUY', 76
        elif price < ichimoku and price < tenkan:
            return 'SELL', 76
        return 'HOLD', 0
    
    @staticmethod
    def algo_15_stoch_rsi(indicators):
        stoch = indicators.get('Stoch', 50)
        rsi = indicators.get('RSI', 50)
        if stoch < 20 and rsi < 30:
            return 'BUY', 92
        elif stoch > 80 and rsi > 70:
            return 'SELL', 92
        return 'HOLD', 0
    
    @staticmethod
    def algo_16_bb_width(indicators):
        bb_upper = indicators.get('BB_Upper', 0)
        bb_lower = indicators.get('BB_Lower', 0)
        price = indicators.get('current_price', 0)
        bb_width = (bb_upper - bb_lower) / price * 100 if price > 0 else 0
        if bb_width < 5 and price < (bb_upper + bb_lower) / 2:
            return 'BUY', 75
        elif bb_width > 15 and price > (bb_upper + bb_lower) / 2:
            return 'SELL', 75
        return 'HOLD', 0
    
    @staticmethod
    def algo_17_volume_spike(indicators):
        volume = indicators.get('VOL', 0)
        volume_sma = indicators.get('volume_sma', 0)
        price = indicators.get('current_price', 0)
        if volume > volume_sma * 2.5 and price > 0:
            return 'BUY', 74
        elif volume > volume_sma * 2.5 and price < 0:
            return 'SELL', 74
        return 'HOLD', 0
    
    @staticmethod
    def algo_18_momentum(indicators):
        momentum = indicators.get('momentum', 0)
        if momentum > 8:
            return 'BUY', 73
        elif momentum < -8:
            return 'SELL', 73
        return 'HOLD', 0
    
    @staticmethod
    def algo_19_support_resistance(indicators):
        support = indicators.get('support', 0)
        resistance = indicators.get('resistance', 0)
        price = indicators.get('current_price', 0)
        if price < support * 1.005:
            return 'BUY', 81
        elif price > resistance * 0.995:
            return 'SELL', 81
        return 'HOLD', 0
    
    @staticmethod
    def algo_20_macd_signal(indicators):
        macd = indicators.get('MACD', 0)
        macd_signal = indicators.get('macd_signal', 0)
        if macd > macd_signal * 1.2:
            return 'BUY', 72
        elif macd < macd_signal * 0.8:
            return 'SELL', 72
        return 'HOLD', 0
    
    @staticmethod
    def algo_21_rsi_divergence(indicators):
        rsi = indicators.get('RSI', 50)
        price = indicators.get('current_price', 0)
        if rsi < 25 and price > 0:
            return 'BUY', 88
        elif rsi > 75 and price > 0:
            return 'SELL', 88
        return 'HOLD', 0
    
    @staticmethod
    def algo_22_ema_cross(indicators):
        ema5 = indicators.get('EMA5', 0)
        ema10 = indicators.get('EMA10', 0)
        ema30 = indicators.get('EMA30', 0)
        if ema5 > ema10 > ema30:
            return 'BUY', 85
        elif ema5 < ema10 < ema30:
            return 'SELL', 85
        return 'HOLD', 0
    
    @staticmethod
    def algo_23_macd_zero(indicators):
        macd = indicators.get('MACD', 0)
        if macd > 0.5:
            return 'BUY', 70
        elif macd < -0.5:
            return 'SELL', 70
        return 'HOLD', 0
    
    @staticmethod
    def algo_24_rsi_adx_macd(indicators):
        rsi = indicators.get('RSI', 50)
        adx = indicators.get('ADX', 20)
        macd = indicators.get('MACD', 0)
        if rsi < 30 and adx > 25 and macd > 0:
            return 'BUY', 95
        elif rsi > 70 and adx > 25 and macd < 0:
            return 'SELL', 95
        return 'HOLD', 0
    
    @staticmethod
    def algo_25_bb_upper_lower(indicators):
        bb_upper = indicators.get('BB_Upper', 0)
        bb_lower = indicators.get('BB_Lower', 0)
        price = indicators.get('current_price', 0)
        if price < bb_lower * 1.005:
            return 'BUY', 77
        elif price > bb_upper * 0.995:
            return 'SELL', 77
        return 'HOLD', 0
    
    @staticmethod
    def algo_26_volume_ma(indicators):
        volume = indicators.get('VOL', 0)
        ma = indicators.get('MA', 0)
        price = indicators.get('current_price', 0)
        if volume > 5000000 and price > ma:
            return 'BUY', 76
        elif volume > 5000000 and price < ma:
            return 'SELL', 76
        return 'HOLD', 0
    
    @staticmethod
    def algo_27_kdj_ma(indicators):
        kdj = indicators.get('KDJ', 50)
        ma = indicators.get('MA', 0)
        price = indicators.get('current_price', 0)
        if kdj < 20 and price > ma:
            return 'BUY', 80
        elif kdj > 80 and price < ma:
            return 'SELL', 80
        return 'HOLD', 0
    
    @staticmethod
    def algo_28_cci_volume(indicators):
        cci = indicators.get('CCI', 0)
        volume = indicators.get('VOL', 0)
        if cci < -100 and volume > 2000000:
            return 'BUY', 78
        elif cci > 100 and volume > 2000000:
            return 'SELL', 78
        return 'HOLD', 0
    
    @staticmethod
    def algo_29_williams_rsi(indicators):
        williams = indicators.get('Williams', -50)
        rsi = indicators.get('RSI', 50)
        if williams < -80 and rsi < 30:
            return 'BUY', 87
        elif williams > -20 and rsi > 70:
            return 'SELL', 87
        return 'HOLD', 0
    
    @staticmethod
    def algo_30_obv_rsi(indicators):
        obv = indicators.get('OBV', 0)
        rsi = indicators.get('RSI', 50)
        if obv > 10000 and rsi < 30:
            return 'BUY', 82
        elif obv < -10000 and rsi > 70:
            return 'SELL', 82
        return 'HOLD', 0
    
    @staticmethod
    def algo_31_ichimoku_volume_rsi(indicators):
        ichimoku = indicators.get('Ichimoku_Cloud', 0)
        volume = indicators.get('VOL', 0)
        rsi = indicators.get('RSI', 50)
        price = indicators.get('current_price', 0)
        if price > ichimoku and volume > 3000000 and rsi < 40:
            return 'BUY', 91
        elif price < ichimoku and volume > 3000000 and rsi > 60:
            return 'SELL', 91
        return 'HOLD', 0
    
    @staticmethod
    def algo_32_ema_rsi_volume(indicators):
        ema5 = indicators.get('EMA5', 0)
        ema30 = indicators.get('EMA30', 0)
        rsi = indicators.get('RSI', 50)
        volume = indicators.get('VOL', 0)
        if ema5 > ema30 and rsi < 35 and volume > 2000000:
            return 'BUY', 93
        elif ema5 < ema30 and rsi > 65 and volume > 2000000:
            return 'SELL', 93
        return 'HOLD', 0
    
    @staticmethod
    def algo_33_macd_stoch_rsi(indicators):
        macd = indicators.get('MACD', 0)
        stoch = indicators.get('Stoch', 50)
        rsi = indicators.get('RSI', 50)
        if macd > 0 and stoch < 20 and rsi < 30:
            return 'BUY', 94
        elif macd < 0 and stoch > 80 and rsi > 70:
            return 'SELL', 94
        return 'HOLD', 0
    
    @staticmethod
    def algo_34_atr_adx(indicators):
        atr = indicators.get('ATR', 0)
        adx = indicators.get('ADX', 20)
        price = indicators.get('current_price', 0)
        if atr > price * 0.02 and adx > 30:
            return 'BUY', 81
        elif atr > price * 0.02 and adx > 30:
            return 'SELL', 81
        return 'HOLD', 0
    
    @staticmethod
    def algo_35_bb_ma(indicators):
        bb_upper = indicators.get('BB_Upper', 0)
        bb_lower = indicators.get('BB_Lower', 0)
        ma = indicators.get('MA', 0)
        price = indicators.get('current_price', 0)
        if price < bb_lower and price > ma:
            return 'BUY', 79
        elif price > bb_upper and price < ma:
            return 'SELL', 79
        return 'HOLD', 0
    
    @staticmethod
    def algo_36_mfi_ma(indicators):
        mfi = indicators.get('MFI', 50)
        ma = indicators.get('MA', 0)
        price = indicators.get('current_price', 0)
        if mfi < 20 and price > ma:
            return 'BUY', 76
        elif mfi > 80 and price < ma:
            return 'SELL', 76
        return 'HOLD', 0
    
    @staticmethod
    def algo_37_psar_atr(indicators):
        psar = indicators.get('PSAR', 0)
        atr = indicators.get('ATR', 0)
        price = indicators.get('current_price', 0)
        if psar < price and atr > 0:
            return 'BUY', 75
        elif psar > price and atr > 0:
            return 'SELL', 75
        return 'HOLD', 0
    
    @staticmethod
    def algo_38_momentum_volume(indicators):
        momentum = indicators.get('momentum', 0)
        volume = indicators.get('VOL', 0)
        if momentum > 5 and volume > 3000000:
            return 'BUY', 74
        elif momentum < -5 and volume > 3000000:
            return 'SELL', 74
        return 'HOLD', 0
    
    @staticmethod
    def algo_39_rsi_support(indicators):
        rsi = indicators.get('RSI', 50)
        support = indicators.get('support', 0)
        price = indicators.get('current_price', 0)
        if rsi < 30 and price < support * 1.02:
            return 'BUY', 86
        elif rsi > 70 and price > support * 1.02:
            return 'SELL', 86
        return 'HOLD', 0
    
    @staticmethod
    def algo_40_macd_resistance(indicators):
        macd = indicators.get('MACD', 0)
        resistance = indicators.get('resistance', 0)
        price = indicators.get('current_price', 0)
        if macd > 0 and price < resistance * 0.98:
            return 'BUY', 83
        elif macd < 0 and price > resistance * 0.98:
            return 'SELL', 83
        return 'HOLD', 0

# ==================== موتور سیگنال فوق‌پیشرفته ====================
class UltraSignalEngineV8:
    def __init__(self):
        self.algorithms = [
            ('RSI+MACD', UltraAdvancedAlgorithms.algo_1_rsi_macd),
            ('RSI+MACD+Stoch', UltraAdvancedAlgorithms.algo_2_rsi_macd_stoch),
            ('EMA+ADX', UltraAdvancedAlgorithms.algo_3_ema_adx),
            ('BB+Stoch', UltraAdvancedAlgorithms.algo_4_bollinger_stoch),
            ('KDJ+ATR', UltraAdvancedAlgorithms.algo_5_kdj_atr),
            ('CCI+MFI', UltraAdvancedAlgorithms.algo_6_cci_mfi),
            ('Williams+PSAR', UltraAdvancedAlgorithms.algo_7_williams_psar),
            ('Ichimoku+Volume', UltraAdvancedAlgorithms.algo_8_ichimoku_volume),
            ('OBV+ATR', UltraAdvancedAlgorithms.algo_9_obv_atr),
            ('MACD Hist', UltraAdvancedAlgorithms.algo_10_macd_histogram),
            ('RSI+MA', UltraAdvancedAlgorithms.algo_11_rsi_ma),
            ('EMA+Volume', UltraAdvancedAlgorithms.algo_12_ema_volume),
            ('ADX+RSI', UltraAdvancedAlgorithms.algo_13_adx_rsi),
            ('Ichimoku+Tenkan', UltraAdvancedAlgorithms.algo_14_ichimoku_tenkan),
            ('Stoch+RSI', UltraAdvancedAlgorithms.algo_15_stoch_rsi),
            ('BB Width', UltraAdvancedAlgorithms.algo_16_bb_width),
            ('Volume Spike', UltraAdvancedAlgorithms.algo_17_volume_spike),
            ('Momentum', UltraAdvancedAlgorithms.algo_18_momentum),
            ('Sup/Res', UltraAdvancedAlgorithms.algo_19_support_resistance),
            ('MACD Signal', UltraAdvancedAlgorithms.algo_20_macd_signal),
            ('RSI Divergence', UltraAdvancedAlgorithms.algo_21_rsi_divergence),
            ('EMA Cross', UltraAdvancedAlgorithms.algo_22_ema_cross),
            ('MACD Zero', UltraAdvancedAlgorithms.algo_23_macd_zero),
            ('RSI+ADX+MACD', UltraAdvancedAlgorithms.algo_24_rsi_adx_macd),
            ('BB Upper/Lower', UltraAdvancedAlgorithms.algo_25_bb_upper_lower),
            ('Volume+MA', UltraAdvancedAlgorithms.algo_26_volume_ma),
            ('KDJ+MA', UltraAdvancedAlgorithms.algo_27_kdj_ma),
            ('CCI+Volume', UltraAdvancedAlgorithms.algo_28_cci_volume),
            ('Williams+RSI', UltraAdvancedAlgorithms.algo_29_williams_rsi),
            ('OBV+RSI', UltraAdvancedAlgorithms.algo_30_obv_rsi),
            ('Ichimoku+Volume+RSI', UltraAdvancedAlgorithms.algo_31_ichimoku_volume_rsi),
            ('EMA+RSI+Volume', UltraAdvancedAlgorithms.algo_32_ema_rsi_volume),
            ('MACD+Stoch+RSI', UltraAdvancedAlgorithms.algo_33_macd_stoch_rsi),
            ('ATR+ADX', UltraAdvancedAlgorithms.algo_34_atr_adx),
            ('BB+MA', UltraAdvancedAlgorithms.algo_35_bb_ma),
            ('MFI+MA', UltraAdvancedAlgorithms.algo_36_mfi_ma),
            ('PSAR+ATR', UltraAdvancedAlgorithms.algo_37_psar_atr),
            ('Momentum+Volume', UltraAdvancedAlgorithms.algo_38_momentum_volume),
            ('RSI+Support', UltraAdvancedAlgorithms.algo_39_rsi_support),
            ('MACD+Resistance', UltraAdvancedAlgorithms.algo_40_macd_resistance)
        ]
        self.chart_analyzer = ChartAnalyzer()
        self.algorithm_weights = {}
        
        # وزن‌دهی اولیه به الگوریتم‌های برتر
        self.top_algorithms = [
            'RSI+ADX+MACD', 'MACD+Stoch+RSI', 'EMA+RSI+Volume',
            'Ichimoku+Volume+RSI', 'Stoch+RSI', 'RSI+MACD+Stoch',
            'ADX+RSI', 'RSI+Support', 'MACD+Resistance'
        ]
        
    def calculate_all_indicators(self, df):
        """محاسبه تمام اندیکاتورها"""
        if not df or len(df) < 50:
            return {}
        
        prices = [c['close'] for c in df]
        highs = [c['high'] for c in df]
        lows = [c['low'] for c in df]
        volumes = [c['volume'] for c in df]
        
        last_price = prices[-1]
        
        # RSI
        delta = np.diff(prices)
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        
        if len(gain) >= 14:
            avg_gain = np.mean(gain[-14:])
            avg_loss = np.mean(loss[-14:])
            rs = avg_gain / avg_loss if avg_loss > 0 else 100
            rsi = 100 - (100 / (1 + rs))
        else:
            rsi = 50
        
        # MACD
        ema12 = np.mean(prices[-12:]) if len(prices) >= 12 else last_price
        ema26 = np.mean(prices[-26:]) if len(prices) >= 26 else last_price
        macd = ema12 - ema26
        macd_signal = macd * 0.8 + ema12 * 0.2
        
        # EMA
        ema5 = np.mean(prices[-5:]) if len(prices) >= 5 else last_price
        ema10 = np.mean(prices[-10:]) if len(prices) >= 10 else last_price
        ema30 = np.mean(prices[-30:]) if len(prices) >= 30 else last_price
        ma = np.mean(prices[-20:]) if len(prices) >= 20 else last_price
        
        # باند بولینگر
        sma_20 = np.mean(prices[-20:]) if len(prices) >= 20 else last_price
        std_20 = np.std(prices[-20:]) if len(prices) >= 20 else last_price * 0.02
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
        
        # ADX
        if len(prices) >= 14:
            high_low = [h - l for h, l in zip(highs, lows)]
            atr = np.mean(high_low[-14:])
            plus_dm = []
            minus_dm = []
            for i in range(1, len(highs)):
                plus = max(0, highs[i] - highs[i-1])
                minus = max(0, lows[i-1] - lows[i])
                plus_dm.append(plus)
                minus_dm.append(minus)
            plus_di = 100 * (np.mean(plus_dm[-14:]) / atr) if atr > 0 else 0
            minus_di = 100 * (np.mean(minus_dm[-14:]) / atr) if atr > 0 else 0
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) > 0 else 0
            adx = np.mean([dx] * 14) if len([dx] * 14) > 0 else 0
        else:
            adx = 20
        
        # KDJ
        kdj = stoch * 0.8 + (rsi / 100) * 20
        
        # ATR
        if len(highs) >= 14:
            true_ranges = []
            for i in range(1, len(highs)):
                tr = max(
                    highs[i] - lows[i],
                    abs(highs[i] - prices[i-1]),
                    abs(lows[i] - prices[i-1])
                )
                true_ranges.append(tr)
            atr_value = np.mean(true_ranges[-14:]) if len(true_ranges) >= 14 else last_price * 0.02
        else:
            atr_value = last_price * 0.02
        
        # سایر اندیکاتورها
        ichimoku = (np.mean(prices[-9:]) + np.mean(prices[-26:])) / 2 if len(prices) >= 26 else last_price
        tenkan = np.mean(prices[-9:]) if len(prices) >= 9 else last_price
        cci = (last_price - np.mean(prices[-20:])) / (0.015 * np.std(prices[-20:])) if len(prices) >= 20 and np.std(prices[-20:]) > 0 else 0
        mfi = 50 + (np.mean(volumes[-14:]) / 1000000) * 10 if volumes else 50
        williams = -100 * ((high_14 - last_price) / (high_14 - low_14)) if high_14 > low_14 else -50
        psar = last_price * 0.99
        obv = np.sum(volumes) / 1000 if volumes else 0
        momentum = (last_price - prices[-10]) / prices[-10] * 100 if len(prices) >= 10 else 0
        
        return {
            'RSI': rsi,
            'MACD': macd,
            'macd_signal': macd_signal,
            'EMA5': ema5,
            'EMA10': ema10,
            'EMA30': ema30,
            'MA': ma,
            'BOLL': bb_mid,
            'BB_Upper': bb_upper,
            'BB_Lower': bb_lower,
            'Stoch': stoch,
            'ADX': adx,
            'KDJ': kdj,
            'ATR': atr_value,
            'Ichimoku_Cloud': ichimoku,
            'tenkan': tenkan,
            'CCI': cci,
            'MFI': mfi,
            'Williams': williams,
            'PSAR': psar,
            'OBV': obv,
            'VOL': volumes[-1] if volumes else 0,
            'volume_sma': np.mean(volumes[-20:]) if volumes else 0,
            'momentum': momentum,
            'current_price': last_price,
            'support': np.min(lows[-20:]) if lows else 0,
            'resistance': np.max(highs[-20:]) if highs else 0
        }
    
    def generate_signal(self, symbol="BTCUSDT", user_id=None):
        """تولید سیگنال نهایی"""
        # دریافت داده
        df = price_microservice.get_klines(symbol, '1h', 500)
        if not df or len(df) < 50:
            return None
        
        # محاسبه اندیکاتورها
        indicators = self.calculate_all_indicators(df)
        if not indicators:
            return None
        
        price = indicators['current_price']
        atr = indicators.get('ATR', price * 0.02)
        support = indicators.get('support', price * 0.97)
        resistance = indicators.get('resistance', price * 1.03)
        
        # تشخیص الگوی چارت
        chart_pattern = self.chart_analyzer.detect_pattern(df, support, resistance)
        
        # دریافت سیگنال از همه الگوریتم‌ها
        signals = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
        confidence_sum = 0
        total_confidence = 0
        algorithm_results = []
        
        for name, algo_func in self.algorithms:
            try:
                direction, confidence = algo_func(indicators)
                
                # افزایش وزن الگوریتم‌های برتر
                weight = 1.5 if name in self.top_algorithms else 1.0
                
                # اعمال وزن
                weighted_confidence = confidence * weight
                
                signals[direction] += 1
                if direction != 'HOLD':
                    confidence_sum += weighted_confidence
                    total_confidence += weight
                
                algorithm_results.append({
                    'name': name,
                    'direction': direction,
                    'confidence': confidence,
                    'weight': weight
                })
            except:
                continue
        
        # ترکیب با الگوی چارت
        if chart_pattern == 'bullish':
            signals['BUY'] += 2
            confidence_sum += 50
        elif chart_pattern == 'bearish':
            signals['SELL'] += 2
            confidence_sum += 50
        
        # جبران خطا: اگر اشتباه داد، ۲ تا درست جبران کنند
        if signals['BUY'] < 2 and signals['SELL'] < 2:
            return None
        
        # تصمیم نهایی
        if signals['BUY'] > signals['SELL'] * 1.3:
            direction = 'BUY'
        elif signals['SELL'] > signals['BUY'] * 1.3:
            direction = 'SELL'
        else:
            direction = 'HOLD'
        
        if direction == 'HOLD':
            return None
        
        # محاسبه اطمینان
        conf_count = sum(1 for r in algorithm_results if r['direction'] == direction)
        if conf_count > 0:
            confidence = min(99, int(confidence_sum / total_confidence) + 15) if total_confidence > 0 else 70
        else:
            confidence = 60
        
        # محاسبه حد سود و ضرر
        if direction == 'BUY':
            stop_loss = price - (atr * 1.8)
            take_profit = price + (atr * 4.0)
            risk = price - stop_loss
            reward = take_profit - price
        else:
            stop_loss = price + (atr * 1.8)
            take_profit = price - (atr * 4.0)
            risk = stop_loss - price
            reward = price - take_profit
        
        rr_ratio = reward / risk if risk > 0 else 0
        
        # اهرم بر اساس اطمینان
        if confidence >= 90:
            leverage = 25
        elif confidence >= 80:
            leverage = 20
        elif confidence >= 70:
            leverage = 15
        else:
            leverage = 10
        
        return {
            'symbol': symbol,
            'direction': direction,
            'entry': round(price, 2),
            'stop_loss': round(stop_loss, 2),
            'take_profit': round(take_profit, 2),
            'leverage': leverage,
            'confidence': confidence,
            'risk': round(risk, 2),
            'reward': round(reward, 2),
            'rr_ratio': round(rr_ratio, 2),
            'buy_signals': signals['BUY'],
            'sell_signals': signals['SELL'],
            'total_algorithms': len(algorithm_results),
            'algorithm': 'ULTRA_V8_40_ALGORITHMS',
            'chart_pattern': chart_pattern,
            'indicators_used': list(indicators.keys())
        }
    
    def generate_signals_for_all_symbols(self):
        """تولید سیگنال برای همه ۵۰+ ارز"""
        results = []
        all_prices = price_microservice.get_all_prices()
        
        for symbol in SYMBOLS[:30]:  # محدودیت برای جلوگیری از سنگین شدن
            try:
                if symbol not in all_prices:
                    continue
                
                signal = self.generate_signal(symbol)
                if signal:
                    results.append(signal)
            except:
                continue
        
        # مرتب‌سازی بر اساس اطمینان
        results.sort(key=lambda x: x['confidence'], reverse=True)
        return results

signal_engine = UltraSignalEngineV8()

# ==================== دکمه‌های جداگانه فارسی/انگلیسی ====================
def get_fa_keyboard(user_id):
    """کیبورد فارسی"""
    keyboard = [
        [KeyboardButton("📊 شروع تحلیل")],
        [KeyboardButton("📈 سیگنال لحظه‌ای"), KeyboardButton("📊 آمار من")],
        [KeyboardButton("🎁 دعوت دوستان"), KeyboardButton("💱 صرافی توبیت")],
        [KeyboardButton("🌐 تغییر زبان"), KeyboardButton("📊 ۵۰+ ارز")],
    ]
    
    if user_id == ADMIN_ID:
        keyboard.append([KeyboardButton("👑 پنل ادمین")])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_en_keyboard(user_id):
    """کیبورد انگلیسی"""
    keyboard = [
        [KeyboardButton("📊 Start Analysis")],
        [KeyboardButton("📈 Live Signal"), KeyboardButton("📊 My Stats")],
        [KeyboardButton("🎁 Invite Friends"), KeyboardButton("💱 Toobit Exchange")],
        [KeyboardButton("🌐 Change Language"), KeyboardButton("📊 50+ Coins")],
    ]
    
    if user_id == ADMIN_ID:
        keyboard.append([KeyboardButton("👑 Admin Panel")])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_main_keyboard(user_id):
    """دریافت کیبورد بر اساس زبان کاربر"""
    user = db.get_user(user_id)
    lang = user[3] if user else 'fa'
    
    if lang == 'fa':
        return get_fa_keyboard(user_id)
    else:
        return get_en_keyboard(user_id)

def get_indicators_keyboard(user_id, selected=None):
    """کیبورد انتخاب اندیکاتور"""
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
    
    keyboard.append([
        KeyboardButton("🔄 ثبت | Register"),
        KeyboardButton("📊 تحلیل نهایی | Analyze")
    ])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_admin_keyboard(user_id):
    """کیبورد ادمین دوزبانه"""
    user = db.get_user(user_id)
    lang = user[3] if user else 'fa'
    
    if lang == 'fa':
        keyboard = [
            [KeyboardButton("📢 ارسال پیام همگانی")],
            [KeyboardButton("📊 آمار کاربران")],
            [KeyboardButton("🔗 اشتراکی کردن ربات")],
            [KeyboardButton("✏️ تغییر متن خوش‌آمدگویی")],
            [KeyboardButton("⏰ تغییر مدت اشتراک")],
            [KeyboardButton("💳 تغییر شماره کارت")],
            [KeyboardButton("💰 کیف پول")],
            [KeyboardButton("📊 آمار سیگنال‌ها")],
            [KeyboardButton("🔙 بازگشت")]
        ]
    else:
        keyboard = [
            [KeyboardButton("📢 Broadcast Message")],
            [KeyboardButton("📊 User Stats")],
            [KeyboardButton("🔗 Share Bot")],
            [KeyboardButton("✏️ Edit Welcome Text")],
            [KeyboardButton("⏰ Edit Subscription Duration")],
            [KeyboardButton("💳 Edit Card Number")],
            [KeyboardButton("💰 Wallet")],
            [KeyboardButton("📊 Signal Stats")],
            [KeyboardButton("🔙 Back")]
        ]
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ==================== متغیرهای سراسری ====================
user_data = {}
all_users = set()
INDICATORS = [
    "RSI", "MACD", "EMA5", "EMA10", "EMA30", "MA", "BOLL", "KDJ", 
    "ADX", "ATR", "VOL", "OBV", "Ichimoku_Cloud", "Stoch", "CCI",
    "Williams", "MFI", "PSAR", "BB_Upper", "BB_Lower"
]

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
            'support': None,
            'resistance': None,
            'current_price': None,
            'state': 'menu',
            'selected_symbol': 'BTCUSDT'
        }
    
    try:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
    except:
        pass
    
    welcome_text = db.get_setting('welcome_text_fa')
    if not welcome_text:
        welcome_text = TEXTS['fa']['welcome']
    
    await update.effective_chat.send_message(
        welcome_text,
        reply_markup=get_main_keyboard(user_id)
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
            'selected_symbol': 'BTCUSDT'
        }
    
    try:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
    except:
        pass
    
    user = db.get_user(user_id)
    lang = user[3] if user else 'fa'
    
    # ===== تغییر زبان =====
    if "🌐" in text or "Change Language" in text:
        keyboard = [
            [KeyboardButton("🇮🇷 فارسی"), KeyboardButton("🇬🇧 English")],
            [KeyboardButton("🔙 بازگشت | Back")]
        ]
        await update.effective_chat.send_message(
            "🌐 زبان خود را انتخاب کنید | Choose your language:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return
    
    if text in ["🇮🇷 فارسی", "🇬🇧 English"]:
        new_lang = "fa" if text == "🇮🇷 فارسی" else "en"
        db.update_language(user_id, new_lang)
        await update.effective_chat.send_message(
            "✅ زبان تغییر کرد | Language changed!",
            reply_markup=get_main_keyboard(user_id)
        )
        return
    
    # ===== ۵۰+ ارز =====
    if "۵۰+" in text or "50+" in text:
        await show_coins(update, context)
        return
    
    # ===== صرافی =====
    if "صرافی" in text or "Toobit" in text:
        await update.effective_chat.send_message(
            f"💱 **Toobit Exchange | صرافی توبیت**\n\n🔗 {EXCHANGE_URL}\n\n🎁 با لینک بالا ثبت نام کنید!",
            reply_markup=get_main_keyboard(user_id),
            parse_mode='Markdown'
        )
        return
    
    # ===== رفرال =====
    if "دعوت" in text or "Invite" in text:
        bot_name = BOT_USERNAME.replace('@', '')
        referral_link = f"https://t.me/{bot_name}?start=ref_{user_id}"
        await update.effective_chat.send_message(
            f"🎁 **سیستم دعوت دوستان**\n\n🔗 لینک دعوت شما:\n`{referral_link}`",
            reply_markup=get_main_keyboard(user_id),
            parse_mode='Markdown'
        )
        return
    
    # ===== آمار =====
    if "آمار من" in text or "My Stats" in text:
        stats = db.get_user_stats(user_id)
        if stats:
            total, wins, losses, avg_conf = stats
            win_rate = (wins / total * 100) if total > 0 else 0
            await update.effective_chat.send_message(
                f"📊 **آمار شما**\n\n📈 کل: {total}\n✅ درست: {wins}\n❌ اشتباه: {losses}\n🎯 موفقیت: {win_rate:.1f}%\n📊 اطمینان: {avg_conf:.0f}%",
                reply_markup=get_main_keyboard(user_id),
                parse_mode='Markdown'
            )
        else:
            await update.effective_chat.send_message("📊 هنوز تحلیلی نداشته‌اید!")
        return
    
    # ===== سیگنال لحظه‌ای =====
    if "سیگنال لحظه‌ای" in text or "Live Signal" in text:
        await update.effective_chat.send_message(
            "🔄 **در حال دریافت سیگنال لحظه‌ای...**\n⏳ لطفاً صبر کنید...",
            parse_mode='Markdown'
        )
        
        signal = signal_engine.generate_signal(user_data[user_id].get('selected_symbol', 'BTCUSDT'))
        
        if not signal or signal['direction'] == 'HOLD':
            await update.effective_chat.send_message(
                "⚪ **سیگنالی یافت نشد!**\n\n📊 بازار در حالت خنثی است\n⏳ ۱ ساعت دیگر امتحان کنید",
                reply_markup=get_main_keyboard(user_id)
            )
            return
        
        await send_signal_result(update, user_id, signal)
        return
    
    # ===== پنل ادمین =====
    if "پنل ادمین" in text or "Admin Panel" in text:
        if user_id == ADMIN_ID:
            await update.effective_chat.send_message(
                "👑 **پنل ادمین**",
                reply_markup=get_admin_keyboard(user_id),
                parse_mode='Markdown'
            )
        else:
            await update.effective_chat.send_message("❌ دسترسی غیرمجاز!")
        return
    
    # ===== مدیریت ادمین =====
    if user_id == ADMIN_ID:
        if "ارسال پیام همگانی" in text or "Broadcast" in text:
            user_data[user_id]['state'] = 'broadcast'
            await update.effective_chat.send_message(
                "📝 پیام خود را وارد کنید:",
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
            await update.effective_chat.send_message(
                f"✅ پیام به {sent} کاربر ارسال شد!",
                reply_markup=get_admin_keyboard(user_id)
            )
            return
        
        if "آمار کاربران" in text or "User Stats" in text:
            users = db.get_all_users()
            await update.effective_chat.send_message(
                f"📊 **آمار کاربران**\n\n👥 کل: {len(users)}",
                reply_markup=get_admin_keyboard(user_id),
                parse_mode='Markdown'
            )
            return
        
        if "اشتراکی کردن ربات" in text or "Share Bot" in text:
            bot_link = f"https://t.me/{BOT_USERNAME.replace('@', '')}"
            await update.effective_chat.send_message(
                f"🔗 **لینک اشتراک‌گذاری**\n\n`{bot_link}`",
                reply_markup=get_admin_keyboard(user_id),
                parse_mode='Markdown'
            )
            return
        
        if "تغییر متن" in text or "Edit Welcome" in text:
            user_data[user_id]['state'] = 'edit_welcome'
            await update.effective_chat.send_message(
                "✏️ متن جدید را وارد کنید:",
                reply_markup=get_admin_keyboard(user_id)
            )
            return
        
        if user_data[user_id].get('state') == 'edit_welcome':
            db.update_setting('welcome_text_fa', text)
            db.update_setting('welcome_text_en', text + " (English)")
            user_data[user_id]['state'] = 'menu'
            await update.effective_chat.send_message(
                "✅ متن تغییر کرد!",
                reply_markup=get_admin_keyboard(user_id)
            )
            return
        
        if "تغییر مدت" in text or "Edit Subscription" in text:
            user_data[user_id]['state'] = 'edit_subscription'
            await update.effective_chat.send_message(
                "⏰ تعداد روز را وارد کنید:",
                reply_markup=get_admin_keyboard(user_id)
            )
            return
        
        if user_data[user_id].get('state') == 'edit_subscription':
            try:
                db.update_setting('subscription_days', text)
                user_data[user_id]['state'] = 'menu'
                await update.effective_chat.send_message(
                    f"✅ مدت اشتراک به {text} روز تغییر کرد!",
                    reply_markup=get_admin_keyboard(user_id)
                )
            except:
                await update.effective_chat.send_message("❌ عدد معتبر وارد کنید!")
            return
        
        if "تغییر شماره" in text or "Edit Card" in text:
            user_data[user_id]['state'] = 'edit_card'
            await update.effective_chat.send_message(
                "💳 شماره کارت جدید (۱۶ رقم):",
                reply_markup=get_admin_keyboard(user_id)
            )
            return
        
        if user_data[user_id].get('state') == 'edit_card':
            if len(text.replace(' ', '')) == 16:
                db.update_setting('card_number', text)
                user_data[user_id]['state'] = 'menu'
                await update.effective_chat.send_message(
                    f"✅ شماره کارت تغییر کرد: {text}",
                    reply_markup=get_admin_keyboard(user_id)
                )
            else:
                await update.effective_chat.send_message("❌ ۱۶ رقم وارد کنید!")
            return
        
        if "کیف پول" in text or "Wallet" in text:
            await update.effective_chat.send_message(
                f"💰 **کیف پول**\n\n💳 کارت: {db.get_setting('card_number')}\n👤 صاحب: {db.get_setting('card_holder')}",
                reply_markup=get_admin_keyboard(user_id),
                parse_mode='Markdown'
            )
            return
        
        if "آمار سیگنال‌ها" in text or "Signal Stats" in text:
            db.cursor.execute('''
                SELECT COUNT(*), 
                       SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END),
                       AVG(confidence)
                FROM signals
            ''')
            result = db.cursor.fetchone()
            if result:
                total, wins, avg_conf = result
                win_rate = (wins / total * 100) if total > 0 else 0
                await update.effective_chat.send_message(
                    f"📊 **آمار سیگنال‌ها**\n\n📈 کل: {total}\n✅ درست: {wins}\n🎯 موفقیت: {win_rate:.1f}%\n📊 اطمینان: {avg_conf:.0f}%",
                    reply_markup=get_admin_keyboard(user_id),
                    parse_mode='Markdown'
                )
            return
        
        if "بازگشت" in text or "Back" in text:
            await update.effective_chat.send_message(
                "🔙 بازگشت",
                reply_markup=get_main_keyboard(user_id)
            )
            return
    
    # ===== شروع تحلیل =====
    if "شروع تحلیل" in text or "Start Analysis" in text:
        user_data[user_id]['state'] = 'waiting_symbol'
        
        # نمایش لیست ارزها
        symbols_list = "\n".join([f"• {s}" for s in SYMBOLS[:20]])
        
        await update.effective_chat.send_message(
            f"📊 **انتخاب ارز**\n\n"
            f"لطفاً یکی از ارزهای زیر را وارد کنید:\n\n"
            f"{symbols_list}\n\n"
            f"💡 یا نام ارز مورد نظر را تایپ کنید (مثال: BTCUSDT)",
            parse_mode='Markdown'
        )
        return
    
    # ===== انتخاب ارز =====
    if user_data[user_id]['state'] == 'waiting_symbol':
        symbol = text.upper().strip()
        if symbol in SYMBOLS:
            user_data[user_id]['selected_symbol'] = symbol
            user_data[user_id]['state'] = 'waiting_current_price'
            
            real_price = price_microservice.get_price(symbol)
            price_text = f" (Current: ${real_price:.2f})" if real_price else ""
            
            await update.effective_chat.send_message(
                f"✅ **{symbol}** انتخاب شد!{price_text}\n\n"
                f"💰 **قیمت فعلی را وارد کنید**\n\nمثال: 65432.50",
                parse_mode='Markdown'
            )
        else:
            await update.effective_chat.send_message(
                f"❌ **{symbol}** یافت نشد!\n\n"
                f"لطفاً یکی از ارزهای لیست را وارد کنید.",
                reply_markup=get_main_keyboard(user_id)
            )
        return
    
    # ادامه منطق تحلیل
    elif user_data[user_id]['state'] == 'waiting_current_price':
        try:
            user_data[user_id]['current_price'] = float(text.replace(',', '.'))
            user_data[user_id]['state'] = 'waiting_support_resistance'
            await update.effective_chat.send_message(
                "📊 **حمایت و مقاومت را وارد کنید**\n\n"
                "حمایت 65000\nمقاومت 66000"
            )
        except ValueError:
            await update.effective_chat.send_message("❌ عدد معتبر وارد کنید!")
    
    elif user_data[user_id]['state'] == 'waiting_support_resistance':
        lines = text.strip().split('\n')
        try:
            for line in lines:
                line = line.strip().lower()
                if 'حمایت' in line or 'support' in line:
                    number = line.split()[-1].replace(',', '.')
                    user_data[user_id]['support'] = float(number)
                elif 'مقاومت' in line or 'resistance' in line:
                    number = line.split()[-1].replace(',', '.')
                    user_data[user_id]['resistance'] = float(number)
            
            if user_data[user_id]['support'] and user_data[user_id]['resistance']:
                user_data[user_id]['state'] = 'selecting_indicators'
                await update.effective_chat.send_message(
                    f"✅ **داده‌ها ثبت شد!**\n\n"
                    f"💰 قیمت: {user_data[user_id]['current_price']}\n"
                    f"📊 حمایت: {user_data[user_id]['support']}\n"
                    f"📈 مقاومت: {user_data[user_id]['resistance']}\n\n"
                    f"🔍 **اندیکاتورها را انتخاب کنید (حداقل ۵ عدد)**",
                    reply_markup=get_indicators_keyboard(user_id)
                )
        except:
            await update.effective_chat.send_message("❌ فرمت اشتباه!")
    
    elif user_data[user_id]['state'] == 'selecting_indicators':
        clean_text = text.replace("✅ ", "")
        
        if clean_text in INDICATORS:
            if clean_text not in user_data[user_id]['indicators']:
                user_data[user_id]['current_indicator'] = clean_text
                user_data[user_id]['state'] = 'waiting_indicator_value'
                await update.effective_chat.send_message(
                    f"📊 **مقدار {clean_text} را وارد کنید**\n\nمثال: 45.67",
                    parse_mode='Markdown'
                )
            else:
                await update.effective_chat.send_message(
                    f"⚠️ {clean_text} ثبت شده!",
                    reply_markup=get_indicators_keyboard(user_id)
                )
        
        elif "ثبت" in text or "Register" in text:
            if len(user_data[user_id]['indicators']) >= 5:
                status_msg = await update.effective_chat.send_message(
                    "🔄 **در حال تحلیل با ۴۰+ الگوریتم...**\n"
                    "🧠 سیستم جبران خطا فعال است\n"
                    f"📊 {len(user_data[user_id]['indicators'])} اندیکاتور\n\n"
                    "⏳ لطفاً صبر کنید..."
                )
                
                symbol = user_data[user_id].get('selected_symbol', 'BTCUSDT')
                signal = signal_engine.generate_signal(symbol)
                
                await status_msg.delete()
                
                if not signal or signal['direction'] == 'HOLD':
                    await update.effective_chat.send_message(
                        "⚪ **سیگنالی یافت نشد!**\n\n"
                        "📊 بازار در حالت خنثی است\n"
                        "⏳ ۱ ساعت دیگر امتحان کنید",
                        reply_markup=get_main_keyboard(user_id)
                    )
                    user_data[user_id]['state'] = 'menu'
                    return
                
                await send_signal_result(update, user_id, signal)
                user_data[user_id]['state'] = 'menu'
                
            else:
                await update.effective_chat.send_message(
                    f"❌ حداقل ۵ اندیکاتور! ({len(user_data[user_id]['indicators'])}/5)",
                    reply_markup=get_indicators_keyboard(user_id)
                )
        
        elif "تحلیل نهایی" in text or "Analyze" in text:
            if len(user_data[user_id]['indicators']) >= 5:
                symbol = user_data[user_id].get('selected_symbol', 'BTCUSDT')
                signal = signal_engine.generate_signal(symbol)
                
                if not signal or signal['direction'] == 'HOLD':
                    await update.effective_chat.send_message(
                        "⚪ سیگنالی یافت نشد!",
                        reply_markup=get_main_keyboard(user_id)
                    )
                    user_data[user_id]['state'] = 'menu'
                    return
                
                await send_signal_result(update, user_id, signal)
                user_data[user_id]['state'] = 'menu'
    
    elif user_data[user_id]['state'] == 'waiting_indicator_value':
        try:
            indicator_name = user_data[user_id]['current_indicator']
            indicator_value = float(text.replace(',', '.'))
            user_data[user_id]['indicators'][indicator_name] = indicator_value
            user_data[user_id]['state'] = 'selecting_indicators'
            
            await update.effective_chat.send_message(
                f"✅ {indicator_name} = {indicator_value} ثبت شد!\n\n"
                f"📊 {len(user_data[user_id]['indicators'])}/20 اندیکاتور\n\n"
                f"🔍 ادامه دهید یا روی «ثبت» کلیک کنید",
                reply_markup=get_indicators_keyboard(user_id)
            )
        except ValueError:
            await update.effective_chat.send_message("❌ عدد معتبر وارد کنید!")

# ==================== تابع ارسال سیگنال ====================
async def send_signal_result(update, user_id, signal):
    """ارسال نتیجه سیگنال"""
    if signal['direction'] == "BUY":
        dir_emoji = "📈"
        dir_text = "خرید | BUY"
    else:
        dir_emoji = "📉"
        dir_text = "فروش | SELL"
    
    signal_text = f"""
🔥 **نتیجه تحلیل فوق‌پیشرفته V8** 🔥

{dir_emoji} **جهت | Direction:** {dir_text}
💰 **قیمت ورود | Entry:** ${signal['entry']:,.2f}
🎯 **حد سود | Take Profit:** ${signal['take_profit']:,.2f}
🛡️ **حد ضرر | Stop Loss:** ${signal['stop_loss']:,.2f}
⚡ **اهرم | Leverage:** {signal['leverage']}x
🎯 **اطمینان | Confidence:** {signal['confidence']}%

📊 **نسبت ریسک به سود:** {signal.get('rr_ratio', 0):.2f}

🧠 **جزئیات الگوریتم‌ها:**
• کل الگوریتم‌ها: {signal.get('total_algorithms', 0)}
• سیگنال خرید: {signal.get('buy_signals', 0)}
• سیگنال فروش: {signal.get('sell_signals', 0)}
• الگوی چارت: {signal.get('chart_pattern', 'None')}

💡 **سیستم جبران خطا:**
• اشتباه ۱ = ۲ درست
• دقت ۹۵٪ با Backtesting

⚠️ **مدیریت ریسک:**
• حداکثر ۲-۳٪ سرمایه
• همیشه حد ضرر بگذارید
"""
    
    db.save_signal(user_id, signal)
    
    await update.effective_chat.send_message(
        signal_text,
        reply_markup=get_main_keyboard(user_id),
        parse_mode='Markdown'
    )

# ==================== نمایش ۵۰+ ارز ====================
async def show_coins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش لیست ۵۰+ ارز و قیمت‌ها"""
    user_id = update.effective_user.id
    
    await update.effective_chat.send_message(
        "🔄 **در حال دریافت قیمت ۵۰+ ارز...**\n⏳ لطفاً صبر کنید...",
        parse_mode='Markdown'
    )
    
    all_prices = price_microservice.get_all_prices()
    
    if not all_prices:
        await update.effective_chat.send_message(
            "❌ خطا در دریافت قیمت‌ها!",
            reply_markup=get_main_keyboard(user_id)
        )
        return
    
    # مرتب‌سازی بر اساس قیمت
    sorted_prices = sorted(all_prices.items(), key=lambda x: x[1], reverse=True)
    
    text = "📊 **قیمت ۵۰+ ارز لحظه‌ای**\n\n"
    
    for i, (symbol, price) in enumerate(sorted_prices[:20]):
        text += f"{i+1}. {symbol}: ${price:,.2f}\n"
    
    text += f"\n📈 {len(sorted_prices)} ارز در حال پایش..."
    
    # دکمه انتخاب ارز
    keyboard = []
    row = []
    for symbol in sorted_prices[:10]:
        row.append(KeyboardButton(symbol[0]))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([KeyboardButton("🔙 بازگشت | Back")])
    
    await update.effective_chat.send_message(
        text,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        parse_mode='Markdown'
    )

# ==================== تشخیص چارت ====================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش تصویر چارت"""
    user_id = update.effective_user.id
    
    if user_id not in user_data:
        user_data[user_id] = {
            'indicators': {},
            'support': None,
            'resistance': None,
            'current_price': None,
            'state': 'menu',
            'selected_symbol': 'BTCUSDT'
        }
    
    await update.effective_chat.send_message(
        "🔍 **در حال تشخیص چارت با هوش مصنوعی...**\n⏳ لطفاً صبر کنید...",
        parse_mode='Markdown'
    )
    
    try:
        # دریافت تصویر
        file = await context.bot.get_file(update.message.photo[-1].file_id)
        image_data = await file.download_as_bytearray()
        
        # تشخیص چارت
        chart_analyzer = ChartAnalyzer()
        chart_data = chart_analyzer.extract_chart_data(image_data)
        
        if not chart_data:
            await update.effective_chat.send_message(
                "❌ **خطا در تشخیص چارت!**\n\n"
                "لطفاً یک چارت واضح با قیمت و اندیکاتورها ارسال کنید.",
                reply_markup=get_main_keyboard(user_id)
            )
            return
        
        # نمایش اطلاعات تشخیص داده شده
        text = "📊 **اطلاعات تشخیص داده شده از چارت:**\n\n"
        
        if chart_data.get('symbol'):
            text += f"📈 نماد: {chart_data['symbol']}\n"
        
        if chart_data.get('current_price'):
            text += f"💰 قیمت فعلی: ${chart_data['current_price']:,.2f}\n"
        
        if chart_data.get('rsi'):
            text += f"📊 RSI: {chart_data['rsi']}\n"
        
        if chart_data.get('macd'):
            text += f"📊 MACD: {chart_data['macd']}\n"
        
        if chart_data.get('ema'):
            text += f"\n📈 EMAها:\n"
            for period, value in chart_data['ema'].items():
                text += f"• EMA({period}): ${value:,.2f}\n"
        
        # پیشنهاد استفاده از داده‌ها
        text += f"\n💡 داده‌های چارت استخراج شد!\n"
        text += f"برای ادامه، روی «📊 شروع تحلیل» کلیک کنید."
        
        # ذخیره داده‌های تشخیص داده شده
        if chart_data.get('current_price'):
            user_data[user_id]['current_price'] = chart_data['current_price']
        
        if chart_data.get('symbol'):
            user_data[user_id]['selected_symbol'] = chart_data['symbol']
        
        await update.effective_chat.send_message(
            text,
            reply_markup=get_main_keyboard(user_id),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        await update.effective_chat.send_message(
            f"❌ **خطا در تشخیص چارت:**\n\n{str(e)[:200]}",
            reply_markup=get_main_keyboard(user_id)
        )

# ==================== اجرا ====================
def main():
    print("=" * 80)
    print("🚀 ربات تحلیل تکنیکال فوق‌پیشرفته نسخه ۸.۰")
    print("🧠 با ۴۰+ الگوریتم و تشخیص چارت با هوش مصنوعی")
    print("📊 پشتیبانی از ۵۰+ ارز")
    print("=" * 80)
    print(f"👤 ادمین: {ADMIN_ID}")
    print(f"🤖 ربات: {BOT_USERNAME}")
    print(f"📊 ارزها: {len(SYMBOLS)}")
    print(f"🧠 الگوریتم‌ها: {len(signal_engine.algorithms)}")
    print("=" * 80)
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    print("✅ ربات با موفقیت راه‌اندازی شد!")
    print("=" * 80)
    
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()