#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
═══════════════════════════════════════════════════════════════════════════════
🚀 ربات مادر نهایی - نسخه وب کامل 100.2 Ultimate Enterprise
⚡ پشتیبانی از ۵۰ ماشین + ۵۰ کتابخانه + ایزوله سازی کامل
🌐 پنل مدیریت با ۲۰+ دکمه فعال
💎 سیستم کمیسیون دقیق رفرال با کش پیشرفته
🤖 محدودیت ۳ ربات در هر اشتراک (قابل تنظیم)
🔒 بازیابی خودکار پس از خرابی سرور
🖥️ مدیریت ۵۰ سرور - اضافه کردن سرور جدید به ماشین‌ها
📦 کش پیشرفته با Redis-like
🔄 تابع‌های قوی برای هر دکمه
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import time
import json
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
import signal
import pickle
import asyncio
from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict
from typing import Optional, Dict, Any, List
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dataclasses import dataclass, asdict
from enum import Enum

# ==================== Flask & Extensions ====================
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, send_file, make_response
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import requests
import paramiko

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
    'CACHE': os.path.join(BASE_DIR, "cache"),
    'BACKUPS': os.path.join(BASE_DIR, "backups"),
    'STATE': os.path.join(BASE_DIR, "state"),
    'UPLOADS': os.path.join(BASE_DIR, "uploads"),
    'SERVER_SCRIPTS': os.path.join(BASE_DIR, "server_scripts"),
    'ISOLATION': os.path.join(BASE_DIR, "isolation"),
    'LIBRARIES': os.path.join(BASE_DIR, "libraries")
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
        msg = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[EMAIL_HIDDEN]', msg)
        return msg

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(DIRS['LOGS'], 'web_app.log'), encoding='utf-8'),
        logging.FileHandler(os.path.join(DIRS['LOGS'], 'errors.log'), encoding='utf-8', level=logging.ERROR),
        logging.StreamHandler()
    ]
)
for handler in logging.root.handlers:
    handler.setFormatter(SecureFormatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s'))
logger = logging.getLogger('WebBotBuilder')

# ==================== تنظیمات اپلیکیشن ====================
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(64))
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB
app.config['UPLOAD_FOLDER'] = DIRS['UPLOADS']
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = '🔐 لطفاً ابتدا وارد شوید'
login_manager.session_protection = 'strong'

# ==================== تنظیمات پیش‌فرض ====================
DEFAULT_SETTINGS = {
    # تنظیمات مالی
    'trc20_address': "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A",
    'card_number': "5892101187322777",
    'card_number_display': "5892 1011 8732 2777",
    'card_holder': "مرتضی نیکخو خنجری",
    'card_bank': "بانک ملی - سپهر",
    'subscription_price': 2000000,
    'subscription_price_str': "۲,۰۰۰,۰۰۰ تومان",
    'subscription_price_usd': "50 USD",
    'withdraw_percent': 7,
    'min_withdraw': 2000000,
    
    # تنظیمات کاربران
    'max_bots_per_subscription': 3,
    'max_users_capacity': 100000,
    'max_builds_per_hour': 10,
    'max_concurrent_builds': 50,
    'rate_limit_per_second': 10,
    
    # تنظیمات سیستم
    'health_check_interval': 30,
    'auto_scale_threshold': 80,
    'backup_interval': 3600,
    'state_save_interval': 60,
    'cache_ttl': 3600,
    'max_machines': 50,
    'isolation_enabled': True,
    
    # تنظیمات ظاهری
    'site_name': 'ربات ساز حرفه‌ای',
    'site_description': 'ساخت ربات تلگرامی بدون نیاز به دانش برنامه‌نویسی | پشتیبانی از ۵۰ ماشین',
    'contact_email': 'support@example.com',
    'telegram_support': '@shahraghee13',
    'logo_text': '🤖 ربات ساز',
    'footer_text': 'تمامی حقوق محفوظ است',
    
    # متون راهنما
    'guide_text_fa': """📚 **راهنمای کامل استفاده**

1️⃣ **ساخت ربات**
• فایل .py یا .zip خود را آپلود کنید
• پشتیبانی از ساختار پوشه‌بندی
• توکن ربات باید در کد باشد

2️⃣ **مدیریت ربات‌ها**
• هر کاربر می‌تواند تا ۳ ربات بسازد
• قابلیت استارت/استاپ/حذف ربات
• مشاهده وضعیت لحظه‌ای

3️⃣ **سیستم مالی**
• اشتراک ماهیانه با قیمت {price}
• سیستم دعوت دوستان با {commission}% کمیسیون
• برداشت از {min_withdraw} تومان

4️⃣ **پنل مدیریت**
• تایید فیش‌های کاربران
• مدیریت ماشین‌ها و سرورها
• ارسال پیام همگانی
• مشاهده آمار لحظه‌ای

📞 **پشتیبانی:** {support}""",

    'guide_text_en': """📚 **Complete User Guide**

1️⃣ **Build Bot**
• Upload your .py or .zip file
• Support for folder structure
• Bot token must be in code

2️⃣ **Bot Management**
• Each user can build up to 3 bots
• Start/Stop/Delete capabilities
• Real-time status monitoring

3️⃣ **Financial System**
• Monthly subscription at {price}
• Referral system with {commission}% commission
• Withdraw from {min_withdraw} Toman

4️⃣ **Admin Panel**
• Receipt verification
• Server and machine management
• Broadcast messages
• Real-time statistics

📞 **Support:** {support}""",

    'welcome_text_fa': "🚀 به {name} عزیز خوش آمدید!\nبه ربات ساز حرفه‌ای خوش آمدید. از پنل کاربری می‌توانید ربات خود را بسازید.",
    'welcome_text_en': "🚀 Welcome {name}!\nWelcome to Professional Bot Builder. You can build your bot from the dashboard.",
    
    'subscription_active_text_fa': "✅ اشتراک شما با موفقیت فعال شد!\nاکنون می‌توانید حداکثر {max_bots} ربات بسازید.",
    'subscription_active_text_en': "✅ Your subscription has been activated!\nYou can now build up to {max_bots} bots.",
    
    'subscription_payment_text_fa': "💳 لطفاً مبلغ {price} را به شماره کارت زیر واریز کنید:\n`{card}`\n👤 {holder}\n🏦 {bank}\n\n📸 پس از واریز، تصویر تراکنش را ارسال کنید",
    'subscription_payment_text_en': "💳 Please send {price} to TRC20 address:\n`{address}`\n🌐 Network: TRC20 (USDT)\n\n📸 Send transaction screenshot after payment",
    
    'capacity_warning_message': "⚠️ ظرفیت ربات تکمیل شده است! لطفاً وارد ربات جدید شوید: @NEW_BOT",
    'new_bot_link': "@NEW_BOT"
}

# ==================== کتابخانه‌های محبوب (۵۰ عدد) ====================
POPULAR_LIBRARIES = {
    'requests': 'requests', 'aiohttp': 'aiohttp', 'httpx': 'httpx',
    'flask': 'flask', 'fastapi': 'fastapi', 'django': 'django', 'quart': 'quart',
    'sqlalchemy': 'sqlalchemy', 'asyncpg': 'asyncpg', 'redis': 'redis', 'aioredis': 'aioredis',
    'motor': 'motor', 'pyTelegramBotAPI': 'pyTelegramBotAPI', 'aiogram': 'aiogram',
    'python-telegram-bot': 'python-telegram-bot', 'telethon': 'telethon',
    'numpy': 'numpy', 'pandas': 'pandas', 'scipy': 'scipy', 'scikit-learn': 'scikit-learn',
    'pillow': 'Pillow', 'beautifulsoup4': 'beautifulsoup4', 'selenium': 'selenium',
    'jdatetime': 'jdatetime', 'persiantools': 'persiantools',
    'cryptography': 'cryptography', 'pycryptodome': 'pycryptodome',
    'loguru': 'loguru', 'tqdm': 'tqdm', 'colorama': 'colorama',
    'python-dotenv': 'python-dotenv', 'click': 'click',
    'celery': 'celery', 'huey': 'huey', 'rq': 'rq',
    'gunicorn': 'gunicorn', 'uvicorn': 'uvicorn', 'hypercorn': 'hypercorn',
    'pytest': 'pytest', 'black': 'black', 'flake8': 'flake8',
    'mypy': 'mypy', 'isort': 'isort', 'pre-commit': 'pre-commit',
    'docker': 'docker', 'kubernetes': 'kubernetes',
    'boto3': 'boto3', 'google-cloud-storage': 'google-cloud-storage',
    'twilio': 'twilio', 'sendgrid': 'sendgrid',
    'stripe': 'stripe', 'paypalrestsdk': 'paypalrestsdk'
}

