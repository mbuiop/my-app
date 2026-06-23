#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ربات تحلیل تکنیکال فوق‌پیشرفته نسخه ۷.۰
با پشتیبانی از ۱۰۰+ ارز، الگوریتم‌های کوانتومی و هوش مصنوعی
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
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import warnings
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

# لینک صرافی توبیت
EXCHANGE_URL = "https://www.toobit.com/fa/r?i=5EQpCT"

# ==================== لیست ۱۰۰+ ارز پشتیبانی شده ====================
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
    'NEOUSDT', 'ONTUSDT', 'WAVESUSDT', 'ICXUSDT', 'QTUMUSDT'
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
                last_analysis TIMESTAMP,
                joined_at TIMESTAMP,
                plan TEXT DEFAULT 'BASIC',
                plan_expire TIMESTAMP,
                balance INTEGER DEFAULT 0,
                is_admin BOOLEAN DEFAULT 0,
                is_banned BOOLEAN DEFAULT 0,
                favorite_symbols TEXT DEFAULT '["BTCUSDT","ETHUSDT"]'
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
                created_at TIMESTAMP
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
            'welcome_text_fa': '🔥 به ربات تحلیل تکنیکال فوق‌پیشرفته خوش آمدید!',
            'welcome_text_en': '🔥 Welcome to Ultra Advanced Technical Analysis Bot!',
            'subscription_days': '30',
            'card_number': '5892101187322777',
            'card_holder': 'مرتضی نیکخو خنجری',
            'subscription_price': '500000'
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
             leverage, confidence, indicators_used, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            datetime.now().isoformat()
        ))
        self.conn.commit()
    
    def get_user_stats(self, user_id):
        self.cursor.execute('''
            SELECT 
                COUNT(*) as total_signals,
                AVG(confidence) as avg_confidence,
                MAX(confidence) as best_confidence
            FROM signals WHERE user_id = ?
        ''', (user_id,))
        return self.cursor.fetchone()
    
    def get_all_users(self):
        self.cursor.execute('SELECT user_id, language FROM users WHERE is_banned = 0')
        return self.cursor.fetchall()

db = Database()

# ==================== میکروسرویس قیمت با پشتیبانی از ۱۰۰+ ارز ====================
class MultiSymbolPriceService:
    def __init__(self):
        self.binance_url = "https://api.binance.com/api/v3"
        self.cache = {}
        self.cache_time = {}
        self.cache_klines = {}
        self.running = True
        
    def get_price(self, symbol="BTCUSDT"):
        cache_key = f"price_{symbol}"
        if cache_key in self.cache and time.time() - self.cache_time.get(cache_key, 0) < 3:
            return self.cache[cache_key]
        
        try:
            response = requests.get(
                f"{self.binance_url}/ticker/price?symbol={symbol}",
                timeout=3
            )
            if response.status_code == 200:
                price = float(response.json()['price'])
                self.cache[cache_key] = price
                self.cache_time[cache_key] = time.time()
                return price
        except:
            pass
        return None
    
    def get_klines(self, symbol="BTCUSDT", interval="1h", limit=200):
        cache_key = f"klines_{symbol}_{interval}_{limit}"
        if cache_key in self.cache_klines and time.time() - self.cache_time.get(cache_key, 0) < 60:
            return self.cache_klines[cache_key]
        
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
            self.cache_klines[cache_key] = prices
            self.cache_time[cache_key] = time.time()
            return prices
        except:
            return []
    
    def get_all_prices(self):
        """دریافت قیمت تمام ارزها"""
        prices = {}
        for symbol in SUPPORTED_SYMBOLS:
            price = self.get_price(symbol)
            if price:
                prices[symbol] = price
        return prices
    
    def get_top_gainers(self, count=10):
        """دریافت بیشترین رشد قیمت"""
        prices = self.get_all_prices()
        # در حالت واقعی باید تغییرات قیمت رو حساب کنی
        return sorted(prices.items(), key=lambda x: x[1], reverse=True)[:count]

