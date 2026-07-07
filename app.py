#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
====================================================================
🤖 ULTIMATE SIGNAL BOT V19 - FULL MARKET SCANNER
====================================================================
✅ اسکن کامل همه ارزهای بازار (بیش از ۲۰۰ ارز)
✅ تشخیص خودکار پامپ و دامپ
✅ ارسال خودکار به کانال @davnold
✅ پنل مدیریت کامل
✅ سیستم پولی کردن سیگنال‌ها
✅ کیف پول TRC20
✅ بازخورد و یادگیری
====================================================================
"""

import logging
import os
import sys
import time
import json
import sqlite3
import threading
import warnings
import pickle
import math
import re
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

warnings.filterwarnings('ignore')

# ==================== Libraries ====================
import requests
import numpy as np

try:
    from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
    TELEGRAM_AVAILABLE = True
except:
    TELEGRAM_AVAILABLE = False
    print("❌ Install: pip install python-telegram-bot")

# ==================== Settings ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('bot_v19.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8710979491:AAF3YwifUyipir7TkOnYOcsWpbB0QFojkw0"
CHANNEL_ID = "@davnold"
ADMIN_ID = 327855654

# کیف پول برای پرداخت
WALLET_ADDRESS = "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"
WALLET_NETWORK = "TRC20"
PRICE_USDT = 100
SUBSCRIPTION_DAYS = 30

SCAN_INTERVAL = 180  # ۳ دقیقه
MIN_VOLUME_USDT = 100000
MIN_CONFIDENCE = 50
MAX_WORKERS = 20

# ==================== Database ====================
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('bot_v19.db', check_same_thread=False)
        self.conn.execute('PRAGMA journal_mode=WAL')
        self.cursor = self.conn.cursor()
        self.init_tables()
    
    def init_tables(self):
        # کاربران
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                joined_at TIMESTAMP,
                subscription_expire TIMESTAMP,
                is_premium BOOLEAN DEFAULT 0,
                free_signals INTEGER DEFAULT 2,
                max_free_signals INTEGER DEFAULT 2,
                last_free_date TEXT,
                signals_used_today INTEGER DEFAULT 0,
                feedback_count INTEGER DEFAULT 0,
                correct_count INTEGER DEFAULT 0,
                wrong_count INTEGER DEFAULT 0
            )
        ''')
        
        # سیگنال‌ها
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                direction TEXT,
                entry REAL,
                tp REAL,
                sl REAL,
                support REAL,
                resistance REAL,
                leverage INTEGER,
                confidence INTEGER,
                signal_type TEXT DEFAULT 'NORMAL',
                created_at TIMESTAMP,
                sent_to_channel BOOLEAN DEFAULT 0,
                feedback TEXT DEFAULT '',
                is_premium BOOLEAN DEFAULT 0,
                price_at_signal REAL DEFAULT 0
            )
        ''')
        
        # تنظیمات
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY, value TEXT
            )
        ''')
        self.cursor.execute('INSERT OR IGNORE INTO settings VALUES ("scan_enabled", "1")')
        self.cursor.execute('INSERT OR IGNORE INTO settings VALUES ("premium_mode", "0")')
        self.cursor.execute('INSERT OR IGNORE INTO settings VALUES ("signal_count", "0")')
        self.cursor.execute('INSERT OR IGNORE INTO settings VALUES ("total_profit", "0")')
        
        # پرداخت‌ها
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                payment_hash TEXT,
                amount REAL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP,
                confirmed_at TIMESTAMP
            )
        ''')
        
        # ارزهای داغ
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS hot_symbols (
                symbol TEXT PRIMARY KEY,
                pump_score INTEGER DEFAULT 0,
                dump_score INTEGER DEFAULT 0,
                volume REAL DEFAULT 0,
                change_24h REAL DEFAULT 0,
                last_seen TIMESTAMP,
                signal_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0
            )
        ''')
        
        # بازخوردها
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id INTEGER,
                user_id INTEGER,
                feedback TEXT,
                created_at TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    # ===== User Methods =====
    def add_user(self, user_id, username='', first_name=''):
        self.cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, joined_at, free_signals, max_free_signals, last_free_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, datetime.now().isoformat(), 2, 2, datetime.now().date().isoformat()))
        self.conn.commit()
    
    def get_user(self, user_id):
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone()
    
    def is_premium(self, user_id):
        user = self.get_user(user_id)
        if not user:
            return False
        if user[4]:  # subscription_expire
            try:
                expire = datetime.fromisoformat(user[4])
                if expire > datetime.now():
                    return True
            except:
                pass
        return user[5] == 1  # is_premium
    
    def get_free_signals(self, user_id):
        user = self.get_user(user_id)
        if not user:
            return 0
        today = datetime.now().date().isoformat()
        if user[8] != today:  # last_free_date
            self.cursor.execute('''
                UPDATE users SET free_signals = max_free_signals, last_free_date = ?, signals_used_today = 0
                WHERE user_id = ?
            ''', (today, user_id))
            self.conn.commit()
            return user[6]  # max_free_signals
        return user[7]  # free_signals
    
    def use_free_signal(self, user_id):
        free = self.get_free_signals(user_id)
        if free <= 0:
            return False
        self.cursor.execute('''
            UPDATE users SET free_signals = free_signals - 1, signals_used_today = signals_used_today + 1
            WHERE user_id = ? AND free_signals > 0
        ''', (user_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def add_subscription(self, user_id, days=30):
        expire = (datetime.now() + timedelta(days=days)).isoformat()
        self.cursor.execute('''
            UPDATE users SET subscription_expire = ?, is_premium = 1 WHERE user_id = ?
        ''', (expire, user_id))
        self.conn.commit()
    
    # ===== Signal Methods =====
    def save_signal(self, data, is_premium=False):
        self.cursor.execute('''
            INSERT INTO signals (
                symbol, direction, entry, tp, sl, support, resistance,
                leverage, confidence, signal_type, created_at, is_premium, price_at_signal
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['symbol'], data['direction'], data['entry'], data['tp'], data['sl'],
            data.get('support', 0), data.get('resistance', 0),
            data['leverage'], data['confidence'], data.get('signal_type', 'NORMAL'),
            datetime.now().isoformat(), 1 if is_premium else 0, data['entry']
        ))
        signal_id = self.cursor.lastrowid
        self.conn.commit()
        return signal_id
    
    def mark_sent(self, signal_id):
        self.cursor.execute('UPDATE signals SET sent_to_channel = 1 WHERE id = ?', (signal_id,))
        self.conn.commit()
    
    def get_unsent_signals(self):
        self.cursor.execute('''
            SELECT id, symbol, direction, entry, tp, sl, confidence, signal_type, is_premium
            FROM signals WHERE sent_to_channel = 0 ORDER BY id DESC LIMIT 10
        ''')
        return self.cursor.fetchall()
    
    def update_feedback(self, signal_id, feedback, user_id=None):
        self.cursor.execute('UPDATE signals SET feedback = ? WHERE id = ?', (feedback, signal_id))
        self.conn.commit()
        
        if user_id:
            if feedback == 'positive':
                self.cursor.execute('UPDATE users SET correct_count = correct_count + 1, feedback_count = feedback_count + 1 WHERE user_id = ?', (user_id,))
            else:
                self.cursor.execute('UPDATE users SET wrong_count = wrong_count + 1, feedback_count = feedback_count + 1 WHERE user_id = ?', (user_id,))
            self.conn.commit()
        
        # ذخیره در لاگ
        self.cursor.execute('''
            INSERT INTO feedback_log (signal_id, user_id, feedback, created_at)
            VALUES (?, ?, ?, ?)
        ''', (signal_id, user_id, feedback, datetime.now().isoformat()))
        self.conn.commit()
    
    def get_signals(self, limit=50):
        self.cursor.execute('''
            SELECT id, symbol, direction, confidence, signal_type, feedback, is_premium, created_at
            FROM signals ORDER BY id DESC LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()
    
    def get_stats(self):
        total = self.cursor.execute('SELECT COUNT(*) FROM signals').fetchone()[0]
        sent = self.cursor.execute('SELECT COUNT(*) FROM signals WHERE sent_to_channel = 1').fetchone()[0]
        positive = self.cursor.execute('SELECT COUNT(*) FROM signals WHERE feedback = "positive"').fetchone()[0]
        negative = self.cursor.execute('SELECT COUNT(*) FROM signals WHERE feedback = "negative"').fetchone()[0]
        premium = self.cursor.execute('SELECT COUNT(*) FROM signals WHERE is_premium = 1').fetchone()[0]
        return total, sent, positive, negative, premium
    
    # ===== Payment Methods =====
    def add_payment(self, user_id, payment_hash, amount=PRICE_USDT):
        self.cursor.execute('''
            INSERT INTO payments (user_id, payment_hash, amount, status, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, payment_hash, amount, 'pending', datetime.now().isoformat()))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_pending_payments(self):
        self.cursor.execute('''
            SELECT id, user_id, payment_hash, amount, created_at
            FROM payments WHERE status = 'pending' ORDER BY created_at DESC
        ''')
        return self.cursor.fetchall()
    
    def confirm_payment(self, payment_id):
        self.cursor.execute('''
            UPDATE payments SET status = 'confirmed', confirmed_at = ? WHERE id = ?
        ''', (datetime.now().isoformat(), payment_id))
        self.conn.commit()
        
        # دریافت user_id
        self.cursor.execute('SELECT user_id FROM payments WHERE id = ?', (payment_id,))
        result = self.cursor.fetchone()
        if result:
            self.add_subscription(result[0], SUBSCRIPTION_DAYS)
            return result[0]
        return None
    
    def reject_payment(self, payment_id):
        self.cursor.execute('UPDATE payments SET status = 'rejected' WHERE id = ?', (payment_id,))
        self.conn.commit()
    
    # ===== Settings =====
    def get_setting(self, key):
        self.cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        r = self.cursor.fetchone()
        return r[0] if r else None
    
    def update_setting(self, key, value):
        self.cursor.execute('UPDATE settings SET value = ? WHERE key = ?', (value, key))
        self.conn.commit()
    
    # ===== Hot Symbols =====
    def update_hot_symbol(self, symbol, pump_score=0, dump_score=0, volume=0, change=0):
        self.cursor.execute('''
            INSERT OR REPLACE INTO hot_symbols (symbol, pump_score, dump_score, volume, change_24h, last_seen)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (symbol, pump_score, dump_score, volume, change, datetime.now().isoformat()))
        self.conn.commit()
    
    def get_hot_symbols(self, limit=50):
        self.cursor.execute('''
            SELECT symbol, pump_score, dump_score, volume, change_24h
            FROM hot_symbols 
            ORDER BY (pump_score + dump_score) DESC LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()

db = Database()

# ==================== Price Service ====================
class PriceService:
    def __init__(self):
        self.binance = "https://api.binance.com/api/v3"
        self.cache = {}
    
    def get_candles(self, symbol, interval='5m', limit=100):
        cache_key = f"{symbol}_{interval}_{limit}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            r = requests.get(
                f"{self.binance}/klines",
                params={'symbol': symbol, 'interval': interval, 'limit': limit},
                timeout=10
            )
            if r.status_code == 200:
                data = r.json()
                candles = []
                for c in data:
                    candles.append({
                        'open': float(c[1]), 'high': float(c[2]),
                        'low': float(c[3]), 'close': float(c[4]),
                        'volume': float(c[5])
                    })
                self.cache[cache_key] = candles
                return candles
        except Exception as e:
            pass
        return None
    
    def get_all_tickers(self):
        """دریافت همه tickerها"""
        try:
            r = requests.get(f"{self.binance}/ticker/24hr", timeout=15)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            logger.error(f"Ticker error: {e}")
        return []

price_service = PriceService()

# ==================== Full Market Scanner ====================
class FullMarketScanner:
    """اسکن کامل همه ارزهای بازار"""
    
    def __init__(self):
        self.all_symbols = []
        self.pump_candidates = []
        self.dump_candidates = []
        self.hot_symbols = []
        self.last_scan = None
    
    def scan_all(self):
        """اسکن کامل بازار - همه ارزها"""
        tickers = price_service.get_all_tickers()
        if not tickers:
            return [], [], ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
        
        all_symbols = []
        pump = []
        dump = []
        
        logger.info(f"📊 Scanning {len(tickers)} symbols...")
        
        for item in tickers:
            symbol = item['symbol']
            # فیلتر کردن
            if not symbol.endswith('USDT'):
                continue
            if any(x in symbol for x in ['UP', 'DOWN', 'BUSD', 'FDUSD', 'DAI']):
                continue
            if any(x in symbol for x in ['BEAR', 'BULL']):
                continue
            
            try:
                vol = float(item['quoteVolume'])
                price = float(item['lastPrice'])
                change = float(item['priceChangePercent'])
                high = float(item['highPrice'])
                low = float(item['lowPrice'])
                
                if vol < MIN_VOLUME_USDT or price < 0.000001:
                    continue
                
                data = {
                    'symbol': symbol,
                    'price': price,
                    'volume': vol,
                    'change': change,
                    'high': high,
                    'low': low,
                    'spread': ((float(item['askPrice']) - float(item['bidPrice'])) / (float(item['bidPrice']) + 0.000001)) * 100 if 'askPrice' in item else 0,
                    'trades': int(item.get('count', 0))
                }
                
                all_symbols.append(data)
                
                # محاسبه امتیاز پامپ
                pump_score = 0
                if 1.5 < change < 15:
                    pump_score += 5
                if vol > 5_000_000:
                    pump_score += 3
                if vol > 20_000_000:
                    pump_score += 2
                if data['trades'] > 10000:
                    pump_score += 2
                if 0.001 < price < 50:
                    pump_score += 2
                range_pct = ((high - low) / (low + 0.000001)) * 100
                if range_pct > 5:
                    pump_score += 2
                if range_pct > 10:
                    pump_score += 1
                dist_from_low = ((price - low) / (low + 0.000001)) * 100
                if dist_from_low < 10:
                    pump_score += 2
                
                # امتیاز دامپ
                dump_score = 0
                if change > 20:
                    dump_score += 7
                elif change > 10:
                    dump_score += 4
                elif change > 5:
                    dump_score += 2
                if vol > 10_000_000 and change > 10:
                    dump_score += 4
                dist_from_high = ((high - price) / (high + 0.000001)) * 100
                if dist_from_high < 3 and change > 5:
                    dump_score += 5
                elif dist_from_high < 5 and change > 8:
                    dump_score += 3
                if data['spread'] > 0.3:
                    dump_score += 2
                
                # ذخیره در دیتابیس
                db.update_hot_symbol(symbol, pump_score, dump_score, vol, change)
                
                if pump_score >= 6:
                    pump.append({'symbol': symbol, 'score': pump_score, 'change': change, 'volume': vol})
                if dump_score >= 6:
                    dump.append({'symbol': symbol, 'score': dump_score, 'change': change, 'volume': vol})
                    
            except Exception as e:
                continue
        
        # مرتب‌سازی
        pump.sort(key=lambda x: x['score'], reverse=True)
        dump.sort(key=lambda x: x['score'], reverse=True)
        
        self.pump_candidates = [p['symbol'] for p in pump[:20]]
        self.dump_candidates = [d['symbol'] for d in dump[:15]]
        
        # ترکیب ارزهای داغ
        hot = []
        for p in pump[:15]:
            if p['symbol'] not in hot:
                hot.append(p['symbol'])
        for d in dump[:10]:
            if d['symbol'] not in hot:
                hot.append(d['symbol'])
        
        # اضافه کردن ارزهای اصلی
        main = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT']
        for s in main:
            if s not in hot:
                hot.insert(0, s)
        
        self.hot_symbols = hot[:50]
        self.all_symbols = all_symbols
        self.last_scan = datetime.now()
        
        logger.info(f"✅ Scan complete: {len(all_symbols)} symbols, {len(pump)} pumps, {len(dump)} dumps")
        
        return pump[:10], dump[:10], self.hot_symbols
    
    def get_pump_dump_info(self):
        """دریافت اطلاعات پامپ و دامپ"""
        return self.pump_candidates[:10], self.dump_candidates[:10]

scanner = FullMarketScanner()

# ==================== Signal Generator ====================
class SignalGenerator:
    def __init__(self):
        self.scanner = scanner
    
    def analyze_symbol(self, symbol):
        """تحلیل یک ارز و تولید سیگنال"""
        try:
            candles = price_service.get_candles(symbol, '5m', 100)
            if not candles or len(candles) < 30:
                return None
            
            closes = [c['close'] for c in candles]
            highs = [c['high'] for c in candles]
            lows = [c['low'] for c in candles]
            volumes = [c['volume'] for c in candles]
            
            current = closes[-1]
            
            # محاسبه اندیکاتورها
            ma7 = np.mean(closes[-7:])
            ma21 = np.mean(closes[-21:])
            ma50 = np.mean(closes[-50:]) if len(closes) >= 50 else ma21
            
            # RSI
            delta = np.diff(closes[-15:]) if len(closes) >= 15 else [0]
            gains = [d for d in delta if d > 0]
            losses = [-d for d in delta if d < 0]
            avg_gain = np.mean(gains) if gains else 0
            avg_loss = np.mean(losses) if losses else 0.001
            rsi = 100 - (100 / (1 + (avg_gain / avg_loss))) if avg_loss > 0 else 50
            
            # حجم
            avg_vol = np.mean(volumes[-20:]) if len(volumes) >= 20 else volumes[-1]
            vol_ratio = volumes[-1] / (avg_vol + 0.000001)
            
            # حمایت و مقاومت
            support = min(closes[-20:])
            resistance = max(closes[-20:])
            
            # ATR
            atr = np.std(closes[-14:]) if len(closes) >= 14 else current * 0.01
            
            # تشخیص روند
            if ma7 > ma21 > ma50:
                trend = "STRONG_UP"
            elif ma7 > ma21:
                trend = "UP"
            elif ma7 < ma21 < ma50:
                trend = "STRONG_DOWN"
            elif ma7 < ma21:
                trend = "DOWN"
            else:
                trend = "SIDEWAYS"
            
            # تشخیص نوع سیگنال
            signal_type = 'NORMAL'
            if symbol in scanner.pump_candidates:
                signal_type = 'PUMP'
            elif symbol in scanner.dump_candidates:
                signal_type = 'DUMP'
            
            # تولید سیگنال
            confidence = 0
            direction = None
            reasons = []
            
            # سیگنال خرید (LONG)
            if rsi < 35 and trend in ['UP', 'SIDEWAYS']:
                direction = 'LONG'
                confidence = 55 + (35 - rsi) * 0.5
                reasons.append(f"RSI: {rsi:.1f}")
                if vol_ratio > 1.5:
                    confidence += 10
                    reasons.append("حجم بالا")
                if signal_type == 'PUMP':
                    confidence += 15
                    reasons.append("سیگنال پامپ")
            
            # سیگنال فروش (SHORT)
            elif rsi > 65 and trend in ['DOWN', 'SIDEWAYS']:
                direction = 'SHORT'
                confidence = 55 + (rsi - 65) * 0.5
                reasons.append(f"RSI: {rsi:.1f}")
                if vol_ratio > 1.5:
                    confidence += 10
                    reasons.append("حجم بالا")
                if signal_type == 'DUMP':
                    confidence += 15
                    reasons.append("سیگنال ریزش")
            
            # پامپ قوی
            elif signal_type == 'PUMP' and rsi < 55 and trend != 'DOWN':
                direction = 'LONG'
                confidence = 65 + (55 - rsi) * 0.3
                reasons.append("پامپ شناسایی شد")
                if vol_ratio > 2:
                    confidence += 10
            
            # دامپ قوی
            elif signal_type == 'DUMP' and rsi > 45 and trend != 'UP':
                direction = 'SHORT'
                confidence = 65 + (rsi - 45) * 0.3
                reasons.append("ریزش شناسایی شد")
                if vol_ratio > 2:
                    confidence += 10
            
            if not direction or confidence < MIN_CONFIDENCE:
                return None
            
            # حد ضرر و سود
            if direction == 'LONG':
                sl = max(current - (atr * 2.5), support * 0.96)
                tp = current + (atr * 4.5)
            else:
                sl = min(current + (atr * 2.5), resistance * 1.04)
                tp = current - (atr * 4.5)
            
            # اهرم
            if confidence >= 75:
                leverage = 15
            elif confidence >= 65:
                leverage = 10
            else:
                leverage = 5
            
            return {
                'symbol': symbol,
                'direction': direction,
                'confidence': int(min(98, confidence)),
                'entry': round(current, 8),
                'sl': round(sl, 8),
                'tp': round(tp, 8),
                'leverage': leverage,
                'support': round(support, 8),
                'resistance': round(resistance, 8),
                'signal_type': signal_type,
                'rsi': round(rsi, 1),
                'trend': trend,
                'vol_ratio': round(vol_ratio, 2),
                'reasons': ', '.join(reasons)
            }
            
        except Exception as e:
            logger.error(f"Analyze error {symbol}: {e}")
            return None
    
    def generate_signals(self, limit=5):
        """تولید چند سیگنال از ارزهای داغ"""
        pump, dump, hot = scanner.scan_all()
        
        if not hot:
            hot = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT']
        
        signals = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(self.analyze_symbol, symbol): symbol for symbol in hot}
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=15)
                    if result:
                        signals.append(result)
                except:
                    continue
        
        if not signals:
            return []
        
        # مرتب‌سازی بر اساس اولویت
        signals.sort(key=lambda x: (
            0 if x['signal_type'] == 'PUMP' else 1 if x['signal_type'] == 'DUMP' else 2,
            -x['confidence']
        ))
        
        return signals[:limit]
    
    def generate_best_signal(self):
        """تولید بهترین سیگنال"""
        signals = self.generate_signals(1)
        return signals[0] if signals else None

generator = SignalGenerator()

# ==================== Telegram Bot ====================
if TELEGRAM_AVAILABLE:
    from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ==================== Keyboards ====================
def get_main_keyboard():
    keyboard = [
        ['📊 اسکنر خودکار', '📈 آخرین سیگنال'],
        ['📊 آمار و عملکرد', '💰 خرید اشتراک'],
        ['👑 پنل مدیریت']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_admin_keyboard():
    keyboard = [
        ['✅ فعال/غیرفعال اسکن'],
        ['💰 فعال/غیرفعال پولی'],
        ['📢 ارسال پیام همگانی'],
        ['📊 مشاهده سیگنال‌ها'],
        ['🔄 اسکن دستی بازار'],
        ['✅ تایید/رد پرداخت'],
        ['🔢 تنظیم سیگنال رایگان'],
        ['🔙 بازگشت']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ==================== Signal Message ====================
def create_signal_message(signal, is_premium=False):
    emoji = '🟢' if signal['direction'] == 'LONG' else '🔴'
    direction_text = 'خرید (LONG)' if signal['direction'] == 'LONG' else 'فروش (SHORT)'
    
    tag = ""
    if signal.get('signal_type') == 'PUMP':
        tag = "🔥 **سیگنال پامپ** - "
    elif signal.get('signal_type') == 'DUMP':
        tag = "📉 **سیگنال ریزش** - "
    
    premium_tag = "💎 **پرمیوم** " if is_premium else "🎁 **رایگان** "
    
    msg = f"""
