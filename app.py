#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ربات مادر نهایی - نسخه 9.0 با ایزوله‌سازی داکر، سیستم اشتراک، رفرال پیشرفته و لود بالانس
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
import logging
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
import secrets
import docker
import paramiko
import redis
from functools import wraps

# ==================== تنظیمات پایه ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "database")
FILES_DIR = os.path.join(BASE_DIR, "user_files")
RUNNING_DIR = os.path.join(BASE_DIR, "running_bots")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
RECEIPTS_DIR = os.path.join(BASE_DIR, "receipts")

os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(FILES_DIR, exist_ok=True)
os.makedirs(RUNNING_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(RECEIPTS_DIR, exist_ok=True)

# ==================== توکن ربات مادر ====================
BOT_TOKEN = "7685135237:AAEmsHktRw9cEqrHTkCoPZk-fBimK7TDjOo"
bot = telebot.TeleBot(BOT_TOKEN)
bot.delete_webhook()

# ==================== تنظیمات متغیر (قابل تغییر توسط ادمین) ====================
ADMIN_IDS = [327855654]
CARD_NUMBER = "5892101187322777"
CARD_HOLDER = "مرتضی نیکخو خنجری"
PRICE_PER_MONTH = 2000000  # 2 میلیون تومان
PRICE_3_MONTHS = 5000000   # 5 میلیون تومان (تخفیف)
MIN_WITHDRAW_AMOUNT = 2000000  # حداقل برداشت 2 میلیون
REFERRAL_COMMISSION_PERCENT = 7  # 7 درصد پورسانت
TRIAL_HOURS = 24  # تست 24 ساعته

# متن راهنما (قابل تغییر توسط ادمین)
GUIDE_TEXT = """📚 راهنمای کامل ربات مادر

1️⃣ ساخت ربات:
   • ابتدا اشتراک خود را فعال کنید
   • فایل .py یا .zip خود را آپلود کنید
   • توکن ربات باید داخل کد باشد

2️⃣ انواع اشتراک:
   • ماهانه: 2,000,000 تومان
   • سه ماهه: 5,000,000 تومان
   • تست رایگان: 24 ساعت

3️⃣ سیستم رفرال:
   • هر نفر 7% پورسانت خرید
   • لینک اختصاصی خود را به اشتراک بگذارید

4️⃣ برداشت وجه:
   • حداقل مبلغ برداشت: 2,000,000 تومان
   • از طریق بخش برداشت اقدام کنید

5️⃣ پشتیبانی:
   • @shahraghee13
"""

# ==================== راه‌اندازی سرویس‌های خارجی ====================
try:
    docker_client = docker.from_env()
    DOCKER_AVAILABLE = True
except:
    DOCKER_AVAILABLE = False
    print("⚠️ Docker در دسترس نیست")

try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    REDIS_AVAILABLE = True
except:
    REDIS_AVAILABLE = False
    print("⚠️ Redis در دسترس نیست")

# ==================== لاگینگ ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            os.path.join(LOGS_DIR, 'mother_bot.log'),
            maxBytes=10485760,
            backupCount=10
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== دیتابیس پیشرفته SQLite ====================
DB_PATH = os.path.join(DB_DIR, 'mother_bot.db')

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

# ایجاد تمام جداول
with get_db() as conn:
    # جدول کاربران
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            balance INTEGER DEFAULT 0,
            bots_count INTEGER DEFAULT 0,
            max_bots INTEGER DEFAULT 1,
            referral_code TEXT UNIQUE,
            referred_by INTEGER,
            referrals_count INTEGER DEFAULT 0,
            verified_referrals INTEGER DEFAULT 0,
            payment_status TEXT DEFAULT 'pending',
            payment_date TIMESTAMP,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP,
            last_active TIMESTAMP
        )
    ''')
    
    # جدول ربات‌ها
    conn.execute('''
        CREATE TABLE IF NOT EXISTS bots (
            id TEXT PRIMARY KEY,
            user_id INTEGER,
            token TEXT,
            name TEXT,
            username TEXT,
            file_path TEXT,
            folder_path TEXT,
            container_id TEXT,
            server_id TEXT,
            pid INTEGER,
            status TEXT DEFAULT 'stopped',
            created_at TIMESTAMP,
            last_active TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    ''')
    
    # جدول فیش‌های واریزی
    conn.execute('''
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            receipt_path TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP,
            reviewed_at TIMESTAMP,
            reviewed_by INTEGER,
            payment_code TEXT UNIQUE,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')
    
    # جدول اشتراک‌ها
    conn.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            plan_type TEXT,
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            is_active INTEGER DEFAULT 1,
            paid_amount INTEGER,
            created_at TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')
    
    # جدول تست 24 ساعته
    conn.execute('''
        CREATE TABLE IF NOT EXISTS trial_usage (
            user_id INTEGER PRIMARY KEY,
            start_time TIMESTAMP,
            bot_id TEXT,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')
    
    # جدول رفرال و پورسانت
    conn.execute('''
        CREATE TABLE IF NOT EXISTS commissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            reason TEXT,
            created_at TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')
    
    # جدول درخواست‌های برداشت
    conn.execute('''
        CREATE TABLE IF NOT EXISTS withdraw_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            card_number TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP,
            processed_at TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')
    
    # جدول سرورها برای لود بالانس
    conn.execute('''
        CREATE TABLE IF NOT EXISTS servers (
            id TEXT PRIMARY KEY,
            name TEXT,
            ip TEXT,
            ssh_user TEXT,
            ssh_password TEXT,
            max_bots INTEGER DEFAULT 1000,
            active_bots INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP
        )
    ''')
    
    conn.commit()

# ==================== کلاس مدیریت امنیت ====================
class SecurityManager:
    """بررسی امنیت کد کاربر قبل از اجرا"""
    
    DANGEROUS_IMPORTS = [
        'os', 'subprocess', 'sys', 'shutil', 'socket',
        'requests', 'urllib', 'http', 'ftp', 'smtplib',
        'sqlite3', 'mysql', 'psycopg2', 'pymongo'
    ]
    
    DANGEROUS_PATTERNS = [
        r'os\.system', r'subprocess\.', r'eval\s*\(', r'exec\s*\(',
        r'__import__\s*\(', r'base64\.b64decode', r'socket\.'
    ]
    
    @staticmethod
    def validate_code(code):
        errors = []
        code_lower = code.lower()
        
        for imp in SecurityManager.DANGEROUS_IMPORTS:
            if re.search(rf'\b{imp}\b', code_lower):
                errors.append(f"ایمپورت ممنوع: {imp}")
        
        for pattern in SecurityManager.DANGEROUS_PATTERNS:
            if re.search(pattern, code_lower):
                errors.append(f"کد خطرناک شناسایی شد")
        
        if len(code) > 100000:
            errors.append("حجم کد بیش از حد مجاز است (حداکثر 100KB)")
        
        return len(errors) == 0, errors

# ==================== کلاس مدیریت داکر ====================
class DockerManager:
    """ایزوله‌سازی کامل کد کاربر در داکر"""
    
    def __init__(self):
        self.containers = {}
    
    def run_bot_in_docker(self, bot_id, code, token):
        if not DOCKER_AVAILABLE:
            return {'success': False, 'error': 'Docker در دسترس نیست'}
        
        try:
            work_dir = os.path.join(RUNNING_DIR, f"docker_{bot_id}")
            os.makedirs(work_dir, exist_ok=True)
            
            code_path = os.path.join(work_dir, 'bot.py')
            with open(code_path, 'w', encoding='utf-8') as f:
                f.write(code)
            
            container = docker_client.containers.run(
                'python:3.11-slim',
                command=f'python /app/bot.py',
                detach=True,
                mem_limit='512m',
                cpu_quota=50000,
                network_mode='bridge',
                read_only=True,
                volumes={work_dir: {'bind': '/app', 'mode': 'ro'}},
                name=f'bot_{bot_id}',
                remove=True
            )
            
            self.containers[bot_id] = container.id
            return {'success': True, 'container_id': container.id}
            
        except Exception as e:
            logger.error(f"Docker error: {e}")
            return {'success': False, 'error': str(e)}
    
    def stop_container(self, bot_id):
        if bot_id in self.containers:
            try:
                container = docker_client.containers.get(self.containers[bot_id])
                container.stop(timeout=5)
                del self.containers[bot_id]
                return True
            except:
                pass
        return False

# ==================== کلاس مدیریت سرور ====================
class ServerManager:
    """مدیریت سرورها و لود بالانس"""
    
    def __init__(self):
        self.servers = self.load_servers_from_db()
    
    def load_servers_from_db(self):
        servers = []
        try:
            with get_db() as conn:
                rows = conn.execute('SELECT * FROM servers WHERE status = "active"').fetchall()
                for row in rows:
                    servers.append(dict(row))
        except:
            pass
        return servers
    
    def add_server(self, name, ip, ssh_user, ssh_password, max_bots=1000):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, username=ssh_user, password=ssh_password, timeout=10)
            ssh.close()
            
            server_id = hashlib.md5(f"{ip}_{time.time()}".encode()).hexdigest()[:10]
            
            with get_db() as conn:
                conn.execute('''
                    INSERT INTO servers (id, name, ip, ssh_user, ssh_password, max_bots, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (server_id, name, ip, ssh_user, ssh_password, max_bots, datetime.now().isoformat()))
                conn.commit()
            
            self.servers = self.load_servers_from_db()
            return {'success': True, 'server_id': server_id}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_best_server(self):
        if not self.servers:
            return None
        
        best = min(self.servers, key=lambda s: s['active_bots'] / s['max_bots'])
        if best['active_bots'] < best['max_bots']:
            return best
        return None
    
    def run_bot_on_server(self, server, bot_id, code, token):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(server['ip'], username=server['ssh_user'], password=server['ssh_password'], timeout=10)
            
            commands = f"""
mkdir -p /home/bots/{bot_id}
cat > /home/bots/{bot_id}/bot.py << 'EOF'
{code}
EOF
cd /home/bots/{bot_id}
docker run -d --name bot_{bot_id} --memory=512m --cpus=0.5 -v $(pwd):/app python:3.11-slim python /app/bot.py
echo $! > /home/bots/{bot_id}/pid.txt
"""
            ssh.exec_command(commands)
            ssh.close()
            
            with get_db() as conn:
                conn.execute('UPDATE servers SET active_bots = active_bots + 1 WHERE id = ?', (server['id'],))
                conn.commit()
            
            return {'success': True, 'server_id': server['id']}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

# ==================== کلاس مدیریت اشتراک ====================
class SubscriptionManager:
    
    @staticmethod
    def activate_subscription(user_id, plan_type, paid_amount):
        with get_db() as conn:
            now = datetime.now()
            
            if plan_type == 'monthly':
                end_date = now + timedelta(days=30)
            elif plan_type == '3months':
                end_date = now + timedelta(days=90)
            else:
                return False
            
            # غیرفعال کردن اشتراک قبلی
            conn.execute('UPDATE subscriptions SET is_active = 0 WHERE user_id = ?', (user_id,))
            
            conn.execute('''
                INSERT INTO subscriptions (user_id, plan_type, start_date, end_date, is_active, paid_amount, created_at)
                VALUES (?, ?, ?, ?, 1, ?, ?)
            ''', (user_id, plan_type, now.isoformat(), end_date.isoformat(), paid_amount, now.isoformat()))
            
            conn.execute('UPDATE users SET payment_status = ?, payment_date = ? WHERE user_id = ?',
                        ('approved', now.isoformat(), user_id))
            conn.commit()
            return True
    
    @staticmethod
    def activate_trial(user_id, bot_id):
        with get_db() as conn:
            now = datetime.now()
            conn.execute('''
                INSERT OR REPLACE INTO trial_usage (user_id, start_time, bot_id, is_active)
                VALUES (?, ?, ?, 1)
            ''', (user_id, now.isoformat(), bot_id))
            conn.commit()
            return True
    
    @staticmethod
    def check_trial_active(user_id):
        with get_db() as conn:
            row = conn.execute('''
                SELECT start_time FROM trial_usage 
                WHERE user_id = ? AND is_active = 1
            ''', (user_id,)).fetchone()
            
            if not row:
                return False
            
            start_time = datetime.fromisoformat(row['start_time'])
            if datetime.now() - start_time > timedelta(hours=TRIAL_HOURS):
                conn.execute('UPDATE trial_usage SET is_active = 0 WHERE user_id = ?', (user_id,))
                conn.commit()
                return False
            return True
    
    @staticmethod
    def has_active_subscription(user_id):
        with get_db() as conn:
            row = conn.execute('''
                SELECT end_date FROM subscriptions 
                WHERE user_id = ? AND is_active = 1 AND end_date > ?
            ''', (user_id, datetime.now().isoformat())).fetchone()
            return row is not None
    
    @staticmethod
    def can_create_bot(user_id):
        if SubscriptionManager.has_active_subscription(user_id):
            return True, 'subscription'
        
        if SubscriptionManager.check_trial_active(user_id):
            return True, 'trial'
        
        return False, None

# ==================== کلاس مدیریت رفرال ====================
class ReferralManager:
    
    @staticmethod
    def process_purchase_commission(referrer_id, paid_amount):
        commission = int(paid_amount * REFERRAL_COMMISSION_PERCENT / 100)
        
        with get_db() as conn:
            conn.execute('''
                INSERT INTO commissions (user_id, amount, reason, created_at)
                VALUES (?, ?, ?, ?)
            ''', (referrer_id, commission, f'پورسانت {REFERRAL_COMMISSION_PERCENT}% از خرید', datetime.now().isoformat()))
            
            conn.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (commission, referrer_id))
            conn.commit()
            
            try:
                bot.send_message(referrer_id, f"🎉 {commission:,} تومان پورسانت به کیف پول شما اضافه شد!")
            except:
                pass
            
            return commission
    
    @staticmethod
    def get_referral_link(user_id):
        with get_db() as conn:
            user = conn.execute('SELECT referral_code FROM users WHERE user_id = ?', (user_id,)).fetchone()
            if user:
                bot_username = bot.get_me().username
                return f"https://t.me/{bot_username}?start={user['referral_code']}"
        return None

# ==================== کلاس مدیریت برداشت ====================
class WithdrawManager:
    
    @staticmethod
    def request_withdraw(user_id, amount, card_number):
        if amount < MIN_WITHDRAW_AMOUNT:
            return False, f"حداقل مبلغ برداشت {MIN_WITHDRAW_AMOUNT:,} تومان است"
        
        with get_db() as conn:
            balance = conn.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,)).fetchone()
            
            if not balance or balance['balance'] < amount:
                return False, "موجودی کیف پول کافی نیست"
            
            conn.execute('''
                INSERT INTO withdraw_requests (user_id, amount, card_number, created_at)
                VALUES (?, ?, ?, ?)
            ''', (user_id, amount, card_number, datetime.now().isoformat()))
            
            conn.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (amount, user_id))
            conn.commit()
            
            for admin_id in ADMIN_IDS:
                try:
                    bot.send_message(admin_id, f"💰 درخواست برداشت جدید\n👤 کاربر: {user_id}\n💰 مبلغ: {amount:,} تومان\n💳 کارت: {card_number}")
                except:
                    pass
            
            return True, "درخواست برداشت ثبت شد"
    
    @staticmethod
    def get_balance(user_id):
        with get_db() as conn:
            user = conn.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,)).fetchone()
            return user['balance'] if user else 0

