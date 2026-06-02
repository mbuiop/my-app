#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ربات مادر نهایی - نسخه پایدار با رفع خطای Markdown
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

# ==================== تنظیمات پایه ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "database")
FILES_DIR = os.path.join(BASE_DIR, "user_files")
RUNNING_DIR = os.path.join(BASE_DIR, "running_bots")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
RECEIPTS_DIR = os.path.join(BASE_DIR, "receipts")
FOLDERS_DIR = os.path.join(BASE_DIR, "user_folders")

for d in [DB_DIR, FILES_DIR, RUNNING_DIR, LOGS_DIR, RECEIPTS_DIR, FOLDERS_DIR]:
    os.makedirs(d, exist_ok=True)

# ==================== توکن و تنظیمات ====================
BOT_TOKEN = "7685135237:AAEmsHktRw9cEqrHTkCoPZk-fBimK7TDjOo"
ADMIN_IDS = [327855654]
BOT_USERNAME = "ROBTTSAZE_bot"

# تنظیمات مالی
SUBSCRIPTION_PRICE = 2000000
SUBSCRIPTION_PRICE_STR = "۲,۰۰۰,۰۰۰ تومان"
CARD_NUMBER = "5892101187322777"
CARD_NUMBER_DISPLAY = "5892 1011 8732 2777"
CARD_HOLDER = "مرتضی نیکخو خنجری"
CARD_BANK = "بانک ملی"
WITHDRAW_PERCENT = 7
MIN_WITHDRAW = 2000000
MAX_BOTS_PER_USER = 3

# ==================== دیتابیس ====================
DB_PATH = os.path.join(DB_DIR, 'mother_bot.db')

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

# ایجاد جداول
with get_db() as conn:
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            balance INTEGER DEFAULT 0,
            bots_count INTEGER DEFAULT 0,
            max_bots INTEGER DEFAULT 3,
            referral_code TEXT UNIQUE,
            referred_by INTEGER,
            referrals_count INTEGER DEFAULT 0,
            verified_referrals INTEGER DEFAULT 0,
            subscription_status TEXT DEFAULT 'inactive',
            subscription_expiry TIMESTAMP,
            created_at TIMESTAMP,
            last_active TIMESTAMP
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS bots (
            id TEXT PRIMARY KEY,
            user_id INTEGER,
            token TEXT,
            name TEXT,
            username TEXT,
            file_path TEXT,
            folder_path TEXT,
            folder_id TEXT,
            pid INTEGER,
            status TEXT DEFAULT 'stopped',
            created_at TIMESTAMP,
            last_active TIMESTAMP,
            execution_count INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS folders (
            id TEXT PRIMARY KEY,
            user_id INTEGER,
            folder_name TEXT,
            folder_path TEXT,
            parent_id TEXT,
            created_at TIMESTAMP,
            file_count INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS folder_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folder_id TEXT,
            file_name TEXT,
            file_path TEXT,
            file_size INTEGER,
            added_at TIMESTAMP,
            FOREIGN KEY(folder_id) REFERENCES folders(id) ON DELETE CASCADE
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            receipt_path TEXT,
            status TEXT DEFAULT 'pending',
            payment_code TEXT UNIQUE,
            created_at TIMESTAMP,
            reviewed_at TIMESTAMP,
            reviewed_by INTEGER
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS withdraw_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            card_number TEXT,
            card_holder TEXT,
            bank_name TEXT,
            status TEXT DEFAULT 'pending',
            tracking_code TEXT,
            created_at TIMESTAMP,
            processed_at TIMESTAMP
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS libraries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            version TEXT,
            installed_at TIMESTAMP
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP
        )
    ''')
    
    # تنظیمات پیش‌فرض
    default_settings = {
        'subscription_price': str(SUBSCRIPTION_PRICE),
        'subscription_price_str': SUBSCRIPTION_PRICE_STR,
        'card_number': CARD_NUMBER,
        'card_number_display': CARD_NUMBER_DISPLAY,
        'card_holder': CARD_HOLDER,
        'card_bank': CARD_BANK,
        'withdraw_percent': str(WITHDRAW_PERCENT),
        'min_withdraw': str(MIN_WITHDRAW),
        'max_bots_per_user': str(MAX_BOTS_PER_USER),
    }
    
    for key, value in default_settings.items():
        conn.execute("INSERT OR IGNORE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
                    (key, value, datetime.now().isoformat()))
    
    conn.commit()

# ==================== توابع کمکی ====================
def get_setting(key):
    with get_db() as conn:
        result = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        if result:
            return result['value']
    return None

def get_user(user_id):
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return dict(user) if user else None

def create_user(user_id, username, first_name, last_name, referred_by=None):
    now = datetime.now().isoformat()
    referral_code = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:10]
    
    with get_db() as conn:
        conn.execute('''
            INSERT OR IGNORE INTO users 
            (user_id, username, first_name, last_name, referral_code, referred_by, created_at, last_active, subscription_status, max_bots)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'inactive', ?)
        ''', (user_id, username, first_name, last_name, referral_code, referred_by, now, now, MAX_BOTS_PER_USER))
        
        if referred_by and referred_by != user_id:
            conn.execute("UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = ?", (referred_by,))
        conn.commit()
    
    return True

def check_subscription(user_id):
    user = get_user(user_id)
    if not user:
        return False
    if user['subscription_status'] == 'active':
        if user['subscription_expiry']:
            expiry = datetime.fromisoformat(user['subscription_expiry'])
            if expiry > datetime.now():
                return True
    return False

def activate_subscription(user_id):
    expiry = datetime.now() + timedelta(days=30)
    with get_db() as conn:
        conn.execute('''
            UPDATE users SET subscription_status = 'active', subscription_expiry = ?
            WHERE user_id = ?
        ''', (expiry.isoformat(), user_id))
        conn.commit()
    return expiry

def add_wallet_balance(user_id, amount):
    with get_db() as conn:
        conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        conn.commit()

def get_user_bots_count(user_id):
    with get_db() as conn:
        result = conn.execute("SELECT COUNT(*) as c FROM bots WHERE user_id = ?", (user_id,)).fetchone()
        return result['c'] if result else 0

def can_create_bot(user_id):
    max_bots = int(get_setting('max_bots_per_user') or 3)
    current_bots = get_user_bots_count(user_id)
    return current_bots < max_bots, max_bots, current_bots

def extract_token_from_code(code):
    patterns = [
        r'token\s*=\s*["\']([^"\']+)["\']',
        r'TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'BOT_TOKEN\s*=\s*["\']([^"\']+)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, code, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

def verify_token(token):
    try:
        resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        if resp.status_code == 200:
            return True, resp.json().get('result', {})
        return False, {}
    except:
        return False, {}

# ==================== موتور اجرا ====================
class BotEngine:
    def __init__(self):
        self.active = {}
        self.lock = threading.RLock()
    
    def execute(self, bot_id, user_id, code, folder_path=None):
        bot_dir = os.path.join(RUNNING_DIR, bot_id)
        os.makedirs(bot_dir, exist_ok=True)
        code_path = os.path.join(bot_dir, 'bot.py')
        
        with open(code_path, 'w', encoding='utf-8') as f:
            f.write(code)
        
        cwd = folder_path if folder_path and os.path.exists(folder_path) else bot_dir
        
        try:
            process = subprocess.Popen(
                [sys.executable, code_path],
                cwd=cwd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            
            with self.lock:
                self.active[bot_id] = {
                    'process': process,
                    'pid': process.pid,
                    'started_at': time.time()
                }
            
            return True, None
        except Exception as e:
            return False, str(e)
    
    def stop(self, bot_id):
        with self.lock:
            if bot_id in self.active:
                try:
                    self.active[bot_id]['process'].terminate()
                    time.sleep(1)
                    del self.active[bot_id]
                    return True
                except:
                    pass
        return False
    
    def is_running(self, bot_id):
        with self.lock:
            if bot_id in self.active:
                if self.active[bot_id]['process'].poll() is None:
                    return True
                else:
                    del self.active[bot_id]
        return False
    
    def get_status(self, bot_id):
        running = self.is_running(bot_id)
        if running:
            with self.lock:
                uptime = int(time.time() - self.active[bot_id]['started_at'])
                return {'running': True, 'uptime': uptime}
        return {'running': False}

engine = BotEngine()

# ==================== مدیریت پوشه ====================
class FolderManager:
    def create_folder(self, user_id, folder_name, parent_id=None):
        folder_path = os.path.join(FOLDERS_DIR, str(user_id), folder_name)
        if parent_id:
            with get_db() as conn:
                parent = conn.execute("SELECT folder_path FROM folders WHERE id = ?", (parent_id,)).fetchone()
                if parent:
                    folder_path = os.path.join(parent['folder_path'], folder_name)
        
        if os.path.exists(folder_path):
            return None, "پوشه وجود دارد"
        
        os.makedirs(folder_path, exist_ok=True)
        folder_id = hashlib.md5(f"{user_id}_{folder_name}_{time.time()}".encode()).hexdigest()[:12]
        
        with get_db() as conn:
            conn.execute('''
                INSERT INTO folders (id, user_id, folder_name, folder_path, parent_id, created_at, file_count)
                VALUES (?, ?, ?, ?, ?, ?, 0)
            ''', (folder_id, user_id, folder_name, folder_path, parent_id, datetime.now().isoformat()))
            conn.commit()
        
        return folder_id, "پوشه ساخته شد"
    
    def add_file(self, folder_id, file_name, content):
        with get_db() as conn:
            folder = conn.execute("SELECT folder_path FROM folders WHERE id = ?", (folder_id,)).fetchone()
            if not folder:
                return False, "پوشه یافت نشد"
            
            file_path = os.path.join(folder['folder_path'], file_name)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            conn.execute('''
                INSERT INTO folder_files (folder_id, file_name, file_path, file_size, added_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (folder_id, file_name, file_path, len(content), datetime.now().isoformat()))
            conn.execute("UPDATE folders SET file_count = file_count + 1 WHERE id = ?", (folder_id,))
            conn.commit()
            return True, "فایل اضافه شد"
    
    def get_files(self, folder_id):
        with get_db() as conn:
            files = conn.execute("SELECT file_name, file_size FROM folder_files WHERE folder_id = ?", (folder_id,)).fetchall()
            return [dict(f) for f in files]
    
    def read_file(self, folder_id, file_name):
        with get_db() as conn:
            file_info = conn.execute("SELECT file_path FROM folder_files WHERE folder_id = ? AND file_name = ?", (folder_id, file_name)).fetchone()
            if file_info and os.path.exists(file_info['file_path']):
                with open(file_info['file_path'], 'r', encoding='utf-8') as f:
                    return f.read()
        return None