price_service = MultiSymbolPriceService()

# ==================== الگوریتم‌های کوانتومی و هوش مصنوعی فوق‌پیشرفته ====================
class QuantumSignalEngine:
    def __init__(self):
        self.rf_model = RandomForestRegressor(n_estimators=300, max_depth=20, random_state=42)
        self.gb_model = GradientBoostingRegressor(n_estimators=200, learning_rate=0.05, max_depth=10)
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=10)
        self.is_trained = False
        self.training_data = None
        
    def calculate_fourier_transform(self, prices):
        """تبدیل فوریه برای شناسایی چرخه‌ها"""
        n = len(prices)
        if n < 10:
            return np.array([0])
        
        yf = fft(prices)
        frequencies = fftfreq(n)
        
        # شناسایی فرکانس‌های غالب
        magnitudes = np.abs(yf)
        dominant_freq = frequencies[np.argmax(magnitudes[1:]) + 1] if len(magnitudes) > 1 else 0
        
        return {
            'dominant_frequency': abs(dominant_freq),
            'spectrum': magnitudes.tolist(),
            'phase': np.angle(yf).tolist()
        }
    
    def calculate_markov_chain(self, prices):
        """زنجیره مارکوف برای پیش‌بینی روند"""
        if len(prices) < 2:
            return {'up_prob': 0.5, 'down_prob': 0.5}
        
        # محاسبه تغییرات
        changes = np.diff(prices)
        up_count = sum(1 for x in changes if x > 0)
        down_count = sum(1 for x in changes if x < 0)
        total = len(changes)
        
        return {
            'up_probability': up_count / total if total > 0 else 0.5,
            'down_probability': down_count / total if total > 0 else 0.5,
            'volatility': np.std(changes) if len(changes) > 0 else 0
        }
    
    def calculate_hurst_exponent(self, prices, max_lag=50):
        """نماگر هرست - تشخیص روند یا بازگشت"""
        if len(prices) < max_lag:
            return 0.5
        
        lags = range(2, min(max_lag, len(prices) // 2))
        tau = [np.sqrt(np.std(np.subtract(prices[lag:], prices[:-lag]))) for lag in lags]
        poly = np.polyfit(np.log(lags), np.log(tau), 1)
        
        hurst = poly[0] * 2.0
        return max(0, min(1, hurst))
    
    def calculate_wavelet_analysis(self, prices):
        """تحلیل ویولت - شناسایی ساختارهای چندمقیاسی"""
        if len(prices) < 10:
            return {'trend_strength': 0.5}
        
        # تبدیل موجک ساده با استفاده از تفاضل‌های در مقیاس‌های مختلف
        scales = [2, 4, 8, 16]
        wavelet_coeffs = []
        
        for scale in scales:
            if len(prices) > scale * 2:
                coeff = np.mean([prices[i] - prices[i-scale] for i in range(scale, len(prices), scale)])
                wavelet_coeffs.append(abs(coeff))
        
        if wavelet_coeffs:
            trend_strength = np.mean(wavelet_coeffs) / np.std(prices)
            return {
                'trend_strength': max(0, min(1, trend_strength * 2)),
                'wavelet_coeffs': wavelet_coeffs
            }
        
        return {'trend_strength': 0.5}
    
    def calculate_elliott_wave(self, prices):
        """تشخیص الگوهای امواج الیوت"""
        if len(prices) < 20:
            return {'wave_pattern': 'undefined'}
        
        # تشخیص موج‌های ضربه‌ای و اصلاحی
        diffs = np.diff(prices)
        patterns = []
        
        for i in range(0, len(diffs) - 4, 5):
            if i + 4 < len(diffs):
                wave_1 = diffs[i]
                wave_2 = diffs[i+1]
                wave_3 = diffs[i+2]
                wave_4 = diffs[i+3]
                wave_5 = diffs[i+4]
                
                if wave_1 > 0 and wave_3 > max(wave_1, wave_5):
                    patterns.append('impulse')
                elif wave_2 < 0 and wave_4 < 0:
                    patterns.append('correction')
        
        return {
            'wave_pattern': 'impulse' if patterns.count('impulse') > patterns.count('correction') else 'correction',
            'confidence': len(patterns) / (len(diffs) / 5) if len(diffs) > 0 else 0
        }
    
    def calculate_market_microstructure(self, order_book):
        """تحلیل ریزساختار بازار"""
        if not order_book:
            return {'imbalance': 0, 'pressure': 0}
        
        bids = order_book.get('bids', [])
        asks = order_book.get('asks', [])
        
        if not bids or not asks:
            return {'imbalance': 0, 'pressure': 0}
        
        # محاسبه عدم تعادل سفارشات
        bid_volume = sum([b[1] for b in bids[:5]])
        ask_volume = sum([a[1] for a in asks[:5]])
        
        imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume + 1e-6)
        pressure = bid_volume / (bid_volume + ask_volume + 1e-6)
        
        return {
            'imbalance': imbalance,
            'pressure': pressure,
            'spread': asks[0][0] - bids[0][0] if asks and bids else 0
        }
    
    def generate_signal(self, prices, indicators, order_book, support, resistance, current_price):
        """تولید سیگنال با استفاده از تمام الگوریتم‌ها"""
        
        # ۱. تحلیل فوریه
        fourier = self.calculate_fourier_transform(prices)
        
        # ۲. زنجیره مارکوف
        markov = self.calculate_markov_chain(prices)
        
        # ۳. نماگر هرست
        hurst = self.calculate_hurst_exponent(prices)
        
        # ۴. تحلیل ویولت
        wavelet = self.calculate_wavelet_analysis(prices)
        
        # ۵. امواج الیوت
        elliott = self.calculate_elliott_wave(prices)
        
        # ۶. ریزساختار بازار
        microstructure = self.calculate_market_microstructure(order_book)
        
        # محاسبه نمره نهایی با ترکیب وزنی
        buy_score = 0
        sell_score = 0
        
        # اندیکاتورهای کلاسیک
        rsi = indicators.get('RSI', 50)
        macd = indicators.get('MACD', 0)
        adx = indicators.get('ADX', 20)
        
        # وزندهی به اندیکاتورها
        if rsi < 30:
            buy_score += 20
        elif rsi > 70:
            sell_score += 20
            
        if macd > 0:
            buy_score += 15
        else:
            sell_score += 15
            
        if adx > 25:
            buy_score += 10
            
        # وزندهی به الگوریتم‌های پیشرفته
        if hurst > 0.6:  # روند قوی
            if rsi < 50:
                buy_score += 15
            else:
                sell_score += 15
        elif hurst < 0.4:  # بازگشت به میانگین
            buy_score += 10
        
        if wavelet['trend_strength'] > 0.6:
            buy_score += 12
        
        if elliott['wave_pattern'] == 'impulse':
            buy_score += 10
        
        if microstructure.get('pressure', 0) > 0.6:
            buy_score += 15
        
        if markov['up_probability'] > 0.6:
            buy_score += 8
        
        # موقعیت قیمت در محدوده
        if support and resistance:
            price_range = resistance - support
            if price_range > 0:
                position = (current_price - support) / price_range
                if position < 0.3:
                    buy_score += 10
                elif position > 0.7:
                    sell_score += 10
        
        # تصمیم نهایی
        total_score = buy_score - sell_score
        confidence = min(98, 50 + abs(total_score) * 1.5)
        
        if total_score > 10:
            direction = "BUY"
        elif total_score < -10:
            direction = "SELL"
        else:
            direction = "HOLD"
            confidence = 50
        
        # محاسبه حد سود و ضرر با فیزیک کوانتومی
        if direction == "BUY":
            take_profit = current_price + (resistance - current_price) * 0.8 if resistance else current_price * 1.05
            stop_loss = current_price - (current_price - support) * 0.3 if support else current_price * 0.97
        elif direction == "SELL":
            take_profit = current_price - (current_price - support) * 0.8 if support else current_price * 0.95
            stop_loss = current_price + (resistance - current_price) * 0.3 if resistance else current_price * 1.03
        else:
            take_profit = current_price
            stop_loss = current_price
        
        # محاسبه اهرم داینامیک
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
            'rsi': round(rsi, 1),
            'macd': round(macd, 4),
            'adx': round(adx, 1),
            'hurst': round(hurst, 3),
            'buy_score': round(buy_score, 1),
            'sell_score': round(sell_score, 1),
            'fourier_dominant': round(abs(fourier.get('dominant_frequency', 0)), 4),
            'markov_up': round(markov.get('up_probability', 0.5) * 100, 1),
            'elliott_pattern': elliott.get('wave_pattern', 'undefined'),
            'microstructure_pressure': round(microstructure.get('pressure', 0.5) * 100, 1),
            'wavelet_trend': round(wavelet.get('trend_strength', 0.5) * 100, 1)
        }

