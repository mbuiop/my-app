#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ربات مادر نهایی - نسخه نهایی 14.0
با قابلیت نصب خودکار کتابخانه‌ها
"""

import subprocess
import sys
import os

# ==================== نصب خودکار کتابخانه‌های مورد نیاز ====================
def install_required_packages():
    """نصب خودکار تمام کتابخانه‌های مورد نیاز"""
    
    required_packages = [
        'pyTelegramBotAPI>=4.8.0',
        'requests>=2.28.0',
        'psutil>=5.9.0',
        'docker>=6.0.0',
        'paramiko>=3.0.0',
        'redis>=4.5.0',
        'aiohttp>=3.8.0',
        'sqlalchemy>=2.0.0',
        'cryptography>=41.0.0',
        'python-dotenv>=1.0.0',
        'loguru>=0.7.0',
        'coloredlogs>=15.0.0',
        'rich>=13.0.0',
        'schedule>=1.2.0',
        'pytz>=2023.0',
        'jdatetime>=4.0.0',
        'beautifulsoup4>=4.12.0',
        'lxml>=4.9.0',
        'pillow>=10.0.0',
        'qrcode>=7.4.0',
        'selenium>=4.15.0',
        'playwright>=1.40.0',
        'flask>=3.0.0',
        'fastapi>=0.104.0',
        'uvicorn>=0.24.0',
        'gunicorn>=21.2.0',
        'jinja2>=3.1.0',
        'pymongo>=4.5.0',
        'motor>=3.3.0',
        'elasticsearch>=8.11.0',
        'pydantic>=2.5.0',
        'click>=8.1.0',
        'typer>=0.9.0',
        'colorama>=0.4.6',
        'tqdm>=4.66.0',
        'pyyaml>=6.0.0',
        'toml>=0.10.2',
        'json5>=0.9.0',
        'httpx>=0.25.0',
        'websockets>=12.0',
        'python-socketio>=5.10.0',
        'celery>=5.3.0',
        'pika>=1.3.0',
        'confluent-kafka>=2.3.0',
        'prometheus-client>=0.19.0',
        'sentry-sdk>=1.38.0',
        'newrelic>=9.0.0',
        'datadog>=0.48.0',
        'boto3>=1.34.0',
        'openai>=1.3.0',
        'anthropic>=0.7.0',
        'huggingface-hub>=0.20.0',
        'torch>=2.1.0',
        'tensorflow>=2.14.0',
        'numpy>=1.24.0',
        'pandas>=2.1.0',
        'matplotlib>=3.8.0',
        'seaborn>=0.13.0',
        'plotly>=5.18.0'
    ]
    
    print("=" * 70)
    print("🔧 بررسی و نصب کتابخانه‌های مورد نیاز...")
    print("=" * 70)
    
    installed = []
    failed = []
    
    for package in required_packages:
        print(f"📦 در حال نصب {package}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "--upgrade", package])
            installed.append(package)
            print(f"   ✅ {package} نصب شد")
        except Exception as e:
            failed.append(package)
            print(f"   ❌ خطا در نصب {package}: {e}")
    
    print("=" * 70)
    print(f"✅ نصب شدند: {len(installed)} کتابخانه")
    print(f"❌ ناموفق: {len(failed)} کتابخانه")
    print("=" * 70)
    
    if failed:
        print("⚠️ کتابخانه‌های زیر نصب نشدند (ممکن است نیاز به نصب دستی داشته باشند):")
        for f in failed:
            print(f"   - {f}")

# اجرای نصب خودکار
try:
    install_required_packages()
except Exception as e:
    print(f"⚠️ خطا در نصب خودکار: {e}")
    print("ادامه می‌دهیم با کتابخانه‌های موجود...")

# ==================== ادامه کد اصلی ربات ====================

import telebot
from telebot import types
import sqlite3
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
import random

# تلاش برای import کتابخانه‌های اختیاری
try:
    import psutil
    PSUTIL_AVAILABLE = True
except:
    PSUTIL_AVAILABLE = False

try:
    import docker
    DOCKER_AVAILABLE = True
except:
    DOCKER_AVAILABLE = False

try:
    import redis
    REDIS_AVAILABLE = True
except:
    REDIS_AVAILABLE = False

try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except:
    CRYPTO_AVAILABLE = False

# ==================== تنظیمات پایه ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "database")
FILES_DIR = os.path.join(BASE_DIR, "user_files")
RUNNING_DIR = os.path.join(BASE_DIR, "running_bots")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
RECEIPTS_DIR = os.path.join(BASE_DIR, "receipts")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
TEMP_DIR = os.path.join(BASE_DIR, "temp")

for d in [DB_DIR, FILES_DIR, RUNNING_DIR, LOGS_DIR, RECEIPTS_DIR, BACKUP_DIR, TEMP_DIR]:
    os.makedirs(d, exist_ok=True)

# ==================== توکن ربات مادر ====================
BOT_TOKEN = "7685135237:AAEmsHktRw9cEqrHTkCoPZk-fBimK7TDjOo"
bot = telebot.TeleBot(BOT_TOKEN)
bot.delete_webhook()

# ==================== تنظیمات متغیر ====================
ADMIN_IDS = [327855654]
CARD_NUMBER = "5892101187322777"
CARD_HOLDER = "مرتضی نیکخو خنجری"
PRICE_PER_MONTH = 2000000
PRICE_3_MONTHS = 5000000
PRICE_6_MONTHS = 9000000
PRICE_12_MONTHS = 15000000
MIN_WITHDRAW_AMOUNT = 2000000
REFERRAL_COMMISSION_PERCENT = 7
TRIAL_HOURS = 24
MAX_FILE_SIZE = 50 * 1024 * 1024

GUIDE_TEXT = """📚 راهنمای کامل ربات مادر نهایی

1️⃣ ساخت ربات:
   • ابتدا اشتراک خود را فعال کنید یا از تست 24 ساعته استفاده کنید
   • فایل .py یا .zip خود را آپلود کنید
   • توکن ربات باید داخل کد باشد

2️⃣ انواع اشتراک:
   • ماهانه: 2,000,000 تومان
   • سه ماهه: 5,000,000 تومان
   • شش ماهه: 9,000,000 تومان
   • یکساله: 15,000,000 تومان
   • تست رايگان: 24 ساعت (فقط یک بار)

3️⃣ سیستم رفرال:
   • هر نفر 7 درصد پورسانت خرید
   • پورسانت تا 3 سطح
   • لینک اختصاصی خود را به اشتراک بگذارید

4️⃣ برداشت وجه:
   • حداقل مبلغ برداشت: 2,000,000 تومان
   • از طریق بخش برداشت اقدام کنید

5️⃣ پشتیبانی:
   • @shahraghee13
