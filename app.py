#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
═══════════════════════════════════════════════════════════════════════════════
🚀 ربات مادر نهایی - نسخه 23.0 HyperScale Enterprise
⚡ مقیاس ابری - پایگاه داده توزیع شده - اجرای موقتی ۵ دقیقه‌ای
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
import aiohttp
import aiosqlite
import redis
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from functools import wraps
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List, Any
import tempfile
import pathlib
import asyncio

# ==================== تنظیمات پایه HyperScale ====================
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
    'USER_PROJECTS': os.path.join(BASE_DIR, "user_projects"),
    'FOLDER_STRUCTURES': os.path.join(BASE_DIR, "folder_structures")
}

for dir_path in DIRS.values():
    os.makedirs(dir_path, exist_ok=True)

# ==================== توکن و تنظیمات ====================
BOT_TOKEN = "8266270866:AAF6m1x4weSUEvzIj1gkbIS_j0yAdxCSs78"
ADMIN_IDS = [327855654]
BOT_USERNAME = "ROBTTSAZE_bot"

# تنظیمات پیش‌فرض جدید
SETTINGS = {
    'card_number': "5892101187322777",
    'card_number_display': "5892 1011 8732 2777",
    'card_holder': "مرتضی نیکخو خنجری",
    'card_bank': "بانک ملی - سپهر",
    'subscription_price': 2000000,
    'subscription_price_str': "۲,۰۰۰,۰۰۰ تومان",
    'withdraw_percent': 7,
    'min_withdraw': 2000000,
    'max_bots_per_user': 3,  # حداکثر ۳ ربات با یک اشتراک
    'bot_active_minutes': 5,  # هر ربات ۵ دقیقه فعال می‌ماند
    'receipt_review_hours': 24,  # زمان بررسی فیش
    'max_builds_per_hour': 10,
    'max_concurrent_builds': 50,  # افزایش برای مقیاس بالا
    'rate_limit_per_second': 10,
    'health_check_interval': 10,
    'auto_scale_threshold': 70,
    'redis_host': 'localhost',
    'redis_port': 6379,
    'redis_db': 0,
    'db_pool_size': 200,
    'worker_threads': 1000,
    'max_upload_size_mb': 100,
    'session_timeout_minutes': 30
}

# ==================== اتصال به Redis برای Cache توزیع شده ====================
try:
    redis_client = redis.Redis(
        host=SETTINGS['redis_host'],
        port=SETTINGS['redis_port'],
        db=SETTINGS['redis_db'],
        decode_responses=True,
        socket_connect_timeout=5
    )
    redis_client.ping()
    REDIS_AVAILABLE = True
    print("✅ Redis متصل شد - کش توزیع شده فعال")
except Exception as e:
    REDIS_AVAILABLE = False
    print(f"⚠️ Redis در دسترس نیست: {e} - استفاده از کش محلی")