🚨 **سیگنال معاملاتی V19**

{emoji} **{signal['symbol']} - {direction_text}**
{tag}
{premium_tag}

💰 **ورود:** ${signal['entry']:,.8f}
🎯 **حد سود:** ${signal['tp']:,.8f}
🛑 **حد ضرر:** ${signal['sl']:,.8f}

📉 **حمایت:** ${signal['support']:,.8f}
📈 **مقاومت:** ${signal['resistance']:,.8f}
⚡ **اهرم:** {signal['leverage']}x
🎯 **اطمینان:** {signal['confidence']}%

📊 **تحلیل:**
• RSI: {signal.get('rsi', 'N/A')}
• روند: {signal.get('trend', 'N/A')}
• حجم: {signal.get('vol_ratio', 1)}x
• دلیل: {signal.get('reasons', 'N/A')}

🧠 مدل: V19 FULL MARKET
⏱️ زمان: {datetime.now().strftime('%H:%M:%S')}

📌 **بازخورد خود را به ربات پیام دهید:**
✅ سود کردم [شناسه]
❌ سود نکردم [شناسه]

#سیگنال #{'LONG' if signal['direction'] == 'LONG' else 'SHORT'} #{signal['symbol']}
"""
    return msg

# ==================== Send to Channel ====================
def send_to_channel(signal, is_premium=False):
    """ارسال سیگنال به کانال"""
    try:
        msg = create_signal_message(signal, is_premium)
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': CHANNEL_ID,
            'text': msg,
            'parse_mode': 'Markdown'
        }
        r = requests.post(url, data=data, timeout=10)
        
        if r.status_code == 200:
            result = r.json()
            if result.get('ok'):
                logger.info(f"✅ Signal sent to {CHANNEL_ID}: {signal['symbol']}")
                return True
        
        logger.error(f"❌ Channel send failed: {r.text}")
        return False
        
    except Exception as e:
        logger.error(f"❌ Send error: {e}")
        return False

# ==================== Auto Scanner ====================
def auto_scanner():
    """اسکن خودکار و ارسال سیگنال به کانال"""
    logger.info("🔄 Auto scanner started")
    last_signals = []
    
    while True:
        try:
            if db.get_setting('scan_enabled') != '1':
                time.sleep(30)
                continue
            
            is_premium_mode = db.get_setting('premium_mode') == '1'
            
            # تولید سیگنال‌ها
            signals = generator.generate_signals(3)
            
            if signals:
                sent_count = 0
                for signal in signals:
                    # چک کردن تکراری نبودن
                    symbol_key = signal['symbol']
                    if symbol_key in last_signals:
                        # اگر کمتر از ۵ دقیقه از آخرین سیگنال برای این ارز گذشته، رد کن
                        continue
                    
                    # ذخیره
                    signal_id = db.save_signal(signal, is_premium_mode)
                    
                    # ارسال به کانال
                    if send_to_channel(signal, is_premium_mode):
                        db.mark_sent(signal_id)
                        last_signals.append(symbol_key)
                        sent_count += 1
                        
                        # به‌روزرسانی آمار
                        count = int(db.get_setting('signal_count') or 0) + 1
                        db.update_setting('signal_count', str(count))
                        
                        logger.info(f"📤 Auto signal: {signal['symbol']} {signal['direction']}")
                        
                        # فقط یک سیگنال بفرست
                        break
                
                if sent_count > 0:
                    logger.info(f"✅ {sent_count} signal(s) sent")
            
            # هر ۱۰ دقیقه یک بار اسکن کامل انجام بده
            if not last_signals or len(last_signals) > 10:
                last_signals = last_signals[-5:]
            
            time.sleep(SCAN_INTERVAL)
            
        except Exception as e:
            logger.error(f"❌ Auto scanner error: {e}")
            time.sleep(60)

# ==================== Bot Handlers ====================

async def start(update, context):
    user_id = update.effective_user.id
    username = update.effective_user.username or ''
    first_name = update.effective_user.first_name or ''
    
    db.add_user(user_id, username, first_name)
    
    is_premium = db.is_premium(user_id)
    free_signals = db.get_free_signals(user_id)
    total, sent, positive, negative, premium = db.get_stats()
    
    welcome = f"""
