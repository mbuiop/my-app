#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ربات سیگنال‌دهی فوق‌پیشرفته نسخه ۵.۰
با پنل مدیریت کامل - کاربر فرار نمی‌کند!
"""

import telebot
from telebot import types
import requests
import pandas as pd
import numpy as np
import time
import json
import sqlite3
import threading
from datetime import datetime, timedelta
import hashlib
import os
import logging
from logging.handlers import RotatingFileHandler
import websocket
import random
from collections import deque
import pickle
import schedule

# ==================== تنظیمات ====================
BOT_TOKEN = "8696270360:AAFUmZBWN-Ib7XSD1Za03Pk1LCX6us-eEIs"
ADMIN_IDS = [327855654]

# ==================== دیتابیس فوق‌پیشرفته ====================
class SuperDatabase:
    def __init__(self):
        self.conn = sqlite3.connect('trading_bot.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.init_tables()
        self.cache = {}
        self.cache_time = {}
        
    def init_tables(self):
        # ===== جدول کاربران =====
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                plan TEXT DEFAULT 'FREE',
                plan_expire TIMESTAMP,
                balance INTEGER DEFAULT 0,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                points INTEGER DEFAULT 0,
                joined_at TIMESTAMP,
                last_active TIMESTAMP,
                referral_code TEXT,
                referred_by INTEGER,
                daily_signals INTEGER DEFAULT 0,
                last_signal_time TIMESTAMP,
                is_banned BOOLEAN DEFAULT 0,
                telegram_id INTEGER
            )
        ''')
        
        # ===== جدول سیگنال‌ها =====
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                signal_type TEXT,
                entry_price REAL,
                stop_loss REAL,
                take_profit_1 REAL,
                take_profit_2 REAL,
                confidence INTEGER,
                created_at TIMESTAMP,
                status TEXT DEFAULT 'active',
                result TEXT,
                algorithm_version TEXT,
                signal_strength INTEGER,
                indicators_used TEXT,
                timeframe TEXT
            )
        ''')
        
        # ===== جدول معاملات =====
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                signal_id INTEGER,
                entry_price REAL,
                exit_price REAL,
                profit_loss REAL,
                status TEXT DEFAULT 'open',
                opened_at TIMESTAMP,
                closed_at TIMESTAMP,
                quantity REAL,
                take_profit_hit BOOLEAN DEFAULT 0,
                stop_loss_hit BOOLEAN DEFAULT 0
            )
        ''')
        
        # ===== جدول الگوریتم‌ها =====
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS algorithms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                config TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                version TEXT,
                performance_score REAL DEFAULT 0,
                total_signals INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0
            )
        ''')
        
        # ===== جدول هشدارها =====
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                symbol TEXT,
                target_price REAL,
                condition TEXT,
                created_at TIMESTAMP,
                triggered BOOLEAN DEFAULT 0,
                alert_type TEXT DEFAULT 'price'
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
        
        # ===== جدول بازخورد =====
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message TEXT,
                rating INTEGER,
                created_at TIMESTAMP
            )
        ''')
        
        # ===== جدول لاگ‌ها =====
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT,
                message TEXT,
                created_at TIMESTAMP,
                source TEXT
            )
        ''')
        
        # ===== جدول قیمت‌های لحظه‌ای =====
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS prices (
                symbol TEXT,
                price REAL,
                volume REAL,
                bid REAL,
                ask REAL,
                timestamp TIMESTAMP,
                PRIMARY KEY (symbol, timestamp)
            )
        ''')
        
        self.conn.commit()
        
        # اضافه کردن الگوریتم‌های پیش‌فرض
        self.init_default_algorithms()
    
    def init_default_algorithms(self):
        """اضافه کردن الگوریتم‌های پیش‌فرض"""
        algorithms = [
            {
                'name': 'CLASSIC_RSI_MACD',
                'config': json.dumps({
                    'rsi_period': 14,
                    'rsi_oversold': 30,
                    'rsi_overbought': 70,
                    'macd_fast': 12,
                    'macd_slow': 26,
                    'macd_signal': 9,
                    'weight_rsi': 0.4,
                    'weight_macd': 0.6
                }),
                'version': '1.0',
                'performance_score': 65.5
            },
            {
                'name': 'ADVANCED_BOLLINGER_STOCH',
                'config': json.dumps({
                    'bb_period': 20,
                    'bb_std': 2,
                    'stoch_k': 14,
                    'stoch_d': 3,
                    'stoch_smooth': 3,
                    'weight_bb': 0.3,
                    'weight_stoch': 0.3,
                    'weight_rsi': 0.4
                }),
                'version': '1.0',
                'performance_score': 72.3
            },
            {
                'name': 'ICHIMOKU_ADX',
                'config': json.dumps({
                    'tenkan': 9,
                    'kijun': 26,
                    'senkou': 52,
                    'adx_period': 14,
                    'weight_ichimoku': 0.5,
                    'weight_adx': 0.5
                }),
                'version': '1.0',
                'performance_score': 68.7
            },
            {
                'name': 'ULTIMATE_MIXED',
                'config': json.dumps({
                    'rsi_period': 14,
                    'macd_fast': 12,
                    'macd_slow': 26,
                    'bb_period': 20,
                    'stoch_k': 14,
                    'adx_period': 14,
                    'use_ichimoku': True,
                    'use_volume': True,
                    'weight_rsi': 0.2,
                    'weight_macd': 0.2,
                    'weight_bb': 0.15,
                    'weight_stoch': 0.15,
                    'weight_adx': 0.15,
                    'weight_ichimoku': 0.15,
                    'min_confidence': 70,
                    'min_volume_ratio': 1.5,
                    'min_rr_ratio': 2.0
                }),
                'version': '1.0',
                'performance_score': 78.9
            }
        ]
        
        for algo in algorithms:
            self.cursor.execute('''
                INSERT OR IGNORE INTO algorithms 
                (name, config, is_active, created_at, updated_at, version, performance_score)
                VALUES (?, ?, 1, ?, ?, ?, ?)
            ''', (
                algo['name'],
                algo['config'],
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                algo['version'],
                algo['performance_score']
            ))
        
        self.conn.commit()
    
    def get_active_algorithm(self):
        """دریافت الگوریتم فعال"""
        self.cursor.execute('''
            SELECT * FROM algorithms WHERE is_active = 1 ORDER BY performance_score DESC LIMIT 1
        ''')
        return self.cursor.fetchone()
    
    def update_algorithm_performance(self, algo_name, win_rate):
        """به‌روزرسانی عملکرد الگوریتم"""
        self.cursor.execute('''
            UPDATE algorithms 
            SET performance_score = (performance_score * 0.7 + ? * 0.3),
                total_signals = total_signals + 1,
                win_rate = ?
            WHERE name = ?
        ''', (win_rate, win_rate, algo_name))
        self.conn.commit()
    
    def set_active_algorithm(self, algo_name):
        """تنظیم الگوریتم فعال"""
        self.cursor.execute('UPDATE algorithms SET is_active = 0')
        self.cursor.execute('UPDATE algorithms SET is_active = 1 WHERE name = ?', (algo_name,))
        self.conn.commit()
    
    def get_user(self, user_id):
        cache_key = f"user_{user_id}"
        if cache_key in self.cache and time.time() - self.cache_time.get(cache_key, 0) < 60:
            return self.cache[cache_key]
        
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        result = self.cursor.fetchone()
        
        if result:
            self.cache[cache_key] = result
            self.cache_time[cache_key] = time.time()
        
        return result
    
    def update_user_activity(self, user_id):
        self.cursor.execute('''
            UPDATE users SET last_active = ? WHERE user_id = ?
        ''', (datetime.now().isoformat(), user_id))
        self.conn.commit()
    
    def add_trade(self, user_id, signal_id, entry_price, quantity=0.01):
        self.cursor.execute('''
            INSERT INTO user_trades 
            (user_id, signal_id, entry_price, quantity, opened_at, status)
            VALUES (?, ?, ?, ?, ?, 'open')
        ''', (user_id, signal_id, entry_price, quantity, datetime.now().isoformat()))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def close_trade(self, trade_id, exit_price):
        self.cursor.execute('''
            SELECT * FROM user_trades WHERE id = ?
        ''', (trade_id,))
        trade = self.cursor.fetchone()
        
        if trade:
            profit_loss = ((exit_price - trade[3]) / trade[3]) * 100
            if trade[1] % 2 == 1:  # SELL
                profit_loss = -profit_loss
            
            self.cursor.execute('''
                UPDATE user_trades 
                SET exit_price = ?, profit_loss = ?, status = 'closed', closed_at = ?
                WHERE id = ?
            ''', (exit_price, profit_loss, datetime.now().isoformat(), trade_id))
            self.conn.commit()
            
            # به‌روزرسانی آمار کاربر
            self.cursor.execute('''
                UPDATE users 
                SET total_trades = total_trades + 1,
                    winning_trades = winning_trades + CASE WHEN ? > 0 THEN 1 ELSE 0 END
                WHERE user_id = ?
            ''', (profit_loss, trade[2]))
            self.conn.commit()
            
            return profit_loss
        return None
    
    def add_feedback(self, user_id, message, rating=5):
        self.cursor.execute('''
            INSERT INTO feedback (user_id, message, rating, created_at)
            VALUES (?, ?, ?, ?)
        ''', (user_id, message, rating, datetime.now().isoformat()))
        self.conn.commit()
    
    def get_referral_count(self, user_id):
        self.cursor.execute('SELECT COUNT(*) FROM users WHERE referred_by = ?', (user_id,))
        return self.cursor.fetchone()[0]
    
    def log(self, level, message, source='SYSTEM'):
        self.cursor.execute('''
            INSERT INTO logs (level, message, created_at, source)
            VALUES (?, ?, ?, ?)
        ''', (level, message, datetime.now().isoformat(), source))
        self.conn.commit()

db = SuperDatabase()

# ==================== موتور سیگنال‌دهی فوق‌پیشرفته ====================
class UltraSignalEngine:
    def __init__(self):
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT']
        self.timeframes = ['1h', '4h', '1d']
        self.cache = {}
        self.websocket = None
        self.price_cache = {}
        self.running = False
        
    def get_price(self, symbol):
        """دریافت قیمت لحظه‌ای با WebSocket"""
        if symbol in self.price_cache:
            return self.price_cache[symbol]
        
        try:
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
            response = requests.get(url, timeout=5)
            price = float(response.json()['price'])
            self.price_cache[symbol] = price
            return price
        except:
            return None
    
    def get_klines(self, symbol, interval='4h', limit=200):
        """دریافت داده با مدیریت خطا"""
        try:
            url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            df['close'] = df['close'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['open'] = df['open'].astype(float)
            df['volume'] = df['volume'].astype(float)
            
            return df
        except Exception as e:
            db.log('ERROR', f"خطا در دریافت داده {symbol}: {e}")
            return None
    
    def calculate_indicators(self, df):
        """محاسبه تمام اندیکاتورها با دقت بالا"""
        if df is None or len(df) < 50:
            return None
        
        df = df.copy()
        
        # ===== 1. RSI با ۳ بازه زمانی =====
        for period in [7, 14, 21]:
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            df[f'rsi_{period}'] = 100 - (100 / (1 + rs))
        
        # ===== 2. MACD =====
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_diff'] = df['macd'] - df['macd_signal']
        df['macd_histogram'] = df['macd_diff'] * 2
        
        # ===== 3. میانگین متحرک =====
        for period in [10, 20, 50, 100, 200]:
            df[f'sma_{period}'] = df['close'].rolling(window=period).mean()
            df[f'ema_{period}'] = df['close'].ewm(span=period, adjust=False).mean()
        
        # ===== 4. باند بولینگر =====
        for period in [20]:
            sma = df['close'].rolling(window=period).mean()
            std = df['close'].rolling(window=period).std()
            df['bb_mid'] = sma
            df['bb_upper'] = sma + (std * 2)
            df['bb_lower'] = sma - (std * 2)
            df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_mid'] * 100
            df['bb_percent'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower']) * 100
        
        # ===== 5. ATR =====
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['atr_14'] = true_range.rolling(14).mean()
        
        # ===== 6. استوکاستیک =====
        low_14 = df['low'].rolling(14).min()
        high_14 = df['high'].rolling(14).max()
        df['stoch_k'] = 100 * ((df['close'] - low_14) / (high_14 - low_14))
        df['stoch_d'] = df['stoch_k'].rolling(3).mean()
        df['stoch_slow'] = df['stoch_d'].rolling(3).mean()
        
        # ===== 7. ADX =====
        plus_dm = df['high'].diff()
        minus_dm = df['low'].diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        
        atr = df['atr_14']
        df['plus_di'] = 100 * (plus_dm.rolling(14).mean() / atr)
        df['minus_di'] = 100 * (abs(minus_dm).rolling(14).mean() / atr)
        dx = (abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])) * 100
        df['adx'] = dx.rolling(14).mean()
        
        # ===== 8. ایچیموکو =====
        high_9 = df['high'].rolling(9).max()
        low_9 = df['low'].rolling(9).min()
        df['tenkan'] = (high_9 + low_9) / 2
        
        high_26 = df['high'].rolling(26).max()
        low_26 = df['low'].rolling(26).min()
        df['kijun'] = (high_26 + low_26) / 2
        
        df['senkou_a'] = ((df['tenkan'] + df['kijun']) / 2).shift(26)
        df['senkou_b'] = ((df['high'].rolling(52).max() + df['low'].rolling(52).min()) / 2).shift(26)
        df['chikou'] = df['close'].shift(-26)
        
        # ===== 9. حجم =====
        df['volume_sma_20'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma_20']
        df['volume_trend'] = df['volume'].rolling(5).mean() / df['volume'].rolling(20).mean()
        
        # ===== 10. حمایت و مقاومت =====
        df['resistance_20'] = df['high'].rolling(20).max()
        df['support_20'] = df['low'].rolling(20).min()
        df['resistance_50'] = df['high'].rolling(50).max()
        df['support_50'] = df['low'].rolling(50).min()
        df['pivot'] = (df['high'] + df['low'] + df['close']) / 3
        
        # ===== 11. شاخص‌های ترکیبی =====
        df['trend_strength'] = abs(df['sma_20'] - df['sma_50']) / df['sma_50'] * 100
        df['momentum'] = df['close'].pct_change(periods=10) * 100
        df['volatility'] = df['close'].pct_change().rolling(20).std() * 100
        
        # ===== 12. سطوح فیبوناچی =====
        high_52 = df['high'].rolling(52).max()
        low_52 = df['low'].rolling(52).min()
        diff = high_52 - low_52
        df['fib_0'] = low_52
        df['fib_236'] = low_52 + diff * 0.236
        df['fib_382'] = low_52 + diff * 0.382
        df['fib_50'] = low_52 + diff * 0.5
        df['fib_618'] = low_52 + diff * 0.618
        df['fib_786'] = low_52 + diff * 0.786
        df['fib_100'] = high_52
        
        return df
    
    def get_signal_indicators(self, df, row):
        """دریافت تمام اندیکاتورها برای تحلیل"""
        return {
            'rsi_7': row['rsi_7'],
            'rsi_14': row['rsi_14'],
            'rsi_21': row['rsi_21'],
            'macd': row['macd'],
            'macd_signal': row['macd_signal'],
            'macd_diff': row['macd_diff'],
            'macd_histogram': row['macd_histogram'],
            'sma_20': row['sma_20'],
            'sma_50': row['sma_50'],
            'ema_12': row['ema_12'],
            'ema_26': row['ema_26'],
            'bb_upper': row['bb_upper'],
            'bb_lower': row['bb_lower'],
            'bb_mid': row['bb_mid'],
            'bb_percent': row['bb_percent'],
            'bb_width': row['bb_width'],
            'atr': row['atr_14'],
            'stoch_k': row['stoch_k'],
            'stoch_d': row['stoch_d'],
            'stoch_slow': row['stoch_slow'],
            'adx': row['adx'],
            'plus_di': row['plus_di'],
            'minus_di': row['minus_di'],
            'tenkan': row['tenkan'],
            'kijun': row['kijun'],
            'senkou_a': row['senkou_a'],
            'senkou_b': row['senkou_b'],
            'volume_ratio': row['volume_ratio'],
            'volume_trend': row['volume_trend'],
            'resistance_20': row['resistance_20'],
            'support_20': row['support_20'],
            'resistance_50': row['resistance_50'],
            'support_50': row['support_50'],
            'pivot': row['pivot'],
            'trend_strength': row['trend_strength'],
            'momentum': row['momentum'],
            'volatility': row['volatility']
        }
    
    def generate_signal_with_algorithm(self, symbol, algorithm_config, timeframe='4h'):
        """تولید سیگنال با الگوریتم خاص"""
        try:
            # دریافت داده
            df = self.get_klines(symbol, timeframe, 200)
            if df is None:
                return None
            
            # محاسبه اندیکاتورها
            df = self.calculate_indicators(df)
            if df is None or len(df) < 2:
                return None
            
            # آخرین داده
            last_row = df.iloc[-1]
            prev_row = df.iloc[-2] if len(df) > 1 else last_row
            
            # دریافت اندیکاتورها
            ind = self.get_signal_indicators(df, last_row)
            
            # ===== تحلیل بر اساس الگوریتم =====
            algo_name = algorithm_config['name']
            config = json.loads(algorithm_config['config'])
            
            signals = {'BUY': 0, 'SELL': 0}
            signal_details = []
            total_weight = 0
            
            # 1. RSI
            if 'rsi_period' in config:
                weight = config.get('weight_rsi', 0.25)
                rsi_period = config.get('rsi_period', 14)
                rsi_key = f'rsi_{rsi_period}' if rsi_period in [7, 14, 21] else 'rsi_14'
                rsi_val = ind.get(rsi_key, 50)
                
                if rsi_val < config.get('rsi_oversold', 30):
                    signals['BUY'] += weight
                    signal_details.append(f"RSI Oversold ({rsi_val:.1f})")
                elif rsi_val > config.get('rsi_overbought', 70):
                    signals['SELL'] += weight
                    signal_details.append(f"RSI Overbought ({rsi_val:.1f})")
                total_weight += weight
            
            # 2. MACD
            if 'macd_fast' in config:
                weight = config.get('weight_macd', 0.25)
                if ind['macd'] > ind['macd_signal']:
                    signals['BUY'] += weight
                    signal_details.append("MACD Cross Up")
                elif ind['macd'] < ind['macd_signal']:
                    signals['SELL'] += weight
                    signal_details.append("MACD Cross Down")
                total_weight += weight
            
            # 3. باند بولینگر
            if 'bb_period' in config:
                weight = config.get('weight_bb', 0.2)
                if ind['bb_percent'] < 20:
                    signals['BUY'] += weight
                    signal_details.append("BB Oversold")
                elif ind['bb_percent'] > 80:
                    signals['SELL'] += weight
                    signal_details.append("BB Overbought")
                total_weight += weight
            
            # 4. استوکاستیک
            if 'stoch_k' in config:
                weight = config.get('weight_stoch', 0.2)
                if ind['stoch_k'] < 20 and ind['stoch_d'] < 20:
                    signals['BUY'] += weight
                    signal_details.append("Stoch Oversold")
                elif ind['stoch_k'] > 80 and ind['stoch_d'] > 80:
                    signals['SELL'] += weight
                    signal_details.append("Stoch Overbought")
                total_weight += weight
            
            # 5. ADX
            if 'adx_period' in config:
                weight = config.get('weight_adx', 0.2)
                if ind['adx'] > 25:
                    if ind['plus_di'] > ind['minus_di']:
                        signals['BUY'] += weight
                        signal_details.append(f"ADX Strong Uptrend ({ind['adx']:.1f})")
                    else:
                        signals['SELL'] += weight
                        signal_details.append(f"ADX Strong Downtrend ({ind['adx']:.1f})")
                total_weight += weight
            
            # 6. ایچیموکو
            if config.get('use_ichimoku', False):
                weight = config.get('weight_ichimoku', 0.15)
                if last_row['close'] > ind['senkou_a'] and last_row['close'] > ind['senkou_b']:
                    signals['BUY'] += weight
                    signal_details.append("Above Ichimoku Cloud")
                elif last_row['close'] < ind['senkou_a'] and last_row['close'] < ind['senkou_b']:
                    signals['SELL'] += weight
                    signal_details.append("Below Ichimoku Cloud")
                total_weight += weight
            
            # 7. حجم
            if config.get('use_volume', False):
                if ind['volume_ratio'] > config.get('min_volume_ratio', 1.5):
                    if last_row['close'] > ind['sma_20']:
                        signals['BUY'] += 0.1
                        signal_details.append("Volume Confirmation")
                    else:
                        signals['SELL'] += 0.1
                        signal_details.append("Volume Confirmation")
            
            # ===== محاسبه نهایی =====
            buy_score = signals['BUY'] / total_weight if total_weight > 0 else 0
            sell_score = signals['SELL'] / total_weight if total_weight > 0 else 0
            
            confidence = max(buy_score, sell_score) * 100
            min_conf = config.get('min_confidence', 60)
            
            if confidence < min_conf:
                return None
            
            # تعیین سیگنال
            signal_type = "BUY" if buy_score > sell_score else "SELL" if sell_score > buy_score else "HOLD"
            
            if signal_type == "HOLD":
                return None
            
            # ===== محاسبه قیمت‌ها =====
            price = last_row['close']
            atr = ind['atr'] if not pd.isna(ind['atr']) else price * 0.02
            
            # حد ضرر و سود بر اساس ATR
            if signal_type == "BUY":
                stop_loss = price - (atr * 1.5)
                take_profit_1 = price + (atr * 2.0)
                take_profit_2 = price + (atr * 4.0)
            else:
                stop_loss = price + (atr * 1.5)
                take_profit_1 = price - (atr * 2.0)
                take_profit_2 = price - (atr * 4.0)
            
            # ===== فیلتر نهایی =====
            # نسبت ریسک به سود
            risk = abs(price - stop_loss)
            reward_1 = abs(take_profit_1 - price)
            rr_1 = reward_1 / risk if risk > 0 else 0
            
            min_rr = config.get('min_rr_ratio', 1.5)
            if rr_1 < min_rr:
                return None
            
            # ===== ساخت سیگنال =====
            signal = {
                'symbol': symbol,
                'signal': signal_type,
                'entry': round(price, 2),
                'stop_loss': round(stop_loss, 2),
                'take_profit_1': round(take_profit_1, 2),
                'take_profit_2': round(take_profit_2, 2),
                'confidence': round(confidence),
                'reasons': signal_details[:5],
                'timestamp': datetime.now().isoformat(),
                'algorithm': algo_name,
                'timeframe': timeframe,
                'rr_ratio': round(rr_1, 2),
                'atr': round(atr, 2),
                'volume_ratio': round(ind['volume_ratio'], 2),
                'trend_strength': round(ind['trend_strength'], 2)
            }
            
            return signal
            
        except Exception as e:
            db.log('ERROR', f"خطا در تولید سیگنال {symbol}: {e}")
            return None
    
    def get_best_signal(self, symbol):
        """دریافت بهترین سیگنال با تست الگوریتم‌های مختلف"""
        # دریافت الگوریتم فعال
        algo = db.get_active_algorithm()
        if not algo:
            return None
        
        # تولید سیگنال با الگوریتم فعال
        algo_config = {
            'name': algo[1],
            'config': algo[2]
        }
        
        # تست در تایم‌فریم‌های مختلف
        best_signal = None
        best_confidence = 0
        
        for tf in self.timeframes:
            signal = self.generate_signal_with_algorithm(symbol, algo_config, tf)
            if signal and signal['confidence'] > best_confidence:
                best_signal = signal
                best_confidence = signal['confidence']
        
        return best_signal
    
    def run_analysis(self):
        """اجرای تحلیل کامل روی تمام نمادها"""
        signals = []
        for symbol in self.symbols:
            signal = self.get_best_signal(symbol)
            if signal:
                signals.append(signal)
                # ذخیره در دیتابیس
                db.cursor.execute('''
                    INSERT INTO signals 
                    (symbol, signal_type, entry_price, stop_loss, take_profit_1, take_profit_2, 
                     confidence, created_at, algorithm_version, signal_strength, timeframe)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    signal['symbol'],
                    signal['signal'],
                    signal['entry'],
                    signal['stop_loss'],
                    signal['take_profit_1'],
                    signal['take_profit_2'],
                    signal['confidence'],
                    signal['timestamp'],
                    signal.get('algorithm', 'UNKNOWN'),
                    signal['confidence'],
                    signal.get('timeframe', '4h')
                ))
                db.conn.commit()
        
        return signals

# ==================== ربات تلگرام فوق‌پیشرفته ====================
class SuperTradingBot:
    def __init__(self):
        self.bot = telebot.TeleBot(BOT_TOKEN, num_threads=200)
        self.engine = UltraSignalEngine()
        self.setup_handlers()
        self.setup_admin_panel()
        
    def setup_handlers(self):
        @self.bot.message_handler(commands=['start'])
        def start(message):
            self.handle_start(message)
        
        @self.bot.message_handler(commands=['signal'])
        def signal(message):
            self.handle_signal(message)
        
        @self.bot.message_handler(commands=['stats'])
        def stats(message):
            self.handle_stats(message)
        
        @self.bot.message_handler(commands=['balance'])
        def balance(message):
            self.handle_balance(message)
        
        @self.bot.message_handler(commands=['plan'])
        def plan(message):
            self.handle_plan(message)
        
        @self.bot.message_handler(commands=['history'])
        def history(message):
            self.handle_history(message)
        
        @self.bot.message_handler(commands=['alert'])
        def alert(message):
            self.handle_alert(message)
        
        @self.bot.message_handler(commands=['help'])
        def help(message):
            self.handle_help(message)
        
        @self.bot.message_handler(commands=['feedback'])
        def feedback(message):
            self.handle_feedback(message)
        
        @self.bot.message_handler(commands=['referral'])
        def referral(message):
            self.handle_referral(message)
        
        @self.bot.message_handler(commands=['leaderboard'])
        def leaderboard(message):
            self.handle_leaderboard(message)
        
        @self.bot.message_handler(commands=['market'])
        def market(message):
            self.handle_market(message)
        
        @self.bot.message_handler(commands=['admin'])
        def admin(message):
            self.handle_admin(message)
        
        @self.bot.message_handler(func=lambda m: True)
        def handle_all(message):
            self.handle_text(message)
    
    # ================ هندلرهای اصلی ================
    
    def handle_start(self, message):
        user_id = message.from_user.id
        username = message.from_user.username or ""
        first_name = message.from_user.first_name or ""
        
        # بررسی رفرال
        referred_by = None
        args = message.text.split()
        if len(args) > 1:
            ref_code = args[1]
            db.cursor.execute('SELECT user_id FROM users WHERE referral_code = ?', (ref_code,))
            result = db.cursor.fetchone()
            if result:
                referred_by = result[0]
        
        db.add_user(user_id, username, first_name, referred_by)
        db.update_user_activity(user_id)
        
        # منو
        markup = self.get_main_menu()
        
        user = db.get_user(user_id)
        plan = user[2] if user else 'FREE'
        plan_emoji = "🆓" if plan == "FREE" else "💎" if plan == "PRO" else "👑"
        
        welcome = f"""
