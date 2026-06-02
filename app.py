#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
═══════════════════════════════════════════════════════════════════════════════
🚀 ربات مادر نهایی - نسخه 23.1 STABLE
✅ رفع کامل باگ‌ها - دکمه‌ها کار می‌کنند - اشتراک به درستی بررسی می‌شود
═══════════════════════════════════════════════════════════════════════════════
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
from functools import wraps
from collections import defaultdict

# ==================== تنظیمات پایه ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DIRS = {
    'DB': os.path.join(BASE_DIR, "database"),
    'FILES': os.path.join(BASE_DIR, "user_files"),
    'RUNNING': os.path.join(BASE_DIR, "running_bots"),
    'LOGS': os.path.join(BASE_DIR, "logs"),
    'RECEIPTS': os.path.join(BASE_DIR, "receipts"),
    'TEMP': os.path.join(BASE_DIR, "temp"),
    'MACHINES': os.path.join(BASE_DIR, "machines"),
    'USER_PROJECTS': os.path.join(BASE_DIR, "user_projects"),
}

for dir_path in DIRS.values():
    os.makedirs(dir_path, exist_ok=True)

# ==================== توکن و تنظیمات ====================
BOT_TOKEN = "8266270866:AAF6m1x4weSUEvzIj1gkbIS_j0yAdxCSs78"
ADMIN_IDS = [327855654]
BOT_USERNAME = "ROBTTSAZE_bot"

# تنظیمات پیش‌فرض
SETTINGS = {
    'card_number': "5892101187322777",
    'card_number_display': "5892 1011 8732 2777",
    'card_holder': "مرتضی نیکخو خنجری",
    'card_bank': "بانک ملی - سپهر",
    'subscription_price': 2000000,
    'subscription_price_str': "۲,۰۰۰,۰۰۰ تومان",
    'withdraw_percent': 7,
    'min_withdraw': 200000,
    'max_bots_per_user': 3,
    'bot_active_minutes': 5,
    'guide_text': "📚 راهنمای استفاده\n\n1️⃣ برای ساخت ربات، فایل .py یا .zip خود را ارسال کنید\n2️⃣ پس از پرداخت اشتراک ماهیانه، می‌توانید ربات بسازید\n3️⃣ هر کاربر می‌تواند حداکثر ۳ ربات فعال داشته باشد\n4️⃣ هر ربات به مدت ۵ دقیقه فعال می‌ماند\n5️⃣ با دعوت دوستان، ۷٪ کمیسیون دریافت کنید",
    'max_builds_per_hour': 10,
    'max_concurrent_builds': 5,
    'rate_limit_per_second': 5,
}

# ==================== دیتابیس ====================
class Database:
    def __init__(self):
        self._init_db()
        self._init_tables()
    
    def _init_db(self):
        self.conn = sqlite3.connect(
            os.path.join(DIRS['DB'], 'mother_bot.db'),
            timeout=30,
            check_same_thread=False
        )
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
    
    def execute(self, query, params=(), fetch=True):
        try:
            cursor = self.conn.execute(query, params)
            self.conn.commit()
            if fetch:
                return cursor.fetchall()
            return cursor.lastrowid
        except Exception as e:
            print(f"DB error: {e}")
            return []
    
    def _init_tables(self):
        # کاربران
        self.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                bots_count INTEGER DEFAULT 0,
                subscription_status TEXT DEFAULT 'inactive',
                subscription_expiry TIMESTAMP,
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                referrals_count INTEGER DEFAULT 0,
                wallet_balance INTEGER DEFAULT 0,
                created_at TIMESTAMP,
                last_active TIMESTAMP
            )
        ''')
        
        # ربات‌ها
        self.execute('''
            CREATE TABLE IF NOT EXISTS bots (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                token TEXT,
                name TEXT,
                username TEXT,
                file_path TEXT,
                pid INTEGER,
                status TEXT DEFAULT 'stopped',
                created_at TIMESTAMP,
                expires_at TIMESTAMP,
                last_active TIMESTAMP
            )
        ''')
        
        # فیش‌ها
        self.execute('''
            CREATE TABLE IF NOT EXISTS receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                receipt_path TEXT,
                status TEXT DEFAULT 'pending',
                payment_code TEXT UNIQUE,
                created_at TIMESTAMP
            )
        ''')
        
        # درخواست‌های برداشت
        self.execute('''
            CREATE TABLE IF NOT EXISTS withdraw_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                card_number TEXT,
                card_holder TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP
            )
        ''')
        
        # تنظیمات سیستم
        for key, value in SETTINGS.items():
            self.execute('INSERT OR IGNORE INTO system_settings (key, value) VALUES (?, ?)', (key, str(value)))
        
        # ایجاد دیتابیس system_settings اگر نیست
        self.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''', fetch=False)

db = Database()

# ==================== توابع کمکی ====================
def get_setting(key):
    result = db.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
    if result:
        val = result[0]['value']
        if key in ['subscription_price', 'withdraw_percent', 'min_withdraw', 
                   'max_bots_per_user', 'bot_active_minutes', 'max_builds_per_hour']:
            return int(val)
        return val
    return SETTINGS.get(key)

def update_setting(key, value):
    db.execute("UPDATE system_settings SET value = ? WHERE key = ?", (str(value), key))

def generate_referral_code(user_id):
    return hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:10]

def get_user(user_id):
    users = db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    return dict(users[0]) if users else None

def create_user(user_id, username, first_name, last_name, referred_by=None):
    now = datetime.now().isoformat()
    referral_code = generate_referral_code(user_id)
    
    db.execute('''
        INSERT OR IGNORE INTO users 
        (user_id, username, first_name, last_name, referral_code, referred_by, created_at, last_active, wallet_balance)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
    ''', (user_id, username, first_name, last_name, referral_code, referred_by, now, now))
    
    db.execute('UPDATE users SET last_active = ? WHERE user_id = ?', (now, user_id))
    return True

