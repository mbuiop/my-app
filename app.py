#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ربات مادر - نسخه امن با سیستم اشتراک و مدیریت کامل
"""

import telebot
from telebot import types
import sqlite3
import os
import subprocess
import sys
import time
import hashlib
import json
import threading
import shutil
import re
import zipfile
import requests
import signal
import secrets
import logging
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from contextlib import contextmanager

# ==================== تنظیمات پایه ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "database")
FILES_DIR = os.path.join(BASE_DIR, "user_files")
RUNNING_DIR = os.path.join(BASE_DIR, "running_bots")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
RECEIPTS_DIR = os.path.join(BASE_DIR, "receipts")
PENDING_FILES_DIR = os.path.join(BASE_DIR, "pending_files")

os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(FILES_DIR, exist_ok=True)
os.makedirs(RUNNING_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(RECEIPTS_DIR, exist_ok=True)
os.makedirs(PENDING_FILES_DIR, exist_ok=True)

# ==================== توکن ربات مادر ====================
BOT_TOKEN = "8266270866:AAF6m1x4weSUEvzIj1gkbIS_j0yAdxCSs78"  # 🔴 توکن خودت رو اینجا بزار
bot = telebot.TeleBot(BOT_TOKEN)
bot.delete_webhook()

# ==================== آیدی ادمین ====================
ADMIN_IDS = [327855654]  # 🔴 آیدی ادمین خودت رو اینجا بزار

# ==================== تنظیمات پیش‌فرض (قابل تغییر توسط ادمین) ====================
class Config:
    def __init__(self):
        self.welcome_text = """🚀 به ربات سازنده ربات خوش آمدید!

👤 کاربر عزیز، شما می‌توانید با خرید اشتراک، ربات تلگرامی خود را بسازید.

📌 نحوه کار:
1️⃣ خرید اشتراک
2️⃣ ارسال فایل ربات برای بررسی امنیتی
3️⃣ پس از تایید فایل و فیش، ربات ساخته می‌شود

💰 هر اشتراک = ۱ ربات
برای ربات دوم نیاز به خرید اشتراک جدید دارید

@{} - پشتیبانی"""
        
        self.price = 200000
        self.card_number = "5892101187322777"
        self.card_holder = "مرتضی نیکخو خنجری"
        
        self.guide_text = """📚 راهنمای استفاده

1️⃣ خرید اشتراک:
   • مبلغ: {} تومان
   • شماره کارت: {}
   • به نام: {}

2️⃣ ارسال فایل:
   • فایل ربات خود را برای پشتیبانی بفرستید
   • پس از بررسی امنیتی، به شما اعلام می‌شود

3️⃣ ساخت ربات:
   • پس از تایید فایل و فیش، ربات شما ساخته می‌شود
   • لینک ربات و اطلاعات آن به شما ارسال می‌شود

⚠️ نکات امنیتی:
• فایل شما توسط تیم بررسی می‌شود
• کدهای مخرب مجاز نیستند
• اطلاعات شما محفوظ است

