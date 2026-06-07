#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
═══════════════════════════════════════════════════════════════════════════════
🚀 ربات مادر نهایی - نسخه 100.0 Enterprise Mega Scale
⚡ پشتیبانی از میلیون‌ها کاربر - معماری میکروسرویس کامل
🌐 پشتیبانی از زبان فارسی و انگلیسی
💎 سیستم کمیسیون دقیق رفرال
🤖 محدودیت ۳ ربات در هر اشتراک
🔒 بازیابی خودکار پس از خرابی سرور
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
import pickle
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from functools import wraps
from collections import defaultdict
from typing import Optional, Dict, Any, List

import telebot
from telebot import types
import requests
from flask import Flask, request, jsonify

# ==================== امنیت: توکن از محیط ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ Error: BOT_TOKEN not found!")
    print("✅ Solution: export BOT_TOKEN='your_token_here'")
    sys.exit(1)

ENCRYPTION_PASSWORD = os.environ.get("ENCRYPTION_PASSWORD", "")
if not ENCRYPTION_PASSWORD:
    print("⚠️ Warning: ENCRYPTION_PASSWORD not set")
    ENCRYPTION_PASSWORD = "DEFAULT_INSECURE_KEY_CHANGE_ME"

# ==================== آدرس کیف پول TRC20 ====================
TRC20_ADDRESS = "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"

# ==================== تلاش برای وارد کردن کتابخانه‌های اختیاری ====================
REDIS_AVAILABLE = False
CELERY_AVAILABLE = False
CRYPTO_AVAILABLE = False
SENTRY_AVAILABLE = False
ELASTIC_AVAILABLE = False
PROMETHEUS_AVAILABLE = False

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
    
    kdf = PBKDF2(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"mother_bot_secure_salt_2024_v2",
        iterations=100000,
    )
    SECRET_KEY = base64.urlsafe_b64encode(kdf.derive(ENCRYPTION_PASSWORD.encode()))
    FERNET_CIPHER = Fernet(SECRET_KEY)
    
except ImportError:
    CRYPTO_AVAILABLE = False
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
    'QUEUE': os.path.join(BASE_DIR, "queue"),
    'BACKUPS': os.path.join(BASE_DIR, "backups"),
    'ARCHIVE': os.path.join(BASE_DIR, "archive"),
    'STATE': os.path.join(BASE_DIR, "state")
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
        return msg

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            os.path.join(DIRS['LOGS'], 'mother_bot.log'),
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

# ==================== توکن و تنظیمات ====================
ADMIN_IDS = [327855654]
BOT_USERNAME = "ROBTTSAZE_bot"

# تنظیمات پیش‌فرض
DEFAULT_SETTINGS = {
    'trc20_address': TRC20_ADDRESS,
    'subscription_price': 2000000,
    'subscription_price_str': "۲,۰۰۰,۰۰۰ تومان",
    'subscription_price_usd': "50 USD",
    'withdraw_percent': 7,
    'min_withdraw': 2000000,
    'max_bots_per_subscription': 3,
    'guide_text_fa': "📚 راهنمای استفاده\n\n1️⃣ برای ساخت ربات، فایل .py یا .zip خود را ارسال کنید\n2️⃣ پس از پرداخت اشتراک ماهیانه، می‌توانید ربات بسازید\n3️⃣ هر کاربر می‌تواند تا ۳ ربات بسازد\n4️⃣ با دعوت دوستان، ۷٪ کمیسیون دریافت کنید\n5️⃣ پس از رسیدن به ۲ میلیون تومان، می‌توانید برداشت کنید",
    'guide_text_en': "📚 User Guide\n\n1️⃣ Send your .py or .zip file\n2️⃣ After subscription payment, you can build bots\n3️⃣ Each user can build up to 3 bots\n4️⃣ Invite friends and get 7% commission\n5️⃣ Withdraw after reaching 2,000,000 Toman",
    'max_builds_per_hour': 10,
    'max_concurrent_builds': 20,
    'rate_limit_per_second': 5,
    'health_check_interval': 30,
    'auto_scale_threshold': 80,
    'backup_interval': 3600,
    'state_save_interval': 60
}

# ==================== دکمه‌های منو ====================
MENU_BUTTONS_FA = [
    '🤖 ساخت ربات جدید',
    '📋 ربات‌های من',
    '🔄 فعال/غیرفعال',
    '🗑 حذف ربات',
    '💰 کیف پول و اشتراک',
    '📚 راهنما',
    '👥 دعوت دوستان',
    '💸 درخواست برداشت',
    '📦 کتابخانه',
    '📊 آمار',
    '📞 پشتیبانی',
    '⚡ وضعیت صف',
    '📈 مصرف من',
    '🌐 زبان / Language'
]

MENU_BUTTONS_EN = [
    '🤖 New Bot',
    '📋 My Bots',
    '🔄 Start/Stop',
    '🗑 Delete Bot',
    '💰 Wallet & Subscription',
    '📚 Guide',
    '👥 Invite Friends',
    '💸 Withdraw',
    '📦 Library',
    '📊 Stats',
    '📞 Support',
    '⚡ Queue Status',
    '📈 My Usage',
    '🌐 Language / زبان'
]

ADMIN_BUTTONS_FA = [
    '👑 پنل مدیریت',
    '📢 پیام همگانی'
]

ADMIN_BUTTONS_EN = [
    '👑 Admin Panel',
    '📢 Broadcast'
]