folder_manager = FolderManager()

# ==================== کتابخانه منیجر ====================
class LibraryManager:
    def install(self, lib_name, chat_id, message_id, bot_instance):
        def install_thread():
            try:
                bot_instance.edit_message_text(f"🔄 در حال نصب {lib_name}...", chat_id, message_id)
                
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", lib_name, "--quiet"],
                    capture_output=True, text=True, timeout=120
                )
                
                if result.returncode == 0:
                    bot_instance.edit_message_text(f"✅ {lib_name} نصب شد!", chat_id, message_id)
                    with get_db() as conn:
                        conn.execute("INSERT OR IGNORE INTO libraries (name, installed_at) VALUES (?, ?)",
                                    (lib_name, datetime.now().isoformat()))
                        conn.commit()
                else:
                    error = result.stderr[:200] if result.stderr else "خطا"
                    bot_instance.edit_message_text(f"❌ خطا: {error}", chat_id, message_id)
            except Exception as e:
                bot_instance.edit_message_text(f"❌ خطا: {str(e)[:100]}", chat_id, message_id)
        
        threading.Thread(target=install_thread, daemon=True).start()
        return True

library_manager = LibraryManager()

# ==================== ربات اصلی ====================
bot = telebot.TeleBot(BOT_TOKEN)
bot.remove_webhook()

# ==================== منوی اصلی (بدون Markdown مشکل‌دار) ====================
def get_main_menu(user_id):
    is_admin = user_id in ADMIN_IDS
    has_subscription = check_subscription(user_id)
    
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    
    if has_subscription:
        buttons = [
            types.KeyboardButton('🤖 ساخت ربات جدید'),
            types.KeyboardButton('📁 مدیریت پوشه'),
            types.KeyboardButton('▶️ اجرای ربات'),
            types.KeyboardButton('🛑 توقف ربات'),
            types.KeyboardButton('📋 لیست ربات ها'),
            types.KeyboardButton('🗑 حذف ربات'),
        ]
    else:
        buttons = [types.KeyboardButton('💰 خرید اشتراک')]
    
    buttons.extend([
        types.KeyboardButton('💰 کیف پول'),
        types.KeyboardButton('👥 دعوت دوستان'),
        types.KeyboardButton('💸 درخواست برداشت'),
        types.KeyboardButton('📦 کتابخانه ها'),
        types.KeyboardButton('📚 راهنما'),
        types.KeyboardButton('📊 آمار'),
        types.KeyboardButton('📞 پشتیبانی'),
    ])
    
    if is_admin:
        buttons.extend([
            types.KeyboardButton('👑 پنل مدیریت'),
            types.KeyboardButton('📢 پیام همگانی')
        ])
    
    markup.add(*buttons)
    return markup