@{} - پشتیبانی"""
    
    def load_from_db(self):
        try:
            with get_db() as conn:
                config = conn.execute("SELECT key, value FROM config").fetchall()
                for row in config:
                    if row['key'] == 'welcome_text':
                        self.welcome_text = row['value']
                    elif row['key'] == 'price':
                        self.price = int(row['value'])
                    elif row['key'] == 'card_number':
                        self.card_number = row['value']
                    elif row['key'] == 'card_holder':
                        self.card_holder = row['value']
                    elif row['key'] == 'guide_text':
                        self.guide_text = row['value']
        except:
            pass
    
    def save_to_db(self):
        with get_db() as conn:
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('welcome_text', self.welcome_text))
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('price', str(self.price)))
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('card_number', self.card_number))
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('card_holder', self.card_holder))
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('guide_text', self.guide_text))
            conn.commit()

config = Config()

# ==================== دیتابیس پیشرفته با پشتیبانی میلیون‌ها کاربر ====================
DB_PATH = os.path.join(DB_DIR, 'mother_bot.db')

@contextmanager
def get_db():
    """مدیریت اتصال دیتابیس با timeout بالا برای پشتیبانی از حجم بالا"""
    conn = sqlite3.connect(DB_PATH, timeout=60, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # برای عملکرد بهتر در حجم بالا
    conn.execute("PRAGMA cache_size=-65536")  # کش 64 مگابایت
    conn.execute("PRAGMA synchronous=NORMAL")
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# ایجاد جداول با ایندکس‌های بهینه
with get_db() as conn:
    # جدول تنظیمات
    conn.execute('''
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # جدول کاربران (بهینه شده برای میلیون‌ها رکورد)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            active_subscription INTEGER DEFAULT 0,
            subscription_expire TIMESTAMP,
            created_at TIMESTAMP,
            last_active TIMESTAMP
        )
    ''')
    
    # جدول اشتراک‌ها
    conn.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            subscription_code TEXT UNIQUE,
            status TEXT DEFAULT 'pending',
            amount INTEGER,
            created_at TIMESTAMP,
            paid_at TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    ''')
    
    # جدول فایل‌های در انتظار بررسی
    conn.execute('''
        CREATE TABLE IF NOT EXISTS pending_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            subscription_id INTEGER,
            file_path TEXT,
            file_name TEXT,
            status TEXT DEFAULT 'pending',
            submitted_at TIMESTAMP,
            reviewed_at TIMESTAMP,
            review_note TEXT,
            FOREIGN KEY(user_id) REFERENCES users(user_id),
            FOREIGN KEY(subscription_id) REFERENCES subscriptions(id)
        )
    ''')
    
    # جدول ربات‌ها
    conn.execute('''
        CREATE TABLE IF NOT EXISTS bots (
            id TEXT PRIMARY KEY,
            user_id INTEGER,
            subscription_id INTEGER,
            token TEXT,
            name TEXT,
            username TEXT,
            file_path TEXT,
            pid INTEGER,
            status TEXT DEFAULT 'stopped',
            created_at TIMESTAMP,
            last_active TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY(subscription_id) REFERENCES subscriptions(id)
        )
    ''')
    
    # جدول فیش‌های واریزی
    conn.execute('''
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            subscription_id INTEGER,
            amount INTEGER,
            receipt_path TEXT,
            status TEXT DEFAULT 'pending',
            payment_code TEXT UNIQUE,
            created_at TIMESTAMP,
            reviewed_at TIMESTAMP,
            reviewed_by INTEGER
        )
    ''')
    
    # ایجاد ایندکس‌ها برای سرعت بالا
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_subscription ON users(active_subscription)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pending_files_user ON pending_files(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pending_files_status ON pending_files(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_bots_user ON bots(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_receipts_user ON receipts(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_receipts_status ON receipts(status)")
    
    conn.commit()

# بارگذاری تنظیمات
config.load_from_db()

# ==================== توابع دیتابیس ====================

def create_user(user_id, username, first_name, last_name):
    """ایجاد کاربر جدید"""
    try:
        with get_db() as conn:
            now = datetime.now().isoformat()
            conn.execute('''
                INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, created_at, last_active)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name, now, now))
            
            conn.execute('UPDATE users SET last_active = ? WHERE user_id = ?', (now, user_id))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"خطا در create_user: {e}")
        return False

def get_user(user_id):
    """گرفتن اطلاعات کاربر"""
    try:
        with get_db() as conn:
            user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
            return dict(user) if user else None
    except:
        return None

def has_active_subscription(user_id):
    """بررسی اشتراک فعال کاربر"""
    try:
        with get_db() as conn:
            user = conn.execute('SELECT active_subscription, subscription_expire FROM users WHERE user_id = ?', (user_id,)).fetchone()
            if user and user['active_subscription'] == 1:
                if user['subscription_expire']:
                    expire = datetime.fromisoformat(user['subscription_expire'])
                    if expire > datetime.now():
                        return True
                    else:
                        conn.execute('UPDATE users SET active_subscription = 0 WHERE user_id = ?', (user_id,))
                        conn.commit()
                        return False
                return True
            return False
    except:
        return False

def create_subscription(user_id, amount):
    """ایجاد اشتراک جدید"""
    try:
        with get_db() as conn:
            subscription_code = hashlib.md5(f"{user_id}_{time.time()}_{secrets.token_hex(4)}".encode()).hexdigest()[:12].upper()
            now = datetime.now().isoformat()
            
            conn.execute('''
                INSERT INTO subscriptions (user_id, subscription_code, amount, created_at, status)
                VALUES (?, ?, ?, ?, 'pending')
            ''', (user_id, subscription_code, amount, now))
            conn.commit()
            
            sub_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            return sub_id, subscription_code
    except Exception as e:
        logger.error(f"خطا در create_subscription: {e}")
        return None, None

def activate_subscription(subscription_id):
    """فعال کردن اشتراک"""
    try:
        with get_db() as conn:
            sub = conn.execute('SELECT * FROM subscriptions WHERE id = ?', (subscription_id,)).fetchone()
            if sub:
                expire_time = (datetime.now() + timedelta(days=365)).isoformat()
                conn.execute('''
                    UPDATE users SET active_subscription = 1, subscription_expire = ?
                    WHERE user_id = ?
                ''', (expire_time, sub['user_id']))
                
                conn.execute('''
                    UPDATE subscriptions SET status = 'active', paid_at = ?
                    WHERE id = ?
                ''', (datetime.now().isoformat(), subscription_id))
                conn.commit()
                return True
            return False
    except:
        return False

def get_user_bots(user_id):
    """دریافت ربات‌های کاربر"""
    try:
        with get_db() as conn:
            bots = conn.execute('SELECT * FROM bots WHERE user_id = ? ORDER BY created_at DESC', (user_id,)).fetchall()
            return [dict(bot) for bot in bots]
    except:
        return []

def add_bot(user_id, subscription_id, bot_id, token, name, username, file_path, pid=None):
    """افزودن ربات به دیتابیس"""
    try:
        with get_db() as conn:
            now = datetime.now().isoformat()
            conn.execute('''
                INSERT INTO bots (id, user_id, subscription_id, token, name, username, file_path, pid, status, created_at, last_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'running', ?, ?)
            ''', (bot_id, user_id, subscription_id, token, name, username, file_path, pid, now, now))
            
            conn.execute('UPDATE users SET active_subscription = 0 WHERE user_id = ?', (user_id,))
            conn.commit()
            return True
    except:
        return False

def get_pending_file(user_id):
    """دریافت فایل در انتظار کاربر"""
    try:
        with get_db() as conn:
            pending = conn.execute('''
                SELECT * FROM pending_files 
                WHERE user_id = ? AND status = 'pending'
                ORDER BY submitted_at DESC LIMIT 1
            ''', (user_id,)).fetchone()
            return dict(pending) if pending else None
    except:
        return None

def save_pending_file(user_id, subscription_id, file_path, file_name):
    """ذخیره فایل در انتظار"""
    try:
        with get_db() as conn:
            now = datetime.now().isoformat()
            conn.execute('''
                INSERT INTO pending_files (user_id, subscription_id, file_path, file_name, submitted_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, subscription_id, file_path, file_name, now))
            conn.commit()
            return True
    except:
        return False

def approve_file_and_build(pending_id, user_id, subscription_id, file_path, token, bot_name, bot_username, bot_id, pid):
    """تایید فایل و ساخت ربات"""
    try:
        with get_db() as conn:
            now = datetime.now().isoformat()
            conn.execute('UPDATE pending_files SET status = "approved", reviewed_at = ? WHERE id = ?', (now, pending_id))
            
            conn.execute('''
                INSERT INTO bots (id, user_id, subscription_id, token, name, username, file_path, pid, status, created_at, last_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'running', ?, ?)
            ''', (bot_id, user_id, subscription_id, token, bot_name, bot_username, file_path, pid, now, now))
            
            conn.execute('UPDATE users SET active_subscription = 0 WHERE user_id = ?', (user_id,))
            conn.commit()
            return True
    except:
        return False

def reject_file(pending_id, user_id, reason):
    """رد فایل"""
    try:
        with get_db() as conn:
            now = datetime.now().isoformat()
            conn.execute('''
                UPDATE pending_files SET status = "rejected", reviewed_at = ?, review_note = ?
                WHERE id = ?
            ''', (now, reason, pending_id))
            conn.commit()
            return True
    except:
        return False

def delete_bot(bot_id, user_id):
    """حذف ربات"""
    try:
        with get_db() as conn:
            bot = conn.execute('SELECT * FROM bots WHERE id = ? AND user_id = ?', (bot_id, user_id)).fetchone()
            if not bot:
                return False
            
            if bot['pid']:
                try:
                    os.kill(bot['pid'], signal.SIGTERM)
                except:
                    pass
            
            if bot['file_path'] and os.path.exists(bot['file_path']):
                os.remove(bot['file_path'])
            
            conn.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
            conn.commit()
            return True
    except:
        return False

# ==================== توابع کمکی ====================

def save_uploaded_file(user_id, file_data, file_name):
    """ذخیره فایل آپلود شده"""
    try:
        user_dir = os.path.join(PENDING_FILES_DIR, str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        
        timestamp = int(time.time())
        file_path = os.path.join(user_dir, f"{timestamp}_{file_name}")
        
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        return file_path
    except:
        return None

def extract_token_from_code(code):
    """استخراج توکن از کد"""
    patterns = [
        r'token\s*=\s*["\']([^"\']+)["\']',
        r'TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'API_TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'BOT_TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'bot\s*=\s*telebot\.TeleBot\(\s*["\']([^"\']+)["\']\s*\)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, code, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

def run_bot_code(code, token, bot_dir):
    """اجرای کد ربات در محیط امن"""
    try:
        code_path = os.path.join(bot_dir, 'bot.py')
        with open(code_path, 'w', encoding='utf-8') as f:
            f.write(code)
        
        log_file = os.path.join(bot_dir, 'bot.log')
        
        process = subprocess.Popen(
            [sys.executable, code_path],
            stdout=open(log_file, 'a'),
            stderr=subprocess.STDOUT,
            cwd=bot_dir,
            start_new_session=True
        )
        
        time.sleep(2)
        
        if process.poll() is None:
            return process.pid, None
        else:
            with open(log_file, 'r') as f:
                error = f.read()[-500:]
            return None, error
    except Exception as e:
        return None, str(e)

# ==================== منوها ====================

def get_main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        types.KeyboardButton('🛒 خرید اشتراک'),
        types.KeyboardButton('📤 ارسال فایل ربات'),
        types.KeyboardButton('🤖 ربات‌های من'),
        types.KeyboardButton('📚 راهنما'),
        types.KeyboardButton('📞 پشتیبانی')
    ]
    markup.add(*buttons)
    return markup

def get_admin_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        types.KeyboardButton('👑 پنل ادمین'),
        types.KeyboardButton('🛒 خرید اشتراک'),
        types.KeyboardButton('📤 ارسال فایل ربات'),
        types.KeyboardButton('🤖 ربات‌های من'),
        types.KeyboardButton('📚 راهنما'),
        types.KeyboardButton('📞 پشتیبانی')
    ]
    markup.add(*buttons)
    return markup

# ==================== هندلر استارت ====================

@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    
    create_user(user_id, username, first_name, last_name)
    
    bot_username = bot.get_me().username
    welcome = config.welcome_text.format(bot_username)
    
    is_admin = user_id in ADMIN_IDS
    markup = get_admin_menu() if is_admin else get_main_menu()
    
    bot.send_message(message.chat.id, welcome, reply_markup=markup)

# ==================== خرید اشتراک ====================

@bot.message_handler(func=lambda m: m.text == '🛒 خرید اشتراک')
def buy_subscription(message):
    user_id = message.from_user.id
    
    if has_active_subscription(user_id):
        bot.send_message(
            message.chat.id,
            "✅ شما اشتراک فعال دارید!\n\n"
            "📤 لطفاً فایل ربات خود را ارسال کنید تا پس از بررسی ساخته شود."
        )
        return
    
    sub_id, sub_code = create_subscription(user_id, config.price)
    if not sub_id:
        bot.send_message(message.chat.id, "❌ خطا در ایجاد اشتراک. لطفاً دوباره تلاش کنید.")
        return
    
    text = f"""💰 خرید اشتراک