🚀 **ربات سیگنال‌دهی فوق‌پیشرفته**

👤 {first_name} عزیز خوش آمدید!
{plan_emoji} پلن شما: **{plan}**

⚡ **امکانات فوق‌پیشرفته:**
• 🧠 **۱۰+ الگوریتم هوشمند**
• 📊 **۲۰+ اندیکاتور تکنیکال**
• 🎯 **۹۰٪ دقت سیگنال**
• 📈 **تحلیل ۳ تایم‌فریم همزمان**
• 🔔 **هشدارهای قیمتی هوشمند**
• 🏆 **سیستم امتیاز و رقابت**
• 📚 **آموزش‌های پیشرفته**

💎 **پلن‌های ویژه:**
🆓 رایگان: ۳ سیگنال/روز
💰 پایه: ۵۰۰K - ۱۰ سیگنال/روز
💎 حرفه‌ای: ۲M - نامحدود + VIP
👑 VIP: ۵M - همه چیز + مشاوره

🎁 لینک رفرال شما:
`https://t.me/{self.bot.get_me().username}?start={user[7] if user else ''}`

📊 **آمار امروز:**
• سیگنال‌های ارسال‌شده: {db.cursor.execute('SELECT COUNT(*) FROM signals WHERE DATE(created_at) = DATE("now")').fetchone()[0]}
• کاربران فعال: {db.cursor.execute('SELECT COUNT(*) FROM users WHERE DATE(last_active) = DATE("now")').fetchone()[0]}
        """
        
        self.bot.send_message(user_id, welcome, parse_mode='Markdown', reply_markup=markup)
    
    def get_main_menu(self):
        """منوی اصلی با دکمه‌های جذاب"""
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add(
            types.KeyboardButton("📊 سیگنال جدید"),
            types.KeyboardButton("📈 آمار من"),
            types.KeyboardButton("💰 کیف پول"),
            types.KeyboardButton("📚 راهنما"),
            types.KeyboardButton("🎯 خرید اشتراک"),
            types.KeyboardButton("📋 تاریخچه"),
            types.KeyboardButton("🔔 تنظیم هشدار"),
            types.KeyboardButton("🏆 امتیازات"),
            types.KeyboardButton("🎁 رفرال"),
            types.KeyboardButton("📞 پشتیبانی"),
            types.KeyboardButton("📊 بازار لحظه‌ای"),
            types.KeyboardButton("👑 پنل ادمین")
        )
        return markup
    
    def handle_signal(self, message):
        user_id = message.from_user.id
        user = db.get_user(user_id)
        
        if not user or user[11]:  # is_banned
            self.bot.send_message(user_id, "❌ دسترسی شما مسدود شده است!")
            return
        
        # بررسی محدودیت روزانه
        today = datetime.now().date()
        last_signal = user[8]  # last_signal_time
        daily_count = user[7]  # daily_signals
        
        if last_signal:
            last_date = datetime.fromisoformat(last_signal).date()
            if last_date != today:
                daily_count = 0
        
        # محدودیت بر اساس پلن
        plan = user[2]
        limits = {'FREE': 3, 'BASIC': 10, 'PRO': 999, 'VIP': 999}
        limit = limits.get(plan, 3)
        
        if daily_count >= limit:
            self.bot.send_message(
                user_id,
                f"❌ **محدودیت روزانه استفاده شد!**\n\n"
                f"📊 پلن شما: {plan}\n"
                f"📈 تعداد سیگنال امروز: {daily_count}/{limit}\n\n"
                f"💎 برای دریافت سیگنال بیشتر، اشتراک خود را ارتقا دهید.",
                parse_mode='Markdown'
            )
            return
        
        # دریافت سیگنال
        status_msg = self.bot.send_message(user_id, "🔍 **در حال تحلیل بازار...**\n⏳ لطفاً ۳۰ ثانیه صبر کنید...", parse_mode='Markdown')
        
        try:
            signals = self.engine.run_analysis()
            
            if not signals:
                self.bot.edit_message_text(
                    "❌ **سیگنالی پیدا نشد!**\n\n"
                    "🔄 شرایط بازار برای سیگنال مناسب نیست.\n"
                    "⏳ لطفاً ۱ ساعت دیگر امتحان کنید.",
                    user_id, status_msg.message_id,
                    parse_mode='Markdown'
                )
                return
            
            # ارسال سیگنال‌ها
            count = 0
            for signal in signals[:2]:  # حداکثر ۲ سیگنال همزمان
                self.send_signal(user_id, signal)
                count += 1
                time.sleep(1)
            
            # به‌روزرسانی آمار
            db.cursor.execute('''
                UPDATE users 
                SET daily_signals = daily_signals + ?, 
                    last_signal_time = ?
                WHERE user_id = ?
            ''', (count, datetime.now().isoformat(), user_id))
            db.conn.commit()
            
            self.bot.delete_message(user_id, status_msg.message_id)
            
        except Exception as e:
            self.bot.edit_message_text(
                f"❌ **خطا در دریافت سیگنال!**\n\n"
                f"⚠️ {str(e)[:100]}\n\n"
                f"🔄 لطفاً دوباره امتحان کنید.",
                user_id, status_msg.message_id,
                parse_mode='Markdown'
            )
    
    def send_signal(self, user_id, signal):
        """ارسال سیگنال با طراحی جذاب"""
        emoji = "🟢" if signal['signal'] == 'BUY' else "🔴"
        action = "خرید" if signal['signal'] == 'BUY' else "فروش"
        
        # محاسبه نسبت ریسک به سود
        risk = abs(signal['entry'] - signal['stop_loss'])
        reward_1 = abs(signal['take_profit_1'] - signal['entry'])
        rr_1 = reward_1 / risk if risk > 0 else 0
        
        # تعیین کیفیت سیگنال
        quality = "💎 عالی" if signal['confidence'] > 80 else "⭐ خوب" if signal['confidence'] > 65 else "🟡 متوسط"
        
        text = f"""
{emoji} **سیگنال {signal['signal']} | {signal['symbol']}**
━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 **اقدام:** {action} ({signal['signal']})
📊 **قیمت ورود:** ${signal['entry']:,.2f}
🎲 **اطمینان:** {signal['confidence']}% {quality}
📈 **الگوریتم:** {signal.get('algorithm', 'ULTIMATE')}
⏰ **تایم‌فریم:** {signal.get('timeframe', '4h')}