# ==================== لاگینگ فوق پیشرفته ====================
class HighPerformanceLogger:
    def __init__(self):
        self.log_queue = queue.Queue()
        self.logger = logging.getLogger('HyperScaleBot')
        self.logger.setLevel(logging.INFO)
        
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s')
        
        file_handler = RotatingFileHandler(
            os.path.join(DIRS['LOGS'], 'hyperscale_bot.log'),
            maxBytes=1024*1024*1024,  # 1GB
            backupCount=20,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        self._start_worker()
    
    def _start_worker(self):
        def worker():
            while True:
                try:
                    level, msg, args = self.log_queue.get(timeout=1)
                    getattr(self.logger, level)(msg, *args)
                except queue.Empty:
                    continue
                except Exception:
                    pass
        threading.Thread(target=worker, daemon=True).start()
    
    def log(self, level, msg, *args):
        self.log_queue.put((level, msg, args))
    
    def info(self, msg, *args):
        self.log('info', msg, *args)
    
    def error(self, msg, *args):
        self.log('error', msg, *args)
    
    def warning(self, msg, *args):
        self.log('warning', msg, *args)

logger = HighPerformanceLogger()

# ==================== دیتابیس توزیع شده با Connection Pool ====================
class DistributedDatabase:
    def __init__(self):
        self.db_path = os.path.join(DIRS['DB'], 'hyperscale_bot.db')
        self.pool = queue.Queue(maxsize=SETTINGS['db_pool_size'])
        self._init_pool()
        self._init_tables()
    
    def _init_pool(self):
        for _ in range(SETTINGS['db_pool_size']):
            conn = sqlite3.connect(self.db_path, timeout=60, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=-1000000")
            conn.execute("PRAGMA page_size=32768")
            conn.execute("PRAGMA mmap_size=30000000000")
            self.pool.put(conn)
    
    def get_connection(self):
        return self.pool.get(timeout=30)
    
    def return_connection(self, conn):
        self.pool.put(conn)
    
    def execute(self, query, params=(), fetch=True):
        conn = self.get_connection()
        try:
            cursor = conn.execute(query, params)
            conn.commit()
            if fetch:
                return cursor.fetchall()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"DB error: {e} - Query: {query[:100]}")
            return []
        finally:
            self.return_connection(conn)
    
    def executemany(self, query, params_list):
        conn = self.get_connection()
        try:
            cursor = conn.executemany(query, params_list)
            conn.commit()
            return cursor.rowcount
        except Exception as e:
            logger.error(f"DB executemany error: {e}")
            return 0
        finally:
            self.return_connection(conn)
    
    def _init_tables(self):
        # کاربران با فیلدهای جدید
        self.execute('''
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
                verified_referrals INTEGER DEFAULT 0,
                wallet_balance INTEGER DEFAULT 0,
                created_at TIMESTAMP,
                last_active TIMESTAMP,
                warning_sent INTEGER DEFAULT 0,
                total_builds INTEGER DEFAULT 0,
                last_build_at TIMESTAMP,
                language TEXT DEFAULT 'fa',
                notification_enabled INTEGER DEFAULT 1,
                active_sessions INTEGER DEFAULT 0
            )
        ''')
        
        # ربات‌ها با زمان انقضای ۵ دقیقه‌ای
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
                expires_at TIMESTAMP,
                join_enabled INTEGER DEFAULT 1,
                join_block_message TEXT DEFAULT '🚫 سرور در حال حاضر پر است. لطفاً بعداً تلاش کنید.',
                health_status TEXT DEFAULT 'healthy',
                last_health_check TIMESTAMP,
                restart_count INTEGER DEFAULT 0,
                project_type TEXT DEFAULT 'single_file',
                project_structure TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        # پروژه‌های کاربران (ساختار پوشه)
        self.execute('''
            CREATE TABLE IF NOT EXISTS user_projects (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                project_name TEXT,
                folder_path TEXT,
                structure TEXT,
                main_file TEXT,
                created_at TIMESTAMP,
                last_modified TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        # کتابخانه‌های نصب شده
        self.execute('''
            CREATE TABLE IF NOT EXISTS user_libraries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                library_name TEXT,
                version TEXT,
                installed_at TIMESTAMP,
                status TEXT DEFAULT 'installed',
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        # کتابخانه‌های سیستمی پیشنهادی
        self.execute('''
            CREATE TABLE IF NOT EXISTS system_libraries (
                name TEXT PRIMARY KEY,
                description TEXT,
                category TEXT,
                is_premium INTEGER DEFAULT 0,
                install_count INTEGER DEFAULT 0
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
                region TEXT DEFAULT 'default'
            )
        ''')
        
        # فیش‌ها
        self.execute('''
            CREATE TABLE IF NOT EXISTS receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                receipt_path TEXT,
                status TEXT DEFAULT 'pending',
                payment_code TEXT UNIQUE,
                reviewed_by INTEGER,
                reviewed_at TIMESTAMP,
                created_at TIMESTAMP,
                reviewed_at_fa TEXT
            )
        ''')
        
        # درخواست‌های برداشت
        self.execute('''
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
                severity TEXT DEFAULT 'normal'
            )
        ''')
        
        # تنظیمات سیستم
        self.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP,
                updated_by INTEGER
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
                active_bots INTEGER DEFAULT 0
            )
        ''')
        
        # پیام‌های سیستم (قابل تغییر توسط ادمین)
        self.execute('''
            CREATE TABLE IF NOT EXISTS system_messages (
                key TEXT PRIMARY KEY,
                title TEXT,
                content TEXT,
                updated_at TIMESTAMP
            )
        ''')
        
        # ذخیره تنظیمات پیش‌فرض
        for key, value in SETTINGS.items():
            self.execute('''
                INSERT OR IGNORE INTO system_settings (key, value, updated_at)
                VALUES (?, ?, ?)
            ''', (key, str(value), datetime.now().isoformat()))
        
        # ذخیره پیام‌های پیش‌فرض
        default_messages = {
            'build_start': {'title': 'پیام شروع ساخت', 'content': 'کاربر گرامی از اینکه ربات قدرتمند ما را برای اجرای کد خود انتخاب کردید ممنون هستیم.\n\nبرای ساخت لطفاً مبلغ {price} را به کارت زیر واریز کرده و رسید خود را آپلود کنید:\n\n🏦 {bank}\n💳 {card}\n👤 {holder}\n\n⏱️ فرآیند بررسی تا ۲۴ ساعت زمان می‌برد.\n📊 وضعیت خود را از بخش کیف پول پیگیری کنید.'},
            'subscription_active': {'title': 'پیام فعالسازی اشتراک', 'content': 'کاربر گرامی {name}، اشتراک شما با موفقیت فعال شد!\n\n✅ شما می‌توانید حداکثر {max_bots} ربات بسازید.\n⏱️ هر ربات به مدت {duration} دقیقه فعال خواهد بود.\n📁 برای پروژه‌های چندفایلی، ساختار پوشه خود را آماده کنید.\n🔑 مطمئن شوید توکن ربات در کد شما وجود دارد.\n\nاز گزینه‌های زیر انتخاب کنید:'},
            'folder_guide': {'title': 'راهنمای ساختار پوشه', 'content': '📁 راهنمای ساختار پوشه:\n\nبرای پروژه‌های چندفایلی:\n• main.py (فایل اصلی)\n• requirements.txt (کتابخانه‌ها)\n• پوشه‌های دلخواه\n\nبرای ساخت پوشه جدید:\n/folder create <نام پوشه>\n\nبرای آپلود در پوشه:\n/folder upload <نام پوشه>\n\nبرای اجرای پروژه:\n/folder run <نام پوشه>'}
        }
        
        for key, msg in default_messages.items():
            self.execute('''
                INSERT OR IGNORE INTO system_messages (key, title, content, updated_at)
                VALUES (?, ?, ?, ?)
            ''', (key, msg['title'], msg['content'], datetime.now().isoformat()))
        
        # ایندکس‌ها برای سرعت بالا
        indices = [
            "CREATE INDEX IF NOT EXISTS idx_bots_user_id ON bots(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_bots_status ON bots(status)",
            "CREATE INDEX IF NOT EXISTS idx_bots_expires_at ON bots(expires_at)",
            "CREATE INDEX IF NOT EXISTS idx_users_referral_code ON users(referral_code)",
            "CREATE INDEX IF NOT EXISTS idx_users_subscription ON users(subscription_status, subscription_expiry)",
            "CREATE INDEX IF NOT EXISTS idx_receipts_status ON receipts(status)",
            "CREATE INDEX IF NOT EXISTS idx_withdraw_status ON withdraw_requests(status)",
            "CREATE INDEX IF NOT EXISTS idx_errors_timestamp ON errors(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_user_projects_user_id ON user_projects(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_user_libraries_user_id ON user_libraries(user_id)"
        ]
        
        for idx in indices:
            self.execute(idx)

db = DistributedDatabase()

# ==================== کش توزیع شده ====================
class DistributedCache:
    def __init__(self, default_ttl=3600):
        self.default_ttl = default_ttl
        self.local_cache = {}
        self.lock = threading.RLock()
    
    def _get_redis_key(self, key):
        return f"cache:{key}"
    
    def set(self, key, value, ttl=None):
        if ttl is None:
            ttl = self.default_ttl
        
        if REDIS_AVAILABLE:
            try:
                redis_client.setex(self._get_redis_key(key), ttl, json.dumps(value))
                return
            except:
                pass
        
        with self.lock:
            self.local_cache[key] = {
                'value': value,
                'expires': time.time() + ttl
            }
    
    def get(self, key):
        if REDIS_AVAILABLE:
            try:
                data = redis_client.get(self._get_redis_key(key))
                if data:
                    return json.loads(data)
            except:
                pass
        
        with self.lock:
            item = self.local_cache.get(key)
            if item and item['expires'] > time.time():
                return item['value']
            if key in self.local_cache:
                del self.local_cache[key]
        return None
    
    def delete(self, key):
        if REDIS_AVAILABLE:
            try:
                redis_client.delete(self._get_redis_key(key))
            except:
                pass
        with self.lock:
            if key in self.local_cache:
                del self.local_cache[key]
    
    def clear_pattern(self, pattern):
        if REDIS_AVAILABLE:
            try:
                for key in redis_client.scan_iter(f"cache:{pattern}*"):
                    redis_client.delete(key)
            except:
                pass

cache = DistributedCache(ttl=SETTINGS['health_check_interval'])

# ==================== Rate Limiter پیشرفته ====================
class AdvancedRateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
        self.lock = threading.RLock()
    
    def is_allowed(self, user_id, limit_per_second=10):
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
        cache_key = f"builds_today_{user_id}_{datetime.now().date()}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        result = db.execute("SELECT COUNT(*) as count FROM bots WHERE user_id = ? AND DATE(created_at) = DATE('now')", (user_id,))
        count = result[0]['count'] if result else 0
        cache.set(cache_key, count, ttl=3600)
        return count
    
    def increment_user_builds(self, user_id):
        cache_key = f"builds_today_{user_id}_{datetime.now().date()}"
        count = self.get_user_builds_today(user_id) + 1
        cache.set(cache_key, count, ttl=3600)
        return count

rate_limiter = AdvancedRateLimiter()

# ==================== مدیریت پروژه و پوشه ====================
class ProjectManager:
    def __init__(self):
        self.active_projects = {}
        self.lock = threading.RLock()
    
    def create_project_folder(self, user_id: int, folder_name: str) -> dict:
        """ایجاد پوشه پروژه برای کاربر"""
        # پاکسازی نام پوشه
        folder_name = re.sub(r'[^\w\-_.]', '_', folder_name)
        
        user_folder = os.path.join(DIRS['USER_PROJECTS'], str(user_id))
        os.makedirs(user_folder, exist_ok=True)
        
        project_path = os.path.join(user_folder, folder_name)
        
        if os.path.exists(project_path):
            return {'success': False, 'error': 'پوشه با این نام وجود دارد'}
        
        os.makedirs(project_path)
        
        # ساختار پیش‌فرض
        structure = {
            'name': folder_name,
            'path': project_path,
            'files': [],
            'created_at': datetime.now().isoformat(),
            'main_file': None
        }
        
        project_id = str(uuid.uuid4())[:8]
        db.execute('''
            INSERT INTO user_projects (id, user_id, project_name, folder_path, structure, created_at, last_modified)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (project_id, user_id, folder_name, project_path, json.dumps(structure), 
              datetime.now().isoformat(), datetime.now().isoformat()))
        
        return {'success': True, 'project_id': project_id, 'path': project_path}
    
    def upload_file_to_project(self, user_id: int, project_name: str, filename: str, file_content: bytes, subpath: str = '') -> dict:
        """آپلود فایل در پوشه پروژه"""
        user_folder = os.path.join(DIRS['USER_PROJECTS'], str(user_id))
        project_path = os.path.join(user_folder, project_name)
        
        if not os.path.exists(project_path):
            return {'success': False, 'error': 'پروژه یافت نشد'}
        
        if subpath:
            target_dir = os.path.join(project_path, subpath)
            os.makedirs(target_dir, exist_ok=True)
            file_path = os.path.join(target_dir, filename)
        else:
            file_path = os.path.join(project_path, filename)
        
        # جلوگیری از path traversal
        if not os.path.abspath(file_path).startswith(os.path.abspath(project_path)):
            return {'success': False, 'error': 'مسیر نامعتبر'}
        
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        # به‌روزرسانی ساختار
        project = db.execute("SELECT structure, id FROM user_projects WHERE user_id = ? AND project_name = ?", 
                            (user_id, project_name))
        if project:
            structure = json.loads(project[0]['structure'])
            rel_path = os.path.join(subpath, filename) if subpath else filename
            if rel_path not in structure['files']:
                structure['files'].append(rel_path)
            
            if filename.endswith('.py') and not structure.get('main_file'):
                structure['main_file'] = rel_path
            
            db.execute('''
                UPDATE user_projects SET structure = ?, last_modified = ?
                WHERE id = ?
            ''', (json.dumps(structure), datetime.now().isoformat(), project[0]['id']))
        
        return {'success': True, 'file_path': file_path}
    
    def run_project(self, user_id: int, project_name: str, bot_token: str) -> dict:
        """اجرای پروژه به صورت موقت (۵ دقیقه)"""
        user_folder = os.path.join(DIRS['USER_PROJECTS'], str(user_id))
        project_path = os.path.join(user_folder, project_name)
        
        if not os.path.exists(project_path):
            return {'success': False, 'error': 'پروژه یافت نشد'}
        
        project = db.execute("SELECT structure FROM user_projects WHERE user_id = ? AND project_name = ?", 
                            (user_id, project_name))
        if not project:
            return {'success': False, 'error': 'پروژه یافت نشد'}
        
        structure = json.loads(project[0]['structure'])
        main_file = structure.get('main_file')
        
        if not main_file:
            # دنبال فایل اصلی بگرد
            for f in structure.get('files', []):
                if f.endswith('.py') and ('main' in f.lower() or f == 'bot.py'):
                    main_file = f
                    break
        
        if not main_file:
            return {'success': False, 'error': 'فایل اصلی (main.py یا bot.py) یافت نشد'}
        
        main_file_path = os.path.join(project_path, main_file)
        
        with open(main_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()
        
        # نصب کتابخانه‌های مورد نیاز
        req_file = os.path.join(project_path, 'requirements.txt')
        if os.path.exists(req_file):
            with open(req_file, 'r') as f:
                libs = f.read().strip().split('\n')
            for lib in libs:
                if lib.strip():
                    subprocess.run([sys.executable, '-m', 'pip', 'install', lib.strip(), '--quiet'], 
                                 capture_output=True, timeout=60)
        
        # اجرای ربات با زمان انقضای ۵ دقیقه
        bot_id = hashlib.md5(f"{user_id}{bot_token}{time.time()}".encode()).hexdigest()[:16]
        expires_at = datetime.now() + timedelta(minutes=SETTINGS['bot_active_minutes'])
        
        result = machine_manager.run_bot_with_expiry(bot_id, code, bot_token, expires_at)
        
        if result['success']:
            db.execute('''
                INSERT INTO bots (id, user_id, token, name, username, folder_path, pid, machine_id, 
                                 status, created_at, expires_at, project_type, project_structure)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'running', ?, ?, 'folder', ?)
            ''', (bot_id, user_id, bot_token, project_name, f"{project_name}_bot", project_path,
                  result['pid'], result['machine_id'], datetime.now().isoformat(), 
                  expires_at.isoformat(), json.dumps(structure)))
            
            db.execute('UPDATE users SET bots_count = bots_count + 1 WHERE user_id = ?', (user_id,))
            
            # زمانبندی توقف خودکار
            threading.Timer(SETTINGS['bot_active_minutes'] * 60, 
                           lambda: self._auto_stop_bot(bot_id)).start()
        
        return result
    
    def _auto_stop_bot(self, bot_id: str):
        """توقف خودکار ربات بعد از ۵ دقیقه"""
        machine_manager.stop_bot(bot_id)
        db.execute('UPDATE bots SET status = "expired", last_active = ? WHERE id = ?', 
                  (datetime.now().isoformat(), bot_id))
        bot_rec = db.execute('SELECT user_id FROM bots WHERE id = ?', (bot_id,))
        if bot_rec:
            try:
                temp_bot = telebot.TeleBot(BOT_TOKEN)
                temp_bot.send_message(bot_rec[0]['user_id'], 
                    f"⏰ ربات شما به مدت {SETTINGS['bot_active_minutes']} دقیقه فعال بود و اکنون متوقف شد.\n"
                    f"برای فعالسازی مجدد، از بخش ربات‌های من استفاده کنید.")
            except:
                pass
    
    def get_user_projects(self, user_id: int) -> list:
        projects = db.execute('''
            SELECT id, project_name, created_at, last_modified 
            FROM user_projects WHERE user_id = ? ORDER BY last_modified DESC
        ''', (user_id,))
        return [dict(p) for p in projects]
    
    def delete_project(self, user_id: int, project_name: str) -> bool:
        user_folder = os.path.join(DIRS['USER_PROJECTS'], str(user_id))
        project_path = os.path.join(user_folder, project_name)
        
        if os.path.exists(project_path):
            shutil.rmtree(project_path)
        
        db.execute('DELETE FROM user_projects WHERE user_id = ? AND project_name = ?', (user_id, project_name))
        return True

project_manager = ProjectManager()

# ==================== مدیریت کتابخانه‌ها ====================
class LibraryManager:
    def __init__(self):
        self.installing_locks = {}
        self.lock = threading.RLock()
    
    def get_available_libraries(self, search: str = '') -> list:
        """دریافت لیست کتابخانه‌های محبوب"""
        query = "SELECT name, description, category, is_premium, install_count FROM system_libraries"
        params = []
        if search:
            query += " WHERE name LIKE ?"
            params.append(f"%{search}%")
        query += " ORDER BY install_count DESC LIMIT 100"
        
        result = db.execute(query, params)
        if result:
            return [dict(r) for r in result]
        
        # کتابخانه‌های پیش‌فرض
        default_libs = [
            ('requests', 'کتابخانه HTTP', 'network', 0, 0),
            ('aiohttp', 'HTTP غیرهمزمان', 'network', 0, 0),
            ('flask', 'وب فریمورک', 'web', 0, 0),
            ('fastapi', 'API فریمورک', 'web', 0, 0),
            ('sqlalchemy', 'ORM', 'database', 0, 0),
            ('redis', 'کلاینت Redis', 'database', 0, 0),
            ('motor', 'MongoDB غیرهمزمان', 'database', 0, 0),
            ('numpy', 'محاسبات عددی', 'science', 0, 0),
            ('pandas', 'تحلیل داده', 'science', 0, 0),
            ('pillow', 'پردازش تصویر', 'image', 0, 0),
            ('beautifulsoup4', 'پارسر HTML', 'web', 0, 0),
            ('selenium', 'اتوماسیون مرورگر', 'automation', 0, 0),
            ('jdatetime', 'تاریخ شمسی', 'utility', 0, 0),
            ('cryptography', 'رمزنگاری', 'security', 0, 0),
            ('loguru', 'لاگینگ', 'utility', 0, 0),
            ('tqdm', 'نوار پیشرفت', 'utility', 0, 0),
            ('asyncpg', 'PostgreSQL', 'database', 0, 0),
            ('telebot', 'Telegram Bot', 'bot', 0, 0),
            ('aiogram', 'Telegram Bot v3', 'bot', 0, 0),
            ('pydantic', 'Validation', 'utility', 0, 0),
        ]
        
        db.executemany('''
            INSERT OR IGNORE INTO system_libraries (name, description, category, is_premium, install_count)
            VALUES (?, ?, ?, ?, ?)
        ''', default_libs)
        
        result = db.execute("SELECT name, description, category, is_premium, install_count FROM system_libraries ORDER BY install_count DESC LIMIT 50")
        return [dict(r) for r in result] if result else []
    
    def install_library(self, user_id: int, lib_name: str, chat_id: int, msg_id: int) -> bool:
        """نصب کتابخانه برای کاربر"""
        with self.lock:
            if lib_name in self.installing_locks:
                return False
            self.installing_locks[lib_name] = True
        
        try:
            process = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', lib_name, '--quiet'],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if process.returncode == 0:
                # ثبت در دیتابیس
                db.execute('''
                    INSERT INTO user_libraries (user_id, library_name, version, installed_at, status)
                    VALUES (?, ?, ?, ?, 'installed')
                ''', (user_id, lib_name, 'latest', datetime.now().isoformat()))
                
                db.execute('''
                    UPDATE system_libraries SET install_count = install_count + 1 WHERE name = ?
                ''', (lib_name,))
                
                try:
                    temp_bot = telebot.TeleBot(BOT_TOKEN)
                    temp_bot.edit_message_text(f"✅ کتابخانه {lib_name} با موفقیت نصب شد!", chat_id, msg_id)
                except:
                    pass
                return True
            else:
                error = process.stderr[:200] if process.stderr else "خطا"
                try:
                    temp_bot = telebot.TeleBot(BOT_TOKEN)
                    temp_bot.edit_message_text(f"❌ خطا در نصب {lib_name}: {error}", chat_id, msg_id)
                except:
                    pass
                return False
        except subprocess.TimeoutExpired:
            try:
                temp_bot = telebot.TeleBot(BOT_TOKEN)
                temp_bot.edit_message_text(f"❌ زمان نصب کتابخانه {lib_name} تمام شد!", chat_id, msg_id)
            except:
                pass
            return False
        except Exception as e:
            try:
                temp_bot = telebot.TeleBot(BOT_TOKEN)
                temp_bot.edit_message_text(f"❌ خطا: {str(e)[:100]}", chat_id, msg_id)
            except:
                pass
            return False
        finally:
            with self.lock:
                if lib_name in self.installing_locks:
                    del self.installing_locks[lib_name]
    
    def get_user_libraries(self, user_id: int) -> list:
        result = db.execute('''
            SELECT library_name, version, installed_at, status 
            FROM user_libraries WHERE user_id = ? ORDER BY installed_at DESC
        ''', (user_id,))
        return [dict(r) for r in result] if result else []
    
    def uninstall_library(self, user_id: int, lib_name: str) -> bool:
        subprocess.run([sys.executable, '-m', 'pip', 'uninstall', lib_name, '-y', '--quiet'],
                      capture_output=True)
        db.execute('DELETE FROM user_libraries WHERE user_id = ? AND library_name = ?', (user_id, lib_name))
        return True

library_manager = LibraryManager()

# ==================== مدیریت ماشین با زمان انقضا ====================
class MachineManager:
    def __init__(self):
        self.port_counter = 8000
        self.processes = {}
        self.expiry_timers = {}
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=SETTINGS['worker_threads'])
    
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
    
    def run_bot_with_expiry(self, bot_id: str, code: str, token: str, expires_at: datetime) -> dict:
        """اجرای ربات با زمان انقضا"""
        try:
            machine_id = self.get_available_machine()
            if not machine_id:
                return {'success': False, 'error': 'همه ماشین‌ها پر هستند'}
            
            port = self.get_available_port()
            bot_dir = os.path.join(DIRS['MACHINES'], f"machine_{machine_id:03d}", bot_id)
            os.makedirs(bot_dir, exist_ok=True)
            
            code_path = os.path.join(bot_dir, 'bot.py')
            
            # افزودن کد مدیریت زمان انقضا
            expiry_check_code = f'''
# ========== سیستم مدیریت زمان انقضا ==========
import threading
import time
import sys

EXPIRY_TIME = "{expires_at.isoformat()}"
CHECK_INTERVAL = 10

def check_expiry():
    from datetime import datetime
    while True:
        try:
            expiry = datetime.fromisoformat(EXPIRY_TIME)
            if datetime.now() >= expiry:
                print("⏰ زمان انقضای ربات فرا رسید. در حال خروج...")
                sys.exit(0)
            time.sleep(CHECK_INTERVAL)
        except:
            time.sleep(CHECK_INTERVAL)

expiry_thread = threading.Thread(target=check_expiry, daemon=True)
expiry_thread.start()
# ===========================================
'''
            
            join_check_code = f'''
# ========== سیستم مدیریت عضوگیری ==========
import sqlite3, os
from functools import wraps

def check_join_enabled(func):
    @wraps(func)
    def wrapper(message, *args, **kwargs):
        try:
            conn = sqlite3.connect(os.path.join("{DIRS['DB']}", 'hyperscale_bot.db'), timeout=3)
            cursor = conn.cursor()
            cursor.execute("SELECT join_enabled, join_block_message FROM bots WHERE id = ?", ("{bot_id}",))
            result = cursor.fetchone()
            conn.close()
            if result and result[0] == 0:
                bot.reply_to(message, result[1] if result[1] else "🚫 سرور در حال حاضر پر است")
                return
        except:
            pass
        return func(message, *args, **kwargs)
    return wrapper
# ===========================================
'''
            
            with open(code_path, 'w', encoding='utf-8') as f:
                f.write(expiry_check_code + "\n" + join_check_code + "\n" + code)
            
            log_file = os.path.join(DIRS['LOGS'], f"bot_{bot_id}.log")
            
            process = subprocess.Popen(
                [sys.executable, code_path],
                stdout=open(log_file, 'a'),
                stderr=subprocess.STDOUT,
                cwd=bot_dir,
                start_new_session=True
            )
            
            time.sleep(1.5)
            
            if process.poll() is None:
                with self.lock:
                    self.processes[bot_id] = {
                        'process': process,
                        'pid': process.pid,
                        'machine_id': machine_id,
                        'port': port,
                        'dir': bot_dir,
                        'start_time': time.time(),
                        'expires_at': expires_at
                    }
                
                db.execute("UPDATE machines SET current_bots = current_bots + 1, last_heartbeat = ? WHERE id = ?",
                          (datetime.now().isoformat(), machine_id))
                
                return {'success': True, 'pid': process.pid, 'machine_id': machine_id}
            else:
                return {'success': False, 'error': 'خطا در اجرای ربات'}
        except Exception as e:
            return {'success': False, 'error': str(e)[:100]}
    
    def stop_bot(self, bot_id: str):
        with self.lock:
            if bot_id in self.processes:
                try:
                    info = self.processes[bot_id]
                    os.kill(info['pid'], signal.SIGTERM)
                    time.sleep(0.5)
                    if os.path.exists(info['dir']):
                        shutil.rmtree(info['dir'], ignore_errors=True)
                    db.execute("UPDATE machines SET current_bots = current_bots - 1 WHERE id = ?", (info['machine_id'],))
                    del self.processes[bot_id]
                    db.execute("UPDATE bots SET status = 'stopped', last_active = ? WHERE id = ?",
                              (datetime.now().isoformat(), bot_id))
                    return True
                except:
                    pass
        return False
    
    def get_status(self, bot_id: str):
        with self.lock:
            if bot_id in self.processes:
                info = self.processes[bot_id]
                try:
                    os.kill(info['pid'], 0)
                    remaining = max(0, (info['expires_at'] - datetime.now()).total_seconds())
                    return {
                        'running': True, 
                        'pid': info['pid'], 
                        'machine_id': info['machine_id'],
                        'uptime': time.time() - info['start_time'],
                        'remaining_seconds': int(remaining),
                        'expires_at': info['expires_at'].isoformat()
                    }
                except:
                    if bot_id in self.processes:
                        del self.processes[bot_id]
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