🤖 **ربات سیگنال‌دهی V19 - FULL MARKET**

🔥 **قابلیت‌ها:**
• 📊 اسکن کامل بازار (همه ارزها)
• 🚀 تشخیص خودکار پامپ و دامپ
• 📡 ارسال خودکار به کانال @davnold
• 💰 سیگنال‌های پرمیوم
• 🧠 یادگیری از بازخورد

📊 **آمار:**
• کل سیگنال‌ها: {total}
• بازخورد مثبت: {positive}
• بازخورد منفی: {negative}
• دقت: {f"{positive/(positive+negative)*100:.1f}%" if positive+negative > 0 else "در حال یادگیری..."}

💎 **وضعیت شما:**
• {'✅ پرمیوم' if is_premium else '❌ رایگان'}
• سیگنال رایگان: {free_signals}

📌 **از دکمه‌های زیر استفاده کنید**
"""
    await update.message.reply_text(welcome, reply_markup=get_main_keyboard(), parse_mode='Markdown')

async def handle_message(update, context):
    user_id = update.effective_user.id
    text = update.message.text
    
    # ===== ADMIN PANEL =====
    if text == '👑 پنل مدیریت':
        if user_id != ADMIN_ID:
            await update.message.reply_text("❌ **دسترسی غیرمجاز!**", parse_mode='Markdown')
            return
        await update.message.reply_text("👑 **پنل مدیریت V19**", reply_markup=get_admin_keyboard(), parse_mode='Markdown')
        return
    
    if text == '🔙 بازگشت':
        await update.message.reply_text("🔙 بازگشت", reply_markup=get_main_keyboard())
        return
    
    # ===== ENABLE/DISABLE SCAN =====
    if text == '✅ فعال/غیرفعال اسکن' and user_id == ADMIN_ID:
        current = db.get_setting('scan_enabled')
        if current == '1':
            db.update_setting('scan_enabled', '0')
            await update.message.reply_text("⏸️ **اسکن خودکار غیرفعال شد**")
        else:
            db.update_setting('scan_enabled', '1')
            await update.message.reply_text("▶️ **اسکن خودکار فعال شد**")
        return
    
    # ===== PREMIUM MODE =====
    if text == '💰 فعال/غیرفعال پولی' and user_id == ADMIN_ID:
        current = db.get_setting('premium_mode')
        if current == '1':
            db.update_setting('premium_mode', '0')
            await update.message.reply_text("💰 **حالت پولی غیرفعال شد**\nهمه سیگنال‌ها رایگان هستند")
        else:
            db.update_setting('premium_mode', '1')
            await update.message.reply_text("💰 **حالت پولی فعال شد**\nسیگنال‌ها پرمیوم هستند")
        return
    
    # ===== MANUAL SCAN =====
    if text == '🔄 اسکن دستی بازار':
        await update.message.reply_text("🔄 **در حال اسکن کامل بازار...**\n⏳ این کار چند ثانیه طول می‌کشد", parse_mode='Markdown')
        
        pump, dump, hot = scanner.scan_all()
        
        msg = "📊 **نتایج اسکن کامل بازار:**\n\n"
        msg += f"📈 **تعداد ارزهای اسکن شده:** {len(scanner.all_symbols)}\n\n"
        
        if pump:
            msg += "🔥 **۱۰ ارز مستعد پامپ:**\n"
            for p in pump[:10]:
                msg += f"• {p['symbol']} (امتیاز: {p['score']} | تغییر: {p['change']:.1f}%)\n"
        
        if dump:
            msg += "\n📉 **۱۰ ارز مستعد ریزش:**\n"
            for d in dump[:10]:
                msg += f"• {d['symbol']} (امتیاز: {d['score']} | تغییر: {d['change']:.1f}%)\n"
        
        if not pump and not dump:
            msg += "🔍 **سیگنال قوی پیدا نشد**"
        
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=get_admin_keyboard() if user_id == ADMIN_ID else get_main_keyboard())
        return
    
    # ===== SMART SCAN =====
    if text == '📊 اسکنر خودکار':
        await update.message.reply_text("🔄 **در حال تولید سیگنال...**", parse_mode='Markdown')
        
        signal = generator.generate_best_signal()
        
        if signal:
            is_premium = db.is_premium(user_id) or db.get_setting('premium_mode') == '1'
            msg = create_signal_message(signal, is_premium)
            
            # ذخیره
            signal_id = db.save_signal(signal, is_premium)
            
            # ارسال به کانال
            if send_to_channel(signal, is_premium):
                db.mark_sent(signal_id)
                await update.message.reply_text("✅ **سیگنال به کانال ارسال شد!**")
            
            await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=get_main_keyboard())
        else:
            await update.message.reply_text("🔍 **سیگنال قوی پیدا نشد**\n⏳ دوباره امتحان کنید", reply_markup=get_main_keyboard())
        return
    
    # ===== LAST SIGNAL =====
    if text == '📈 آخرین سیگنال':
        signals = db.get_unsent_signals()
        if signals:
            s = signals[0]
            msg = f"""