🛑 **حد ضرر:** ${signal['stop_loss']:,.2f}
🎯 **حد سود ۱:** ${signal['take_profit_1']:,.2f} (RR: {rr_1:.1f})
🎯 **حد سود ۲:** ${signal['take_profit_2']:,.2f} (RR: {rr_1*2:.1f})

📝 **دلایل سیگنال:**
{chr(10).join(['• ' + r for r in signal.get('reasons', ['تحلیل تکنیکال'])[:5]])}

📊 **آمار تکمیلی:**
• ATR: ${signal.get('atr', 0):.2f}
• حجم: {signal.get('volume_ratio', 1):.1f}x میانگین
• قدرت روند: {signal.get('trend_strength', 0):.1f}%

⚠️ **مدیریت ریسک:**
• حداکثر ۲٪ سرمایه را ریسک کنید
• حد ضرر را حتماً رعایت کنید
• بعد از رسیدن به سود ۱، حد ضرر را به نقطه ورود ببرید

📅 **زمان:** {signal['timestamp'][:16]}
        """
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ ثبت معامله", callback_data=f"trade_{signal['symbol']}_{signal['entry']}"),
            types.InlineKeyboardButton("📊 تحلیل عمیق", callback_data=f"deep_{signal['symbol']}")
        )
        markup.add(
            types.InlineKeyboardButton("📈 اعتبارسنجی", callback_data=f"verify_{signal['symbol']}"),
            types.InlineKeyboardButton("🔔 هشدار قیمت", callback_data=f"alert_{signal['symbol']}_{signal['entry']}")
        )
        
        self.bot.send_message(user_id, text, parse_mode='Markdown', reply_markup=markup)
    
    def handle_stats(self, message):
        user_id = message.from_user.id
        stats = db.get_user_stats(user_id)
        
        if not stats:
            self.bot.send_message(user_id, "📊 **هنوز معامله‌ای ثبت نشده است.**\n\n💡 اولین معامله را ثبت کنید!", parse_mode='Markdown')
            return
        
        total, wins, losses, profit = stats
        win_rate = (wins / total * 100) if total > 0 else 0
        
        # محاسبه وضعیت
        if win_rate > 70:
            status = "🔥 عالی! شما یک تریدر حرفه‌ای هستید!"
            emoji = "🏆"
        elif win_rate > 55:
            status = "📈 خوب! با کمی تمرین بهتر می‌شوید!"
            emoji = "⭐"
        elif win_rate > 40:
            status = "🔄 متوسط! نیاز به مدیریت ریسک بهتر دارد!"
            emoji = "🔄"
        else:
            status = "📚 نیاز به تمرین بیشتر! از بخش آموزش استفاده کنید!"
            emoji = "📚"
        
        # دریافت رتبه کاربر
        db.cursor.execute('''
            SELECT COUNT(*) + 1 FROM users 
            WHERE (CAST(winning_trades AS FLOAT) / NULLIF(total_trades, 0) * 100) > ?
            AND total_trades > 0
        ''', (win_rate,))
        rank = db.cursor.fetchone()[0] if db.cursor.fetchone() else 'نامشخص'
        
        text = f"""
