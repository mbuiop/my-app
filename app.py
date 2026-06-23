#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ربات تحلیل تکنیکال فوق‌پیشرفته نسخه ۶.۰
با سیستم میکروسرویس و الگوریتم‌های پیشرفته
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
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
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
                is_banned BOOLEAN DEFAULT 0
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
        
        # تنظیمات پیش‌فرض
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

# ==================== میکروسرویس دریافت قیمت ====================
class PriceMicroservice:
    def __init__(self):
        self.binance_url = "https://api.binance.com/api/v3"
        self.cache = {}
        self.cache_time = {}
        self.running = True
        
    def get_price(self, symbol="BTCUSDT"):
        if symbol in self.cache and time.time() - self.cache_time.get(symbol, 0) < 3:
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
    
    def get_klines(self, symbol="BTCUSDT", interval="1h", limit=200):
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
                'best_ask': asks[0][0] if asks else 0
            }
        except:
            return None

price_microservice = PriceMicroservice()

# ==================== الگوریتم‌های پیشرفته فیزیک و ریاضی ====================
class AdvancedSignalEngine:
    def __init__(self):
        self.weights = {
            'RSI': 5.0, 'MACD': 4.8, 'EMA5': 4.5, 'EMA10': 4.2, 'EMA30': 4.0,
            'MA': 3.8, 'BOLL': 4.6, 'KDJ': 4.4, 'ADX': 4.2, 'ATR': 3.5,
            'VOL': 3.2, 'OBV': 3.5, 'Ichimoku_Cloud': 4.3, 'Stoch': 4.1,
            'CCI': 3.9, 'Williams': 3.7, 'MFI': 4.0, 'PSAR': 3.6,
            'BB_Upper': 3.4, 'BB_Lower': 3.4
        }
    
    def calculate_rsi(self, prices, period=14):
        if len(prices) < period + 1:
            return 50
        
        delta = prices[-1] - prices[-period-1]
        gain = max(delta, 0)
        loss = max(-delta, 0)
        
        for i in range(len(prices) - period, len(prices) - 1):
            delta = prices[i] - prices[i-1]
            gain = gain * (period - 1) / period + max(delta, 0)
            loss = loss * (period - 1) / period + max(-delta, 0)
        
        rs = gain / loss if loss > 0 else 100
        return 100 - (100 / (1 + rs))
    
    def calculate_bollinger(self, prices, period=20, std_dev=2):
        if len(prices) < period:
            return {'upper': 0, 'middle': 0, 'lower': 0}
        
        sma = np.mean(prices[-period:])
        std = np.std(prices[-period:])
        
        return {
            'upper': sma + std * std_dev,
            'middle': sma,
            'lower': sma - std * std_dev
        }
    
    def calculate_macd(self, prices, fast=12, slow=26, signal=9):
        if len(prices) < slow:
            return {'macd': 0, 'signal': 0, 'histogram': 0}
        
        ema_fast = np.mean(prices[-fast:]) if len(prices) < fast else np.mean(prices[-fast:])
        ema_slow = np.mean(prices[-slow:]) if len(prices) < slow else np.mean(prices[-slow:])
        
        macd = ema_fast - ema_slow
        macd_signal = macd * 0.8 + ema_fast * 0.2
        
        return {
            'macd': macd,
            'signal': macd_signal,
            'histogram': macd - macd_signal
        }
    
    def calculate_adx(self, prices, period=14):
        if len(prices) < period + 1:
            return 0
        
        high_low = [p['high'] - p['low'] for p in prices]
        high_close = [abs(p['high'] - prices[i-1]['close']) for i, p in enumerate(prices) if i > 0]
        low_close = [abs(p['low'] - prices[i-1]['close']) for i, p in enumerate(prices) if i > 0]
        
        true_ranges = []
        for i in range(len(prices)):
            if i == 0:
                true_ranges.append(prices[i]['high'] - prices[i]['low'])
            else:
                tr = max(
                    prices[i]['high'] - prices[i]['low'],
                    abs(prices[i]['high'] - prices[i-1]['close']),
                    abs(prices[i]['low'] - prices[i-1]['close'])
                )
                true_ranges.append(tr)
        
        atr = np.mean(true_ranges[-period:])
        
        plus_dm = []
        minus_dm = []
        for i in range(1, len(prices)):
            plus = max(0, prices[i]['high'] - prices[i-1]['high'])
            minus = max(0, prices[i-1]['low'] - prices[i]['low'])
            plus_dm.append(plus)
            minus_dm.append(minus)
        
        plus_di = 100 * (np.mean(plus_dm[-period:]) / atr) if atr > 0 else 0
        minus_di = 100 * (np.mean(minus_dm[-period:]) / atr) if atr > 0 else 0
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) > 0 else 0
        return dx
    
    def analyze_with_physics(self, indicators, support, resistance, current_price):
        """تحلیل با الگوریتم‌های فیزیک و ریاضی"""
        
        # محاسبه نیروی بازار (قانون دوم نیوتن)
        price_range = resistance - support
        price_position = (current_price - support) / price_range if price_range > 0 else 0.5
        
        # نیروی خرید و فروش
        buy_force = 0
        sell_force = 0
        
        for indicator, value in indicators.items():
            try:
                val = float(value)
                
                if indicator == 'RSI':
                    if val < 30:
                        buy_force += (30 - val) * 0.5
                    elif val > 70:
                        sell_force += (val - 70) * 0.5
                
                elif indicator == 'MACD':
                    if val > 0:
                        buy_force += val * 0.3
                    else:
                        sell_force += abs(val) * 0.3
                
                elif indicator in ['EMA5', 'EMA10', 'EMA30', 'MA']:
                    if val < current_price:
                        buy_force += (current_price - val) / current_price * 2
                    else:
                        sell_force += (val - current_price) / current_price * 2
                
                elif indicator == 'ADX':
                    if val > 25:
                        force = (val - 25) / 25 * 0.5
                        if price_position < 0.3:
                            buy_force += force
                        elif price_position > 0.7:
                            sell_force += force
                
                elif indicator == 'BOLL':
                    if val < support:
                        buy_force += 0.5
                    elif val > resistance:
                        sell_force += 0.5
                
                elif indicator in ['KDJ', 'Stoch']:
                    if val < 20:
                        buy_force += (20 - val) * 0.3
                    elif val > 80:
                        sell_force += (val - 80) * 0.3
            except:
                continue
        
        # محاسبه شتاب بازار (قانون اول نیوتن)
        acceleration = buy_force - sell_force
        
        # محاسبه مومنتوم (قانون پایستگی)
        momentum = buy_force + sell_force
        
        # محاسبه انرژی پتانسیل
        potential_energy = abs(price_position - 0.5) * 2
        
        # امتیاز نهایی
        net_score = buy_force - sell_force
        max_force = max(buy_force, sell_force, 1)
        normalized_score = (net_score / max_force) * 5
        
        # تعیین جهت با قوانین فیزیک
        if acceleration > 0.5 and buy_force > sell_force:
            direction = "BUY"
            confidence = min(95, 60 + (buy_force / (buy_force + sell_force) * 40))
        elif acceleration < -0.5 and sell_force > buy_force:
            direction = "SELL"
            confidence = min(95, 60 + (sell_force / (buy_force + sell_force) * 40))
        else:
            direction = "HOLD"
            confidence = 50
        
        # محاسبه حد سود و ضرر با قانون هوک (ارتعاشات)
        if direction == "BUY":
            take_profit = current_price + (resistance - current_price) * 0.7
            stop_loss = current_price - (current_price - support) * 0.3
        elif direction == "SELL":
            take_profit = current_price - (current_price - support) * 0.7
            stop_loss = current_price + (resistance - current_price) * 0.3
        else:
            take_profit = current_price
            stop_loss = current_price
        
        # محاسبه اهرم بر اساس قدرت سیگنال
        leverage = min(30, max(3, int(confidence / 10) + 2))
        
        return {
            'direction': direction,
            'entry': round(current_price, 2),
            'take_profit': round(take_profit, 2),
            'stop_loss': round(stop_loss, 2),
            'leverage': leverage,
            'confidence': round(confidence),
            'buy_force': round(buy_force, 2),
            'sell_force': round(sell_force, 2),
            'momentum': round(momentum, 2),
            'price_position': round(price_position * 100, 1)
        }
    
    def generate_signal(self, indicators, support, resistance, current_price):
        """تولید سیگنال نهایی با الگوریتم‌های ترکیبی"""
        
        # دریافت قیمت واقعی
        live_price = price_microservice.get_price()
        if live_price:
            current_price = live_price
        
        # تحلیل با فیزیک
        physics_result = self.analyze_with_physics(indicators, support, resistance, current_price)
        
        # تحلیل تکنیکال پیشرفته
        rsi_value = indicators.get('RSI', 50)
        macd_value = indicators.get('MACD', 0)
        adx_value = indicators.get('ADX', 20)
        
        # ترکیب نتایج
        if physics_result['direction'] == "BUY":
            if rsi_value < 30 and adx_value > 25:
                confidence = min(95, physics_result['confidence'] + 15)
                direction = "BUY"
            elif rsi_value < 40 and macd_value > 0:
                confidence = min(90, physics_result['confidence'] + 10)
                direction = "BUY"
            else:
                confidence = physics_result['confidence']
                direction = "BUY"
                
        elif physics_result['direction'] == "SELL":
            if rsi_value > 70 and adx_value > 25:
                confidence = min(95, physics_result['confidence'] + 15)
                direction = "SELL"
            elif rsi_value > 60 and macd_value < 0:
                confidence = min(90, physics_result['confidence'] + 10)
                direction = "SELL"
            else:
                confidence = physics_result['confidence']
                direction = "SELL"
        else:
            direction = "HOLD"
            confidence = 50
        
        # تنظیم اهرم
        if confidence >= 85:
            leverage = 25
        elif confidence >= 75:
            leverage = 20
        elif confidence >= 65:
            leverage = 15
        elif confidence >= 55:
            leverage = 10
        else:
            leverage = 5
        
        return {
            'direction': direction,
            'entry': physics_result['entry'],
            'take_profit': physics_result['take_profit'],
            'stop_loss': physics_result['stop_loss'],
            'leverage': leverage,
            'confidence': confidence,
            'buy_force': physics_result['buy_force'],
            'sell_force': physics_result['sell_force'],
            'momentum': physics_result['momentum'],
            'price_position': physics_result['price_position'],
            'rsi': round(rsi_value, 1),
            'macd': round(macd_value, 4),
            'adx': round(adx_value, 1)
        }

