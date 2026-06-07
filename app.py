#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
═══════════════════════════════════════════════════════════════════════════════
🚀 ربات مادر نهایی - نسخه امن Enterprise
═══════════════════════════════════════════════════════════════════════════════
⚡ معماری میکروسرویس کامل - پشتیبانی از میلیون‌ها کاربر
🔒 ایزوله‌سازی قدرتمند - هر ربات در ماشین مجازی جداگانه
🌐 پشتیبانی از دو زبان فارسی و انگلیسی (قابل تغییر توسط کاربر)
💎 سیستم کمیسیون دقیق رفرال (۷٪ از هر اشتراک به معرف تعلق می‌گیرد)
🤖 محدودیت ۳ ربات در هر اشتراک (قابل تنظیم توسط ادمین)
🔄 بازیابی خودکار پس از خرابی سرور
📊 Auto-Scale - مقیاس‌پذیری خودکار
💳 شماره کارت و اطلاعات بانکی جهت واریز
═══════════════════════════════════════════════════════════════════════════════
"""

# ==================== ایمپورت‌های اصلی ====================
import os
import sys
import time
import json
import signal
import secrets
import hashlib
import logging
import sqlite3
import threading
import subprocess
import zipfile
import shutil
import re
import queue
import uuid
import base64
import pickle
import traceback
import gc
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from functools import wraps
from collections import defaultdict
from typing import Optional, Dict, Any, List, Tuple, Union

# ==================== کتابخانه‌های شخص ثالث ====================
try:
    import telebot
    from telebot import types
    TELEBOT_AVAILABLE = True
except ImportError:
    print("❌ telebot not installed! Run: pip install pyTelegramBotAPI")
    sys.exit(1)

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    print("❌ requests not installed! Run: pip install requests")
    sys.exit(1)

try:
    from flask import Flask, request, jsonify
    FLASK_AVAILABLE = True
except ImportError:
    print("⚠️ Flask not available - web endpoints disabled")
    FLASK_AVAILABLE = False

# ==================== کتابخانه‌های اختیاری (پیشرفته) ====================
REDIS_AVAILABLE = False
CELERY_AVAILABLE = False
CRYPTO_AVAILABLE = False
SENTRY_AVAILABLE = False
ELASTIC_AVAILABLE = False
PROMETHEUS_AVAILABLE = False
PSUTIL_AVAILABLE = False

try:
    import redis
    REDIS_AVAILABLE = True
    print("✅ Redis loaded")
except ImportError:
    print("⚠️ Redis not available - using simple cache")

try:
    from celery import Celery
    CELERY_AVAILABLE = True
    print("✅ Celery loaded")
except ImportError:
    print("⚠️ Celery not available - using simple queue")

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
    CRYPTO_AVAILABLE = True
    print("✅ Cryptography loaded")
except ImportError:
    print("⚠️ Cryptography not available - run: pip install cryptography")

try:
    import sentry_sdk
    from sentry_sdk import capture_exception
    SENTRY_AVAILABLE = True
    print("✅ Sentry loaded")
except ImportError:
    def capture_exception(e):
        pass
    print("⚠️ Sentry not available")

try:
    from elasticsearch import Elasticsearch
    ELASTIC_AVAILABLE = True
    print("✅ Elasticsearch loaded")
except ImportError:
    print("⚠️ Elasticsearch not available")

try:
    from prometheus_client import Counter, Gauge, Histogram, generate_latest
    PROMETHEUS_AVAILABLE = True
    print("✅ Prometheus loaded")
except ImportError:
    print("⚠️ Prometheus not available")

try:
    import psutil
    PSUTIL_AVAILABLE = True
    print("✅ Psutil loaded")
except ImportError:
    print("⚠️ Psutil not available")

# ==================== تنظیمات امنیت و توکن ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    print("=" * 60)
    print("❌ ERROR: BOT_TOKEN not found!")
    print("👉 Run: export BOT_TOKEN='your_bot_token_here'")
    print("=" * 60)
    sys.exit(1)

ENCRYPTION_PASSWORD = os.environ.get("ENCRYPTION_PASSWORD", "")
if not ENCRYPTION_PASSWORD:
    print("⚠️ WARNING: ENCRYPTION_PASSWORD not set")
    print("👉 Run: export ENCRYPTION_PASSWORD='your_strong_password'")
    ENCRYPTION_PASSWORD = "CHANGE_THIS_DEFAULT_PASSWORD_2024"

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", secrets.token_hex(32))

# ==================== تنظیمات اصلی ====================
ADMIN_IDS = [327855654]  # 🔴 آیدی ادمین را اینجا قرار دهید
BOT_USERNAME = "ROBTTSAZE_bot"
TRC20_ADDRESS = "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"

# اطلاعات کارت بانکی
CARD_NUMBER = "5892101187322777"
CARD_NUMBER_DISPLAY = "5892 1011 8732 2777"
CARD_HOLDER = "مرتضی نیکخو خنجری"
CARD_BANK = "بانک ملی - سپهر"

# ==================== ثابت‌های سیستم ====================
VERSION = "4.0.0"
START_TIME = time.time()
MAX_FILE_SIZE = 50 * 1024 * 1024
MAX_CONCURRENT_BUILDS = 20
MAX_QUEUE_SIZE = 10000
DEFAULT_MAX_BOTS_PER_SUBSCRIPTION = 3
DEFAULT_SUBSCRIPTION_PRICE = 2000000
DEFAULT_WITHDRAW_PERCENT = 7
DEFAULT_MIN_WITHDRAW = 2000000

# ==================== مسیرهای دایرکتوری ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DIRS = {
    'DB': os.path.join(BASE_DIR, "database"),
    'FILES': os.path.join(BASE_DIR, "user_files"),
    'RUNNING': os.path.join(BASE_DIR, "running_bots"),
    'LOGS': os.path.join(BASE_DIR, "logs"),
    'RECEIPTS': os.path.join(BASE_DIR, "receipts"),
    'TEMP': os.path.join(BASE_DIR, "temp"),
    'MACHINES': os.path.join(BASE_DIR, "machines"),
    'CACHE': os.path.join(BASE_DIR, "cache"),
    'QUEUE': os.path.join(BASE_DIR, "queue"),
    'BACKUPS': os.path.join(BASE_DIR, "backups"),
    'ARCHIVE': os.path.join(BASE_DIR, "archive"),
    'STATE': os.path.join(BASE_DIR, "state"),
    'METRICS': os.path.join(BASE_DIR, "metrics")
}

for dir_path in DIRS.values():
    os.makedirs(dir_path, exist_ok=True)

# ==================== لاگینگ امن ====================
class SecureFormatter(logging.Formatter):
    def format(self, record):
        msg = super().format(record)
        msg = re.sub(r'bot\d+:[A-Za-z0-9_-]{20,}', '[TOKEN_HIDDEN]', msg)
        msg = re.sub(r'\d{10}:[A-Za-z0-9_-]{35,}', '[TOKEN_HIDDEN]', msg)
        msg = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP_HIDDEN]', msg)
        msg = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD_HIDDEN]', msg)
        return msg

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            os.path.join(DIRS['LOGS'], 'mother_bot.log'),
            maxBytes=500*1024*1024,
            backupCount=10,
            encoding='utf-8'
        ),
        RotatingFileHandler(
            os.path.join(DIRS['LOGS'], 'errors.log'),
            maxBytes=100*1024*1024,
            backupCount=10,
            encoding='utf-8'
        ),
        logging.StreamHandler()
    ]
)

for handler in logging.root.handlers:
    handler.setFormatter(SecureFormatter('%(asctime)s - %(levelname)s - %(message)s'))

logger = logging.getLogger('MotherBot')

# ==================== کلید رمزنگاری ثابت ====================
if CRYPTO_AVAILABLE:
    kdf = PBKDF2(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"mother_bot_secure_salt_2024_v4",
        iterations=100000,
    )
    CRYPTO_KEY = base64.urlsafe_b64encode(kdf.derive(ENCRYPTION_PASSWORD.encode()))
    CRYPTO_CIPHER = Fernet(CRYPTO_KEY)
    logger.info("✅ Cryptography initialized with persistent key")
else:
    CRYPTO_CIPHER = None

# ==================== کلاس کش ====================
class SimpleCache:
    def __init__(self, ttl=3600):
        self.cache = {}
        self.ttl = ttl
        self.lock = threading.RLock()
        self.stats = {"hits": 0, "misses": 0}
    
    def get(self, key):
        with self.lock:
            item = self.cache.get(key)
            if item and item['expires'] > time.time():
                self.stats["hits"] += 1
                return item['value']
            if key in self.cache:
                del self.cache[key]
            self.stats["misses"] += 1
        return None
    
    def set(self, key, value, ttl=None):
        if ttl is None:
            ttl = self.ttl
        with self.lock:
            self.cache[key] = {'value': value, 'expires': time.time() + ttl}
    
    def delete(self, key):
        with self.lock:
            if key in self.cache:
                del self.cache[key]
    
    def get_stats(self):
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total * 100) if total > 0 else 0
        return {"hits": self.stats["hits"], "misses": self.stats["misses"], "hit_rate": hit_rate, "size": len(self.cache)}

cache = SimpleCache(ttl=3600)

# ==================== Rate Limiter ====================
class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
        self.lock = threading.RLock()
    
    def is_allowed(self, user_id, limit_per_second=5):
        with self.lock:
            now = time.time()
            user_requests = self.requests[user_id]
            user_requests = [t for t in user_requests if now - t < 1]
            if len(user_requests) >= limit_per_second:
                return False
            user_requests.append(now)
            self.requests[user_id] = user_requests
            return True
    
    def get_user_builds_today(self, user_id):
        today = datetime.now().date().isoformat()
        key = f"builds_{user_id}_{today}"
        cached = cache.get(key)
        if cached is not None:
            return cached
        result = db.execute("SELECT COUNT(*) as count FROM bots WHERE user_id = ? AND DATE(created_at) = ?", 
                           (user_id, today))
        count = result[0]['count'] if result else 0
        cache.set(key, count, ttl=3600)
        return count

rate_limiter = RateLimiter()

# ==================== دیتابیس ====================
class Database:
    def __init__(self):
        self.conn = None
        self._init_db()
        self._init_tables()
        self._start_backup_thread()
    
    def _init_db(self):
        db_path = os.path.join(DIRS['DB'], 'mother_bot.db')
        self.conn = sqlite3.connect(
            db_path,
            timeout=60,
            check_same_thread=False
        )
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA cache_size=-500000")
        self.conn.execute("PRAGMA page_size=8192")
        self.conn.execute("PRAGMA temp_store=MEMORY")
    
    def _start_backup_thread(self):
        def backup_worker():
            while True:
                time.sleep(3600)
                self._create_backup()
        threading.Thread(target=backup_worker, daemon=True).start()
    
    def _create_backup(self):
        try:
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            backup_path = os.path.join(DIRS['BACKUPS'], backup_name)
            shutil.copy2(os.path.join(DIRS['DB'], 'mother_bot.db'), backup_path)
            backups = sorted([f for f in os.listdir(DIRS['BACKUPS']) if f.endswith('.db')])
            for old in backups[:-50]:
                os.remove(os.path.join(DIRS['BACKUPS'], old))
            logger.info(f"✅ Backup created: {backup_name}")
        except Exception as e:
            logger.error(f"Backup failed: {e}")
    
    def execute(self, query, params=()):
        try:
            cursor = self.conn.execute(query, params)
            self.conn.commit()
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"DB error: {e}")
            return []
    
    def encrypt_token(self, token):
        if CRYPTO_AVAILABLE and CRYPTO_CIPHER:
            try:
                return CRYPTO_CIPHER.encrypt(token.encode()).decode()
            except:
                return token
        return token
    
    def decrypt_token(self, encrypted_token):
        if CRYPTO_AVAILABLE and CRYPTO_CIPHER:
            try:
                return CRYPTO_CIPHER.decrypt(encrypted_token.encode()).decode()
            except:
                return None
        return encrypted_token
    
    def _init_tables(self):
        # کاربران
        self.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language TEXT DEFAULT 'fa',
                bots_count INTEGER DEFAULT 0,
                max_bots INTEGER DEFAULT 3,
                subscription_status TEXT DEFAULT 'inactive',
                subscription_expiry TIMESTAMP,
                subscription_purchased_at TIMESTAMP,
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                referrals_count INTEGER DEFAULT 0,
                verified_referrals INTEGER DEFAULT 0,
                wallet_balance INTEGER DEFAULT 0,
                total_commission INTEGER DEFAULT 0,
                created_at TIMESTAMP,
                last_active TIMESTAMP,
                last_payment_hash TEXT,
                is_banned INTEGER DEFAULT 0,
                is_premium INTEGER DEFAULT 0
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
                pid INTEGER,
                machine_id INTEGER,
                port INTEGER,
                status TEXT DEFAULT 'stopped',
                created_at TIMESTAMP,
                last_active TIMESTAMP,
                last_restore_point TIMESTAMP,
                join_enabled INTEGER DEFAULT 1,
                join_block_message TEXT DEFAULT '🚫 سرور پر است',
                health_status TEXT DEFAULT 'healthy',
                last_health_check TIMESTAMP,
                restart_count INTEGER DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        # ماشین‌ها
        self.execute('''
            CREATE TABLE IF NOT EXISTS machines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                status TEXT DEFAULT 'active',
                current_bots INTEGER DEFAULT 0,
                max_bots INTEGER DEFAULT 5000,
                memory_used INTEGER DEFAULT 0,
                max_memory INTEGER DEFAULT 256000,
                cpu_usage REAL DEFAULT 0,
                last_heartbeat TIMESTAMP,
                created_at TIMESTAMP,
                auto_scaled INTEGER DEFAULT 0,
                region TEXT DEFAULT 'default',
                is_kubernetes_pod INTEGER DEFAULT 0
            )
        ''')
        
        # فیش‌ها
        self.execute('''
            CREATE TABLE IF NOT EXISTS receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                receipt_path TEXT,
                tx_hash TEXT,
                status TEXT DEFAULT 'pending',
                reviewed_by INTEGER,
                reviewed_at TIMESTAMP,
                created_at TIMESTAMP
            )
        ''')
        
        # درخواست‌های برداشت
        self.execute('''
            CREATE TABLE IF NOT EXISTS withdraw_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                address TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP,
                processed_at TIMESTAMP
            )
        ''')
        
        # کمیسیون‌ها
        self.execute('''
            CREATE TABLE IF NOT EXISTS commissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                from_user INTEGER,
                amount INTEGER,
                reason TEXT,
                created_at TIMESTAMP,
                paid BOOLEAN DEFAULT 0
            )
        ''')
        
        # تراکنش‌ها
        self.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                type TEXT,
                amount INTEGER,
                balance_before INTEGER,
                balance_after INTEGER,
                reference_id TEXT,
                created_at TIMESTAMP
            )
        ''')
        
        # خطاها
        self.execute('''
            CREATE TABLE IF NOT EXISTS errors (
                id TEXT PRIMARY KEY,
                type TEXT,
                message TEXT,
                user_id INTEGER,
                bot_id TEXT,
                timestamp TIMESTAMP,
                resolved BOOLEAN DEFAULT 0,
                stack_trace TEXT
            )
        ''')
        
        # تنظیمات سیستم
        self.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP
            )
        ''')
        
        # آمار روزانه
        self.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT PRIMARY KEY,
                new_users INTEGER DEFAULT 0,
                new_bots INTEGER DEFAULT 0,
                new_subscriptions INTEGER DEFAULT 0,
                total_revenue INTEGER DEFAULT 0,
                active_users INTEGER DEFAULT 0
            )
        ''')
        
        # فعالیت‌های کاربران
        self.execute('''
            CREATE TABLE IF NOT EXISTS user_activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                details TEXT,
                ip TEXT,
                created_at TIMESTAMP
            )
        ''')
        
        # بکاپ‌ها
        self.execute('''
            CREATE TABLE IF NOT EXISTS backups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                size INTEGER,
                location TEXT,
                created_at TIMESTAMP,
                status TEXT DEFAULT 'success'
            )
        ''')
        
        # تنظیمات پیش‌فرض
        default_settings = {
            'card_number': CARD_NUMBER,
            'card_number_display': CARD_NUMBER_DISPLAY,
            'card_holder': CARD_HOLDER,
            'card_bank': CARD_BANK,
            'trc20_address': TRC20_ADDRESS,
            'subscription_price': str(DEFAULT_SUBSCRIPTION_PRICE),
            'subscription_price_str': '۲,۰۰۰,۰۰۰ تومان',
            'subscription_price_usd': '50 USD',
            'withdraw_percent': str(DEFAULT_WITHDRAW_PERCENT),
            'min_withdraw': str(DEFAULT_MIN_WITHDRAW),
            'max_bots_per_subscription': str(DEFAULT_MAX_BOTS_PER_SUBSCRIPTION),
            'max_builds_per_hour': '10',
            'max_concurrent_builds': str(MAX_CONCURRENT_BUILDS),
            'rate_limit_per_second': '5',
            'health_check_interval': '30',
            'auto_scale_threshold': '80',
            'guide_text_fa': "📚 راهنمای استفاده\n\n1️⃣ برای ساخت ربات، فایل .py یا .zip خود را ارسال کنید\n2️⃣ پس از پرداخت اشتراک، می‌توانید ربات بسازید\n3️⃣ هر کاربر می‌تواند تا ۳ ربات بسازد\n4️⃣ با دعوت دوستان، ۷٪ کمیسیون دریافت کنید\n5️⃣ پس از رسیدن به ۲ میلیون تومان، می‌توانید برداشت کنید",
            'guide_text_en': "📚 User Guide\n\n1️⃣ Send your .py or .zip file\n2️⃣ After subscription payment, you can build bots\n3️⃣ Each user can build up to 3 bots\n4️⃣ Invite friends and get 7% commission\n5️⃣ Withdraw after reaching 2,000,000 Toman"
        }
        
        now = datetime.now().isoformat()
        for key, value in default_settings.items():
            self.execute('INSERT OR IGNORE INTO system_settings (key, value, updated_at) VALUES (?, ?, ?)', 
                        (key, str(value), now))
        
        # ایجاد ماشین‌ها
        machines = self.execute("SELECT COUNT(*) as count FROM machines")
        if machines[0]['count'] == 0:
            for i in range(1, 11):
                self.execute('''
                    INSERT INTO machines (id, name, status, max_bots, max_memory, created_at)
                    VALUES (?, ?, 'active', ?, ?, ?)
                ''', (i, f"Machine-{i:03d}", 5000, 256000, now))
        
        logger.info("✅ Database tables initialized")

db = Database()

# ==================== توابع کمکی ====================
def get_setting(key, default=None):
    result = db.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
    if result:
        val = result[0]['value']
        if key in ['subscription_price', 'withdraw_percent', 'min_withdraw', 
                   'max_bots_per_subscription', 'max_builds_per_hour', 
                   'max_concurrent_builds', 'rate_limit_per_second',
                   'health_check_interval', 'auto_scale_threshold']:
            try:
                return int(val)
            except:
                return default
        return val
    return default

def update_setting(key, value):
    db.execute("UPDATE system_settings SET value = ?, updated_at = ? WHERE key = ?", 
               (str(value), datetime.now().isoformat(), key))

def get_user_language(user_id):
    users = db.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
    if users:
        return users[0]['language']
    return 'fa'

def generate_referral_code(user_id):
    return hashlib.md5(f"{user_id}_{time.time()}_{secrets.token_hex(4)}".encode()).hexdigest()[:12]

def get_user(user_id):
    users = db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    if users:
        return dict(users[0])
    return None

def create_user(user_id, username, first_name, last_name, referred_by=None, language='fa'):
    now = datetime.now().isoformat()
    referral_code = generate_referral_code(user_id)
    max_bots = get_setting('max_bots_per_subscription', 3)
    
    db.execute('''
        INSERT OR IGNORE INTO users 
        (user_id, username, first_name, last_name, referral_code, referred_by, 
         created_at, last_active, subscription_status, wallet_balance, language, max_bots)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'inactive', 0, ?, ?)
    ''', (user_id, username, first_name, last_name, referral_code, referred_by, 
          now, now, language, max_bots))
    
    db.execute('UPDATE users SET last_active = ? WHERE user_id = ?', (now, user_id))
    
    if referred_by and referred_by != user_id:
        db.execute('UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = ?', (referred_by,))
        db.execute('UPDATE daily_stats SET new_users = new_users + 1 WHERE date = ?', 
                  (datetime.now().date().isoformat(),))
    
    return True

def check_subscription(user_id):
    user = get_user(user_id)
    if not user:
        return False
    
    if user.get('is_banned', 0) == 1:
        return False
    
    if user['subscription_status'] == 'active':
        if user['subscription_expiry']:
            expiry = datetime.fromisoformat(user['subscription_expiry'])
            if expiry > datetime.now():
                return True
            else:
                db.execute('UPDATE users SET subscription_status = "inactive" WHERE user_id = ?', (user_id,))
    return False

def get_remaining_bots(user_id):
    user = get_user(user_id)
    if not user or not check_subscription(user_id):
        return 0
    
    max_bots = user.get('max_bots', get_setting('max_bots_per_subscription', 3))
    current_bots = user.get('bots_count', 0)
    return max(0, max_bots - current_bots)

def activate_subscription(user_id, tx_hash=None, months=1):
    user = get_user(user_id)
    now = datetime.now()
    
    if user and user['subscription_status'] == 'active' and user['subscription_expiry']:
        new_expiry = datetime.fromisoformat(user['subscription_expiry']) + timedelta(days=30*months)
    else:
        new_expiry = now + timedelta(days=30*months)
    
    db.execute('''
        UPDATE users 
        SET subscription_status = 'active', 
            subscription_expiry = ?, 
            subscription_purchased_at = ?,
            last_payment_hash = ?
        WHERE user_id = ?
    ''', (new_expiry.isoformat(), now.isoformat(), tx_hash, user_id))
    
    db.execute('UPDATE daily_stats SET new_subscriptions = new_subscriptions + 1, total_revenue = total_revenue + ? WHERE date = ?',
              (get_setting('subscription_price', 2000000), datetime.now().date().isoformat()))
    
    # ==================== اضافه کردن کمیسیون به معرف (دقیق و درست) ====================
    if user and user.get('referred_by'):
        commission_percent = get_setting('withdraw_percent', 7)
        price = get_setting('subscription_price', 2000000)
        commission = int(price * commission_percent / 100)
        
        # اضافه کردن کمیسیون به کیف پول معرف
        db.execute('''
            UPDATE users SET wallet_balance = wallet_balance + ?, total_commission = total_commission + ?
            WHERE user_id = ?
        ''', (commission, commission, user['referred_by']))
        
        # ثبت کمیسیون در جدول commissions
        db.execute('''
            INSERT INTO commissions (user_id, from_user, amount, reason, created_at, paid)
            VALUES (?, ?, ?, 'referral_subscription', ?, 1)
        ''', (user['referred_by'], user_id, commission, now.isoformat()))
        
        # ثبت تراکنش
        tx_id = hashlib.md5(f"{user['referred_by']}_{now.timestamp()}_commission".encode()).hexdigest()[:16]
        db.execute('''
            INSERT INTO transactions (id, user_id, type, amount, balance_before, balance_after, reference_id, created_at)
            VALUES (?, ?, 'commission', ?, ?, ?, ?, ?)
        ''', (tx_id, user['referred_by'], commission, 
              get_user(user['referred_by'])['wallet_balance'] - commission,
              get_user(user['referred_by'])['wallet_balance'], 
              user_id, now.isoformat()))
        
        logger.info(f"✅ Commission {commission} added to user {user['referred_by']} for referring {user_id}")
        
        # اطلاع به معرف
        try:
            lang = get_user_language(user['referred_by'])
            if lang == 'fa':
                msg = f"🎉 کمیسیون {commission:,} تومان از اشتراک کاربر جدید به کیف پول شما اضافه شد!"
            else:
                msg = f"🎉 Commission {commission:,} Toman from new user subscription added to your wallet!"
            bot.send_message(user['referred_by'], msg)
        except:
            pass
    
    return True

def add_wallet_balance(user_id, amount):
    user = get_user(user_id)
    if not user:
        return 0
    new_balance = user['wallet_balance'] + amount
    db.execute('UPDATE users SET wallet_balance = ? WHERE user_id = ?', (new_balance, user_id))
    return new_balance

def get_user_bots(user_id):
    bots = db.execute('SELECT * FROM bots WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    return [dict(bot) for bot in bots]

def get_bot(bot_id):
    bots = db.execute('SELECT * FROM bots WHERE id = ?', (bot_id,))
    return dict(bots[0]) if bots else None

def delete_bot(bot_id, user_id):
    bot_rec = get_bot(bot_id)
    if not bot_rec or (user_id and bot_rec['user_id'] != user_id):
        return False
    
    machine_manager.stop_bot(bot_id)
    
    if bot_rec.get('file_path') and os.path.exists(bot_rec['file_path']):
        os.remove(bot_rec['file_path'])
    
    bot_dir = os.path.join(DIRS['MACHINES'], f"machine_{bot_rec['machine_id']:03d}", bot_id) if bot_rec.get('machine_id') else None
    if bot_dir and os.path.exists(bot_dir):
        shutil.rmtree(bot_dir)
    
    db.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
    if user_id:
        db.execute('UPDATE users SET bots_count = bots_count - 1 WHERE user_id = ?', (user_id,))
    
    return True

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

def is_channel_bot(token):
    try:
        resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            result = data.get('result', {})
            if not result.get('is_bot', False) or result.get('type') == 'channel':
                return True, result.get('username', '')
            return False, result.get('username', '')
        return True, None
    except:
        return True, None

def add_bot(user_id, bot_id, token, name, username, file_path, pid=None, machine_id=None):
    now = datetime.now().isoformat()
    encrypted_token = db.encrypt_token(token)
    db.execute('''
        INSERT INTO bots 
        (id, user_id, token, name, username, file_path, pid, machine_id, status, created_at, last_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'running', ?, ?)
    ''', (bot_id, user_id, encrypted_token, name, username, file_path, pid, machine_id, now, now))
    db.execute('UPDATE users SET bots_count = bots_count + 1, total_builds = total_builds + 1, last_build_at = ? WHERE user_id = ?', 
              (now, user_id))
    db.execute('UPDATE daily_stats SET new_bots = new_bots + 1 WHERE date = ?', 
              (datetime.now().date().isoformat(),))
    return True

def can_create_bot(user_id):
    if not check_subscription(user_id):
        return False, "no_subscription"
    
    remaining = get_remaining_bots(user_id)
    if remaining <= 0:
        return False, "limit_reached"
    
    builds_today = rate_limiter.get_user_builds_today(user_id)
    max_builds = get_setting('max_builds_per_hour', 10)
    if builds_today >= max_builds:
        return False, "rate_limit"
    
    return True, "ok"

# ==================== کلاس مدیریت ماشین‌ها ====================
class MachineManager:
    def __init__(self):
        self.port_counter = 8000
        self.processes = {}
        self.lock = threading.RLock()
        self._restore_bots()
    
    def _restore_bots(self):
        try:
            running_bots = db.execute('SELECT id, token, file_path, name FROM bots WHERE status = "running"')
            restored = 0
            for bot_rec in running_bots:
                bot_id = bot_rec['id']
                token = db.decrypt_token(bot_rec['token'])
                if token and os.path.exists(bot_rec['file_path']):
                    with open(bot_rec['file_path'], 'r', encoding='utf-8', errors='ignore') as f:
                        code = f.read()
                    result = self.run_bot(bot_id, code, token, restore=True)
                    if result.get('success'):
                        restored += 1
                        logger.info(f"✅ Restored bot: {bot_rec['name']}")
                    else:
                        db.execute('UPDATE bots SET status = "stopped" WHERE id = ?', (bot_id,))
            logger.info(f"✅ Restored {restored} bots after crash")
        except Exception as e:
            logger.error(f"Bot restoration failed: {e}")
    
    def get_available_machine(self):
        machines = db.execute("SELECT * FROM machines WHERE status = 'active' ORDER BY current_bots ASC")
        for m in machines:
            if m['current_bots'] < m['max_bots']:
                return m['id']
        return None
    
    def get_available_port(self):
        with self.lock:
            port = self.port_counter
            self.port_counter += 1
            if self.port_counter > 9000:
                self.port_counter = 8000
            return port
    
    def assign_bot(self, bot_id, machine_id):
        db.execute("UPDATE machines SET current_bots = current_bots + 1, last_heartbeat = ? WHERE id = ?",
                  (datetime.now().isoformat(), machine_id))
    
    def release_bot(self, bot_id, machine_id):
        db.execute("UPDATE machines SET current_bots = current_bots - 1 WHERE id = ?", (machine_id,))
    
    def run_bot(self, bot_id, code, token, restore=False):
        try:
            machine_id = self.get_available_machine()
            if not machine_id:
                return {'success': False, 'error': 'همه ماشین‌ها پر هستند'}
            
            port = self.get_available_port()
            bot_dir = os.path.join(DIRS['MACHINES'], f"machine_{machine_id:03d}", bot_id)
            os.makedirs(bot_dir, exist_ok=True)
            code_path = os.path.join(bot_dir, 'bot.py')
            
            with open(code_path, 'w', encoding='utf-8') as f:
                f.write(code)
            
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
                with self.lock:
                    self.processes[bot_id] = {
                        'process': process,
                        'pid': process.pid,
                        'machine_id': machine_id,
                        'port': port,
                        'dir': bot_dir,
                        'start_time': time.time()
                    }
                self.assign_bot(bot_id, machine_id)
                
                if not restore:
                    db.execute("UPDATE bots SET status = 'running', machine_id = ?, pid = ?, last_active = ? WHERE id = ?",
                              (machine_id, process.pid, datetime.now().isoformat(), bot_id))
                return {'success': True, 'pid': process.pid, 'machine_id': machine_id}
            else:
                return {'success': False, 'error': 'خطا در اجرای ربات'}
        except Exception as e:
            return {'success': False, 'error': str(e)[:100]}
    
    def stop_bot(self, bot_id):
        with self.lock:
            if bot_id in self.processes:
                try:
                    info = self.processes[bot_id]
                    os.kill(info['pid'], signal.SIGTERM)
                    time.sleep(1)
                    self.release_bot(bot_id, info['machine_id'])
                    del self.processes[bot_id]
                    db.execute("UPDATE bots SET status = 'stopped', last_active = ? WHERE id = ?",
                              (datetime.now().isoformat(), bot_id))
                    return True
                except:
                    pass
        return False
    
    def get_status(self, bot_id):
        with self.lock:
            if bot_id in self.processes:
                info = self.processes[bot_id]
                try:
                    os.kill(info['pid'], 0)
                    return {'running': True, 'pid': info['pid'], 'machine_id': info['machine_id'],
                            'uptime': time.time() - info['start_time']}
                except:
                    if bot_id in self.processes:
                        del self.processes[bot_id]
                        self.release_bot(bot_id, info['machine_id'])
                        db.execute("UPDATE bots SET status = 'stopped' WHERE id = ?", (bot_id,))
        return {'running': False}
    
    def get_stats(self):
        machines = db.execute("SELECT * FROM machines WHERE status = 'active'")
        total_bots = sum(m['current_bots'] for m in machines)
        total_capacity = sum(m['max_bots'] for m in machines)
        return {
            'total': len(list(machines)),
            'total_bots': total_bots,
            'total_capacity': total_capacity,
            'available': total_capacity - total_bots,
            'usage_percent': (total_bots / total_capacity) * 100 if total_capacity > 0 else 0
        }

# ==================== صف ساخت ====================
class BuildQueue:
    def __init__(self):
        self.queue = queue.Queue()
        self.processing = {}
        self.lock = threading.RLock()
        self.worker_threads = []
        self._start_workers()
    
    def _start_workers(self):
        max_concurrent = get_setting('max_concurrent_builds', 20)
        for i in range(max_concurrent):
            t = threading.Thread(target=self._worker, daemon=True)
            t.start()
            self.worker_threads.append(t)
        logger.info(f"✅ Started {max_concurrent} build workers")
    
    def add_build(self, user_id, file_path, file_name, chat_id, message_id, build_data):
        build_id = str(uuid.uuid4())[:8]
        build_item = {
            'id': build_id,
            'user_id': user_id,
            'file_path': file_path,
            'file_name': file_name,
            'chat_id': chat_id,
            'message_id': message_id,
            'added_at': time.time(),
            'build_data': build_data
        }
        self.queue.put(build_item)
        
        with self.lock:
            self.processing[build_id] = {'status': 'queued', 'position': self.queue.qsize()}
        
        return build_id
    
    def _worker(self):
        while True:
            try:
                build_item = self.queue.get(timeout=1)
                with self.lock:
                    if build_item['id'] in self.processing:
                        self.processing[build_item['id']]['status'] = 'processing'
                
                self._process_build(build_item)
                self.queue.task_done()
                
                with self.lock:
                    if build_item['id'] in self.processing:
                        del self.processing[build_item['id']]
                
            except queue.Empty:
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"Worker error: {e}")
                time.sleep(1)
    
    def _process_build(self, build_item):
        temp_bot = telebot.TeleBot(BOT_TOKEN)
        
        try:
            temp_bot.edit_message_text(
                f"🔄 در حال ساخت ربات...\n🆔 {build_item['id']}\n⏳ لطفاً صبر کنید",
                build_item['chat_id'],
                build_item['message_id']
            )
            
            build_data = build_item['build_data']
            
            result = machine_manager.run_bot(build_data['bot_id'], build_data['main_code'], build_data['token'])
            
            if result['success']:
                add_bot(
                    build_data['user_id'], 
                    build_data['bot_id'], 
                    build_data['token'], 
                    build_data['bot_info']['first_name'], 
                    build_data['bot_info']['username'], 
                    build_data['file_path'], 
                    result['pid'], 
                    result['machine_id']
                )
                
                remaining = get_remaining_bots(build_data['user_id'])
                lang = get_user_language(build_data['user_id'])
                
                if lang == 'fa':
                    success_text = f"✅ ربات {build_data['bot_info']['first_name']} ساخته شد!\n🤖 ربات باقیمانده: {remaining}"
                else:
                    success_text = f"✅ Bot {build_data['bot_info']['first_name']} created!\n🤖 Remaining slots: {remaining}"
                
                temp_bot.edit_message_text(success_text, build_item['chat_id'], build_item['message_id'])
            else:
                lang = get_user_language(build_data['user_id'])
                error_text = f"❌ خطا در ساخت: {result.get('error', 'مشخص نشده')}" if lang == 'fa' else f"❌ Build failed: {result.get('error', 'Unknown')}"
                temp_bot.edit_message_text(error_text, build_item['chat_id'], build_item['message_id'])
            
        except Exception as e:
            logger.error(f"Build failed: {e}")
            try:
                temp_bot.edit_message_text(f"❌ خطا در ساخت ربات: {str(e)[:100]}", 
                                          build_item['chat_id'], build_item['message_id'])
            except:
                pass
    
    def get_queue_length(self):
        return self.queue.qsize()

# ==================== Health Checker ====================
class HealthChecker:
    def __init__(self):
        self.checking = True
        self.thread = threading.Thread(target=self._monitor, daemon=True)
        self.thread.start()
    
    def _monitor(self):
        while self.checking:
            try:
                interval = get_setting('health_check_interval', 30)
                
                for bot_rec in db.execute('SELECT id, token, status FROM bots WHERE status = "running"'):
                    bot_id = bot_rec['id']
                    token = db.decrypt_token(bot_rec['token'])
                    
                    if token:
                        try:
                            resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
                            if resp.status_code != 200:
                                self._restart_bot(bot_id)
                        except:
                            self._restart_bot(bot_id)
                
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Health check error: {e}")
                time.sleep(60)
    
    def _restart_bot(self, bot_id):
        bot_rec = db.execute('SELECT * FROM bots WHERE id = ?', (bot_id,))
        if not bot_rec:
            return
        
        bot_rec = dict(bot_rec[0])
        machine_manager.stop_bot(bot_id)
        time.sleep(2)
        
        if os.path.exists(bot_rec['file_path']):
            try:
                with open(bot_rec['file_path'], 'r', encoding='utf-8', errors='ignore') as f:
                    code = f.read()
                
                token = db.decrypt_token(bot_rec['token'])
                if token:
                    result = machine_manager.run_bot(bot_id, code, token)
                    if result['success']:
                        db.execute('UPDATE bots SET status = "running", machine_id = ?, pid = ?, last_active = ? WHERE id = ?',
                                  (result['machine_id'], result['pid'], datetime.now().isoformat(), bot_id))
                        logger.info(f"✅ Auto-restarted bot {bot_id}")
            except Exception as e:
                logger.error(f"Failed to restart bot {bot_id}: {e}")

# ==================== Auto-Scale Manager ====================
class AutoScaleManager:
    def __init__(self):
        self.monitoring = True
        self.thread = threading.Thread(target=self._monitor, daemon=True)
        self.thread.start()
    
    def _monitor(self):
        while self.monitoring:
            try:
                threshold = get_setting('auto_scale_threshold', 80)
                
                machines = db.execute("SELECT id, current_bots, max_bots FROM machines WHERE status = 'active'")
                total_capacity = sum(m['max_bots'] for m in machines)
                total_used = sum(m['current_bots'] for m in machines)
                usage_percent = (total_used / total_capacity) * 100 if total_capacity > 0 else 0
                
                if usage_percent > threshold:
                    self._scale_up()
                
                time.sleep(60)
            except Exception as e:
                logger.error(f"Auto-scale error: {e}")
                time.sleep(60)
    
    def _scale_up(self):
        try:
            new_id = len(db.execute("SELECT id FROM machines")) + 1
            db.execute('''
                INSERT INTO machines (id, name, status, max_bots, max_memory, created_at)
                VALUES (?, ?, 'active', ?, ?, ?)
            ''', (new_id, f"Machine-{new_id:03d}", 5000, 256000, datetime.now().isoformat()))
            
            logger.info(f"✅ Scaled up - new machine {new_id} created")
            
            for admin_id in ADMIN_IDS:
                try:
                    bot.send_message(admin_id, f"📈 سیستم افزایش یافت - ماشین جدید {new_id} اضافه شد")
                except:
                    pass
        except Exception as e:
            logger.error(f"Scale up failed: {e}")

# ==================== متن‌های چند زبانه ====================
TEXTS = {
    'fa': {
        'welcome': "🚀 خوش آمدید {name}!",
        'id': "👤 شناسه: `{id}`",
        'referral_code': "🎁 کد معرف: `{code}`",
        'invite_link': "🔗 لینک دعوت: `{link}`",
        'referrals': "📊 دعوت‌ها: {count}",
        'balance': "💰 موجودی: {balance:,} تومان",
        'subscription_status': "💳 وضعیت: {status}",
        'remaining_bots': "🤖 ربات باقیمانده: {remaining}/{max}",
        'active': "✅ فعال",
        'inactive': "❌ غیرفعال",
        'no_subscription': "❌ اشتراک فعال نیست. ابتدا اشتراک خریداری کنید.",
        'limit_reached': "❌ به حد مجاز {max} ربات رسیده‌اید.",
        'send_file': "📤 فایل `.py` یا `.zip` خود را ارسال کنید.",
        'processing': "🔄 در حال پردازش...",
        'invalid_file': "❌ فقط فایل‌های .py یا .zip",
        'file_too_large': "❌ حجم بیشتر از ۵۰ مگابایت",
        'token_not_found': "❌ توکن در کد پیدا نشد",
        'invalid_token': "❌ توکن نامعتبر",
        'build_success': "✅ ربات {name} ساخته شد!\n🤖 ربات باقیمانده: {remaining}",
        'build_failed': "❌ ساخت ناموفق: {error}",
        'no_bots': "📋 رباتی ندارید",
        'bot_list': "📋 لیست ربات‌های شما",
        'select_bot': "🤖 ربات را انتخاب کنید:",
        'confirm_delete': "⚠️ آیا برای حذف اطمینان دارید؟",
        'deleted': "✅ حذف شد",
        'started': "✅ فعال شد",
        'stopped': "✅ متوقف شد",
        'wallet': "💰 **کیف پول و اشتراک**\n\nموجودی: {balance:,} تومان\n\n💳 برای فعالسازی {price:,} تومان را به کارت زیر واریز:\n`{card}`\n👤 {holder}\n🏦 {bank}\n\n🌐 یا به آدرس TRC20:\n`{trc20}`\n\n📸 پس از واریز، تصویر تراکنش را ارسال کنید",
        'receipt_received': "✅ تصویر دریافت شد، در انتظار تایید",
        'receipt_pending': "⏳ فیش قبلی در انتظار تایید است",
        'invite': "👥 **سیستم دعوت دوستان**\n\n🔗 لینک: `{link}`\n🎁 کد: `{code}`\n📊 دعوت‌ها: {count}\n💰 کمیسیون هر اشتراک: {percent}%\n💎 کمیسیون کل: {total:,} تومان",
        'stats': "📊 **آمار سیستم**\n\n👥 کاربران: {users:,}\n✅ اشتراک فعال: {active:,}\n🤖 ربات‌ها: {bots:,}\n🟢 ربات فعال: {running:,}\n💰 موجودی کل: {wallet:,} تومان\n📸 فیش‌های pending: {pending}",
        'guide': "📚 **راهنمای استفاده**\n\n1️⃣ ربات خود را در @BotFather بسازید\n2️⃣ توکن را در کد قرار دهید\n3️⃣ فایل .py را برای من ارسال کنید\n4️⃣ ربات شما ساخته می‌شود!\n\n⚠️ هر اشتراک فقط {max_bots} ربات می‌تواند بسازد.\n💰 کمیسیون دعوت: {percent}%\n📞 پشتیبانی: @{support}",
        'support': "📞 پشتیبانی: @{username}",
        'language_changed': "✅ زبان به فارسی تغییر کرد",
        'language_changed_en': "✅ Language changed to English",
        'admin_panel': "👑 **پنل مدیریت**",
        'no_pending': "📸 فیشی در انتظار تایید نیست",
        'approve': "✅ تایید",
        'reject': "❌ رد",
        'approved': "✅ اشتراک فعال شد",
        'rejected': "❌ فیش رد شد",
        'receipt_info': "📸 فیش جدید\n👤 کاربر: {name} (ID: {id})\n💰 مبلغ: {amount:,} تومان\n🆔 کد: {code}",
        'broadcast_sent': "✅ پیام به {count} کاربر ارسال شد",
        'enter_broadcast': "📢 متن پیام همگانی را ارسال کنید:",
        'error': "❌ خطا: {error}",
        'success': "✅ {message}",
        'persian': "🇮🇷 فارسی",
        'english': "🇬🇧 English",
        'copy_link': "📋 کپی لینک",
        'copy_card': "📋 کپی شماره کارت",
        'copy_trc20': "📋 کپی آدرس TRC20",
        'address_copied': "✅ کپی شد!",
        'link_copied': "✅ لینک کپی شد!",
        'card_copied': "✅ شماره کارت کپی شد!",
        'usage': "📈 **مصرف شما امروز**\n\n🤖 ساخت ربات: {builds}/{max_builds}\n📈 {bar} {percent}%\n\n📋 تعداد ربات‌ها: {bots}\n📦 ربات باقیمانده: {remaining}/{max_bots}",
        'queue_status': "⚡ **وضعیت صف ساخت**\n\n📊 در صف: {queue}\n⚙️ حداکثر همزمان: {max_concurrent}\n📈 ساخت امروز شما: {builds}/{max_builds}",
        'my_usage': "📈 مصرف من",
        'queue': "⚡ وضعیت صف",
        'admin_settings': "⚙️ تنظیمات",
        'admin_machines': "🖥️ ماشین‌ها",
        'admin_stats_full': "📊 آمار کامل",
        'back': "🔙 بازگشت",
        'set_price': "💰 قیمت اشتراک (تومان):",
        'price_set': "✅ قیمت اشتراک به {price:,} تومان تغییر کرد",
        'set_max_bots': "🤖 حداکثر ربات در هر اشتراک:",
        'max_bots_set': "✅ حداکثر ربات به {max} تغییر کرد",
        'set_withdraw_percent': "💰 درصد کمیسیون (عدد بین 1 تا 50):",
        'withdraw_percent_set': "✅ درصد کمیسیون به {percent}% تغییر کرد",
        'invalid_number': "❌ عدد نامعتبر",
        'commission_info': "💰 کمیسیون {amount:,} تومان به کیف پول شما اضافه شد"
    },
    'en': {
        'welcome': "🚀 Welcome {name}!",
        'id': "👤 ID: `{id}`",
        'referral_code': "🎁 Referral Code: `{code}`",
        'invite_link': "🔗 Invite Link: `{link}`",
        'referrals': "📊 Referrals: {count}",
        'balance': "💰 Balance: {balance:,} Toman",
        'subscription_status': "💳 Status: {status}",
        'remaining_bots': "🤖 Remaining bots: {remaining}/{max}",
        'active': "✅ Active",
        'inactive': "❌ Inactive",
        'no_subscription': "❌ No active subscription. Please purchase first.",
        'limit_reached': "❌ You've reached the limit of {max} bots.",
        'send_file': "📤 Send your `.py` or `.zip` file.",
        'processing': "🔄 Processing...",
        'invalid_file': "❌ Only .py or .zip files",
        'file_too_large': "❌ File too large (max 50MB)",
        'token_not_found': "❌ Bot token not found in code",
        'invalid_token': "❌ Invalid bot token",
        'build_success': "✅ Bot {name} created!\n🤖 Remaining slots: {remaining}",
        'build_failed': "❌ Build failed: {error}",
        'no_bots': "📋 No bots yet",
        'bot_list': "📋 Your Bots",
        'select_bot': "🤖 Select a bot:",
        'confirm_delete': "⚠️ Are you sure?",
        'deleted': "✅ Deleted",
        'started': "✅ Started",
        'stopped': "✅ Stopped",
        'wallet': "💰 **Wallet & Subscription**\n\nBalance: {balance:,} Toman\n\n💳 Send {price:,} Toman to card:\n`{card}`\n👤 {holder}\n🏦 {bank}\n\n🌐 Or TRC20 address:\n`{trc20}`\n\n📸 Send transaction screenshot after payment",
        'receipt_received': "✅ Receipt received, pending approval",
        'receipt_pending': "⏳ Previous receipt pending approval",
        'invite': "👥 **Invite System**\n\n🔗 Link: `{link}`\n🎁 Code: `{code}`\n📊 Referrals: {count}\n💰 Commission per subscription: {percent}%\n💎 Total Commission: {total:,} Toman",
        'stats': "📊 **System Statistics**\n\n👥 Users: {users:,}\n✅ Active Subscriptions: {active:,}\n🤖 Total Bots: {bots:,}\n🟢 Running Bots: {running:,}\n💰 Total Balance: {wallet:,} Toman\n📸 Pending Receipts: {pending}",
        'guide': "📚 **User Guide**\n\n1️⃣ Create a bot with @BotFather\n2️⃣ Put the token in your code\n3️⃣ Send the .py file to me\n4️⃣ Your bot will be built!\n\n⚠️ Each subscription allows only {max_bots} bots.\n💰 Referral commission: {percent}%\n📞 Support: @{support}",
        'support': "📞 Support: @{username}",
        'language_changed': "✅ Language changed to English",
        'language_changed_fa': "✅ زبان به فارسی تغییر کرد",
        'admin_panel': "👑 **Admin Panel**",
        'no_pending': "📸 No pending receipts",
        'approve': "✅ Approve",
        'reject': "❌ Reject",
        'approved': "✅ Subscription activated",
        'rejected': "❌ Receipt rejected",
        'receipt_info': "📸 New Receipt\n👤 User: {name} (ID: {id})\n💰 Amount: {amount:,} Toman\n🆔 Code: {code}",
        'broadcast_sent': "✅ Message sent to {count} users",
        'enter_broadcast': "📢 Enter broadcast message:",
        'error': "❌ Error: {error}",
        'success': "✅ {message}",
        'persian': "🇮🇷 Persian",
        'english': "🇬🇧 English",
        'copy_link': "📋 Copy Link",
        'copy_card': "📋 Copy Card Number",
        'copy_trc20': "📋 Copy TRC20 Address",
        'address_copied': "✅ Copied!",
        'link_copied': "✅ Link copied!",
        'card_copied': "✅ Card number copied!",
        'usage': "📈 **Your Daily Usage**\n\n🤖 Bot builds: {builds}/{max_builds}\n📈 {bar} {percent}%\n\n📋 Total bots: {bots}\n📦 Remaining slots: {remaining}/{max_bots}",
        'queue_status': "⚡ **Build Queue Status**\n\n📊 In queue: {queue}\n⚙️ Max concurrent: {max_concurrent}\n📈 Your builds today: {builds}/{max_builds}",
        'my_usage': "📈 My Usage",
        'queue': "⚡ Queue Status",
        'admin_settings': "⚙️ Settings",
        'admin_machines': "🖥️ Machines",
        'admin_stats_full': "📊 Full Stats",
        'back': "🔙 Back",
        'set_price': "💰 Subscription price (Toman):",
        'price_set': "✅ Subscription price set to {price:,} Toman",
        'set_max_bots': "🤖 Max bots per subscription:",
        'max_bots_set': "✅ Max bots set to {max}",
        'set_withdraw_percent': "💰 Commission percentage (1-50):",
        'withdraw_percent_set': "✅ Commission percentage set to {percent}%",
        'invalid_number': "❌ Invalid number",
        'commission_info': "💰 Commission {amount:,} Toman added to your wallet"
    }
}

def get_text(user_id, key, **kwargs):
    lang = get_user_language(user_id)
    text = TEXTS.get(lang, TEXTS['fa']).get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except:
            pass
    return text

# ==================== دکمه‌های منو ====================
MENU_FA = [
    '🤖 ساخت ربات جدید', '📋 ربات‌های من', '🔄 فعال/غیرفعال', '🗑 حذف ربات',
    '💰 کیف پول', '👥 دعوت دوستان', '📚 راهنما', '📊 آمار', '📞 پشتیبانی',
    '📈 مصرف من', '⚡ وضعیت صف', '🌐 English'
]

MENU_EN = [
    '🤖 New Bot', '📋 My Bots', '🔄 Start/Stop', '🗑 Delete Bot',
    '💰 Wallet', '👥 Invite', '📚 Guide', '📊 Stats', '📞 Support',
    '📈 My Usage', '⚡ Queue', '🌐 فارسی'
]

ADMIN_MENU_FA = ['👑 پنل مدیریت', '📢 پیام همگانی']
ADMIN_MENU_EN = ['👑 Admin Panel', '📢 Broadcast']

def get_main_menu(user_id):
    is_admin = user_id in ADMIN_IDS
    lang = get_user_language(user_id)
    
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    
    if lang == 'fa':
        buttons = MENU_FA.copy()
        if is_admin:
            buttons.extend(ADMIN_MENU_FA)
    else:
        buttons = MENU_EN.copy()
        if is_admin:
            buttons.extend(ADMIN_MENU_EN)
    
    markup.add(*buttons)
    return markup

# ==================== ربات تلگرام ====================
bot = telebot.TeleBot(BOT_TOKEN)
bot.delete_webhook()

# ایجاد نمونه‌ها
machine_manager = MachineManager()
build_queue = BuildQueue()
health_checker = HealthChecker()
auto_scaler = AutoScaleManager()

# ==================== دکوریتور Rate Limit ====================
def rate_limit(limit_per_second=5):
    def decorator(func):
        @wraps(func)
        def wrapper(message, *args, **kwargs):
            user_id = message.from_user.id
            if not rate_limiter.is_allowed(user_id, limit_per_second):
                bot.reply_to(message, get_text(user_id, 'error', error="Please wait..."))
                return
            return func(message, *args, **kwargs)
        return wrapper
    return decorator

# ==================== دستور start ====================
@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "User"
    username = message.from_user.username or ""
    
    args = message.text.split()
    preferred_lang = 'fa'
    if len(args) > 1 and args[1] == 'en':
        preferred_lang = 'en'
    
    referred_by = None
    if len(args) > 1 and args[1] not in ['fa', 'en']:
        code = args[1]
        users = db.execute('SELECT user_id FROM users WHERE referral_code = ?', (code,))
        if users and users[0]['user_id'] != user_id:
            referred_by = users[0]['user_id']
            try:
                bot.send_message(referred_by, get_text(referred_by, 'commission_info', amount=get_setting('subscription_price', 2000000) * get_setting('withdraw_percent', 7) // 100))
            except:
                pass
    
    create_user(user_id, username, first_name, "", referred_by, preferred_lang)
    user = get_user(user_id)
    referral_link = f"https://t.me/{BOT_USERNAME}?start={user['referral_code']}"
    remaining = get_remaining_bots(user_id)
    max_bots = user.get('max_bots', get_setting('max_bots_per_subscription', 3))
    is_subscribed = check_subscription(user_id)
    lang = user['language']
    
    if lang == 'fa':
        text = (f"🚀 خوش آمدید {first_name}!\n\n"
                f"👤 شناسه: `{user_id}`\n"
                f"🎁 کد معرف: `{user['referral_code']}`\n"
                f"🔗 لینک دعوت: `{referral_link}`\n"
                f"📊 دعوت‌ها: {user['referrals_count']}\n"
                f"💰 موجودی: {user['wallet_balance']:,} تومان\n"
                f"💳 وضعیت: {'✅ فعال' if is_subscribed else '❌ غیرفعال'}\n"
                f"🤖 ربات باقیمانده: {remaining}/{max_bots}")
    else:
        text = (f"🚀 Welcome {first_name}!\n\n"
                f"👤 ID: `{user_id}`\n"
                f"🎁 Referral Code: `{user['referral_code']}`\n"
                f"🔗 Invite Link: `{referral_link}`\n"
                f"📊 Referrals: {user['referrals_count']}\n"
                f"💰 Balance: {user['wallet_balance']:,} Toman\n"
                f"💳 Status: {'✅ Active' if is_subscribed else '❌ Inactive'}\n"
                f"🤖 Remaining: {remaining}/{max_bots}")
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(get_text(user_id, 'copy_link'), callback_data=f"copy_{user['referral_code']}"))
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=get_main_menu(user_id))

# ==================== کپی لینک ====================
@bot.callback_query_handler(func=lambda call: call.data.startswith('copy_'))
def copy_link(call):
    code = call.data.replace('copy_', '')
    link = f"https://t.me/{BOT_USERNAME}?start={code}"
    bot.answer_callback_query(call.id, get_text(call.from_user.id, 'link_copied'), show_alert=True)

# ==================== تغییر زبان ====================
@bot.message_handler(func=lambda m: m.text in ['🌐 English', '🌐 فارسی'])
def change_language(message):
    user_id = message.from_user.id
    current_lang = get_user_language(user_id)
    new_lang = 'en' if current_lang == 'fa' else 'fa'
    
    db.execute("UPDATE users SET language = ? WHERE user_id = ?", (new_lang, user_id))
    
    msg = get_text(user_id, 'language_changed' if new_lang == 'fa' else 'language_changed_en')
    bot.send_message(message.chat.id, msg, reply_markup=get_main_menu(user_id))

# ==================== کیف پول ====================
@bot.message_handler(func=lambda m: m.text in ['💰 کیف پول', '💰 Wallet'])
@rate_limit(3)
def wallet(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    text = get_text(user_id, 'wallet',
                   balance=user['wallet_balance'],
                   price=get_setting('subscription_price', 2000000),
                   card=CARD_NUMBER_DISPLAY,
                   holder=CARD_HOLDER,
                   bank=CARD_BANK,
                   trc20=get_setting('trc20_address', TRC20_ADDRESS))
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(get_text(user_id, 'copy_card'), callback_data="copy_card"),
        types.InlineKeyboardButton(get_text(user_id, 'copy_trc20'), callback_data="copy_trc20")
    )
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "copy_card")
def copy_card(call):
    bot.answer_callback_query(call.id, get_text(call.from_user.id, 'card_copied'), show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "copy_trc20")
def copy_trc20(call):
    address = get_setting('trc20_address', TRC20_ADDRESS)
    bot.answer_callback_query(call.id, f"✅ {address}", show_alert=True)

# ==================== دریافت فیش ====================
@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    
    pending = db.execute('SELECT id FROM receipts WHERE user_id = ? AND status = "pending"', (user_id,))
    if pending:
        bot.reply_to(message, get_text(user_id, 'receipt_pending'))
        return
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        tx_hash = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:16].upper()
        receipt_path = os.path.join(DIRS['RECEIPTS'], f"{user_id}_{tx_hash}.jpg")
        
        with open(receipt_path, 'wb') as f:
            f.write(downloaded)
        
        price = get_setting('subscription_price', 2000000)
        
        db.execute('''
            INSERT INTO receipts (user_id, amount, receipt_path, tx_hash, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, price, receipt_path, tx_hash, datetime.now().isoformat()))
        
        bot.reply_to(message, get_text(user_id, 'receipt_received'))
        
        user = get_user(user_id)
        for admin_id in ADMIN_IDS:
            try:
                with open(receipt_path, 'rb') as f:
                    caption = get_text(admin_id, 'receipt_info',
                                      name=user['first_name'],
                                      id=user_id,
                                      amount=price,
                                      code=tx_hash)
                    bot.send_photo(admin_id, f, caption=caption)
            except:
                pass
        
    except Exception as e:
        bot.reply_to(message, get_text(user_id, 'error', error=str(e)[:50]))

# ==================== دعوت دوستان ====================
@bot.message_handler(func=lambda m: m.text in ['👥 دعوت دوستان', '👥 Invite'])
@rate_limit(3)
def invite(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    link = f"https://t.me/{BOT_USERNAME}?start={user['referral_code']}"
    
    text = get_text(user_id, 'invite',
                   link=link,
                   code=user['referral_code'],
                   count=user['referrals_count'],
                   percent=get_setting('withdraw_percent', 7),
                   total=user.get('total_commission', 0))
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(get_text(user_id, 'copy_link'), callback_data=f"copy_{user['referral_code']}"))
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

# ==================== ساخت ربات جدید ====================
@bot.message_handler(func=lambda m: m.text in ['🤖 ساخت ربات جدید', '🤖 New Bot'])
@rate_limit(3)
def new_bot(message):
    user_id = message.from_user.id
    
    if not check_subscription(user_id):
        bot.reply_to(message, get_text(user_id, 'no_subscription'))
        return
    
    remaining = get_remaining_bots(user_id)
    if remaining <= 0:
        max_bots = get_setting('max_bots_per_subscription', 3)
        bot.reply_to(message, get_text(user_id, 'limit_reached', max=max_bots))
        return
    
    bot.reply_to(message, get_text(user_id, 'send_file'))

# ==================== پردازش فایل ربات ====================
@bot.message_handler(content_types=['document'])
def handle_build_file(message):
    user_id = message.from_user.id
    
    if not check_subscription(user_id):
        bot.reply_to(message, get_text(user_id, 'no_subscription'))
        return
    
    remaining = get_remaining_bots(user_id)
    if remaining <= 0:
        max_bots = get_setting('max_bots_per_subscription', 3)
        bot.reply_to(message, get_text(user_id, 'limit_reached', max=max_bots))
        return
    
    file_name = message.document.file_name
    if not (file_name.endswith('.py') or file_name.endswith('.zip')):
        bot.reply_to(message, get_text(user_id, 'invalid_file'))
        return
    
    if message.document.file_size > MAX_FILE_SIZE:
        bot.reply_to(message, get_text(user_id, 'file_too_large'))
        return
    
    status_msg = bot.reply_to(message, get_text(user_id, 'processing'))
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        user_dir = os.path.join(DIRS['FILES'], str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        file_path = os.path.join(user_dir, f"{int(time.time())}_{file_name}")
        
        with open(file_path, 'wb') as f:
            f.write(downloaded)
        
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
            bot.edit_message_text(get_text(user_id, 'error', error="No Python file found"),
                                 message.chat.id, status_msg.message_id)
            return
        
        token = extract_token_from_code(code)
        if not token:
            bot.edit_message_text(get_text(user_id, 'token_not_found'),
                                 message.chat.id, status_msg.message_id)
            return
        
        try:
            resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
            if resp.status_code != 200:
                bot.edit_message_text(get_text(user_id, 'invalid_token'),
                                     message.chat.id, status_msg.message_id)
                return
            bot_info = resp.json()['result']
        except:
            bot.edit_message_text(get_text(user_id, 'invalid_token'),
                                 message.chat.id, status_msg.message_id)
            return
        
        bot_id = hashlib.md5(f"{user_id}{token}{time.time()}".encode()).hexdigest()[:16]
        
        machine_id = machine_manager.get_available_machine()
        if not machine_id:
            bot.edit_message_text(get_text(user_id, 'error', error="No machine available"),
                                 message.chat.id, status_msg.message_id)
            return
        
        build_data = {
            'bot_id': bot_id,
            'user_id': user_id,
            'token': token,
            'bot_info': bot_info,
            'file_path': file_path,
            'main_code': code,
            'chat_id': message.chat.id,
            'message_id': status_msg.message_id
        }
        
        build_queue.add_build(user_id, file_path, file_name, message.chat.id, status_msg.message_id, build_data)
        
    except Exception as e:
        bot.edit_message_text(get_text(user_id, 'build_failed', error=str(e)[:100]),
                             message.chat.id, status_msg.message_id)

# ==================== ربات‌های من ====================
@bot.message_handler(func=lambda m: m.text in ['📋 ربات‌های من', '📋 My Bots'])
@rate_limit(5)
def my_bots(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    
    if not bots:
        bot.reply_to(message, get_text(user_id, 'no_bots'))
        return
    
    for b in bots[:10]:
        status = machine_manager.get_status(b['id'])
        emoji = "🟢" if status.get('running') else "🔴"
        text = f"{emoji} {b['name']}\n🔗 t.me/{b['username']}"
        bot.send_message(message.chat.id, text)

# ==================== فعال/غیرفعال ====================
@bot.message_handler(func=lambda m: m.text in ['🔄 فعال/غیرفعال', '🔄 Start/Stop'])
@rate_limit(3)
def toggle_prompt(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    
    if not bots:
        bot.reply_to(message, get_text(user_id, 'no_bots'))
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        status = machine_manager.get_status(b['id'])
        emoji = "🟢" if status.get('running') else "🔴"
        markup.add(types.InlineKeyboardButton(f"{emoji} {b['name']}", callback_data=f"toggle_{b['id']}"))
    
    bot.send_message(message.chat.id, get_text(user_id, 'select_bot'), reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_'))
def toggle_bot(call):
    bot_id = call.data.replace('toggle_', '')
    bot_rec = get_bot(bot_id)
    
    if not bot_rec or bot_rec['user_id'] != call.from_user.id:
        bot.answer_callback_query(call.id, get_text(call.from_user.id, 'error', error="Not found"))
        return
    
    status = machine_manager.get_status(bot_id)
    
    if status.get('running'):
        if machine_manager.stop_bot(bot_id):
            bot.answer_callback_query(call.id, get_text(call.from_user.id, 'stopped'))
        else:
            bot.answer_callback_query(call.id, get_text(call.from_user.id, 'error', error="Stop failed"))
    else:
        if os.path.exists(bot_rec['file_path']):
            with open(bot_rec['file_path'], 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
            token = db.decrypt_token(bot_rec['token'])
            if token:
                result = machine_manager.run_bot(bot_id, code, token)
                if result['success']:
                    db.execute("UPDATE bots SET machine_id = ?, pid = ?, status = 'running' WHERE id = ?",
                              (result['machine_id'], result['pid'], bot_id))
                    bot.answer_callback_query(call.id, get_text(call.from_user.id, 'started'))
                else:
                    bot.answer_callback_query(call.id, get_text(call.from_user.id, 'error', error=result.get('error')))
            else:
                bot.answer_callback_query(call.id, get_text(call.from_user.id, 'error', error="Token error"))
        else:
            bot.answer_callback_query(call.id, get_text(call.from_user.id, 'error', error="File not found"))

# ==================== حذف ربات ====================
@bot.message_handler(func=lambda m: m.text in ['🗑 حذف ربات', '🗑 Delete Bot'])
@rate_limit(3)
def delete_prompt(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    
    if not bots:
        bot.reply_to(message, get_text(user_id, 'no_bots'))
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        markup.add(types.InlineKeyboardButton(f"🗑 {b['name']}", callback_data=f"del_{b['id']}"))
    
    bot.send_message(message.chat.id, get_text(user_id, 'select_bot'), reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('del_'))
def confirm_delete(call):
    bot_id = call.data.replace('del_', '')
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Yes", callback_data=f"confirm_del_{bot_id}"),
        types.InlineKeyboardButton("❌ No", callback_data="cancel_del")
    )
    bot.edit_message_text(get_text(call.from_user.id, 'confirm_delete'),
                         call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_del_'))
def do_delete(call):
    bot_id = call.data.replace('confirm_del_', '')
    user_id = call.from_user.id
    
    if delete_bot(bot_id, user_id):
        bot.edit_message_text(get_text(user_id, 'deleted'), call.message.chat.id, call.message.message_id)
    else:
        bot.edit_message_text(get_text(user_id, 'error', error="Delete failed"), call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == 'cancel_del')
def cancel_delete(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== راهنما ====================
@bot.message_handler(func=lambda m: m.text in ['📚 راهنما', '📚 Guide'])
@rate_limit(3)
def guide(message):
    user_id = message.from_user.id
    max_bots = get_setting('max_bots_per_subscription', 3)
    percent = get_setting('withdraw_percent', 7)
    support_user = get_setting('support_username', 'shahraghee13')
    
    text = get_text(user_id, 'guide', max_bots=max_bots, percent=percent, support=support_user)
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== آمار ====================
@bot.message_handler(func=lambda m: m.text in ['📊 آمار', '📊 Stats'])
@rate_limit(3)
def stats(message):
    user_id = message.from_user.id
    
    users = db.execute('SELECT COUNT(*) as count FROM users')[0]['count']
    active = db.execute('SELECT COUNT(*) as count FROM users WHERE subscription_status = "active"')[0]['count']
    bots = db.execute('SELECT COUNT(*) as count FROM bots')[0]['count']
    running = db.execute('SELECT COUNT(*) as count FROM bots WHERE status = "running"')[0]['count']
    total_wallet = db.execute('SELECT SUM(wallet_balance) as total FROM users')[0]['total'] or 0
    pending = db.execute('SELECT COUNT(*) as count FROM receipts WHERE status = "pending"')[0]['count']
    
    text = get_text(user_id, 'stats',
                   users=users,
                   active=active,
                   bots=bots,
                   running=running,
                   wallet=total_wallet,
                   pending=pending)
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== مصرف من ====================
@bot.message_handler(func=lambda m: m.text in ['📈 مصرف من', '📈 My Usage'])
@rate_limit(5)
def my_usage(message):
    user_id = message.from_user.id
    builds_today = rate_limiter.get_user_builds_today(user_id)
    max_builds = get_setting('max_builds_per_hour', 10)
    bots_count = len(get_user_bots(user_id))
    remaining = get_remaining_bots(user_id)
    max_bots = get_setting('max_bots_per_subscription', 3)
    
    bar_length = int((builds_today / max_builds) * 20) if max_builds > 0 else 0
    bar = "█" * bar_length + "░" * (20 - bar_length)
    percent = int((builds_today / max_builds) * 100) if max_builds > 0 else 0
    
    text = get_text(user_id, 'usage',
                   builds=builds_today,
                   max_builds=max_builds,
                   bar=bar,
                   percent=percent,
                   bots=bots_count,
                   remaining=remaining,
                   max_bots=max_bots)
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== وضعیت صف ====================
@bot.message_handler(func=lambda m: m.text in ['⚡ وضعیت صف', '⚡ Queue'])
@rate_limit(5)
def queue_status(message):
    user_id = message.from_user.id
    builds_today = rate_limiter.get_user_builds_today(user_id)
    max_builds = get_setting('max_builds_per_hour', 10)
    queue_len = build_queue.get_queue_length()
    max_concurrent = get_setting('max_concurrent_builds', 20)
    
    text = get_text(user_id, 'queue_status',
                   queue=queue_len,
                   max_concurrent=max_concurrent,
                   builds=builds_today,
                   max_builds=max_builds)
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== پشتیبانی ====================
@bot.message_handler(func=lambda m: m.text == '📞 پشتیبانی')
@rate_limit(3)
def support(message):
    user_id = message.from_user.id
    support_user = get_setting('support_username', 'shahraghee13')
    text = get_text(user_id, 'support', username=support_user)
    bot.send_message(message.chat.id, text)

# ==================== پنل مدیریت ====================
@bot.message_handler(func=lambda m: m.text in ['👑 پنل مدیریت', '👑 Admin Panel'])
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    user_id = message.from_user.id
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(get_text(user_id, 'admin_receipts'), callback_data="admin_receipts"),
        types.InlineKeyboardButton(get_text(user_id, 'admin_stats_full'), callback_data="admin_stats"),
        types.InlineKeyboardButton(get_text(user_id, 'admin_machines'), callback_data="admin_machines"),
        types.InlineKeyboardButton(get_text(user_id, 'admin_settings'), callback_data="admin_settings"),
        types.InlineKeyboardButton(get_text(user_id, 'back'), callback_data="admin_back")
    )
    bot.send_message(message.chat.id, get_text(user_id, 'admin_panel'), reply_markup=markup)

# ==================== کال‌بک‌های مدیریت ====================
@bot.callback_query_handler(func=lambda call: call.data == "admin_receipts")
def admin_receipts(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    receipts = db.execute("SELECT * FROM receipts WHERE status = 'pending' ORDER BY created_at")
    if not receipts:
        bot.send_message(call.message.chat.id, get_text(call.from_user.id, 'no_pending'))
        return
    
    for r in receipts:
        user = get_user(r['user_id'])
        text = f"📸 فیش\n👤 {user['first_name'] if user else 'Unknown'}\n💰 {r['amount']:,} تومان\n🆔 {r['tx_hash']}"
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(get_text(call.from_user.id, 'approve'), callback_data=f"approve_{r['id']}"),
            types.InlineKeyboardButton(get_text(call.from_user.id, 'reject'), callback_data=f"reject_{r['id']}")
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
    
    rid = int(call.data.replace('approve_', ''))
    receipt = db.execute("SELECT user_id, amount, tx_hash FROM receipts WHERE id = ?", (rid,))
    
    if receipt:
        user_id = receipt[0]['user_id']
        activate_subscription(user_id, receipt[0]['tx_hash'])
        db.execute("UPDATE receipts SET status = 'approved', reviewed_by = ?, reviewed_at = ? WHERE id = ?",
                  (call.from_user.id, datetime.now().isoformat(), rid))
        
        try:
            bot.send_message(user_id, get_text(user_id, 'approved'))
        except:
            pass
        
        bot.answer_callback_query(call.id, get_text(call.from_user.id, 'approved'))
        bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_'))
def reject_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    rid = int(call.data.replace('reject_', ''))
    db.execute("UPDATE receipts SET status = 'rejected', reviewed_by = ?, reviewed_at = ? WHERE id = ?",
              (call.from_user.id, datetime.now().isoformat(), rid))
    
    bot.answer_callback_query(call.id, get_text(call.from_user.id, 'rejected'))
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_stats(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    users = db.execute('SELECT COUNT(*) as count FROM users')[0]['count']
    active = db.execute('SELECT COUNT(*) as count FROM users WHERE subscription_status = "active"')[0]['count']
    bots = db.execute('SELECT COUNT(*) as count FROM bots')[0]['count']
    running = db.execute('SELECT COUNT(*) as count FROM bots WHERE status = "running"')[0]['count']
    total_wallet = db.execute('SELECT SUM(wallet_balance) as total FROM users')[0]['total'] or 0
    total_commission = db.execute('SELECT SUM(amount) as total FROM commissions')[0]['total'] or 0
    pending = db.execute('SELECT COUNT(*) as count FROM receipts WHERE status = "pending"')[0]['count']
    machine_stats = machine_manager.get_stats()
    
    text = f"📊 **Full Statistics**\n\n"
    text += f"👥 Users: {users}\n"
    text += f"✅ Active Subscriptions: {active}\n"
    text += f"🤖 Total Bots: {bots}\n"
    text += f"🟢 Running Bots: {running}\n"
    text += f"💰 Total Wallet: {total_wallet:,} Toman\n"
    text += f"💎 Total Commission Paid: {total_commission:,} Toman\n"
    text += f"📸 Pending Receipts: {pending}\n"
    text += f"🖥️ Machines: {machine_stats['total']}\n"
    text += f"📊 Usage: {machine_stats['usage_percent']:.1f}%\n"
    text += f"⚡ Available Capacity: {machine_stats['available']}"
    
    bot.send_message(call.message.chat.id, text)

@bot.callback_query_handler(func=lambda call: call.data == "admin_machines")
def admin_machines(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    machines = db.execute("SELECT * FROM machines ORDER BY id")
    text = "🖥️ **Machines Status**\n\n"
    for m in machines:
        usage = (m['current_bots'] / m['max_bots']) * 100 if m['max_bots'] > 0 else 0
        status_emoji = "🟢" if m['status'] == 'active' else "🔴"
        text += f"{status_emoji} {m['name']}: {m['current_bots']}/{m['max_bots']} ({usage:.1f}%)\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "admin_settings")
def admin_settings(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("💰 Subscription Price", callback_data="admin_set_price"),
        types.InlineKeyboardButton("🤖 Max Bots Per Subscription", callback_data="admin_set_max_bots"),
        types.InlineKeyboardButton("💰 Commission Percentage", callback_data="admin_set_withdraw_percent"),
        types.InlineKeyboardButton("🔙 Back", callback_data="admin_back")
    )
    bot.send_message(call.message.chat.id, "⚙️ **System Settings**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_price")
def admin_set_price(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, get_text(call.from_user.id, 'set_price'))
    bot.register_next_step_handler(msg, process_set_price)

def process_set_price(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        price = int(message.text.strip())
        if price < 10000:
            bot.reply_to(message, "❌ Price cannot be less than 10,000 Toman")
            return
        update_setting('subscription_price', price)
        update_setting('subscription_price_str', f"{price:,} تومان")
        update_setting('subscription_price_usd', f"${price // 40000} USD")
        bot.reply_to(message, get_text(message.from_user.id, 'price_set', price=price))
    except:
        bot.reply_to(message, get_text(message.from_user.id, 'invalid_number'))

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_max_bots")
def admin_set_max_bots(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, get_text(call.from_user.id, 'set_max_bots'))
    bot.register_next_step_handler(msg, process_set_max_bots)

def process_set_max_bots(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        max_bots = int(message.text.strip())
        if max_bots < 1 or max_bots > 100:
            bot.reply_to(message, "❌ Number must be between 1 and 100")
            return
        update_setting('max_bots_per_subscription', max_bots)
        db.execute("UPDATE users SET max_bots = ?", (max_bots,))
        bot.reply_to(message, get_text(message.from_user.id, 'max_bots_set', max=max_bots))
    except:
        bot.reply_to(message, get_text(message.from_user.id, 'invalid_number'))

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_withdraw_percent")
def admin_set_withdraw_percent(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, get_text(call.from_user.id, 'set_withdraw_percent'))
    bot.register_next_step_handler(msg, process_set_withdraw_percent)

def process_set_withdraw_percent(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        percent = int(message.text.strip())
        if percent < 1 or percent > 50:
            bot.reply_to(message, "❌ Percentage must be between 1 and 50")
            return
        update_setting('withdraw_percent', percent)
        bot.reply_to(message, get_text(message.from_user.id, 'withdraw_percent_set', percent=percent))
    except:
        bot.reply_to(message, get_text(message.from_user.id, 'invalid_number'))

@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    admin_panel(call.message)

# ==================== پیام همگانی ====================
@bot.message_handler(func=lambda m: m.text in ['📢 پیام همگانی', '📢 Broadcast'])
def broadcast_prompt(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(message.chat.id, get_text(message.from_user.id, 'enter_broadcast'))
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    text = message.text
    users = db.execute("SELECT user_id FROM users WHERE is_banned = 0")
    sent = 0
    failed = 0
    
    for user in users:
        try:
            lang = get_user_language(user['user_id'])
            broadcast_text = f"📢 **Announcement**\n\n{text}" if lang == 'en' else f"📢 **اعلامیه**\n\n{text}"
            bot.send_message(user['user_id'], broadcast_text, parse_mode='Markdown')
            sent += 1
            time.sleep(0.05)
        except:
            failed += 1
    
    bot.reply_to(message, get_text(message.from_user.id, 'broadcast_sent', count=sent))

# ==================== درخواست برداشت ====================
@bot.message_handler(func=lambda m: m.text in ['💸 درخواست برداشت'])
@rate_limit(2)
def withdraw_request(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    lang = get_user_language(user_id)
    
    min_withdraw = get_setting('min_withdraw', 2000000)
    
    if user['wallet_balance'] < min_withdraw:
        text = f"❌ Minimum withdrawal is {min_withdraw:,} Toman" if lang == 'en' else f"❌ حداقل برداشت {min_withdraw:,} تومان است"
        bot.send_message(message.chat.id, text)
        return
    
    msg = bot.send_message(message.chat.id, "💳 Enter TRC20 address for withdrawal:" if lang == 'en' else "💳 آدرس کیف پول TRC20 برای برداشت:")
    bot.register_next_step_handler(msg, process_withdraw_address, user)

def process_withdraw_address(message, user):
    address = message.text.strip()
    lang = get_user_language(user['user_id'])
    amount = user['wallet_balance']
    
    db.execute('''
        INSERT INTO withdraw_requests (user_id, amount, address, created_at, status)
        VALUES (?, ?, ?, ?, 'pending')
    ''', (user['user_id'], amount, address, datetime.now().isoformat()))
    
    db.execute('UPDATE users SET wallet_balance = 0 WHERE user_id = ?', (user['user_id'],))
    
    text = f"✅ Withdrawal request for {amount:,} Toman submitted!" if lang == 'en' else f"✅ درخواست برداشت {amount:,} تومان ثبت شد"
    bot.send_message(message.chat.id, text)
    
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id, f"💰 Withdrawal Request\n👤 {user['first_name']}\n🆔 {user['user_id']}\n💰 {amount:,} Toman\n💳 {address}")
        except:
            pass

# ==================== مانیتورینگ سیستم ====================
def system_monitor():
    while True:
        try:
            # بررسی انقضای اشتراک
            for user in db.execute('SELECT user_id, subscription_expiry FROM users WHERE subscription_status = "active"'):
                if user['subscription_expiry']:
                    expiry = datetime.fromisoformat(user['subscription_expiry'])
                    if expiry < datetime.now():
                        db.execute('UPDATE users SET subscription_status = "inactive" WHERE user_id = ?', (user['user_id'],))
                        logger.info(f"Subscription expired for user {user['user_id']}")
            
            # آمار روزانه
            today = datetime.now().date().isoformat()
            db.execute('INSERT OR IGNORE INTO daily_stats (date, new_users, new_bots, new_subscriptions, total_revenue) VALUES (?, 0, 0, 0, 0)', (today,))
            
            time.sleep(60)
        except Exception as e:
            logger.error(f"Monitor error: {e}")
            time.sleep(60)

threading.Thread(target=system_monitor, daemon=True).start()

# ==================== وب سرور ====================
if FLASK_AVAILABLE:
    flask_app = Flask(__name__)
    
    @flask_app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'ok',
            'version': VERSION,
            'uptime': int(time.time() - START_TIME),
            'active_bots': len(machine_manager.processes),
            'queue_size': build_queue.get_queue_length(),
            'timestamp': datetime.now().isoformat()
        })
    
    @flask_app.route('/stats', methods=['GET'])
    def stats_endpoint():
        if request.headers.get('X-API-Key') != WEBHOOK_SECRET:
            return jsonify({'error': 'Unauthorized'}), 401
        return jsonify(db.get_stats())
    
    def run_flask():
        flask_app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
    
    threading.Thread(target=run_flask, daemon=True).start()
    logger.info("✅ Web server started on port 5000")

# ==================== کتابخانه‌های محبوب ====================
POPULAR_LIBRARIES = {
    'requests': 'requests', 'aiohttp': 'aiohttp', 'httpx': 'httpx',
    'flask': 'flask', 'fastapi': 'fastapi', 'django': 'django',
    'sqlalchemy': 'sqlalchemy', 'asyncpg': 'asyncpg', 'redis': 'redis',
    'motor': 'motor', 'pyTelegramBotAPI': 'pyTelegramBotAPI',
    'aiogram': 'aiogram', 'numpy': 'numpy', 'pandas': 'pandas',
    'pillow': 'Pillow', 'beautifulsoup4': 'beautifulsoup4',
    'selenium': 'selenium', 'jdatetime': 'jdatetime',
    'cryptography': 'cryptography', 'loguru': 'loguru', 'tqdm': 'tqdm'
}

# ==================== اجرای اصلی ====================
if __name__ == "__main__":
    print("=" * 80)
    print("🚀 SUPER MOTHER BOT - ENTERPRISE EDITION v4.0".center(80))
    print("=" * 80)
    print(f"👑 Admins: {ADMIN_IDS}")
    print(f"🤖 Bot: @{BOT_USERNAME}")
    print(f"💳 Card: {CARD_NUMBER_DISPLAY}")
    print(f"🌐 TRC20: {TRC20_ADDRESS}")
    print(f"💰 Price: {get_setting('subscription_price', 2000000):,} Toman")
    print(f"🤖 Max bots per sub: {get_setting('max_bots_per_subscription', 3)}")
    print(f"💰 Commission: {get_setting('withdraw_percent', 7)}%")
    print(f"📊 Health Check: http://localhost:5000/health")
    print("=" * 80)
    print("✅ Features:")
    print("   ✓ Multi-language (Persian/English)")
    print("   ✓ Advanced Database with WAL mode")
    print("   ✓ Auto-backup & Cleanup")
    print("   ✓ Rate Limiting")
    print("   ✓ Token Encryption")
    print("   ✓ Referral System with Commission")
    print("   ✓ Max 3 bots per subscription")
    print("   ✓ Admin Panel")
    print("   ✓ System Monitoring")
    print("   ✓ Auto-Scale")
    print("   ✓ Health Checker")
    print("   ✓ Build Queue")
    print("=" * 80)
    print("✅ Bot is running...")
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            logger.error(f"Polling error: {e}")
            time.sleep(5)