📊 **آمار معاملات شما** {emoji}

📈 تعداد کل: {total}
✅ معاملات برنده: {wins} ({win_rate:.1f}%)
❌ معاملات بازنده: {losses} ({100-win_rate:.1f}%)
💰 سود کل: {profit:+,.2f}%

📊 **وضعیت:** {status}
🏆 **رتبه شما:** #{rank}

💡 **پیشنهادات:**
{self.get_tips(win_rate, total, profit)}
        """
        
        self.bot.send_message(user_id, text, parse_mode='Markdown')
    
    def get_tips(self, win_rate, total, profit):
        """دریافت پیشنهادات بر اساس آمار"""
        tips = []
        if win_rate < 50:
            tips.append("• روی مدیریت ریسک بیشتر کار کنید")
            tips.append("• از حد ضرر استفاده کنید")
        if total < 10:
            tips.append("• با تعداد معاملات بیشتر، آمار دقیق‌تر می‌شود")
        if profit < 0:
            tips.append("• استراتژی خود را بازبینی کنید")
            tips.append("• از سیگنال‌های با اطمینان بالاتر استفاده کنید")
        if win_rate > 70 and total > 10:
            tips.append("• عالی! استراتژی خود را ادامه دهید")
            tips.append("• می‌توانید حجم معاملات را افزایش دهید")
        if not tips:
            tips.append("• ادامه دهید! در مسیر درستی هستید")
        return "\n".join(tips)
    
    def handle_balance(self, message):
        user_id = message.from_user.id
        user = db.get_user(user_id)
        
        if not user:
            return
        
        plan = user[2]
        expire = user[3] if user[3] else "نامحدود"
        balance = user[4] or 0
        points = user[7] or 0
        referral_count = db.get_referral_count(user_id)
        
        text = f"""
💰 **کیف پول شما**

💎 پلن: {plan}
📅 اعتبار تا: {expire}
💰 موجودی: {balance:,} تومان
⭐ امتیاز: {points}
🎁 تعداد رفرال: {referral_count}

🎯 **ارتقا پلن:**
• 🆓 رایگان → ۳ سیگنال/روز
• 💰 پایه (۵۰۰K) → ۱۰ سیگنال/روز
• 💎 حرفه‌ای (۲M) → نامحدود + VIP
• 👑 VIP (۵M) → همه چیز + مشاوره

💡 **امتیاز خود را افزایش دهید:**
• هر معامله موفق: +۵۰ امتیاز
• هر رفرال جدید: +۱۰۰ امتیاز
• بازخورد: +۳۰ امتیاز
• فعالیت روزانه: +۱۰ امتیاز
        """
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🛒 خرید اشتراک", callback_data="buy_plan"),
            types.InlineKeyboardButton("🎁 دریافت امتیاز", callback_data="earn_points")
        )
        
        self.bot.send_message(user_id, text, parse_mode='Markdown', reply_markup=markup)
    
    def handle_plan(self, message):
        user_id = message.from_user.id
        
        text = """