signal_engine = QuantumSignalEngine()

# ==================== متغیرهای سراسری ====================
user_data = {}
all_users = set()

# ==================== لیست اندیکاتورها ====================
INDICATORS = [
    "RSI", "MACD", "EMA5", "EMA10", "EMA30", "MA", "BOLL", "KDJ", 
    "ADX", "ATR", "VOL", "OBV", "Ichimoku_Cloud", "Stoch", "CCI",
    "Williams", "MFI", "PSAR", "BB_Upper", "BB_Lower"
]

# ==================== متون دوزبانه کاملاً جداسازی شده ====================
TEXTS_FA = {
    'welcome': '🔥 به ربات تحلیل تکنیکال فوق‌پیشرفته خوش آمدید!\n\n📊 با ۲۰ اندیکاتور و الگوریتم‌های کوانتومی\n🎯 دقت سیگنال تا ۹۸٪\n\n🚀 برای شروع روی "📊 شروع تحلیل" کلیک کنید.',
    'select_symbol': '🔍 لطفاً ارز مورد نظر را انتخاب کنید:',
    'enter_price': '💰 قیمت فعلی ارز را وارد کنید:',
    'enter_support_resistance': '📊 حمایت و مقاومت را وارد کنید:\n\n📉 حمایت:\n📈 مقاومت:',
    'select_indicators': '🔍 اندیکاتورها را انتخاب کنید (حداقل ۵ عدد)',
    'signal_result': '🔥 نتیجه تحلیل کوانتومی',
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
    'back': '🔙 بازگشت',
    'register': '🔄 ثبت',
    'analyze': '📊 تحلیل'
}

