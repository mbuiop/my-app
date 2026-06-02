#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
═══════════════════════════════════════════════════════════════════════════════
🚀 ربات مادر نهایی نسخه 23.0 - Enterprise Ultra Scale
⚡ با تکنولوژی پیشرفته - پشتیبانی از میلیون‌ها کاربر - معماری خوشه‌ای نسل جدید
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
import signal
import secrets
import logging
import queue
import uuid
import asyncio
import aiofiles
import aiohttp
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from functools import wraps
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import redis
import pymongo
from pymongo import MongoClient, ASCENDING, DESCENDING, IndexModel
import psycopg2
from psycopg2 import pool
import asyncio
import uvloop
import aioredis
from motor.motor_asyncio import AsyncIOMotorClient
import asyncpg
import celery
from celery import Celery
import pickle
import msgpack
import orjson
import numpy as np
import pandas as pd

# ==================== تنظیمات پیشرفته ====================

# فعال‌سازی uvloop برای عملکرد فوق‌العاده بالا
try:
    uvloop.install()
except:
    pass

# تنظیمات پایه
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ساختار پوشه‌ها با بهینه‌سازی
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
    'FOLDERS': os.path.join(BASE_DIR, "user_folders"),
    'PROJECTS': os.path.join(BASE_DIR, "projects"),
}

for dir_path in DIRS.values():
    os.makedirs(dir_path, exist_ok=True)

# ==================== پایگاه داده‌های بزرگ و فوق پیشرفته ====================

# 1. Redis برای کش فوق سریع
try:
    redis_client = redis.Redis(
        host='localhost',
        port=6379,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True
    )
    redis_client.ping()
    REDIS_AVAILABLE = True
    print("✅ Redis متصل شد")
except:
    REDIS_AVAILABLE = False
    print("⚠️ Redis در دسترس نیست - از کش داخلی استفاده می‌شود")

# 2. MongoDB برای دیتابیس اصلی (میلیون‌ها رکورد)
try:
    mongo_client = MongoClient(
        'mongodb://localhost:27017/',
        maxPoolSize=2000,
        minPoolSize=100,
        waitQueueTimeoutMS=5000
    )
    db_mongo = mongo_client['mother_bot_db']
    MONGO_AVAILABLE = True
    
    # ایجاد ایندکس‌ها برای سرعت فوق‌العاده بالا
    db_mongo.users.create_index([('user_id', ASCENDING)], unique=True)
    db_mongo.bots.create_index([('user_id', ASCENDING), ('created_at', DESCENDING)])
    db_mongo.bots.create_index([('status', ASCENDING)])
    db_mongo.folders.create_index([('user_id', ASCENDING), ('folder_path', ASCENDING)])
    db_mongo.executions.create_index([('user_id', ASCENDING), ('executed_at', DESCENDING)])
    
    print("✅ MongoDB متصل شد")
except:
    MONGO_AVAILABLE = False
    print("⚠️ MongoDB در دسترس نیست - از SQLite استفاده می‌شود")

# 3. PostgreSQL برای دیتابیس تراکنشی
try:
    pg_pool = pool.SimpleConnectionPool(
        1, 200,
        host="localhost",
        database="mother_bot_db",
        user="postgres",
        password="postgres",
        port=5432
    )
    POSTGRES_AVAILABLE = True
    print("✅ PostgreSQL متصل شد")
except:
    POSTGRES_AVAILABLE = False
    print("⚠️ PostgreSQL در دسترس نیست")

# ==================== کلاس دیتابیس هیبریدی فوق پیشرفته ====================

