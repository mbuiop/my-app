#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
═══════════════════════════════════════════════════════════════════════════════
🚀 ربات مادر نهایی - نسخه 100.2 Ultimate Enterprise
⚡ پشتیباز از میلیون‌ها کاربر - معماری میکروسرویس کامل
🌐 پنل مدیریت فقط فارسی - پیام‌های کاربران چندزبانه
💎 سیستم کمیسیون دقیق رفرال
🤖 محدودیت ۳ ربات در هر اشتراک (قابل تنظیم)
🔒 بازیابی خودکار پس از خرابی سرور
🖥️ مدیریت چند سرور - اضافه کردن سرور جدید به ماشین‌ها
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
import paramiko
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
    'SERVER_SCRIPTS': os.path.join(BASE_DIR, "server_scripts")
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
    'max_users_capacity': 10000,
    'capacity_warning_message': "⚠️ ظرفیت ربات تکمیل شده است! لطفاً وارد ربات جدید شوید: @NEW_BOT",
    'new_bot_link': "@NEW_BOT",
    'guide_text_fa': "📚 راهنمای استفاده\n\n1️⃣ برای ساخت ربات، فایل .py یا .zip خود را ارسال کنید\n2️⃣ پس از پرداخت اشتراک ماهیانه، می‌توانید ربات بسازید\n3️⃣ هر کاربر می‌تواند تا ۳ ربات بسازد\n4️⃣ با دعوت دوستان، ۷٪ کمیسیون دریافت کنید\n5️⃣ پس از رسیدن به ۲ میلیون تومان، می‌توانید برداشت کنید",
    'guide_text_en': "📚 User Guide\n\n1️⃣ Send your .py or .zip file\n2️⃣ After subscription payment, you can build bots\n3️⃣ Each user can build up to 3 bots\n4️⃣ Invite friends and get 7% commission\n5️⃣ Withdraw after reaching 2,000,000 Toman",
    'welcome_text_fa': "🚀 خوش آمدید {name}!\nبه ربات سازنده ربات خوش آمدید.",
    'welcome_text_en': "🚀 Welcome {name}!\nWelcome to the bot builder bot.",
    'subscription_active_text_fa': "✅ اشتراک شما با موفقیت فعال شد!\nاکنون می‌توانید ربات خود را بسازید.",
    'subscription_active_text_en': "✅ Your subscription has been activated!\nYou can now build your bot.",
    'subscription_payment_text_fa': "💳 برای فعالسازی {price} را به آدرس زیر واریز:\n`{address}`\n🌐 شبکه: TRC20 (USDT)\n\n📸 پس از واریز، تصویر تراکنش را ارسال کنید",
    'subscription_payment_text_en': "💳 To activate, send {price} to:\n`{address}`\n🌐 Network: TRC20 (USDT)\n\n📸 Send transaction screenshot after payment",
    'max_builds_per_hour': 10,
    'max_concurrent_builds': 20,
    'rate_limit_per_second': 5,
    'health_check_interval': 30,
    'auto_scale_threshold': 80,
    'backup_interval': 3600,
    'state_save_interval': 60
}

# ==================== دکمه‌های منوی عمومی (دو زبانه) ====================
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

# ==================== دکمه‌های پنل مدیریت (فقط فارسی) ====================
ADMIN_BUTTONS = [
    '👑 پنل مدیریت',
    '📸 تایید فیش',
    '💰 تایید برداشت',
    '⚙️ تنظیمات سیستم',
    '📊 آمار کاربران',
    '🗑 حذف کاربران',
    '🗑 حذف ربات‌های کاربران',
    '📢 پیام همگانی',
    '🔍 بررسی ربات‌های کاربران',
    '💳 تنظیم آدرس کیف پول',
    '📝 عوض کردن متن راهنما',
    '👋 عوض کردن متن خوش آمد گویی',
    '✅ عوض کردن متن فعالسازی اشتراک',
    '💸 عوض کردن متن خرید اشتراک',
    '🔄 ریستارت ربات‌های مرده',
    '🐛 مدیریت خطاهای ربات',
    '⚙️ تنظیم ظرفیت کاربران',
    '🖥️ مدیریت ماشین‌ها',
    '➕ اضافه کردن سرور جدید',
    '🔙 بازگشت به منوی اصلی'
]

# ==================== متن‌های چند زبانه ====================
TEXTS = {
    'fa': {
        'welcome': "🚀 خوش آمدید {name}!",
        'subscription_active': "✅ اشتراک فعال",
        'subscription_inactive': "❌ اشتراک غیرفعال",
        'bots_remaining': "🤖 ربات‌های باقیمانده: {remaining}/{max}",
        'deposit_address': "💳 آدرس واریز:\n`{address}`\n🏦 شبکه: کارت به کارت",
        'deposit_address_trc20': "💳 آدرس واریز TRC20:\n`{address}`\n🌐 شبکه: TRC20 (USDT)",
        'send_receipt': "📸 لطفاً تصویر تراکنش را ارسال کنید",
        'receipt_received': "✅ تصویر دریافت شد، در انتظار تایید",
        'commission_added': "🎉 کمیسیون {amount:,} تومان به کیف پول شما اضافه شد",
        'bot_limit_reached': "❌ به حداکثر مجاز {max} ربات رسیده‌اید",
        'build_guide': "📚 راهنمای ساخت ربات\n\n1️⃣ فایل .py یا .zip خود را ارسال کنید\n2️⃣ می‌توانید پوشه‌بندی دلخواه داشته باشید\n3️⃣ منتظر بمانید تا ساخته شود\n4️⃣ ربات شما آماده است!",
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
        'payment_guide_fa': "💳 برای فعالسازی {price} را به کارت زیر واریز:\n`{card}`\n👤 {holder}\n🏦 {bank}\n\n📸 پس از واریز، تصویر تراکنش را ارسال کنید",
        'payment_guide_en': "💳 To activate, send {price} to TRC20 address:\n`{address}`\n🌐 Network: TRC20 (USDT)\n\n📸 Send transaction screenshot after payment",
        'receipt_pending': "⏳ فیش قبلی در انتظار تایید است",
        'send_file': "📤 فایل `.py` یا `.zip` خود را ارسال کنید\n💡 می‌توانید پوشه‌بندی دلخواه داشته باشید",
        'capacity_full': "⚠️ ظرفیت ربات تکمیل شده است! لطفاً وارد ربات جدید شوید: {link}",
        'language_changed': "✅ زبان به فارسی تغییر کرد",
        'language_changed_en': "✅ Language changed to English"
    },
    'en': {
        'welcome': "🚀 Welcome {name}!",
        'subscription_active': "✅ Subscription Active",
        'subscription_inactive': "❌ Subscription Inactive",
        'bots_remaining': "🤖 Bots remaining: {remaining}/{max}",
        'deposit_address': "💳 Deposit Address:\n`{address}`\n🌐 Network: TRC20 (USDT)",
        'deposit_address_trc20': "💳 TRC20 Deposit Address:\n`{address}`\n🌐 Network: TRC20 (USDT)",
        'send_receipt': "📸 Please send your transaction screenshot",
        'receipt_received': "✅ Receipt received, pending approval",
        'commission_added': "🎉 Commission {amount:,} Toman added to your wallet",
        'bot_limit_reached': "❌ You have reached the maximum of {max} bots",
        'build_guide': "📚 Bot Building Guide\n\n1️⃣ Send your .py or .zip file\n2️⃣ You can have custom folder structure\n3️⃣ Wait for it to be built\n4️⃣ Your bot is ready!",
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
        'payment_guide_fa': "💳 To activate, send {price} to:\n`{address}`\n🌐 Network: TRC20 (USDT)\n\n📸 Send transaction screenshot after payment",
        'payment_guide_en': "💳 To activate, send {price} to TRC20 address:\n`{address}`\n🌐 Network: TRC20 (USDT)\n\n📸 Send transaction screenshot after payment",
        'receipt_pending': "⏳ Previous receipt pending approval",
        'send_file': "📤 Send your `.py` or `.zip` file\n💡 You can have custom folder structure",
        'capacity_full': "⚠️ Bot capacity is full! Please join new bot: {link}",
        'language_changed': "✅ Language changed to Persian",
        'language_changed_en': "✅ زبان به انگلیسی تغییر کرد"
    }
}