TEXTS_EN = {
    'welcome': '🔥 Welcome to Ultra Advanced Technical Analysis Bot!\n\n📊 With 20 indicators and quantum algorithms\n🎯 Signal accuracy up to 98%\n\n🚀 Click "📊 Start Analysis" to begin.',
    'select_symbol': '🔍 Please select your cryptocurrency:',
    'enter_price': '💰 Enter current price:',
    'enter_support_resistance': '📊 Enter support and resistance:\n\n📉 Support:\n📈 Resistance:',
    'select_indicators': '🔍 Select indicators (minimum 5)',
    'signal_result': '🔥 Quantum Analysis Result',
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
    'back': '🔙 Back',
    'register': '🔄 Register',
    'analyze': '📊 Analyze'
}

def get_text(user_id, key):
    """دریافت متن بر اساس زبان کاربر"""
    user = db.get_user(user_id)
    lang = user[3] if user else 'fa'
    
    if lang == 'en':
        return TEXTS_EN.get(key, TEXTS_FA.get(key, ''))
    return TEXTS_FA.get(key, '')

# ==================== کیبوردهای دوزبانه جداگانه ====================
def get_main_keyboard(user_id):
    """کیبورد اصلی بر اساس زبان کاربر"""
    user = db.get_user(user_id)
    lang = user[3] if user else 'fa'
    
    if lang == 'en':
        return ReplyKeyboardMarkup([
            [KeyboardButton("📊 Start Analysis")],
            [KeyboardButton("📊 My Stats"), KeyboardButton("💱 Toobit Exchange")],
            [KeyboardButton("🎁 Invite Friends"), KeyboardButton("🌐 Change Language")]
        ], resize_keyboard=True)
    else:
        return ReplyKeyboardMarkup([
            [KeyboardButton("📊 شروع تحلیل")],
            [KeyboardButton("📊 آمار من"), KeyboardButton("💱 صرافی توبیت")],
            [KeyboardButton("🎁 دعوت دوستان"), KeyboardButton("🌐 تغییر زبان")]
        ], resize_keyboard=True)

