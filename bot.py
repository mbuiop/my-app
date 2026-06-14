#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ربات مادر نهایی نسخه 12.0 - اجرا روی سرور مادر در صورت نبود سرور دیگه
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
import requests
import signal
import secrets
import logging
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
import paramiko

# ==================== تنظیمات پایه ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "database")
FILES_DIR = os.path.join(BASE_DIR, "user_files")
RUNNING_DIR = os.path.join(BASE_DIR, "running_bots")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
RECEIPTS_DIR = os.path.join(BASE_DIR, "receipts")
PENDING_FILES_DIR = os.path.join(BASE_DIR, "pending_files")
SERVERS_DIR = os.path.join(BASE_DIR, "servers")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")

for dir_path in [DB_DIR, FILES_DIR, RUNNING_DIR, LOGS_DIR, RECEIPTS_DIR, PENDING_FILES_DIR, SERVERS_DIR, BACKUP_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# ==================== توکن ربات مادر ====================
BOT_TOKEN = "7685135237:AAEmsHktRw9cEqrHTkCoPZk-fBimK7TDjOo"
bot = telebot.TeleBot(BOT_TOKEN, num_threads=100)
bot.delete_webhook()

# ==================== آیدی ادمین ====================
ADMIN_IDS = [327855654]

# ==================== تنظیمات ====================
class Config:
    def __init__(self):
        self.price = 2000000
        self.card_number = "5892101187322777"
        self.card_holder = "مرتضی نیکخو خنجری"
        self.subscription_days = 30
    
    def load_from_db(self):
        try:
            with get_db() as conn:
                config_data = conn.execute("SELECT key, value FROM config").fetchall()
                for row in config_data:
                    if row['key'] == 'price':
                        self.price = int(row['value'])
                    elif row['key'] == 'card_number':
                        self.card_number = row['value']
                    elif row['key'] == 'card_holder':
                        self.card_holder = row['value']
                    elif row['key'] == 'subscription_days':
                        self.subscription_days = int(row['value'])
        except:
            pass
    
    def save_to_db(self):
        with get_db() as conn:
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('price', str(self.price)))
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('card_number', self.card_number))
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('card_holder', self.card_holder))
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('subscription_days', str(self.subscription_days)))
            conn.commit()

config = Config()

# ==================== لاگینگ ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[RotatingFileHandler(os.path.join(LOGS_DIR, 'mother_bot.log'), maxBytes=10485760, backupCount=30)]
)

# ==================== دیتابیس ====================
DB_PATH = os.path.join(DB_DIR, 'mother_bot.db')

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=120, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA cache_size=-262144")
    try:
        yield conn
        conn.commit()
    except:
        conn.rollback()
        raise
    finally:
        conn.close()

# ایجاد جداول
with get_db() as conn:
    conn.execute('CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            referral_code TEXT UNIQUE,
            referred_by INTEGER,
            balance INTEGER DEFAULT 0,
            total_earned INTEGER DEFAULT 0,
            active_subscription INTEGER DEFAULT 0,
            subscription_expire TIMESTAMP,
            subscription_id INTEGER,
            total_bots INTEGER DEFAULT 0,
            created_at TIMESTAMP
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            subscription_code TEXT UNIQUE,
            status TEXT DEFAULT 'pending',
            amount INTEGER,
            created_at TIMESTAMP,
            paid_at TIMESTAMP,
            expires_at TIMESTAMP
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS pending_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            subscription_id INTEGER,
            file_path TEXT,
            file_name TEXT,
            file_hash TEXT,
            status TEXT DEFAULT 'pending',
            submitted_at TIMESTAMP,
            reviewed_at TIMESTAMP
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS servers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            ip TEXT,
            port INTEGER,
            username TEXT,
            password TEXT,
            status TEXT DEFAULT 'active',
            current_load INTEGER DEFAULT 0,
            max_load INTEGER DEFAULT 10,
            created_at TIMESTAMP
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS bots (
            id TEXT PRIMARY KEY,
            user_id INTEGER,
            subscription_id INTEGER,
            server_id INTEGER,
            token TEXT,
            name TEXT,
            username TEXT,
            file_path TEXT,
            pid INTEGER,
            status TEXT DEFAULT 'stopped',
            created_at TIMESTAMP,
            expires_at TIMESTAMP
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            subscription_id INTEGER,
            amount INTEGER,
            receipt_path TEXT,
            status TEXT DEFAULT 'pending',
            payment_code TEXT UNIQUE,
            created_at TIMESTAMP
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS withdraw_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            card_number TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP
        )
    ''')
    
    conn.commit()

config.load_from_db()

# ==================== توابع دیتابیس ====================

def generate_referral_code(user_id):
    return hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:10].upper()

def create_user(user_id, username, first_name, last_name, referred_by=None):
    try:
        with get_db() as conn:
            now = datetime.now().isoformat()
            referral_code = generate_referral_code(user_id)
            
            existing = conn.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,)).fetchone()
            if existing:
                return True
            
            conn.execute('''
                INSERT INTO users (user_id, username, first_name, last_name, referral_code, referred_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name, referral_code, referred_by, now))
            conn.commit()
            
            if referred_by:
                conn.execute('UPDATE users SET balance = balance + 50000 WHERE user_id = ?', (referred_by,))
                conn.commit()
            return True
    except:
        return False