# ==================== متن‌های چند زبانه ====================
TEXTS = {
    'fa': {
        'welcome': "🚀 خوش آمدید {name}!",
        'subscription_active': "✅ اشتراک فعال",
        'subscription_inactive': "❌ اشتراک غیرفعال",
        'bots_remaining': "🤖 ربات‌های باقیمانده: {remaining}/{max}",
        'deposit_address': "💳 آدرس واریز TRC20:\n`{address}`",
        'send_receipt': "📸 لطفاً تصویر تراکنش را ارسال کنید",
        'receipt_received': "✅ تصویر دریافت شد، در انتظار تایید",
        'commission_added': "🎉 کمیسیون {amount:,} تومان به کیف پول شما اضافه شد",
        'bot_limit_reached': "❌ به حداکثر مجاز {max} ربات رسیده‌اید",
        'build_guide': "📚 راهنمای ساخت ربات\n\n1️⃣ فایل .py خود را ارسال کنید\n2️⃣ منتظر بمانید تا ساخته شود\n3️⃣ ربات شما آماده است!",
        'error': "❌ خطا: {error}",
        'success': "✅ موفق: {message}",
        'persian': "🇮🇷 فارسی",
        'english': "🇬🇧 انگلیسی",
        'balance': "💰 موجودی: {balance:,} تومان",
        'referral_count': "👥 دعوت‌ها: {count}",
        'expiry_date': "📅 انقضا: {date}",
        'no_bots': "📋 رباتی ندارید",
        'bot_list': "📋 لیست ربات‌های شما",
        'select_bot': "🤖 ربات را انتخاب کنید:",
        'confirm_delete': "⚠️ آیا برای حذف اطمینان دارید؟",
        'deleted': "✅ حذف شد",
        'started': "✅ فعال شد",
        'stopped': "✅ متوقف شد",
        'processing': "🔄 در حال پردازش...",
        'invalid_file': "❌ فقط فایل‌های .py یا .zip",
        'file_too_large': "❌ حجم بیشتر از ۵۰ مگابایت",
        'token_not_found': "❌ توکن در کد پیدا نشد",
        'invalid_token': "❌ توکن نامعتبر",
        'build_success': "✅ ربات {name} ساخته شد!\n🤖 ربات باقیمانده: {remaining}",
        'build_failed': "❌ ساخت ناموفق: {error}",
        'stats_title': "📊 **آمار سیستم**",
        'users_count': "👥 کاربران: {count:,}",
        'active_subs': "✅ اشتراک فعال: {count:,}",
        'total_bots': "🤖 کل ربات‌ها: {count:,}",
        'running_bots': "🟢 ربات فعال: {count:,}",
        'total_wallet': "💰 کیف پول کل: {amount:,} تومان",
        'machine_stats': "🖥️ ماشین‌ها: {machines} | مصرف: {usage}%",
        'queue_status': "⚡ صف ساخت: {queue}",
        'support': "📞 پشتیبانی: @shahraghee13",
        'invite_title': "👥 **سیستم دعوت دوستان**",
        'referral_code': "🎁 کد معرف: `{code}`",
        'referral_link': "🔗 لینک دعوت: `{link}`",
        'commission_rate': "💰 کمیسیون هر اشتراک: {percent}%",
        'total_commission': "💎 کمیسیون کل: {amount:,} تومان",
        'copy_link': "📋 کپی لینک",
        'address_copied': "✅ آدرس کپی شد!",
        'link_copied': "✅ لینک کپی شد!",
        'subscription_status': "💳 وضعیت: {status}",
        'remaining_bots': "📦 ربات باقیمانده: {remaining}/{max}",
        'daily_usage': "📊 **مصرف شما امروز**",
        'builds_today': "🤖 ساخت ربات: {count}/{max}",
        'usage_bar': "📈 {bar} {percent}%",
        'total_bots_count': "📋 تعداد ربات‌ها: {count}",
        'wallet_title': "💰 **کیف پول و اشتراک**",
        'wallet_balance': "💰 موجودی: {balance:,} تومان",
        'payment_guide': "💳 برای فعالسازی {price} را به آدرس زیر واریز:\n`{address}`\n🌐 شبکه: TRC20 (USDT)\n\n📸 پس از واریز، تصویر تراکنش را ارسال کنید",
        'receipt_pending': "⏳ فیش قبلی در انتظار تایید است",
        'admin_panel': "👑 پنل مدیریت:",
        'admin_receipts': "📸 فیش‌ها",
        'admin_stats': "📊 آمار",
        'admin_machines': "🖥️ ماشین‌ها",
        'admin_withdraws': "💰 برداشت‌ها",
        'admin_settings': "⚙️ تنظیمات",
        'admin_back': "🔙 بازگشت",
        'no_pending': "✅ موردی ندارد",
        'approve': "✅ تایید",
        'reject': "❌ رد",
        'approved': "✅ تایید شد",
        'rejected': "❌ رد شد",
        'language_changed': "✅ زبان به فارسی تغییر کرد",
        'language_changed_en': "✅ Language changed to English",
        'send_file': "📤 فایل `.py` یا `.zip` خود را ارسال کنید"
    },
    'en': {
        'welcome': "🚀 Welcome {name}!",
        'subscription_active': "✅ Subscription Active",
        'subscription_inactive': "❌ Subscription Inactive",
        'bots_remaining': "🤖 Bots remaining: {remaining}/{max}",
        'deposit_address': "💳 TRC20 Deposit Address:\n`{address}`",
        'send_receipt': "📸 Please send your transaction screenshot",
        'receipt_received': "✅ Receipt received, pending approval",
        'commission_added': "🎉 Commission {amount:,} Toman added to your wallet",
        'bot_limit_reached': "❌ You have reached the maximum of {max} bots",
        'build_guide': "📚 Bot Building Guide\n\n1️⃣ Send your .py file\n2️⃣ Wait for it to be built\n3️⃣ Your bot is ready!",
        'error': "❌ Error: {error}",
        'success': "✅ Success: {message}",
        'persian': "🇮🇷 Persian",
        'english': "🇬🇧 English",
        'balance': "💰 Balance: {balance:,} Toman",
        'referral_count': "👥 Referrals: {count}",
        'expiry_date': "📅 Expiry: {date}",
        'no_bots': "📋 No bots yet",
        'bot_list': "📋 Your Bots",
        'select_bot': "🤖 Select a bot:",
        'confirm_delete': "⚠️ Are you sure you want to delete?",
        'deleted': "✅ Deleted",
        'started': "✅ Started",
        'stopped': "✅ Stopped",
        'processing': "🔄 Processing...",
        'invalid_file': "❌ Only .py or .zip files",
        'file_too_large': "❌ File too large (max 50MB)",
        'token_not_found': "❌ Bot token not found in code",
        'invalid_token': "❌ Invalid bot token",
        'build_success': "✅ Bot {name} created!\n🤖 Remaining slots: {remaining}",
        'build_failed': "❌ Build failed: {error}",
        'stats_title': "📊 **System Statistics**",
        'users_count': "👥 Users: {count:,}",
        'active_subs': "✅ Active Subscriptions: {count:,}",
        'total_bots': "🤖 Total Bots: {count:,}",
        'running_bots': "🟢 Running Bots: {count:,}",
        'total_wallet': "💰 Total Wallet: {amount:,} Toman",
        'machine_stats': "🖥️ Machines: {machines} | Usage: {usage}%",
        'queue_status': "⚡ Build Queue: {queue}",
        'support': "📞 Support: @shahraghee13",
        'invite_title': "👥 **Referral System**",
        'referral_code': "🎁 Referral Code: `{code}`",
        'referral_link': "🔗 Invite Link: `{link}`",
        'commission_rate': "💰 Commission per subscription: {percent}%",
        'total_commission': "💎 Total Commission: {amount:,} Toman",
        'copy_link': "📋 Copy Link",
        'address_copied': "✅ Address copied!",
        'link_copied': "✅ Link copied!",
        'subscription_status': "💳 Status: {status}",
        'remaining_bots': "📦 Remaining bots: {remaining}/{max}",
        'daily_usage': "📊 **Your Daily Usage**",
        'builds_today': "🤖 Bot builds: {count}/{max}",
        'usage_bar': "📈 {bar} {percent}%",
        'total_bots_count': "📋 Total bots: {count}",
        'wallet_title': "💰 **Wallet & Subscription**",
        'wallet_balance': "💰 Balance: {balance:,} Toman",
        'payment_guide': "💳 To activate, send {price} to:\n`{address}`\n🌐 Network: TRC20 (USDT)\n\n📸 Send transaction screenshot after payment",
        'receipt_pending': "⏳ Previous receipt pending approval",
        'admin_panel': "👑 Admin Panel:",
        'admin_receipts': "📸 Receipts",
        'admin_stats': "📊 Stats",
        'admin_machines': "🖥️ Machines",
        'admin_withdraws': "💰 Withdrawals",
        'admin_settings': "⚙️ Settings",
        'admin_back': "🔙 Back",
        'no_pending': "✅ Nothing pending",
        'approve': "✅ Approve",
        'reject': "❌ Reject",
        'approved': "✅ Approved",
        'rejected': "❌ Rejected",
        'language_changed': "✅ Language changed to Persian",
        'language_changed_en': "✅ زبان به انگلیسی تغییر کرد",
        'send_file': "📤 Send your `.py` or `.zip` file"
    }
}

# ==================== کلاس ذخیره وضعیت (State Manager) ====================
class StateManager:
    def __init__(self):
        self.state_file = os.path.join(DIRS['STATE'], 'system_state.pkl')
        self.state = {}
        self.lock = threading.RLock()
        self._load_state()
        self._start_save_thread()
    
    def _load_state(self):
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'rb') as f:
                    self.state = pickle.load(f)
                logger.info("✅ System state restored from backup")
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            self.state = {
                'active_bots': {},
                'user_subscriptions': {},
                'last_backup': None,
                'system_health': 'healthy',
                'startup_time': time.time()
            }
    
    def _save_state(self):
        try:
            with open(self.state_file, 'wb') as f:
                pickle.dump(self.state, f)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def _start_save_thread(self):
        def saver():
            while True:
                time.sleep(get_setting('state_save_interval'))
                with self.lock:
                    self._save_state()
        threading.Thread(target=saver, daemon=True).start()
    
    def update_bot_state(self, bot_id, status, pid=None):
        with self.lock:
            self.state['active_bots'][bot_id] = {
                'status': status,
                'pid': pid,
                'timestamp': time.time()
            }
    
    def get_bot_state(self, bot_id):
        return self.state.get('active_bots', {}).get(bot_id)