# ==================== دستور start (بدون Markdown) ====================
@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or ""
    username = message.from_user.username or ""
    
    referred_by = None
    args = message.text.split()
    if len(args) > 1:
        code = args[1]
        with get_db() as conn:
            referrer = conn.execute("SELECT user_id FROM users WHERE referral_code = ?", (code,)).fetchone()
            if referrer and referrer['user_id'] != user_id:
                referred_by = referrer['user_id']
                try:
                    bot.send_message(referred_by, f"🎉 {first_name} با لینک شما وارد شد!")
                except:
                    pass
    
    create_user(user_id, username, first_name, message.from_user.last_name or "", referred_by)
    user = get_user(user_id)
    bot_username = bot.get_me().username
    
    has_subscription = check_subscription(user_id)
    
    # ساخت پیام ساده بدون Markdown
    text = f"""🚀 به ربات مادر خوش آمدید {first_name}!

👤 شناسه: {user_id}
🎁 کد معرف: {user['referral_code']}
🔗 لینک دعوت: https://t.me/{bot_username}?start={user['referral_code']}
💰 موجودی: {user['balance']:,} تومان

"""
    if has_subscription:
        expiry = datetime.fromisoformat(user['subscription_expiry'])
        text += f"✅ اشتراک فعال تا: {expiry.strftime('%Y-%m-%d')}\n"
        text += f"🤖 ربات ساخته شده: {get_user_bots_count(user_id)}/{get_setting('max_bots_per_user')}"
    else:
        text += f"❌ اشتراک شما فعال نیست!\n"
        text += f"💰 قیمت اشتراک: {get_setting('subscription_price_str')}\n\n"
        text += "برای فعال سازی از دکمه خرید اشتراک استفاده کنید."
    
    bot.send_message(message.chat.id, text, reply_markup=get_main_menu(user_id))

# ==================== خرید اشتراک ====================
@bot.message_handler(func=lambda m: m.text == '💰 خرید اشتراک')
def buy_subscription(message):
    user_id = message.from_user.id
    
    if check_subscription(user_id):
        bot.send_message(message.chat.id, "✅ شما قبلاً اشتراک فعال دارید!")
        return
    
    price = get_setting('subscription_price_str')
    card = get_setting('card_number_display')
    holder = get_setting('card_holder')
    bank = get_setting('card_bank')
    
    text = f"""💳 خرید اشتراک ماهیانه

💰 مبلغ: {price}

🏦 اطلاعات کارت:
{card}
👤 {holder}
🏦 {bank}

📌 نحوه پرداخت:
1️⃣ مبلغ را به کارت فوق واریز کنید
2️⃣ رسید را به صورت عکس ارسال کنید
3️⃣ پس از تایید، اشتراک شما فعال می‌شود

⏱ زمان بررسی: حداکثر 24 ساعت

⚠️ توجه: پس از فعال سازی، می توانید تا {get_setting('max_bots_per_user')} ربات بسازید!"""
    
    bot.send_message(message.chat.id, text)

# ==================== فیش پرداخت ====================
@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        payment_code = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:8].upper()
        receipt_path = os.path.join(RECEIPTS_DIR, f"{user_id}_{payment_code}.jpg")
        
        with open(receipt_path, 'wb') as f:
            f.write(downloaded)
        
        with get_db() as conn:
            conn.execute('''
                INSERT INTO receipts (user_id, amount, receipt_path, payment_code, created_at, status)
                VALUES (?, ?, ?, ?, ?, 'pending')
            ''', (user_id, SUBSCRIPTION_PRICE, receipt_path, payment_code, datetime.now().isoformat()))
            conn.commit()
        
        bot.reply_to(message, 
                    f"✅ فیش شما دریافت شد!\n\n"
                    f"💰 مبلغ: {SUBSCRIPTION_PRICE_STR}\n"
                    f"🆔 کد پیگیری: {payment_code}\n\n"
                    f"⏱ ظرف 24 ساعت بررسی می شود.")
        
        for admin_id in ADMIN_IDS:
            try:
                with open(receipt_path, 'rb') as f:
                    bot.send_photo(admin_id, f, caption=f"📸 فیش جدید\n👤 {user_id}\n💰 {SUBSCRIPTION_PRICE_STR}")
            except:
                pass
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")

# ==================== ساخت ربات جدید ====================
@bot.message_handler(func=lambda m: m.text == '🤖 ساخت ربات جدید')
def new_bot(message):
    user_id = message.from_user.id
    
    if not check_subscription(user_id):
        bot.send_message(message.chat.id, 
                        f"❌ اشتراک شما فعال نیست!\n💰 قیمت اشتراک: {get_setting('subscription_price_str')}\nاز دکمه خرید اشتراک استفاده کنید.")
        return
    
    can_create, max_bots, current_bots = can_create_bot(user_id)
    if not can_create:
        bot.send_message(message.chat.id, 
                        f"⚠️ شما به حداکثر مجاز {max_bots} ربات رسیده اید!\nبرای ساخت ربات جدید، ابتدا یکی از ربات های خود را حذف کنید.")
        return
    
    bot.send_message(message.chat.id, 
                    f"📤 ارسال فایل ربات\n\n"
                    f"فایل py. یا zip. خود را ارسال کنید.\n"
                    f"✅ حداکثر حجم: 50 مگابایت\n"
                    f"✅ توکن داخل کد باشد\n"
                    f"✅ حداکثر {max_bots} ربات فعال")