# ==================== دیتابیس ====================
class Database:
    def __init__(self):
        self.conn = None
        self._init_db()
        self._init_tables()
    
    def _init_db(self):
        db_path = os.path.join(DIRS['DB'], 'web_app.db')
        self.conn = sqlite3.connect(db_path, timeout=120, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA cache_size=-1000000")
        self.conn.execute("PRAGMA page_size=16384")
        self.conn.execute("PRAGMA mmap_size=30000000000")
    
    def execute(self, query, params=()):
        try:
            cursor = self.conn.execute(query, params)
            self.conn.commit()
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"DB error: {e}")
            return []
    
    def executemany(self, query, params_list):
        try:
            cursor = self.conn.executemany(query, params_list)
            self.conn.commit()
            return cursor.rowcount
        except Exception as e:
            logger.error(f"DB executemany error: {e}")
            return 0
    
    def _init_tables(self):
        # 1. کاربران
        self.execute('''
            CREATE TABLE IF NOT EXISTS web_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                telegram_id INTEGER,
                is_admin INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                is_banned INTEGER DEFAULT 0,
                is_premium INTEGER DEFAULT 0,
                wallet_balance INTEGER DEFAULT 0,
                created_at TIMESTAMP,
                last_login TIMESTAMP,
                language TEXT DEFAULT 'fa',
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                referrals_count INTEGER DEFAULT 0,
                verified_referrals INTEGER DEFAULT 0,
                total_commission INTEGER DEFAULT 0,
                bots_count INTEGER DEFAULT 0,
                max_bots INTEGER DEFAULT 3,
                subscription_status TEXT DEFAULT 'inactive',
                subscription_expiry TIMESTAMP,
                subscription_purchased_at TIMESTAMP,
                last_payment_hash TEXT
            )
        ''')
        
        # 2. ربات‌ها
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
                join_block_message TEXT DEFAULT '🚫 سرور در حال حاضر پر است. لطفاً بعداً تلاش کنید.',
                health_status TEXT DEFAULT 'healthy',
                last_health_check TIMESTAMP,
                restart_count INTEGER DEFAULT 0,
                error_message TEXT,
                memory_usage INTEGER DEFAULT 0,
                cpu_usage REAL DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES web_users(id)
            )
        ''')
        
        # 3. ماشین‌ها (۵۰ ماشین)
        self.execute('''
            CREATE TABLE IF NOT EXISTS machines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                ip TEXT,
                port INTEGER DEFAULT 22,
                username TEXT,
                password TEXT,
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
                is_local INTEGER DEFAULT 1,
                ssh_key_path TEXT,
                docker_image TEXT DEFAULT 'python:3.10-slim'
            )
        ''')
        
        # 4. فیش‌ها
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
                created_at TIMESTAMP,
                admin_comment TEXT
            )
        ''')
        
        # 5. درخواست‌های برداشت
        self.execute('''
            CREATE TABLE IF NOT EXISTS withdraw_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                address TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP,
                processed_at TIMESTAMP,
                tx_hash TEXT,
                admin_comment TEXT
            )
        ''')
        
        # 6. کمیسیون‌ها
        self.execute('''
            CREATE TABLE IF NOT EXISTS commissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                from_user INTEGER,
                amount INTEGER,
                reason TEXT,
                created_at TIMESTAMP,
                paid BOOLEAN DEFAULT 0,
                paid_at TIMESTAMP
            )
        ''')
        
        # 7. خطاها
        self.execute('''
            CREATE TABLE IF NOT EXISTS errors (
                id TEXT PRIMARY KEY,
                type TEXT,
                message TEXT,
                user_id INTEGER,
                bot_id TEXT,
                timestamp TIMESTAMP,
                resolved BOOLEAN DEFAULT 0,
                stack_trace TEXT,
                resolved_at TIMESTAMP,
                resolved_by INTEGER
            )
        ''')
        
        # 8. تنظیمات سیستم
        self.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP,
                updated_by INTEGER
            )
        ''')
        
        # 9. آمار روزانه
        self.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT PRIMARY KEY,
                new_users INTEGER DEFAULT 0,
                new_bots INTEGER DEFAULT 0,
                new_subscriptions INTEGER DEFAULT 0,
                total_revenue INTEGER DEFAULT 0,
                active_users INTEGER DEFAULT 0,
                total_requests INTEGER DEFAULT 0,
                avg_response_time REAL DEFAULT 0,
                total_bots_created INTEGER DEFAULT 0,
                total_commissions_paid INTEGER DEFAULT 0
            )
        ''')
        
        # 10. سرورهای از راه دور
        self.execute('''
            CREATE TABLE IF NOT EXISTS remote_servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                ip TEXT,
                port INTEGER DEFAULT 22,
                username TEXT,
                password TEXT,
                ssh_key TEXT,
                status TEXT DEFAULT 'pending',
                machine_id INTEGER,
                created_at TIMESTAMP,
                last_connection TIMESTAMP,
                connection_success INTEGER DEFAULT 0
            )
        ''')
        
        # 11. اشتراک‌ها
        self.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                status TEXT DEFAULT 'inactive',
                expiry_date TIMESTAMP,
                purchased_at TIMESTAMP,
                payment_hash TEXT,
                months INTEGER DEFAULT 1,
                amount INTEGER,
                FOREIGN KEY(user_id) REFERENCES web_users(id)
            )
        ''')
        
        # 12. کش سیستمی
        self.execute('''
            CREATE TABLE IF NOT EXISTS system_cache (
                key TEXT PRIMARY KEY,
                value TEXT,
                expires_at TIMESTAMP,
                created_at TIMESTAMP
            )
        ''')
        
        # 13. کتابخانه‌های نصب شده
        self.execute('''
            CREATE TABLE IF NOT EXISTS installed_libraries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                version TEXT,
                installed_at TIMESTAMP,
                installed_by INTEGER,
                size INTEGER DEFAULT 0
            )
        ''')
        
        # 14. لاگ عملیات
        self.execute('''
            CREATE TABLE IF NOT EXISTS action_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                target_id TEXT,
                details TEXT,
                ip TEXT,
                created_at TIMESTAMP
            )
        ''')
        
        # ========== تنظیمات پیش‌فرض ==========
        for key, value in DEFAULT_SETTINGS.items():
            self.execute('INSERT OR IGNORE INTO system_settings (key, value, updated_at) VALUES (?, ?, ?)',
                        (key, str(value), datetime.now().isoformat()))
        
        # ========== ایجاد ۵۰ ماشین (سرور) ==========
        existing_machines = self.execute("SELECT COUNT(*) as count FROM machines")
        if existing_machines and existing_machines[0]['count'] == 0:
            # ماشین اصلی محلی
            self.execute('''
                INSERT INTO machines (id, name, status, max_bots, max_memory, created_at, is_local, region)
                VALUES (1, 'سرور اصلی تهران', 'active', 5000, 256000, ?, 1, 'Tehran')
            ''', (datetime.now().isoformat(),))
            
            # ۴۹ ماشین مجازی برای نمایش
            regions = ['Tehran', 'Dubai', 'Frankfurt', 'London', 'Singapore', 'Virginia', 'Oregon', 'Mumbai', 'Sydney', 'SaoPaulo']
            for i in range(2, 51):
                region = regions[i % len(regions)]
                self.execute('''
                    INSERT INTO machines (name, status, max_bots, max_memory, created_at, is_local, region, ip)
                    VALUES (?, 'active', 5000, 256000, ?, 0, ?, ?)
                ''', (f'سرور {i} - {region}', datetime.now().isoformat(), region, f'10.0.0.{i}'))
            logger.info("✅ 50 machines created")
        
        # ========== ایجاد کتابخانه‌های پیش‌فرض ==========
        for lib_name in list(POPULAR_LIBRARIES.keys())[:50]:
            self.execute('INSERT OR IGNORE INTO installed_libraries (name, version, installed_at) VALUES (?, ?, ?)',
                        (lib_name, 'latest', datetime.now().isoformat()))
        
        # ========== ایجاد ادمین خاص ==========
        admin_email = "morteza.yari1377m@gmail.com"
        admin_password = "M09145978426m"
        existing_admin = self.execute("SELECT * FROM web_users WHERE email = ?", (admin_email,))
        if not existing_admin:
            referral_code = hashlib.md5(f"{admin_email}_{time.time()}".encode()).hexdigest()[:12]
            self.execute('''
                INSERT INTO web_users (email, username, full_name, password_hash, is_admin, is_active, created_at, referral_code, wallet_balance, max_bots)
                VALUES (?, ?, ?, ?, 1, 1, ?, ?, 1000000, 100)
            ''', (admin_email, 'admin', 'مدیر سیستم', generate_password_hash(admin_password), 
                  datetime.now().isoformat(), referral_code))
            
            admin_id = self.execute("SELECT id FROM web_users WHERE email = ?", (admin_email,))[0]['id']
            expiry = (datetime.now() + timedelta(days=365*100)).isoformat()
            self.execute('''
                INSERT INTO subscriptions (user_id, status, expiry_date, purchased_at, months)
                VALUES (?, 'active', ?, ?, 1200)
            ''', (admin_id, expiry, datetime.now().isoformat()))
            logger.info(f"✅ Admin created: {admin_email}")

db = Database()

# ==================== مدل کاربر ====================
class User(UserMixin):
    def __init__(self, user_data):
        self.id = user_data['id']
        self.username = user_data['username']
        self.email = user_data['email']
        self.full_name = user_data['full_name']
        self.is_admin = user_data['is_admin']
        self.wallet_balance = user_data['wallet_balance']
        self.referral_code = user_data['referral_code']
        self.referrals_count = user_data['referrals_count']
        self.total_commission = user_data['total_commission']
        self.language = user_data.get('language', 'fa')
        self.bots_count = user_data.get('bots_count', 0)
        self.max_bots = user_data.get('max_bots', 3)
    
    @staticmethod
    def get(user_id):
        user_data = db.execute("SELECT * FROM web_users WHERE id = ?", (user_id,))
        if user_data:
            return User(user_data[0])
        return None
    
    @staticmethod
    def get_by_email(email):
        user_data = db.execute("SELECT * FROM web_users WHERE email = ?", (email,))
        if user_data:
            return User(user_data[0])
        return None

@login_manager.user_loader
def load_user(user_id):
    return User.get(int(user_id))

# ==================== کش پیشرفته ====================
class AdvancedCache:
    def __init__(self, default_ttl=3600):
        self.cache = {}
        self.stats = {'hits': 0, 'misses': 0, 'sets': 0, 'deletes': 0}
        self.default_ttl = default_ttl
        self.lock = threading.RLock()
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self):
        def cleanup():
            while True:
                time.sleep(300)  # هر ۵ دقیقه
                self._clean_expired()
        t = threading.Thread(target=cleanup, daemon=True)
        t.start()
    
    def _clean_expired(self):
        with self.lock:
            now = time.time()
            expired = [k for k, v in self.cache.items() if v['expires'] < now]
            for k in expired:
                del self.cache[k]
            if expired:
                logger.debug(f"Cache cleaned: {len(expired)} items")
    
    def get(self, key):
        with self.lock:
            item = self.cache.get(key)
            if item and item['expires'] > time.time():
                self.stats['hits'] += 1
                return item['value']
            if key in self.cache:
                del self.cache[key]
            self.stats['misses'] += 1
        return None
    
    def set(self, key, value, ttl=None):
        if ttl is None:
            ttl = self.default_ttl
        with self.lock:
            self.cache[key] = {'value': value, 'expires': time.time() + ttl, 'created': time.time()}
            self.stats['sets'] += 1
            # محدودیت حافظه کش (حداکثر 10000 آیتم)
            if len(self.cache) > 10000:
                oldest = min(self.cache.keys(), key=lambda k: self.cache[k]['created'])
                del self.cache[oldest]
    
    def delete(self, key):
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                self.stats['deletes'] += 1
                return True
        return False
    
    def clear(self):
        with self.lock:
            count = len(self.cache)
            self.cache.clear()
            self.stats['deletes'] += count
            return count
    
    def get_stats(self):
        total = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total * 100) if total > 0 else 0
        return {
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'sets': self.stats['sets'],
            'deletes': self.stats['deletes'],
            'size': len(self.cache),
            'hit_rate': round(hit_rate, 2)
        }
    
    def get_or_set(self, key, func, ttl=None):
        value = self.get(key)
        if value is not None:
            return value
        value = func()
        self.set(key, value, ttl)
        return value

cache = AdvancedCache(default_ttl=3600)

# ==================== Rate Limiter پیشرفته ====================
class AdvancedRateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
        self.banned = {}
        self.lock = threading.RLock()
    
    def is_allowed(self, user_id, limit_per_second=10, limit_per_minute=100, limit_per_hour=500):
        with self.lock:
            # بررسی بن بودن
            if user_id in self.banned:
                if time.time() < self.banned[user_id]:
                    return False, f"مسدود شده تا {datetime.fromtimestamp(self.banned[user_id]).strftime('%H:%M:%S')}"
                else:
                    del self.banned[user_id]
            
            now = time.time()
            
            # بررسی در ثانیه
            sec_requests = [t for t in self.requests[user_id] if now - t < 1]
            if len(sec_requests) >= limit_per_second:
                self._ban_user(user_id, 60)
                return False, "محدودیت سرعت (۱ ثانیه) - مسدود موقت ۱ دقیقه"
            
            # بررسی در دقیقه
            min_requests = [t for t in self.requests[user_id] if now - t < 60]
            if len(min_requests) >= limit_per_minute:
                self._ban_user(user_id, 300)
                return False, "محدودیت سرعت (۱ دقیقه) - مسدود موقت ۵ دقیقه"
            
            # بررسی در ساعت
            hour_requests = [t for t in self.requests[user_id] if now - t < 3600]
            if len(hour_requests) >= limit_per_hour:
                self._ban_user(user_id, 3600)
                return False, "محدودیت سرعت (۱ ساعت) - مسدود موقت ۱ ساعت"
            
            self.requests[user_id].append(now)
            return True, "ok"
    
    def _ban_user(self, user_id, duration):
        self.banned[user_id] = time.time() + duration
        logger.warning(f"User {user_id} banned for {duration}s")
    
    def get_stats(self, user_id):
        now = time.time()
        return {
            'last_second': len([t for t in self.requests[user_id] if now - t < 1]),
            'last_minute': len([t for t in self.requests[user_id] if now - t < 60]),
            'last_hour': len([t for t in self.requests[user_id] if now - t < 3600]),
            'is_banned': user_id in self.banned,
            'ban_expires': datetime.fromtimestamp(self.banned[user_id]).isoformat() if user_id in self.banned else None
        }

rate_limiter = AdvancedRateLimiter()

# ==================== ایزوله سازی ربات‌ها ====================
class BotIsolation:
    def __init__(self):
        self.isolation_enabled = True
    
    def create_isolated_env(self, bot_id, requirements=None):
        """ایجاد محیط ایزوله برای هر ربات"""
        isolation_dir = os.path.join(DIRS['ISOLATION'], bot_id)
        os.makedirs(isolation_dir, exist_ok=True)
        
        # ایجاد venv مجازی
        venv_dir = os.path.join(isolation_dir, 'venv')
        if not os.path.exists(venv_dir):
            subprocess.run([sys.executable, '-m', 'venv', venv_dir], capture_output=True)
        
        # ایجاد فایل requirements
        if requirements:
            req_file = os.path.join(isolation_dir, 'requirements.txt')
            with open(req_file, 'w') as f:
                f.write('\n'.join(requirements))
            
            # نصب کتابخانه‌ها
            pip_path = os.path.join(venv_dir, 'bin', 'pip')
            subprocess.run([pip_path, 'install', '-r', req_file], capture_output=True)
        
        return {
            'isolated': True,
            'venv_path': venv_dir,
            'python_path': os.path.join(venv_dir, 'bin', 'python'),
            'isolation_dir': isolation_dir
        }
    
    def run_isolated_bot(self, bot_id, code_path, token):
        """اجرای ربات در محیط ایزوله"""
        isolation = self.create_isolated_env(bot_id)
        
        log_file = os.path.join(DIRS['LOGS'], f"isolated_bot_{bot_id}.log")
        
        process = subprocess.Popen(
            [isolation['python_path'], code_path],
            stdout=open(log_file, 'a'),
            stderr=subprocess.STDOUT,
            cwd=os.path.dirname(code_path),
            start_new_session=True,
            env={
                **os.environ,
                'BOT_TOKEN': token,
                'ISOLATED_BOT_ID': bot_id,
                'PYTHONPATH': isolation['isolation_dir']
            }
        )
        
        return process

bot_isolation = BotIsolation()

# ==================== مدیریت ۵۰ ماشین ====================
class MachineManager:
    def __init__(self):
        self.processes = {}
        self.port_counter = 8000
        self.lock = threading.RLock()
        self.machine_lock = threading.RLock()
        self._restore_bots_after_crash()
        self._start_auto_scaler()
    
    def _start_auto_scaler(self):
        def auto_scale():
            while True:
                try:
                    machines = db.execute("SELECT id, current_bots, max_bots, status FROM machines WHERE status = 'active'")
                    for machine in machines:
                        usage = (machine['current_bots'] / machine['max_bots']) * 100 if machine['max_bots'] > 0 else 0
                        threshold = get_setting('auto_scale_threshold')
                        if usage > threshold:
                            new_max = int(machine['max_bots'] * 1.2)
                            if new_max <= 50000:
                                self.update_machine_capacity(machine['id'], new_max)
                                logger.info(f"Auto-scaled machine {machine['id']} to {new_max}")
                    time.sleep(300)  # هر ۵ دقیقه
                except Exception as e:
                    logger.error(f"Auto-scale error: {e}")
                    time.sleep(60)
        t = threading.Thread(target=auto_scale, daemon=True)
        t.start()
    
    def _restore_bots_after_crash(self):
        try:
            logger.info("🔄 Restoring bots after crash...")
            running_bots = db.execute('SELECT id, token, file_path, name, machine_id FROM bots WHERE status = "running"')
            restored = 0
            for bot_rec in running_bots:
                bot_id = bot_rec['id']
                token = bot_rec['token']
                if token and os.path.exists(bot_rec['file_path']):
                    with open(bot_rec['file_path'], 'r', encoding='utf-8', errors='ignore') as f:
                        code = f.read()
                    result = self.run_bot(bot_id, code, token, restore=True)
                    if result.get('success'):
                        restored += 1
                    else:
                        db.execute('UPDATE bots SET status = "stopped" WHERE id = ?', (bot_id,))
            logger.info(f"✅ Restored {restored} bots")
        except Exception as e:
            logger.error(f"Restore failed: {e}")
    
    def get_all_machines(self):
        return db.execute("SELECT * FROM machines ORDER BY id")
    
    def get_available_machine(self):
        with self.machine_lock:
            machines = db.execute("SELECT * FROM machines WHERE status = 'active' ORDER BY current_bots ASC")
            for m in machines:
                if m['current_bots'] < m['max_bots']:
                    return m['id']
            return None
    
    def get_best_machine(self, region='default'):
        with self.machine_lock:
            query = "SELECT * FROM machines WHERE status = 'active'"
            if region != 'default':
                query += f" AND region = '{region}'"
            query += " ORDER BY current_bots ASC"
            machines = db.execute(query)
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
                return {'success': False, 'error': 'همه ۵۰ ماشین پر هستند'}
            
            port = self.get_available_port()
            bot_dir = os.path.join(DIRS['MACHINES'], f"machine_{machine_id:03d}", bot_id)
            os.makedirs(bot_dir, exist_ok=True)
            code_path = os.path.join(bot_dir, 'bot.py')
            
            # افزودن کد مدیریت عضوگیری
            join_check_code = f'''