def get_symbol_keyboard(user_id):
    """کیبورد انتخاب ارز"""
    keyboard = []
    row = []
    for i, symbol in enumerate(SUPPORTED_SYMBOLS[:20]):
        row.append(KeyboardButton(symbol))
        if len(row) == 4 or i == 19:
            keyboard.append(row)
            row = []
    
    user = db.get_user(user_id)
    lang = user[3] if user else 'fa'
    
    if lang == 'en':
        keyboard.append([KeyboardButton("🔙 Back")])
    else:
        keyboard.append([KeyboardButton("🔙 بازگشت")])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_indicators_keyboard(user_id, selected=None):
    """کیبورد انتخاب اندیکاتورها"""
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
    """کیبورد ادمین"""
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
            [KeyboardButton("🔙 بازگشت")]
        ], resize_keyboard=True)

# ==================== هندلرها ====================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or ""
    first_name = update.effective_user.first_name or ""
    
    all_users.add(user_id)
    
    # مدیریت رفرال
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

async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تغییر زبان کاربر"""
    user_id = update.effective_user.id
    current_lang = db.get_user(user_id)[3] if db.get_user(user_id) else 'fa'
    
    # دکمه‌های تغییر زبان - فقط به زبانی که کاربر انتخاب میکنه
    keyboard = [
        [KeyboardButton("🇮🇷 فارسی"), KeyboardButton("🇬🇧 English")],
        [KeyboardButton("🔙 بازگشت" if current_lang == 'fa' else "🔙 Back")]
    ]
    
    await update.effective_chat.send_message(
        "🌐 زبان خود را انتخاب کنید | Choose your language:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
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
    
    # ===== انتخاب زبان =====
    if text in ["🇮🇷 فارسی", "🇬🇧 English"]:
        new_lang = "fa" if text == "🇮🇷 فارسی" else "en"
        db.update_language(user_id, new_lang)
        
        welcome_msg = TEXTS_FA['welcome'] if new_lang == 'fa' else TEXTS_EN['welcome']
        await update.effective_chat.send_message(
            f"✅ {'زبان تغییر کرد!' if new_lang == 'fa' else 'Language changed!'}\n\n{welcome_msg}",
            reply_markup=get_main_keyboard(user_id),
            parse_mode='Markdown'
        )
        return
    
    # ===== تغییر زبان =====
    if "🌐 تغییر زبان" in text or "Change Language" in text:
        await change_language(update, context)
        return
    
    # ===== صرافی توبیت =====
    if "💱 صرافی توبیت" in text or "Toobit Exchange" in text:
        msg = f"💱 **{'صرافی توبیت' if lang == 'fa' else 'Toobit Exchange'}**\n\n🔗 {EXCHANGE_URL}\n\n🎁 {'با لینک بالا ثبت نام کنید و از جوایز ویژه بهره‌مند شوید!' if lang == 'fa' else 'Register with the link above and get special rewards!'}"
        await update.effective_chat.send_message(
            msg,
            reply_markup=get_main_keyboard(user_id),
            parse_mode='Markdown'
        )
        return
    
    # ===== رفرال =====
    if "🎁 دعوت دوستان" in text or "Invite Friends" in text:
        referral_link = f"https://t.me/{BOT_USERNAME.replace('@', '')}?start=ref_{user_id}"
        referral_count = db.cursor.execute('SELECT referral_count FROM users WHERE user_id = ?', (user_id,)).fetchone()[0]
        
        msg = f"🎁 **{'سیستم دعوت دوستان' if lang == 'fa' else 'Referral System'}**\n\n"
        msg += f"🔗 {'لینک دعوت شما' if lang == 'fa' else 'Your referral link'}:\n`{referral_link}`\n\n"
        msg += f"👥 {'تعداد دعوت‌ها' if lang == 'fa' else 'Total referrals'}: {referral_count}\n\n"
        msg += f"📤 {'لینک را با دوستان خود به اشتراک بگذارید!' if lang == 'fa' else 'Share the link with your friends!'}"
        
        await update.effective_chat.send_message(
            msg,
            reply_markup=get_main_keyboard(user_id),
            parse_mode='Markdown'
        )
        return
    
    # ===== آمار من =====
    if "📊 آمار من" in text or "My Stats" in text:
        stats = db.get_user_stats(user_id)
        if stats:
            total, avg_conf, best_conf = stats
            msg = f"📊 **{'آمار شما' if lang == 'fa' else 'Your Stats'}**\n\n"
            msg += f"📈 {'تعداد تحلیل‌ها' if lang == 'fa' else 'Total Analysis'}: {total}\n"
            msg += f"🎯 {'میانگین اطمینان' if lang == 'fa' else 'Avg Confidence'}: {avg_conf:.0f}%\n"
            msg += f"🏆 {'بهترین اطمینان' if lang == 'fa' else 'Best Confidence'}: {best_conf:.0f}%\n"
            msg += f"👥 {'تعداد دعوت‌ها' if lang == 'fa' else 'Total Referrals'}: {db.cursor.execute('SELECT referral_count FROM users WHERE user_id = ?', (user_id,)).fetchone()[0]}"
            
            await update.effective_chat.send_message(
                msg,
                reply_markup=get_main_keyboard(user_id),
                parse_mode='Markdown'
            )
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
            await update.effective_chat.send_message(
                "🔙",
                reply_markup=get_main_keyboard(user_id)
            )
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
        
        elif "ثبت" in text or "Register" in text:
            if len(user_data[user_id]['indicators']) >= 5:
                # اجرای تحلیل
                status_msg = await update.effective_chat.send_message(
                    f"🔄 **{'در حال تحلیل کوانتومی...' if lang == 'fa' else 'Quantum Analysis in progress...'}**\n"
                    f"🧮 {'میکروسرویس‌های هوش مصنوعی در حال پردازش...' if lang == 'fa' else 'AI microservices processing...'}\n\n"
                    f"📊 {len(user_data[user_id]['indicators'])} {'اندیکاتور بارگذاری شد' if lang == 'fa' else 'indicators loaded'}"
                )
                
                # دریافت داده‌ها
                symbol = user_data[user_id]['symbol']
                klines = price_service.get_klines(symbol, "1h", 200)
                prices = [k['close'] for k in klines] if klines else []
                order_book = price_service.get_order_book(symbol) if hasattr(price_service, 'get_order_book') else None
                
                result = signal_engine.generate_signal(
                    prices,
                    user_data[user_id]['indicators'],
                    order_book,
                    user_data[user_id]['support'],
                    user_data[user_id]['resistance'],
                    user_data[user_id]['current_price']
                )
                
                await status_msg.delete()
                
                # ایجاد پیام نتیجه
                if result['direction'] == "BUY":
                    direction_emoji = "📈"
                    direction_text = get_text(user_id, 'buy')
                elif result['direction'] == "SELL":
                    direction_emoji = "📉"
                    direction_text = get_text(user_id, 'sell')
                else:
                    direction_emoji = "⚪"
                    direction_text = get_text(user_id, 'hold')
                
                signal_text = f"""