# ==================== آپلود فایل ====================
@bot.message_handler(content_types=['document'])
def handle_build_file(message):
    user_id = message.from_user.id
    file_name = message.document.file_name
    
    if not check_subscription(user_id):
        bot.reply_to(message, "❌ اشتراک فعال نیست!")
        return
    
    if not (file_name.endswith('.py') or file_name.endswith('.zip')):
        bot.reply_to(message, "❌ فقط فایل های py. یا zip. مجاز هستند!")
        return
    
    if message.document.file_size > 50 * 1024 * 1024:
        bot.reply_to(message, "❌ حجم بیشتر از 50 مگابایت!")
        return
    
    can_create, max_bots, current_bots = can_create_bot(user_id)
    if not can_create:
        bot.reply_to(message, f"❌ حداکثر {max_bots} ربات!")
        return
    
    status_msg = bot.reply_to(message, "🔄 در حال پردازش فایل...")
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        user_dir = os.path.join(FILES_DIR, str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        file_path = os.path.join(user_dir, f"{int(time.time())}_{file_name}")
        
        with open(file_path, 'wb') as f:
            f.write(downloaded)
        
        # استخراج کد
        code = ""
        if file_name.endswith('.zip'):
            extract_dir = os.path.join(FILES_DIR, str(user_id), f"extract_{int(time.time())}")
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(file_path, 'r') as zf:
                zf.extractall(extract_dir)
            
            for root, _, files in os.walk(extract_dir):
                for f in files:
                    if f.endswith('.py'):
                        with open(os.path.join(root, f), 'r', encoding='utf-8', errors='ignore') as cf:
                            code = cf.read()
                            break
                if code:
                    break
            shutil.rmtree(extract_dir, ignore_errors=True)
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
        
        if not code:
            bot.edit_message_text("❌ فایل پایتون پیدا نشد!", message.chat.id, status_msg.message_id)
            return
        
        token = extract_token_from_code(code)
        if not token:
            bot.edit_message_text("❌ توکن در کد پیدا نشد!", message.chat.id, status_msg.message_id)
            return
        
        valid, bot_info = verify_token(token)
        if not valid:
            bot.edit_message_text("❌ توکن نامعتبر است!", message.chat.id, status_msg.message_id)
            return
        
        bot_id = hashlib.md5(f"{user_id}{token}{time.time()}".encode()).hexdigest()[:12]
        
        with get_db() as conn:
            conn.execute('''
                INSERT INTO bots (id, user_id, token, name, username, file_path, status, created_at, last_active, execution_count)
                VALUES (?, ?, ?, ?, ?, ?, 'stopped', ?, ?, 0)
            ''', (bot_id, user_id, token, bot_info['first_name'], bot_info['username'], file_path, 
                  datetime.now().isoformat(), datetime.now().isoformat()))
            conn.execute("UPDATE users SET bots_count = bots_count + 1 WHERE user_id = ?", (user_id,))
            conn.commit()
        
        # اجرا
        success, error = engine.execute(bot_id, user_id, code)
        
        if success:
            with get_db() as conn:
                conn.execute("UPDATE bots SET status = 'running' WHERE id = ?", (bot_id,))
                conn.commit()
            
            # کمیسیون به معرف
            user = get_user(user_id)
            if user and user.get('referred_by'):
                commission = int(SUBSCRIPTION_PRICE * WITHDRAW_PERCENT / 100)
                add_wallet_balance(user['referred_by'], commission)
                try:
                    bot.send_message(user['referred_by'], 
                                   f"🎉 کمیسیون دعوت!\n\nکاربر {user['first_name']} اشتراک خرید.\n💰 مبلغ کمیسیون: {commission:,} تومان")
                except:
                    pass
            
            reply = f"✅ ربات با موفقیت ساخته شد!\n\n"
            reply += f"🤖 نام: {bot_info['first_name']}\n"
            reply += f"🔗 t.me/{bot_info['username']}\n"
            reply += f"🆔 شناسه: {bot_id}\n\n"
            reply += f"✅ ربات در حال اجراست!\nبرای توقف از منوی توقف ربات استفاده کنید."
            
            bot.edit_message_text(reply, message.chat.id, status_msg.message_id)
        else:
            bot.edit_message_text(f"❌ خطا در اجرا: {error}", message.chat.id, status_msg.message_id)
        
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)[:200]}", message.chat.id, status_msg.message_id)

# ==================== مدیریت پوشه ====================
@bot.message_handler(func=lambda m: m.text == '📁 مدیریت پوشه')
def manage_folders(message):
    user_id = message.from_user.id
    
    if not check_subscription(user_id):
        bot.send_message(message.chat.id, "❌ ابتدا اشتراک خود را فعال کنید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📁 ساخت پوشه جدید", callback_data="create_folder"),
        types.InlineKeyboardButton("📂 لیست پوشه ها", callback_data="list_folders")
    )
    
    bot.send_message(message.chat.id, "📁 مدیریت پوشه ها", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "create_folder")
def create_folder_prompt(call):
    msg = bot.send_message(call.message.chat.id, "📁 نام پوشه را وارد کنید:")
    bot.register_next_step_handler(msg, process_create_folder)
    bot.answer_callback_query(call.id)

def process_create_folder(message):
    user_id = message.from_user.id
    name = message.text.strip()
    
    if not re.match(r'^[a-zA-Z0-9_\-]+$', name):
        bot.reply_to(message, "❌ نام نامعتبر!")
        return
    
    folder_id, result = folder_manager.create_folder(user_id, name)
    if folder_id:
        bot.reply_to(message, f"✅ {result}\n🆔 شناسه: {folder_id}")
    else:
        bot.reply_to(message, f"❌ {result}")

@bot.callback_query_handler(func=lambda call: call.data == "list_folders")
def list_folders(call):
    user_id = call.from_user.id
    
    with get_db() as conn:
        folders = conn.execute("SELECT id, folder_name, file_count FROM folders WHERE user_id = ?", (user_id,)).fetchall()
    
    if not folders:
        bot.send_message(call.message.chat.id, "📂 پوشه ای ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for f in folders:
        markup.add(types.InlineKeyboardButton(f"📂 {f['folder_name']} ({f['file_count']} فایل)", 
                                             callback_data=f"view_folder_{f['id']}"))
    
    bot.edit_message_text("📂 پوشه های شما:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('view_folder_'))
def view_folder(call):
    folder_id = call.data.replace('view_folder_', '')
    files = folder_manager.get_files(folder_id)
    
    with get_db() as conn:
        folder = conn.execute("SELECT folder_name FROM folders WHERE id = ?", (folder_id,)).fetchone()
    
    if not folder:
        bot.answer_callback_query(call.id, "پوشه یافت نشد!")
        return
    
    text = f"📁 {folder['folder_name']}\n🆔 {folder_id}\n📄 فایل ها: {len(files)}\n\n"
    
    if files:
        text += "فایل ها:\n"
        for f in files:
            text += f"• {f['file_name']} ({f['file_size']} بایت)\n"
    else:
        text += "📂 فایلی وجود ندارد"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("📄 افزودن فایل", callback_data=f"add_file_{folder_id}"))
    markup.add(types.InlineKeyboardButton("▶️ اجرا", callback_data=f"run_folder_{folder_id}"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="list_folders"))
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('add_file_'))
def add_file_prompt(call):
    folder_id = call.data.replace('add_file_', '')
    msg = bot.send_message(call.message.chat.id, "📄 نام فایل را وارد کنید:\n(مثال: main.py)")
    bot.register_next_step_handler(msg, process_add_file_name, folder_id)
    bot.answer_callback_query(call.id)