signal_engine = AdvancedSignalEngine()

# ==================== متغیرهای سراسری ====================
user_data = {}
all_users = set()
referral_data = {}

# ==================== لیست اندیکاتورها ====================
INDICATORS = [
    "RSI", "MACD", "EMA5", "EMA10", "EMA30", "MA", "BOLL", "KDJ", 
    "ADX", "ATR", "VOL", "OBV", "Ichimoku_Cloud", "Stoch", "CCI",
    "Williams", "MFI", "PSAR", "BB_Upper", "BB_Lower"
]

# ==================== متون دوزبانه ====================
TEXTS = {
    'fa': {
        'welcome': '🔥 به ربات تحلیل تکنیکال فوق‌پیشرفته خوش آمدید!\n\n📊 با ۲۰ اندیکاتور و الگوریتم‌های فیزیک و ریاضی\n🎯 دقت سیگنال تا ۹۵٪\n\n🚀 برای شروع روی "📊 شروع تحلیل" کلیک کنید.',
        'enter_price': '💰 قیمت فعلی ارز را وارد کنید:',
        'enter_support': '📊 حمایت و مقاومت را وارد کنید:\n\nحمایت 65000\nمقاومت 66000',
        'select_indicators': '🔍 اندیکاتورها را انتخاب کنید (حداقل ۵ عدد)',
        'signal_result': '🔥 نتیجه تحلیل',
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
        'stats': '📊 آمار من'
    },
    'en': {
        'welcome': '🔥 Welcome to Ultra Advanced Technical Analysis Bot!\n\n📊 With 20 indicators and physics/math algorithms\n🎯 Signal accuracy up to 95%\n\n🚀 Click "📊 Start Analysis" to begin.',
        'enter_price': '💰 Enter current price:',
        'enter_support': '📊 Enter support and resistance:\n\nSupport 65000\nResistance 66000',
        'select_indicators': '🔍 Select indicators (minimum 5)',
        'signal_result': '🔥 Analysis Result',
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
        'stats': '📊 My Stats'
    }
}