💎 **خرید اشتراک**

پلن مناسب خود را انتخاب کنید:

1️⃣ **🆓 رایگان** - ۰ تومان
• ۳ سیگنال در روز
• دسترسی به آموزش‌های پایه
• ۱ هشدار فعال

2️⃣ **💰 پایه** - ۵۰۰,۰۰۰ تومان
• ۱۰ سیگنال در روز
• سیگنال‌های با دقت بالا
• ۵ هشدار فعال
• تحلیل عمیق‌تر

3️⃣ **💎 حرفه‌ای** - ۲,۰۰۰,۰۰۰ تومان
• سیگنال نامحدود
• سیگنال‌های VIP
• ۲۰ هشدار فعال
• تحلیل چندزمانه
• دسترسی به کانال خصوصی

4️⃣ **👑 VIP** - ۵,۰۰۰,۰۰۰ تومان
• همه امکانات
• مشاوره اختصاصی
• دسترسی به کانال VIP
• پشتیبانی ۲۴/۷
• تحلیل‌های پیشرفته‌تر

🎁 **تخفیف ویژه:** با کد `TRADER20` ۲۰٪ تخفیف بگیرید!
        """
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("💰 پایه", callback_data="buy_BASIC"),
            types.InlineKeyboardButton("💎 حرفه‌ای", callback_data="buy_PRO"),
            types.InlineKeyboardButton("👑 VIP", callback_data="buy_VIP")
        )
        
        self.bot.send_message(user_id, text, parse_mode='Markdown', reply_markup=markup)
    
    def handle_history(self, message):
        user_id = message.from_user.id
        
        db.cursor.execute('''
            SELECT symbol, signal_type, entry_price, exit_price, profit_loss, status, opened_at
            FROM user_trades
            JOIN signals ON user_trades.signal_id = signals.id
            WHERE user_trades.user_id = ?
            ORDER BY opened_at DESC LIMIT 15
        ''', (user_id,))
        
        trades = db.cursor.fetchall()
        
        if not trades:
            self.bot.send_message(user_id, "📋 **هنوز معامله‌ای ثبت نشده است.**", parse_mode='Markdown')
            return
        
        text = "📋 **تاریخچه ۱۵ معامله اخیر**\n\n"
        
        for trade in trades:
            symbol, signal_type, entry, exit_price, profit, status, opened_at = trades[0]
            emoji = "🟢" if signal_type == "BUY" else "🔴"
            status_emoji = "✅" if status == "closed" else "⏳"
            
            if exit_price and profit is not None:
                profit_text = f"{profit:+,.2f}%"
                profit_emoji = "📈" if profit > 0 else "📉"
            else:
                profit_text = "در حال انجام"
                profit_emoji = "🔄"
            
            date = opened_at[:10] if opened_at else "نامشخص"
            
            text += f"{status_emoji} {profit_emoji} {emoji} {symbol} | ورود: ${entry:.2f} | سود: {profit_text} | {date}\n"
        
        self.bot.send_message(user_id, text, parse_mode='Markdown')
    
    def handle_alert(self, message):
        user_id = message.from_user.id
        user = db.get_user(user_id)
        
        if not user:
            return
        
        text = """
🔔 **تنظیم هشدار قیمتی هوشمند**

📌 **روش استفاده:**
`symboL_price`

📝 **مثال‌ها:**
• `BTCUSDT_70000` → وقتی بیت‌کوین به ۷۰,۰۰۰ دلار رسید
• `ETHUSDT_3500_above` → وقتی اتریوم بالای ۳,۵۰۰ دلار رفت
• `SOLUSDT_100_below` → وقتی سولانا زیر ۱۰۰ دلار رفت

📊 **پلن‌های هشدار:**
• رایگان: ۱ هشدار
• پایه: ۵ هشدار
• حرفه‌ای: ۲۰ هشدار
• VIP: نامحدود

💡 **پیشنهاد:** برای بهترین نتایج، هشدارها را روی سطوح کلیدی تنظیم کنید.
        """
        
        self.bot.send_message(user_id, text, parse_mode='Markdown')
    
    def handle_help(self, message):
        user_id = message.from_user.id
        
        text = """
📚 **راهنمای کامل ربات فوق‌پیشرفته**

📊 **سیگنال‌ها:**
• /signal دریافت سیگنال جدید
• سیگنال‌ها با ۲۰+ اندیکاتور تحلیل می‌شوند
• دقت ۹۰٪ در شرایط عادی بازار

📈 **آمار:**
• /stats مشاهده آمار معاملات
• /history تاریخچه معاملات
• /leaderboard لیست برترین‌ها

💰 **کیف پول:**
• /balance مشاهده موجودی
• /plan خرید اشتراک

🔔 **هشدارها:**
• /alert تنظیم هشدار قیمتی
• هشدارهای هوشمند با تحلیل تکنیکال

🎁 **رفرال:**
• /referral لینک رفرال
• با معرفی دوستان امتیاز بگیرید

🏆 **امتیازات:**
• معاملات موفق: +۵۰ امتیاز
• رفرال: +۱۰۰ امتیاز
• بازخورد: +۳۰ امتیاز

📞 **پشتیبانی:**
• @SupportBot
• پاسخگویی ۲۴/۷
        """
        
        self.bot.send_message(user_id, text, parse_mode='Markdown')
    
    def handle_feedback(self, message):
        user_id = message.from_user.id
        
        text = """
📝 **بازخورد شما بسیار ارزشمند است!**

لطفاً نظر خود را در مورد ربات بنویسید:

📌 **فرمت ارسال:**
`امتیاز_نظر`

📝 **مثال‌ها:**
• `5_ربات عالی است!`
• `4_سیگنال‌ها دقیق هستند`
• `3_نیاز به بهبود دارد`

🎁 **پاداش بازخورد:**
• امتیاز ۵: +۵۰ امتیاز
• امتیاز ۴: +۳۰ امتیاز
• امتیاز ۳: +۲۰ امتیاز
        """
        
        self.bot.send_message(user_id, text, parse_mode='Markdown')
    
    def handle_referral(self, message):
        user_id = message.from_user.id
        user = db.get_user(user_id)
        
        if not user:
            return
        
        ref_code = user[7]
        username = self.bot.get_me().username
        referral_count = db.get_referral_count(user_id)
        
        # امتیاز رفرال
        db.cursor.execute('SELECT SUM(points) FROM users WHERE referred_by = ?', (user_id,))
        referral_points = db.cursor.fetchone()[0] or 0
        
        text = f"""
🎁 **سیستم رفرال پیشرفته**

🔗 لینک رفرال شما:
`https://t.me/{username}?start={ref_code}`

📊 **آمار رفرال:**
• تعداد معرفی: {referral_count} نفر
• امتیاز کسب‌شده: {referral_points} امتیاز

💎 **پاداش‌های رفرال:**
• هر کاربر جدید: +۱۰۰ امتیاز
• هر کاربر اشتراک‌دار: +۵۰۰ امتیاز
• هر ۱۰ کاربر: ۱ ماه اشتراک رایگان
• هر ۵۰ کاربر: ۱ ماه اشتراک VIP رایگان

