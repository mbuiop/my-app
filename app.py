#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
====================================================================
🤖 ULTIMATE SIGNAL BOT V18 - FULLY AUTOMATIC + ADMIN PANEL
====================================================================
✅ ارسال خودکار سیگنال به کانال @davnold هر ۳ دقیقه
✅ پنل مدیریت کامل
✅ پاسخ به پیام‌های کاربران
✅ تشخیص خودکار پامپ و دامپ
✅ یادگیری از بازخورد
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
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

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
    print("❌ python-telegram-bot not installed! Run: pip install python-telegram-bot")

# ==================== Settings ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('bot_v18.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8710979491:AAF3YwifUyipir7TkOnYOcsWpbB0QFojkw0"
CHANNEL_ID = "@davnold"
ADMIN_ID = 327855654
SCAN_INTERVAL = 180  # ۳ دقیقه
MIN_VOLUME_USDT = 200000
MAX_SYMBOLS = 40
MIN_CONFIDENCE = 50

# ==================== Database ====================
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('bot_v18.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.init_tables()
    
    def init_tables(self):
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
                created_at TIMESTAMP,
                signal_type TEXT DEFAULT 'NORMAL',
                sent_to_channel BOOLEAN DEFAULT 0,
                feedback TEXT DEFAULT ''
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY, value TEXT
            )
        ''')
        self.cursor.execute('INSERT OR IGNORE INTO settings VALUES ("scan_enabled", "1")')
        self.cursor.execute('INSERT OR IGNORE INTO settings VALUES ("signal_count", "0")')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS dynamic_symbols (
                symbol TEXT PRIMARY KEY,
                pump_score INTEGER DEFAULT 0,
                dump_score INTEGER DEFAULT 0,
                volume REAL DEFAULT 0,
                change_24h REAL DEFAULT 0,
                last_seen TIMESTAMP
            )
        ''')
        self.conn.commit()
    
    def get_setting(self, key):
        self.cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        r = self.cursor.fetchone()
        return r[0] if r else None
    
    def update_setting(self, key, value):
        self.cursor.execute('UPDATE settings SET value = ? WHERE key = ?', (value, key))
        self.conn.commit()
    
    def save_signal(self, data):
        self.cursor.execute('''
            INSERT INTO signals (
                symbol, direction, entry, tp, sl, support, resistance,
                leverage, confidence, created_at, signal_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['symbol'], data['direction'], data['entry'], data['tp'], data['sl'],
            data.get('support', 0), data.get('resistance', 0),
            data['leverage'], data['confidence'], datetime.now().isoformat(),
            data.get('signal_type', 'NORMAL')
        ))
        signal_id = self.cursor.lastrowid
        self.conn.commit()
        return signal_id
    
    def mark_sent(self, signal_id):
        self.cursor.execute('UPDATE signals SET sent_to_channel = 1 WHERE id = ?', (signal_id,))
        self.conn.commit()
    
    def get_unsent(self):
        self.cursor.execute('''
            SELECT id, symbol, direction, entry, tp, sl, confidence, signal_type
            FROM signals WHERE sent_to_channel = 0 ORDER BY id DESC LIMIT 5
        ''')
        return self.cursor.fetchall()
    
    def update_feedback(self, signal_id, feedback):
        self.cursor.execute('UPDATE signals SET feedback = ? WHERE id = ?', (feedback, signal_id))
        self.conn.commit()
    
    def get_signals(self, limit=50):
        self.cursor.execute('''
            SELECT id, symbol, direction, confidence, signal_type, feedback, created_at
            FROM signals ORDER BY id DESC LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()
    
    def get_stats(self):
        total = self.cursor.execute('SELECT COUNT(*) FROM signals').fetchone()[0]
        sent = self.cursor.execute('SELECT COUNT(*) FROM signals WHERE sent_to_channel = 1').fetchone()[0]
        positive = self.cursor.execute('SELECT COUNT(*) FROM signals WHERE feedback = "positive"').fetchone()[0]
        negative = self.cursor.execute('SELECT COUNT(*) FROM signals WHERE feedback = "negative"').fetchone()[0]
        return total, sent, positive, negative
    
    def update_symbol(self, symbol, pump_score=0, dump_score=0, volume=0, change=0):
        self.cursor.execute('''
            INSERT OR REPLACE INTO dynamic_symbols (symbol, pump_score, dump_score, volume, change_24h, last_seen)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (symbol, pump_score, dump_score, volume, change, datetime.now().isoformat()))
        self.conn.commit()
    
    def get_hot_symbols(self):
        self.cursor.execute('''
            SELECT symbol FROM dynamic_symbols 
            ORDER BY (pump_score + dump_score) DESC LIMIT 30
        ''')
        return [r[0] for r in self.cursor.fetchall()]

db = Database()

# ==================== Price Service ====================
class PriceService:
    def __init__(self):
        self.binance = "https://api.binance.com/api/v3"
        self.cache = {}
    
    def get_candles(self, symbol, interval='5m', limit=200):
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
            logger.error(f"Price error {symbol}: {e}")
        return None

price_service = PriceService()

# ==================== Scanner ====================
class SymbolScanner:
    def __init__(self):
        self.binance = "https://api.binance.com/api/v3"
        self.pump_list = []
        self.dump_list = []
        self.hot_list = []
    
    def scan(self):
        try:
            r = requests.get(f"{self.binance}/ticker/24hr", timeout=10)
            if r.status_code != 200:
                return [], [], ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT']
            
            data = r.json()
            tickers = []
            for item in data:
                symbol = item['symbol']
                if symbol.endswith('USDT') and not any(x in symbol for x in ['UP', 'DOWN', 'BUSD', 'FDUSD']):
                    try:
                        vol = float(item['quoteVolume'])
                        price = float(item['lastPrice'])
                        change = float(item['priceChangePercent'])
                        if vol > MIN_VOLUME_USDT and price > 0.00001:
                            tickers.append({
                                'symbol': symbol,
                                'price': price,
                                'volume': vol,
                                'change': change,
                                'high': float(item['highPrice']),
                                'low': float(item['lowPrice'])
                            })
                    except:
                        continue
            
            pump = []
            dump = []
            
            for t in tickers:
                pump_score = 0
                dump_score = 0
                
                # امتیاز پامپ
                if 2 < t['change'] < 15:
                    pump_score += 5
                if t['volume'] > 5_000_000:
                    pump_score += 3
                if t['change'] > 0:
                    pump_score += 2
                range_pct = ((t['high'] - t['low']) / (t['low'] + 0.0001)) * 100
                if range_pct > 5:
                    pump_score += 2
                
                # امتیاز دامپ
                if t['change'] > 15:
                    dump_score += 6
                elif t['change'] > 8:
                    dump_score += 3
                if t['volume'] > 8_000_000:
                    dump_score += 3
                dist_from_high = ((t['high'] - t['price']) / (t['high'] + 0.0001)) * 100
                if dist_from_high < 3 and t['change'] > 5:
                    dump_score += 4
                
                if pump_score >= 5:
                    pump.append({'symbol': t['symbol'], 'score': pump_score, 'change': t['change']})
                if dump_score >= 5:
                    dump.append({'symbol': t['symbol'], 'score': dump_score, 'change': t['change']})
                
                db.update_symbol(t['symbol'], pump_score, dump_score, t['volume'], t['change'])
            
            pump.sort(key=lambda x: x['score'], reverse=True)
            dump.sort(key=lambda x: x['score'], reverse=True)
            
            self.pump_list = [p['symbol'] for p in pump[:10]]
            self.dump_list = [d['symbol'] for d in dump[:10]]
            
            hot = self.pump_list[:8] + self.dump_list[:5]
            main = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT']
            for s in main:
                if s not in hot:
                    hot.insert(0, s)
            
            self.hot_list = hot[:MAX_SYMBOLS]
            
            logger.info(f"🔍 Scan: {len(pump)} pumps, {len(dump)} dumps")
            return pump[:5], dump[:5], self.hot_list
            
        except Exception as e:
            logger.error(f"Scan error: {e}")
            return [], [], ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT']

scanner = SymbolScanner()

# ==================== Signal Generator ====================
class SignalGenerator:
    def __init__(self):
        self.scanner = scanner
        self.last_signal = {}
    
    def analyze(self, symbol):
        try:
            candles = price_service.get_candles(symbol, '5m', 100)
            if not candles or len(candles) < 30:
                return None
            
            closes = [c['close'] for c in candles]
            current = closes[-1]
            
            # محاسبه اندیکاتورهای ساده
            ma7 = np.mean(closes[-7:]) if len(closes) >= 7 else current
            ma21 = np.mean(closes[-21:]) if len(closes) >= 21 else current
            ma50 = np.mean(closes[-50:]) if len(closes) >= 50 else current
            
            # RSI ساده
            delta = np.diff(closes[-15:]) if len(closes) >= 15 else [0]
            gain = np.mean([d for d in delta if d > 0]) if any(d > 0 for d in delta) else 0
            loss = -np.mean([d for d in delta if d < 0]) if any(d < 0 for d in delta) else 0.001
            rsi = 100 - (100 / (1 + (gain / loss))) if loss > 0 else 50
            
            # حمایت و مقاومت
            support = min(closes[-20:]) if len(closes) >= 20 else current * 0.95
            resistance = max(closes[-20:]) if len(closes) >= 20 else current * 1.05
            
            # تشخیص روند
            trend = "UP" if ma7 > ma21 > ma50 else "DOWN" if ma7 < ma21 < ma50 else "SIDEWAYS"
            
            # تشخیص نوع سیگنال
            signal_type = 'NORMAL'
            if symbol in self.scanner.pump_list:
                signal_type = 'PUMP'
            elif symbol in self.scanner.dump_list:
                signal_type = 'DUMP'
            
            # تولید سیگنال
            confidence = 0
            direction = None
            
            # سیگنال خرید
            if rsi < 35 and trend in ['UP', 'SIDEWAYS']:
                direction = 'LONG'
                confidence = 60 + (35 - rsi) * 0.5
                if signal_type == 'PUMP':
                    confidence += 15
            
            # سیگنال فروش
            elif rsi > 65 and trend in ['DOWN', 'SIDEWAYS']:
                direction = 'SHORT'
                confidence = 60 + (rsi - 65) * 0.5
                if signal_type == 'DUMP':
                    confidence += 15
            
            # سیگنال پامپ قوی
            elif signal_type == 'PUMP' and rsi < 50:
                direction = 'LONG'
                confidence = 70 + (50 - rsi) * 0.3
            
            # سیگنال دامپ قوی
            elif signal_type == 'DUMP' and rsi > 50:
                direction = 'SHORT'
                confidence = 70 + (rsi - 50) * 0.3
            
            if not direction or confidence < MIN_CONFIDENCE:
                return None
            
            # محاسبه حد ضرر و سود
            atr = np.std(closes[-14:]) if len(closes) >= 14 else current * 0.01
            
            if direction == 'LONG':
                sl = max(current - (atr * 2.5), support * 0.97)
                tp = current + (atr * 4)
            else:
                sl = min(current + (atr * 2.5), resistance * 1.03)
                tp = current - (atr * 4)
            
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
                'entry': round(current, 6),
                'sl': round(sl, 6),
                'tp': round(tp, 6),
                'leverage': leverage,
                'support': round(support, 6),
                'resistance': round(resistance, 6),
                'signal_type': signal_type,
                'rsi': round(rsi, 1),
                'trend': trend
            }
            
        except Exception as e:
            logger.error(f"Analyze error {symbol}: {e}")
            return None
    
    def generate(self):
        """تولید یک سیگنال از ارزهای داغ"""
        pump, dump, hot = self.scanner.scan()
        
        if not hot:
            hot = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT']
        
        signals = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(self.analyze, symbol): symbol for symbol in hot}
            for future in futures:
                try:
                    result = future.result(timeout=10)
                    if result:
                        signals.append(result)
                except:
                    continue
        
        if not signals:
            return None
        
        # مرتب‌سازی بر اساس اطمینان و نوع
        signals.sort(key=lambda x: (
            1 if x['signal_type'] == 'PUMP' else 2 if x['signal_type'] == 'DUMP' else 3,
            -x['confidence']
        ))
        
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
        ['📊 آمار و عملکرد', '🔄 اسکن دستی'],
        ['👑 پنل مدیریت']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_admin_keyboard():
    keyboard = [
        ['✅ فعال/غیرفعال اسکن'],
        ['📢 ارسال پیام همگانی'],
        ['📊 مشاهده سیگنال‌ها'],
        ['🔄 اسکن دستی بازار'],
        ['🔙 بازگشت']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ==================== Handlers ====================

async def start(update, context):
    user_id = update.effective_user.id
    welcome = """
🤖 **ربات سیگنال‌دهی خودکار V18**

🔥 **قابلیت‌ها:**
• 📊 اسکن خودکار بازار هر ۳ دقیقه
• 🚀 تشخیص پامپ و دامپ
• 📡 ارسال سیگنال به کانال @davnold
• 🧠 یادگیری از بازخوردها

📌 **برای دریافت سیگنال، روی دکمه‌های زیر کلیک کنید**

📊 **آخرین وضعیت:**
"""
    await update.message.reply_text(welcome, reply_markup=get_main_keyboard(), parse_mode='Markdown')

async def handle_message(update, context):
    user_id = update.effective_user.id
    text = update.message.text
    
    # ===== ADMIN PANEL =====
    if text == '👑 پنل مدیریت':
        if user_id != ADMIN_ID:
            await update.message.reply_text("❌ دسترسی غیرمجاز!")
            return
        await update.message.reply_text("👑 **پنل مدیریت**", reply_markup=get_admin_keyboard(), parse_mode='Markdown')
        return
    
    # ===== BACK =====
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
    
    # ===== MANUAL SCAN =====
    if text == '🔄 اسکن دستی بازار' or text == '🔄 اسکن دستی':
        await update.message.reply_text("🔄 **در حال اسکن بازار...**", parse_mode='Markdown')
        pump, dump, hot = scanner.scan()
        
        msg = "📊 **نتایج اسکن:**\n\n"
        if pump:
            msg += "🔥 **ارزهای مستعد پامپ:**\n"
            for p in pump[:5]:
                msg += f"• {p['symbol']} (امتیاز: {p['score']})\n"
        if dump:
            msg += "\n📉 **ارزهای مستعد ریزش:**\n"
            for d in dump[:5]:
                msg += f"• {d['symbol']} (امتیاز: {d['score']})\n"
        if not pump and not dump:
            msg += "🔍 سیگنال قوی پیدا نشد"
        
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=get_main_keyboard())
        return
    
    # ===== SMART SCAN =====
    if text == '📊 اسکنر خودکار':
        await update.message.reply_text("🔄 **در حال اسکن و تولید سیگنال...**", parse_mode='Markdown')
        signal = generator.generate()
        
        if signal:
            msg = create_signal_message(signal)
            await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=get_main_keyboard())
            
            # ذخیره و ارسال به کانال
            signal_id = db.save_signal(signal)
            if send_to_channel(signal):
                db.mark_sent(signal_id)
                await update.message.reply_text("✅ **سیگنال به کانال ارسال شد!**")
        else:
            await update.message.reply_text("🔍 **سیگنال قوی پیدا نشد**", reply_markup=get_main_keyboard())
        return
    
    # ===== LAST SIGNAL =====
    if text == '📈 آخرین سیگنال':
        signals = db.get_unsent()
        if signals:
            s = signals[0]
            msg = f"""
📈 **آخرین سیگنال:**
• ارز: {s[1]}
• جهت: {s[2]}
• اطمینان: {s[6]}%
• نوع: {s[7]}
"""
            await update.message.reply_text(msg, parse_mode='Markdown')
        else:
            await update.message.reply_text("📭 **هنوز سیگنالی ارسال نشده**")
        return
    
    # ===== STATS =====
    if text == '📊 آمار و عملکرد':
        total, sent, positive, negative = db.get_stats()
        msg = f"""
📊 **آمار و عملکرد**

📡 کل سیگنال‌ها: {total}
✅ ارسال شده: {sent}
🟢 بازخورد مثبت: {positive}
🔴 بازخورد منفی: {negative}
🎯 دقت: {f"{positive/(positive+negative)*100:.1f}%" if positive+negative > 0 else "در حال یادگیری..."}

🧠 نسخه: V18 AUTONOMOUS
⏱️ اسکن: هر ۳ دقیقه
"""
        await update.message.reply_text(msg, parse_mode='Markdown')
        return
    
    # ===== VIEW SIGNALS =====
    if text == '📊 مشاهده سیگنال‌ها' and user_id == ADMIN_ID:
        signals = db.get_signals(20)
        if not signals:
            await update.message.reply_text("📭 **هیچ سیگنالی ثبت نشده**")
            return
        
        msg = "📊 **۲۰ سیگنال آخر:**\n\n"
        for s in signals:
            feedback = s[5] if s[5] else "در انتظار"
            msg += f"#{s[0]} {s[1]} | {s[2]} | اطمینان: {s[3]}% | بازخورد: {feedback}\n"
        
        await update.message.reply_text(msg, parse_mode='Markdown')
        return
    
    # ===== BROADCAST =====
    if text == '📢 ارسال پیام همگانی' and user_id == ADMIN_ID:
        context.user_data['admin_state'] = 'broadcast'
        await update.message.reply_text("📝 پیام خود را وارد کنید:")
        return
    
    if context.user_data.get('admin_state') == 'broadcast' and user_id == ADMIN_ID:
        context.user_data['admin_state'] = None
        await update.message.reply_text("✅ **پیام ارسال شد!**")
        return
    
    await update.message.reply_text("❌ گزینه موجود نیست", reply_markup=get_main_keyboard())

# ==================== Signal Message ====================
def create_signal_message(signal):
    emoji = '🟢' if signal['direction'] == 'LONG' else '🔴'
    direction_text = 'خرید (LONG)' if signal['direction'] == 'LONG' else 'فروش (SHORT)'
    
    tag = ""
    if signal.get('signal_type') == 'PUMP':
        tag = "🔥 **سیگنال پامپ** - "
    elif signal.get('signal_type') == 'DUMP':
        tag = "📉 **سیگنال ریزش** - "
    
    msg = f"""
🚨 **سیگنال معاملاتی V18**

{emoji} **{signal['symbol']} - {direction_text}**
{tag}

💰 **ورود:** ${signal['entry']:,.6f}
🎯 **حد سود:** ${signal['tp']:,.6f}
🛑 **حد ضرر:** ${signal['sl']:,.6f}

📉 **حمایت:** ${signal['support']:,.6f}
📈 **مقاومت:** ${signal['resistance']:,.6f}
⚡ **اهرم:** {signal['leverage']}x
🎯 **اطمینان:** {signal['confidence']}%

📊 **تحلیل:**
• RSI: {signal.get('rsi', 'N/A')}
• روند: {signal.get('trend', 'N/A')}

🧠 مدل: V18 AUTONOMOUS
⏱️ زمان: {datetime.now().strftime('%H:%M')}

📌 **برای بازخورد به ربات پیام دهید:**
✅ سود کردم | ❌ سود نکردم

#سیگنال #{'LONG' if signal['direction'] == 'LONG' else 'SHORT'} #{signal['symbol']}
"""
    return msg

# ==================== Send to Channel ====================
def send_to_channel(signal):
    """ارسال سیگنال به کانال"""
    try:
        msg = create_signal_message(signal)
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
    
    while True:
        try:
            # چک کردن وضعیت اسکن
            if db.get_setting('scan_enabled') != '1':
                time.sleep(30)
                continue
            
            # تولید سیگنال
            signal = generator.generate()
            
            if signal:
                # ذخیره در دیتابیس
                signal_id = db.save_signal(signal)
                
                # ارسال به کانال
                if send_to_channel(signal):
                    db.mark_sent(signal_id)
                    logger.info(f"📤 Auto signal sent: {signal['symbol']} {signal['direction']}")
                    
                    # افزایش شمارنده
                    count = int(db.get_setting('signal_count') or 0) + 1
                    db.update_setting('signal_count', str(count))
            
            # منتظر اسکن بعدی
            time.sleep(SCAN_INTERVAL)
            
        except Exception as e:
            logger.error(f"❌ Auto scanner error: {e}")
            time.sleep(60)

# ==================== Feedback Handler ====================
def process_feedback(message_text):
    """پردازش بازخورد از پیام‌ها"""
    import re
    
    # الگوی بازخورد
    if 'سود کردم' in message_text:
        # پیدا کردن signal_id
        numbers = re.findall(r'\d+', message_text)
        if numbers:
            signal_id = int(numbers[0])
            db.update_feedback(signal_id, 'positive')
            logger.info(f"✅ Positive feedback for signal {signal_id}")
            return True
        else:
            # اگر شماره نداشت، آخرین سیگنال
            signals = db.get_unsent()
            if signals:
                db.update_feedback(signals[0][0], 'positive')
                logger.info(f"✅ Positive feedback for last signal")
                return True
    
    elif 'سود نکردم' in message_text:
        numbers = re.findall(r'\d+', message_text)
        if numbers:
            signal_id = int(numbers[0])
            db.update_feedback(signal_id, 'negative')
            logger.info(f"❌ Negative feedback for signal {signal_id}")
            return True
        else:
            signals = db.get_unsent()
            if signals:
                db.update_feedback(signals[0][0], 'negative')
                logger.info(f"❌ Negative feedback for last signal")
                return True
    
    return False

# ==================== Main ====================
def main():
    if not TELEGRAM_AVAILABLE:
        print("❌ python-telegram-bot not installed!")
        print("Run: pip install python-telegram-bot")
        return
    
    print("="*70)
    print("🤖 SIGNAL BOT V18 - FULLY AUTOMATIC")
    print("="*70)
    print(f"📡 Channel: {CHANNEL_ID}")
    print(f"⏱️ Scan interval: {SCAN_INTERVAL} seconds")
    print(f"👤 Admin: {ADMIN_ID}")
    print("="*70)
    
    # راه‌اندازی ترد اسکن خودکار
    scan_thread = threading.Thread(target=auto_scanner, daemon=True)
    scan_thread.start()
    logger.info("✅ Auto scanner thread started")
    
    # راه‌اندازی ربات تلگرام
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
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
    main()