def check_subscription(user_id):
    """بررسی فعال بودن اشتراک کاربر"""
    user = get_user(user_id)
    if not user:
        return False
    
    # اگر فعال است و تاریخ انقضا دارد
    if user['subscription_status'] == 'active' and user['subscription_expiry']:
        expiry = datetime.fromisoformat(user['subscription_expiry'])
        if expiry > datetime.now():
            return True
        else:
            # منقضی شده
            db.execute('UPDATE users SET subscription_status = "inactive" WHERE user_id = ?', (user_id,))
            return False
    
    return False

def get_active_bots_count(user_id):
    """تعداد ربات‌های فعال کاربر"""
    result = db.execute('SELECT COUNT(*) as count FROM bots WHERE user_id = ? AND status = "running"', (user_id,))
    return result[0]['count'] if result else 0

def can_create_bot(user_id):
    """بررسی آیا کاربر می‌تواند ربات جدید بسازد"""
    # بررسی اشتراک
    if not check_subscription(user_id):
        return False, "❌ اشتراک شما فعال نیست. لطفاً ابتدا اشتراک تهیه کنید."
    
    # بررسی تعداد ربات‌های فعال
    active_bots = get_active_bots_count(user_id)
    max_bots = get_setting('max_bots_per_user')
    
    if active_bots >= max_bots:
        return False, f"❌ شما حداکثر {max_bots} ربات فعال می‌توانید داشته باشید.\nبرای ساخت ربات جدید، ابتدا یکی از ربات‌های خود را حذف کنید."
    
    return True, "ok"

def activate_subscription(user_id, months=1):
    """فعال کردن اشتراک کاربر"""
    user = get_user(user_id)
    now = datetime.now()
    
    if user and user['subscription_status'] == 'active' and user['subscription_expiry']:
        new_expiry = datetime.fromisoformat(user['subscription_expiry']) + timedelta(days=30*months)
    else:
        new_expiry = now + timedelta(days=30*months)
    
    db.execute('''
        UPDATE users 
        SET subscription_status = 'active', subscription_expiry = ?
        WHERE user_id = ?
    ''', (new_expiry.isoformat(), user_id))
    
    return new_expiry

def add_wallet_balance(user_id, amount):
    user = get_user(user_id)
    new_balance = (user['wallet_balance'] or 0) + amount
    db.execute('UPDATE users SET wallet_balance = ? WHERE user_id = ?', (new_balance, user_id))

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

def verify_bot_token(token):
    """بررسی اعتبار توکن ربات"""
    try:
        resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('ok') and data.get('result', {}).get('is_bot'):
                return True, data['result']
        return False, None
    except:
        return False, None

def run_bot_process(bot_id, code, token):
    """اجرای ربات به عنوان پروسه جداگانه با زمان انقضای ۵ دقیقه"""
    try:
        bot_dir = os.path.join(DIRS['RUNNING'], bot_id)
        os.makedirs(bot_dir, exist_ok=True)
        
        code_path = os.path.join(bot_dir, 'bot.py')
        
        # افزودن کد زمان انقضا به ابتدای فایل
        expiry_code = f'''
import threading
import time
import sys
from datetime import datetime, timedelta

EXPIRY_MINUTES = {get_setting("bot_active_minutes")}

def check_expiry():
    start_time = datetime.now()
    expiry_time = start_time + timedelta(minutes=EXPIRY_MINUTES)
    while True:
        if datetime.now() >= expiry_time:
            print("⏰ زمان فعالسازی ربات به پایان رسید.")
            sys.exit(0)
        time.sleep(10)

threading.Thread(target=check_expiry, daemon=True).start()
'''
        
        with open(code_path, 'w', encoding='utf-8') as f:
            f.write(expiry_code + "\n" + code)
        
        log_file = os.path.join(DIRS['LOGS'], f"bot_{bot_id}.log")
        
        process = subprocess.Popen(
            [sys.executable, code_path],
            stdout=open(log_file, 'a'),
            stderr=subprocess.STDOUT,
            cwd=bot_dir,
            start_new_session=True
        )
        
        time.sleep(2)
        
        if process.poll() is None:
            return True, process.pid
        else:
            return False, None
    except Exception as e:
        return False, str(e)

def stop_bot_process(bot_id):
    """متوقف کردن پروسه ربات"""
    try:
        bot_dir = os.path.join(DIRS['RUNNING'], bot_id)
        pid_file = os.path.join(bot_dir, 'pid.txt')
        
        # دریافت PID از دیتابیس
        bot_data = db.execute('SELECT pid FROM bots WHERE id = ?', (bot_id,))
        if bot_data and bot_data[0]['pid']:
            try:
                os.kill(bot_data[0]['pid'], signal.SIGTERM)
            except:
                pass
        
        # پاک کردن پوشه
        if os.path.exists(bot_dir):
            shutil.rmtree(bot_dir, ignore_errors=True)
        
        return True
    except:
        return False

def delete_bot(bot_id, user_id):
    """حذف کامل ربات"""
    bot_data = db.execute('SELECT * FROM bots WHERE id = ?', (bot_id,))
    if not bot_data:
        return False
    
    bot_data = dict(bot_data[0])
    if bot_data['user_id'] != user_id:
        return False
    
    # توقف پروسه
    stop_bot_process(bot_id)
    
    # حذف فایل
    if bot_data.get('file_path') and os.path.exists(bot_data['file_path']):
        os.remove(bot_data['file_path'])
    
    # حذف از دیتابیس
    db.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
    db.execute('UPDATE users SET bots_count = bots_count - 1 WHERE user_id = ?', (user_id,))
    
    return True

# ==================== ربات تلگرام ====================
bot = telebot.TeleBot(BOT_TOKEN)

# ==================== منوهای کیبورد ====================
def get_main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        types.KeyboardButton('🤖 ساخت ربات جدید'),
        types.KeyboardButton('📋 ربات‌های من'),
        types.KeyboardButton('🔄 فعال/غیرفعال ربات'),
        types.KeyboardButton('🗑 حذف ربات'),
        types.KeyboardButton('💰 کیف پول و اشتراک'),
        types.KeyboardButton('👥 دعوت دوستان'),
        types.KeyboardButton('💸 درخواست برداشت'),
        types.KeyboardButton('📚 راهنما'),
        types.KeyboardButton('📞 پشتیبانی')
    ]
    markup.add(*buttons)
    return markup