# ==================== مدیریت پیام‌های سیستم ====================
class MessageManager:
    def __init__(self):
        self.cache = {}
    
    def get_message(self, key: str, **kwargs) -> str:
        """دریافت پیام با قابلیت جایگزینی متغیرها"""
        cached = cache.get(f"msg_{key}")
        if cached:
            content = cached
        else:
            result = db.execute("SELECT content FROM system_messages WHERE key = ?", (key,))
            if result:
                content = result[0]['content']
                cache.set(f"msg_{key}", content, ttl=300)
            else:
                content = "پیام یافت نشد"
        
        try:
            return content.format(**kwargs)
        except:
            return content
    
    def update_message(self, key: str, title: str, content: str, admin_id: int):
        db.execute('''
            UPDATE system_messages SET title = ?, content = ?, updated_at = ?
            WHERE key = ?
        ''', (title, content, datetime.now().isoformat(), key))
        cache.delete(f"msg_{key}")
        logger.info(f"Message updated: {key} by {admin_id}")
    
    def get_all_messages(self) -> list:
        result = db.execute("SELECT key, title, content, updated_at FROM system_messages")
        return [dict(r) for r in result] if result else []

message_manager = MessageManager()

# ایجاد نمونه‌ها
machine_manager = MachineManager()
build_queue = None  # بعداً تعریف می‌شود

# ==================== ربات تلگرام ====================
bot = telebot.TeleBot(BOT_TOKEN)
bot.delete_webhook()

# ==================== توابع کمکی ====================

def get_setting(key):
    cached = cache.get(f"setting_{key}")
    if cached is not None:
        return cached
    result = db.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
    if result:
        val = result[0]['value']
        if key in ['subscription_price', 'withdraw_percent', 'min_withdraw', 
                   'max_builds_per_hour', 'max_concurrent_builds', 'rate_limit_per_second',
                   'health_check_interval', 'auto_scale_threshold', 'max_bots_per_user',
                   'bot_active_minutes', 'receipt_review_hours']:
            val = int(val)
        cache.set(f"setting_{key}", val, ttl=300)
        return val
    return SETTINGS.get(key)

def update_setting(key, value, admin_id=None):
    db.execute('''
        UPDATE system_settings SET value = ?, updated_at = ?, updated_by = ?
        WHERE key = ?
    ''', (str(value), datetime.now().isoformat(), admin_id, key))
    cache.delete(f"setting_{key}")
    logger.info(f"Setting updated: {key} = {value} by {admin_id}")

def generate_referral_code(user_id):
    return hashlib.md5(f"{user_id}_{time.time()}_{secrets.token_hex(4)}".encode()).hexdigest()[:12]

def get_user(user_id):
    cached = cache.get(f"user_{user_id}")
    if cached:
        return cached
    users = db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    if users:
        user = dict(users[0])
        cache.set(f"user_{user_id}", user, ttl=60)
        return user
    return None

def create_user(user_id, username, first_name, last_name, referred_by=None):
    now = datetime.now().isoformat()
    referral_code = generate_referral_code(user_id)
    
    db.execute('''
        INSERT OR IGNORE INTO users 
        (user_id, username, first_name, last_name, referral_code, referred_by, created_at, last_active, subscription_status, wallet_balance)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'inactive', 0)
    ''', (user_id, username, first_name, last_name, referral_code, referred_by, now, now))
    
    db.execute('UPDATE users SET last_active = ? WHERE user_id = ?', (now, user_id))
    
    if referred_by and referred_by != user_id:
        db.execute('UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = ?', (referred_by,))
        db.execute('UPDATE daily_stats SET new_users = new_users + 1 WHERE date = ?', (datetime.now().date().isoformat(),))
    
    cache.delete(f"user_{user_id}")
    return True

def check_subscription_and_limit(user_id):
    """بررسی اشتراک و محدودیت تعداد ربات‌ها"""
    user = get_user(user_id)
    if not user:
        return False, "کاربر یافت نشد"
    
    # بررسی اشتراک
    if user['subscription_status'] != 'active':
        expiry_check = user.get('subscription_expiry')
        if expiry_check:
            expiry = datetime.fromisoformat(expiry_check)
            if expiry > datetime.now():
                # فعال کردن مجدد
                db.execute('UPDATE users SET subscription_status = "active", warning_sent = 0 WHERE user_id = ?', (user_id,))
                cache.delete(f"user_{user_id}")
                user['subscription_status'] = 'active'
            else:
                return False, "اشتراک شما منقضی شده است"
        else:
            return False, "اشتراک فعال ندارید"
    
    # بررسی تعداد ربات‌های فعال
    active_bots = db.execute('SELECT COUNT(*) as count FROM bots WHERE user_id = ? AND status = "running"', (user_id,))
    active_count = active_bots[0]['count'] if active_bots else 0
    max_bots = get_setting('max_bots_per_user')
    
    if active_count >= max_bots:
        return False, f"شما حداکثر {max_bots} ربات فعال می‌توانید داشته باشید"
    
    return True, "ok"

def activate_subscription(user_id, months=1):
    user = get_user(user_id)
    now = datetime.now()
    if user and user['subscription_status'] == 'active' and user['subscription_expiry']:
        new_expiry = datetime.fromisoformat(user['subscription_expiry']) + timedelta(days=30*months)
    else:
        new_expiry = now + timedelta(days=30*months)
    
    db.execute('''
        UPDATE users 
        SET subscription_status = 'active', subscription_expiry = ?, warning_sent = 0 
        WHERE user_id = ?
    ''', (new_expiry.isoformat(), user_id))
    cache.delete(f"user_{user_id}")
    
    db.execute('UPDATE daily_stats SET new_subscriptions = new_subscriptions + 1, total_revenue = total_revenue + ? WHERE date = ?',
              (get_setting('subscription_price'), datetime.now().date().isoformat()))
    
    # ارسال پیام خوش‌آمدگویی با راهنمایی
    welcome_msg = message_manager.get_message(
        'subscription_active',
        name=user['first_name'] if user else 'کاربر گرامی',
        max_bots=get_setting('max_bots_per_user'),
        duration=get_setting('bot_active_minutes')
    )
    
    try:
        temp_bot = telebot.TeleBot(BOT_TOKEN)
        temp_bot.send_message(user_id, welcome_msg)
    except:
        pass

def add_wallet_balance(user_id, amount):
    user = get_user(user_id)
    new_balance = user['wallet_balance'] + amount
    db.execute('UPDATE users SET wallet_balance = ? WHERE user_id = ?', (new_balance, user_id))
    cache.delete(f"user_{user_id}")
    return new_balance

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

def is_channel_bot(token):
    try:
        resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            result = data.get('result', {})
            if not result.get('is_bot', False):
                return True, result.get('username', '')
            return False, result.get('username', '')
        return True, None
    except:
        return True, None

def log_error(error_type, message, user_id=None, bot_id=None, severity='normal'):
    error_id = hashlib.md5(f"{time.time()}_{user_id}_{bot_id}_{secrets.token_hex(4)}".encode()).hexdigest()[:16]
    db.execute('''
        INSERT INTO errors (id, type, message, user_id, bot_id, timestamp, resolved, severity)
        VALUES (?, ?, ?, ?, ?, ?, 0, ?)
    ''', (error_id, error_type, message[:500], user_id, bot_id, datetime.now().isoformat(), severity))
    
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    db.execute('DELETE FROM errors WHERE timestamp < ?', (week_ago,))

# ==================== Rate Limit Decorator ====================
def rate_limit(limit_per_second=10):
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

# ==================== منوی اصلی ====================
def get_main_menu(is_admin=False):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        types.KeyboardButton('🤖 ساخت ربات جدید'),
        types.KeyboardButton('📁 مدیریت پروژه'),
        types.KeyboardButton('📋 ربات‌های من'),
        types.KeyboardButton('🔄 فعال/غیرفعال'),
        types.KeyboardButton('🗑 حذف ربات'),
        types.KeyboardButton('💰 کیف پول و اشتراک'),
        types.KeyboardButton('📚 راهنما'),
        types.KeyboardButton('👥 دعوت دوستان'),
        types.KeyboardButton('💸 درخواست برداشت'),
        types.KeyboardButton('📦 کتابخانه'),
        types.KeyboardButton('📊 آمار'),
        types.KeyboardButton('📞 پشتیبانی'),
        types.KeyboardButton('⚡ وضعیت صف'),
        types.KeyboardButton('⏱️ زمان باقیمانده')
    ]
    if is_admin:
        buttons.extend([
            types.KeyboardButton('👑 پنل مدیریت'),
            types.KeyboardButton('📢 پیام همگانی'),
            types.KeyboardButton('✏️ ویرایش پیام‌ها')
        ])
    markup.add(*buttons)
    return markup

# ==================== دستورات ====================

@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or ""
    username = message.from_user.username or ""
    
    referred_by = None
    args = message.text.split()
    if len(args) > 1:
        code = args[1]
        users = db.execute('SELECT user_id FROM users WHERE referral_code = ?', (code,))
        if users and users[0]['user_id'] != user_id:
            referred_by = users[0]['user_id']
            try:
                bot.send_message(referred_by, f"🎉 {first_name} با لینک شما وارد شد!")
            except:
                pass
    
    create_user(user_id, username, first_name, message.from_user.last_name or "", referred_by)
    user = get_user(user_id)
    referral_link = f"https://t.me/{BOT_USERNAME}?start={user['referral_code']}"
    
    text = (f"🚀 خوش آمدید {first_name}!\n\n"
            f"👤 شناسه: `{user_id}`\n"
            f"🎁 کد معرف: `{user['referral_code']}`\n"
            f"🔗 لینک دعوت: `{referral_link}`\n"
            f"📊 دعوت‌ها: {user['referrals_count']}\n"
            f"💰 موجودی: {user['wallet_balance']:,} تومان\n"
            f"🤖 حداکثر ربات: {get_setting('max_bots_per_user')}\n"
            f"⏱️ زمان فعالسازی هر ربات: {get_setting('bot_active_minutes')} دقیقه")
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📋 کپی لینک", callback_data=f"copy_link_{user['referral_code']}"))
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=get_main_menu(user_id in ADMIN_IDS))

@bot.callback_query_handler(func=lambda call: call.data.startswith('copy_link_'))
def copy_link_callback(call):
    code = call.data.replace('copy_link_', '')
    link = f"https://t.me/{BOT_USERNAME}?start={code}"
    bot.answer_callback_query(call.id, f"✅ لینک کپی شد!\n{link}", show_alert=True)

# ==================== ساخت ربات جدید با پیام شفاف ====================
@bot.message_handler(func=lambda m: m.text == '🤖 ساخت ربات جدید')
@rate_limit(3)
def new_bot(message):
    user_id = message.from_user.id
    
    # بررسی اشتراک و محدودیت
    can_proceed, msg = check_subscription_and_limit(user_id)
    if not can_proceed:
        bot.send_message(message.chat.id, f"❌ {msg}")
        return
    
    # ارسال پیام شفاف برای ساخت ربات
    card = get_setting('card_number_display')
    bank = get_setting('card_bank')
    holder = get_setting('card_holder')
    price = get_setting('subscription_price_str')
    
    build_msg = message_manager.get_message(
        'build_start',
        price=price,
        bank=bank,
        card=card,
        holder=holder
    )
    
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("💳 مشاهده کارت", callback_data="show_card"),
        types.InlineKeyboardButton("📸 آپلود رسید", callback_data="upload_receipt")
    )
    
    bot.send_message(message.chat.id, build_msg, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "show_card")
def show_card(call):
    card = get_setting('card_number_display')
    bank = get_setting('card_bank')
    holder = get_setting('card_holder')
    
    text = f"🏦 {bank}\n💳 `{card}`\n👤 {holder}"
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "upload_receipt")
def upload_receipt_prompt(call):
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "📸 لطفاً تصویر رسید خود را ارسال کنید")