state_manager = StateManager()

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
    
    def _start_backup_thread(self):
        def backup_worker():
            while True:
                time.sleep(get_setting('backup_interval'))
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
            
            logger.info(f"✅ Database backup created: {backup_name}")
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
        if CRYPTO_AVAILABLE:
            return FERNET_CIPHER.encrypt(token.encode()).decode()
        return token
    
    def decrypt_token(self, encrypted_token):
        if CRYPTO_AVAILABLE:
            try:
                return FERNET_CIPHER.decrypt(encrypted_token.encode()).decode()
            except Exception:
                logger.error("Failed to decrypt token")
                return None
        return encrypted_token
    
    def _init_tables(self):
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
                is_premium INTEGER DEFAULT 0,
                login_attempts INTEGER DEFAULT 0,
                last_ip TEXT
            )
        ''')
        
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
                schedule_start TEXT,
                schedule_stop TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
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
        
        self.execute('''
            CREATE TABLE IF NOT EXISTS crypto_transactions (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                tx_hash TEXT UNIQUE,
                amount INTEGER,
                confirmations INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP,
                verified_at TIMESTAMP
            )
        ''')
        
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
        
        self.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP
            )
        ''')
        
        self.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT PRIMARY KEY,
                new_users INTEGER DEFAULT 0,
                new_bots INTEGER DEFAULT 0,
                new_subscriptions INTEGER DEFAULT 0,
                total_revenue INTEGER DEFAULT 0,
                active_users INTEGER DEFAULT 0,
                total_requests INTEGER DEFAULT 0,
                avg_response_time REAL DEFAULT 0
            )
        ''')
        
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
        
        self.execute('''
            CREATE TABLE IF NOT EXISTS security_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                user_id INTEGER,
                ip TEXT,
                details TEXT,
                created_at TIMESTAMP
            )
        ''')
        
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
        
        for key, value in DEFAULT_SETTINGS.items():
            self.execute('''
                INSERT OR IGNORE INTO system_settings (key, value, updated_at) 
                VALUES (?, ?, ?)
            ''', (key, str(value), datetime.now().isoformat()))
        
        for i in range(1, 11):
            self.execute('''
                INSERT OR IGNORE INTO machines (id, name, status, max_bots, max_memory, created_at, is_kubernetes_pod)
                VALUES (?, ?, 'active', ?, ?, ?, 0)
            ''', (i, f"Machine-{i:03d}", 5000, 256000, datetime.now().isoformat()))

db = Database()

# ==================== توابع کمکی ====================
def get_setting(key):
    result = db.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
    if result:
        val = result[0]['value']
        if key in ['subscription_price', 'withdraw_percent', 'min_withdraw', 
                   'max_bots_per_subscription', 'max_builds_per_hour', 
                   'max_concurrent_builds', 'rate_limit_per_second',
                   'health_check_interval', 'auto_scale_threshold',
                   'backup_interval', 'state_save_interval']:
            try:
                return int(val)
            except:
                return DEFAULT_SETTINGS.get(key)
        return val
    return DEFAULT_SETTINGS.get(key)

def update_setting(key, value):
    db.execute("UPDATE system_settings SET value = ?, updated_at = ? WHERE key = ?", 
               (str(value), datetime.now().isoformat(), key))

def get_user_language(user_id):
    user = get_user(user_id)
    if user:
        return user.get('language', 'fa')
    return 'fa'

def get_text(user_id, key, **kwargs):
    lang = get_user_language(user_id)
    text = TEXTS.get(lang, TEXTS['fa']).get(key, key)
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
    if users:
        return dict(users[0])
    return None

def create_user(user_id, username, first_name, last_name, referred_by=None, language='fa'):
    now = datetime.now().isoformat()
    referral_code = generate_referral_code(user_id)
    max_bots = get_setting('max_bots_per_subscription')
    
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
                db.execute('UPDATE users SET subscription_status = "inactive", warning_sent = 0 WHERE user_id = ?', (user_id,))
    
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
        UPDATE users 
        SET subscription_status = 'active', 
            subscription_expiry = ?, 
            subscription_purchased_at = ?,
            last_payment_hash = ?
        WHERE user_id = ?
    ''', (new_expiry.isoformat(), now.isoformat(), tx_hash, user_id))
    
    db.execute('UPDATE daily_stats SET new_subscriptions = new_subscriptions + 1, total_revenue = total_revenue + ? WHERE date = ?',
              (get_setting('subscription_price'), datetime.now().date().isoformat()))
    
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
    
    guide_text = get_text(user_id, 'build_guide')
    bot.send_message(user_id, guide_text)
    logger.info(f"Subscription activated for user {user_id}")

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
        (id, user_id, token, name, username, file_path, pid, machine_id, status, created_at, last_active, join_enabled, join_block_message, health_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'running', ?, ?, 1, '🚫 سرور در حال حاضر پر است. لطفاً بعداً تلاش کنید.', 'healthy')
    ''', (bot_id, user_id, encrypted_token, name, username, file_path, pid, machine_id, now, now))
    db.execute('UPDATE users SET bots_count = bots_count + 1, total_builds = total_builds + 1, last_build_at = ? WHERE user_id = ?', (now, user_id))
    db.execute('UPDATE daily_stats SET new_bots = new_bots + 1 WHERE date = ?', (datetime.now().date().isoformat(),))
    return True

def can_create_bot(user_id):
    if not check_subscription(user_id):
        return False, "no_subscription"
    
    remaining = get_remaining_bots(user_id)
    if remaining <= 0:
        return False, "limit_reached"
    
    builds_today = rate_limiter.get_user_builds_today(user_id)
    max_builds = get_setting('max_builds_per_hour')
    if builds_today >= max_builds:
        return False, "rate_limit"
    
    return True, "ok"

def log_error(error_type, message, user_id=None, bot_id=None, stack_trace=None):
    error_id = hashlib.md5(f"{time.time()}_{user_id}_{bot_id}_{secrets.token_hex(4)}".encode()).hexdigest()[:16]
    db.execute('''
        INSERT INTO errors (id, type, message, user_id, bot_id, timestamp, resolved, stack_trace)
        VALUES (?, ?, ?, ?, ?, ?, 0, ?)
    ''', (error_id, error_type, message[:500], user_id, bot_id, datetime.now().isoformat(), stack_trace))
    
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    db.execute('DELETE FROM errors WHERE timestamp < ?', (week_ago,))

def install_library(lib_name, chat_id, msg_id):
    try:
        process = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', lib_name, '--quiet'],
            capture_output=True,
            text=True,
            timeout=120
        )
        if process.returncode == 0:
            bot.edit_message_text(f"✅ کتابخانه {lib_name} نصب شد!", chat_id, msg_id)
            return True
        else:
            error = process.stderr[:200] if process.stderr else "خطا"
            bot.edit_message_text(f"❌ خطا: {error}", chat_id, msg_id)
            return False
    except subprocess.TimeoutExpired:
        bot.edit_message_text(f"❌ زمان نصب تمام شد!", chat_id, msg_id)
        return False
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)[:100]}", chat_id, msg_id)
        return False

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
        result = db.execute("SELECT COUNT(*) as count FROM bots WHERE user_id = ? AND DATE(created_at) = ?", 
                           (user_id, today))
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
                
                user = get_user(build_data['user_id'])
                if user and user.get('referred_by'):
                    commission_percent = get_setting('withdraw_percent')
                    price = get_setting('subscription_price')
                    commission = int(price * commission_percent / 100)
                    add_wallet_balance(user['referred_by'], commission)
                    try:
                        temp_bot.send_message(user['referred_by'], 
                            get_text(user['referred_by'], 'commission_added', amount=commission))
                    except:
                        pass
                
                remaining = get_remaining_bots(build_data['user_id'])
                success_text = get_text(build_data['user_id'], 'build_success', 
                                       name=build_data['bot_info']['first_name'], 
                                       remaining=remaining)
                temp_bot.edit_message_text(success_text, build_item['chat_id'], build_item['message_id'])
            else:
                temp_bot.edit_message_text(
                    get_text(build_data['user_id'], 'build_failed', error=result.get('error', 'مشخص نشده')),
                    build_item['chat_id'], 
                    build_item['message_id']
                )
            
        except Exception as e:
            logger.error(f"Build failed: {e}")
            try:
                temp_bot.edit_message_text(
                    f"❌ خطا در ساخت ربات: {str(e)[:100]}", 
                    build_item['chat_id'], 
                    build_item['message_id']
                )
            except:
                pass
    
    def get_status(self, build_id):
        with self.lock:
            if build_id in self.processing:
                return self.processing[build_id]
        return None
    
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
                interval = get_setting('health_check_interval')
                
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
                        
                        user = db.execute('SELECT user_id FROM bots WHERE id = ?', (bot_id,))
                        if user:
                            try:
                                lang = get_user_language(user[0]['user_id'])
                                msg = "🔄 Your bot was automatically restarted." if lang == 'en' else "🔄 ربات شما به صورت خودکار ریستارت شد."
                                bot.send_message(user[0]['user_id'], msg)
                            except:
                                pass
                    else:
                        db.execute('UPDATE bots SET status = "error" WHERE id = ?', (bot_id,))
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
                threshold = get_setting('auto_scale_threshold')
                
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
                    lang = get_user_language(admin_id)
                    msg = f"📈 System scaled up - New machine {new_id} added" if lang == 'en' else f"📈 مقیاس سیستم افزایش یافت - ماشین جدید {new_id} اضافه شد"
                    bot.send_message(admin_id, msg)
                except:
                    pass
        
        except Exception as e:
            logger.error(f"Scale up failed: {e}")
    
    def get_scaling_recommendation(self):
        machines = db.execute("SELECT * FROM machines WHERE status = 'active'")
        total_capacity = sum(m['max_bots'] for m in machines)
        total_used = sum(m['current_bots'] for m in machines)
        usage_percent = (total_used / total_capacity) * 100 if total_capacity > 0 else 0
        
        if usage_percent > 80:
            return "⚠️ نیاز به مقیاس بالا - اضافه کردن ماشین جدید" if get_user_language(ADMIN_IDS[0]) == 'fa' else "⚠️ Scale up needed - add new machine"
        elif usage_percent > 60:
            return "⚡ نزدیک به ظرفیت، پیشنهاد مقیاس" if get_user_language(ADMIN_IDS[0]) == 'fa' else "⚡ Near capacity, scale recommended"
        elif usage_percent < 20 and len(machines) > 5:
            return "📉 می‌توانید مقیاس را کاهش دهید" if get_user_language(ADMIN_IDS[0]) == 'fa' else "📉 You can scale down"
        else:
            return "✅ ظرفیت کافی است" if get_user_language(ADMIN_IDS[0]) == 'fa' else "✅ Capacity sufficient"

# ==================== مدیریت ماشین‌ها ====================
class MachineManager:
    def __init__(self):
        self.port_counter = 8000
        self.processes = {}
        self.lock = threading.RLock()
        self._restore_bots_after_crash()
    
    def _restore_bots_after_crash(self):
        try:
            logger.info("🔄 Checking for bots to restore after crash...")
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
                return {'success': False, 'error': 'همه ماشین‌ها پر هستند' if not restore else 'No machine available'}
            
            port = self.get_available_port()
            bot_dir = os.path.join(DIRS['MACHINES'], f"machine_{machine_id:03d}", bot_id)
            os.makedirs(bot_dir, exist_ok=True)
            
            code_path = os.path.join(bot_dir, 'bot.py')
            
            join_check_code = f'''