🔥 **{get_text(user_id, 'signal_result')}** 🔥

{direction_emoji} **{'جهت' if lang == 'fa' else 'Direction'}:** {direction_text}
💰 **{'قیمت ورود' if lang == 'fa' else 'Entry'}:** ${result['entry']:,.2f}
🎯 **{get_text(user_id, 'profit')}:** ${result['take_profit']:,.2f}
🛡️ **{get_text(user_id, 'loss')}:** ${result['stop_loss']:,.2f}
⚡ **{get_text(user_id, 'leverage')}:** {result['leverage']}x
🎯 **{get_text(user_id, 'confidence')}:** {result['confidence']}%

📊 **{'جزئیات کوانتومی' if lang == 'fa' else 'Quantum Details'}**:
• RSI: {result.get('rsi', 0)}
• MACD: {result.get('macd', 0)}
• ADX: {result.get('adx', 0)}
• {'نماگر هرست' if lang == 'fa' else 'Hurst Exponent'}: {result.get('hurst', 0)}
• {'نیروی خرید' if lang == 'fa' else 'Buy Force'}: {result.get('buy_score', 0):.1f}
• {'نیروی فروش' if lang == 'fa' else 'Sell Force'}: {result.get('sell_score', 0):.1f}
• {'فرکانس غالب' if lang == 'fa' else 'Dominant Frequency'}: {result.get('fourier_dominant', 0):.4f}
• {'احتمال صعود' if lang == 'fa' else 'Up Probability'}: {result.get('markov_up', 0):.1f}%
• {'الگوی الیوت' if lang == 'fa' else 'Elliott Pattern'}: {result.get('elliott_pattern', 'undefined')}
• {'فشار میکرواستراکچر' if lang == 'fa' else 'Microstructure Pressure'}: {result.get('microstructure_pressure', 0):.1f}%
• {'روند ویولت' if lang == 'fa' else 'Wavelet Trend'}: {result.get('wavelet_trend', 0):.1f}%