class UltraDatabase:
    """دیتابیس هیبریدی با پشتیبانی از MongoDB + Redis + PostgreSQL"""
    
    def __init__(self):
        self.redis = redis_client if REDIS_AVAILABLE else None
        self.mongo = db_mongo if MONGO_AVAILABLE else None
        self.sqlite_conn = None
        self._init_sqlite()
        self._init_tables()
    
    def _init_sqlite(self):
        self.sqlite_conn = sqlite3.connect(
            os.path.join(DIRS['DB'], 'mother_bot.db'),
            timeout=60,
            check_same_thread=False
        )
        self.sqlite_conn.row_factory = sqlite3.Row
        self.sqlite_conn.execute("PRAGMA journal_mode=WAL")
        self.sqlite_conn.execute("PRAGMA synchronous=NORMAL")
        self.sqlite_conn.execute("PRAGMA cache_size=-1000000")
        self.sqlite_conn.execute("PRAGMA page_size=32768")
        self.sqlite_conn.execute("PRAGMA mmap_size=100000000000")
    
    def _init_tables(self):
        """ایجاد جداول اصلی"""
        
        # کاربران
        self._execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                bots_count INTEGER DEFAULT 0,
                subscription_status TEXT DEFAULT 'inactive',
                subscription_expiry TIMESTAMP,
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                referrals_count INTEGER DEFAULT 0,
                wallet_balance INTEGER DEFAULT 0,
                created_at TIMESTAMP,
                last_active TIMESTAMP,
                total_executions INTEGER DEFAULT 0,
                total_builds INTEGER DEFAULT 0,
                folders_count INTEGER DEFAULT 0,
                active_until TIMESTAMP
            )
        ''')
        
        # ربات‌ها (حداکثر ۳ تا)
        self._execute('''
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
                last_execution TIMESTAMP,
                execution_count INTEGER DEFAULT 0,
                is_5min_mode INTEGER DEFAULT 0,
                next_deactivation TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        # پوشه‌های کاربران
        self._execute('''
            CREATE TABLE IF NOT EXISTS folders (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                folder_name TEXT,
                folder_path TEXT,
                structure TEXT,
                created_at TIMESTAMP,
                last_used TIMESTAMP,
                file_count INTEGER DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        # اجراهای ۵ دقیقه‌ای
        self._execute('''
            CREATE TABLE IF NOT EXISTS executions (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                bot_id TEXT,
                status TEXT,
                started_at TIMESTAMP,
                ended_at TIMESTAMP,
                output TEXT,
                error TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        # کتابخانه‌های نصب شده
        self._execute('''
            CREATE TABLE IF NOT EXISTS installed_libraries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                version TEXT,
                installed_at TIMESTAMP
            )
        ''')
        
        # تنظیمات سیستم (قابل تغییر توسط ادمین)
        self._execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                category TEXT,
                updated_by INTEGER,
                updated_at TIMESTAMP
            )
        ''')
        
        # پیام‌های سیستم (قابل تغییر)
        self._execute('''
            CREATE TABLE IF NOT EXISTS system_messages (
                key TEXT PRIMARY KEY,
                title TEXT,
                message TEXT,
                updated_by INTEGER,
                updated_at TIMESTAMP
            )
        ''')
        
        # فیش‌های پرداخت
        self._execute('''
            CREATE TABLE IF NOT EXISTS receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                receipt_path TEXT,
                status TEXT DEFAULT 'pending',
                payment_code TEXT UNIQUE,
                reviewed_by INTEGER,
                reviewed_at TIMESTAMP,
                created_at TIMESTAMP
            )
        ''')
        
        # درخواست‌های برداشت
        self._execute('''
            CREATE TABLE IF NOT EXISTS withdraw_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                card_number TEXT,
                card_holder TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP,
                processed_at TIMESTAMP
            )
        ''')
        
        # ذخیره در MongoDB اگر در دسترس باشد
        if self.mongo:
            self.mongo.system_settings.insert_many([
                {'_id': 'card_number', 'value': '5892101187322777', 'category': 'payment'},
                {'_id': 'subscription_price', 'value': 50000, 'category': 'payment'},
                {'_id': 'max_bots_per_user', 'value': 3, 'category': 'limits'},
                {'_id': 'execution_duration', 'value': 5, 'category': 'limits'},  # 5 دقیقه
                {'_id': 'max_builds_per_hour', 'value': 10, 'category': 'limits'},
                {'_id': 'withdraw_percent', 'value': 7, 'category': 'payment'},
                {'_id': 'min_withdraw', 'value': 2000000, 'category': 'payment'},
            ], ordered=False)
        
        # تنظیمات پیش‌فرض
        default_settings = {
            'card_number': '5892101187322777',
            'card_number_display': '5892 1011 8732 2777',
            'card_holder': 'مرتضی نیکخو خنجری',
            'card_bank': 'بانک ملی - سپهر',
            'subscription_price': 50000,
            'subscription_price_str': '۵۰,۰۰۰ تومان',
            'max_bots_per_user': 3,
            'execution_duration': 5,  # 5 دقیقه
            'max_builds_per_hour': 10,
            'withdraw_percent': 7,
            'min_withdraw': 2000000,
            'max_concurrent_builds': 50,
            'rate_limit_per_second': 10,
            'health_check_interval': 30,
            'auto_scale_threshold': 80
        }
        
        for key, value in default_settings.items():
            self._execute('INSERT OR IGNORE INTO system_settings (key, value, updated_at) VALUES (?, ?, ?)', 
                         (key, str(value), datetime.now().isoformat()))
        
        # پیام‌های پیش‌فرض سیستم
        default_messages = {
            'welcome': {'title': 'پیام خوش‌آمدگویی', 'message': '🚀 به ربات مادر خوش آمدید!'},
            'subscription_prompt': {'title': 'درخواست اشتراک', 'message': 'لطفاً مبلغ را واریز کرده و رسید خود را ارسال کنید.'},
            'subscription_activated': {'title': 'فعال‌سازی اشتراک', 'message': '✅ اشتراک شما با موفقیت فعال شد!'},
            'build_instruction': {'title': 'دستورالعمل ساخت', 'message': '📝 لطفاً فایل خود را ارسال کنید.'},
            'payment_guide': {'title': 'راهنمای پرداخت', 'message': '💳 مبلغ را به کارت زیر واریز کنید.'}
        }
        
        for key, data in default_messages.items():
            self._execute('INSERT OR IGNORE INTO system_messages (key, title, message, updated_at) VALUES (?, ?, ?, ?)',
                         (key, data['title'], data['message'], datetime.now().isoformat()))
    
    def _execute(self, query, params=()):
        try:
            cursor = self.sqlite_conn.execute(query, params)
            self.sqlite_conn.commit()
            return cursor.fetchall()
        except Exception as e:
            print(f"DB error: {e}")
            return []
    
    def get_setting(self, key):
        """دریافت تنظیمات با اولویت: Redis > MongoDB > SQLite"""
        
        # اول Redis
        if self.redis:
            cached = self.redis.get(f"setting_{key}")
            if cached:
                return cached
        
        # بعد MongoDB
        if self.mongo:
            setting = self.mongo.system_settings.find_one({'_id': key})
            if setting:
                value = setting.get('value')
                if self.redis:
                    self.redis.setex(f"setting_{key}", 3600, str(value))
                return value
        
        # نهایت SQLite
        result = self._execute("SELECT value FROM system_settings WHERE key = ?", (key,))
        if result:
            return result[0]['value']
        
        return None
    
    def update_setting(self, key, value, updated_by=None):
        """به‌روزرسانی تنظیمات در همه دیتابیس‌ها"""
        
        # به‌روزرسانی در SQLite
        self._execute("UPDATE system_settings SET value = ?, updated_by = ?, updated_at = ? WHERE key = ?",
                     (str(value), updated_by, datetime.now().isoformat(), key))
        
        # به‌روزرسانی در MongoDB
        if self.mongo:
            self.mongo.system_settings.update_one(
                {'_id': key},
                {'$set': {'value': value, 'updated_by': updated_by, 'updated_at': datetime.now()}},
                upsert=True
            )
        
        # حذف کش در Redis
        if self.redis:
            self.redis.delete(f"setting_{key}")
        
        return True
    
    def get_message(self, key):
        """دریافت پیام سیستم"""
        result = self._execute("SELECT message FROM system_messages WHERE key = ?", (key,))
        if result:
            return result[0]['message']
        return None
    
    def update_message(self, key, message, title, updated_by):
        """به‌روزرسانی پیام سیستم"""
        self._execute("UPDATE system_messages SET title = ?, message = ?, updated_by = ?, updated_at = ? WHERE key = ?",
                     (title, message, updated_by, datetime.now().isoformat(), key))
        return True
    
    def get_user_bots_count(self, user_id):
        """تعداد ربات‌های کاربر"""
        result = self._execute("SELECT COUNT(*) as count FROM bots WHERE user_id = ?", (user_id,))
        return result[0]['count'] if result else 0
    
    def can_create_bot(self, user_id):
        """بررسی مجاز بودن ساخت ربات جدید (حداکثر ۳ تا)"""
        max_bots = int(self.get_setting('max_bots_per_user') or 3)
        current_bots = self.get_user_bots_count(user_id)
        return current_bots < max_bots, max_bots, current_bots
    
    def add_bot(self, bot_id, user_id, token, name, username, file_path, folder_path=None):
        """افزودن ربات جدید"""
        now = datetime.now().isoformat()
        self._execute('''
            INSERT INTO bots 
            (id, user_id, token, name, username, file_path, folder_path, status, created_at, last_active, execution_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'stopped', ?, ?, 0)
        ''', (bot_id, user_id, token, name, username, file_path, folder_path, now, now))
        
        self._execute('UPDATE users SET bots_count = bots_count + 1, total_builds = total_builds + 1 WHERE user_id = ?', (user_id,))
        
        return True
    
    def add_execution(self, exec_id, user_id, bot_id):
        """ثبت اجرای جدید"""
        now = datetime.now().isoformat()
        self._execute('''
            INSERT INTO executions (id, user_id, bot_id, status, started_at)
            VALUES (?, ?, ?, 'running', ?)
        ''', (exec_id, user_id, bot_id, now))
        return True
    
    def update_execution_result(self, exec_id, status, output=None, error=None):
        """به‌روزرسانی نتیجه اجرا"""
        ended_at = datetime.now().isoformat()
        self._execute('''
            UPDATE executions 
            SET status = ?, ended_at = ?, output = ?, error = ?
            WHERE id = ?
        ''', (status, ended_at, output, error, exec_id))
        return True
    
    def create_folder(self, folder_id, user_id, folder_name, folder_path, structure):
        """ایجاد پوشه جدید"""
        now = datetime.now().isoformat()
        self._execute('''
            INSERT INTO folders (id, user_id, folder_name, folder_path, structure, created_at, last_used, file_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        ''', (folder_id, user_id, folder_name, folder_path, structure, now, now))
        
        self._execute('UPDATE users SET folders_count = folders_count + 1 WHERE user_id = ?', (user_id,))
        return True
    
    def get_user_folders(self, user_id):
        """دریافت پوشه‌های کاربر"""
        return self._execute('SELECT * FROM folders WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    
    def get_folder_by_id(self, folder_id):
        """دریافت پوشه با آیدی"""
        result = self._execute('SELECT * FROM folders WHERE id = ?', (folder_id,))
        return dict(result[0]) if result else None
    
    def add_library(self, name, version):
        """اضافه کردن کتابخانه نصب شده"""
        now = datetime.now().isoformat()
        self._execute('INSERT OR IGNORE INTO installed_libraries (name, version, installed_at) VALUES (?, ?, ?)',
                     (name, version, now))
        return True
    
    def get_installed_libraries(self):
        """دریافت کتابخانه‌های نصب شده"""
        return self._execute('SELECT * FROM installed_libraries ORDER BY installed_at DESC')
    
    def deactivate_all_user_bots(self, user_id):
        """غیرفعال کردن تمام ربات‌های کاربر"""
        self._execute('UPDATE bots SET status = "stopped", next_deactivation = NULL WHERE user_id = ? AND status = "running"', (user_id,))
        return True

# ایجاد نمونه دیتابیس
ultra_db = UltraDatabase()

# ==================== سیستم اجرای ۵ دقیقه‌ای پیشرفته ====================

class FiveMinuteExecutor:
    """سیستم اجرای ۵ دقیقه‌ای فوق پیشرفته"""
    
    def __init__(self):
        self.active_executions = {}
        self.execution_timers = {}
        self.lock = threading.RLock()
        self.executor_pool = ThreadPoolExecutor(max_workers=100)
        self._start_monitor()
    
    def _start_monitor(self):
        """شروع مانیتورینگ خودکار"""
        def monitor():
            while True:
                try:
                    now = datetime.now()
                    # پیدا کردن ربات‌هایی که زمانشان تمام شده
                    expired = ultra_db._execute('''
                        SELECT id, user_id, token, file_path, folder_path, next_deactivation 
                        FROM bots 
                        WHERE status = "running" 
                        AND next_deactivation IS NOT NULL 
                        AND next_deactivation <= ?
                    ''', (now.isoformat(),))
                    
                    for bot in expired:
                        self.stop_bot_execution(bot['id'], bot['user_id'])
                    
                    time.sleep(10)
                except Exception as e:
                    print(f"Monitor error: {e}")
                    time.sleep(30)
        
        threading.Thread(target=monitor, daemon=True).start()
    
    def execute_bot(self, bot_id, user_id, code, folder_path=None):
        """اجرای ربات برای ۵ دقیقه"""
        
        exec_id = str(uuid.uuid4())[:8]
        
        # ذخیره اجرا
        ultra_db.add_execution(exec_id, user_id, bot_id)
        
        # تنظیم زمان غیرفعال‌سازی (5 دقیقه بعد)
        duration = int(ultra_db.get_setting('execution_duration') or 5)
        deactivation_time = datetime.now() + timedelta(minutes=duration)
        
        ultra_db._execute('''
            UPDATE bots 
            SET status = 'running', 
                last_execution = ?, 
                execution_count = execution_count + 1,
                next_deactivation = ?,
                is_5min_mode = 1
            WHERE id = ?
        ''', (datetime.now().isoformat(), deactivation_time.isoformat(), bot_id))
        
        # اجرا در thread جداگانه
        with self.lock:
            self.active_executions[bot_id] = {
                'exec_id': exec_id,
                'started_at': datetime.now(),
                'deactivation_at': deactivation_time,
                'code': code,
                'process': None
            }
        
        # شروع اجرا
        self.executor_pool.submit(self._run_bot_code, bot_id, user_id, exec_id, code, folder_path)
        
        # تنظیم تایمر برای غیرفعال‌سازی
        timer = threading.Timer(duration * 60, self._auto_stop, [bot_id, user_id])
        timer.daemon = True
        timer.start()
        
        with self.lock:
            self.execution_timers[bot_id] = timer
        
        return exec_id, deactivation_time
    
    def _run_bot_code(self, bot_id, user_id, exec_id, code, folder_path):
        """اجرای کد ربات در محیط ایزوله"""
        try:
            # ایجاد محیط ایزوله
            bot_dir = os.path.join(DIRS['RUNNING'], bot_id)
            os.makedirs(bot_dir, exist_ok=True)
            
            # ذخیره کد در فایل موقت
            code_path = os.path.join(bot_dir, 'bot_code.py')
            with open(code_path, 'w', encoding='utf-8') as f:
                f.write(code)
            
            # اجرا با subprocess
            process = subprocess.Popen(
                [sys.executable, code_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=bot_dir if not folder_path else folder_path,
                text=True
            )
            
            with self.lock:
                if bot_id in self.active_executions:
                    self.active_executions[bot_id]['process'] = process
            
            # دریافت خروجی با تایم‌اوت
            try:
                stdout, stderr = process.communicate(timeout=300)  # 5 دقیقه حداکثر
                output = stdout[:1000] if stdout else "اجرا شد"
                error = stderr[:500] if stderr else None
                
                ultra_db.update_execution_result(exec_id, 'completed', output, error)
            except subprocess.TimeoutExpired:
                process.kill()
                ultra_db.update_execution_result(exec_id, 'timeout', error="زمان اجرا تمام شد")
            
        except Exception as e:
            ultra_db.update_execution_result(exec_id, 'error', error=str(e)[:500])
        finally:
            # پاکسازی فایل‌های موقت
            try:
                shutil.rmtree(bot_dir, ignore_errors=True)
            except:
                pass
    
    def _auto_stop(self, bot_id, user_id):
        """توقف خودکار ربات بعد از ۵ دقیقه"""
        self.stop_bot_execution(bot_id, user_id)
    
    def stop_bot_execution(self, bot_id, user_id):
        """توقف اجرای ربات"""
        with self.lock:
            if bot_id in self.active_executions:
                info = self.active_executions[bot_id]
                if info.get('process'):
                    try:
                        info['process'].kill()
                    except:
                        pass
                
                del self.active_executions[bot_id]
            
            if bot_id in self.execution_timers:
                try:
                    self.execution_timers[bot_id].cancel()
                except:
                    pass
                del self.execution_timers[bot_id]
        
        # به‌روزرسانی دیتابیس
        ultra_db._execute('''
            UPDATE bots 
            SET status = 'stopped', next_deactivation = NULL, is_5min_mode = 0 
            WHERE id = ?
        ''', (bot_id,))
        
        ultra_db._execute('''
            UPDATE executions 
            SET status = 'auto_stopped', ended_at = ?
            WHERE bot_id = ? AND status = 'running'
        ''', (datetime.now().isoformat(), bot_id))
        
        # اطلاع به کاربر
        try:
            temp_bot = telebot.TeleBot(BOT_TOKEN)
            temp_bot.send_message(user_id, f"⏰ زمان ۵ دقیقه‌ای ربات شما به پایان رسید. برای اجرای مجدد، دکمه اجرا را بزنید.")
        except:
            pass
        
        return True
    
    def get_execution_status(self, bot_id):
        """دریافت وضعیت اجرا"""
        with self.lock:
            if bot_id in self.active_executions:
                info = self.active_executions[bot_id]
                remaining = (info['deactivation_at'] - datetime.now()).total_seconds()
                return {
                    'running': True,
                    'remaining_minutes': max(0, int(remaining / 60)),
                    'remaining_seconds': max(0, int(remaining % 60)),
                    'deactivation_at': info['deactivation_at'].isoformat()
                }
        
        return {'running': False}

# ==================== سیستم مدیریت پوشه‌ها و ساختار ====================

class FolderManager:
    """مدیریت پوشه‌ها و ساختارهای کاربران"""
    
    def __init__(self):
        self.folder_locks = defaultdict(threading.Lock)
    
    def create_user_folder(self, user_id, folder_name):
        """ایجاد پوشه جدید برای کاربر"""
        
        # ساختار پوشه
        folder_path = os.path.join(DIRS['FOLDERS'], str(user_id), folder_name)
        
        if os.path.exists(folder_path):
            return None, "پوشه با این نام قبلاً وجود دارد"
        
        try:
            os.makedirs(folder_path, exist_ok=True)
            
            # ایجاد فایل‌های اولیه
            structure = {
                'name': folder_name,
                'created_at': datetime.now().isoformat(),
                'files': [],
                'subfolders': []
            }
            
            # ذخیره در دیتابیس
            folder_id = hashlib.md5(f"{user_id}_{folder_name}_{time.time()}".encode()).hexdigest()[:12]
            ultra_db.create_folder(folder_id, user_id, folder_name, folder_path, json.dumps(structure))
            
            return folder_id, "پوشه با موفقیت ایجاد شد"
        except Exception as e:
            return None, f"خطا در ایجاد پوشه: {str(e)}"
    
    def add_file_to_folder(self, folder_id, file_name, file_content):
        """افزودن فایل به پوشه"""
        folder = ultra_db.get_folder_by_id(folder_id)
        if not folder:
            return False, "پوشه یافت نشد"
        
        folder_path = folder['folder_path']
        file_path = os.path.join(folder_path, file_name)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file_content)
            
            # به‌روزرسانی ساختار
            structure = json.loads(folder['structure'])
            structure['files'].append({
                'name': file_name,
                'path': file_path,
                'added_at': datetime.now().isoformat(),
                'size': len(file_content)
            })
            
            ultra_db._execute('UPDATE folders SET structure = ?, last_used = ?, file_count = file_count + 1 WHERE id = ?',
                            (json.dumps(structure), datetime.now().isoformat(), folder_id))
            
            return True, "فایل با موفقیت اضافه شد"
        except Exception as e:
            return False, f"خطا: {str(e)}"
    
    def get_folder_structure(self, folder_id):
        """دریافت ساختار پوشه"""
        folder = ultra_db.get_folder_by_id(folder_id)
        if not folder:
            return None
        return json.loads(folder['structure'])
    
    def get_folder_files(self, folder_id):
        """دریافت فایل‌های پوشه"""
        structure = self.get_folder_structure(folder_id)
        if structure:
            return structure.get('files', [])
        return []
    
    def read_file_content(self, folder_id, file_name):
        """خواندن محتوای فایل"""
        folder = ultra_db.get_folder_by_id(folder_id)
        if not folder:
            return None
        
        file_path = os.path.join(folder['folder_path'], file_name)
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        return None

# ==================== سیستم کتابخانه‌های دلخواه حرفه‌ای ====================

class LibraryManager:
    """مدیریت نصب کتابخانه‌های دلخواه"""
    
    def __init__(self):
        self.installing = set()
        self.install_lock = threading.Lock()
    
    def get_available_libraries(self):
        """لیست کتابخانه‌های موجود"""
        return {
            'Web Frameworks': {
                'Flask': 'flask',
                'FastAPI': 'fastapi',
                'Django': 'django',
                'Sanic': 'sanic',
                'Quart': 'quart',
            },
            'Async Libraries': {
                'aiohttp': 'aiohttp',
                'httpx': 'httpx',
                'aiogram': 'aiogram',
                'asyncio': 'asyncio',
                'uvloop': 'uvloop',
            },
            'Database': {
                'SQLAlchemy': 'sqlalchemy',
                'asyncpg': 'asyncpg',
                'Motor (MongoDB)': 'motor',
                'redis-py': 'redis',
                'Psycopg2': 'psycopg2-binary',
            },
            'Data Science': {
                'NumPy': 'numpy',
                'Pandas': 'pandas',
                'Matplotlib': 'matplotlib',
                'Scikit-learn': 'scikit-learn',
            },
            'Telegram Bots': {
                'pyTelegramBotAPI': 'pyTelegramBotAPI',
                'python-telegram-bot': 'python-telegram-bot',
                'aiogram 3.x': 'aiogram',
            },
            'Utils': {
                'Requests': 'requests',
                'BeautifulSoup': 'beautifulsoup4',
                'Selenium': 'selenium',
                'Pillow': 'Pillow',
                'jdatetime': 'jdatetime',
                'cryptography': 'cryptography',
                'loguru': 'loguru',
                'tqdm': 'tqdm',
            }
        }
    
    def install_library(self, lib_name, chat_id, message_id, bot_instance):
        """نصب کتابخانه با نمایش پیشرفت"""
        
        if lib_name in self.installing:
            bot_instance.edit_message_text(f"⏳ {lib_name} در حال نصب است...", chat_id, message_id)
            return False
        
        with self.install_lock:
            self.installing.add(lib_name)
        
        def install():
            try:
                bot_instance.edit_message_text(f"📦 در حال نصب {lib_name}...", chat_id, message_id)
                
                process = subprocess.run(
                    [sys.executable, '-m', 'pip', 'install', lib_name, '--quiet', '--no-cache-dir'],
                    capture_output=True,
                    text=True,
                    timeout=180
                )
                
                if process.returncode == 0:
                    # دریافت نسخه
                    version = self._get_library_version(lib_name)
                    ultra_db.add_library(lib_name, version)
                    
                    bot_instance.edit_message_text(
                        f"✅ کتابخانه {lib_name} با موفقیت نصب شد!\n📌 نسخه: {version}",
                        chat_id, message_id
                    )
                else:
                    error = process.stderr[:300] if process.stderr else "خطای ناشناخته"
                    bot_instance.edit_message_text(
                        f"❌ خطا در نصب {lib_name}:\n{error}",
                        chat_id, message_id
                    )
            except subprocess.TimeoutExpired:
                bot_instance.edit_message_text(f"❌ زمان نصب {lib_name} به پایان رسید", chat_id, message_id)
            except Exception as e:
                bot_instance.edit_message_text(f"❌ خطا: {str(e)[:100]}", chat_id, message_id)
            finally:
                with self.install_lock:
                    self.installing.discard(lib_name)
        
        threading.Thread(target=install, daemon=True).start()
        return True
    
    def _get_library_version(self, lib_name):
        """دریافت نسخه کتابخانه"""
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'show', lib_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            for line in result.stdout.split('\n'):
                if line.startswith('Version:'):
                    return line.split(':', 1)[1].strip()
        except:
            pass
        return "نامشخص"
    
    def uninstall_library(self, lib_name, chat_id, message_id, bot_instance):
        """حذف کتابخانه"""
        try:
            process = subprocess.run(
                [sys.executable, '-m', 'pip', 'uninstall', lib_name, '-y', '--quiet'],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if process.returncode == 0:
                ultra_db._execute('DELETE FROM installed_libraries WHERE name = ?', (lib_name,))
                bot_instance.edit_message_text(f"✅ {lib_name} با موفقیت حذف شد", chat_id, message_id)
            else:
                bot_instance.edit_message_text(f"❌ خطا در حذف {lib_name}", chat_id, message_id)
        except Exception as e:
            bot_instance.edit_message_text(f"❌ خطا: {str(e)[:100]}", chat_id, message_id)

# ==================== ربات اصلی با تنظیمات کامل ====================

BOT_TOKEN = "8266270866:AAF6m1x4weSUEvzIj1gkbIS_j0yAdxCSs78"
ADMIN_IDS = [327855654]
BOT_USERNAME = "ROBTTSAZE_bot"

# ایجاد نمونه‌ها
bot = telebot.TeleBot(BOT_TOKEN)
bot.delete_webhook()

executor = FiveMinuteExecutor()
folder_manager = FolderManager()
library_manager = LibraryManager()

# ==================== توابع کمکی ====================

def get_user(user_id):
    result = ultra_db._execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    return dict(result[0]) if result else None

def create_user(user_id, username, first_name, last_name, referred_by=None):
    now = datetime.now().isoformat()
    referral_code = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:12]
    
    ultra_db._execute('''
        INSERT OR IGNORE INTO users 
        (user_id, username, first_name, last_name, referral_code, referred_by, created_at, last_active, subscription_status, wallet_balance)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'inactive', 0)
    ''', (user_id, username, first_name, last_name, referral_code, referred_by, now, now))
    
    return True

def activate_subscription(user_id):
    """فعال‌سازی اشتراک کاربر"""
    now = datetime.now()
    expiry = now + timedelta(days=30)
    
    ultra_db._execute('''
        UPDATE users 
        SET subscription_status = 'active', subscription_expiry = ?, active_until = ?
        WHERE user_id = ?
    ''', (expiry.isoformat(), expiry.isoformat(), user_id))
    
    return expiry

def check_subscription(user_id):
    """بررسی وضعیت اشتراک"""
    user = get_user(user_id)
    if not user:
        return False
    
    if user['subscription_status'] == 'active':
        expiry = datetime.fromisoformat(user['subscription_expiry'])
        if expiry > datetime.now():
            return True
    
    return False

def extract_token_from_code(code):
    """استخراج توکن از کد"""
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

def is_valid_bot_token(token):
    """بررسی اعتبار توکن"""
    try:
        resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        return resp.status_code == 200
    except:
        return False

def get_bot_info(token):
    """دریافت اطلاعات ربات"""
    resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
    if resp.status_code == 200:
        return resp.json()['result']
    return None

# ==================== منوهای پیشرفته ====================

def get_main_menu(user_id):
    """منوی اصلی کاربر"""
    is_admin = user_id in ADMIN_IDS
    user = get_user(user_id)
    has_subscription = check_subscription(user_id)
    
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    
    buttons = []
    
    if has_subscription:
        buttons.extend([
            types.KeyboardButton('🤖 ساخت ربات جدید'),
            types.KeyboardButton('📁 مدیریت پوشه‌ها'),
            types.KeyboardButton('▶️ اجرای ربات (۵ دقیقه)'),
            types.KeyboardButton('📋 ربات‌های من'),
            types.KeyboardButton('🔄 فعال/غیرفعال'),
            types.KeyboardButton('🗑 حذف ربات'),
        ])
    else:
        buttons.append(types.KeyboardButton('💰 خرید اشتراک'))
    
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
            types.KeyboardButton('⚙️ تنظیمات پیام‌ها')
        ])
    
    markup.add(*buttons)
    return markup

# ==================== دستورات اصلی ====================

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
        users = ultra_db._execute('SELECT user_id FROM users WHERE referral_code = ?', (code,))
        if users and users[0]['user_id'] != user_id:
            referred_by = users[0]['user_id']
    
    create_user(user_id, username, first_name, message.from_user.last_name or "", referred_by)
    user = get_user(user_id)
    
    # پیام خوش‌آمدگویی
    welcome_msg = ultra_db.get_message('welcome') or "🚀 به ربات مادر خوش آمدید!"
    
    text = f"{welcome_msg}\n\n"
    text += f"👤 نام: {first_name}\n"
    text += f"🆔 شناسه: `{user_id}`\n"
    text += f"🎁 کد معرف: `{user['referral_code']}`\n"
    text += f"💰 موجودی: {user['wallet_balance']:,} تومان\n"
    
    if check_subscription(user_id):
        expiry = datetime.fromisoformat(user['subscription_expiry'])
        text += f"✅ اشتراک فعال تا: {expiry.strftime('%Y-%m-%d')}\n"
        text += f"🤖 ربات ساخته شده: {ultra_db.get_user_bots_count(user_id)}/{ultra_db.get_setting('max_bots_per_user')}\n"
    else:
        text += f"❌ اشتراک: غیرفعال\n"
        text += f"💰 قیمت اشتراک: {ultra_db.get_setting('subscription_price_str')}\n"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown', 
                    reply_markup=get_main_menu(user_id))

# ==================== خرید اشتراک ====================

@bot.message_handler(func=lambda m: m.text == '💰 خرید اشتراک')
def buy_subscription(message):
    user_id = message.from_user.id
    
    if check_subscription(user_id):
        bot.send_message(message.chat.id, "✅ شما قبلاً اشتراک فعال دارید!")
        return
    
    price = ultra_db.get_setting('subscription_price_str')
    card = ultra_db.get_setting('card_number_display')
    holder = ultra_db.get_setting('card_holder')
    bank = ultra_db.get_setting('card_bank')
    
    text = f"""
💳 **خرید اشتراک ماهیانه**

💰 مبلغ: {price}

🏦 اطلاعات کارت:
`{card}`
👤 {holder}
🏦 {bank}

📌 **نحوه پرداخت:**
1️⃣ مبلغ را به کارت فوق واریز کنید
2️⃣ رسید را به صورت عکس ارسال کنید
3️⃣ پس از تایید، اشتراک شما فعال می‌شود

⏱ زمان بررسی: حداکثر ۲۴ ساعت
    """
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== ساخت ربات جدید با توضیحات کامل ====================

@bot.message_handler(func=lambda m: m.text == '🤖 ساخت ربات جدید')
def new_bot(message):
    user_id = message.from_user.id
    
    # بررسی اشتراک
    if not check_subscription(user_id):
        bot.send_message(message.chat.id, 
                        f"❌ اشتراک فعال نیست!\n💰 هزینه اشتراک: {ultra_db.get_setting('subscription_price_str')}\n"
                        f"از دکمه `💰 خرید اشتراک` استفاده کنید.", 
                        parse_mode='Markdown')
        return
    
    # بررسی محدودیت تعداد ربات‌ها (حداکثر ۳ تا)
    can_create, max_bots, current_bots = ultra_db.can_create_bot(user_id)
    if not can_create:
        bot.send_message(message.chat.id, 
                        f"⚠️ شما به حداکثر مجاز {max_bots} ربات رسیده‌اید!\n"
                        f"برای ساخت ربات جدید، ابتدا یکی از ربات‌های خود را حذف کنید.")
        return
    
    # پیام شفاف و کامل
    text = f"""
🌟 **ساخت ربات جدید**

کاربر گرامی {message.from_user.first_name} 
از اینکه ربات قدرتمند ما را برای اجرای کد خود انتخاب کردید، ممنون هستیم!

📌 **مراحل ساخت:**
1️⃣ مبلغ {ultra_db.get_setting('subscription_price_str')} را به کارت زیر واریز کنید
2️⃣ همینجا رسید خود را ارسال کنید (عکس)
3️⃣ پس از تایید، اشتراک شما فعال می‌شود

💳 **اطلاعات کارت:**
`{ultra_db.get_setting('card_number_display')}`
👤 {ultra_db.get_setting('card_holder')}
🏦 {ultra_db.get_setting('card_bank')}

⏱ **زمان بررسی:** حداکثر ۲۴ ساعت

⚠️ **توجه:** 
- هر کاربر حداکثر {ultra_db.get_setting('max_bots_per_user')} ربات می‌تواند داشته باشد
- هر بار اجرای ربات به مدت {ultra_db.get_setting('execution_duration')} دقیقه است
- توکن ربات خود را داخل کد قرار دهید

✅ **پس از فعال شدن اشتراک**، می‌توانید:
- فایل .py یا .zip خود را ارسال کنید
- یا از طریق پوشه‌ها، کد خود را سازماندهی کنید
    """
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== رسید پرداخت ====================

@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    
    # بررسی فیش تکراری
    existing = ultra_db._execute('SELECT id FROM receipts WHERE user_id = ? AND status = "pending"', (user_id,))
    if existing:
        bot.reply_to(message, "⏳ فیش قبلی شما در انتظار تایید است. لطفاً صبور باشید.")
        return
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        payment_code = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:8].upper()
        receipt_path = os.path.join(DIRS['RECEIPTS'], f"{user_id}_{payment_code}.jpg")
        
        with open(receipt_path, 'wb') as f:
            f.write(downloaded)
        
        ultra_db._execute('''
            INSERT INTO receipts (user_id, amount, receipt_path, payment_code, created_at, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
        ''', (user_id, ultra_db.get_setting('subscription_price'), receipt_path, payment_code, datetime.now().isoformat()))
        
        bot.reply_to(message, 
                    f"✅ فیش شما دریافت شد!\n"
                    f"💰 مبلغ: {ultra_db.get_setting('subscription_price_str')}\n"
                    f"🆔 کد پیگیری: {payment_code}\n\n"
                    f"⏱ ظرف ۲۴ ساعت بررسی و نتیجه به شما اعلام می‌شود.")
        
        # اطلاع به ادمین‌ها
        user = get_user(user_id)
        for admin_id in ADMIN_IDS:
            try:
                with open(receipt_path, 'rb') as f:
                    bot.send_photo(admin_id, f, 
                                  caption=f"📸 **فیش جدید**\n"
                                         f"👤 کاربر: {user['first_name']}\n"
                                         f"🆔 آیدی: {user_id}\n"
                                         f"💰 مبلغ: {ultra_db.get_setting('subscription_price_str')}\n"
                                         f"🆔 کد: {payment_code}",
                                  parse_mode='Markdown')
            except:
                pass
    
    except Exception as e:
        bot.reply_to(message, f"❌ خطا در دریافت فیش: {str(e)}")

# ==================== پیام تایید اشتراک ====================

def send_subscription_activated_message(user_id):
    """ارسال پیام تایید اشتراک با توضیحات کامل"""
    
    user = get_user(user_id)
    max_bots = ultra_db.get_setting('max_bots_per_user')
    exec_duration = ultra_db.get_setting('execution_duration')
    
    text = f"""
✅ **اشتراک شما با موفقیت فعال شد!**

کاربر گرامی {user['first_name']}
اشتراک ماهیانه شما فعال گردید.

📋 **امکانات شما:**
- ساخت حداکثر {max_bots} ربات
- هر بار اجرا به مدت {exec_duration} دقیقه
- دسترسی به تمام کتابخانه‌ها
- مدیریت پوشه‌ها و فایل‌ها

📌 **نحوه ساخت ربات:**

**روش اول - ارسال فایل:**
- فایل .py یا .zip خود را ارسال کنید
- مطمئن شوید توکن داخل کد شما هست

**روش دوم - ساخت پوشه:**
1️⃣ از منوی `📁 مدیریت پوشه‌ها` استفاده کنید
2️⃣ یک پوشه جدید با نام دلخواه بسازید
3️⃣ فایل‌های خود را داخل پوشه آپلود کنید
4️⃣ کد اصلی را با نام `main.py` ذخیره کنید

▶️ **اجرای ربات:**
- پس از ساخت ربات، از منوی `▶️ اجرای ربات (۵ دقیقه)` استفاده کنید
- ربات شما به مدت {exec_duration} دقیقه اجرا می‌شود
- پس از اتمام زمان، خودکار متوقف می‌شود

⚠️ **نکات مهم:**
- توکن ربات حتماً داخل کد شما باشد
- از کتابخانه‌های مجاز استفاده کنید
- حداکثر {max_bots} ربات فعال می‌توانید داشته باشید

موفق باشید! 🚀
    """
    
    bot.send_message(user_id, text, parse_mode='Markdown')

# ==================== مدیریت پوشه‌ها ====================

@bot.message_handler(func=lambda m: m.text == '📁 مدیریت پوشه‌ها')
def manage_folders(message):
    user_id = message.from_user.id
    
    if not check_subscription(user_id):
        bot.send_message(message.chat.id, "❌ ابتدا اشتراک خود را فعال کنید!")
        return
    
    folders = ultra_db.get_user_folders(user_id)
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    # دکمه ساخت پوشه جدید
    markup.add(types.InlineKeyboardButton("📁➕ ساخت پوشه جدید", callback_data="create_folder"))
    
    if folders:
        markup.add(types.InlineKeyboardButton("📂 لیست پوشه‌های من", callback_data="list_folders"))
    
    bot.send_message(message.chat.id, "📁 **مدیریت پوشه‌ها**\n\n"
                    "می‌توانید پوشه‌های خود را مدیریت کنید.\n"
                    "در هر پوشه می‌توانید چندین فایل پایتون قرار دهید.",
                    parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "create_folder")
def create_folder_prompt(call):
    msg = bot.send_message(call.message.chat.id, "📁 **نام پوشه جدید را وارد کنید:**\n(فقط حروف انگلیسی و عدد)")
    bot.register_next_step_handler(msg, process_create_folder)
    bot.answer_callback_query(call.id)

def process_create_folder(message):
    user_id = message.from_user.id
    folder_name = message.text.strip()
    
    # اعتبارسنجی نام
    if not re.match(r'^[a-zA-Z0-9_\-]+$', folder_name):
        bot.reply_to(message, "❌ نام پوشه فقط می‌تواند شامل حروف انگلیسی، اعداد، خط تیره و زیرخط باشد.")
        return
    
    folder_id, result = folder_manager.create_user_folder(user_id, folder_name)
    
    if folder_id:
        bot.reply_to(message, f"✅ پوشه `{folder_name}` با موفقیت ساخته شد!\n\n"
                    f"🆔 آیدی پوشه: `{folder_id}`\n\n"
                    f"حالا می‌توانید:\n"
                    f"• از منوی مدیریت فایل‌ها، فایل‌های خود را اضافه کنید\n"
                    f"• فایل اصلی خود را با نام `main.py` ذخیره کنید\n"
                    f"• سپس ربات خود را از طریق این پوشه اجرا کنید",
                    parse_mode='Markdown')
    else:
        bot.reply_to(message, f"❌ {result}")

@bot.callback_query_handler(func=lambda call: call.data == "list_folders")
def list_folders(call):
    user_id = call.from_user.id
    folders = ultra_db.get_user_folders(user_id)
    
    if not folders:
        bot.send_message(call.message.chat.id, "📂 شما هیچ پوشه‌ای ندارید.")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for folder in folders:
        markup.add(types.InlineKeyboardButton(f"📂 {folder['folder_name']}", 
                                             callback_data=f"view_folder_{folder['id']}"))
    
    bot.edit_message_text("📂 **پوشه‌های شما:**", 
                         call.message.chat.id, 
                         call.message.message_id,
                         parse_mode='Markdown',
                         reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('view_folder_'))
def view_folder(call):
    folder_id = call.data.replace('view_folder_', '')
    folder = ultra_db.get_folder_by_id(folder_id)
    
    if not folder:
        bot.answer_callback_query(call.id, "پوشه یافت نشد!")
        return
    
    structure = json.loads(folder['structure'])
    files = structure.get('files', [])
    
    text = f"📁 **{folder['folder_name']}**\n\n"
    text += f"🆔 آیدی: `{folder_id}`\n"
    text += f"📅 ساخته شده: {folder['created_at'][:16]}\n"
    text += f"📄 تعداد فایل‌ها: {len(files)}\n\n"
    
    if files:
        text += "**فایل‌ها:**\n"
        for f in files:
            text += f"• `{f['name']}` ({f['size']} بایت)\n"
    else:
        text += "📂 هیچ فایلی در این پوشه وجود ندارد."
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("📄 افزودن فایل", callback_data=f"add_file_{folder_id}"))
    markup.add(types.InlineKeyboardButton("▶️ اجرا به عنوان ربات", callback_data=f"run_folder_bot_{folder_id}"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="list_folders"))
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                         parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('add_file_'))
def add_file_prompt(call):
    folder_id = call.data.replace('add_file_', '')
    msg = bot.send_message(call.message.chat.id, "📄 **نام فایل را وارد کنید:**\n(مثال: main.py)")
    bot.register_next_step_handler(msg, process_add_file_name, folder_id, call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id)

def process_add_file_name(message, folder_id, chat_id, original_msg_id):
    file_name = message.text.strip()
    
    if not file_name.endswith('.py'):
        bot.reply_to(message, "❌ فقط فایل‌های پایتون (.py) مجاز هستند.")
        return
    
    msg = bot.send_message(message.chat.id, f"📝 **محتوای فایل {file_name} را ارسال کنید:**\n(کد پایتون خود را بنویسید)")
    bot.register_next_step_handler(msg, process_add_file_content, folder_id, file_name, chat_id, original_msg_id)

def process_add_file_content(message, folder_id, file_name, chat_id, original_msg_id):
    content = message.text
    
    success, result = folder_manager.add_file_to_folder(folder_id, file_name, content)
    
    if success:
        bot.reply_to(message, f"✅ فایل `{file_name}` با موفقیت اضافه شد!\n\n"
                    f"برای اجرای ربات، از دکمه `▶️ اجرا به عنوان ربات` استفاده کنید.",
                    parse_mode='Markdown')
    else:
        bot.reply_to(message, f"❌ {result}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('run_folder_bot_'))
def run_folder_bot(call):
    user_id = call.from_user.id
    folder_id = call.data.replace('run_folder_bot_', '')
    
    if not check_subscription(user_id):
        bot.answer_callback_query(call.id, "اشتراک شما فعال نیست!", show_alert=True)
        return
    
    # بررسی محدودیت تعداد ربات‌ها
    can_create, max_bots, current_bots = ultra_db.can_create_bot(user_id)
    if not can_create:
        bot.answer_callback_query(call.id, f"شما حداکثر {max_bots} ربات می‌توانید داشته باشید!", show_alert=True)
        return
    
    folder = ultra_db.get_folder_by_id(folder_id)
    if not folder:
        bot.answer_callback_query(call.id, "پوشه یافت نشد!")
        return
    
    # پیدا کردن فایل اصلی
    structure = json.loads(folder['structure'])
    files = structure.get('files', [])
    
    main_file = None
    for f in files:
        if f['name'] == 'main.py':
            main_file = f
            break
    
    if not main_file:
        bot.answer_callback_query(call.id, "فایل main.py در پوشه یافت نشد!", show_alert=True)
        return
    
    # خواندن محتوای فایل اصلی
    code = folder_manager.read_file_content(folder_id, 'main.py')
    if not code:
        bot.answer_callback_query(call.id, "خطا در خواندن فایل!", show_alert=True)
        return
    
    # استخراج توکن
    token = extract_token_from_code(code)
    if not token:
        bot.answer_callback_query(call.id, "توکن در کد پیدا نشد!\nلطفاً token = 'YOUR_TOKEN' را اضافه کنید.", show_alert=True)
        return
    
    # بررسی اعتبار توکن
    if not is_valid_bot_token(token):
        bot.answer_callback_query(call.id, "توکن نامعتبر است!", show_alert=True)
        return
    
    bot_info = get_bot_info(token)
    
    # ایجاد ربات
    bot_id = hashlib.md5(f"{user_id}_{token}_{time.time()}".encode()).hexdigest()[:16]
    ultra_db.add_bot(bot_id, user_id, token, bot_info['first_name'], bot_info['username'], 
                    main_file.get('path', ''), folder['folder_path'])
    
    # اجرای ربات
    exec_id, deactivation_time = executor.execute_bot(bot_id, user_id, code, folder['folder_path'])
    
    bot.edit_message_text(
        f"✅ ربات `{bot_info['first_name']}` با موفقیت اجرا شد!\n\n"
        f"🆔 آیدی ربات: `{bot_id}`\n"
        f"🤖 نام: @{bot_info['username']}\n"
        f"⏱ زمان اجرا: {ultra_db.get_setting('execution_duration')} دقیقه\n"
        f"⏰ زمان غیرفعال‌سازی: {deactivation_time.strftime('%H:%M:%S')}\n\n"
        f"پس از اتمام زمان، ربات به طور خودکار متوقف می‌شود.",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown'
    )

# ==================== اجرای ربات (۵ دقیقه) ====================

@bot.message_handler(func=lambda m: m.text == '▶️ اجرای ربات (۵ دقیقه)')
def run_bot_prompt(message):
    user_id = message.from_user.id
    
    if not check_subscription(user_id):
        bot.send_message(message.chat.id, "❌ ابتدا اشتراک خود را فعال کنید!")
        return
    
    bots = ultra_db._execute('SELECT id, name, username, status FROM bots WHERE user_id = ?', (user_id,))
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما هیچ رباتی ندارید!\nاز دکمه `🤖 ساخت ربات جدید` استفاده کنید.", parse_mode='Markdown')
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        status_emoji = "🟢" if b['status'] == 'running' else "🔴"
        markup.add(types.InlineKeyboardButton(f"{status_emoji} {b['name']}", callback_data=f"execute_bot_{b['id']}"))
    
    bot.send_message(message.chat.id, "▶️ **انتخاب ربات برای اجرا:**\n\n"
                    "⚠️ توجه: هر بار اجرا به مدت ۵ دقیقه است.\n"
                    "پس از اتمام زمان، ربات خودکار متوقف می‌شود.",
                    parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('execute_bot_'))
def execute_bot(call):
    user_id = call.from_user.id
    bot_id = call.data.replace('execute_bot_', '')
    
    if not check_subscription(user_id):
        bot.answer_callback_query(call.id, "اشتراک شما فعال نیست!", show_alert=True)
        return
    
    # دریافت اطلاعات ربات
    bot_info = ultra_db._execute('SELECT * FROM bots WHERE id = ? AND user_id = ?', (bot_id, user_id))
    if not bot_info:
        bot.answer_callback_query(call.id, "ربات یافت نشد!", show_alert=True)
        return
    
    bot_info = dict(bot_info[0])
    
    # بررسی وضعیت فعلی
    status = executor.get_execution_status(bot_id)
    if status['running']:
        bot.answer_callback_query(call.id, 
                                 f"ربات در حال اجراست!\nزمان باقیمانده: {status['remaining_minutes']}:{status['remaining_seconds']:02d}",
                                 show_alert=True)
        return
    
    # خواندن کد
    if bot_info['folder_path'] and os.path.exists(bot_info['folder_path']):
        main_path = os.path.join(bot_info['folder_path'], 'main.py')
        if os.path.exists(main_path):
            with open(main_path, 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
        else:
            code = None
    elif bot_info['file_path'] and os.path.exists(bot_info['file_path']):
        with open(bot_info['file_path'], 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()
    else:
        bot.answer_callback_query(call.id, "فایل ربات یافت نشد!", show_alert=True)
        return
    
    if not code:
        bot.answer_callback_query(call.id, "خطا در خواندن کد!", show_alert=True)
        return
    
    # اجرا
    exec_id, deactivation_time = executor.execute_bot(bot_id, user_id, code, bot_info.get('folder_path'))
    
    bot.answer_callback_query(call.id, f"✅ ربات با موفقیت اجرا شد!\nزمان اجرا: ۵ دقیقه", show_alert=True)
    
    bot.edit_message_text(
        f"✅ ربات `{bot_info['name']}` در حال اجراست!\n\n"
        f"⏱ مدت زمان: {ultra_db.get_setting('execution_duration')} دقیقه\n"
        f"⏰ زمان غیرفعال‌سازی: {deactivation_time.strftime('%H:%M:%S')}\n\n"
        f"پس از اتمام زمان، ربات خودکار متوقف می‌شود.\n"
        f"برای توقف زودهنگام از منوی ربات‌های من استفاده کنید.",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown'
    )

# ==================== وضعیت اجرا ====================

@bot.message_handler(func=lambda m: m.text == '⚡ وضعیت اجرا')
def execution_status(message):
    user_id = message.from_user.id
    bots = ultra_db._execute('SELECT id, name, status FROM bots WHERE user_id = ?', (user_id,))
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما هیچ رباتی ندارید!")
        return
    
    text = "⚡ **وضعیت اجرای ربات‌ها**\n\n"
    
    for b in bots:
        status = executor.get_execution_status(b['id'])
        if status['running']:
            text += f"🟢 **{b['name']}**\n"
            text += f"   ⏱ زمان باقیمانده: {status['remaining_minutes']}:{status['remaining_seconds']:02d}\n"
            text += f"   ⏰ غیرفعال‌سازی: {status['deactivation_at'][11:16]}\n\n"
        else:
            text += f"🔴 **{b['name']}** - متوقف\n\n"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== کتابخانه‌های دلخواه ====================

@bot.message_handler(func=lambda m: m.text == '📦 کتابخانه‌ها')
def libraries_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("📚 لیست کتابخانه‌ها", callback_data="lib_list"))
    markup.add(types.InlineKeyboardButton("🔧 نصب کتابخانه دلخواه", callback_data="lib_install_custom"))
    markup.add(types.InlineKeyboardButton("✅ کتابخانه‌های نصب شده", callback_data="lib_installed"))
    
    bot.send_message(message.chat.id, "📦 **مدیریت کتابخانه‌ها**\n\n"
                    "می‌توانید کتابخانه‌های پایتون را نصب کنید.\n"
                    "کتابخانه‌های نصب شده در تمام ربات‌ها قابل استفاده هستند.",
                    parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "lib_list")
def library_list(call):
    libs = library_manager.get_available_libraries()
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    for category, items in libs.items():
        markup.add(types.InlineKeyboardButton(f"📁 {category}", callback_data=f"lib_cat_{category}"))
    
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="lib_back"))
    
    bot.edit_message_text("📚 **دسته‌بندی کتابخانه‌ها:**\n"
                         "روی هر دسته کلیک کنید تا کتابخانه‌های آن را ببینید.",
                         call.message.chat.id,
                         call.message.message_id,
                         parse_mode='Markdown',
                         reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lib_cat_'))
def library_category(call):
    category = call.data.replace('lib_cat_', '')
    libs = library_manager.get_available_libraries()
    
    if category not in libs:
        bot.answer_callback_query(call.id, "دسته یافت نشد!")
        return
    
    items = libs[category]
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for name, lib in items.items():
        markup.add(types.InlineKeyboardButton(f"📦 {name}", callback_data=f"lib_install_{lib}"))
    
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="lib_list"))
    
    bot.edit_message_text(f"📁 **{category}**\n\n"
                         f"برای نصب هر کتابخانه روی آن کلیک کنید:",
                         call.message.chat.id,
                         call.message.message_id,
                         parse_mode='Markdown',
                         reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lib_install_'))
def install_library_callback(call):
    lib_name = call.data.replace('lib_install_', '')
    
    status_msg = bot.send_message(call.message.chat.id, f"🔄 در حال نصب {lib_name}...")
    
    library_manager.install_library(lib_name, call.message.chat.id, status_msg.message_id, bot)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "lib_install_custom")
def install_custom_prompt(call):
    msg = bot.send_message(call.message.chat.id, "🔧 **نام کتابخانه مورد نظر را وارد کنید:**\n(مثال: requests, numpy, etc.)")
    bot.register_next_step_handler(msg, process_custom_install)
    bot.answer_callback_query(call.id)

def process_custom_install(message):
    lib_name = message.text.strip()
    status_msg = bot.reply_to(message, f"🔄 در حال نصب {lib_name}...")
    library_manager.install_library(lib_name, message.chat.id, status_msg.message_id, bot)

@bot.callback_query_handler(func=lambda call: call.data == "lib_installed")
def installed_libraries(call):
    libs = ultra_db.get_installed_libraries()
    
    if not libs:
        bot.edit_message_text("📦 **کتابخانه‌های نصب شده**\n\n"
                             "هیچ کتابخانه‌ای نصب نشده است.\n"
                             "از منوی اصلی کتابخانه‌ها برای نصب استفاده کنید.",
                             call.message.chat.id,
                             call.message.message_id,
                             parse_mode='Markdown')
        return
    
    text = "✅ **کتابخانه‌های نصب شده**\n\n"
    for lib in libs:
        text += f"• `{lib['name']}` - نسخه {lib['version']}\n"
        text += f"  📅 نصب: {lib['installed_at'][:16]}\n\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="lib_back"))
    
    bot.edit_message_text(text,
                         call.message.chat.id,
                         call.message.message_id,
                         parse_mode='Markdown',
                         reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "lib_back")
def lib_back(call):
    libraries_menu(call.message)

# ==================== ربات‌های من ====================

@bot.message_handler(func=lambda m: m.text == '📋 ربات‌های من')
def my_bots(message):
    user_id = message.from_user.id
    bots = ultra_db._execute('SELECT * FROM bots WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما هیچ رباتی ندارید!\nاز دکمه `🤖 ساخت ربات جدید` استفاده کنید.", parse_mode='Markdown')
        return
    
    text = "🤖 **لیست ربات‌های شما**\n\n"
    
    for b in bots:
        b = dict(b)
        status = executor.get_execution_status(b['id'])
        
        if status['running']:
            status_text = f"🟢 در حال اجرا ({status['remaining_minutes']}:{status['remaining_seconds']:02d})"
        else:
            status_text = "🔴 متوقف"
        
        text += f"**{b['name']}**\n"
        text += f"🆔 `{b['id']}`\n"
        text += f"🔗 t.me/{b['username']}\n"
        text += f"📊 وضعیت: {status_text}\n"
        text += f"▶️ تعداد اجرا: {b['execution_count']}\n"
        text += f"📅 ساخته شده: {b['created_at'][:16]}\n\n"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== سایر منوها ====================

@bot.message_handler(func=lambda m: m.text == '💰 کیف پول')
def wallet(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    text = f"💰 **کیف پول شما**\n\n"
    text += f"👤 {user['first_name']}\n"
    text += f"💵 موجودی: {user['wallet_balance']:,} تومان\n"
    text += f"👥 دعوت‌ها: {user['referrals_count']}\n"
    text += f"💰 کمیسیون هر دعوت: {ultra_db.get_setting('withdraw_percent')}%\n"
    text += f"💸 حداقل برداشت: {int(ultra_db.get_setting('min_withdraw')):,} تومان"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '👥 دعوت دوستان')
def invite(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    referral_link = f"https://t.me/{BOT_USERNAME}?start={user['referral_code']}"
    
    text = f"👥 **سیستم دعوت دوستان**\n\n"
    text += f"🎁 کد معرف: `{user['referral_code']}`\n"
    text += f"🔗 لینک دعوت: `{referral_link}`\n"
    text += f"📊 تعداد دعوت‌ها: {user['referrals_count']}\n"
    text += f"💰 کمیسیون هر دعوت: {ultra_db.get_setting('withdraw_percent')}%\n\n"
    text += f"هر دوست که از طریق لینک شما ثبت‌نام کند و اشتراک بخرد، کمیسیون دریافت می‌کنید!"
    
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
    
    min_withdraw = int(ultra_db.get_setting('min_withdraw'))
    
    if user['wallet_balance'] < min_withdraw:
        bot.send_message(message.chat.id, 
                        f"❌ موجودی شما ({user['wallet_balance']:,} تومان) کمتر از حداقل برداشت ({min_withdraw:,} تومان) است.")
        return
    
    msg = bot.send_message(message.chat.id, "💳 **شماره کارت خود را وارد کنید:**")
    bot.register_next_step_handler(msg, process_withdraw_card)

def process_withdraw_card(message):
    card = message.text.strip()
    msg = bot.send_message(message.chat.id, "👤 **نام صاحب کارت را وارد کنید:**")
    bot.register_next_step_handler(msg, process_withdraw_amount, card)

def process_withdraw_amount(message, card):
    holder = message.text.strip()
    user_id = message.from_user.id
    user = get_user(user_id)
    
    ultra_db._execute('''
        INSERT INTO withdraw_requests (user_id, amount, card_number, card_holder, created_at, status)
        VALUES (?, ?, ?, ?, ?, 'pending')
    ''', (user_id, user['wallet_balance'], card, holder, datetime.now().isoformat()))
    
    ultra_db._execute('UPDATE users SET wallet_balance = 0 WHERE user_id = ?', (user_id,))
    
    bot.reply_to(message, f"✅ درخواست برداشت {user['wallet_balance']:,} تومان ثبت شد.\nپس از بررسی، مبلغ به کارت شما واریز می‌شود.")
    
    for admin_id in ADMIN_IDS:
        bot.send_message(admin_id, f"💰 درخواست برداشت جدید\n👤 کاربر: {user['first_name']}\n🆔 {user_id}\n💰 مبلغ: {user['wallet_balance']:,} تومان")

@bot.message_handler(func=lambda m: m.text == '📚 راهنما')
def guide(message):
    guide_text = ultra_db.get_message('guide') or """
📚 **راهنمای جامع ربات مادر**

**🎯 نحوه ساخت ربات:**
1. ابتدا اشتراک خود را فعال کنید
2. فایل .py یا .zip را ارسال کنید
3. یا از طریق پوشه‌ها کد خود را سازماندهی کنید

**▶️ اجرای ربات:**
- هر بار اجرا ۵ دقیقه است
- پس از اتمام زمان خودکار متوقف می‌شود
- می‌توانید مجدداً اجرا کنید

**📁 مدیریت پوشه‌ها:**
- پوشه‌های مختلف برای پروژه‌های مختلف
- فایل‌های خود را داخل پوشه آپلود کنید
- فایل اصلی باید main.py باشد

**📦 کتابخانه‌ها:**
- می‌توانید هر کتابخانه پایتونی نصب کنید
- کتابخانه‌های نصب شده در همه ربات‌ها قابل استفاده است

**💰 سیستم مالی:**
- هر دعوت ۷٪ کمیسیون
- حداقل برداشت ۲ میلیون تومان

**🆘 پشتیبانی:**
در صورت مشکل با @shahraghee13 تماس بگیرید.
"""
    
    bot.send_message(message.chat.id, guide_text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '📊 آمار')
def stats(message):
    users_count = ultra_db._execute('SELECT COUNT(*) as count FROM users')[0]['count']
    active_subs = ultra_db._execute('SELECT COUNT(*) as count FROM users WHERE subscription_status = "active"')[0]['count']
    bots_count = ultra_db._execute('SELECT COUNT(*) as count FROM bots')[0]['count']
    folders_count = ultra_db._execute('SELECT COUNT(*) as count FROM folders')[0]['count']
    total_wallet = ultra_db._execute('SELECT SUM(wallet_balance) as total FROM users')[0]['total'] or 0
    total_executions = ultra_db._execute('SELECT COUNT(*) as count FROM executions')[0]['count']
    
    text = f"📊 **آمار سیستم**\n\n"
    text += f"👥 کل کاربران: {users_count:,}\n"
    text += f"✅ اشتراک فعال: {active_subs:,}\n"
    text += f"🤖 ربات‌ها: {bots_count:,}\n"
    text += f"📁 پوشه‌ها: {folders_count:,}\n"
    text += f"▶️ کل اجراها: {total_executions:,}\n"
    text += f"💰 موجودی کل: {total_wallet:,} تومان\n"
    text += f"⚡ محدودیت هر کاربر: {ultra_db.get_setting('max_bots_per_user')} ربات\n"
    text += f"⏱ زمان هر اجرا: {ultra_db.get_setting('execution_duration')} دقیقه"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '📞 پشتیبانی')
def support(message):
    bot.send_message(message.chat.id, "📞 **پشتیبانی ربات مادر**\n\n"
                    "برای ارتباط با پشتیبانی:\n"
                    "🆔 @shahraghee13\n\n"
                    "سوالات خود را بپرسید، در اسرع وقت پاسخ داده می‌شود.",
                    parse_mode='Markdown')

# ==================== فعال/غیرفعال و حذف ربات ====================

@bot.message_handler(func=lambda m: m.text == '🔄 فعال/غیرفعال')
def toggle_bot_prompt(message):
    user_id = message.from_user.id
    bots = ultra_db._execute('SELECT id, name, status FROM bots WHERE user_id = ?', (user_id,))
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما هیچ رباتی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        status_emoji = "🟢" if b['status'] == 'running' else "🔴"
        markup.add(types.InlineKeyboardButton(f"{status_emoji} {b['name']}", callback_data=f"toggle_bot_{b['id']}"))
    
    bot.send_message(message.chat.id, "🔄 **انتخاب ربات:**", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_bot_'))
def toggle_bot(call):
    bot_id = call.data.replace('toggle_bot_', '')
    user_id = call.from_user.id
    
    status = executor.get_execution_status(bot_id)
    
    if status['running']:
        executor.stop_bot_execution(bot_id, user_id)
        bot.answer_callback_query(call.id, "✅ ربات متوقف شد!")
    else:
        # اجرای مجدد
        bot_info = ultra_db._execute('SELECT * FROM bots WHERE id = ? AND user_id = ?', (bot_id, user_id))
        if bot_info:
            bot_info = dict(bot_info[0])
            
            if bot_info['folder_path'] and os.path.exists(bot_info['folder_path']):
                main_path = os.path.join(bot_info['folder_path'], 'main.py')
                if os.path.exists(main_path):
                    with open(main_path, 'r', encoding='utf-8') as f:
                        code = f.read()
                    executor.execute_bot(bot_id, user_id, code, bot_info['folder_path'])
                    bot.answer_callback_query(call.id, "✅ ربات اجرا شد!")
                else:
                    bot.answer_callback_query(call.id, "فایل main.py یافت نشد!")
            else:
                bot.answer_callback_query(call.id, "فایل ربات یافت نشد!")
    
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: m.text == '🗑 حذف ربات')
def delete_bot_prompt(message):
    user_id = message.from_user.id
    bots = ultra_db._execute('SELECT id, name FROM bots WHERE user_id = ?', (user_id,))
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما هیچ رباتی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        markup.add(types.InlineKeyboardButton(f"🗑 {b['name']}", callback_data=f"delete_bot_{b['id']}"))
    
    bot.send_message(message.chat.id, "🗑 **ربات مورد نظر برای حذف:**", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_bot_'))
def confirm_delete_bot(call):
    bot_id = call.data.replace('delete_bot_', '')
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ بله، حذف شود", callback_data=f"confirm_del_{bot_id}"),
              types.InlineKeyboardButton("❌ انصراف", callback_data="cancel_del"))
    
    bot.edit_message_text("⚠️ **آیا از حذف این ربات اطمینان دارید؟**\nاین عمل غیرقابل بازگشت است.",
                         call.message.chat.id,
                         call.message.message_id,
                         parse_mode='Markdown',
                         reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_del_'))
def do_delete_bot(call):
    bot_id = call.data.replace('confirm_del_', '')
    user_id = call.from_user.id
    
    # توقف ربات اگر در حال اجراست
    executor.stop_bot_execution(bot_id, user_id)
    
    # حذف از دیتابیس
    ultra_db._execute('DELETE FROM bots WHERE id = ? AND user_id = ?', (bot_id, user_id))
    ultra_db._execute('UPDATE users SET bots_count = bots_count - 1 WHERE user_id = ?', (user_id,))
    
    bot.edit_message_text("✅ ربات با موفقیت حذف شد.",
                         call.message.chat.id,
                         call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "cancel_del")
def cancel_delete(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)

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
    )
    
    bot.send_message(message.chat.id, "👑 **پنل مدیریت پیشرفته**", parse_mode='Markdown', reply_markup=markup)

# تایید فیش
@bot.callback_query_handler(func=lambda call: call.data == "admin_receipts")
def admin_receipts(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    receipts = ultra_db._execute('SELECT * FROM receipts WHERE status = "pending" ORDER BY created_at')
    
    if not receipts:
        bot.send_message(call.message.chat.id, "📸 هیچ فیش در انتظار تاییدی وجود ندارد.")
        return
    
    for r in receipts:
        r = dict(r)
        user = get_user(r['user_id'])
        
        text = f"📸 **فیش پرداخت**\n"
        text += f"👤 کاربر: {user['first_name'] if user else 'نامشخص'}\n"
        text += f"🆔 آیدی: {r['user_id']}\n"
        text += f"💰 مبلغ: {r['amount']:,} تومان\n"
        text += f"🆔 کد: `{r['payment_code']}`\n"
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
    receipt = ultra_db._execute('SELECT user_id FROM receipts WHERE id = ?', (rid,))
    
    if receipt:
        user_id = receipt[0]['user_id']
        
        # به‌روزرسانی وضعیت فیش
        ultra_db._execute('UPDATE receipts SET status = "approved", reviewed_by = ?, reviewed_at = ? WHERE id = ?',
                         (call.from_user.id, datetime.now().isoformat(), rid))
        
        # فعال‌سازی اشتراک
        expiry = activate_subscription(user_id)
        
        # ارسال پیام تایید به کاربر
        send_subscription_activated_message(user_id)
        
        bot.answer_callback_query(call.id, "✅ اشتراک کاربر فعال شد!")
        bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_receipt_'))
def reject_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    rid = int(call.data.replace('reject_receipt_', ''))
    receipt = ultra_db._execute('SELECT user_id, payment_code FROM receipts WHERE id = ?', (rid,))
    
    if receipt:
        user_id = receipt[0]['user_id']
        
        ultra_db._execute('UPDATE receipts SET status = "rejected", reviewed_by = ?, reviewed_at = ? WHERE id = ?',
                         (call.from_user.id, datetime.now().isoformat(), rid))
        
        bot.send_message(user_id, f"❌ متأسفانه فیش پرداخت شما رد شد.\n"
                        f"کد پیگیری: {receipt[0]['payment_code']}\n\n"
                        f"لطفاً مجدداً اقدام کنید یا با پشتیبانی تماس بگیرید.")
        
        bot.answer_callback_query(call.id, "❌ فیش رد شد!")
        bot.delete_message(call.message.chat.id, call.message.message_id)

# مدیریت کاربران
@bot.callback_query_handler(func=lambda call: call.data == "admin_users")
def admin_users(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🔍 جستجوی کاربر", callback_data="admin_search_user"),
        types.InlineKeyboardButton("💰 افزایش موجودی", callback_data="admin_add_balance"),
        types.InlineKeyboardButton("🎁 فعال‌سازی اشتراک", callback_data="admin_activate_sub"),
        types.InlineKeyboardButton("🚫 مسدود کردن کاربر", callback_data="admin_ban_user"),
        types.InlineKeyboardButton("📋 لیست کاربران", callback_data="admin_list_users"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    bot.edit_message_text("👥 **مدیریت کاربران**",
                         call.message.chat.id,
                         call.message.message_id,
                         parse_mode='Markdown',
                         reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_search_user")
def admin_search_user(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, "🔍 **آیدی عددی کاربر را وارد کنید:**")
    bot.register_next_step_handler(msg, process_admin_search)
    bot.answer_callback_query(call.id)

def process_admin_search(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        user_id = int(message.text.strip())
        user = get_user(user_id)
        
        if user:
            bots = ultra_db._execute('SELECT COUNT(*) as count FROM bots WHERE user_id = ?', (user_id,))
            executions = ultra_db._execute('SELECT COUNT(*) as count FROM executions WHERE user_id = ?', (user_id,))
            
            text = f"👤 **اطلاعات کاربر**\n\n"
            text += f"نام: {user['first_name']}\n"
            text += f"آیدی: `{user['user_id']}`\n"
            text += f"نام کاربری: @{user['username'] if user['username'] else 'ندارد'}\n"
            text += f"💰 موجودی: {user['wallet_balance']:,} تومان\n"
            text += f"✅ اشتراک: {'فعال' if check_subscription(user_id) else 'غیرفعال'}\n"
            if user['subscription_expiry']:
                text += f"📅 انقضا: {user['subscription_expiry'][:16]}\n"
            text += f"🤖 تعداد ربات: {bots[0]['count']}\n"
            text += f"▶️ تعداد اجرا: {executions[0]['count']}\n"
            text += f"👥 دعوت‌ها: {user['referrals_count']}\n"
            text += f"📅 عضویت: {user['created_at'][:16]}"
            
            bot.reply_to(message, text, parse_mode='Markdown')
        else:
            bot.reply_to(message, "❌ کاربر یافت نشد!")
    except:
        bot.reply_to(message, "❌ آیدی نامعتبر!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_add_balance")
def admin_add_balance(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, "💰 **فرمت: آیدی کاربر مبلغ**\nمثال: `123456789 100000`")
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
            new_balance = user['wallet_balance'] + amount
            ultra_db._execute('UPDATE users SET wallet_balance = ? WHERE user_id = ?', (new_balance, user_id))
            
            bot.reply_to(message, f"✅ {amount:,} تومان به کیف پول {user['first_name']} اضافه شد.\nموجودی جدید: {new_balance:,} تومان")
            bot.send_message(user_id, f"💰 مبلغ {amount:,} تومان به کیف پول شما اضافه شد.")
        else:
            bot.reply_to(message, "❌ کاربر یافت نشد!")
    except:
        bot.reply_to(message, "❌ فرمت نامعتبر! مثال: `123456789 100000`")

@bot.callback_query_handler(func=lambda call: call.data == "admin_activate_sub")
def admin_activate_sub(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, "🎁 **آیدی عددی کاربر را وارد کنید:**")
    bot.register_next_step_handler(msg, process_admin_activate_sub)
    bot.answer_callback_query(call.id)

def process_admin_activate_sub(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        user_id = int(message.text.strip())
        user = get_user(user_id)
        
        if user:
            expiry = activate_subscription(user_id)
            send_subscription_activated_message(user_id)
            
            bot.reply_to(message, f"✅ اشتراک {user['first_name']} تا {expiry.strftime('%Y-%m-%d')} فعال شد.")
        else:
            bot.reply_to(message, "❌ کاربر یافت نشد!")
    except:
        bot.reply_to(message, "❌ آیدی نامعتبر!")

# تنظیمات سیستم
@bot.callback_query_handler(func=lambda call: call.data == "admin_settings")
def admin_settings(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    current_max_bots = ultra_db.get_setting('max_bots_per_user')
    current_exec_duration = ultra_db.get_setting('execution_duration')
    current_price = ultra_db.get_setting('subscription_price_str')
    
    text = f"⚙️ **تنظیمات فعلی سیستم**\n\n"
    text += f"📌 حداکثر ربات هر کاربر: {current_max_bots}\n"
    text += f"⏱ زمان هر اجرا: {current_exec_duration} دقیقه\n"
    text += f"💰 قیمت اشتراک: {current_price}\n"
    text += f"👥 کمیسیون دعوت: {ultra_db.get_setting('withdraw_percent')}%\n"
    text += f"💸 حداقل برداشت: {int(ultra_db.get_setting('min_withdraw')):,} تومان\n"
    text += f"⚡ حداکثر ساخت همزمان: {ultra_db.get_setting('max_concurrent_builds')}"
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📌 تغییر حداکثر ربات", callback_data="admin_set_max_bots"),
        types.InlineKeyboardButton("⏱ تغییر زمان اجرا", callback_data="admin_set_exec_duration"),
        types.InlineKeyboardButton("💰 تغییر قیمت اشتراک", callback_data="admin_set_price"),
        types.InlineKeyboardButton("👥 تغییر کمیسیون", callback_data="admin_set_withdraw_percent"),
        types.InlineKeyboardButton("💸 تغییر حداقل برداشت", callback_data="admin_set_min_withdraw"),
        types.InlineKeyboardButton("💳 تغییر اطلاعات کارت", callback_data="admin_set_card"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    bot.edit_message_text(text,
                         call.message.chat.id,
                         call.message.message_id,
                         parse_mode='Markdown',
                         reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_max_bots")
def admin_set_max_bots(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, "📌 **حداکثر تعداد ربات برای هر کاربر (عدد):**\nمثال: 3")
    bot.register_next_step_handler(msg, process_set_max_bots)
    bot.answer_callback_query(call.id)

def process_set_max_bots(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        value = int(message.text.strip())
        if 1 <= value <= 50:
            ultra_db.update_setting('max_bots_per_user', value, message.from_user.id)
            bot.reply_to(message, f"✅ حداکثر ربات هر کاربر به {value} تغییر کرد.")
        else:
            bot.reply_to(message, "❌ عدد باید بین 1 تا 50 باشد.")
    except:
        bot.reply_to(message, "❌ عدد معتبر وارد کنید.")

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_exec_duration")
def admin_set_exec_duration(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, "⏱ **زمان هر اجرا به دقیقه (عدد):**\nمثال: 5")
    bot.register_next_step_handler(msg, process_set_exec_duration)
    bot.answer_callback_query(call.id)

def process_set_exec_duration(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        value = int(message.text.strip())
        if 1 <= value <= 60:
            ultra_db.update_setting('execution_duration', value, message.from_user.id)
            bot.reply_to(message, f"✅ زمان هر اجرا به {value} دقیقه تغییر کرد.")
        else:
            bot.reply_to(message, "❌ عدد باید بین 1 تا 60 باشد.")
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
        ultra_db.update_setting('subscription_price', price, message.from_user.id)
        ultra_db.update_setting('subscription_price_str', f"{price:,} تومان", message.from_user.id)
        bot.reply_to(message, f"✅ قیمت اشتراک به {price:,} تومان تغییر کرد.")
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
        ultra_db.update_setting('card_number', card, message.from_user.id)
        display = ' '.join([card[i:i+4] for i in range(0, 16, 4)])
        ultra_db.update_setting('card_number_display', display, message.from_user.id)
        
        msg = bot.send_message(message.chat.id, "👤 **نام صاحب کارت:**")
        bot.register_next_step_handler(msg, process_set_card_holder, card)
    else:
        bot.reply_to(message, "❌ شماره کارت باید ۱۶ رقم باشد.")

def process_set_card_holder(message, card):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    holder = message.text.strip()
    ultra_db.update_setting('card_holder', holder, message.from_user.id)
    bot.reply_to(message, f"✅ اطلاعات کارت به‌روزرسانی شد.\n`{ultra_db.get_setting('card_number_display')}`\n👤 {holder}")

# تنظیم پیام‌های سیستم
@bot.callback_query_handler(func=lambda call: call.data == "admin_messages")
def admin_messages(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    messages = ultra_db._execute('SELECT key, title FROM system_messages')
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for msg in messages:
        markup.add(types.InlineKeyboardButton(f"📝 {msg['title']}", callback_data=f"edit_message_{msg['key']}"))
    
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back"))
    
    bot.edit_message_text("📝 **تنظیم پیام‌های سیستم**\n\n"
                         "روی هر پیام کلیک کنید تا متن آن را تغییر دهید.",
                         call.message.chat.id,
                         call.message.message_id,
                         parse_mode='Markdown',
                         reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('edit_message_'))
def edit_message_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    key = call.data.replace('edit_message_', '')
    current = ultra_db.get_message(key)
    
    msg = bot.send_message(call.message.chat.id, 
                          f"📝 **ویرایش پیام**\n\n"
                          f"کلید: `{key}`\n"
                          f"متن فعلی:\n{current}\n\n"
                          f"متن جدید را ارسال کنید:")
    
    bot.register_next_step_handler(msg, process_edit_message, key, call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id)

def process_edit_message(message, key, chat_id, msg_id):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    new_text = message.text
    ultra_db.update_message(key, new_text, f"پیام {key}", message.from_user.id)
    
    bot.reply_to(message, f"✅ پیام با موفقیت به‌روزرسانی شد.")
    bot.delete_message(chat_id, msg_id)

# گزارش کامل
@bot.callback_query_handler(func=lambda call: call.data == "admin_full_report")
def admin_full_report(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    users_count = ultra_db._execute('SELECT COUNT(*) as count FROM users')[0]['count']
    active_subs = ultra_db._execute('SELECT COUNT(*) as count FROM users WHERE subscription_status = "active"')[0]['count']
    bots_count = ultra_db._execute('SELECT COUNT(*) as count FROM bots')[0]['count']
    folders_count = ultra_db._execute('SELECT COUNT(*) as count FROM folders')[0]['count']
    executions_count = ultra_db._execute('SELECT COUNT(*) as count FROM executions')[0]['count']
    total_wallet = ultra_db._execute('SELECT SUM(wallet_balance) as total FROM users')[0]['total'] or 0
    total_revenue = ultra_db._execute('SELECT SUM(amount) as total FROM receipts WHERE status = "approved"')[0]['total'] or 0
    pending_receipts = ultra_db._execute('SELECT COUNT(*) as count FROM receipts WHERE status = "pending"')[0]['count']
    pending_withdraws = ultra_db._execute('SELECT COUNT(*) as count FROM withdraw_requests WHERE status = "pending"')[0]['count']
    
    text = f"📊 **گزارش کامل سیستم**\n\n"
    text += f"👥 **کاربران**\n"
    text += f"   کل کاربران: {users_count:,}\n"
    text += f"   اشتراک فعال: {active_subs:,}\n"
    text += f"   نرخ فعال‌سازی: {(active_subs/users_count*100):.1f}%\n\n"
    
    text += f"🤖 **ربات‌ها**\n"
    text += f"   کل ربات‌ها: {bots_count:,}\n"
    text += f"   میانگین هر کاربر: {(bots_count/users_count):.1f}\n\n"
    
    text += f"📁 **پوشه‌ها**\n"
    text += f"   کل پوشه‌ها: {folders_count:,}\n\n"
    
    text += f"▶️ **اجراها**\n"
    text += f"   کل اجراها: {executions_count:,}\n\n"
    
    text += f"💰 **مالی**\n"
    text += f"   موجودی کل: {total_wallet:,} تومان\n"
    text += f"   درآمد کل: {total_revenue:,} تومان\n"
    text += f"   فیش‌های در انتظار: {pending_receipts}\n"
    text += f"   درخواست‌های برداشت: {pending_withdraws}\n\n"
    
    text += f"⚙️ **تنظیمات**\n"
    text += f"   حداکثر ربات هر کاربر: {ultra_db.get_setting('max_bots_per_user')}\n"
    text += f"   زمان هر اجرا: {ultra_db.get_setting('execution_duration')} دقیقه\n"
    text += f"   قیمت اشتراک: {ultra_db.get_setting('subscription_price_str')}"
    
    bot.edit_message_text(text,
                         call.message.chat.id,
                         call.message.message_id,
                         parse_mode='Markdown')

# وضعیت سرور
@bot.callback_query_handler(func=lambda call: call.data == "admin_server_status")
def admin_server_status(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    import psutil
    
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    text = f"🖥️ **وضعیت سرور**\n\n"
    text += f"**CPU**\n"
    text += f"   استفاده: {cpu_percent}%\n"
    text += f"   هسته‌ها: {psutil.cpu_count()}\n\n"
    
    text += f"**RAM**\n"
    text += f"   استفاده: {memory.used / (1024**3):.1f} GB / {memory.total / (1024**3):.1f} GB\n"
    text += f"   درصد: {memory.percent}%\n\n"
    
    text += f"**Disk**\n"
    text += f"   استفاده: {disk.used / (1024**3):.1f} GB / {disk.total / (1024**3):.1f} GB\n"
    text += f"   درصد: {disk.percent}%\n\n"
    
    text += f"**پایگاه‌های داده**\n"
    text += f"   Redis: {'✅ فعال' if REDIS_AVAILABLE else '❌ غیرفعال'}\n"
    text += f"   MongoDB: {'✅ فعال' if MONGO_AVAILABLE else '❌ غیرفعال'}\n"
    text += f"   PostgreSQL: {'✅ فعال' if POSTGRES_AVAILABLE else '❌ غیرفعال'}\n\n"
    
    text += f"**ربات‌ها**\n"
    running_bots = len([k for k in executor.active_executions.keys()])
    text += f"   در حال اجرا: {running_bots}\n"
    text += f"   کل ربات‌ها: {ultra_db._execute('SELECT COUNT(*) as count FROM bots')[0]['count']}"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔄 بروزرسانی", callback_data="admin_server_status"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back"))
    
    bot.edit_message_text(text,
                         call.message.chat.id,
                         call.message.message_id,
                         parse_mode='Markdown',
                         reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call):
    admin_panel(call.message)

# ==================== پیام همگانی ====================

@bot.message_handler(func=lambda m: m.text == '📢 پیام همگانی')
def broadcast_prompt(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(message.chat.id, "📢 **متن پیام همگانی را ارسال کنید:**")
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    text = message.text
    users = ultra_db._execute('SELECT user_id FROM users')
    
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
                         message.chat.id,
                         status_msg.message_id,
                         parse_mode='Markdown')

# ==================== تنظیمات پیام‌ها ====================

@bot.message_handler(func=lambda m: m.text == '⚙️ تنظیمات پیام‌ها')
def messages_settings(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📝 ویرایش پیام خوش‌آمدگویی", callback_data="edit_welcome"),
        types.InlineKeyboardButton("📝 ویرایش راهنما", callback_data="edit_guide"),
        types.InlineKeyboardButton("📝 ویرایش پیام فعال‌سازی", callback_data="edit_activation"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    bot.send_message(message.chat.id, "⚙️ **تنظیمات پیام‌ها**", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "edit_welcome")
def edit_welcome(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, "📝 **متن جدید پیام خوش‌آمدگویی را ارسال کنید:**")
    bot.register_next_step_handler(msg, process_edit_welcome, call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id)

def process_edit_welcome(message, chat_id, msg_id):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    ultra_db.update_message('welcome', message.text, 'پیام خوش‌آمدگویی', message.from_user.id)
    bot.reply_to(message, "✅ پیام خوش‌آمدگویی با موفقیت به‌روزرسانی شد.")
    bot.delete_message(chat_id, msg_id)

@bot.callback_query_handler(func=lambda call: call.data == "edit_guide")
def edit_guide(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, "📝 **متن جدید راهنما را ارسال کنید:**")
    bot.register_next_step_handler(msg, process_edit_guide, call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id)

def process_edit_guide(message, chat_id, msg_id):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    ultra_db.update_setting('guide_text', message.text, message.from_user.id)
    bot.reply_to(message, "✅ راهنما با موفقیت به‌روزرسانی شد.")
    bot.delete_message(chat_id, msg_id)

# ==================== اجرای اصلی ====================

if __name__ == "__main__":
    print("=" * 80)
    print("🚀 ربات مادر فوق پیشرفته - نسخه 23.0 Ultimate Enterprise".center(80))
    print("=" * 80)
    print(f"👑 ادمین‌ها: {ADMIN_IDS}")
    print(f"🤖 نام ربات: @{BOT_USERNAME}")
    print(f"💰 قیمت اشتراک: {ultra_db.get_setting('subscription_price_str')}")
    print(f"📌 حداکثر ربات هر کاربر: {ultra_db.get_setting('max_bots_per_user')}")
    print(f"⏱ زمان هر اجرا: {ultra_db.get_setting('execution_duration')} دقیقه")
    print(f"⭐ کمیسیون رفرال: {ultra_db.get_setting('withdraw_percent')}%")
    print(f"💾 Redis: {'✅' if REDIS_AVAILABLE else '❌'}")
    print(f"💾 MongoDB: {'✅' if MONGO_AVAILABLE else '❌'}")
    print(f"💾 PostgreSQL: {'✅' if POSTGRES_AVAILABLE else '❌'}")
    print("=" * 80)
    print("🔥 ربات با موفقیت راه‌اندازی شد!")
    print("=" * 80)
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)