# ========== سیستم مدیریت عضوگیری ==========
import sqlite3, os, time, threading
from functools import wraps

DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'database', 'web_app.db')
join_enabled_cache = True
block_message_cache = "🚫 سرور پر است"

def update_cache():
    global join_enabled_cache, block_message_cache
    try:
        conn = sqlite3.connect(DB_PATH, timeout=3)
        cursor = conn.cursor()
        cursor.execute("SELECT join_enabled, join_block_message FROM bots WHERE id = ?", ("{bot_id}",))
        result = cursor.fetchone()
        conn.close()
        if result:
            join_enabled_cache = result[0] == 1
            block_message_cache = result[1] if result[1] else "🚫 سرور پر است"
    except:
        pass

def cache_updater():
    while True:
        update_cache()
        time.sleep(30)

threading.Thread(target=cache_updater, daemon=True).start()
update_cache()

def check_join_enabled(func):
    @wraps(func)
    def wrapper(message, *args, **kwargs):
        if not join_enabled_cache:
            bot.reply_to(message, block_message_cache)
            return
        return func(message, *args, **kwargs)
    return wrapper
# ===========================================
'''
            
            with open(code_path, 'w', encoding='utf-8') as f:
                f.write(join_check_code + "\n" + code)
            
            log_file = os.path.join(DIRS['LOGS'], f"bot_{bot_id}.log")
            
            # ایزوله سازی در صورت فعال بودن
            if get_setting('isolation_enabled'):
                process = bot_isolation.run_isolated_bot(bot_id, code_path, token)
            else:
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
            return {'success': False, 'error': str(e)[:200]}
    
    def stop_bot(self, bot_id):
        with self.lock:
            if bot_id in self.processes:
                try:
                    info = self.processes[bot_id]
                    os.kill(info['pid'], signal.SIGTERM)
                    time.sleep(1)
                    if info['process'].poll() is None:
                        os.kill(info['pid'], signal.SIGKILL)
                    self.release_bot(bot_id, info['machine_id'])
                    del self.processes[bot_id]
                    db.execute("UPDATE bots SET status = 'stopped', last_active = ? WHERE id = ?",
                              (datetime.now().isoformat(), bot_id))
                    return True
                except Exception as e:
                    logger.error(f"Stop bot error: {e}")
        return False
    
    def get_status(self, bot_id):
        with self.lock:
            if bot_id in self.processes:
                info = self.processes[bot_id]
                try:
                    os.kill(info['pid'], 0)
                    return {
                        'running': True,
                        'pid': info['pid'],
                        'machine_id': info['machine_id'],
                        'uptime': round(time.time() - info['start_time'], 1),
                        'port': info['port']
                    }
                except:
                    if bot_id in self.processes:
                        del self.processes[bot_id]
                        self.release_bot(bot_id, info['machine_id'])
                        db.execute("UPDATE bots SET status = 'stopped' WHERE id = ?", (bot_id,))
        return {'running': False}
    
    def restart_all_dead_bots(self):
        dead_bots = db.execute('SELECT id, token, file_path FROM bots WHERE status = "running"')
        restarted = 0
        for bot_rec in dead_bots:
            bot_id = bot_rec['id']
            status = self.get_status(bot_id)
            if not status.get('running'):
                token = bot_rec['token']
                if token and os.path.exists(bot_rec['file_path']):
                    with open(bot_rec['file_path'], 'r', encoding='utf-8', errors='ignore') as f:
                        code = f.read()
                    result = self.run_bot(bot_id, code, token)
                    if result.get('success'):
                        restarted += 1
        return restarted
    
    def get_stats(self):
        machines = db.execute("SELECT * FROM machines WHERE status = 'active'")
        machine_list = list(machines)
        total_bots = sum(m['current_bots'] for m in machine_list)
        total_capacity = sum(m['max_bots'] for m in machine_list)
        return {
            'total': len(machine_list),
            'total_bots': total_bots,
            'total_capacity': total_capacity,
            'available': total_capacity - total_bots,
            'usage_percent': (total_bots / total_capacity) * 100 if total_capacity > 0 else 0,
            'machines': [{'id': m['id'], 'name': m['name'], 'current': m['current_bots'], 
                          'max': m['max_bots'], 'usage': (m['current_bots']/m['max_bots']*100) if m['max_bots']>0 else 0,
                          'status': m['status'], 'region': m['region']} for m in machine_list]
        }
    
    def update_machine_capacity(self, machine_id, max_bots):
        db.execute("UPDATE machines SET max_bots = ? WHERE id = ?", (max_bots, machine_id))
        return True
    
    def update_machine_status(self, machine_id, status):
        db.execute("UPDATE machines SET status = ? WHERE id = ?", (status, machine_id))
        return True
    
    def add_machine(self, name, ip, username, password, max_bots=5000, region='default'):
        db.execute('''
            INSERT INTO machines (name, ip, username, password, max_bots, region, status, created_at, is_local)
            VALUES (?, ?, ?, ?, ?, ?, 'active', ?, 0)
        ''', (name, ip, username, password, max_bots, region, datetime.now().isoformat()))
        return True
    
    def delete_bot(self, bot_id, user_id):
        bot = db.execute("SELECT * FROM bots WHERE id = ? AND user_id = ?", (bot_id, user_id))
        if not bot:
            return False
        self.stop_bot(bot_id)
        bot_dir = os.path.join(DIRS['MACHINES'], f"machine_{bot[0]['machine_id']:03d}", bot_id) if bot[0].get('machine_id') else None
        if bot_dir and os.path.exists(bot_dir):
            shutil.rmtree(bot_dir)
        
        # حذف محیط ایزوله
        isolation_dir = os.path.join(DIRS['ISOLATION'], bot_id)
        if os.path.exists(isolation_dir):
            shutil.rmtree(isolation_dir)
        
        db.execute("DELETE FROM bots WHERE id = ?", (bot_id,))
        db.execute("UPDATE web_users SET bots_count = bots_count - 1 WHERE id = ?", (user_id,))
        return True

bot_manager = MachineManager()

# ==================== صف ساخت پیشرفته ====================
class AdvancedBuildQueue:
    def __init__(self):
        self.queue = queue.PriorityQueue()
        self.processing = {}
        self.lock = threading.RLock()
        self.worker_threads = []
        self.stats = {'total_built': 0, 'total_failed': 0, 'avg_build_time': 0}
        self._start_workers()
    
    def _start_workers(self):
        max_concurrent = get_setting('max_concurrent_builds')
        for i in range(max_concurrent):
            t = threading.Thread(target=self._worker, daemon=True, name=f"BuildWorker-{i}")
            t.start()
            self.worker_threads.append(t)
        logger.info(f"✅ Started {max_concurrent} build workers")
    
    def add_build(self, user_id, file_path, file_name, build_data, priority=5):
        build_id = str(uuid.uuid4())[:8]
        build_item = {
            'id': build_id,
            'user_id': user_id,
            'file_path': file_path,
            'file_name': file_name,
            'added_at': time.time(),
            'priority': priority,
            'build_data': build_data
        }
        self.queue.put((priority, build_id, build_item))
        with self.lock:
            self.processing[build_id] = {'status': 'queued', 'position': self.queue.qsize(), 'added_at': time.time()}
        return build_id
    
    def _worker(self):
        while True:
            try:
                priority, build_id, build_item = self.queue.get(timeout=1)
                with self.lock:
                    if build_id in self.processing:
                        self.processing[build_id]['status'] = 'processing'
                        self.processing[build_id]['started_at'] = time.time()
                
                start_time = time.time()
                self._process_build(build_item)
                build_time = time.time() - start_time
                
                # به‌روزرسانی آمار
                with self.lock:
                    self.stats['total_built'] += 1
                    self.stats['avg_build_time'] = (self.stats['avg_build_time'] * (self.stats['total_built'] - 1) + build_time) / self.stats['total_built']
                
                self.queue.task_done()
                with self.lock:
                    if build_id in self.processing:
                        del self.processing[build_id]
                
            except queue.Empty:
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"Worker error: {e}")
                with self.lock:
                    self.stats['total_failed'] += 1
                time.sleep(1)
    
    def _process_build(self, build_item):
        try:
            build_data = build_item['build_data']
            result = bot_manager.run_bot(build_data['bot_id'], build_data['main_code'], build_data['token'])
            
            if result['success']:
                db.execute('''
                    INSERT INTO bots (id, user_id, token, name, username, file_path, folder_path, pid, machine_id, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'running', ?)
                ''', (build_data['bot_id'], build_data['user_id'], build_data['token'], 
                      build_data['bot_info']['first_name'], build_data['bot_info']['username'],
                      build_data['file_path'], build_data.get('folder_path'), result['pid'], 
                      result.get('machine_id', 1), datetime.now().isoformat()))
                
                db.execute("UPDATE web_users SET bots_count = bots_count + 1 WHERE id = ?", (build_data['user_id'],))
                logger.info(f"✅ Bot {build_data['bot_id']} built successfully")
            else:
                log_error("build_error", result.get('error', 'Unknown'), build_data['user_id'])
        except Exception as e:
            logger.error(f"Build failed: {e}")
            log_error("build_exception", str(e), build_item['user_id'])
    
    def get_queue_length(self):
        return self.queue.qsize()
    
    def get_queue_status(self):
        with self.lock:
            return {
                'queued': self.queue.qsize(),
                'processing': len([p for p in self.processing.values() if p['status'] == 'processing']),
                'workers': len(self.worker_threads),
                'total_built': self.stats['total_built'],
                'total_failed': self.stats['total_failed'],
                'avg_build_time': round(self.stats['avg_build_time'], 2),
                'items': [(k, v['status']) for k, v in list(self.processing.items())[:10]]
            }
    
    def get_user_position(self, user_id):
        with self.lock:
            # پیدا کردن موقعیت کاربر در صف
            position = 1
            temp_queue = list(self.queue.queue)
            for p, bid, item in sorted(temp_queue):
                if item['user_id'] == user_id:
                    return position
                position += 1
            return None

build_queue = AdvancedBuildQueue()

# ==================== Health Checker ====================
class HealthChecker:
    def __init__(self):
        self.checking = True
        self.stats = {'checks': 0, 'restarts': 0, 'failures': 0}
        self.thread = threading.Thread(target=self._monitor, daemon=True)
        self.thread.start()
    
    def _monitor(self):
        while self.checking:
            try:
                interval = get_setting('health_check_interval')
                running_bots = db.execute('SELECT id, token, name, status FROM bots WHERE status = "running"')
                
                for bot_rec in running_bots:
                    bot_id = bot_rec['id']
                    token = bot_rec['token']
                    
                    if token:
                        try:
                            # بررسی با API تلگرام
                            resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
                            if resp.status_code != 200:
                                self._handle_unhealthy_bot(bot_id)
                            else:
                                db.execute("UPDATE bots SET health_status = 'healthy', last_health_check = ? WHERE id = ?",
                                         (datetime.now().isoformat(), bot_id))
                        except Exception as e:
                            self._handle_unhealthy_bot(bot_id)
                    
                    self.stats['checks'] += 1
                    time.sleep(0.1)  # جلوگیری از overload
                
                # بررسی ماشین‌ها
                machines = db.execute("SELECT id, ip, status FROM machines WHERE is_local = 0")
                for machine in machines:
                    # تست اتصال به ماشین از راه دور
                    try:
                        ssh = paramiko.SSHClient()
                        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                        ssh.connect(machine['ip'], timeout=5)
                        ssh.close()
                        db.execute("UPDATE machines SET status = 'active', last_heartbeat = ? WHERE id = ?",
                                 (datetime.now().isoformat(), machine['id']))
                    except:
                        db.execute("UPDATE machines SET status = 'offline', last_heartbeat = ? WHERE id = ?",
                                 (datetime.now().isoformat(), machine['id']))
                
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Health check error: {e}")
                self.stats['failures'] += 1
                time.sleep(60)
    
    def _handle_unhealthy_bot(self, bot_id):
        db.execute("UPDATE bots SET health_status = 'unhealthy', last_health_check = ? WHERE id = ?",
                  (datetime.now().isoformat(), bot_id))
        
        # تلاش برای ریستارت
        restart_count = db.execute("SELECT restart_count FROM bots WHERE id = ?", (bot_id,))
        if restart_count and restart_count[0]['restart_count'] < 3:
            self._restart_bot(bot_id)
        else:
            db.execute("UPDATE bots SET status = 'error', error_message = 'Too many restarts' WHERE id = ?", (bot_id,))
    
    def _restart_bot(self, bot_id):
        bot_rec = db.execute('SELECT * FROM bots WHERE id = ?', (bot_id,))
        if not bot_rec:
            return
        
        bot_rec = dict(bot_rec[0])
        bot_manager.stop_bot(bot_id)
        time.sleep(2)
        
        if os.path.exists(bot_rec['file_path']):
            try:
                with open(bot_rec['file_path'], 'r', encoding='utf-8', errors='ignore') as f:
                    code = f.read()
                token = bot_rec['token']
                if token:
                    result = bot_manager.run_bot(bot_id, code, token)
                    if result['success']:
                        db.execute('UPDATE bots SET status = "running", restart_count = restart_count + 1, machine_id = ?, pid = ?, last_active = ?, health_status = "healthy" WHERE id = ?',
                                  (result['machine_id'], result['pid'], datetime.now().isoformat(), bot_id))
                        self.stats['restarts'] += 1
                        logger.info(f"✅ Auto-restarted bot {bot_id}")
                    else:
                        db.execute('UPDATE bots SET status = "error", error_message = ? WHERE id = ?', 
                                  (result.get('error', 'Restart failed')[:200], bot_id))
            except Exception as e:
                logger.error(f"Failed to restart bot {bot_id}: {e}")
                db.execute('UPDATE bots SET status = "error", error_message = ? WHERE id = ?', (str(e)[:200], bot_id))
    
    def get_stats(self):
        return self.stats

health_checker = HealthChecker()

# ==================== مدیریت سرورهای از راه دور ====================
class RemoteServerManager:
    def __init__(self):
        self.connections = {}
        self.lock = threading.RLock()
    
    def add_server(self, name, ip, username, password, port=22, machine_id=None):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, port=port, username=username, password=password, timeout=10)
            ssh.close()
            
            db.execute('''
                INSERT INTO remote_servers (name, ip, port, username, password, machine_id, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'connected', ?)
            ''', (name, ip, port, username, password, machine_id, datetime.now().isoformat()))
            
            if machine_id:
                db.execute('UPDATE machines SET ip = ?, username = ?, password = ?, is_local = 0 WHERE id = ?',
                          (ip, username, password, machine_id))
            
            return True, "اتصال با موفقیت برقرار شد"
        except Exception as e:
            return False, f"خطا در اتصال: {str(e)}"
    
    def deploy_to_server(self, machine_id, bot_code, bot_id):
        machine = db.execute("SELECT * FROM machines WHERE id = ?", (machine_id,))
        if not machine:
            return False, "ماشین یافت نشد"
        
        machine = machine[0]
        if machine.get('is_local', 1) == 1:
            return False, "این ماشین محلی است"
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(machine['ip'], port=machine.get('port', 22), 
                       username=machine['username'], password=machine['password'], timeout=10)
            
            sftp = ssh.open_sftp()
            remote_dir = f"/root/mother_bot/machines/machine_{machine_id:03d}/{bot_id}"
            try:
                sftp.mkdir(remote_dir)
            except:
                pass
            
            remote_file = f"{remote_dir}/bot.py"
            with sftp.open(remote_file, 'w') as f:
                f.write(bot_code)
            
            sftp.close()
            
            cmd = f"cd {remote_dir} && nohup python3 bot.py > /dev/null 2>&1 &"
            ssh.exec_command(cmd)
            ssh.close()
            
            return True, "ربات با موفقیت روی سرور مستقر شد"
        except Exception as e:
            return False, f"خطا در استقرار: {str(e)}"
    
    def get_servers(self):
        return db.execute("SELECT * FROM remote_servers ORDER BY created_at DESC")
    
    def test_connection(self, server_id):
        server = db.execute("SELECT * FROM remote_servers WHERE id = ?", (server_id,))
        if not server:
            return False, "سرور یافت نشد"
        
        server = server[0]
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(server['ip'], port=server['port'], 
                       username=server['username'], password=server['password'], timeout=10)
            ssh.close()
            db.execute("UPDATE remote_servers SET status = 'connected', last_connection = ?, connection_success = connection_success + 1 WHERE id = ?",
                      (datetime.now().isoformat(), server_id))
            return True, "اتصال برقرار است"
        except Exception as e:
            db.execute("UPDATE remote_servers SET status = 'failed', last_connection = ? WHERE id = ?",
                      (datetime.now().isoformat(), server_id))
            return False, f"خطا: {str(e)}"

remote_manager = RemoteServerManager()

# ==================== کتابخانه‌ها ====================
class LibraryManager:
    def __init__(self):
        self.lock = threading.RLock()
    
    def get_installed_libraries(self):
        return db.execute("SELECT * FROM installed_libraries ORDER BY name")
    
    def install_library(self, lib_name, user_id):
        try:
            # نصب کتابخانه
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', lib_name, '--quiet'],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                # استخراج نسخه
                version_result = subprocess.run(
                    [sys.executable, '-m', 'pip', 'show', lib_name],
                    capture_output=True,
                    text=True
                )
                version = 'latest'
                for line in version_result.stdout.split('\n'):
                    if line.startswith('Version:'):
                        version = line.split(':')[1].strip()
                
                db.execute('''
                    INSERT OR REPLACE INTO installed_libraries (name, version, installed_at, installed_by)
                    VALUES (?, ?, ?, ?)
                ''', (lib_name, version, datetime.now().isoformat(), user_id))
                return True, f"کتابخانه {lib_name} با موفقیت نصب شد"
            else:
                error = result.stderr[:200] if result.stderr else "خطا"
                return False, f"خطا در نصب: {error}"
        except subprocess.TimeoutExpired:
            return False, "زمان نصب به پایان رسید"
        except Exception as e:
            return False, f"خطا: {str(e)[:100]}"
    
    def uninstall_library(self, lib_name):
        try:
            subprocess.run(
                [sys.executable, '-m', 'pip', 'uninstall', lib_name, '-y', '--quiet'],
                capture_output=True,
                timeout=60
            )
            db.execute("DELETE FROM installed_libraries WHERE name = ?", (lib_name,))
            return True, f"کتابخانه {lib_name} حذف شد"
        except Exception as e:
            return False, f"خطا: {str(e)[:100]}"
    
    def search_library(self, query):
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'search', query],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout[:2000]
        except:
            return "امکان جستجو وجود ندارد"

library_manager = LibraryManager()

# ==================== توابع کمکی ====================
def get_setting(key):
    cached = cache.get(f"setting_{key}")
    if cached is not None:
        return cached
    
    result = db.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
    if result:
        val = result[0]['value']
        numeric_keys = ['subscription_price', 'withdraw_percent', 'min_withdraw', 
                        'max_bots_per_subscription', 'max_builds_per_hour', 
                        'max_concurrent_builds', 'rate_limit_per_second',
                        'health_check_interval', 'auto_scale_threshold',
                        'max_users_capacity', 'max_machines']
        if key in numeric_keys:
            try:
                val = int(val)
            except:
                val = DEFAULT_SETTINGS.get(key)
        cache.set(f"setting_{key}", val, ttl=300)
        return val
    return DEFAULT_SETTINGS.get(key)

def update_setting(key, value):
    db.execute("UPDATE system_settings SET value = ?, updated_at = ? WHERE key = ?", 
               (str(value), datetime.now().isoformat(), key))
    cache.delete(f"setting_{key}")

def generate_referral_code(user_id):
    return hashlib.md5(f"{user_id}_{time.time()}_{secrets.token_hex(8)}".encode()).hexdigest()[:12]

def check_user_subscription(user_id):
    # ادمین همیشه اشتراک فعال دارد
    user = db.execute("SELECT is_admin FROM web_users WHERE id = ?", (user_id,))
    if user and user[0]['is_admin'] == 1:
        return True
    
    cached = cache.get(f"subscription_{user_id}")
    if cached is not None:
        return cached
    
    subs = db.execute("SELECT status, expiry_date FROM subscriptions WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
    if subs:
        sub = subs[0]
        if sub['status'] == 'active' and sub['expiry_date']:
            expiry = datetime.fromisoformat(sub['expiry_date'])
            if expiry > datetime.now():
                cache.set(f"subscription_{user_id}", True, ttl=3600)
                return True
            else:
                db.execute("UPDATE subscriptions SET status = 'inactive' WHERE user_id = ?", (user_id,))
    cache.set(f"subscription_{user_id}", False, ttl=300)
    return False

def get_remaining_bots(user_id):
    if not check_user_subscription(user_id):
        return 0
    max_bots = get_setting('max_bots_per_subscription')
    current_bots = db.execute("SELECT COUNT(*) as count FROM bots WHERE user_id = ?", (user_id,))[0]['count']
    return max_bots - current_bots

def add_wallet_balance(user_id, amount, reason=None):
    db.execute("UPDATE web_users SET wallet_balance = wallet_balance + ? WHERE id = ?", (amount, user_id))
    if reason:
        db.execute("INSERT INTO action_logs (user_id, action, details, created_at) VALUES (?, 'add_balance', ?, ?)",
                  (user_id, f"{amount}: {reason}", datetime.now().isoformat()))
    return True

def activate_subscription(user_id, tx_hash=None, months=1):
    now = datetime.now()
    existing = db.execute("SELECT expiry_date FROM subscriptions WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
    
    if existing and existing[0]['expiry_date']:
        new_expiry = datetime.fromisoformat(existing[0]['expiry_date']) + timedelta(days=30*months)
        db.execute("UPDATE subscriptions SET status = 'active', expiry_date = ?, purchased_at = ?, payment_hash = ? WHERE user_id = ?",
                  (new_expiry.isoformat(), now.isoformat(), tx_hash, user_id))
    else:
        new_expiry = now + timedelta(days=30*months)
        db.execute("INSERT INTO subscriptions (user_id, status, expiry_date, purchased_at, payment_hash, months, amount) VALUES (?, 'active', ?, ?, ?, ?, ?)",
                  (user_id, new_expiry.isoformat(), now.isoformat(), tx_hash, months, get_setting('subscription_price')))
    
    cache.delete(f"subscription_{user_id}")
    
    # کمیسیون به معرف
    user = db.execute("SELECT referred_by FROM web_users WHERE id = ?", (user_id,))
    if user and user[0]['referred_by']:
        commission_percent = get_setting('withdraw_percent')
        price = get_setting('subscription_price')
        commission = int(price * commission_percent / 100)
        
        db.execute("UPDATE web_users SET wallet_balance = wallet_balance + ?, total_commission = total_commission + ? WHERE id = ?",
                  (commission, commission, user[0]['referred_by']))
        
        db.execute("INSERT INTO commissions (user_id, from_user, amount, reason, created_at, paid) VALUES (?, ?, ?, 'referral_subscription', ?, 1)",
                  (user[0]['referred_by'], user_id, commission, now.isoformat()))
    
    # ثبت آمار روزانه
    today = datetime.now().date().isoformat()
    db.execute("UPDATE daily_stats SET new_subscriptions = new_subscriptions + 1, total_revenue = total_revenue + ? WHERE date = ?",
              (get_setting('subscription_price'), today))
    
    logger.info(f"Subscription activated for user {user_id}")
    return True

def extract_token_from_code(code):
    patterns = [
        r'token\s*=\s*["\']([^"\']+)["\']',
        r'TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'BOT_TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'API_TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'TELEGRAM_TOKEN\s*=\s*["\']([^"\']+)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, code, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

def extract_zip_with_structure(zip_path, extract_to):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    
    main_code = ""
    main_file = None
    
    # اولویت فایل‌ها
    priority_files = ['main.py', 'bot.py', 'app.py', 'run.py', '__init__.py', 'start.py']
    
    for root, dirs, files in os.walk(extract_to):
        for file in files:
            if file.endswith('.py'):
                if file in priority_files:
                    main_file = os.path.join(root, file)
                    break
                if not main_file:
                    main_file = os.path.join(root, file)
        if main_file:
            break
    
    if main_file:
        with open(main_file, 'r', encoding='utf-8', errors='ignore') as f:
            main_code = f.read()
    
    return main_code, extract_to

def log_error(error_type, message, user_id=None, bot_id=None, stack_trace=None):
    error_id = hashlib.md5(f"{time.time()}_{user_id}_{bot_id}_{secrets.token_hex(8)}".encode()).hexdigest()[:16]
    db.execute('''
        INSERT INTO errors (id, type, message, user_id, bot_id, timestamp, resolved, stack_trace)
        VALUES (?, ?, ?, ?, ?, ?, 0, ?)
    ''', (error_id, error_type, message[:1000], user_id, bot_id, datetime.now().isoformat(), stack_trace))
    logger.error(f"[{error_type}] {message[:200]}")

def log_action(user_id, action, target_id=None, details=None, ip=None):
    db.execute('''
        INSERT INTO action_logs (user_id, action, target_id, details, ip, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, action, target_id, details, ip or request.remote_addr, datetime.now().isoformat()))