# ==================== کیبوردها ====================
def get_main_keyboard(user_id):
    user = db.get_user(user_id)
    lang = user[3] if user else 'fa'
    t = TEXTS[lang]
    
    keyboard = [
        [KeyboardButton("📊 شروع تحلیل | Start Analysis")],
        [KeyboardButton(f"{t['stats']} | My Stats"), KeyboardButton(f"{t['exchange']} | Toobit")],
        [KeyboardButton(f"{t['referral']} | Invite"), KeyboardButton(f"{t['change_lang']} | Change")],
    ]
    
    if user_id == ADMIN_ID:
        keyboard.append([KeyboardButton(f"{t['admin_panel']} | Admin Panel")])
    
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
    
    keyboard.append([
        KeyboardButton("🔄 ثبت | Register"),
        KeyboardButton("📊 تحلیل | Analyze")
    ])
    
    user = db.get_user(user_id)
    lang = user[3] if user else 'fa'
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_admin_keyboard(user_id):
    keyboard = [
        [KeyboardButton("📢 ارسال پیام همگانی | Broadcast")],
        [KeyboardButton("📊 آمار کاربران | User Stats")],
        [KeyboardButton("🔗 اشتراکی کردن ربات | Share Bot")],
        [KeyboardButton("✏️ تغییر متن خوش‌آمدگویی | Edit Welcome")],
        [KeyboardButton("⏰ تغییر مدت اشتراک | Edit Subscription")],
        [KeyboardButton("💳 تغییر شماره کارت | Edit Card")],
        [KeyboardButton("💰 کیف پول | Wallet")],
        [KeyboardButton("🔙 بازگشت | Back")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

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
            db.cursor.execute('SELECT user_id FROM users WHERE referral_code = ?', (ref_code,))
            result = db.cursor.fetchone()
            if result:
                referred_by = result[0]
        except:
            pass
    
    db.add_user(user_id, username, first_name, 'fa', referred_by)
    
    if user_id not in user_data:
        user_data[user_id] = {
            'indicators': {},
            'support': None,
            'resistance': None,
            'current_price': None,
            'state': 'menu'
        }
    
    # حذف پیام استارت
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
            'state': 'menu'
        }
    
    try:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
    except:
        pass
    
    user = db.get_user(user_id)
    lang = user[3] if user else 'fa'
    t = TEXTS[lang]
    
    # ===== تغییر زبان =====
    if "🌐 تغییر زبان" in text or "Change Language" in text:
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
    
    # ===== صرافی توبیت =====
    if "💱 صرافی توبیت" in text or "Toobit Exchange" in text:
        await update.effective_chat.send_message(
            f"💱 **Toobit Exchange | صرافی توبیت**\n\n🔗 {EXCHANGE_URL}\n\n🎁 با لینک بالا ثبت نام کنید و از جوایز ویژه بهره‌مند شوید!",
            reply_markup=get_main_keyboard(user_id),
            parse_mode='Markdown'
        )
        return
    
    # ===== رفرال =====
    if "🎁 دعوت دوستان" in text or "Invite Friends" in text:
        referral_link = f"https://t.me/{BOT_USERNAME.replace('@', '')}?start=ref_{user_id}"
        referral_count = db.cursor.execute('SELECT referral_count FROM users WHERE user_id = ?', (user_id,)).fetchone()[0]
        
        await update.effective_chat.send_message(
            f"🎁 **سیستم دعوت دوستان**\n\n"
            f"🔗 لینک دعوت شما:\n`{referral_link}`\n\n"
            f"👥 تعداد دعوت‌ها: {referral_count}\n\n"
            f"📤 لینک را با دوستان خود به اشتراک بگذارید!",
            reply_markup=get_main_keyboard(user_id),
            parse_mode='Markdown'
        )
        return
    
    # ===== آمار من =====
    if "📊 آمار من" in text or "My Stats" in text:
        stats = db.get_user_stats(user_id)
        if stats:
            total, avg_conf, best_conf = stats
            await update.effective_chat.send_message(
                f"📊 **آمار شما**\n\n"
                f"📈 تعداد تحلیل‌ها: {total}\n"
                f"🎯 میانگین اطمینان: {avg_conf:.0f}%\n"
                f"🏆 بهترین اطمینان: {best_conf:.0f}%\n"
                f"👥 تعداد دعوت‌ها: {db.cursor.execute('SELECT referral_count FROM users WHERE user_id = ?', (user_id,)).fetchone()[0]}",
                reply_markup=get_main_keyboard(user_id),
                parse_mode='Markdown'
            )
        else:
            await update.effective_chat.send_message(
                "📊 هنوز تحلیلی انجام نداده‌اید!",
                reply_markup=get_main_keyboard(user_id)
            )
        return
    
    # ===== پنل ادمین =====
    if "👑 پنل ادمین" in text or "Admin Panel" in text:
        if user_id == ADMIN_ID:
            await update.effective_chat.send_message(
                "👑 **پنل ادمین**\n\n"
                "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
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
            await update.effective_chat.send_message(
                f"✅ پیام به {sent} کاربر ارسال شد!",
                reply_markup=get_admin_keyboard(user_id)
            )
            return
        
        if "📊 آمار کاربران" in text or "User Stats" in text:
            users = db.get_all_users()
            total = len(users)
            await update.effective_chat.send_message(
                f"📊 **آمار کاربران**\n\n"
                f"👥 کل کاربران: {total}\n"
                f"📈 کاربران فارسی: {sum(1 for u in users if u[1] == 'fa')}\n"
                f"📈 کاربران انگلیسی: {sum(1 for u in users if u[1] == 'en')}",
                reply_markup=get_admin_keyboard(user_id),
                parse_mode='Markdown'
            )
            return
        
        if "🔗 اشتراکی کردن ربات" in text or "Share Bot" in text:
            bot_link = f"https://t.me/{BOT_USERNAME.replace('@', '')}"
            await update.effective_chat.send_message(
                f"🔗 **لینک اشتراک‌گذاری ربات**\n\n"
                f"📤 لینک:\n`{bot_link}`\n\n"
                f"📋 متن پیشنهادی:\n"
                f"🔥 به ربات تحلیل تکنیکال فوق‌پیشرفته بپیوندید!\n"
                f"🎯 دقت سیگنال تا ۹۵٪\n"
                f"🔗 {bot_link}",
                reply_markup=get_admin_keyboard(user_id),
                parse_mode='Markdown'
            )
            return
        
        if "✏️ تغییر متن خوش‌آمدگویی" in text or "Edit Welcome" in text:
            user_data[user_id]['state'] = 'edit_welcome'
            await update.effective_chat.send_message(
                "✏️ متن جدید خوش‌آمدگویی را وارد کنید:",
                reply_markup=get_admin_keyboard(user_id)
            )
            return
        
        if user_data[user_id].get('state') == 'edit_welcome':
            db.update_setting('welcome_text_fa', text)
            db.update_setting('welcome_text_en', text + " (English version)")
            user_data[user_id]['state'] = 'menu'
            await update.effective_chat.send_message(
                "✅ متن خوش‌آمدگویی با موفقیت تغییر کرد!",
                reply_markup=get_admin_keyboard(user_id)
            )
            return
        
        if "⏰ تغییر مدت اشتراک" in text or "Edit Subscription" in text:
            user_data[user_id]['state'] = 'edit_subscription_days'
            await update.effective_chat.send_message(
                "⏰ تعداد روزهای اشتراک را وارد کنید:\n(مثال: 30)",
                reply_markup=get_admin_keyboard(user_id)
            )
            return
        
        if user_data[user_id].get('state') == 'edit_subscription_days':
            try:
                days = int(text)
                db.update_setting('subscription_days', str(days))
                user_data[user_id]['state'] = 'menu'
                await update.effective_chat.send_message(
                    f"✅ مدت اشتراک به {days} روز تغییر کرد!",
                    reply_markup=get_admin_keyboard(user_id)
                )
            except:
                await update.effective_chat.send_message("❌ لطفاً یک عدد معتبر وارد کنید!")
            return
        
        if "💳 تغییر شماره کارت" in text or "Edit Card" in text:
            user_data[user_id]['state'] = 'edit_card_number'
            await update.effective_chat.send_message(
                "💳 شماره کارت جدید را وارد کنید:\n(۱۶ رقم)",
                reply_markup=get_admin_keyboard(user_id)
            )
            return
        
        if user_data[user_id].get('state') == 'edit_card_number':
            if len(text.replace(' ', '')) == 16:
                db.update_setting('card_number', text)
                user_data[user_id]['state'] = 'menu'
                await update.effective_chat.send_message(
                    f"✅ شماره کارت تغییر کرد!\n💳 {text}",
                    reply_markup=get_admin_keyboard(user_id)
                )
            else:
                await update.effective_chat.send_message("❌ شماره کارت باید ۱۶ رقم باشد!")
            return
        
        if "💰 کیف پول" in text or "Wallet" in text:
            await update.effective_chat.send_message(
                f"💰 **کیف پول**\n\n"
                f"💳 شماره کارت: {db.get_setting('card_number')}\n"
                f"👤 صاحب کارت: {db.get_setting('card_holder')}\n"
                f"💰 قیمت اشتراک: {db.get_setting('subscription_price')} تومان\n"
                f"⏰ مدت اشتراک: {db.get_setting('subscription_days')} روز",
                reply_markup=get_admin_keyboard(user_id),
                parse_mode='Markdown'
            )
            return
        
        if "🔙 بازگشت" in text or "Back" in text:
            await update.effective_chat.send_message(
                "🔙 بازگشت به منوی اصلی",
                reply_markup=get_main_keyboard(user_id)
            )
            return
    
    # ===== منطق اصلی ربات =====
    if "📊 شروع تحلیل" in text or "Start Analysis" in text:
        user_data[user_id]['state'] = 'waiting_current_price'
        user_data[user_id]['indicators'] = {}
        user_data[user_id]['support'] = None
        user_data[user_id]['resistance'] = None
        user_data[user_id]['current_price'] = None
        
        real_price = price_microservice.get_price()
        price_text = f" (Current: ${real_price:.2f})" if real_price else ""
        
        await update.effective_chat.send_message(
            f"💰 **قیمت فعلی ارز را وارد کنید**{price_text}\n\n"
            f"مثال: 65432.50",
            parse_mode='Markdown'
        )
        return
    
    # ادامه منطق...
    elif user_data[user_id]['state'] == 'waiting_current_price':
        try:
            user_data[user_id]['current_price'] = float(text.replace(',', '.'))
            user_data[user_id]['state'] = 'waiting_support_resistance'
            await update.effective_chat.send_message(
                "📊 **حمایت و مقاومت را وارد کنید**\n\n"
                "**فرمت:**\n"
                "حمایت 65000\n"
                "مقاومت 66000\n\n"
                "💡 دقیقاً مانند نمونه بالا تایپ کنید."
            )
        except ValueError:
            await update.effective_chat.send_message("❌ لطفاً عدد معتبر وارد کنید!")
    
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
                if user_data[user_id]['support'] >= user_data[user_id]['resistance']:
                    await update.effective_chat.send_message("❌ حمایت باید کمتر از مقاومت باشد!")
                    return
                
                user_data[user_id]['state'] = 'selecting_indicators'
                await update.effective_chat.send_message(
                    f"✅ **داده‌ها ثبت شد!**\n\n"
                    f"💰 قیمت: {user_data[user_id]['current_price']}\n"
                    f"📊 حمایت: {user_data[user_id]['support']}\n"
                    f"📈 مقاومت: {user_data[user_id]['resistance']}\n\n"
                    f"🔍 **اندیکاتورها را انتخاب کنید (حداقل ۵ عدد)**\n"
                    f"💡 اندیکاتور بیشتر = دقت بالاتر",
                    reply_markup=get_indicators_keyboard(user_id)
                )
        except:
            await update.effective_chat.send_message("❌ فرمت اشتباه! لطفاً مجدداً وارد کنید.")
    
    elif user_data[user_id]['state'] == 'selecting_indicators':
        clean_text = text.replace("✅ ", "")
        
        if clean_text in INDICATORS:
            if clean_text not in user_data[user_id]['indicators']:
                user_data[user_id]['current_indicator'] = clean_text
                user_data[user_id]['state'] = 'waiting_indicator_value'
                await update.effective_chat.send_message(
                    f"📊 **مقدار {clean_text} را وارد کنید**\n\n"
                    f"مثال: 45.67",
                    parse_mode='Markdown'
                )
            else:
                await update.effective_chat.send_message(
                    f"⚠️ {clean_text} قبلاً ثبت شده است!",
                    reply_markup=get_indicators_keyboard(user_id)
                )
        
        elif "ثبت" in text or "Register" in text:
            if len(user_data[user_id]['indicators']) >= 5:
                # اجرای تحلیل
                status_msg = await update.effective_chat.send_message(
                    "🔄 **در حال تحلیل با الگوریتم‌های پیشرفته...**\n"
                    "🧮 میکروسرویس‌های فیزیک و ریاضی در حال پردازش...\n\n"
                    f"📊 {len(user_data[user_id]['indicators'])} اندیکاتور بارگذاری شد"
                )
                
                result = signal_engine.generate_signal(
                    user_data[user_id]['indicators'],
                    user_data[user_id]['support'],
                    user_data[user_id]['resistance'],
                    user_data[user_id]['current_price']
                )
                
                await status_msg.delete()
                
                if result['direction'] == "BUY":
                    direction_emoji = "📈"
                    direction_text = "خرید | BUY"
                elif result['direction'] == "SELL":
                    direction_emoji = "📉"
                    direction_text = "فروش | SELL"
                else:
                    direction_emoji = "⚪"
                    direction_text = "نگهداری | HOLD"
                
                signal_text = f"""
🔥 **نتیجه تحلیل | Analysis Result** 🔥

{direction_emoji} **جهت | Direction:** {direction_text}
💰 **قیمت ورود | Entry:** ${result['entry']:,.2f}
🎯 **حد سود | Take Profit:** ${result['take_profit']:,.2f}
🛡️ **حد ضرر | Stop Loss:** ${result['stop_loss']:,.2f}
⚡ **اهرم | Leverage:** {result['leverage']}x
🎯 **اطمینان | Confidence:** {result['confidence']}%

📊 **جزئیات | Details:**
• RSI: {result.get('rsi', 0)}
• MACD: {result.get('macd', 0)}
• ADX: {result.get('adx', 0)}
• نیروی خرید | Buy Force: {result.get('buy_force', 0):.2f}
• نیروی فروش | Sell Force: {result.get('sell_force', 0):.2f}
• موقعیت قیمت | Price Position: {result.get('price_position', 0)}%

⚠️ **مدیریت ریسک | Risk Management:**
• حداکثر ۲-۳٪ سرمایه را ریسک کنید
• همیشه از حد ضرر استفاده کنید
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
                    f"❌ حداقل ۵ اندیکاتور وارد کنید! ({len(user_data[user_id]['indicators'])}/5)",
                    reply_markup=get_indicators_keyboard(user_id)
                )
        
        elif "تحلیل" in text or "Analyze" in text:
            # همان منطق ثبت
            if len(user_data[user_id]['indicators']) >= 5:
                status_msg = await update.effective_chat.send_message(
                    "🔄 در حال تحلیل با الگوریتم‌های پیشرفته..."
                )
                
                result = signal_engine.generate_signal(
                    user_data[user_id]['indicators'],
                    user_data[user_id]['support'],
                    user_data[user_id]['resistance'],
                    user_data[user_id]['current_price']
                )
                
                await status_msg.delete()
                
                if result['direction'] == "BUY":
                    direction_emoji = "📈"
                    direction_text = "خرید | BUY"
                elif result['direction'] == "SELL":
                    direction_emoji = "📉"
                    direction_text = "فروش | SELL"
                else:
                    direction_emoji = "⚪"
                    direction_text = "نگهداری | HOLD"
                
                signal_text = f"""
🔥 **نتیجه تحلیل | Analysis Result** 🔥

{direction_emoji} **جهت | Direction:** {direction_text}
💰 **قیمت ورود | Entry:** ${result['entry']:,.2f}
🎯 **حد سود | Take Profit:** ${result['take_profit']:,.2f}
🛡️ **حد ضرر | Stop Loss:** ${result['stop_loss']:,.2f}
⚡ **اهرم | Leverage:** {result['leverage']}x
🎯 **اطمینان | Confidence:** {result['confidence']}%

📊 **جزئیات | Details:**
• RSI: {result.get('rsi', 0)}
• MACD: {result.get('macd', 0)}
• ADX: {result.get('adx', 0)}
• نیروی خرید | Buy Force: {result.get('buy_force', 0):.2f}
• نیروی فروش | Sell Force: {result.get('sell_force', 0):.2f}
• موقعیت قیمت | Price Position: {result.get('price_position', 0)}%

⚠️ **مدیریت ریسک | Risk Management:**
• حداکثر ۲-۳٪ سرمایه را ریسک کنید
• همیشه از حد ضرر استفاده کنید
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
                f"✅ {indicator_name} = {indicator_value} ثبت شد!\n\n"
                f"📊 اندیکاتورهای ثبت شده: {len(user_data[user_id]['indicators'])}/20\n\n"
                f"🔍 اندیکاتور بعدی را انتخاب کنید یا روی «ثبت» کلیک کنید",
                reply_markup=get_indicators_keyboard(user_id)
            )
        except ValueError:
            await update.effective_chat.send_message("❌ لطفاً عدد معتبر وارد کنید! (مثال: 45.67)")

# ==================== اجرا ====================
def main():
    print("=" * 70)
    print("🚀 ربات تحلیل تکنیکال فوق‌پیشرفته نسخه ۶.۰")
    print("🔥 با الگوریتم‌های فیزیک و ریاضی")
    print("=" * 70)
    print(f"👤 ادمین: {ADMIN_ID}")
    print(f"🤖 ربات: {BOT_USERNAME}")
    print(f"📊 اندیکاتورها: {len(INDICATORS)}")
    print(f"💱 صرافی: Toobit")
    print("=" * 70)
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ ربات با موفقیت راه‌اندازی شد!")
    print("=" * 70)
    
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()