def process_add_file_name(message, folder_id):
    file_name = message.text.strip()
    if not file_name.endswith('.py'):
        bot.reply_to(message, "❌ فقط فایل های py. مجاز!")
        return
    
    msg = bot.send_message(message.chat.id, f"📝 محتوای {file_name} را ارسال کنید:")
    bot.register_next_step_handler(msg, process_add_file_content, folder_id, file_name)

def process_add_file_content(message, folder_id, file_name):
    content = message.text
    success, result = folder_manager.add_file(folder_id, file_name, content)
    bot.reply_to(message, f"✅ {result}" if success else f"❌ {result}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('run_folder_'))
def run_folder(call):
    user_id = call.from_user.id
    folder_id = call.data.replace('run_folder_', '')
    
    if not check_subscription(user_id):
        bot.answer_callback_query(call.id, "❌ اشتراک فعال نیست!", show_alert=True)
        return
    
    code = folder_manager.read_file(folder_id, 'main.py')
    if not code:
        bot.answer_callback_query(call.id, "❌ فایل main.py یافت نشد!", show_alert=True)
        return
    
    token = extract_token_from_code(code)
    if not token:
        bot.answer_callback_query(call.id, "❌ توکن پیدا نشد!", show_alert=True)
        return
    
    valid, bot_info = verify_token(token)
    if not valid:
        bot.answer_callback_query(call.id, "❌ توکن نامعتبر!", show_alert=True)
        return
    
    can_create, max_bots, current_bots = can_create_bot(user_id)
    if not can_create:
        bot.answer_callback_query(call.id, f"❌ حداکثر {max_bots} ربات!", show_alert=True)
        return
    
    with get_db() as conn:
        folder = conn.execute("SELECT folder_path FROM folders WHERE id = ?", (folder_id,)).fetchone()
        folder_path = folder['folder_path'] if folder else None
    
    bot_id = hashlib.md5(f"{user_id}{token}{time.time()}".encode()).hexdigest()[:12]
    
    with get_db() as conn:
        conn.execute('''
            INSERT INTO bots (id, user_id, token, name, username, folder_path, folder_id, status, created_at, last_active, execution_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'stopped', ?, ?, 0)
        ''', (bot_id, user_id, token, bot_info['first_name'], bot_info['username'], folder_path, folder_id,
              datetime.now().isoformat(), datetime.now().isoformat()))
        conn.execute("UPDATE users SET bots_count = bots_count + 1 WHERE user_id = ?", (user_id,))
        conn.commit()
    
    success, error = engine.execute(bot_id, user_id, code, folder_path)
    
    if success:
        with get_db() as conn:
            conn.execute("UPDATE bots SET status = 'running' WHERE id = ?", (bot_id,))
            conn.commit()
        
        bot.answer_callback_query(call.id, "✅ ربات اجرا شد!", show_alert=True)
        bot.edit_message_text(f"✅ ربات {bot_info['first_name']} اجرا شد!", call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, f"❌ {error[:50]}", show_alert=True)

# ==================== لیست ربات ها ====================
@bot.message_handler(func=lambda m: m.text == '📋 لیست ربات ها')
def list_bots(message):
    user_id = message.from_user.id
    
    with get_db() as conn:
        bots = conn.execute("SELECT id, name, username, status, created_at, execution_count FROM bots WHERE user_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما هیچ رباتی ندارید!")
        return
    
    text = "🤖 لیست ربات های شما\n\n"
    for b in bots:
        status = engine.get_status(b['id'])
        status_text = "🟢 فعال" if status['running'] else "🔴 متوقف"
        text += f"{b['name']}\n"
        text += f"🔗 t.me/{b['username']}\n"
        text += f"📊 {status_text}\n"
        text += f"▶️ اجراها: {b['execution_count']}\n"
        text += f"📅 {b['created_at'][:10]}\n\n"
    
    bot.send_message(message.chat.id, text)

# ==================== اجرای ربات ====================
@bot.message_handler(func=lambda m: m.text == '▶️ اجرای ربات')
def run_prompt(message):
    user_id = message.from_user.id
    
    with get_db() as conn:
        bots = conn.execute("SELECT id, name FROM bots WHERE user_id = ?", (user_id,)).fetchall()
    
    if not bots:
        bot.send_message(message.chat.id, "📋 رباتی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        is_running = engine.is_running(b['id'])
        emoji = "🟢" if is_running else "🔴"
        markup.add(types.InlineKeyboardButton(f"{emoji} {b['name']}", callback_data=f"run_{b['id']}"))
    
    bot.send_message(message.chat.id, "▶️ انتخاب ربات:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('run_'))
def run_bot(call):
    bot_id = call.data.replace('run_', '')
    user_id = call.from_user.id
    
    if not check_subscription(user_id):
        bot.answer_callback_query(call.id, "❌ اشتراک فعال نیست!", show_alert=True)
        return
    
    if engine.is_running(bot_id):
        bot.answer_callback_query(call.id, "ربات در حال اجراست!", show_alert=True)
        return
    
    with get_db() as conn:
        bot_info = conn.execute("SELECT file_path, folder_path, token FROM bots WHERE id = ? AND user_id = ?", (bot_id, user_id)).fetchone()
    
    if not bot_info:
        bot.answer_callback_query(call.id, "ربات یافت نشد!", show_alert=True)
        return
    
    code = None
    if bot_info['folder_path'] and os.path.exists(bot_info['folder_path']):
        main_path = os.path.join(bot_info['folder_path'], 'main.py')
        if os.path.exists(main_path):
            with open(main_path, 'r', encoding='utf-8') as f:
                code = f.read()
    elif bot_info['file_path'] and os.path.exists(bot_info['file_path']):
        with open(bot_info['file_path'], 'r', encoding='utf-8') as f:
            code = f.read()
    
    if not code:
        bot.answer_callback_query(call.id, "فایل ربات یافت نشد!", show_alert=True)
        return
    
    success, error = engine.execute(bot_id, user_id, code, bot_info['folder_path'])
    
    if success:
        with get_db() as conn:
            conn.execute("UPDATE bots SET status = 'running', execution_count = execution_count + 1 WHERE id = ?", (bot_id,))
            conn.commit()
        bot.answer_callback_query(call.id, "✅ ربات اجرا شد!", show_alert=True)
    else:
        bot.answer_callback_query(call.id, f"❌ {error[:50]}", show_alert=True)
    
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== توقف ربات ====================
@bot.message_handler(func=lambda m: m.text == '🛑 توقف ربات')
def stop_prompt(message):
    user_id = message.from_user.id
    
    with get_db() as conn:
        bots = conn.execute("SELECT id, name FROM bots WHERE user_id = ?", (user_id,)).fetchall()
    
    if not bots:
        bot.send_message(message.chat.id, "📋 رباتی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        if engine.is_running(b['id']):
            markup.add(types.InlineKeyboardButton(f"🛑 {b['name']}", callback_data=f"stop_{b['id']}"))
    
    if not markup.keyboard:
        bot.send_message(message.chat.id, "📋 هیچ ربات در حال اجرایی ندارید!")
        return
    
    bot.send_message(message.chat.id, "🛑 انتخاب ربات:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('stop_'))
def stop_bot(call):
    bot_id = call.data.replace('stop_', '')
    engine.stop(bot_id)
    
    with get_db() as conn:
        conn.execute("UPDATE bots SET status = 'stopped' WHERE id = ?", (bot_id,))
        conn.commit()
    
    bot.answer_callback_query(call.id, "✅ ربات متوقف شد!", show_alert=True)
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== حذف ربات ====================
@bot.message_handler(func=lambda m: m.text == '🗑 حذف ربات')
def delete_prompt(message):
    user_id = message.from_user.id
    
    with get_db() as conn:
        bots = conn.execute("SELECT id, name FROM bots WHERE user_id = ?", (user_id,)).fetchall()
    
    if not bots:
        bot.send_message(message.chat.id, "📋 رباتی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        markup.add(types.InlineKeyboardButton(f"🗑 {b['name']}", callback_data=f"del_{b['id']}"))
    
    bot.send_message(message.chat.id, "🗑 انتخاب ربات:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('del_'))
def confirm_delete(call):
    bot_id = call.data.replace('del_', '')
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ بله", callback_data=f"confirm_del_{bot_id}"),
              types.InlineKeyboardButton("❌ انصراف", callback_data="cancel_del"))
    bot.edit_message_text("⚠️ اطمینان دارید؟", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_del_'))
def do_delete(call):
    bot_id = call.data.replace('confirm_del_', '')
    user_id = call.from_user.id
    
    engine.stop(bot_id)
    
    with get_db() as conn:
        conn.execute("DELETE FROM bots WHERE id = ? AND user_id = ?", (bot_id, user_id))
        conn.execute("UPDATE users SET bots_count = bots_count - 1 WHERE user_id = ?", (user_id,))
        conn.commit()
    
    bot.edit_message_text("✅ ربات حذف شد!", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "cancel_del")
def cancel_delete(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== کیف پول ====================
@bot.message_handler(func=lambda m: m.text == '💰 کیف پول')
def wallet(message):
    user = get_user(message.from_user.id)
    if not user:
        bot.send_message(message.chat.id, "❌ /start بزنید")
        return
    
    can_create, max_bots, current_bots = can_create_bot(message.from_user.id)
    withdraw_percent = get_setting('withdraw_percent')
    min_withdraw = get_setting('min_withdraw')
    
    text = f"💰 کیف پول شما\n\n"
    text += f"👤 {user['first_name']}\n"
    text += f"💵 موجودی: {user['balance']:,} تومان\n"
    text += f"👥 دعوت ها: {user['referrals_count']}\n"
    text += f"✅ تایید شده: {user['verified_referrals']}\n"
    text += f"🤖 ربات ها: {current_bots}/{max_bots}\n\n"
    text += f"💰 کمیسیون دعوت: {withdraw_percent}%\n"
    text += f"💸 حداقل برداشت: {int(min_withdraw):,} تومان\n\n"
    text += f"💡 هر دعوت = {int(SUBSCRIPTION_PRICE * int(withdraw_percent) / 100):,} تومان پاداش"
    
    bot.send_message(message.chat.id, text)

# ==================== دعوت دوستان ====================
@bot.message_handler(func=lambda m: m.text == '👥 دعوت دوستان')
def invite(message):
    user = get_user(message.from_user.id)
    bot_username = bot.get_me().username
    withdraw_percent = get_setting('withdraw_percent')
    
    commission = int(SUBSCRIPTION_PRICE * int(withdraw_percent) / 100)
    
    text = f"👥 دعوت دوستان\n\n"
    text += f"🎁 کد: {user['referral_code']}\n"
    text += f"🔗 لینک: https://t.me/{bot_username}?start={user['referral_code']}\n"
    text += f"📊 دعوت ها: {user['referrals_count']}\n"
    text += f"✅ تایید شده: {user['verified_referrals']}\n\n"
    text += f"💰 هر دعوت: {commission:,} تومان پاداش\n"
    text += f"📌 کمیسیون: {withdraw_percent}% از مبلغ اشتراک\n\n"
    text += f"💡 هر دوست شما که اشتراک بخرد، {withdraw_percent}% به حساب شما واریز می شود!"
    
    bot.send_message(message.chat.id, text)

# ==================== درخواست برداشت ====================
@bot.message_handler(func=lambda m: m.text == '💸 درخواست برداشت')
def withdraw_request(message):
    user = get_user(message.from_user.id)
    min_w = int(get_setting('min_withdraw'))
    
    if user['balance'] < min_w:
        bot.send_message(message.chat.id, f"❌ موجودی کمتر از حداقل برداشت ({min_w:,} تومان)")
        return
    
    msg = bot.send_message(message.chat.id, "💳 شماره کارت (16 رقم):")
    bot.register_next_step_handler(msg, process_withdraw_card, user)

def process_withdraw_card(message, user):
    card = message.text.strip().replace(' ', '')
    if len(card) != 16 or not card.isdigit():
        bot.reply_to(message, "❌ شماره کارت نامعتبر!")
        return
    
    msg = bot.send_message(message.chat.id, "👤 نام صاحب کارت:")
    bot.register_next_step_handler(msg, process_withdraw_holder, user, card)

def process_withdraw_holder(message, user, card):
    holder = message.text.strip()
    
    msg = bot.send_message(message.chat.id, "🏦 نام بانک:")
    bot.register_next_step_handler(msg, process_withdraw_bank, user, card, holder)

def process_withdraw_bank(message, user, card, holder):
    bank = message.text.strip()
    tracking_code = hashlib.md5(f"{user['user_id']}_{card}_{time.time()}".encode()).hexdigest()[:12].upper()
    
    with get_db() as conn:
        conn.execute('''
            INSERT INTO withdraw_requests (user_id, amount, card_number, card_holder, bank_name, tracking_code, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
        ''', (user['user_id'], user['balance'], card, holder, bank, tracking_code, datetime.now().isoformat()))
        conn.execute("UPDATE users SET balance = 0 WHERE user_id = ?", (user['user_id'],))
        conn.commit()
    
    bot.reply_to(message, 
                f"✅ درخواست برداشت ثبت شد!\n\n"
                f"💰 مبلغ: {user['balance']:,} تومان\n"
                f"💳 کارت: {card[:4]}****{card[-4:]}\n"
                f"🏦 بانک: {bank}\n"
                f"🔑 کد رهگیری: {tracking_code}\n\n"
                f"پس از بررسی، مبلغ به کارت شما واریز می شود.")
    
    for admin_id in ADMIN_IDS:
        bot.send_message(admin_id, f"💰 درخواست برداشت\n👤 {user['first_name']}\n🆔 {user['user_id']}\n💰 {user['balance']:,} تومان")

# ==================== کتابخانه ها ====================
@bot.message_handler(func=lambda m: m.text == '📦 کتابخانه ها')
def libraries_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    libs = ['requests', 'numpy', 'pandas', 'flask', 'django', 'pillow', 'beautifulsoup4', 'selenium', 'pyTelegramBotAPI', 'aiogram', 'jdatetime']
    for lib in libs[:10]:
        markup.add(types.InlineKeyboardButton(f"📦 {lib}", callback_data=f"install_{lib}"))
    markup.add(types.InlineKeyboardButton("🔧 نصب دستی", callback_data="install_custom"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="lib_back"))
    
    bot.send_message(message.chat.id, "📦 کتابخانه های محبوب", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('install_'))
def install_lib(call):
    lib = call.data.replace('install_', '')
    if lib == 'custom':
        msg = bot.send_message(call.message.chat.id, "🔧 نام کتابخانه:")
        bot.register_next_step_handler(msg, install_custom)
        bot.answer_callback_query(call.id)
        return
    elif lib == 'back':
        libraries_menu(call.message)
        return
    
    status_msg = bot.send_message(call.message.chat.id, f"🔄 در حال نصب {lib}...")
    library_manager.install(lib, call.message.chat.id, status_msg.message_id, bot)
    bot.answer_callback_query(call.id)

def install_custom(message):
    lib = message.text.strip()
    status_msg = bot.reply_to(message, f"🔄 در حال نصب {lib}...")
    library_manager.install(lib, message.chat.id, status_msg.message_id, bot)

@bot.callback_query_handler(func=lambda call: call.data == "lib_back")
def lib_back(call):
    libraries_menu(call.message)

# ==================== راهنما ====================
@bot.message_handler(func=lambda m: m.text == '📚 راهنما')
def guide(message):
    text = f"""📚 راهنمای ربات مادر

🎯 نحوه ساخت ربات:
1️⃣ از دکمه خرید اشتراک اشتراک خود را فعال کنید
2️⃣ پس از فعال سازی، از ساخت ربات جدید استفاده کنید
3️⃣ فایل py. یا zip. خود را ارسال کنید
4️⃣ توکن داخل کد باشد

💰 قیمت اشتراک: {get_setting('subscription_price_str')}
📌 محدودیت: هر کاربر حداکثر {get_setting('max_bots_per_user')} ربات

▶️ اجرای ربات:
- ربات ها پس از ساخت خودکار اجرا می شوند
- برای توقف از توقف ربات استفاده کنید

👥 دعوت دوستان:
- هر دعوت {get_setting('withdraw_percent')}% کمیسیون
- حداقل برداشت {int(get_setting('min_withdraw')):,} تومان

📦 کتابخانه ها:
- می توانید هر کتابخانه پایتونی نصب کنید

🆘 پشتیبانی: @shahraghee13"""
    
    bot.send_message(message.chat.id, text)

# ==================== آمار ====================
@bot.message_handler(func=lambda m: m.text == '📊 آمار')
def stats(message):
    with get_db() as conn:
        users = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()['c']
        active_subs = conn.execute("SELECT COUNT(*) as c FROM users WHERE subscription_status = 'active'").fetchone()['c']
        bots = conn.execute("SELECT COUNT(*) as c FROM bots").fetchone()['c']
        total_wallet = conn.execute("SELECT SUM(balance) as t FROM users").fetchone()['t'] or 0
    
    running = sum(1 for b in range(10))  # تقریبی
    
    text = f"📊 آمار سیستم\n\n"
    text += f"👥 کاربران: {users}\n"
    text += f"✅ اشتراک فعال: {active_subs}\n"
    text += f"🤖 ربات ها: {bots}\n"
    text += f"💰 موجودی کل: {total_wallet:,} تومان\n"
    text += f"📌 حداکثر ربات: {get_setting('max_bots_per_user')}"
    
    bot.send_message(message.chat.id, text)

# ==================== پشتیبانی ====================
@bot.message_handler(func=lambda m: m.text == '📞 پشتیبانی')
def support(message):
    bot.send_message(message.chat.id, "📞 پشتیبانی: @shahraghee13")

# ==================== پنل مدیریت ساده ====================
@bot.message_handler(func=lambda m: m.text == '👑 پنل مدیریت')
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📸 تایید فیش", callback_data="admin_receipts"),
        types.InlineKeyboardButton("💰 تایید برداشت", callback_data="admin_withdraws"),
        types.InlineKeyboardButton("👥 کاربران", callback_data="admin_users"),
        types.InlineKeyboardButton("🎁 فعال سازی", callback_data="admin_activate"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    bot.send_message(message.chat.id, "👑 پنل مدیریت", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_receipts")
def admin_receipts(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    with get_db() as conn:
        receipts = conn.execute("SELECT * FROM receipts WHERE status = 'pending' ORDER BY created_at").fetchall()
    
    if not receipts:
        bot.send_message(call.message.chat.id, "📸 فیشی وجود ندارد")
        return
    
    for r in receipts:
        text = f"📸 فیش #{r['id']}\n👤 {r['user_id']}\n💰 {r['amount']:,} تومان\n🆔 {r['payment_code']}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_{r['id']}"),
                  types.InlineKeyboardButton("❌ رد", callback_data=f"reject_{r['id']}"))
        
        if os.path.exists(r['receipt_path']):
            with open(r['receipt_path'], 'rb') as f:
                bot.send_photo(call.message.chat.id, f, caption=text, reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_'))
def approve_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    rid = int(call.data.replace('approve_', ''))
    
    with get_db() as conn:
        receipt = conn.execute("SELECT user_id FROM receipts WHERE id = ?", (rid,)).fetchone()
        if receipt:
            conn.execute("UPDATE receipts SET status = 'approved', reviewed_by = ?, reviewed_at = ? WHERE id = ?",
                        (call.from_user.id, datetime.now().isoformat(), rid))
            expiry = activate_subscription(receipt['user_id'])
            conn.commit()
            
            bot.send_message(receipt['user_id'], 
                            f"✅ اشتراک شما فعال شد!\n\n📅 تا تاریخ: {expiry.strftime('%Y-%m-%d')}\n🤖 می توانید حداکثر {get_setting('max_bots_per_user')} ربات بسازید!")
            
            bot.answer_callback_query(call.id, "✅ اشتراک فعال شد!")
            bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_'))
def reject_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    rid = int(call.data.replace('reject_', ''))
    
    with get_db() as conn:
        receipt = conn.execute("SELECT user_id FROM receipts WHERE id = ?", (rid,)).fetchone()
        if receipt:
            conn.execute("UPDATE receipts SET status = 'rejected', reviewed_by = ?, reviewed_at = ? WHERE id = ?",
                        (call.from_user.id, datetime.now().isoformat(), rid))
            conn.commit()
            
            bot.send_message(receipt['user_id'], "❌ فیش شما رد شد!\nلطفاً با پشتیبانی تماس بگیرید: @shahraghee13")
            
            bot.answer_callback_query(call.id, "❌ رد شد!")
            bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_withdraws")
def admin_withdraws(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    with get_db() as conn:
        withdraws = conn.execute("SELECT * FROM withdraw_requests WHERE status = 'pending' ORDER BY created_at").fetchall()
    
    if not withdraws:
        bot.send_message(call.message.chat.id, "💰 درخواستی وجود ندارد")
        return
    
    for w in withdraws:
        text = f"💰 برداشت #{w['id']}\n👤 {w['user_id']}\n💰 {w['amount']:,} تومان\n💳 {w['card_number']}\n👤 {w['card_holder']}\n🏦 {w['bank_name']}"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_wd_{w['id']}"))
        bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_wd_'))
def approve_withdraw(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    wid = int(call.data.replace('approve_wd_', ''))
    
    with get_db() as conn:
        conn.execute("UPDATE withdraw_requests SET status = 'approved', processed_at = ? WHERE id = ?",
                    (datetime.now().isoformat(), wid))
        conn.commit()
    
    bot.answer_callback_query(call.id, "✅ تایید شد!")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_users")
def admin_users(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    with get_db() as conn:
        users = conn.execute("SELECT user_id, first_name, balance, subscription_status, created_at FROM users ORDER BY created_at DESC LIMIT 20").fetchall()
    
    if not users:
        bot.send_message(call.message.chat.id, "📋 کاربری وجود ندارد")
        return
    
    text = "👥 20 کاربر آخر\n\n"
    for u in users:
        status = "✅" if u['subscription_status'] == 'active' else "❌"
        text += f"{status} {u['user_id']} - {u['first_name']}\n"
        text += f"   💰 {u['balance']:,} تومان\n"
        text += f"   📅 {u['created_at'][:10]}\n\n"
    
    bot.send_message(call.message.chat.id, text)

@bot.callback_query_handler(func=lambda call: call.data == "admin_activate")
def admin_activate_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, "🎁 آیدی کاربر را وارد کنید:")
    bot.register_next_step_handler(msg, process_admin_activate)
    bot.answer_callback_query(call.id)

def process_admin_activate(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        user_id = int(message.text.strip())
        expiry = activate_subscription(user_id)
        bot.reply_to(message, f"✅ اشتراک {user_id} تا {expiry.strftime('%Y-%m-%d')} فعال شد!")
        bot.send_message(user_id, f"✅ اشتراک شما توسط ادمین فعال شد!\n📅 تا {expiry.strftime('%Y-%m-%d')}\nحالا می توانید ربات بسازید.")
    except:
        bot.reply_to(message, "❌ خطا!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    admin_panel(call.message)

# ==================== پیام همگانی ====================
@bot.message_handler(func=lambda m: m.text == '📢 پیام همگانی')
def broadcast_prompt(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(message.chat.id, "📢 متن پیام را ارسال کنید:")
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    text = message.text
    
    with get_db() as conn:
        users = conn.execute("SELECT user_id FROM users").fetchall()
    
    sent = 0
    status_msg = bot.reply_to(message, f"🔄 در حال ارسال به {len(users)} کاربر...")
    
    for user in users:
        try:
            bot.send_message(user['user_id'], f"📢 پیام همگانی\n\n{text}")
            sent += 1
            time.sleep(0.05)
        except:
            pass
    
    bot.edit_message_text(f"✅ به {sent} کاربر ارسال شد!", message.chat.id, status_msg.message_id)

# ==================== اجرا ====================
if __name__ == "__main__":
    print("=" * 60)
    print("🚀 ربات مادر - نسخه پایدار")
    print("=" * 60)
    print(f"👑 ادمین: {ADMIN_IDS}")
    print(f"💰 قیمت اشتراک: {SUBSCRIPTION_PRICE_STR}")
    print(f"📌 حداکثر ربات: {MAX_BOTS_PER_USER}")
    print("=" * 60)
    print("🔥 ربات با موفقیت راه اندازی شد!")
    print("=" * 60)
    
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=60)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)