# ==================== مدیریت پروژه و پوشه ====================
@bot.message_handler(func=lambda m: m.text == '📁 مدیریت پروژه')
@rate_limit(3)
def manage_projects(message):
    user_id = message.from_user.id
    
    can_proceed, msg = check_subscription_and_limit(user_id)
    if not can_proceed:
        bot.send_message(message.chat.id, f"❌ {msg}")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📁 ساخت پوشه جدید", callback_data="project_create"),
        types.InlineKeyboardButton("📂 پروژه‌های من", callback_data="project_list"),
        types.InlineKeyboardButton("📤 آپلود فایل", callback_data="project_upload"),
        types.InlineKeyboardButton("▶️ اجرای پروژه", callback_data="project_run"),
        types.InlineKeyboardButton("🗑 حذف پروژه", callback_data="project_delete"),
        types.InlineKeyboardButton("📋 راهنمای ساختار", callback_data="project_guide")
    )
    
    bot.send_message(message.chat.id, "📁 **مدیریت پروژه‌ها**\n\nشما می‌توانید پروژه‌های چندفایلی خود را مدیریت کنید.", 
                    parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "project_guide")
def project_guide(call):
    guide = message_manager.get_message('folder_guide')
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, guide)

@bot.callback_query_handler(func=lambda call: call.data == "project_create")
def project_create_prompt(call):
    msg = bot.send_message(call.message.chat.id, "📁 **نام پوشه پروژه را وارد کنید:**\n\n(فقط حروف انگلیسی، اعداد و خط تیره)")
    bot.register_next_step_handler(msg, process_project_create)

def process_project_create(message):
    user_id = message.from_user.id
    folder_name = message.text.strip()
    
    if not re.match(r'^[\w\-_.]+$', folder_name):
        bot.reply_to(message, "❌ نام پوشه نامعتبر. فقط از حروف انگلیسی، اعداد، خط تیره و زیرخط استفاده کنید.")
        return
    
    result = project_manager.create_project_folder(user_id, folder_name)
    if result['success']:
        bot.reply_to(message, f"✅ پوشه `{folder_name}` با موفقیت ساخته شد!\n\nشما می‌توانید فایل‌های خود را در این پوشه آپلود کنید.", parse_mode='Markdown')
    else:
        bot.reply_to(message, f"❌ {result['error']}")

@bot.callback_query_handler(func=lambda call: call.data == "project_list")
def project_list(call):
    user_id = call.from_user.id
    projects = project_manager.get_user_projects(user_id)
    
    if not projects:
        bot.answer_callback_query(call.id, "📁 پروژه‌ای ندارید")
        bot.send_message(call.message.chat.id, "📁 پروژه‌ای ندارید. از گزینه «ساخت پوشه جدید» استفاده کنید.")
        return
    
    text = "📂 **پروژه‌های شما:**\n\n"
    for p in projects[:10]:
        text += f"📁 `{p['project_name']}`\n   🕐 ساخته شده: {p['created_at'][:16]}\n\n"
    
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "project_upload")
def project_upload_prompt(call):
    user_id = call.from_user.id
    projects = project_manager.get_user_projects(user_id)
    
    if not projects:
        bot.answer_callback_query(call.id, "📁 ابتدا یک پروژه بسازید")
        bot.send_message(call.message.chat.id, "📁 ابتدا یک پوشه پروژه بسازید.")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for p in projects[:10]:
        markup.add(types.InlineKeyboardButton(f"📂 {p['project_name']}", callback_data=f"upload_to_{p['project_name']}"))
    
    bot.edit_message_text("📁 **انتخاب پروژه برای آپلود:**", call.message.chat.id, call.message.message_id, 
                          reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('upload_to_'))
def upload_to_project(call):
    project_name = call.data.replace('upload_to_', '')
    bot.answer_callback_query(call.id)
    
    msg = bot.send_message(call.message.chat.id, f"📤 **فایل خود را برای پروژه `{project_name}` ارسال کنید.**\n\n(می‌توانید همزمان چند فایل ارسال کنید)\n\nبرای پایان آپلود /done را بزنید.")
    
    # ذخیره اطلاعات موقت
    cache.set(f"upload_session_{call.from_user.id}", {'project_name': project_name, 'files': []}, ttl=600)
    bot.register_next_step_handler(msg, handle_project_file_upload, project_name)

def handle_project_file_upload(message, project_name):
    user_id = message.from_user.id
    
    if message.text == '/done':
        session = cache.get(f"upload_session_{user_id}")
        if session and session.get('files'):
            bot.reply_to(message, f"✅ {len(session['files'])} فایل با موفقیت آپلود شد!")
        else:
            bot.reply_to(message, "📁 فایلی آپلود نشد.")
        cache.delete(f"upload_session_{user_id}")
        return
    
    if not message.document:
        bot.reply_to(message, "❌ لطفاً فایل ارسال کنید یا /done بزنید.")
        return
    
    file_name = message.document.file_name
    file_size = message.document.file_size
    
    max_size = get_setting('max_upload_size_mb') * 1024 * 1024
    if file_size > max_size:
        bot.reply_to(message, f"❌ حجم فایل بیشتر از {get_setting('max_upload_size_mb')} مگابایت است")
        return
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        result = project_manager.upload_file_to_project(user_id, project_name, file_name, downloaded)
        
        if result['success']:
            session = cache.get(f"upload_session_{user_id}")
            if session:
                session['files'].append(file_name)
                cache.set(f"upload_session_{user_id}", session, ttl=600)
            bot.reply_to(message, f"✅ فایل `{file_name}` آپلود شد.\n\nادامه دهید یا /done بزنید.", parse_mode='Markdown')
        else:
            bot.reply_to(message, f"❌ {result['error']}")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)[:100]}")
    
    bot.register_next_step_handler(message, handle_project_file_upload, project_name)

@bot.callback_query_handler(func=lambda call: call.data == "project_run")
def project_run_prompt(call):
    user_id = call.from_user.id
    
    can_proceed, msg = check_subscription_and_limit(user_id)
    if not can_proceed:
        bot.answer_callback_query(call.id, msg)
        bot.send_message(call.message.chat.id, f"❌ {msg}")
        return
    
    projects = project_manager.get_user_projects(user_id)
    if not projects:
        bot.answer_callback_query(call.id, "📁 پروژه‌ای ندارید")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for p in projects:
        markup.add(types.InlineKeyboardButton(f"▶️ {p['project_name']}", callback_data=f"run_project_{p['project_name']}"))
    
    bot.edit_message_text("▶️ **انتخاب پروژه برای اجرا:**\n\n(ربات به مدت ۵ دقیقه فعال خواهد ماند)", 
                         call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('run_project_'))
def run_project(call):
    project_name = call.data.replace('run_project_', '')
    user_id = call.from_user.id
    
    bot.answer_callback_query(call.id, "🔄 در حال اجرا...")
    
    # دریافت توکن از کاربر
    msg = bot.send_message(call.message.chat.id, f"🔑 **لطفاً توکن ربات خود را برای پروژه `{project_name}` وارد کنید:**\n\n(مطمئن شوید توکن داخل کد نیز وجود دارد)")
    bot.register_next_step_handler(msg, process_run_project_token, project_name)

def process_run_project_token(message, project_name):
    user_id = message.from_user.id
    token = message.text.strip()
    
    # بررسی توکن
    is_channel, username = is_channel_bot(token)
    if is_channel:
        bot.reply_to(message, "❌ این توکن متعلق به کانال است! از توکن ربات استفاده کنید.")
        return
    
    resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
    if resp.status_code != 200:
        bot.reply_to(message, "❌ توکن نامعتبر است!")
        return
    
    # اجرای پروژه
    result = project_manager.run_project(user_id, project_name, token)
    
    if result['success']:
        bot_info = resp.json()['result']
        expires_in = get_setting('bot_active_minutes')
        
        text = (f"✅ **ربات {bot_info.get('first_name', project_name)} با موفقیت اجرا شد!**\n\n"
                f"🤖 نام: @{bot_info.get('username', 'unknown')}\n"
                f"⏱️ زمان فعال بودن: {expires_in} دقیقه\n"
                f"📊 وضعیت: فعال\n\n"
                f"⚠️ توجه: ربات شما به طور خودکار پس از {expires_in} دقیقه متوقف می‌شود.")
        
        bot.reply_to(message, text)
    else:
        bot.reply_to(message, f"❌ خطا در اجرا: {result.get('error', 'مشخص نشده')}")

@bot.callback_query_handler(func=lambda call: call.data == "project_delete")
def project_delete_prompt(call):
    user_id = call.from_user.id
    projects = project_manager.get_user_projects(user_id)
    
    if not projects:
        bot.answer_callback_query(call.id, "📁 پروژه‌ای ندارید")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for p in projects:
        markup.add(types.InlineKeyboardButton(f"🗑 {p['project_name']}", callback_data=f"delete_project_{p['project_name']}"))
    
    bot.edit_message_text("🗑 **انتخاب پروژه برای حذف:**", call.message.chat.id, call.message.message_id, 
                          reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_project_'))
def delete_project(call):
    project_name = call.data.replace('delete_project_', '')
    user_id = call.from_user.id
    
    if project_manager.delete_project(user_id, project_name):
        bot.answer_callback_query(call.id, f"✅ پروژه {project_name} حذف شد")
        bot.edit_message_text(f"✅ پروژه `{project_name}` با موفقیت حذف شد.", 
                             call.message.chat.id, call.message.message_id, parse_mode='Markdown')
    else:
        bot.answer_callback_query(call.id, "❌ خطا در حذف")

# ==================== کتابخانه حرفه‌ای ====================
@bot.message_handler(func=lambda m: m.text == '📦 کتابخانه')
@rate_limit(3)
def library_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📚 کتابخانه‌های محبوب", callback_data="lib_popular"),
        types.InlineKeyboardButton("🔍 جستجوی کتابخانه", callback_data="lib_search"),
        types.InlineKeyboardButton("📋 کتابخانه‌های من", callback_data="lib_mine"),
        types.InlineKeyboardButton("🔧 نصب دستی", callback_data="lib_manual"),
        types.InlineKeyboardButton("🗑 حذف کتابخانه", callback_data="lib_uninstall"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="lib_back")
    )
    bot.reply_to(message, "📦 **مدیریت کتابخانه‌ها**\n\nکتابخانه‌های مورد نیاز خود را نصب کنید.", 
                parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "lib_popular")
def lib_popular(call):
    libs = library_manager.get_available_libraries()
    
    if not libs:
        bot.answer_callback_query(call.id, "کتابخانه‌ای یافت نشد")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for lib in libs[:30]:
        premium_mark = "⭐ " if lib.get('is_premium') else ""
        markup.add(types.InlineKeyboardButton(f"📦 {premium_mark}{lib['name']}", 
                                              callback_data=f"install_lib_{lib['name']}"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="lib_back"))
    
    bot.edit_message_text("📚 **کتابخانه‌های محبوب:**\n\nجهت نصب روی هر کتابخانه کلیک کنید.",
                         call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "lib_search")
def lib_search_prompt(call):
    msg = bot.send_message(call.message.chat.id, "🔍 **نام کتابخانه مورد نظر را وارد کنید:**")
    bot.register_next_step_handler(msg, process_lib_search)

def process_lib_search(message):
    search_term = message.text.strip()
    libs = library_manager.get_available_libraries(search_term)
    
    if not libs:
        bot.reply_to(message, "❌ کتابخانه‌ای یافت نشد")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for lib in libs[:20]:
        markup.add(types.InlineKeyboardButton(f"📦 {lib['name']}", callback_data=f"install_lib_{lib['name']}"))
    
    bot.reply_to(message, f"🔍 **نتایج جستجو برای «{search_term}»:**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "lib_mine")
def lib_mine(call):
    user_id = call.from_user.id
    libs = library_manager.get_user_libraries(user_id)
    
    if not libs:
        bot.answer_callback_query(call.id, "کتابخانه‌ای نصب نکرده‌اید")
        bot.send_message(call.message.chat.id, "📚 شما هنوز کتابخانه‌ای نصب نکرده‌اید.")
        return
    
    text = "📋 **کتابخانه‌های نصب شده شما:**\n\n"
    for lib in libs:
        text += f"📦 {lib['library_name']}\n   🕐 نصب: {lib['installed_at'][:16]}\n\n"
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('install_lib_'))
def install_library(call):
    lib_name = call.data.replace('install_lib_', '')
    user_id = call.from_user.id
    
    status_msg = bot.send_message(call.message.chat.id, f"🔄 در حال نصب {lib_name}...")
    
    success = library_manager.install_library(user_id, lib_name, call.message.chat.id, status_msg.message_id)
    
    if success:
        bot.answer_callback_query(call.id, f"✅ {lib_name} نصب شد")
    else:
        bot.answer_callback_query(call.id, f"❌ خطا در نصب {lib_name}")

@bot.callback_query_handler(func=lambda call: call.data == "lib_manual")
def lib_manual_prompt(call):
    msg = bot.send_message(call.message.chat.id, "🔧 **نام کتابخانه برای نصب دستی:**")
    bot.register_next_step_handler(msg, install_custom_library)

def install_custom_library(message):
    lib = message.text.strip()
    if not lib:
        bot.reply_to(message, "❌ نام کتابخانه را وارد کنید")
        return
    
    status_msg = bot.reply_to(message, f"🔄 در حال نصب {lib}...")
    success = library_manager.install_library(message.from_user.id, lib, message.chat.id, status_msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "lib_uninstall")
def lib_uninstall_prompt(call):
    user_id = call.from_user.id
    libs = library_manager.get_user_libraries(user_id)
    
    if not libs:
        bot.answer_callback_query(call.id, "کتابخانه‌ای برای حذف ندارید")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for lib in libs:
        markup.add(types.InlineKeyboardButton(f"🗑 {lib['library_name']}", callback_data=f"uninstall_lib_{lib['library_name']}"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="lib_back"))
    
    bot.edit_message_text("🗑 **انتخاب کتابخانه برای حذف:**", call.message.chat.id, call.message.message_id, 
                          reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('uninstall_lib_'))
def uninstall_library(call):
    lib_name = call.data.replace('uninstall_lib_', '')
    user_id = call.from_user.id
    
    if library_manager.uninstall_library(user_id, lib_name):
        bot.answer_callback_query(call.id, f"✅ {lib_name} حذف شد")
        bot.edit_message_text(f"✅ کتابخانه `{lib_name}` با موفقیت حذف شد.", 
                             call.message.chat.id, call.message.message_id, parse_mode='Markdown')
    else:
        bot.answer_callback_query(call.id, "❌ خطا در حذف")

@bot.callback_query_handler(func=lambda call: call.data == "lib_back")
def lib_back(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "🚀 منوی اصلی:", reply_markup=get_main_menu(call.from_user.id in ADMIN_IDS))

