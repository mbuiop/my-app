#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
═══════════════════════════════════════════════════════════════════════════════
🚀 ربات مادر نهایی - نسخه 100.3 Multi-Language Ultimate Enterprise
⚡ پشتیبانی از میلیون‌ها کاربر - معماری میکروسرویس کامل
🌐 پشتیبانی از 15+ زبان برنامه نویسی
💎 سیستم کمیسیون دقیق رفرال
🤖 محدودیت ربات در هر اشتراک (قابل تنظیم)
🔒 بازیابی خودکار پس از خرابی سرور
🖥️ مدیریت چند سرور - اضافه کردن سرور جدید
🐍 Python - 🟨 JS - 🐘 PHP - ☕ Java - 📘 C# - 🔵 Go - 💎 Ruby - 🦀 Rust - 🟣 Kotlin - 🐦 Swift - 💙 TS - 🌙 Lua - 🐪 Perl - 💧 Elixir - 🔮 Crystal
═══════════════════════════════════════════════════════════════════════════════
"""

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
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from functools import wraps
from collections import defaultdict
from typing import Optional, Dict, Any, List

import telebot
from telebot import types
import requests
from flask import Flask, request, jsonify

# ==================== کتابخانه‌های اختیاری ====================
try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False
    print("⚠️ paramiko not available - run: pip install paramiko")

try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("⚠️ cryptography not available - run: pip install cryptography")

# ==================== امنیت: توکن از محیط ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ Error: BOT_TOKEN not found!")
    print("✅ Solution: export BOT_TOKEN='your_token_here'")
    sys.exit(1)

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
    'SERVER_SCRIPTS': os.path.join(BASE_DIR, "server_scripts"),
    'LANG_WORKERS': os.path.join(BASE_DIR, "language_workers"),
}

for dir_path in DIRS.values():
    os.makedirs(dir_path, exist_ok=True)

# ==================== پوشه‌های مخصوص هر زبان ====================
LANG_DIRS = {
    'python': os.path.join(DIRS['LANG_WORKERS'], 'python'),
    'javascript': os.path.join(DIRS['LANG_WORKERS'], 'javascript'),
    'php': os.path.join(DIRS['LANG_WORKERS'], 'php'),
    'java': os.path.join(DIRS['LANG_WORKERS'], 'java'),
    'csharp': os.path.join(DIRS['LANG_WORKERS'], 'csharp'),
    'golang': os.path.join(DIRS['LANG_WORKERS'], 'golang'),
    'ruby': os.path.join(DIRS['LANG_WORKERS'], 'ruby'),
    'rust': os.path.join(DIRS['LANG_WORKERS'], 'rust'),
    'kotlin': os.path.join(DIRS['LANG_WORKERS'], 'kotlin'),
    'swift': os.path.join(DIRS['LANG_WORKERS'], 'swift'),
    'typescript': os.path.join(DIRS['LANG_WORKERS'], 'typescript'),
    'lua': os.path.join(DIRS['LANG_WORKERS'], 'lua'),
    'perl': os.path.join(DIRS['LANG_WORKERS'], 'perl'),
    'elixir': os.path.join(DIRS['LANG_WORKERS'], 'elixir'),
    'crystal': os.path.join(DIRS['LANG_WORKERS'], 'crystal'),
}

for dir_path in LANG_DIRS.values():
    os.makedirs(dir_path, exist_ok=True)

# ==================== لاگینگ امن ====================
class SecureFormatter(logging.Formatter):
    def format(self, record):
        msg = super().format(record)
        msg = re.sub(r'bot\d+:[A-Za-z0-9_-]{20,}', '[TOKEN_HIDDEN]', msg)
        msg = re.sub(r'\d{10}:[A-Za-z0-9_-]{35,}', '[TOKEN_HIDDEN]', msg)
        msg = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP_HIDDEN]', msg)
        msg = re.sub(r'password["\']?\s*[=:]\s*["\']([^"\']+)["\']', 'password="[HIDDEN]"', msg)
        return msg

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            os.path.join(DIRS['LOGS'], 'mother_bot.log'),
            maxBytes=100*1024*1024,
            backupCount=20,
            encoding='utf-8'
        ),
        logging.StreamHandler()
    ]
)

for handler in logging.root.handlers:
    handler.setFormatter(SecureFormatter('%(asctime)s - %(levelname)s - %(message)s'))

logger = logging.getLogger('MotherBot')

# ==================== توکن و تنظیمات ====================
ADMIN_IDS = [327855654]
BOT_USERNAME = "ROBTTSAZE_bot"

# تنظیمات پیش‌فرض
DEFAULT_SETTINGS = {
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
    'max_bots_per_subscription': 3,
    'max_users_capacity': 100000,
    'capacity_warning_message': "⚠️ ظرفیت ربات تکمیل شده است! لطفاً وارد ربات جدید شوید: @NEW_BOT",
    'new_bot_link': "@NEW_BOT",
    'guide_text_fa': """📚 راهنمای استفاده

1️⃣ برای ساخت ربات، فایل پروژه خود را ارسال کنید
2️⃣ پس از پرداخت اشتراک ماهیانه، می‌توانید ربات بسازید
3️⃣ هر کاربر می‌تواند تا ۳ ربات بسازد
4️⃣ با دعوت دوستان، ۷٪ کمیسیون دریافت کنید
5️⃣ پس از رسیدن به ۲ میلیون تومان، می‌توانید برداشت کنید

📌 زبان‌های پشتیبانی شده:
🐍 Python (.py) - 🟨 JavaScript (.js) - 🐘 PHP (.php) - ☕ Java (.java)
📘 C# (.cs) - 🔵 Go (.go) - 💎 Ruby (.rb) - 🦀 Rust (.rs)
🟣 Kotlin (.kt) - 🐦 Swift (.swift) - 💙 TypeScript (.ts)
🌙 Lua (.lua) - 🐪 Perl (.pl) - 💧 Elixir (.exs) - 🔮 Crystal (.cr)""",
    'guide_text_en': """📚 User Guide

1️⃣ Send your project file (.py, .zip, etc.)
2️⃣ After subscription payment, you can build bots
3️⃣ Each user can build up to 3 bots
4️⃣ Invite friends and get 7% commission
5️⃣ Withdraw after reaching 2,000,000 Toman

