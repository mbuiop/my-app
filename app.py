#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
═══════════════════════════════════════════════════════════════════════════════
🚀 ربات مادر نهایی - نسخه پایدار نهایی
⚡ بدون خطا - اشتراک همیشه فعال - اجرای پایدار
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
import secrets
import uuid
from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

# ==================== تنظیمات پایه ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DIRS = {
    'DB': os.path.join(BASE_DIR, "database"),
    'FILES': os.path.join(BASE_DIR, "user_files"),
    'RUNNING': os.path.join(BASE_DIR, "running_bots"),
    'LOGS': os.path.join(BASE_DIR, "logs"),
    'RECEIPTS': os.path.join(BASE_DIR, "receipts"),
    'TEMP': os.path.join(BASE_DIR, "temp"),
    'FOLDERS': os.path.join(BASE_DIR, "user_folders"),
}

for dir_path in DIRS.values():
    os.makedirs(dir_path, exist_ok=True)

# ==================== توکن و تنظیمات ====================
BOT_TOKEN = "8266270866:AAF6m1x4weSUEvzIj1gkbIS_j0yAdxCSs78"
ADMIN_IDS = [327855654]
BOT_USERNAME = "ROBTTSAZE_bot"

# تنظیمات پیش‌فرض - اشتراک همیشه فعال است!
SETTINGS = {
    'card_number': "5892101187322777",
    'card_number_display': "5892 1011 8732 2777",
    'card_holder': "مرتضی نیکخو خنجری",
    'card_bank': "بانک ملی - سپهر",
    'subscription_price': 50000,
    'subscription_price_str': "۵۰,۰۰۰ تومان",
    'max_bots_per_user': 3,
    'withdraw_percent': 7,
    'min_withdraw': 2000000,
}