# ==================== زمان باقیمانده ربات‌ها ====================
@bot.message_handler(func=lambda m: m.text == '⏱️ زمان باقیمانده')
@rate_limit(5)
def remaining_time(message):
    user_id = message.from_user.id
    bots = db.execute('SELECT id, name, status FROM bots WHERE user_id = ?', (user_id,))
    
    if not bots:
        bot.send_message(message.chat.id, "⏱️ رباتی ندارید")
        return
    
    text = "⏱️ **زمان باقیمانده ربات‌ها:**\n\n"
    for b in bots:
        status = machine_manager.get_status(b['id'])
        if status.get('running'):
            remaining = status.get('remaining_seconds', 0)
            minutes = remaining // 60
            seconds = remaining % 60
            text += f"✅ {b['name']}: {minutes} دقیقه {seconds} ثانیه\n"
        else:
            text += f"❌ {b['name']}: متوقف\n"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== ربات‌های من با نمایش زمان ====================
@bot.message_handler(func=lambda m: m.text == '📋 ربات‌های من')
@rate_limit(5)
def my_bots(message):
    user_id = message.from_user.id
    bots = db.execute('SELECT * FROM bots WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    
    if not bots:
        bot.send_message(message.chat.id, "📋 رباتی ندارید")
        return
    
    for b in bots[:10]:
        status = machine_manager.get_status(b['id'])
        if status.get('running'):
            remaining = status.get('remaining_seconds', 0)
            minutes = remaining // 60
            emoji = "🟢"
            time_text = f"⏱️ {minutes} دقیقه"
        else:
            emoji = "🔴"
            time_text = "⏸️ متوقف"
        
        bot.send_message(message.chat.id, 
                        f"{emoji} **{b['name']}**\n"
                        f"🔗 t.me/{b['username']}\n"
                        f"{time_text}\n"
                        f"🆔 `{b['id']}`", parse_mode='Markdown')

# ==================== فیش‌ها ====================
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
        payment_code = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:8].upper()
        receipt_path = os.path.join(DIRS['RECEIPTS'], f"{user_id}_{payment_code}.jpg")
        
        with open(receipt_path, 'wb') as f:
            f.write(downloaded)
        
        db.execute('INSERT INTO receipts (user_id, amount, receipt_path, payment_code, created_at) VALUES (?, ?, ?, ?, ?)',
                  (user_id, get_setting('subscription_price'), receipt_path, payment_code, datetime.now().isoformat()))
        
        bot.reply_to(message, f"✅ فیش دریافت شد\n💰 {get_setting('subscription_price_str')}\n🆔 {payment_code}\n\n⏱️ بررسی تا ۲۴ ساعت")
        
        for admin_id in ADMIN_IDS:
            try:
                with open(receipt_path, 'rb') as f:
                    bot.send_photo(admin_id, f, caption=f"📸 فیش جدید\n👤 {message.from_user.first_name}\n🆔 {user_id}\n💰 {get_setting('subscription_price_str')}\n🆔 {payment_code}")
            except:
                pass
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")
        log_error("receipt_error", str(e), user_id)