# ==================== توابع کمکی اصلی ====================

def generate_referral_code(user_id):
    return hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:8]

def get_user(user_id):
    try:
        with get_db() as conn:
            user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
            return dict(user) if user else None
    except:
        return None

def create_user(user_id, username, first_name, last_name, referred_by=None):
    try:
        with get_db() as conn:
            now = datetime.now().isoformat()
            referral_code = generate_referral_code(user_id)
            
            conn.execute('''
                INSERT OR IGNORE INTO users 
                (user_id, username, first_name, last_name, referral_code, referred_by, created_at, last_active, payment_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name, referral_code, referred_by, now, now, 'pending'))
            
            conn.execute('UPDATE users SET last_active = ? WHERE user_id = ?', (now, user_id))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"خطا در create_user: {e}")
        return False

def extract_token_from_code(code):
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

def extract_files_from_zip(zip_path, extract_to):
    py_files = []
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        
        for root, _, files in os.walk(extract_to):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        py_files.append({'name': file, 'path': file_path, 'content': content})
                    except:
                        pass
    except:
        pass
    return py_files

def save_uploaded_file(user_id, file_data, file_name):
    try:
        user_dir = os.path.join(FILES_DIR, str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        timestamp = int(time.time())
        file_path = os.path.join(user_dir, f"{timestamp}_{file_name}")
        with open(file_path, 'wb') as f:
            f.write(file_data)
        return file_path
    except:
        return None

def add_bot_to_db(user_id, bot_id, token, name, username, file_path, container_id=None, server_id=None):
    try:
        with get_db() as conn:
            now = datetime.now().isoformat()
            conn.execute('''
                INSERT INTO bots (id, user_id, token, name, username, file_path, container_id, server_id, status, created_at, last_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (bot_id, user_id, token, name, username, file_path, container_id, server_id, 'running', now, now))
            
            conn.execute('UPDATE users SET bots_count = bots_count + 1, last_active = ? WHERE user_id = ?', (now, user_id))
            conn.commit()
            return True
    except:
        return False

def delete_bot_from_db(bot_id, user_id):
    try:
        with get_db() as conn:
            bot = conn.execute('SELECT * FROM bots WHERE id = ? AND user_id = ?', (bot_id, user_id)).fetchone()
            if not bot:
                return False
            
            DockerManager().stop_container(bot_id)
            
            if bot['file_path'] and os.path.exists(bot['file_path']):
                os.remove(bot['file_path'])
            
            conn.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
            conn.execute('UPDATE users SET bots_count = bots_count - 1 WHERE user_id = ?', (user_id,))
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

# ==================== منوی اصلی ====================
def get_main_menu(is_admin=False):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    
    buttons = [
        types.KeyboardButton('🤖 ساخت ربات جدید'),
        types.KeyboardButton('📋 ربات‌های من'),
        types.KeyboardButton('🔄 فعال/غیرفعال کردن'),
        types.KeyboardButton('🗑 حذف ربات'),
        types.KeyboardButton('💰 کیف پول و رفرال'),
        types.KeyboardButton('🎁 اشتراک و تست ۲۴ ساعته'),
        types.KeyboardButton('💳 برداشت وجه'),
        types.KeyboardButton('📚 راهنما'),
        types.KeyboardButton('📦 نصب کتابخانه'),
        types.KeyboardButton('📊 آمار'),
        types.KeyboardButton('📞 پشتیبانی')
    ]
    
    if is_admin:
        buttons.append(types.KeyboardButton('👑 پنل ادمین'))
    
    markup.add(*buttons)
    return markup

# ==================== هندلر استارت ====================
@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    
    referred_by = None
    args = message.text.split()
    if len(args) > 1:
        ref_code = args[1]
        try:
            with get_db() as conn:
                referrer = conn.execute('SELECT user_id FROM users WHERE referral_code = ?', (ref_code,)).fetchone()
                if referrer and referrer['user_id'] != user_id:
                    referred_by = referrer['user_id']
                    try:
                        bot.send_message(referred_by, f"🎉 یک نفر با لینک رفرال شما وارد شد!\n👤 {first_name}\n🆔 {user_id}")
                    except:
                        pass
        except:
            pass
    
    create_user(user_id, username, first_name, last_name, referred_by)
    
    user = get_user(user_id) or {'referral_code': '', 'referrals_count': 0, 'verified_referrals': 0}
    bot_username = bot.get_me().username
    referral_link = f"https://t.me/{bot_username}?start={user['referral_code']}"
    
    is_admin = user_id in ADMIN_IDS
    markup = get_main_menu(is_admin)
    
    welcome_text = (
        f"🚀 به ربات مادر نهایی خوش آمدید {first_name}!\n\n"
        f"👤 آیدی شما: {user_id}\n"
        f"🎁 کد رفرال شما: {user['referral_code']}\n"
        f"🔗 لینک دعوت: {referral_link}\n\n"
        f"💰 موجودی کیف پول: {WithdrawManager.get_balance(user_id):,} تومان\n\n"
        f"💡 هر خرید از لینک شما = ۷٪ پورسانت\n"
        f"🎁 تست ۲۴ ساعته رایگان برای ساخت ربات\n"
        f"📤 برای ساخت ربات، اشتراک خود را فعال کنید"
    )
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

# ==================== اشتراک و تست ۲۴ ساعته ====================
@bot.message_handler(func=lambda m: m.text == '🎁 اشتراک و تست ۲۴ ساعته')
def subscription_menu(message):
    user_id = message.from_user.id
    
    has_sub = SubscriptionManager.has_active_subscription(user_id)
    trial_active = SubscriptionManager.check_trial_active(user_id)
    
    text = f"🎁 **مدیریت اشتراک و تست**\n\n"
    text += f"📊 وضعیت فعلی:\n"
    text += f"{'✅ اشتراک فعال' if has_sub else '❌ بدون اشتراک فعال'}\n"
    text += f"{'✅ تست ۲۴ ساعته فعال' if trial_active else '❌ تست فعال نیست'}\n\n"
    text += f"💰 **قیمت اشتراک:**\n"
    text += f"• ماهانه: {PRICE_PER_MONTH:,} تومان\n"
    text += f"• سه ماهه: {PRICE_3_MONTHS:,} تومان (تخفیف ویژه)\n\n"
    text += f"🎁 **تست رایگان ۲۴ ساعته:**\n"
    text += f"• بدون پرداخت هزینه\n"
    text += f"• فقط یک بار قابل استفاده\n"
    text += f"• بعد از ۲۴ ساعت ربات متوقف می‌شود\n\n"
    text += f"💳 شماره کارت: `{CARD_NUMBER}`\n"
    text += f"🏦 به نام: {CARD_HOLDER}"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💰 خرید ماهانه", callback_data="buy_monthly"),
        types.InlineKeyboardButton("💰 خرید سه ماهه", callback_data="buy_3months"),
        types.InlineKeyboardButton("🎁 فعال‌سازی تست ۲۴ ساعته", callback_data="activate_trial")
    )
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ['buy_monthly', 'buy_3months'])
def buy_subscription(call):
    user_id = call.from_user.id
    
    if call.data == 'buy_monthly':
        amount = PRICE_PER_MONTH
        plan = 'monthly'
    else:
        amount = PRICE_3_MONTHS
        plan = '3months'
    
    text = (
        f"💰 **خرید اشتراک {plan}**\n\n"
        f"مبلغ: {amount:,} تومان\n"
        f"شماره کارت: `{CARD_NUMBER}`\n"
        f"به نام: {CARD_HOLDER}\n\n"
        f"📸 پس از واریز، تصویر فیش را ارسال کنید\n"
        f"🆔 کد پیگیری خود را یادداشت کنید"
    )
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == 'activate_trial')
def activate_trial(call):
    user_id = call.from_user.id
    
    if SubscriptionManager.check_trial_active(user_id):
        bot.answer_callback_query(call.id, "❌ شما قبلاً از تست ۲۴ ساعته استفاده کرده‌اید!")
        return
    
    bot.edit_message_text(
        "🎁 **تست ۲۴ ساعته فعال شد!**\n\n"
        "✅ می‌توانید یک ربات بسازید\n"
        "⏰ بعد از ۲۴ ساعت ربات متوقف می‌شود\n"
        "💡 برای استفاده دائمی، اشتراک تهیه کنید",
        call.message.chat.id,
        call.message.message_id
    )