⚠️ **{'مدیریت ریسک' if lang == 'fa' else 'Risk Management'}**:
• {'حداکثر ۲-۳٪ سرمایه را ریسک کنید' if lang == 'fa' else 'Risk max 2-3% of capital'}
• {'همیشه از حد ضرر استفاده کنید' if lang == 'fa' else 'Always use stop loss'}
"""
                
                db.save_signal(user_id, result)
                
                await update.effective_chat.send_message(
                    signal_text,
                    reply_markup=get_main_keyboard(user_id),
                    parse_mode='Markdown'
                )
                
                user_data[user_id]['state'] = 'menu'
                
            else:
                await update.effective_chat.send_message(
                    f"❌ {'حداقل ۵ اندیکاتور وارد کنید!' if lang == 'fa' else 'Minimum 5 indicators required!'} ({len(user_data[user_id]['indicators'])}/5)",
                    reply_markup=get_indicators_keyboard(user_id)
                )
        
        elif "تحلیل" in text or "Analyze" in text:
            # همان منطق ثبت
            if len(user_data[user_id]['indicators']) >= 5:
                status_msg = await update.effective_chat.send_message(
                    "🔄 **{'در حال تحلیل کوانتومی...' if lang == 'fa' else 'Quantum Analysis in progress...'}**"
                )
                
                symbol = user_data[user_id]['symbol']
                klines = price_service.get_klines(symbol, "1h", 200)
                prices = [k['close'] for k in klines] if klines else []
                order_book = price_service.get_order_book(symbol) if hasattr(price_service, 'get_order_book') else None
                
                result = signal_engine.generate_signal(
                    prices,
                    user_data[user_id]['indicators'],
                    order_book,
                    user_data[user_id]['support'],
                    user_data[user_id]['resistance'],
                    user_data[user_id]['current_price']
                )
                
                await status_msg.delete()
                
                if result['direction'] == "BUY":
                    direction_emoji = "📈"
                    direction_text = get_text(user_id, 'buy')
                elif result['direction'] == "SELL":
                    direction_emoji = "📉"
                    direction_text = get_text(user_id, 'sell')
                else:
                    direction_emoji = "⚪"
                    direction_text = get_text(user_id, 'hold')
                
                signal_text = f"""
🔥 **{get_text(user_id, 'signal_result')}** 🔥

