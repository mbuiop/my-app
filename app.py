#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║     🚀 ULTRA MOTHER BOT - ENTERPRISE EDITION v24.0                          ║
║     ⚡ Distributed System - Microservices Architecture - High Performance   ║
║     🔥 Support: Millions of Users - 1000+ Concurrent Builds                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
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
import queue
import signal
import logging
from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import asyncio
import aiohttp
import aiofiles
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
import pickle
import zlib
from abc import ABC, abstractmethod

# ==================== تنظیمات پیشرفته مقیاس بالا ====================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# معماری پوشه‌های توزیع شده
DIRS = {
    # دیتابیس‌ها
    'DB_MASTER': os.path.join(BASE_DIR, "db_master"),
    'DB_SLAVE_1': os.path.join(BASE_DIR, "db_slave_1"),
    'DB_SLAVE_2': os.path.join(BASE_DIR, "db_slave_2"),
    'DB_CACHE': os.path.join(BASE_DIR, "db_cache"),
    
    # داده‌های کاربران
    'USERS_DATA': os.path.join(BASE_DIR, "data", "users"),
    'BOTS_DATA': os.path.join(BASE_DIR, "data", "bots"),
    'EXECUTIONS_DATA': os.path.join(BASE_DIR, "data", "executions"),
    
    # فایل‌های سیستم
    'FILES': os.path.join(BASE_DIR, "storage", "files"),
    'FOLDERS': os.path.join(BASE_DIR, "storage", "folders"),
    'RUNNING': os.path.join(BASE_DIR, "runtime", "running_bots"),
    'LOGS': os.path.join(BASE_DIR, "logs"),
    'RECEIPTS': os.path.join(BASE_DIR, "storage", "receipts"),
    'TEMP': os.path.join(BASE_DIR, "temp"),
    'BACKUPS': os.path.join(BASE_DIR, "backups"),
    
    # کتابخانه‌ها و پکیج‌ها
    'LIBRARIES': os.path.join(BASE_DIR, "libraries"),
    'PACKAGES': os.path.join(BASE_DIR, "packages"),
    
    # کش و ایندکس
    'CACHE': os.path.join(BASE_DIR, "cache"),
    'INDEX': os.path.join(BASE_DIR, "index"),
    'QUEUE': os.path.join(BASE_DIR, "queue"),
}

for dir_path in DIRS.values():
    os.makedirs(dir_path, exist_ok=True)

# توکن ربات
BOT_TOKEN = "8266270866:AAF6m1x4weSUEvzIj1gkbIS_j0yAdxCSs78"
ADMIN_IDS = [327855654]
BOT_USERNAME = "ROBTTSAZE_bot"

# ==================== کلاس‌های دیتابیس توزیع شده ====================

class DatabaseType(Enum):
    MASTER = "master"
    SLAVE = "slave"
    CACHE = "cache"