# ==================== دیتابیس ====================
class Database:
    def __init__(self):
        self.db_type = "sqlite"
        self.pool = None
        self.conn = None
        self._connect()
        self._init_tables()
    
    def _connect(self):
        # اول سعی کن PostgreSQL وصل بشی
        try:
            self.pool = SimpleConnectionPool(
                minconn=1,
                maxconn=50,
                host="localhost",  # اینارو بعدا عوض کن
                port=5432,
                database="motherbot",
                user="postgres",
                password="your_password"
            )
            self.db_type = "postgres"
            print("✅ PostgreSQL connected")
            return
        except:
            print("⚠️ PostgreSQL not available, using SQLite")
        
        # اگه نشد SQLite
        db_path = os.path.join(DIRS['DB'], 'mother_bot.db')
        os.makedirs(DIRS['DB'], exist_ok=True)
        self.conn = sqlite3.connect(db_path, timeout=60, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA cache_size=-500000")
        self.db_type = "sqlite"
        print("✅ SQLite connected")
    
    def execute(self, query, params=()):
        if self.db_type == "postgres":
            # PostgreSQL
            conn = self.pool.getconn()
            try:
                pg_query = query.replace('?', '%s')
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(pg_query, params)
                    if query.strip().upper().startswith('SELECT'):
                        return [dict(row) for row in cur.fetchall()]
                    conn.commit()
                    return []
            finally:
                self.pool.putconn(conn)
        else:
            # SQLite
            if params:
                cursor = self.conn.execute(query, params)
            else:
                cursor = self.conn.execute(query)
            self.conn.commit()
            if query.strip().upper().startswith('SELECT'):
                return [dict(row) for row in cursor.fetchall()]
            return []
    
    def _init_tables(self):
        # جدول users
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
        
        # جدول bots
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
                join_block_message TEXT,
                health_status TEXT DEFAULT 'healthy',
                last_health_check TIMESTAMP,
                restart_count INTEGER DEFAULT 0,
                error_message TEXT
            )
        ''')
        
        # جدول machines
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
                is_local INTEGER DEFAULT 1
            )
        ''')
        
        # جدول receipts
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
        
        # جدول withdraw_requests
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
        
        # جدول commissions
        self.execute('''
            CREATE TABLE IF NOT EXISTS commissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                from_user INTEGER,
                amount INTEGER,
                reason TEXT,
                created_at TIMESTAMP,
                paid INTEGER DEFAULT 0
            )
        ''')
        
        # جدول errors
        self.execute('''
            CREATE TABLE IF NOT EXISTS errors (
                id TEXT PRIMARY KEY,
                type TEXT,
                message TEXT,
                user_id INTEGER,
                bot_id TEXT,
                timestamp TIMESTAMP,
                resolved INTEGER DEFAULT 0,
                stack_trace TEXT
            )
        ''')
        
        # جدول system_settings
        self.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP
            )
        ''')
        
        # جدول daily_stats
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
        
        # جدول remote_servers
        self.execute('''
            CREATE TABLE IF NOT EXISTS remote_servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                ip TEXT,
                port INTEGER DEFAULT 22,
                username TEXT,
                password TEXT,
                status TEXT DEFAULT 'pending',
                machine_id INTEGER,
                created_at TIMESTAMP
            )
        ''')
        
        # تنظیمات پیش‌فرض
        for key, value in DEFAULT_SETTINGS.items():
            self.execute('''
                INSERT OR IGNORE INTO system_settings (key, value, updated_at) 
                VALUES (?, ?, ?)
            ''', (key, str(value), datetime.now().isoformat()))
        
        # ماشین محلی
        existing = self.execute("SELECT COUNT(*) as count FROM machines WHERE is_local = 1")
        if existing and existing[0]['count'] == 0:
            self.execute('''
                INSERT INTO machines (id, name, status, max_bots, max_memory, created_at, is_local)
                VALUES (1, 'سرور اصلی', 'active', 5000, 256000, ?, 1)
            ''', (datetime.now().isoformat(),))
    
    def encrypt_token(self, token):
        return token
    
    def decrypt_token(self, encrypted_token):
        return encrypted_token

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
                   'backup_interval', 'state_save_interval', 'max_users_capacity']:
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
    
    # بررسی ظرفیت
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
    
    return True, "ok"

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
    
    # ارسال پیام فعالسازی به زبان کاربر
    lang = get_user_language(user_id)
    if lang == 'fa':
        active_text = get_setting('subscription_active_text_fa')
    else:
        active_text = get_setting('subscription_active_text_en')
    
    try:
        bot.send_message(user_id, active_text)
    except:
        pass
    
    # اضافه کردن کمیسیون به معرف
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

def add_bot(user_id, bot_id, token, name, username, file_path, pid=None, machine_id=None):
    now = datetime.now().isoformat()
    db.execute('''
        INSERT INTO bots 
        (id, user_id, token, name, username, file_path, pid, machine_id, status, created_at, last_active, join_enabled, join_block_message, health_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'running', ?, ?, 1, '🚫 سرور در حال حاضر پر است. لطفاً بعداً تلاش کنید.', 'healthy')
    ''', (bot_id, user_id, token, name, username, file_path, pid, machine_id, now, now))
    db.execute('UPDATE users SET bots_count = bots_count + 1 WHERE user_id = ?', (user_id,))
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
                
                remaining = get_remaining_bots(build_data['user_id'])
                success_text = get_text(build_data['user_id'], 'build_success', 
                                       name=build_data['bot_info']['first_name'], 
                                       remaining=remaining)
                temp_bot.edit_message_text(success_text, build_item['chat_id'], build_item['message_id'])
            else:
                error_msg = result.get('error', 'مشخص نشده')
                temp_bot.edit_message_text(
                    get_text(build_data['user_id'], 'build_failed', error=error_msg),
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
    
    def get_queue_length(self):
        return self.queue.qsize()

# ==================== مدیریت ماشین‌ها ====================
# ======================== ماشین‌ها ========================
class MachineManager:
    def __init__(self):
        self.port_counter = 8000
        self.processes = {}
        self.lock = threading.RLock()
        self._restore_bots_after_crash()

    def _restore_bots_after_crash(self):
        """بازیابی ربات‌ها پس از کرش سرور"""
        try:
            logger.info("🔄 Checking for bots to restore...")
            running_bots = db.execute('SELECT id, token, file_path, name FROM bots WHERE status = "running"')
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
                        logger.info(f"✅ Restored bot: {bot_rec['name']}")
                    else:
                        db.execute('UPDATE bots SET status = "stopped" WHERE id = ?', (bot_id,))
            logger.info(f"✅ Restored {restored} bots after crash")
        except Exception as e:
            logger.error(f"Bot restoration failed: {e}")
    
    def get_available_machine(self):
        """دریافت بهترین ماشین با الگوریتم هوشمند (CPU + RAM + بار)"""
        machines = db.execute("""
            SELECT id, current_bots, max_bots, 
                   cpu_usage, memory_used,
                   (current_bots * 1.0 / max_bots) as load_ratio
            FROM machines 
            WHERE status = 'active' 
            AND current_bots < max_bots
            ORDER BY 
                cpu_usage ASC,
                memory_used ASC,
                load_ratio ASC
            LIMIT 1
        """)
        
        if machines:
            return machines[0]['id']
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
    
    def restart_all_dead_bots(self):
        """ریستارت کردن تمام ربات‌های مرده"""
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
        
        avg_cpu = sum(m.get('cpu_usage', 0) for m in machine_list) / max(len(machine_list), 1)
        avg_mem = sum(m.get('memory_used', 0) for m in machine_list) / max(len(machine_list), 1)
        
        return {
            'total': len(machine_list),
            'total_bots': total_bots,
            'total_capacity': total_capacity,
            'available': total_capacity - total_bots,
            'usage_percent': (total_bots / total_capacity) * 100 if total_capacity > 0 else 0,
            'avg_cpu': round(avg_cpu, 1),
            'avg_memory': round(avg_mem, 1)
        }
    
    def update_machine_capacity(self, machine_id, max_bots):
        db.execute("UPDATE machines SET max_bots = ? WHERE id = ?", (max_bots, machine_id))
        return True
            
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
    
    def restart_all_dead_bots(self):
        """ریستارت کردن تمام ربات‌های مرده"""
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
            'usage_percent': (total_bots / total_capacity) * 100 if total_capacity > 0 else 0
        }
    
    def update_machine_capacity(self, machine_id, max_bots):
        """به‌روزرسانی ظرفیت ماشین"""
        db.execute("UPDATE machines SET max_bots = ? WHERE id = ?", (max_bots, machine_id))
        return True

# ==================== مدیریت سرورهای از راه دور ====================
class RemoteServerManager:
    def __init__(self):
        self.servers = {}
    
    def add_server(self, name, ip, username, password, port=22, machine_id=None):
        """اضافه کردن سرور جدید"""
        # تست اتصال
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, port=port, username=username, password=password, timeout=10)
            ssh.close()
            
            # ذخیره در دیتابیس
            db.execute('''
                INSERT INTO remote_servers (name, ip, port, username, password, machine_id, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'connected', ?)
            ''', (name, ip, port, username, password, machine_id, datetime.now().isoformat()))
            
            # به‌روزرسانی ماشین مربوطه
            if machine_id:
                db.execute('''
                    UPDATE machines SET ip = ?, username = ?, password = ?, is_local = 0 WHERE id = ?
                ''', (ip, username, password, machine_id))
            
            return True, "اتصال با موفقیت برقرار شد"
        except Exception as e:
            return False, f"خطا در اتصال: {str(e)}"
    
    def deploy_to_server(self, machine_id, bot_code, bot_id):
        """استقرار ربات روی سرور از راه دور"""
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
            
            # ایجاد دایرکتوری
            sftp = ssh.open_sftp()
            remote_dir = f"/root/mother_bot/machines/machine_{machine_id:03d}/{bot_id}"
            try:
                sftp.mkdir(remote_dir)
            except:
                pass
            
            # آپلود فایل
            remote_file = f"{remote_dir}/bot.py"
            with sftp.open(remote_file, 'w') as f:
                f.write(bot_code)
            
            sftp.close()
            
            # اجرای ربات
            cmd = f"cd {remote_dir} && nohup python3 bot.py > /dev/null 2>&1 &"
            ssh.exec_command(cmd)
            ssh.close()
            
            return True, "ربات با موفقیت روی سرور مستقر شد"
        except Exception as e:
            return False, f"خطا در استقرار: {str(e)}"

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
                    token = bot_rec['token']
                    
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
                
                token = bot_rec['token']
                if token:
                    result = machine_manager.run_bot(bot_id, code, token)
                    if result['success']:
                        db.execute('UPDATE bots SET status = "running", machine_id = ?, pid = ?, last_active = ? WHERE id = ?',
                                  (result['machine_id'], result['pid'], datetime.now().isoformat(), bot_id))
                        logger.info(f"✅ Auto-restarted bot {bot_id}")
            except Exception as e:
                logger.error(f"Failed to restart bot {bot_id}: {e}")
                db.execute('UPDATE bots SET status = "error", error_message = ? WHERE id = ?', (str(e)[:200], bot_id))

# ==================== ربات تلگرام ====================
bot = telebot.TeleBot(BOT_TOKEN)
bot.delete_webhook()

# ایجاد نمونه‌ها
machine_manager = MachineManager()
remote_manager = RemoteServerManager()
build_queue = BuildQueue()
health_checker = HealthChecker()

# ==================== منوی اصلی ====================
def get_main_menu(user_id):
    """دریافت منوی اصلی بر اساس زبان کاربر (پنل مدیریت فقط فارسی)"""
    user = get_user(user_id)
    lang = user['language'] if user else 'fa'
    is_admin = user_id in ADMIN_IDS
    
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    
    if lang == 'fa':
        buttons = MENU_BUTTONS_FA.copy()
    else:
        buttons = MENU_BUTTONS_EN.copy()
    
    # اضافه کردن دکمه‌های مدیریت (فقط فارسی)
    if is_admin:
        for btn in ADMIN_BUTTONS:
            buttons.append(btn)
    
    markup.add(*buttons)
    return markup

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
    
    result, msg = create_user(user_id, username, first_name, message.from_user.last_name or "", referred_by, preferred_lang)
    
    if not result:
        if msg == "capacity_full":
            capacity_msg = get_setting('capacity_warning_message')
            bot.send_message(message.chat.id, capacity_msg)
            return
    
    user = get_user(user_id)
    referral_link = f"https://t.me/{BOT_USERNAME}?start={user['referral_code']}"
    remaining_bots = get_remaining_bots(user_id)
    max_bots = get_setting('max_bots_per_subscription')
    is_subscribed = check_subscription(user_id)
    lang = user['language']
    
    # متن خوش آمدگویی از تنظیمات
    if lang == 'fa':
        welcome_text = get_setting('welcome_text_fa').format(name=first_name)
    else:
        welcome_text = get_setting('welcome_text_en').format(name=first_name)
    
    if lang == 'fa':
        text = (f"{welcome_text}\n\n"
                f"👤 شناسه: `{user_id}`\n"
                f"🎁 کد معرف: `{user['referral_code']}`\n"
                f"🔗 لینک دعوت: `{referral_link}`\n"
                f"📊 دعوت‌ها: {user['referrals_count']}\n"
                f"💰 موجودی: {user['wallet_balance']:,} تومان\n"
                f"💳 وضعیت: {'✅ فعال' if is_subscribed else '❌ غیرفعال'}\n"
                f"🤖 ربات‌های باقیمانده: {remaining_bots}/{max_bots}")
    else:
        text = (f"{welcome_text}\n\n"
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

# ==================== زبان (دو زبانه) ====================
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
    lang = call.data.replace('lang_', '')
    user_id = call.from_user.id
    
    db.execute("UPDATE users SET language = ? WHERE user_id = ?", (lang, user_id))
    
    msg = "✅ Language set to English" if lang == 'en' else "✅ زبان به فارسی تغییر کرد"
    bot.answer_callback_query(call.id, msg)
    
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    
    success_msg = get_text(user_id, 'language_changed_en' if lang == 'en' else 'language_changed')
    new_menu = get_main_menu(user_id)
    bot.send_message(call.message.chat.id, success_msg, reply_markup=new_menu)

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
        # فارسی: کارت به کارت
        text = (f"💰 **کیف پول و اشتراک**\n\n"
                f"👤 {user['first_name']}\n"
                f"💳 وضعیت: {'✅ فعال' if is_subscribed else '❌ غیرفعال'}\n"
                f"📅 انقضا: {expiry}\n"
                f"💰 موجودی: {user['wallet_balance']:,} تومان\n"
                f"👥 دعوت‌ها: {user['referrals_count']}\n"
                f"🤖 ربات‌های باقیمانده: {remaining_bots}/{max_bots}\n\n")
        
        payment_text = get_setting('subscription_payment_text_fa').format(
            price=get_setting('subscription_price_str'),
            address=get_setting('trc20_address')
        )
        text += payment_text
    else:
        # انگلیسی: TRC20
        text = (f"💰 **Wallet & Subscription**\n\n"
                f"👤 {user['first_name']}\n"
                f"💳 Status: {'✅ Active' if is_subscribed else '❌ Inactive'}\n"
                f"📅 Expiry: {expiry}\n"
                f"💰 Balance: {user['wallet_balance']:,} Toman\n"
                f"👥 Referrals: {user['referrals_count']}\n"
                f"🤖 Remaining Bots: {remaining_bots}/{max_bots}\n\n")
        
        payment_text = get_setting('subscription_payment_text_en').format(
            price=get_setting('subscription_price_usd'),
            address=get_setting('trc20_address')
        )
        text += payment_text
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(get_text(user_id, 'copy_link'), callback_data="copy_address"))
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "copy_address")
def copy_address(call):
    user_id = call.from_user.id
    lang = get_user_language(user_id)
    if lang == 'fa':
        address = get_setting('card_number_display')
    else:
        address = get_setting('trc20_address')
    bot.answer_callback_query(call.id, f"✅ {address}", show_alert=True)

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
                    caption = f"📸 فیش جدید\n👤 کاربر: {message.from_user.first_name}\n🆔 ID: {user_id}\n💰 مبلغ: {get_setting('subscription_price_str')}\n🆔 کد: {tx_hash}"
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

# ==================== ساخت ربات جدید (با پشتیبانی از پوشه) ====================
@bot.message_handler(func=lambda m: m.text in ['🤖 ساخت ربات جدید', '🤖 New Bot'])
def new_bot(message):
    user_id = message.from_user.id
    lang = get_user_language(user_id)
    
    can_create, reason = can_create_bot(user_id)
    
    if not can_create:
        if reason == "no_subscription":
            text = "❌ You need an active subscription first!" if lang == 'en' else "❌ ابتدا باید اشتراک فعال کنید!"
        else:
            text = f"❌ You have reached the maximum of {get_setting('max_bots_per_subscription')} bots" if lang == 'en' else f"❌ به حداکثر {get_setting('max_bots_per_subscription')} ربات رسیده‌اید"
        
        bot.send_message(message.chat.id, text)
        return
    
    bot.send_message(message.chat.id, get_text(user_id, 'send_file'))

def extract_zip_with_structure(zip_path, extract_to):
    """استخراج فایل zip با حفظ ساختار پوشه‌ها"""
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    
    # پیدا کردن فایل اصلی پایتون
    main_code = ""
    main_file = None
    
    for root, dirs, files in os.walk(extract_to):
        for file in files:
            if file.endswith('.py'):
                # اولویت با فایل‌های نام‌گذاری شده خاص
                if file in ['main.py', 'bot.py', 'app.py', 'run.py']:
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
        folder_path = None
        
        if file_name.endswith('.zip'):
            extract_dir = os.path.join(DIRS['TEMP'], f"extract_{user_id}_{int(time.time())}")
            os.makedirs(extract_dir, exist_ok=True)
            main_code, folder_path = extract_zip_with_structure(file_path, extract_dir)
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
        
        # ذخیره مسیر پوشه اگر zip بوده
        if folder_path:
            final_folder = os.path.join(DIRS['FILES'], str(user_id), f"bot_{bot_id}")
            shutil.move(folder_path, final_folder)
            folder_path = final_folder
        
        build_data = {
            'bot_id': bot_id,
            'user_id': user_id,
            'token': token,
            'bot_info': bot_info,
            'file_path': file_path,
            'folder_path': folder_path,
            'main_code': main_code,
            'chat_id': message.chat.id,
            'message_id': status_msg.message_id
        }
        
        build_queue.add_build(user_id, file_path, file_name, message.chat.id, status_msg.message_id, build_data)
        
    except Exception as e:
        bot.edit_message_text(get_text(user_id, 'error', error=str(e)[:100]), 
                             message.chat.id, status_msg.message_id)
        log_error("build_error", str(e), user_id)

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
        if b.get('error_message'):
            text += f"\n⚠️ خطا: {b['error_message'][:50]}"
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
    
    if status.get('running'):
        if machine_manager.stop_bot(bot_id):
            bot.answer_callback_query(call.id, get_text(call.from_user.id, 'stopped'))
        else:
            bot.answer_callback_query(call.id, get_text(call.from_user.id, 'error', error="Stop failed"))
    else:
        if os.path.exists(bot_rec['file_path']):
            with open(bot_rec['file_path'], 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
            token = bot_rec['token']
            if token:
                result = machine_manager.run_bot(bot_id, code, token)
                if result['success']:
                    db.execute("UPDATE bots SET machine_id = ?, pid = ?, status = 'running', error_message = NULL WHERE id = ?",
                              (result['machine_id'], result['pid'], bot_id))
                    bot.answer_callback_query(call.id, get_text(call.from_user.id, 'started'))
                else:
                    bot.answer_callback_query(call.id, get_text(call.from_user.id, 'error', error=result.get('error', 'Unknown')))
            else:
                bot.answer_callback_query(call.id, get_text(call.from_user.id, 'error', error="Token error"))
        else:
            bot.answer_callback_query(call.id, get_text(call.from_user.id, 'error', error="File not found"))

# ==================== حذف ربات ====================
@bot.message_handler(func=lambda m: m.text in ['🗑 حذف ربات', '🗑 Delete Bot'])
def delete_prompt(message):
    user_id = message.from_user.id
    
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

@bot.message_handler(func=lambda m: m.text in ['📦 کتابخانه', '📦 Library'])
def library_menu(message):
    lang = get_user_language(message.from_user.id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    for name, lib in list(POPULAR_LIBRARIES.items())[:20]:
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
    
    if lang == 'fa':
        guide_text = get_setting('guide_text_fa')
    else:
        guide_text = get_setting('guide_text_en')
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
            bot.send_message(admin_id, f"💰 درخواست برداشت\n👤 {user['first_name']}\n🆔 {user['user_id']}\n💰 {amount:,} تومان\n💳 {address}")
        except:
            pass

# ==================== پنل مدیریت (فقط فارسی - تمام دکمه‌ها) ====================

@bot.message_handler(func=lambda m: m.text == '👑 پنل مدیریت')
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        '📸 تایید فیش',
        '💰 تایید برداشت',
        '⚙️ تنظیمات سیستم',
        '📊 آمار کاربران',
        '🗑 حذف کاربران',
        '🗑 حذف ربات‌های کاربران',
        '📢 پیام همگانی',
        '🔍 بررسی ربات‌های کاربران',
        '💳 تنظیم آدرس کیف پول',
        '📝 عوض کردن متن راهنما',
        '👋 عوض کردن متن خوش آمد گویی',
        '✅ عوض کردن متن فعالسازی اشتراک',
        '💸 عوض کردن متن خرید اشتراک',
        '🔄 ریستارت ربات‌های مرده',
        '🐛 مدیریت خطاهای ربات',
        '⚙️ تنظیم ظرفیت کاربران',
        '🖥️ مدیریت ماشین‌ها',
        '➕ اضافه کردن سرور جدید',
        '🔙 بازگشت به منوی اصلی'
    ]
    markup.add(*buttons)
    
    bot.send_message(message.chat.id, "👑 **پنل مدیریت** - لطفاً یکی از گزینه‌های زیر را انتخاب کنید:", 
                    parse_mode='Markdown', reply_markup=markup)

# ==================== تایید فیش ====================
@bot.message_handler(func=lambda m: m.text == '📸 تایید فیش')
def admin_receipts(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    receipts = db.execute('SELECT * FROM receipts WHERE status = "pending" ORDER BY created_at')
    if not receipts:
        bot.send_message(message.chat.id, "✅ هیچ فیش در انتظار تاییدی وجود ندارد")
        return
    
    for r in receipts:
        user = get_user(r['user_id'])
        text = f"📸 **فیش جدید**\n👤 کاربر: {user['first_name'] if user else 'نامشخص'}\n🆔 آیدی: {r['user_id']}\n💰 مبلغ: {r['amount']:,} تومان\n🆔 کد: {r['tx_hash']}"
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_receipt_{r['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"reject_receipt_{r['id']}")
        )
        if os.path.exists(r['receipt_path']):
            with open(r['receipt_path'], 'rb') as f:
                bot.send_photo(message.chat.id, f, caption=text, parse_mode='Markdown', reply_markup=markup)
        else:
            bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

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
        
        bot.answer_callback_query(call.id, "✅ فیش تایید شد و اشتراک فعال گردید")
        bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_receipt_'))
def reject_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    rid = int(call.data.replace('reject_receipt_', ''))
    db.execute('UPDATE receipts SET status = "rejected", reviewed_by = ?, reviewed_at = ? WHERE id = ?',
              (call.from_user.id, datetime.now().isoformat(), rid))
    bot.answer_callback_query(call.id, "❌ فیش رد شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== تایید برداشت ====================
@bot.message_handler(func=lambda m: m.text == '💰 تایید برداشت')
def admin_withdraws(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    withdraws = db.execute('SELECT * FROM withdraw_requests WHERE status = "pending" ORDER BY created_at')
    if not withdraws:
        bot.send_message(message.chat.id, "✅ هیچ درخواست برداشتی در انتظار تایید نیست")
        return
    
    for w in withdraws:
        user = get_user(w['user_id'])
        text = f"💰 **درخواست برداشت**\n👤 کاربر: {user['first_name'] if user else 'نامشخص'}\n🆔 آیدی: {w['user_id']}\n💰 مبلغ: {w['amount']:,} تومان\n💳 آدرس: {w['address']}"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ تایید واریز شد", callback_data=f"approve_withdraw_{w['id']}"))
        bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_withdraw_'))
def approve_withdraw(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    wid = int(call.data.replace('approve_withdraw_', ''))
    w = db.execute('SELECT user_id, amount FROM withdraw_requests WHERE id = ?', (wid,))
    if w:
        db.execute('UPDATE withdraw_requests SET status = "approved", processed_at = ? WHERE id = ?',
                  (datetime.now().isoformat(), wid))
        bot.answer_callback_query(call.id, "✅ برداشت تایید شد")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        
        try:
            bot.send_message(w[0]['user_id'], f"✅ درخواست برداشت {w[0]['amount']:,} تومان شما تایید و واریز شد.")
        except:
            pass

# ==================== آمار کاربران ====================
@bot.message_handler(func=lambda m: m.text == '📊 آمار کاربران')
def admin_user_stats(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    users_count = db.execute('SELECT COUNT(*) as count FROM users')[0]['count']
    active_subs = db.execute('SELECT COUNT(*) as count FROM users WHERE subscription_status = "active"')[0]['count']
    banned_users = db.execute('SELECT COUNT(*) as count FROM users WHERE is_banned = 1')[0]['count']
    total_bots = db.execute('SELECT COUNT(*) as count FROM bots')[0]['count']
    running_bots = db.execute('SELECT COUNT(*) as count FROM bots WHERE status = "running"')[0]['count']
    total_wallet = db.execute('SELECT SUM(wallet_balance) as total FROM users')[0]['total'] or 0
    total_commission = db.execute('SELECT SUM(amount) as total FROM commissions')[0]['total'] or 0
    
    today = datetime.now().date().isoformat()
    daily = db.execute('SELECT * FROM daily_stats WHERE date = ?', (today,))
    
    text = (f"📊 **آمار کامل کاربران**\n\n"
            f"👥 کل کاربران: {users_count:,}\n"
            f"✅ اشتراک فعال: {active_subs:,}\n"
            f"🚫 کاربران مسدود: {banned_users:,}\n"
            f"🤖 کل ربات‌ها: {total_bots:,}\n"
            f"🟢 ربات فعال: {running_bots:,}\n"
            f"💰 کیف پول کل: {total_wallet:,} تومان\n"
            f"💎 کل کمیسیون پرداختی: {total_commission:,} تومان\n\n")
    
    if daily:
        d = daily[0]
        text += (f"📅 **آمار امروز**\n"
                f"👥 کاربران جدید: {d['new_users']}\n"
                f"🤖 ربات‌های جدید: {d['new_bots']}\n"
                f"✅ اشتراک‌های جدید: {d['new_subscriptions']}\n"
                f"💰 درآمد امروز: {d['total_revenue']:,} تومان")
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== حذف کاربران ====================
@bot.message_handler(func=lambda m: m.text == '🗑 حذف کاربران')
def admin_delete_user(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(message.chat.id, "🗑 آیدی عددی کاربر را برای حذف وارد کنید:")
    bot.register_next_step_handler(msg, process_admin_delete_user)

def process_admin_delete_user(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        uid = int(message.text.strip())
        user = get_user(uid)
        if user:
            # حذف تمام ربات‌های کاربر
            bots = get_user_bots(uid)
            for bot in bots:
                delete_bot(bot['id'], uid)
            
            db.execute('DELETE FROM users WHERE user_id = ?', (uid,))
            bot.reply_to(message, f"✅ کاربر {uid} و تمام ربات‌هایش حذف شد")
        else:
            bot.reply_to(message, "❌ کاربر یافت نشد")
    except:
        bot.reply_to(message, "❌ آیدی نامعتبر")

# ==================== حذف ربات‌های کاربران ====================
@bot.message_handler(func=lambda m: m.text == '🗑 حذف ربات‌های کاربران')
def admin_delete_user_bots(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(message.chat.id, "🗑 آیدی عددی کاربر را برای حذف تمام ربات‌هایش وارد کنید:")
    bot.register_next_step_handler(msg, process_delete_user_bots)

def process_delete_user_bots(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        uid = int(message.text.strip())
        user = get_user(uid)
        if user:
            bots = get_user_bots(uid)
            deleted = 0
            for bot in bots:
                if delete_bot(bot['id'], uid):
                    deleted += 1
            bot.reply_to(message, f"✅ {deleted} ربات از کاربر {uid} حذف شد")
        else:
            bot.reply_to(message, "❌ کاربر یافت نشد")
    except:
        bot.reply_to(message, "❌ آیدی نامعتبر")

# ==================== بررسی ربات‌های کاربران ====================
@bot.message_handler(func=lambda m: m.text == '🔍 بررسی ربات‌های کاربران')
def admin_check_user_bots(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(message.chat.id, "🔍 آیدی عددی کاربر را برای بررسی ربات‌هایش وارد کنید:")
    bot.register_next_step_handler(msg, process_check_user_bots)

def process_check_user_bots(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        uid = int(message.text.strip())
        user = get_user(uid)
        if user:
            bots = get_user_bots(uid)
            if not bots:
                bot.reply_to(message, f"📋 کاربر {uid} هیچ رباتی ندارد")
                return
            
            text = f"📋 **ربات‌های کاربر {user['first_name']} (آیدی: {uid})**\n\n"
            for b in bots:
                status = machine_manager.get_status(b['id'])
                status_emoji = "🟢" if status.get('running') else "🔴"
                text += f"{status_emoji} `{b['id'][:8]}...` - {b['name']}\n"
                if b.get('error_message'):
                    text += f"   ⚠️ خطا: {b['error_message'][:50]}\n"
            
            bot.reply_to(message, text, parse_mode='Markdown')
        else:
            bot.reply_to(message, "❌ کاربر یافت نشد")
    except:
        bot.reply_to(message, "❌ آیدی نامعتبر")

# ==================== تنظیم آدرس کیف پول ====================
@bot.message_handler(func=lambda m: m.text == '💳 تنظیم آدرس کیف پول')
def admin_set_wallet_address(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("💰 آدرس TRC20 (انگلیسی)", callback_data="set_trc20"),
        types.InlineKeyboardButton("🏦 شماره کارت (فارسی)", callback_data="set_card"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back_settings")
    )
    bot.send_message(message.chat.id, "💳 انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "set_trc20")
def set_trc20(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "💰 آدرس کیف پول TRC20 را وارد کنید:")
    bot.register_next_step_handler(msg, process_set_trc20)

def process_set_trc20(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    address = message.text.strip()
    update_setting('trc20_address', address)
    bot.reply_to(message, f"✅ آدرس TRC20 به {address} تغییر کرد")

@bot.callback_query_handler(func=lambda call: call.data == "set_card")
def set_card(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "🏦 شماره کارت (۱۶ رقمی) را وارد کنید:")
    bot.register_next_step_handler(msg, process_set_card)

def process_set_card(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    card = message.text.strip().replace(" ", "")
    display = ' '.join([card[i:i+4] for i in range(0, len(card), 4)])
    update_setting('card_number', card)
    update_setting('card_number_display', display)
    bot.reply_to(message, f"✅ شماره کارت به {display} تغییر کرد")

# ==================== عوض کردن متن راهنما ====================
@bot.message_handler(func=lambda m: m.text == '📝 عوض کردن متن راهنما')
def admin_set_guide(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🇮🇷 فارسی", callback_data="set_guide_fa"),
        types.InlineKeyboardButton("🇬🇧 English", callback_data="set_guide_en")
    )
    bot.send_message(message.chat.id, "📝 انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "set_guide_fa")
def set_guide_fa(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "📝 متن راهنمای فارسی را وارد کنید:")
    bot.register_next_step_handler(msg, process_set_guide_fa)

def process_set_guide_fa(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    update_setting('guide_text_fa', message.text)
    bot.reply_to(message, "✅ متن راهنمای فارسی ذخیره شد")

@bot.callback_query_handler(func=lambda call: call.data == "set_guide_en")
def set_guide_en(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "📝 Enter English guide text:")
    bot.register_next_step_handler(msg, process_set_guide_en)

def process_set_guide_en(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    update_setting('guide_text_en', message.text)
    bot.reply_to(message, "✅ English guide saved")

# ==================== عوض کردن متن خوش آمد گویی ====================
@bot.message_handler(func=lambda m: m.text == '👋 عوض کردن متن خوش آمد گویی')
def admin_set_welcome(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🇮🇷 فارسی", callback_data="set_welcome_fa"),
        types.InlineKeyboardButton("🇬🇧 English", callback_data="set_welcome_en")
    )
    bot.send_message(message.chat.id, "👋 انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "set_welcome_fa")
def set_welcome_fa(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "👋 متن خوش آمد گویی فارسی (از {name} استفاده کنید):")
    bot.register_next_step_handler(msg, process_set_welcome_fa)

def process_set_welcome_fa(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    update_setting('welcome_text_fa', message.text)
    bot.reply_to(message, "✅ متن خوش آمد گویی فارسی ذخیره شد")

@bot.callback_query_handler(func=lambda call: call.data == "set_welcome_en")
def set_welcome_en(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "👋 Enter English welcome text (use {name}):")
    bot.register_next_step_handler(msg, process_set_welcome_en)

def process_set_welcome_en(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    update_setting('welcome_text_en', message.text)
    bot.reply_to(message, "✅ English welcome text saved")

# ==================== عوض کردن متن فعالسازی اشتراک ====================
@bot.message_handler(func=lambda m: m.text == '✅ عوض کردن متن فعالسازی اشتراک')
def admin_set_active_text(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🇮🇷 فارسی", callback_data="set_active_fa"),
        types.InlineKeyboardButton("🇬🇧 English", callback_data="set_active_en")
    )
    bot.send_message(message.chat.id, "✅ انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "set_active_fa")
def set_active_fa(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "✅ متن فعالسازی اشتراک فارسی:")
    bot.register_next_step_handler(msg, process_set_active_fa)

def process_set_active_fa(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    update_setting('subscription_active_text_fa', message.text)
    bot.reply_to(message, "✅ متن فعالسازی اشتراک فارسی ذخیره شد")

@bot.callback_query_handler(func=lambda call: call.data == "set_active_en")
def set_active_en(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "✅ Enter English subscription activation text:")
    bot.register_next_step_handler(msg, process_set_active_en)

def process_set_active_en(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    update_setting('subscription_active_text_en', message.text)
    bot.reply_to(message, "✅ English subscription activation text saved")

# ==================== عوض کردن متن خرید اشتراک ====================
@bot.message_handler(func=lambda m: m.text == '💸 عوض کردن متن خرید اشتراک')
def admin_set_payment_text(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🇮🇷 فارسی (کارت به کارت)", callback_data="set_payment_fa"),
        types.InlineKeyboardButton("🇬🇧 English (TRC20)", callback_data="set_payment_en")
    )
    bot.send_message(message.chat.id, "💸 انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "set_payment_fa")
def set_payment_fa(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "💸 متن خرید اشتراک فارسی (از {price} و {address} استفاده کنید):")
    bot.register_next_step_handler(msg, process_set_payment_fa)

def process_set_payment_fa(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    update_setting('subscription_payment_text_fa', message.text)
    bot.reply_to(message, "✅ متن خرید اشتراک فارسی ذخیره شد")

@bot.callback_query_handler(func=lambda call: call.data == "set_payment_en")
def set_payment_en(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "💸 Enter English payment text (use {price} and {address}):")
    bot.register_next_step_handler(msg, process_set_payment_en)

def process_set_payment_en(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    update_setting('subscription_payment_text_en', message.text)
    bot.reply_to(message, "✅ English payment text saved")

# ==================== ریستارت ربات‌های مرده ====================
@bot.message_handler(func=lambda m: m.text == '🔄 ریستارت ربات‌های مرده')
def admin_restart_dead_bots(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    status_msg = bot.reply_to(message, "🔄 در حال بررسی و ریستارت ربات‌های مرده...")
    restarted = machine_manager.restart_all_dead_bots()
    bot.edit_message_text(f"✅ {restarted} ربات مرده با موفقیت ریستارت شدند", 
                         message.chat.id, status_msg.message_id)

# ==================== مدیریت خطاهای ربات ====================
@bot.message_handler(func=lambda m: m.text == '🐛 مدیریت خطاهای ربات')
def admin_errors(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    errors = db.execute('SELECT * FROM errors WHERE resolved = 0 ORDER BY timestamp DESC LIMIT 30')
    if not errors:
        bot.send_message(message.chat.id, "✅ هیچ خطای حل نشده‌ای وجود ندارد")
        return
    
    for e in errors:
        text = (f"🐛 **خطا**\n"
                f"نوع: {e['type']}\n"
                f"پیام: {e['message'][:150]}\n"
                f"زمان: {e['timestamp'][:16]}\n"
                f"کاربر: {e['user_id'] or 'نامشخص'}\n"
                f"ربات: {e['bot_id'] or 'نامشخص'}")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ علامت رفع شد", callback_data=f"resolve_error_{e['id']}"))
        bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('resolve_error_'))
def resolve_error(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    eid = call.data.replace('resolve_error_', '')
    db.execute('UPDATE errors SET resolved = 1 WHERE id = ?', (eid,))
    bot.answer_callback_query(call.id, "✅ خطا به عنوان رفع شده علامت خورد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== تنظیم ظرفیت کاربران ====================
@bot.message_handler(func=lambda m: m.text == '⚙️ تنظیم ظرفیت کاربران')
def admin_set_capacity(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    current = get_setting('max_users_capacity')
    msg = bot.send_message(message.chat.id, f"⚙️ ظرفیت فعلی: {current} کاربر\n\nحداکثر ظرفیت جدید را وارد کنید (عدد بین 100 تا 100000):")
    bot.register_next_step_handler(msg, process_set_capacity)

def process_set_capacity(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        capacity = int(message.text.strip())
        if 100 <= capacity <= 100000:
            update_setting('max_users_capacity', capacity)
            
            # به‌روزرسانی متن هشدار
            warning_text = get_setting('capacity_warning_message')
            bot.reply_to(message, f"✅ ظرفیت به {capacity} کاربر تغییر کرد")
            
            # نمایش ظرفیت فعلی
            current_users = db.execute('SELECT COUNT(*) as count FROM users')[0]['count']
            remaining = capacity - current_users
            bot.send_message(message.chat.id, f"📊 کاربران فعلی: {current_users}\n📊 ظرفیت خالی: {remaining}")
        else:
            bot.reply_to(message, "❌ عدد بین 100 تا 100000")
    except:
        bot.reply_to(message, "❌ عدد نامعتبر")

# ==================== مدیریت ماشین‌ها (با 5 دکمه) ====================
@bot.message_handler(func=lambda m: m.text == '🖥️ مدیریت ماشین‌ها')
def admin_machines(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📋 لیست ماشین‌ها", callback_data="machines_list"),
        types.InlineKeyboardButton("📈 افزایش ظرفیت ماشین", callback_data="machines_increase"),
        types.InlineKeyboardButton("📉 کاهش ظرفیت ماشین", callback_data="machines_decrease"),
        types.InlineKeyboardButton("🔄 ریستارت ماشین", callback_data="machines_restart"),
        types.InlineKeyboardButton("❌ غیرفعال کردن ماشین", callback_data="machines_disable"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back_machines")
    )
    bot.send_message(message.chat.id, "🖥️ **مدیریت ماشین‌ها** - انتخاب کنید:", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "machines_list")
def machines_list(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    machines = db.execute("SELECT * FROM machines ORDER BY id")
    text = "🖥️ **لیست ماشین‌ها**\n\n"
    for m in machines:
        usage = (m['current_bots'] / m['max_bots']) * 100 if m['max_bots'] > 0 else 0
        status_emoji = "🟢" if m['status'] == 'active' else "🔴"
        local_tag = "📍 محلی" if m.get('is_local', 1) == 1 else "🌐 از راه دور"
        text += f"{status_emoji} **{m['name']}** ({local_tag})\n"
        text += f"   └ ربات‌ها: {m['current_bots']}/{m['max_bots']} ({usage:.1f}%)\n"
        if m.get('ip'):
            text += f"   └ آدرس: {m['ip']}\n"
        text += "\n"
    
    machine_stats = machine_manager.get_stats()
    text += f"📊 **جمع کل:** {machine_stats['total_bots']}/{machine_stats['total_capacity']} ({machine_stats['usage_percent']:.1f}%)"
    
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "machines_increase")
def machines_increase(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    machines = db.execute("SELECT id, name, max_bots FROM machines WHERE status = 'active'")
    markup = types.InlineKeyboardMarkup(row_width=1)
    for m in machines:
        markup.add(types.InlineKeyboardButton(f"📈 {m['name']} (فعلی: {m['max_bots']})", callback_data=f"inc_machine_{m['id']}"))
    bot.send_message(call.message.chat.id, "📈 انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('inc_machine_'))
def inc_machine(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    machine_id = int(call.data.replace('inc_machine_', ''))
    msg = bot.send_message(call.message.chat.id, "📈 ظرفیت جدید (حداکثر 50000):")
    bot.register_next_step_handler(msg, lambda m: process_change_capacity(m, machine_id, 'inc'))

@bot.callback_query_handler(func=lambda call: call.data == "machines_decrease")
def machines_decrease(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    machines = db.execute("SELECT id, name, max_bots FROM machines WHERE status = 'active'")
    markup = types.InlineKeyboardMarkup(row_width=1)
    for m in machines:
        markup.add(types.InlineKeyboardButton(f"📉 {m['name']} (فعلی: {m['max_bots']})", callback_data=f"dec_machine_{m['id']}"))
    bot.send_message(call.message.chat.id, "📉 انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('dec_machine_'))
def dec_machine(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    machine_id = int(call.data.replace('dec_machine_', ''))
    msg = bot.send_message(call.message.chat.id, "📉 ظرفیت جدید (حداقل برابر با تعداد ربات‌های فعلی):")
    bot.register_next_step_handler(msg, lambda m: process_change_capacity(m, machine_id, 'dec'))

def process_change_capacity(message, machine_id, action):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        new_capacity = int(message.text.strip())
        machine = db.execute("SELECT * FROM machines WHERE id = ?", (machine_id,))
        if machine:
            machine = machine[0]
            current_bots = machine['current_bots']
            
            if action == 'dec' and new_capacity < current_bots:
                bot.reply_to(message, f"❌ ظرفیت نمی‌تواند کمتر از {current_bots} (تعداد ربات‌های فعلی) باشد")
                return
            
            if 100 <= new_capacity <= 50000:
                machine_manager.update_machine_capacity(machine_id, new_capacity)
                bot.reply_to(message, f"✅ ظرفیت ماشین {machine['name']} به {new_capacity} تغییر کرد")
            else:
                bot.reply_to(message, "❌ عدد بین 100 تا 50000")
        else:
            bot.reply_to(message, "❌ ماشین یافت نشد")
    except:
        bot.reply_to(message, "❌ عدد نامعتبر")

@bot.callback_query_handler(func=lambda call: call.data == "machines_restart")
def machines_restart(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    bot.send_message(call.message.chat.id, "🔄 در حال ریستارت ربات‌های روی این ماشین...")
    # ریستارت ربات‌های مرده
    restarted = machine_manager.restart_all_dead_bots()
    bot.send_message(call.message.chat.id, f"✅ {restarted} ربات ریستارت شدند")

@bot.callback_query_handler(func=lambda call: call.data == "machines_disable")
def machines_disable(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    machines = db.execute("SELECT id, name, status FROM machines")
    markup = types.InlineKeyboardMarkup(row_width=1)
    for m in machines:
        status_emoji = "🟢" if m['status'] == 'active' else "🔴"
        markup.add(types.InlineKeyboardButton(f"{status_emoji} {m['name']}", callback_data=f"toggle_machine_{m['id']}"))
    bot.send_message(call.message.chat.id, "🎛️ انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_machine_'))
def toggle_machine(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    machine_id = int(call.data.replace('toggle_machine_', ''))
    machine = db.execute("SELECT status, name FROM machines WHERE id = ?", (machine_id,))
    if machine:
        machine = machine[0]
        new_status = 'inactive' if machine['status'] == 'active' else 'active'
        db.execute("UPDATE machines SET status = ? WHERE id = ?", (new_status, machine_id))
        status_text = "غیرفعال" if new_status == 'inactive' else "فعال"
        bot.answer_callback_query(call.id, f"✅ ماشین {machine['name']} {status_text} شد")
        bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== اضافه کردن سرور جدید ====================
@bot.message_handler(func=lambda m: m.text == '➕ اضافه کردن سرور جدید')
def admin_add_server(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(message.chat.id, "➕ **اضافه کردن سرور جدید**\n\nلطفاً اطلاعات را وارد کنید:\n1️⃣ نام سرور:")
    bot.register_next_step_handler(msg, process_server_name)

def process_server_name(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    server_name = message.text.strip()
    msg = bot.send_message(message.chat.id, "2️⃣ آدرس IP:")
    bot.register_next_step_handler(msg, lambda m: process_server_ip(m, server_name))

def process_server_ip(message, server_name):
    if message.from_user.id not in ADMIN_IDS:
        return
    server_ip = message.text.strip()
    msg = bot.send_message(message.chat.id, "3️⃣ پورت (پیش‌فرض 22):")
    bot.register_next_step_handler(msg, lambda m: process_server_port(m, server_name, server_ip))

def process_server_port(message, server_name, server_ip):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        port = int(message.text.strip()) if message.text.strip() else 22
    except:
        port = 22
    msg = bot.send_message(message.chat.id, "4️⃣ نام کاربری:")
    bot.register_next_step_handler(msg, lambda m: process_server_username(m, server_name, server_ip, port))

def process_server_username(message, server_name, server_ip, port):
    if message.from_user.id not in ADMIN_IDS:
        return
    username = message.text.strip()
    msg = bot.send_message(message.chat.id, "5️⃣ رمز عبور:")
    bot.register_next_step_handler(msg, lambda m: process_server_password(m, server_name, server_ip, port, username))

def process_server_password(message, server_name, server_ip, port, username):
    if message.from_user.id not in ADMIN_IDS:
        return
    password = message.text.strip()
    
    # انتخاب ماشین برای اتصال
    machines = db.execute("SELECT id, name FROM machines WHERE is_local = 1 OR status = 'active'")
    markup = types.InlineKeyboardMarkup(row_width=1)
    for m in machines:
        markup.add(types.InlineKeyboardButton(f"🖥️ {m['name']}", callback_data=f"assign_machine_{m['id']}_{server_name}_{server_ip}_{port}_{username}_{password}"))
    
    bot.send_message(message.chat.id, "6️⃣ این سرور به کدام ماشین متصل شود؟", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('assign_machine_'))
def assign_machine_to_server(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    parts = call.data.replace('assign_machine_', '').split('_')
    machine_id = int(parts[0])
    server_name = parts[1]
    server_ip = parts[2]
    port = int(parts[3])
    username = parts[4]
    password = '_'.join(parts[5:]) if len(parts) > 5 else ""
    
    status_msg = bot.send_message(call.message.chat.id, "🔄 در حال اتصال به سرور...")
    
    success, msg = remote_manager.add_server(server_name, server_ip, username, password, port, machine_id)
    
    if success:
        bot.edit_message_text(f"✅ سرور با موفقیت اضافه شد!\n\n📊 وضعیت: {msg}", 
                             call.message.chat.id, status_msg.message_id)
        
        # به‌روزرسانی ماشین
        db.execute("UPDATE machines SET ip = ?, username = ?, is_local = 0 WHERE id = ?", 
                  (server_ip, username, machine_id))
    else:
        bot.edit_message_text(f"❌ خطا: {msg}", call.message.chat.id, status_msg.message_id)

# ==================== تنظیمات سیستم ====================
@bot.message_handler(func=lambda m: m.text == '⚙️ تنظیمات سیستم')
def admin_settings(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("💰 قیمت اشتراک", callback_data="admin_set_price"),
        types.InlineKeyboardButton("🤖 حداکثر ربات در اشتراک", callback_data="admin_set_max_bots"),
        types.InlineKeyboardButton("📈 محدودیت ساخت در ساعت", callback_data="admin_set_build_limit"),
        types.InlineKeyboardButton("💸 درصد کمیسیون", callback_data="admin_set_commission"),
        types.InlineKeyboardButton("💰 حداقل برداشت", callback_data="admin_set_min_withdraw"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back_settings")
    )
    bot.send_message(message.chat.id, "⚙️ **تنظیمات سیستم**", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_price")
def admin_set_price(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "💰 قیمت اشتراک (تومان):")
    bot.register_next_step_handler(msg, process_set_price)

def process_set_price(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        price = int(message.text.strip())
        update_setting('subscription_price', price)
        update_setting('subscription_price_str', f"{price:,} تومان")
        update_setting('subscription_price_usd', f"${price // 40000} USD")
        bot.reply_to(message, f"✅ قیمت اشتراک به {price:,} تومان تغییر کرد")
    except:
        bot.reply_to(message, "❌ عدد نامعتبر")

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_max_bots")
def admin_set_max_bots(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "🤖 حداکثر ربات در هر اشتراک (پیش‌فرض 3):")
    bot.register_next_step_handler(msg, process_set_max_bots)

def process_set_max_bots(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        max_bots = int(message.text.strip())
        if 1 <= max_bots <= 100:
            update_setting('max_bots_per_subscription', max_bots)
            db.execute('UPDATE users SET max_bots = ?', (max_bots,))
            bot.reply_to(message, f"✅ حداکثر ربات به {max_bots} تغییر کرد")
        else:
            bot.reply_to(message, "❌ عدد بین 1 تا 100")
    except:
        bot.reply_to(message, "❌ عدد نامعتبر")

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_build_limit")
def admin_set_build_limit(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "📈 حداکثر ساخت ربات در ساعت (پیش‌فرض 10):")
    bot.register_next_step_handler(msg, process_set_build_limit)

def process_set_build_limit(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        limit = int(message.text.strip())
        if 1 <= limit <= 100:
            update_setting('max_builds_per_hour', limit)
            bot.reply_to(message, f"✅ محدودیت ساخت به {limit} ربات در ساعت تغییر کرد")
        else:
            bot.reply_to(message, "❌ عدد بین 1 تا 100")
    except:
        bot.reply_to(message, "❌ عدد نامعتبر")

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_commission")
def admin_set_commission(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "💸 درصد کمیسیون معرف (پیش‌فرض 7):")
    bot.register_next_step_handler(msg, process_set_commission)

def process_set_commission(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        percent = int(message.text.strip())
        if 1 <= percent <= 50:
            update_setting('withdraw_percent', percent)
            bot.reply_to(message, f"✅ درصد کمیسیون به {percent}% تغییر کرد")
        else:
            bot.reply_to(message, "❌ عدد بین 1 تا 50")
    except:
        bot.reply_to(message, "❌ عدد نامعتبر")

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_min_withdraw")
def admin_set_min_withdraw(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "💰 حداقل مبلغ برداشت (تومان، پیش‌فرض 2,000,000):")
    bot.register_next_step_handler(msg, process_set_min_withdraw)

def process_set_min_withdraw(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        min_amount = int(message.text.strip())
        if min_amount >= 100000:
            update_setting('min_withdraw', min_amount)
            bot.reply_to(message, f"✅ حداقل برداشت به {min_amount:,} تومان تغییر کرد")
        else:
            bot.reply_to(message, "❌ حداقل 100,000 تومان")
    except:
        bot.reply_to(message, "❌ عدد نامعتبر")

# ==================== پیام همگانی ====================
@bot.message_handler(func=lambda m: m.text == '📢 پیام همگانی')
def broadcast_prompt(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("📝 متن ساده", callback_data="broadcast_text"),
        types.InlineKeyboardButton("🖼️ با تصویر", callback_data="broadcast_photo")
    )
    bot.send_message(message.chat.id, "📢 انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "broadcast_text")
def broadcast_text(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "📝 متن پیام همگانی را ارسال کنید:")
    bot.register_next_step_handler(msg, process_broadcast_text)

def process_broadcast_text(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    text = message.text
    users = db.execute("SELECT user_id, language FROM users WHERE is_banned = 0")
    sent = 0
    failed = 0
    
    status_msg = bot.reply_to(message, "🔄 در حال ارسال پیام همگانی...")
    
    for user in users:
        try:
            # ارسال به زبان کاربر
            if user['language'] == 'fa':
                msg_text = f"📢 **اعلامیه**\n\n{text}"
            else:
                msg_text = f"📢 **Announcement**\n\n{text}"
            bot.send_message(user['user_id'], msg_text, parse_mode='Markdown')
            sent += 1
            time.sleep(0.05)
        except:
            failed += 1
    
    bot.edit_message_text(f"✅ پیام به {sent} کاربر ارسال شد\n❌ ناموفق: {failed}", 
                         message.chat.id, status_msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "broadcast_photo")
def broadcast_photo(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "🖼️ تصویر و سپس کپشن را ارسال کنید:")
    bot.register_next_step_handler(msg, process_broadcast_photo)

def process_broadcast_photo(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    if not message.photo:
        bot.reply_to(message, "❌ لطفاً یک تصویر ارسال کنید")
        return
    
    caption = message.caption or ""
    file_id = message.photo[-1].file_id
    
    users = db.execute("SELECT user_id, language FROM users WHERE is_banned = 0")
    sent = 0
    failed = 0
    
    status_msg = bot.reply_to(message, "🔄 در حال ارسال پیام همگانی...")
    
    for user in users:
        try:
            if user['language'] == 'fa':
                msg_caption = f"📢 **اعلامیه**\n\n{caption}"
            else:
                msg_caption = f"📢 **Announcement**\n\n{caption}"
            bot.send_photo(user['user_id'], file_id, caption=msg_caption, parse_mode='Markdown')
            sent += 1
            time.sleep(0.05)
        except:
            failed += 1
    
    bot.edit_message_text(f"✅ پیام به {sent} کاربر ارسال شد\n❌ ناموفق: {failed}", 
                         message.chat.id, status_msg.message_id)

# ==================== کال‌بک‌های بازگشت ====================
@bot.callback_query_handler(func=lambda call: call.data == "admin_back_settings")
def admin_back_settings(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    admin_settings(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "admin_back_machines")
def admin_back_machines(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    admin_machines(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== بازگشت به منوی اصلی ====================
@bot.message_handler(func=lambda m: m.text == '🔙 بازگشت به منوی اصلی')
def back_to_main(message):
    bot.send_message(message.chat.id, "🚀 منوی اصلی:", reply_markup=get_main_menu(message.from_user.id))

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
        'total_users': db.execute('SELECT COUNT(*) as count FROM users')[0]['count'],
        'total_bots': db.execute('SELECT COUNT(*) as count FROM bots')[0]['count']
    })

def run_flask():
    flask_app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

threading.Thread(target=run_flask, daemon=True).start()
start_time = time.time()

# ==================== اجرا ====================
if __name__ == "__main__":
    print("=" * 80)
    print("🚀 ربات مادر نهایی - نسخه 100.2 Ultimate Enterprise".center(80))
    print("=" * 80)
    print(f"👑 ادمین‌ها: {ADMIN_IDS}")
    print(f"🤖 ربات: @{BOT_USERNAME}")
    print(f"💰 قیمت اشتراک: {get_setting('subscription_price_str')}")
    print(f"🤖 حداکثر ربات در هر اشتراک: {get_setting('max_bots_per_subscription')}")
    print(f"💳 آدرس TRC20: {get_setting('trc20_address')}")
    print(f"🏦 شماره کارت (فارسی): {get_setting('card_number_display')}")
    print(f"📊 Health Check: http://localhost:5000/health")
    print("=" * 80)
    print("✅ ویژگی‌ها:")
    print("   - دو زبانه (فارسی/انگلیسی) - پنل مدیریت فقط فارسی")
    print("   - سیستم پرداخت: فارسی (کارت به کارت) / انگلیسی (TRC20)")
    print("   - کمیسیون معرف قابل تنظیم")
    print("   - بازیابی خودکار پس از کرش")
    print("   - حداکثر 3 ربات در هر اشتراک (قابل تنظیم)")
    print("   - مدیریت ظرفیت کاربران (پیام هشدار خودکار)")
    print("   - اضافه کردن سرور جدید به ماشین‌ها")
    print("   - مدیریت ماشین‌ها با 5 دکمه (افزایش/کاهش ظرفیت)")
    print("   - ساخت ربات با پوشه (حفظ ساختار)")
    print("   - تغییر تمام متون از پنل مدیریت")
    print("=" * 80)
    print("✅ ربات در حال اجرا است...")
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            logger.error(f"Polling error: {e}")
            time.sleep(5)