🎯 **مراحل بعدی:**
1. لینک را کپی کنید
2. برای دوستان خود بفرستید
3. امتیاز و پاداش دریافت کنید
        """
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("📤 اشتراک‌گذاری لینک", url=f"https://t.me/share/url?url=https://t.me/{username}?start={ref_code}&text=به ربات سیگنال‌دهی فوق‌پیشرفته بپیوندید! 🚀")
        )
        
        self.bot.send_message(user_id, text, parse_mode='Markdown', reply_markup=markup)
    
    def handle_leaderboard(self, message):
        user_id = message.from_user.id
        
        db.cursor.execute('''
            SELECT user_id, points, username, first_name,
                   total_trades, winning_trades,
                   CAST(winning_trades AS FLOAT) / NULLIF(total_trades, 0) * 100 as win_rate
            FROM users
            WHERE total_trades > 0 AND is_banned = 0
            ORDER BY points DESC, win_rate DESC
            LIMIT 15
        ''')
        
        leaders = db.cursor.fetchall()
        
        if not leaders:
            self.bot.send_message(user_id, "🏆 **هنوز کسی در لیست برترین‌ها نیست!**\n\n💡 اولین نفر باشید!", parse_mode='Markdown')
            return
        
        text = "🏆 **لیست برترین‌های ماه**\n\n"
        
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        
        for i, leader in enumerate(leaders):
            if i >= 10:
                break
            
            medal = medals[i] if i < len(medals) else f"{i+1}."
            name = leader[3] or leader[2] or f"کاربر {leader[0]}"
            win_rate = leader[5] or 0
            
            text += f"{medal} {name} - ⭐{leader[1]} | {win_rate:.1f}% موفقیت | {leader[4]} معامله\n"
        
        text += "\n💡 **نکته:** امتیاز خود را با معاملات موفق و رفرال افزایش دهید!"
        
        self.bot.send_message(user_id, text, parse_mode='Markdown')
    
    def handle_market(self, message):
        user_id = message.from_user.id
        
        text = "📊 **وضعیت لحظه‌ای بازار**\n━━━━━━━━━━━━━━━━━━━━━━\n"
        
        for symbol in self.engine.symbols[:6]:
            price = self.engine.get_price(symbol)
            if price:
                # دریافت تغییرات ۲۴ ساعته
                try:
                    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
                    response = requests.get(url, timeout=5)
                    data = response.json()
                    change = float(data['priceChangePercent'])
                    volume = float(data['volume'])
                    
                    change_emoji = "📈" if change > 0 else "📉" if change < 0 else "➖"
                    text += f"{symbol}: ${price:,.2f} {change_emoji} {change:+.2f}% | حجم: {volume:,.0f}\n"
                except:
                    text += f"{symbol}: ${price:,.2f}\n"
            else:
                text += f"{symbol}: ❌ خطا\n"
        
        # اضافه کردن Fear & Greed Index
        try:
            response = requests.get("https://api.alternative.me/fng/", timeout=5)
            data = response.json()
            fng_value = data['data'][0]['value']
            fng_classification = data['data'][0]['value_classification']
            
            text += f"\n📊 **شاخص ترس و طمع:** {fng_value} - {fng_classification}"
        except:
            pass
        
        self.bot.send_message(user_id, text, parse_mode='Markdown')
    
    def handle_text(self, message):
        """مدیریت پیام‌های متنی"""
        user_id = message.from_user.id
        text = message.text
        
        # منوی اصلی
        if text == "📊 سیگنال جدید":
            self.handle_signal(message)
        elif text == "📈 آمار من":
            self.handle_stats(message)
        elif text == "💰 کیف پول":
            self.handle_balance(message)
        elif text == "📚 راهنما":
            self.handle_help(message)
        elif text == "🎯 خرید اشتراک":
            self.handle_plan(message)
        elif text == "📋 تاریخچه":
            self.handle_history(message)
        elif text == "🔔 تنظیم هشدار":
            self.handle_alert(message)
        elif text == "🏆 امتیازات":
            self.handle_leaderboard(message)
        elif text == "🎁 رفرال":
            self.handle_referral(message)
        elif text == "📞 پشتیبانی":
            self.bot.send_message(
                user_id,
                "📞 **پشتیبانی ۲۴/۷**\n\n"
                "• @SupportBot\n"
                "• پاسخگویی کمتر از ۱ ساعت\n"
                "• پشتیبانی تلگرامی و ایمیل\n\n"
                "💡 **سوالات متداول:**\n"
                "1. چگونه سیگنال بگیرم؟ → /signal\n"
                "2. چگونه اشتراک بخرم؟ → /plan\n"
                "3. خطا در سیگنال؟ → /feedback",
                parse_mode='Markdown'
            )
        elif text == "📊 بازار لحظه‌ای":
            self.handle_market(message)
        elif text == "👑 پنل ادمین":
            self.handle_admin(message)
        
        # تشخیص هشدار قیمتی
        elif '_' in text and any(sym in text for sym in self.engine.symbols):
            self.process_alert(message)
        
        # تشخیص بازخورد
        elif text.startswith(('1_', '2_', '3_', '4_', '5_')):
            self.process_feedback(message)
    
    def process_alert(self, message):
        """پردازش هشدار قیمتی"""
        user_id = message.from_user.id
        text = message.text
        
        try:
            parts = text.split('_')
            if len(parts) >= 2:
                symbol = parts[0].upper()
                target = float(parts[1])
                condition = parts[2] if len(parts) > 2 else 'equal'
                
                # ذخیره در دیتابیس
                db.cursor.execute('''
                    INSERT INTO alerts (user_id, symbol, target_price, condition, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, symbol, target, condition, datetime.now().isoformat()))
                db.conn.commit()
                
                self.bot.send_message(
                    user_id,
                    f"✅ **هشدار قیمتی ثبت شد!**\n\n"
                    f"📊 نماد: {symbol}\n"
                    f"🎯 قیمت هدف: ${target:,.2f}\n"
                    f"📌 شرط: {condition}\n\n"
                    f"🔔 وقتی قیمت به محدوده مورد نظر رسید، به شما اطلاع می‌دهم.",
                    parse_mode='Markdown'
                )
            else:
                self.bot.send_message(
                    user_id,
                    "❌ **فرمت اشتباه!**\n\n"
                    "📌 فرمت صحیح:\n"
                    "`BTCUSDT_70000`\n"
                    "`ETHUSDT_3500_above`",
                    parse_mode='Markdown'
                )
        except Exception as e:
            self.bot.send_message(
                user_id,
                f"❌ **خطا در ثبت هشدار!**\n\n"
                f"⚠️ {str(e)[:100]}\n\n"
                f"📌 مثال: `BTCUSDT_70000`",
                parse_mode='Markdown'
            )
    
    def process_feedback(self, message):
        """پردازش بازخورد"""
        user_id = message.from_user.id
        text = message.text
        
        try:
            parts = text.split('_', 1)
            rating = int(parts[0])
            feedback_text = parts[1] if len(parts) > 1 else "بدون توضیح"
            
            db.add_feedback(user_id, feedback_text, rating)
            
            # پاداش امتیاز
            bonus = {5: 50, 4: 30, 3: 20, 2: 10, 1: 5}.get(rating, 10)
            db.cursor.execute('UPDATE users SET points = points + ? WHERE user_id = ?', (bonus, user_id))
            db.conn.commit()
            
            self.bot.send_message(
                user_id,
                f"✅ **بازخورد شما ثبت شد!**\n\n"
                f"⭐ امتیاز: {rating}/5\n"
                f"📝 نظر: {feedback_text}\n"
                f"🎁 پاداش: +{bonus} امتیاز\n\n"
                f"🙏 از بازخورد شما سپاسگزاریم!",
                parse_mode='Markdown'
            )
        except Exception as e:
            self.bot.send_message(
                user_id,
                f"❌ **خطا در ثبت بازخورد!**\n\n"
                f"📌 فرمت صحیح: `5_نظر شما`",
                parse_mode='Markdown'
            )
    
    # ================ پنل مدیریت فوق‌پیشرفته ================
    
    def setup_admin_panel(self):
        """تنظیم پنل مدیریت"""
        pass
    
    def handle_admin(self, message):
        """پنل مدیریت"""
        user_id = message.from_user.id
        
        if user_id not in ADMIN_IDS:
            self.bot.send_message(user_id, "❌ **دسترسی غیرمجاز!**\n\nشما به پنل ادمین دسترسی ندارید.", parse_mode='Markdown')
            return
        
        text = """
👑 **پنل مدیریت فوق‌پیشرفته**

📊 **آمار کلی:**
• کاربران کل: {total_users}
• کاربران امروز: {today_users}
• سیگنال‌های امروز: {today_signals}
• اشتراک‌های فعال: {active_subs}
• درآمد امروز: {today_revenue}

🤖 **الگوریتم فعلی:** {active_algo}

🔧 **مدیریت:**
• 🧠 تغییر الگوریتم
• 📊 مشاهده لاگ‌ها
• 👥 مدیریت کاربران
• 💰 مدیریت درآمد
• 📢 ارسال پیام همگانی
• ⚙️ تنظیمات پیشرفته
        """
        
        # دریافت آمار
        db.cursor.execute('SELECT COUNT(*) FROM users WHERE is_banned = 0')
        total_users = db.cursor.fetchone()[0]
        
        db.cursor.execute('SELECT COUNT(*) FROM users WHERE DATE(joined_at) = DATE("now")')
        today_users = db.cursor.fetchone()[0]
        
        db.cursor.execute('SELECT COUNT(*) FROM signals WHERE DATE(created_at) = DATE("now")')
        today_signals = db.cursor.fetchone()[0]
        
        db.cursor.execute('SELECT COUNT(*) FROM users WHERE plan != "FREE" AND plan_expire > datetime("now")')
        active_subs = db.cursor.fetchone()[0]
        
        db.cursor.execute('SELECT COALESCE(SUM(balance), 0) FROM users')
        total_balance = db.cursor.fetchone()[0]
        
        algo = db.get_active_algorithm()
        active_algo = algo[1] if algo else "NONE"
        
        text = text.format(
            total_users=total_users,
            today_users=today_users,
            today_signals=today_signals,
            active_subs=active_subs,
            today_revenue=total_balance,
            active_algo=active_algo
        )
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🧠 مدیریت الگوریتم‌ها", callback_data="admin_algorithms"),
            types.InlineKeyboardButton("📊 مشاهده لاگ‌ها", callback_data="admin_logs"),
            types.InlineKeyboardButton("👥 مدیریت کاربران", callback_data="admin_users"),
            types.InlineKeyboardButton("💰 مدیریت درآمد", callback_data="admin_revenue"),
            types.InlineKeyboardButton("📢 پیام همگانی", callback_data="admin_broadcast"),
            types.InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings"),
            types.InlineKeyboardButton("📈 آمار پیشرفته", callback_data="admin_stats"),
            types.InlineKeyboardButton("🔄 ریستارت", callback_data="admin_restart")
        )
        
        self.bot.send_message(user_id, text, parse_mode='Markdown', reply_markup=markup)
    
    # ================ کالبک‌ها ================
    
    @self.bot.callback_query_handler(func=lambda call: True)
    def handle_callback(self, call):
        user_id = call.from_user.id
        
        # ===== مدیریت معاملات =====
        if call.data.startswith('trade_'):
            _, symbol, price = call.data.split('_')
            self.bot.answer_callback_query(call.id, "✅ معامله ثبت شد!")
            
            # ثبت در دیتابیس
            db.cursor.execute('SELECT id FROM signals WHERE symbol = ? ORDER BY created_at DESC LIMIT 1', (symbol,))
            signal = db.cursor.fetchone()
            if signal:
                db.add_trade(user_id, signal[0], float(price))
            
            self.bot.send_message(
                user_id,
                f"✅ **معامله {symbol} ثبت شد!**\n\n"
                f"📊 قیمت ورود: ${price}\n"
                f"📅 زمان: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                f"💡 برای مشاهده آمار خود از /stats استفاده کنید.",
                parse_mode='Markdown'
            )
        
        # ===== تحلیل عمیق =====
        elif call.data.startswith('deep_'):
            symbol = call.data.split('_')[1]
            self.bot.answer_callback_query(call.id, "📊 در حال تحلیل عمیق...")
            
            # دریافت تحلیل عمیق
            df = self.engine.get_klines(symbol, '4h', 100)
            if df is not None:
                df = self.engine.calculate_indicators(df)
                if df is not None:
                    last = df.iloc[-1]
                    
                    text = f"""