# ==================== کیف پول و رفرال ====================
@bot.message_handler(func=lambda m: m.text == '💰 کیف پول و رفرال')
def wallet_ref(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        bot.send_message(message.chat.id, "❌ لطفاً /start را بزنید")
        return
    
    referral_link = ReferralManager.get_referral_link(user_id)
    balance = WithdrawManager.get_balance(user_id)
    
    text = f"💰 **کیف پول و سیستم رفرال**\n\n"
    text += f"👤 کاربر: {user['first_name']}\n"
    text += f"🆔 آیدی: {user_id}\n\n"
    text += f"💳 **موجودی قابل برداشت:** {balance:,} تومان\n\n"
    text += f"🎁 **لینک رفرال شما:**\n`{referral_link}`\n\n"
    text += f"📊 **آمار رفرال:**\n"
    text += f"• کلیک‌ها: {user['referrals_count']}\n"
    text += f"• خریدهای موفق: {user['verified_referrals']}\n\n"
    text += f"💰 **پورسانت:**\n"
    text += f"• هر خرید از لینک شما = {REFERRAL_COMMISSION_PERCENT}% به کیف پول شما\n\n"
    text += f"💡 هر ۵ خرید موفق = ۱ ربات اضافه"
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# ==================== برداشت وجه ====================
@bot.message_handler(func=lambda m: m.text == '💳 برداشت وجه')
def withdraw_menu(message):
    user_id = message.from_user.id
    balance = WithdrawManager.get_balance(user_id)
    
    text = (
        f"💳 **برداشت وجه**\n\n"
        f"💰 موجودی قابل برداشت: {balance:,} تومان\n"
        f"📌 حداقل مبلغ برداشت: {MIN_WITHDRAW_AMOUNT:,} تومان\n\n"
        f"⚠️ لطفاً مبلغ و شماره کارت خود را به صورت زیر ارسال کنید:\n\n"
        f"`مبلغ|شماره کارت`\n\n"
        f"مثال: `2000000|6037991234567890`"
    )
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")
    bot.register_next_step_handler(message, process_withdraw)

def process_withdraw(message):
    user_id = message.from_user.id
    
    try:
        parts = message.text.split('|')
        if len(parts) != 2:
            bot.reply_to(message, "❌ فرمت صحیح نیست! مثال: `2000000|6037991234567890`", parse_mode="Markdown")
            return
        
        amount = int(parts[0].strip())
        card_number = parts[1].strip()
        
        success, msg = WithdrawManager.request_withdraw(user_id, amount, card_number)
        bot.reply_to(message, msg)
        
    except ValueError:
        bot.reply_to(message, "❌ مبلغ باید عدد باشد!")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")

# ==================== فیش واریزی ====================
@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    
    try:
        with get_db() as conn:
            existing = conn.execute('SELECT id FROM receipts WHERE user_id = ? AND status = "pending"', (user_id,)).fetchone()
            if existing:
                bot.reply_to(message, "⏳ شما یک فیش در انتظار بررسی دارید")
                return
    except:
        pass
    
    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    payment_code = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:8].upper()
    receipt_path = os.path.join(RECEIPTS_DIR, f"{user_id}_{payment_code}.jpg")
    
    with open(receipt_path, 'wb') as f:
        f.write(downloaded_file)
    
    # سعی می‌کنیم مبلغ را از کپشن تشخیص دهیم
    amount = PRICE_PER_MONTH
    plan_type = 'monthly'
    if message.caption:
        if 'سه ماهه' in message.caption or '3ماه' in message.caption:
            amount = PRICE_3_MONTHS
            plan_type = '3months'
    
    with get_db() as conn:
        conn.execute('''
            INSERT INTO receipts (user_id, amount, receipt_path, created_at, payment_code)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, amount, receipt_path, datetime.now().isoformat(), payment_code))
        conn.commit()
    
    bot.reply_to(
        message,
        f"✅ فیش دریافت شد\n"
        f"💰 مبلغ: {amount:,} تومان\n"
        f"📋 نوع: {plan_type}\n"
        f"🆔 کد پیگیری: {payment_code}\n\n"
        f"پس از بررسی توسط ادمین، اشتراک شما فعال می‌شود"
    )
    
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(
                admin_id,
                f"📸 فیش جدید\n👤 کاربر: {user_id}\n💰 مبلغ: {amount:,} تومان\n📋 {plan_type}\n🆔 {payment_code}"
            )
        except:
            pass

# ==================== ساخت ربات جدید ====================
@bot.message_handler(func=lambda m: m.text == '🤖 ساخت ربات جدید')
def new_bot(message):
    user_id = message.from_user.id
    
    can_create, reason = SubscriptionManager.can_create_bot(user_id)
    
    if not can_create:
        text = (
            f"❌ شما دسترسی به ساخت ربات ندارید!\n\n"
            f"برای ساخت ربات:\n"
            f"1️⃣ فعال‌سازی تست ۲۴ ساعته (رایگان)\n"
            f"2️⃣ خرید اشتراک ماهانه یا سه ماهه\n\n"
            f"💳 شماره کارت: `{CARD_NUMBER}`\n"
            f"🏦 به نام: {CARD_HOLDER}"
        )
        bot.send_message(message.chat.id, text, parse_mode="Markdown")
        return
    
    text = (
        f"🤖 **ساخت ربات جدید**\n\n"
        f"کاربر گرامی، از اینکه مارو انتخاب کردین متشکرم!\n\n"
        f"📤 **مراحل ساخت ربات:**\n"
        f"1️⃣ فایل `.py` یا `.zip` خود را ارسال کنید\n"
        f"2️⃣ توکن ربات باید داخل کد باشد\n"
        f"3️⃣ حداکثر حجم: ۵۰ مگابایت\n"
        f"4️⃣ در صورت وجود چند فایل، آنها را zip کنید\n\n"
        f"✅ **تایپ اشتراک:** {reason}\n"
        f"🔒 کد شما در محیط ایزوله داکر اجرا می‌شود"
    )
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# ==================== آپلود و اجرای ربات ====================
@bot.message_handler(content_types=['document'])
def handle_build_file(message):
    user_id = message.from_user.id
    
    can_create, reason = SubscriptionManager.can_create_bot(user_id)
    if not can_create:
        bot.reply_to(message, "❌ ابتدا اشتراک خود را فعال کنید یا تست ۲۴ ساعته را فعال نمایید!")
        return
    
    file_name = message.document.file_name
    
    if not (file_name.endswith('.py') or file_name.endswith('.zip')):
        bot.reply_to(message, "❌ فقط فایل‌های `.py` یا `.zip` مجاز هستند!")
        return
    
    if message.document.file_size > 50 * 1024 * 1024:
        bot.reply_to(message, "❌ حجم فایل نباید بیشتر از ۵۰ مگابایت باشد!")
        return
    
    status_msg = bot.reply_to(message, "🔄 در حال پردازش فایل...")
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        file_path = save_uploaded_file(user_id, downloaded_file, file_name)
        if not file_path:
            bot.edit_message_text("❌ خطا در ذخیره فایل", message.chat.id, status_msg.message_id)
            return
        
        main_code = ""
        
        if file_name.endswith('.zip'):
            extract_dir = os.path.join(FILES_DIR, str(user_id), f"extract_{int(time.time())}")
            os.makedirs(extract_dir, exist_ok=True)
            
            py_files = extract_files_from_zip(file_path, extract_dir)
            for pf in py_files:
                if pf['name'] in ['bot.py', 'main.py', 'run.py', '__init__.py']:
                    main_code = pf['content']
                    break
            
            if not main_code and py_files:
                main_code = py_files[0]['content']
            
            shutil.rmtree(extract_dir, ignore_errors=True)
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                main_code = f.read()
        
        if not main_code:
            bot.edit_message_text("❌ هیچ فایل پایتونی پیدا نشد!", message.chat.id, status_msg.message_id)
            return
        
        # بررسی امنیت کد
        is_safe, errors = SecurityManager.validate_code(main_code)
        if not is_safe:
            bot.edit_message_text(
                f"❌ کد شما از نظر امنیتی مشکل دارد!\n\n⚠️ خطاها:\n" + "\n".join(errors),
                message.chat.id,
                status_msg.message_id
            )
            return
        
        token = extract_token_from_code(main_code)
        if not token:
            bot.edit_message_text("❌ توکن در کد پیدا نشد!", message.chat.id, status_msg.message_id)
            return
        
        # بررسی توکن
        try:
            response = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
            if response.status_code != 200:
                bot.edit_message_text("❌ توکن معتبر نیست!", message.chat.id, status_msg.message_id)
                return
            bot_info = response.json()['result']
            bot_name = bot_info['first_name']
            bot_username = bot_info['username']
        except Exception as e:
            bot.edit_message_text(f"❌ خطا در بررسی توکن: {str(e)}", message.chat.id, status_msg.message_id)
            return
        
        bot.edit_message_text("⚡ در حال اجرا در محیط ایزوله داکر...", message.chat.id, status_msg.message_id)
        
        # اجرا در داکر
        bot_id = hashlib.md5(f"{user_id}{token}{time.time()}".encode()).hexdigest()[:10]
        docker_mgr = DockerManager()
        result = docker_mgr.run_bot_in_docker(bot_id, main_code, token)
        
        if result['success']:
            add_bot_to_db(user_id, bot_id, token, bot_name, bot_username, file_path, result.get('container_id'))
            
            # اگر تست ۲۴ ساعته فعال است، ذخیره کن
            if SubscriptionManager.check_trial_active(user_id):
                SubscriptionManager.activate_trial(user_id, bot_id)
            
            reply = f"✅ ربات با موفقیت ساخته شد! 🎉\n\n"
            reply += f"🤖 نام: {bot_name}\n"
            reply += f"🔗 لینک: https://t.me/{bot_username}\n"
            reply += f"🆔 آیدی: {bot_id}\n"
            reply += f"🔄 وضعیت: در حال اجرا در داکر\n\n"
            
            if reason == 'trial':
                reply += f"⏰ **تست ۲۴ ساعته فعال است**\n"
                reply += f"⏳ بعد از ۲۴ ساعت ربات متوقف می‌شود\n"
                reply += f"💡 برای ادامه، اشتراک تهیه کنید"
            
            bot.edit_message_text(reply, message.chat.id, status_msg.message_id)
        else:
            bot.edit_message_text(f"❌ خطا در اجرا:\n{result.get('error', 'خطای ناشناخته')}", message.chat.id, status_msg.message_id)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        bot.edit_message_text(f"❌ خطا: {str(e)}", message.chat.id, status_msg.message_id)

# ==================== ربات‌های من ====================
@bot.message_handler(func=lambda m: m.text == '📋 ربات‌های من')
def my_bots(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما رباتی ندارید!\nبرای ساخت ربات از گزینه «ساخت ربات جدید» استفاده کنید")
        return
    
    for b in bots[:10]:
        status_emoji = "🟢" if b['status'] == 'running' else "🔴"
        status_text = "در حال اجرا" if b['status'] == 'running' else "متوقف"
        
        text = f"{status_emoji} **{b['name']}**\n"
        text += f"🔗 https://t.me/{b['username']}\n"
        text += f"🆔 `{b['id']}`\n"
        text += f"📊 وضعیت: {status_text}\n"
        text += f"📅 {b['created_at'][:10]}"
        
        bot.send_message(message.chat.id, text, parse_mode="Markdown")

# ==================== فعال/غیرفعال کردن ====================
@bot.message_handler(func=lambda m: m.text == '🔄 فعال/غیرفعال کردن')
def toggle_prompt(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما رباتی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        status = "🟢" if b['status'] == 'running' else "🔴"
        markup.add(types.InlineKeyboardButton(f"{status} {b['name']}", callback_data=f"toggle_{b['id']}"))
    
    bot.send_message(message.chat.id, "🔄 ربات مورد نظر را انتخاب کنید:", reply_markup=markup)

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
            DockerManager().stop_container(bot_id)
            conn.execute('UPDATE bots SET status = ? WHERE id = ?', ('stopped', bot_id))
            conn.commit()
            bot.answer_callback_query(call.id, "✅ ربات متوقف شد")
            bot.edit_message_text(f"✅ ربات {bot_info['name']} متوقف شد.", call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "❌ ربات در حال حاضر متوقف است")

# ==================== حذف ربات ====================
@bot.message_handler(func=lambda m: m.text == '🗑 حذف ربات')
def delete_prompt(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما رباتی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        markup.add(types.InlineKeyboardButton(f"🗑 {b['name']}", callback_data=f"delete_{b['id']}"))
    
    bot.send_message(message.chat.id, "⚠️ ربات مورد نظر را انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
def confirm_delete(call):
    bot_id = call.data.replace('delete_', '')
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ بله", callback_data=f"confirm_del_{bot_id}"),
        types.InlineKeyboardButton("❌ خیر", callback_data="cancel_del")
    )
    bot.edit_message_text("⚠️ آیا از حذف این ربات اطمینان دارید؟", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_del_'))
def do_delete(call):
    bot_id = call.data.replace('confirm_del_', '')
    user_id = call.from_user.id
    
    if delete_bot_from_db(bot_id, user_id):
        bot.edit_message_text("✅ ربات با موفقیت حذف شد.", call.message.chat.id, call.message.message_id)
    else:
        bot.edit_message_text("❌ خطا در حذف ربات!", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == 'cancel_del')
def cancel_delete(call):
    bot.edit_message_text("❌ عملیات حذف لغو شد.", call.message.chat.id, call.message.message_id)

# ==================== راهنما ====================
@bot.message_handler(func=lambda m: m.text == '📚 راهنما')
def guide(message):
    bot.send_message(message.chat.id, GUIDE_TEXT, parse_mode="Markdown")

# ==================== نصب کتابخانه ====================
@bot.message_handler(func=lambda m: m.text == '📦 نصب کتابخانه')
def install_library_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    libs = [
        ('requests', 'requests'), ('numpy', 'numpy'), ('pandas', 'pandas'),
        ('flask', 'flask'), ('pyTelegramBotAPI', 'pyTelegramBotAPI'),
        ('aiogram', 'aiogram'), ('jdatetime', 'jdatetime'), ('🔧 دستی', 'custom')
    ]
    for name, data in libs:
        markup.add(types.InlineKeyboardButton(name, callback_data=f"lib_{data}"))
    
    bot.send_message(message.chat.id, "📦 کتابخانه مورد نظر را انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lib_'))
def install_library_callback(call):
    lib = call.data.replace('lib_', '')
    
    if lib == 'custom':
        msg = bot.send_message(call.message.chat.id, "📦 نام کتابخانه را وارد کنید:")
        bot.register_next_step_handler(msg, install_custom_library)
        return
    
    bot.answer_callback_query(call.id, f"در حال نصب {lib}...")
    
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "install", lib], capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            bot.send_message(call.message.chat.id, f"✅ کتابخانه {lib} با موفقیت نصب شد.")
        else:
            bot.send_message(call.message.chat.id, f"❌ خطا در نصب:\n{result.stderr[:200]}")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ خطا: {str(e)}")

def install_custom_library(message):
    lib = message.text.strip()
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "install", lib], capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            bot.send_message(message.chat.id, f"✅ کتابخانه {lib} با موفقیت نصب شد.")
        else:
            bot.send_message(message.chat.id, f"❌ خطا در نصب:\n{result.stderr[:200]}")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطا: {str(e)}")

# ==================== آمار ====================
@bot.message_handler(func=lambda m: m.text == '📊 آمار')
def stats(message):
    try:
        with get_db() as conn:
            total_users = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
            total_bots = conn.execute('SELECT COUNT(*) FROM bots').fetchone()[0]
            running_bots = conn.execute('SELECT COUNT(*) FROM bots WHERE status = "running"').fetchone()[0]
            total_payments = conn.execute('SELECT COUNT(*) FROM receipts WHERE status = "approved"').fetchone()[0]
            total_withdraw = conn.execute('SELECT SUM(amount) FROM withdraw_requests WHERE status = "pending"').fetchone()[0] or 0
        
        text = f"📊 **آمار کلی**\n\n"
        text += f"👥 کل کاربران: {total_users}\n"
        text += f"🤖 کل ربات‌ها: {total_bots}\n"
        text += f"🟢 فعال: {running_bots}\n"
        text += f"💰 پرداخت‌ها: {total_payments}\n"
        text += f"💳 درخواست برداشت: {total_withdraw:,} تومان"
        
        bot.send_message(message.chat.id, text, parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, "📊 آمار در دسترس نیست")

# ==================== پشتیبانی ====================
@bot.message_handler(func=lambda m: m.text == '📞 پشتیبانی')
def support(message):
    bot.send_message(message.chat.id, "📞 **پشتیبانی:** @shahraghee13", parse_mode="Markdown")

# ==================== پنل ادمین کامل ====================
@bot.message_handler(func=lambda m: m.text == '👑 پنل ادمین')
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ شما دسترسی ادمین ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📸 فیش‌ها", callback_data="admin_receipts"),
        types.InlineKeyboardButton("👥 کاربران", callback_data="admin_users"),
        types.InlineKeyboardButton("📊 آمار کامل", callback_data="admin_stats"),
        types.InlineKeyboardButton("💰 تایید پرداخت", callback_data="admin_approve"),
        types.InlineKeyboardButton("💳 تغییر قیمت", callback_data="admin_change_price"),
        types.InlineKeyboardButton("🏧 تغییر شماره کارت", callback_data="admin_change_card"),
        types.InlineKeyboardButton("🖨 تغییر متن راهنما", callback_data="admin_change_guide"),
        types.InlineKeyboardButton("🖥 اضافه کردن سرور", callback_data="admin_add_server"),
        types.InlineKeyboardButton("🗑 حذف ربات کاربران", callback_data="admin_delete_user_bot"),
        types.InlineKeyboardButton("💰 لیست برداشت‌ها", callback_data="admin_withdraw_list"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    bot.send_message(message.chat.id, "👑 **پنل مدیریت پیشرفته**", parse_mode="Markdown", reply_markup=markup)

# ==================== هندلرهای پنل ادمین ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_receipts")
def admin_receipts(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        receipts = conn.execute('SELECT * FROM receipts WHERE status = "pending" ORDER BY created_at DESC').fetchall()
    
    if not receipts:
        bot.send_message(call.message.chat.id, "📸 هیچ فیش در انتظاری نیست")
        return
    
    for r in receipts:
        text = f"🆔 {r['id']}\n👤 {r['user_id']}\n💰 {r['amount']:,} تومان\n🆔 {r['payment_code']}"
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_receipt_{r['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"reject_receipt_{r['id']}")
        )
        
        if os.path.exists(r['receipt_path']):
            with open(r['receipt_path'], 'rb') as f:
                bot.send_photo(call.message.chat.id, f, caption=text, reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_receipt_'))
def approve_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    receipt_id = int(call.data.replace('approve_receipt_', ''))
    
    with get_db() as conn:
        receipt = conn.execute('SELECT * FROM receipts WHERE id = ?', (receipt_id,)).fetchone()
        if receipt:
            conn.execute('UPDATE receipts SET status = "approved", reviewed_at = ?, reviewed_by = ? WHERE id = ?',
                        (datetime.now().isoformat(), call.from_user.id, receipt_id))
            
            # فعال کردن اشتراک
            if receipt['amount'] == PRICE_PER_MONTH:
                SubscriptionManager.activate_subscription(receipt['user_id'], 'monthly', receipt['amount'])
            elif receipt['amount'] == PRICE_3_MONTHS:
                SubscriptionManager.activate_subscription(receipt['user_id'], '3months', receipt['amount'])
            
            # بررسی رفرال برای پورسانت
            user = conn.execute('SELECT referred_by FROM users WHERE user_id = ?', (receipt['user_id'],)).fetchone()
            if user and user['referred_by']:
                ReferralManager.process_purchase_commission(user['referred_by'], receipt['amount'])
                conn.execute('UPDATE users SET verified_referrals = verified_referrals + 1 WHERE user_id = ?', (user['referred_by'],))
            
            conn.commit()
            
            try:
                bot.send_message(receipt['user_id'], f"✅ اشتراک شما فعال شد!\n💰 مبلغ: {receipt['amount']:,} تومان\n🎉 می‌توانید ربات خود را بسازید.")
            except:
                pass
    
    bot.answer_callback_query(call.id, "✅ تایید شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_receipt_'))
def reject_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    receipt_id = int(call.data.replace('reject_receipt_', ''))
    
    with get_db() as conn:
        receipt = conn.execute('SELECT * FROM receipts WHERE id = ?', (receipt_id,)).fetchone()
        if receipt:
            conn.execute('UPDATE receipts SET status = "rejected", reviewed_at = ?, reviewed_by = ? WHERE id = ?',
                        (datetime.now().isoformat(), call.from_user.id, receipt_id))
            conn.commit()
            
            try:
                bot.send_message(receipt['user_id'], f"❌ فیش شما رد شد. لطفاً با پشتیبانی تماس بگیرید: @shahraghee13")
            except:
                pass
    
    bot.answer_callback_query(call.id, "❌ رد شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_change_price")
def admin_change_price(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "💰 قیمت جدید ماهانه را وارد کنید (تومان):\nمثال: 2500000")
    bot.register_next_step_handler(msg, process_price_change)

def process_price_change(message):
    global PRICE_PER_MONTH, PRICE_3_MONTHS
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        new_price = int(message.text.strip())
        PRICE_PER_MONTH = new_price
        PRICE_3_MONTHS = int(new_price * 2.5)
        bot.reply_to(message, f"✅ قیمت با موفقیت تغییر کرد!\nماهانه: {PRICE_PER_MONTH:,} تومان\nسه ماهه: {PRICE_3_MONTHS:,} تومان")
    except:
        bot.reply_to(message, "❌ عدد معتبر وارد کنید!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_change_card")
def admin_change_card(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "🏧 شماره کارت جدید را وارد کنید:")
    bot.register_next_step_handler(msg, process_card_change)

def process_card_change(message):
    global CARD_NUMBER
    if message.from_user.id not in ADMIN_IDS:
        return
    
    CARD_NUMBER = message.text.strip()
    bot.reply_to(message, f"✅ شماره کارت با موفقیت تغییر کرد:\n{CARD_NUMBER}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_change_guide")
def admin_change_guide(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "📝 متن جدید راهنما را ارسال کنید:")
    bot.register_next_step_handler(msg, process_guide_change)

def process_guide_change(message):
    global GUIDE_TEXT
    if message.from_user.id not in ADMIN_IDS:
        return
    
    GUIDE_TEXT = message.text
    bot.reply_to(message, "✅ متن راهنما با موفقیت تغییر کرد!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_add_server")
def admin_add_server(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "🖥 **اضافه کردن سرور جدید**\n\nلطفاً اطلاعات را به صورت زیر وارد کنید:\n\n`نام|آیپی|یوزرنیم|رمز|حداکثر ربات`\n\nمثال:\n`server1|192.168.1.100|root|password123|1000`", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_add_server)

def process_add_server(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        parts = message.text.split('|')
        if len(parts) < 5:
            bot.reply_to(message, "❌ فرمت صحیح نیست!")
            return
        
        name = parts[0].strip()
        ip = parts[1].strip()
        ssh_user = parts[2].strip()
        ssh_password = parts[3].strip()
        max_bots = int(parts[4].strip())
        
        server_mgr = ServerManager()
        result = server_mgr.add_server(name, ip, ssh_user, ssh_password, max_bots)
        
        if result['success']:
            bot.reply_to(message, f"✅ سرور {name} با موفقیت اضافه شد!")
        else:
            bot.reply_to(message, f"❌ خطا: {result['error']}")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_delete_user_bot")
def admin_delete_user_bot(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        bots = conn.execute('SELECT b.id, b.name, b.username, u.user_id, u.first_name FROM bots b JOIN users u ON b.user_id = u.user_id').fetchall()
    
    if not bots:
        bot.send_message(call.message.chat.id, "📋 هیچ رباتی وجود ندارد")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        markup.add(types.InlineKeyboardButton(f"🗑 {b['name']} (کاربر: {b['first_name']})", callback_data=f"admin_del_bot_{b['id']}"))
    
    bot.send_message(call.message.chat.id, "🗑 ربات مورد نظر برای حذف را انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_del_bot_'))
def admin_confirm_delete_bot(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    bot_id = call.data.replace('admin_del_bot_', '')
    
    with get_db() as conn:
        bot_info = conn.execute('SELECT * FROM bots WHERE id = ?', (bot_id,)).fetchone()
        if bot_info:
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("✅ بله", callback_data=f"admin_confirm_del_{bot_id}"),
                types.InlineKeyboardButton("❌ خیر", callback_data="admin_cancel_del")
            )
            bot.edit_message_text(f"⚠️ آیا از حذف ربات {bot_info['name']} (کاربر: {bot_info['user_id']}) اطمینان دارید؟",
                                 call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_confirm_del_'))
def admin_do_delete_bot(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    bot_id = call.data.replace('admin_confirm_del_', '')
    
    with get_db() as conn:
        bot_info = conn.execute('SELECT user_id FROM bots WHERE id = ?', (bot_id,)).fetchone()
        if bot_info:
            DockerManager().stop_container(bot_id)
            conn.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
            conn.execute('UPDATE users SET bots_count = bots_count - 1 WHERE user_id = ?', (bot_info['user_id'],))
            conn.commit()
    
    bot.edit_message_text("✅ ربات با موفقیت حذف شد.", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_withdraw_list")
def admin_withdraw_list(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        withdraws = conn.execute('SELECT * FROM withdraw_requests WHERE status = "pending" ORDER BY created_at DESC').fetchall()
    
    if not withdraws:
        bot.send_message(call.message.chat.id, "💰 هیچ درخواست برداشتی وجود ندارد")
        return
    
    for w in withdraws:
        text = f"💰 درخواست برداشت\n"
        text += f"👤 کاربر: {w['user_id']}\n"
        text += f"💰 مبلغ: {w['amount']:,} تومان\n"
        text += f"💳 کارت: {w['card_number']}\n"
        text += f"📅 تاریخ: {w['created_at'][:19]}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ پرداخت شد", callback_data=f"withdraw_done_{w['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"withdraw_reject_{w['id']}")
        )
        
        bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('withdraw_done_'))
def withdraw_done(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    withdraw_id = int(call.data.replace('withdraw_done_', ''))
    
    with get_db() as conn:
        conn.execute('UPDATE withdraw_requests SET status = "completed", processed_at = ? WHERE id = ?',
                    (datetime.now().isoformat(), withdraw_id))
        conn.commit()
    
    bot.answer_callback_query(call.id, "✅ ثبت شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('withdraw_reject_'))
def withdraw_reject(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    withdraw_id = int(call.data.replace('withdraw_reject_', ''))
    
    with get_db() as conn:
        withdraw = conn.execute('SELECT * FROM withdraw_requests WHERE id = ?', (withdraw_id,)).fetchone()
        if withdraw:
            conn.execute('UPDATE withdraw_requests SET status = "rejected", processed_at = ? WHERE id = ?',
                        (datetime.now().isoformat(), withdraw_id))
            conn.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (withdraw['amount'], withdraw['user_id']))
            conn.commit()
            
            try:
                bot.send_message(withdraw['user_id'], f"❌ درخواست برداشت شما رد شد. مبلغ {withdraw['amount']:,} تومان به کیف پول شما بازگردانده شد.")
            except:
                pass
    
    bot.answer_callback_query(call.id, "❌ رد شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_stats(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        total_users = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        total_bots = conn.execute('SELECT COUNT(*) FROM bots').fetchone()[0]
        running_bots = conn.execute('SELECT COUNT(*) FROM bots WHERE status = "running"').fetchone()[0]
        total_receipts = conn.execute('SELECT COUNT(*) FROM receipts').fetchone()[0]
        pending = conn.execute('SELECT COUNT(*) FROM receipts WHERE status = "pending"').fetchone()[0]
        approved = conn.execute('SELECT COUNT(*) FROM receipts WHERE status = "approved"').fetchone()[0]
        total_amount = conn.execute('SELECT SUM(amount) FROM receipts WHERE status = "approved"').fetchone()[0] or 0
        paid_users = conn.execute('SELECT COUNT(*) FROM users WHERE payment_status = "approved"').fetchone()[0]
        total_withdraw_pending = conn.execute('SELECT SUM(amount) FROM withdraw_requests WHERE status = "pending"').fetchone()[0] or 0
        total_balance = conn.execute('SELECT SUM(balance) FROM users').fetchone()[0] or 0
    
    text = f"📊 **آمار کامل سیستم**\n\n"
    text += f"👥 کل کاربران: {total_users}\n"
    text += f"✅ پرداخت کرده: {paid_users}\n"
    text += f"🤖 کل ربات‌ها: {total_bots}\n"
    text += f"🟢 فعال: {running_bots}\n"
    text += f"📸 کل فیش‌ها: {total_receipts}\n"
    text += f"⏳ در انتظار: {pending}\n"
    text += f"✅ تایید شده: {approved}\n"
    text += f"💰 مجموع واریزی: {total_amount:,} تومان\n"
    text += f"💳 درخواست برداشت: {total_withdraw_pending:,} تومان\n"
    text += f"🏦 مجموع موجودی کاربران: {total_balance:,} تومان"
    
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_users")
def admin_users(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        users = conn.execute('''
            SELECT user_id, username, first_name, bots_count, verified_referrals, 
                   payment_status, balance, created_at
            FROM users ORDER BY created_at DESC LIMIT 20
        ''').fetchall()
    
    text = "👥 **۲۰ کاربر آخر:**\n\n"
    for u in users:
        payment = "✅" if u['payment_status'] == 'approved' else "⏳"
        text += f"{payment} {u['user_id']} - {u['first_name']}\n"
        text += f"   🤖 {u['bots_count']} ربات | 🎁 {u['verified_referrals']} رفرال | 💰 {u['balance']:,} تومان\n\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_approve")
def admin_approve_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "💰 آیدی کاربر را وارد کنید:")
    bot.register_next_step_handler(msg, process_admin_approve)

def process_admin_approve(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        user_id = int(message.text.strip())
        with get_db() as conn:
            conn.execute('UPDATE users SET payment_status = "approved", payment_date = ? WHERE user_id = ?',
                        (datetime.now().isoformat(), user_id))
            conn.commit()
        
        bot.reply_to(message, f"✅ پرداخت کاربر {user_id} تایید شد")
        try:
            bot.send_message(user_id, f"✅ پرداخت شما تایید شد!\nاکنون می‌توانید ربات بسازید.")
        except:
            pass
    except:
        bot.reply_to(message, "❌ آیدی باید عدد باشد")

@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call):
    user_id = call.from_user.id
    is_admin = user_id in ADMIN_IDS
    markup = get_main_menu(is_admin)
    
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "🚀 منوی اصلی:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_cancel_del")
def admin_cancel_del(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== مانیتورینگ ====================
def monitor_trials():
    """بررسی دوره‌ای تست‌های ۲۴ ساعته"""
    while True:
        try:
            with get_db() as conn:
                trials = conn.execute('SELECT user_id, bot_id FROM trial_usage WHERE is_active = 1').fetchall()
                for trial in trials:
                    if not SubscriptionManager.check_trial_active(trial['user_id']):
                        # تست تمام شده، ربات را متوقف کن
                        if trial['bot_id']:
                            DockerManager().stop_container(trial['bot_id'])
                            conn.execute('UPDATE bots SET status = "stopped" WHERE id = ?', (trial['bot_id'],))
                        logger.info(f"تست ۲۴ ساعته کاربر {trial['user_id']} به پایان رسید")
            
            time.sleep(3600)  # هر یک ساعت چک کن
        except Exception as e:
            logger.error(f"خطا در مانیتورینگ تست‌ها: {e}")
            time.sleep(60)

# شروع تردهای مانیتورینگ
monitor_thread = threading.Thread(target=monitor_trials, daemon=True)
monitor_thread.start()

# ==================== اجرا ====================
if __name__ == "__main__":
    print("=" * 70)
    print("🚀 ربات مادر نهایی - نسخه 9.0 با ایزوله‌سازی داکر و سیستم اشتراک")
    print("=" * 70)
    print(f"✅ داکر: {'فعال' if DOCKER_AVAILABLE else 'غیرفعال'}")
    print(f"✅ ردیس: {'فعال' if REDIS_AVAILABLE else 'غیرفعال'}")
    print(f"✅ ادمین: {ADMIN_IDS}")
    print(f"✅ قیمت ماهانه: {PRICE_PER_MONTH:,} تومان")
    print(f"✅ قیمت سه ماهه: {PRICE_3_MONTHS:,} تومان")
    print(f"✅ حداقل برداشت: {MIN_WITHDRAW_AMOUNT:,} تومان")
    print("=" * 70)
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            logger.error(f"خطا: {e}")
            time.sleep(5)