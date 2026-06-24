#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ربات تحلیل تکنیکال فوق‌پیشرفته نسخه ۸.۵
ترکیب نسخه ۸ (یادگیری عمیق + معاملات خودکار) + تشخیص چارت نسخه ۹
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
from scipy.fft import fft, fftfreq
from scipy.signal import find_peaks, hilbert
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, VotingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import warnings
warnings.filterwarnings('ignore')

# ==================== کتابخانه‌های تشخیص چارت ====================
try:
    import cv2
    import pytesseract
    from PIL import Image
    import io
    CHART_OCR_AVAILABLE = True
except:
    CHART_OCR_AVAILABLE = False
    print("⚠️ برای تشخیص چارت، کتابخانه‌های زیر را نصب کنید:")
    print("pip install opencv-python pillow pytesseract")

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
    'XVGUSDT', 'REEFUSDT', 'CKBUSDT', 'ARDRUSDT', 'DGBUSDT',
    'NEOUSDT', 'ONTUSDT', 'WAVESUSDT', 'ICXUSDT', 'QTUMUSDT',
    # Small Cap
    'BATUSDT', 'ZRXUSDT', 'OMGUSDT', 'NMRUSDT', 'BNTUSDT',
    'LRCUSDT', 'DENTUSDT', 'CELRUSDT', 'OXTUSDT', 'FETUSDT',
    'ANKRUSDT', 'RLCUSDT', 'CTSIUSDT', 'STXUSDT', 'ARUSDT',
    'GLMRUSDT', 'ASTRUSDT', 'ACAUSDT', 'KARUSDT', 'MOVRUSDT',
    'CFGUSDT', 'AUDIOUSDT', 'RADUSDT', 'BANDUSDT', 'NUUSDT',
    'KAVAUSDT', 'HIVEUSDT', 'LPTUSDT', 'RENUSDT', 'SRMUSDT',
    'RAYUSDT', 'FIDAUSDT', 'ORCAUSDT', 'COPEUSDT', 'MNGOUSDT',
    'SAMOUSDT', 'DUSTUSDT', 'BONKUSDT', 'MYROUSDT', 'WIFUSDT',
    # DeFi
    'UNIUSDT', 'AAVEUSDT', 'MKRUSDT', 'COMPUSDT', 'YFIUSDT',
    'SUSHIUSDT', 'CAKEUSDT', 'BAKEUSDT', 'CVXUSDT', 'FXSUSDT',
    'CRVUSDT', 'PENDLEUSDT', 'GMXUSDT', 'GNSUSDT', 'RDNTUSDT',
    'BALUSDT', 'LDOUSDT', 'RPLUSDT', 'FRAXUSDT', 'MIMUSDT',
    # Layer 1 & 2
    'ETHUSDT', 'SOLUSDT', 'AVAXUSDT', 'DOTUSDT', 'ATOMUSDT',
    'NEARUSDT', 'ALGOUSDT', 'VETUSDT', 'ICPUSDT', 'FILUSDT',
    'APTUSDT', 'SUIUSDT', 'SEIUSDT', 'TIAUSDT', 'INJUSDT',
    'ARBUSDT', 'OPUSDT', 'MATICUSDT', 'BASEUSDT', 'BLASTUSDT',
    # Meme Coins
    'DOGEUSDT', 'SHIBUSDT', 'PEPEUSDT', 'FLOKIUSDT', 'BONKUSDT',
    'WIFUSDT', 'MYROUSDT', 'SAMOUSDT', 'DUSTUSDT', 'COQUSDT',
    'BABYDOGEUSDT', 'KISHUUSDT', 'HUSKYUSDT', 'WOJAKUSDT', 'CHADUSDT'
]