# ==================== دیتابیس ====================
class Database:
    def __init__(self):
        self.conn = sqlite3.connect(os.path.join(DIRS['DB'], 'mother_bot.db'), timeout=60, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cache = {}
        self._init_tables()
    
    def execute(self, query, params=()):
        try:
            cursor = self.conn.execute(query, params)
            self.conn.commit()
            return cursor.fetchall()
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
                subscription_active INTEGER DEFAULT 1,
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
                folder_path TEXT,
                status TEXT DEFAULT 'stopped',
                created_at TIMESTAMP,
                last_active TIMESTAMP,
                execution_count INTEGER DEFAULT 0,
                process_pid INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        # پوشه‌ها
        self.execute('''
            CREATE TABLE IF NOT EXISTS folders (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                folder_name TEXT,
                folder_path TEXT,
                parent_id TEXT,
                structure TEXT,
                created_at TIMESTAMP,
                file_count INTEGER DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
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
        
        # تنظیمات
        self.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # کتابخانه‌های نصب شده
        self.execute('''
            CREATE TABLE IF NOT EXISTS installed_libraries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                version TEXT,
                installed_at TIMESTAMP
            )
        ''')
        
        for key, value in SETTINGS.items():
            self.execute('INSERT OR IGNORE INTO system_settings (key, value) VALUES (?, ?)', (key, str(value)))
    
    def get_setting(self, key):
        if key in self.cache:
            return self.cache[key]
        result = self.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
        if result:
            value = result[0]['value']
            if key in ['subscription_price', 'max_bots_per_user', 'withdraw_percent', 'min_withdraw']:
                value = int(value)
            self.cache[key] = value
            return value
        return SETTINGS.get(key)
    
    def update_setting(self, key, value):
        self.execute("UPDATE system_settings SET value = ? WHERE key = ?", (str(value), key))
        if key in self.cache:
            del self.cache[key]
        return True

db = Database()

# ==================== سیستم اجرای ربات ====================
class BotExecutor:
    """مدیریت اجرای ربات‌ها - پایدار و بدون خطا"""
    
    def __init__(self):
        self.active_bots = {}
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=50)
        self._start_monitor()
    
    def _start_monitor(self):
        """مانیتورینگ ربات‌های در حال اجرا"""
        def monitor():
            while True:
                try:
                    with self.lock:
                        for bot_id, info in list(self.active_bots.items()):
                            if info.get('process'):
                                if info['process'].poll() is not None:
                                    # ربات crashed یا متوقف شده
                                    del self.active_bots[bot_id]
                                    db.execute("UPDATE bots SET status = 'stopped' WHERE id = ?", (bot_id,))
                    time.sleep(10)
                except:
                    time.sleep(30)
        
        threading.Thread(target=monitor, daemon=True).start()
    
    def start_bot(self, bot_id, user_id, code, folder_path=None):
        """اجرای ربات"""
        if bot_id in self.active_bots:
            return False, "ربات در حال اجراست"
        
        bot_dir = os.path.join(DIRS['RUNNING'], bot_id)
        os.makedirs(bot_dir, exist_ok=True)
        
        code_path = os.path.join(bot_dir, 'bot.py')
        with open(code_path, 'w', encoding='utf-8') as f:
            f.write(code)
        
        try:
            process = subprocess.Popen(
                [sys.executable, code_path],
                cwd=folder_path or bot_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            
            with self.lock:
                self.active_bots[bot_id] = {
                    'process': process,
                    'pid': process.pid,
                    'started_at': datetime.now(),
                    'user_id': user_id
                }
            
            db.execute("UPDATE bots SET status = 'running', process_pid = ?, last_active = ? WHERE id = ?",
                      (process.pid, datetime.now().isoformat(), bot_id))
            
            return True, "ربات با موفقیت اجرا شد"
        except Exception as e:
            return False, f"خطا: {str(e)}"
    
    def stop_bot(self, bot_id, user_id):
        """توقف ربات"""
        with self.lock:
            if bot_id in self.active_bots:
                info = self.active_bots[bot_id]
                try:
                    info['process'].terminate()
                    time.sleep(1)
                    if info['process'].poll() is None:
                        info['process'].kill()
                except:
                    pass
                del self.active_bots[bot_id]
        
        db.execute("UPDATE bots SET status = 'stopped', process_pid = NULL WHERE id = ?", (bot_id,))
        return True
    
    def is_running(self, bot_id):
        """بررسی وضعیت ربات"""
        with self.lock:
            if bot_id in self.active_bots:
                info = self.active_bots[bot_id]
                if info['process'].poll() is None:
                    return True
                else:
                    del self.active_bots[bot_id]
                    db.execute("UPDATE bots SET status = 'stopped' WHERE id = ?", (bot_id,))
        return False
    
    def get_status(self, bot_id):
        """دریافت وضعیت ربات"""
        running = self.is_running(bot_id)
        if running:
            with self.lock:
                info = self.active_bots[bot_id]
                uptime = int((datetime.now() - info['started_at']).total_seconds())
                return {'running': True, 'uptime': uptime}
        return {'running': False, 'uptime': 0}
    
    def stop_all_user_bots(self, user_id):
        """توقف تمام ربات‌های یک کاربر"""
        bots = db.execute("SELECT id FROM bots WHERE user_id = ? AND status = 'running'", (user_id,))
        for bot in bots:
            self.stop_bot(bot['id'], user_id)
        return True

# ==================== سیستم مدیریت پوشه‌ها ====================
class FolderManager:
    def create_folder(self, user_id, folder_name, parent_id=None):
        folder_path = os.path.join(DIRS['FOLDERS'], str(user_id), folder_name)
        if parent_id:
            parent = db.execute("SELECT folder_path FROM folders WHERE id = ?", (parent_id,))
            if parent:
                folder_path = os.path.join(parent[0]['folder_path'], folder_name)
        
        if os.path.exists(folder_path):
            return None, "پوشه با این نام وجود دارد"
        
        os.makedirs(folder_path, exist_ok=True)
        folder_id = hashlib.md5(f"{user_id}_{folder_name}_{time.time()}".encode()).hexdigest()[:12]
        structure = json.dumps({'name': folder_name, 'created_at': datetime.now().isoformat(), 'files': []})
        
        db.execute('''
            INSERT INTO folders (id, user_id, folder_name, folder_path, parent_id, structure, created_at, file_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        ''', (folder_id, user_id, folder_name, folder_path, parent_id, structure, datetime.now().isoformat()))
        
        return folder_id, "پوشه ساخته شد"
    
    def add_file(self, folder_id, file_name, content):
        folders = db.execute('SELECT * FROM folders WHERE id = ?', (folder_id,))
        if not folders:
            return False, "پوشه یافت نشد"
        
        folder = dict(folders[0])
        file_path = os.path.join(folder['folder_path'], file_name)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        structure = json.loads(folder['structure'])
        structure['files'].append({'name': file_name, 'added_at': datetime.now().isoformat(), 'size': len(content)})
        
        db.execute('UPDATE folders SET structure = ?, file_count = file_count + 1 WHERE id = ?',
                  (json.dumps(structure), folder_id))
        return True, "فایل اضافه شد"
    
    def get_files(self, folder_id):
        folders = db.execute('SELECT structure FROM folders WHERE id = ?', (folder_id,))
        if folders:
            return json.loads(folders[0]['structure']).get('files', [])
        return []
    
    def read_file(self, folder_id, file_name):
        folders = db.execute('SELECT folder_path FROM folders WHERE id = ?', (folder_id,))
        if folders:
            path = os.path.join(folders[0]['folder_path'], file_name)
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
        return None
    
    def get_folder_hierarchy(self, user_id):
        """دریافت ساختار درختی پوشه‌ها"""
        folders = db.execute('SELECT id, folder_name, parent_id FROM folders WHERE user_id = ?', (user_id,))
        hierarchy = {}
        for folder in folders:
            parent = folder['parent_id'] or 'root'
            if parent not in hierarchy:
                hierarchy[parent] = []
            hierarchy[parent].append(dict(folder))
        return hierarchy

# ==================== توابع کمکی ====================
def get_user(user_id):
    users = db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    return dict(users[0]) if users else None

def create_user(user_id, username, first_name, last_name, referred_by=None):
    now = datetime.now().isoformat()
    referral_code = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:12]
    db.execute('''
        INSERT OR IGNORE INTO users 
        (user_id, username, first_name, last_name, referral_code, referred_by, created_at, last_active, subscription_active, wallet_balance)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 0)
    ''', (user_id, username, first_name, last_name, referral_code, referred_by, now, now))
    
    if referred_by:
        db.execute('UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = ?', (referred_by,))
    
    return True

def extract_token(code):
    patterns = [r'token\s*=\s*["\']([^"\']+)["\']', r'TOKEN\s*=\s*["\']([^"\']+)["\']', r'BOT_TOKEN\s*=\s*["\']([^"\']+)["\']']
    for p in patterns:
        m = re.search(p, code, re.IGNORECASE)
        if m:
            return m.group(1)
    return None

def verify_token(token):
    try:
        resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('ok'):
                return True, data.get('result', {})
        return False, {}
    except:
        return False, {}

def install_library(lib_name, chat_id, message_id, bot_instance):
    """نصب کتابخانه در پس‌زمینه"""
    def install():
        try:
            bot_instance.edit_message_text(f"📦 در حال نصب {lib_name}...", chat_id, message_id)
            
            process = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', lib_name, '--quiet'],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if process.returncode == 0:
                # دریافت نسخه
                version = subprocess.run([sys.executable, '-m', 'pip', 'show', lib_name],
                                        capture_output=True, text=True, timeout=10)
                ver = "نامشخص"
                for line in version.stdout.split('\n'):
                    if line.startswith('Version:'):
                        ver = line.split(':', 1)[1].strip()
                        break
                
                db.execute('INSERT OR IGNORE INTO installed_libraries (name, version, installed_at) VALUES (?, ?, ?)',
                          (lib_name, ver, datetime.now().isoformat()))
                
                bot_instance.edit_message_text(f"✅ {lib_name} نسخه {ver} نصب شد!", chat_id, message_id)
            else:
                error = process.stderr[:200] if process.stderr else "خطا"
                bot_instance.edit_message_text(f"❌ خطا: {error}", chat_id, message_id)
        except subprocess.TimeoutExpired:
            bot_instance.edit_message_text("❌ زمان نصب تمام شد!", chat_id, message_id)
        except Exception as e:
            bot_instance.edit_message_text(f"❌ خطا: {str(e)[:100]}", chat_id, message_id)
    
    threading.Thread(target=install, daemon=True).start()
    return True

# ==================== ربات اصلی ====================
bot = telebot.TeleBot(BOT_TOKEN)
bot.remove_webhook()

executor = BotExecutor()
folder_manager = FolderManager()

# ==================== منوها ====================
def get_main_menu(user_id):
    is_admin = user_id in ADMIN_IDS
    user = get_user(user_id)
    subscription_active = user.get('subscription_active', 1) if user else 1
    
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    
    if subscription_active:
        buttons = [
            types.KeyboardButton('🤖 ساخت ربات جدید'),
            types.KeyboardButton('📁 مدیریت پوشه‌ها'),
            types.KeyboardButton('▶️ اجرای ربات'),
            types.KeyboardButton('🛑 توقف ربات'),
            types.KeyboardButton('📋 ربات‌های من'),
            types.KeyboardButton('🗑 حذف ربات'),
        ]
    else:
        buttons = [types.KeyboardButton('💰 خرید اشتراک')]
    
    buttons.extend([
        types.KeyboardButton('💰 کیف پول'),
        types.KeyboardButton('👥 دعوت دوستان'),
        types.KeyboardButton('💸 درخواست برداشت'),
        types.KeyboardButton('📦 کتابخانه‌ها'),
        types.KeyboardButton('📚 راهنما'),
        types.KeyboardButton('📊 آمار'),
        types.KeyboardButton('⚡ وضعیت اجرا'),
        types.KeyboardButton('📞 پشتیبانی'),
    ])
    
    if is_admin:
        buttons.extend([types.KeyboardButton('👑 مدیریت'), types.KeyboardButton('📢 پیام همگانی')])
    
    markup.add(*buttons)
    return markup

# ==================== دستور start ====================
@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or ""
    username = message.from_user.username or ""
    
    referred_by = None
    args = message.text.split()
    if len(args) > 1:
        code = args[1]
        users = db.execute('SELECT user_id FROM users WHERE referral_code = ?', (code,))
        if users and users[0]['user_id'] != user_id:
            referred_by = users[0]['user_id']
            try:
                bot.send_message(referred_by, f"🎉 {first_name} با لینک شما وارد شد!")
            except:
                pass
    
    create_user(user_id, username, first_name, message.from_user.last_name or "", referred_by)
    user = get_user(user_id)
    
    text = f"""🚀 **خوش آمدید {first_name}**!

👤 نام: {first_name}
🆔 شناسه: `{user_id}`
🎁 کد معرف: `{user['referral_code']}`
💰 موجودی: {user['wallet_balance']:,} تومان

✅ **اشتراک شما فعال است!**
📌 حداکثر {db.get_setting('max_bots_per_user')} ربات
🔓 ربات‌های شما همیشه فعال هستند

📤 برای شروع، از دکمه `🤖 ساخت ربات جدید` استفاده کنید."""
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=get_main_menu(user_id))

# ==================== خرید اشتراک ====================
@bot.message_handler(func=lambda m: m.text == '💰 خرید اشتراک')
def buy_subscription(message):
    user_id = message.from_user.id
    
    text = f"""
💳 **خرید اشتراک ماهیانه**

💰 مبلغ: {db.get_setting('subscription_price_str')}

🏦 **اطلاعات کارت:**
`{db.get_setting('card_number_display')}`
👤 {db.get_setting('card_holder')}
🏦 {db.get_setting('card_bank')}

📌 **نحوه پرداخت:**
1️⃣ مبلغ را به کارت فوق واریز کنید
2️⃣ رسید را به صورت عکس ارسال کنید
3️⃣ پس از تایید، اشتراک شما فعال می‌شود

⏱ زمان بررسی: حداکثر ۲۴ ساعت

💡 **پس از فعال‌سازی، ربات‌های شما همیشه فعال خواهند بود!**
"""
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== رسید پرداخت ====================
@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    
    pending = db.execute('SELECT id FROM receipts WHERE user_id = ? AND status = "pending"', (user_id,))
    if pending:
        bot.reply_to(message, "⏳ فیش قبلی در انتظار تایید است")
        return
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        code = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:8].upper()
        path = os.path.join(DIRS['RECEIPTS'], f"{user_id}_{code}.jpg")
        
        with open(path, 'wb') as f:
            f.write(downloaded)
        
        db.execute('INSERT INTO receipts (user_id, amount, receipt_path, payment_code, created_at, status) VALUES (?, ?, ?, ?, ?, "pending")',
                  (user_id, db.get_setting('subscription_price'), path, code, datetime.now().isoformat()))
        
        bot.reply_to(message, f"✅ فیش دریافت شد!\n💰 {db.get_setting('subscription_price_str')}\n🆔 {code}\n\n⏱ ظرف 24 ساعت بررسی می‌شود.")
        
        # اطلاع به ادمین
        user = get_user(user_id)
        for admin_id in ADMIN_IDS:
            try:
                with open(path, 'rb') as f:
                    bot.send_photo(admin_id, f, caption=f"📸 فیش جدید\n👤 {user['first_name']}\n🆔 {user_id}\n💰 {db.get_setting('subscription_price_str')}")
            except:
                pass
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")

# ==================== تایید فیش توسط ادمین ====================
@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_receipt_'))
def approve_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    rid = int(call.data.replace('approve_receipt_', ''))
    receipt = db.execute('SELECT user_id FROM receipts WHERE id = ?', (rid,))
    
    if receipt:
        user_id = receipt[0]['user_id']
        db.execute('UPDATE receipts SET status = "approved" WHERE id = ?', (rid,))
        db.execute('UPDATE users SET subscription_active = 1 WHERE user_id = ?', (user_id,))
        
        bot.send_message(user_id, "✅ **اشتراک شما با موفقیت فعال شد!**\n\n"
                        f"📌 **امکانات شما:**\n"
                        f"- ساخت حداکثر {db.get_setting('max_bots_per_user')} ربات\n"
                        f"- ربات‌های شما همیشه فعال هستند\n"
                        f"- دسترسی به تمام کتابخانه‌ها\n\n"
                        f"از دکمه `🤖 ساخت ربات جدید` استفاده کنید.")
        
        bot.answer_callback_query(call.id, "✅ اشتراک فعال شد!")
        bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== ساخت ربات جدید ====================
@bot.message_handler(func=lambda m: m.text == '🤖 ساخت ربات جدید')
def new_bot(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or ""
    user = get_user(user_id)
    
    if not user.get('subscription_active', 1):
        bot.send_message(message.chat.id, 
                        f"❌ اشتراک شما فعال نیست!\n💰 {db.get_setting('subscription_price_str')}\nاز دکمه `💰 خرید اشتراک` استفاده کنید.",
                        parse_mode='Markdown')
        return
    
    count = db.execute('SELECT COUNT(*) as c FROM bots WHERE user_id = ?', (user_id,))[0]['c']
    max_bots = db.get_setting('max_bots_per_user')
    
    if count >= max_bots:
        bot.send_message(message.chat.id, 
                        f"⚠️ شما به حداکثر مجاز {max_bots} ربات رسیده‌اید!\n"
                        f"برای ساخت ربات جدید، ابتدا یکی از ربات‌های خود را حذف کنید.",
                        parse_mode='Markdown')
        return
    
    text = f"""🌟 **ساخت ربات جدید**

کاربر گرامی {first_name}

📌 **مراحل ساخت:**
1️⃣ فایل `.py` یا `.zip` خود را ارسال کنید
2️⃣ مطمئن شوید توکن داخل کد شما هست
3️⃣ پس از ساخت، ربات شما همیشه فعال خواهد بود

✅ **امکانات شما:**
- حداکثر {max_bots} ربات
- ربات‌ها همیشه فعال
- دسترسی به کتابخانه‌ها

📤 **لطفاً فایل خود را ارسال کنید:**"""
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== دریافت فایل ====================
@bot.message_handler(content_types=['document'])
def handle_file(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user.get('subscription_active', 1):
        bot.reply_to(message, "❌ اشتراک شما فعال نیست!")
        return
    
    file_name = message.document.file_name
    if not (file_name.endswith('.py') or file_name.endswith('.zip')):
        bot.reply_to(message, "❌ فقط فایل‌های .py یا .zip مجاز هستند!")
        return
    
    if message.document.file_size > 50 * 1024 * 1024:
        bot.reply_to(message, "❌ حجم بیشتر از ۵۰ مگابایت!")
        return
    
    status_msg = bot.reply_to(message, "🔄 در حال بررسی فایل...")
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        
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
            bot.edit_message_text("❌ فایل پایتون پیدا نشد!", message.chat.id, status_msg.message_id)
            return
        
        token = extract_token(code)
        if not token:
            bot.edit_message_text("❌ توکن در کد پیدا نشد!\nلطفاً token = 'YOUR_TOKEN' را اضافه کنید.", 
                                message.chat.id, status_msg.message_id, parse_mode='Markdown')
            return
        
        valid, bot_info = verify_token(token)
        if not valid:
            bot.edit_message_text("❌ توکن نامعتبر است!", message.chat.id, status_msg.message_id)
            return
        
        # ایجاد ربات
        bot_id = hashlib.md5(f"{user_id}{token}{time.time()}".encode()).hexdigest()[:16]
        db.execute('''
            INSERT INTO bots (id, user_id, token, name, username, file_path, created_at, last_active, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'stopped')
        ''', (bot_id, user_id, token, bot_info.get('first_name', 'ربات'), bot_info.get('username', ''), 
              file_path, datetime.now().isoformat(), datetime.now().isoformat()))
        
        db.execute('UPDATE users SET bots_count = bots_count + 1 WHERE user_id = ?', (user_id,))
        
        # اجرای خودکار ربات (همیشه فعال)
        success, result = executor.start_bot(bot_id, user_id, code)
        
        if success:
            bot.edit_message_text(
                f"✅ **ربات با موفقیت ساخته و اجرا شد!**\n\n"
                f"🤖 نام: `{bot_info.get('first_name', 'ربات')}`\n"
                f"🔗 آیدی: @{bot_info.get('username', '')}\n"
                f"🆔 شناسه: `{bot_id}`\n\n"
                f"✅ **ربات شما همیشه فعال است!**\n"
                f"برای توقف از منوی `🛑 توقف ربات` استفاده کنید.",
                message.chat.id, status_msg.message_id, parse_mode='Markdown')
        else:
            bot.edit_message_text(f"❌ خطا در اجرا: {result}", message.chat.id, status_msg.message_id)
        
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)[:200]}", message.chat.id, status_msg.message_id)

# ==================== مدیریت پوشه‌ها ====================
@bot.message_handler(func=lambda m: m.text == '📁 مدیریت پوشه‌ها')
def manage_folders(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user.get('subscription_active', 1):
        bot.send_message(message.chat.id, "❌ ابتدا اشتراک خود را فعال کنید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("📁➕ ساخت پوشه جدید", callback_data="create_folder"))
    markup.add(types.InlineKeyboardButton("📁➕ ساخت زیرپوشه", callback_data="create_subfolder"))
    markup.add(types.InlineKeyboardButton("📂 لیست پوشه‌ها", callback_data="list_folders"))
    
    bot.send_message(message.chat.id, "📁 **مدیریت پوشه‌ها**\n\n"
                    "می‌توانید پوشه‌های خود را مدیریت کنید.\n"
                    "در هر پوشه می‌توانید فایل‌های پایتون قرار دهید.",
                    parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "create_folder")
def create_folder_prompt(call):
    msg = bot.send_message(call.message.chat.id, "📁 **نام پوشه جدید را وارد کنید:**\n(فقط حروف انگلیسی و عدد)")
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
        bot.reply_to(message, f"✅ {result}\n🆔 آیدی: `{folder_id}`", parse_mode='Markdown')
    else:
        bot.reply_to(message, f"❌ {result}")

@bot.callback_query_handler(func=lambda call: call.data == "create_subfolder")
def create_subfolder_prompt(call):
    user_id = call.from_user.id
    folders = db.execute('SELECT id, folder_name FROM folders WHERE user_id = ?', (user_id,))
    
    if not folders:
        bot.answer_callback_query(call.id, "ابتدا یک پوشه اصلی بسازید!", show_alert=True)
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for f in folders:
        markup.add(types.InlineKeyboardButton(f"📁 {f['folder_name']}", callback_data=f"select_parent_{f['id']}"))
    
    bot.edit_message_text("📁 **پوشه والد را انتخاب کنید:**", 
                         call.message.chat.id, call.message.message_id, reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('select_parent_'))
def select_parent(call):
    parent_id = call.data.replace('select_parent_', '')
    msg = bot.send_message(call.message.chat.id, "📁 **نام زیرپوشه را وارد کنید:**")
    bot.register_next_step_handler(msg, process_create_subfolder, parent_id)
    bot.answer_callback_query(call.id)

def process_create_subfolder(message, parent_id):
    user_id = message.from_user.id
    name = message.text.strip()
    
    if not re.match(r'^[a-zA-Z0-9_\-]+$', name):
        bot.reply_to(message, "❌ نام نامعتبر!")
        return
    
    folder_id, result = folder_manager.create_folder(user_id, name, parent_id)
    if folder_id:
        bot.reply_to(message, f"✅ {result}\n🆔 آیدی: `{folder_id}`", parse_mode='Markdown')
    else:
        bot.reply_to(message, f"❌ {result}")

@bot.callback_query_handler(func=lambda call: call.data == "list_folders")
def list_folders(call):
    user_id = call.from_user.id
    hierarchy = folder_manager.get_folder_hierarchy(user_id)
    
    if not hierarchy.get('root', []) and not any(hierarchy.values()):
        bot.send_message(call.message.chat.id, "📂 شما هیچ پوشه‌ای ندارید.")
        return
    
    def build_tree(parent_id='root', level=0):
        result = []
        indent = "  " * level
        for folder in hierarchy.get(parent_id, []):
            result.append(f"{indent}📂 {folder['folder_name']}")
            result.extend(build_tree(folder['id'], level + 1))
        return result
    
    tree_text = "\n".join(build_tree())
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    all_folders = db.execute('SELECT id, folder_name FROM folders WHERE user_id = ?', (user_id,))
    for f in all_folders:
        markup.add(types.InlineKeyboardButton(f"📂 {f['folder_name']}", callback_data=f"view_folder_{f['id']}"))
    
    bot.edit_message_text(f"📂 **ساختار پوشه‌های شما:**\n\n{tree_text}\n\nبرای مشاهده محتوا کلیک کنید:",
                         call.message.chat.id, call.message.message_id,
                         parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('view_folder_'))
def view_folder(call):
    folder_id = call.data.replace('view_folder_', '')
    folders = db.execute('SELECT * FROM folders WHERE id = ?', (folder_id,))
    
    if not folders:
        bot.answer_callback_query(call.id, "پوشه یافت نشد!")
        return
    
    folder = dict(folders[0])
    files = folder_manager.get_files(folder_id)
    
    text = f"📁 **{folder['folder_name']}**\n\n"
    text += f"🆔 آیدی: `{folder_id}`\n"
    text += f"📅 ساخته شده: {folder['created_at'][:16]}\n"
    text += f"📄 تعداد فایل‌ها: {len(files)}\n\n"
    
    if files:
        text += "**📄 فایل‌ها:**\n"
        for f in files:
            text += f"• `{f['name']}` ({f['size']} بایت)\n"
    else:
        text += "📂 هیچ فایلی در این پوشه وجود ندارد.\n"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("📄 افزودن فایل", callback_data=f"add_file_{folder_id}"))
    markup.add(types.InlineKeyboardButton("▶️ اجرا به عنوان ربات", callback_data=f"run_folder_{folder_id}"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="list_folders"))
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                         parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('add_file_'))
def add_file_prompt(call):
    folder_id = call.data.replace('add_file_', '')
    msg = bot.send_message(call.message.chat.id, "📄 **نام فایل:**\n(مثال: main.py)")
    bot.register_next_step_handler(msg, process_add_file_name, folder_id)
    bot.answer_callback_query(call.id)

def process_add_file_name(message, folder_id):
    file_name = message.text.strip()
    if not file_name.endswith('.py'):
        bot.reply_to(message, "❌ فقط فایل‌های .py مجاز!")
        return
    
    msg = bot.send_message(message.chat.id, f"📝 **محتوای {file_name} را ارسال کنید:**")
    bot.register_next_step_handler(msg, process_add_file_content, folder_id, file_name)

def process_add_file_content(message, folder_id, file_name):
    content = message.text
    success, result = folder_manager.add_file(folder_id, file_name, content)
    bot.reply_to(message, f"✅ {result}" if success else f"❌ {result}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('run_folder_'))
def run_folder(call):
    user_id = call.from_user.id
    folder_id = call.data.replace('run_folder_', '')
    user = get_user(user_id)
    
    if not user.get('subscription_active', 1):
        bot.answer_callback_query(call.id, "اشتراک شما فعال نیست!", show_alert=True)
        return
    
    code = folder_manager.read_file(folder_id, 'main.py')
    if not code:
        bot.answer_callback_query(call.id, "فایل main.py یافت نشد!", show_alert=True)
        return
    
    token = extract_token(code)
    if not token:
        bot.answer_callback_query(call.id, "توکن پیدا نشد!", show_alert=True)
        return
    
    valid, bot_info = verify_token(token)
    if not valid:
        bot.answer_callback_query(call.id, "توکن نامعتبر!", show_alert=True)
        return
    
    folders = db.execute('SELECT folder_path FROM folders WHERE id = ?', (folder_id,))
    folder_path = folders[0]['folder_path'] if folders else None
    
    # بررسی محدودیت تعداد ربات‌ها
    count = db.execute('SELECT COUNT(*) as c FROM bots WHERE user_id = ?', (user_id,))[0]['c']
    max_bots = db.get_setting('max_bots_per_user')
    
    if count >= max_bots:
        bot.answer_callback_query(call.id, f"حداکثر {max_bots} ربات!", show_alert=True)
        return
    
    # ایجاد ربات
    bot_id = hashlib.md5(f"{user_id}_{token}_{time.time()}".encode()).hexdigest()[:16]
    db.execute('''
        INSERT INTO bots (id, user_id, token, name, username, folder_path, created_at, last_active, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'stopped')
    ''', (bot_id, user_id, token, bot_info.get('first_name', 'ربات'), bot_info.get('username', ''), 
          folder_path, datetime.now().isoformat(), datetime.now().isoformat()))
    
    db.execute('UPDATE users SET bots_count = bots_count + 1 WHERE user_id = ?', (user_id,))
    
    # اجرا
    success, result = executor.start_bot(bot_id, user_id, code, folder_path)
    
    if success:
        bot.edit_message_text(
            f"✅ **ربات از پوشه با موفقیت اجرا شد!**\n\n"
            f"🤖 نام: `{bot_info.get('first_name', 'ربات')}`\n"
            f"🔗 آیدی: @{bot_info.get('username', '')}\n"
            f"✅ ربات شما همیشه فعال است!",
            call.message.chat.id, call.message.message_id, parse_mode='Markdown')
    else:
        bot.edit_message_text(f"❌ خطا: {result}", call.message.chat.id, call.message.message_id)
    
    bot.answer_callback_query(call.id, "✅ ربات اجرا شد!")

# ==================== اجرای ربات ====================
@bot.message_handler(func=lambda m: m.text == '▶️ اجرای ربات')
def run_prompt(message):
    user_id = message.from_user.id
    bots = db.execute('SELECT id, name, status FROM bots WHERE user_id = ?', (user_id,))
    
    if not bots:
        bot.send_message(message.chat.id, "📋 رباتی ندارید!\nاز `🤖 ساخت ربات جدید` استفاده کنید.", parse_mode='Markdown')
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        is_running = executor.is_running(b['id'])
        status_emoji = "🟢" if is_running else "🔴"
        markup.add(types.InlineKeyboardButton(f"{status_emoji} {b['name']}", callback_data=f"run_bot_{b['id']}"))
    
    bot.send_message(message.chat.id, "▶️ **انتخاب ربات برای اجرا:**\n(ربات‌ها همیشه فعال هستند)", 
                    parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('run_bot_'))
def run_bot(call):
    bot_id = call.data.replace('run_bot_', '')
    user_id = call.from_user.id
    
    if executor.is_running(bot_id):
        bot.answer_callback_query(call.id, "ربات در حال اجراست!", show_alert=True)
        return
    
    b = db.execute('SELECT * FROM bots WHERE id = ? AND user_id = ?', (bot_id, user_id))
    if not b:
        bot.answer_callback_query(call.id, "ربات یافت نشد!", show_alert=True)
        return
    
    b = dict(b[0])
    
    if b['folder_path'] and os.path.exists(os.path.join(b['folder_path'], 'main.py')):
        with open(os.path.join(b['folder_path'], 'main.py'), 'r', encoding='utf-8') as f:
            code = f.read()
        folder_path = b['folder_path']
    elif b['file_path'] and os.path.exists(b['file_path']):
        with open(b['file_path'], 'r', encoding='utf-8') as f:
            code = f.read()
        folder_path = None
    else:
        bot.answer_callback_query(call.id, "فایل ربات یافت نشد!", show_alert=True)
        return
    
    success, result = executor.start_bot(bot_id, user_id, code, folder_path)
    
    if success:
        bot.answer_callback_query(call.id, "✅ ربات اجرا شد!", show_alert=True)
    else:
        bot.answer_callback_query(call.id, f"❌ {result[:50]}", show_alert=True)
    
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== توقف ربات ====================
@bot.message_handler(func=lambda m: m.text == '🛑 توقف ربات')
def stop_prompt(message):
    user_id = message.from_user.id
    bots = db.execute('SELECT id, name FROM bots WHERE user_id = ?', (user_id,))
    
    if not bots:
        bot.send_message(message.chat.id, "📋 رباتی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        if executor.is_running(b['id']):
            markup.add(types.InlineKeyboardButton(f"🛑 {b['name']}", callback_data=f"stop_bot_{b['id']}"))
    
    if not markup.keyboard:
        bot.send_message(message.chat.id, "📋 هیچ ربات در حال اجرایی ندارید!")
        return
    
    bot.send_message(message.chat.id, "🛑 **ربات مورد نظر برای توقف:**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('stop_bot_'))
def stop_bot(call):
    bot_id = call.data.replace('stop_bot_', '')
    user_id = call.from_user.id
    
    executor.stop_bot(bot_id, user_id)
    bot.answer_callback_query(call.id, "✅ ربات متوقف شد!")
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== لیست ربات‌ها ====================
@bot.message_handler(func=lambda m: m.text == '📋 ربات‌های من')
def list_bots(message):
    user_id = message.from_user.id
    bots = db.execute('SELECT id, name, username, status, created_at FROM bots WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما هیچ رباتی ندارید!\nاز دکمه `🤖 ساخت ربات جدید` استفاده کنید.", parse_mode='Markdown')
        return
    
    text = "🤖 **لیست ربات‌های شما**\n\n"
    for b in bots:
        is_running = executor.is_running(b['id'])
        status_text = "🟢 فعال" if is_running else "🔴 متوقف"
        
        text += f"**{b['name']}**\n"
        text += f"🔗 t.me/{b['username']}\n"
        text += f"📊 وضعیت: {status_text}\n"
        text += f"📅 ساخته شده: {b['created_at'][:16]}\n\n"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== حذف ربات ====================
@bot.message_handler(func=lambda m: m.text == '🗑 حذف ربات')
def delete_prompt(message):
    user_id = message.from_user.id
    bots = db.execute('SELECT id, name FROM bots WHERE user_id = ?', (user_id,))
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما هیچ رباتی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        markup.add(types.InlineKeyboardButton(f"🗑 {b['name']}", callback_data=f"delete_bot_{b['id']}"))
    
    bot.send_message(message.chat.id, "🗑 **ربات مورد نظر برای حذف:**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_bot_'))
def confirm_delete(call):
    bot_id = call.data.replace('delete_bot_', '')
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ بله", callback_data=f"confirm_del_{bot_id}"),
              types.InlineKeyboardButton("❌ انصراف", callback_data="cancel_del"))
    bot.edit_message_text("⚠️ **آیا اطمینان دارید؟**", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_del_'))
def do_delete(call):
    bot_id = call.data.replace('confirm_del_', '')
    user_id = call.from_user.id
    
    executor.stop_bot(bot_id, user_id)
    db.execute('DELETE FROM bots WHERE id = ? AND user_id = ?', (bot_id, user_id))
    db.execute('UPDATE users SET bots_count = bots_count - 1 WHERE user_id = ?', (user_id,))
    
    bot.edit_message_text("✅ ربات حذف شد!", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "cancel_del")
def cancel_delete(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== وضعیت اجرا ====================
@bot.message_handler(func=lambda m: m.text == '⚡ وضعیت اجرا')
def exec_status(message):
    user_id = message.from_user.id
    bots = db.execute('SELECT id, name FROM bots WHERE user_id = ?', (user_id,))
    
    if not bots:
        bot.send_message(message.chat.id, "📋 رباتی ندارید!")
        return
    
    text = "⚡ **وضعیت ربات‌ها**\n\n"
    for b in bots:
        status = executor.get_status(b['id'])
        if status['running']:
            uptime = status['uptime']
            hours = uptime // 3600
            minutes = (uptime % 3600) // 60
            seconds = uptime % 60
            text += f"🟢 **{b['name']}** - فعال (آپ‌تایم: {hours:02d}:{minutes:02d}:{seconds:02d})\n"
        else:
            text += f"🔴 **{b['name']}** - متوقف\n"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== کیف پول ====================
@bot.message_handler(func=lambda m: m.text == '💰 کیف پول')
def wallet(message):
    user = get_user(message.from_user.id)
    text = f"💰 **کیف پول شما**\n\n"
    text += f"👤 {user['first_name']}\n"
    text += f"💵 موجودی: {user['wallet_balance']:,} تومان\n"
    text += f"👥 دعوت‌ها: {user['referrals_count']}\n"
    text += f"💰 کمیسیون: {db.get_setting('withdraw_percent')}%\n"
    text += f"💸 حداقل برداشت: {db.get_setting('min_withdraw'):,} تومان"
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== دعوت دوستان ====================
@bot.message_handler(func=lambda m: m.text == '👥 دعوت دوستان')
def invite(message):
    user = get_user(message.from_user.id)
    link = f"https://t.me/{BOT_USERNAME}?start={user['referral_code']}"
    text = f"👥 **دعوت دوستان**\n\n"
    text += f"🎁 کد: `{user['referral_code']}`\n"
    text += f"🔗 لینک: `{link}`\n"
    text += f"📊 دعوت‌ها: {user['referrals_count']}\n"
    text += f"💰 هر دعوت: {db.get_setting('withdraw_percent')}% کمیسیون"
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== درخواست برداشت ====================
@bot.message_handler(func=lambda m: m.text == '💸 درخواست برداشت')
def withdraw_request(message):
    user = get_user(message.from_user.id)
    min_w = db.get_setting('min_withdraw')
    
    if user['wallet_balance'] < min_w:
        bot.send_message(message.chat.id, f"❌ موجودی کمتر از حداقل برداشت ({min_w:,} تومان)")
        return
    
    msg = bot.send_message(message.chat.id, "💳 شماره کارت (۱۶ رقم):")
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
    db.execute('INSERT INTO withdraw_requests (user_id, amount, card_number, card_holder, created_at, status) VALUES (?, ?, ?, ?, ?, "pending")',
              (user['user_id'], user['wallet_balance'], card, holder, datetime.now().isoformat()))
    db.execute('UPDATE users SET wallet_balance = 0 WHERE user_id = ?', (user['user_id'],))
    
    bot.reply_to(message, f"✅ درخواست برداشت {user['wallet_balance']:,} تومان ثبت شد!")
    
    for admin_id in ADMIN_IDS:
        bot.send_message(admin_id, f"💰 درخواست برداشت\n👤 {user['first_name']}\n🆔 {user['user_id']}\n💰 {user['wallet_balance']:,} تومان")

# ==================== کتابخانه‌ها ====================
@bot.message_handler(func=lambda m: m.text == '📦 کتابخانه‌ها')
def libraries_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("📚 لیست کتابخانه‌ها", callback_data="lib_list"))
    markup.add(types.InlineKeyboardButton("🔧 نصب کتابخانه", callback_data="lib_install"))
    markup.add(types.InlineKeyboardButton("✅ نصب شده‌ها", callback_data="lib_installed"))
    
    bot.send_message(message.chat.id, "📦 **مدیریت کتابخانه‌ها**", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "lib_list")
def lib_list(call):
    libs = {
        'وب': {'Flask': 'flask', 'FastAPI': 'fastapi', 'Django': 'django'},
        'Async': {'aiohttp': 'aiohttp', 'httpx': 'httpx', 'aiogram': 'aiogram'},
        'دیتابیس': {'SQLAlchemy': 'sqlalchemy', 'asyncpg': 'asyncpg', 'redis': 'redis'},
        'ابزارها': {'requests': 'requests', 'beautifulsoup4': 'beautifulsoup4', 'numpy': 'numpy', 'pandas': 'pandas'}
    }
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for cat in libs.keys():
        markup.add(types.InlineKeyboardButton(f"📁 {cat}", callback_data=f"lib_cat_{cat}"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="lib_back"))
    
    bot.edit_message_text("📚 **دسته‌بندی کتابخانه‌ها:**", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lib_cat_'))
def lib_category(call):
    category = call.data.replace('lib_cat_', '')
    libs = {
        'وب': {'Flask': 'flask', 'FastAPI': 'fastapi', 'Django': 'django'},
        'Async': {'aiohttp': 'aiohttp', 'httpx': 'httpx', 'aiogram': 'aiogram'},
        'دیتابیس': {'SQLAlchemy': 'sqlalchemy', 'asyncpg': 'asyncpg', 'redis': 'redis'},
        'ابزارها': {'requests': 'requests', 'beautifulsoup4': 'beautifulsoup4', 'numpy': 'numpy', 'pandas': 'pandas'}
    }
    
    items = libs.get(category, {})
    markup = types.InlineKeyboardMarkup(row_width=2)
    for name, lib in items.items():
        markup.add(types.InlineKeyboardButton(f"📦 {name}", callback_data=f"install_lib_{lib}"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="lib_list"))
    
    bot.edit_message_text(f"📁 {category}:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('install_lib_'))
def install_lib(call):
    lib = call.data.replace('install_lib_', '')
    status_msg = bot.send_message(call.message.chat.id, f"🔄 در حال نصب {lib}...")
    install_library(lib, call.message.chat.id, status_msg.message_id, bot)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "lib_install")
def lib_install_custom(call):
    msg = bot.send_message(call.message.chat.id, "🔧 نام کتابخانه را وارد کنید:")
    bot.register_next_step_handler(msg, process_custom_install)
    bot.answer_callback_query(call.id)

def process_custom_install(message):
    lib = message.text.strip()
    status_msg = bot.reply_to(message, f"🔄 در حال نصب {lib}...")
    install_library(lib, message.chat.id, status_msg.message_id, bot)

@bot.callback_query_handler(func=lambda call: call.data == "lib_installed")
def lib_installed(call):
    libs = db.execute('SELECT * FROM installed_libraries ORDER BY installed_at DESC')
    
    if not libs:
        bot.edit_message_text("📦 هیچ کتابخانه‌ای نصب نشده است.", call.message.chat.id, call.message.message_id)
        return
    
    text = "✅ **کتابخانه‌های نصب شده**\n\n"
    for lib in libs:
        text += f"• `{lib['name']}` - {lib['version']}\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="lib_back"))
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "lib_back")
def lib_back(call):
    libraries_menu(call.message)

# ==================== راهنما ====================
@bot.message_handler(func=lambda m: m.text == '📚 راهنما')
def guide(message):
    text = """📚 **راهنمای جامع**

**🎯 ساخت ربات:**
1️⃣ از دکمه `🤖 ساخت ربات جدید` استفاده کنید
2️⃣ فایل .py یا .zip خود را ارسال کنید
3️⃣ پس از ساخت، ربات همیشه فعال است

**▶️ اجرای ربات:**
- ربات‌ها پس از ساخت خودکار اجرا می‌شوند
- برای توقف از `🛑 توقف ربات` استفاده کنید
- برای اجرای مجدد از `▶️ اجرای ربات` استفاده کنید

**📁 پوشه‌ها:**
- می‌توانید پوشه‌های تو در تو بسازید
- فایل اصلی باید main.py باشد

**📦 کتابخانه‌ها:**
- می‌توانید هر کتابخانه پایتونی نصب کنید

**💰 مالی:**
- هر دعوت ۷٪ کمیسیون
- حداقل برداشت ۲ میلیون تومان

**🆘 پشتیبانی: @shahraghee13"""
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== آمار ====================
@bot.message_handler(func=lambda m: m.text == '📊 آمار')
def stats(message):
    users = db.execute('SELECT COUNT(*) as c FROM users')[0]['c']
    active = db.execute('SELECT COUNT(*) as c FROM users WHERE subscription_active = 1')[0]['c']
    bots = db.execute('SELECT COUNT(*) as c FROM bots')[0]['c']
    running = sum(1 for b in db.execute('SELECT id FROM bots') if executor.is_running(b['id']))
    total_wallet = db.execute('SELECT SUM(wallet_balance) as t FROM users')[0]['t'] or 0
    
    text = f"📊 **آمار سیستم**\n\n"
    text += f"👥 کاربران: {users}\n"
    text += f"✅ اشتراک فعال: {active}\n"
    text += f"🤖 ربات‌ها: {bots}\n"
    text += f"🟢 در حال اجرا: {running}\n"
    text += f"💰 موجودی کل: {total_wallet:,} تومان\n"
    text += f"📌 حداکثر ربات: {db.get_setting('max_bots_per_user')}\n"
    text += f"✅ ربات‌ها همیشه فعال هستند"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== پشتیبانی ====================
@bot.message_handler(func=lambda m: m.text == '📞 پشتیبانی')
def support(message):
    bot.send_message(message.chat.id, "📞 **پشتیبانی:** @shahraghee13\n\nسوالات خود را بپرسید.", parse_mode='Markdown')

# ==================== پنل مدیریت ====================
@bot.message_handler(func=lambda m: m.text == '👑 مدیریت')
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📸 تایید فیش", callback_data="admin_receipts"),
        types.InlineKeyboardButton("💰 تایید برداشت", callback_data="admin_withdraws"),
        types.InlineKeyboardButton("👥 کاربران", callback_data="admin_users"),
        types.InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings"),
    )
    
    bot.send_message(message.chat.id, "👑 **پنل مدیریت**", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_receipts")
def admin_receipts(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    receipts = db.execute('SELECT * FROM receipts WHERE status = "pending" ORDER BY created_at')
    
    if not receipts:
        bot.send_message(call.message.chat.id, "📸 فیشی وجود ندارد.")
        return
    
    for r in receipts:
        r = dict(r)
        user = get_user(r['user_id'])
        text = f"📸 فیش\n👤 {user['first_name'] if user else 'نامشخص'}\n💰 {r['amount']:,} تومان\n🆔 {r['payment_code']}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_receipt_{r['id']}"),
                  types.InlineKeyboardButton("❌ رد", callback_data=f"reject_receipt_{r['id']}"))
        
        if os.path.exists(r['receipt_path']):
            with open(r['receipt_path'], 'rb') as f:
                bot.send_photo(call.message.chat.id, f, caption=text, reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, text, reply_markup=markup)
    
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_receipt_'))
def reject_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    rid = int(call.data.replace('reject_receipt_', ''))
    db.execute('UPDATE receipts SET status = "rejected" WHERE id = ?', (rid,))
    bot.answer_callback_query(call.id, "❌ رد شد!")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_withdraws")
def admin_withdraws(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    withdraws = db.execute('SELECT * FROM withdraw_requests WHERE status = "pending"')
    
    if not withdraws:
        bot.send_message(call.message.chat.id, "💰 درخواستی وجود ندارد.")
        return
    
    for w in withdraws:
        w = dict(w)
        user = get_user(w['user_id'])
        text = f"💰 برداشت\n👤 {user['first_name']}\n💰 {w['amount']:,} تومان\n💳 {w['card_number']}"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_wd_{w['id']}"))
        bot.send_message(call.message.chat.id, text, reply_markup=markup)
    
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_wd_'))
def approve_withdraw(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    wid = int(call.data.replace('approve_wd_', ''))
    db.execute('UPDATE withdraw_requests SET status = "approved" WHERE id = ?', (wid,))
    bot.answer_callback_query(call.id, "✅ تایید شد!")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_users")
def admin_users(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🔍 جستجو", callback_data="admin_search"),
        types.InlineKeyboardButton("💰 افزایش موجودی", callback_data="admin_add_balance"),
        types.InlineKeyboardButton("🎁 فعال‌سازی اشتراک", callback_data="admin_activate"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    bot.edit_message_text("👥 مدیریت کاربران:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_search")
def admin_search(call):
    msg = bot.send_message(call.message.chat.id, "🔍 آیدی کاربر:")
    bot.register_next_step_handler(msg, process_admin_search)
    bot.answer_callback_query(call.id)

def process_admin_search(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        uid = int(message.text.strip())
        user = get_user(uid)
        if user:
            bots = db.execute('SELECT COUNT(*) as c FROM bots WHERE user_id = ?', (uid,))[0]['c']
            text = f"👤 {user['first_name']}\n🆔 {uid}\n💰 {user['wallet_balance']:,} تومان\n✅ اشتراک: {'فعال' if user['subscription_active'] else 'غیرفعال'}\n🤖 ربات: {bots}"
            bot.reply_to(message, text)
        else:
            bot.reply_to(message, "❌ یافت نشد!")
    except:
        bot.reply_to(message, "❌ نامعتبر!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_add_balance")
def admin_add_balance(call):
    msg = bot.send_message(call.message.chat.id, "💰 آیدی و مبلغ (مثال: 123456 100000):")
    bot.register_next_step_handler(msg, process_add_balance)
    bot.answer_callback_query(call.id)

def process_add_balance(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        parts = message.text.strip().split()
        uid = int(parts[0])
        amount = int(parts[1])
        user = get_user(uid)
        if user:
            new_balance = user['wallet_balance'] + amount
            db.execute('UPDATE users SET wallet_balance = ? WHERE user_id = ?', (new_balance, uid))
            bot.reply_to(message, f"✅ {amount:,} تومان اضافه شد!")
            bot.send_message(uid, f"💰 {amount:,} تومان به کیف پول شما اضافه شد!")
        else:
            bot.reply_to(message, "❌ کاربر یافت نشد!")
    except:
        bot.reply_to(message, "❌ فرمت نامعتبر!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_activate")
def admin_activate(call):
    msg = bot.send_message(call.message.chat.id, "🎁 آیدی کاربر:")
    bot.register_next_step_handler(msg, process_admin_activate)
    bot.answer_callback_query(call.id)

def process_admin_activate(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        uid = int(message.text.strip())
        db.execute('UPDATE users SET subscription_active = 1 WHERE user_id = ?', (uid,))
        bot.reply_to(message, f"✅ اشتراک {uid} فعال شد!")
        bot.send_message(uid, "✅ اشتراک شما توسط ادمین فعال شد!\nربات‌های شما همیشه فعال خواهند بود.")
    except:
        bot.reply_to(message, "❌ خطا!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_settings")
def admin_settings(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📌 حداکثر ربات", callback_data="set_max_bots"),
        types.InlineKeyboardButton("💰 قیمت اشتراک", callback_data="set_price"),
        types.InlineKeyboardButton("💳 کارت", callback_data="set_card"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    text = f"⚙️ تنظیمات:\n📌 حداکثر ربات: {db.get_setting('max_bots_per_user')}\n💰 قیمت: {db.get_setting('subscription_price_str')}"
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "set_max_bots")
def set_max_bots(call):
    msg = bot.send_message(call.message.chat.id, "📌 حداکثر ربات (1-10):")
    bot.register_next_step_handler(msg, process_set_max_bots)
    bot.answer_callback_query(call.id)

def process_set_max_bots(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        val = int(message.text.strip())
        if 1 <= val <= 10:
            db.update_setting('max_bots_per_user', val)
            bot.reply_to(message, f"✅ حداکثر {val} ربات شد!")
        else:
            bot.reply_to(message, "❌ بین 1 تا 10")
    except:
        bot.reply_to(message, "❌ عدد معتبر")

@bot.callback_query_handler(func=lambda call: call.data == "set_price")
def set_price(call):
    msg = bot.send_message(call.message.chat.id, "💰 قیمت جدید (تومان):")
    bot.register_next_step_handler(msg, process_set_price)
    bot.answer_callback_query(call.id)

def process_set_price(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        price = int(message.text.strip())
        db.update_setting('subscription_price', price)
        db.update_setting('subscription_price_str', f"{price:,} تومان")
        bot.reply_to(message, f"✅ قیمت {price:,} تومان شد!")
    except:
        bot.reply_to(message, "❌ عدد معتبر")

@bot.callback_query_handler(func=lambda call: call.data == "set_card")
def set_card(call):
    msg = bot.send_message(call.message.chat.id, "💳 شماره کارت ۱۶ رقم:")
    bot.register_next_step_handler(msg, process_set_card)
    bot.answer_callback_query(call.id)

def process_set_card(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    card = message.text.strip().replace(' ', '')
    if len(card) == 16 and card.isdigit():
        db.update_setting('card_number', card)
        display = ' '.join([card[i:i+4] for i in range(0, 16, 4)])
        db.update_setting('card_number_display', display)
        bot.reply_to(message, f"✅ {display}")
    else:
        bot.reply_to(message, "❌ ۱۶ رقم")

@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    admin_panel(call.message)

# ==================== پیام همگانی ====================
@bot.message_handler(func=lambda m: m.text == '📢 پیام همگانی')
def broadcast_prompt(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(message.chat.id, "📢 متن پیام:")
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    text = message.text
    users = db.execute('SELECT user_id FROM users')
    sent = 0
    
    status_msg = bot.reply_to(message, f"🔄 در حال ارسال به {len(users)} کاربر...")
    
    for user in users:
        try:
            bot.send_message(user['user_id'], f"📢 **پیام همگانی**\n\n{text}", parse_mode='Markdown')
            sent += 1
            time.sleep(0.05)
        except:
            pass
    
    bot.edit_message_text(f"✅ به {sent} کاربر ارسال شد!", message.chat.id, status_msg.message_id)

# ==================== اجرای اصلی ====================
if __name__ == "__main__":
    print("=" * 60)
    print("🚀 ربات مادر - نسخه پایدار نهایی")
    print("=" * 60)
    print(f"👑 ادمین‌ها: {ADMIN_IDS}")
    print(f"🤖 @{BOT_USERNAME}")
    print(f"💰 قیمت: {db.get_setting('subscription_price_str')}")
    print(f"📌 حداکثر ربات: {db.get_setting('max_bots_per_user')}")
    print(f"✅ ربات‌ها همیشه فعال هستند!")
    print("=" * 60)
    print("🔥 ربات با موفقیت راه‌اندازی شد!")
    print("=" * 60)
    
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=60)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)