# ==================== فعال/غیرفعال ====================
@bot.message_handler(func=lambda m: m.text == '🔄 فعال/غیرفعال')
@rate_limit(3)
def toggle_prompt(message):
    user_id = message.from_user.id
    bots = db.execute('SELECT id, name FROM bots WHERE user_id = ?', (user_id,))
    if not bots:
        bot.send_message(message.chat.id, "📋 رباتی ندارید")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        status = machine_manager.get_status(b['id'])
        emoji = "🟢" if status.get('running') else "🔴"
        markup.add(types.InlineKeyboardButton(f"{emoji} {b['name']}", callback_data=f"toggle_{b['id']}"))
    bot.send_message(message.chat.id, "🔄 انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_'))
def toggle_bot(call):
    bot_id = call.data.replace('toggle_', '')
    bot_rec = db.execute('SELECT * FROM bots WHERE id = ?', (bot_id,))
    if not bot_rec or bot_rec[0]['user_id'] != call.from_user.id:
        bot.answer_callback_query(call.id, "❌ یافت نشد")
        return
    
    bot_rec = dict(bot_rec[0])
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
            
            expires_at = datetime.now() + timedelta(minutes=get_setting('bot_active_minutes'))
            result = machine_manager.run_bot_with_expiry(bot_id, code, bot_rec['token'], expires_at)
            
            if result['success']:
                db.execute("UPDATE bots SET machine_id = ?, pid = ?, status = 'running', expires_at = ? WHERE id = ?",
                          (result['machine_id'], result['pid'], expires_at.isoformat(), bot_id))
                bot.answer_callback_query(call.id, "✅ فعال شد")
            else:
                bot.answer_callback_query(call.id, f"❌ {result.get('error', 'خطا')}")
        else:
            bot.answer_callback_query(call.id, "❌ فایل یافت نشد")

# ==================== حذف ربات ====================
@bot.message_handler(func=lambda m: m.text == '🗑 حذف ربات')
@rate_limit(3)
def delete_prompt(message):
    user_id = message.from_user.id
    bots = db.execute('SELECT id, name FROM bots WHERE user_id = ?', (user_id,))
    if not bots:
        bot.send_message(message.chat.id, "📋 رباتی ندارید")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        markup.add(types.InlineKeyboardButton(f"🗑 {b['name']}", callback_data=f"delete_{b['id']}"))
    bot.send_message(message.chat.id, "🗑 انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
def confirm_delete(call):
    bot_id = call.data.replace('delete_', '')
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ بله", callback_data=f"confirm_del_{bot_id}"), 
               types.InlineKeyboardButton("❌ انصراف", callback_data="cancel_del"))
    bot.edit_message_text("⚠️ اطمینان دارید؟", call.message.chat.id, call.message.message_id, reply_markup=markup)

def delete_bot(bot_id, user_id):
    bot_rec = db.execute('SELECT * FROM bots WHERE id = ?', (bot_id,))
    if not bot_rec or (user_id and bot_rec[0]['user_id'] != user_id):
        return False
    
    bot_rec = dict(bot_rec[0])
    machine_manager.stop_bot(bot_id)
    
    if bot_rec.get('file_path') and os.path.exists(bot_rec['file_path']):
        os.remove(bot_rec['file_path'])
    
    if bot_rec.get('folder_path') and os.path.exists(bot_rec['folder_path']):
        shutil.rmtree(bot_rec['folder_path'], ignore_errors=True)
    
    db.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
    if user_id:
        db.execute('UPDATE users SET bots_count = bots_count - 1 WHERE user_id = ?', (user_id,))
    
    cache.delete(f"user_{user_id}")
    return True

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

# ==================== کیف پول و اشتراک ====================
@bot.message_handler(func=lambda m: m.text == '💰 کیف پول و اشتراک')
@rate_limit(3)
def wallet(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        bot.send_message(message.chat.id, "❌ /start بزنید")
        return
    
    is_subscribed = user['subscription_status'] == 'active'
    if user.get('subscription_expiry'):
        expiry = datetime.fromisoformat(user['subscription_expiry']).strftime('%Y-%m-%d %H:%M')
    else:
        expiry = "ندارد"
    
    active_bots = db.execute('SELECT COUNT(*) as count FROM bots WHERE user_id = ? AND status = "running"', (user_id,))
    active_count = active_bots[0]['count'] if active_bots else 0
    max_bots = get_setting('max_bots_per_user')
    
    text = (f"💰 **کیف پول و اشتراک**\n\n"
            f"👤 {user['first_name']}\n"
            f"💳 وضعیت: {'✅ فعال' if is_subscribed else '❌ غیرفعال'}\n"
            f"📅 انقضا: {expiry}\n"
            f"💰 موجودی: {user['wallet_balance']:,} تومان\n"
            f"👥 دعوت‌ها: {user['referrals_count']}\n"
            f"🤖 ربات فعال: {active_count}/{max_bots}\n"
            f"⏱️ زمان هر ربات: {get_setting('bot_active_minutes')} دقیقه")
    
    if not is_subscribed:
        text += (f"\n\n💳 برای فعالسازی {get_setting('subscription_price_str')} را به کارت زیر واریز:\n"
                f"`{get_setting('card_number_display')}`\n"
                f"👤 {get_setting('card_holder')}\n"
                f"🏦 {get_setting('card_bank')}")
    
    markup = types.InlineKeyboardMarkup()
    if not is_subscribed:
        markup.add(types.InlineKeyboardButton("💳 مشاهده کارت", callback_data="show_card"),
                  types.InlineKeyboardButton("📸 آپلود رسید", callback_data="upload_receipt"))
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

# ==================== دعوت دوستان ====================
@bot.message_handler(func=lambda m: m.text == '👥 دعوت دوستان')
@rate_limit(3)
def invite(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    referral_link = f"https://t.me/{BOT_USERNAME}?start={user['referral_code']}"
    
    text = (f"👥 **سیستم دعوت دوستان**\n\n"
            f"🎁 کد معرف: `{user['referral_code']}`\n"
            f"🔗 لینک: `{referral_link}`\n"
            f"📊 دعوت‌ها: {user['referrals_count']}\n"
            f"💰 کمیسیون هر دعوت: {get_setting('withdraw_percent')}% از مبلغ اشتراک")
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📋 کپی لینک", callback_data=f"copy_link_{user['referral_code']}"))
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

# ==================== درخواست برداشت ====================
@bot.message_handler(func=lambda m: m.text == '💸 درخواست برداشت')
@rate_limit(2)
def withdraw_request(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if user['wallet_balance'] < get_setting('min_withdraw'):
        bot.send_message(message.chat.id, f"❌ موجودی {user['wallet_balance']:,} کمتر از حداقل {get_setting('min_withdraw'):,} است")
        return
    
    msg = bot.send_message(message.chat.id, "💳 شماره کارت مقصد (۱۶ رقم):")
    bot.register_next_step_handler(msg, process_withdraw_card, user)

def process_withdraw_card(message, user):
    card_number = message.text.strip()
    if not re.match(r'^\d{16}$', card_number):
        bot.reply_to(message, "❌ شماره کارت باید ۱۶ رقم باشد")
        return
    
    msg = bot.send_message(message.chat.id, "👤 نام صاحب کارت:")
    bot.register_next_step_handler(msg, process_withdraw_holder, user, card_number)

def process_withdraw_holder(message, user, card_number):
    card_holder = message.text.strip()
    db.execute('INSERT INTO withdraw_requests (user_id, amount, card_number, card_holder, created_at, status) VALUES (?, ?, ?, ?, ?, "pending")',
              (user['user_id'], user['wallet_balance'], card_number, card_holder, datetime.now().isoformat()))
    db.execute('UPDATE users SET wallet_balance = 0 WHERE user_id = ?', (user['user_id'],))
    cache.delete(f"user_{user['user_id']}")
    
    bot.send_message(message.chat.id, f"✅ درخواست برداشت {user['wallet_balance']:,} تومان ثبت شد")
    
    for admin_id in ADMIN_IDS:
        bot.send_message(admin_id, f"💰 درخواست برداشت جدید\n👤 {user['first_name']}\n🆔 {user['user_id']}\n💰 {user['wallet_balance']:,} تومان\n💳 {card_number}")

# ==================== وضعیت صف ====================
@bot.message_handler(func=lambda m: m.text == '⚡ وضعیت صف')
@rate_limit(5)
def queue_status(message):
    queue_len = build_queue.get_queue_length() if build_queue else 0
    max_concurrent = get_setting('max_concurrent_builds')
    
    text = (f"⚡ **وضعیت صف ساخت ربات**\n\n"
            f"📊 در صف: {queue_len}\n"
            f"⚙️ حداکثر همزمان: {max_concurrent}\n"
            f"📈 ساخت امروز شما: {rate_limiter.get_user_builds_today(message.from_user.id)}/{get_setting('max_builds_per_hour')}")
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== آمار ====================
@bot.message_handler(func=lambda m: m.text == '📊 آمار')
@rate_limit(3)
def stats(message):
    users = db.execute('SELECT COUNT(*) as count FROM users')[0]['count']
    active_subs = db.execute('SELECT COUNT(*) as count FROM users WHERE subscription_status = "active"')[0]['count']
    bots = db.execute('SELECT COUNT(*) as count FROM bots')[0]['count']
    running = db.execute('SELECT COUNT(*) as count FROM bots WHERE status = "running"')[0]['count']
    total_wallet = db.execute('SELECT SUM(wallet_balance) as total FROM users')[0]['total'] or 0
    machine_stats = machine_manager.get_stats()
    queue_len = build_queue.get_queue_length() if build_queue else 0
    
    text = (f"📊 **آمار سیستم HyperScale**\n\n"
            f"👥 کاربران: {users:,}\n"
            f"✅ اشتراک فعال: {active_subs:,}\n"
            f"🤖 کل ربات‌ها: {bots:,}\n"
            f"🟢 ربات فعال: {running:,}\n"
            f"💰 کیف پول کل: {total_wallet:,} تومان\n"
            f"🖥️ ظرفیت: {machine_stats['available']:,} خالی از {machine_stats['total_capacity']:,}\n"
            f"📊 مصرف: {machine_stats['usage_percent']:.1f}%\n"
            f"⚡ صف ساخت: {queue_len}\n"
            f"⏱️ زمان فعالسازی هر ربات: {get_setting('bot_active_minutes')} دقیقه\n"
            f"🤖 حداکثر ربات هر کاربر: {get_setting('max_bots_per_user')}")
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== راهنما ====================
@bot.message_handler(func=lambda m: m.text == '📚 راهنما')
@rate_limit(3)
def guide(message):
    guide_text = get_setting('guide_text')
    bot.send_message(message.chat.id, guide_text)

# ==================== پشتیبانی ====================
@bot.message_handler(func=lambda m: m.text == '📞 پشتیبانی')
@rate_limit(3)
def support(message):
    bot.send_message(message.chat.id, "📞 **پشتیبانی:**\n\n@shahraghee13\n\nسوالات خود را مطرح کنید.")

# ==================== آپلود فایل (تک فایل) ====================
@bot.message_handler(content_types=['document'])
def handle_build_file(message):
    user_id = message.from_user.id
    
    can_proceed, msg = check_subscription_and_limit(user_id)
    if not can_proceed:
        bot.reply_to(message, f"❌ {msg}")
        return
    
    file_name = message.document.file_name
    if not (file_name.endswith('.py') or file_name.endswith('.zip')):
        bot.reply_to(message, "❌ فقط فایل‌های .py یا .zip پشتیبانی می‌شوند")
        return
    
    if message.document.file_size > 50 * 1024 * 1024:
        bot.reply_to(message, "❌ حجم فایل بیشتر از ۵۰ مگابایت است")
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
            bot.edit_message_text("❌ فایل پایتون معتبری پیدا نشد", message.chat.id, status_msg.message_id)
            return
        
        token = extract_token_from_code(main_code)
        if not token:
            bot.edit_message_text("❌ توکن ربات در کد پیدا نشد!\n\nلطفاً مطمئن شوید توکن به صورت token = 'YOUR_TOKEN' در کد وجود دارد.", 
                                message.chat.id, status_msg.message_id)
            return
        
        is_channel, _ = is_channel_bot(token)
        if is_channel:
            bot.edit_message_text("❌ این توکن متعلق به کانال است! از توکن ربات استفاده کنید.", 
                                message.chat.id, status_msg.message_id)
            return
        
        resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        if resp.status_code != 200:
            bot.edit_message_text("❌ توکن نامعتبر است!", message.chat.id, status_msg.message_id)
            return
        
        bot_info = resp.json()['result']
        
        rate_limiter.increment_user_builds(user_id)
        
        bot_id = hashlib.md5(f"{user_id}{token}{time.time()}".encode()).hexdigest()[:16]
        expires_at = datetime.now() + timedelta(minutes=get_setting('bot_active_minutes'))
        
        bot.edit_message_text(f"🔄 در حال ساخت ربات...\n⏱️ زمان فعالسازی: {get_setting('bot_active_minutes')} دقیقه", 
                            message.chat.id, status_msg.message_id)
        
        # اجرای مستقیم ربات
        result = machine_manager.run_bot_with_expiry(bot_id, main_code, token, expires_at)
        
        if result['success']:
            db.execute('''
                INSERT INTO bots (id, user_id, token, name, username, file_path, pid, machine_id, 
                                 status, created_at, expires_at, project_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'running', ?, ?, 'single_file')
            ''', (bot_id, user_id, token, bot_info.get('first_name', 'ربات'), 
                  bot_info.get('username', ''), file_path, result['pid'], result['machine_id'],
                  datetime.now().isoformat(), expires_at.isoformat()))
            
            db.execute('UPDATE users SET bots_count = bots_count + 1, total_builds = total_builds + 1, last_build_at = ? WHERE user_id = ?',
                      (datetime.now().isoformat(), user_id))
            
            # کمیسیون برای معرف
            user = get_user(user_id)
            if user and user.get('referred_by'):
                commission = int(get_setting('subscription_price') * get_setting('withdraw_percent') / 100)
                add_wallet_balance(user['referred_by'], commission)
                try:
                    bot.send_message(user['referred_by'], f"🎉 کمیسیون {commission:,} تومان از ساخت ربات توسط دعوت‌شده شما به کیف پول اضافه شد")
                except:
                    pass
            
            bot.edit_message_text(
                f"✅ **ربات {bot_info.get('first_name', 'شما')} با موفقیت ساخته شد!**\n\n"
                f"🤖 نام: @{bot_info.get('username', 'unknown')}\n"
                f"⏱️ زمان فعال بودن: {get_setting('bot_active_minutes')} دقیقه\n"
                f"📊 وضعیت: فعال\n\n"
                f"⚠️ توجه: ربات شما به طور خودکار پس از {get_setting('bot_active_minutes')} دقیقه متوقف می‌شود.\n"
                f"برای تمدید، از بخش ربات‌های من گزینه فعال را بزنید.", 
                message.chat.id, status_msg.message_id, parse_mode='Markdown')
        else:
            bot.edit_message_text(f"❌ خطا در ساخت ربات: {result.get('error', 'مشخص نشده')}", 
                                message.chat.id, status_msg.message_id)
        
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)[:200]}", message.chat.id, status_msg.message_id)
        log_error("build_error", str(e), user_id, severity='high')

# ==================== پنل مدیریت پیشرفته ====================
@bot.message_handler(func=lambda m: m.text == '👑 پنل مدیریت')
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📸 تایید فیش", callback_data="admin_receipts"),
        types.InlineKeyboardButton("💰 تایید برداشت", callback_data="admin_withdraws"),
        types.InlineKeyboardButton("👥 مدیریت کاربران", callback_data="admin_users"),
        types.InlineKeyboardButton("🤖 مدیریت ربات‌ها", callback_data="admin_bots"),
        types.InlineKeyboardButton("⏹ توقف عضوگیری", callback_data="admin_stop_bot_join"),
        types.InlineKeyboardButton("⚙️ تنظیمات سیستم", callback_data="admin_settings"),
        types.InlineKeyboardButton("🔧 خطاها", callback_data="admin_errors"),
        types.InlineKeyboardButton("📊 گزارش کامل", callback_data="admin_report"),
        types.InlineKeyboardButton("🖥️ مدیریت ماشین", callback_data="admin_machines"),
        types.InlineKeyboardButton("⚡ تنظیمات مقیاس", callback_data="admin_scale_settings"),
        types.InlineKeyboardButton("✏️ ویرایش پیام‌ها", callback_data="admin_edit_messages"),
        types.InlineKeyboardButton("📈 آمار پیشرفته", callback_data="admin_advanced_stats"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    bot.send_message(message.chat.id, "👑 **پنل مدیریت HyperScale**", parse_mode='Markdown', reply_markup=markup)

# ==================== ویرایش پیام‌های سیستم ====================
@bot.callback_query_handler(func=lambda call: call.data == "admin_edit_messages")
def admin_edit_messages(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    messages = message_manager.get_all_messages()
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for msg in messages:
        markup.add(types.InlineKeyboardButton(f"✏️ {msg['title']}", callback_data=f"edit_msg_{msg['key']}"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back"))
    
    bot.edit_message_text("✏️ **انتخاب پیام برای ویرایش:**", 
                         call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('edit_msg_'))
def edit_message_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg_key = call.data.replace('edit_msg_', '')
    current = db.execute("SELECT title, content FROM system_messages WHERE key = ?", (msg_key,))
    
    if current:
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, 
                        f"✏️ **ویرایش پیام: {current[0]['title']}**\n\n"
                        f"متن فعلی:\n{current[0]['content']}\n\n"
                        f"متن جدید را ارسال کنید:")
        bot.register_next_step_handler(call.message, process_edit_message, msg_key)
    else:
        bot.answer_callback_query(call.id, "پیام یافت نشد")

def process_edit_message(message, msg_key):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    new_content = message.text.strip()
    db.execute('UPDATE system_messages SET content = ?, updated_at = ? WHERE key = ?',
              (new_content, datetime.now().isoformat(), msg_key))
    cache.delete(f"msg_{msg_key}")
    
    bot.reply_to(message, f"✅ پیام با موفقیت به‌روزرسانی شد!")

# ==================== آمار پیشرفته ====================
@bot.callback_query_handler(func=lambda call: call.data == "admin_advanced_stats")
def admin_advanced_stats(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    # آمار ۷ روز اخیر
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    new_users_week = db.execute("SELECT COUNT(*) as count FROM users WHERE created_at > ?", (week_ago,))
    new_bots_week = db.execute("SELECT COUNT(*) as count FROM bots WHERE created_at > ?", (week_ago,))
    revenue_week = db.execute("SELECT SUM(total_revenue) as total FROM daily_stats WHERE date > ?", 
                              (datetime.now().date() - timedelta(days=7)).isoformat())
    
    # کتابخانه‌های پرنصب
    top_libs = db.execute("SELECT name, install_count FROM system_libraries ORDER BY install_count DESC LIMIT 5")
    
    # خطاهای اخیر
    recent_errors = db.execute("SELECT COUNT(*) as count FROM errors WHERE timestamp > ? AND resolved = 0", (week_ago,))
    
    text = (f"📈 **آمار پیشرفته HyperScale**\n\n"
            f"📊 آمار هفته اخیر:\n"
            f"👥 کاربران جدید: {new_users_week[0]['count'] if new_users_week else 0}\n"
            f"🤖 ربات‌های جدید: {new_bots_week[0]['count'] if new_bots_week else 0}\n"
            f"💰 درآمد هفته: {revenue_week[0]['total'] if revenue_week and revenue_week[0]['total'] else 0:,} تومان\n\n"
            f"📚 کتابخانه‌های پرنصب:\n")
    
    if top_libs:
        for lib in top_libs:
            text += f"📦 {lib['name']}: {lib['install_count']} نصب\n"
    else:
        text += "هنوز نصب نشده\n"
    
    text += f"\n⚠️ خطاهای باز: {recent_errors[0]['count'] if recent_errors else 0}"
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id)

# ==================== تنظیمات سیستم پیشرفته ====================
@bot.callback_query_handler(func=lambda call: call.data == "admin_settings")
def admin_settings(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💳 کارت بانکی", callback_data="admin_set_card"),
        types.InlineKeyboardButton("💰 قیمت اشتراک", callback_data="admin_set_price"),
        types.InlineKeyboardButton("📝 متن راهنما", callback_data="admin_set_guide"),
        types.InlineKeyboardButton("📈 محدودیت ساخت", callback_data="admin_set_build_limit"),
        types.InlineKeyboardButton("🤖 حداکثر ربات کاربر", callback_data="admin_set_max_bots"),
        types.InlineKeyboardButton("⏱️ زمان فعالسازی", callback_data="admin_set_bot_duration"),
        types.InlineKeyboardButton("📁 حجم آپلود", callback_data="admin_set_upload_size"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    bot.edit_message_text("⚙️ **تنظیمات سیستم HyperScale**", 
                         call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_max_bots")
def admin_set_max_bots(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "🤖 **حداکثر تعداد ربات برای هر کاربر (مثال: 3):**")
    bot.register_next_step_handler(msg, process_set_max_bots)

def process_set_max_bots(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        max_bots = int(message.text.strip())
        if 1 <= max_bots <= 50:
            update_setting('max_bots_per_user', max_bots, message.from_user.id)
            bot.reply_to(message, f"✅ حداکثر ربات هر کاربر به {max_bots} تغییر کرد")
        else:
            bot.reply_to(message, "❌ عدد بین 1 تا 50")
    except:
        bot.reply_to(message, "❌ عدد معتبر وارد کنید")

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_bot_duration")
def admin_set_bot_duration(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "⏱️ **زمان فعالسازی هر ربات به دقیقه (مثال: 5):**")
    bot.register_next_step_handler(msg, process_set_bot_duration)

def process_set_bot_duration(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        duration = int(message.text.strip())
        if 1 <= duration <= 60:
            update_setting('bot_active_minutes', duration, message.from_user.id)
            bot.reply_to(message, f"✅ زمان فعالسازی هر ربات به {duration} دقیقه تغییر کرد")
        else:
            bot.reply_to(message, "❌ عدد بین 1 تا 60")
    except:
        bot.reply_to(message, "❌ عدد معتبر وارد کنید")

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_upload_size")
def admin_set_upload_size(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "📁 **حداکثر حجم آپلود به مگابایت (مثال: 100):**")
    bot.register_next_step_handler(msg, process_set_upload_size)

def process_set_upload_size(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        size = int(message.text.strip())
        if 10 <= size <= 500:
            update_setting('max_upload_size_mb', size, message.from_user.id)
            bot.reply_to(message, f"✅ حداکثر حجم آپلود به {size} مگابایت تغییر کرد")
        else:
            bot.reply_to(message, "❌ عدد بین 10 تا 500")
    except:
        bot.reply_to(message, "❌ عدد معتبر وارد کنید")

# ==================== سایر کال‌بک‌های مدیریت ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_receipts")
def admin_receipts(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    receipts = db.execute('SELECT * FROM receipts WHERE status = "pending" ORDER BY created_at')
    if not receipts:
        bot.send_message(call.message.chat.id, "📸 فیشی وجود ندارد")
        return
    for r in receipts:
        user = get_user(r['user_id'])
        text = f"📸 فیش جدید\n👤 {user['first_name'] if user else 'نامشخص'}\n🆔 {user['user_id'] if user else r['user_id']}\n💰 {r['amount']:,} تومان\n🆔 {r['payment_code']}"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_receipt_{r['id']}"),
                  types.InlineKeyboardButton("❌ رد", callback_data=f"reject_receipt_{r['id']}"))
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
    r = db.execute('SELECT user_id FROM receipts WHERE id = ?', (rid,))
    if r:
        db.execute('UPDATE receipts SET status = "approved", reviewed_by = ?, reviewed_at = ? WHERE id = ?',
                  (call.from_user.id, datetime.now().isoformat(), rid))
        activate_subscription(r[0]['user_id'])
        bot.answer_callback_query(call.id, "✅ اشتراک کاربر فعال شد")
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

@bot.callback_query_handler(func=lambda call: call.data == "admin_withdraws")
def admin_withdraws(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    withdraws = db.execute('SELECT * FROM withdraw_requests WHERE status = "pending" ORDER BY created_at')
    if not withdraws:
        bot.send_message(call.message.chat.id, "💰 درخواست برداشتی وجود ندارد")
        return
    for w in withdraws:
        user = get_user(w['user_id'])
        text = f"💰 درخواست برداشت\n👤 {user['first_name'] if user else 'نامشخص'}\n🆔 {w['user_id']}\n💰 {w['amount']:,} تومان\n💳 {w['card_number']}\n👤 {w['card_holder']}"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_withdraw_{w['id']}"))
        bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_withdraw_'))
def approve_withdraw(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    wid = int(call.data.replace('approve_withdraw_', ''))
    db.execute('UPDATE withdraw_requests SET status = "approved", processed_at = ? WHERE id = ?',
              (datetime.now().isoformat(), wid))
    bot.answer_callback_query(call.id, "✅ برداشت تایید شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_users")
def admin_users(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔍 جستجوی کاربر", callback_data="admin_search_user"),
        types.InlineKeyboardButton("🗑 حذف کاربر", callback_data="admin_delete_user"),
        types.InlineKeyboardButton("💰 افزایش موجودی", callback_data="admin_add_balance"),
        types.InlineKeyboardButton("🎁 فعالسازی اشتراک", callback_data="admin_activate_sub"),
        types.InlineKeyboardButton("📋 لیست کاربران", callback_data="admin_list_users"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    bot.edit_message_text("👥 **مدیریت کاربران**", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_list_users")
def admin_list_users(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    users = db.execute('SELECT user_id, first_name, subscription_status, wallet_balance FROM users ORDER BY created_at DESC LIMIT 50')
    if not users:
        bot.send_message(call.message.chat.id, "👥 کاربری وجود ندارد")
        return
    
    text = "📋 **لیست کاربران اخیر:**\n\n"
    for u in users:
        text += f"👤 {u['first_name']} - {u['user_id']}\n   💳 {u['subscription_status']} - 💰 {u['wallet_balance']:,}\n\n"
    
    bot.send_message(call.message.chat.id, text)

@bot.callback_query_handler(func=lambda call: call.data == "admin_search_user")
def admin_search_user(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "🔍 **آیدی کاربر را وارد کنید:**")
    bot.register_next_step_handler(msg, process_admin_search)

def process_admin_search(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        uid = int(message.text.strip())
        user = get_user(uid)
        if user:
            bots = db.execute('SELECT COUNT(*) as count FROM bots WHERE user_id = ?', (uid,))
            active_bots = db.execute('SELECT COUNT(*) as count FROM bots WHERE user_id = ? AND status = "running"', (uid,))
            text = (f"👤 {user['first_name']}\n"
                   f"🆔 {user['user_id']}\n"
                   f"💰 موجودی: {user['wallet_balance']:,} تومان\n"
                   f"✅ اشتراک: {user['subscription_status']}\n"
                   f"📅 انقضا: {user.get('subscription_expiry', 'ندارد')[:16] if user.get('subscription_expiry') else 'ندارد'}\n"
                   f"🤖 کل ربات: {bots[0]['count']}\n"
                   f"🟢 ربات فعال: {active_bots[0]['count']}\n"
                   f"👥 دعوت‌ها: {user['referrals_count']}\n"
                   f"📊 ساخت امروز: {rate_limiter.get_user_builds_today(uid)}")
            bot.reply_to(message, text)
        else:
            bot.reply_to(message, "❌ کاربر یافت نشد")
    except:
        bot.reply_to(message, "❌ آیدی نامعتبر")

@bot.callback_query_handler(func=lambda call: call.data == "admin_delete_user")
def admin_delete_user(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "🗑 **آیدی کاربر برای حذف:**")
    bot.register_next_step_handler(msg, process_admin_delete)

def process_admin_delete(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        uid = int(message.text.strip())
        # توقف تمام ربات‌های کاربر
        for bot_rec in db.execute('SELECT id FROM bots WHERE user_id = ?', (uid,)):
            machine_manager.stop_bot(bot_rec['id'])
        db.execute('DELETE FROM users WHERE user_id = ?', (uid,))
        cache.delete(f"user_{uid}")
        bot.reply_to(message, f"✅ کاربر {uid} و تمام ربات‌هایش حذف شد")
    except:
        bot.reply_to(message, "❌ خطا در حذف")

@bot.callback_query_handler(func=lambda call: call.data == "admin_add_balance")
def admin_add_balance(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "💰 **آیدی و مبلغ (مثال: 123456 100000):**")
    bot.register_next_step_handler(msg, process_add_balance)

def process_add_balance(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        parts = message.text.strip().split()
        uid = int(parts[0])
        amount = int(parts[1])
        add_wallet_balance(uid, amount)
        bot.reply_to(message, f"✅ {amount:,} تومان به کیف پول کاربر {uid} اضافه شد")
        try:
            bot.send_message(uid, f"💰 {amount:,} تومان به کیف پول شما اضافه شد")
        except:
            pass
    except:
        bot.reply_to(message, "❌ فرمت نامعتبر. مثال: 123456 100000")

@bot.callback_query_handler(func=lambda call: call.data == "admin_activate_sub")
def admin_activate_sub(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "🎁 **آیدی کاربر برای فعالسازی اشتراک:**")
    bot.register_next_step_handler(msg, process_activate_sub)

def process_activate_sub(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        uid = int(message.text.strip())
        activate_subscription(uid)
        bot.reply_to(message, f"✅ اشتراک کاربر {uid} فعال شد")
        try:
            bot.send_message(uid, f"🎁 اشتراک شما توسط ادمین فعال شد!")
        except:
            pass
    except:
        bot.reply_to(message, "❌ خطا")

@bot.callback_query_handler(func=lambda call: call.data == "admin_bots")
def admin_bots(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📋 لیست ربات‌ها", callback_data="admin_list_bots"),
        types.InlineKeyboardButton("🗑 حذف ربات", callback_data="admin_delete_bot"),
        types.InlineKeyboardButton("🔄 ریستارت ربات", callback_data="admin_fix_bot"),
        types.InlineKeyboardButton("⏱️ بررسی ربات‌های منقضی", callback_data="admin_check_expired"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    bot.edit_message_text("🤖 **مدیریت ربات‌ها**", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_check_expired")
def admin_check_expired(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    expired_bots = db.execute("SELECT id, name, user_id, expires_at FROM bots WHERE expires_at < datetime('now') AND status = 'running'")
    count = 0
    for bot_rec in expired_bots:
        machine_manager.stop_bot(bot_rec['id'])
        db.execute("UPDATE bots SET status = 'expired' WHERE id = ?", (bot_rec['id'],))
        count += 1
    
    bot.answer_callback_query(call.id, f"✅ {count} ربات منقضی متوقف شد")
    bot.send_message(call.message.chat.id, f"✅ {count} ربات که زمان آنها منقضی شده بود متوقف شدند.")

@bot.callback_query_handler(func=lambda call: call.data == "admin_list_bots")
def admin_list_bots(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    bots = db.execute('SELECT id, name, user_id, status, expires_at FROM bots ORDER BY created_at DESC LIMIT 50')
    if not bots:
        bot.send_message(call.message.chat.id, "📋 رباتی وجود ندارد")
        return
    
    text = "🤖 **لیست ربات‌های اخیر:**\n\n"
    for b in bots:
        status_emoji = "🟢" if b['status'] == 'running' else ("⏰" if b['status'] == 'expired' else "🔴")
        expires = b['expires_at'][:16] if b['expires_at'] else "ندارد"
        text += f"{status_emoji} {b['name']}\n   👤 {b['user_id']}\n   ⏱️ انقضا: {expires}\n   🆔 `{b['id']}`\n\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "admin_delete_bot")
def admin_delete_bot(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "🗑 **آیدی ربات برای حذف:**")
    bot.register_next_step_handler(msg, process_admin_delete_bot)

def process_admin_delete_bot(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    bot_id = message.text.strip()
    if delete_bot(bot_id, None):
        bot.reply_to(message, f"✅ ربات {bot_id} حذف شد")
    else:
        bot.reply_to(message, "❌ ربات یافت نشد")

@bot.callback_query_handler(func=lambda call: call.data == "admin_fix_bot")
def admin_fix_bot(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "🔧 **آیدی ربات برای ریستارت:**")
    bot.register_next_step_handler(msg, process_fix_bot)

def process_fix_bot(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    bot_id = message.text.strip()
    bot_rec = db.execute('SELECT * FROM bots WHERE id = ?', (bot_id,))
    if not bot_rec:
        bot.reply_to(message, "❌ ربات یافت نشد")
        return
    
    bot_rec = dict(bot_rec[0])
    machine_manager.stop_bot(bot_id)
    time.sleep(1)
    
    if bot_rec.get('file_path') and os.path.exists(bot_rec['file_path']):
        with open(bot_rec['file_path'], 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()
        
        expires_at = datetime.now() + timedelta(minutes=get_setting('bot_active_minutes'))
        result = machine_manager.run_bot_with_expiry(bot_id, code, bot_rec['token'], expires_at)
        
        if result['success']:
            db.execute("UPDATE bots SET machine_id = ?, pid = ?, status = 'running', expires_at = ? WHERE id = ?",
                      (result['machine_id'], result['pid'], expires_at.isoformat(), bot_id))
            bot.reply_to(message, f"✅ ربات {bot_id} ریستارت شد و {get_setting('bot_active_minutes')} دقیقه فعال است")
        else:
            bot.reply_to(message, f"❌ {result.get('error', 'خطا')}")
    else:
        bot.reply_to(message, "❌ فایل ربات یافت نشد")

@bot.callback_query_handler(func=lambda call: call.data == "admin_stop_bot_join")
def admin_stop_bot_join(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    bots = db.execute('SELECT id, name, username, join_enabled FROM bots WHERE status = "running"')
    if not bots:
        bot.send_message(call.message.chat.id, "❌ ربات فعالی وجود ندارد")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        status_emoji = "🟢" if b['join_enabled'] == 1 else "🔴"
        markup.add(types.InlineKeyboardButton(f"{status_emoji} {b['name']}", callback_data=f"toggle_join_{b['id']}"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back"))
    bot.edit_message_text("⏹ **توقف/فعالسازی عضوگیری ربات‌ها**", 
                         call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_join_'))
def toggle_join_admin(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    bot_id = call.data.replace('toggle_join_', '')
    current = db.execute('SELECT join_enabled, name FROM bots WHERE id = ?', (bot_id,))
    if not current:
        bot.answer_callback_query(call.id, "❌ یافت نشد")
        return
    is_enabled = current[0]['join_enabled']
    bot_name = current[0]['name']
    
    if is_enabled == 1:
        msg = bot.send_message(call.message.chat.id, f"📝 **پیام مسدودیت برای {bot_name}:**\n(پیامی که کاربران هنگام بسته بودن عضوگیری می‌بینند)")
        bot.register_next_step_handler(msg, lambda m: save_block_message_admin(m, bot_id, call))
        bot.answer_callback_query(call.id)
    else:
        db.execute('UPDATE bots SET join_enabled = 1 WHERE id = ?', (bot_id,))
        bot.answer_callback_query(call.id, f"✅ عضوگیری {bot_name} فعال شد")
        bot.send_message(call.message.chat.id, f"✅ عضوگیری ربات {bot_name} فعال شد")

def save_block_message_admin(message, bot_id, original_call):
    if message.from_user.id not in ADMIN_IDS:
        return
    block_text = message.text.strip() or "🚫 سرور در حال حاضر پر است. لطفاً بعداً تلاش کنید."
    bot_info = db.execute('SELECT name FROM bots WHERE id = ?', (bot_id,))
    bot_name = bot_info[0]['name'] if bot_info else "ربات"
    db.execute('UPDATE bots SET join_enabled = 0, join_block_message = ? WHERE id = ?', (block_text, bot_id))
    bot.send_message(message.chat.id, f"✅ عضوگیری ربات {bot_name} متوقف شد\n📨 پیام نمایش داده شده: {block_text}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_errors")
def admin_errors(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    errors = db.execute('SELECT * FROM errors WHERE resolved = 0 ORDER BY timestamp DESC LIMIT 30')
    if not errors:
        bot.send_message(call.message.chat.id, "✅ خطایی وجود ندارد")
        return
    
    for e in errors:
        severity_emoji = "🔴" if e['severity'] == 'high' else "🟡" if e['severity'] == 'normal' else "🟢"
        text = f"{severity_emoji} **{e['type']}**\n📝 {e['message'][:150]}\n🕐 {e['timestamp'][:16]}\n👤 کاربر: {e['user_id'] or 'نامشخص'}"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ علامت رفع شد", callback_data=f"resolve_error_{e['id']}"))
        bot.send_message(call.message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('resolve_error_'))
def resolve_error_admin(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    eid = call.data.replace('resolve_error_', '')
    db.execute('UPDATE errors SET resolved = 1 WHERE id = ?', (eid,))
    bot.answer_callback_query(call.id, "✅ خطا به عنوان رفع شده علامت خورد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_report")
def admin_report(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    users = db.execute('SELECT COUNT(*) as count FROM users')[0]['count']
    active = db.execute('SELECT COUNT(*) as count FROM users WHERE subscription_status = "active"')[0]['count']
    bots = db.execute('SELECT COUNT(*) as count FROM bots')[0]['count']
    running = db.execute('SELECT COUNT(*) as count FROM bots WHERE status = "running"')[0]['count']
    expired = db.execute('SELECT COUNT(*) as count FROM bots WHERE status = "expired"')[0]['count']
    total_wallet = db.execute('SELECT SUM(wallet_balance) as total FROM users')[0]['total'] or 0
    machine_stats = machine_manager.get_stats()
    
    today = datetime.now().date().isoformat()
    daily = db.execute('SELECT * FROM daily_stats WHERE date = ?', (today,))
    if daily:
        d = daily[0]
        daily_text = f"\n📅 امروز:\n   👥 کاربران جدید: {d['new_users']}\n   🤖 ربات جدید: {d['new_bots']}\n   💰 درآمد: {d['total_revenue']:,} تومان"
    else:
        daily_text = ""
    
    text = (f"📊 **گزارش کامل سیستم HyperScale**\n\n"
            f"👥 کل کاربران: {users:,}\n"
            f"✅ اشتراک فعال: {active:,}\n"
            f"🤖 کل ربات‌ها: {bots:,}\n"
            f"🟢 ربات فعال: {running:,}\n"
            f"⏰ ربات منقضی: {expired:,}\n"
            f"💰 کیف پول کل: {total_wallet:,} تومان\n"
            f"🖥️ ظرفیت ماشین‌ها: {machine_stats['available']:,} خالی از {machine_stats['total_capacity']:,}\n"
            f"📊 مصرف: {machine_stats['usage_percent']:.1f}%\n{daily_text}")
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_machines")
def admin_machines(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    machines = db.execute("SELECT * FROM machines ORDER BY id")
    if not machines:
        bot.send_message(call.message.chat.id, "🖥️ ماشینی وجود ندارد")
        return
    
    text = "🖥️ **وضعیت ماشین‌ها:**\n\n"
    for m in machines:
        usage = (m['current_bots'] / m['max_bots']) * 100 if m['max_bots'] > 0 else 0
        status_emoji = "🟢" if m['status'] == 'active' else "🔴"
        text += f"{status_emoji} **{m['name']}**\n   🤖 {m['current_bots']}/{m['max_bots']} ({usage:.1f}%)\n   💾 رم: {m['memory_used']}/{m['max_memory']} MB\n   ⚡ CPU: {m['cpu_usage']:.1f}%\n   🕐 آخرین فعالیت: {m['last_heartbeat'][:16] if m['last_heartbeat'] else 'ندارد'}\n\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "admin_scale_settings")
def admin_scale_settings(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📈 تغییر آستانه خودکار", callback_data="admin_set_threshold"),
        types.InlineKeyboardButton("⚙️ تغییر حداکثر همزمانی", callback_data="admin_set_concurrent"),
        types.InlineKeyboardButton("⏱️ تغییر فاصله چک سلامت", callback_data="admin_set_health_interval"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    bot.edit_message_text("⚡ **تنظیمات مقیاس‌پذیری**", 
                         call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_threshold")
def admin_set_threshold(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "📈 **آستانه خودکار (درصد، مثال: 70):**\n(زمانی که مصرف به این درصد برسد، ماشین جدید اضافه می‌شود)")
    bot.register_next_step_handler(msg, process_set_threshold)

def process_set_threshold(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        threshold = int(message.text.strip())
        if 30 <= threshold <= 95:
            update_setting('auto_scale_threshold', threshold, message.from_user.id)
            bot.reply_to(message, f"✅ آستانه خودکار به {threshold}% تغییر کرد")
        else:
            bot.reply_to(message, "❌ عدد بین 30 تا 95")
    except:
        bot.reply_to(message, "❌ عدد معتبر وارد کنید")

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_concurrent")
def admin_set_concurrent(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "⚙️ **حداکثر ساخت همزمان (مثال: 50):**")
    bot.register_next_step_handler(msg, process_set_concurrent)

def process_set_concurrent(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        concurrent = int(message.text.strip())
        if 1 <= concurrent <= 200:
            update_setting('max_concurrent_builds', concurrent, message.from_user.id)
            bot.reply_to(message, f"✅ حداکثر ساخت همزمان به {concurrent} تغییر کرد")
        else:
            bot.reply_to(message, "❌ عدد بین 1 تا 200")
    except:
        bot.reply_to(message, "❌ عدد معتبر وارد کنید")

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_health_interval")
def admin_set_health_interval(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "⏱️ **فاصله چک سلامت (ثانیه، مثال: 10):**")
    bot.register_next_step_handler(msg, process_set_health_interval)

def process_set_health_interval(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        interval = int(message.text.strip())
        if 5 <= interval <= 120:
            update_setting('health_check_interval', interval, message.from_user.id)
            bot.reply_to(message, f"✅ فاصله چک سلامت به {interval} ثانیه تغییر کرد")
        else:
            bot.reply_to(message, "❌ عدد بین 5 تا 120")
    except:
        bot.reply_to(message, "❌ عدد معتبر وارد کنید")

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_card")
def admin_set_card(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "💳 **شماره کارت جدید (۱۶ رقم):**")
    bot.register_next_step_handler(msg, process_set_card)

def process_set_card(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    card = message.text.strip().replace(' ', '')
    if not re.match(r'^\d{16}$', card):
        bot.reply_to(message, "❌ شماره کارت باید ۱۶ رقم باشد")
        return
    update_setting('card_number', card, message.from_user.id)
    display = ' '.join([card[i:i+4] for i in range(0, 16, 4)])
    update_setting('card_number_display', display, message.from_user.id)
    bot.reply_to(message, f"✅ شماره کارت به {display} تغییر کرد")

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_price")
def admin_set_price(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "💰 **قیمت اشتراک (تومان، مثال: 2000000):**")
    bot.register_next_step_handler(msg, process_set_price)

def process_set_price(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        price = int(message.text.strip())
        if price >= 100000:
            update_setting('subscription_price', price, message.from_user.id)
            update_setting('subscription_price_str', f"{price:,} تومان", message.from_user.id)
            bot.reply_to(message, f"✅ قیمت اشتراک به {price:,} تومان تغییر کرد")
        else:
            bot.reply_to(message, "❌ قیمت باید حداقل ۱۰۰,۰۰۰ تومان باشد")
    except:
        bot.reply_to(message, "❌ عدد معتبر وارد کنید")

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_guide")
def admin_set_guide(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "📝 **متن راهنمای جدید را ارسال کنید:**")
    bot.register_next_step_handler(msg, process_set_guide)

def process_set_guide(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    update_setting('guide_text', message.text.strip(), message.from_user.id)
    bot.reply_to(message, "✅ متن راهنما با موفقیت به‌روزرسانی شد")

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_build_limit")
def admin_set_build_limit(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "📈 **حداکثر ساخت ربات در ساعت برای هر کاربر (مثال: 10):**")
    bot.register_next_step_handler(msg, process_set_build_limit)

def process_set_build_limit(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        limit = int(message.text.strip())
        if 1 <= limit <= 100:
            update_setting('max_builds_per_hour', limit, message.from_user.id)
            bot.reply_to(message, f"✅ حداکثر ساخت در ساعت به {limit} تغییر کرد")
        else:
            bot.reply_to(message, "❌ عدد بین 1 تا 100")
    except:
        bot.reply_to(message, "❌ عدد معتبر وارد کنید")

@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "🚀 منوی اصلی:", reply_markup=get_main_menu(True))

# ==================== پیام همگانی ====================
@bot.message_handler(func=lambda m: m.text == '📢 پیام همگانی')
def broadcast_prompt(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(message.chat.id, "📢 **متن پیام همگانی را ارسال کنید:**\n\n(می‌توانید از Markdown استفاده کنید)")
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    text = message.text
    users = db.execute("SELECT user_id FROM users")
    sent = 0
    failed = 0
    
    status_msg = bot.reply_to(message, "🔄 در حال ارسال پیام همگانی...")
    
    for user in users:
        try:
            bot.send_message(user['user_id'], text, parse_mode='Markdown')
            sent += 1
            time.sleep(0.05)
        except:
            failed += 1
    
    bot.edit_message_text(f"✅ پیام همگانی ارسال شد!\n\n📨 ارسال موفق: {sent}\n❌ ناموفق: {failed}", 
                         message.chat.id, status_msg.message_id)

# ==================== ویرایش پیام‌ها ====================
@bot.message_handler(func=lambda m: m.text == '✏️ ویرایش پیام‌ها')
def edit_messages_prompt(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    messages = message_manager.get_all_messages()
    text = "✏️ **پیام‌های قابل ویرایش:**\n\n"
    for msg in messages:
        text += f"• `{msg['key']}` - {msg['title']}\n"
    text += "\nبرای ویرایش از دستور زیر استفاده کنید:\n/editmsg <key> <متن جدید>"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== مانیتورینگ خودکار ====================
def monitor_system():
    while True:
        try:
            # بررسی اشتراک‌های منقضی
            for user in db.execute('SELECT user_id, subscription_expiry, subscription_status FROM users WHERE subscription_status = "active"'):
                if user['subscription_expiry']:
                    expiry = datetime.fromisoformat(user['subscription_expiry'])
                    if expiry < datetime.now():
                        db.execute('UPDATE users SET subscription_status = "inactive", warning_sent = 0 WHERE user_id = ?', (user['user_id'],))
                        try:
                            bot.send_message(user['user_id'], f"⚠️ اشتراک شما منقضی شد!\n💰 {get_setting('subscription_price_str')}\nلطفاً برای تمدید اقدام کنید.")
                        except:
                            pass
            
            # بررسی ربات‌های منقضی
            expired_bots = db.execute("SELECT id, user_id FROM bots WHERE expires_at < datetime('now') AND status = 'running'")
            for bot_rec in expired_bots:
                machine_manager.stop_bot(bot_rec['id'])
                db.execute("UPDATE bots SET status = 'expired' WHERE id = ?", (bot_rec['id'],))
                try:
                    bot.send_message(bot_rec['user_id'], f"⏰ یکی از ربات‌های شما به دلیل پایان زمان {get_setting('bot_active_minutes')} دقیقه‌ای متوقف شد.\nبرای فعالسازی مجدد از بخش ربات‌های من استفاده کنید.")
                except:
                    pass
            
            # ثبت آمار روزانه
            today = datetime.now().date().isoformat()
            db.execute('INSERT OR IGNORE INTO daily_stats (date, new_users, new_bots, new_subscriptions, total_revenue, active_bots) VALUES (?, 0, 0, 0, 0, 0)', (today,))
            
            active_bots = db.execute("SELECT COUNT(*) as count FROM bots WHERE status = 'running'")[0]['count']
            db.execute('UPDATE daily_stats SET active_bots = ? WHERE date = ?', (active_bots, today))
            
            time.sleep(60)
        except Exception as e:
            logger.error(f"Monitor error: {e}")
            time.sleep(60)

threading.Thread(target=monitor_system, daemon=True).start()

# ==================== کلاس BuildQueue نهایی ====================
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
                f"🔄 در حال ساخت ربات...\n🆔 {build_item['id']}\n⏱️ زمان فعالسازی: {get_setting('bot_active_minutes')} دقیقه\n⏳ لطفاً صبر کنید",
                build_item['chat_id'],
                build_item['message_id']
            )
            
            build_data = build_item['build_data']
            
            result = machine_manager.run_bot_with_expiry(
                build_data['bot_id'], 
                build_data['main_code'], 
                build_data['token'],
                datetime.now() + timedelta(minutes=get_setting('bot_active_minutes'))
            )
            
            if result['success']:
                db.execute('''
                    INSERT INTO bots (id, user_id, token, name, username, file_path, pid, machine_id, 
                                     status, created_at, expires_at, project_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'running', ?, ?, 'single_file')
                ''', (build_data['bot_id'], build_data['user_id'], build_data['token'],
                      build_data['bot_info']['first_name'], build_data['bot_info']['username'],
                      build_data['file_path'], result['pid'], result['machine_id'],
                      datetime.now().isoformat(), 
                      (datetime.now() + timedelta(minutes=get_setting('bot_active_minutes'))).isoformat()))
                
                db.execute('UPDATE users SET bots_count = bots_count + 1, total_builds = total_builds + 1, last_build_at = ? WHERE user_id = ?',
                          (datetime.now().isoformat(), build_data['user_id']))
                
                user = get_user(build_data['user_id'])
                if user and user.get('referred_by'):
                    commission = int(get_setting('subscription_price') * get_setting('withdraw_percent') / 100)
                    add_wallet_balance(user['referred_by'], commission)
                    try:
                        temp_bot.send_message(user['referred_by'], f"🎉 کمیسیون {commission:,} تومان به کیف پول شما اضافه شد")
                    except:
                        pass
                
                temp_bot.edit_message_text(
                    f"✅ **ربات {build_data['bot_info']['first_name']} با موفقیت ساخته شد!**\n\n"
                    f"🤖 نام: @{build_data['bot_info']['username']}\n"
                    f"⏱️ زمان فعال بودن: {get_setting('bot_active_minutes')} دقیقه\n\n"
                    f"⚠️ توجه: ربات شما به طور خودکار پس از {get_setting('bot_active_minutes')} دقیقه متوقف می‌شود.",
                    build_item['chat_id'], 
                    build_item['message_id'],
                    parse_mode='Markdown'
                )
            else:
                temp_bot.edit_message_text(
                    f"❌ خطا در ساخت: {result.get('error', 'مشخص نشده')}", 
                    build_item['chat_id'], 
                    build_item['message_id']
                )
            
        except Exception as e:
            logger.error(f"Build failed: {e}")
            try:
                temp_bot.edit_message_text(
                    f"❌ خطا در ساخت ربات: {str(e)[:200]}", 
                    build_item['chat_id'], 
                    build_item['message_id']
                )
            except:
                pass
    
    def get_queue_length(self):
        return self.queue.qsize()

# ایجاد نمونه BuildQueue
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
                
                # بررسی ربات‌های در حال اجرا
                for bot_rec in db.execute('SELECT id, token, status, expires_at FROM bots WHERE status = "running"'):
                    # بررسی انقضا
                    if bot_rec['expires_at']:
                        expiry = datetime.fromisoformat(bot_rec['expires_at'])
                        if expiry < datetime.now():
                            machine_manager.stop_bot(bot_rec['id'])
                            db.execute("UPDATE bots SET status = 'expired' WHERE id = ?", (bot_rec['id'],))
                            continue
                    
                    # بررسی سلامت API
                    try:
                        resp = requests.get(
                            f"https://api.telegram.org/bot{bot_rec['token']}/getMe",
                            timeout=5
                        )
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
        
        if bot_rec.get('file_path') and os.path.exists(bot_rec['file_path']):
            try:
                with open(bot_rec['file_path'], 'r', encoding='utf-8', errors='ignore') as f:
                    code = f.read()
                
                expires_at = datetime.now() + timedelta(minutes=get_setting('bot_active_minutes'))
                result = machine_manager.run_bot_with_expiry(bot_id, code, bot_rec['token'], expires_at)
                
                if result['success']:
                    db.execute('UPDATE bots SET status = "running", machine_id = ?, pid = ?, expires_at = ?, last_active = ? WHERE id = ?',
                              (result['machine_id'], result['pid'], expires_at.isoformat(), datetime.now().isoformat(), bot_id))
                    logger.info(f"✅ Auto-restarted bot {bot_id}")
                    
                    user = db.execute('SELECT user_id FROM bots WHERE id = ?', (bot_id,))
                    if user:
                        try:
                            temp_bot = telebot.TeleBot(BOT_TOKEN)
                            temp_bot.send_message(user[0]['user_id'], f"🔄 ربات {bot_rec['name']} به صورت خودکار ریستارت شد و {get_setting('bot_active_minutes')} دقیقه دیگر فعال است.")
                        except:
                            pass
                else:
                    db.execute('UPDATE bots SET status = "error" WHERE id = ?', (bot_id,))
            except Exception as e:
                logger.error(f"Failed to restart bot {bot_id}: {e}")

health_checker = HealthChecker()

# ==================== اجرا ====================
if __name__ == "__main__":
    print("=" * 80)
    print("🚀 ربات مادر HyperScale - نسخه 23.0 Ultimate".center(80))
    print("=" * 80)
    print(f"👑 ادمین‌ها: {ADMIN_IDS}")
    print(f"🤖 نام ربات: @{BOT_USERNAME}")
    print(f"💰 قیمت اشتراک: {get_setting('subscription_price_str')}")
    print(f"⭐ کمیسیون رفرال: {get_setting('withdraw_percent')}%")
    print(f"⏱️ زمان فعالسازی هر ربات: {get_setting('bot_active_minutes')} دقیقه")
    print(f"🤖 حداکثر ربات هر کاربر: {get_setting('max_bots_per_user')}")
    print(f"⚡ حداکثر ساخت همزمان: {get_setting('max_concurrent_builds')}")
    print(f"📁 پشتیبانی از پوشه: فعال")
    print(f"📚 کتابخانه سفارشی: فعال")
    print("=" * 80)
    print("✅ ربات با موفقیت راه‌اندازی شد!")
    print("=" * 80)
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            logger.error(f"Polling error: {e}")
            time.sleep(5)