# ========== سیستم مدیریت عضوگیری ==========
import sqlite3, os, time, threading
from functools import wraps

DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'database', 'mother_bot.db')
CHECK_INTERVAL = 30
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
        time.sleep(CHECK_INTERVAL)

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
                
                state_manager.update_bot_state(bot_id, 'running', process.pid)
                return {'success': True, 'pid': process.pid, 'machine_id': machine_id}
            else:
                return {'success': False, 'error': 'خطا در اجرای ربات' if not restore else 'Failed to start'}
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
                    state_manager.update_bot_state(bot_id, 'stopped')
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

# ==================== ربات تلگرام ====================
bot = telebot.TeleBot(BOT_TOKEN)
bot.delete_webhook()

# ایجاد نمونه‌ها
machine_manager = MachineManager()
build_queue = BuildQueue()
health_checker = HealthChecker()
auto_scaler = AutoScaleManager()

# ==================== منوی اصلی (رفع شده) ====================
def get_main_menu(user_id):
    """دریافت منوی اصلی بر اساس زبان کاربر"""
    try:
        user = get_user(user_id)
        lang = user['language'] if user else 'fa'
    except:
        lang = 'fa'
    
    is_admin = user_id in ADMIN_IDS
    
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    
    if lang == 'fa':
        buttons = MENU_BUTTONS_FA.copy()
        if is_admin:
            buttons.extend(ADMIN_BUTTONS_FA)
    else:
        buttons = MENU_BUTTONS_EN.copy()
        if is_admin:
            buttons.extend(ADMIN_BUTTONS_EN)
    
    markup.add(*buttons)
    return markup

# ==================== به‌روزرسانی منو پس از تغییر زبان ====================
def update_user_menu(chat_id, user_id):
    """به‌روزرسانی منوی کاربر پس از تغییر زبان"""
    try:
        new_menu = get_main_menu(user_id)
        bot.send_message(chat_id, get_text(user_id, 'language_changed' if get_user_language(user_id) == 'fa' else 'language_changed_en'),
                        reply_markup=new_menu)
    except Exception as e:
        logger.error(f"Menu update error: {e}")
        # اگر خطا خورد، دوباره تلاش کن
        time.sleep(1)
        try:
            new_menu = get_main_menu(user_id)
            bot.send_message(chat_id, get_text(user_id, 'language_changed' if get_user_language(user_id) == 'fa' else 'language_changed_en'),
                            reply_markup=new_menu)
        except:
            pass

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
                bot.send_message(referred_by, get_text(referred_by, 'welcome', name=first_name))
            except:
                pass
    
    create_user(user_id, username, first_name, message.from_user.last_name or "", referred_by, preferred_lang)
    user = get_user(user_id)
    referral_link = f"https://t.me/{BOT_USERNAME}?start={user['referral_code']}"
    remaining_bots = get_remaining_bots(user_id)
    max_bots = get_setting('max_bots_per_subscription')
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
                f"🤖 ربات‌های باقیمانده: {remaining_bots}/{max_bots}")
    else:
        text = (f"🚀 Welcome {first_name}!\n\n"
                f"👤 ID: `{user_id}`\n"
                f"🎁 Referral Code: `{user['referral_code']}`\n"
                f"🔗 Invite Link: `{referral_link}`\n"
                f"📊 Referrals: {user['referrals_count']}\n"
                f"💰 Balance: {user['wallet_balance']:,} Toman\n"
                f"💳 Status: {'✅ Active' if is_subscribed else '❌ Inactive'}\n"
                f"🤖 Remaining Bots: {remaining_bots}/{max_bots}")
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(get_text(user_id, 'copy_link'), 
                                          callback_data=f"copy_link_{user['referral_code']}"))
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown', 
                    reply_markup=get_main_menu(user_id))