class DistributedDatabase:
    """دیتابیس توزیع شده با پشتیبانی از Master-Slave و کش هوشمند"""
    
    def __init__(self):
        self.connections: Dict[str, sqlite3.Connection] = {}
        self.locks: Dict[str, threading.RLock] = {}
        self.cache = {}
        self.cache_lock = threading.RLock()
        self._init_all_databases()
        self._init_cluster()
    
    def _init_all_databases(self):
        """راه‌اندازی تمام دیتابیس‌ها"""
        for name, path in [('master', DIRS['DB_MASTER']), 
                           ('slave1', DIRS['DB_SLAVE_1']),
                           ('slave2', DIRS['DB_SLAVE_2']),
                           ('cache', DIRS['DB_CACHE'])]:
            os.makedirs(path, exist_ok=True)
            db_path = os.path.join(path, 'mother_bot.db')
            conn = sqlite3.connect(db_path, timeout=60, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=-500000")
            conn.execute("PRAGMA mmap_size=10000000000")
            self.connections[name] = conn
            self.locks[name] = threading.RLock()
        
        # جدول‌های اصلی
        self._init_tables()
    
    def _init_tables(self):
        master_conn = self.connections['master']
        
        # جدول کاربران با ایندکس‌های پیشرفته
        master_conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                phone TEXT,
                email TEXT,
                bots_count INTEGER DEFAULT 0,
                subscription_status TEXT DEFAULT 'inactive',
                subscription_expiry TIMESTAMP,
                subscription_type TEXT DEFAULT 'monthly',
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                referrals_count INTEGER DEFAULT 0,
                verified_referrals INTEGER DEFAULT 0,
                wallet_balance INTEGER DEFAULT 0,
                total_spent INTEGER DEFAULT 0,
                created_at TIMESTAMP,
                last_active TIMESTAMP,
                last_ip TEXT,
                language TEXT DEFAULT 'fa',
                is_banned INTEGER DEFAULT 0,
                warning_count INTEGER DEFAULT 0,
                total_executions INTEGER DEFAULT 0,
                total_builds INTEGER DEFAULT 0,
                folders_count INTEGER DEFAULT 0,
                active_until TIMESTAMP,
                INDEX idx_subscription (subscription_status, subscription_expiry),
                INDEX idx_referral (referral_code),
                INDEX idx_created (created_at)
            )
        ''')
        
        # جدول ربات‌ها با ایندکس‌های بهینه
        master_conn.execute('''
            CREATE TABLE IF NOT EXISTS bots (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                token TEXT,
                name TEXT,
                username TEXT,
                file_path TEXT,
                folder_path TEXT,
                folder_id TEXT,
                pid INTEGER,
                machine_id INTEGER,
                port INTEGER,
                status TEXT DEFAULT 'stopped',
                created_at TIMESTAMP,
                last_active TIMESTAMP,
                last_execution TIMESTAMP,
                execution_count INTEGER DEFAULT 0,
                is_5min_mode INTEGER DEFAULT 0,
                next_deactivation TIMESTAMP,
                memory_usage INTEGER DEFAULT 0,
                cpu_usage REAL DEFAULT 0,
                error_count INTEGER DEFAULT 0,
                last_error TEXT,
                INDEX idx_user (user_id),
                INDEX idx_status (status),
                INDEX idx_deactivation (next_deactivation),
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        # جدول پوشه‌های کاربران با ساختار درختی
        master_conn.execute('''
            CREATE TABLE IF NOT EXISTS folders (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                folder_name TEXT,
                folder_path TEXT,
                parent_id TEXT,
                structure TEXT,
                created_at TIMESTAMP,
                last_used TIMESTAMP,
                file_count INTEGER DEFAULT 0,
                size INTEGER DEFAULT 0,
                INDEX idx_user_folder (user_id, folder_name),
                INDEX idx_parent (parent_id),
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        # جدول اجراهای ۵ دقیقه‌ای
        master_conn.execute('''
            CREATE TABLE IF NOT EXISTS executions (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                bot_id TEXT,
                status TEXT,
                started_at TIMESTAMP,
                ended_at TIMESTAMP,
                duration INTEGER,
                output TEXT,
                error TEXT,
                memory_used INTEGER,
                cpu_used REAL,
                INDEX idx_user_exec (user_id, started_at),
                INDEX idx_bot_exec (bot_id),
                INDEX idx_status_exec (status),
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        # جدول کتابخانه‌های نصب شده
        master_conn.execute('''
            CREATE TABLE IF NOT EXISTS libraries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                version TEXT,
                description TEXT,
                size INTEGER,
                installed_at TIMESTAMP,
                installed_by INTEGER,
                INDEX idx_name (name)
            )
        ''')
        
        # جدول فیش‌های پرداخت
        master_conn.execute('''
            CREATE TABLE IF NOT EXISTS receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                receipt_path TEXT,
                status TEXT DEFAULT 'pending',
                payment_code TEXT UNIQUE,
                transaction_id TEXT,
                reviewed_by INTEGER,
                reviewed_at TIMESTAMP,
                created_at TIMESTAMP,
                INDEX idx_user_receipt (user_id, status),
                INDEX idx_payment (payment_code)
            )
        ''')
        
        # جدول درخواست‌های برداشت
        master_conn.execute('''
            CREATE TABLE IF NOT EXISTS withdraw_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                card_number TEXT,
                card_holder TEXT,
                bank_name TEXT,
                status TEXT DEFAULT 'pending',
                tracking_code TEXT,
                created_at TIMESTAMP,
                processed_at TIMESTAMP,
                INDEX idx_user_withdraw (user_id, status)
            )
        ''')
        
        # جدول تنظیمات سیستم
        master_conn.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                category TEXT,
                description TEXT,
                updated_by INTEGER,
                updated_at TIMESTAMP
            )
        ''')
        
        # جدول پیام‌های سیستم
        master_conn.execute('''
            CREATE TABLE IF NOT EXISTS system_messages (
                key TEXT PRIMARY KEY,
                title TEXT,
                message TEXT,
                variables TEXT,
                updated_by INTEGER,
                updated_at TIMESTAMP
            )
        ''')
        
        # جدول آمار روزانه
        master_conn.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT PRIMARY KEY,
                new_users INTEGER DEFAULT 0,
                active_users INTEGER DEFAULT 0,
                new_bots INTEGER DEFAULT 0,
                active_bots INTEGER DEFAULT 0,
                new_subscriptions INTEGER DEFAULT 0,
                total_revenue INTEGER DEFAULT 0,
                total_executions INTEGER DEFAULT 0,
                INDEX idx_date (date)
            )
        ''')
        
        # جدول خطاهای سیستم
        master_conn.execute('''
            CREATE TABLE IF NOT EXISTS system_errors (
                id TEXT PRIMARY KEY,
                type TEXT,
                message TEXT,
                stack_trace TEXT,
                user_id INTEGER,
                bot_id TEXT,
                timestamp TIMESTAMP,
                resolved INTEGER DEFAULT 0,
                INDEX idx_resolved (resolved),
                INDEX idx_timestamp (timestamp)
            )
        ''')
        
        master_conn.commit()
        
        # تنظیمات پیش‌فرض
        default_settings = {
            'card_number': ('5892101187322777', 'payment', 'شماره کارت'),
            'card_number_display': ('5892 1011 8732 2777', 'payment', 'شماره کارت نمایشی'),
            'card_holder': ('مرتضی نیکخو خنجری', 'payment', 'نام صاحب کارت'),
            'card_bank': ('بانک ملی - سپهر', 'payment', 'نام بانک'),
            'subscription_price': ('50000', 'payment', 'قیمت اشتراک'),
            'subscription_price_str': ('۵۰,۰۰۰ تومان', 'payment', 'قیمت اشتراک نمایشی'),
            'max_bots_per_user': ('3', 'limits', 'حداکثر ربات هر کاربر'),
            'execution_duration': ('5', 'limits', 'مدت زمان اجرا به دقیقه'),
            'withdraw_percent': ('7', 'payment', 'درصد کمیسیون'),
            'min_withdraw': ('2000000', 'payment', 'حداقل مبلغ برداشت'),
            'max_concurrent_executions': ('100', 'performance', 'حداکثر اجرای همزمان'),
            'rate_limit_per_user': ('10', 'security', 'محدودیت درخواست در ثانیه'),
            'cache_ttl': ('3600', 'performance', 'زمان کش به ثانیه'),
        }
        
        for key, (value, category, desc) in default_settings.items():
            master_conn.execute('''
                INSERT OR IGNORE INTO system_settings (key, value, category, description, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (key, value, category, desc, datetime.now().isoformat()))
        
        # پیام‌های پیش‌فرض
        default_messages = {
            'welcome': ('خوش‌آمدگویی', '''🚀 **به ربات مادر خوش آمدید!**

کاربر گرامی {first_name}
از اینکه به جمع ما پیوستید، خوشحالیم!

📋 **برای شروع:**
1️⃣ اشتراک خود را فعال کنید
2️⃣ ربات خود را بسازید
3️⃣ از امکانات پیشرفته لذت ببرید

💡 سوالی دارید؟ با پشتیبانی تماس بگیرید.'''),
            
            'subscription_activated': ('فعال‌سازی اشتراک', '''✅ **اشتراک شما فعال شد!**

کاربر گرامی {first_name}
اشتراک ماهیانه شما با موفقیت فعال گردید.

📋 **امکانات شما:**
- ساخت حداکثر {max_bots} ربات
- هر بار اجرا {duration} دقیقه
- دسترسی به کتابخانه‌های پیشرفته
- پشتیبانی ۲۴/۷

🎯 **حالا می‌توانید:**
1. فایل .py یا .zip خود را ارسال کنید
2. یا از پوشه‌ها استفاده کنید

موفق باشید! 🚀'''),
            
            'build_instruction': ('دستورالعمل ساخت', '''🌟 **ساخت ربات جدید**

کاربر گرامی {first_name}
از اینکه ربات قدرتمند ما را برای اجرای کد خود انتخاب کردید، ممنون هستیم!

📌 **برای ساخت ربات:**
1️⃣ مبلغ {price} را به کارت زیر واریز کنید:
`{card}`
👤 {holder}
🏦 {bank}

2️⃣ همینجا رسید خود را ارسال کنید

3️⃣ پس از تایید، اشتراک شما فعال می‌شود

⏱ زمان بررسی: حداکثر ۲۴ ساعت

⚠️ **توجه:** توکن ربات خود را داخل کد قرار دهید!'''),
        }
        
        for key, (title, message) in default_messages.items():
            master_conn.execute('''
                INSERT OR IGNORE INTO system_messages (key, title, message, updated_at)
                VALUES (?, ?, ?, ?)
            ''', (key, title, message, datetime.now().isoformat()))
        
        master_conn.commit()
    
    def execute(self, query: str, params: tuple = (), db_type: DatabaseType = DatabaseType.MASTER):
        """اجرای کوئری با پشتیبانی از دیتابیس‌های مختلف"""
        db_name = db_type.value
        with self.locks[db_name]:
            try:
                cursor = self.connections[db_name].execute(query, params)
                if query.strip().upper().startswith(('SELECT', 'PRAGMA')):
                    return cursor.fetchall()
                self.connections[db_name].commit()
                return cursor.lastrowid if query.strip().upper().startswith('INSERT') else True
            except Exception as e:
                print(f"DB Error on {db_name}: {e}")
                if db_type == DatabaseType.MASTER:
                    self._replicate_to_slaves(query, params)
                return []
    
    def _replicate_to_slaves(self, query: str, params: tuple):
        """همگام‌سازی با دیتابیس‌های Slave"""
        for slave_name in ['slave1', 'slave2']:
            try:
                with self.locks[slave_name]:
                    self.connections[slave_name].execute(query, params)
                    self.connections[slave_name].commit()
            except Exception as e:
                print(f"Replication error to {slave_name}: {e}")
    
    def _init_cluster(self):
        """راه‌اندازی خوشه دیتابیس"""
        # ایجاد ایندکس‌های اضافی برای سرعت
        master_conn = self.connections['master']
        
        # ایندکس‌های ترکیبی برای کوئری‌های سنگین
        master_conn.execute('CREATE INDEX IF NOT EXISTS idx_users_sub_status ON users(subscription_status, subscription_expiry)')
        master_conn.execute('CREATE INDEX IF NOT EXISTS idx_bots_user_status ON bots(user_id, status)')
        master_conn.execute('CREATE INDEX IF NOT EXISTS idx_executions_user_status ON executions(user_id, status)')
        
        master_conn.commit()
        
        # اجرای VACUUM برای بهینه‌سازی
        master_conn.execute('VACUUM')
    
    def get_cached(self, key: str, ttl: int = 3600):
        """دریافت از کش"""
        with self.cache_lock:
            if key in self.cache:
                data, expiry = self.cache[key]
                if time.time() < expiry:
                    return data
                del self.cache[key]
        return None
    
    def set_cached(self, key: str, value: Any, ttl: int = 3600):
        """ذخیره در کش"""
        with self.cache_lock:
            self.cache[key] = (value, time.time() + ttl)
    
    def get_setting(self, key: str):
        """دریافت تنظیمات با کش"""
        cached = self.get_cached(f"setting_{key}")
        if cached:
            return cached
        
        result = self.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
        if result:
            value = result[0]['value']
            if key in ['subscription_price', 'max_bots_per_user', 'execution_duration', 
                       'withdraw_percent', 'min_withdraw', 'max_concurrent_executions']:
                value = int(value)
            self.set_cached(f"setting_{key}", value)
            return value
        return None
    
    def update_setting(self, key: str, value: str, updated_by: int = None):
        """به‌روزرسانی تنظیمات"""
        self.execute("UPDATE system_settings SET value = ?, updated_by = ?, updated_at = ? WHERE key = ?",
                    (str(value), updated_by, datetime.now().isoformat(), key))
        self.set_cached(f"setting_{key}", None, 0)  # پاک کردن کش
    
    def get_message(self, key: str, variables: dict = None):
        """دریافت پیام با جایگزینی متغیرها"""
        result = self.execute("SELECT message FROM system_messages WHERE key = ?", (key,))
        if result:
            message = result[0]['message']
            if variables:
                try:
                    message = message.format(**variables)
                except:
                    pass
            return message
        return None
    
    def update_message(self, key: str, message: str, title: str, updated_by: int):
        """به‌روزرسانی پیام"""
        self.execute("UPDATE system_messages SET message = ?, title = ?, updated_by = ?, updated_at = ? WHERE key = ?",
                    (message, title, updated_by, datetime.now().isoformat(), key))
        return True
    
    def get_user(self, user_id: int):
        """دریافت کاربر از کش یا دیتابیس"""
        cached = self.get_cached(f"user_{user_id}")
        if cached:
            return cached
        
        result = self.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        if result:
            user = dict(result[0])
            self.set_cached(f"user_{user_id}", user, 300)
            return user
        return None
    
    def create_user(self, user_id: int, username: str, first_name: str, last_name: str, referred_by: int = None):
        """ایجاد کاربر جدید"""
        now = datetime.now().isoformat()
        referral_code = hashlib.md5(f"{user_id}_{time.time()}_{secrets.token_hex(4)}".encode()).hexdigest()[:12]
        
        self.execute('''
            INSERT OR IGNORE INTO users 
            (user_id, username, first_name, last_name, referral_code, referred_by, created_at, last_active, 
             subscription_status, wallet_balance, language)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'inactive', 0, 'fa')
        ''', (user_id, username, first_name, last_name, referral_code, referred_by, now, now))
        
        if referred_by and referred_by != user_id:
            self.execute('UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = ?', (referred_by,))
        
        # بروزرسانی آمار روزانه
        today = datetime.now().date().isoformat()
        self.execute('''
            INSERT INTO daily_stats (date, new_users) 
            VALUES (?, 1) 
            ON CONFLICT(date) DO UPDATE SET new_users = new_users + 1
        ''', (today,))
        
        self.set_cached(f"user_{user_id}", None, 0)
        return True
    
    def check_subscription(self, user_id: int) -> bool:
        """بررسی وضعیت اشتراک"""
        user = self.get_user(user_id)
        if not user or user['subscription_status'] != 'active':
            return False
        
        if user['subscription_expiry']:
            expiry = datetime.fromisoformat(user['subscription_expiry'])
            if expiry > datetime.now():
                return True
            self.execute('UPDATE users SET subscription_status = "inactive" WHERE user_id = ?', (user_id,))
            self.set_cached(f"user_{user_id}", None, 0)
        return False
    
    def activate_subscription(self, user_id: int, months: int = 1):
        """فعال‌سازی اشتراک"""
        user = self.get_user(user_id)
        now = datetime.now()
        
        if user and user['subscription_status'] == 'active' and user['subscription_expiry']:
            new_expiry = datetime.fromisoformat(user['subscription_expiry']) + timedelta(days=30*months)
        else:
            new_expiry = now + timedelta(days=30*months)
        
        self.execute('''
            UPDATE users 
            SET subscription_status = 'active', subscription_expiry = ?, active_until = ?
            WHERE user_id = ?
        ''', (new_expiry.isoformat(), new_expiry.isoformat(), user_id))
        
        # بروزرسانی آمار
        today = datetime.now().date().isoformat()
        self.execute('''
            INSERT INTO daily_stats (date, new_subscriptions, total_revenue) 
            VALUES (?, 1, ?) 
            ON CONFLICT(date) DO UPDATE SET new_subscriptions = new_subscriptions + 1, total_revenue = total_revenue + ?
        ''', (today, self.get_setting('subscription_price'), self.get_setting('subscription_price')))
        
        self.set_cached(f"user_{user_id}", None, 0)
        return new_expiry
    
    def add_wallet_balance(self, user_id: int, amount: int):
        """افزایش موجودی کیف پول"""
        user = self.get_user(user_id)
        if user:
            new_balance = user['wallet_balance'] + amount
            self.execute('UPDATE users SET wallet_balance = ? WHERE user_id = ?', (new_balance, user_id))
            self.set_cached(f"user_{user_id}", None, 0)
            return new_balance
        return None
    
    def get_user_bots_count(self, user_id: int) -> int:
        """تعداد ربات‌های کاربر"""
        result = self.execute("SELECT COUNT(*) as count FROM bots WHERE user_id = ?", (user_id,))
        return result[0]['count'] if result else 0
    
    def can_create_bot(self, user_id: int) -> tuple:
        """بررسی مجاز بودن ساخت ربات"""
        max_bots = self.get_setting('max_bots_per_user') or 3
        current_bots = self.get_user_bots_count(user_id)
        return current_bots < max_bots, max_bots, current_bots
    
    def add_bot(self, bot_id: str, user_id: int, token: str, name: str, username: str, 
                file_path: str = None, folder_path: str = None, folder_id: str = None):
        """افزودن ربات جدید"""
        now = datetime.now().isoformat()
        self.execute('''
            INSERT INTO bots 
            (id, user_id, token, name, username, file_path, folder_path, folder_id, status, created_at, last_active, execution_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'stopped', ?, ?, 0)
        ''', (bot_id, user_id, token, name, username, file_path, folder_path, folder_id, now, now))
        
        self.execute('UPDATE users SET bots_count = bots_count + 1, total_builds = total_builds + 1 WHERE user_id = ?', (user_id,))
        
        today = datetime.now().date().isoformat()
        self.execute('''
            INSERT INTO daily_stats (date, new_bots) 
            VALUES (?, 1) 
            ON CONFLICT(date) DO UPDATE SET new_bots = new_bots + 1
        ''', (today,))
        
        self.set_cached(f"user_{user_id}", None, 0)
        return True
    
    def delete_bot(self, bot_id: str, user_id: int) -> bool:
        """حذف ربات"""
        # دریافت اطلاعات ربات
        bot = self.execute("SELECT folder_path, file_path FROM bots WHERE id = ? AND user_id = ?", (bot_id, user_id))
        
        if bot:
            # حذف فایل‌های فیزیکی
            if bot[0]['file_path'] and os.path.exists(bot[0]['file_path']):
                try:
                    os.remove(bot[0]['file_path'])
                except:
                    pass
            
            # حذف از دیتابیس
            self.execute('DELETE FROM bots WHERE id = ? AND user_id = ?', (bot_id, user_id))
            self.execute('UPDATE users SET bots_count = bots_count - 1 WHERE user_id = ?', (user_id,))
            
            self.set_cached(f"user_{user_id}", None, 0)
            return True
        return False
    
    def create_folder(self, folder_id: str, user_id: int, folder_name: str, 
                      folder_path: str, parent_id: str = None):
        """ایجاد پوشه جدید"""
        now = datetime.now().isoformat()
        structure = json.dumps({
            'name': folder_name,
            'created_at': now,
            'files': [],
            'subfolders': [],
            'parent': parent_id
        })
        
        self.execute('''
            INSERT INTO folders (id, user_id, folder_name, folder_path, parent_id, structure, created_at, last_used, file_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
        ''', (folder_id, user_id, folder_name, folder_path, parent_id, structure, now, now))
        
        self.execute('UPDATE users SET folders_count = folders_count + 1 WHERE user_id = ?', (user_id,))
        return True
    
    def add_execution(self, exec_id: str, user_id: int, bot_id: str):
        """ثبت اجرای جدید"""
        now = datetime.now().isoformat()
        self.execute('''
            INSERT INTO executions (id, user_id, bot_id, status, started_at)
            VALUES (?, ?, ?, 'running', ?)
        ''', (exec_id, user_id, bot_id, now))
        
        self.execute('UPDATE users SET total_executions = total_executions + 1 WHERE user_id = ?', (user_id,))
        return True
    
    def update_execution_result(self, exec_id: str, status: str, duration: int = None, 
                                output: str = None, error: str = None, 
                                memory_used: int = None, cpu_used: float = None):
        """به‌روزرسانی نتیجه اجرا"""
        ended_at = datetime.now().isoformat()
        
        if duration is None:
            exec_data = self.execute("SELECT started_at FROM executions WHERE id = ?", (exec_id,))
            if exec_data:
                started = datetime.fromisoformat(exec_data[0]['started_at'])
                duration = int((datetime.now() - started).total_seconds())
        
        self.execute('''
            UPDATE executions 
            SET status = ?, ended_at = ?, duration = ?, output = ?, error = ?, memory_used = ?, cpu_used = ?
            WHERE id = ?
        ''', (status, ended_at, duration, output, error, memory_used, cpu_used, exec_id))
        return True
    
    def log_error(self, error_type: str, message: str, user_id: int = None, 
                  bot_id: str = None, stack_trace: str = None):
        """ثبت خطا در سیستم"""
        error_id = hashlib.md5(f"{time.time()}_{user_id}_{bot_id}_{secrets.token_hex(4)}".encode()).hexdigest()[:16]
        self.execute('''
            INSERT INTO system_errors (id, type, message, stack_trace, user_id, bot_id, timestamp, resolved)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        ''', (error_id, error_type, message[:1000], stack_trace, user_id, bot_id, datetime.now().isoformat()))
        
        # پاکسازی خطاهای قدیمی (بیشتر از 30 روز)
        month_ago = (datetime.now() - timedelta(days=30)).isoformat()
        self.execute("DELETE FROM system_errors WHERE timestamp < ?", (month_ago,))
        
        return error_id

# ==================== سیستم اجرای ۵ دقیقه‌ای مقیاس بالا ====================

class ExecutionStatus(Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    COMPLETED = "completed"
    TIMEOUT = "timeout"
    ERROR = "error"

@dataclass
class ExecutionInfo:
    """اطلاعات اجرای ربات"""
    exec_id: str
    bot_id: str
    user_id: int
    status: ExecutionStatus
    started_at: datetime
    deactivation_at: datetime
    process: Optional[subprocess.Popen] = None
    timer: Optional[threading.Timer] = None
    memory_used: int = 0
    cpu_used: float = 0.0

class HighScaleExecutor:
    """سیستم اجرای مقیاس بالا با پشتیبانی از هزاران اجرای همزمان"""
    
    def __init__(self, db: DistributedDatabase):
        self.db = db
        self.active_executions: Dict[str, ExecutionInfo] = {}
        self.lock = threading.RLock()
        self.executor_pool = ThreadPoolExecutor(max_workers=200)
        self.process_pool = ProcessPoolExecutor(max_workers=50)
        self._start_monitor()
        self._start_stats_collector()
    
    def _start_monitor(self):
        """مانیتورینگ خودکار اجراها"""
        def monitor():
            while True:
                try:
                    now = datetime.now()
                    
                    # پیدا کردن ربات‌های منقضی شده
                    expired = self.db.execute('''
                        SELECT id, user_id, token, file_path, folder_path, next_deactivation 
                        FROM bots 
                        WHERE status = 'running' 
                        AND next_deactivation IS NOT NULL 
                        AND next_deactivation <= ?
                    ''', (now.isoformat(),))
                    
                    for bot in expired:
                        self.stop_execution(bot['id'], bot['user_id'])
                    
                    # بروزرسانی آمار روزانه
                    today = datetime.now().date().isoformat()
                    active_bots = len([b for b in self.active_executions.values() if b.status == ExecutionStatus.RUNNING])
                    self.db.execute('''
                        INSERT INTO daily_stats (date, active_bots) 
                        VALUES (?, ?) 
                        ON CONFLICT(date) DO UPDATE SET active_bots = ?
                    ''', (today, active_bots, active_bots))
                    
                    time.sleep(10)
                except Exception as e:
                    print(f"Monitor error: {e}")
                    time.sleep(30)
        
        threading.Thread(target=monitor, daemon=True).start()
    
    def _start_stats_collector(self):
        """جمع‌آوری آمار مصرف منابع"""
        def collect_stats():
            import psutil
            while True:
                try:
                    with self.lock:
                        for bot_id, info in list(self.active_executions.items()):
                            if info.process and info.process.poll() is None:
                                try:
                                    proc = psutil.Process(info.process.pid)
                                    info.memory_used = proc.memory_info().rss // 1024  # KB
                                    info.cpu_used = proc.cpu_percent(interval=0.1)
                                except:
                                    pass
                    time.sleep(5)
                except:
                    time.sleep(10)
        
        threading.Thread(target=collect_stats, daemon=True).start()
    
    def execute_bot(self, bot_id: str, user_id: int, code: str, folder_path: str = None) -> tuple:
        """اجرای ربات با زمان ۵ دقیقه"""
        
        exec_id = str(uuid.uuid4())[:8]
        duration = self.db.get_setting('execution_duration') or 5
        deactivation_time = datetime.now() + timedelta(minutes=duration)
        
        # ذخیره در دیتابیس
        self.db.add_execution(exec_id, user_id, bot_id)
        self.db.execute('''
            UPDATE bots 
            SET status = 'running', 
                last_execution = ?, 
                execution_count = execution_count + 1,
                next_deactivation = ?,
                is_5min_mode = 1
            WHERE id = ?
        ''', (datetime.now().isoformat(), deactivation_time.isoformat(), bot_id))
        
        # ایجاد اطلاعات اجرا
        exec_info = ExecutionInfo(
            exec_id=exec_id,
            bot_id=bot_id,
            user_id=user_id,
            status=ExecutionStatus.RUNNING,
            started_at=datetime.now(),
            deactivation_at=deactivation_time
        )
        
        with self.lock:
            self.active_executions[bot_id] = exec_info
        
        # شروع اجرا در پس‌زمینه
        future = self.executor_pool.submit(self._run_bot_code, bot_id, user_id, exec_id, code, folder_path)
        
        # تنظیم تایمر برای توقف خودکار
        timer = threading.Timer(duration * 60, self._auto_stop, [bot_id, user_id])
        timer.daemon = True
        timer.start()
        
        with self.lock:
            if bot_id in self.active_executions:
                self.active_executions[bot_id].timer = timer
        
        return exec_id, deactivation_time
    
    def _run_bot_code(self, bot_id: str, user_id: int, exec_id: str, code: str, folder_path: str = None):
        """اجرای کد ربات در محیط ایزوله"""
        bot_dir = os.path.join(DIRS['RUNNING'], bot_id)
        os.makedirs(bot_dir, exist_ok=True)
        
        code_path = os.path.join(bot_dir, 'bot_code.py')
        
        # افزودن کد مدیریت تایم‌اوت
        enhanced_code = self._add_timeout_handler(code)
        
        with open(code_path, 'w', encoding='utf-8') as f:
            f.write(enhanced_code)
        
        try:
            process = subprocess.Popen(
                [sys.executable, code_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=folder_path if folder_path else bot_dir,
                text=True,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )
            
            with self.lock:
                if bot_id in self.active_executions:
                    self.active_executions[bot_id].process = process
            
            # دریافت خروجی با تایم‌اوت
            try:
                stdout, stderr = process.communicate(timeout=300)
                output = stdout[:2000] if stdout else "اجرا موفقیت‌آمیز بود"
                error = stderr[:1000] if stderr else None
                
                # محاسبه زمان اجرا
                with self.lock:
                    if bot_id in self.active_executions:
                        duration = int((datetime.now() - self.active_executions[bot_id].started_at).total_seconds())
                        memory = self.active_executions[bot_id].memory_used
                        cpu = self.active_executions[bot_id].cpu_used
                    else:
                        duration, memory, cpu = 0, 0, 0
                
                self.db.update_execution_result(exec_id, 'completed', duration, output, error, memory, cpu)
                
            except subprocess.TimeoutExpired:
                # کشتن فرآیند در صورت تایم‌اوت
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                process.kill()
                self.db.update_execution_result(exec_id, 'timeout', error="زمان اجرا به پایان رسید")
            
        except Exception as e:
            self.db.update_execution_result(exec_id, 'error', error=str(e)[:500])
            self.db.log_error('execution_error', str(e), user_id, bot_id)
        
        finally:
            # پاکسازی فایل‌های موقت
            try:
                shutil.rmtree(bot_dir, ignore_errors=True)
            except:
                pass
            
            with self.lock:
                if bot_id in self.active_executions and self.active_executions[bot_id].status == ExecutionStatus.RUNNING:
                    if self.active_executions[bot_id].timer:
                        try:
                            self.active_executions[bot_id].timer.cancel()
                        except:
                            pass
                    del self.active_executions[bot_id]
    
    def _add_timeout_handler(self, code: str) -> str:
        """افزودن هندلر تایم‌اوت به کد"""
        timeout_handler = '''
# ========== سیستم مدیریت زمان و تایم‌اوت ==========
import signal
import time

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("زمان اجرا به پایان رسید!")

# تنظیم تایم‌اوت 5 دقیقه
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(300)

# =================================================
'''
        return timeout_handler + "\n" + code
    
    def _auto_stop(self, bot_id: str, user_id: int):
        """توقف خودکار ربات"""
        self.stop_execution(bot_id, user_id)
    
    def stop_execution(self, bot_id: str, user_id: int) -> bool:
        """توقف اجرای ربات"""
        with self.lock:
            if bot_id in self.active_executions:
                info = self.active_executions[bot_id]
                
                if info.process and info.process.poll() is None:
                    try:
                        # کشتن فرآیند و زیرفرآیندها
                        if hasattr(os, 'killpg'):
                            os.killpg(os.getpgid(info.process.pid), signal.SIGTERM)
                        info.process.kill()
                    except:
                        pass
                
                if info.timer:
                    try:
                        info.timer.cancel()
                    except:
                        pass
                
                # محاسبه زمان اجرا
                duration = int((datetime.now() - info.started_at).total_seconds())
                
                del self.active_executions[bot_id]
            else:
                duration = 0
        
        # به‌روزرسانی دیتابیس
        self.db.execute('UPDATE bots SET status = "stopped", next_deactivation = NULL WHERE id = ?', (bot_id,))
        self.db.execute('''
            UPDATE executions 
            SET status = "auto_stopped", ended_at = ?, duration = ?
            WHERE bot_id = ? AND status = "running"
        ''', (datetime.now().isoformat(), duration, bot_id))
        
        # اطلاع به کاربر
        try:
            temp_bot = telebot.TeleBot(BOT_TOKEN)
            temp_bot.send_message(user_id, f"⏰ زمان {self.db.get_setting('execution_duration')} دقیقه‌ای ربات شما به پایان رسید!")
        except:
            pass
        
        return True
    
    def get_execution_status(self, bot_id: str) -> dict:
        """دریافت وضعیت اجرا"""
        with self.lock:
            if bot_id in self.active_executions:
                info = self.active_executions[bot_id]
                remaining = (info.deactivation_at - datetime.now()).total_seconds()
                return {
                    'running': True,
                    'remaining_seconds': max(0, int(remaining)),
                    'remaining_minutes': max(0, int(remaining // 60)),
                    'remaining_seconds_part': max(0, int(remaining % 60)),
                    'deactivation_at': info.deactivation_at.isoformat(),
                    'memory_used': info.memory_used,
                    'cpu_used': info.cpu_used
                }
        return {'running': False, 'remaining_seconds': 0}
    
    def get_stats(self) -> dict:
        """دریافت آمار اجراها"""
        with self.lock:
            running = len([e for e in self.active_executions.values() if e.status == ExecutionStatus.RUNNING])
            total_memory = sum(e.memory_used for e in self.active_executions.values())
            avg_cpu = sum(e.cpu_used for e in self.active_executions.values()) / running if running > 0 else 0
            
            return {
                'total_active': len(self.active_executions),
                'running': running,
                'total_memory_mb': total_memory // 1024,
                'average_cpu': round(avg_cpu, 2)
            }

# ==================== سیستم مدیریت پوشه‌های پیشرفته ====================

class AdvancedFolderManager:
    """مدیریت پوشه‌ها با ساختار درختی و پشتیبانی از فایل‌های چندگانه"""
    
    def __init__(self, db: DistributedDatabase):
        self.db = db
        self.locks = defaultdict(threading.RLock)
    
    def create_folder_structure(self, user_id: int, folder_path: str) -> tuple:
        """ایجاد ساختار پوشه با پشتیبانی از مسیرهای تو در تو (مثلاً ditabis/subfolder)"""
        
        # بررسی مسیر
        parts = folder_path.strip('/').split('/')
        current_path = ""
        parent_id = None
        
        for i, part in enumerate(parts):
            current_path = os.path.join(current_path, part) if current_path else part
            
            # بررسی وجود پوشه
            existing = self.db.execute('''
                SELECT id FROM folders WHERE user_id = ? AND folder_name = ? AND parent_id IS ?
            ''', (user_id, part, parent_id))
            
            if existing:
                parent_id = existing[0]['id']
                continue
            
            # ایجاد پوشه جدید
            folder_id = hashlib.md5(f"{user_id}_{current_path}_{time.time()}".encode()).hexdigest()[:12]
            physical_path = os.path.join(DIRS['FOLDERS'], str(user_id), current_path)
            os.makedirs(physical_path, exist_ok=True)
            
            self.db.create_folder(folder_id, user_id, part, physical_path, parent_id)
            parent_id = folder_id
        
        return parent_id, f"ساختار {folder_path} با موفقیت ایجاد شد"
    
    def add_file_to_folder(self, folder_id: str, file_name: str, content: str) -> tuple:
        """افزودن فایل به پوشه"""
        folders = self.db.execute('SELECT * FROM folders WHERE id = ?', (folder_id,))
        if not folders:
            return False, "پوشه یافت نشد"
        
        folder = dict(folders[0])
        file_path = os.path.join(folder['folder_path'], file_name)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # به‌روزرسانی ساختار
            structure = json.loads(folder['structure'])
            structure['files'].append({
                'name': file_name,
                'path': file_path,
                'added_at': datetime.now().isoformat(),
                'size': len(content),
                'type': 'py' if file_name.endswith('.py') else 'other'
            })
            
            # بروزرسانی حجم
            total_size = sum(f.get('size', 0) for f in structure['files'])
            
            self.db.execute('''
                UPDATE folders 
                SET structure = ?, last_used = ?, file_count = file_count + 1, size = ?
                WHERE id = ?
            ''', (json.dumps(structure), datetime.now().isoformat(), total_size, folder_id))
            
            return True, f"فایل {file_name} با موفقیت اضافه شد"
        except Exception as e:
            return False, f"خطا: {str(e)}"
    
    def get_folder_tree(self, user_id: int) -> dict:
        """دریافت ساختار درختی پوشه‌ها"""
        folders = self.db.execute('SELECT * FROM folders WHERE user_id = ?', (user_id,))
        
        tree = {}
        for folder in folders:
            folder = dict(folder)
            parent = folder.get('parent_id')
            if parent not in tree:
                tree[parent] = []
            tree[parent].append(folder)
        
        return tree
    
    def get_folder_content(self, folder_id: str) -> dict:
        """دریافت محتوای کامل پوشه"""
        folders = self.db.execute('SELECT * FROM folders WHERE id = ?', (folder_id,))
        if not folders:
            return None
        
        folder = dict(folders[0])
        structure = json.loads(folder['structure'])
        
        # خواندن محتوای فایل‌ها
        files_content = {}
        for file_info in structure.get('files', []):
            file_path = file_info.get('path')
            if file_path and os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    files_content[file_info['name']] = f.read()
        
        return {
            'info': folder,
            'structure': structure,
            'files_content': files_content
        }
    
    def get_main_code(self, folder_id: str) -> str:
        """دریافت کد اصلی (main.py) از پوشه"""
        folders = self.db.execute('SELECT folder_path FROM folders WHERE id = ?', (folder_id,))
        if not folders:
            return None
        
        main_path = os.path.join(folders[0]['folder_path'], 'main.py')
        if os.path.exists(main_path):
            with open(main_path, 'r', encoding='utf-8') as f:
                return f.read()
        return None

# ==================== سیستم کتابخانه‌های حرفه‌ای ====================

class ProfessionalLibraryManager:
    """مدیریت کتابخانه‌های پیشرفته با پشتیبانی از نصب خودکار و نمایش پیشرفت"""
    
    def __init__(self, db: DistributedDatabase):
        self.db = db
        self.installing = set()
        self.install_lock = threading.Lock()
        self.install_queue = queue.Queue()
        self._start_install_worker()
    
    def _start_install_worker(self):
        """شروع کارگر نصب کتابخانه"""
        def worker():
            while True:
                try:
                    lib_name, chat_id, message_id, bot_instance = self.install_queue.get(timeout=1)
                    self._install_library(lib_name, chat_id, message_id, bot_instance)
                    self.install_queue.task_done()
                except queue.Empty:
                    time.sleep(0.5)
                except Exception as e:
                    print(f"Install worker error: {e}")
        
        threading.Thread(target=worker, daemon=True).start()
    
    def _install_library(self, lib_name: str, chat_id: int, message_id: int, bot_instance):
        """نصب کتابخانه با نمایش پیشرفت"""
        
        if lib_name in self.installing:
            try:
                bot_instance.edit_message_text(f"⏳ {lib_name} در حال نصب است...", chat_id, message_id)
            except:
                pass
            return
        
        with self.install_lock:
            self.installing.add(lib_name)
        
        try:
            bot_instance.edit_message_text(f"📦 در حال نصب {lib_name}...", chat_id, message_id)
            
            # نصب با نمایش پیشرفت
            process = subprocess.Popen(
                [sys.executable, '-m', 'pip', 'install', lib_name, '--no-cache-dir'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(timeout=180)
            
            if process.returncode == 0:
                # دریافت نسخه
                version = self._get_version(lib_name)
                size = self._get_package_size(lib_name)
                description = self._get_description(lib_name)
                
                # ذخیره در دیتابیس
                self.db.execute('''
                    INSERT OR REPLACE INTO libraries (name, version, description, size, installed_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (lib_name, version, description, size, datetime.now().isoformat()))
                
                bot_instance.edit_message_text(
                    f"✅ **{lib_name}** با موفقیت نصب شد!\n\n"
                    f"📌 **نسخه:** {version}\n"
                    f"📦 **حجم:** {size // 1024} KB\n"
                    f"📝 **توضیحات:** {description[:200]}\n\n"
                    f"کتابخانه نصب شد و در تمام ربات‌ها قابل استفاده است.",
                    chat_id, message_id,
                    parse_mode='Markdown'
                )
            else:
                error = stderr[:500] if stderr else "خطای ناشناخته"
                bot_instance.edit_message_text(
                    f"❌ **خطا در نصب {lib_name}**\n\n```\n{error}\n```\n"
                    f"لطفاً نام کتابخانه را بررسی کنید.",
                    chat_id, message_id,
                    parse_mode='Markdown'
                )
        except subprocess.TimeoutExpired:
            process.kill()
            bot_instance.edit_message_text(f"❌ زمان نصب {lib_name} به پایان رسید", chat_id, message_id)
        except Exception as e:
            bot_instance.edit_message_text(f"❌ خطا: {str(e)[:200]}", chat_id, message_id)
        finally:
            with self.install_lock:
                self.installing.discard(lib_name)
    
    def _get_version(self, lib_name: str) -> str:
        """دریافت نسخه کتابخانه"""
        try:
            result = subprocess.run([sys.executable, '-m', 'pip', 'show', lib_name],
                                   capture_output=True, text=True, timeout=10)
            for line in result.stdout.split('\n'):
                if line.startswith('Version:'):
                    return line.split(':', 1)[1].strip()
        except:
            pass
        return "نامشخص"
    
    def _get_package_size(self, lib_name: str) -> int:
        """دریافت حجم کتابخانه"""
        try:
            result = subprocess.run([sys.executable, '-m', 'pip', 'show', lib_name],
                                   capture_output=True, text=True, timeout=10)
            for line in result.stdout.split('\n'):
                if line.startswith('Size:'):
                    return int(line.split(':', 1)[1].strip())
        except:
            pass
        return 0
    
    def _get_description(self, lib_name: str) -> str:
        """دریافت توضیحات کتابخانه"""
        try:
            result = subprocess.run([sys.executable, '-m', 'pip', 'show', lib_name],
                                   capture_output=True, text=True, timeout=10)
            in_summary = False
            for line in result.stdout.split('\n'):
                if line.startswith('Summary:'):
                    return line.split(':', 1)[1].strip()
        except:
            pass
        return "توضیحات موجود نیست"
    
    def get_available_libraries(self) -> dict:
        """لیست کتابخانه‌های موجود با دسته‌بندی"""
        return {
            '🌐 **فریمورک‌های وب**': {
                'Flask': 'flask',
                'FastAPI': 'fastapi',
                'Django': 'django',
                'Sanic': 'sanic',
            },
            '⚡ **کتابخانه‌های Async**': {
                'aiohttp': 'aiohttp',
                'httpx': 'httpx',
                'aiogram': 'aiogram',
                'asyncio': 'asyncio',
            },
            '🗄️ **دیتابیس‌ها**': {
                'SQLAlchemy': 'sqlalchemy',
                'asyncpg': 'asyncpg',
                'redis': 'redis',
                'motor': 'motor',
            },
            '📊 **دیتا ساینس**': {
                'numpy': 'numpy',
                'pandas': 'pandas',
                'matplotlib': 'matplotlib',
                'scikit-learn': 'scikit-learn',
            },
            '🤖 **ربات تلگرام**': {
                'pyTelegramBotAPI': 'pyTelegramBotAPI',
                'python-telegram-bot': 'python-telegram-bot',
                'aiogram 3.x': 'aiogram',
            },
            '🛠️ **ابزارها**': {
                'requests': 'requests',
                'beautifulsoup4': 'beautifulsoup4',
                'selenium': 'selenium',
                'Pillow': 'Pillow',
                'jdatetime': 'jdatetime',
                'cryptography': 'cryptography',
                'loguru': 'loguru',
                'tqdm': 'tqdm',
            },
            '📈 **ماشین لرنینگ**': {
                'tensorflow': 'tensorflow',
                'torch': 'torch',
                'transformers': 'transformers',
            }
        }
    
    def queue_install(self, lib_name: str, chat_id: int, message_id: int, bot_instance):
        """افزودن به صف نصب"""
        self.install_queue.put((lib_name, chat_id, message_id, bot_instance))
        return True

# ==================== ربات اصلی با معماری پیشرفته ====================

# راه‌اندازی دیتابیس توزیع شده
db = DistributedDatabase()

# راه‌اندازی سیستم اجرا
executor = HighScaleExecutor(db)

# راه‌اندازی مدیریت پوشه‌ها
folder_manager = AdvancedFolderManager(db)

# راه‌اندازی مدیریت کتابخانه‌ها
library_manager = ProfessionalLibraryManager(db)

# راه‌اندازی ربات
bot = telebot.TeleBot(BOT_TOKEN)
bot.delete_webhook()

# ==================== توابع کمکی ====================

def get_user(user_id: int):
    return db.get_user(user_id)

def create_user(user_id: int, username: str, first_name: str, last_name: str, referred_by: int = None):
    return db.create_user(user_id, username, first_name, last_name, referred_by)

def check_subscription(user_id: int) -> bool:
    return db.check_subscription(user_id)

def extract_token_from_code(code: str) -> str:
    patterns = [
        r'token\s*=\s*["\']([^"\']+)["\']',
        r'TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'BOT_TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'API_TOKEN\s*=\s*["\']([^"\']+)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, code, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

def verify_bot_token(token: str) -> tuple:
    try:
        resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('ok'):
                return True, data.get('result', {})
        return False, {}
    except:
        return False, {}

# ==================== منوی اصلی ====================

def get_main_menu(user_id: int):
    is_admin = user_id in ADMIN_IDS
    has_subscription = check_subscription(user_id)
    
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = []
    
    if has_subscription:
        buttons = [
            types.KeyboardButton('🤖 ساخت ربات جدید'),
            types.KeyboardButton('📁 مدیریت پوشه‌ها'),
            types.KeyboardButton('▶️ اجرای ربات (۵ دقیقه)'),
            types.KeyboardButton('📋 لیست ربات‌ها'),
            types.KeyboardButton('🔄 توقف ربات'),
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
        buttons.extend([
            types.KeyboardButton('👑 پنل مدیریت'),
            types.KeyboardButton('📢 پیام همگانی'),
            types.KeyboardButton('⚙️ تنظیمات پیشرفته')
        ])
    
    markup.add(*buttons)
    return markup

# ==================== دستور start ====================

@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or ""
    username = message.from_user.username or ""
    
    # پردازش کد معرف
    referred_by = None
    args = message.text.split()
    if len(args) > 1:
        code = args[1]
        users = db.execute("SELECT user_id FROM users WHERE referral_code = ?", (code,))
        if users and users[0]['user_id'] != user_id:
            referred_by = users[0]['user_id']
            try:
                bot.send_message(referred_by, f"🎉 {first_name} با لینک شما وارد شد!")
            except:
                pass
    
    create_user(user_id, username, first_name, message.from_user.last_name or "", referred_by)
    user = get_user(user_id)
    
    # ارسال پیام خوش‌آمدگویی
    welcome_msg = db.get_message('welcome', {'first_name': first_name})
    
    text = f"{welcome_msg}\n\n"
    text += f"👤 نام: {first_name}\n"
    text += f"🆔 شناسه: `{user_id}`\n"
    text += f"🎁 کد معرف: `{user['referral_code']}`\n"
    text += f"💰 موجودی: {user['wallet_balance']:,} تومان\n"
    
    if check_subscription(user_id):
        expiry = datetime.fromisoformat(user['subscription_expiry'])
        text += f"✅ اشتراک فعال تا: {expiry.strftime('%Y-%m-%d')}\n"
        text += f"🤖 ربات ساخته شده: {db.get_user_bots_count(user_id)}/{db.get_setting('max_bots_per_user')}\n"
    else:
        text += f"❌ اشتراک: غیرفعال\n"
        text += f"💰 قیمت اشتراک: {db.get_setting('subscription_price_str')}"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=get_main_menu(user_id))

# ==================== خرید اشتراک و ساخت ربات ====================

@bot.message_handler(func=lambda m: m.text == '💰 خرید اشتراک')
def buy_subscription(message):
    user_id = message.from_user.id
    
    if check_subscription(user_id):
        bot.send_message(message.chat.id, "✅ شما قبلاً اشتراک فعال دارید!")
        return
    
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

⏱ **زمان بررسی:** حداکثر ۲۴ ساعت

💡 پس از فعال‌سازی اشتراک، می‌توانید ربات خود را بسازید.
    """
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '🤖 ساخت ربات جدید')
def new_bot(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or ""
    
    if not check_subscription(user_id):
        # ارسال پیام شفاف برای کاربر
        text = db.get_message('build_instruction', {
            'first_name': first_name,
            'price': db.get_setting('subscription_price_str'),
            'card': db.get_setting('card_number_display'),
            'holder': db.get_setting('card_holder'),
            'bank': db.get_setting('card_bank')
        })
        bot.send_message(message.chat.id, text, parse_mode='Markdown')
        return
    
    can_create, max_bots, current_bots = db.can_create_bot(user_id)
    if not can_create:
        bot.send_message(message.chat.id, 
                        f"⚠️ **شما به حداکثر مجاز {max_bots} ربات رسیده‌اید!**\n\n"
                        f"برای ساخت ربات جدید، ابتدا یکی از ربات‌های خود را حذف کنید.\n"
                        f"از منوی `🗑 حذف ربات` استفاده کنید.",
                        parse_mode='Markdown')
        return
    
    bot.send_message(message.chat.id, 
                    f"🌟 **ساخت ربات جدید**\n\n"
                    f"کاربر گرامی {first_name}\n\n"
                    f"📌 **مراحل ساخت:**\n\n"
                    f"1️⃣ فایل `.py` یا `.zip` خود را ارسال کنید\n"
                    f"2️⃣ مطمئن شوید توکن داخل کد شما هست\n"
                    f"3️⃣ پس از ساخت، ربات شما قابل اجراست\n\n"
                    f"✅ **امکانات شما:**\n"
                    f"- حداکثر {max_bots} ربات فعال\n"
                    f"- هر بار اجرا به مدت {db.get_setting('execution_duration')} دقیقه\n"
                    f"- دسترسی به کتابخانه‌های متنوع\n\n"
                    f"📤 **لطفاً فایل خود را ارسال کنید:**",
                    parse_mode='Markdown')

# ==================== دریافت فایل ====================

@bot.message_handler(content_types=['document'])
def handle_build_file(message):
    user_id = message.from_user.id
    
    if not check_subscription(user_id):
        bot.reply_to(message, "❌ اشتراک فعال نیست! ابتدا اشتراک خود را فعال کنید.")
        return
    
    file_name = message.document.file_name
    if not (file_name.endswith('.py') or file_name.endswith('.zip')):
        bot.reply_to(message, "❌ فقط فایل‌های `.py` یا `.zip` مجاز هستند!")
        return
    
    if message.document.file_size > 50 * 1024 * 1024:
        bot.reply_to(message, "❌ حجم فایل بیشتر از ۵۰ مگابایت است!")
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
            bot.edit_message_text("❌ فایل پایتون در آرشیو پیدا نشد!", message.chat.id, status_msg.message_id)
            return
        
        token = extract_token_from_code(code)
        if not token:
            bot.edit_message_text("❌ توکن در کد پیدا نشد!\nلطفاً `token = 'YOUR_TOKEN'` را اضافه کنید.", 
                                message.chat.id, status_msg.message_id, parse_mode='Markdown')
            return
        
        valid, bot_info = verify_bot_token(token)
        if not valid:
            bot.edit_message_text("❌ توکن نامعتبر است! لطفاً توکن معتبر وارد کنید.", 
                                message.chat.id, status_msg.message_id)
            return
        
        # ایجاد ربات
        bot_id = hashlib.md5(f"{user_id}{token}{time.time()}".encode()).hexdigest()[:16]
        db.add_bot(bot_id, user_id, token, bot_info.get('first_name', 'ربات'), 
                  bot_info.get('username', ''), file_path)
        
        # اجرای خودکار
        exec_id, deactivation_time = executor.execute_bot(bot_id, user_id, code)
        
        bot.edit_message_text(
            f"✅ **ربات با موفقیت ساخته و اجرا شد!**\n\n"
            f"🤖 نام: `{bot_info.get('first_name', 'ربات')}`\n"
            f"🔗 آیدی: @{bot_info.get('username', '')}\n"
            f"🆔 شناسه: `{bot_id}`\n\n"
            f"⏱ **زمان اجرا:** {db.get_setting('execution_duration')} دقیقه\n"
            f"⏰ **غیرفعال‌سازی:** {deactivation_time.strftime('%H:%M:%S')}\n\n"
            f"پس از اتمام زمان، ربات خودکار متوقف می‌شود.\n"
            f"برای اجرای مجدد از منوی `▶️ اجرای ربات` استفاده کنید.",
            message.chat.id,
            status_msg.message_id,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)[:200]}", message.chat.id, status_msg.message_id)
        db.log_error('build_error', str(e), user_id)

# ==================== رسید پرداخت ====================

@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    
    # بررسی فیش تکراری
    pending = db.execute("SELECT id FROM receipts WHERE user_id = ? AND status = 'pending'", (user_id,))
    if pending:
        bot.reply_to(message, "⏳ فیش قبلی شما در انتظار تایید است. لطفاً صبور باشید.")
        return
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        payment_code = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:8].upper()
        receipt_path = os.path.join(DIRS['RECEIPTS'], f"{user_id}_{payment_code}.jpg")
        
        with open(receipt_path, 'wb') as f:
            f.write(downloaded)
        
        transaction_id = hashlib.sha256(f"{user_id}_{payment_code}_{time.time()}".encode()).hexdigest()[:16]
        
        db.execute('''
            INSERT INTO receipts (user_id, amount, receipt_path, payment_code, transaction_id, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
        ''', (user_id, db.get_setting('subscription_price'), receipt_path, payment_code, transaction_id, datetime.now().isoformat()))
        
        bot.reply_to(message, 
                    f"✅ **فیش شما دریافت شد!**\n\n"
                    f"💰 مبلغ: {db.get_setting('subscription_price_str')}\n"
                    f"🆔 کد پیگیری: `{payment_code}`\n"
                    f"🔑 شناسه تراکنش: `{transaction_id}`\n\n"
                    f"⏱ ظرف ۲۴ ساعت بررسی و نتیجه به شما اعلام می‌شود.\n\n"
                    f"پس از تایید، اشتراک شما فعال خواهد شد.",
                    parse_mode='Markdown')
        
        # اطلاع به ادمین‌ها
        user = get_user(user_id)
        for admin_id in ADMIN_IDS:
            try:
                with open(receipt_path, 'rb') as f:
                    bot.send_photo(admin_id, f, 
                                  caption=f"📸 **فیش جدید**\n\n"
                                         f"👤 کاربر: {user['first_name']}\n"
                                         f"🆔 آیدی: `{user_id}`\n"
                                         f"💰 مبلغ: {db.get_setting('subscription_price_str')}\n"
                                         f"🆔 کد: `{payment_code}`\n"
                                         f"🔑 تراکنش: `{transaction_id}`",
                                  parse_mode='Markdown')
            except:
                pass
                
    except Exception as e:
        bot.reply_to(message, f"❌ خطا در دریافت فیش: {str(e)}")
        db.log_error('receipt_error', str(e), user_id)

# ==================== پیام تایید اشتراک ====================

def send_subscription_activated_message(user_id: int):
    """ارسال پیام تایید اشتراک با توضیحات کامل"""
    user = get_user(user_id)
    first_name = user['first_name'] if user else 'کاربر'
    max_bots = db.get_setting('max_bots_per_user')
    duration = db.get_setting('execution_duration')
    
    # ارسال پیام فعال‌سازی
    text = db.get_message('subscription_activated', {
        'first_name': first_name,
        'max_bots': max_bots,
        'duration': duration
    })
    
    bot.send_message(user_id, text, parse_mode='Markdown')
    
    # ارسال پیام اضافی با توضیحات ساخت
    extra_text = f"""
📌 **نحوه ساخت ربات:**

**روش اول - ارسال فایل:**
• فایل `.py` یا `.zip` خود را ارسال کنید
• مطمئن شوید توکن داخل کد شما هست

**روش دوم - ساخت پوشه:**
1️⃣ از منوی `📁 مدیریت پوشه‌ها` استفاده کنید
2️⃣ یک پوشه جدید با نام دلخواه بسازید
3️⃣ فایل‌های خود را داخل پوشه آپلود کنید
4️⃣ کد اصلی را با نام `main.py` ذخیره کنید
5️⃣ از دکمه اجرا برای راه‌اندازی استفاده کنید

⚠️ **نکات مهم:**
• توکن ربات حتماً داخل کد شما باشد
• هر بار اجرا {duration} دقیقه است
• حداکثر {max_bots} ربات فعال می‌توانید داشته باشید

**موفق باشید! 🚀**
"""
    
    bot.send_message(user_id, extra_text, parse_mode='Markdown')

# ==================== مدیریت پوشه‌ها ====================

@bot.message_handler(func=lambda m: m.text == '📁 مدیریت پوشه‌ها')
def manage_folders(message):
    user_id = message.from_user.id
    
    if not check_subscription(user_id):
        bot.send_message(message.chat.id, "❌ ابتدا اشتراک خود را فعال کنید!")
        return
    
    folders = db.execute("SELECT id, folder_name FROM folders WHERE user_id = ?", (user_id,))
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("📁➕ ساخت پوشه جدید", callback_data="create_folder"))
    markup.add(types.InlineKeyboardButton("📁➕ ساخت پوشه تو در تو", callback_data="create_nested_folder"))
    
    if folders:
        markup.add(types.InlineKeyboardButton("📂 لیست پوشه‌های من", callback_data="list_folders"))
    
    bot.send_message(message.chat.id, 
                    "📁 **مدیریت پوشه‌ها**\n\n"
                    "می‌توانید پوشه‌های خود را مدیریت کنید.\n"
                    "در هر پوشه می‌توانید چندین فایل پایتون قرار دهید.\n\n"
                    "💡 **نکته:** برای ساخت پوشه تو در تو (مثل `mybot/subfolder`)، "
                    "از گزینه ساخت پوشه تو در تو استفاده کنید.",
                    parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "create_folder")
def create_folder_prompt(call):
    msg = bot.send_message(call.message.chat.id, "📁 **نام پوشه جدید را وارد کنید:**\n(فقط حروف انگلیسی و عدد)")
    bot.register_next_step_handler(msg, process_create_folder)
    bot.answer_callback_query(call.id)

def process_create_folder(message):
    user_id = message.from_user.id
    folder_name = message.text.strip()
    
    if not re.match(r'^[a-zA-Z0-9_\-]+$', folder_name):
        bot.reply_to(message, "❌ نام پوشه فقط می‌تواند شامل حروف انگلیسی، اعداد، خط تیره و زیرخط باشد.")
        return
    
    folder_id, result = folder_manager.create_folder_structure(user_id, folder_name)
    
    if folder_id:
        bot.reply_to(message, f"✅ پوشه `{folder_name}` با موفقیت ساخته شد!\n\n🆔 آیدی پوشه: `{folder_id}`", parse_mode='Markdown')
    else:
        bot.reply_to(message, f"❌ {result}")

@bot.callback_query_handler(func=lambda call: call.data == "create_nested_folder")
def create_nested_prompt(call):
    msg = bot.send_message(call.message.chat.id, 
                          "📁 **مسیر پوشه تو در تو را وارد کنید:**\n"
                          "مثال: `mybot/subfolder/subsub`\n\n"
                          "💡 با این کار، تمام پوشه‌های مسیر ساخته می‌شوند.")
    bot.register_next_step_handler(msg, process_create_nested_folder)
    bot.answer_callback_query(call.id)

def process_create_nested_folder(message):
    user_id = message.from_user.id
    folder_path = message.text.strip()
    
    if not re.match(r'^[a-zA-Z0-9_\-/]+$', folder_path):
        bot.reply_to(message, "❌ مسیر نامعتبر! فقط حروف انگلیسی، اعداد، خط تیره و اسلش مجاز است.")
        return
    
    folder_id, result = folder_manager.create_folder_structure(user_id, folder_path)
    
    if folder_id:
        bot.reply_to(message, f"✅ ساختار `{folder_path}` با موفقیت ایجاد شد!\n\n🆔 آیدی آخرین پوشه: `{folder_id}`", parse_mode='Markdown')
    else:
        bot.reply_to(message, f"❌ {result}")

@bot.callback_query_handler(func=lambda call: call.data == "list_folders")
def list_folders(call):
    user_id = call.from_user.id
    folders = db.execute("SELECT id, folder_name, parent_id, file_count FROM folders WHERE user_id = ? ORDER BY created_at", (user_id,))
    
    if not folders:
        bot.send_message(call.message.chat.id, "📂 شما هیچ پوشه‌ای ندارید.")
        return
    
    # ساخت درخت پوشه‌ها
    folder_tree = {}
    for folder in folders:
        parent = folder['parent_id'] or 'root'
        if parent not in folder_tree:
            folder_tree[parent] = []
        folder_tree[parent].append(folder)
    
    def build_tree(parent_id, level=0):
        result = []
        indent = "  " * level
        for folder in folder_tree.get(parent_id, []):
            result.append(f"{indent}📂 {folder['folder_name']} ({folder['file_count']} فایل)")
            result.extend(build_tree(folder['id'], level + 1))
        return result
    
    tree_text = "\n".join(build_tree('root'))
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for folder in folders:
        markup.add(types.InlineKeyboardButton(f"📂 {folder['folder_name']}", callback_data=f"view_folder_{folder['id']}"))
    
    bot.edit_message_text(f"📂 **پوشه‌های شما:**\n\n{tree_text}\n\nبرای مشاهده محتوا روی پوشه کلیک کنید.", 
                         call.message.chat.id, call.message.message_id,
                         parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('view_folder_'))
def view_folder(call):
    folder_id = call.data.replace('view_folder_', '')
    content = folder_manager.get_folder_content(folder_id)
    
    if not content:
        bot.answer_callback_query(call.id, "پوشه یافت نشد!")
        return
    
    folder = content['info']
    structure = content['structure']
    files = structure.get('files', [])
    
    text = f"📁 **{folder['folder_name']}**\n\n"
    text += f"🆔 آیدی: `{folder_id}`\n"
    text += f"📅 ساخته شده: {folder['created_at'][:16]}\n"
    text += f"📄 تعداد فایل‌ها: {len(files)}\n"
    
    if folder.get('size'):
        text += f"📦 حجم کل: {folder['size'] // 1024} KB\n"
    
    text += "\n"
    
    if files:
        text += "**📄 فایل‌ها:**\n"
        for f in files:
            text += f"• `{f['name']}` ({f['size']} بایت) - {f['added_at'][:16]}\n"
    else:
        text += "📂 هیچ فایلی در این پوشه وجود ندارد.\n"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("📄 افزودن فایل", callback_data=f"add_file_{folder_id}"))
    markup.add(types.InlineKeyboardButton("📂 افزودن زیرپوشه", callback_data=f"add_subfolder_{folder_id}"))
    markup.add(types.InlineKeyboardButton("▶️ اجرا به عنوان ربات", callback_data=f"run_folder_bot_{folder_id}"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="list_folders"))
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                         parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('add_file_'))
def add_file_prompt(call):
    folder_id = call.data.replace('add_file_', '')
    msg = bot.send_message(call.message.chat.id, "📄 **نام فایل را وارد کنید:**\n(مثال: main.py)")
    bot.register_next_step_handler(msg, process_add_file_name, folder_id)
    bot.answer_callback_query(call.id)

def process_add_file_name(message, folder_id):
    file_name = message.text.strip()
    
    if not file_name.endswith('.py'):
        bot.reply_to(message, "❌ فقط فایل‌های پایتون (.py) مجاز هستند.")
        return
    
    msg = bot.send_message(message.chat.id, f"📝 **محتوای فایل {file_name} را ارسال کنید:**\n(کد پایتون خود را بنویسید)")
    bot.register_next_step_handler(msg, process_add_file_content, folder_id, file_name)

def process_add_file_content(message, folder_id, file_name):
    content = message.text
    
    success, result = folder_manager.add_file_to_folder(folder_id, file_name, content)
    
    if success:
        bot.reply_to(message, f"✅ فایل `{file_name}` با موفقیت اضافه شد!\n\n"
                    f"برای اجرای ربات، از دکمه `▶️ اجرا به عنوان ربات` استفاده کنید.",
                    parse_mode='Markdown')
    else:
        bot.reply_to(message, f"❌ {result}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('add_subfolder_'))
def add_subfolder_prompt(call):
    parent_id = call.data.replace('add_subfolder_', '')
    msg = bot.send_message(call.message.chat.id, "📁 **نام زیرپوشه را وارد کنید:**")
    bot.register_next_step_handler(msg, process_add_subfolder, parent_id)
    bot.answer_callback_query(call.id)

def process_add_subfolder(message, parent_id):
    user_id = message.from_user.id
    folder_name = message.text.strip()
    
    if not re.match(r'^[a-zA-Z0-9_\-]+$', folder_name):
        bot.reply_to(message, "❌ نام نامعتبر!")
        return
    
    # دریافت مسیر کامل از پدر
    parent = db.execute("SELECT folder_path, folder_name FROM folders WHERE id = ?", (parent_id,))
    if not parent:
        bot.reply_to(message, "❌ پوشه والد یافت نشد!")
        return
    
    full_path = os.path.join(parent[0]['folder_path'], folder_name)
    folder_id, result = folder_manager.create_folder_structure(user_id, full_path)
    
    if folder_id:
        bot.reply_to(message, f"✅ زیرپوشه `{folder_name}` با موفقیت ایجاد شد!", parse_mode='Markdown')
    else:
        bot.reply_to(message, f"❌ {result}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('run_folder_bot_'))
def run_folder_bot(call):
    user_id = call.from_user.id
    folder_id = call.data.replace('run_folder_bot_', '')
    
    if not check_subscription(user_id):
        bot.answer_callback_query(call.id, "اشتراک شما فعال نیست!", show_alert=True)
        return
    
    can_create, max_bots, current_bots = db.can_create_bot(user_id)
    if not can_create:
        bot.answer_callback_query(call.id, f"شما حداکثر {max_bots} ربات می‌توانید داشته باشید!", show_alert=True)
        return
    
    # خواندن کد اصلی
    code = folder_manager.get_main_code(folder_id)
    if not code:
        bot.answer_callback_query(call.id, "فایل main.py در پوشه یافت نشد!", show_alert=True)
        return
    
    token = extract_token_from_code(code)
    if not token:
        bot.answer_callback_query(call.id, "توکن در کد پیدا نشد!", show_alert=True)
        return
    
    valid, bot_info = verify_bot_token(token)
    if not valid:
        bot.answer_callback_query(call.id, "توکن نامعتبر است!", show_alert=True)
        return
    
    # دریافت مسیر پوشه
    folders = db.execute("SELECT folder_path FROM folders WHERE id = ?", (folder_id,))
    folder_path = folders[0]['folder_path'] if folders else None
    
    # ایجاد ربات
    bot_id = hashlib.md5(f"{user_id}_{token}_{time.time()}".encode()).hexdigest()[:16]
    db.add_bot(bot_id, user_id, token, bot_info.get('first_name', 'ربات'), 
              bot_info.get('username', ''), None, folder_path, folder_id)
    
    # اجرای ربات
    exec_id, deactivation_time = executor.execute_bot(bot_id, user_id, code, folder_path)
    
    bot.answer_callback_query(call.id, "✅ ربات با موفقیت اجرا شد!", show_alert=True)
    
    bot.edit_message_text(
        f"✅ **ربات از پوشه با موفقیت اجرا شد!**\n\n"
        f"🤖 نام: `{bot_info.get('first_name', 'ربات')}`\n"
        f"🔗 آیدی: @{bot_info.get('username', '')}\n"
        f"🆔 شناسه: `{bot_id}`\n\n"
        f"⏱ **زمان اجرا:** {db.get_setting('execution_duration')} دقیقه\n"
        f"⏰ **غیرفعال‌سازی:** {deactivation_time.strftime('%H:%M:%S')}\n\n"
        f"پس از اتمام زمان، ربات خودکار متوقف می‌شود.",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown'
    )

# ==================== اجرای ربات ====================

@bot.message_handler(func=lambda m: m.text == '▶️ اجرای ربات (۵ دقیقه)')
def run_bot_prompt(message):
    user_id = message.from_user.id
    
    if not check_subscription(user_id):
        bot.send_message(message.chat.id, "❌ ابتدا اشتراک خود را فعال کنید!")
        return
    
    bots = db.execute("SELECT id, name, username, status FROM bots WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما هیچ رباتی ندارید!\nاز دکمه `🤖 ساخت ربات جدید` استفاده کنید.", parse_mode='Markdown')
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        status = executor.get_execution_status(b['id'])
        status_emoji = "🟢" if status['running'] else "🔴"
        status_text = f"({status['remaining_seconds']}s)" if status['running'] else ""
        markup.add(types.InlineKeyboardButton(f"{status_emoji} {b['name']} {status_text}", callback_data=f"execute_bot_{b['id']}"))
    
    bot.send_message(message.chat.id, 
                    "▶️ **انتخاب ربات برای اجرا:**\n\n"
                    f"⚠️ **توجه:** هر بار اجرا به مدت {db.get_setting('execution_duration')} دقیقه است.\n"
                    "پس از اتمام زمان، ربات خودکار متوقف می‌شود.\n\n"
                    "🟢 در حال اجرا | 🔴 متوقف",
                    parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('execute_bot_'))
def execute_bot(call):
    user_id = call.from_user.id
    bot_id = call.data.replace('execute_bot_', '')
    
    if not check_subscription(user_id):
        bot.answer_callback_query(call.id, "اشتراک شما فعال نیست!", show_alert=True)
        return
    
    status = executor.get_execution_status(bot_id)
    if status['running']:
        bot.answer_callback_query(call.id, 
                                 f"ربات در حال اجراست!\n⏱ زمان باقیمانده: {status['remaining_minutes']}:{status['remaining_seconds_part']:02d}",
                                 show_alert=True)
        return
    
    # دریافت اطلاعات ربات
    bot_info = db.execute("SELECT * FROM bots WHERE id = ? AND user_id = ?", (bot_id, user_id))
    if not bot_info:
        bot.answer_callback_query(call.id, "ربات یافت نشد!", show_alert=True)
        return
    
    bot_info = dict(bot_info[0])
    
    # خواندن کد
    code = None
    if bot_info.get('folder_path') and os.path.exists(bot_info['folder_path']):
        main_path = os.path.join(bot_info['folder_path'], 'main.py')
        if os.path.exists(main_path):
            with open(main_path, 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
    elif bot_info.get('file_path') and os.path.exists(bot_info['file_path']):
        with open(bot_info['file_path'], 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()
    
    if not code:
        bot.answer_callback_query(call.id, "فایل ربات یافت نشد!", show_alert=True)
        return
    
    # اجرا
    exec_id, deactivation_time = executor.execute_bot(bot_id, user_id, code, bot_info.get('folder_path'))
    
    bot.answer_callback_query(call.id, f"✅ ربات با موفقیت اجرا شد!\n⏱ زمان: {db.get_setting('execution_duration')} دقیقه", show_alert=True)
    
    bot.edit_message_text(
        f"✅ **ربات `{bot_info['name']}` در حال اجراست!**\n\n"
        f"⏱ **مدت زمان:** {db.get_setting('execution_duration')} دقیقه\n"
        f"⏰ **غیرفعال‌سازی:** {deactivation_time.strftime('%H:%M:%S')}\n\n"
        f"پس از اتمام زمان، ربات خودکار متوقف می‌شود.\n"
        f"برای توقف زودهنگام از منوی `🔄 توقف ربات` استفاده کنید.",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown'
    )

# ==================== لیست ربات‌ها ====================

@bot.message_handler(func=lambda m: m.text == '📋 لیست ربات‌ها')
def list_bots(message):
    user_id = message.from_user.id
    bots = db.execute("SELECT id, name, username, status, execution_count, created_at FROM bots WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما هیچ رباتی ندارید!\nاز دکمه `🤖 ساخت ربات جدید` استفاده کنید.", parse_mode='Markdown')
        return
    
    text = "🤖 **لیست ربات‌های شما**\n\n"
    for b in bots:
        status = executor.get_execution_status(b['id'])
        if status['running']:
            status_text = f"🟢 در حال اجرا ({status['remaining_minutes']}:{status['remaining_seconds_part']:02d})"
        else:
            status_text = "🔴 متوقف"
        
        text += f"**{b['name']}**\n"
        text += f"🆔 `{b['id'][:8]}...`\n"
        text += f"🔗 t.me/{b['username']}\n"
        text += f"📊 وضعیت: {status_text}\n"
        text += f"▶️ تعداد اجرا: {b['execution_count']}\n"
        text += f"📅 ساخته شده: {b['created_at'][:16]}\n\n"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== توقف ربات ====================

@bot.message_handler(func=lambda m: m.text == '🔄 توقف ربات')
def stop_bot_prompt(message):
    user_id = message.from_user.id
    bots = db.execute("SELECT id, name FROM bots WHERE user_id = ? AND status = 'running'", (user_id,))
    
    if not bots:
        bot.send_message(message.chat.id, "📋 هیچ ربات در حال اجرایی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        status = executor.get_execution_status(b['id'])
        remaining = f" ({status['remaining_seconds']}s)" if status['running'] else ""
        markup.add(types.InlineKeyboardButton(f"🛑 {b['name']}{remaining}", callback_data=f"stop_bot_{b['id']}"))
    
    bot.send_message(message.chat.id, "🛑 **ربات مورد نظر برای توقف:**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('stop_bot_'))
def stop_bot(call):
    bot_id = call.data.replace('stop_bot_', '')
    user_id = call.from_user.id
    executor.stop_execution(bot_id, user_id)
    bot.answer_callback_query(call.id, "✅ ربات متوقف شد!")
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== حذف ربات ====================

@bot.message_handler(func=lambda m: m.text == '🗑 حذف ربات')
def delete_bot_prompt(message):
    user_id = message.from_user.id
    bots = db.execute("SELECT id, name FROM bots WHERE user_id = ?", (user_id,))
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما هیچ رباتی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        markup.add(types.InlineKeyboardButton(f"🗑 {b['name']}", callback_data=f"delete_bot_{b['id']}"))
    
    bot.send_message(message.chat.id, "🗑 **ربات مورد نظر برای حذف:**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_bot_'))
def confirm_delete_bot(call):
    bot_id = call.data.replace('delete_bot_', '')
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ بله، حذف شود", callback_data=f"confirm_del_{bot_id}"),
              types.InlineKeyboardButton("❌ انصراف", callback_data="cancel_del"))
    
    bot.edit_message_text("⚠️ **آیا از حذف این ربات اطمینان دارید؟**\nاین عمل غیرقابل بازگشت است.",
                         call.message.chat.id, call.message.message_id,
                         parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_del_'))
def do_delete_bot(call):
    bot_id = call.data.replace('confirm_del_', '')
    user_id = call.from_user.id
    
    # توقف ربات اگر در حال اجراست
    executor.stop_execution(bot_id, user_id)
    
    # حذف از دیتابیس
    db.delete_bot(bot_id, user_id)
    
    bot.edit_message_text("✅ ربات با موفقیت حذف شد.", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "cancel_del")
def cancel_delete(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== وضعیت اجرا ====================

@bot.message_handler(func=lambda m: m.text == '⚡ وضعیت اجرا')
def execution_status(message):
    user_id = message.from_user.id
    bots = db.execute("SELECT id, name FROM bots WHERE user_id = ?", (user_id,))
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما هیچ رباتی ندارید!")
        return
    
    text = "⚡ **وضعیت اجرای ربات‌ها**\n\n"
    
    for b in bots:
        status = executor.get_execution_status(b['id'])
        if status['running']:
            text += f"🟢 **{b['name']}**\n"
            text += f"   ⏱ زمان باقیمانده: {status['remaining_minutes']}:{status['remaining_seconds_part']:02d}\n"
            text += f"   💾 مصرف حافظه: {status.get('memory_used', 0)} KB\n"
            text += f"   🔥 مصرف CPU: {status.get('cpu_used', 0)}%\n\n"
        else:
            text += f"🔴 **{b['name']}** - متوقف\n\n"
    
    # آمار کلی
    stats = executor.get_stats()
    text += f"\n📊 **آمار سیستم:**\n"
    text += f"🔹 اجراهای فعال: {stats['running']}\n"
    text += f"🔹 کل اجراها: {stats['total_active']}\n"
    text += f"🔹 حافظه مصرفی: {stats['total_memory_mb']} MB\n"
    text += f"🔹 میانگین CPU: {stats['average_cpu']}%"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== کیف پول و دعوت و برداشت ====================

@bot.message_handler(func=lambda m: m.text == '💰 کیف پول')
def wallet(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    text = f"💰 **کیف پول شما**\n\n"
    text += f"👤 {user['first_name']}\n"
    text += f"💵 **موجودی:** {user['wallet_balance']:,} تومان\n"
    text += f"👥 **دعوت‌ها:** {user['referrals_count']} نفر\n"
    text += f"💰 **کمیسیون هر دعوت:** {db.get_setting('withdraw_percent')}%\n"
    text += f"💸 **حداقل برداشت:** {db.get_setting('min_withdraw'):,} تومان\n"
    text += f"💳 **کل هزینه:** {user.get('total_spent', 0):,} تومان"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '👥 دعوت دوستان')
def invite(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    referral_link = f"https://t.me/{BOT_USERNAME}?start={user['referral_code']}"
    
    text = f"👥 **سیستم دعوت دوستان**\n\n"
    text += f"🎁 **کد معرف:** `{user['referral_code']}`\n"
    text += f"🔗 **لینک دعوت:** `{referral_link}`\n"
    text += f"📊 **تعداد دعوت‌ها:** {user['referrals_count']}\n"
    text += f"💰 **کمیسیون هر دعوت:** {db.get_setting('withdraw_percent')}%\n\n"
    text += f"✨ هر دوست که از طریق لینک شما ثبت‌نام کند و اشتراک بخرد، {db.get_setting('withdraw_percent')}% کمیسیون دریافت می‌کنید!"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📋 کپی لینک", callback_data=f"copy_link_{user['referral_code']}"))
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('copy_link_'))
def copy_link(call):
    code = call.data.replace('copy_link_', '')
    link = f"https://t.me/{BOT_USERNAME}?start={code}"
    bot.answer_callback_query(call.id, f"✅ لینک کپی شد!\n{link}", show_alert=True)

@bot.message_handler(func=lambda m: m.text == '💸 درخواست برداشت')
def withdraw_request(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    min_withdraw = db.get_setting('min_withdraw')
    
    if user['wallet_balance'] < min_withdraw:
        bot.send_message(message.chat.id, 
                        f"❌ **موجودی شما کمتر از حداقل برداشت است!**\n\n"
                        f"💰 موجودی شما: {user['wallet_balance']:,} تومان\n"
                        f"💸 حداقل برداشت: {min_withdraw:,} تومان\n\n"
                        f"برای افزایش موجودی، دوستان خود را دعوت کنید.",
                        parse_mode='Markdown')
        return
    
    msg = bot.send_message(message.chat.id, "💳 **شماره کارت خود را وارد کنید:**\n(۱۶ رقم)")
    bot.register_next_step_handler(msg, process_withdraw_card)

def process_withdraw_card(message):
    card = message.text.strip().replace(' ', '')
    if not (len(card) == 16 and card.isdigit()):
        bot.reply_to(message, "❌ شماره کارت باید ۱۶ رقم باشد!")
        return
    
    msg = bot.send_message(message.chat.id, "🏦 **نام بانک را وارد کنید:**")
    bot.register_next_step_handler(msg, process_withdraw_bank, card)

def process_withdraw_bank(message, card):
    bank = message.text.strip()
    msg = bot.send_message(message.chat.id, "👤 **نام صاحب کارت را وارد کنید:**")
    bot.register_next_step_handler(msg, process_withdraw_holder, card, bank)

def process_withdraw_holder(message, card, bank):
    holder = message.text.strip()
    user_id = message.from_user.id
    user = get_user(user_id)
    
    # ایجاد کد رهگیری
    tracking_code = hashlib.md5(f"{user_id}_{card}_{time.time()}".encode()).hexdigest()[:12].upper()
    
    db.execute('''
        INSERT INTO withdraw_requests (user_id, amount, card_number, card_holder, bank_name, tracking_code, created_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
    ''', (user_id, user['wallet_balance'], card, holder, bank, tracking_code, datetime.now().isoformat()))
    
    db.execute('UPDATE users SET wallet_balance = 0 WHERE user_id = ?', (user_id,))
    
    bot.reply_to(message, 
                f"✅ **درخواست برداشت ثبت شد!**\n\n"
                f"💰 مبلغ: {user['wallet_balance']:,} تومان\n"
                f"💳 کارت: {card[:4]}****{card[-4:]}\n"
                f"🏦 بانک: {bank}\n"
                f"🔑 کد رهگیری: `{tracking_code}`\n\n"
                f"پس از بررسی، مبلغ به کارت شما واریز می‌شود.",
                parse_mode='Markdown')
    
    for admin_id in ADMIN_IDS:
        bot.send_message(admin_id, 
                        f"💰 **درخواست برداشت جدید**\n\n"
                        f"👤 کاربر: {user['first_name']}\n"
                        f"🆔 آیدی: {user_id}\n"
                        f"💰 مبلغ: {user['wallet_balance']:,} تومان\n"
                        f"💳 کارت: {card}\n"
                        f"👤 صاحب کارت: {holder}\n"
                        f"🔑 کد رهگیری: {tracking_code}",
                        parse_mode='Markdown')

# ==================== کتابخانه‌های حرفه‌ای ====================

@bot.message_handler(func=lambda m: m.text == '📦 کتابخانه‌ها')
def libraries_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("📚 لیست کتابخانه‌ها", callback_data="lib_list"))
    markup.add(types.InlineKeyboardButton("🔧 نصب کتابخانه دلخواه", callback_data="lib_install_custom"))
    markup.add(types.InlineKeyboardButton("✅ کتابخانه‌های نصب شده", callback_data="lib_installed"))
    markup.add(types.InlineKeyboardButton("📊 آمار کتابخانه‌ها", callback_data="lib_stats"))
    
    bot.send_message(message.chat.id, 
                    "📦 **مدیریت کتابخانه‌های پیشرفته**\n\n"
                    "می‌توانید کتابخانه‌های پایتون را نصب کنید.\n"
                    "کتابخانه‌های نصب شده در تمام ربات‌ها قابل استفاده هستند.\n\n"
                    "💡 **نکته:** نصب کتابخانه در پس‌زمینه انجام می‌شود.",
                    parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "lib_list")
def library_list(call):
    libs = library_manager.get_available_libraries()
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for category, items in libs.items():
        markup.add(types.InlineKeyboardButton(f"{category[:30]}", callback_data=f"lib_cat_{category[:20]}"))
    
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="lib_back"))
    
    bot.edit_message_text("📚 **دسته‌بندی کتابخانه‌ها:**\n\n"
                         "روی هر دسته کلیک کنید تا کتابخانه‌های آن را ببینید.\n"
                         "کتابخانه‌های محبوب و پرکاربرد در هر دسته قرار دارند.",
                         call.message.chat.id, call.message.message_id,
                         parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lib_cat_'))
def library_category(call):
    category_name = call.data.replace('lib_cat_', '')
    libs = library_manager.get_available_libraries()
    
    # پیدا کردن دسته اصلی
    category = None
    for cat, items in libs.items():
        if cat.startswith(category_name) or category_name in cat:
            category = items
            break
    
    if not category:
        bot.answer_callback_query(call.id, "دسته یافت نشد!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for name, lib in category.items():
        # بررسی نصب بودن
        installed = db.execute("SELECT id FROM libraries WHERE name = ?", (lib,))
        status = "✅" if installed else "📦"
        markup.add(types.InlineKeyboardButton(f"{status} {name}", callback_data=f"install_lib_{lib}"))
    
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="lib_list"))
    
    bot.edit_message_text(f"📁 **کتابخانه‌های این دسته:**\n\n"
                         f"✅ = نصب شده | 📦 = قابل نصب\n\n"
                         f"برای نصب روی کتابخانه کلیک کنید:",
                         call.message.chat.id, call.message.message_id,
                         reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('install_lib_'))
def install_library_callback(call):
    lib_name = call.data.replace('install_lib_', '')
    
    status_msg = bot.send_message(call.message.chat.id, f"🔄 در حال آماده‌سازی برای نصب {lib_name}...")
    
    library_manager.queue_install(lib_name, call.message.chat.id, status_msg.message_id, bot)
    bot.answer_callback_query(call.id, f"📦 {lib_name} به صف نصب اضافه شد!")

@bot.callback_query_handler(func=lambda call: call.data == "lib_install_custom")
def install_custom_prompt(call):
    msg = bot.send_message(call.message.chat.id, 
                          "🔧 **نصب کتابخانه دلخواه**\n\n"
                          "نام کتابخانه را وارد کنید:\n"
                          "مثال: `requests`, `numpy`, `django`\n\n"
                          "⚠️ نام کتابخانه باید دقیقاً مطابق با PyPI باشد.")
    bot.register_next_step_handler(msg, process_custom_install)
    bot.answer_callback_query(call.id)

def process_custom_install(message):
    lib_name = message.text.strip().lower()
    status_msg = bot.reply_to(message, f"🔄 در حال آماده‌سازی برای نصب {lib_name}...")
    library_manager.queue_install(lib_name, message.chat.id, status_msg.message_id, bot)

@bot.callback_query_handler(func=lambda call: call.data == "lib_installed")
def installed_libraries(call):
    libs = db.execute("SELECT * FROM libraries ORDER BY installed_at DESC")
    
    if not libs:
        bot.edit_message_text("📦 **کتابخانه‌های نصب شده**\n\n"
                             "هیچ کتابخانه‌ای نصب نشده است.\n"
                             "از منوی اصلی کتابخانه‌ها برای نصب استفاده کنید.",
                             call.message.chat.id, call.message.message_id,
                             parse_mode='Markdown')
        return
    
    text = "✅ **کتابخانه‌های نصب شده**\n\n"
    for lib in libs:
        text += f"**📦 {lib['name']}**\n"
        text += f"   📌 نسخه: `{lib['version']}`\n"
        if lib.get('description'):
            text += f"   📝 {lib['description'][:100]}...\n"
        if lib.get('size'):
            text += f"   💾 حجم: {lib['size'] // 1024} KB\n"
        text += f"   📅 نصب: {lib['installed_at'][:16]}\n\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="lib_back"))
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                         parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "lib_stats")
def library_stats(call):
    total = db.execute("SELECT COUNT(*) as c FROM libraries")[0]['c']
    recent = db.execute("SELECT COUNT(*) as c FROM libraries WHERE installed_at >= datetime('now', '-7 days')")[0]['c']
    
    # محبوب‌ترین کتابخانه‌ها
    popular = db.execute("SELECT name, COUNT(*) as installs FROM libraries GROUP BY name ORDER BY installs DESC LIMIT 5")
    
    text = "📊 **آمار کتابخانه‌ها**\n\n"
    text += f"📦 **کل کتابخانه‌های نصب شده:** {total}\n"
    text += f"🆕 **نصب شده در ۷ روز اخیر:** {recent}\n\n"
    
    if popular:
        text += "🔥 **محبوب‌ترین کتابخانه‌ها:**\n"
        for p in popular:
            text += f"• `{p['name']}` - {p['installs']} بار نصب\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="lib_back"))
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                         parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "lib_back")
def lib_back(call):
    libraries_menu(call.message)

# ==================== راهنما و آمار و پشتیبانی ====================

@bot.message_handler(func=lambda m: m.text == '📚 راهنما')
def guide(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    first_name = user['first_name'] if user else "کاربر"
    
    guide_text = f"""
📚 **راهنمای جامع ربات مادر**

کاربر گرامی {first_name}، خوش آمدید!

---

**🎯 نحوه ساخت ربات:**

**روش اول - ارسال فایل:**
1️⃣ از منوی `💰 خرید اشتراک` اشتراک خود را فعال کنید
2️⃣ پس از فعال‌سازی، از منوی `🤖 ساخت ربات جدید` استفاده کنید
3️⃣ فایل `.py` یا `.zip` خود را ارسال کنید
4️⃣ مطمئن شوید توکن داخل کد شما هست

**روش دوم - استفاده از پوشه‌ها:**
1️⃣ از منوی `📁 مدیریت پوشه‌ها` یک پوشه جدید بسازید
2️⃣ فایل‌های خود را داخل پوشه آپلود کنید
3️⃣ فایل اصلی را با نام `main.py` ذخیره کنید
4️⃣ از دکمه `▶️ اجرای ربات` استفاده کنید

---

**▶️ اجرای ربات:**
- هر بار اجرا {db.get_setting('execution_duration')} دقیقه است
- پس از اتمام زمان خودکار متوقف می‌شود
- می‌توانید مجدداً اجرا کنید

---

**📦 کتابخانه‌ها:**
- می‌توانید هر کتابخانه پایتونی نصب کنید
- کتابخانه‌های نصب شده در همه ربات‌ها قابل استفاده است

---

**💰 سیستم مالی:**
- هر دعوت {db.get_setting('withdraw_percent')}٪ کمیسیون
- حداقل برداشت {db.get_setting('min_withdraw'):,} تومان

---

**📌 محدودیت‌ها:**
- هر کاربر حداکثر {db.get_setting('max_bots_per_user')} ربات می‌تواند داشته باشد

---

**🆘 پشتیبانی:**
در صورت مشکل یا سوال با @shahraghee13 تماس بگیرید.
"""
    
    bot.send_message(message.chat.id, guide_text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '📊 آمار')
def stats(message):
    # آمار عمومی
    users_count = db.execute("SELECT COUNT(*) as c FROM users")[0]['c']
    active_subs = db.execute("SELECT COUNT(*) as c FROM users WHERE subscription_status = 'active'")[0]['c']
    bots_count = db.execute("SELECT COUNT(*) as c FROM bots")[0]['c']
    folders_count = db.execute("SELECT COUNT(*) as c FROM folders")[0]['c']
    total_wallet = db.execute("SELECT SUM(wallet_balance) as t FROM users")[0]['t'] or 0
    total_executions = db.execute("SELECT COUNT(*) as c FROM executions")[0]['c']
    total_libraries = db.execute("SELECT COUNT(*) as c FROM libraries")[0]['c']
    
    # آمار اجراهای امروز
    today = datetime.now().date().isoformat()
    daily = db.execute("SELECT * FROM daily_stats WHERE date = ?", (today,))
    if daily:
        daily = daily[0]
        today_new_users = daily['new_users']
        today_new_bots = daily['new_bots']
        today_revenue = daily['total_revenue']
    else:
        today_new_users = today_new_bots = today_revenue = 0
    
    # آمار سیستم اجرا
    exec_stats = executor.get_stats()
    
    text = f"📊 **آمار پیشرفته سیستم**\n\n"
    text += f"═══════════════════════\n"
    text += f"👥 **کاربران**\n"
    text += f"   کل کاربران: {users_count:,}\n"
    text += f"   اشتراک فعال: {active_subs:,}\n"
    text += f"   نرخ فعال‌سازی: {(active_subs/users_count*100):.1f}%\n\n"
    
    text += f"🤖 **ربات‌ها**\n"
    text += f"   کل ربات‌ها: {bots_count:,}\n"
    text += f"   میانگین هر کاربر: {(bots_count/users_count):.1f}\n"
    text += f"   در حال اجرا: {exec_stats['running']}\n\n"
    
    text += f"📁 **پوشه‌ها**\n"
    text += f"   کل پوشه‌ها: {folders_count:,}\n\n"
    
    text += f"▶️ **اجراها**\n"
    text += f"   کل اجراها: {total_executions:,}\n"
    text += f"   اجراهای فعال: {exec_stats['total_active']}\n\n"
    
    text += f"📦 **کتابخانه‌ها**\n"
    text += f"   کتابخانه‌های نصب شده: {total_libraries}\n\n"
    
    text += f"💰 **مالی**\n"
    text += f"   موجودی کل: {total_wallet:,} تومان\n"
    text += f"   درآمد امروز: {today_revenue:,} تومان\n\n"
    
    text += f"📈 **آمار امروز**\n"
    text += f"   کاربران جدید: {today_new_users}\n"
    text += f"   ربات‌های جدید: {today_new_bots}\n\n"
    
    text += f"⚙️ **تنظیمات فعلی**\n"
    text += f"   حداکثر ربات: {db.get_setting('max_bots_per_user')}\n"
    text += f"   زمان هر اجرا: {db.get_setting('execution_duration')} دقیقه\n"
    text += f"   قیمت اشتراک: {db.get_setting('subscription_price_str')}\n"
    text += f"   کمیسیون دعوت: {db.get_setting('withdraw_percent')}%\n\n"
    
    text += f"🖥️ **مصرف منابع**\n"
    text += f"   حافظه مصرفی: {exec_stats['total_memory_mb']} MB\n"
    text += f"   میانگین CPU: {exec_stats['average_cpu']}%"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '📞 پشتیبانی')
def support(message):
    text = """
📞 **پشتیبانی ربات مادر**

برای ارتباط با پشتیبانی:

🆔 **تلگرام:** @shahraghee13

⏱ **ساعات پاسخگویی:**
- شنبه تا پنجشنبه: ۹ صبح تا ۹ شب
- جمعه‌ها: ۱۰ صبح تا ۶ عصر

📝 **قبل از تماس، لطفاً موارد زیر را آماده داشته باشید:**
- آیدی عددی خود (`/start` را بزنید تا مشاهده کنید)
- کد پیگیری (در صورت داشتن درخواست)
- توضیح کامل مشکل

🚀 **پاسخگویی سریع و حرفه‌ای**
"""
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== پنل مدیریت پیشرفته ====================

@bot.message_handler(func=lambda m: m.text == '👑 پنل مدیریت')
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📸 تایید فیش‌ها", callback_data="admin_receipts"),
        types.InlineKeyboardButton("💰 تایید برداشت", callback_data="admin_withdraws"),
        types.InlineKeyboardButton("👥 مدیریت کاربران", callback_data="admin_users"),
        types.InlineKeyboardButton("🤖 مدیریت ربات‌ها", callback_data="admin_bots"),
        types.InlineKeyboardButton("📁 مدیریت پوشه‌ها", callback_data="admin_folders"),
        types.InlineKeyboardButton("⚙️ تنظیمات سیستم", callback_data="admin_settings"),
        types.InlineKeyboardButton("📝 تنظیم پیام‌ها", callback_data="admin_messages"),
        types.InlineKeyboardButton("📊 گزارش کامل", callback_data="admin_full_report"),
        types.InlineKeyboardButton("🖥️ وضعیت سرور", callback_data="admin_server_status"),
        types.InlineKeyboardButton("🔧 خطاهای سیستم", callback_data="admin_errors"),
        types.InlineKeyboardButton("📦 مدیریت کتابخانه", callback_data="admin_libraries"),
        types.InlineKeyboardButton("💾 پشتیبان‌گیری", callback_data="admin_backup"),
    )
    
    bot.send_message(message.chat.id, 
                    "👑 **پنل مدیریت پیشرفته**\n\n"
                    "از دکمه‌های زیر برای مدیریت سیستم استفاده کنید.",
                    parse_mode='Markdown', reply_markup=markup)

# تایید فیش
@bot.callback_query_handler(func=lambda call: call.data == "admin_receipts")
def admin_receipts(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    receipts = db.execute("SELECT * FROM receipts WHERE status = 'pending' ORDER BY created_at")
    
    if not receipts:
        bot.send_message(call.message.chat.id, "📸 هیچ فیش در انتظار تاییدی وجود ندارد.")
        return
    
    for r in receipts:
        r = dict(r)
        user = get_user(r['user_id'])
        
        text = f"📸 **فیش پرداخت**\n\n"
        text += f"👤 کاربر: {user['first_name'] if user else 'نامشخص'}\n"
        text += f"🆔 آیدی: `{r['user_id']}`\n"
        text += f"💰 مبلغ: {r['amount']:,} تومان\n"
        text += f"🆔 کد: `{r['payment_code']}`\n"
        text += f"🔑 تراکنش: `{r.get('transaction_id', '---')}`\n"
        text += f"📅 تاریخ: {r['created_at'][:16]}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ تایید و فعال‌سازی", callback_data=f"approve_receipt_{r['id']}"),
                  types.InlineKeyboardButton("❌ رد", callback_data=f"reject_receipt_{r['id']}"))
        
        if os.path.exists(r['receipt_path']):
            with open(r['receipt_path'], 'rb') as f:
                bot.send_photo(call.message.chat.id, f, caption=text, parse_mode='Markdown', reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, text, parse_mode='Markdown', reply_markup=markup)
    
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_receipt_'))
def approve_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    rid = int(call.data.replace('approve_receipt_', ''))
    receipt = db.execute("SELECT user_id FROM receipts WHERE id = ?", (rid,))
    
    if receipt:
        user_id = receipt[0]['user_id']
        
        # به‌روزرسانی وضعیت فیش
        db.execute("UPDATE receipts SET status = 'approved', reviewed_by = ?, reviewed_at = ? WHERE id = ?",
                  (call.from_user.id, datetime.now().isoformat(), rid))
        
        # فعال‌سازی اشتراک
        expiry = db.activate_subscription(user_id)
        
        # ارسال پیام تایید به کاربر
        send_subscription_activated_message(user_id)
        
        bot.answer_callback_query(call.id, "✅ اشتراک کاربر فعال شد!")
        bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_receipt_'))
def reject_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    rid = int(call.data.replace('reject_receipt_', ''))
    receipt = db.execute("SELECT user_id, payment_code FROM receipts WHERE id = ?", (rid,))
    
    if receipt:
        user_id = receipt[0]['user_id']
        
        db.execute("UPDATE receipts SET status = 'rejected', reviewed_by = ?, reviewed_at = ? WHERE id = ?",
                  (call.from_user.id, datetime.now().isoformat(), rid))
        
        bot.send_message(user_id, 
                        f"❌ **متأسفانه فیش پرداخت شما رد شد.**\n\n"
                        f"🆔 کد پیگیری: {receipt[0]['payment_code']}\n\n"
                        f"لطفاً مجدداً اقدام کنید یا با پشتیبانی تماس بگیرید.\n"
                        f"📞 @shahraghee13")
        
        bot.answer_callback_query(call.id, "❌ فیش رد شد!")
        bot.delete_message(call.message.chat.id, call.message.message_id)

# تایید برداشت
@bot.callback_query_handler(func=lambda call: call.data == "admin_withdraws")
def admin_withdraws(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    withdraws = db.execute("SELECT * FROM withdraw_requests WHERE status = 'pending' ORDER BY created_at")
    
    if not withdraws:
        bot.send_message(call.message.chat.id, "💰 هیچ درخواست برداشتی وجود ندارد.")
        return
    
    for w in withdraws:
        w = dict(w)
        user = get_user(w['user_id'])
        text = f"💰 **درخواست برداشت**\n\n"
        text += f"👤 کاربر: {user['first_name'] if user else 'نامشخص'}\n"
        text += f"🆔 آیدی: `{w['user_id']}`\n"
        text += f"💰 مبلغ: {w['amount']:,} تومان\n"
        text += f"💳 کارت: {w['card_number'][:4]}****{w['card_number'][-4:]}\n"
        text += f"👤 صاحب کارت: {w['card_holder']}\n"
        text += f"🏦 بانک: {w.get('bank_name', '---')}\n"
        text += f"🔑 کد رهگیری: `{w.get('tracking_code', '---')}`\n"
        text += f"📅 تاریخ: {w['created_at'][:16]}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ تایید واریز", callback_data=f"approve_withdraw_{w['id']}"))
        
        bot.send_message(call.message.chat.id, text, parse_mode='Markdown', reply_markup=markup)
    
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_withdraw_'))
def approve_withdraw(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    wid = int(call.data.replace('approve_withdraw_', ''))
    withdraw = db.execute("SELECT user_id, amount, tracking_code FROM withdraw_requests WHERE id = ?", (wid,))
    
    if withdraw:
        db.execute("UPDATE withdraw_requests SET status = 'approved', processed_at = ? WHERE id = ?",
                  (datetime.now().isoformat(), wid))
        
        user_id = withdraw[0]['user_id']
        amount = withdraw[0]['amount']
        tracking = withdraw[0]['tracking_code']
        
        bot.send_message(user_id,
                        f"✅ **درخواست برداشت شما تایید شد!**\n\n"
                        f"💰 مبلغ: {amount:,} تومان\n"
                        f"🔑 کد رهگیری: {tracking}\n\n"
                        f"مبلغ به حساب شما واریز خواهد شد.\n"
                        f"حداکثر ۷۲ ساعت کاری.")
        
        bot.answer_callback_query(call.id, "✅ برداشت تایید شد!")
        bot.delete_message(call.message.chat.id, call.message.message_id)

# مدیریت کاربران
@bot.callback_query_handler(func=lambda call: call.data == "admin_users")
def admin_users(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔍 جستجوی کاربر", callback_data="admin_search_user"),
        types.InlineKeyboardButton("💰 افزایش موجودی", callback_data="admin_add_balance"),
        types.InlineKeyboardButton("🎁 فعال‌سازی اشتراک", callback_data="admin_activate_sub"),
        types.InlineKeyboardButton("🚫 مسدود کردن کاربر", callback_data="admin_ban_user"),
        types.InlineKeyboardButton("✅ رفع مسدودیت", callback_data="admin_unban_user"),
        types.InlineKeyboardButton("📋 لیست کاربران", callback_data="admin_list_users"),
        types.InlineKeyboardButton("📊 برترین کاربران", callback_data="admin_top_users"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    bot.edit_message_text("👥 **مدیریت کاربران**\n\n"
                         "از دکمه‌های زیر برای مدیریت کاربران استفاده کنید.",
                         call.message.chat.id, call.message.message_id,
                         parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_search_user")
def admin_search_user(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, "🔍 **آیدی عددی کاربر یا نام کاربری را وارد کنید:**")
    bot.register_next_step_handler(msg, process_admin_search)
    bot.answer_callback_query(call.id)

def process_admin_search(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    search = message.text.strip()
    
    # جستجو با آیدی یا نام کاربری
    if search.isdigit():
        users = db.execute("SELECT * FROM users WHERE user_id = ?", (int(search),))
    else:
        users = db.execute("SELECT * FROM users WHERE username LIKE ?", (f"%{search}%",))
    
    if not users:
        bot.reply_to(message, "❌ کاربری یافت نشد!")
        return
    
    for user in users:
        user = dict(user)
        bots = db.execute("SELECT COUNT(*) as c FROM bots WHERE user_id = ?", (user['user_id'],))[0]['c']
        executions = db.execute("SELECT COUNT(*) as c FROM executions WHERE user_id = ?", (user['user_id'],))[0]['c']
        receipts = db.execute("SELECT SUM(amount) as t FROM receipts WHERE user_id = ? AND status = 'approved'", (user['user_id'],))[0]['t'] or 0
        
        text = f"👤 **اطلاعات کاربر**\n\n"
        text += f"نام: {user['first_name']}\n"
        text += f"نام کاربری: @{user['username'] if user['username'] else 'ندارد'}\n"
        text += f"🆔 آیدی: `{user['user_id']}`\n"
        text += f"📞 تلفن: {user.get('phone', '---')}\n"
        text += f"📧 ایمیل: {user.get('email', '---')}\n\n"
        
        text += f"💰 **مالی:**\n"
        text += f"   موجودی: {user['wallet_balance']:,} تومان\n"
        text += f"   کل هزینه: {user.get('total_spent', 0):,} تومان\n"
        text += f"   فیش‌های تایید شده: {receipts:,} تومان\n\n"
        
        text += f"✅ **اشتراک:**\n"
        text += f"   وضعیت: {'فعال' if check_subscription(user['user_id']) else 'غیرفعال'}\n"
        if user['subscription_expiry']:
            text += f"   انقضا: {user['subscription_expiry'][:16]}\n\n"
        
        text += f"🤖 **ربات‌ها:**\n"
        text += f"   تعداد ربات: {bots}\n"
        text += f"   تعداد اجرا: {executions}\n\n"
        
        text += f"👥 **دعوت‌ها:**\n"
        text += f"   دعوت‌ها: {user['referrals_count']}\n"
        text += f"   کد معرف: `{user['referral_code']}`\n\n"
        
        text += f"📅 **تاریخ عضویت:** {user['created_at'][:16]}\n"
        text += f"🕐 **آخرین فعالیت:** {user['last_active'][:16]}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("💰 افزایش موجودی", callback_data=f"admin_add_balance_user_{user['user_id']}"))
        markup.add(types.InlineKeyboardButton("🎁 فعال‌سازی اشتراک", callback_data=f"admin_activate_user_{user['user_id']}"))
        if user.get('is_banned'):
            markup.add(types.InlineKeyboardButton("✅ رفع مسدودیت", callback_data=f"admin_unban_user_{user['user_id']}"))
        else:
            markup.add(types.InlineKeyboardButton("🚫 مسدود کردن", callback_data=f"admin_ban_user_{user['user_id']}"))
        
        bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_add_balance")
def admin_add_balance(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, 
                          "💰 **افزایش موجودی کاربر**\n\n"
                          "فرمت: `آیدی کاربر مبلغ`\n"
                          "مثال: `123456789 100000`\n\n"
                          "⚠️ مبلغ به تومان وارد شود.")
    bot.register_next_step_handler(msg, process_admin_add_balance)
    bot.answer_callback_query(call.id)

def process_admin_add_balance(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        parts = message.text.strip().split()
        user_id = int(parts[0])
        amount = int(parts[1])
        
        user = get_user(user_id)
        if user:
            new_balance = db.add_wallet_balance(user_id, amount)
            bot.reply_to(message, f"✅ {amount:,} تومان به کیف پول {user['first_name']} اضافه شد.\n💰 موجودی جدید: {new_balance:,} تومان")
            bot.send_message(user_id, f"💰 مبلغ {amount:,} تومان به کیف پول شما اضافه شد.\n🙏 سپاس از اعتماد شما!")
        else:
            bot.reply_to(message, "❌ کاربر یافت نشد!")
    except:
        bot.reply_to(message, "❌ فرمت نامعتبر! مثال: `123456789 100000`")

@bot.callback_query_handler(func=lambda call: call.data == "admin_activate_sub")
def admin_activate_sub(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, "🎁 **فعال‌سازی اشتراک کاربر**\n\nآیدی عددی کاربر را وارد کنید:")
    bot.register_next_step_handler(msg, process_admin_activate_sub)
    bot.answer_callback_query(call.id)

def process_admin_activate_sub(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        user_id = int(message.text.strip())
        user = get_user(user_id)
        
        if user:
            expiry = db.activate_subscription(user_id)
            send_subscription_activated_message(user_id)
            bot.reply_to(message, f"✅ اشتراک {user['first_name']} تا {expiry.strftime('%Y-%m-%d')} فعال شد.")
        else:
            bot.reply_to(message, "❌ کاربر یافت نشد!")
    except:
        bot.reply_to(message, "❌ آیدی نامعتبر!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_list_users")
def admin_list_users(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    users = db.execute("SELECT user_id, first_name, username, subscription_status, wallet_balance, created_at FROM users ORDER BY created_at DESC LIMIT 20")
    
    if not users:
        bot.send_message(call.message.chat.id, "📋 کاربری وجود ندارد.")
        return
    
    text = "📋 **آخرین کاربران ثبت‌نام شده**\n\n"
    for user in users:
        text += f"**{user['first_name']}**\n"
        text += f"🆔 `{user['user_id']}`\n"
        text += f"💰 {user['wallet_balance']:,} تومان\n"
        text += f"✅ {'فعال' if user['subscription_status'] == 'active' else 'غیرفعال'}\n"
        text += f"📅 {user['created_at'][:16]}\n\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

# تنظیمات سیستم
@bot.callback_query_handler(func=lambda call: call.data == "admin_settings")
def admin_settings(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    current_max_bots = db.get_setting('max_bots_per_user')
    current_exec_duration = db.get_setting('execution_duration')
    current_price = db.get_setting('subscription_price_str')
    current_withdraw = db.get_setting('withdraw_percent')
    current_min_withdraw = db.get_setting('min_withdraw')
    
    text = f"⚙️ **تنظیمات فعلی سیستم**\n\n"
    text += f"📌 **محدودیت‌ها:**\n"
    text += f"   حداکثر ربات هر کاربر: {current_max_bots}\n"
    text += f"   زمان هر اجرا: {current_exec_duration} دقیقه\n\n"
    
    text += f"💰 **مالی:**\n"
    text += f"   قیمت اشتراک: {current_price}\n"
    text += f"   کمیسیون دعوت: {current_withdraw}%\n"
    text += f"   حداقل برداشت: {current_min_withdraw:,} تومان\n\n"
    
    text += f"💳 **اطلاعات کارت:**\n"
    text += f"   شماره کارت: `{db.get_setting('card_number_display')}`\n"
    text += f"   صاحب کارت: {db.get_setting('card_holder')}\n"
    text += f"   بانک: {db.get_setting('card_bank')}"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📌 حداکثر ربات", callback_data="admin_set_max_bots"),
        types.InlineKeyboardButton("⏱ زمان اجرا", callback_data="admin_set_duration"),
        types.InlineKeyboardButton("💰 قیمت اشتراک", callback_data="admin_set_price"),
        types.InlineKeyboardButton("👥 کمیسیون", callback_data="admin_set_withdraw"),
        types.InlineKeyboardButton("💸 حداقل برداشت", callback_data="admin_set_min_withdraw"),
        types.InlineKeyboardButton("💳 کارت", callback_data="admin_set_card"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                         parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_max_bots")
def admin_set_max_bots(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, "📌 **حداکثر تعداد ربات برای هر کاربر (۱-۲۰):**")
    bot.register_next_step_handler(msg, process_set_max_bots)
    bot.answer_callback_query(call.id)

def process_set_max_bots(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        value = int(message.text.strip())
        if 1 <= value <= 20:
            db.update_setting('max_bots_per_user', str(value), message.from_user.id)
            bot.reply_to(message, f"✅ حداکثر ربات هر کاربر به {value} تغییر کرد.")
        else:
            bot.reply_to(message, "❌ عدد باید بین 1 تا 20 باشد.")
    except:
        bot.reply_to(message, "❌ عدد معتبر وارد کنید.")

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_duration")
def admin_set_duration(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, "⏱ **مدت زمان اجرا به دقیقه (۱-۳۰):**")
    bot.register_next_step_handler(msg, process_set_duration)
    bot.answer_callback_query(call.id)

def process_set_duration(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        value = int(message.text.strip())
        if 1 <= value <= 30:
            db.update_setting('execution_duration', str(value), message.from_user.id)
            bot.reply_to(message, f"✅ زمان هر اجرا به {value} دقیقه تغییر کرد.")
        else:
            bot.reply_to(message, "❌ عدد باید بین 1 تا 30 باشد.")
    except:
        bot.reply_to(message, "❌ عدد معتبر وارد کنید.")

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_price")
def admin_set_price(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, "💰 **قیمت جدید اشتراک (تومان):**\nمثال: 50000")
    bot.register_next_step_handler(msg, process_set_price)
    bot.answer_callback_query(call.id)

def process_set_price(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        price = int(message.text.strip())
        db.update_setting('subscription_price', str(price), message.from_user.id)
        db.update_setting('subscription_price_str', f"{price:,} تومان", message.from_user.id)
        bot.reply_to(message, f"✅ قیمت اشتراک به {price:,} تومان تغییر کرد.")
    except:
        bot.reply_to(message, "❌ عدد معتبر وارد کنید.")

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_withdraw")
def admin_set_withdraw(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, "👥 **درصد کمیسیون دعوت (۱-۵۰):**\nمثال: 7")
    bot.register_next_step_handler(msg, process_set_withdraw)
    bot.answer_callback_query(call.id)

def process_set_withdraw(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        percent = int(message.text.strip())
        if 1 <= percent <= 50:
            db.update_setting('withdraw_percent', str(percent), message.from_user.id)
            bot.reply_to(message, f"✅ کمیسیون دعوت به {percent}% تغییر کرد.")
        else:
            bot.reply_to(message, "❌ عدد باید بین 1 تا 50 باشد.")
    except:
        bot.reply_to(message, "❌ عدد معتبر وارد کنید.")

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_min_withdraw")
def admin_set_min_withdraw(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, "💸 **حداقل مبلغ برداشت (تومان):**\nمثال: 2000000")
    bot.register_next_step_handler(msg, process_set_min_withdraw)
    bot.answer_callback_query(call.id)

def process_set_min_withdraw(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        amount = int(message.text.strip())
        if amount >= 100000:
            db.update_setting('min_withdraw', str(amount), message.from_user.id)
            bot.reply_to(message, f"✅ حداقل برداشت به {amount:,} تومان تغییر کرد.")
        else:
            bot.reply_to(message, "❌ حداقل مبلغ باید ۱۰۰,۰۰۰ تومان باشد.")
    except:
        bot.reply_to(message, "❌ عدد معتبر وارد کنید.")

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_card")
def admin_set_card(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, "💳 **شماره کارت جدید (۱۶ رقم):**")
    bot.register_next_step_handler(msg, process_set_card)
    bot.answer_callback_query(call.id)

def process_set_card(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    card = message.text.strip().replace(' ', '')
    if len(card) == 16 and card.isdigit():
        db.update_setting('card_number', card, message.from_user.id)
        display = ' '.join([card[i:i+4] for i in range(0, 16, 4)])
        db.update_setting('card_number_display', display, message.from_user.id)
        
        msg = bot.send_message(message.chat.id, "👤 **نام صاحب کارت را وارد کنید:**")
        bot.register_next_step_handler(msg, process_set_card_holder, card)
    else:
        bot.reply_to(message, "❌ شماره کارت باید ۱۶ رقم باشد.")

def process_set_card_holder(message, card):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    holder = message.text.strip()
    db.update_setting('card_holder', holder, message.from_user.id)
    
    msg = bot.send_message(message.chat.id, "🏦 **نام بانک را وارد کنید:**")
    bot.register_next_step_handler(msg, process_set_card_bank)

def process_set_card_bank(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    bank = message.text.strip()
    db.update_setting('card_bank', bank, message.from_user.id)
    
    bot.reply_to(message, f"✅ اطلاعات کارت به‌روزرسانی شد.\n"
                f"`{db.get_setting('card_number_display')}`\n"
                f"👤 {db.get_setting('card_holder')}\n"
                f"🏦 {db.get_setting('card_bank')}",
                parse_mode='Markdown')

# تنظیم پیام‌ها
@bot.callback_query_handler(func=lambda call: call.data == "admin_messages")
def admin_messages(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    messages = db.execute("SELECT key, title FROM system_messages")
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for msg in messages:
        markup.add(types.InlineKeyboardButton(f"📝 {msg['title']}", callback_data=f"edit_message_{msg['key']}"))
    
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back"))
    
    bot.edit_message_text("📝 **تنظیم پیام‌های سیستم**\n\n"
                         "روی هر پیام کلیک کنید تا متن آن را تغییر دهید.\n"
                         "می‌توانید از متغیرهای زیر استفاده کنید:\n"
                         "`{first_name}` - نام کاربر\n"
                         "`{price}` - قیمت اشتراک\n"
                         "`{card}` - شماره کارت\n"
                         "`{max_bots}` - حداکثر ربات\n"
                         "`{duration}` - زمان اجرا",
                         call.message.chat.id, call.message.message_id,
                         parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('edit_message_'))
def edit_message_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    key = call.data.replace('edit_message_', '')
    current = db.get_message(key)
    
    msg = bot.send_message(call.message.chat.id, 
                          f"📝 **ویرایش پیام**\n\n"
                          f"کلید: `{key}`\n\n"
                          f"**متن فعلی:**\n{current}\n\n"
                          f"**متن جدید را ارسال کنید:**\n"
                          f"(از متغیرها می‌توانید استفاده کنید)")
    
    bot.register_next_step_handler(msg, process_edit_message, key, call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id)

def process_edit_message(message, key, chat_id, msg_id):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    new_text = message.text
    title = db.execute("SELECT title FROM system_messages WHERE key = ?", (key,))
    title = title[0]['title'] if title else "پیام سیستم"
    
    db.update_message(key, new_text, title, message.from_user.id)
    
    bot.reply_to(message, f"✅ پیام `{key}` با موفقیت به‌روزرسانی شد.", parse_mode='Markdown')
    bot.delete_message(chat_id, msg_id)

# گزارش کامل
@bot.callback_query_handler(func=lambda call: call.data == "admin_full_report")
def admin_full_report(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    # آمار پایه
    users_count = db.execute("SELECT COUNT(*) as c FROM users")[0]['c']
    active_subs = db.execute("SELECT COUNT(*) as c FROM users WHERE subscription_status = 'active'")[0]['c']
    bots_count = db.execute("SELECT COUNT(*) as c FROM bots")[0]['c']
    folders_count = db.execute("SELECT COUNT(*) as c FROM folders")[0]['c']
    executions_count = db.execute("SELECT COUNT(*) as c FROM executions")[0]['c']
    libraries_count = db.execute("SELECT COUNT(*) as c FROM libraries")[0]['c']
    
    # آمار مالی
    total_wallet = db.execute("SELECT SUM(wallet_balance) as t FROM users")[0]['t'] or 0
    total_revenue = db.execute("SELECT SUM(amount) as t FROM receipts WHERE status = 'approved'")[0]['t'] or 0
    pending_receipts = db.execute("SELECT COUNT(*) as c FROM receipts WHERE status = 'pending'")[0]['c']
    pending_withdraws = db.execute("SELECT COUNT(*) as c FROM withdraw_requests WHERE status = 'pending'")[0]['c']
    
    # آمار اجرا
    exec_stats = executor.get_stats()
    
    # آمار امروز
    today = datetime.now().date().isoformat()
    daily = db.execute("SELECT * FROM daily_stats WHERE date = ?", (today,))
    if daily:
        daily = daily[0]
        today_new_users = daily['new_users']
        today_new_bots = daily['new_bots']
        today_new_subs = daily['new_subscriptions']
        today_revenue = daily['total_revenue']
    else:
        today_new_users = today_new_bots = today_new_subs = today_revenue = 0
    
    text = f"📊 **گزارش کامل سیستم**\n\n"
    text += f"═══════════════════════\n"
    text += f"👥 **کاربران**\n"
    text += f"   کل کاربران: {users_count:,}\n"
    text += f"   اشتراک فعال: {active_subs:,}\n"
    text += f"   نرخ فعال‌سازی: {(active_subs/users_count*100):.1f}%\n\n"
    
    text += f"🤖 **ربات‌ها**\n"
    text += f"   کل ربات‌ها: {bots_count:,}\n"
    text += f"   میانگین هر کاربر: {(bots_count/users_count):.1f}\n"
    text += f"   در حال اجرا: {exec_stats['running']}\n\n"
    
    text += f"📁 **پوشه‌ها**\n"
    text += f"   کل پوشه‌ها: {folders_count:,}\n\n"
    
    text += f"▶️ **اجراها**\n"
    text += f"   کل اجراها: {executions_count:,}\n"
    text += f"   اجراهای فعال: {exec_stats['total_active']}\n\n"
    
    text += f"📦 **کتابخانه‌ها**\n"
    text += f"   کتابخانه‌های نصب شده: {libraries_count}\n\n"
    
    text += f"💰 **مالی**\n"
    text += f"   موجودی کل: {total_wallet:,} تومان\n"
    text += f"   درآمد کل: {total_revenue:,} تومان\n"
    text += f"   فیش‌های در انتظار: {pending_receipts}\n"
    text += f"   درخواست‌های برداشت: {pending_withdraws}\n\n"
    
    text += f"📈 **آمار امروز ({today})**\n"
    text += f"   کاربران جدید: {today_new_users}\n"
    text += f"   ربات‌های جدید: {today_new_bots}\n"
    text += f"   اشتراک‌های جدید: {today_new_subs}\n"
    text += f"   درآمد امروز: {today_revenue:,} تومان\n\n"
    
    text += f"🖥️ **مصرف منابع**\n"
    text += f"   حافظه مصرفی: {exec_stats['total_memory_mb']} MB\n"
    text += f"   میانگین CPU: {exec_stats['average_cpu']}%\n\n"
    
    text += f"⚙️ **تنظیمات فعلی**\n"
    text += f"   حداکثر ربات: {db.get_setting('max_bots_per_user')}\n"
    text += f"   زمان اجرا: {db.get_setting('execution_duration')} دقیقه\n"
    text += f"   قیمت اشتراک: {db.get_setting('subscription_price_str')}\n"
    text += f"   کمیسیون: {db.get_setting('withdraw_percent')}%"
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                         parse_mode='Markdown')

# وضعیت سرور
@bot.callback_query_handler(func=lambda call: call.data == "admin_server_status")
def admin_server_status(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    try:
        import psutil
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        text = f"🖥️ **وضعیت سرور**\n\n"
        
        text += f"**CPU:**\n"
        text += f"   استفاده: {cpu_percent}%\n"
        text += f"   هسته‌ها: {psutil.cpu_count()}\n"
        text += f"   فرکانس: {psutil.cpu_freq().current/1000:.1f} GHz\n\n"
        
        text += f"**RAM:**\n"
        text += f"   استفاده: {memory.used / (1024**3):.1f} GB / {memory.total / (1024**3):.1f} GB\n"
        text += f"   درصد: {memory.percent}%\n\n"
        
        text += f"**Disk:**\n"
        text += f"   استفاده: {disk.used / (1024**3):.1f} GB / {disk.total / (1024**3):.1f} GB\n"
        text += f"   درصد: {disk.percent}%\n\n"
        
        text += f"**ربات‌ها:**\n"
        text += f"   اجراهای فعال: {len(executor.active_executions)}\n"
        text += f"   ربات‌های کل: {db.execute('SELECT COUNT(*) as c FROM bots')[0]['c']}\n\n"
        
        text += f"**دیتابیس:**\n"
        text += f"   سایز دیتابیس: {os.path.getsize(os.path.join(DIRS['DB_MASTER'], 'mother_bot.db')) / (1024**2):.1f} MB\n"
        text += f"   تعداد جداول: 12"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 بروزرسانی", callback_data="admin_server_status"))
        markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back"))
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                             parse_mode='Markdown', reply_markup=markup)
    except ImportError:
        bot.edit_message_text("❌ برای مشاهده وضعیت سرور، کتابخانه `psutil` را نصب کنید:\n`pip install psutil`",
                             call.message.chat.id, call.message.message_id, parse_mode='Markdown')

# خطاهای سیستم
@bot.callback_query_handler(func=lambda call: call.data == "admin_errors")
def admin_errors(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    errors = db.execute("SELECT * FROM system_errors WHERE resolved = 0 ORDER BY timestamp DESC LIMIT 20")
    
    if not errors:
        bot.edit_message_text("✅ **هیچ خطای حل‌نشده‌ای وجود ندارد.**\n\n"
                             "سیستم در وضعیت پایدار است.",
                             call.message.chat.id, call.message.message_id,
                             parse_mode='Markdown')
        return
    
    text = "⚠️ **خطاهای سیستم (حل‌نشده)**\n\n"
    for e in errors:
        text += f"**{e['type']}**\n"
        text += f"📝 {e['message'][:150]}...\n"
        text += f"🕐 {e['timestamp'][:16]}\n"
        if e.get('user_id'):
            text += f"👤 کاربر: {e['user_id']}\n"
        text += f"🔑 آیدی: `{e['id'][:8]}`\n\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ علامت‌گذاری همه به عنوان حل شده", callback_data="admin_resolve_all_errors"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back"))
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                         parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_resolve_all_errors")
def resolve_all_errors(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    db.execute("UPDATE system_errors SET resolved = 1 WHERE resolved = 0")
    bot.answer_callback_query(call.id, "✅ تمام خطاها به عنوان حل شده علامت‌گذاری شدند!")
    admin_errors(call)

@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    admin_panel(call.message)

# ==================== پیام همگانی ====================

@bot.message_handler(func=lambda m: m.text == '📢 پیام همگانی')
def broadcast_prompt(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📝 متن ساده", callback_data="broadcast_text"),
              types.InlineKeyboardButton("🖼️ با عکس", callback_data="broadcast_photo"),
              types.InlineKeyboardButton("🔊 با فایل", callback_data="broadcast_document"))
    
    bot.send_message(message.chat.id, "📢 **نوع پیام همگانی را انتخاب کنید:**", 
                    parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "broadcast_text")
def broadcast_text_prompt(call):
    msg = bot.send_message(call.message.chat.id, "📢 **متن پیام همگانی را ارسال کنید:**\n(می‌توانید از Markdown استفاده کنید)")
    bot.register_next_step_handler(msg, process_broadcast_text)
    bot.answer_callback_query(call.id)

def process_broadcast_text(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    text = message.text
    users = db.execute("SELECT user_id FROM users WHERE is_banned = 0")
    
    sent = 0
    failed = 0
    
    status_msg = bot.reply_to(message, f"🔄 در حال ارسال به {len(users)} کاربر...")
    
    for user in users:
        try:
            bot.send_message(user['user_id'], f"📢 **پیام همگانی**\n\n{text}", parse_mode='Markdown')
            sent += 1
            time.sleep(0.05)
        except:
            failed += 1
    
    bot.edit_message_text(f"✅ **نتیجه ارسال**\n\n"
                         f"📨 ارسال شده: {sent}\n"
                         f"❌ ناموفق: {failed}\n"
                         f"👥 کل کاربران: {len(users)}",
                         message.chat.id, status_msg.message_id,
                         parse_mode='Markdown')

# ==================== تنظیمات پیشرفته ====================

@bot.message_handler(func=lambda m: m.text == '⚙️ تنظیمات پیشرفته')
def advanced_settings(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💾 پشتیبان‌گیری", callback_data="admin_backup"),
        types.InlineKeyboardButton("🔄 بازگردانی", callback_data="admin_restore"),
        types.InlineKeyboardButton("🗑 پاکسازی کش", callback_data="admin_clear_cache"),
        types.InlineKeyboardButton("📊 بهینه‌سازی دیتابیس", callback_data="admin_optimize_db"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    bot.send_message(message.chat.id, "⚙️ **تنظیمات پیشرفته سیستم**\n\n"
                    "ابزارهای مدیریتی پیشرفته برای نگهداری سیستم.",
                    parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_backup")
def admin_backup(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    backup_dir = os.path.join(DIRS['BACKUPS'], datetime.now().strftime("%Y%m%d_%H%M%S"))
    os.makedirs(backup_dir, exist_ok=True)
    
    status_msg = bot.send_message(call.message.chat.id, "🔄 در حال ایجاد پشتیبان...")
    
    try:
        # کپی دیتابیس
        for db_name in ['master', 'slave1', 'slave2', 'cache']:
            src = os.path.join(DIRS[f'DB_{db_name.upper()}'], 'mother_bot.db')
            if os.path.exists(src):
                dst = os.path.join(backup_dir, f'mother_bot_{db_name}.db')
                shutil.copy2(src, dst)
        
        # ذخیره اطلاعات پشتیبان
        backup_info = {
            'date': datetime.now().isoformat(),
            'created_by': call.from_user.id,
            'size': sum(os.path.getsize(os.path.join(backup_dir, f)) for f in os.listdir(backup_dir))
        }
        
        with open(os.path.join(backup_dir, 'backup_info.json'), 'w') as f:
            json.dump(backup_info, f, indent=2)
        
        bot.edit_message_text(f"✅ **پشتیبان با موفقیت ایجاد شد!**\n\n"
                             f"📁 مسیر: `{backup_dir}`\n"
                             f"📦 حجم: {backup_info['size'] / (1024**2):.1f} MB\n"
                             f"🕐 زمان: {backup_info['date'][:19]}",
                             call.message.chat.id, status_msg.message_id,
                             parse_mode='Markdown')
    except Exception as e:
        bot.edit_message_text(f"❌ خطا در ایجاد پشتیبان: {str(e)}",
                             call.message.chat.id, status_msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_clear_cache")
def admin_clear_cache(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    # پاک کردن کش دیتابیس
    db.cache.clear()
    
    # پاک کردن کش فیزیکی
    cache_dir = DIRS['CACHE']
    if os.path.exists(cache_dir):
        for f in os.listdir(cache_dir):
            try:
                os.remove(os.path.join(cache_dir, f))
            except:
                pass
    
    bot.answer_callback_query(call.id, "✅ کش سیستم با موفقیت پاک شد!")
    
    bot.edit_message_text("✅ **کش سیستم با موفقیت پاک شد!**\n\n"
                         "حافظه کش آزاد شد و سیستم با سرعت بالاتر کار خواهد کرد.",
                         call.message.chat.id, call.message.message_id,
                         parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "admin_optimize_db")
def admin_optimize_db(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    status_msg = bot.send_message(call.message.chat.id, "🔄 در حال بهینه‌سازی دیتابیس...")
    
    try:
        # VACUUM و بهینه‌سازی
        for db_name in ['master', 'slave1', 'slave2', 'cache']:
            conn = db.connections[db_name]
            conn.execute("VACUUM")
            conn.execute("ANALYZE")
        
        bot.edit_message_text("✅ **دیتابیس با موفقیت بهینه‌سازی شد!**\n\n"
                             "عملیات VACUUM و ANALYZE انجام شد.\n"
                             "حجم دیتابیس کاهش یافت و سرعت کوئری‌ها افزایش پیدا کرد.",
                             call.message.chat.id, status_msg.message_id,
                             parse_mode='Markdown')
    except Exception as e:
        bot.edit_message_text(f"❌ خطا در بهینه‌سازی: {str(e)}",
                             call.message.chat.id, status_msg.message_id)

# ==================== اجرای اصلی ====================

if __name__ == "__main__":
    print("=" * 80)
    print("╔═══════════════════════════════════════════════════════════════════════════════╗")
    print("║     🚀 ULTRA MOTHER BOT - ENTERPRISE EDITION v24.0                          ║")
    print("║     ⚡ Distributed System - Microservices Architecture                      ║")
    print("║     🔥 Ready to serve millions of users                                     ║")
    print("╚═══════════════════════════════════════════════════════════════════════════════╝")
    print("=" * 80)
    print(f"👑 ادمین‌ها: {ADMIN_IDS}")
    print(f"🤖 نام ربات: @{BOT_USERNAME}")
    print(f"💰 قیمت اشتراک: {db.get_setting('subscription_price_str')}")
    print(f"📌 حداکثر ربات هر کاربر: {db.get_setting('max_bots_per_user')}")
    print(f"⏱ زمان هر اجرا: {db.get_setting('execution_duration')} دقیقه")
    print(f"⭐ کمیسیون رفرال: {db.get_setting('withdraw_percent')}%")
    print("=" * 80)
    print("📊 **معماری سیستم:**")
    print(f"   🗄️ دیتابیس مستر: فعال")
    print(f"   🗄️ دیتابیس اسلیو: 2 عدد")
    print(f"   💾 کش: فعال")
    print(f"   ⚡ تردپول: 200 کارگر")
    print(f"   🔄 پروسس پول: 50 کارگر")
    print("=" * 80)
    print("🔥 ربات با موفقیت راه‌اندازی شد!")
    print("🚀 آماده پاسخگویی به درخواست‌ها...")
    print("=" * 80)
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)