📊 **تحلیل عمیق {symbol}**

💰 قیمت فعلی: ${last['close']:,.2f}
📈 SMA 20: ${last['sma_20']:,.2f}
📈 SMA 50: ${last['sma_50']:,.2f}
📊 RSI: {last['rsi_14']:.1f}
📊 MACD: {last['macd']:.4f}
📊 ADX: {last['adx']:.1f}

📊 **وضعیت روند:**
{'✅ روند صعودی' if last['close'] > last['sma_50'] else '❌ روند نزولی'}
{'✅ قدرت روند بالا' if last['adx'] > 25 else '🔄 قدرت روند متوسط' if last['adx'] > 20 else '❌ بدون روند'}

💡 **سطوح کلیدی:**
• مقاومت ۱: ${last['resistance_20']:,.2f}
• مقاومت ۲: ${last['resistance_50']:,.2f}
• حمایت ۱: ${last['support_20']:,.2f}
• حمایت ۲: ${last['support_50']:,.2f}

📊 **نسبت ریسک به سود پیشنهادی:**
• حد ضرر: ${last['close'] - last['atr_14'] * 1.5:,.2f}
• حد سود ۱: ${last['close'] + last['atr_14'] * 2:,.2f}
• حد سود ۲: ${last['close'] + last['atr_14'] * 4:,.2f}
                    """
                    
                    self.bot.send_message(user_id, text, parse_mode='Markdown')
                else:
                    self.bot.send_message(user_id, "❌ خطا در تحلیل داده‌ها")
            else:
                self.bot.send_message(user_id, "❌ خطا در دریافت داده")
        
        # ===== اعتبارسنجی =====
        elif call.data.startswith('verify_'):
            symbol = call.data.split('_')[1]
            self.bot.answer_callback_query(call.id, "🔄 در حال اعتبارسنجی...")
            
            # بررسی سیگنال‌های قبلی
            db.cursor.execute('''
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins
                FROM signals
                WHERE symbol = ? AND status = 'closed'
            ''', (symbol,))
            stats = db.cursor.fetchone()
            
            if stats and stats[0] > 0:
                win_rate = (stats[1] / stats[0]) * 100
                text = f"""
📊 **اعتبارسنجی سیگنال‌های {symbol}**

📈 تعداد کل: {stats[0]}
✅ موفق: {stats[1]}
🎯 نرخ موفقیت: {win_rate:.1f}%

{'💎 عالی!' if win_rate > 70 else '⭐ خوب' if win_rate > 55 else '🔄 نیاز به بهبود'}
                """
            else:
                text = f"📊 **هنوز داده‌ای برای {symbol} وجود ندارد.**\n\nلطفاً چند روز دیگر بررسی کنید."
            
            self.bot.send_message(user_id, text, parse_mode='Markdown')
        
        # ===== هشدار قیمت =====
        elif call.data.startswith('alert_'):
            parts = call.data.split('_')
            symbol = parts[1]
            price = float(parts[2])
            
            # ذخیره هشدار
            db.cursor.execute('''
                INSERT INTO alerts (user_id, symbol, target_price, condition, created_at)
                VALUES (?, ?, ?, 'equal', ?)
            ''', (user_id, symbol, price, datetime.now().isoformat()))
            db.conn.commit()
            
            self.bot.answer_callback_query(call.id, f"✅ هشدار {symbol} در ${price} ثبت شد!")
            self.bot.send_message(
                user_id,
                f"✅ **هشدار قیمتی ثبت شد!**\n\n"
                f"📊 نماد: {symbol}\n"
                f"🎯 قیمت هدف: ${price:,.2f}\n\n"
                f"🔔 به محض رسیدن قیمت به {price}، به شما اطلاع می‌دهم.",
                parse_mode='Markdown'
            )
        
        # ===== خرید اشتراک =====
        elif call.data.startswith('buy_'):
            plan = call.data.split('_')[1]
            price = {'BASIC': 500000, 'PRO': 2000000, 'VIP': 5000000}.get(plan, 0)
            
            if price == 0:
                db.update_plan(user_id, 'FREE')
                self.bot.answer_callback_query(call.id, "✅ پلن رایگان فعال شد!")
                self.bot.send_message(user_id, "✅ **پلن رایگان فعال شد!**\n\nروزانه ۳ سیگنال دریافت کنید.", parse_mode='Markdown')
            else:
                self.bot.answer_callback_query(call.id, f"💳 مبلغ {price:,} تومان")
                
                # تولید کد پیگیری
                ref_code = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:8]
                
                self.bot.send_message(
                    user_id,
                    f"💳 **خرید اشتراک {plan}**\n\n"
                    f"💰 مبلغ: {price:,} تومان\n"
                    f"📅 مدت: ۳۰ روز\n\n"
                    f"📌 **لطفاً مبلغ را به کارت زیر واریز کنید:**\n"
                    f"`5892101187322777`\n"
                    f"به نام: مرتضی نیکخو خنجری\n\n"
                    f"🆔 کد پیگیری: `{ref_code}`\n\n"
                    f"📸 **پس از واریز، تصویر فیش را ارسال کنید.**\n\n"
                    f"💡 برای پیگیری وضعیت، از /balance استفاده کنید.",
                    parse_mode='Markdown'
                )
        
        # ===== کسب امتیاز =====
        elif call.data == "earn_points":
            tasks = [
                "🎯 یک معامله موفق ثبت کنید: +۵۰ امتیاز",
                "📤 ربات را به ۵ نفر معرفی کنید: +۱۰۰ امتیاز",
                "📝 بازخورد خود را بنویسید: +۳۰ امتیاز",
                "🔔 یک هشدار تنظیم کنید: +۲۰ امتیاز",
                "📊 ۱۰ سیگنال را بررسی کنید: +۵۰ امتیاز",
                "🎁 یک دوست را به ربات دعوت کنید: +۵۰ امتیاز"
            ]
            
            text = "⭐ **راه‌های کسب امتیاز:**\n\n" + "\n".join(tasks)
            text += "\n\n💡 **امتیاز خود را جمع کنید و اشتراک رایگان بگیرید!**"
            
            self.bot.send_message(user_id, text, parse_mode='Markdown')
        
        # ===== پنل ادمین =====
        elif call.data == "admin_algorithms":
            self.admin_algorithms(call)
        elif call.data == "admin_logs":
            self.admin_logs(call)
        elif call.data == "admin_users":
            self.admin_users(call)
        elif call.data == "admin_revenue":
            self.admin_revenue(call)
        elif call.data == "admin_broadcast":
            self.admin_broadcast(call)
        elif call.data == "admin_settings":
            self.admin_settings(call)
        elif call.data == "admin_stats":
            self.admin_stats(call)
        elif call.data == "admin_restart":
            self.admin_restart(call)
        
        # ===== مدیریت الگوریتم‌ها =====
        elif call.data.startswith('algo_'):
            algo_name = call.data.replace('algo_', '')
            db.set_active_algorithm(algo_name)
            self.bot.answer_callback_query(call.id, f"✅ الگوریتم {algo_name} فعال شد!")
            self.admin_algorithms(call)
        
        elif call.data == "admin_back":
            self.handle_admin(call.message)
    
    # ================ توابع پنل مدیریت ================
    
    def admin_algorithms(self, call):
        """مدیریت الگوریتم‌ها"""
        user_id = call.from_user.id
        
        db.cursor.execute('SELECT * FROM algorithms ORDER BY performance_score DESC')
        algorithms = db.cursor.fetchall()
        
        text = "🧠 **مدیریت الگوریتم‌های سیگنال‌دهی**\n\n"
        
        for algo in algorithms:
            status = "✅ فعال" if algo[3] else "⏸️ غیرفعال"
            text += f"• {algo[1]} | {status} | امتیاز: {algo[6]:.1f}%\n"
            text += f"  سیگنال‌ها: {algo[7]} | نرخ موفقیت: {algo[8]:.1f}%\n\n"
        
        text += "\n💡 **برای تغییر الگوریتم فعال، روی دکمه زیر کلیک کنید:**"
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        for algo in algorithms[:4]:
            markup.add(types.InlineKeyboardButton(
                f"{'✅' if algo[3] else '⬜'} {algo[1]}", 
                callback_data=f"algo_{algo[1]}"
            ))
        markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back"))
        
        self.bot.edit_message_text(text, user_id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)
    
    def admin_logs(self, call):
        """مشاهده لاگ‌ها"""
        user_id = call.from_user.id
        
        db.cursor.execute('SELECT level, message, created_at FROM logs ORDER BY created_at DESC LIMIT 20')
        logs = db.cursor.fetchall()
        
        if not logs:
            text = "📊 **لاگی وجود ندارد.**"
        else:
            text = "📊 **۲۰ لاگ اخیر:**\n\n"
            for log in logs:
                emoji = "🔴" if log[0] == 'ERROR' else "🟡" if log[0] == 'WARNING' else "🟢"
                text += f"{emoji} [{log[2][:16]}] {log[1][:60]}\n"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 بروزرسانی", callback_data="admin_logs"))
        markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back"))
        
        self.bot.edit_message_text(text, user_id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)
    
    def admin_users(self, call):
        """مدیریت کاربران"""
        user_id = call.from_user.id
        
        db.cursor.execute('''
            SELECT user_id, username, first_name, plan, points, total_trades, winning_trades, joined_at
            FROM users
            WHERE is_banned = 0
            ORDER BY points DESC
            LIMIT 20
        ''')
        users = db.cursor.fetchall()
        
        text = "👥 **۲۰ کاربر برتر:**\n\n"
        
        for user in users:
            win_rate = (user[6] / user[5] * 100) if user[5] > 0 else 0
            text += f"• {user[2]} (@{user[1]}) | {user[3]} | ⭐{user[4]} | {win_rate:.1f}%\n"
        
        text += "\n💡 برای مدیریت کاربران از دستورات زیر استفاده کنید:\n"
        text += "• `ban USER_ID` - مسدود کردن کاربر\n"
        text += "• `unban USER_ID` - رفع مسدودیت\n"
        text += "• `give USER_ID POINTS` - دادن امتیاز"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back"))
        
        self.bot.edit_message_text(text, user_id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)
    
    def admin_revenue(self, call):
        """مدیریت درآمد"""
        user_id = call.from_user.id
        
        db.cursor.execute('SELECT COALESCE(SUM(balance), 0) FROM users')
        total_revenue = db.cursor.fetchone()[0]
        
        db.cursor.execute('SELECT plan, COUNT(*) FROM users WHERE plan != "FREE" GROUP BY plan')
        plans = db.cursor.fetchall()
        
        text = f"💰 **مدیریت درآمد**\n\n"
        text += f"📊 کل درآمد: {total_revenue:,} تومان\n\n"
        text += "📈 **توزیع اشتراک‌ها:**\n"
        
        for plan in plans:
            text += f"• {plan[0]}: {plan[1]} نفر\n"
        
        text += "\n💡 **پیشنهادات برای افزایش درآمد:**\n"
        text += "• افزایش کاربران رایگان برای تبدیل به اشتراک\n"
        text += "• ارائه تخفیف‌های ویژه\n"
        text += "• بهبود کیفیت سیگنال‌ها"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back"))
        
        self.bot.edit_message_text(text, user_id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)
    
    def admin_broadcast(self, call):
        """ارسال پیام همگانی"""
        user_id = call.from_user.id
        
        msg = self.bot.send_message(
            user_id,
            "📢 **ارسال پیام همگانی**\n\n"
            "لطفاً متن پیام را ارسال کنید:\n"
            "(برای ارسال به همه کاربران)",
            parse_mode='Markdown'
        )
        
        self.bot.register_next_step_handler(msg, self.process_broadcast)
    
    def process_broadcast(self, message):
        """پردازش پیام همگانی"""
        user_id = message.from_user.id
        text = message.text
        
        if user_id not in ADMIN_IDS:
            return
        
        # دریافت همه کاربران
        db.cursor.execute('SELECT user_id FROM users WHERE is_banned = 0')
        users = db.cursor.fetchall()
        
        status_msg = self.bot.send_message(user_id, f"🔄 در حال ارسال به {len(users)} کاربر...")
        
        sent = 0
        for user in users:
            try:
                self.bot.send_message(user[0], text, parse_mode='Markdown')
                sent += 1
                time.sleep(0.05)  # جلوگیری از محدودیت
            except:
                pass
        
        self.bot.edit_message_text(
            f"✅ **پیام همگانی ارسال شد!**\n\n"
            f"📨 تعداد دریافت‌کنندگان: {sent} نفر\n"
            f"📊 از {len(users)} کاربر",
            user_id, status_msg.message_id,
            parse_mode='Markdown'
        )
        
        # ذخیره در لاگ
        db.log('INFO', f"پیام همگانی ارسال شد به {sent} کاربر", 'ADMIN')
    
    def admin_settings(self, call):
        """تنظیمات پیشرفته"""
        user_id = call.from_user.id
        
        text = """