"""

# ==================== لاگینگ ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(os.path.join(LOGS_DIR, 'mother_bot.log'), maxBytes=10485760, backupCount=10),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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
    
    conn.execute('''
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
            last_active TIMESTAMP
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            plan_type TEXT,
            receipt_path TEXT,
            status TEXT DEFAULT 'pending',
            payment_code TEXT UNIQUE,
            created_at TIMESTAMP,
            reviewed_at TIMESTAMP,
            reviewed_by INTEGER
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            plan_type TEXT,
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            is_active INTEGER DEFAULT 1,
            paid_amount INTEGER,
            created_at TIMESTAMP
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS trial_usage (
            user_id INTEGER PRIMARY KEY,
            start_time TIMESTAMP,
            bot_id TEXT,
            is_active INTEGER DEFAULT 1,
            used_before INTEGER DEFAULT 0
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS commissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            reason TEXT,
            from_user_id INTEGER,
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
            created_at TIMESTAMP,
            processed_at TIMESTAMP
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            message TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP
        )
    ''')
    
    conn.commit()

# ==================== کلاس‌های اصلی ====================

class BotRunner:
    @staticmethod
    def run_bot(bot_id, code, token):
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
                return {'success': True, 'pid': process.pid}
            else:
                with open(log_file, 'r') as f:
                    error = f.read()[-500:]
                return {'success': False, 'error': error}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def stop_bot(bot_id):
        try:
            with get_db() as conn:
                bot_info = conn.execute('SELECT pid FROM bots WHERE id = ?', (bot_id,)).fetchone()
                if bot_info and bot_info['pid']:
                    os.kill(bot_info['pid'], signal.SIGTERM)
                    return True
        except:
            pass
        return False

class SubscriptionManager:
    @staticmethod
    def has_active_subscription(user_id):
        with get_db() as conn:
            row = conn.execute('SELECT end_date FROM subscriptions WHERE user_id = ? AND is_active = 1 AND end_date > datetime("now")', (user_id,)).fetchone()
            return row is not None
    
    @staticmethod
    def get_subscription_info(user_id):
        with get_db() as conn:
            row = conn.execute('SELECT plan_type, start_date, end_date, paid_amount FROM subscriptions WHERE user_id = ? AND is_active = 1 AND end_date > datetime("now") ORDER BY end_date DESC LIMIT 1', (user_id,)).fetchone()
            return dict(row) if row else None
    
    @staticmethod
    def activate_subscription(user_id, plan_type, paid_amount):
        now = datetime.now()
        if plan_type == 'monthly':
            end_date = now + timedelta(days=30)
            max_bots = 5
        elif plan_type == '3months':
            end_date = now + timedelta(days=90)
            max_bots = 15
        elif plan_type == '6months':
            end_date = now + timedelta(days=180)
            max_bots = 35
        elif plan_type == '12months':
            end_date = now + timedelta(days=365)
            max_bots = 100
        else:
            return False
        
        with get_db() as conn:
            conn.execute('UPDATE subscriptions SET is_active = 0 WHERE user_id = ?', (user_id,))
            conn.execute('INSERT INTO subscriptions (user_id, plan_type, start_date, end_date, is_active, paid_amount, created_at) VALUES (?, ?, ?, ?, 1, ?, ?)', (user_id, plan_type, now.isoformat(), end_date.isoformat(), paid_amount, now.isoformat()))
            conn.execute('UPDATE users SET payment_status = ?, payment_date = ?, max_bots = ? WHERE user_id = ?', ('approved', now.isoformat(), max_bots, user_id))
            conn.commit()
            return True
    
    @staticmethod
    def can_use_trial(user_id):
        with get_db() as conn:
            row = conn.execute('SELECT used_before FROM trial_usage WHERE user_id = ?', (user_id,)).fetchone()
            if row and row['used_before'] == 1:
                return False, "شما قبلاً از تست 24 ساعته استفاده کرده اید"
            return True, "می توانید استفاده کنید"
    
    @staticmethod
    def activate_trial(user_id):
        with get_db() as conn:
            now = datetime.now()
            conn.execute('INSERT OR REPLACE INTO trial_usage (user_id, start_time, is_active, used_before, created_at) VALUES (?, ?, 1, 1, ?)', (user_id, now.isoformat(), now.isoformat()))
            conn.execute('UPDATE users SET max_bots = 1 WHERE user_id = ?', (user_id,))
            conn.commit()
            return True
    
    @staticmethod
    def is_trial_active(user_id):
        with get_db() as conn:
            row = conn.execute('SELECT start_time FROM trial_usage WHERE user_id = ? AND is_active = 1', (user_id,)).fetchone()
            if not row:
                return False
            start_time = datetime.fromisoformat(row['start_time'])
            if datetime.now() - start_time > timedelta(hours=TRIAL_HOURS):
                conn.execute('UPDATE trial_usage SET is_active = 0 WHERE user_id = ?', (user_id,))
                conn.commit()
                return False
            return True
    
    @staticmethod
    def get_trial_remaining(user_id):
        with get_db() as conn:
            row = conn.execute('SELECT start_time FROM trial_usage WHERE user_id = ? AND is_active = 1', (user_id,)).fetchone()
            if not row:
                return 0
            start_time = datetime.fromisoformat(row['start_time'])
            elapsed = datetime.now() - start_time
            remaining = timedelta(hours=TRIAL_HOURS) - elapsed
            return max(0, int(remaining.total_seconds() / 3600))
    
    @staticmethod
    def can_create_bot(user_id):
        if SubscriptionManager.has_active_subscription(user_id):
            return True, 'subscription'
        if SubscriptionManager.is_trial_active(user_id):
            return True, 'trial'
        return False, None
    
    @staticmethod
    def get_available_bots_count(user_id):
        if SubscriptionManager.has_active_subscription(user_id):
            info = SubscriptionManager.get_subscription_info(user_id)
            if info:
                plan = info['plan_type']
                plans = {'monthly': 5, '3months': 15, '6months': 35, '12months': 100}
                return plans.get(plan, 5)
        if SubscriptionManager.is_trial_active(user_id):
            return 1
        return 0

class ReferralManager:
    @staticmethod
    def generate_referral_code(user_id):
        return hashlib.md5(f"{user_id}_{time.time()}_{random.randint(1000,9999)}".encode()).hexdigest()[:8]
    
    @staticmethod
    def get_referral_link(user_id):
        with get_db() as conn:
            user = conn.execute('SELECT referral_code FROM users WHERE user_id = ?', (user_id,)).fetchone()
            if user:
                bot_username = bot.get_me().username
                return f"https://t.me/{bot_username}?start={user['referral_code']}"
        return None
    
    @staticmethod
    def get_referral_stats(user_id):
        with get_db() as conn:
            total_clicks = conn.execute('SELECT COUNT(*) FROM users WHERE referred_by = ?', (user_id,)).fetchone()[0]
            verified = conn.execute('SELECT COUNT(*) FROM users WHERE referred_by = ? AND payment_status = "approved"', (user_id,)).fetchone()[0]
            total_commission = conn.execute('SELECT SUM(amount) FROM commissions WHERE user_id = ?', (user_id,)).fetchone()[0] or 0
            return {'total_clicks': total_clicks, 'verified': verified, 'total_commission': total_commission}
    
    @staticmethod
    def process_purchase_commission(buyer_id, paid_amount):
        with get_db() as conn:
            buyer = conn.execute('SELECT referred_by FROM users WHERE user_id = ?', (buyer_id,)).fetchone()
            if buyer and buyer['referred_by']:
                referrer_id = buyer['referred_by']
                commission = int(paid_amount * REFERRAL_COMMISSION_PERCENT / 100)
                if commission > 0:
                    conn.execute('INSERT INTO commissions (user_id, amount, reason, from_user_id, created_at) VALUES (?, ?, ?, ?, ?)', (referrer_id, commission, f"پورسانت {REFERRAL_COMMISSION_PERCENT} درصد از خرید کاربر {buyer_id}", buyer_id, datetime.now().isoformat()))
                    conn.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (commission, referrer_id))
                    conn.execute('UPDATE users SET verified_referrals = verified_referrals + 1 WHERE user_id = ?', (referrer_id,))
                    conn.commit()
                    try:
                        bot.send_message(referrer_id, f"🎉 {commission:,} تومان پورسانت به کیف پول شما اضافه شد!\n\n👤 خریدار: {buyer_id}\n💰 مبلغ خرید: {paid_amount:,} تومان\n📊 درصد: {REFERRAL_COMMISSION_PERCENT}%")
                    except:
                        pass
                    return commission
        return 0
    
    @staticmethod
    def get_balance(user_id):
        with get_db() as conn:
            user = conn.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,)).fetchone()
            return user['balance'] if user else 0

class WithdrawManager:
    @staticmethod
    def request_withdraw(user_id, amount, card_number):
        if amount < MIN_WITHDRAW_AMOUNT:
            return False, f"حداقل مبلغ برداشت {MIN_WITHDRAW_AMOUNT:,} تومان است"
        
        with get_db() as conn:
            balance = conn.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,)).fetchone()
            if not balance or balance['balance'] < amount:
                return False, "موجودی کیف پول کافی نیست"
            
            conn.execute('INSERT INTO withdraw_requests (user_id, amount, card_number, created_at) VALUES (?, ?, ?, ?)', (user_id, amount, card_number, datetime.now().isoformat()))
            conn.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (amount, user_id))
            conn.commit()
            
            for admin_id in ADMIN_IDS:
                try:
                    bot.send_message(admin_id, f"💰 درخواست برداشت جدید\n\n👤 کاربر: {user_id}\n💰 مبلغ: {amount:,} تومان\n💳 کارت: {card_number}")
                except:
                    pass
            
            return True, "درخواست برداشت ثبت شد. پس از بررسی، مبلغ به کارت شما واریز می شود."
    
    @staticmethod
    def get_withdraw_requests(status='pending'):
        with get_db() as conn:
            rows = conn.execute('SELECT * FROM withdraw_requests WHERE status = ? ORDER BY created_at DESC', (status,)).fetchall()
            return [dict(row) for row in rows]
    
    @staticmethod
    def process_withdraw(request_id, action):
        with get_db() as conn:
            request = conn.execute('SELECT * FROM withdraw_requests WHERE id = ?', (request_id,)).fetchone()
            if not request:
                return False, "درخواست یافت نشد"
            
            if action == 'approve':
                conn.execute('UPDATE withdraw_requests SET status = "approved", processed_at = ? WHERE id = ?', (datetime.now().isoformat(), request_id))
                try:
                    bot.send_message(request['user_id'], f"✅ درخواست برداشت شما تایید شد!\n\n💰 مبلغ: {request['amount']:,} تومان\n💳 به کارت {request['card_number']} واریز شد.")
                except:
                    pass
            elif action == 'reject':
                conn.execute('UPDATE withdraw_requests SET status = "rejected", processed_at = ? WHERE id = ?', (datetime.now().isoformat(), request_id))
                conn.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (request['amount'], request['user_id']))
                try:
                    bot.send_message(request['user_id'], f"❌ درخواست برداشت شما رد شد.\n\n💰 مبلغ {request['amount']:,} تومان به کیف پول شما برگشت.")
                except:
                    pass
            conn.commit()
            return True, "عملیات با موفقیت انجام شد"

# ==================== توابع کمکی ====================

def create_user(user_id, username, first_name, last_name, referred_by=None):
    try:
        now = datetime.now().isoformat()
        referral_code = ReferralManager.generate_referral_code(user_id)
        with get_db() as conn:
            conn.execute('INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, referral_code, referred_by, created_at, last_active, payment_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', (user_id, username, first_name, last_name, referral_code, referred_by, now, now, 'pending'))
            conn.execute('UPDATE users SET last_active = ? WHERE user_id = ?', (now, user_id))
            if referred_by:
                conn.execute('UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = ?', (referred_by,))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"خطا در create_user: {e}")
        return False

def get_user(user_id):
    try:
        with get_db() as conn:
            user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
            return dict(user) if user else None
    except:
        return None

def extract_token_from_code(code):
    patterns = [
        r'token\s*=\s*["\']([^"\']+)["\']',
        r'TOKEN\s*=\s*["\']([^"\']+)["\']',
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

def add_bot_to_db(user_id, bot_id, token, name, username, file_path, pid=None):
    try:
        now = datetime.now().isoformat()
        with get_db() as conn:
            conn.execute('INSERT INTO bots (id, user_id, token, name, username, file_path, pid, status, created_at, last_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (bot_id, user_id, token, name, username, file_path, pid, 'running', now, now))
            conn.execute('UPDATE users SET bots_count = bots_count + 1, last_active = ? WHERE user_id = ?', (now, user_id))
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

def update_bot_status(bot_id, status):
    try:
        with get_db() as conn:
            conn.execute('UPDATE bots SET status = ?, last_active = ? WHERE id = ?', (status, datetime.now().isoformat(), bot_id))
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
            BotRunner.stop_bot(bot_id)
            if bot['file_path'] and os.path.exists(bot['file_path']):
                os.remove(bot['file_path'])
            bot_dir = os.path.join(RUNNING_DIR, bot_id)
            if os.path.exists(bot_dir):
                shutil.rmtree(bot_dir, ignore_errors=True)
            conn.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
            conn.execute('UPDATE users SET bots_count = bots_count - 1 WHERE user_id = ?', (user_id,))
            conn.commit()
            return True
    except:
        return False

def add_notification(user_id, title, message):
    with get_db() as conn:
        conn.execute('INSERT INTO notifications (user_id, title, message, created_at) VALUES (?, ?, ?, ?)', (user_id, title, message, datetime.now().isoformat()))
        conn.commit()

def security_check_code(code):
    dangerous = ['os.system', 'subprocess', 'eval(', 'exec(', '__import__', 'open(']
    errors = []
    for item in dangerous:
        if item in code.lower():
            errors.append(f"کد خطرناک: {item}")
    return len(errors) == 0, errors

# ==================== منوی اصلی ====================
def get_main_menu(is_admin=False):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        types.KeyboardButton('🤖 ساخت ربات جدید'),
        types.KeyboardButton('📋 ربات‌های من'),
        types.KeyboardButton('🔄 فعال/غیرفعال کردن'),
        types.KeyboardButton('🗑 حذف ربات'),
        types.KeyboardButton('💰 کیف پول و رفرال'),
        types.KeyboardButton('🎁 اشتراک و تست 24 ساعته'),
        types.KeyboardButton('💳 برداشت وجه'),
        types.KeyboardButton('📚 راهنما'),
        types.KeyboardButton('📦 نصب کتابخانه'),
        types.KeyboardButton('📊 آمار'),
        types.KeyboardButton('📞 پشتیبانی'),
        types.KeyboardButton('🎁 جایزه روزانه')
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
                        bot.send_message(referred_by, f"🎉 یک نفر با لینک رفرال شما وارد شد!\n\n👤 {first_name}\n🆔 {user_id}")
                    except:
                        pass
        except:
            pass
    
    create_user(user_id, username, first_name, last_name, referred_by)
    user = get_user(user_id)
    referral_link = ReferralManager.get_referral_link(user_id)
    balance = ReferralManager.get_balance(user_id)
    stats = ReferralManager.get_referral_stats(user_id)
    is_admin = user_id in ADMIN_IDS
    markup = get_main_menu(is_admin)
    
    has_sub = SubscriptionManager.has_active_subscription(user_id)
    sub_info = SubscriptionManager.get_subscription_info(user_id) if has_sub else None
    trial_active = SubscriptionManager.is_trial_active(user_id)
    trial_remaining = SubscriptionManager.get_trial_remaining(user_id) if trial_active else 0
    
    welcome_text = (
        f"🚀 **به ربات مادر نهایی خوش آمدید {first_name}!**\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **اطلاعات کاربری**\n"
        f"└ آیدی: `{user_id}`\n\n"
        f"💰 **کیف پول**\n"
        f"└ موجودی: {balance:,} تومان\n\n"
        f"🎁 **سیستم رفرال**\n"
        f"└ لینک دعوت: {referral_link}\n"
        f"└ کلیک‌ها: {stats['total_clicks']}\n"
        f"└ خریدهای موفق: {stats['verified']}\n\n"
    )
    
    if has_sub and sub_info:
        end_date = datetime.fromisoformat(sub_info['end_date'])
        days_left = (end_date - datetime.now()).days
        welcome_text += f"└ ✅ اشتراک فعال: {sub_info['plan_type']}\n└ 📅 انقضا: {end_date.strftime('%Y-%m-%d')}\n└ ⏳ روزهای باقیمانده: {days_left}\n\n"
    elif trial_active:
        welcome_text += f"└ 🎁 تست ۲۴ ساعته فعال\n└ ⏰ ساعت باقیمانده: {trial_remaining}\n\n"
    else:
        welcome_text += f"└ ❌ بدون اشتراک فعال\n\n"
    
    welcome_text += (
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 هر خرید از لینک شما = {REFERRAL_COMMISSION_PERCENT}% پورسانت\n"
        f"🎁 تست ۲۴ ساعته رایگان (فقط یک بار)\n"
        f"💳 حداقل برداشت: {MIN_WITHDRAW_AMOUNT:,} تومان\n\n"
        f"📤 برای ساخت ربات از گزینه «ساخت ربات جدید» استفاده کنید"
    )
    
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=markup)

# ==================== اشتراک و تست 24 ساعته ====================
@bot.message_handler(func=lambda m: m.text == '🎁 اشتراک و تست 24 ساعته')
def subscription_menu(message):
    user_id = message.from_user.id
    
    has_sub = SubscriptionManager.has_active_subscription(user_id)
    trial_active = SubscriptionManager.is_trial_active(user_id)
    can_trial, trial_msg = SubscriptionManager.can_use_trial(user_id)
    trial_remaining = SubscriptionManager.get_trial_remaining(user_id) if trial_active else 0
    
    text = f"🎁 **مدیریت اشتراک و تست ۲۴ ساعته**\n\n"
    text += f"📊 **وضعیت فعلی شما**\n"
    
    if has_sub:
        sub_info = SubscriptionManager.get_subscription_info(user_id)
        end_date = datetime.fromisoformat(sub_info['end_date'])
        text += f"└ ✅ اشتراک فعال: {sub_info['plan_type']}\n└ 📅 انقضا: {end_date.strftime('%Y-%m-%d')}\n"
    elif trial_active:
        text += f"└ 🎁 تست ۲۴ ساعته فعال\n└ ⏰ زمان باقیمانده: {trial_remaining} ساعت\n"
    else:
        text += f"└ ❌ هیچ اشتراک فعالی ندارید\n"
    
    text += f"\n💰 **تعرفه‌های اشتراک**\n"
    text += f"└ ماهانه: {PRICE_PER_MONTH:,} تومان (5 ربات)\n"
    text += f"└ سه ماهه: {PRICE_3_MONTHS:,} تومان (15 ربات)\n"
    text += f"└ شش ماهه: {PRICE_6_MONTHS:,} تومان (35 ربات)\n"
    text += f"└ یکساله: {PRICE_12_MONTHS:,} تومان (100 ربات)\n\n"
    text += f"🎁 **تست رایگان ۲۴ ساعته**\n"
    text += f"└ {trial_msg}\n\n"
    text += f"💳 شماره کارت: `{CARD_NUMBER}`\n🏦 به نام: {CARD_HOLDER}\n\n"
    text += f"📸 پس از واریز، تصویر فیش را ارسال کنید"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💰 ماهانه", callback_data="buy_monthly"),
        types.InlineKeyboardButton("💰 سه ماهه", callback_data="buy_3months"),
        types.InlineKeyboardButton("💰 شش ماهه", callback_data="buy_6months"),
        types.InlineKeyboardButton("💰 یکساله", callback_data="buy_12months")
    )
    if can_trial and not trial_active:
        markup.add(types.InlineKeyboardButton("🎁 فعال‌سازی تست 24 ساعته", callback_data="activate_trial"))
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def buy_subscription(call):
    plans = {
        'buy_monthly': ('monthly', PRICE_PER_MONTH),
        'buy_3months': ('3months', PRICE_3_MONTHS),
        'buy_6months': ('6months', PRICE_6_MONTHS),
        'buy_12months': ('12months', PRICE_12_MONTHS)
    }
    if call.data in plans:
        plan, amount = plans[call.data]
    else:
        bot.answer_callback_query(call.id, "طرح نامعتبر")
        return
    
    payment_code = hashlib.md5(f"{call.from_user.id}_{time.time()}".encode()).hexdigest()[:8].upper()
    text = f"💰 **خرید اشتراک {plan}**\n\nمبلغ: {amount:,} تومان\nشماره کارت: `{CARD_NUMBER}`\nبه نام: {CARD_HOLDER}\n\n📸 پس از واریز، تصویر فیش را ارسال کنید\n🆔 کد پیگیری: `{payment_code}`"
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'activate_trial')
def activate_trial(call):
    user_id = call.from_user.id
    can_trial, msg = SubscriptionManager.can_use_trial(user_id)
    if not can_trial:
        bot.answer_callback_query(call.id, msg)
        return
    if SubscriptionManager.is_trial_active(user_id):
        bot.answer_callback_query(call.id, "تست ۲۴ ساعته در حال حاضر فعال است")
        return
    
    SubscriptionManager.activate_trial(user_id)
    text = f"🎁 **تست ۲۴ ساعته فعال شد!**\n\n✅ می‌توانید یک ربات بسازید\n⏰ زمان باقیمانده: {TRIAL_HOURS} ساعت\n💡 برای استفاده دائمی، اشتراک تهیه کنید"
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

# ==================== کیف پول و رفرال ====================
@bot.message_handler(func=lambda m: m.text == '💰 کیف پول و رفرال')
def wallet_ref(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        bot.send_message(message.chat.id, "❌ لطفاً /start را بزنید")
        return
    
    referral_link = ReferralManager.get_referral_link(user_id)
    balance = ReferralManager.get_balance(user_id)
    stats = ReferralManager.get_referral_stats(user_id)
    
    text = f"💰 **کیف پول و سیستم رفرال**\n\n"
    text += f"👤 کاربر: {user['first_name']}\n🆔 آیدی: `{user_id}`\n\n"
    text += f"💳 موجودی قابل برداشت: {balance:,} تومان\n\n"
    text += f"🎁 لینک رفرال شما:\n{referral_link}\n"
    text += f"└ کلیک‌ها: {stats['total_clicks']}\n"
    text += f"└ خریدهای موفق: {stats['verified']}\n"
    text += f"└ کل پورسانت: {stats['total_commission']:,} تومان\n\n"
    text += f"💰 هر خرید از لینک شما = {REFERRAL_COMMISSION_PERCENT}% پورسانت\n"
    text += f"💳 حداقل مبلغ برداشت: {MIN_WITHDRAW_AMOUNT:,} تومان"
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# ==================== برداشت وجه ====================
@bot.message_handler(func=lambda m: m.text == '💳 برداشت وجه')
def withdraw_menu(message):
    balance = ReferralManager.get_balance(message.from_user.id)
    text = f"💳 **برداشت وجه**\n\n💰 موجودی: {balance:,} تومان\n📌 حداقل مبلغ برداشت: {MIN_WITHDRAW_AMOUNT:,} تومان\n\nلطفاً به صورت زیر ارسال کنید:\n`مبلغ|شماره کارت`\nمثال: `2000000|6037991234567890`"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")
    bot.register_next_step_handler(message, process_withdraw)

def process_withdraw(message):
    try:
        parts = message.text.split('|')
        if len(parts) != 2:
            bot.reply_to(message, "فرمت صحیح نیست! مثال: `2000000|6037991234567890`", parse_mode="Markdown")
            return
        amount = int(parts[0].strip())
        card_number = parts[1].strip()
        success, msg = WithdrawManager.request_withdraw(message.from_user.id, amount, card_number)
        bot.reply_to(message, msg)
    except ValueError:
        bot.reply_to(message, "❌ مبلغ باید عدد باشد!")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")

# ==================== فیش واریزی ====================
@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    
    plan_type = 'monthly'
    amount = PRICE_PER_MONTH
    if message.caption:
        caption = message.caption.lower()
        if 'سه ماهه' in caption:
            plan_type, amount = '3months', PRICE_3_MONTHS
        elif 'شش ماهه' in caption:
            plan_type, amount = '6months', PRICE_6_MONTHS
        elif 'یک ساله' in caption or '12 ماه' in caption:
            plan_type, amount = '12months', PRICE_12_MONTHS
    
    with get_db() as conn:
        if conn.execute('SELECT id FROM receipts WHERE user_id = ? AND status = "pending"', (user_id,)).fetchone():
            bot.reply_to(message, "⏳ شما یک فیش در انتظار بررسی دارید")
            return
    
    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    payment_code = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:8].upper()
    receipt_path = os.path.join(RECEIPTS_DIR, f"{user_id}_{payment_code}.jpg")
    
    with open(receipt_path, 'wb') as f:
        f.write(downloaded_file)
    
    with get_db() as conn:
        conn.execute('INSERT INTO receipts (user_id, amount, plan_type, receipt_path, payment_code, created_at) VALUES (?, ?, ?, ?, ?, ?)', (user_id, amount, plan_type, receipt_path, payment_code, datetime.now().isoformat()))
        conn.commit()
    
    bot.reply_to(message, f"✅ فیش شما دریافت شد!\n💰 مبلغ: {amount:,} تومان\n📋 نوع: {plan_type}\n🆔 کد: `{payment_code}`\n\nپس از بررسی توسط ادمین، اشتراک شما فعال می‌شود.", parse_mode="Markdown")
    
    for admin_id in ADMIN_IDS:
        try:
            bot.send_photo(admin_id, photo=open(receipt_path, 'rb'), caption=f"📸 فیش جدید\n👤 کاربر: {user_id}\n💰 مبلغ: {amount:,} تومان\n📋 {plan_type}\n🆔 {payment_code}")
        except:
            pass

# ==================== ساخت ربات جدید ====================
@bot.message_handler(func=lambda m: m.text == '🤖 ساخت ربات جدید')
def new_bot(message):
    user_id = message.from_user.id
    can_create, reason = SubscriptionManager.can_create_bot(user_id)
    
    if not can_create:
        text = f"❌ **شما دسترسی به ساخت ربات ندارید!**\n\nبرای ساخت ربات:\n1️⃣ فعال‌سازی تست ۲۴ ساعته (رایگان)\n2️⃣ خرید اشتراک\n\n💳 شماره کارت: `{CARD_NUMBER}`\n🏦 به نام: {CARD_HOLDER}"
        bot.send_message(message.chat.id, text, parse_mode="Markdown")
        return
    
    bots_count = len(get_user_bots(user_id))
    max_bots = SubscriptionManager.get_available_bots_count(user_id)
    
    text = f"🤖 **ساخت ربات جدید**\n\n📊 وضعیت: {reason}\n🤖 ربات‌های ساخته شده: {bots_count}\n📈 حداکثر مجاز: {max_bots}\n\n📤 فایل .py یا .zip خود را ارسال کنید\n✅ توکن داخل کد باشد\n🔒 کد در محیط ایزوله اجرا می‌شود"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# ==================== آپلود و اجرای ربات ====================
@bot.message_handler(content_types=['document'])
def handle_build_file(message):
    user_id = message.from_user.id
    
    can_create, reason = SubscriptionManager.can_create_bot(user_id)
    if not can_create:
        bot.reply_to(message, "❌ ابتدا اشتراک خود را فعال کنید یا تست ۲۴ ساعته را فعال نمایید!")
        return
    
    bots_count = len(get_user_bots(user_id))
    max_bots = SubscriptionManager.get_available_bots_count(user_id)
    if bots_count >= max_bots:
        bot.reply_to(message, f"❌ شما به حداکثر تعداد ربات مجاز ({max_bots}) رسیده‌اید!")
        return
    
    file_name = message.document.file_name
    if not (file_name.endswith('.py') or file_name.endswith('.zip')):
        bot.reply_to(message, "❌ فقط فایل‌های `.py` یا `.zip` مجاز هستند!")
        return
    
    if message.document.file_size > MAX_FILE_SIZE:
        bot.reply_to(message, f"❌ حجم فایل نباید بیشتر از {MAX_FILE_SIZE // (1024*1024)} مگابایت باشد!")
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
            extract_dir = os.path.join(TEMP_DIR, f"extract_{user_id}_{int(time.time())}")
            os.makedirs(extract_dir, exist_ok=True)
            py_files = extract_files_from_zip(file_path, extract_dir)
            for pf in py_files:
                if pf['name'] in ['bot.py', 'main.py', 'run.py']:
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
        
        is_safe, errors = security_check_code(main_code)
        if not is_safe:
            bot.edit_message_text(f"❌ کد شما از نظر امنیتی مشکل دارد!\n\n" + "\n".join(errors), message.chat.id, status_msg.message_id)
            return
        
        token = extract_token_from_code(main_code)
        if not token:
            bot.edit_message_text("❌ توکن در کد پیدا نشد!", message.chat.id, status_msg.message_id)
            return
        
        try:
            response = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
            if response.status_code != 200:
                bot.edit_message_text("❌ توکن معتبر نیست!", message.chat.id, status_msg.message_id)
                return
            bot_info = response.json()['result']
            bot_name = bot_info['first_name']
            bot_username = bot_info['username']
        except Exception as e:
            bot.edit_message_text(f"❌ خطا در بررسی توکن: {str(e)}", message.chat.id, status_msg.message_id)
            return
        
        bot.edit_message_text("⚡ در حال اجرای ربات...", message.chat.id, status_msg.message_id)
        
        bot_id = hashlib.md5(f"{user_id}{token}{time.time()}".encode()).hexdigest()[:10]
        result = BotRunner.run_bot(bot_id, main_code, token)
        
        if result['success']:
            add_bot_to_db(user_id, bot_id, token, bot_name, bot_username, file_path, result.get('pid'))
            reply = f"✅ **ربات با موفقیت ساخته شد!** 🎉\n\n🤖 نام: {bot_name}\n🔗 لینک: https://t.me/{bot_username}\n🆔 آیدی: `{bot_id}`\n🔄 وضعیت: در حال اجرا"
            if reason == 'trial':
                remaining = SubscriptionManager.get_trial_remaining(user_id)
                reply += f"\n\n⏰ **تست ۲۴ ساعته فعال**\n└ زمان باقیمانده: {remaining} ساعت"
                with get_db() as conn:
                    conn.execute('UPDATE trial_usage SET bot_id = ? WHERE user_id = ?', (bot_id, user_id))
                    conn.commit()
            bot.edit_message_text(reply, message.chat.id, status_msg.message_id, parse_mode="Markdown")
            add_notification(user_id, "ربات ساخته شد", f"ربات {bot_name} با موفقیت ساخته شد")
        else:
            bot.edit_message_text(f"❌ خطا در اجرا:\n{result.get('error', 'خطای ناشناخته')[:300]}", message.chat.id, status_msg.message_id)
        
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)}", message.chat.id, status_msg.message_id)

# ==================== ربات‌های من ====================
@bot.message_handler(func=lambda m: m.text == '📋 ربات‌های من')
def my_bots(message):
    bots = get_user_bots(message.from_user.id)
    if not bots:
        bot.send_message(message.chat.id, "📋 شما رباتی ندارید!")
        return
    
    for b in bots[:10]:
        status = "🟢" if b['status'] == 'running' else "🔴"
        text = f"{status} **{b['name']}**\n🔗 https://t.me/{b['username']}\n🆔 `{b['id']}`\n📅 {b['created_at'][:10]}"
        bot.send_message(message.chat.id, text, parse_mode="Markdown")

# ==================== فعال/غیرفعال کردن ====================
@bot.message_handler(func=lambda m: m.text == '🔄 فعال/غیرفعال کردن')
def toggle_prompt(message):
    bots = get_user_bots(message.from_user.id)
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
            BotRunner.stop_bot(bot_id)
            update_bot_status(bot_id, 'stopped')
            bot.answer_callback_query(call.id, "✅ ربات متوقف شد")
            bot.edit_message_text(f"✅ ربات {bot_info['name']} متوقف شد.", call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "⚠️ برای راه‌اندازی مجدد، ربات را حذف و دوباره بسازید")

# ==================== حذف ربات ====================
@bot.message_handler(func=lambda m: m.text == '🗑 حذف ربات')
def delete_prompt(message):
    bots = get_user_bots(message.from_user.id)
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
    markup.add(types.InlineKeyboardButton("✅ بله", callback_data=f"confirm_del_{bot_id}"), types.InlineKeyboardButton("❌ خیر", callback_data="cancel_del"))
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
    libs = [('requests', 'requests'), ('numpy', 'numpy'), ('pandas', 'pandas'), ('flask', 'flask'), ('pyTelegramBotAPI', 'pyTelegramBotAPI'), ('aiogram', 'aiogram'), ('jdatetime', 'jdatetime'), ('🔧 دستی', 'custom')]
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
    
    bot.answer_callback_query(call.id, f"🔄 در حال نصب {lib}...")
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", lib], capture_output=True, text=True, timeout=60)
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
    user_id = message.from_user.id
    user = get_user(user_id)
    bots = get_user_bots(user_id)
    balance = ReferralManager.get_balance(user_id)
    
    text = f"📊 **آمار شما**\n\n👤 کاربر: {user['first_name']}\n🆔 `{user_id}`\n\n🤖 کل ربات‌ها: {len(bots)}\n💰 موجودی کیف پول: {balance:,} تومان\n🎁 کد رفرال: `{user['referral_code']}`"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# ==================== پشتیبانی ====================
@bot.message_handler(func=lambda m: m.text == '📞 پشتیبانی')
def support(message):
    bot.send_message(message.chat.id, "📞 **پشتیبانی:** @shahraghee13", parse_mode="Markdown")

# ==================== جایزه روزانه ====================
@bot.message_handler(func=lambda m: m.text == '🎁 جایزه روزانه')
def daily_reward(message):
    user_id = message.from_user.id
    last_reward = cache.get(f"daily_reward_{user_id}") if 'cache' in dir() else None
    
    if last_reward:
        bot.send_message(message.chat.id, "⏰ شما امروز جایزه خود را دریافت کرده‌اید!\nفردا دوباره امتحان کنید.")
        return
    
    reward = random.randint(1000, 50000)
    with get_db() as conn:
        conn.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (reward, user_id))
        conn.commit()
    
    if 'cache' in dir():
        cache.set(f"daily_reward_{user_id}", datetime.now().isoformat(), ttl=86400)
    
    bot.send_message(message.chat.id, f"🎁 **جایزه روزانه شما**\n💰 {reward:,} تومان به کیف پول شما اضافه شد!", parse_mode="Markdown")
    add_notification(user_id, "جایزه روزانه", f"{reward:,} تومان به کیف پول شما اضافه شد")

# ==================== پنل ادمین ====================
@bot.message_handler(func=lambda m: m.text == '👑 پنل ادمین')
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ شما دسترسی ادمین ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📸 فیش‌ها", callback_data="admin_receipts"),
        types.InlineKeyboardButton("💰 برداشت‌ها", callback_data="admin_withdraw"),
        types.InlineKeyboardButton("👥 کاربران", callback_data="admin_users"),
        types.InlineKeyboardButton("📊 آمار کامل", callback_data="admin_stats"),
        types.InlineKeyboardButton("💳 تغییر قیمت", callback_data="admin_price"),
        types.InlineKeyboardButton("🏧 تغییر کارت", callback_data="admin_card"),
        types.InlineKeyboardButton("🗑 حذف ربات کاربر", callback_data="admin_delete_bot"),
        types.InlineKeyboardButton("📢 ارسال نوتیف", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")
    )
    bot.send_message(message.chat.id, "👑 **پنل مدیریت**", reply_markup=markup, parse_mode="Markdown")

# ==================== هندلرهای ادمین ====================
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
        text = f"📸 **فیش #{r['id']}**\n👤 کاربر: {r['user_id']}\n💰 {r['amount']:,} تومان\n📋 {r['plan_type']}\n🆔 {r['payment_code']}"
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
def approve_receipt_admin(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    receipt_id = int(call.data.replace('approve_receipt_', ''))
    with get_db() as conn:
        receipt = conn.execute('SELECT * FROM receipts WHERE id = ?', (receipt_id,)).fetchone()
        if receipt:
            conn.execute('UPDATE receipts SET status = "approved", reviewed_at = ?, reviewed_by = ? WHERE id = ?', (datetime.now().isoformat(), call.from_user.id, receipt_id))
            SubscriptionManager.activate_subscription(receipt['user_id'], receipt['plan_type'], receipt['amount'])
            ReferralManager.process_purchase_commission(receipt['user_id'], receipt['amount'])
            conn.commit()
            try:
                bot.send_message(receipt['user_id'], f"✅ اشتراک شما فعال شد!\n💰 {receipt['amount']:,} تومان\n📋 {receipt['plan_type']}\n🎉 می‌توانید ربات بسازید.")
            except:
                pass
    bot.answer_callback_query(call.id, "✅ تایید شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_receipt_'))
def reject_receipt_admin(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    receipt_id = int(call.data.replace('reject_receipt_', ''))
    with get_db() as conn:
        receipt = conn.execute('SELECT * FROM receipts WHERE id = ?', (receipt_id,)).fetchone()
        if receipt:
            conn.execute('UPDATE receipts SET status = "rejected", reviewed_at = ?, reviewed_by = ? WHERE id = ?', (datetime.now().isoformat(), call.from_user.id, receipt_id))
            conn.commit()
            try:
                bot.send_message(receipt['user_id'], f"❌ فیش شما رد شد. لطفاً با پشتیبانی تماس بگیرید: @shahraghee13")
            except:
                pass
    bot.answer_callback_query(call.id, "❌ رد شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_withdraw")
def admin_withdraw(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    withdraws = WithdrawManager.get_withdraw_requests('pending')
    if not withdraws:
        bot.send_message(call.message.chat.id, "💰 هیچ درخواست برداشتی وجود ندارد")
        return
    
    for w in withdraws:
        text = f"💰 **درخواست برداشت #{w['id']}**\n👤 کاربر: {w['user_id']}\n💰 {w['amount']:,} تومان\n💳 {w['card_number']}"
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید", callback_data=f"withdraw_approve_{w['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"withdraw_reject_{w['id']}")
        )
        bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('withdraw_approve_'))
def withdraw_approve_admin(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    withdraw_id = int(call.data.replace('withdraw_approve_', ''))
    success, msg = WithdrawManager.process_withdraw(withdraw_id, 'approve')
    bot.answer_callback_query(call.id, msg)
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('withdraw_reject_'))
def withdraw_reject_admin(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    withdraw_id = int(call.data.replace('withdraw_reject_', ''))
    success, msg = WithdrawManager.process_withdraw(withdraw_id, 'reject')
    bot.answer_callback_query(call.id, msg)
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_users")
def admin_users_list(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        users = conn.execute('SELECT user_id, first_name, bots_count, verified_referrals, balance, payment_status FROM users ORDER BY created_at DESC LIMIT 30').fetchall()
    
    text = "👥 **۳۰ کاربر آخر:**\n\n"
    for u in users:
        status = "✅" if u['payment_status'] == 'approved' else "⏳"
        text += f"{status} {u['user_id']} - {u['first_name']}\n└ 🤖{u['bots_count']} | 🎁{u['verified_referrals']} | 💰{u['balance']:,}\n\n"
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_stats_full(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        total_users = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        total_bots = conn.execute('SELECT COUNT(*) FROM bots').fetchone()[0]
        running_bots = conn.execute('SELECT COUNT(*) FROM bots WHERE status = "running"').fetchone()[0]
        total_amount = conn.execute('SELECT SUM(amount) FROM receipts WHERE status = "approved"').fetchone()[0] or 0
        total_balance = conn.execute('SELECT SUM(balance) FROM users').fetchone()[0] or 0
    
    text = f"📊 **آمار کامل**\n\n👥 کاربران: {total_users}\n🤖 ربات‌ها: {total_bots}\n🟢 فعال: {running_bots}\n💰 مجموع واریزی: {total_amount:,} تومان\n🏦 موجودی کاربران: {total_balance:,} تومان"
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_price")
def admin_price_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    msg = bot.send_message(call.message.chat.id, "💰 قیمت جدید ماهانه را وارد کنید (تومان):")
    bot.register_next_step_handler(msg, process_admin_price)

def process_admin_price(message):
    global PRICE_PER_MONTH, PRICE_3_MONTHS, PRICE_6_MONTHS, PRICE_12_MONTHS
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        new_price = int(message.text.strip())
        PRICE_PER_MONTH = new_price
        PRICE_3_MONTHS = int(new_price * 2.5)
        PRICE_6_MONTHS = int(new_price * 4.5)
        PRICE_12_MONTHS = int(new_price * 8)
        bot.reply_to(message, f"✅ قیمت‌ها تغییر کرد:\nماهانه: {PRICE_PER_MONTH:,}\nسه ماهه: {PRICE_3_MONTHS:,}\nشش ماهه: {PRICE_6_MONTHS:,}\nیکساله: {PRICE_12_MONTHS:,}")
    except:
        bot.reply_to(message, "❌ عدد معتبر وارد کنید!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_card")
def admin_card_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    msg = bot.send_message(call.message.chat.id, "🏧 شماره کارت جدید را وارد کنید:")
    bot.register_next_step_handler(msg, process_admin_card)

def process_admin_card(message):
    global CARD_NUMBER
    if message.from_user.id not in ADMIN_IDS:
        return
    CARD_NUMBER = message.text.strip()
    bot.reply_to(message, f"✅ شماره کارت تغییر کرد: {CARD_NUMBER}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_delete_bot")
def admin_delete_bot_list(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        bots = conn.execute('SELECT b.id, b.name, u.user_id, u.first_name FROM bots b JOIN users u ON b.user_id = u.user_id LIMIT 50').fetchall()
    
    if not bots:
        bot.send_message(call.message.chat.id, "🤖 هیچ رباتی وجود ندارد")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        markup.add(types.InlineKeyboardButton(f"🗑 {b['name']} (کاربر: {b['first_name']})", callback_data=f"admin_del_bot_{b['id']}"))
    bot.send_message(call.message.chat.id, "🗑 ربات مورد نظر را انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_del_bot_'))
def admin_confirm_delete_bot(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    bot_id = call.data.replace('admin_del_bot_', '')
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ بله", callback_data=f"admin_confirm_del_{bot_id}"),
        types.InlineKeyboardButton("❌ خیر", callback_data="admin_back")
    )
    bot.edit_message_text(f"⚠️ آیا از حذف ربات {bot_id} اطمینان دارید؟", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_confirm_del_'))
def admin_do_delete_bot(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    bot_id = call.data.replace('admin_confirm_del_', '')
    with get_db() as conn:
        bot_info = conn.execute('SELECT user_id FROM bots WHERE id = ?', (bot_id,)).fetchone()
        if bot_info:
            BotRunner.stop_bot(bot_id)
            conn.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
            conn.execute('UPDATE users SET bots_count = bots_count - 1 WHERE user_id = ?', (bot_info['user_id'],))
            conn.commit()
    bot.edit_message_text("✅ ربات حذف شد.", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast")
def admin_broadcast_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    msg = bot.send_message(call.message.chat.id, "📢 متن پیام همگانی را وارد کنید:")
    bot.register_next_step_handler(msg, process_admin_broadcast)

def process_admin_broadcast(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    with get_db() as conn:
        users = conn.execute('SELECT user_id FROM users').fetchall()
    
    success = 0
    for user in users:
        try:
            bot.send_message(user['user_id'], f"📢 **اعلان همگانی**\n\n{message.text}", parse_mode="Markdown")
            success += 1
        except:
            pass
        time.sleep(0.05)
    
    bot.reply_to(message, f"✅ پیام برای {success} کاربر ارسال شد.")

@bot.callback_query_handler(func=lambda call: call.data == "back_to_menu")
def back_to_menu_callback(call):
    user_id = call.from_user.id
    is_admin = user_id in ADMIN_IDS
    markup = get_main_menu(is_admin)
    bot.edit_message_text("🚀 منوی اصلی:", call.message.chat.id, call.message.message_id, reply_markup=markup)

# ==================== کش ساده ====================
class SimpleCache:
    def __init__(self):
        self.cache = {}
        self.times = {}
    
    def get(self, key):
        if key in self.cache and self.times.get(key, 0) > time.time():
            return self.cache[key]
        return None
    
    def set(self, key, value, ttl=3600):
        self.cache[key] = value
        self.times[key] = time.time() + ttl

cache = SimpleCache()

# ==================== مانیتورینگ ====================
def monitor_trials():
    while True:
        try:
            with get_db() as conn:
                trials = conn.execute('SELECT user_id, bot_id FROM trial_usage WHERE is_active = 1').fetchall()
                for trial in trials:
                    if not SubscriptionManager.is_trial_active(trial['user_id']):
                        if trial['bot_id']:
                            BotRunner.stop_bot(trial['bot_id'])
                            update_bot_status(trial['bot_id'], 'stopped')
                            try:
                                bot.send_message(trial['user_id'], f"⏰ تست ۲۴ ساعته شما به پایان رسید!\nربات شما متوقف شد.\nبرای ادامه، اشتراک تهیه کنید.")
                            except:
                                pass
            time.sleep(1800)
        except:
            time.sleep(60)

monitor_thread = threading.Thread(target=monitor_trials, daemon=True)
monitor_thread.start()

# ==================== اجرا ====================
if __name__ == "__main__":
    print("=" * 70)
    print("🚀 ربات مادر نهایی - نسخه نهایی 14.0")
    print("=" * 70)
    print(f"✅ نصب خودکار کتابخانه‌ها: فعال")
    print(f"✅ داکر: {'فعال' if DOCKER_AVAILABLE else 'غیرفعال'}")
    print(f"✅ ردیس: {'فعال' if REDIS_AVAILABLE else 'غیرفعال'}")
    print(f"✅ امنیت: {'فعال' if CRYPTO_AVAILABLE else 'ساده'}")
    print("=" * 70)
    print("🤖 ربات در حال اجراست...")
    print("=" * 70)
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            logger.error(f"خطا: {e}")
            time.sleep(5)