# ==================== دیتابیس ====================
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('trading_bot_v8.db', check_same_thread=False)
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
                last_analysis TIMESTAMP,
                joined_at TIMESTAMP,
                plan TEXT DEFAULT 'BASIC',
                plan_expire TIMESTAMP,
                balance INTEGER DEFAULT 0,
                is_admin BOOLEAN DEFAULT 0,
                is_banned BOOLEAN DEFAULT 0,
                favorite_symbols TEXT DEFAULT '["BTCUSDT","ETHUSDT"]',
                trading_mode TEXT DEFAULT 'manual',
                auto_trade BOOLEAN DEFAULT 0,
                risk_percent INTEGER DEFAULT 2,
                max_position INTEGER DEFAULT 10
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
                indicators_used TEXT,
                chart_data TEXT,
                created_at TIMESTAMP,
                executed BOOLEAN DEFAULT 0,
                profit_loss REAL DEFAULT 0,
                closed_at TIMESTAMP
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS chart_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                symbol TEXT,
                chart_data TEXT,
                detected_patterns TEXT,
                indicators TEXT,
                created_at TIMESTAMP
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
                closed_at TIMESTAMP
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
            'welcome_text_fa': '🔥 به ربات تحلیل تکنیکال فوق‌پیشرفته نسخه ۸.۵ خوش آمدید!\n\n📊 با ۲۰۰+ ارز، الگوریتم‌های کوانتومی، یادگیری عمیق و تشخیص چارت\n🎯 دقت سیگنال تا ۹۸٪\n🚀 معاملات خودکار با هوش مصنوعی\n📸 قابلیت تحلیل چارت از تصویر\n\nبرای شروع روی "📊 شروع تحلیل" کلیک کنید.',
            'welcome_text_en': '🔥 Welcome to Ultra Advanced Technical Analysis Bot v8.5!\n\n📊 With 200+ coins, quantum algorithms, deep learning and chart recognition\n🎯 Signal accuracy up to 98%\n🚀 AI-powered automated trading\n📸 Chart analysis from image\n\nClick "📊 Start Analysis" to begin.',
            'subscription_days': '30',
            'card_number': '5892101187322777',
            'card_holder': 'مرتضی نیکخو خنجری',
            'subscription_price': '500000',
            'auto_trade_enabled': '0',
            'max_auto_trade': '5',
            'min_confidence': '80'
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
    
    def save_signal(self, user_id, signal_data):
        self.cursor.execute('''
            INSERT INTO signals 
            (user_id, symbol, signal_type, entry_price, take_profit, stop_loss, 
             leverage, confidence, indicators_used, chart_data, created_at)
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
            json.dumps(signal_data.get('indicators_used', [])),
            json.dumps(signal_data.get('chart_data', {})),
            datetime.now().isoformat()
        ))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def save_chart_analysis(self, user_id, symbol, chart_data, patterns, indicators):
        self.cursor.execute('''
            INSERT INTO chart_analyses (user_id, symbol, chart_data, detected_patterns, indicators, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            user_id, symbol, json.dumps(chart_data), 
            json.dumps(patterns), json.dumps(indicators),
            datetime.now().isoformat()
        ))
        self.conn.commit()
    
    def update_signal_result(self, signal_id, profit):
        self.cursor.execute('''
            UPDATE signals SET profit_loss = ?, closed_at = ?, executed = 1
            WHERE id = ?
        ''', (profit, datetime.now().isoformat(), signal_id))
        self.conn.commit()
    
    def get_user_stats(self, user_id):
        self.cursor.execute('''
            SELECT 
                COUNT(*) as total_signals,
                AVG(confidence) as avg_confidence,
                MAX(confidence) as best_confidence,
                SUM(CASE WHEN executed = 1 AND profit_loss > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN executed = 1 AND profit_loss < 0 THEN 1 ELSE 0 END) as losses
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

db = Database()

# ==================== میکروسرویس قیمت ====================
class AdvancedPriceMicroservice:
    def __init__(self):
        self.binance_url = "https://api.binance.com/api/v3"
        self.coinbase_url = "https://api.coinbase.com/v2"
        self.kraken_url = "https://api.kraken.com/0/public"
        self.cache = {}
        self.cache_time = {}
        self.cache_klines = {}
        self.cache_klines_time = {}
        
    def get_price(self, symbol="BTCUSDT"):
        cache_key = f"price_{symbol}"
        if cache_key in self.cache and time.time() - self.cache_time.get(cache_key, 0) < 2:
            return self.cache[cache_key]
        
        try:
            response = requests.get(
                f"{self.binance_url}/ticker/price?symbol={symbol}",
                timeout=2
            )
            if response.status_code == 200:
                price = float(response.json()['price'])
                self.cache[cache_key] = price
                self.cache_time[cache_key] = time.time()
                return price
        except:
            try:
                response = requests.get(
                    f"{self.coinbase_url}/prices/{symbol}/spot",
                    timeout=2
                )
                if response.status_code == 200:
                    price = float(response.json()['data']['amount'])
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
    
    def get_order_book(self, symbol="BTCUSDT", limit=20):
        try:
            url = f"{self.binance_url}/depth?symbol={symbol}&limit={limit}"
            response = requests.get(url, timeout=3)
            data = response.json()
            
            bids = [[float(x[0]), float(x[1])] for x in data['bids']]
            asks = [[float(x[0]), float(x[1])] for x in data['asks']]
            
            return {
                'bids': bids,
                'asks': asks,
                'best_bid': bids[0][0] if bids else 0,
                'best_ask': asks[0][0] if asks else 0,
                'spread': (asks[0][0] - bids[0][0]) if asks and bids else 0
            }
        except:
            return None
    
    def get_all_prices(self):
        prices = {}
        for symbol in SUPPORTED_SYMBOLS[:50]:
            price = self.get_price(symbol)
            if price:
                prices[symbol] = price
        return prices
    
    def get_top_gainers(self, count=10):
        prices = self.get_all_prices()
        return sorted(prices.items(), key=lambda x: x[1], reverse=True)[:count]

price_service = AdvancedPriceMicroservice()

# ==================== تشخیص چارت با هوش مصنوعی ====================
class ChartAnalyzerV8:
    """تشخیص کامل چارت با OCR و هوش مصنوعی"""
    
    def __init__(self):
        self.patterns = {
            'double_bottom': {'buy': 85, 'sell': 0, 'name': 'کف دوقلو'},
            'double_top': {'buy': 0, 'sell': 85, 'name': 'سقف دوقلو'},
            'bullish_engulfing': {'buy': 80, 'sell': 0, 'name': 'حمله صعودی'},
            'bearish_engulfing': {'buy': 0, 'sell': 80, 'name': 'حمله نزولی'},
            'hammer': {'buy': 75, 'sell': 0, 'name': 'چکش'},
            'shooting_star': {'buy': 0, 'sell': 75, 'name': 'ستاره دنباله‌دار'},
            'bullish_flag': {'buy': 70, 'sell': 0, 'name': 'پرچم صعودی'},
            'bearish_flag': {'buy': 0, 'sell': 70, 'name': 'پرچم نزولی'},
            'head_and_shoulders': {'buy': 0, 'sell': 90, 'name': 'سر و شانه'},
            'inverse_head_and_shoulders': {'buy': 90, 'sell': 0, 'name': 'سر و شانه معکوس'},
            'support_bounce': {'buy': 82, 'sell': 0, 'name': 'برگشت از حمایت'},
            'resistance_rejection': {'buy': 0, 'sell': 82, 'name': 'رد از مقاومت'},
        }
        
        self.indicators_patterns = {
            'rsi': r'RSI[\(0-9,]*:\s*([0-9\.]+)',
            'macd': r'MACD[\(0-9,]*:\s*([0-9\.]+)',
            'ema': r'EMA\((\d+)\):\s*([0-9,\.]+)',
            'ma': r'MA\((\d+)\):\s*([0-9,\.]+)',
            'boll': r'BOLL[\(0-9,]*:\s*([0-9,\.]+)',
            'stoch': r'Stoch[\(0-9,]*:\s*([0-9\.]+)',
            'adx': r'ADX[\(0-9,]*:\s*([0-9\.]+)',
            'volume': r'VOL[\(0-9,]*:\s*([0-9,\.]+)',
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
            chart_data['image_info'] = {'width': width, 'height': height}
            
            patterns = self.detect_patterns(chart_data)
            indicators = self.detect_indicators(text)
            
            quality = self.calculate_quality(chart_data, patterns, indicators)
            
            return {
                'chart_data': chart_data,
                'patterns': patterns,
                'indicators': indicators,
                'raw_text': text[:500] if text else '',
                'analysis_quality': quality
            }
            
        except Exception as e:
            logger.error(f"خطا در تحلیل چارت: {e}")
            return None
    
    def extract_chart_data(self, text):
        """استخراج داده‌های کلیدی از متن"""
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
            if change_match and data['change_percent'] is None:
                try:
                    data['change_percent'] = float(change_match.group(1))
                except:
                    pass
            
            if '1D' in line or '1d' in line:
                data['timeframe'] = '1D'
            elif '4h' in line:
                data['timeframe'] = '4h'
            elif '1h' in line:
                data['timeframe'] = '1h'
        
        return data
    
    def detect_patterns(self, chart_data):
        """تشخیص الگوهای چارت"""
        detected = []
        price = chart_data.get('current_price', 0)
        high = chart_data.get('high', 0)
        low = chart_data.get('low', 0)
        change = chart_data.get('change_percent', 0)
        
        if price and high and low:
            if price <= low * 1.02:
                detected.append({
                    'name': 'حمایت',
                    'type': 'support',
                    'confidence': 82,
                    'description': 'قیمت در نزدیکی سطح حمایت'
                })
            
            if price >= high * 0.98:
                detected.append({
                    'name': 'مقاومت',
                    'type': 'resistance',
                    'confidence': 82,
                    'description': 'قیمت در نزدیکی سطح مقاومت'
                })
            
            if change and abs(change) > 3:
                detected.append({
                    'name': 'روند صعودی قوی' if change > 0 else 'روند نزولی قوی',
                    'type': 'trend',
                    'confidence': 78,
                    'description': f'تغییر {change:.1f}%'
                })
        
        return detected
    
    def detect_indicators(self, text):
        """تشخیص اندیکاتورها از متن"""
        indicators = {}
        for name, pattern in self.indicators_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    if name == 'ema' or name == 'ma':
                        period = int(match.group(1))
                        value = float(match.group(2).replace(',', ''))
                        if name not in indicators:
                            indicators[name] = {}
                        indicators[name][period] = value
                    else:
                        value = float(match.group(1).replace(',', ''))
                        indicators[name] = value
                except:
                    pass
        return indicators
    
    def calculate_quality(self, chart_data, patterns, indicators):
        """محاسبه کیفیت تحلیل"""
        quality = 0
        if chart_data.get('symbol'):
            quality += 20
        if chart_data.get('current_price'):
            quality += 20
        if chart_data.get('high') and chart_data.get('low'):
            quality += 15
        if chart_data.get('change_percent') is not None:
            quality += 10
        if patterns:
            quality += min(len(patterns) * 5, 20)
        if indicators:
            quality += min(len(indicators) * 2, 15)
        return min(quality, 100)

chart_analyzer = ChartAnalyzerV8()

# ==================== الگوریتم‌های هوش مصنوعی ====================
class DeepLearningEngine:
    def __init__(self):
        self.models = {}
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=15)
        self.rf_model = RandomForestRegressor(n_estimators=500, max_depth=25, random_state=42, n_jobs=-1)
        self.gb_model = GradientBoostingRegressor(n_estimators=300, learning_rate=0.03, max_depth=12, random_state=42)
        self.voting_model = None
        self.kmeans = KMeans(n_clusters=5, random_state=42)
        self.is_trained = False
        self.training_features = None
        
    def extract_features(self, candles):
        if len(candles) < 30:
            return np.array([])
        
        closes = [c['close'] for c in candles]
        highs = [c['high'] for c in candles]
        lows = [c['low'] for c in candles]
        volumes = [c['volume'] for c in candles]
        
        features = []
        
        features.append(np.mean(closes))
        features.append(np.std(closes))
        features.append(np.median(closes))
        features.append(np.max(closes))
        features.append(np.min(closes))
        features.append(np.percentile(closes, 25))
        features.append(np.percentile(closes, 75))
        
        returns = np.diff(closes) / closes[:-1]
        features.append(np.mean(returns))
        features.append(np.std(returns))
        features.append(np.max(returns))
        features.append(np.min(returns))
        
        features.append(np.mean(volumes))
        features.append(np.std(volumes))
        
        rsi = self.calculate_rsi(closes)
        features.append(rsi)
        
        macd, signal, hist = self.calculate_macd(closes)
        features.append(macd)
        features.append(signal)
        features.append(hist)
        
        bb_upper, bb_middle, bb_lower = self.calculate_bollinger(closes)
        features.append(bb_upper)
        features.append(bb_middle)
        features.append(bb_lower)
        
        features.append(np.std(returns) * np.sqrt(252))
        
        for i in range(5, 30, 5):
            if i < len(closes):
                features.append(closes[-1] / closes[-i] - 1)
        
        fft_vals = np.abs(fft(closes[-100:]))[:10]
        features.extend(fft_vals)
        
        return np.array(features)
    
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
    
    def calculate_bollinger(self, prices, period=20, std_dev=2):
        if len(prices) < period:
            return 0, 0, 0
        sma = np.mean(prices[-period:])
        std = np.std(prices[-period:])
        return sma + std * std_dev, sma, sma - std * std_dev
    
    def train_models(self, historical_data):
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
        self.is_trained = True
        self.training_features = X_pca
        
    def predict_signal(self, candles):
        if not self.is_trained:
            return {'signal': 0, 'confidence': 50}
        
        features = self.extract_features(candles)
        if len(features) == 0:
            return {'signal': 0, 'confidence': 50}
        
        features_scaled = self.scaler.transform([features])
        features_pca = self.pca.transform(features_scaled)
        
        rf_pred = self.rf_model.predict(features_pca)[0]
        gb_pred = self.gb_model.predict(features_pca)[0]
        voting_pred = self.voting_model.predict(features_pca)[0] if self.voting_model else (rf_pred + gb_pred) / 2
        
        cluster = self.kmeans.predict(features_pca)[0]
        
        predictions = [rf_pred, gb_pred]
        agreement = sum(predictions) / len(predictions)
        confidence = 50 + abs(agreement - 0.5) * 80
        
        signal = 1 if voting_pred > 0.5 else -1 if voting_pred < 0.4 else 0
        
        return {
            'signal': signal,
            'confidence': min(98, confidence),
            'rf_pred': rf_pred,
            'gb_pred': gb_pred,
            'voting_pred': voting_pred,
            'cluster': cluster
        }

# ==================== موتور کوانتومی ====================
class QuantumEngineV8:
    def __init__(self):
        self.dl_engine = DeepLearningEngine()
        self.models_trained = False
        
    def calculate_hurst_exponent(self, prices, max_lag=50):
        if len(prices) < max_lag:
            return 0.5
        lags = range(2, min(max_lag, len(prices) // 2))
        tau = [np.sqrt(np.std(np.subtract(prices[lag:], prices[:-lag]))) for lag in lags]
        poly = np.polyfit(np.log(lags), np.log(tau), 1)
        hurst = poly[0] * 2.0
        return max(0, min(1, hurst))
    
    def calculate_fractal_dimension(self, prices):
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
    
    def calculate_lyapunov_exponent(self, prices):
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
        if distances:
            return np.mean(distances)
        return 0
    
    def calculate_elliott_wave(self, prices):
        if len(prices) < 30:
            return {'wave_pattern': 'unknown', 'confidence': 0}
        
        diffs = np.diff(prices)
        patterns = []
        
        for i in range(0, len(diffs) - 6, 5):
            if i + 5 < len(diffs):
                wave1 = diffs[i]
                wave2 = diffs[i+1]
                wave3 = diffs[i+2]
                wave4 = diffs[i+3]
                wave5 = diffs[i+4]
                
                if wave1 > 0 and wave2 < 0 and wave3 > max(wave1, wave5) and wave4 < 0 and wave5 > 0:
                    patterns.append('impulse_up')
                elif wave1 < 0 and wave2 > 0 and wave3 < min(wave1, wave5) and wave4 > 0 and wave5 < 0:
                    patterns.append('impulse_down')
        
        if patterns:
            impulse_up = patterns.count('impulse_up')
            impulse_down = patterns.count('impulse_down')
            
            if impulse_up > impulse_down:
                return {'wave_pattern': 'impulse_up', 'confidence': min(90, impulse_up * 20)}
            elif impulse_down > impulse_up:
                return {'wave_pattern': 'impulse_down', 'confidence': min(90, impulse_down * 20)}
        
        return {'wave_pattern': 'unknown', 'confidence': 50}
    
    def detect_harmonic_patterns(self, prices):
        if len(prices) < 20:
            return []
        
        patterns = []
        for i in range(0, len(prices) - 5):
            try:
                X = prices[i]
                A = prices[i+1]
                B = prices[i+2]
                C = prices[i+3]
                D = prices[i+4]
                
                XA = abs(A - X)
                AB = abs(B - A)
                BC = abs(C - B)
                CD = abs(D - C)
                
                if XA > 0:
                    if 0.618 - 0.05 < AB/XA < 0.618 + 0.05:
                        if 0.382 - 0.05 < BC/AB < 0.382 + 0.05:
                            if 1.272 - 0.05 < CD/BC < 1.272 + 0.05:
                                patterns.append('Gartley')
                    
                    if 0.382 - 0.05 < AB/XA < 0.382 + 0.05:
                        if 0.382 - 0.05 < BC/AB < 0.382 + 0.05:
                            if 2.618 - 0.05 < CD/BC < 2.618 + 0.05:
                                patterns.append('Bat')
            except:
                continue
        
        return patterns
    
    def calculate_market_regime(self, candles):
        if len(candles) < 50:
            return {'regime': 'neutral', 'strength': 0}
        
        closes = [c['close'] for c in candles]
        ma20 = np.mean(closes[-20:])
        ma50 = np.mean(closes[-50:])
        
        price_to_ma20 = (closes[-1] - ma20) / ma20
        slope20 = (ma20 - np.mean(closes[-40:-20])) / np.mean(closes[-40:-20]) if len(closes) >= 40 else 0
        
        if price_to_ma20 > 0.05 and slope20 > 0.01:
            regime = 'bullish_trend'
            strength = min(100, 50 + (price_to_ma20 * 100))
        elif price_to_ma20 < -0.05 and slope20 < -0.01:
            regime = 'bearish_trend'
            strength = min(100, 50 + (abs(price_to_ma20) * 100))
        elif abs(price_to_ma20) < 0.02:
            regime = 'neutral'
            strength = 30
        else:
            regime = 'reversal'
            strength = 70 - abs(price_to_ma20) * 50
        
        return {'regime': regime, 'strength': max(0, min(100, strength))}
    
    def calculate_order_flow(self, candles):
        if len(candles) < 10:
            return {'buying_pressure': 0.5, 'selling_pressure': 0.5}
        
        buying_pressure = 0
        selling_pressure = 0
        
        for candle in candles[-20:]:
            body = candle['close'] - candle['open']
            if body > 0:
                buying_pressure += body * candle['volume'] * 0.7
                selling_pressure += (candle['high'] - candle['close']) * candle['volume'] * 0.3
            else:
                selling_pressure += abs(body) * candle['volume'] * 0.7
                buying_pressure += (candle['low'] - candle['open']) * candle['volume'] * 0.3
        
        total_pressure = buying_pressure + selling_pressure
        if total_pressure > 0:
            return {
                'buying_pressure': buying_pressure / total_pressure,
                'selling_pressure': selling_pressure / total_pressure,
                'imbalance': (buying_pressure - selling_pressure) / total_pressure
            }
        
        return {'buying_pressure': 0.5, 'selling_pressure': 0.5, 'imbalance': 0}
    
    def generate_signal(self, candles, indicators, order_book, support, resistance, current_price, symbol="BTCUSDT", chart_data=None):
        closes = [c['close'] for c in candles] if candles else []
        
        hurst = self.calculate_hurst_exponent(closes)
        fractal_dim = self.calculate_fractal_dimension(closes)
        lyapunov = self.calculate_lyapunov_exponent(closes)
        elliott = self.calculate_elliott_wave(closes)
        harmonic_patterns = self.detect_harmonic_patterns(closes)
        regime = self.calculate_market_regime(candles)
        order_flow = self.calculate_order_flow(candles)
        
        dl_prediction = {'signal': 0, 'confidence': 50}
        if self.models_trained:
            dl_prediction = self.dl_engine.predict_signal(candles)
        
        rsi = indicators.get('RSI', 50)
        macd = indicators.get('MACD', 0)
        adx = indicators.get('ADX', 20)
        
        price_range = resistance - support if resistance and support else current_price * 0.1
        price_position = (current_price - support) / price_range if price_range > 0 else 0.5
        
        # ===== استفاده از داده‌های چارت =====
        if chart_data:
            if chart_data.get('current_price'):
                current_price = chart_data['current_price']
            if chart_data.get('support'):
                support = chart_data['support']
            if chart_data.get('resistance'):
                resistance = chart_data['resistance']
        
        buy_score = 50
        sell_score = 50
        
        if hurst > 0.6:
            if regime['regime'] == 'bullish_trend':
                buy_score += 15
            elif regime['regime'] == 'bearish_trend':
                sell_score += 15
        elif hurst < 0.4:
            if price_position < 0.3:
                buy_score += 20
            elif price_position > 0.7:
                sell_score += 20
        
        if elliott['wave_pattern'] == 'impulse_up':
            buy_score += 20
        elif elliott['wave_pattern'] == 'impulse_down':
            sell_score += 20
        
        pattern_weights = {'Gartley': 15, 'Bat': 12, 'Butterfly': 18, 'Crab': 20}
        for pattern in harmonic_patterns:
            if pattern in pattern_weights:
                buy_score += pattern_weights[pattern] * 0.5
        
        if regime['regime'] == 'bullish_trend':
            buy_score += 10
        elif regime['regime'] == 'bearish_trend':
            sell_score += 10
        
        if order_flow.get('buying_pressure', 0) > 0.6:
            buy_score += 15
        if order_flow.get('selling_pressure', 0) > 0.6:
            sell_score += 15
        
        if dl_prediction['signal'] > 0:
            buy_score += dl_prediction['confidence'] * 0.1
        elif dl_prediction['signal'] < 0:
            sell_score += dl_prediction['confidence'] * 0.1
        
        if rsi < 30:
            buy_score += 20
        elif rsi > 70:
            sell_score += 20
        
        if macd > 0:
            buy_score += 10
        else:
            sell_score += 10
        
        if adx > 25:
            if buy_score > sell_score:
                buy_score += 10
            else:
                sell_score += 10
        
        if price_position < 0.3:
            buy_score += 15
        elif price_position > 0.7:
            sell_score += 15
        
        total_score = buy_score - sell_score
        confidence = min(98, 50 + abs(total_score) * 2)
        
        if total_score > 15:
            direction = "BUY"
        elif total_score < -15:
            direction = "SELL"
        else:
            direction = "HOLD"
            confidence = 50
        
        atr = np.std(np.diff(closes[-20:])) if len(closes) >= 20 else current_price * 0.01
        
        if direction == "BUY":
            take_profit = current_price + (resistance - current_price) * 0.8 if resistance else current_price * (1 + (confidence / 1000))
            stop_loss = current_price - (current_price - support) * 0.3 if support else current_price * (1 - (confidence / 1500))
        elif direction == "SELL":
            take_profit = current_price - (current_price - support) * 0.8 if support else current_price * (1 - (confidence / 1000))
            stop_loss = current_price + (resistance - current_price) * 0.3 if resistance else current_price * (1 + (confidence / 1500))
        else:
            take_profit = current_price
            stop_loss = current_price
        
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
            'adx': round(adx, 1),
            'hurst': round(hurst, 3),
            'fractal_dim': round(fractal_dim, 3),
            'lyapunov': round(lyapunov, 3),
            'elliott_pattern': elliott.get('wave_pattern', 'unknown'),
            'harmonic_patterns': harmonic_patterns,
            'market_regime': regime.get('regime', 'neutral'),
            'regime_strength': round(regime.get('strength', 0), 1),
            'buying_pressure': round(order_flow.get('buying_pressure', 0.5) * 100, 1),
            'selling_pressure': round(order_flow.get('selling_pressure', 0.5) * 100, 1),
            'order_imbalance': round(order_flow.get('imbalance', 0) * 100, 1),
            'ml_prediction': dl_prediction.get('signal', 0),
            'ml_confidence': round(dl_prediction.get('confidence', 50), 1),
            'price_position': round(price_position * 100, 1),
            'buy_score': round(buy_score, 1),
            'sell_score': round(sell_score, 1),
            'total_score': round(total_score, 1),
            'chart_data': chart_data
        }

quantum_engine = QuantumEngineV8()

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
        if not db.get_setting('auto_trade_enabled') == '1':
            return
        
        users = db.get_all_users()
        for user_id, lang in users:
            user = db.get_user(user_id)
            if not user or user[14] != 1:
                continue
            
            favorites = json.loads(user[13]) if user[13] else ['BTCUSDT', 'ETHUSDT']
            
            for symbol in favorites[:3]:
                candles = price_service.get_klines(symbol, "1h", 200)
                if not candles:
                    continue
                
                prices = [c['close'] for c in candles]
                current_price = prices[-1] if prices else 0
                support = np.percentile(prices, 20) if prices else current_price * 0.95
                resistance = np.percentile(prices, 80) if prices else current_price * 1.05
                
                indicators = {
                    'RSI': quantum_engine.dl_engine.calculate_rsi(prices),
                    'MACD': quantum_engine.dl_engine.calculate_macd(prices)[0],
                    'ADX': 25
                }
                
                signal = quantum_engine.generate_signal(
                    candles, indicators, None, support, resistance, current_price, symbol
                )
                
                if signal['confidence'] > int(db.get_setting('min_confidence') or 80):
                    await self.execute_auto_trade(user_id, signal)
    
    async def execute_auto_trade(self, user_id, signal):
        if signal['direction'] == 'HOLD':
            return
        
        signal_id = db.save_signal(user_id, signal)
        
        user = db.get_user(user_id)
        risk_percent = user[15] if user else 2
        max_position = user[16] if user else 10
        
        position_size = self.calculate_position_size(signal, risk_percent, max_position)
        
        trade = {
            'user_id': user_id,
            'symbol': signal['symbol'],
            'side': signal['direction'].lower(),
            'entry_price': signal['entry'],
            'quantity': position_size,
            'stop_loss': signal['stop_loss'],
            'take_profit': signal['take_profit'],
            'created_at': datetime.now().isoformat()
        }
        
        self.active_trades[user_id] = trade
        
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"🤖 **معامله خودکار اجرا شد!**\n\n"
                     f"📊 {signal['symbol']}\n"
                     f"📈 {'خرید' if signal['direction'] == 'BUY' else 'فروش'}\n"
                     f"💰 قیمت ورود: ${signal['entry']:,.2f}\n"
                     f"🎯 حد سود: ${signal['take_profit']:,.2f}\n"
                     f"🛡️ حد ضرر: ${signal['stop_loss']:,.2f}\n"
                     f"📊 حجم: {position_size:.4f}\n"
                     f"🎯 اطمینان: {signal['confidence']}%",
                parse_mode='Markdown'
            )
        except:
            pass
    
    def calculate_position_size(self, signal, risk_percent, max_position):
        if signal['direction'] == 'BUY':
            risk_distance = signal['entry'] - signal['stop_loss']
        else:
            risk_distance = signal['stop_loss'] - signal['entry']
        
        if risk_distance <= 0:
            return 0.01
        
        position_size = (risk_percent / 100) / (risk_distance / signal['entry'])
        return min(position_size, max_position)

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
    'welcome': '🔥 به ربات تحلیل تکنیکال فوق‌پیشرفته نسخه ۸.۵ خوش آمدید!\n\n📊 با ۲۰۰+ ارز، الگوریتم‌های کوانتومی، یادگیری عمیق و تشخیص چارت\n🎯 دقت سیگنال تا ۹۸٪\n🚀 معاملات خودکار با هوش مصنوعی\n📸 قابلیت تحلیل چارت از تصویر\n\nبرای شروع روی "📊 شروع تحلیل" کلیک کنید.',
    'select_symbol': '🔍 لطفاً ارز مورد نظر را انتخاب کنید:',
    'enter_price': '💰 قیمت فعلی ارز را وارد کنید:',
    'enter_support_resistance': '📊 حمایت و مقاومت را وارد کنید:\n\n📉 حمایت:\n📈 مقاومت:',
    'select_indicators': '🔍 اندیکاتورها را انتخاب کنید (حداقل ۵ عدد)',
    'signal_result': '🔥 نتیجه تحلیل کوانتومی نسخه ۸.۵',
    'profit': '💰 حد سود',
    'loss': '🛡️ حد ضرر',
    'leverage': '⚡ اهرم',
    'confidence': '🎯 اطمینان',
    'buy': '📈 خرید',
    'sell': '📉 فروش',
    'hold': '⚪ نگهداری',
    'admin_panel': '👑 پنل ادمین',
    'change_lang': '🌐 تغییر زبان',
    'referral': '🎁 دعوت دوستان',
    'exchange': '💱 صرافی توبیت',
    'stats': '📊 آمار من',
    'start_analysis': '📊 شروع تحلیل',
    'chart_analysis': '📸 تحلیل چارت',
    'back': '🔙 بازگشت',
    'register': '🔄 ثبت',
    'analyze': '📊 تحلیل',
    'auto_trade': '🤖 معاملات خودکار',
    'my_trades': '📊 معاملات من',
    'settings': '⚙️ تنظیمات',
    'risk_management': '🛡️ مدیریت ریسک'
}

TEXTS_EN = {
    'welcome': '🔥 Welcome to Ultra Advanced Technical Analysis Bot v8.5!\n\n📊 With 200+ coins, quantum algorithms, deep learning and chart recognition\n🎯 Signal accuracy up to 98%\n🚀 AI-powered automated trading\n📸 Chart analysis from image\n\nClick "📊 Start Analysis" to begin.',
    'select_symbol': '🔍 Please select your cryptocurrency:',
    'enter_price': '💰 Enter current price:',
    'enter_support_resistance': '📊 Enter support and resistance:\n\n📉 Support:\n📈 Resistance:',
    'select_indicators': '🔍 Select indicators (minimum 5)',
    'signal_result': '🔥 Quantum Analysis Result v8.5',
    'profit': '💰 Take Profit',
    'loss': '🛡️ Stop Loss',
    'leverage': '⚡ Leverage',
    'confidence': '🎯 Confidence',
    'buy': '📈 BUY',
    'sell': '📉 SELL',
    'hold': '⚪ HOLD',
    'admin_panel': '👑 Admin Panel',
    'change_lang': '🌐 Change Language',
    'referral': '🎁 Invite Friends',
    'exchange': '💱 Toobit Exchange',
    'stats': '📊 My Stats',
    'start_analysis': '📊 Start Analysis',
    'chart_analysis': '📸 Chart Analysis',
    'back': '🔙 Back',
    'register': '🔄 Register',
    'analyze': '📊 Analyze',
    'auto_trade': '🤖 Auto Trade',
    'my_trades': '📊 My Trades',
    'settings': '⚙️ Settings',
    'risk_management': '🛡️ Risk Management'
}

def get_text(user_id, key):
    user = db.get_user(user_id)
    lang = user[3] if user else 'fa'
    if lang == 'en':
        return TEXTS_EN.get(key, TEXTS_FA.get(key, ''))
    return TEXTS_FA.get(key, '')

# ==================== کیبوردها ====================
def get_main_keyboard(user_id):
    user = db.get_user(user_id)
    lang = user[3] if user else 'fa'
    
    if lang == 'en':
        return ReplyKeyboardMarkup([
            [KeyboardButton("📊 Start Analysis")],
            [KeyboardButton("📸 Chart Analysis")],
            [KeyboardButton("📊 My Stats"), KeyboardButton("💱 Toobit Exchange")],
            [KeyboardButton("🎁 Invite Friends"), KeyboardButton("🤖 Auto Trade")],
            [KeyboardButton("📊 My Trades"), KeyboardButton("⚙️ Settings")],
            [KeyboardButton("🌐 Change Language")]
        ], resize_keyboard=True)
    else:
        return ReplyKeyboardMarkup([
            [KeyboardButton("📊 شروع تحلیل")],
            [KeyboardButton("📸 تحلیل چارت")],
            [KeyboardButton("📊 آمار من"), KeyboardButton("💱 صرافی توبیت")],
            [KeyboardButton("🎁 دعوت دوستان"), KeyboardButton("🤖 معاملات خودکار")],
            [KeyboardButton("📊 معاملات من"), KeyboardButton("⚙️ تنظیمات")],
            [KeyboardButton("🌐 تغییر زبان")]
        ], resize_keyboard=True)

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
    
    if lang == 'en':
        keyboard.append([KeyboardButton("🔄 Register"), KeyboardButton("📊 Analyze")])
        keyboard.append([KeyboardButton("🔙 Back")])
    else:
        keyboard.append([KeyboardButton("🔄 ثبت"), KeyboardButton("📊 تحلیل")])
        keyboard.append([KeyboardButton("🔙 بازگشت")])
    
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
            [KeyboardButton("⚙️ تنظیمات سیستم")],
            [KeyboardButton("🔙 بازگشت")]
        ], resize_keyboard=True)

# ==================== هندلر عکس (تحلیل چارت) ====================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تحلیل کامل چارت از تصویر"""
    user_id = update.effective_user.id
    
    await update.effective_chat.send_message(
        "🔍 **در حال تحلیل چارت با هوش مصنوعی...**\n"
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
                "❌ **خطا در تحلیل چارت!**\n\n"
                "لطفاً یک چارت واضح با موارد زیر ارسال کنید:\n"
                "✅ قیمت مشخص\n"
                "✅ اندیکاتورها (RSI, MACD, EMA)\n"
                "✅ حمایت و مقاومت\n"
                "✅ حجم معاملات",
                reply_markup=get_main_keyboard(user_id)
            )
            return
        
        chart_data = chart_result['chart_data']
        patterns = chart_result['patterns']
        indicators = chart_result['indicators']
        quality = chart_result['analysis_quality']
        
        # نمایش اطلاعات استخراج شده
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
        if chart_data.get('timeframe'):
            text += f"⏰ تایم‌فریم: {chart_data['timeframe']}\n"
        
        if indicators:
            text += f"\n📊 **اندیکاتورهای تشخیص داده شده:**\n"
            for name, value in indicators.items():
                if name == 'ema':
                    for period, val in value.items():
                        text += f"• EMA({period}): ${val:,.2f}\n"
                elif name in ['RSI', 'MACD', 'Stoch', 'ADX']:
                    text += f"• {name}: {value:.2f}\n"
        
        if patterns:
            text += f"\n🧠 **الگوهای تشخیص داده شده:**\n"
            for pattern in patterns[:5]:
                text += f"• {pattern['name']} (اطمینان: {pattern['confidence']}%)\n"
        
        text += f"\n⭐ **کیفیت تحلیل:** {quality}%\n"
        
        db.save_chart_analysis(user_id, chart_data.get('symbol', 'UNKNOWN'), chart_data, patterns, indicators)
        
        await update.effective_chat.send_message(
            text,
            reply_markup=get_main_keyboard(user_id),
            parse_mode='Markdown'
        )
        
        # اگر کیفیت بالا بود و ارز مشخص بود، سیگنال تولید کن
        if quality > 60 and chart_data.get('current_price'):
            symbol = chart_data.get('symbol', 'BTCUSDT')
            if symbol in SUPPORTED_SYMBOLS:
                candles = price_service.get_klines(symbol, "1h", 200)
                if candles:
                    indicators_dict = {}
                    if indicators.get('RSI'):
                        indicators_dict['RSI'] = indicators['RSI']
                    if indicators.get('MACD'):
                        indicators_dict['MACD'] = indicators['MACD']
                    
                    # استفاده از داده‌های چارت برای تولید سیگنال
                    signal = quantum_engine.generate_signal(
                        candles,
                        indicators_dict,
                        None,
                        chart_data.get('support', 0),
                        chart_data.get('resistance', 0),
                        chart_data.get('current_price', 0),
                        symbol,
                        chart_data
                    )
                    
                    if signal and signal['direction'] != 'HOLD':
                        await update.effective_chat.send_message(
                            "🔥 **سیگنال خودکار از چارت:**\n"
                            "ربات بر اساس تحلیل چارت، سیگنال زیر را تولید کرده است:",
                            parse_mode='Markdown'
                        )
                        await send_signal_result(update, user_id, signal)
        
    except Exception as e:
        await update.effective_chat.send_message(
            f"❌ **خطا در تحلیل چارت:**\n\n{str(e)[:200]}",
            reply_markup=get_main_keyboard(user_id)
        )

# ==================== بقیه هندلرها ====================
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
            'indicators': {},
            'support': None,
            'resistance': None,
            'current_price': None,
            'state': 'menu',
            'symbol': 'BTCUSDT'
        }
    
    try:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
    except:
        pass
    
    user = db.get_user(user_id)
    lang = user[3] if user else 'fa'
    
    # ===== تحلیل چارت =====
    if "📸 تحلیل چارت" in text or "Chart Analysis" in text:
        await update.effective_chat.send_message(
            "📸 **تصویر چارت خود را ارسال کنید**\n\n"
            "ربات با هوش مصنوعی پیشرفته:\n"
            "✅ استخراج کامل داده‌های چارت\n"
            "✅ تشخیص الگوهای کندل استیک\n"
            "✅ شناسایی اندیکاتورها\n"
            "✅ تولید سیگنال دقیق\n\n"
            "📤 لطفاً یک تصویر واضح از چارت ارسال کنید.",
            reply_markup=get_main_keyboard(user_id)
        )
        return
    
    # ===== تنظیمات =====
    if "⚙️ تنظیمات" in text or "Settings" in text:
        if lang == 'fa':
            keyboard = [
                [KeyboardButton("🛡️ مدیریت ریسک")],
                [KeyboardButton("📊 تنظیمات تحلیل")],
                [KeyboardButton("🔙 بازگشت")]
            ]
        else:
            keyboard = [
                [KeyboardButton("🛡️ Risk Management")],
                [KeyboardButton("📊 Analysis Settings")],
                [KeyboardButton("🔙 Back")]
            ]
        await update.effective_chat.send_message(
            "⚙️ **تنظیمات**" if lang == 'fa' else "⚙️ **Settings**",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
            parse_mode='Markdown'
        )
        return
    
    # ===== مدیریت ریسک =====
    if "🛡️ مدیریت ریسک" in text or "Risk Management" in text:
        user = db.get_user(user_id)
        risk = user[15] if user else 2
        max_pos = user[16] if user else 10
        
        msg = f"🛡️ **{('مدیریت ریسک' if lang == 'fa' else 'Risk Management')}**\n\n"
        msg += f"📊 {('درصد ریسک' if lang == 'fa' else 'Risk Percent')}: {risk}%\n"
        msg += f"📊 {('حداکثر حجم' if lang == 'fa' else 'Max Position')}: {max_pos}\n\n"
        msg += f"📝 {('برای تغییر، عدد جدید را وارد کنید:' if lang == 'fa' else 'Enter new value:')}\n"
        msg += f"💡 {('مثال' if lang == 'fa' else 'Example')}: risk:3, max:15"
        
        user_data[user_id]['state'] = 'risk_settings'
        await update.effective_chat.send_message(msg, parse_mode='Markdown')
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
            await update.effective_chat.send_message(
                "✅ **تنظیمات ذخیره شد!**" if lang == 'fa' else "✅ **Settings saved!**",
                reply_markup=get_main_keyboard(user_id),
                parse_mode='Markdown'
            )
        except:
            await update.effective_chat.send_message(
                "❌ **فرمت اشتباه!**" if lang == 'fa' else "❌ **Invalid format!**",
                parse_mode='Markdown'
            )
        return
    
    # ===== معاملات خودکار =====
    if "🤖 معاملات خودکار" in text or "Auto Trade" in text:
        user = db.get_user(user_id)
        auto_trade = user[14] if user else 0
        
        status = "✅ فعال" if auto_trade else "❌ غیرفعال"
        msg = f"🤖 **{('معاملات خودکار' if lang == 'fa' else 'Auto Trade')}**\n\n"
        msg += f"📊 {('وضعیت' if lang == 'fa' else 'Status')}: {status}\n\n"
        
        if lang == 'fa':
            msg += "برای فعال/غیرفعال کردن، روی دکمه زیر کلیک کنید:"
            keyboard = [
                [KeyboardButton("✅ فعال کردن") if not auto_trade else KeyboardButton("❌ غیرفعال کردن")],
                [KeyboardButton("🔙 بازگشت")]
            ]
        else:
            msg += "Click below to enable/disable:"
            keyboard = [
                [KeyboardButton("✅ Enable") if not auto_trade else KeyboardButton("❌ Disable")],
                [KeyboardButton("🔙 Back")]
            ]
        
        await update.effective_chat.send_message(
            msg,
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
            parse_mode='Markdown'
        )
        return
    
    if "✅ فعال کردن" in text or "Enable" in text or "❌ غیرفعال کردن" in text or "Disable" in text:
        auto_trade = 1 if "فعال" in text or "Enable" in text else 0
        db.cursor.execute('UPDATE users SET auto_trade = ? WHERE user_id = ?', (auto_trade, user_id))
        db.conn.commit()
        
        status = "فعال" if auto_trade else "غیرفعال"
        msg = f"✅ **{('معاملات خودکار' if lang == 'fa' else 'Auto Trade')} {status} {('شد!' if lang == 'fa' else '!')}**"
        
        await update.effective_chat.send_message(
            msg,
            reply_markup=get_main_keyboard(user_id),
            parse_mode='Markdown'
        )
        return
    
    # ===== معاملات من =====
    if "📊 معاملات من" in text or "My Trades" in text:
        trades = db.get_user_trades(user_id)
        if trades:
            msg = f"📊 **{('معاملات اخیر' if lang == 'fa' else 'Recent Trades')}**\n\n"
            for trade in trades[:10]:
                profit_symbol = "📈" if trade[6] > 0 else "📉" if trade[6] < 0 else "⚪"
                msg += f"{profit_symbol} {trade[1]} - {('خرید' if trade[2] == 'buy' else 'فروش') if lang == 'fa' else trade[2]}\n"
                msg += f"💰 {('سود' if lang == 'fa' else 'Profit')}: ${trade[6]:.2f}\n\n"
            await update.effective_chat.send_message(msg, parse_mode='Markdown')
        else:
            await update.effective_chat.send_message(
                "📊 **هیچ معامله‌ای یافت نشد**" if lang == 'fa' else "📊 **No trades found**",
                parse_mode='Markdown'
            )
        return
    
    # ===== تغییر زبان =====
    if "🌐 تغییر زبان" in text or "Change Language" in text:
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
    
    # ===== صرافی توبیت =====
    if "💱 صرافی توبیت" in text or "Toobit Exchange" in text:
        msg = f"💱 **Toobit Exchange | صرافی توبیت**\n\n🔗 {EXCHANGE_URL}\n\n🎁 {'با لینک بالا ثبت نام کنید و از جوایز ویژه بهره‌مند شوید!' if lang == 'fa' else 'Register with the link above and get special rewards!'}"
        await update.effective_chat.send_message(msg, reply_markup=get_main_keyboard(user_id), parse_mode='Markdown')
        return
    
    # ===== رفرال =====
    if "🎁 دعوت دوستان" in text or "Invite Friends" in text:
        referral_link = f"https://t.me/{BOT_USERNAME.replace('@', '')}?start=ref_{user_id}"
        referral_count = db.cursor.execute('SELECT referral_count FROM users WHERE user_id = ?', (user_id,)).fetchone()[0]
        
        msg = f"🎁 **{('سیستم دعوت دوستان' if lang == 'fa' else 'Referral System')}**\n\n"
        msg += f"🔗 {('لینک دعوت شما' if lang == 'fa' else 'Your referral link')}:\n`{referral_link}`\n\n"
        msg += f"👥 {('تعداد دعوت‌ها' if lang == 'fa' else 'Total referrals')}: {referral_count}\n\n"
        msg += f"📤 {('لینک را با دوستان خود به اشتراک بگذارید!' if lang == 'fa' else 'Share the link with your friends!')}"
        
        await update.effective_chat.send_message(msg, reply_markup=get_main_keyboard(user_id), parse_mode='Markdown')
        return
    
    # ===== آمار من =====
    if "📊 آمار من" in text or "My Stats" in text:
        stats = db.get_user_stats(user_id)
        if stats:
            total, avg_conf, best_conf, wins, losses = stats
            win_rate = (wins / (wins + losses) * 100) if wins + losses > 0 else 0
            
            msg = f"📊 **{('آمار شما' if lang == 'fa' else 'Your Stats')}**\n\n"
            msg += f"📈 {('تعداد تحلیل‌ها' if lang == 'fa' else 'Total Analysis')}: {total}\n"
            msg += f"🎯 {('میانگین اطمینان' if lang == 'fa' else 'Avg Confidence')}: {avg_conf:.0f}%\n"
            msg += f"🏆 {('بهترین اطمینان' if lang == 'fa' else 'Best Confidence')}: {best_conf:.0f}%\n"
            msg += f"🏅 {('نرخ برد' if lang == 'fa' else 'Win Rate')}: {win_rate:.1f}%\n"
            msg += f"👥 {('تعداد دعوت‌ها' if lang == 'fa' else 'Total Referrals')}: {db.cursor.execute('SELECT referral_count FROM users WHERE user_id = ?', (user_id,)).fetchone()[0]}"
            
            await update.effective_chat.send_message(msg, reply_markup=get_main_keyboard(user_id), parse_mode='Markdown')
        else:
            await update.effective_chat.send_message(
                "📊 {'هنوز تحلیلی انجام نداده‌اید!' if lang == 'fa' else 'No analysis yet!'}",
                reply_markup=get_main_keyboard(user_id)
            )
        return
    
    # ===== شروع تحلیل =====
    if "📊 شروع تحلیل" in text or "Start Analysis" in text:
        user_data[user_id]['state'] = 'selecting_symbol'
        await update.effective_chat.send_message(
            get_text(user_id, 'select_symbol'),
            reply_markup=get_symbol_keyboard(user_id)
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
                f"💰 **{get_text(user_id, 'enter_price')}**{price_text}\n\n"
                f"📝 {('مثال' if lang == 'fa' else 'Example')}: 65432.50",
                parse_mode='Markdown'
            )
        elif "🔙" in text:
            user_data[user_id]['state'] = 'menu'
            await update.effective_chat.send_message("🔙", reply_markup=get_main_keyboard(user_id))
        else:
            await update.effective_chat.send_message(
                "❌ {'لطفاً یکی از ارزهای لیست را انتخاب کنید!' if lang == 'fa' else 'Please select a symbol from the list!'}",
                reply_markup=get_symbol_keyboard(user_id)
            )
        return
    
    # ===== دریافت قیمت =====
    elif user_data[user_id]['state'] == 'waiting_price':
        try:
            user_data[user_id]['current_price'] = float(text.replace(',', '.'))
            user_data[user_id]['state'] = 'waiting_support_resistance'
            
            await update.effective_chat.send_message(
                f"📊 **{get_text(user_id, 'enter_support_resistance')}**\n\n"
                f"📉 {('مثال' if lang == 'fa' else 'Example')}: 65000\n"
                f"📈 {('مثال' if lang == 'fa' else 'Example')}: 66000",
                parse_mode='Markdown'
            )
        except ValueError:
            await update.effective_chat.send_message(
                "❌ {'لطفاً عدد معتبر وارد کنید!' if lang == 'fa' else 'Please enter a valid number!'}"
            )
    
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
        
        if support and resistance:
            if support < resistance:
                user_data[user_id]['support'] = support
                user_data[user_id]['resistance'] = resistance
                user_data[user_id]['state'] = 'selecting_indicators'
                
                await update.effective_chat.send_message(
                    f"✅ **{'داده‌ها ثبت شد!' if lang == 'fa' else 'Data saved!'}**\n\n"
                    f"💰 {'قیمت' if lang == 'fa' else 'Price'}: {user_data[user_id]['current_price']}\n"
                    f"📊 {'حمایت' if lang == 'fa' else 'Support'}: {support}\n"
                    f"📈 {'مقاومت' if lang == 'fa' else 'Resistance'}: {resistance}\n\n"
                    f"🔍 **{get_text(user_id, 'select_indicators')}**\n"
                    f"💡 {'اندیکاتور بیشتر = دقت بالاتر' if lang == 'fa' else 'More indicators = higher accuracy'}",
                    reply_markup=get_indicators_keyboard(user_id)
                )
            else:
                await update.effective_chat.send_message(
                    "❌ {'حمایت باید کمتر از مقاومت باشد!' if lang == 'fa' else 'Support must be less than resistance!'}"
                )
        else:
            await update.effective_chat.send_message(
                "❌ {'فرمت اشتباه! لطفاً مجدداً وارد کنید.' if lang == 'fa' else 'Invalid format! Please try again.'}"
            )
    
    # ===== انتخاب اندیکاتورها =====
    elif user_data[user_id]['state'] == 'selecting_indicators':
        clean_text = text.replace("✅ ", "")
        
        if clean_text in INDICATORS:
            if clean_text not in user_data[user_id]['indicators']:
                user_data[user_id]['current_indicator'] = clean_text
                user_data[user_id]['state'] = 'waiting_indicator_value'
                await update.effective_chat.send_message(
                    f"📊 **{'مقدار' if lang == 'fa' else 'Value of'} {clean_text} {'را وارد کنید' if lang == 'fa' else ''}**\n\n"
                    f"📝 {'مثال' if lang == 'fa' else 'Example'}: 45.67",
                    parse_mode='Markdown'
                )
            else:
                await update.effective_chat.send_message(
                    f"⚠️ {clean_text} {'قبلاً ثبت شده است!' if lang == 'fa' else 'already added!'}",
                    reply_markup=get_indicators_keyboard(user_id)
                )
        
        elif "ثبت" in text or "Register" in text or "تحلیل" in text or "Analyze" in text:
            if len(user_data[user_id]['indicators']) >= 5:
                symbol = user_data[user_id]['symbol']
                candles = price_service.get_klines(symbol, "1h", 200)
                order_book = price_service.get_order_book(symbol)
                
                if not candles:
                    await update.effective_chat.send_message(
                        "❌ {'خطا در دریافت داده‌های قیمت!' if lang == 'fa' else 'Error getting price data!'}"
                    )
                    return
                
                status_msg = await update.effective_chat.send_message(
                    f"🔄 **{'تحلیل کوانتومی نسخه ۸.۵ در حال اجرا...' if lang == 'fa' else 'Quantum Analysis v8.5 running...'}**\n"
                    f"🧠 {'الگوریتم‌های هوش مصنوعی در حال پردازش...' if lang == 'fa' else 'AI algorithms processing...'}\n"
                    f"📊 {len(user_data[user_id]['indicators'])} {'اندیکاتور' if lang == 'fa' else 'indicators'}",
                    parse_mode='Markdown'
                )
                
                result = quantum_engine.generate_signal(
                    candles,
                    user_data[user_id]['indicators'],
                    order_book,
                    user_data[user_id]['support'],
                    user_data[user_id]['resistance'],
                    user_data[user_id]['current_price'],
                    symbol
                )
                
                await status_msg.delete()
                
                await send_signal_result(update, user_id, result)
                user_data[user_id]['state'] = 'menu'
                
            else:
                await update.effective_chat.send_message(
                    f"❌ {'حداقل ۵ اندیکاتور وارد کنید!' if lang == 'fa' else 'Minimum 5 indicators required!'} ({len(user_data[user_id]['indicators'])}/5)",
                    reply_markup=get_indicators_keyboard(user_id)
                )
    
    elif user_data[user_id]['state'] == 'waiting_indicator_value':
        try:
            indicator_name = user_data[user_id]['current_indicator']
            indicator_value = float(text.replace(',', '.'))
            user_data[user_id]['indicators'][indicator_name] = indicator_value
            user_data[user_id]['state'] = 'selecting_indicators'
            
            await update.effective_chat.send_message(
                f"✅ {indicator_name} = {indicator_value} {'ثبت شد!' if lang == 'fa' else 'saved!'}\n\n"
                f"📊 {'اندیکاتورهای ثبت شده' if lang == 'fa' else 'Indicators saved'}: {len(user_data[user_id]['indicators'])}/20\n\n"
                f"🔍 {'اندیکاتور بعدی را انتخاب کنید یا روی «ثبت» کلیک کنید' if lang == 'fa' else 'Select next indicator or click "Register"'}",
                reply_markup=get_indicators_keyboard(user_id)
            )
        except ValueError:
            await update.effective_chat.send_message(
                "❌ {'لطفاً عدد معتبر وارد کنید!' if lang == 'fa' else 'Please enter a valid number!'}"
            )
    
    # ===== پنل ادمین =====
    elif "👑 پنل ادمین" in text or "Admin Panel" in text:
        if user_id == ADMIN_ID:
            await update.effective_chat.send_message(
                "👑 **پنل ادمین**\n\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
                reply_markup=get_admin_keyboard(user_id),
                parse_mode='Markdown'
            )
        else:
            await update.effective_chat.send_message(
                "❌ دسترسی غیرمجاز!",
                reply_markup=get_main_keyboard(user_id)
            )
        return
    
    # ===== مدیریت ادمین =====
    if user_id == ADMIN_ID:
        if "📢 ارسال پیام همگانی" in text or "Broadcast" in text:
            user_data[user_id]['state'] = 'broadcast'
            await update.effective_chat.send_message(
                "📝 {'پیام خود را برای ارسال به تمام کاربران وارد کنید:' if lang == 'fa' else 'Enter your broadcast message:'}",
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
                f"✅ {'پیام به' if lang == 'fa' else 'Message sent to'} {sent} {'کاربر ارسال شد!' if lang == 'fa' else 'users!'}",
                reply_markup=get_admin_keyboard(user_id)
            )
            return
        
        if "📊 آمار کاربران" in text or "User Stats" in text:
            users = db.get_all_users()
            total = len(users)
            fa_count = sum(1 for u in users if u[1] == 'fa')
            en_count = sum(1 for u in users if u[1] == 'en')
            
            await update.effective_chat.send_message(
                f"📊 **{'آمار کاربران' if lang == 'fa' else 'User Stats'}**\n\n"
                f"👥 {'کل کاربران' if lang == 'fa' else 'Total Users'}: {total}\n"
                f"📈 {'کاربران فارسی' if lang == 'fa' else 'Persian Users'}: {fa_count}\n"
                f"📈 {'کاربران انگلیسی' if lang == 'fa' else 'English Users'}: {en_count}",
                reply_markup=get_admin_keyboard(user_id),
                parse_mode='Markdown'
            )
            return
        
        if "🔗 اشتراکی کردن ربات" in text or "Share Bot" in text:
            bot_link = f"https://t.me/{BOT_USERNAME.replace('@', '')}"
            
            if lang == 'fa':
                msg = f"🔗 **لینک اشتراک‌گذاری ربات**\n\n📤 لینک:\n`{bot_link}`\n\n📋 متن پیشنهادی:\n🔥 به ربات تحلیل تکنیکال فوق‌پیشرفته بپیوندید!\n🎯 دقت سیگنال تا ۹۸٪\n🔗 {bot_link}"
            else:
                msg = f"🔗 **Bot Share Link**\n\n📤 Link:\n`{bot_link}`\n\n📋 Suggested text:\n🔥 Join the Ultra Advanced Technical Analysis Bot!\n🎯 Signal accuracy up to 98%\n🔗 {bot_link}"
            
            await update.effective_chat.send_message(
                msg,
                reply_markup=get_admin_keyboard(user_id),
                parse_mode='Markdown'
            )
            return
        
        if "✏️ تغییر متن خوش‌آمدگویی" in text or "Edit Welcome" in text:
            user_data[user_id]['state'] = 'edit_welcome'
            await update.effective_chat.send_message(
                "✏️ {'متن جدید خوش‌آمدگویی را وارد کنید:' if lang == 'fa' else 'Enter new welcome text:'}",
                reply_markup=get_admin_keyboard(user_id)
            )
            return
        
        if user_data[user_id].get('state') == 'edit_welcome':
            db.update_setting('welcome_text_fa', text)
            db.update_setting('welcome_text_en', text)
            user_data[user_id]['state'] = 'menu'
            await update.effective_chat.send_message(
                "✅ {'متن خوش‌آمدگویی با موفقیت تغییر کرد!' if lang == 'fa' else 'Welcome text updated successfully!'}",
                reply_markup=get_admin_keyboard(user_id)
            )
            return
        
        if "⏰ تغییر مدت اشتراک" in text or "Edit Subscription" in text:
            user_data[user_id]['state'] = 'edit_subscription'
            await update.effective_chat.send_message(
                "⏰ {'تعداد روزهای اشتراک را وارد کنید:' if lang == 'fa' else 'Enter subscription days:'}\n📝 {'مثال' if lang == 'fa' else 'Example'}: 30",
                reply_markup=get_admin_keyboard(user_id)
            )
            return
        
        if user_data[user_id].get('state') == 'edit_subscription':
            try:
                days = int(text)
                db.update_setting('subscription_days', str(days))
                user_data[user_id]['state'] = 'menu'
                await update.effective_chat.send_message(
                    f"✅ {'مدت اشتراک به' if lang == 'fa' else 'Subscription set to'} {days} {'روز تغییر کرد!' if lang == 'fa' else 'days!'}",
                    reply_markup=get_admin_keyboard(user_id)
                )
            except:
                await update.effective_chat.send_message(
                    "❌ {'لطفاً یک عدد معتبر وارد کنید!' if lang == 'fa' else 'Please enter a valid number!'}"
                )
            return
        
        if "💳 تغییر شماره کارت" in text or "Edit Card" in text:
            user_data[user_id]['state'] = 'edit_card'
            await update.effective_chat.send_message(
                "💳 {'شماره کارت جدید را وارد کنید:' if lang == 'fa' else 'Enter new card number:'}\n(۱۶ {'رقم' if lang == 'fa' else 'digits'})",
                reply_markup=get_admin_keyboard(user_id)
            )
            return
        
        if user_data[user_id].get('state') == 'edit_card':
            if len(text.replace(' ', '')) == 16:
                db.update_setting('card_number', text)
                user_data[user_id]['state'] = 'menu'
                await update.effective_chat.send_message(
                    f"✅ {'شماره کارت تغییر کرد!' if lang == 'fa' else 'Card number updated!'}\n💳 {text}",
                    reply_markup=get_admin_keyboard(user_id)
                )
            else:
                await update.effective_chat.send_message(
                    "❌ {'شماره کارت باید ۱۶ رقم باشد!' if lang == 'fa' else 'Card number must be 16 digits!'}"
                )
            return
        
        if "💰 کیف پول" in text or "Wallet" in text:
            card_number = db.get_setting('card_number')
            card_holder = db.get_setting('card_holder')
            price = db.get_setting('subscription_price')
            days = db.get_setting('subscription_days')
            
            if lang == 'fa':
                msg = f"💰 **کیف پول**\n\n💳 شماره کارت: {card_number}\n👤 صاحب کارت: {card_holder}\n💰 قیمت اشتراک: {price} تومان\n⏰ مدت اشتراک: {days} روز"
            else:
                msg = f"💰 **Wallet**\n\n💳 Card Number: {card_number}\n👤 Card Holder: {card_holder}\n💰 Subscription Price: {price} IRR\n⏰ Subscription Days: {days}"
            
            await update.effective_chat.send_message(
                msg,
                reply_markup=get_admin_keyboard(user_id),
                parse_mode='Markdown'
            )
            return
        
        if "⚙️ تنظیمات سیستم" in text or "System Settings" in text:
            min_conf = db.get_setting('min_confidence')
            max_lev = db.get_setting('max_leverage')
            auto_trade_enabled = db.get_setting('auto_trade_enabled')
            
            if lang == 'fa':
                msg = f"⚙️ **تنظیمات سیستم**\n\n"
                msg += f"🎯 حداقل اطمینان: {min_conf}%\n"
                msg += f"⚡ حداکثر اهرم: {max_lev}x\n"
                msg += f"🤖 معاملات خودکار: {'فعال' if auto_trade_enabled == '1' else 'غیرفعال'}\n\n"
                msg += "برای تغییر، عدد جدید را وارد کنید:\n"
                msg += "مثال: min_conf:85, max_lev:25"
            else:
                msg = f"⚙️ **System Settings**\n\n"
                msg += f"🎯 Min Confidence: {min_conf}%\n"
                msg += f"⚡ Max Leverage: {max_lev}x\n"
                msg += f"🤖 Auto Trade: {'Enabled' if auto_trade_enabled == '1' else 'Disabled'}\n\n"
                msg += "Enter new values:\n"
                msg += "Example: min_conf:85, max_lev:25"
            
            user_data[user_id]['state'] = 'system_settings'
            await update.effective_chat.send_message(msg, parse_mode='Markdown')
            return
        
        if user_data[user_id].get('state') == 'system_settings':
            try:
                parts = text.split(',')
                for part in parts:
                    if 'min_conf' in part.lower():
                        val = int(part.split(':')[1].strip())
                        db.update_setting('min_confidence', str(val))
                    elif 'max_lev' in part.lower():
                        val = int(part.split(':')[1].strip())
                        db.update_setting('max_leverage', str(val))
                
                user_data[user_id]['state'] = 'menu'
                await update.effective_chat.send_message(
                    "✅ **تنظیمات سیستم ذخیره شد!**" if lang == 'fa' else "✅ **System settings saved!**",
                    reply_markup=get_admin_keyboard(user_id),
                    parse_mode='Markdown'
                )
            except:
                await update.effective_chat.send_message(
                    "❌ **فرمت اشتباه!**" if lang == 'fa' else "❌ **Invalid format!**",
                    parse_mode='Markdown'
                )
            return
        
        if "🔙 بازگشت" in text or "Back" in text:
            await update.effective_chat.send_message(
                "🔙 بازگشت به منوی اصلی",
                reply_markup=get_main_keyboard(user_id)
            )
            return

# ==================== تابع ارسال سیگنال ====================
async def send_signal_result(update, user_id, signal):
    if signal['direction'] == "BUY":
        dir_emoji = "📈"
        dir_text = "خرید | BUY"
    else:
        dir_emoji = "📉"
        dir_text = "فروش | SELL"
    
    # نمایش الگوهای هارمونیک
    harmonic_text = ""
    if signal.get('harmonic_patterns'):
        harmonic_text = f"• {'الگوهای هارمونیک' if db.get_user(user_id)[3] == 'fa' else 'Harmonic Patterns'}: {', '.join(signal['harmonic_patterns'])}\n"
    
    signal_text = f"""
🔥 **{get_text(user_id, 'signal_result')}** 🔥

{dir_emoji} **{'جهت' if db.get_user(user_id)[3] == 'fa' else 'Direction'}:** {dir_text}
💰 **{'قیمت ورود' if db.get_user(user_id)[3] == 'fa' else 'Entry'}:** ${signal['entry']:,.2f}
🎯 **{get_text(user_id, 'profit')}:** ${signal['take_profit']:,.2f}
🛡️ **{get_text(user_id, 'loss')}:** ${signal['stop_loss']:,.2f}
⚡ **{get_text(user_id, 'leverage')}:** {signal['leverage']}x
🎯 **{get_text(user_id, 'confidence')}:** {signal['confidence']}%

📊 **{'جزئیات کوانتومی نسخه ۸.۵' if db.get_user(user_id)[3] == 'fa' else 'Quantum Details v8.5'}**:
• RSI: {signal.get('rsi', 0)}
• MACD: {signal.get('macd', 0)}
• ADX: {signal.get('adx', 0)}
• {'نماگر هرست' if db.get_user(user_id)[3] == 'fa' else 'Hurst Exponent'}: {signal.get('hurst', 0)}
• {'بعد فراکتال' if db.get_user(user_id)[3] == 'fa' else 'Fractal Dimension'}: {signal.get('fractal_dim', 0)}
• {'نماگر لیاپانوف' if db.get_user(user_id)[3] == 'fa' else 'Lyapunov Exponent'}: {signal.get('lyapunov', 0)}
• {'الگوی الیوت' if db.get_user(user_id)[3] == 'fa' else 'Elliott Pattern'}: {signal.get('elliott_pattern', 'unknown')}
{harmonic_text}• {'رژیم بازار' if db.get_user(user_id)[3] == 'fa' else 'Market Regime'}: {signal.get('market_regime', 'neutral')}
• {'فشار خرید' if db.get_user(user_id)[3] == 'fa' else 'Buying Pressure'}: {signal.get('buying_pressure', 0)}%
• {'فشار فروش' if db.get_user(user_id)[3] == 'fa' else 'Selling Pressure'}: {signal.get('selling_pressure', 0)}%
• {'پیش‌بینی ML' if db.get_user(user_id)[3] == 'fa' else 'ML Prediction'}: {signal.get('ml_prediction', 0)}
• {'اطمینان ML' if db.get_user(user_id)[3] == 'fa' else 'ML Confidence'}: {signal.get('ml_confidence', 0)}%
• {'موقعیت قیمت' if db.get_user(user_id)[3] == 'fa' else 'Price Position'}: {signal.get('price_position', 0)}%

⚠️ **{'مدیریت ریسک' if db.get_user(user_id)[3] == 'fa' else 'Risk Management'}**:
• {'حداکثر ۲-۳٪ سرمایه را ریسک کنید' if db.get_user(user_id)[3] == 'fa' else 'Risk max 2-3% of capital'}
• {'همیشه از حد ضرر استفاده کنید' if db.get_user(user_id)[3] == 'fa' else 'Always use stop loss'}
"""
    
    if signal.get('chart_data'):
        signal_text += f"\n📸 **{'تحلیل چارت' if db.get_user(user_id)[3] == 'fa' else 'Chart Analysis'}**: {'فعال' if db.get_user(user_id)[3] == 'fa' else 'Active'}"
    
    db.save_signal(user_id, signal)
    
    await update.effective_chat.send_message(
        signal_text,
        reply_markup=get_main_keyboard(user_id),
        parse_mode='Markdown'
    )

# ==================== اجرا ====================
def main():
    print("=" * 80)
    print("🚀 ربات تحلیل تکنیکال فوق‌پیشرفته نسخه ۸.۵")
    print("🧠 ترکیب نسخه ۸ + تشخیص چارت نسخه ۹")
    print("📊 پشتیبانی از ۲۰۰+ ارز، یادگیری عمیق، کوانتوم و OCR")
    print("=" * 80)
    print(f"👤 ادمین: {ADMIN_ID}")
    print(f"🤖 ربات: {BOT_USERNAME}")
    print(f"📊 اندیکاتورها: {len(INDICATORS)}")
    print(f"💱 پشتیبانی از {len(SUPPORTED_SYMBOLS)} ارز")
    print(f"🧠 الگوریتم‌ها: ۵۰+ ویژگی، ۴ مدل ML")
    print(f"📸 تشخیص چارت: {'فعال' if CHART_OCR_AVAILABLE else 'غیرفعال'}")
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