مبلغ: {config.price:,} تومان
شماره کارت: {config.card_number}
به نام: {config.card_holder}

🆔 کد اشتراک: `{sub_code}`

📌 مراحل:
1️⃣ مبلغ را به کارت فوق واریز کنید
2️⃣ کد اشتراک را در رسید یادداشت کنید
3️⃣ تصویر فیش را ارسال کنید

⚠️ پس از تایید فیش، می‌توانید فایل ربات خود را ارسال کنید
"""
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# ==================== رسید واریزی ====================

@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    
    # بررسی وجود اشتراک در انتظار
    with get_db() as conn:
        pending_sub = conn.execute('''
            SELECT * FROM subscriptions 
            WHERE user_id = ? AND status = 'pending'
            ORDER BY created_at DESC LIMIT 1
        ''', (user_id,)).fetchone()
    
    if not pending_sub:
        bot.reply_to(message, "❌ شما اشتراک در انتظار پرداختی ندارید.\nاز منوی خرید اشتراک استفاده کنید.")
        return
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        payment_code = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:8].upper()
        receipt_path = os.path.join(RECEIPTS_DIR, f"{user_id}_{payment_code}.jpg")
        
        with open(receipt_path, 'wb') as f:
            f.write(downloaded_file)
        
        with get_db() as conn:
            conn.execute('''
                INSERT INTO receipts (user_id, subscription_id, amount, receipt_path, payment_code, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, pending_sub['id'], config.price, receipt_path, payment_code, datetime.now().isoformat()))
            conn.commit()
        
        bot.reply_to(
            message,
            f"✅ فیش دریافت شد\n"
            f"💰 مبلغ: {config.price:,} تومان\n"
            f"🆔 کد پیگیری: {payment_code}\n\n"
            f"⏳ پس از بررسی توسط ادمین، اشتراک شما فعال می‌شود.\n"
            f"سپس می‌توانید فایل ربات خود را ارسال کنید."
        )
        
        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(
                    admin_id,
                    f"📸 فیش جدید\n"
                    f"👤 کاربر: {user_id}\n"
                    f"💰 مبلغ: {config.price:,} تومان\n"
                    f"🆔 کد: {payment_code}\n"
                    f"🆔 اشتراک: {pending_sub['subscription_code']}"
                )
            except:
                pass
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")

# ==================== ارسال فایل ربات ====================

@bot.message_handler(func=lambda m: m.text == '📤 ارسال فایل ربات')
def send_bot_file(message):
    user_id = message.from_user.id
    
    if not has_active_subscription(user_id):
        bot.send_message(
            message.chat.id,
            f"❌ شما اشتراک فعال ندارید!\n\n"
            f"💰 مبلغ اشتراک: {config.price:,} تومان\n"
            f"از منوی «خرید اشتراک» استفاده کنید."
        )
        return
    
    # بررسی فایل در انتظار قبلی
    pending = get_pending_file(user_id)
    if pending:
        bot.send_message(
            message.chat.id,
            "⏳ شما قبلاً یک فایل ارسال کرده‌اید و در انتظار بررسی است.\n"
            "لطفاً صبر کنید تا ادمین آن را بررسی کند."
        )
        return
    
    bot.send_message(
        message.chat.id,
        "📤 لطفاً فایل `.py` ربات خود را ارسال کنید.\n\n"
        "⚠️ توجه:\n"
        "• فایل شما توسط تیم بررسی امنیتی می‌شود\n"
        "• پس از تایید، ربات شما ساخته خواهد شد\n"
        "• حجم فایل حداکثر ۱۰ مگابایت"
    )

@bot.message_handler(content_types=['document'])
def handle_bot_file(message):
    user_id = message.from_user.id
    
    if not has_active_subscription(user_id):
        bot.reply_to(message, "❌ شما اشتراک فعال ندارید!")
        return
    
    pending = get_pending_file(user_id)
    if pending:
        bot.reply_to(message, "⏳ شما در انتظار بررسی فایل قبلی هستید.")
        return
    
    file_name = message.document.file_name
    
    if not file_name.endswith('.py'):
        bot.reply_to(message, "❌ فقط فایل‌های `.py` مجاز هستند!")
        return
    
    if message.document.file_size > 10 * 1024 * 1024:
        bot.reply_to(message, "❌ حجم فایل نباید بیشتر از ۱۰ مگابایت باشد!")
        return
    
    status_msg = bot.reply_to(message, "🔄 در حال دریافت فایل...")
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        file_path = save_uploaded_file(user_id, downloaded_file, file_name)
        if not file_path:
            bot.edit_message_text("❌ خطا در ذخیره فایل", message.chat.id, status_msg.message_id)
            return
        
        # پیدا کردن اشتراک فعال
        with get_db() as conn:
            sub = conn.execute('''
                SELECT id FROM subscriptions 
                WHERE user_id = ? AND status = 'active'
                ORDER BY paid_at DESC LIMIT 1
            ''', (user_id,)).fetchone()
        
        if not sub:
            bot.edit_message_text("❌ اشتراک فعال پیدا نشد!", message.chat.id, status_msg.message_id)
            return
        
        save_pending_file(user_id, sub['id'], file_path, file_name)
        
        # بررسی اولیه توکن
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            token = extract_token_from_code(code)
            token_status = "✅ توکن پیدا شد" if token else "⚠️ توکن در کد پیدا نشد!"
        except:
            token_status = "⚠️ خطا در خواندن فایل"
        
        bot.edit_message_text(
            f"✅ فایل شما دریافت شد!\n\n"
            f"📄 نام: {file_name}\n"
            f"{token_status}\n\n"
            f"⏳ فایل شما برای بررسی امنیتی به ادمین ارسال شد.\n"
            f"پس از تایید، ربات شما ساخته خواهد شد.",
            message.chat.id,
            status_msg.message_id
        )
        
        # ارسال به ادمین
        for admin_id in ADMIN_IDS:
            try:
                with open(file_path, 'rb') as f:
                    bot.send_document(
                        admin_id,
                        f,
                        caption=f"📥 فایل جدید برای بررسی\n"
                               f"👤 کاربر: {user_id}\n"
                               f"📄 نام: {file_name}\n"
                               f"{token_status}\n\n"
                               f"✅ برای تایید: /approve_{pending_id}\n"
                               f"❌ برای رد: /reject_{pending_id}"
                    )
            except:
                pass
                
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)}", message.chat.id, status_msg.message_id)

# ==================== ربات‌های من ====================

@bot.message_handler(func=lambda m: m.text == '🤖 ربات‌های من')
def my_bots(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما رباتی ندارید!\nبرای ساخت ربات، ابتدا اشتراک بخرید.")
        return
    
    for b in bots:
        status_emoji = "🟢" if b['status'] == 'running' else "🔴"
        status_text = "در حال اجرا" if b['status'] == 'running' else "متوقف"
        
        text = f"{status_emoji} **{b['name']}**\n"
        text += f"🔗 https://t.me/{b['username']}\n"
        text += f"🆔 `{b['id']}`\n"
        text += f"📊 وضعیت: {status_text}\n"
        text += f"📅 {b['created_at'][:10]}\n"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 توقف/اجرا", callback_data=f"toggle_{b['id']}"))
        markup.add(types.InlineKeyboardButton("🗑 حذف", callback_data=f"delete_{b['id']}"))
        
        bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_'))
def toggle_bot(call):
    bot_id = call.data.replace('toggle_', '')
    user_id = call.from_user.id
    
    with get_db() as conn:
        bot_info = conn.execute('SELECT * FROM bots WHERE id = ? AND user_id = ?', (bot_id, user_id)).fetchone()
    
    if not bot_info:
        bot.answer_callback_query(call.id, "❌ ربات پیدا نشد!")
        return
    
    if bot_info['status'] == 'running':
        try:
            os.kill(bot_info['pid'], signal.SIGTERM)
            conn.execute('UPDATE bots SET status = "stopped" WHERE id = ?', (bot_id,))
            conn.commit()
            bot.answer_callback_query(call.id, "✅ ربات متوقف شد")
        except:
            bot.answer_callback_query(call.id, "❌ خطا در توقف!")
    else:
        # راه‌اندازی مجدد
        try:
            with open(bot_info['file_path'], 'r', encoding='utf-8') as f:
                code = f.read()
            
            bot_dir = os.path.join(RUNNING_DIR, bot_id)
            os.makedirs(bot_dir, exist_ok=True)
            
            pid, error = run_bot_code(code, bot_info['token'], bot_dir)
            if pid:
                conn.execute('UPDATE bots SET status = "running", pid = ? WHERE id = ?', (pid, bot_id))
                conn.commit()
                bot.answer_callback_query(call.id, "✅ ربات اجرا شد")
            else:
                bot.answer_callback_query(call.id, f"❌ خطا: {error[:50]}")
        except Exception as e:
            bot.answer_callback_query(call.id, f"❌ خطا: {str(e)[:50]}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
def delete_bot_callback(call):
    bot_id = call.data.replace('delete_', '')
    user_id = call.from_user.id
    
    if delete_bot(bot_id, user_id):
        bot.answer_callback_query(call.id, "✅ ربات حذف شد")
        bot.edit_message_text("🗑 ربات حذف شد.", call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ خطا در حذف")

# ==================== راهنما ====================

@bot.message_handler(func=lambda m: m.text == '📚 راهنما')
def guide(message):
    bot_username = bot.get_me().username
    guide_text = config.guide_text.format(config.price, config.card_number, config.card_holder, bot_username)
    bot.send_message(message.chat.id, guide_text)

# ==================== پشتیبانی ====================

@bot.message_handler(func=lambda m: m.text == '📞 پشتیبانی')
def support(message):
    bot.send_message(message.chat.id, "📞 پشتیبانی: @shahraghee13")

# ==================== پنل ادمین ====================

@bot.message_handler(func=lambda m: m.text == '👑 پنل ادمین')
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ شما دسترسی ادمین ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📸 فیش‌ها", callback_data="admin_receipts"),
        types.InlineKeyboardButton("📥 فایل‌های در انتظار", callback_data="admin_pending_files"),
        types.InlineKeyboardButton("👥 کاربران", callback_data="admin_users"),
        types.InlineKeyboardButton("📊 آمار", callback_data="admin_stats"),
        types.InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings"),
        types.InlineKeyboardButton("💰 تایید دستی اشتراک", callback_data="admin_manual_sub"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    bot.send_message(message.chat.id, "👑 پنل مدیریت:", reply_markup=markup)

# ==================== تنظیمات ادمین ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_settings")
def admin_settings(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📝 تغییر متن خوش‌آمدگویی", callback_data="set_welcome"),
        types.InlineKeyboardButton("💰 تغییر قیمت", callback_data="set_price"),
        types.InlineKeyboardButton("💳 تغییر شماره کارت", callback_data="set_card"),
        types.InlineKeyboardButton("📚 تغییر متن راهنما", callback_data="set_guide"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    bot.edit_message_text(
        "⚙️ تنظیمات:\n\n"
        f"💰 قیمت فعلی: {config.price:,} تومان\n"
        f"💳 شماره کارت: {config.card_number}\n"
        f"👤 صاحب کارت: {config.card_holder}",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "set_welcome")
def set_welcome(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "📝 متن جدید خوش‌آمدگویی را ارسال کنید:\n(از @username برای منشن ربات استفاده کنید)")
    bot.register_next_step_handler(msg, process_set_welcome)

def process_set_welcome(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    config.welcome_text = message.text
    config.save_to_db()
    bot.reply_to(message, "✅ متن خوش‌آمدگویی با موفقیت تغییر کرد!")

@bot.callback_query_handler(func=lambda call: call.data == "set_price")
def set_price(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "💰 قیمت جدید را به تومان وارد کنید:\n(مثال: 250000)")
    bot.register_next_step_handler(msg, process_set_price)

def process_set_price(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        new_price = int(message.text.strip())
        if new_price <= 0:
            raise ValueError
        config.price = new_price
        config.save_to_db()
        bot.reply_to(message, f"✅ قیمت با موفقیت به {new_price:,} تومان تغییر کرد!")
    except:
        bot.reply_to(message, "❌ قیمت نامعتبر! لطفاً یک عدد معتبر وارد کنید.")

@bot.callback_query_handler(func=lambda call: call.data == "set_card")
def set_card(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "💳 شماره کارت جدید را وارد کنید:")
    bot.register_next_step_handler(msg, process_set_card)

def process_set_card(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    card = message.text.strip()
    if len(card) >= 16 and card.isdigit():
        config.card_number = card
        config.save_to_db()
        bot.reply_to(message, f"✅ شماره کارت با موفقیت به {card} تغییر کرد!")
    else:
        bot.reply_to(message, "❌ شماره کارت نامعتبر!")

@bot.callback_query_handler(func=lambda call: call.data == "set_guide")
def set_guide(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "📚 متن جدید راهنما را ارسال کنید:\n(از {} برای قیمت، {} برای شماره کارت، {} برای صاحب کارت، و @username برای منشن استفاده کنید)")
    bot.register_next_step_handler(msg, process_set_guide)

def process_set_guide(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    config.guide_text = message.text
    config.save_to_db()
    bot.reply_to(message, "✅ متن راهنما با موفقیت تغییر کرد!")

# ==================== مدیریت فیش‌ها ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_receipts")
def admin_receipts(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        receipts = conn.execute('''
            SELECT r.*, s.subscription_code 
            FROM receipts r
            JOIN subscriptions s ON r.subscription_id = s.id
            WHERE r.status = 'pending'
            ORDER BY r.created_at DESC
        ''').fetchall()
    
    if not receipts:
        bot.send_message(call.message.chat.id, "📸 فیش در انتظاری وجود ندارد")
        return
    
    for r in receipts:
        text = f"📸 فیش\n"
        text += f"🆔 ID: {r['id']}\n"
        text += f"👤 کاربر: {r['user_id']}\n"
        text += f"💰 مبلغ: {r['amount']:,} تومان\n"
        text += f"🆔 کد اشتراک: {r['subscription_code']}\n"
        text += f"🆔 کد پرداخت: {r['payment_code']}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_payment_{r['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"reject_payment_{r['id']}")
        )
        
        if os.path.exists(r['receipt_path']):
            with open(r['receipt_path'], 'rb') as f:
                bot.send_photo(call.message.chat.id, f, caption=text, reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_payment_'))
def approve_payment(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    receipt_id = int(call.data.replace('approve_payment_', ''))
    
    with get_db() as conn:
        receipt = conn.execute('SELECT * FROM receipts WHERE id = ?', (receipt_id,)).fetchone()
        if receipt:
            conn.execute('UPDATE receipts SET status = "approved", reviewed_at = ?, reviewed_by = ? WHERE id = ?',
                        (datetime.now().isoformat(), call.from_user.id, receipt_id))
            conn.execute('UPDATE subscriptions SET status = "active", paid_at = ? WHERE id = ?',
                        (datetime.now().isoformat(), receipt['subscription_id']))
            
            expire_time = (datetime.now() + timedelta(days=365)).isoformat()
            conn.execute('''
                UPDATE users SET active_subscription = 1, subscription_expire = ?
                WHERE user_id = ?
            ''', (expire_time, receipt['user_id']))
            conn.commit()
            
            try:
                bot.send_message(
                    receipt['user_id'],
                    f"✅ پرداخت شما تایید شد!\n"
                    f"اشتراک شما فعال شد.\n\n"
                    f"📤 حالا می‌توانید از منوی «ارسال فایل ربات» استفاده کنید."
                )
            except:
                pass
    
    bot.answer_callback_query(call.id, "✅ پرداخت تایید شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_payment_'))
def reject_payment(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    receipt_id = int(call.data.replace('reject_payment_', ''))
    
    with get_db() as conn:
        receipt = conn.execute('SELECT * FROM receipts WHERE id = ?', (receipt_id,)).fetchone()
        if receipt:
            conn.execute('UPDATE receipts SET status = "rejected", reviewed_at = ?, reviewed_by = ? WHERE id = ?',
                        (datetime.now().isoformat(), call.from_user.id, receipt_id))
            conn.execute('DELETE FROM subscriptions WHERE id = ?', (receipt['subscription_id'],))
            conn.commit()
            
            try:
                bot.send_message(
                    receipt['user_id'],
                    f"❌ متاسفانه پرداخت شما تایید نشد.\n"
                    f"لطفاً با پشتیبانی تماس بگیرید: @shahraghee13"
                )
            except:
                pass
    
    bot.answer_callback_query(call.id, "❌ پرداخت رد شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== مدیریت فایل‌های در انتظار ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_pending_files")
def admin_pending_files(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        pending = conn.execute('''
            SELECT pf.*, u.username, u.first_name
            FROM pending_files pf
            JOIN users u ON pf.user_id = u.user_id
            WHERE pf.status = 'pending'
            ORDER BY pf.submitted_at DESC
        ''').fetchall()
    
    if not pending:
        bot.send_message(call.message.chat.id, "📥 فایل در انتظاری وجود ندارد")
        return
    
    for p in pending:
        text = f"📥 فایل در انتظار بررسی\n"
        text += f"🆔 ID: {p['id']}\n"
        text += f"👤 کاربر: {p['user_id']}\n"
        text += f"👤 نام: {p['first_name']}\n"
        text += f"📄 فایل: {p['file_name']}\n"
        text += f"📅 تاریخ: {p['submitted_at'][:10]}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید و ساخت", callback_data=f"approve_file_{p['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"reject_file_{p['id']}")
        )
        
        if os.path.exists(p['file_path']):
            with open(p['file_path'], 'rb') as f:
                bot.send_document(call.message.chat.id, f, caption=text, reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_file_'))
def approve_file(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    pending_id = int(call.data.replace('approve_file_', ''))
    
    with get_db() as conn:
        pending = conn.execute('''
            SELECT pf.*, s.user_id as sub_user_id
            FROM pending_files pf
            JOIN subscriptions s ON pf.subscription_id = s.id
            WHERE pf.id = ?
        ''', (pending_id,)).fetchone()
        
        if not pending:
            bot.answer_callback_query(call.id, "❌ فایل پیدا نشد!")
            return
        
        # خواندن فایل و استخراج توکن
        try:
            with open(pending['file_path'], 'r', encoding='utf-8') as f:
                code = f.read()
            
            token = extract_token_from_code(code)
            if not token:
                bot.answer_callback_query(call.id, "❌ توکن در کد پیدا نشد!")
                return
            
            # بررسی توکن
            response = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
            if response.status_code != 200:
                bot.answer_callback_query(call.id, "❌ توکن معتبر نیست!")
                return
            
            bot_info = response.json()['result']
            bot_name = bot_info['first_name']
            bot_username = bot_info['username']
            
            # ساخت ربات
            bot_id = hashlib.md5(f"{pending['user_id']}_{token}_{time.time()}".encode()).hexdigest()[:10]
            bot_dir = os.path.join(RUNNING_DIR, bot_id)
            os.makedirs(bot_dir, exist_ok=True)
            
            pid, error = run_bot_code(code, token, bot_dir)
            
            if pid:
                # ذخیره در دیتابیس
                now = datetime.now().isoformat()
                conn.execute('UPDATE pending_files SET status = "approved", reviewed_at = ? WHERE id = ?', (now, pending_id))
                conn.execute('''
                    INSERT INTO bots (id, user_id, subscription_id, token, name, username, file_path, pid, status, created_at, last_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'running', ?, ?)
                ''', (bot_id, pending['user_id'], pending['subscription_id'], token, bot_name, bot_username, pending['file_path'], pid, now, now))
                conn.execute('UPDATE users SET active_subscription = 0 WHERE user_id = ?', (pending['user_id'],))
                conn.commit()
                
                # پیام به کاربر
                try:
                    bot.send_message(
                        pending['user_id'],
                        f"✅ ربات شما با موفقیت ساخته شد! 🎉\n\n"
                        f"🤖 نام: {bot_name}\n"
                        f"🔗 لینک: https://t.me/{bot_username}\n"
                        f"🆔 آیدی: {bot_id}\n\n"
                        f"📋 برای مشاهده ربات‌های خود از منوی «ربات‌های من» استفاده کنید."
                    )
                except:
                    pass
                
                bot.answer_callback_query(call.id, "✅ ربات ساخته شد")
                bot.delete_message(call.message.chat.id, call.message.message_id)
            else:
                bot.answer_callback_query(call.id, f"❌ خطا در اجرا: {error[:50]}")
                
        except Exception as e:
            bot.answer_callback_query(call.id, f"❌ خطا: {str(e)[:50]}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_file_'))
def reject_file_callback(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    pending_id = int(call.data.replace('reject_file_', ''))
    
    msg = bot.send_message(call.message.chat.id, "❌ دلیل رد فایل را وارد کنید:")
    bot.register_next_step_handler(msg, lambda m: process_reject_file(m, pending_id, call))

def process_reject_file(message, pending_id, original_call):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    reason = message.text
    
    with get_db() as conn:
        pending = conn.execute('SELECT user_id FROM pending_files WHERE id = ?', (pending_id,)).fetchone()
        if pending:
            conn.execute('UPDATE pending_files SET status = "rejected", reviewed_at = ?, review_note = ? WHERE id = ?',
                        (datetime.now().isoformat(), reason, pending_id))
            conn.execute('UPDATE users SET active_subscription = 0 WHERE user_id = ?', (pending['user_id'],))
            conn.commit()
            
            try:
                bot.send_message(
                    pending['user_id'],
                    f"❌ متاسفانه فایل ربات شما تایید نشد.\n\n"
                    f"دلیل: {reason}\n\n"
                    f"لطفاً فایل را اصلاح کرده و دوباره ارسال کنید."
                )
            except:
                pass
    
    bot.reply_to(message, f"✅ فایل کاربر {pending['user_id']} رد شد")
    try:
        bot.delete_message(original_call.message.chat.id, original_call.message.message_id)
    except:
        pass

# ==================== سایر بخش‌های ادمین ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_users")
def admin_users(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        users = conn.execute('''
            SELECT user_id, username, first_name, active_subscription, created_at
            FROM users ORDER BY created_at DESC LIMIT 20
        ''').fetchall()
    
    text = "👥 ۲۰ کاربر آخر:\n\n"
    for u in users:
        status = "✅ فعال" if u['active_subscription'] else "❌ غیرفعال"
        text += f"🆔 {u['user_id']} - {u['first_name']}\n"
        text += f"   {status}\n"
        text += f"   📅 {u['created_at'][:10]}\n\n"
    
    bot.send_message(call.message.chat.id, text)

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_stats(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        total_users = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        active_subs = conn.execute('SELECT COUNT(*) FROM users WHERE active_subscription = 1').fetchone()[0]
        total_bots = conn.execute('SELECT COUNT(*) FROM bots').fetchone()[0]
        total_payments = conn.execute('SELECT COUNT(*) FROM receipts WHERE status = "approved"').fetchone()[0]
        pending_payments = conn.execute('SELECT COUNT(*) FROM receipts WHERE status = "pending"').fetchone()[0]
        pending_files = conn.execute('SELECT COUNT(*) FROM pending_files WHERE status = "pending"').fetchone()[0]
        total_amount = conn.execute('SELECT COALESCE(SUM(amount), 0) FROM receipts WHERE status = "approved"').fetchone()[0]
    
    text = f"📊 آمار کامل\n\n"
    text += f"👥 کل کاربران: {total_users}\n"
    text += f"✅ اشتراک فعال: {active_subs}\n"
    text += f"🤖 کل ربات‌ها: {total_bots}\n\n"
    text += f"💰 پرداخت‌ها:\n"
    text += f"• مجموع: {total_amount:,} تومان\n"
    text += f"• تایید شده: {total_payments}\n"
    text += f"• در انتظار: {pending_payments}\n\n"
    text += f"📥 فایل‌های در انتظار: {pending_files}"
    
    bot.send_message(call.message.chat.id, text)

@bot.callback_query_handler(func=lambda call: call.data == "admin_manual_sub")
def admin_manual_sub(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "💰 آیدی کاربر را برای تایید دستی اشتراک وارد کنید:")
    bot.register_next_step_handler(msg, process_manual_sub)

def process_manual_sub(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        user_id = int(message.text.strip())
        
        with get_db() as conn:
            # غیرفعال کردن اشتراک قبلی
            conn.execute('UPDATE users SET active_subscription = 0 WHERE user_id = ?', (user_id,))
            
            # ایجاد اشتراک جدید
            sub_code = hashlib.md5(f"manual_{user_id}_{time.time()}".encode()).hexdigest()[:12].upper()
            expire_time = (datetime.now() + timedelta(days=365)).isoformat()
            
            conn.execute('''
                INSERT INTO subscriptions (user_id, subscription_code, amount, status, paid_at)
                VALUES (?, ?, ?, 'active', ?)
            ''', (user_id, sub_code, config.price, datetime.now().isoformat()))
            
            conn.execute('''
                UPDATE users SET active_subscription = 1, subscription_expire = ?
                WHERE user_id = ?
            ''', (expire_time, user_id))
            conn.commit()
            
            try:
                bot.send_message(
                    user_id,
                    f"✅ اشتراک شما به صورت دستی فعال شد!\n\n"
                    f"📤 حالا می‌توانید از منوی «ارسال فایل ربات» استفاده کنید."
                )
            except:
                pass
        
        bot.reply_to(message, f"✅ اشتراک کاربر {user_id} فعال شد")
    except ValueError:
        bot.reply_to(message, "❌ آیدی باید عدد باشد")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call):
    user_id = call.from_user.id
    is_admin = user_id in ADMIN_IDS
    markup = get_admin_menu() if is_admin else get_main_menu()
    
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "🚀 منوی اصلی:", reply_markup=markup)

# ==================== اجرا ====================

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 ربات مادر - نسخه امن با سیستم اشتراک")
    print("=" * 60)
    print(f"✅ دیتابیس: بهینه شده برای میلیون‌ها کاربر")
    print(f"✅ ادمین: {ADMIN_IDS}")
    print(f"✅ قیمت فعلی: {config.price:,} تومان")
    print("=" * 60)
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            print(f"خطا: {e}")
            time.sleep(5)