@bot.callback_query_handler(func=lambda call: call.data.startswith('copy_link_'))
def copy_link_callback(call):
    code = call.data.replace('copy_link_', '')
    link = f"https://t.me/{BOT_USERNAME}?start={code}"
    bot.answer_callback_query(call.id, get_text(call.from_user.id, 'link_copied'), show_alert=True)

# ==================== زبان (رفع شده) ====================
@bot.message_handler(func=lambda m: m.text in ['🌐 زبان / Language', '🌐 Language / زبان'])
def change_language(message):
    user_id = message.from_user.id
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(TEXTS['fa']['persian'], callback_data="lang_fa"),
        types.InlineKeyboardButton(TEXTS['en']['english'], callback_data="lang_en")
    )
    bot.send_message(message.chat.id, "Select your language / زبان خود را انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def set_language(call):
    try:
        lang = call.data.replace('lang_', '')
        user_id = call.from_user.id
        
        # به‌روزرسانی زبان در دیتابیس
        db.execute("UPDATE users SET language = ? WHERE user_id = ?", (lang, user_id))
        
        # پاسخ به کاربر
        msg = "✅ Language set to English" if lang == 'en' else "✅ زبان به فارسی تغییر کرد"
        bot.answer_callback_query(call.id, msg)
        
        # حذف پیام انتخاب زبان
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        
        # ارسال پیام تایید با منوی جدید
        success_msg = get_text(user_id, 'language_changed_en' if lang == 'en' else 'language_changed')
        
        # گرفتن منوی جدید بر اساس زبان تازه
        new_menu = get_main_menu(user_id)
        
        # ارسال پیام با منوی جدید
        bot.send_message(call.message.chat.id, success_msg, reply_markup=new_menu)
        
        # به‌روزرسانی منوی اصلی کاربر (اختیاری)
        update_user_menu(call.message.chat.id, user_id)
        
    except Exception as e:
        logger.error(f"Language change error: {e}")
        # در صورت خطا، دوباره تلاش کن
        try:
            new_menu = get_main_menu(user_id)
            bot.send_message(call.message.chat.id, "✅ Language updated", reply_markup=new_menu)
        except:
            pass

# ==================== کیف پول و اشتراک ====================
@bot.message_handler(func=lambda m: m.text in ['💰 کیف پول و اشتراک', '💰 Wallet & Subscription'])
def wallet(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        bot.send_message(message.chat.id, get_text(user_id, 'error', error="Start with /start"))
        return
    
    lang = user['language']
    is_subscribed = check_subscription(user_id)
    expiry = datetime.fromisoformat(user['subscription_expiry']).strftime('%Y-%m-%d') if user['subscription_expiry'] else "N/A"
    remaining_bots = get_remaining_bots(user_id)
    max_bots = get_setting('max_bots_per_subscription')
    
    if lang == 'fa':
        text = (f"💰 **کیف پول و اشتراک**\n\n"
                f"👤 {user['first_name']}\n"
                f"💳 وضعیت: {'✅ فعال' if is_subscribed else '❌ غیرفعال'}\n"
                f"📅 انقضا: {expiry}\n"
                f"💰 موجودی: {user['wallet_balance']:,} تومان\n"
                f"👥 دعوت‌ها: {user['referrals_count']}\n"
                f"🤖 ربات‌های باقیمانده: {remaining_bots}/{max_bots}\n\n"
                f"💳 برای فعالسازی {get_setting('subscription_price_str')} را به آدرس زیر واریز:\n"
                f"`{TRC20_ADDRESS}`\n"
                f"🌐 شبکه: TRC20 (USDT)\n\n"
                f"📸 پس از واریز، تصویر تراکنش را ارسال کنید")
    else:
        text = (f"💰 **Wallet & Subscription**\n\n"
                f"👤 {user['first_name']}\n"
                f"💳 Status: {'✅ Active' if is_subscribed else '❌ Inactive'}\n"
                f"📅 Expiry: {expiry}\n"
                f"💰 Balance: {user['wallet_balance']:,} Toman\n"
                f"👥 Referrals: {user['referrals_count']}\n"
                f"🤖 Remaining Bots: {remaining_bots}/{max_bots}\n\n"
                f"💳 To activate, send {get_setting('subscription_price_str')} to:\n"
                f"`{TRC20_ADDRESS}`\n"
                f"🌐 Network: TRC20 (USDT)\n\n"
                f"📸 Send transaction screenshot after payment")
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(get_text(user_id, 'copy_link'), callback_data="copy_address"))
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "copy_address")
def copy_address(call):
    bot.answer_callback_query(call.id, get_text(call.from_user.id, 'address_copied'), show_alert=True)