def get_user(user_id):
    try:
        with get_db() as conn:
            user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
            return dict(user) if user else None
    except:
        return None

def has_active_subscription(user_id):
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

def get_subscription_days_left(user_id):
    try:
        with get_db() as conn:
            user = conn.execute('SELECT subscription_expire FROM users WHERE user_id = ?', (user_id,)).fetchone()
            if user and user['subscription_expire']:
                expire = datetime.fromisoformat(user['subscription_expire'])
                return max(0, (expire - datetime.now()).days)
            return 0
    except:
        return 0

def create_subscription(user_id, amount):
    try:
        with get_db() as conn:
            subscription_code = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:16].upper()
            now = datetime.now().isoformat()
            expires_at = (datetime.now() + timedelta(days=config.subscription_days)).isoformat()
            
            conn.execute('''
                INSERT INTO subscriptions (user_id, subscription_code, amount, created_at, expires_at, status)
                VALUES (?, ?, ?, ?, ?, 'pending')
            ''', (user_id, subscription_code, amount, now, expires_at))
            conn.commit()
            
            sub_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            return sub_id, subscription_code
    except:
        return None, None

def activate_subscription(subscription_id, user_id, amount):
    try:
        with get_db() as conn:
            expires_at = (datetime.now() + timedelta(days=config.subscription_days)).isoformat()
            
            conn.execute('UPDATE users SET active_subscription = 0 WHERE user_id = ?', (user_id,))
            conn.execute('''
                UPDATE users SET active_subscription = 1, subscription_expire = ?, subscription_id = ?
                WHERE user_id = ?
            ''', (expires_at, subscription_id, user_id))
            
            conn.execute('UPDATE subscriptions SET status = "active", paid_at = ? WHERE id = ?',
                        (datetime.now().isoformat(), subscription_id))
            
            # پاداش رفرال
            user = conn.execute('SELECT referred_by FROM users WHERE user_id = ?', (user_id,)).fetchone()
            if user and user['referred_by']:
                bonus = int(amount * 0.1)
                conn.execute('UPDATE users SET balance = balance + ?, total_earned = total_earned + ? WHERE user_id = ?',
                            (bonus, bonus, user['referred_by']))
            
            conn.commit()
            return True
    except:
        return False

def get_user_balance(user_id):
    try:
        with get_db() as conn:
            user = conn.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,)).fetchone()
            return user['balance'] if user else 0
    except:
        return 0

def can_create_bot(user_id):
    try:
        with get_db() as conn:
            bots_count = conn.execute('SELECT COUNT(*) FROM bots WHERE user_id = ?', (user_id,)).fetchone()[0]
            return has_active_subscription(user_id) and bots_count == 0
    except:
        return False

def add_bot(user_id, subscription_id, server_id, bot_id, token, name, username, file_path, pid=None):
    try:
        with get_db() as conn:
            now = datetime.now().isoformat()
            expires_at = (datetime.now() + timedelta(days=config.subscription_days)).isoformat()
            
            conn.execute('''
                INSERT INTO bots (id, user_id, subscription_id, server_id, token, name, username, file_path, pid, status, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'running', ?, ?)
            ''', (bot_id, user_id, subscription_id, server_id, token, name, username, file_path, pid, now, expires_at))
            
            conn.execute('UPDATE users SET total_bots = total_bots + 1, active_subscription = 0 WHERE user_id = ?', (user_id,))
            conn.commit()
            return True
    except:
        return False

def get_user_bots(user_id):
    try:
        with get_db() as conn:
            bots = conn.execute('SELECT * FROM bots WHERE user_id = ? ORDER BY created_at DESC', (user_id,)).fetchall()
            return [dict(bot) for bot in bots]
    except:
        return []

def delete_bot(bot_id, user_id):
    try:
        with get_db() as conn:
            bot = conn.execute('SELECT * FROM bots WHERE id = ? AND user_id = ?', (bot_id, user_id)).fetchone()
            if bot:
                if bot['server_id']:
                    server = conn.execute('SELECT * FROM servers WHERE id = ?', (bot['server_id'],)).fetchone()
                    if server:
                        stop_bot_on_server(dict(server), bot_id)
                conn.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
                conn.commit()
                return True
            return False
    except:
        return False