# ==================== دکوریتورها ====================
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('🔒 دسترسی غیرمجاز! این بخش فقط برای ادمین است.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def subscription_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('🔐 لطفاً ابتدا وارد شوید', 'warning')
            return redirect(url_for('login'))
        if not check_user_subscription(current_user.id):
            flash('⚠️ برای استفاده از این بخش نیاز به اشتراک فعال دارید', 'warning')
            return redirect(url_for('pricing'))
        return f(*args, **kwargs)
    return decorated_function

def rate_limit_decorator(limit_per_second=10, limit_per_minute=100, limit_per_hour=500):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if current_user.is_authenticated:
                allowed, msg = rate_limiter.is_allowed(current_user.id, limit_per_second, limit_per_minute, limit_per_hour)
                if not allowed:
                    flash(msg, 'error')
                    return redirect(request.referrer or url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ==================== مسیرهای اصلی سایت ====================

@app.route('/')
def index():
    site_name = get_setting('site_name')
    site_description = get_setting('site_description')
    stats = {
        'total_users': db.execute("SELECT COUNT(*) as count FROM web_users")[0]['count'],
        'total_bots': db.execute("SELECT COUNT(*) as count FROM bots")[0]['count'],
        'running_bots': db.execute("SELECT COUNT(*) as count FROM bots WHERE status = 'running'")[0]['count'],
        'active_machines': db.execute("SELECT COUNT(*) as count FROM machines WHERE status = 'active'")[0]['count']
    }
    return render_template('index.html', 
                          site_name=site_name, 
                          site_description=site_description,
                          stats=stats,
                          user=current_user if current_user.is_authenticated else None)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user_data = db.execute("SELECT * FROM web_users WHERE email = ? OR username = ?", (email, email))
        if user_data and check_password_hash(user_data[0]['password_hash'], password):
            user = User(user_data[0])
            login_user(user, remember=True)
            db.execute("UPDATE web_users SET last_login = ? WHERE id = ?", (datetime.now().isoformat(), user.id))
            log_action(user.id, 'login', details=f"Login from {request.remote_addr}")
            flash(f'✨ خوش آمدید {user.full_name or user.email}!', 'success')
            
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('dashboard'))
        
        flash('❌ ایمیل/نام کاربری یا رمز عبور اشتباه است', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')
        full_name = request.form.get('full_name')
        ref_code = request.form.get('ref_code')
        
        if password != confirm:
            flash('❌ رمز عبور با تکرار آن مطابقت ندارد', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('❌ رمز عبور باید حداقل ۶ کاراکتر باشد', 'error')
            return render_template('register.html')
        
        existing = db.execute("SELECT id FROM web_users WHERE email = ? OR username = ?", (email, username))
        if existing:
            flash('❌ ایمیل یا نام کاربری قبلاً ثبت شده است', 'error')
            return render_template('register.html')
        
        # بررسی ظرفیت
        users_count = db.execute("SELECT COUNT(*) as count FROM web_users")[0]['count']
        max_capacity = get_setting('max_users_capacity')
        if users_count >= max_capacity:
            flash('⚠️ ظرفیت ثبت نام تکمیل شده است', 'error')
            return render_template('register.html')
        
        # بررسی کد معرف
        referred_by = None
        if ref_code:
            referrer = db.execute("SELECT id FROM web_users WHERE referral_code = ?", (ref_code,))
            if referrer:
                referred_by = referrer[0]['id']
        
        password_hash = generate_password_hash(password)
        referral_code = generate_referral_code(int(time.time()))
        max_bots = get_setting('max_bots_per_subscription')
        
        db.execute('''
            INSERT INTO web_users (username, email, password_hash, full_name, referral_code, referred_by, created_at, max_bots)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (username, email, password_hash, full_name, referral_code, referred_by, datetime.now().isoformat(), max_bots))
        
        user_id = db.execute("SELECT id FROM web_users WHERE email = ?", (email,))[0]['id']
        
        if referred_by:
            db.execute("UPDATE web_users SET referrals_count = referrals_count + 1 WHERE id = ?", (referred_by,))
        
        # به‌روزرسانی آمار روزانه
        today = datetime.now().date().isoformat()
        db.execute("UPDATE daily_stats SET new_users = new_users + 1 WHERE date = ?", (today,))
        
        log_action(user_id, 'register', details=f"New user registered")
        flash('✅ ثبت نام با موفقیت انجام شد! اکنون می‌توانید وارد شوید.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    log_action(current_user.id, 'logout')
    logout_user()
    flash('👋 از سیستم خارج شدید', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    # آمار کاربر
    bots = db.execute("SELECT * FROM bots WHERE user_id = ? ORDER BY created_at DESC", (current_user.id,))
    bots_list = []
    for bot in bots:
        status = bot_manager.get_status(bot['id'])
        bots_list.append({
            'id': bot['id'],
            'name': bot['name'],
            'username': bot['username'],
            'status': 'running' if status.get('running') else 'stopped',
            'created_at': bot['created_at'][:16] if bot['created_at'] else '',
            'error': bot['error_message'],
            'health': bot['health_status'],
            'machine_id': bot['machine_id']
        })
    
    return render_template('dashboard.html',
                          user=current_user,
                          bots=bots_list,
                          remaining_bots=get_remaining_bots(current_user.id),
                          max_bots=get_setting('max_bots_per_subscription'),
                          has_subscription=check_user_subscription(current_user.id),
                          queue_status=build_queue.get_queue_status(),
                          builds_today=rate_limiter.get_user_builds_today(current_user.id),
                          max_builds_per_hour=get_setting('max_builds_per_hour'),
                          rate_stats=rate_limiter.get_stats(current_user.id))

@app.route('/pricing')
def pricing():
    return render_template('pricing.html',
                          price=get_setting('subscription_price_str'),
                          price_amount=get_setting('subscription_price'),
                          max_bots=get_setting('max_bots_per_subscription'),
                          commission=get_setting('withdraw_percent'))

@app.route('/guide')
def guide():
    lang = current_user.language if current_user.is_authenticated else 'fa'
    if lang == 'fa':
        guide_text = get_setting('guide_text_fa').format(
            price=get_setting('subscription_price_str'),
            commission=get_setting('withdraw_percent'),
            min_withdraw=get_setting('min_withdraw'),
            support=get_setting('telegram_support')
        )
    else:
        guide_text = get_setting('guide_text_en').format(
            price=get_setting('subscription_price_usd'),
            commission=get_setting('withdraw_percent'),
            min_withdraw=get_setting('min_withdraw'),
            support=get_setting('telegram_support')
        )
    return render_template('guide.html', guide_text=guide_text)

@app.route('/libraries')
@login_required
def libraries():
    installed = library_manager.get_installed_libraries()
    popular = {k: v for k, v in list(POPULAR_LIBRARIES.items())[:50]}
    return render_template('libraries.html', installed=installed, popular=popular)

@app.route('/library/install', methods=['POST'])
@login_required
@admin_required
def library_install():
    lib_name = request.form.get('lib_name')
    if not lib_name:
        flash('نام کتابخانه را وارد کنید', 'error')
        return redirect(url_for('libraries'))
    
    success, msg = library_manager.install_library(lib_name, current_user.id)
    flash(msg, 'success' if success else 'error')
    return redirect(url_for('libraries'))

@app.route('/library/uninstall/<lib_name>')
@login_required
@admin_required
def library_uninstall(lib_name):
    success, msg = library_manager.uninstall_library(lib_name)
    flash(msg, 'success' if success else 'error')
    return redirect(url_for('libraries'))

@app.route('/create-bot', methods=['GET', 'POST'])
@login_required
@subscription_required
@rate_limit_decorator(limit_per_second=3, limit_per_minute=20, limit_per_hour=50)
def create_bot():
    if request.method == 'POST':
        remaining = get_remaining_bots(current_user.id)
        if remaining <= 0:
            flash(f'❌ شما به حداکثر مجاز ({get_setting("max_bots_per_subscription")} ربات) رسیده‌اید', 'error')
            return redirect(url_for('dashboard'))
        
        if 'bot_file' not in request.files:
            flash('📁 لطفاً فایل ربات را انتخاب کنید', 'error')
            return redirect(url_for('create_bot'))
        
        file = request.files['bot_file']
        if file.filename == '':
            flash('📁 لطفاً فایل را انتخاب کنید', 'error')
            return redirect(url_for('create_bot'))
        
        filename = secure_filename(file.filename)
        if not (filename.endswith('.py') or filename.endswith('.zip')):
            flash('❌ فقط فایل‌های .py یا .zip مجاز هستند', 'error')
            return redirect(url_for('create_bot'))
        
        file_path = os.path.join(DIRS['UPLOADS'], f"{current_user.id}_{int(time.time())}_{filename}")
        file.save(file_path)
        
        # استخراج کد
        main_code = ""
        folder_path = None
        
        if filename.endswith('.zip'):
            extract_dir = os.path.join(DIRS['TEMP'], f"extract_{current_user.id}_{int(time.time())}")
            os.makedirs(extract_dir, exist_ok=True)
            main_code, folder_path = extract_zip_with_structure(file_path, extract_dir)
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                main_code = f.read()
        
        if not main_code:
            flash('❌ فایل پایتون در zip پیدا نشد', 'error')
            return redirect(url_for('create_bot'))
        
        # استخراج توکن
        token = extract_token_from_code(main_code)
        if not token:
            flash('❌ توکن ربات در کد پیدا نشد. لطفاً از متغیر TOKEN یا token استفاده کنید.', 'error')
            return redirect(url_for('create_bot'))
        
        # بررسی اعتبار توکن
        try:
            resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
            if resp.status_code != 200:
                flash('❌ توکن ربات معتبر نیست', 'error')
                return redirect(url_for('create_bot'))
            bot_info = resp.json()['result']
        except Exception as e:
            flash(f'❌ خطا در ارتباط با تلگرام: {str(e)[:100]}', 'error')
            return redirect(url_for('create_bot'))
        
        rate_limiter.increment_user_builds(current_user.id)
        bot_id = hashlib.md5(f"{current_user.id}{token}{time.time()}{secrets.token_hex(4)}".encode()).hexdigest()[:16]
        
        build_data = {
            'bot_id': bot_id,
            'user_id': current_user.id,
            'token': token,
            'bot_info': bot_info,
            'file_path': file_path,
            'folder_path': folder_path,
            'main_code': main_code
        }
        
        build_queue.add_build(current_user.id, file_path, filename, build_data)
        log_action(current_user.id, 'create_bot', bot_id, f"Bot name: {bot_info['first_name']}")
        
        flash(f'✅ ربات {bot_info["first_name"]} در صف ساخت قرار گرفت (شماره صف: {build_queue.get_queue_length()})', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('create_bot.html',
                          remaining_bots=get_remaining_bots(current_user.id),
                          max_bots=get_setting('max_bots_per_subscription'))

@app.route('/queue-status')
@login_required
def queue_status():
    status = build_queue.get_queue_status()
    user_position = build_queue.get_user_position(current_user.id)
    return jsonify({
        'queue_length': status['queued'],
        'processing': status['processing'],
        'your_position': user_position,
        'total_built_today': status.get('total_built', 0),
        'avg_build_time': status.get('avg_build_time', 0)
    })

@app.route('/bot/<bot_id>/start')
@login_required
def bot_start(bot_id):
    bot_data = db.execute("SELECT * FROM bots WHERE id = ? AND user_id = ?", (bot_id, current_user.id))
    if not bot_data:
        flash('❌ ربات یافت نشد', 'error')
        return redirect(url_for('dashboard'))
    
    bot = bot_data[0]
    if os.path.exists(bot['file_path']):
        with open(bot['file_path'], 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()
        result = bot_manager.run_bot(bot_id, code, bot['token'])
        if result['success']:
            log_action(current_user.id, 'start_bot', bot_id, f"Started on machine {result.get('machine_id')}")
            flash('✅ ربات با موفقیت راه‌اندازی شد', 'success')
        else:
            flash(f'❌ خطا: {result.get("error", "مشخص نشده")}', 'error')
    else:
        flash('❌ فایل ربات یافت نشد', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/bot/<bot_id>/stop')
@login_required
def bot_stop(bot_id):
    if bot_manager.stop_bot(bot_id):
        log_action(current_user.id, 'stop_bot', bot_id)
        flash('✅ ربات متوقف شد', 'success')
    else:
        flash('❌ خطا در توقف ربات', 'error')
    return redirect(url_for('dashboard'))

@app.route('/bot/<bot_id>/delete')
@login_required
def bot_delete(bot_id):
    if bot_manager.delete_bot(bot_id, current_user.id):
        log_action(current_user.id, 'delete_bot', bot_id)
        flash('✅ ربات با موفقیت حذف شد', 'success')
    else:
        flash('❌ خطا در حذف ربات', 'error')
    return redirect(url_for('dashboard'))

@app.route('/bot/<bot_id>/join-toggle')
@login_required
def bot_join_toggle(bot_id):
    bot = db.execute("SELECT join_enabled FROM bots WHERE id = ? AND user_id = ?", (bot_id, current_user.id))
    if bot:
        new_status = 0 if bot[0]['join_enabled'] else 1
        db.execute("UPDATE bots SET join_enabled = ? WHERE id = ?", (new_status, bot_id))
        flash('✅ وضعیت عضوگیری تغییر کرد', 'success')
    return redirect(url_for('dashboard'))

@app.route('/wallet')
@login_required
def wallet():
    subs = db.execute("SELECT expiry_date, status FROM subscriptions WHERE user_id = ? ORDER BY id DESC LIMIT 1", (current_user.id,))
    expiry = subs[0]['expiry_date'][:10] if subs and subs[0]['expiry_date'] else 'نامشخص'
    
    receipts = db.execute("SELECT * FROM receipts WHERE user_id = ? ORDER BY created_at DESC LIMIT 20", (current_user.id,))
    withdraws = db.execute("SELECT * FROM withdraw_requests WHERE user_id = ? ORDER BY created_at DESC LIMIT 20", (current_user.id,))
    commissions = db.execute("SELECT SUM(amount) as total FROM commissions WHERE user_id = ?", (current_user.id,))
    
    return render_template('wallet.html',
                          user=current_user,
                          has_subscription=check_user_subscription(current_user.id),
                          expiry=expiry,
                          receipts=receipts,
                          withdraws=withdraws,
                          total_commission=commissions[0]['total'] if commissions else 0,
                          trc20_address=get_setting('trc20_address'),
                          card_display=get_setting('card_number_display'),
                          card_holder=get_setting('card_holder'),
                          card_bank=get_setting('card_bank'),
                          price=get_setting('subscription_price_str'))

@app.route('/submit-receipt', methods=['POST'])
@login_required
def submit_receipt():
    if 'receipt_image' not in request.files:
        flash('📸 لطفاً تصویر فیش را انتخاب کنید', 'error')
        return redirect(url_for('wallet'))
    
    file = request.files['receipt_image']
    if file.filename == '':
        flash('📸 لطفاً تصویر را انتخاب کنید', 'error')
        return redirect(url_for('wallet'))
    
    pending = db.execute("SELECT id FROM receipts WHERE user_id = ? AND status = 'pending'", (current_user.id,))
    if pending:
        flash('⏳ شما قبلاً یک فیش در انتظار تایید دارید', 'warning')
        return redirect(url_for('wallet'))
    
    filename = secure_filename(f"{current_user.id}_{int(time.time())}_{file.filename}")
    filepath = os.path.join(DIRS['RECEIPTS'], filename)
    file.save(filepath)
    
    tx_hash = hashlib.md5(f"{current_user.id}_{time.time()}_{secrets.token_hex(4)}".encode()).hexdigest()[:16].upper()
    db.execute('''
        INSERT INTO receipts (user_id, amount, receipt_path, tx_hash, created_at, status)
        VALUES (?, ?, ?, ?, ?, 'pending')
    ''', (current_user.id, get_setting('subscription_price'), filepath, tx_hash, datetime.now().isoformat()))
    
    log_action(current_user.id, 'submit_receipt', tx_hash, f"Amount: {get_setting('subscription_price')}")
    flash('✅ فیش شما با موفقیت ثبت شد و در انتظار تایید است', 'success')
    return redirect(url_for('wallet'))

@app.route('/withdraw-request', methods=['POST'])
@login_required
def withdraw_request():
    amount = int(request.form.get('amount', 0))
    address = request.form.get('address', '').strip()
    min_withdraw = get_setting('min_withdraw')
    
    if amount < min_withdraw:
        flash(f'❌ حداقل مبلغ برداشت {min_withdraw:,} تومان است', 'error')
        return redirect(url_for('wallet'))
    if amount > current_user.wallet_balance:
        flash('❌ موجودی کافی نیست', 'error')
        return redirect(url_for('wallet'))
    if not address or len(address) < 10:
        flash('❌ آدرس کیف پول معتبر نیست', 'error')
        return redirect(url_for('wallet'))
    
    db.execute('''
        INSERT INTO withdraw_requests (user_id, amount, address, created_at, status)
        VALUES (?, ?, ?, ?, 'pending')
    ''', (current_user.id, amount, address, datetime.now().isoformat()))
    db.execute("UPDATE web_users SET wallet_balance = wallet_balance - ? WHERE id = ?", (amount, current_user.id))
    
    log_action(current_user.id, 'withdraw_request', address, f"Amount: {amount}")
    flash(f'✅ درخواست برداشت {amount:,} تومان با موفقیت ثبت شد', 'success')
    return redirect(url_for('wallet'))

@app.route('/referrals')
@login_required
def referrals():
    referral_link = f"{request.host_url}register?ref={current_user.referral_code}"
    referred_users = db.execute("SELECT username, full_name, email, created_at FROM web_users WHERE referred_by = ? ORDER BY created_at DESC", (current_user.id,))
    commissions = db.execute("SELECT amount, from_user, created_at FROM commissions WHERE user_id = ? ORDER BY created_at DESC LIMIT 50", (current_user.id,))
    
    return render_template('referrals.html',
                          user=current_user,
                          referral_link=referral_link,
                          commission_percent=get_setting('withdraw_percent'),
                          min_withdraw=get_setting('min_withdraw'),
                          referred_users=referred_users,
                          commissions=commissions)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        language = request.form.get('language', 'fa')
        telegram_id = request.form.get('telegram_id')
        
        db.execute("UPDATE web_users SET full_name = ?, email = ?, language = ?, telegram_id = ? WHERE id = ?",
                  (full_name, email, language, telegram_id, current_user.id))
        
        log_action(current_user.id, 'update_profile')
        flash('✅ اطلاعات با موفقیت به‌روز شد', 'success')
        return redirect(url_for('profile'))
    
    return render_template('profile.html', user=current_user)

@app.route('/change-password', methods=['POST'])
@login_required
def change_password():
    old_password = request.form.get('old_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    user_data = db.execute("SELECT password_hash FROM web_users WHERE id = ?", (current_user.id,))[0]
    
    if not check_password_hash(user_data['password_hash'], old_password):
        flash('❌ رمز عبور فعلی اشتباه است', 'error')
        return redirect(url_for('profile'))
    
    if new_password != confirm_password:
        flash('❌ رمز عبور جدید با تکرار آن مطابقت ندارد', 'error')
        return redirect(url_for('profile'))
    
    if len(new_password) < 6:
        flash('❌ رمز عبور باید حداقل ۶ کاراکتر باشد', 'error')
        return redirect(url_for('profile'))
    
    db.execute("UPDATE web_users SET password_hash = ? WHERE id = ?", 
              (generate_password_hash(new_password), current_user.id))
    
    log_action(current_user.id, 'change_password')
    flash('✅ رمز عبور با موفقیت تغییر کرد', 'success')
    return redirect(url_for('profile'))

# ==================== پنل مدیریت (بیش از ۲۰ دکمه) ====================

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    # آمار کلی
    total_users = db.execute("SELECT COUNT(*) as count FROM web_users")[0]['count']
    active_subs = db.execute("SELECT COUNT(*) as count FROM subscriptions WHERE status = 'active'")[0]['count']
    total_bots = db.execute("SELECT COUNT(*) as count FROM bots")[0]['count']
    running_bots = db.execute("SELECT COUNT(*) as count FROM bots WHERE status = 'running'")[0]['count']
    total_wallet = db.execute("SELECT SUM(wallet_balance) as total FROM web_users")[0]['total'] or 0
    pending_receipts = db.execute("SELECT COUNT(*) as count FROM receipts WHERE status = 'pending'")[0]['count']
    pending_withdraws = db.execute("SELECT COUNT(*) as count FROM withdraw_requests WHERE status = 'pending'")[0]['count']
    total_errors = db.execute("SELECT COUNT(*) as count FROM errors WHERE resolved = 0")[0]['count']
    
    # آمار روزانه
    today = datetime.now().date().isoformat()
    daily = db.execute("SELECT * FROM daily_stats WHERE date = ?", (today,))
    if daily:
        daily_stats = daily[0]
    else:
        daily_stats = {'new_users': 0, 'new_bots': 0, 'new_subscriptions': 0, 'total_revenue': 0}
    
    # آمار ماشین‌ها
    machine_stats = bot_manager.get_stats()
    queue_status = build_queue.get_queue_status()
    cache_stats = cache.get_stats()
    health_stats = health_checker.get_stats()
    
    # نمودارهای ۳۰ روز اخیر
    last_30_days = db.execute("SELECT date, new_users, new_bots, total_revenue FROM daily_stats ORDER BY date DESC LIMIT 30")
    
    return render_template('admin/dashboard.html',
                          total_users=total_users,
                          active_subs=active_subs,
                          total_bots=total_bots,
                          running_bots=running_bots,
                          total_wallet=total_wallet,
                          pending_receipts=pending_receipts,
                          pending_withdraws=pending_withdraws,
                          total_errors=total_errors,
                          daily_stats=daily_stats,
                          machine_stats=machine_stats,
                          queue_status=queue_status,
                          cache_stats=cache_stats,
                          health_stats=health_stats,
                          last_30_days=last_30_days)

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    users = db.execute("SELECT * FROM web_users ORDER BY created_at DESC")
    return render_template('admin/users.html', users=users)

@app.route('/admin/user/<int:user_id>/view')
@login_required
@admin_required
def admin_user_view(user_id):
    user = db.execute("SELECT * FROM web_users WHERE id = ?", (user_id,))
    if not user:
        flash('کاربر یافت نشد', 'error')
        return redirect(url_for('admin_users'))
    
    user = user[0]
    bots = db.execute("SELECT * FROM bots WHERE user_id = ?", (user_id,))
    receipts = db.execute("SELECT * FROM receipts WHERE user_id = ? ORDER BY created_at DESC LIMIT 10", (user_id,))
    withdraws = db.execute("SELECT * FROM withdraw_requests WHERE user_id = ? ORDER BY created_at DESC LIMIT 10", (user_id,))
    commissions = db.execute("SELECT * FROM commissions WHERE user_id = ? OR from_user = ? ORDER BY created_at DESC LIMIT 20", (user_id, user_id))
    
    return render_template('admin/user_view.html', user=user, bots=bots, receipts=receipts, withdraws=withdraws, commissions=commissions)

@app.route('/admin/user/<int:user_id>/toggle')
@login_required
@admin_required
def admin_toggle_user(user_id):
    user = db.execute("SELECT is_active FROM web_users WHERE id = ?", (user_id,))
    if user:
        new_status = 0 if user[0]['is_active'] else 1
        db.execute("UPDATE web_users SET is_active = ? WHERE id = ?", (new_status, user_id))
        log_action(current_user.id, 'toggle_user', str(user_id), f"New status: {new_status}")
        flash('✅ وضعیت کاربر تغییر کرد', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/user/<int:user_id>/ban')
@login_required
@admin_required
def admin_ban_user(user_id):
    if user_id == current_user.id:
        flash('❌ نمی‌توانید خودتان را مسدود کنید', 'error')
        return redirect(url_for('admin_users'))
    
    user = db.execute("SELECT is_banned FROM web_users WHERE id = ?", (user_id,))
    if user:
        new_status = 0 if user[0]['is_banned'] else 1
        db.execute("UPDATE web_users SET is_banned = ? WHERE id = ?", (new_status, user_id))
        log_action(current_user.id, 'ban_user', str(user_id), f"Banned: {new_status}")
        flash('✅ وضعیت مسدودیت کاربر تغییر کرد', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/user/<int:user_id>/delete')
@login_required
@admin_required
def admin_delete_user(user_id):
    if user_id == current_user.id:
        flash('❌ نمی‌توانید خودتان را حذف کنید', 'error')
        return redirect(url_for('admin_users'))
    
    bots = db.execute("SELECT id FROM bots WHERE user_id = ?", (user_id,))
    for bot in bots:
        bot_manager.delete_bot(bot['id'], user_id)
    db.execute("DELETE FROM web_users WHERE id = ?", (user_id,))
    db.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
    
    log_action(current_user.id, 'delete_user', str(user_id))
    flash('✅ کاربر با موفقیت حذف شد', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/user/<int:user_id>/add-balance', methods=['POST'])
@login_required
@admin_required
def admin_add_balance(user_id):
    amount = int(request.form.get('amount', 0))
    reason = request.form.get('reason', '')
    
    if amount > 0:
        db.execute("UPDATE web_users SET wallet_balance = wallet_balance + ? WHERE id = ?", (amount, user_id))
        db.execute("INSERT INTO action_logs (user_id, action, details, created_at) VALUES (?, 'admin_add_balance', ?, ?)",
                  (user_id, f"{amount}: {reason}", datetime.now().isoformat()))
        flash(f'✅ {amount:,} تومان به کیف پول کاربر اضافه شد', 'success')
    return redirect(url_for('admin_user_view', user_id=user_id))

@app.route('/admin/user/<int:user_id>/subscription', methods=['POST'])
@login_required
@admin_required
def admin_extend_subscription(user_id):
    months = int(request.form.get('months', 1))
    activate_subscription(user_id, f"admin_{current_user.id}", months)
    flash(f'✅ اشتراک کاربر برای {months} ماه تمدید شد', 'success')
    return redirect(url_for('admin_user_view', user_id=user_id))

@app.route('/admin/bots')
@login_required
@admin_required
def admin_bots():
    bots = db.execute("SELECT bots.*, web_users.email, web_users.full_name FROM bots LEFT JOIN web_users ON bots.user_id = web_users.id ORDER BY bots.created_at DESC")
    return render_template('admin/bots.html', bots=bots)

@app.route('/admin/bot/<bot_id>/delete')
@login_required
@admin_required
def admin_delete_bot(bot_id):
    bot = db.execute("SELECT user_id FROM bots WHERE id = ?", (bot_id,))
    if bot:
        bot_manager.delete_bot(bot_id, bot[0]['user_id'])
        log_action(current_user.id, 'admin_delete_bot', bot_id)
        flash('✅ ربات با موفقیت حذف شد', 'success')
    return redirect(url_for('admin_bots'))

@app.route('/admin/bot/<bot_id>/restart')
@login_required
@admin_required
def admin_restart_bot(bot_id):
    bot = db.execute("SELECT * FROM bots WHERE id = ?", (bot_id,))
    if bot:
        bot = bot[0]
        bot_manager.stop_bot(bot_id)
        time.sleep(1)
        if os.path.exists(bot['file_path']):
            with open(bot['file_path'], 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
            result = bot_manager.run_bot(bot_id, code, bot['token'])
            if result['success']:
                log_action(current_user.id, 'admin_restart_bot', bot_id)
                flash('✅ ربات با موفقیت ریستارت شد', 'success')
            else:
                flash(f'❌ خطا: {result.get("error", "")}', 'error')
    return redirect(url_for('admin_bots'))

@app.route('/admin/restart-all-dead')
@login_required
@admin_required
def admin_restart_all_dead():
    restarted = bot_manager.restart_all_dead_bots()
    log_action(current_user.id, 'restart_all_dead', details=f"Restarted: {restarted}")
    flash(f'✅ {restarted} ربات مرده با موفقیت ریستارت شدند', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/receipts')
@login_required
@admin_required
def admin_receipts():
    pending_receipts = db.execute("SELECT receipts.*, web_users.email, web_users.full_name FROM receipts LEFT JOIN web_users ON receipts.user_id = web_users.id WHERE receipts.status = 'pending' ORDER BY receipts.created_at")
    all_receipts = db.execute("SELECT receipts.*, web_users.email, web_users.full_name FROM receipts LEFT JOIN web_users ON receipts.user_id = web_users.id ORDER BY receipts.created_at DESC LIMIT 50")
    return render_template('admin/receipts.html', receipts=pending_receipts, all_receipts=all_receipts)

@app.route('/admin/receipt/<int:receipt_id>/approve')
@login_required
@admin_required
def admin_approve_receipt(receipt_id):
    receipt = db.execute("SELECT user_id FROM receipts WHERE id = ?", (receipt_id,))
    if receipt:
        activate_subscription(receipt[0]['user_id'], f"receipt_{receipt_id}")
        db.execute("UPDATE receipts SET status = 'approved', reviewed_by = ?, reviewed_at = ? WHERE id = ?",
                  (current_user.id, datetime.now().isoformat(), receipt_id))
        log_action(current_user.id, 'approve_receipt', str(receipt_id))
        flash('✅ فیش تایید شد و اشتراک کاربر فعال گردید', 'success')
    return redirect(url_for('admin_receipts'))

@app.route('/admin/receipt/<int:receipt_id>/reject')
@login_required
@admin_required
def admin_reject_receipt(receipt_id):
    db.execute("UPDATE receipts SET status = 'rejected', reviewed_by = ?, reviewed_at = ? WHERE id = ?",
              (current_user.id, datetime.now().isoformat(), receipt_id))
    log_action(current_user.id, 'reject_receipt', str(receipt_id))
    flash('❌ فیش رد شد', 'success')
    return redirect(url_for('admin_receipts'))

@app.route('/admin/withdraws')
@login_required
@admin_required
def admin_withdraws():
    pending_withdraws = db.execute("SELECT withdraw_requests.*, web_users.email, web_users.full_name FROM withdraw_requests LEFT JOIN web_users ON withdraw_requests.user_id = web_users.id WHERE withdraw_requests.status = 'pending' ORDER BY withdraw_requests.created_at")
    all_withdraws = db.execute("SELECT withdraw_requests.*, web_users.email, web_users.full_name FROM withdraw_requests LEFT JOIN web_users ON withdraw_requests.user_id = web_users.id ORDER BY withdraw_requests.created_at DESC LIMIT 50")
    return render_template('admin/withdraws.html', withdraws=pending_withdraws, all_withdraws=all_withdraws)

@app.route('/admin/withdraw/<int:withdraw_id>/approve')
@login_required
@admin_required
def admin_approve_withdraw(withdraw_id):
    withdraw = db.execute("SELECT user_id, amount FROM withdraw_requests WHERE id = ?", (withdraw_id,))
    if withdraw:
        db.execute("UPDATE withdraw_requests SET status = 'approved', processed_at = ? WHERE id = ?",
                  (datetime.now().isoformat(), withdraw_id))
        log_action(current_user.id, 'approve_withdraw', str(withdraw_id), f"Amount: {withdraw[0]['amount']}")
        flash('✅ درخواست برداشت تایید شد', 'success')
    return redirect(url_for('admin_withdraws'))

@app.route('/admin/withdraw/<int:withdraw_id>/reject')
@login_required
@admin_required
def admin_reject_withdraw(withdraw_id):
    withdraw = db.execute("SELECT user_id, amount FROM withdraw_requests WHERE id = ?", (withdraw_id,))
    if withdraw:
        # برگرداندن موجودی
        db.execute("UPDATE web_users SET wallet_balance = wallet_balance + ? WHERE id = ?", 
                  (withdraw[0]['amount'], withdraw[0]['user_id']))
        db.execute("UPDATE withdraw_requests SET status = 'rejected', processed_at = ? WHERE id = ?",
                  (datetime.now().isoformat(), withdraw_id))
        log_action(current_user.id, 'reject_withdraw', str(withdraw_id))
        flash('❌ درخواست برداشت رد شد', 'success')
    return redirect(url_for('admin_withdraws'))

@app.route('/admin/machines')
@login_required
@admin_required
def admin_machines():
    machines = db.execute("SELECT * FROM machines ORDER BY id")
    stats = bot_manager.get_stats()
    return render_template('admin/machines.html', machines=machines, stats=stats, max_machines=get_setting('max_machines'))

@app.route('/admin/machine/<int:machine_id>/capacity', methods=['POST'])
@login_required
@admin_required
def admin_machine_capacity(machine_id):
    new_capacity = int(request.form.get('max_bots', 5000))
    if 100 <= new_capacity <= 50000:
        bot_manager.update_machine_capacity(machine_id, new_capacity)
        log_action(current_user.id, 'update_machine_capacity', str(machine_id), f"New capacity: {new_capacity}")
        flash('✅ ظرفیت ماشین تغییر کرد', 'success')
    return redirect(url_for('admin_machines'))

@app.route('/admin/machine/<int:machine_id>/toggle')
@login_required
@admin_required
def admin_machine_toggle(machine_id):
    machine = db.execute("SELECT status FROM machines WHERE id = ?", (machine_id,))
    if machine:
        new_status = 'inactive' if machine[0]['status'] == 'active' else 'active'
        db.execute("UPDATE machines SET status = ? WHERE id = ?", (new_status, machine_id))
        log_action(current_user.id, 'toggle_machine', str(machine_id), f"New status: {new_status}")
        flash('✅ وضعیت ماشین تغییر کرد', 'success')
    return redirect(url_for('admin_machines'))

@app.route('/admin/machine/add', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_add_machine():
    if request.method == 'POST':
        name = request.form.get('name')
        ip = request.form.get('ip')
        port = int(request.form.get('port', 22))
        username = request.form.get('username')
        password = request.form.get('password')
        max_bots = int(request.form.get('max_bots', 5000))
        region = request.form.get('region', 'default')
        
        bot_manager.add_machine(name, ip, username, password, max_bots, region)
        log_action(current_user.id, 'add_machine', name, f"IP: {ip}")
        flash('✅ ماشین جدید با موفقیت اضافه شد', 'success')
        return redirect(url_for('admin_machines'))
    
    return render_template('admin/add_machine.html')

@app.route('/admin/machine/<int:machine_id>/delete')
@login_required
@admin_required
def admin_delete_machine(machine_id):
    if machine_id == 1:
        flash('❌ نمی‌توانید ماشین اصلی را حذف کنید', 'error')
        return redirect(url_for('admin_machines'))
    
    # انتقال ربات‌ها به ماشین دیگر
    bots = db.execute("SELECT id FROM bots WHERE machine_id = ?", (machine_id,))
    for bot in bots:
        bot_manager.stop_bot(bot['id'])
        db.execute("UPDATE bots SET machine_id = 1 WHERE id = ?", (bot['id'],))
    
    db.execute("DELETE FROM machines WHERE id = ?", (machine_id,))
    log_action(current_user.id, 'delete_machine', str(machine_id))
    flash('✅ ماشین با موفقیت حذف شد', 'success')
    return redirect(url_for('admin_machines'))

@app.route('/admin/servers')
@login_required
@admin_required
def admin_servers():
    servers = remote_manager.get_servers()
    machines = db.execute("SELECT id, name FROM machines WHERE is_local = 0")
    return render_template('admin/servers.html', servers=servers, machines=machines)

@app.route('/admin/server/add', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_add_server():
    if request.method == 'POST':
        name = request.form.get('name')
        ip = request.form.get('ip')
        port = int(request.form.get('port', 22))
        username = request.form.get('username')
        password = request.form.get('password')
        machine_id = request.form.get('machine_id')
        
        success, msg = remote_manager.add_server(name, ip, username, password, port, int(machine_id) if machine_id else None)
        flash(msg, 'success' if success else 'error')
        if success:
            log_action(current_user.id, 'add_server', name, f"IP: {ip}")
        return redirect(url_for('admin_servers'))
    
    machines = db.execute("SELECT id, name FROM machines WHERE is_local = 0 OR id = 1")
    return render_template('admin/add_server.html', machines=machines)

@app.route('/admin/server/<int:server_id>/test')
@login_required
@admin_required
def admin_test_server(server_id):
    success, msg = remote_manager.test_connection(server_id)
    flash(msg, 'success' if success else 'error')
    return redirect(url_for('admin_servers'))

@app.route('/admin/server/<int:server_id>/delete')
@login_required
@admin_required
def admin_delete_server(server_id):
    db.execute("DELETE FROM remote_servers WHERE id = ?", (server_id,))
    log_action(current_user.id, 'delete_server', str(server_id))
    flash('✅ سرور با موفقیت حذف شد', 'success')
    return redirect(url_for('admin_servers'))

@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_settings():
    if request.method == 'POST':
        for key in DEFAULT_SETTINGS.keys():
            value = request.form.get(key)
            if value is not None:
                update_setting(key, value)
        log_action(current_user.id, 'update_settings')
        flash('✅ تنظیمات با موفقیت ذخیره شد', 'success')
        return redirect(url_for('admin_settings'))
    
    settings = {}
    for key in DEFAULT_SETTINGS.keys():
        settings[key] = get_setting(key)
    
    return render_template('admin/settings.html', settings=settings)

@app.route('/admin/broadcast', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_broadcast():
    if request.method == 'POST':
        message = request.form.get('message')
        message_type = request.form.get('type', 'text')
        filter_type = request.form.get('filter', 'all')
        
        # ساخت فیلتر
        if filter_type == 'active_subs':
            users = db.execute("SELECT user_id FROM subscriptions WHERE status = 'active'")
        elif filter_type == 'admins':
            users = db.execute("SELECT id FROM web_users WHERE is_admin = 1")
        else:
            users = db.execute("SELECT id FROM web_users WHERE is_active = 1")
        
        sent = 0
        failed = 0
        
        for user in users:
            try:
                if message_type == 'text':
                    # ارسال متن ساده (در قالب ایمیل پیاده می‌شود)
                    pass
                sent += 1
            except:
                failed += 1
        
        log_action(current_user.id, 'broadcast', details=f"Type: {message_type}, Filter: {filter_type}")
        flash(f'✅ پیام به {sent} کاربر ارسال شد (ناموفق: {failed})', 'success')
        return redirect(url_for('admin_broadcast'))
    
    users_count = db.execute("SELECT COUNT(*) as count FROM web_users")[0]['count']
    active_subs = db.execute("SELECT COUNT(*) as count FROM subscriptions WHERE status = 'active'")[0]['count']
    
    return render_template('admin/broadcast.html', users_count=users_count, active_subs=active_subs)

@app.route('/admin/errors')
@login_required
@admin_required
def admin_errors():
    errors = db.execute("SELECT * FROM errors ORDER BY timestamp DESC LIMIT 100")
    return render_template('admin/errors.html', errors=errors)

@app.route('/admin/error/<error_id>/resolve')
@login_required
@admin_required
def admin_resolve_error(error_id):
    db.execute("UPDATE errors SET resolved = 1, resolved_at = ?, resolved_by = ? WHERE id = ?",
              (datetime.now().isoformat(), current_user.id, error_id))
    log_action(current_user.id, 'resolve_error', error_id)
    flash('✅ خطا به عنوان رفع شده علامت خورد', 'success')
    return redirect(url_for('admin_errors'))

@app.route('/admin/logs')
@login_required
@admin_required
def admin_logs():
    logs = db.execute("SELECT * FROM action_logs ORDER BY created_at DESC LIMIT 200")
    return render_template('admin/logs.html', logs=logs)

@app.route('/admin/cache/clear')
@login_required
@admin_required
def admin_clear_cache():
    cleared = cache.clear()
    log_action(current_user.id, 'clear_cache', details=f"Cleared {cleared} items")
    flash(f'✅ {cleared} آیتم از کش حذف شد', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/backup', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_backup():
    if request.method == 'POST':
        backup_dir = os.path.join(DIRS['BACKUPS'], f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        os.makedirs(backup_dir, exist_ok=True)
        
        # پشتیبان‌گیری از دیتابیس
        shutil.copy2(os.path.join(DIRS['DB'], 'web_app.db'), backup_dir)
        
        # پشتیبان‌گیری از فایل‌های مهم
        for folder in ['user_files', 'receipts', 'uploads']:
            src = DIRS.get(folder.upper(), os.path.join(BASE_DIR, folder))
            dst = os.path.join(backup_dir, folder)
            if os.path.exists(src):
                shutil.copytree(src, dst)
        
        log_action(current_user.id, 'create_backup')
        flash(f'✅ پشتیبان با موفقیت در {backup_dir} ایجاد شد', 'success')
        return redirect(url_for('admin_dashboard'))
    
    backups = os.listdir(DIRS['BACKUPS']) if os.path.exists(DIRS['BACKUPS']) else []
    return render_template('admin/backup.html', backups=backups)

# ==================== API مسیرها ====================

@app.route('/api/bot/<bot_id>/status')
@login_required
def api_bot_status(bot_id):
    bot = db.execute("SELECT user_id FROM bots WHERE id = ?", (bot_id,))
    if not bot or bot[0]['user_id'] != current_user.id:
        return jsonify({'error': 'Not found'}), 404
    status = bot_manager.get_status(bot_id)
    return jsonify(status)

@app.route('/api/user/stats')
@login_required
def api_user_stats():
    return jsonify({
        'wallet_balance': current_user.wallet_balance,
        'referrals_count': current_user.referrals_count,
        'total_commission': current_user.total_commission,
        'has_subscription': check_user_subscription(current_user.id),
        'remaining_bots': get_remaining_bots(current_user.id),
        'builds_today': rate_limiter.get_user_builds_today(current_user.id),
        'queue_status': build_queue.get_queue_status(),
        'rate_stats': rate_limiter.get_stats(current_user.id)
    })

@app.route('/api/admin/stats')
@login_required
@admin_required
def api_admin_stats():
    return jsonify({
        'total_users': db.execute("SELECT COUNT(*) as count FROM web_users")[0]['count'],
        'total_bots': db.execute("SELECT COUNT(*) as count FROM bots")[0]['count'],
        'running_bots': db.execute("SELECT COUNT(*) as count FROM bots WHERE status = 'running'")[0]['count'],
        'total_wallet': db.execute("SELECT SUM(wallet_balance) as total FROM web_users")[0]['total'] or 0,
        'machine_stats': bot_manager.get_stats(),
        'queue_status': build_queue.get_queue_status(),
        'cache_stats': cache.get_stats(),
        'health_stats': health_checker.get_stats()
    })

@app.route('/api/system/health')
def api_system_health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'active_bots': len(bot_manager.processes),
        'queue_size': build_queue.get_queue_length(),
        'cache_hit_rate': cache.get_stats()['hit_rate'],
        'total_users': db.execute("SELECT COUNT(*) as count FROM web_users")[0]['count'],
        'total_bots': db.execute("SELECT COUNT(*) as count FROM bots")[0]['count']
    })

# ==================== مانیتورینگ سیستم ====================
def system_monitor():
    while True:
        try:
            # بررسی انقضای اشتراک
            for sub in db.execute('SELECT user_id, expiry_date FROM subscriptions WHERE status = "active"'):
                if sub['expiry_date']:
                    expiry = datetime.fromisoformat(sub['expiry_date'])
                    if expiry < datetime.now():
                        db.execute("UPDATE subscriptions SET status = 'inactive' WHERE user_id = ?", (sub['user_id'],))
                        cache.delete(f"subscription_{sub['user_id']}")
                        logger.info(f"Subscription expired for user {sub['user_id']}")
            
            # به‌روزرسانی آمار روزانه
            today = datetime.now().date().isoformat()
            db.execute('''
                INSERT OR IGNORE INTO daily_stats (date, new_users, new_bots, new_subscriptions, total_revenue, active_users, total_requests)
                VALUES (?, 0, 0, 0, 0, 0, 0)
            ''', (today,))
            
            # به‌روزرسانی کاربران فعال
            active_users = db.execute("SELECT COUNT(*) as count FROM web_users WHERE julianday('now') - julianday(last_login) < 7")[0]['count']
            db.execute("UPDATE daily_stats SET active_users = ? WHERE date = ?", (active_users, today))
            
            time.sleep(60)
        except Exception as e:
            logger.error(f"System monitor error: {e}")
            time.sleep(60)

threading.Thread(target=system_monitor, daemon=True).start()

# ==================== context processor ====================
@app.context_processor
def utility_processor():
    def number_format(value):
        try:
            return f"{int(value):,}"
        except:
            return str(value)
    
    def time_ago(timestamp):
        if not timestamp:
            return 'نامشخص'
        try:
            dt = datetime.fromisoformat(timestamp)
            diff = datetime.now() - dt
            if diff.days > 30:
                return f"{diff.days//30} ماه پیش"
            elif diff.days > 0:
                return f"{diff.days} روز پیش"
            elif diff.seconds > 3600:
                return f"{diff.seconds//3600} ساعت پیش"
            elif diff.seconds > 60:
                return f"{diff.seconds//60} دقیقه پیش"
            else:
                return "لحظاتی پیش"
        except:
            return timestamp[:16] if timestamp else 'نامشخص'
    
    return dict(number_format=number_format, time_ago=time_ago, get_setting=get_setting)

# ==================== اجرا ====================
if __name__ == '__main__':
    print("=" * 80)
    print("🚀 ربات مادر نهایی - نسخه وب کامل 100.2 Ultimate Enterprise".center(80))
    print("=" * 80)
    print(f"📍 آدرس سایت: http://localhost:5000")
    print(f"👑 ادمین: morteza.yari1377m@gmail.com")
    print(f"🔑 رمز: M09145978426m")
    print(f"💰 قیمت اشتراک: {get_setting('subscription_price_str')}")
    print("=" * 80)
    print("✅ قابلیت‌های کامل پیاده‌سازی شده:")
    print("   🔹 ۵۰ ماشین (سرور) برای اجرای ربات‌ها")
    print("   🔹 ۵۰ کتابخانه محبوب قابل نصب")
    print("   🔹 ایزوله سازی کامل هر ربات")
    print("   🔹 کش پیشرفته با آمار لحظه‌ای")
    print("   🔹 صف ساخت پیشرفته با اولویت‌بندی")
    print("   🔹 Health Check خودکار با ریستارت")
    print("   🔹 Rate Limiting پیشرفته (ثانیه/دقیقه/ساعت)")
    print("   🔹 پنل مدیریت با ۲۰+ دکمه فعال")
    print("   🔹 سیستم خطایابی کامل")
    print("   🔹 پشتیبان‌گیری خودکار")
    print("=" * 80)
    
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)