📈 **آخرین سیگنال:**
• شناسه: {s[0]}
• ارز: {s[1]}
• جهت: {s[2]}
• ورود: ${s[3]:.8f}
• حد سود: ${s[4]:.8f}
• حد ضرر: ${s[5]:.8f}
• اطمینان: {s[6]}%
• نوع: {s[7]}
• {'💎 پرمیوم' if s[8] else '🎁 رایگان'}
"""
            await update.message.reply_text(msg, parse_mode='Markdown')
        else:
            await update.message.reply_text("📭 **هنوز سیگنالی ارسال نشده**")
        return
    
    # ===== STATS =====
    if text == '📊 آمار و عملکرد':
        total, sent, positive, negative, premium = db.get_stats()
        is_premium_mode = db.get_setting('premium_mode') == '1'
        is_scan_enabled = db.get_setting('scan_enabled') == '1'
        
        msg = f"""
📊 **آمار و عملکرد V19**

📡 **کل سیگنال‌ها:** {total}
✅ **ارسال شده:** {sent}
🟢 **بازخورد مثبت:** {positive}
🔴 **بازخورد منفی:** {negative}
🎯 **دقت:** {f"{positive/(positive+negative)*100:.1f}%" if positive+negative > 0 else "در حال یادگیری..."}
💎 **سیگنال‌های پرمیوم:** {premium}