def save_pending_file(user_id, subscription_id, file_path, file_name, file_hash):
    try:
        with get_db() as conn:
            now = datetime.now().isoformat()
            conn.execute('''
                INSERT INTO pending_files (user_id, subscription_id, file_path, file_name, file_hash, submitted_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, subscription_id, file_path, file_name, file_hash, now))
            conn.commit()
            return True
    except:
        return False

def get_pending_files():
    try:
        with get_db() as conn:
            files = conn.execute('SELECT * FROM pending_files WHERE status = "pending" ORDER BY submitted_at DESC').fetchall()
            return [dict(f) for f in files]
    except:
        return []

def get_pending_file_by_id(file_id):
    try:
        with get_db() as conn:
            file = conn.execute('SELECT * FROM pending_files WHERE id = ?', (file_id,)).fetchone()
            return dict(file) if file else None
    except:
        return None

def update_pending_file_status(file_id, status):
    try:
        with get_db() as conn:
            conn.execute('UPDATE pending_files SET status = ?, reviewed_at = ? WHERE id = ?',
                        (status, datetime.now().isoformat(), file_id))
            conn.commit()
            return True
    except:
        return False

# ==================== سیستم مدیریت سرور و اجرا ====================

def get_available_servers():
    """دریافت سرورهای فعال با بار کمتر"""
    with get_db() as conn:
        servers = conn.execute('''
            SELECT * FROM servers 
            WHERE status = 'active' AND current_load < max_load
            ORDER BY current_load ASC
        ''').fetchall()
        return [dict(s) for s in servers]

def get_best_server():
    """بهترین سرور (کمترین بار) یا None اگر سروری نباشد"""
    servers = get_available_servers()
    return servers[0] if servers else None

def test_server_connection(ip, port, username, password):
    """تست اتصال به سرور"""
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip, port=port, username=username, password=password, timeout=10)
        client.close()
        return True
    except:
        return False

def add_new_server(name, ip, port, username, password):
    """اضافه کردن سرور جدید"""
    try:
        if not test_server_connection(ip, port, username, password):
            return False, "❌ اتصال به سرور امکان‌پذیر نیست"
        
        with get_db() as conn:
            now = datetime.now().isoformat()
            conn.execute('''
                INSERT INTO servers (name, ip, port, username, password, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, ip, port, username, password, now))
            conn.commit()
            return True, f"✅ سرور {name} اضافه شد"
    except Exception as e:
        return False, f"❌ خطا: {str(e)}"

def run_bot_on_server(server, bot_id, code, token):
    """اجرای ربات روی سرور مشخص"""
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(server['ip'], port=server['port'], username=server['username'], password=server['password'], timeout=30)
        
        bot_dir = f"/home/ubuntu/bots/{bot_id}"
        client.exec_command(f'mkdir -p {bot_dir}')
        
        sftp = client.open_sftp()
        remote_path = f"{bot_dir}/bot.py"
        with sftp.open(remote_path, 'w') as f:
            f.write(code)
        sftp.close()
        
        # نصب کتابخانه‌های مورد نیاز
        libs = detect_requirements(code)
        for lib in libs[:10]:
            client.exec_command(f'pip3 install {lib} --quiet')
        
        # اجرا با screen
        client.exec_command(f'screen -dmS bot_{bot_id} python3 {remote_path}')
        time.sleep(2)
        
        stdin, stdout, stderr = client.exec_command(f'pgrep -f "screen -dmS bot_{bot_id}"')
        pid = stdout.read().decode().strip()
        
        client.close()
        
        with get_db() as conn:
            conn.execute('UPDATE servers SET current_load = current_load + 1 WHERE id = ?', (server['id'],))
            conn.commit()
        
        return pid, None
    except Exception as e:
        return None, str(e)

def run_bot_on_mother_server(bot_id, code, token):
    """اجرای ربات روی خود سرور مادر (وقتی سرور دیگه‌ای نباشه)"""
    try:
        bot_dir = os.path.join(RUNNING_DIR, bot_id)
        os.makedirs(bot_dir, exist_ok=True)
        
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
                error = f.read()[-200:]
            return None, error
    except Exception as e:
        return None, str(e)

def stop_bot_on_server(server, bot_id):
    """توقف ربات روی سرور"""
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(server['ip'], port=server['port'], username=server['username'], password=server['password'], timeout=30)
        client.exec_command(f'screen -S bot_{bot_id} -X quit')
        client.close()
        
        with get_db() as conn:
            conn.execute('UPDATE servers SET current_load = current_load - 1 WHERE id = ?', (server['id'],))
            conn.commit()
        return True
    except:
        return False

def stop_bot_on_mother(bot_id):
    """توقف ربات روی سرور مادر"""
    try:
        with get_db() as conn:
            bot = conn.execute('SELECT pid FROM bots WHERE id = ?', (bot_id,)).fetchone()
            if bot and bot['pid']:
                os.kill(bot['pid'], signal.SIGTERM)
                return True
        return False
    except:
        return False

def detect_requirements(code):
    """تشخیص کتابخانه‌های مورد نیاز از کد"""
    imports = set()
    lines = code.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('import '):
            parts = line.split()
            if len(parts) > 1:
                lib = parts[1].split('.')[0]
                if lib not in ['os', 'sys', 'time', 'datetime', 'json', 're']:
                    imports.add(lib)
        elif line.startswith('from '):
            parts = line.split()
            if len(parts) > 1:
                lib = parts[1].split('.')[0]
                if lib not in ['os', 'sys', 'time', 'datetime', 'json', 're']:
                    imports.add(lib)
    return list(imports)