def get_admin_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        types.KeyboardButton('🤖 ساخت ربات جدید'),
        types.KeyboardButton('📋 ربات‌های من'),
        types.KeyboardButton('🔄 فعال/غیرفعال ربات'),
        types.KeyboardButton('🗑 حذف ربات'),
        types.KeyboardButton('💰 کیف پول و اشتراک'),
        types.KeyboardButton('👥 دعوت دوستان'),
        types.KeyboardButton('💸 درخواست برداشت'),
        types.KeyboardButton('📚 راهنما'),
        types.KeyboardButton('👑 پنل مدیریت'),
        types.KeyboardButton('📢 پیام همگانی'),
        types.KeyboardButton('📞 پشتیبانی')
    ]
    markup.add(*buttons)
    return markup

# ==================== دستور start ====================
@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or ""
    username = message.from_user.username or ""
    
    # بررسی کد معرف
    referred_by = None
    args = message.text.split()
    if len(args) > 1:
        code = args[1]
        users = db.execute('SELECT user_id FROM users WHERE referral_code = ?', (code,))
        if users and users[0]['user_id'] != user_id:
            referred_by = users[0]['user_id']
            try:
                bot.send_message(referred_by, f"🎉 {first_name} با لینک دعوت شما عضو شد!")
            except:
                pass
    
    create_user(user_id, username, first_name, message.from_user.last_name or "", referred_by)
    user = get_user(user_id)
    
    referral_link = f"https://t.me/{BOT_USERNAME}?start={user['referral_code']}"
    is_admin = user_id in ADMIN_IDS
    
    # بررسی وضعیت اشتراک
    has_subscription = check_subscription(user_id)
    expiry_text = ""
    if has_subscription and user['subscription_expiry']:
        expiry = datetime.fromisoformat(user['subscription_expiry'])
        expiry_text = f"\n📅 انقضای اشتراک: {expiry.strftime('%Y-%m-%d')}"
    
    text = (f"🚀 **خوش آمدید {first_name}**\n\n"
            f"👤 شناسه: `{user_id}`\n"
            f"💰 موجودی: {user['wallet_balance']:,} تومان\n"
            f"👥 تعداد دعوت: {user['referrals_count']}\n"
            f"🎁 کد معرف: `{user['referral_code']}`\n"
            f"🔗 لینک دعوت: `{referral_link}`\n"
            f"💳 وضعیت اشتراک: {'✅ فعال' if has_subscription else '❌ غیرفعال'}{expiry_text}\n\n"
            f"📌 هر ربات به مدت {get_setting('bot_active_minutes')} دقیقه فعال می‌ماند\n"
            f"📌 حداکثر {get_setting('max_bots_per_user')} ربات فعال همزمان")
    
    markup = get_main_menu() if not is_admin else get_admin_menu()
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

# ==================== ساخت ربات جدید ====================
@bot.message_handler(func=lambda m: m.text == '🤖 ساخت ربات جدید')
def new_bot(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    # بررسی اشتراک
    can_create, msg = can_create_bot(user_id)
    if not can_create:
        # نمایش اطلاعات پرداخت
        card = get_setting('card_number_display')
        bank = get_setting('card_bank')
        holder = get_setting('card_holder')
        price = get_setting('subscription_price_str')
        
        text = (f"❌ {msg}\n\n"
                f"💳 **اطلاعات پرداخت اشتراک:**\n"
                f"🏦 {bank}\n"
                f"💳 `{card}`\n"
                f"👤 {holder}\n"
                f"💰 مبلغ: {price}\n\n"
                f"📸 پس از واریز، رسید را به صورت عکس ارسال کنید.\n"
                f"⏱️ رسید شما ظرف ۲۴ ساعت بررسی می‌شود.")
        
        bot.send_message(message.chat.id, text, parse_mode='Markdown')
        return
    
    bot.send_message(message.chat.id, "📤 **فایل ربات خود را ارسال کنید**\n\nپشتیبانی: فایل‌های `.py` یا `.zip`\nحداکثر حجم: ۵۰ مگابایت\n\n⚠️ مطمئن شوید توکن ربات داخل کد وجود دارد.")

# ==================== دریافت فایل ربات ====================
@bot.message_handler(content_types=['document'])
def handle_bot_file(message):
    user_id = message.from_user.id
    
    # بررسی مجدد اشتراک
    can_create, msg = can_create_bot(user_id)
    if not can_create:
        bot.reply_to(message, msg)
        return
    
    file_name = message.document.file_name
    if not (file_name.endswith('.py') or file_name.endswith('.zip')):
        bot.reply_to(message, "❌ فقط فایل‌های `.py` یا `.zip` پشتیبانی می‌شوند.")
        return
    
    if message.document.file_size > 50 * 1024 * 1024:
        bot.reply_to(message, "❌ حجم فایل بیشتر از ۵۰ مگابایت است.")
        return
    
    status_msg = bot.reply_to(message, "🔄 در حال بررسی فایل...")
    
    try:
        # دانلود فایل
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        # ذخیره فایل
        user_dir = os.path.join(DIRS['FILES'], str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        file_path = os.path.join(user_dir, f"{int(time.time())}_{file_name}")
        with open(file_path, 'wb') as f:
            f.write(downloaded)
        
        # استخراج کد
        code = ""
        if file_name.endswith('.zip'):
            extract_dir = os.path.join(DIRS['TEMP'], f"extract_{user_id}_{int(time.time())}")
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
            bot.edit_message_text("❌ فایل پایتون معتبری پیدا نشد.", message.chat.id, status_msg.message_id)
            return
        
        # استخراج توکن
        token = extract_token_from_code(code)
        if not token:
            bot.edit_message_text("❌ توکن ربات در کد پیدا نشد!\n\nلطفاً مطمئن شوید توکن به صورت `TOKEN = 'your_token'` در کد وجود دارد.", 
                                message.chat.id, status_msg.message_id, parse_mode='Markdown')
            return
        
        # بررسی توکن
        is_valid, bot_info = verify_bot_token(token)
        if not is_valid:
            bot.edit_message_text("❌ توکن نامعتبر است! لطفاً توکن صحیح ربات خود را وارد کنید.", 
                                message.chat.id, status_msg.message_id)
            return
        
        bot_name = bot_info.get('first_name', 'ربات')
        bot_username = bot_info.get('username', 'unknown')
        
        # ساخت ربات
        bot_id = hashlib.md5(f"{user_id}{token}{time.time()}".encode()).hexdigest()[:16]
        
        bot.edit_message_text(f"🔄 در حال ساخت ربات {bot_name}...\n⏱️ زمان فعالسازی: {get_setting('bot_active_minutes')} دقیقه", 
                            message.chat.id, status_msg.message_id)
        
        # اجرای ربات
        success, pid = run_bot_process(bot_id, code, token)
        
        if success:
            # ذخیره در دیتابیس
            expires_at = datetime.now() + timedelta(minutes=get_setting('bot_active_minutes'))
            db.execute('''
                INSERT INTO bots (id, user_id, token, name, username, file_path, pid, status, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'running', ?, ?)
            ''', (bot_id, user_id, token, bot_name, bot_username, file_path, pid, datetime.now().isoformat(), expires_at.isoformat()))
            
            db.execute('UPDATE users SET bots_count = bots_count + 1, last_active = ? WHERE user_id = ?', 
                      (datetime.now().isoformat(), user_id))
            
            # کمیسیون برای معرف
            user = get_user(user_id)
            if user and user.get('referred_by'):
                commission = int(get_setting('subscription_price') * get_setting('withdraw_percent') / 100)
                add_wallet_balance(user['referred_by'], commission)
                try:
                    bot.send_message(user['referred_by'], f"🎉 کمیسیون {commission:,} تومان از ساخت ربات توسط دعوت‌شده شما به کیف پول اضافه شد.")
                except:
                    pass
            
            bot.edit_message_text(
                f"✅ **ربات {bot_name} با موفقیت ساخته شد!**\n\n"
                f"🤖 نام کاربری: @{bot_username}\n"
                f"⏱️ زمان فعال بودن: {get_setting('bot_active_minutes')} دقیقه\n"
                f"🆔 شناسه ربات: `{bot_id}`\n\n"
                f"⚠️ توجه: ربات شما پس از {get_setting('bot_active_minutes')} دقیقه به طور خودکار متوقف می‌شود.\n"
                f"برای استفاده مجدد، از بخش «ربات‌های من» آن را دوباره فعال کنید.",
                message.chat.id, status_msg.message_id, parse_mode='Markdown'
            )
            
            # ارسال پیام تایید به ادمین
            for admin_id in ADMIN_IDS:
                try:
                    bot.send_message(admin_id, f"✅ ربات جدید ساخته شد!\n👤 {user['first_name']}\n🆔 {user_id}\n🤖 {bot_name}\n@ {bot_username}")
                except:
                    pass
        else:
            bot.edit_message_text(f"❌ خطا در اجرای ربات: {pid}", message.chat.id, status_msg.message_id)
            
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)[:100]}", message.chat.id, status_msg.message_id)