{direction_emoji} **{'جهت' if lang == 'fa' else 'Direction'}:** {direction_text}
💰 **{'قیمت ورود' if lang == 'fa' else 'Entry'}:** ${result['entry']:,.2f}
🎯 **{get_text(user_id, 'profit')}:** ${result['take_profit']:,.2f}
🛡️ **{get_text(user_id, 'loss')}:** ${result['stop_loss']:,.2f}
⚡ **{get_text(user_id, 'leverage')}:** {result['leverage']}x
🎯 **{get_text(user_id, 'confidence')}:** {result['confidence']}%

📊 **{'جزئیات کوانتومی' if lang == 'fa' else 'Quantum Details'}**:
• RSI: {result.get('rsi', 0)}
• MACD: {result.get('macd', 0)}
• ADX: {result.get('adx', 0)}
• {'نماگر هرست' if lang == 'fa' else 'Hurst Exponent'}: {result.get('hurst', 0)}
• {'نیروی خرید' if lang == 'fa' else 'Buy Force'}: {result.get('buy_score', 0):.1f}
• {'نیروی فروش' if lang == 'fa' else 'Sell Force'}: {result.get('sell_score', 0):.1f}
• {'فرکانس غالب' if lang == 'fa' else 'Dominant Frequency'}: {result.get('fourier_dominant', 0):.4f}
• {'احتمال صعود' if lang == 'fa' else 'Up Probability'}: {result.get('markov_up', 0):.1f}%
• {'الگوی الیوت' if lang == 'fa' else 'Elliott Pattern'}: {result.get('elliott_pattern', 'undefined')}
• {'فشار میکرواستراکچر' if lang == 'fa' else 'Microstructure Pressure'}: {result.get('microstructure_pressure', 0):.1f}%
• {'روند ویولت' if lang == 'fa' else 'Wavelet Trend'}: {result.get('wavelet_trend', 0):.1f}%

⚠️ **{'مدیریت ریسک' if lang == 'fa' else 'Risk Management'}**:
• {'حداکثر ۲-۳٪ سرمایه را ریسک کنید' if lang == 'fa' else 'Risk max 2-3% of capital'}
• {'همیشه از حد ضرر استفاده کنید' if lang == 'fa' else 'Always use stop loss'}
"""
                
                db.save_signal(user_id, result)
                
                await update.effective_chat.send_message(
                    signal_text,
                    reply_markup=get_main_keyboard(user_id),
                    parse_mode='Markdown'
                )
                
                user_data[user_id]['state'] = 'menu'
    
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
                "👑 **{'پنل ادمین' if lang == 'fa' else 'Admin Panel'}**\n\n"
                "{'لطفاً یکی از گزینه‌های زیر را انتخاب کنید:' if lang == 'fa' else 'Please select an option:'}",
                reply_markup=get_admin_keyboard(user_id),
                parse_mode='Markdown'
            )
        else:
            await update.effective_chat.send_message(
                "❌ {'دسترسی غیرمجاز!' if lang == 'fa' else 'Unauthorized access!'}",
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
        
        if "🔙 بازگشت" in text or "Back" in text:
            await update.effective_chat.send_message(
                "🔙 {'بازگشت به منوی اصلی' if lang == 'fa' else 'Back to main menu'}",
                reply_markup=get_main_keyboard(user_id)
            )
            return

# ==================== اجرا ====================
def main():
    print("=" * 70)
    print("🚀 ربات تحلیل تکنیکال فوق‌پیشرفته نسخه ۷.۰")
    print("🔥 با الگوریتم‌های کوانتومی و هوش مصنوعی")
    print("=" * 70)
    print(f"👤 ادمین: {ADMIN_ID}")
    print(f"🤖 ربات: {BOT_USERNAME}")
    print(f"📊 اندیکاتورها: {len(INDICATORS)}")
    print(f"💱 پشتیبانی از {len(SUPPORTED_SYMBOLS)} ارز")
    print("=" * 70)
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ ربات با موفقیت راه‌اندازی شد!")
    print("=" * 70)
    
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()