def extract_token(code):
    """استخراج توکن از کد"""
    patterns = [
        r'[0-9]{8,10}:[A-Za-z0-9_-]{35}',
        r'token\s*=\s*["\']([^"\']+)["\']',
        r'TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'BOT_TOKEN\s*=\s*["\']([^"\']+)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, code, re.IGNORECASE)
        if match:
            token = match.group(1) if match.lastindex else match.group(0)
            return token
    return None

def build_bot_from_pending(file_id):
    """ساخت ربات از فایل تایید شده"""
    result = {'success': False, 'error': None, 'name': None, 'username': None, 'bot_id': None}
    
    pending = get_pending_file_by_id(file_id)
    if not pending:
        result['error'] = "فایل پیدا نشد"
        return result
    
    with open(pending['file_path'], 'r', encoding='utf-8') as f:
        code = f.read()
    
    token = extract_token(code)
    if not token:
        result['error'] = "توکن پیدا نشد"
        return result
    
    # بررسی توکن
    try:
        response = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
        if response.status_code != 200:
            result['error'] = "توکن نامعتبر"
            return result
        bot_info = response.json()['result']
        bot_name = bot_info['first_name']
        bot_username = bot_info['username']
    except:
        result['error'] = "خطا در بررسی توکن"
        return result
    
    bot_id = hashlib.md5(f"{pending['user_id']}_{token}_{time.time()}".encode()).hexdigest()[:12]
    
    # اول سعی کن روی سرورهای دیگه اجرا کن
    server = get_best_server()
    
    if server:
        pid, error = run_bot_on_server(server, bot_id, code, token)
        server_id = server['id']
    else:
        # اگر سروری نبود، روی خود مادر اجرا کن
        pid, error = run_bot_on_mother_server(bot_id, code, token)
        server_id = 0  # 0 یعنی سرور مادر
    
    if pid:
        add_bot(pending['user_id'], pending['subscription_id'], server_id, bot_id, token, bot_name, bot_username, pending['file_path'], pid)
        update_pending_file_status(file_id, 'approved')
        
        result['success'] = True
        result['name'] = bot_name
        result['username'] = bot_username
        result['bot_id'] = bot_id
        
        # پیام موفقیت به کاربر (فقط یک پیام)
        try:
            bot.send_message(
                pending['user_id'],
                f"✅ ربات شما ساخته شد!\n\n🤖 {bot_name}\n🔗 https://t.me/{bot_username}"
            )
        except:
            pass
    else:
        result['error'] = error or "خطا در اجرا"
    
    return result

# ==================== منوها ====================

def get_main_menu(user_id):
    days_left = get_subscription_days_left(user_id)
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        types.KeyboardButton('🛒 خرید اشتراک'),
        types.KeyboardButton('📤 ارسال فایل ربات'),
        types.KeyboardButton('🤖 ربات‌های من'),
        types.KeyboardButton('💰 کیف پول'),
        types.KeyboardButton('📚 راهنما'),
        types.KeyboardButton('📞 پشتیبانی')
    ]
    if days_left > 0:
        buttons.insert(0, types.KeyboardButton(f'📅 {days_left} روز مونده'))
    if user_id in ADMIN_IDS:
        buttons.append(types.KeyboardButton('👑 پنل ادمین'))
    markup.add(*buttons)
    return markup

# ==================== هندلرها ====================

@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    
    referred_by = None
    args = message.text.split()
    if len(args) > 1:
        with get_db() as conn:
            referrer = conn.execute('SELECT user_id FROM users WHERE referral_code = ?', (args[1],)).fetchone()
            if referrer:
                referred_by = referrer['user_id']
    
    create_user(user_id, username, first_name, last_name, referred_by)
    
    bot_username = bot.get_me().username
    user = get_user(user_id)
    referral_link = f"https://t.me/{bot_username}?start={user['referral_code']}" if user else ""
    
    text = f"🚀 به ربات سازنده ربات خوش آمدید!\n\n🎁 لینک رفرال شما:\n{referral_link}"
    bot.send_message(message.chat.id, text, reply_markup=get_main_menu(user_id))

@bot.message_handler(func=lambda m: m.text == '🛒 خرید اشتراک')
def buy_subscription(message):
    user_id = message.from_user.id
    
    if has_active_subscription(user_id):
        bot.send_message(message.chat.id, f"✅ اشتراک فعال دارید! {get_subscription_days_left(user_id)} روز مونده.")
        return
    
    sub_id, sub_code = create_subscription(user_id, config.price)
    if not sub_id:
        bot.send_message(message.chat.id, "❌ خطا")
        return
    
    text = f"""💰 خرید اشتراک

مبلغ: {config.price:,} تومان
کارت: {config.card_number}
به نام: {config.card_holder}

🆔 کد: `{sub_code}`

پس از واریز، تصویر فیش را ارسال کنید."""
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    
    with get_db() as conn:
        pending_sub = conn.execute('''
            SELECT * FROM subscriptions WHERE user_id = ? AND status = 'pending' ORDER BY created_at DESC LIMIT 1
        ''', (user_id,)).fetchone()
    
    if not pending_sub:
        bot.reply_to(message, "❌ اشتراک در انتظاری ندارید.")
        return
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        payment_code = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:12].upper()
        receipt_path = os.path.join(RECEIPTS_DIR, f"{user_id}_{payment_code}.jpg")
        
        with open(receipt_path, 'wb') as f:
            f.write(downloaded_file)
        
        with get_db() as conn:
            conn.execute('''
                INSERT INTO receipts (user_id, subscription_id, amount, receipt_path, payment_code, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, pending_sub['id'], config.price, receipt_path, payment_code, datetime.now().isoformat()))
            conn.commit()
        
        # فقط همین یک پیام به کاربر
        bot.reply_to(message, f"✅ فیش شما با موفقیت ارسال شد.\n🆔 کد پیگیری: {payment_code}\n⏳ پس از تایید، اشتراک شما فعال می‌شود.")
        
        # اطلاع به ادمین (فقط یک پیام)
        for admin_id in ADMIN_IDS:
            try:
                bot.send_photo(admin_id, open(receipt_path, 'rb'), caption=f"📸 فیش جدید\n👤 {user_id}\n💰 {config.price:,} تومان\n🆔 {payment_code}")
            except:
                pass
    except Exception as e:
        bot.reply_to(message, f"❌ خطا")

@bot.message_handler(func=lambda m: m.text == '📤 ارسال فایل ربات')
def send_bot_file(message):
    user_id = message.from_user.id
    
    if not has_active_subscription(user_id):
        bot.send_message(message.chat.id, f"❌ اشتراک فعال ندارید!\n💰 {config.price:,} تومان\nاز منوی خرید اشتراک استفاده کنید.")
        return
    
    if not can_create_bot(user_id):
        bot.send_message(message.chat.id, "❌ قبلاً با این اشتراک ربات ساخته‌اید!")
        return
    
    bot.send_message(message.chat.id, "📤 فایل `.py` خود را ارسال کنید.\n\n✅ پس از تایید ادمین، ربات ساخته می‌شود.")

@bot.message_handler(content_types=['document'])
def handle_bot_file(message):
    user_id = message.from_user.id
    
    if not has_active_subscription(user_id):
        bot.reply_to(message, "❌ اشتراک فعال ندارید!")
        return
    
    if not can_create_bot(user_id):
        bot.reply_to(message, "❌ قبلاً ربات ساخته‌اید!")
        return
    
    file_name = message.document.file_name
    if not file_name.endswith('.py'):
        bot.reply_to(message, "❌ فقط فایل `.py` مجاز است!")
        return
    
    if message.document.file_size > 10 * 1024 * 1024:
        bot.reply_to(message, "❌ حجم بیشتر از ۱۰ مگابایت!")
        return
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        file_path = os.path.join(PENDING_FILES_DIR, str(user_id), f"{int(time.time())}_{file_name}")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'wb') as f:
            f.write(downloaded_file)
        
        file_hash = hashlib.sha256(open(file_path, 'rb').read()).hexdigest()
        
        with get_db() as conn:
            sub = conn.execute('SELECT id FROM subscriptions WHERE user_id = ? AND status = "active" ORDER BY paid_at DESC LIMIT 1', (user_id,)).fetchone()
            if not sub:
                bot.reply_to(message, "❌ اشتراک فعال پیدا نشد!")
                return
            subscription_id = sub['id']
        
        save_pending_file(user_id, subscription_id, file_path, file_name, file_hash)
        
        # فقط همین یک پیام به کاربر
        bot.reply_to(message, f"✅ فایل {file_name} دریافت شد.\n⏳ در لیست انتظار بررسی قرار گرفت.")
        
        # هیچ پیامی به پنل ادمین نمی‌ره، فقط توی لیست فایل‌ها نمایش داده می‌شه
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطا")

@bot.message_handler(func=lambda m: m.text == '🤖 ربات‌های من')
def my_bots(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    
    if not bots:
        bot.send_message(message.chat.id, "📋 رباتی ندارید!")
        return
    
    for b in bots:
        text = f"🤖 {b['name']}\n🔗 https://t.me/{b['username']}\n🆔 `{b['id']}`\n📅 {b['created_at'][:10]}"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🗑 حذف", callback_data=f"delete_{b['id']}"))
        bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
def delete_bot_cmd(call):
    bot_id = call.data.replace('delete_', '')
    user_id = call.from_user.id
    if delete_bot(bot_id, user_id):
        bot.answer_callback_query(call.id, "✅ حذف شد")
        bot.edit_message_text("🗑 ربات حذف شد.", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: m.text == '💰 کیف پول')
def wallet(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    balance = get_user_balance(user_id)
    bot_username = bot.get_me().username
    
    text = f"💰 کیف پول\n\nموجودی: {balance:,} تومان\nکل درآمد: {user['total_earned']:,} تومان\n\n🎁 لینک رفرال:\nhttps://t.me/{bot_username}?start={user['referral_code']}"
    
    markup = types.InlineKeyboardMarkup()
    if balance >= 2000000:
        markup.add(types.InlineKeyboardButton("🏧 برداشت", callback_data="withdraw"))
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "withdraw")
def withdraw_request(call):
    msg = bot.send_message(call.message.chat.id, "💳 شماره کارت را وارد کنید:")
    bot.register_next_step_handler(msg, process_withdraw)

def process_withdraw(message):
    user_id = message.from_user.id
    card = message.text.strip()
    balance = get_user_balance(user_id)
    
    if balance < 2000000:
        bot.reply_to(message, "❌ موجودی کافی نیست")
        return
    
    with get_db() as conn:
        conn.execute('INSERT INTO withdraw_requests (user_id, amount, card_number, created_at) VALUES (?, ?, ?, ?)',
                    (user_id, balance, card, datetime.now().isoformat()))
        conn.execute('UPDATE users SET balance = 0 WHERE user_id = ?', (user_id,))
        conn.commit()
    
    bot.reply_to(message, f"✅ درخواست برداشت {balance:,} تومان ثبت شد.")
    
    for admin_id in ADMIN_IDS:
        bot.send_message(admin_id, f"💰 درخواست برداشت\n👤 {user_id}\n💰 {balance:,} تومان\n💳 {card}")

@bot.message_handler(func=lambda m: m.text == '📚 راهنما')
def guide(message):
    bot.send_message(message.chat.id, f"📚 راهنما\n\n💰 قیمت: {config.price:,} تومان\n💳 کارت: {config.card_number}\n👤 {config.card_holder}")

@bot.message_handler(func=lambda m: m.text == '📞 پشتیبانی')
def support(message):
    bot.send_message(message.chat.id, "📞 @shahraghee13")

@bot.message_handler(func=lambda m: m.text and m.text.startswith('📅'))
def show_days(message):
    days = get_subscription_days_left(message.from_user.id)
    bot.send_message(message.chat.id, f"📅 {days} روز مونده" if days > 0 else "❌ اشتراک فعال ندارید")

# ==================== پنل ادمین ====================

@bot.message_handler(func=lambda m: m.text == '👑 پنل ادمین')
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    with get_db() as conn:
        pending_payments = conn.execute('SELECT COUNT(*) FROM receipts WHERE status = "pending"').fetchone()[0]
        pending_files = conn.execute('SELECT COUNT(*) FROM pending_files WHERE status = "pending"').fetchone()[0]
        servers_count = conn.execute('SELECT COUNT(*) FROM servers WHERE status = "active"').fetchone()[0]
        total_load = conn.execute('SELECT SUM(current_load) FROM servers').fetchone()[0] or 0
        max_load = conn.execute('SELECT SUM(max_load) FROM servers').fetchone()[0] or 0
    
    text = f"👑 پنل ادمین\n\n📸 فیش: {pending_payments}\n📥 فایل: {pending_files}\n🖥️ سرور: {servers_count}\n📊 بار: {total_load}/{max_load}"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📸 فیش‌ها", callback_data="admin_receipts"),
        types.InlineKeyboardButton("📥 فایل‌ها", callback_data="admin_files"),
        types.InlineKeyboardButton("🖥️ سرورها", callback_data="admin_servers"),
        types.InlineKeyboardButton("➕ سرور جدید", callback_data="admin_add_server"),
        types.InlineKeyboardButton("💰 برداشت‌ها", callback_data="admin_withdraws"),
        types.InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings"),
        types.InlineKeyboardButton("🎁 تایید اشتراک", callback_data="admin_manual_sub")
    )
    
    bot.send_message(message.chat.id, text, reply_markup=markup)

# ==================== مدیریت فیش‌ها ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_receipts")
def admin_receipts_list(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    with get_db() as conn:
        receipts = conn.execute('SELECT * FROM receipts WHERE status = "pending" ORDER BY created_at DESC').fetchall()
    
    if not receipts:
        bot.send_message(call.message.chat.id, "📸 فیشی وجود ندارد")
        return
    
    for r in receipts:
        text = f"📸 فیش #{r['id']}\n👤 {r['user_id']}\n💰 {r['amount']:,} تومان\n🆔 {r['payment_code']}"
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_payment_{r['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"reject_payment_{r['id']}")
        )
        if os.path.exists(r['receipt_path']):
            with open(r['receipt_path'], 'rb') as f:
                bot.send_photo(call.message.chat.id, f, caption=text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_payment_'))
def approve_payment(call):
    receipt_id = int(call.data.replace('approve_payment_', ''))
    with get_db() as conn:
        receipt = conn.execute('SELECT * FROM receipts WHERE id = ?', (receipt_id,)).fetchone()
        if receipt:
            activate_subscription(receipt['subscription_id'], receipt['user_id'], receipt['amount'])
            conn.execute('UPDATE receipts SET status = "approved" WHERE id = ?', (receipt_id,))
            conn.commit()
            bot.answer_callback_query(call.id, "✅ تایید شد")
            bot.send_message(receipt['user_id'], f"✅ اشتراک شما فعال شد!\n📅 {config.subscription_days} روز اعتبار.")
            bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_payment_'))
def reject_payment(call):
    receipt_id = int(call.data.replace('reject_payment_', ''))
    with get_db() as conn:
        conn.execute('UPDATE receipts SET status = "rejected" WHERE id = ?', (receipt_id,))
        conn.commit()
        bot.answer_callback_query(call.id, "❌ رد شد")
        bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== مدیریت فایل‌ها (فقط توی پنل نمایش داده می‌شه) ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_files")
def admin_files_list(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    files = get_pending_files()
    
    if not files:
        bot.send_message(call.message.chat.id, "📥 فایلی وجود ندارد")
        return
    
    for f in files:
        text = f"📥 فایل #{f['id']}\n👤 کاربر: {f['user_id']}\n📄 {f['file_name']}\n📅 {f['submitted_at'][:10]}"
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید و ساخت", callback_data=f"build_file_{f['id']}"),
            types.InlineKeyboardButton("❌ حذف", callback_data=f"delete_file_{f['id']}")
        )
        
        if os.path.exists(f['file_path']):
            with open(f['file_path'], 'rb') as file:
                bot.send_document(call.message.chat.id, file, caption=text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('build_file_'))
def build_file(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    file_id = int(call.data.replace('build_file_', ''))
    
    bot.edit_message_caption("🔄 در حال ساخت ربات...", call.message.chat.id, call.message.message_id)
    
    result = build_bot_from_pending(file_id)
    
    if result['success']:
        bot.edit_message_caption(
            f"✅ ربات ساخته شد!\n🤖 {result['name']}\n🔗 https://t.me/{result['username']}",
            call.message.chat.id,
            call.message.message_id
        )
    else:
        bot.edit_message_caption(f"❌ خطا: {result['error']}", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_file_'))
def delete_file(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    file_id = int(call.data.replace('delete_file_', ''))
    update_pending_file_status(file_id, 'deleted')
    bot.answer_callback_query(call.id, "❌ حذف شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== مدیریت سرورها ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_servers")
def admin_servers_list(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    with get_db() as conn:
        servers = conn.execute('SELECT * FROM servers ORDER BY created_at DESC').fetchall()
    
    if not servers:
        bot.send_message(call.message.chat.id, "🖥️ سروری وجود ندارد\nاز دکمه «➕ سرور جدید» استفاده کنید.")
        return
    
    text = "🖥️ **سرورها**\n\n"
    for s in servers:
        text += f"🔹 {s['name']}\n   📍 {s['ip']}:{s['port']}\n   📊 {s['current_load']}/{s['max_load']}\n   ✅ {s['status']}\n\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_add_server")
def admin_add_server(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, 
        "➕ **افزودن سرور**\n\n"
        "اطلاعات را ارسال کنید:\n"
        "`نام\nIP\nپورت\nyوزرنیم\nرمز`\n\n"
        "مثال:\n"
        "`Server1\n192.168.1.100\n22\nroot\n123`")
    
    bot.register_next_step_handler(msg, process_add_server)

def process_add_server(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    lines = message.text.strip().split('\n')
    if len(lines) < 5:
        bot.reply_to(message, "❌ فرمت صحیح نیست")
        return
    
    name = lines[0].strip()
    ip = lines[1].strip()
    try:
        port = int(lines[2].strip())
    except:
        port = 22
    username = lines[3].strip()
    password = lines[4].strip()
    
    status_msg = bot.reply_to(message, "🔄 در حال بررسی...")
    success, msg = add_new_server(name, ip, port, username, password)
    bot.edit_message_text(msg, message.chat.id, status_msg.message_id)

# ==================== سایر بخش‌های ادمین ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_withdraws")
def admin_withdraws_list(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    with get_db() as conn:
        withdraws = conn.execute('SELECT * FROM withdraw_requests WHERE status = "pending" ORDER BY created_at DESC').fetchall()
    
    if not withdraws:
        bot.send_message(call.message.chat.id, "💰 درخواستی وجود ندارد")
        return
    
    for w in withdraws:
        text = f"💰 #{w['id']}\n👤 {w['user_id']}\n💰 {w['amount']:,} تومان\n💳 {w['card_number']}"
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_withdraw_{w['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"reject_withdraw_{w['id']}")
        )
        bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_withdraw_'))
def approve_withdraw(call):
    wid = int(call.data.replace('approve_withdraw_', ''))
    with get_db() as conn:
        conn.execute('UPDATE withdraw_requests SET status = "approved" WHERE id = ?', (wid,))
        conn.commit()
    bot.answer_callback_query(call.id, "✅ تایید شد")

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_withdraw_'))
def reject_withdraw(call):
    wid = int(call.data.replace('reject_withdraw_', ''))
    with get_db() as conn:
        w = conn.execute('SELECT * FROM withdraw_requests WHERE id = ?', (wid,)).fetchone()
        if w:
            conn.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (w['amount'], w['user_id']))
            conn.execute('UPDATE withdraw_requests SET status = "rejected" WHERE id = ?', (wid,))
            conn.commit()
    bot.answer_callback_query(call.id, "❌ رد شد")

@bot.callback_query_handler(func=lambda call: call.data == "admin_settings")
def admin_settings(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("💰 تغییر قیمت", callback_data="set_price"),
        types.InlineKeyboardButton("💳 تغییر کارت", callback_data="set_card"),
        types.InlineKeyboardButton("👤 تغییر صاحب کارت", callback_data="set_holder"),
        types.InlineKeyboardButton("⏰ تغییر مدت اشتراک", callback_data="set_duration"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    bot.edit_message_text(
        f"⚙️ تنظیمات\n\n💰 {config.price:,} تومان\n💳 {config.card_number}\n👤 {config.card_holder}\n⏰ {config.subscription_days} روز",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "set_price")
def set_price(call):
    msg = bot.send_message(call.message.chat.id, f"💰 قیمت جدید (فعلی: {config.price:,}):")
    bot.register_next_step_handler(msg, lambda m: set_config(m, 'price', int))

@bot.callback_query_handler(func=lambda call: call.data == "set_card")
def set_card(call):
    msg = bot.send_message(call.message.chat.id, f"💳 کارت جدید (فعلی: {config.card_number}):")
    bot.register_next_step_handler(msg, lambda m: set_config(m, 'card_number', str))

@bot.callback_query_handler(func=lambda call: call.data == "set_holder")
def set_holder(call):
    msg = bot.send_message(call.message.chat.id, f"👤 صاحب کارت جدید (فعلی: {config.card_holder}):")
    bot.register_next_step_handler(msg, lambda m: set_config(m, 'card_holder', str))

@bot.callback_query_handler(func=lambda call: call.data == "set_duration")
def set_duration(call):
    msg = bot.send_message(call.message.chat.id, f"⏰ مدت اشتراک به روز (فعلی: {config.subscription_days}):")
    bot.register_next_step_handler(msg, lambda m: set_config(m, 'subscription_days', int))

def set_config(message, key, cast):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        val = cast(message.text.strip())
        setattr(config, key, val)
        config.save_to_db()
        bot.reply_to(message, f"✅ {key} تغییر کرد")
    except:
        bot.reply_to(message, "❌ خطا")

@bot.callback_query_handler(func=lambda call: call.data == "admin_manual_sub")
def admin_manual_sub(call):
    msg = bot.send_message(call.message.chat.id, "🎁 آیدی کاربر:")
    bot.register_next_step_handler(msg, process_manual_sub)

def process_manual_sub(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        user_id = int(message.text.strip())
        sub_id, code = create_subscription(user_id, config.price)
        if sub_id and activate_subscription(sub_id, user_id, config.price):
            bot.reply_to(message, f"✅ اشتراک {user_id} فعال شد")
            bot.send_message(user_id, f"✅ اشتراک شما فعال شد!\n📤 فایل ربات خود را ارسال کنید.")
    except:
        bot.reply_to(message, "❌ خطا")

@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call):
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    bot.send_message(call.message.chat.id, "🚀 منوی اصلی:", reply_markup=get_main_menu(call.from_user.id))

# ==================== بررسی انقضا ====================

def check_expired():
    while True:
        try:
            with get_db() as conn:
                expired = conn.execute('''
                    SELECT user_id FROM users 
                    WHERE active_subscription = 1 
                    AND julianday(subscription_expire) - julianday('now') < 0
                ''').fetchall()
                
                for user in expired:
                    conn.execute('UPDATE users SET active_subscription = 0 WHERE user_id = ?', (user['user_id'],))
                    
                    # توقف ربات‌های منقضی شده
                    bots = conn.execute('SELECT id, server_id FROM bots WHERE user_id = ?', (user['user_id'],)).fetchall()
                    for bot in bots:
                        if bot['server_id']:
                            server = conn.execute('SELECT * FROM servers WHERE id = ?', (bot['server_id'],)).fetchone()
                            if server:
                                stop_bot_on_server(dict(server), bot['id'])
                        else:
                            stop_bot_on_mother(bot['id'])
                    
                    try:
                        bot.send_message(user['user_id'], "❌ اشتراک شما منقضی شد!")
                    except:
                        pass
                
                conn.commit()
            time.sleep(3600)
        except:
            time.sleep(3600)

# ==================== اجرا ====================

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 ربات مادر نسخه نهایی")
    print("=" * 60)
    print(f"✅ ادمین: {ADMIN_IDS}")
    print(f"✅ قیمت: {config.price:,} تومان")
    print("=" * 60)
    
    expiry_thread = threading.Thread(target=check_expired, daemon=True)
    expiry_thread.start()
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            print(f"خطا: {e}")
            time.sleep(5)