# ==================== ربات‌های من ====================
@bot.message_handler(func=lambda m: m.text == '📋 ربات‌های من')
def my_bots(message):
    user_id = message.from_user.id
    bots_list = db.execute('SELECT * FROM bots WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    
    if not bots_list:
        bot.send_message(message.chat.id, "📋 شما هیچ رباتی ندارید.\nاز دکمه «ساخت ربات جدید» استفاده کنید.")
        return
    
    for b in bots_list:
        b = dict(b)
        # بررسی وضعیت
        is_running = b['status'] == 'running'
        status_emoji = "🟢" if is_running else "🔴"
        status_text = "فعال" if is_running else "متوقف"
        
        if is_running and b['expires_at']:
            expires = datetime.fromisoformat(b['expires_at'])
            remaining = expires - datetime.now()
            minutes = max(0, remaining.seconds // 60)
            time_text = f"\n⏱️ زمان باقیمانده: {minutes} دقیقه"
        else:
            time_text = ""
        
        text = (f"{status_emoji} **{b['name']}**\n"
                f"🆔 `{b['id']}`\n"
                f"🔗 @{b['username']}\n"
                f"📊 وضعیت: {status_text}{time_text}")
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🔄 فعال/غیرفعال", callback_data=f"toggle_{b['id']}"),
            types.InlineKeyboardButton("🗑 حذف", callback_data=f"delete_{b['id']}")
        )
        
        bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

# ==================== فعال/غیرفعال ربات ====================
@bot.message_handler(func=lambda m: m.text == '🔄 فعال/غیرفعال ربات')
def toggle_bot_prompt(message):
    user_id = message.from_user.id
    bots_list = db.execute('SELECT id, name, status FROM bots WHERE user_id = ?', (user_id,))
    
    if not bots_list:
        bot.send_message(message.chat.id, "📋 شما هیچ رباتی ندارید.")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots_list:
        status_emoji = "🟢" if b['status'] == 'running' else "🔴"
        markup.add(types.InlineKeyboardButton(f"{status_emoji} {b['name']}", callback_data=f"toggle_{b['id']}"))
    
    bot.send_message(message.chat.id, "🔄 ربات مورد نظر را انتخاب کنید:", reply_markup=markup)

# ==================== حذف ربات ====================
@bot.message_handler(func=lambda m: m.text == '🗑 حذف ربات')
def delete_bot_prompt(message):
    user_id = message.from_user.id
    bots_list = db.execute('SELECT id, name, status FROM bots WHERE user_id = ?', (user_id,))
    
    if not bots_list:
        bot.send_message(message.chat.id, "📋 شما هیچ رباتی ندارید.")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots_list:
        markup.add(types.InlineKeyboardButton(f"🗑 {b['name']}", callback_data=f"delete_{b['id']}"))
    
    bot.send_message(message.chat.id, "🗑 ربات مورد نظر برای حذف را انتخاب کنید:", reply_markup=markup)

# ==================== کال‌بک‌های اینلاین ====================
@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_'))
def toggle_bot(call):
    user_id = call.from_user.id
    bot_id = call.data.replace('toggle_', '')
    
    bot_data = db.execute('SELECT * FROM bots WHERE id = ?', (bot_id,))
    if not bot_data:
        bot.answer_callback_query(call.id, "❌ ربات یافت نشد")
        return
    
    bot_data = dict(bot_data[0])
    if bot_data['user_id'] != user_id:
        bot.answer_callback_query(call.id, "❌ این ربات متعلق به شما نیست")
        return
    
    if bot_data['status'] == 'running':
        # متوقف کردن
        if stop_bot_process(bot_id):
            db.execute('UPDATE bots SET status = "stopped" WHERE id = ?', (bot_id,))
            bot.answer_callback_query(call.id, "✅ ربات متوقف شد")
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            bot.send_message(call.message.chat.id, f"✅ ربات {bot_data['name']} متوقف شد.")
        else:
            bot.answer_callback_query(call.id, "❌ خطا در توقف ربات")
    else:
        # فعال کردن - نیاز به بررسی اشتراک
        can_create, msg = can_create_bot(user_id)
        if not can_create:
            bot.answer_callback_query(call.id, msg[:50])
            return
        
        # خواندن کد از فایل
        if os.path.exists(bot_data['file_path']):
            with open(bot_data['file_path'], 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
            
            success, pid = run_bot_process(bot_id, code, bot_data['token'])
            
            if success:
                expires_at = datetime.now() + timedelta(minutes=get_setting('bot_active_minutes'))
                db.execute('UPDATE bots SET status = "running", pid = ?, expires_at = ? WHERE id = ?', 
                          (pid, expires_at.isoformat(), bot_id))
                bot.answer_callback_query(call.id, f"✅ ربات فعال شد - {get_setting('bot_active_minutes')} دقیقه زمان دارد")
                bot.send_message(call.message.chat.id, f"✅ ربات {bot_data['name']} فعال شد.\n⏱️ به مدت {get_setting('bot_active_minutes')} دقیقه فعال خواهد ماند.")
            else:
                bot.answer_callback_query(call.id, f"❌ خطا: {pid[:50] if pid else 'مشخص نشده'}")
        else:
            bot.answer_callback_query(call.id, "❌ فایل ربات یافت نشد")

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
def delete_bot_callback(call):
    user_id = call.from_user.id
    bot_id = call.data.replace('delete_', '')
    
    if delete_bot(bot_id, user_id):
        bot.answer_callback_query(call.id, "✅ ربات حذف شد")
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        bot.send_message(call.message.chat.id, "✅ ربات با موفقیت حذف شد.")
    else:
        bot.answer_callback_query(call.id, "❌ خطا در حذف ربات")

# ==================== کیف پول و اشتراک ====================
@bot.message_handler(func=lambda m: m.text == '💰 کیف پول و اشتراک')
def wallet(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    is_subscribed = check_subscription(user_id)
    active_bots = get_active_bots_count(user_id)
    max_bots = get_setting('max_bots_per_user')
    
    expiry_text = ""
    if is_subscribed and user['subscription_expiry']:
        expiry = datetime.fromisoformat(user['subscription_expiry'])
        expiry_text = f"\n📅 انقضای اشتراک: {expiry.strftime('%Y-%m-%d %H:%M')}"
    
    text = (f"💰 **کیف پول و اشتراک شما**\n\n"
            f"👤 {user['first_name']}\n"
            f"🆔 `{user_id}`\n"
            f"💳 وضعیت اشتراک: {'✅ فعال' if is_subscribed else '❌ غیرفعال'}{expiry_text}\n"
            f"💰 موجودی کیف پول: {user['wallet_balance']:,} تومان\n"
            f"🤖 ربات‌های فعال: {active_bots}/{max_bots}\n"
            f"👥 تعداد دعوت: {user['referrals_count']}\n\n")
    
    if not is_subscribed:
        card = get_setting('card_number_display')
        bank = get_setting('card_bank')
        holder = get_setting('card_holder')
        price = get_setting('subscription_price_str')
        
        text += (f"💳 **اطلاعات پرداخت اشتراک:**\n"
                f"🏦 {bank}\n"
                f"💳 `{card}`\n"
                f"👤 {holder}\n"
                f"💰 مبلغ: {price}\n\n"
                f"📸 پس از واریز، رسید را به صورت عکس ارسال کنید.\n"
                f"⏱️ رسید شما ظرف ۲۴ ساعت بررسی می‌شود.")
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== رسید پرداخت ====================
@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    
    # بررسی وجود رسید pending قبلی
    existing = db.execute('SELECT id FROM receipts WHERE user_id = ? AND status = "pending"', (user_id,))
    if existing:
        bot.reply_to(message, "⏳ شما یک رسید در انتظار تایید دارید. لطفاً صبر کنید تا بررسی شود.")
        return
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        payment_code = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:8].upper()
        receipt_path = os.path.join(DIRS['RECEIPTS'], f"{user_id}_{payment_code}.jpg")
        
        with open(receipt_path, 'wb') as f:
            f.write(downloaded)
        
        db.execute('''
            INSERT INTO receipts (user_id, amount, receipt_path, payment_code, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, get_setting('subscription_price'), receipt_path, payment_code, datetime.now().isoformat()))
        
        bot.reply_to(message, f"✅ رسید شما با موفقیت دریافت شد.\n💰 مبلغ: {get_setting('subscription_price_str')}\n🆔 کد پیگیری: `{payment_code}`\n\n⏱️ رسید شما ظرف ۲۴ ساعت بررسی می‌شود.", parse_mode='Markdown')
        
        # اطلاع به ادمین
        user = get_user(user_id)
        for admin_id in ADMIN_IDS:
            try:
                with open(receipt_path, 'rb') as f:
                    bot.send_photo(admin_id, f, caption=f"📸 رسید جدید\n👤 {user['first_name']}\n🆔 {user_id}\n💰 {get_setting('subscription_price_str')}\n🆔 {payment_code}")
            except:
                bot.send_message(admin_id, f"📸 رسید جدید\n👤 {user['first_name']}\n🆔 {user_id}\n💰 {get_setting('subscription_price_str')}\n🆔 {payment_code}")
                
    except Exception as e:
        bot.reply_to(message, f"❌ خطا در دریافت رسید: {str(e)[:100]}")

# ==================== دعوت دوستان ====================
@bot.message_handler(func=lambda m: m.text == '👥 دعوت دوستان')
def invite(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    referral_link = f"https://t.me/{BOT_USERNAME}?start={user['referral_code']}"
    
    text = (f"👥 **سیستم دعوت از دوستان**\n\n"
            f"🎁 کد معرف شما: `{user['referral_code']}`\n"
            f"🔗 لینک دعوت: `{referral_link}`\n"
            f"📊 تعداد دعوت‌ها: {user['referrals_count']}\n"
            f"💰 کمیسیون هر دعوت: {get_setting('withdraw_percent')}% از مبلغ اشتراک ({int(get_setting('subscription_price') * get_setting('withdraw_percent') / 100):,} تومان)\n\n"
            f"⭐ هر دوست شما که با لینک شما عضو شود و اشتراک بخرد، کمیسیون به کیف پول شما اضافه می‌شود.")
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📋 کپی لینک", callback_data=f"copy_{user['referral_code']}"))
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('copy_'))
def copy_referral_link(call):
    code = call.data.replace('copy_', '')
    link = f"https://t.me/{BOT_USERNAME}?start={code}"
    bot.answer_callback_query(call.id, f"✅ لینک کپی شد!\n{link}", show_alert=True)

# ==================== درخواست برداشت ====================
@bot.message_handler(func=lambda m: m.text == '💸 درخواست برداشت')
def withdraw_request(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    min_withdraw = get_setting('min_withdraw')
    
    if user['wallet_balance'] < min_withdraw:
        bot.send_message(message.chat.id, f"❌ موجودی کیف پول شما ({user['wallet_balance']:,} تومان) کمتر از حداقل مبلغ برداشت ({min_withdraw:,} تومان) است.")
        return
    
    msg = bot.send_message(message.chat.id, "💳 **لطفاً شماره کارت خود را وارد کنید (۱۶ رقم):**")
    bot.register_next_step_handler(msg, process_withdraw_card, user)

def process_withdraw_card(message, user):
    card_number = message.text.strip().replace(' ', '')
    if not re.match(r'^\d{16}$', card_number):
        bot.reply_to(message, "❌ شماره کارت باید ۱۶ رقم باشد. دوباره تلاش کنید.\n/start برای شروع مجدد")
        return
    
    msg = bot.send_message(message.chat.id, "👤 **نام صاحب کارت را وارد کنید:**")
    bot.register_next_step_handler(msg, process_withdraw_holder, user, card_number)

def process_withdraw_holder(message, user, card_number):
    card_holder = message.text.strip()
    
    db.execute('''
        INSERT INTO withdraw_requests (user_id, amount, card_number, card_holder, created_at, status)
        VALUES (?, ?, ?, ?, ?, 'pending')
    ''', (user['user_id'], user['wallet_balance'], card_number, card_holder, datetime.now().isoformat()))
    
    # صفر کردن موجودی
    db.execute('UPDATE users SET wallet_balance = 0 WHERE user_id = ?', (user['user_id'],))
    
    bot.reply_to(message, f"✅ درخواست برداشت به مبلغ {user['wallet_balance']:,} تومان با موفقیت ثبت شد.\n\nپس از بررسی، مبلغ به کارت شما واریز می‌شود.")
    
    # اطلاع به ادمین
    for admin_id in ADMIN_IDS:
        bot.send_message(admin_id, f"💰 درخواست برداشت جدید\n👤 {user['first_name']}\n🆔 {user['user_id']}\n💰 {user['wallet_balance']:,} تومان\n💳 {card_number}\n👤 {card_holder}")

# ==================== راهنما ====================
@bot.message_handler(func=lambda m: m.text == '📚 راهنما')
def guide(message):
    guide_text = get_setting('guide_text')
    bot.send_message(message.chat.id, guide_text)

# ==================== پشتیبانی ====================
@bot.message_handler(func=lambda m: m.text == '📞 پشتیبانی')
def support(message):
    bot.send_message(message.chat.id, "📞 **پشتیبانی**\n\nبرای ارتباط با پشتیبانی، به آیدی زیر پیام دهید:\n\n@shahraghee13\n\nسوالات خود را مطرح کنید.")

# ==================== پنل مدیریت ====================
@bot.message_handler(func=lambda m: m.text == '👑 پنل مدیریت')
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📸 تایید فیش", callback_data="admin_receipts"),
        types.InlineKeyboardButton("💰 تایید برداشت", callback_data="admin_withdraws"),
        types.InlineKeyboardButton("👥 لیست کاربران", callback_data="admin_users"),
        types.InlineKeyboardButton("🤖 لیست ربات‌ها", callback_data="admin_bots"),
        types.InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings"),
        types.InlineKeyboardButton("📊 آمار", callback_data="admin_stats")
    )
    
    bot.send_message(message.chat.id, "👑 **پنل مدیریت**", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_receipts")
def admin_receipts(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    receipts = db.execute('SELECT * FROM receipts WHERE status = "pending" ORDER BY created_at')
    if not receipts:
        bot.answer_callback_query(call.id, "هیچ رسید جدیدی وجود ندارد")
        return
    
    for r in receipts:
        user = get_user(r['user_id'])
        text = f"📸 **رسید جدید**\n👤 {user['first_name'] if user else 'نامشخص'}\n🆔 {r['user_id']}\n💰 {r['amount']:,} تومان\n🆔 {r['payment_code']}\n🕐 {r['created_at'][:16]}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_{r['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"reject_{r['id']}")
        )
        
        if os.path.exists(r['receipt_path']):
            with open(r['receipt_path'], 'rb') as f:
                bot.send_photo(call.message.chat.id, f, caption=text, reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_'))
def approve_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    receipt_id = int(call.data.replace('approve_', ''))
    receipt = db.execute('SELECT user_id FROM receipts WHERE id = ?', (receipt_id,))
    
    if receipt:
        user_id = receipt[0]['user_id']
        activate_subscription(user_id)
        db.execute('UPDATE receipts SET status = "approved" WHERE id = ?', (receipt_id,))
        
        bot.answer_callback_query(call.id, "✅ اشتراک کاربر فعال شد")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        
        try:
            bot.send_message(user_id, f"✅ **اشتراک شما با موفقیت فعال شد!**\n\n🎉 از این پس می‌توانید حداکثر {get_setting('max_bots_per_user')} ربات فعال داشته باشید.\n⏱️ هر ربات به مدت {get_setting('bot_active_minutes')} دقیقه فعال می‌ماند.\n\nاز دکمه «ساخت ربات جدید» استفاده کنید.")
        except:
            pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_'))
def reject_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    receipt_id = int(call.data.replace('reject_', ''))
    receipt = db.execute('SELECT user_id FROM receipts WHERE id = ?', (receipt_id,))
    
    if receipt:
        db.execute('UPDATE receipts SET status = "rejected" WHERE id = ?', (receipt_id,))
        bot.answer_callback_query(call.id, "❌ رسید رد شد")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        
        try:
            bot.send_message(receipt[0]['user_id'], "❌ متأسفانه رسید شما تأیید نشد. لطفاً دوباره اقدام کنید.")
        except:
            pass

@bot.callback_query_handler(func=lambda call: call.data == "admin_withdraws")
def admin_withdraws(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    withdraws = db.execute('SELECT * FROM withdraw_requests WHERE status = "pending" ORDER BY created_at')
    if not withdraws:
        bot.answer_callback_query(call.id, "هیچ درخواست برداشتی وجود ندارد")
        return
    
    for w in withdraws:
        user = get_user(w['user_id'])
        text = f"💰 **درخواست برداشت**\n👤 {user['first_name'] if user else 'نامشخص'}\n🆔 {w['user_id']}\n💰 {w['amount']:,} تومان\n💳 {w['card_number']}\n👤 {w['card_holder']}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ تایید واریز", callback_data=f"withdraw_approve_{w['id']}"))
        
        bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('withdraw_approve_'))
def approve_withdraw(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    withdraw_id = int(call.data.replace('withdraw_approve_', ''))
    db.execute('UPDATE withdraw_requests SET status = "approved" WHERE id = ?', (withdraw_id,))
    
    bot.answer_callback_query(call.id, "✅ برداشت تایید شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_users")
def admin_users(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    users = db.execute('SELECT user_id, first_name, username, subscription_status, wallet_balance, referrals_count FROM users ORDER BY created_at DESC LIMIT 20')
    
    if not users:
        bot.send_message(call.message.chat.id, "هیچ کاربری یافت نشد")
        return
    
    text = "👥 **۲۰ کاربر اخیر:**\n\n"
    for u in users:
        status = "✅ فعال" if u['subscription_status'] == 'active' else "❌ غیرفعال"
        text += f"👤 {u['first_name']}\n🆔 {u['user_id']}\n📊 {status} | 💰 {u['wallet_balance']:,} | 👥 {u['referrals_count']}\n\n"
    
    bot.send_message(call.message.chat.id, text)

@bot.callback_query_handler(func=lambda call: call.data == "admin_bots")
def admin_bots(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    bots_list = db.execute('SELECT id, name, user_id, status, created_at FROM bots ORDER BY created_at DESC LIMIT 30')
    
    if not bots_list:
        bot.send_message(call.message.chat.id, "هیچ رباتی یافت نشد")
        return
    
    text = "🤖 **۳۰ ربات اخیر:**\n\n"
    for b in bots_list:
        status = "🟢 فعال" if b['status'] == 'running' else "🔴 متوقف"
        text += f"🤖 {b['name']}\n👤 {b['user_id']}\n📊 {status}\n🆔 `{b['id']}`\n\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "admin_settings")
def admin_settings(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💳 تغییر کارت", callback_data="set_card"),
        types.InlineKeyboardButton("💰 تغییر قیمت اشتراک", callback_data="set_price"),
        types.InlineKeyboardButton("🤖 حداکثر ربات کاربر", callback_data="set_max_bots"),
        types.InlineKeyboardButton("⏱️ زمان فعالسازی", callback_data="set_duration"),
        types.InlineKeyboardButton("📝 تغییر متن راهنما", callback_data="set_guide")
    )
    
    bot.edit_message_text("⚙️ **تنظیمات سیستم**\n\n"
                         f"💳 کارت: {get_setting('card_number_display')}\n"
                         f"💰 قیمت اشتراک: {get_setting('subscription_price_str')}\n"
                         f"🤖 حداکثر ربات: {get_setting('max_bots_per_user')}\n"
                         f"⏱️ زمان فعالسازی: {get_setting('bot_active_minutes')} دقیقه", 
                         call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "set_card")
def set_card_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "💳 **شماره کارت جدید را وارد کنید (۱۶ رقم):**")
    bot.register_next_step_handler(msg, process_set_card)

def process_set_card(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    card = message.text.strip().replace(' ', '')
    if len(card) == 16 and card.isdigit():
        update_setting('card_number', card)
        display = ' '.join([card[i:i+4] for i in range(0, 16, 4)])
        update_setting('card_number_display', display)
        bot.reply_to(message, f"✅ شماره کارت به {display} تغییر کرد")
    else:
        bot.reply_to(message, "❌ شماره کارت نامعتبر")

@bot.callback_query_handler(func=lambda call: call.data == "set_price")
def set_price_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "💰 **قیمت جدید اشتراک را وارد کنید (تومان):**")
    bot.register_next_step_handler(msg, process_set_price)

def process_set_price(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        price = int(message.text.strip())
        if price >= 100000:
            update_setting('subscription_price', price)
            update_setting('subscription_price_str', f"{price:,} تومان")
            bot.reply_to(message, f"✅ قیمت اشتراک به {price:,} تومان تغییر کرد")
        else:
            bot.reply_to(message, "❌ قیمت باید حداقل ۱۰۰,۰۰۰ تومان باشد")
    except:
        bot.reply_to(message, "❌ عدد معتبر وارد کنید")

@bot.callback_query_handler(func=lambda call: call.data == "set_max_bots")
def set_max_bots_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "🤖 **حداکثر تعداد ربات فعال برای هر کاربر را وارد کنید (۱ تا ۱۰):**")
    bot.register_next_step_handler(msg, process_set_max_bots)

def process_set_max_bots(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        max_bots = int(message.text.strip())
        if 1 <= max_bots <= 10:
            update_setting('max_bots_per_user', max_bots)
            bot.reply_to(message, f"✅ حداکثر ربات هر کاربر به {max_bots} تغییر کرد")
        else:
            bot.reply_to(message, "❌ عدد باید بین ۱ تا ۱۰ باشد")
    except:
        bot.reply_to(message, "❌ عدد معتبر وارد کنید")

@bot.callback_query_handler(func=lambda call: call.data == "set_duration")
def set_duration_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "⏱️ **زمان فعالسازی هر ربات را به دقیقه وارد کنید (۱ تا ۳۰):**")
    bot.register_next_step_handler(msg, process_set_duration)

def process_set_duration(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        duration = int(message.text.strip())
        if 1 <= duration <= 30:
            update_setting('bot_active_minutes', duration)
            bot.reply_to(message, f"✅ زمان فعالسازی هر ربات به {duration} دقیقه تغییر کرد")
        else:
            bot.reply_to(message, "❌ عدد باید بین ۱ تا ۳۰ باشد")
    except:
        bot.reply_to(message, "❌ عدد معتبر وارد کنید")

@bot.callback_query_handler(func=lambda call: call.data == "set_guide")
def set_guide_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "📝 **متن جدید راهنما را ارسال کنید:**")
    bot.register_next_step_handler(msg, process_set_guide)

def process_set_guide(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    update_setting('guide_text', message.text)
    bot.reply_to(message, "✅ متن راهنما به‌روزرسانی شد")

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_stats(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    total_users = db.execute('SELECT COUNT(*) as count FROM users')[0]['count']
    active_subs = db.execute('SELECT COUNT(*) as count FROM users WHERE subscription_status = "active"')[0]['count']
    total_bots = db.execute('SELECT COUNT(*) as count FROM bots')[0]['count']
    active_bots = db.execute('SELECT COUNT(*) as count FROM bots WHERE status = "running"')[0]['count']
    total_wallet = db.execute('SELECT SUM(wallet_balance) as total FROM users')[0]['total'] or 0
    pending_receipts = db.execute('SELECT COUNT(*) as count FROM receipts WHERE status = "pending"')[0]['count']
    pending_withdraws = db.execute('SELECT COUNT(*) as count FROM withdraw_requests WHERE status = "pending"')[0]['count']
    
    text = (f"📊 **آمار کلی سیستم**\n\n"
            f"👥 کل کاربران: {total_users}\n"
            f"✅ اشتراک فعال: {active_subs}\n"
            f"🤖 کل ربات‌ها: {total_bots}\n"
            f"🟢 ربات فعال: {active_bots}\n"
            f"💰 کل موجودی کیف پول: {total_wallet:,} تومان\n"
            f"📸 رسیدهای pending: {pending_receipts}\n"
            f"💰 درخواست برداشت pending: {pending_withdraws}\n\n"
            f"⚙️ تنظیمات فعلی:\n"
            f"🤖 حداکثر ربات هر کاربر: {get_setting('max_bots_per_user')}\n"
            f"⏱️ زمان فعالسازی: {get_setting('bot_active_minutes')} دقیقه\n"
            f"💰 قیمت اشتراک: {get_setting('subscription_price_str')}")
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id)

# ==================== پیام همگانی ====================
@bot.message_handler(func=lambda m: m.text == '📢 پیام همگانی')
def broadcast_prompt(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(message.chat.id, "📢 **متن پیام همگانی را ارسال کنید:**")
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    text = message.text
    users = db.execute("SELECT user_id FROM users")
    sent = 0
    failed = 0
    
    status_msg = bot.reply_to(message, "🔄 در حال ارسال پیام همگانی...")
    
    for user in users:
        try:
            bot.send_message(user['user_id'], text)
            sent += 1
            time.sleep(0.05)
        except:
            failed += 1
    
    bot.edit_message_text(f"✅ **نتیجه ارسال پیام همگانی**\n\n📨 ارسال موفق: {sent}\n❌ ناموفق: {failed}", 
                         message.chat.id, status_msg.message_id)

# ==================== مانیتور خودکار ====================
def auto_monitor():
    """بررسی خودکار ربات‌های منقضی شده"""
    while True:
        try:
            now = datetime.now().isoformat()
            # ربات‌هایی که زمانشان منقضی شده
            expired_bots = db.execute('SELECT id, user_id FROM bots WHERE expires_at < ? AND status = "running"', (now,))
            
            for bot_rec in expired_bots:
                stop_bot_process(bot_rec['id'])
                db.execute('UPDATE bots SET status = "stopped" WHERE id = ?', (bot_rec['id'],))
                try:
                    bot.send_message(bot_rec['user_id'], f"⏰ یکی از ربات‌های شما به دلیل پایان زمان {get_setting('bot_active_minutes')} دقیقه‌ای متوقف شد.\nبرای فعالسازی مجدد از بخش «ربات‌های من» استفاده کنید.")
                except:
                    pass
            
            time.sleep(30)
        except Exception as e:
            print(f"Monitor error: {e}")
            time.sleep(60)

threading.Thread(target=auto_monitor, daemon=True).start()

# ==================== اجرا ====================
if __name__ == "__main__":
    print("=" * 60)
    print("🚀 ربات مادر - نسخه نهایی پایدار")
    print("=" * 60)
    print(f"👑 ادمین‌ها: {ADMIN_IDS}")
    print(f"💰 قیمت اشتراک: {get_setting('subscription_price_str')}")
    print(f"🤖 حداکثر ربات هر کاربر: {get_setting('max_bots_per_user')}")
    print(f"⏱️ زمان فعالسازی هر ربات: {get_setting('bot_active_minutes')} دقیقه")
    print("=" * 60)
    print("✅ ربات با موفقیت راه‌اندازی شد!")
    print("=" * 60)
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)