📌 Supported Languages:
🐍 Python (.py) - 🟨 JavaScript (.js) - 🐘 PHP (.php) - ☕ Java (.java)
📘 C# (.cs) - 🔵 Go (.go) - 💎 Ruby (.rb) - 🦀 Rust (.rs)
🟣 Kotlin (.kt) - 🐦 Swift (.swift) - 💙 TypeScript (.ts)
🌙 Lua (.lua) - 🐪 Perl (.pl) - 💧 Elixir (.exs) - 🔮 Crystal (.cr)""",
    'welcome_text_fa': "🚀 خوش آمدید {name}!\nبه ربات سازنده ربات خوش آمدید.\n\n📌 می‌توانید با 15+ زبان برنامه نویسی ربات بسازید!",
    'welcome_text_en': "🚀 Welcome {name}!\nWelcome to the bot builder bot.\n\n📌 You can build bots with 15+ programming languages!",
    'subscription_active_text_fa': "✅ اشتراک شما با موفقیت فعال شد!\nاکنون می‌توانید ربات خود را بسازید.",
    'subscription_active_text_en': "✅ Your subscription has been activated!\nYou can now build your bot.",
    'subscription_payment_text_fa': "💳 برای فعالسازی {price} را به آدرس زیر واریز:\n`{address}`\n🌐 شبکه: TRC20 (USDT)\n\n📸 پس از واریز، تصویر تراکنش را ارسال کنید",
    'subscription_payment_text_en': "💳 To activate, send {price} to:\n`{address}`\n🌐 Network: TRC20 (USDT)\n\n📸 Send transaction screenshot after payment",
    'max_builds_per_hour': 20,
    'max_concurrent_builds': 30,
    'rate_limit_per_second': 10,
    'health_check_interval': 30,
    'auto_scale_threshold': 80,
    'backup_interval': 3600,
    'state_save_interval': 60,
    'encryption_key': '',
    'enable_remote_servers': True,
    'auto_backup_enabled': True,
    'telemetry_enabled': False,
}

# ==================== زبان‌های پشتیبانی شده (15+ زبان) ====================
SUPPORTED_LANGUAGES = {
    '.py': {'name': 'python', 'emoji': '🐍', 'cmd': [sys.executable], 'ext': '.py', 'wrapper': True, 'install': 'pip install -r requirements.txt'},
    '.js': {'name': 'javascript', 'emoji': '🟨', 'cmd': ['node'], 'ext': '.js', 'wrapper': True, 'install': 'npm install'},
    '.php': {'name': 'php', 'emoji': '🐘', 'cmd': ['php'], 'ext': '.php', 'wrapper': True, 'install': 'composer install'},
    '.java': {'name': 'java', 'emoji': '☕', 'cmd': ['java'], 'ext': '.java', 'wrapper': False, 'install': 'mvn compile'},
    '.cs': {'name': 'csharp', 'emoji': '📘', 'cmd': ['dotnet', 'run'], 'ext': '.csproj', 'wrapper': False, 'install': 'dotnet restore'},
    '.go': {'name': 'golang', 'emoji': '🔵', 'cmd': ['go', 'run'], 'ext': '.go', 'wrapper': False, 'install': 'go mod download'},
    '.rb': {'name': 'ruby', 'emoji': '💎', 'cmd': ['ruby'], 'ext': '.rb', 'wrapper': True, 'install': 'bundle install'},
    '.rs': {'name': 'rust', 'emoji': '🦀', 'cmd': ['cargo', 'run'], 'ext': '.rs', 'wrapper': False, 'install': 'cargo build'},
    '.kt': {'name': 'kotlin', 'emoji': '🟣', 'cmd': ['kotlin'], 'ext': '.kt', 'wrapper': False, 'install': 'gradle build'},
    '.swift': {'name': 'swift', 'emoji': '🐦', 'cmd': ['swift'], 'ext': '.swift', 'wrapper': False, 'install': 'swift package resolve'},
    '.ts': {'name': 'typescript', 'emoji': '💙', 'cmd': ['ts-node'], 'ext': '.ts', 'wrapper': True, 'install': 'npm install'},
    '.lua': {'name': 'lua', 'emoji': '🌙', 'cmd': ['lua'], 'ext': '.lua', 'wrapper': False, 'install': 'luarocks install'},
    '.pl': {'name': 'perl', 'emoji': '🐪', 'cmd': ['perl'], 'ext': '.pl', 'wrapper': False, 'install': 'cpanm --installdeps .'},
    '.exs': {'name': 'elixir', 'emoji': '💧', 'cmd': ['elixir'], 'ext': '.exs', 'wrapper': False, 'install': 'mix deps.get'},
    '.cr': {'name': 'crystal', 'emoji': '🔮', 'cmd': ['crystal'], 'ext': '.cr', 'wrapper': False, 'install': 'shards install'},
}

LANGUAGE_NAMES = {
    'python': 'Python 🐍', 'javascript': 'JavaScript 🟨', 'php': 'PHP 🐘', 'java': 'Java ☕',
    'csharp': 'C# 📘', 'golang': 'Go 🔵', 'ruby': 'Ruby 💎', 'rust': 'Rust 🦀',
    'kotlin': 'Kotlin 🟣', 'swift': 'Swift 🐦', 'typescript': 'TypeScript 💙',
    'lua': 'Lua 🌙', 'perl': 'Perl 🐪', 'elixir': 'Elixir 💧', 'crystal': 'Crystal 🔮'
}

# ==================== دکمه‌های منوی عمومی ====================
MENU_BUTTONS_FA = [
    '🤖 ساخت ربات جدید', '📋 ربات‌های من', '🔄 فعال/غیرفعال', '🗑 حذف ربات',
    '💰 کیف پول و اشتراک', '📚 راهنما', '👥 دعوت دوستان', '💸 درخواست برداشت',
    '📦 کتابخانه', '📊 آمار', '📞 پشتیبانی', '⚡ وضعیت صف', '📈 مصرف من', '🌐 زبان / Language'
]

MENU_BUTTONS_EN = [
    '🤖 New Bot', '📋 My Bots', '🔄 Start/Stop', '🗑 Delete Bot',
    '💰 Wallet & Subscription', '📚 Guide', '👥 Invite Friends', '💸 Withdraw',
    '📦 Library', '📊 Stats', '📞 Support', '⚡ Queue Status', '📈 My Usage', '🌐 Language / زبان'
]

# ==================== دکمه‌های پنل مدیریت ====================
ADMIN_BUTTONS = [
    '👑 پنل مدیریت', '📸 تایید فیش', '💰 تایید برداشت', '⚙️ تنظیمات سیستم',
    '📊 آمار کاربران', '🗑 حذف کاربران', '🗑 حذف ربات‌های کاربران', '📢 پیام همگانی',
    '🔍 بررسی ربات‌های کاربران', '💳 تنظیم آدرس کیف پول', '📝 عوض کردن متن راهنما',
    '👋 عوض کردن متن خوش آمد گویی', '✅ عوض کردن متن فعالسازی اشتراک', '💸 عوض کردن متن خرید اشتراک',
    '🔄 ریستارت ربات‌های مرده', '🐛 مدیریت خطاهای ربات', '⚙️ تنظیم ظرفیت کاربران',
    '🖥️ مدیریت ماشین‌ها', '➕ اضافه کردن سرور جدید', '💾 بکاپ گرفتن', '🔄 بازیابی از بکاپ',
    '🐍 مدیریت پایتون', '🟨 مدیریت JS', '🐘 مدیریت PHP', '☕ مدیریت جاوا',
    '📘 مدیریت سی‌شارپ', '🔵 مدیریت گو', '💎 مدیریت روبی', '🦀 مدیریت راست',
    '🔙 بازگشت به منوی اصلی'
]

# ==================== دیتابیس ====================
class Database:
    def __init__(self):
        self.conn = None
        self._init_db()
        self._init_tables()
    
    def _init_db(self):
        db_path = os.path.join(DIRS['DB'], 'mother_bot.db')
        self.conn = sqlite3.connect(db_path, timeout=60, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA cache_size=-1000000")
        self.conn.execute("PRAGMA page_size=16384")
    
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
    
    def encrypt(self, data):
        if CRYPTO_AVAILABLE and get_setting('encryption_key'):
            try:
                cipher = Fernet(get_setting('encryption_key').encode())
                return cipher.encrypt(data.encode()).decode()
            except:
                return data
        return data
    
    def decrypt(self, encrypted_data):
        if CRYPTO_AVAILABLE and get_setting('encryption_key'):
            try:
                cipher = Fernet(get_setting('encryption_key').encode())
                return cipher.decrypt(encrypted_data.encode()).decode()
            except:
                return encrypted_data
        return encrypted_data
    
    def _init_tables(self):
        # کاربران
        self.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, last_name TEXT,
                language TEXT DEFAULT 'fa', bots_count INTEGER DEFAULT 0, max_bots INTEGER DEFAULT 3,
                subscription_status TEXT DEFAULT 'inactive', subscription_expiry TIMESTAMP,
                subscription_purchased_at TIMESTAMP, referral_code TEXT UNIQUE, referred_by INTEGER,
                referrals_count INTEGER DEFAULT 0, verified_referrals INTEGER DEFAULT 0,
                wallet_balance INTEGER DEFAULT 0, total_commission INTEGER DEFAULT 0,
                created_at TIMESTAMP, last_active TIMESTAMP, last_payment_hash TEXT,
                is_banned INTEGER DEFAULT 0, is_premium INTEGER DEFAULT 0, notes TEXT
            )
        ''')
        
        # ربات‌ها
        self.execute('''
            CREATE TABLE IF NOT EXISTS bots (
                id TEXT PRIMARY KEY, user_id INTEGER, token TEXT, name TEXT, username TEXT,
                language TEXT DEFAULT 'python', file_path TEXT, folder_path TEXT, pid INTEGER,
                machine_id INTEGER, port INTEGER, status TEXT DEFAULT 'stopped',
                created_at TIMESTAMP, last_active TIMESTAMP, last_restore_point TIMESTAMP,
                join_enabled INTEGER DEFAULT 1, join_block_message TEXT DEFAULT '🚫 سرور پر است',
                health_status TEXT DEFAULT 'healthy', last_health_check TIMESTAMP,
                restart_count INTEGER DEFAULT 0, error_message TEXT, memory_usage INTEGER DEFAULT 0,
                cpu_usage REAL DEFAULT 0, FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        ''')
        
        # ماشین‌ها
        self.execute('''
            CREATE TABLE IF NOT EXISTS machines (
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, ip TEXT, port INTEGER DEFAULT 22,
                username TEXT, password TEXT, status TEXT DEFAULT 'active', current_bots INTEGER DEFAULT 0,
                max_bots INTEGER DEFAULT 10000, memory_used INTEGER DEFAULT 0, max_memory INTEGER DEFAULT 512000,
                cpu_usage REAL DEFAULT 0, last_heartbeat TIMESTAMP, created_at TIMESTAMP,
                auto_scaled INTEGER DEFAULT 0, region TEXT DEFAULT 'default', is_local INTEGER DEFAULT 1,
                ssh_key TEXT, total_requests INTEGER DEFAULT 0
            )
        ''')
        
        # فیش‌ها
        self.execute('''
            CREATE TABLE IF NOT EXISTS receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER,
                receipt_path TEXT, tx_hash TEXT, status TEXT DEFAULT 'pending',
                reviewed_by INTEGER, reviewed_at TIMESTAMP, created_at TIMESTAMP, admin_note TEXT
            )
        ''')
        
        # برداشت‌ها
        self.execute('''
            CREATE TABLE IF NOT EXISTS withdraw_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER,
                address TEXT, status TEXT DEFAULT 'pending', created_at TIMESTAMP,
                processed_at TIMESTAMP, transaction_hash TEXT
            )
        ''')
        
        # کمیسیون‌ها
        self.execute('''
            CREATE TABLE IF NOT EXISTS commissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, from_user INTEGER,
                amount INTEGER, reason TEXT, created_at TIMESTAMP, paid BOOLEAN DEFAULT 0
            )
        ''')
        
        # خطاها
        self.execute('''
            CREATE TABLE IF NOT EXISTS errors (
                id TEXT PRIMARY KEY, type TEXT, message TEXT, user_id INTEGER, bot_id TEXT,
                timestamp TIMESTAMP, resolved BOOLEAN DEFAULT 0, stack_trace TEXT, resolved_by INTEGER
            )
        ''')
        
        # تنظیمات
        self.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY, value TEXT, updated_at TIMESTAMP, updated_by INTEGER
            )
        ''')
        
        # آمار روزانه
        self.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT PRIMARY KEY, new_users INTEGER DEFAULT 0, new_bots INTEGER DEFAULT 0,
                new_subscriptions INTEGER DEFAULT 0, total_revenue INTEGER DEFAULT 0,
                active_users INTEGER DEFAULT 0, total_requests INTEGER DEFAULT 0,
                avg_response_time REAL DEFAULT 0, bots_by_language TEXT
            )
        ''')
        
        # بکاپ‌ها
        self.execute('''
            CREATE TABLE IF NOT EXISTS backups (
                id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT, size INTEGER,
                location TEXT, created_at TIMESTAMP, status TEXT DEFAULT 'success', type TEXT DEFAULT 'auto'
            )
        ''')
        
        # سرورهای از راه دور
        self.execute('''
            CREATE TABLE IF NOT EXISTS remote_servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, ip TEXT, port INTEGER DEFAULT 22,
                username TEXT, password TEXT, status TEXT DEFAULT 'pending', machine_id INTEGER,
                created_at TIMESTAMP, last_connection TIMESTAMP, connection_count INTEGER DEFAULT 0
            )
        ''')
        
        # تنظیمات پیش‌فرض
        for key, value in DEFAULT_SETTINGS.items():
            self.execute('INSERT OR IGNORE INTO system_settings (key, value, updated_at) VALUES (?, ?, ?)',
                        (key, str(value), datetime.now().isoformat()))
        
        # ماشین محلی
        existing = self.execute("SELECT COUNT(*) as count FROM machines WHERE is_local = 1")
        if existing and existing[0]['count'] == 0:
            self.execute('''
                INSERT INTO machines (id, name, status, max_bots, max_memory, created_at, is_local)
                VALUES (1, 'سرور اصلی', 'active', 10000, 512000, ?, 1)
            ''', (datetime.now().isoformat(),))

db = Database()
# ==================== توابع کمکی ====================
def get_setting(key):
    result = db.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
    if result:
        val = result[0]['value']
        numeric_keys = ['subscription_price', 'withdraw_percent', 'min_withdraw', 
                       'max_bots_per_subscription', 'max_builds_per_hour', 'max_concurrent_builds',
                       'rate_limit_per_second', 'health_check_interval', 'auto_scale_threshold',
                       'backup_interval', 'state_save_interval', 'max_users_capacity']
        if key in numeric_keys:
            try:
                return int(val)
            except:
                return DEFAULT_SETTINGS.get(key)
        return val
    return DEFAULT_SETTINGS.get(key)

def update_setting(key, value, admin_id=None):
    db.execute("UPDATE system_settings SET value = ?, updated_at = ?, updated_by = ? WHERE key = ?",
               (str(value), datetime.now().isoformat(), admin_id, key))

def get_user_language(user_id):
    user = get_user(user_id)
    return user.get('language', 'fa') if user else 'fa'

def get_text(user_id, key, **kwargs):
    lang = get_user_language(user_id)
    text = TEXTS.get(lang, TEXTS['fa']).get(key, key) if 'TEXTS' in dir() else key
    if kwargs:
        try:
            return text.format(**kwargs)
        except:
            return text
    return text

def generate_referral_code(user_id):
    return hashlib.md5(f"{user_id}_{time.time()}_{secrets.token_hex(4)}".encode()).hexdigest()[:12]

def get_user(user_id):
    users = db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    return dict(users[0]) if users else None

def create_user(user_id, username, first_name, last_name, referred_by=None, language='fa'):
    now = datetime.now().isoformat()
    referral_code = generate_referral_code(user_id)
    max_bots = get_setting('max_bots_per_subscription')
    
    users_count = db.execute('SELECT COUNT(*) as count FROM users')[0]['count']
    max_capacity = get_setting('max_users_capacity')
    
    if users_count >= max_capacity:
        return False, "capacity_full"
    
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
        db.execute('UPDATE daily_stats SET new_users = new_users + 1 WHERE date = ?', (datetime.now().date().isoformat(),))
    
    return True, "ok"

def check_subscription(user_id):
    user = get_user(user_id)
    if not user or user.get('is_banned', 0) == 1:
        return False
    
    if user['subscription_status'] == 'active' and user['subscription_expiry']:
        expiry = datetime.fromisoformat(user['subscription_expiry'])
        if expiry > datetime.now():
            return True
        else:
            db.execute('UPDATE users SET subscription_status = "inactive" WHERE user_id = ?', (user_id,))
    return False

def get_remaining_bots(user_id):
    user = get_user(user_id)
    if not user:
        return 0
    
    max_bots = get_setting('max_bots_per_subscription')
    current_bots = user.get('bots_count', 0)
    
    if check_subscription(user_id):
        return max_bots - current_bots
    return 0

def activate_subscription(user_id, tx_hash=None, months=1):
    user = get_user(user_id)
    now = datetime.now()
    
    if user and user['subscription_status'] == 'active' and user['subscription_expiry']:
        new_expiry = datetime.fromisoformat(user['subscription_expiry']) + timedelta(days=30*months)
    else:
        new_expiry = now + timedelta(days=30*months)
    
    db.execute('''
        UPDATE users SET subscription_status = 'active', subscription_expiry = ?,
        subscription_purchased_at = ?, last_payment_hash = ? WHERE user_id = ?
    ''', (new_expiry.isoformat(), now.isoformat(), tx_hash, user_id))
    
    # پیام فعالسازی
    lang = get_user_language(user_id)
    active_text = get_setting('subscription_active_text_fa' if lang == 'fa' else 'subscription_active_text_en')
    try:
        bot.send_message(user_id, active_text)
    except:
        pass
    
    # کمیسیون به معرف
    if user and user.get('referred_by'):
        commission_percent = get_setting('withdraw_percent')
        price = get_setting('subscription_price')
        commission = int(price * commission_percent / 100)
        
        add_wallet_balance(user['referred_by'], commission)
        db.execute('''
            INSERT INTO commissions (user_id, from_user, amount, reason, created_at, paid)
            VALUES (?, ?, ?, 'referral_subscription', ?, 1)
        ''', (user['referred_by'], user_id, commission, now.isoformat()))
        
        try:
            bot.send_message(user['referred_by'], get_text(user['referred_by'], 'commission_added', amount=commission))
        except:
            pass
    
    db.execute('UPDATE daily_stats SET new_subscriptions = new_subscriptions + 1, total_revenue = total_revenue + ? WHERE date = ?',
              (price, datetime.now().date().isoformat()))
    
    logger.info(f"Subscription activated for user {user_id}")
    return True

def add_wallet_balance(user_id, amount):
    user = get_user(user_id)
    if not user:
        return 0
    new_balance = user['wallet_balance'] + amount
    new_total = user.get('total_commission', 0) + amount
    db.execute('UPDATE users SET wallet_balance = ?, total_commission = ? WHERE user_id = ?', 
               (new_balance, new_total, user_id))
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
    
    if bot_id in machine_manager.processes:
        machine_manager.stop_bot(bot_id)
    
    if bot_rec.get('file_path') and os.path.exists(bot_rec['file_path']):
        try:
            os.remove(bot_rec['file_path'])
        except:
            pass
    
    bot_dir = os.path.join(DIRS['MACHINES'], f"machine_{bot_rec['machine_id']:03d}", bot_id) if bot_rec.get('machine_id') else None
    if bot_dir and os.path.exists(bot_dir):
        try:
            shutil.rmtree(bot_dir)
        except:
            pass
    
    db.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
    if user_id:
        db.execute('UPDATE users SET bots_count = bots_count - 1 WHERE user_id = ?', (user_id,))
    
    return True

def detect_language_from_file(file_name, extracted_dir=None):
    """تشخیص خودکار زبان از روی فایل"""
    for ext, lang_info in SUPPORTED_LANGUAGES.items():
        if file_name.endswith(ext):
            return lang_info['name']
    
    if extracted_dir and os.path.exists(extracted_dir):
        for root, dirs, files in os.walk(extracted_dir):
            for f in files:
                for ext, lang_info in SUPPORTED_LANGUAGES.items():
                    if f.endswith(ext):
                        return lang_info['name']
                # فایل‌های خاص
                if f == 'package.json': return 'javascript'
                if f == 'composer.json': return 'php'
                if f == 'pom.xml' or f == 'build.gradle': return 'java'
                if f == 'Program.cs' or f.endswith('.csproj'): return 'csharp'
                if f == 'go.mod': return 'golang'
                if f == 'Cargo.toml': return 'rust'
                if f == 'Gemfile': return 'ruby'
                if f == 'build.gradle.kts': return 'kotlin'
                if f == 'Package.swift': return 'swift'
                if f == 'tsconfig.json': return 'typescript'
                if f == 'mix.exs': return 'elixir'
                if f == 'shard.yml': return 'crystal'
    return None

def extract_token_from_code(code, language='python'):
    """استخراج توکن از کد زبان‌های مختلف"""
    patterns = {
        'python': [r'token\s*=\s*["\']([^"\']+)["\']', r'TOKEN\s*=\s*["\']([^"\']+)["\']', r'BOT_TOKEN\s*=\s*["\']([^"\']+)["\']'],
        'javascript': [r'token\s*=\s*["\']([^"\']+)["\']', r'TOKEN\s*=\s*["\']([^"\']+)["\']', r'process\.env\.BOT_TOKEN', r'BOT_TOKEN["\']?\s*:\s*["\']([^"\']+)["\']'],
        'php': [r'\$token\s*=\s*["\']([^"\']+)["\']', r'define\(["\']BOT_TOKEN["\']\s*,\s*["\']([^"\']+)["\']'],
        'java': [r'String\s+token\s*=\s*["\']([^"\']+)["\']', r'private\s+static\s+final\s+String\s+TOKEN\s*=\s*["\']([^"\']+)["\']'],
        'csharp': [r'string\s+token\s*=\s*["\']([^"\']+)["\']', r'private\s+static\s+readonly\s+string\s+BotToken\s*=\s*["\']([^"\']+)["\']'],
        'go': [r'token\s*:=\s*["\']([^"\']+)["\']', r'TOKEN\s*=\s*["\']([^"\']+)["\']'],
        'ruby': [r'token\s*=\s*["\']([^"\']+)["\']', r'ENV\["BOT_TOKEN"\]'],
        'rust': [r'token:\s*["\']([^"\']+)["\']', r'let\s+token\s*=\s*["\']([^"\']+)["\']'],
    }
    
    lang_patterns = patterns.get(language, patterns['python'])
    for pattern in lang_patterns:
        match = re.search(pattern, code, re.IGNORECASE)
        if match:
            return match.group(1) if match.groups() else None
    return None

def create_language_wrapper(bot_id, original_code, language):
    """ایجاد wrapper برای مدیریت member join"""
    
    if language == 'python':
        return f'''# ========== سیستم مدیریت عضوگیری ==========
import sqlite3, os, time, threading
from functools import wraps

DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'database', 'mother_bot.db')
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

{original_code}'''
    
    elif language == 'javascript':
        return f'''// ========== سیستم مدیریت عضوگیری ==========
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const DB_PATH = path.join(__dirname, '..', '..', '..', 'database', 'mother_bot.db');
let joinEnabled = true;
let blockMessage = "🚫 سرور پر است";

function updateCache() {{
    const db = new sqlite3.Database(DB_PATH);
    db.get("SELECT join_enabled, join_block_message FROM bots WHERE id = ?", ["{bot_id}"], (err, row) => {{
        if (row) {{
            joinEnabled = row.join_enabled === 1;
            blockMessage = row.join_block_message || "🚫 سرور پر است";
        }}
        db.close();
    }});
}}

setInterval(updateCache, 30000);
updateCache();

function checkJoinEnabled(bot) {{
    bot.on('new_chat_members', (msg) => {{
        if (!joinEnabled) bot.sendMessage(msg.chat.id, blockMessage);
    }});
}}

{original_code}'''
    
    return original_code

def add_bot(user_id, bot_id, token, name, username, file_path, language, pid=None, machine_id=None):
    now = datetime.now().isoformat()
    db.execute('''
        INSERT INTO bots (id, user_id, token, name, username, language, file_path, pid, machine_id, 
        status, created_at, last_active, join_enabled, join_block_message, health_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'running', ?, ?, 1, '🚫 سرور پر است', 'healthy')
    ''', (bot_id, user_id, token, name, username, language, file_path, pid, machine_id, now, now))
    db.execute('UPDATE users SET bots_count = bots_count + 1 WHERE user_id = ?', (user_id,))
    db.execute('UPDATE daily_stats SET new_bots = new_bots + 1 WHERE date = ?', (datetime.now().date().isoformat(),))
    return True

def can_create_bot(user_id):
    if not check_subscription(user_id):
        return False, "no_subscription"
    remaining = get_remaining_bots(user_id)
    if remaining <= 0:
        return False, "limit_reached"
    return True, "ok"

def log_error(error_type, message, user_id=None, bot_id=None, stack_trace=None):
    error_id = hashlib.md5(f"{time.time()}_{user_id}_{bot_id}_{secrets.token_hex(4)}".encode()).hexdigest()[:16]
    db.execute('''
        INSERT INTO errors (id, type, message, user_id, bot_id, timestamp, resolved, stack_trace)
        VALUES (?, ?, ?, ?, ?, ?, 0, ?)
    ''', (error_id, error_type, message[:500], user_id, bot_id, datetime.now().isoformat(), stack_trace))

def create_backup():
    """ایجاد بکاپ از دیتابیس و فایل‌های مهم"""
    try:
        backup_dir = os.path.join(DIRS['BACKUPS'], datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
        os.makedirs(backup_dir, exist_ok=True)
        
        # بکاپ دیتابیس
        db_path = os.path.join(DIRS['DB'], 'mother_bot.db')
        shutil.copy(db_path, os.path.join(backup_dir, 'mother_bot.db'))
        
        # بکاپ تنظیمات
        shutil.copy(os.path.join(DIRS['DB'], 'mother_bot.db-journal'), os.path.join(backup_dir, 'mother_bot.db-journal')) if os.path.exists(os.path.join(DIRS['DB'], 'mother_bot.db-journal')) else None
        
        # ثبت در دیتابیس
        backup_size = sum(os.path.getsize(os.path.join(backup_dir, f)) for f in os.listdir(backup_dir))
        db.execute('INSERT INTO backups (filename, size, location, created_at, status) VALUES (?, ?, ?, ?, ?)',
                  (os.path.basename(backup_dir), backup_size, backup_dir, datetime.now().isoformat(), 'success'))
        
        logger.info(f"Backup created: {backup_dir}")
        return backup_dir
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        return None

# ==================== SimpleCache ====================
class SimpleCache:
    def __init__(self, ttl=3600):
        self.cache = {}
        self.ttl = ttl
        self.lock = threading.RLock()
    
    def get(self, key):
        with self.lock:
            item = self.cache.get(key)
            if item and item['expires'] > time.time():
                return item['value']
            if key in self.cache:
                del self.cache[key]
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
    
    def incr(self, key):
        with self.lock:
            value = self.get(key)
            if value is None:
                value = 0
            new_value = int(value) + 1 if isinstance(value, int) else 1
            self.set(key, new_value)
            return new_value

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
        result = db.execute("SELECT COUNT(*) as count FROM bots WHERE user_id = ? AND DATE(created_at) = ?", (user_id, today))
        count = result[0]['count'] if result else 0
        cache.set(key, count, ttl=3600)
        return count
    
    def increment_user_builds(self, user_id):
        today = datetime.now().date().isoformat()
        key = f"builds_{user_id}_{today}"
        count = self.get_user_builds_today(user_id) + 1
        cache.set(key, count, ttl=3600)
        return count

rate_limiter = RateLimiter()

# ==================== صف ساخت ====================
class BuildQueue:
    def __init__(self):
        self.queue = queue.Queue()
        self.processing = {}
        self.lock = threading.RLock()
        self.worker_threads = []
        self._start_workers()
    
    def _start_workers(self):
        max_concurrent = get_setting('max_concurrent_builds')
        for i in range(max_concurrent):
            t = threading.Thread(target=self._worker, daemon=True)
            t.start()
            self.worker_threads.append(t)
        logger.info(f"Started {max_concurrent} build workers")
    
    def add_build(self, user_id, file_path, file_name, chat_id, message_id, build_data):
        build_id = str(uuid.uuid4())[:8]
        build_item = {
            'id': build_id, 'user_id': user_id, 'file_path': file_path, 'file_name': file_name,
            'chat_id': chat_id, 'message_id': message_id, 'added_at': time.time(), 'build_data': build_data
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
            build_data = build_item['build_data']
            language = build_data.get('language', 'python')
            lang_emoji = SUPPORTED_LANGUAGES.get(f'.{language}', {}).get('emoji', '🐍')
            
            temp_bot.edit_message_text(f"🔄 در حال ساخت ربات {lang_emoji}...\n🆔 {build_item['id']}",
                                      build_item['chat_id'], build_item['message_id'])
            
            result = machine_manager.run_bot(build_data['bot_id'], build_data['main_code'], 
                                            build_data['token'], language=language)
            
            if result['success']:
                add_bot(build_data['user_id'], build_data['bot_id'], build_data['token'],
                       build_data['bot_info']['first_name'], build_data['bot_info']['username'],
                       build_data['file_path'], language, result['pid'], result['machine_id'])
                
                remaining = get_remaining_bots(build_data['user_id'])
                temp_bot.edit_message_text(
                    f"✅ ربات {build_data['bot_info']['first_name']} ساخته شد!\n"
                    f"🤖 ربات باقیمانده: {remaining}\n📌 زبان: {lang_emoji} {LANGUAGE_NAMES.get(language, language)}",
                    build_item['chat_id'], build_item['message_id'])
            else:
                temp_bot.edit_message_text(f"❌ خطا در ساخت: {result.get('error', 'مشخص نشده')}",
                                          build_item['chat_id'], build_item['message_id'])
        except Exception as e:
            logger.error(f"Build failed: {e}")
            try:
                temp_bot.edit_message_text(f"❌ خطا: {str(e)[:100]}", build_item['chat_id'], build_item['message_id'])
            except:
                pass
    
    def get_queue_length(self):
        return self.queue.qsize()

# ==================== مدیریت ماشین‌ها ====================
class MachineManager:
    def __init__(self):
        self.port_counter = 8000
        self.processes = {}
        self.lock = threading.RLock()
        self._restore_bots_after_crash()
    
    def _restore_bots_after_crash(self):
        try:
            logger.info("Restoring bots after crash...")
            running_bots = db.execute('SELECT id, token, file_path, name, language FROM bots WHERE status = "running"')
            restored = 0
            for bot_rec in running_bots:
                bot_id = bot_rec['id']
                token = bot_rec['token']
                language = bot_rec.get('language', 'python')
                if token and os.path.exists(bot_rec['file_path']):
                    with open(bot_rec['file_path'], 'r', encoding='utf-8', errors='ignore') as f:
                        code = f.read()
                    result = self.run_bot(bot_id, code, token, language, restore=True)
                    if result.get('success'):
                        restored += 1
            logger.info(f"Restored {restored} bots")
        except Exception as e:
            logger.error(f"Restoration failed: {e}")
    
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
    
    def run_bot(self, bot_id, code, token, language='python', restore=False):
        try:
            machine_id = self.get_available_machine()
            if not machine_id:
                return {'success': False, 'error': 'همه ماشین‌ها پر هستند'}
            
            port = self.get_available_port()
            bot_dir = os.path.join(DIRS['MACHINES'], f"machine_{machine_id:03d}", bot_id)
            os.makedirs(bot_dir, exist_ok=True)
            
            lang_info = SUPPORTED_LANGUAGES.get(f'.{language}', SUPPORTED_LANGUAGES['.py'])
            ext = lang_info['ext']
            code_path = os.path.join(bot_dir, f'bot{ext}')
            
            # ایجاد wrapper
            if lang_info.get('wrapper', False):
                final_code = create_language_wrapper(bot_id, code, language)
            else:
                final_code = code
            
            with open(code_path, 'w', encoding='utf-8') as f:
                f.write(final_code)
            
            # نصب وابستگی‌ها
            self._install_dependencies(bot_dir, language)
            
            # دستور اجرا
            cmd = self._get_run_command(language, code_path, bot_dir)
            log_file = os.path.join(DIRS['LOGS'], f"bot_{bot_id}_{language}.log")
            
            process = subprocess.Popen(cmd, stdout=open(log_file, 'a'), stderr=subprocess.STDOUT,
                                      cwd=bot_dir, start_new_session=True)
            time.sleep(2)
            
            if process.poll() is None:
                with self.lock:
                    self.processes[bot_id] = {'process': process, 'pid': process.pid, 'machine_id': machine_id,
                                             'port': port, 'dir': bot_dir, 'start_time': time.time(), 'language': language}
                self.assign_bot(bot_id, machine_id)
                if not restore:
                    db.execute("UPDATE bots SET status = 'running', machine_id = ?, pid = ?, last_active = ?, language = ? WHERE id = ?",
                              (machine_id, process.pid, datetime.now().isoformat(), language, bot_id))
                return {'success': True, 'pid': process.pid, 'machine_id': machine_id}
            else:
                return {'success': False, 'error': 'خطا در اجرای ربات'}
        except Exception as e:
            return {'success': False, 'error': str(e)[:100]}
    
    def _install_dependencies(self, bot_dir, language):
        try:
            install_cmd = SUPPORTED_LANGUAGES.get(f'.{language}', {}).get('install')
            if install_cmd:
                if 'pip' in install_cmd and os.path.exists(os.path.join(bot_dir, 'requirements.txt')):
                    subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'],
                                 cwd=bot_dir, capture_output=True, timeout=120)
                elif 'npm' in install_cmd and os.path.exists(os.path.join(bot_dir, 'package.json')):
                    subprocess.run(['npm', 'install'], cwd=bot_dir, capture_output=True, timeout=120)
        except Exception as e:
            logger.error(f"Dependency install failed: {e}")
    
    def _get_run_command(self, language, code_path, bot_dir):
        commands = {
            'python': [sys.executable, code_path],
            'javascript': ['node', code_path],
            'php': ['php', code_path],
            'ruby': ['ruby', code_path],
            'go': ['go', 'run', code_path],
            'lua': ['lua', code_path],
            'perl': ['perl', code_path],
            'typescript': ['ts-node', code_path],
            'swift': ['swift', code_path],
            'kotlin': ['kotlin', code_path],
            'csharp': ['dotnet', 'run', '--project', bot_dir],
            'rust': ['cargo', 'run', '--manifest-path', os.path.join(bot_dir, 'Cargo.toml')],
            'elixir': ['elixir', code_path],
            'crystal': ['crystal', code_path],
        }
        cmd = commands.get(language, [sys.executable, code_path])
        if language == 'java':
            return ['bash', '-c', f'javac {code_path} && java -cp {bot_dir} Main']
        return cmd
    
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
                           'uptime': time.time() - info['start_time'], 'language': info.get('language', 'python')}
                except:
                    if bot_id in self.processes:
                        del self.processes[bot_id]
                        self.release_bot(bot_id, info['machine_id'])
                        db.execute("UPDATE bots SET status = 'stopped' WHERE id = ?", (bot_id,))
        return {'running': False}
    
    def restart_all_dead_bots(self):
        dead_bots = db.execute('SELECT id, token, file_path, language FROM bots WHERE status = "running"')
        restarted = 0
        for bot_rec in dead_bots:
            bot_id = bot_rec['id']
            if not self.get_status(bot_id).get('running'):
                token = bot_rec['token']
                language = bot_rec.get('language', 'python')
                if token and os.path.exists(bot_rec['file_path']):
                    with open(bot_rec['file_path'], 'r', encoding='utf-8', errors='ignore') as f:
                        code = f.read()
                    result = self.run_bot(bot_id, code, token, language)
                    if result.get('success'):
                        restarted += 1
        return restarted
    
    def get_stats(self):
        machines = db.execute("SELECT * FROM machines WHERE status = 'active'")
        machine_list = list(machines)
        total_bots = sum(m['current_bots'] for m in machine_list)
        total_capacity = sum(m['max_bots'] for m in machine_list)
        return {
            'total': len(machine_list), 'total_bots': total_bots, 'total_capacity': total_capacity,
            'available': total_capacity - total_bots, 'usage_percent': (total_bots / total_capacity) * 100 if total_capacity > 0 else 0
        }
    
    def get_language_stats(self):
        stats = {}
        for lang in LANGUAGE_NAMES.keys():
            count = db.execute("SELECT COUNT(*) as count FROM bots WHERE language = ?", (lang,))
            stats[lang] = count[0]['count'] if count else 0
        return stats

# ==================== ربات تلگرام ====================
bot = telebot.TeleBot(BOT_TOKEN)
bot.delete_webhook()

machine_manager = MachineManager()
build_queue = BuildQueue()
# ==================== Health Checker ====================
class HealthChecker:
    def __init__(self):
        self.checking = True
        self.thread = threading.Thread(target=self._monitor, daemon=True)
        self.thread.start()
    
    def _monitor(self):
        while self.checking:
            try:
                interval = get_setting('health_check_interval')
                for bot_rec in db.execute('SELECT id, token FROM bots WHERE status = "running"'):
                    token = bot_rec['token']
                    if token:
                        try:
                            resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
                            if resp.status_code != 200:
                                self._restart_bot(bot_rec['id'])
                        except:
                            self._restart_bot(bot_rec['id'])
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
                token = bot_rec['token']
                language = bot_rec.get('language', 'python')
                if token:
                    result = machine_manager.run_bot(bot_id, code, token, language)
                    if result['success']:
                        db.execute('UPDATE bots SET status = "running", machine_id = ?, pid = ?, last_active = ? WHERE id = ?',
                                  (result['machine_id'], result['pid'], datetime.now().isoformat(), bot_id))
                        logger.info(f"Auto-restarted bot {bot_id}")
            except Exception as e:
                logger.error(f"Failed to restart bot {bot_id}: {e}")

health_checker = HealthChecker()

# ==================== منوی اصلی ====================
def get_main_menu(user_id):
    user = get_user(user_id)
    lang = user['language'] if user else 'fa'
    is_admin = user_id in ADMIN_IDS
    
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = MENU_BUTTONS_FA.copy() if lang == 'fa' else MENU_BUTTONS_EN.copy()
    
    if is_admin:
        for btn in ADMIN_BUTTONS:
            buttons.append(btn)
    
    markup.add(*buttons)
    return markup

def rate_limit(limit_per_second=5):
    def decorator(func):
        @wraps(func)
        def wrapper(message, *args, **kwargs):
            user_id = message.from_user.id
            if not rate_limiter.is_allowed(user_id, limit_per_second):
                bot.reply_to(message, "🚫 لطفاً کمی صبر کنید...")
                return
            return func(message, *args, **kwargs)
        return wrapper
    return decorator

# ==================== دستورات ====================
@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or ""
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
                bot.send_message(referred_by, f"🎉 {first_name} با لینک شما وارد شد!")
            except:
                pass
    
    result, msg = create_user(user_id, username, first_name, message.from_user.last_name or "", referred_by, preferred_lang)
    
    if not result and msg == "capacity_full":
        bot.send_message(message.chat.id, get_setting('capacity_warning_message'))
        return
    
    user = get_user(user_id)
    referral_link = f"https://t.me/{BOT_USERNAME}?start={user['referral_code']}"
    remaining_bots = get_remaining_bots(user_id)
    max_bots = get_setting('max_bots_per_subscription')
    is_subscribed = check_subscription(user_id)
    lang = user['language']
    
    if lang == 'fa':
        welcome_text = get_setting('welcome_text_fa').format(name=first_name)
        text = (f"{welcome_text}\n\n👤 شناسه: `{user_id}`\n🎁 کد معرف: `{user['referral_code']}`\n"
                f"🔗 لینک دعوت: `{referral_link}`\n📊 دعوت‌ها: {user['referrals_count']}\n"
                f"💰 موجودی: {user['wallet_balance']:,} تومان\n"
                f"💳 وضعیت: {'✅ فعال' if is_subscribed else '❌ غیرفعال'}\n"
                f"🤖 ربات‌های باقیمانده: {remaining_bots}/{max_bots}\n\n"
                f"📌 زبان‌های پشتیبانی شده:\n"
                f"🐍 Python - 🟨 JS - 🐘 PHP - ☕ Java\n"
                f"📘 C# - 🔵 Go - 💎 Ruby - 🦀 Rust\n"
                f"🟣 Kotlin - 🐦 Swift - 💙 TS - 🌙 Lua\n"
                f"🐪 Perl - 💧 Elixir - 🔮 Crystal")
    else:
        welcome_text = get_setting('welcome_text_en').format(name=first_name)
        text = (f"{welcome_text}\n\n👤 ID: `{user_id}`\n🎁 Referral Code: `{user['referral_code']}`\n"
                f"🔗 Invite Link: `{referral_link}`\n📊 Referrals: {user['referrals_count']}\n"
                f"💰 Balance: {user['wallet_balance']:,} Toman\n"
                f"💳 Status: {'✅ Active' if is_subscribed else '❌ Inactive'}\n"
                f"🤖 Remaining Bots: {remaining_bots}/{max_bots}\n\n"
                f"📌 Supported Languages:\n"
                f"🐍 Python - 🟨 JS - 🐘 PHP - ☕ Java\n"
                f"📘 C# - 🔵 Go - 💎 Ruby - 🦀 Rust\n"
                f"🟣 Kotlin - 🐦 Swift - 💙 TS - 🌙 Lua\n"
                f"🐪 Perl - 💧 Elixir - 🔮 Crystal")
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📋 کپی لینک", callback_data=f"copy_link_{user['referral_code']}"))
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=get_main_menu(user_id))

@bot.callback_query_handler(func=lambda call: call.data.startswith('copy_link_'))
def copy_link_callback(call):
    code = call.data.replace('copy_link_', '')
    link = f"https://t.me/{BOT_USERNAME}?start={code}"
    bot.answer_callback_query(call.id, f"✅ لینک کپی شد!\n{link}", show_alert=True)

# ==================== زبان ====================
@bot.message_handler(func=lambda m: m.text in ['🌐 زبان / Language', '🌐 Language / زبان'])
def change_language(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa"),
        types.InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")
    )
    bot.send_message(message.chat.id, "Select your language / زبان خود را انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def set_language(call):
    lang = call.data.replace('lang_', '')
    db.execute("UPDATE users SET language = ? WHERE user_id = ?", (lang, call.from_user.id))
    msg = "✅ Language set to English" if lang == 'en' else "✅ زبان به فارسی تغییر کرد"
    bot.answer_callback_query(call.id, msg)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    bot.send_message(call.message.chat.id, msg, reply_markup=get_main_menu(call.from_user.id))

# ==================== کیف پول و اشتراک ====================
@bot.message_handler(func=lambda m: m.text in ['💰 کیف پول و اشتراک', '💰 Wallet & Subscription'])
def wallet(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        bot.send_message(message.chat.id, "❌ /start بزنید")
        return
    
    is_subscribed = check_subscription(user_id)
    expiry = datetime.fromisoformat(user['subscription_expiry']).strftime('%Y-%m-%d') if user['subscription_expiry'] else "ندارد"
    remaining_bots = get_remaining_bots(user_id)
    max_bots = get_setting('max_bots_per_subscription')
    lang = user['language']
    
    if lang == 'fa':
        text = (f"💰 **کیف پول و اشتراک**\n\n👤 {user['first_name']}\n"
                f"💳 وضعیت: {'✅ فعال' if is_subscribed else '❌ غیرفعال'}\n"
                f"📅 انقضا: {expiry}\n💰 موجودی: {user['wallet_balance']:,} تومان\n"
                f"👥 دعوت‌ها: {user['referrals_count']}\n🤖 ربات‌های باقیمانده: {remaining_bots}/{max_bots}\n\n"
                f"💳 برای فعالسازی {get_setting('subscription_price_str')} را به آدرس زیر واریز:\n"
                f"`{get_setting('trc20_address')}`\n🌐 شبکه: TRC20 (USDT)\n\n📸 پس از واریز، تصویر تراکنش را ارسال کنید")
    else:
        text = (f"💰 **Wallet & Subscription**\n\n👤 {user['first_name']}\n"
                f"💳 Status: {'✅ Active' if is_subscribed else '❌ Inactive'}\n"
                f"📅 Expiry: {expiry}\n💰 Balance: {user['wallet_balance']:,} Toman\n"
                f"👥 Referrals: {user['referrals_count']}\n🤖 Remaining Bots: {remaining_bots}/{max_bots}\n\n"
                f"💳 To activate, send {get_setting('subscription_price_usd')} to:\n"
                f"`{get_setting('trc20_address')}`\n🌐 Network: TRC20 (USDT)\n\n📸 Send transaction screenshot after payment")
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📋 کپی آدرس", callback_data="copy_address"))
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "copy_address")
def copy_address(call):
    bot.answer_callback_query(call.id, f"✅ {get_setting('trc20_address')}", show_alert=True)

# ==================== دریافت فیش ====================
@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    existing = db.execute('SELECT id FROM receipts WHERE user_id = ? AND status = "pending"', (user_id,))
    if existing:
        bot.reply_to(message, "⏳ فیش قبلی در انتظار تایید است")
        return
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        tx_hash = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:16].upper()
        receipt_path = os.path.join(DIRS['RECEIPTS'], f"{user_id}_{tx_hash}.jpg")
        
        with open(receipt_path, 'wb') as f:
            f.write(downloaded)
        
        db.execute('INSERT INTO receipts (user_id, amount, receipt_path, tx_hash, created_at) VALUES (?, ?, ?, ?, ?)',
                  (user_id, get_setting('subscription_price'), receipt_path, tx_hash, datetime.now().isoformat()))
        
        bot.reply_to(message, f"✅ فیش دریافت شد\n💰 {get_setting('subscription_price_str')}\n🆔 {tx_hash}")
        
        for admin_id in ADMIN_IDS:
            try:
                with open(receipt_path, 'rb') as f:
                    bot.send_photo(admin_id, f, caption=f"📸 فیش جدید\n👤 {message.from_user.first_name}\n🆔 {user_id}\n💰 {get_setting('subscription_price_str')}")
            except:
                pass
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")

# ==================== دعوت دوستان ====================
@bot.message_handler(func=lambda m: m.text in ['👥 دعوت دوستان', '👥 Invite Friends'])
def invite(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    referral_link = f"https://t.me/{BOT_USERNAME}?start={user['referral_code']}"
    
    text = (f"👥 **سیستم دعوت دوستان**\n\n🎁 کد معرف: `{user['referral_code']}`\n"
            f"🔗 لینک: `{referral_link}`\n📊 دعوت‌ها: {user['referrals_count']}\n"
            f"💰 کمیسیون هر دعوت: {get_setting('withdraw_percent')}%\n"
            f"💎 کمیسیون کل: {user.get('total_commission', 0):,} تومان")
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📋 کپی لینک", callback_data=f"copy_link_{user['referral_code']}"))
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

# ==================== برداشت ====================
@bot.message_handler(func=lambda m: m.text in ['💸 درخواست برداشت', '💸 Withdraw'])
def withdraw_request(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if user['wallet_balance'] < get_setting('min_withdraw'):
        bot.send_message(message.chat.id, f"❌ موجودی {user['wallet_balance']:,} کمتر از حداقل {get_setting('min_withdraw'):,} است")
        return
    
    msg = bot.send_message(message.chat.id, "💳 آدرس کیف پول TRC20 برای برداشت:")
    bot.register_next_step_handler(msg, process_withdraw_address, user)

def process_withdraw_address(message, user):
    address = message.text.strip()
    amount = user['wallet_balance']
    db.execute('INSERT INTO withdraw_requests (user_id, amount, address, created_at, status) VALUES (?, ?, ?, ?, "pending")',
              (user['user_id'], amount, address, datetime.now().isoformat()))
    db.execute('UPDATE users SET wallet_balance = 0 WHERE user_id = ?', (user['user_id'],))
    bot.send_message(message.chat.id, f"✅ درخواست {amount:,} تومان ثبت شد")
    
    for admin_id in ADMIN_IDS:
        bot.send_message(admin_id, f"💰 درخواست برداشت\n👤 {user['first_name']}\n🆔 {user['user_id']}\n💰 {amount:,} تومان")

# ==================== ساخت ربات جدید ====================
@bot.message_handler(func=lambda m: m.text in ['🤖 ساخت ربات جدید', '🤖 New Bot'])
def new_bot(message):
    user_id = message.from_user.id
    
    if not check_subscription(user_id):
        bot.send_message(message.chat.id, "❌ ابتدا باید اشتراک فعال کنید!")
        return
    
    can_create, _ = can_create_bot(user_id)
    if not can_create:
        bot.send_message(message.chat.id, f"❌ به حداکثر {get_setting('max_bots_per_subscription')} ربات رسیده‌اید")
        return
    
    bot.send_message(message.chat.id, "📤 فایل پروژه خود را ارسال کنید\n📌 زبان‌های مجاز:\n🐍 Python - 🟨 JS - 🐘 PHP - ☕ Java\n📘 C# - 🔵 Go - 💎 Ruby - 🦀 Rust\n🟣 Kotlin - 🐦 Swift - 💙 TS - 🌙 Lua\n🐪 Perl - 💧 Elixir - 🔮 Crystal")

def extract_zip_with_structure(zip_path, extract_to):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    
    main_code = ""
    main_file = None
    
    for root, dirs, files in os.walk(extract_to):
        for file in files:
            if any(file.endswith(ext) for ext in ['.py', '.js', '.php', '.java', '.cs', '.go', '.rb', '.rs', '.kt', '.swift', '.ts', '.lua', '.pl', '.exs', '.cr']):
                if file in ['main.py', 'bot.py', 'app.py', 'index.js', 'bot.js', 'index.php', 'Main.java', 'Program.cs', 'main.go', 'main.rs', 'main.kt', 'main.swift', 'main.ts', 'main.lua', 'main.pl', 'main.exs', 'main.cr']:
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

@bot.message_handler(content_types=['document'])
def handle_build_file(message):
    user_id = message.from_user.id
    lang = get_user_language(user_id)
    
    if not check_subscription(user_id):
        bot.reply_to(message, "❌ اشتراک فعال نیست")
        return
    
    file_name = message.document.file_name
    allowed = ['.py', '.js', '.php', '.java', '.cs', '.go', '.rb', '.rs', '.kt', '.swift', '.ts', '.lua', '.pl', '.exs', '.cr', '.zip']
    if not any(file_name.endswith(ext) for ext in allowed):
        bot.reply_to(message, "❌ فرمت فایل مجاز نیست")
        return
    
    if message.document.file_size > 50 * 1024 * 1024:
        bot.reply_to(message, "❌ حجم بیشتر از ۵۰ مگابایت")
        return
    
    status_msg = bot.reply_to(message, "🔄 در حال بررسی...")
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        user_dir = os.path.join(DIRS['FILES'], str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        file_path = os.path.join(user_dir, f"{int(time.time())}_{file_name}")
        with open(file_path, 'wb') as f:
            f.write(downloaded)
        
        main_code = ""
        folder_path = None
        detected_language = None
        
        if file_name.endswith('.zip'):
            extract_dir = os.path.join(DIRS['TEMP'], f"extract_{user_id}_{int(time.time())}")
            os.makedirs(extract_dir, exist_ok=True)
            main_code, folder_path = extract_zip_with_structure(file_path, extract_dir)
            detected_language = detect_language_from_file(file_name, extract_dir)
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                main_code = f.read()
            detected_language = detect_language_from_file(file_name)
        
        if not main_code:
            bot.edit_message_text("❌ فایل کد پیدا نشد", message.chat.id, status_msg.message_id)
            return
        
        if not detected_language:
            bot.edit_message_text("❌ زبان برنامه نویسی تشخیص داده نشد", message.chat.id, status_msg.message_id)
            return
        
        token = extract_token_from_code(main_code, detected_language)
        if not token:
            bot.edit_message_text("❌ توکن پیدا نشد", message.chat.id, status_msg.message_id)
            return
        
        resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        if resp.status_code != 200:
            bot.edit_message_text("❌ توکن نامعتبر", message.chat.id, status_msg.message_id)
            return
        
        bot_info = resp.json()['result']
        rate_limiter.increment_user_builds(user_id)
        bot_id = hashlib.md5(f"{user_id}{token}{time.time()}".encode()).hexdigest()[:16]
        
        if folder_path:
            final_folder = os.path.join(DIRS['FILES'], str(user_id), f"bot_{bot_id}")
            shutil.move(folder_path, final_folder)
            folder_path = final_folder
        
        build_data = {
            'bot_id': bot_id, 'user_id': user_id, 'token': token, 'bot_info': bot_info,
            'file_path': file_path, 'folder_path': folder_path, 'main_code': main_code,
            'language': detected_language, 'chat_id': message.chat.id, 'message_id': status_msg.message_id
        }
        
        build_queue.add_build(user_id, file_path, file_name, message.chat.id, status_msg.message_id, build_data)
        
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)[:100]}", message.chat.id, status_msg.message_id)

# ==================== ربات‌های من ====================
@bot.message_handler(func=lambda m: m.text in ['📋 ربات‌های من', '📋 My Bots'])
def my_bots(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    if not bots:
        bot.send_message(message.chat.id, "📋 رباتی ندارید")
        return
    
    bot.send_message(message.chat.id, "📋 لیست ربات‌های شما:")
    for b in bots[:20]:
        status = machine_manager.get_status(b['id'])
        emoji = "🟢" if status.get('running') else "🔴"
        lang_emoji = SUPPORTED_LANGUAGES.get(f'.{b.get("language", "python")}', {}).get('emoji', '🐍')
        text = f"{emoji} {lang_emoji} {b['name']}\n🔗 t.me/{b['username']}"
        if b.get('error_message'):
            text += f"\n⚠️ خطا: {b['error_message'][:50]}"
        bot.send_message(message.chat.id, text)

# ==================== فعال/غیرفعال ====================
@bot.message_handler(func=lambda m: m.text in ['🔄 فعال/غیرفعال', '🔄 Start/Stop'])
def toggle_prompt(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    if not bots:
        bot.send_message(message.chat.id, "📋 رباتی ندارید")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        status = machine_manager.get_status(b['id'])
        emoji = "🟢" if status.get('running') else "🔴"
        lang_emoji = SUPPORTED_LANGUAGES.get(f'.{b.get("language", "python")}', {}).get('emoji', '🐍')
        markup.add(types.InlineKeyboardButton(f"{emoji} {lang_emoji} {b['name']}", callback_data=f"toggle_{b['id']}"))
    
    bot.send_message(message.chat.id, "🔄 انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_'))
def toggle_bot(call):
    bot_id = call.data.replace('toggle_', '')
    bot_rec = get_bot(bot_id)
    if not bot_rec or bot_rec['user_id'] != call.from_user.id:
        bot.answer_callback_query(call.id, "❌ یافت نشد")
        return
    
    status = machine_manager.get_status(bot_id)
    if status.get('running'):
        if machine_manager.stop_bot(bot_id):
            bot.answer_callback_query(call.id, "✅ متوقف شد")
        else:
            bot.answer_callback_query(call.id, "❌ خطا")
    else:
        if os.path.exists(bot_rec['file_path']):
            with open(bot_rec['file_path'], 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
            token = bot_rec['token']
            language = bot_rec.get('language', 'python')
            result = machine_manager.run_bot(bot_id, code, token, language)
            if result['success']:
                db.execute("UPDATE bots SET machine_id = ?, pid = ?, status = 'running', error_message = NULL WHERE id = ?",
                          (result['machine_id'], result['pid'], bot_id))
                bot.answer_callback_query(call.id, "✅ فعال شد")
            else:
                bot.answer_callback_query(call.id, f"❌ {result.get('error')}")
        else:
            bot.answer_callback_query(call.id, "❌ فایل یافت نشد")

# ==================== حذف ربات ====================
@bot.message_handler(func=lambda m: m.text in ['🗑 حذف ربات', '🗑 Delete Bot'])
def delete_prompt(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    if not bots:
        bot.send_message(message.chat.id, "📋 رباتی ندارید")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        lang_emoji = SUPPORTED_LANGUAGES.get(f'.{b.get("language", "python")}', {}).get('emoji', '🐍')
        markup.add(types.InlineKeyboardButton(f"🗑 {lang_emoji} {b['name']}", callback_data=f"delete_{b['id']}"))
    
    bot.send_message(message.chat.id, "🗑 انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
def confirm_delete(call):
    bot_id = call.data.replace('delete_', '')
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ بله", callback_data=f"confirm_del_{bot_id}"),
        types.InlineKeyboardButton("❌ انصراف", callback_data="cancel_del")
    )
    bot.edit_message_text("⚠️ اطمینان دارید؟", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_del_'))
def do_delete(call):
    bot_id = call.data.replace('confirm_del_', '')
    if delete_bot(bot_id, call.from_user.id):
        bot.edit_message_text("✅ حذف شد", call.message.chat.id, call.message.message_id)
    else:
        bot.edit_message_text("❌ خطا", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == 'cancel_del')
def cancel_delete(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== کتابخانه ====================
POPULAR_LIBRARIES = {
    'requests': 'requests', 'aiohttp': 'aiohttp', 'flask': 'flask',
    'django': 'django', 'numpy': 'numpy', 'pandas': 'pandas',
    'pillow': 'Pillow', 'beautifulsoup4': 'beautifulsoup4',
    'selenium': 'selenium', 'jdatetime': 'jdatetime', 'cryptography': 'cryptography'
}

@bot.message_handler(func=lambda m: m.text in ['📦 کتابخانه', '📦 Library'])
def library_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    for name, lib in list(POPULAR_LIBRARIES.items())[:15]:
        markup.add(types.InlineKeyboardButton(f"📦 {name}", callback_data=f"lib_{lib}"))
    markup.add(types.InlineKeyboardButton("🔧 نصب دستی", callback_data="lib_manual"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="lib_back"))
    bot.reply_to(message, "📦 کتابخانه مورد نظر:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "lib_manual")
def library_manual(call):
    msg = bot.send_message(call.message.chat.id, "🔧 نام کتابخانه:")
    bot.register_next_step_handler(msg, install_custom_library)

def install_custom_library(message):
    lib = message.text.strip()
    if not lib:
        bot.reply_to(message, "❌ نام کتابخانه")
        return
    status = bot.reply_to(message, f"🔄 نصب {lib}...")
    install_library(lib, message.chat.id, status.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lib_') and call.data not in ['lib_manual', 'lib_back'])
def install_selected_library(call):
    lib = call.data.replace('lib_', '')
    status = bot.send_message(call.message.chat.id, f"🔄 نصب {lib}...")
    install_library(lib, call.message.chat.id, status.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "lib_back")
def library_back(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "🚀 منوی اصلی:", reply_markup=get_main_menu(call.from_user.id))

def install_library(lib_name, chat_id, msg_id):
    try:
        process = subprocess.run([sys.executable, '-m', 'pip', 'install', lib_name, '--quiet'],
                                capture_output=True, text=True, timeout=120)
        if process.returncode == 0:
            bot.edit_message_text(f"✅ {lib_name} نصب شد!", chat_id, msg_id)
        else:
            bot.edit_message_text(f"❌ خطا: {process.stderr[:100]}", chat_id, msg_id)
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)[:100]}", chat_id, msg_id)

# ==================== راهنما ====================
@bot.message_handler(func=lambda m: m.text in ['📚 راهنما', '📚 Guide'])
def guide(message):
    lang = get_user_language(message.from_user.id)
    guide_text = get_setting('guide_text_fa') if lang == 'fa' else get_setting('guide_text_en')
    bot.send_message(message.chat.id, guide_text)

# ==================== آمار ====================
@bot.message_handler(func=lambda m: m.text in ['📊 آمار', '📊 Stats'])
def stats(message):
    users = db.execute('SELECT COUNT(*) as count FROM users')[0]['count']
    active_subs = db.execute('SELECT COUNT(*) as count FROM users WHERE subscription_status = "active"')[0]['count']
    bots = db.execute('SELECT COUNT(*) as count FROM bots')[0]['count']
    running = db.execute('SELECT COUNT(*) as count FROM bots WHERE status = "running"')[0]['count']
    total_wallet = db.execute('SELECT SUM(wallet_balance) as total FROM users')[0]['total'] or 0
    machine_stats = machine_manager.get_stats()
    queue_len = build_queue.get_queue_length()
    lang_stats = machine_manager.get_language_stats()
    
    lang_text = "\n📊 **آمار زبان‌ها:**\n"
    for lang_name, count in lang_stats.items():
        if count > 0:
            emoji = SUPPORTED_LANGUAGES.get(f'.{lang_name}', {}).get('emoji', '🐍')
            lang_text += f"{emoji} {LANGUAGE_NAMES.get(lang_name, lang_name)}: {count}\n"
    
    text = (f"📊 **آمار سیستم**\n\n👥 کاربران: {users:,}\n✅ اشتراک فعال: {active_subs:,}\n"
            f"🤖 کل ربات‌ها: {bots:,}\n🟢 ربات فعال: {running:,}\n💰 کیف پول کل: {total_wallet:,} تومان\n"
            f"🖥️ ماشین‌ها: {machine_stats['total']}\n📊 مصرف: {machine_stats['usage_percent']:.1f}%\n"
            f"⚡ صف ساخت: {queue_len}{lang_text}")
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== مصرف من ====================
@bot.message_handler(func=lambda m: m.text in ['📈 مصرف من', '📈 My Usage'])
def my_usage(message):
    user_id = message.from_user.id
    builds_today = rate_limiter.get_user_builds_today(user_id)
    max_builds = get_setting('max_builds_per_hour')
    bots_count = len(get_user_bots(user_id))
    remaining = get_remaining_bots(user_id)
    max_bots = get_setting('max_bots_per_subscription')
    
    bar_length = int((builds_today / max_builds) * 20) if max_builds > 0 else 0
    bar = "█" * bar_length + "░" * (20 - bar_length)
    
    text = (f"📊 **مصرف شما امروز**\n\n🤖 ساخت ربات: {builds_today}/{max_builds}\n"
            f"📈 {bar} {int((builds_today/max_builds)*100) if max_builds>0 else 0}%\n\n"
            f"📋 تعداد ربات‌ها: {bots_count}\n📦 ربات باقیمانده: {remaining}/{max_bots}")
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== وضعیت صف ====================
@bot.message_handler(func=lambda m: m.text in ['⚡ وضعیت صف', '⚡ Queue Status'])
def queue_status(message):
    queue_len = build_queue.get_queue_length()
    max_concurrent = get_setting('max_concurrent_builds')
    user_id = message.from_user.id
    
    text = (f"⚡ **وضعیت صف ساخت**\n\n📊 در صف: {queue_len}\n"
            f"⚙️ حداکثر همزمان: {max_concurrent}\n"
            f"📈 ساخت امروز شما: {rate_limiter.get_user_builds_today(user_id)}/{get_setting('max_builds_per_hour')}")
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== پشتیبانی ====================
@bot.message_handler(func=lambda m: m.text in ['📞 پشتیبانی', '📞 Support'])
def support(message):
    bot.send_message(message.chat.id, "📞 پشتیبانی: @shahraghee13")

# ==================== بازگشت به منوی اصلی ====================
@bot.message_handler(func=lambda m: m.text == '🔙 بازگشت به منوی اصلی')
def back_to_main(message):
    bot.send_message(message.chat.id, "🚀 منوی اصلی:", reply_markup=get_main_menu(message.from_user.id))

# ==================== مانیتورینگ ====================
def system_monitor():
    while True:
        try:
            for user in db.execute('SELECT user_id, subscription_expiry FROM users WHERE subscription_status = "active"'):
                if user['subscription_expiry']:
                    expiry = datetime.fromisoformat(user['subscription_expiry'])
                    if expiry < datetime.now():
                        db.execute('UPDATE users SET subscription_status = "inactive" WHERE user_id = ?', (user['user_id'],))
            
            today = datetime.now().date().isoformat()
            db.execute('INSERT OR IGNORE INTO daily_stats (date) VALUES (?)', (today,))
            
            time.sleep(60)
        except Exception as e:
            logger.error(f"Monitor error: {e}")
            time.sleep(60)

threading.Thread(target=system_monitor, daemon=True).start()

# ==================== Flask ====================
flask_app = Flask(__name__)

@flask_app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'active_bots': len(machine_manager.processes),
        'queue_size': build_queue.get_queue_length(),
        'total_users': db.execute('SELECT COUNT(*) as count FROM users')[0]['count'],
        'total_bots': db.execute('SELECT COUNT(*) as count FROM bots')[0]['count'],
        'language_stats': machine_manager.get_language_stats()
    })

def run_flask():
    flask_app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

threading.Thread(target=run_flask, daemon=True).start()

# ==================== اجرا ====================
if __name__ == "__main__":
    print("=" * 80)
    print("🚀 ربات مادر نهایی - نسخه 100.3 Multi-Language Ultimate Enterprise".center(80))
    print("=" * 80)
    print(f"👑 ادمین‌ها: {ADMIN_IDS}")
    print(f"🤖 ربات: @{BOT_USERNAME}")
    print(f"💰 قیمت اشتراک: {get_setting('subscription_price_str')}")
    print(f"🤖 حداکثر ربات در هر اشتراک: {get_setting('max_bots_per_subscription')}")
    print(f"💳 آدرس TRC20: {get_setting('trc20_address')}")
    print(f"📊 Health Check: http://localhost:5000/health")
    print("=" * 80)
    print("✅ زبان‌های پشتیبانی شده (15+ زبان):")
    print("   🐍 Python - 🟨 JavaScript - 🐘 PHP - ☕ Java")
    print("   📘 C# - 🔵 Go - 💎 Ruby - 🦀 Rust")
    print("   🟣 Kotlin - 🐦 Swift - 💙 TypeScript - 🌙 Lua")
    print("   🐪 Perl - 💧 Elixir - 🔮 Crystal")
    print("=" * 80)
    print("✅ ربات در حال اجرا است...")
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            logger.error(f"Polling error: {e}")
            time.sleep(5)
          