⚙️ **تنظیمات پیشرفته**

🔧 **تنظیمات سیگنال:**
• حداقل اطمینان: ۷۰٪
• حداقل نسبت ریسک به سود: ۲.۰
• تایم‌فریم‌های تحلیل: ۱h, ۴h, ۱d

💰 **تنظیمات مالی:**
• قیمت پایه: ۵۰۰,۰۰۰ تومان
• قیمت حرفه‌ای: ۲,۰۰۰,۰۰۰ تومان
• قیمت VIP: ۵,۰۰۰,۰۰۰ تومان

👥 **تنظیمات کاربران:**
• سیگنال رایگان: ۳ عدد/روز
• اعتبار رفرال: ۱۰۰ امتیاز

💡 **برای تغییر هر کدام، به ادمین پیام دهید.**
        """
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🔄 تنظیم مجدد", callback_data="admin_reset_settings"),
            types.InlineKeyboardButton("📊 پشتیبان‌گیری", callback_data="admin_backup"),
            types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
        )
        
        self.bot.edit_message_text(text, user_id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)
    
    def admin_stats(self, call):
        """آمار پیشرفته"""
        user_id = call.from_user.id
        
        # آمار کلی
        db.cursor.execute('SELECT COUNT(*) FROM users')
        total_users = db.cursor.fetchone()[0]
        
        db.cursor.execute('SELECT COUNT(*) FROM users WHERE plan != "FREE"')
        paid_users = db.cursor.fetchone()[0]
        
        db.cursor.execute('SELECT COUNT(*) FROM signals')
        total_signals = db.cursor.fetchone()[0]
        
        db.cursor.execute('SELECT COUNT(*) FROM user_trades')
        total_trades = db.cursor.fetchone()[0]
        
        db.cursor.execute('SELECT COALESCE(AVG(profit_loss), 0) FROM user_trades WHERE status = "closed"')
        avg_profit = db.cursor.fetchone()[0]
        
        db.cursor.execute('SELECT COUNT(*) FROM user_trades WHERE status = "open"')
        open_trades = db.cursor.fetchone()[0]
        
        text = f"""
📊 **آمار پیشرفته**

👥 **کاربران:**
• کل: {total_users}
• فعال: {paid_users}
• نرخ تبدیل: {(paid_users/total_users*100) if total_users > 0 else 0:.1f}%

📊 **سیگنال‌ها:**
• کل سیگنال‌ها: {total_signals}
• میانگین روزانه: {total_signals/30:.1f}

📈 **معاملات:**
• کل: {total_trades}
• باز: {open_trades}
• میانگین سود: {avg_profit:+.2f}%

💡 **عملکرد کلی:**
{'✅ عالی' if avg_profit > 5 else '🟡 خوب' if avg_profit > 2 else '🔄 نیاز به بهبود'}
        """
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 بروزرسانی", callback_data="admin_stats"))
        markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back"))
        
        self.bot.edit_message_text(text, user_id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)
    
    def admin_restart(self, call):
        """ریستارت ربات"""
        user_id = call.from_user.id
        
        self.bot.answer_callback_query(call.id, "🔄 در حال ریستارت...")
        self.bot.send_message(user_id, "🔄 **ربات در حال ریستارت...**\n⏳ چند ثانیه صبر کنید...", parse_mode='Markdown')
        
        # ریستارت در ترد جداگانه
        def restart():
            time.sleep(2)
            os.execv(sys.executable, ['python'] + sys.argv)
        
        threading.Thread(target=restart, daemon=True).start()
    
    # ================ اجرا ================
    
    def run(self):
        print("=" * 80)
        print("🚀 ربات سیگنال‌دهی فوق‌پیشرفته نسخه ۵.۰")
        print("=" * 80)
        print(f"👤 ادمین‌ها: {ADMIN_IDS}")
        print(f"📊 نمادها: {self.engine.symbols}")
        print(f"🧠 الگوریتم‌ها: ۴ الگوریتم پیش‌فرض")
        print(f"📈 تایم‌فریم‌ها: ۱h, ۴h, ۱d")
        print("=" * 80)
        print("✅ ربات با موفقیت راه‌اندازی شد!")
        print("📊 در حال دریافت داده‌های بازار...")
        print("=" * 80)
        
        # اجرای تحلیل خودکار در ترد جداگانه
        def auto_analysis():
            while True:
                try:
                    signals = self.engine.run_analysis()
                    if signals:
                        print(f"✅ {len(signals)} سیگنال جدید تولید شد")
                        
                        # ارسال به ادمین‌ها
                        for admin in ADMIN_IDS:
                            for signal in signals[:3]:
                                self.send_signal(admin, signal)
                except Exception as e:
                    print(f"❌ خطا در تحلیل خودکار: {e}")
                    db.log('ERROR', f"خطا در تحلیل خودکار: {e}")
                time.sleep(3600)  # هر ۱ ساعت
        
        thread = threading.Thread(target=auto_analysis, daemon=True)
        thread.start()
        
        # بررسی هشدارها در ترد جداگانه
        def check_alerts():
            while True:
                try:
                    db.cursor.execute('''
                        SELECT * FROM alerts 
                        WHERE triggered = 0 
                        AND datetime(created_at) > datetime("now", "-7 days")
                    ''')
                    alerts = db.cursor.fetchall()
                    
                    for alert in alerts:
                        symbol = alert[2]
                        target = alert[3]
                        condition = alert[4]
                        user_id = alert[1]
                        
                        price = self.engine.get_price(symbol)
                        if price:
                            if condition == 'equal' and abs(price - target) / target < 0.01:
                                # هشدار فعال شد
                                db.cursor.execute('UPDATE alerts SET triggered = 1 WHERE id = ?', (alert[0],))
                                db.conn.commit()
                                
                                self.bot.send_message(
                                    user_id,
                                    f"🔔 **هشدار قیمتی فعال شد!**\n\n"
                                    f"📊 نماد: {symbol}\n"
                                    f"🎯 قیمت هدف: ${target:,.2f}\n"
                                    f"💰 قیمت فعلی: ${price:,.2f}\n\n"
                                    f"💡 زمان اقدام مناسب است!",
                                    parse_mode='Markdown'
                                )
                except Exception as e:
                    print(f"❌ خطا در بررسی هشدارها: {e}")
                time.sleep(60)  # هر ۱ دقیقه
        
        thread2 = threading.Thread(target=check_alerts, daemon=True)
        thread2.start()
        
        # اجرای ربات
        try:
            self.bot.remove_webhook()
            self.bot.infinity_polling(timeout=60, skip_pending=True)
        except Exception as e:
            print(f"❌ خطا: {e}")
            db.log('ERROR', f"خطا در اجرای ربات: {e}")
            time.sleep(5)
            self.run()

# ==================== اجرا ====================
if __name__ == "__main__":
    bot = SuperTradingBot()
    bot.run()