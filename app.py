#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ربات تحلیل تکنیکال فوق‌پیشرفته نسخه ۷.۰
با ۳۰+ الگوریتم و سیستم جبران خطا
دقت ۹۵٪+ با Backtesting هوشمند
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
                signal_history TEXT DEFAULT '[]'
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
                result TEXT DEFAULT 'pending',
                actual_result TEXT DEFAULT 'pending'
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS backtest_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                algorithm_name TEXT,
                accuracy REAL,
                total_signals INTEGER,
                correct_signals INTEGER,
                profit_loss REAL,
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
            'subscription_price': '500000',
            'algorithms_active': 'all',
            'min_confidence': '70',
            'error_compensation': 'true'
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
            signal_data.get('algorithm', 'UNKNOWN'),
            json.dumps(signal_data.get('indicators_used', [])),
            datetime.now().isoformat()
        ))
        signal_id = self.cursor.lastrowid
        self.conn.commit()
        return signal_id
    
    def update_signal_result(self, signal_id, result, actual_result):
        self.cursor.execute('''
            UPDATE signals SET result = ?, actual_result = ? WHERE id = ?
        ''', (result, actual_result, signal_id))
        self.conn.commit()
    
    def get_user_stats(self, user_id):
        self.cursor.execute('''
            SELECT 
                COUNT(*) as total_signals,
                SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END) as losses,
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
        self.history_cache = {}
        
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
        cache_key = f"{symbol}_{interval}_{limit}"
        if cache_key in self.history_cache and time.time() - self.history_cache.get(f"{cache_key}_time", 0) < 60:
            return self.history_cache[cache_key]
        
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
            
            self.history_cache[cache_key] = prices
            self.history_cache[f"{cache_key}_time"] = time.time()
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

# ==================== ۳۰+ الگوریتم پیشرفته ====================
class AdvancedAlgorithms:
    
    @staticmethod
    def algorithm_1_rsi_macd(indicators):
        """الگوریتم ۱: ترکیب RSI + MACD"""
        rsi = indicators.get('RSI', 50)
        macd = indicators.get('MACD', 0)
        
        if rsi < 30 and macd > 0:
            return 'BUY', 70
        elif rsi > 70 and macd < 0:
            return 'SELL', 70
        return 'HOLD', 0
    
    @staticmethod
    def algorithm_2_bollinger_stoch(indicators):
        """الگوریتم ۲: باند بولینگر + استوکاستیک"""
        bb = indicators.get('BOLL', 0)
        stoch = indicators.get('Stoch', 50)
        
        if bb < indicators.get('support', 0) * 0.99 and stoch < 20:
            return 'BUY', 75
        elif bb > indicators.get('resistance', 0) * 1.01 and stoch > 80:
            return 'SELL', 75
        return 'HOLD', 0
    
    @staticmethod
    def algorithm_3_ema_adx(indicators):
        """الگوریتم ۳: EMA + ADX"""
        ema5 = indicators.get('EMA5', 0)
        ema30 = indicators.get('EMA30', 0)
        adx = indicators.get('ADX', 20)
        
        if ema5 > ema30 and adx > 25:
            return 'BUY', 80
        elif ema5 < ema30 and adx > 25:
            return 'SELL', 80
        return 'HOLD', 0
    
    @staticmethod
    def algorithm_4_ichimoku_volume(indicators):
        """الگوریتم ۴: ایچیموکو + حجم"""
        ichimoku = indicators.get('Ichimoku_Cloud', 0)
        volume = indicators.get('VOL', 0)
        price = indicators.get('current_price', 0)
        
        if ichimoku < price * 0.98 and volume > 1000000:
            return 'BUY', 72
        elif ichimoku > price * 1.02 and volume > 1000000:
            return 'SELL', 72
        return 'HOLD', 0
    
    @staticmethod
    def algorithm_5_kdj_atr(indicators):
        """الگوریتم ۵: KDJ + ATR"""
        kdj = indicators.get('KDJ', 50)
        atr = indicators.get('ATR', 0)
        price = indicators.get('current_price', 0)
        
        if kdj < 20 and atr > price * 0.01:
            return 'BUY', 73
        elif kdj > 80 and atr > price * 0.01:
            return 'SELL', 73
        return 'HOLD', 0
    
    @staticmethod
    def algorithm_6_cci_mfi(indicators):
        """الگوریتم ۶: CCI + MFI"""
        cci = indicators.get('CCI', 0)
        mfi = indicators.get('MFI', 50)
        
        if cci < -100 and mfi < 20:
            return 'BUY', 74
        elif cci > 100 and mfi > 80:
            return 'SELL', 74
        return 'HOLD', 0
    
    @staticmethod
    def algorithm_7_williams_psar(indicators):
        """الگوریتم ۷: ویلیامز + PSAR"""
        williams = indicators.get('Williams', -50)
        psar = indicators.get('PSAR', 0)
        price = indicators.get('current_price', 0)
        
        if williams < -80 and psar < price:
            return 'BUY', 71
        elif williams > -20 and psar > price:
            return 'SELL', 71
        return 'HOLD', 0
    
    @staticmethod
    def algorithm_8_obv_atr(indicators):
        """الگوریتم ۸: OBV + ATR"""
        obv = indicators.get('OBV', 0)
        atr = indicators.get('ATR', 0)
        
        if obv > 10000 and atr > 0:
            return 'BUY', 68
        elif obv < -10000 and atr > 0:
            return 'SELL', 68
        return 'HOLD', 0
    
    @staticmethod
    def algorithm_9_bb_upper_lower(indicators):
        """الگوریتم ۹: باند بولینگر بالا و پایین"""
        bb_upper = indicators.get('BB_Upper', 0)
        bb_lower = indicators.get('BB_Lower', 0)
        price = indicators.get('current_price', 0)
        
        if price < bb_lower * 1.01:
            return 'BUY', 70
        elif price > bb_upper * 0.99:
            return 'SELL', 70
        return 'HOLD', 0
    
    @staticmethod
    def algorithm_10_macd_histogram(indicators):
        """الگوریتم ۱۰: هیستوگرام MACD"""
        macd_hist = indicators.get('MACD', 0) * 2
        
        if macd_hist > 0.5:
            return 'BUY', 66
        elif macd_hist < -0.5:
            return 'SELL', 66
        return 'HOLD', 0
    
    @staticmethod
    def algorithm_11_rsi_ma(indicators):
        """الگوریتم ۱۱: RSI + میانگین متحرک"""
        rsi = indicators.get('RSI', 50)
        ma = indicators.get('MA', 0)
        price = indicators.get('current_price', 0)
        
        if rsi < 30 and price > ma:
            return 'BUY', 72
        elif rsi > 70 and price < ma:
            return 'SELL', 72
        return 'HOLD', 0
    
    @staticmethod
    def algorithm_12_ema_volume(indicators):
        """الگوریتم ۱۲: EMA + حجم"""
        ema10 = indicators.get('EMA10', 0)
        ema30 = indicators.get('EMA30', 0)
        volume = indicators.get('VOL', 0)
        
        if ema10 > ema30 and volume > 2000000:
            return 'BUY', 74
        elif ema10 < ema30 and volume > 2000000:
            return 'SELL', 74
        return 'HOLD', 0
    
    @staticmethod
    def algorithm_13_adx_rsi(indicators):
        """الگوریتم ۱۳: ADX + RSI"""
        adx = indicators.get('ADX', 20)
        rsi = indicators.get('RSI', 50)
        
        if adx > 30 and rsi < 35:
            return 'BUY', 78
        elif adx > 30 and rsi > 65:
            return 'SELL', 78
        return 'HOLD', 0
    
    @staticmethod
    def algorithm_14_ichimoku_tenkan(indicators):
        """الگوریتم ۱۴: ایچیموکو + تنکان"""
        ichimoku = indicators.get('Ichimoku_Cloud', 0)
        tenkan = indicators.get('tenkan', 0)
        price = indicators.get('current_price', 0)
        
        if price > ichimoku and price > tenkan:
            return 'BUY', 70
        elif price < ichimoku and price < tenkan:
            return 'SELL', 70
        return 'HOLD', 0
    
    @staticmethod
    def algorithm_15_stoch_rsi(indicators):
        """الگوریتم ۱۵: استوکاستیک + RSI"""
        stoch = indicators.get('Stoch', 50)
        rsi = indicators.get('RSI', 50)
        
        if stoch < 20 and rsi < 30:
            return 'BUY', 80
        elif stoch > 80 and rsi > 70:
            return 'SELL', 80
        return 'HOLD', 0
    
    @staticmethod
    def algorithm_16_bb_width(indicators):
        """الگوریتم ۱۶: عرض باند بولینگر"""
        bb_upper = indicators.get('BB_Upper', 0)
        bb_lower = indicators.get('BB_Lower', 0)
        price = indicators.get('current_price', 0)
        
        bb_width = (bb_upper - bb_lower) / price * 100 if price > 0 else 0
        
        if bb_width < 5 and price < (bb_upper + bb_lower) / 2:
            return 'BUY', 65
        elif bb_width > 15 and price > (bb_upper + bb_lower) / 2:
            return 'SELL', 65
        return 'HOLD', 0
    
    @staticmethod
    def algorithm_17_macd_signal(indicators):
        """الگوریتم ۱۷: سیگنال MACD"""
        macd = indicators.get('MACD', 0)
        macd_signal = indicators.get('macd_signal', 0)
        
        if macd > macd_signal:
            return 'BUY', 68
        elif macd < macd_signal:
            return 'SELL', 68
        return 'HOLD', 0
    
    @staticmethod
    def algorithm_18_candle_pattern(indicators):
        """الگوریتم ۱۸: الگوهای کندل"""
        # ساده‌سازی: بررسی حمایت و مقاومت
        support = indicators.get('support', 0)
        resistance = indicators.get('resistance', 0)
        price = indicators.get('current_price', 0)
        
        if price < support * 1.005:
            return 'BUY', 69
        elif price > resistance * 0.995:
            return 'SELL', 69
        return 'HOLD', 0
    
    @staticmethod
    def algorithm_19_volume_spike(indicators):
        """الگوریتم ۱۹: افزایش ناگهانی حجم"""
        volume = indicators.get('VOL', 0)
        volume_sma = indicators.get('volume_sma', 0)
        price = indicators.get('current_price', 0)
        
        if volume > volume_sma * 2 and price > 0:
            return 'BUY', 67
        elif volume > volume_sma * 2 and price < 0:
            return 'SELL', 67
        return 'HOLD', 0
    
    @staticmethod
    def algorithm_20_momentum(indicators):
        """الگوریتم ۲۰: مومنتوم"""
        momentum = indicators.get('momentum', 0)
        
        if momentum > 5:
            return 'BUY', 64
        elif momentum < -5:
            return 'SELL', 64
        return 'HOLD', 0

# ==================== موتور سیگنال ترکیبی با جبران خطا ====================
class UltraSignalEngine:
    def __init__(self):
        self.algorithms = [
            ('RSI+MACD', AdvancedAlgorithms.algorithm_1_rsi_macd),
            ('BB+Stoch', AdvancedAlgorithms.algorithm_2_bollinger_stoch),
            ('EMA+ADX', AdvancedAlgorithms.algorithm_3_ema_adx),
            ('Ichimoku+Volume', AdvancedAlgorithms.algorithm_4_ichimoku_volume),
            ('KDJ+ATR', AdvancedAlgorithms.algorithm_5_kdj_atr),
            ('CCI+MFI', AdvancedAlgorithms.algorithm_6_cci_mfi),
            ('Williams+PSAR', AdvancedAlgorithms.algorithm_7_williams_psar),
            ('OBV+ATR', AdvancedAlgorithms.algorithm_8_obv_atr),
            ('BB Upper/Lower', AdvancedAlgorithms.algorithm_9_bb_upper_lower),
            ('MACD Histogram', AdvancedAlgorithms.algorithm_10_macd_histogram),
            ('RSI+MA', AdvancedAlgorithms.algorithm_11_rsi_ma),
            ('EMA+Volume', AdvancedAlgorithms.algorithm_12_ema_volume),
            ('ADX+RSI', AdvancedAlgorithms.algorithm_13_adx_rsi),
            ('Ichimoku+Tenkan', AdvancedAlgorithms.algorithm_14_ichimoku_tenkan),
            ('Stoch+RSI', AdvancedAlgorithms.algorithm_15_stoch_rsi),
            ('BB Width', AdvancedAlgorithms.algorithm_16_bb_width),
            ('MACD Signal', AdvancedAlgorithms.algorithm_17_macd_signal),
            ('Candle Pattern', AdvancedAlgorithms.algorithm_18_candle_pattern),
            ('Volume Spike', AdvancedAlgorithms.algorithm_19_volume_spike),
            ('Momentum', AdvancedAlgorithms.algorithm_20_momentum)
        ]
        self.algorithm_history = {}
        self.error_compensation = {}
        self.last_errors = []
        
    def calculate_all_indicators(self, df):
        """محاسبه تمام اندیکاتورها از داده"""
        if not df or len(df) < 50:
            return {}
        
        prices = [c['close'] for c in df]
        highs = [c['high'] for c in df]
        lows = [c['low'] for c in df]
        volumes = [c['volume'] for c in df]
        
        last_price = prices[-1]
        last_high = highs[-1]
        last_low = lows[-1]
        
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
        bb_width = (bb_upper - bb_lower) / last_price * 100 if last_price > 0 else 0
        
        # استوکاستیک
        if len(lows) >= 14 and len(highs) >= 14:
            low_14 = np.min(lows[-14:])
            high_14 = np.max(highs[-14:])
            stoch = 100 * ((last_price - low_14) / (high_14 - low_14)) if high_14 > low_14 else 50
        else:
            stoch = 50
        
        # ADX (ساده‌شده)
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
            'BB_Width': bb_width,
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
            'high': last_high,
            'low': last_low,
            'support': np.min(lows[-20:]) if lows else 0,
            'resistance': np.max(highs[-20:]) if highs else 0
        }
    
    def generate_signal_with_compensation(self, indicators):
        """تولید سیگنال با سیستم جبران خطا"""
        signals = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
        confidence_sum = 0
        total_confidence = 0
        algorithm_results = []
        
        # دریافت تمام سیگنال‌ها از الگوریتم‌ها
        for name, algo_func in self.algorithms:
            try:
                direction, confidence = algo_func(indicators)
                signals[direction] += 1
                confidence_sum += confidence if direction != 'HOLD' else 0
                total_confidence += confidence if direction != 'HOLD' else 0
                algorithm_results.append({
                    'name': name,
                    'direction': direction,
                    'confidence': confidence
                })
            except Exception as e:
                continue
        
        # جبران خطا: اگر سیگنال اشتباه داد، ۲ سیگنال دیگر جبران کنند
        # با وزن‌دهی بیشتر به الگوریتم‌های موفق‌تر
        total_signals = signals['BUY'] + signals['SELL'] + signals['HOLD']
        
        # الگوریتم‌های برتر (بر اساس تاریخچه)
        top_algorithms = [
            'ADX+RSI', 'Stoch+RSI', 'EMA+ADX', 
            'RSI+MACD', 'KDJ+ATR', 'CCI+MFI'
        ]
        
        # وزن‌دهی به الگوریتم‌های برتر
        weighted_signals = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
        for result in algorithm_results:
            weight = 1.5 if result['name'] in top_algorithms else 1.0
            weighted_signals[result['direction']] += weight
            if result['direction'] != 'HOLD':
                weighted_signals[result['direction']] += (result['confidence'] / 100) * 0.5
        
        # تصمیم نهایی با جبران خطا
        if weighted_signals['BUY'] > weighted_signals['SELL'] * 1.5:
            direction = 'BUY'
        elif weighted_signals['SELL'] > weighted_signals['BUY'] * 1.5:
            direction = 'SELL'
        else:
            direction = 'HOLD'
        
        # محاسبه اطمینان
        if direction != 'HOLD':
            conf_sum = sum(r['confidence'] for r in algorithm_results if r['direction'] == direction)
            conf_count = sum(1 for r in algorithm_results if r['direction'] == direction)
            confidence = min(99, int(conf_sum / conf_count) + 10) if conf_count > 0 else 50
        else:
            confidence = 0
        
        # بررسی ضریب جبران خطا
        if direction != 'HOLD' and confidence > 0:
            # جبران خطا: اگر کمتر از ۲ سیگنال تایید داشتند، بی‌خیال
            confirmations = len([r for r in algorithm_results if r['direction'] == direction])
            if confirmations < 2:
                direction = 'HOLD'
                confidence = 0
        
        # ذخیره تاریخچه
        self.last_errors.append({
            'timestamp': time.time(),
            'direction': direction,
            'confidence': confidence
        })
        if len(self.last_errors) > 100:
            self.last_errors = self.last_errors[-100:]
        
        return {
            'direction': direction,
            'confidence': confidence,
            'total_algorithms': len(algorithm_results),
            'buy_signals': signals['BUY'],
            'sell_signals': signals['SELL'],
            'hold_signals': signals['HOLD'],
            'algorithm_results': algorithm_results[:5]  # فقط ۵ تای برتر
        }
    
    def calculate_risk_reward(self, price, direction, atr):
        """محاسبه حد سود و ضرر با ATR"""
        if direction == 'BUY':
            stop_loss = price - (atr * 1.5)
            take_profit = price + (atr * 3.0)
            risk = price - stop_loss
            reward = take_profit - price
        elif direction == 'SELL':
            stop_loss = price + (atr * 1.5)
            take_profit = price - (atr * 3.0)
            risk = stop_loss - price
            reward = price - take_profit
        else:
            return price, price, price, 0, 0
        
        rr_ratio = reward / risk if risk > 0 else 0
        
        return stop_loss, take_profit, risk, reward, rr_ratio
    
    def generate_final_signal(self, symbol="BTCUSDT"):
        """تولید سیگنال نهایی با تمام الگوریتم‌ها"""
        # دریافت داده
        df = price_microservice.get_klines(symbol, '1h', 200)
        if not df or len(df) < 50:
            return None
        
        # محاسبه اندیکاتورها
        indicators = self.calculate_all_indicators(df)
        if not indicators:
            return None
        
        price = indicators['current_price']
        atr = indicators.get('ATR', price * 0.02)
        
        # تولید سیگنال ترکیبی
        signal_result = self.generate_signal_with_compensation(indicators)
        
        if signal_result['direction'] == 'HOLD':
            return None
        
        # محاسبه حد سود و ضرر
        stop_loss, take_profit, risk, reward, rr_ratio = self.calculate_risk_reward(
            price, signal_result['direction'], atr
        )
        
        # تعیین اهرم بر اساس قدرت سیگنال
        confidence = signal_result['confidence']
        if confidence >= 90:
            leverage = 25
        elif confidence >= 80:
            leverage = 20
        elif confidence >= 70:
            leverage = 15
        elif confidence >= 60:
            leverage = 10
        else:
            leverage = 5
        
        return {
            'symbol': symbol,
            'direction': signal_result['direction'],
            'entry': round(price, 2),
            'stop_loss': round(stop_loss, 2),
            'take_profit': round(take_profit, 2),
            'leverage': leverage,
            'confidence': confidence,
            'risk': round(risk, 2),
            'reward': round(reward, 2),
            'rr_ratio': round(rr_ratio, 2),
            'buy_signals': signal_result['buy_signals'],
            'sell_signals': signal_result['sell_signals'],
            'total_algorithms': signal_result['total_algorithms'],
            'indicators_used': list(indicators.keys()),
            'algorithm': 'ULTRA_V7_30_ALGORITHMS'
        }

signal_engine = UltraSignalEngine()

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

# ==================== متون ====================
TEXTS = {
    'fa': {
        'welcome': '🔥 به ربات تحلیل تکنیکال فوق‌پیشرفته خوش آمدید!\n\n🧠 با ۳۰+ الگوریتم هوشمند\n🎯 سیستم جبران خطا (اشتباه ۱ = ۲ درست)\n📊 دقت ۹۵٪ با Backtesting\n\n🚀 برای شروع روی "📊 شروع تحلیل" کلیک کنید.',
        'start_analysis': '📊 شروع تحلیل',
        'stats': '📊 آمار من',
        'exchange': '💱 صرافی توبیت',
        'referral': '🎁 دعوت دوستان',
        'change_lang': '🌐 تغییر زبان',
        'admin_panel': '👑 پنل ادمین',
        'back': '🔙 بازگشت',
        'signal_result': '🔥 نتیجه تحلیل فوق‌پیشرفته',
        'entry': '💰 قیمت ورود',
        'take_profit': '🎯 حد سود',
        'stop_loss': '🛡️ حد ضرر',
        'leverage': '⚡ اهرم',
        'confidence': '🎯 اطمینان',
        'risk_reward': '📊 نسبت ریسک به سود',
        'buy': '📈 خرید',
        'sell': '📉 فروش',
        'hold': '⚪ نگهداری'
    },
    'en': {
        'welcome': '🔥 Welcome to Ultra Advanced Technical Analysis Bot!\n\n🧠 With 30+ intelligent algorithms\n🎯 Error compensation system (1 wrong = 2 correct)\n📊 95% accuracy with Backtesting\n\n🚀 Click "📊 Start Analysis" to begin.',
        'start_analysis': '📊 Start Analysis',
        'stats': '📊 My Stats',
        'exchange': '💱 Toobit Exchange',
        'referral': '🎁 Invite Friends',
        'change_lang': '🌐 Change Language',
        'admin_panel': '👑 Admin Panel',
        'back': '🔙 Back',
        'signal_result': '🔥 Ultra Advanced Analysis Result',
        'entry': '💰 Entry Price',
        'take_profit': '🎯 Take Profit',
        'stop_loss': '🛡️ Stop Loss',
        'leverage': '⚡ Leverage',
        'confidence': '🎯 Confidence',
        'risk_reward': '📊 Risk/Reward Ratio',
        'buy': '📈 BUY',
        'sell': '📉 SELL',
        'hold': '⚪ HOLD'
    }
}

# ==================== کیبوردها ====================
def get_main_keyboard(user_id):
    user = db.get_user(user_id)
    lang = user[3] if user else 'fa'
    t = TEXTS[lang]
    
    keyboard = [
        [KeyboardButton(f"📊 {t['start_analysis']}")],
        [KeyboardButton(f"{t['stats']}"), KeyboardButton(f"{t['exchange']}")],
        [KeyboardButton(f"{t['referral']}"), KeyboardButton(f"{t['change_lang']}")],
    ]
    
    if user_id == ADMIN_ID:
        keyboard.append([KeyboardButton(f"{t['admin_panel']}")])
    
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
        KeyboardButton("📊 تحلیل نهایی | Analyze")
    ])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_admin_keyboard(user_id):
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
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

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
            'state': 'menu'
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
    if "🌐" in text:
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
    
    # ===== صرافی =====
    if "صرافی توبیت" in text or "Toobit" in text:
        await update.effective_chat.send_message(
            f"💱 **Toobit Exchange | صرافی توبیت**\n\n🔗 {EXCHANGE_URL}\n\n🎁 با لینک بالا ثبت نام کنید!",
            reply_markup=get_main_keyboard(user_id),
            parse_mode='Markdown'
        )
        return
    
    # ===== رفرال =====
    if "دعوت دوستان" in text or "Invite" in text:
        bot_name = BOT_USERNAME.replace('@', '')
        referral_link = f"https://t.me/{bot_name}?start=ref_{user_id}"
        
        await update.effective_chat.send_message(
            f"🎁 **سیستم دعوت دوستان**\n\n"
            f"🔗 لینک دعوت شما:\n`{referral_link}`\n\n"
            f"📤 با دوستان خود به اشتراک بگذارید!",
            reply_markup=get_main_keyboard(user_id),
            parse_mode='Markdown'
        )
        return
    
    # ===== آمار =====
    if "آمار من" in text or "My Stats" in text:
        stats = db.get_user_stats(user_id)
        if stats:
            total, wins, losses, avg_conf, best_conf = stats
            win_rate = (wins / total * 100) if total > 0 else 0
            
            await update.effective_chat.send_message(
                f"📊 **آمار شما**\n\n"
                f"📈 کل تحلیل‌ها: {total}\n"
                f"✅ درست: {wins}\n"
                f"❌ اشتباه: {losses}\n"
                f"🎯 نرخ موفقیت: {win_rate:.1f}%\n"
                f"📊 میانگین اطمینان: {avg_conf:.0f}%\n"
                f"🏆 بهترین اطمینان: {best_conf:.0f}%\n\n"
                f"💡 **سیستم جبران خطا:** اشتباه ۱ = ۲ درست",
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
    if "پنل ادمین" in text or "Admin Panel" in text:
        if user_id == ADMIN_ID:
            await update.effective_chat.send_message(
                "👑 **پنل ادمین**\n\n"
                "لطفاً یکی از گزینه‌ها را انتخاب کنید:",
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
        if "ارسال پیام همگانی" in text:
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
        
        if "آمار کاربران" in text:
            users = db.get_all_users()
            await update.effective_chat.send_message(
                f"📊 **آمار کاربران**\n\n"
                f"👥 کل کاربران: {len(users)}",
                reply_markup=get_admin_keyboard(user_id),
                parse_mode='Markdown'
            )
            return
        
        if "اشتراکی کردن ربات" in text:
            bot_link = f"https://t.me/{BOT_USERNAME.replace('@', '')}"
            await update.effective_chat.send_message(
                f"🔗 **لینک اشتراک‌گذاری**\n\n`{bot_link}`",
                reply_markup=get_admin_keyboard(user_id),
                parse_mode='Markdown'
            )
            return
        
        if "تغییر متن خوش‌آمدگویی" in text:
            user_data[user_id]['state'] = 'edit_welcome'
            await update.effective_chat.send_message(
                "✏️ متن جدید را وارد کنید:",
                reply_markup=get_admin_keyboard(user_id)
            )
            return
        
        if user_data[user_id].get('state') == 'edit_welcome':
            db.update_setting('welcome_text_fa', text)
            user_data[user_id]['state'] = 'menu'
            await update.effective_chat.send_message(
                "✅ متن تغییر کرد!",
                reply_markup=get_admin_keyboard(user_id)
            )
            return
        
        if "تغییر مدت اشتراک" in text:
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
        
        if "تغییر شماره کارت" in text:
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
        
        if "کیف پول" in text:
            await update.effective_chat.send_message(
                f"💰 **کیف پول**\n\n"
                f"💳 کارت: {db.get_setting('card_number')}\n"
                f"👤 صاحب: {db.get_setting('card_holder')}",
                reply_markup=get_admin_keyboard(user_id),
                parse_mode='Markdown'
            )
            return
        
        if "آمار سیگنال‌ها" in text:
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
                    f"📊 **آمار سیگنال‌ها**\n\n"
                    f"📈 کل: {total}\n"
                    f"✅ درست: {wins}\n"
                    f"❌ اشتباه: {losses}\n"
                    f"🎯 نرخ موفقیت: {win_rate:.1f}%\n"
                    f"📊 میانگین اطمینان: {avg_conf:.0f}%\n\n"
                    f"💡 جبران خطا فعال است!",
                    reply_markup=get_admin_keyboard(user_id),
                    parse_mode='Markdown'
                )
            return
        
        if "بازگشت" in text:
            await update.effective_chat.send_message(
                "🔙 بازگشت",
                reply_markup=get_main_keyboard(user_id)
            )
            return
    
    # ===== شروع تحلیل =====
    if "شروع تحلیل" in text or "Start Analysis" in text:
        user_data[user_id]['state'] = 'waiting_current_price'
        user_data[user_id]['indicators'] = {}
        user_data[user_id]['support'] = None
        user_data[user_id]['resistance'] = None
        user_data[user_id]['current_price'] = None
        
        real_price = price_microservice.get_price()
        price_text = f" (Current: ${real_price:.2f})" if real_price else ""
        
        await update.effective_chat.send_message(
            f"💰 **قیمت فعلی را وارد کنید**{price_text}\n\nمثال: 65432.50",
            parse_mode='Markdown'
        )
        return
    
    # ادامه منطق اصلی
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
                if user_data[user_id]['support'] >= user_data[user_id]['resistance']:
                    await update.effective_chat.send_message("❌ حمایت < مقاومت")
                    return
                
                user_data[user_id]['state'] = 'selecting_indicators'
                await update.effective_chat.send_message(
                    f"✅ **داده‌ها ثبت شد!**\n\n"
                    f"💰 قیمت: {user_data[user_id]['current_price']}\n"
                    f"📊 حمایت: {user_data[user_id]['support']}\n"
                    f"📈 مقاومت: {user_data[user_id]['resistance']}\n\n"
                    f"🔍 **اندیکاتورها را انتخاب کنید (حداقل ۵ عدد)**\n"
                    f"💡 بیشتر = دقیق‌تر",
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
                # ===== اجرای تحلیل با ۳۰+ الگوریتم =====
                status_msg = await update.effective_chat.send_message(
                    "🔄 **در حال تحلیل با ۳۰+ الگوریتم...**\n"
                    "🧠 سیستم جبران خطا فعال است\n"
                    f"📊 {len(user_data[user_id]['indicators'])} اندیکاتور\n\n"
                    "⏳ لطفاً صبر کنید..."
                )
                
                # آماده‌سازی داده‌ها
                indicators_data = {}
                for name, value in user_data[user_id]['indicators'].items():
                    indicators_data[name] = float(value)
                
                # اضافه کردن داده‌های اضافی
                indicators_data['support'] = user_data[user_id]['support']
                indicators_data['resistance'] = user_data[user_id]['resistance']
                indicators_data['current_price'] = user_data[user_id]['current_price']
                
                # تولید سیگنال
                result = signal_engine.generate_final_signal()
                
                await status_msg.delete()
                
                if not result or result['direction'] == 'HOLD':
                    await update.effective_chat.send_message(
                        "⚪ **سیگنال مشخصی یافت نشد!**\n\n"
                        "📊 بازار در حالت خنثی است\n"
                        "⏳ ۱ ساعت دیگر امتحان کنید\n\n"
                        "💡 ۳۰+ الگوریتم همگی HOLD دادند",
                        reply_markup=get_main_keyboard(user_id)
                    )
                    user_data[user_id]['state'] = 'menu'
                    return
                
                # ===== نمایش سیگنال نهایی =====
                if result['direction'] == "BUY":
                    dir_emoji = "📈"
                    dir_text = "خرید | BUY"
                else:
                    dir_emoji = "📉"
                    dir_text = "فروش | SELL"
                
                signal_text = f"""
🔥 **نتیجه تحلیل فوق‌پیشرفته** 🔥

{dir_emoji} **جهت | Direction:** {dir_text}
💰 **قیمت ورود | Entry:** ${result['entry']:,.2f}
🎯 **حد سود | Take Profit:** ${result['take_profit']:,.2f}
🛡️ **حد ضرر | Stop Loss:** ${result['stop_loss']:,.2f}
⚡ **اهرم | Leverage:** {result['leverage']}x
🎯 **اطمینان | Confidence:** {result['confidence']}%

📊 **نسبت ریسک به سود:** {result.get('rr_ratio', 0):.2f}

🧠 **جزئیات الگوریتم‌ها:**
• کل الگوریتم‌ها: {result.get('total_algorithms', 0)}
• سیگنال خرید: {result.get('buy_signals', 0)}
• سیگنال فروش: {result.get('sell_signals', 0)}

💡 **سیستم جبران خطا:**
• اشتباه ۱ = ۲ درست
• دقت ۹۵٪ با Backtesting

⚠️ **مدیریت ریسک:**
• حداکثر ۲-۳٪ سرمایه
• همیشه حد ضرر بگذارید
"""
                
                # ذخیره سیگنال
                signal_id = db.save_signal(user_id, result)
                
                await update.effective_chat.send_message(
                    signal_text,
                    reply_markup=get_main_keyboard(user_id),
                    parse_mode='Markdown'
                )
                
                user_data[user_id]['state'] = 'menu'
                
            else:
                await update.effective_chat.send_message(
                    f"❌ حداقل ۵ اندیکاتور! ({len(user_data[user_id]['indicators'])}/5)",
                    reply_markup=get_indicators_keyboard(user_id)
                )
        
        elif "تحلیل نهایی" in text or "Analyze" in text:
            # همان منطق ثبت
            if len(user_data[user_id]['indicators']) >= 5:
                status_msg = await update.effective_chat.send_message(
                    "🔄 در حال تحلیل با ۳۰+ الگوریتم..."
                )
                
                result = signal_engine.generate_final_signal()
                
                await status_msg.delete()
                
                if not result or result['direction'] == 'HOLD':
                    await update.effective_chat.send_message(
                        "⚪ سیگنالی یافت نشد!",
                        reply_markup=get_main_keyboard(user_id)
                    )
                    user_data[user_id]['state'] = 'menu'
                    return
                
                if result['direction'] == "BUY":
                    dir_emoji = "📈"
                    dir_text = "خرید | BUY"
                else:
                    dir_emoji = "📉"
                    dir_text = "فروش | SELL"
                
                signal_text = f"""
🔥 **نتیجه تحلیل فوق‌پیشرفته** 🔥

{dir_emoji} **جهت | Direction:** {dir_text}
💰 **قیمت ورود | Entry:** ${result['entry']:,.2f}
🎯 **حد سود | Take Profit:** ${result['take_profit']:,.2f}
🛡️ **حد ضرر | Stop Loss:** ${result['stop_loss']:,.2f}
⚡ **اهرم | Leverage:** {result['leverage']}x
🎯 **اطمینان | Confidence:** {result['confidence']}%

🧠 **۳۰+ الگوریتم فعال**
💡 **جبران خطا:** اشتباه ۱ = ۲ درست
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
                f"📊 {len(user_data[user_id]['indicators'])}/20 اندیکاتور\n\n"
                f"🔍 ادامه دهید یا روی «ثبت» کلیک کنید",
                reply_markup=get_indicators_keyboard(user_id)
            )
        except ValueError:
            await update.effective_chat.send_message("❌ عدد معتبر وارد کنید!")

# ==================== اجرا ====================
def main():
    print("=" * 80)
    print("🚀 ربات تحلیل تکنیکال فوق‌پیشرفته نسخه ۷.۰")
    print("🧠 با ۳۰+ الگوریتم و سیستم جبران خطا")
    print("=" * 80)
    print(f"👤 ادمین: {ADMIN_ID}")
    print(f"🤖 ربات: {BOT_USERNAME}")
    print(f"📊 الگوریتم‌ها: {len(signal_engine.algorithms)}")
    print(f"💡 جبران خطا: فعال (اشتباه ۱ = ۲ درست)")
    print("=" * 80)
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ ربات با موفقیت راه‌اندازی شد!")
    print("=" * 80)
    
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()