# ==================== دریافت تصویر تراکنش ====================
@bot.message_handler(content_types=['photo'])
def handle_transaction_receipt(message):
    user_id = message.from_user.id
    
    existing = db.execute('SELECT id FROM receipts WHERE user_id = ? AND status = "pending"', (user_id,))
    if existing:
        bot.reply_to(message, get_text(user_id, 'receipt_pending'))
        return
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        tx_hash = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:16].upper()
        receipt_path = os.path.join(DIRS['RECEIPTS'], f"{user_id}_{tx_hash}.jpg")
        
        with open(receipt_path, 'wb') as f:
            f.write(downloaded)
        
        db.execute('''
            INSERT INTO receipts (user_id, amount, receipt_path, tx_hash, created_at) 
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, get_setting('subscription_price'), receipt_path, tx_hash, datetime.now().isoformat()))
        
        bot.reply_to(message, get_text(user_id, 'receipt_received'))
        
        for admin_id in ADMIN_IDS:
            try:
                with open(receipt_path, 'rb') as f:
                    caption = f"📸 New Receipt\n👤 User: {message.from_user.first_name}\n🆔 ID: {user_id}\n💰 Amount: {get_setting('subscription_price_str')}\n🆔 Hash: {tx_hash}"
                    bot.send_photo(admin_id, f, caption=caption)
            except:
                pass
                
    except Exception as e:
        bot.reply_to(message, get_text(user_id, 'error', error=str(e)[:50]))

# ==================== دعوت دوستان ====================
@bot.message_handler(func=lambda m: m.text in ['👥 دعوت دوستان', '👥 Invite Friends'])
def invite(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    lang = user['language']
    
    referral_link = f"https://t.me/{BOT_USERNAME}?start={user['referral_code']}"
    commission_percent = get_setting('withdraw_percent')
    
    if lang == 'fa':
        text = (f"👥 **سیستم دعوت دوستان**\n\n"
                f"🎁 کد معرف: `{user['referral_code']}`\n"
                f"🔗 لینک: `{referral_link}`\n"
                f"📊 دعوت‌ها: {user['referrals_count']}\n"
                f"💰 کمیسیون هر اشتراک: {commission_percent}%\n"
                f"💎 کمیسیون کل: {user.get('total_commission', 0):,} تومان")
    else:
        text = (f"👥 **Invite Friends**\n\n"
                f"🎁 Referral Code: `{user['referral_code']}`\n"
                f"🔗 Link: `{referral_link}`\n"
                f"📊 Referrals: {user['referrals_count']}\n"
                f"💰 Commission per subscription: {commission_percent}%\n"
                f"💎 Total Commission: {user.get('total_commission', 0):,} Toman")
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(get_text(user_id, 'copy_link'), 
                                          callback_data=f"copy_link_{user['referral_code']}"))
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

# ==================== ساخت ربات جدید ====================
@bot.message_handler(func=lambda m: m.text in ['🤖 ساخت ربات جدید', '🤖 New Bot'])
def new_bot(message):
    user_id = message.from_user.id
    lang = get_user_language(user_id)
    
    can_create, reason = can_create_bot(user_id)
    
    if not can_create:
        if reason == "no_subscription":
            text = "❌ You need an active subscription first!" if lang == 'en' else "❌ ابتدا باید اشتراک فعال کنید!"
        elif reason == "limit_reached":
            max_bots = get_setting('max_bots_per_subscription')
            text = f"❌ You have reached the maximum of {max_bots} bots per subscription" if lang == 'en' else f"❌ به حداکثر {max_bots} ربات در هر اشتراک رسیده‌اید"
        else:
            text = "❌ Rate limit exceeded" if lang == 'en' else "❌ به محدودیت ساعتی رسیده‌اید"
        
        bot.send_message(message.chat.id, text)
        return
    
    bot.send_message(message.chat.id, get_text(user_id, 'send_file'))

@bot.message_handler(content_types=['document'])
def handle_build_file(message):
    user_id = message.from_user.id
    lang = get_user_language(user_id)
    
    can_create, _ = can_create_bot(user_id)
    if not can_create:
        bot.reply_to(message, "❌ Subscription required or limit reached" if lang == 'en' else "❌ اشتراک فعال نیست یا محدودیت رسیده")
        return
    
    file_name = message.document.file_name
    if not (file_name.endswith('.py') or file_name.endswith('.zip')):
        bot.reply_to(message, get_text(user_id, 'invalid_file'))
        return
    
    if message.document.file_size > 50 * 1024 * 1024:
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
        
        main_code = ""
        if file_name.endswith('.zip'):
            extract_dir = os.path.join(DIRS['TEMP'], f"extract_{user_id}_{int(time.time())}")
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            for root, _, files in os.walk(extract_dir):
                for f in files:
                    if f.endswith('.py'):
                        with open(os.path.join(root, f), 'r', encoding='utf-8', errors='ignore') as code_f:
                            main_code = code_f.read()
                            break
                if main_code:
                    break
            shutil.rmtree(extract_dir, ignore_errors=True)
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                main_code = f.read()
        
        if not main_code:
            bot.edit_message_text(get_text(user_id, 'error', error="No Python file found"), 
                                 message.chat.id, status_msg.message_id)
            return
        
        token = extract_token_from_code(main_code)
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
        
        rate_limiter.increment_user_builds(user_id)
        bot_id = hashlib.md5(f"{user_id}{token}{time.time()}".encode()).hexdigest()[:16]
        
        build_data = {
            'bot_id': bot_id,
            'user_id': user_id,
            'token': token,
            'bot_info': bot_info,
            'file_path': file_path,
            'main_code': main_code,
            'chat_id': message.chat.id,
            'message_id': status_msg.message_id
        }
        
        build_queue.add_build(user_id, file_path, file_name, message.chat.id, status_msg.message_id, build_data)
        
    except Exception as e:
        bot.edit_message_text(get_text(user_id, 'error', error=str(e)[:100]), 
                             message.chat.id, status_msg.message_id)

# ==================== ربات‌های من ====================
@bot.message_handler(func=lambda m: m.text in ['📋 ربات‌های من', '📋 My Bots'])
def my_bots(message):
    user_id = message.from_user.id
    lang = get_user_language(user_id)
    
    bots = get_user_bots(user_id)
    if not bots:
        bot.send_message(message.chat.id, get_text(user_id, 'no_bots'))
        return
    
    bot.send_message(message.chat.id, get_text(user_id, 'bot_list'))
    for b in bots[:15]:
        status = machine_manager.get_status(b['id'])
        emoji = "🟢" if status.get('running') else "🔴"
        text = f"{emoji} {b['name']}\n🔗 t.me/{b['username']}"
        bot.send_message(message.chat.id, text)

# ==================== فعال/غیرفعال ====================
@bot.message_handler(func=lambda m: m.text in ['🔄 فعال/غیرفعال', '🔄 Start/Stop'])
def toggle_prompt(message):
    user_id = message.from_user.id
    lang = get_user_language(user_id)
    
    bots = get_user_bots(user_id)
    if not bots:
        bot.send_message(message.chat.id, get_text(user_id, 'no_bots'))
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
    lang = get_user_language(call.from_user.id)
    
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
def delete_prompt(message):
    user_id = message.from_user.id
    lang = get_user_language(user_id)
    
    bots = get_user_bots(user_id)
    if not bots:
        bot.send_message(message.chat.id, get_text(user_id, 'no_bots'))
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        markup.add(types.InlineKeyboardButton(f"🗑 {b['name']}", callback_data=f"delete_{b['id']}"))
    
    bot.send_message(message.chat.id, get_text(user_id, 'select_bot'), reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
def confirm_delete(call):
    bot_id = call.data.replace('delete_', '')
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Yes" if get_user_language(call.from_user.id) == 'en' else "✅ بله", 
                                  callback_data=f"confirm_del_{bot_id}"),
        types.InlineKeyboardButton("❌ No" if get_user_language(call.from_user.id) == 'en' else "❌ انصراف", 
                                  callback_data="cancel_del")
    )
    bot.edit_message_text(get_text(call.from_user.id, 'confirm_delete'),
                         call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_del_'))
def do_delete(call):
    bot_id = call.data.replace('confirm_del_', '')
    if delete_bot(bot_id, call.from_user.id):
        bot.edit_message_text(get_text(call.from_user.id, 'deleted'), 
                             call.message.chat.id, call.message.message_id)
    else:
        bot.edit_message_text(get_text(call.from_user.id, 'error', error="Delete failed"),
                             call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == 'cancel_del')
def cancel_delete(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== کتابخانه ====================
@bot.message_handler(func=lambda m: m.text in ['📦 کتابخانه', '📦 Library'])
def library_menu(message):
    lang = get_user_language(message.from_user.id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    popular = list(POPULAR_LIBRARIES.items())[:20]
    for name, lib in popular:
        markup.add(types.InlineKeyboardButton(f"📦 {name}", callback_data=f"lib_{lib}"))
    
    markup.add(types.InlineKeyboardButton("🔧 Manual Install" if lang == 'en' else "🔧 نصب دستی", 
                                          callback_data="lib_manual"))
    markup.add(types.InlineKeyboardButton("🔙 Back" if lang == 'en' else "🔙 بازگشت", 
                                          callback_data="lib_back"))
    
    bot.reply_to(message, "📦 Select library:" if lang == 'en' else "📦 کتابخانه مورد نظر:", 
                reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "lib_manual")
def library_manual(call):
    msg = bot.send_message(call.message.chat.id, "🔧 Library name:")
    bot.register_next_step_handler(msg, install_custom_library)
    bot.answer_callback_query(call.id)

def install_custom_library(message):
    lib = message.text.strip()
    if not lib:
        bot.reply_to(message, "❌ Invalid library name")
        return
    status = bot.reply_to(message, f"🔄 Installing {lib}...")
    install_library(lib, message.chat.id, status.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lib_') and call.data not in ['lib_manual', 'lib_back'])
def install_selected_library(call):
    lib = call.data.replace('lib_', '')
    status = bot.send_message(call.message.chat.id, f"🔄 Installing {lib}...")
    install_library(lib, call.message.chat.id, status.message_id)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "lib_back")
def library_back(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "🚀 Main Menu:", 
                    reply_markup=get_main_menu(call.from_user.id))

# ==================== راهنما ====================
@bot.message_handler(func=lambda m: m.text in ['📚 راهنما', '📚 Guide'])
def guide(message):
    user_id = message.from_user.id
    lang = get_user_language(user_id)
    
    guide_text = get_setting('guide_text_fa') if lang == 'fa' else get_setting('guide_text_en')
    bot.send_message(message.chat.id, guide_text)

# ==================== آمار ====================
@bot.message_handler(func=lambda m: m.text in ['📊 آمار', '📊 Stats'])
def stats(message):
    user_id = message.from_user.id
    lang = get_user_language(user_id)
    
    users_count = db.execute('SELECT COUNT(*) as count FROM users')[0]['count']
    active_subs = db.execute('SELECT COUNT(*) as count FROM users WHERE subscription_status = "active"')[0]['count']
    total_bots = db.execute('SELECT COUNT(*) as count FROM bots')[0]['count']
    running_bots = db.execute('SELECT COUNT(*) as count FROM bots WHERE status = "running"')[0]['count']
    total_wallet = db.execute('SELECT SUM(wallet_balance) as total FROM users')[0]['total'] or 0
    machine_stats = machine_manager.get_stats()
    queue_len = build_queue.get_queue_length()
    
    if lang == 'fa':
        text = (f"📊 **آمار سیستم**\n\n"
                f"👥 کاربران: {users_count:,}\n"
                f"✅ اشتراک فعال: {active_subs:,}\n"
                f"🤖 کل ربات‌ها: {total_bots:,}\n"
                f"🟢 ربات فعال: {running_bots:,}\n"
                f"💰 کیف پول کل: {total_wallet:,} تومان\n"
                f"🖥️ ماشین‌ها: {machine_stats['total']}\n"
                f"📊 مصرف: {machine_stats['usage_percent']:.1f}%\n"
                f"⚡ صف ساخت: {queue_len}")
    else:
        text = (f"📊 **System Statistics**\n\n"
                f"👥 Users: {users_count:,}\n"
                f"✅ Active Subs: {active_subs:,}\n"
                f"🤖 Total Bots: {total_bots:,}\n"
                f"🟢 Running Bots: {running_bots:,}\n"
                f"💰 Total Wallet: {total_wallet:,} Toman\n"
                f"🖥️ Machines: {machine_stats['total']}\n"
                f"📊 Usage: {machine_stats['usage_percent']:.1f}%\n"
                f"⚡ Build Queue: {queue_len}")
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== مصرف من ====================
@bot.message_handler(func=lambda m: m.text in ['📈 مصرف من', '📈 My Usage'])
def my_usage(message):
    user_id = message.from_user.id
    lang = get_user_language(user_id)
    
    builds_today = rate_limiter.get_user_builds_today(user_id)
    max_builds = get_setting('max_builds_per_hour')
    bots_count = len(get_user_bots(user_id))
    remaining = get_remaining_bots(user_id)
    max_bots = get_setting('max_bots_per_subscription')
    
    bar_length = int((builds_today / max_builds) * 20) if max_builds > 0 else 0
    bar = "█" * bar_length + "░" * (20 - bar_length)
    percent = int((builds_today / max_builds) * 100) if max_builds > 0 else 0
    
    if lang == 'fa':
        text = (f"📊 **مصرف شما امروز**\n\n"
                f"🤖 ساخت ربات: {builds_today}/{max_builds}\n"
                f"📈 {bar} {percent}%\n\n"
                f"📋 تعداد ربات‌ها: {bots_count}\n"
                f"📦 ربات باقیمانده: {remaining}/{max_bots}")
    else:
        text = (f"📊 **Your Daily Usage**\n\n"
                f"🤖 Bot builds: {builds_today}/{max_builds}\n"
                f"📈 {bar} {percent}%\n\n"
                f"📋 Total bots: {bots_count}\n"
                f"📦 Remaining slots: {remaining}/{max_bots}")
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== وضعیت صف ====================
@bot.message_handler(func=lambda m: m.text in ['⚡ وضعیت صف', '⚡ Queue Status'])
def queue_status(message):
    user_id = message.from_user.id
    lang = get_user_language(user_id)
    
    queue_len = build_queue.get_queue_length()
    max_concurrent = get_setting('max_concurrent_builds')
    
    if lang == 'fa':
        text = (f"⚡ **وضعیت صف ساخت ربات**\n\n"
                f"📊 در صف: {queue_len}\n"
                f"⚙️ حداکثر همزمان: {max_concurrent}\n"
                f"📈 ساخت امروز شما: {rate_limiter.get_user_builds_today(user_id)}/{get_setting('max_builds_per_hour')}")
    else:
        text = (f"⚡ **Build Queue Status**\n\n"
                f"📊 In queue: {queue_len}\n"
                f"⚙️ Max concurrent: {max_concurrent}\n"
                f"📈 Your builds today: {rate_limiter.get_user_builds_today(user_id)}/{get_setting('max_builds_per_hour')}")
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== پشتیبانی ====================
@bot.message_handler(func=lambda m: m.text in ['📞 پشتیبانی', '📞 Support'])
def support(message):
    user_id = message.from_user.id
    lang = get_user_language(user_id)
    
    if lang == 'fa':
        bot.send_message(message.chat.id, "📞 پشتیبانی: @shahraghee13")
    else:
        bot.send_message(message.chat.id, "📞 Support: @shahraghee13")

# ==================== درخواست برداشت ====================
@bot.message_handler(func=lambda m: m.text in ['💸 درخواست برداشت', '💸 Withdraw'])
def withdraw_request(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    lang = get_user_language(user_id)
    
    min_withdraw = get_setting('min_withdraw')
    
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

# ==================== پنل مدیریت ====================
@bot.message_handler(func=lambda m: m.text in ['👑 پنل مدیریت', '👑 Admin Panel'])
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    lang = get_user_language(message.from_user.id)
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(get_text(message.from_user.id, 'admin_receipts'), callback_data="admin_receipts"),
        types.InlineKeyboardButton(get_text(message.from_user.id, 'admin_stats'), callback_data="admin_stats"),
        types.InlineKeyboardButton(get_text(message.from_user.id, 'admin_machines'), callback_data="admin_machines"),
        types.InlineKeyboardButton(get_text(message.from_user.id, 'admin_withdraws'), callback_data="admin_withdraws"),
        types.InlineKeyboardButton(get_text(message.from_user.id, 'admin_settings'), callback_data="admin_settings"),
        types.InlineKeyboardButton(get_text(message.from_user.id, 'admin_back'), callback_data="admin_back")
    )
    bot.send_message(message.chat.id, get_text(message.from_user.id, 'admin_panel'), reply_markup=markup)

# ==================== کال‌بک‌های ادمین ====================
@bot.callback_query_handler(func=lambda call: call.data == "admin_receipts")
def admin_receipts(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    receipts = db.execute('SELECT * FROM receipts WHERE status = "pending" ORDER BY created_at')
    if not receipts:
        bot.send_message(call.message.chat.id, get_text(call.from_user.id, 'no_pending'))
        return
    
    for r in receipts:
        user = get_user(r['user_id'])
        text = f"📸 Receipt\n👤 {user['first_name'] if user else 'Unknown'}\n💰 {r['amount']:,} Toman\n🆔 {r['tx_hash']}"
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(get_text(call.from_user.id, 'approve'), callback_data=f"approve_receipt_{r['id']}"),
            types.InlineKeyboardButton(get_text(call.from_user.id, 'reject'), callback_data=f"reject_receipt_{r['id']}")
        )
        if os.path.exists(r['receipt_path']):
            with open(r['receipt_path'], 'rb') as f:
                bot.send_photo(call.message.chat.id, f, caption=text, reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_receipt_'))
def approve_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    rid = int(call.data.replace('approve_receipt_', ''))
    r = db.execute('SELECT user_id, tx_hash FROM receipts WHERE id = ?', (rid,))
    if r:
        db.execute('UPDATE receipts SET status = "approved", reviewed_by = ?, reviewed_at = ? WHERE id = ?',
                  (call.from_user.id, datetime.now().isoformat(), rid))
        activate_subscription(r[0]['user_id'], r[0]['tx_hash'])
        
        max_bots = get_setting('max_bots_per_subscription')
        db.execute('UPDATE users SET max_bots = ? WHERE user_id = ?', (max_bots, r[0]['user_id']))
        
        bot.answer_callback_query(call.id, get_text(call.from_user.id, 'approved'))
        bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_receipt_'))
def reject_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    rid = int(call.data.replace('reject_receipt_', ''))
    db.execute('UPDATE receipts SET status = "rejected", reviewed_by = ?, reviewed_at = ? WHERE id = ?',
              (call.from_user.id, datetime.now().isoformat(), rid))
    bot.answer_callback_query(call.id, get_text(call.from_user.id, 'rejected'))
    bot.delete_message(call.message.chat.id, call.message.message_id)

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
    machine_stats = machine_manager.get_stats()
    queue_len = build_queue.get_queue_length()
    
    text = (f"📊 **Full Statistics**\n\n"
            f"👥 Users: {users}\n"
            f"✅ Active Subscriptions: {active}\n"
            f"🤖 Total Bots: {bots}\n"
            f"🟢 Running Bots: {running}\n"
            f"💰 Total Wallet: {total_wallet:,}\n"
            f"💎 Total Commission Paid: {total_commission:,}\n"
            f"🖥️ Machines: {machine_stats['total']}\n"
            f"📊 Usage: {machine_stats['usage_percent']:.1f}%\n"
            f"⚡ Queue: {queue_len}")
    
    bot.send_message(call.message.chat.id, text)

@bot.callback_query_handler(func=lambda call: call.data == "admin_withdraws")
def admin_withdraws(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    withdraws = db.execute('SELECT * FROM withdraw_requests WHERE status = "pending"')
    if not withdraws:
        bot.send_message(call.message.chat.id, get_text(call.from_user.id, 'no_pending'))
        return
    
    for w in withdraws:
        user = get_user(w['user_id'])
        text = f"💰 Withdrawal\n👤 {user['first_name'] if user else 'Unknown'}\n💰 {w['amount']:,} Toman\n💳 {w['address']}"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(get_text(call.from_user.id, 'approve'), 
                                             callback_data=f"approve_withdraw_{w['id']}"))
        bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_withdraw_'))
def approve_withdraw(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    wid = int(call.data.replace('approve_withdraw_', ''))
    db.execute('UPDATE withdraw_requests SET status = "approved", processed_at = ? WHERE id = ?',
              (datetime.now().isoformat(), wid))
    bot.answer_callback_query(call.id, get_text(call.from_user.id, 'approved'))
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_settings")
def admin_settings(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("💰 Subscription Price", callback_data="admin_set_price"),
        types.InlineKeyboardButton("🤖 Max Bots Per Subscription", callback_data="admin_set_max_bots"),
        types.InlineKeyboardButton("📈 Max Builds Per Hour", callback_data="admin_set_build_limit"),
        types.InlineKeyboardButton("🔙 Back", callback_data="admin_back")
    )
    bot.send_message(call.message.chat.id, "⚙️ Settings:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_max_bots")
def admin_set_max_bots(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "📊 Max bots per subscription (default: 3):")
    bot.register_next_step_handler(msg, process_set_max_bots)

def process_set_max_bots(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        max_bots = int(message.text.strip())
        if 1 <= max_bots <= 100:
            update_setting('max_bots_per_subscription', max_bots)
            db.execute('UPDATE users SET max_bots = ?', (max_bots,))
            bot.reply_to(message, f"✅ Max bots set to {max_bots}")
        else:
            bot.reply_to(message, "❌ Number between 1-100")
    except:
        bot.reply_to(message, "❌ Invalid number")

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_price")
def admin_set_price(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "💰 Subscription price (Toman):")
    bot.register_next_step_handler(msg, process_set_price)

def process_set_price(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        price = int(message.text.strip())
        update_setting('subscription_price', price)
        update_setting('subscription_price_str', f"{price:,} تومان")
        update_setting('subscription_price_usd', f"${price // 40000} USD")
        bot.reply_to(message, f"✅ Price set to {price:,} Toman")
    except:
        bot.reply_to(message, "❌ Invalid number")

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_build_limit")
def admin_set_build_limit(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "📈 Max builds per hour (default: 10):")
    bot.register_next_step_handler(msg, process_set_build_limit)

def process_set_build_limit(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        limit = int(message.text.strip())
        if 1 <= limit <= 100:
            update_setting('max_builds_per_hour', limit)
            bot.reply_to(message, f"✅ Max builds per hour set to {limit}")
        else:
            bot.reply_to(message, "❌ Number between 1-100")
    except:
        bot.reply_to(message, "❌ Invalid number")

@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    admin_panel(call.message)

# ==================== پیام همگانی ====================
@bot.message_handler(func=lambda m: m.text in ['📢 پیام همگانی', '📢 Broadcast'])
def broadcast_prompt(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(message.chat.id, "📢 Enter broadcast message:")
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
    
    bot.reply_to(message, f"✅ Sent to {sent} users\n❌ Failed: {failed}")

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

# ==================== مانیتورینگ سیستم ====================
def system_monitor():
    while True:
        try:
            for user in db.execute('SELECT user_id, subscription_expiry FROM users WHERE subscription_status = "active"'):
                if user['subscription_expiry']:
                    expiry = datetime.fromisoformat(user['subscription_expiry'])
                    if expiry < datetime.now():
                        db.execute('UPDATE users SET subscription_status = "inactive" WHERE user_id = ?', (user['user_id'],))
                        logger.info(f"Subscription expired for user {user['user_id']}")
            
            today = datetime.now().date().isoformat()
            db.execute('INSERT OR IGNORE INTO daily_stats (date, new_users, new_bots, new_subscriptions, total_revenue) VALUES (?, 0, 0, 0, 0)', (today,))
            
            time.sleep(60)
        except Exception as e:
            logger.error(f"System monitor error: {e}")
            time.sleep(60)

threading.Thread(target=system_monitor, daemon=True).start()

# ==================== Flask برای مانیتورینگ ====================
flask_app = Flask(__name__)

@flask_app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'active_bots': len(machine_manager.processes),
        'queue_size': build_queue.get_queue_length(),
        'uptime': time.time() - start_time if 'start_time' in dir() else 0
    })

def run_flask():
    flask_app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

threading.Thread(target=run_flask, daemon=True).start()
start_time = time.time()

# ==================== اجرا ====================
if __name__ == "__main__":
    print("=" * 80)
    print("🚀 Mother Bot - Enterprise Edition v100.0".center(80))
    print("=" * 80)
    print(f"👑 Admins: {ADMIN_IDS}")
    print(f"🤖 Bot: @{BOT_USERNAME}")
    print(f"💰 Price: {get_setting('subscription_price_str')}")
    print(f"🤖 Max bots per subscription: {get_setting('max_bots_per_subscription')}")
    print(f"💳 TRC20 Address: {TRC20_ADDRESS}")
    print(f"📊 Health Check: http://localhost:5000/health")
    print("=" * 80)
    print("✅ Features:")
    print("   - Multi-language (Persian/English)")
    print("   - TRC20 Payment System")
    print("   - Referral Commission (7%)")
    print("   - Auto-restore after crash")
    print("   - Max 3 bots per subscription")
    print("   - Persistent state storage")
    print("   - Auto-backup every hour")
    print("=" * 80)
    print("✅ Bot is running...")
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            logger.error(f"Polling error: {e}")
            time.sleep(5)