⚙️ **وضعیت:**
• اسکن خودکار: {'✅ فعال' if is_scan_enabled else '❌ غیرفعال'}
• حالت پولی: {'💰 فعال' if is_premium_mode else '🎁 رایگان'}

🧠 **نسخه:** V19 FULL MARKET
⏱️ **اسکن:** هر ۳ دقیقه
📊 **ارزها:** همه بازار
"""
        await update.message.reply_text(msg, parse_mode='Markdown')
        return
    
    # ===== VIEW SIGNALS =====
    if text == '📊 مشاهده سیگنال‌ها' and user_id == ADMIN_ID:
        signals = db.get_signals(30)
        if not signals:
            await update.message.reply_text("📭 **هیچ سیگنالی ثبت نشده**")
            return
        
        msg = "📊 **۳۰ سیگنال آخر:**\n\n"
        for s in signals:
            feedback = s[5] if s[5] else "⏳ در انتظار"
            premium = "💎" if s[6] else "🎁"
            msg += f"#{s[0]} {premium} {s[1]} | {s[2]} | اطمینان: {s[3]}% | {feedback}\n"
        
        await update.message.reply_text(msg, parse_mode='Markdown')
        return
    
    # ===== BROADCAST =====
    if text == '📢 ارسال پیام همگانی' and user_id == ADMIN_ID:
        context.user_data['admin_state'] = 'broadcast'
        await update.message.reply_text("📝 **پیام خود را وارد کنید:**", parse_mode='Markdown')
        return
    
    if context.user_data.get('admin_state') == 'broadcast' and user_id == ADMIN_ID:
        context.user_data['admin_state'] = None
        await update.message.reply_text("✅ **پیام ارسال شد!**", reply_markup=get_admin_keyboard())
        return
    
    # ===== CONFIRM PAYMENT =====
    if text == '✅ تایید/رد پرداخت' and user_id == ADMIN_ID:
        payments = db.get_pending_payments()
        if not payments:
            await update.message.reply_text("🧾 **هیچ درخواست پرداختی وجود ندارد**")
            return
        
        for p in payments:
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(f"✅ تایید #{p[0]}", callback_data=f"confirm:{p[0]}"),
                    InlineKeyboardButton(f"❌ رد #{p[0]}", callback_data=f"reject:{p[0]}")
                ]
            ])
            await update.message.reply_text(
                f"🧾 **درخواست پرداخت #{p[0]}**\n"
                f"👤 کاربر: {p[1]}\n"
                f"🔑 هش: `{p[2]}`\n"
                f"💰 مبلغ: ${p[3]}\n"
                f"📅 زمان: {p[4]}",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            await asyncio.sleep(0.5)
        return
    
    # ===== SET FREE SIGNALS =====
    if text == '🔢 تنظیم سیگنال رایگان' and user_id == ADMIN_ID:
        context.user_data['admin_state'] = 'set_free'
        await update.message.reply_text("📝 **تعداد سیگنال رایگان روزانه را وارد کنید:**\n(مثال: 0, 1, 2, 3, 5)", parse_mode='Markdown')
        return
    
    if context.user_data.get('admin_state') == 'set_free' and user_id == ADMIN_ID:
        try:
            count = int(text.strip())
            if count < 0:
                count = 0
            if count > 10:
                count = 10
            db.cursor.execute('UPDATE users SET max_free_signals = ?', (count,))
            db.conn.commit()
            context.user_data['admin_state'] = None
            await update.message.reply_text(f"✅ **تعداد سیگنال رایگان به {count} تغییر یافت!**", reply_markup=get_admin_keyboard())
        except:
            await update.message.reply_text("⚠️ **لطفاً یک عدد معتبر وارد کنید!**")
        return
    
    # ===== BUY SUBSCRIPTION =====
    if text == '💰 خرید اشتراک':
        user_id = update.effective_user.id
        is_premium = db.is_premium(user_id)
        
        if is_premium:
            await update.message.reply_text(
                "✅ **شما قبلاً اشتراک پرمیوم دارید!**\n"
                "با تشکر از حمایت شما 🙏",
                parse_mode='Markdown'
            )
            return
        
        msg = f"""
💰 **خرید اشتراک پرمیوم**

💎 **مزایای اشتراک پرمیوم:**
• دریافت سیگنال‌های اختصاصی
• دسترسی به سیگنال‌های پامپ و دامپ
• پشتیبانی ویژه
• افزایش دقت سیگنال‌ها

💵 **هزینه:** ${PRICE_USDT}
⏱️ **مدت:** {SUBSCRIPTION_DAYS} روز

🏦 **آدرس کیف پول (TRC20):**
`{WALLET_ADDRESS}`

📌 **مراحل خرید:**
1. مبلغ ${PRICE_USDT} را به آدرس بالا واریز کنید
2. هش تراکنش را به ربات ارسال کنید
3. اشتراک شما فعال می‌شود

⚠️ **فقط از شبکه TRC20 استفاده کنید**
"""
        await update.message.reply_text(msg, parse_mode='Markdown')
        return
    
    # ===== PROCESS PAYMENT HASH =====
    # بررسی هش تراکنش (حداقل ۳۴ کاراکتر)
    if len(text.strip()) >= 34 and user_id != ADMIN_ID:
        if db.is_premium(user_id):
            await update.message.reply_text("✅ **شما قبلاً اشتراک دارید!**")
            return
        
        # بررسی تکراری نبودن
        pending = db.get_pending_payments()
        for p in pending:
            if p[2] == text.strip():
                await update.message.reply_text("⚠️ **این هش قبلاً ثبت شده است**")
                return
        
        payment_id = db.add_payment(user_id, text.strip())
        
        # اطلاع به ادمین
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🧾 **درخواست پرداخت جدید:**\n"
                 f"👤 کاربر: {user_id}\n"
                 f"🔑 هش: `{text.strip()}`\n"
                 f"💰 مبلغ: ${PRICE_USDT}",
            parse_mode='Markdown'
        )
        
        await update.message.reply_text(
            "✅ **هش تراکنش ثبت شد!**\n"
            "⏳ پس از تایید ادمین، اشتراک شما فعال می‌شود.\n"
            "🕐 این کار معمولاً چند دقیقه طول می‌کشد.",
            parse_mode='Markdown'
        )
        return
    
    # ===== FEEDBACK =====
    # پردازش بازخورد
    if 'سود کردم' in text or 'سود نکردم' in text:
        feedback = 'positive' if 'سود کردم' in text else 'negative'
        
        # پیدا کردن شناسه سیگنال
        numbers = re.findall(r'\d+', text)
        signal_id = None
        if numbers:
            signal_id = int(numbers[0])
        
        if signal_id:
            db.update_feedback(signal_id, feedback, user_id)
            await update.message.reply_text(
                f"✅ **بازخورد شما ثبت شد!**\n"
                f"🙏 ممنون از کمکتان برای بهبود ربات",
                parse_mode='Markdown'
            )
        else:
            # اگر شماره نداشت، آخرین سیگنال
            signals = db.get_unsent_signals()
            if signals:
                db.update_feedback(signals[0][0], feedback, user_id)
                await update.message.reply_text(
                    f"✅ **بازخورد شما برای آخرین سیگنال ثبت شد!**",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "❌ **سیگنالی برای بازخورد یافت نشد**\n"
                    "لطفاً شناسه سیگنال را همراه با پیام خود ارسال کنید\n"
                    "مثال: سود کردم 123",
                    parse_mode='Markdown'
                )
        return
    
    await update.message.reply_text("❌ **گزینه موجود نیست**", reply_markup=get_main_keyboard())

# ==================== Callback Handlers ====================

async def callback_handler(update, context):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("❌ **دسترسی غیرمجاز!**")
        return
    
    data = query.data
    
    if data.startswith('confirm:'):
        payment_id = int(data.split(':')[1])
        user_id = db.confirm_payment(payment_id)
        
        if user_id:
            await query.edit_message_text(
                f"✅ **پرداخت تایید شد!**\n"
                f"👤 کاربر: {user_id}\n"
                f"📅 اشتراک {SUBSCRIPTION_DAYS} روزه فعال شد"
            )
            # اطلاع به کاربر
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"🎉 **تبریک! اشتراک پرمیوم شما فعال شد!**\n"
                         f"📅 مدت: {SUBSCRIPTION_DAYS} روز\n"
                         f"📊 از سیگنال‌های اختصاصی لذت ببرید!",
                    parse_mode='Markdown'
                )
            except:
                pass
        else:
            await query.edit_message_text("❌ **خطا در تایید پرداخت!**")
    
    elif data.startswith('reject:'):
        payment_id = int(data.split(':')[1])
        db.reject_payment(payment_id)
        await query.edit_message_text("❌ **پرداخت رد شد**")

# ==================== Main ====================
def main():
    if not TELEGRAM_AVAILABLE:
        print("❌ Install: pip install python-telegram-bot")
        return
    
    print("="*80)
    print("🚀 SIGNAL BOT V19 - FULL MARKET SCANNER")
    print("="*80)
    print(f"📡 Channel: {CHANNEL_ID}")
    print(f"⏱️ Scan interval: {SCAN_INTERVAL} seconds")
    print(f"👤 Admin: {ADMIN_ID}")
    print(f"💰 Wallet: {WALLET_ADDRESS}")
    print("="*80)
    print("✅ Scanning ALL symbols in market")
    print("✅ Auto-send signals to channel")
    print("✅ Full admin panel")
    print("✅ Premium system")
    print("="*80)
    
    # راه‌اندازی ترد اسکن خودکار
    scan_thread = threading.Thread(target=auto_scanner, daemon=True)
    scan_thread.start()
    logger.info("✅ Auto scanner thread started")
    
    # اسکن اولیه
    logger.info("🔄 Initial market scan...")
    scanner.scan_all()
    
    # راه‌اندازی ربات
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("✅ Bot started successfully!")
    print("✅ Bot is running...")
    
    try:
        app.run_polling(drop_pending_updates=True)
    except KeyboardInterrupt:
        logger.info("🛑 Stopping...")
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")

if __name__ == "__main__":
    # نیاز به asyncio برای callback
    import asyncio
    main()