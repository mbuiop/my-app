#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║     🚀 ULTRA MOTHER BOT - ENTERPRISE EDITION v10.0                          ║
║     ⚡ High Performance - Isolated Execution - Advanced Caching             ║
║     💰 Commercial Version - Price: 2,000,000 Toman                          ║
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
import signal
import secrets
import logging
import queue
import uuid
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from functools import wraps
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import tempfile
import resource
import platform

# ==================== تنظیمات پیشرفته ====================

# محدودیت‌های سخت‌افزاری برای ایزوله‌سازی
try:
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 * 1024 * 1024, 2 * 1024 * 1024 * 1024))  # 2GB RAM
    resource.setrlimit(resource.RLIMIT_CPU, (300, 300))  # 5 minutes CPU
    resource.setrlimit(resource.RLIMIT_NOFILE, (1024, 1024))  # 1024 open files
except:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DIRS = {
    'DB': os.path.join(BASE_DIR, "database"),
    'CACHE': os.path.join(BASE_DIR, "cache"),
    'FILES': os.path.join(BASE_DIR, "user_files"),
    'RUNNING': os.path.join(BASE_DIR, "running_bots"),
    'ISOLATED': os.path.join(BASE_DIR, "isolated_envs"),
    'LOGS': os.path.join(BASE_DIR, "logs"),
    'RECEIPTS': os.path.join(BASE_DIR, "receipts"),
    'TEMP': os.path.join(BASE_DIR, "temp"),
    'FOLDERS': os.path.join(BASE_DIR, "user_folders"),
}

for dir_path in DIRS.values():
    os.makedirs(dir_path, exist_ok=True)

# ==================== تنظیمات اصلی ====================
BOT_TOKEN = "7685135237:AAEmsHktRw9cEqrHTkCoPZk-fBimK7TDjOo"
ADMIN_IDS = [327855654]
BOT_USERNAME = "ROBTTSAZE_bot"

# تنظیمات مالی
SUBSCRIPTION_PRICE = 2000000  # 2 میلیون تومان
SUBSCRIPTION_PRICE_STR = "۲,۰۰۰,۰۰۰ تومان"
CARD_NUMBER = "5892101187322777"
CARD_NUMBER_DISPLAY = "5892 1011 8732 2777"
CARD_HOLDER = "مرتضی نیکخو خنجری"
CARD_BANK = "بانک ملی"
WITHDRAW_PERCENT = 7
MIN_WITHDRAW = 2000000

# محدودیت‌ها
MAX_BOTS_PER_USER = 3
MAX_CONCURRENT_EXECUTIONS = 100
CACHE_TTL = 3600

# ==================== سیستم کش پیشرفته ====================
class AdvancedCache:
    """کش پیشرفته با پشتیبانی از TTL و حافظه"""
    
    def __init__(self, max_size=10000):
        self.cache = {}
        self.ttl = {}
        self.max_size = max_size
        self.lock = threading.RLock()
        self.hits = 0
        self.misses = 0
        self._start_cleanup()
    
    def _start_cleanup(self):
        def cleanup():
            while True:
                try:
                    with self.lock:
                        now = time.time()
                        expired = [k for k, exp in self.ttl.items() if exp <= now]
                        for k in expired:
                            if k in self.cache:
                                del self.cache[k]
                            if k in self.ttl:
                                del self.ttl[k]
                    time.sleep(60)
                except:
                    pass
        
        threading.Thread(target=cleanup, daemon=True).start()
    
    def get(self, key):
        with self.lock:
            if key in self.cache:
                if self.ttl.get(key, float('inf')) > time.time():
                    self.hits += 1
                    return self.cache[key]
                else:
                    del self.cache[key]
                    if key in self.ttl:
                        del self.ttl[key]
            self.misses += 1
            return None
    
    def set(self, key, value, ttl=CACHE_TTL):
        with self.lock:
            if len(self.cache) >= self.max_size:
                # حذف قدیمی‌ترین مورد
                oldest = min(self.ttl.items(), key=lambda x: x[1])[0]
                del self.cache[oldest]
                del self.ttl[oldest]
            
            self.cache[key] = value
            self.ttl[key] = time.time() + ttl
    
    def delete(self, key):
        with self.lock:
            if key in self.cache:
                del self.cache[key]
            if key in self.ttl:
                del self.ttl[key]
    
    def get_stats(self):
        with self.lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total * 100) if total > 0 else 0
            return {
                'size': len(self.cache),
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': round(hit_rate, 2)
            }

# ==================== دیتابیس پیشرفته ====================
class AdvancedDatabase:
    def __init__(self):
        self.conn = None
        self.cache = AdvancedCache(max_size=5000)
        self._init_db()
        self._init_tables()
    
    def _init_db(self):
        self.conn = sqlite3.connect(
            os.path.join(DIRS['DB'], 'mother_bot.db'),
            timeout=60,
            check_same_thread=False
        )
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA cache_size=-1000000")
        self.conn.execute("PRAGMA mmap_size=10000000000")
    
    def execute(self, query, params=(), use_cache=False, cache_ttl=300):
        if use_cache:
            cache_key = hashlib.md5(f"{query}{params}".encode()).hexdigest()
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached
        
        try:
            cursor = self.conn.execute(query, params)
            self.conn.commit()
            
            if query.strip().upper().startswith('SELECT'):
                result = cursor.fetchall()
                if use_cache:
                    self.cache.set(cache_key, result, cache_ttl)
                return result
            return cursor.lastrowid if query.strip().upper().startswith('INSERT') else True
        except Exception as e:
            print(f"DB Error: {e}")
            return []
    
    def _init_tables(self):
        # کاربران با پشتیبانی از اشتراک پولی
        self.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                phone TEXT,
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
                is_banned INTEGER DEFAULT 0,
                total_executions INTEGER DEFAULT 0,
                total_builds INTEGER DEFAULT 0,
                language TEXT DEFAULT 'fa'
            )
        ''')
        
        # ربات‌ها با محدودیت ۳ تا
        self.execute('''
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
                status TEXT DEFAULT 'stopped',
                created_at TIMESTAMP,
                last_active TIMESTAMP,
                last_execution TIMESTAMP,
                execution_count INTEGER DEFAULT 0,
                memory_used INTEGER DEFAULT 0,
                cpu_used REAL DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        # پوشه‌ها
        self.execute('''
            CREATE TABLE IF NOT EXISTS folders (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                folder_name TEXT,
                folder_path TEXT,
                parent_id TEXT,
                structure TEXT,
                created_at TIMESTAMP,
                file_count INTEGER DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        # فایل‌های پوشه
        self.execute('''
            CREATE TABLE IF NOT EXISTS folder_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_id TEXT,
                file_name TEXT,
                file_path TEXT,
                content TEXT,
                added_at TIMESTAMP,
                FOREIGN KEY(folder_id) REFERENCES folders(id) ON DELETE CASCADE
            )
        ''')
        
        # اجراها
        self.execute('''
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
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
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
                transaction_id TEXT,
                reviewed_by INTEGER,
                reviewed_at TIMESTAMP,
                created_at TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
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
                bank_name TEXT,
                status TEXT DEFAULT 'pending',
                tracking_code TEXT,
                created_at TIMESTAMP,
                processed_at TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        # کتابخانه‌های نصب شده
        self.execute('''
            CREATE TABLE IF NOT EXISTS libraries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                version TEXT,
                description TEXT,
                installed_at TIMESTAMP
            )
        ''')
        
        # تنظیمات سیستم
        self.execute('''
            CREATE TABLE IF NOT EXISTS settings (
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
                active_users INTEGER DEFAULT 0,
                new_bots INTEGER DEFAULT 0,
                active_bots INTEGER DEFAULT 0,
                new_subscriptions INTEGER DEFAULT 0,
                total_revenue INTEGER DEFAULT 0,
                total_executions INTEGER DEFAULT 0
            )
        ''')
        
        # تنظیمات پیش‌فرض
        default_settings = {
            'subscription_price': str(SUBSCRIPTION_PRICE),
            'subscription_price_str': SUBSCRIPTION_PRICE_STR,
            'card_number': CARD_NUMBER,
            'card_number_display': CARD_NUMBER_DISPLAY,
            'card_holder': CARD_HOLDER,
            'card_bank': CARD_BANK,
            'withdraw_percent': str(WITHDRAW_PERCENT),
            'min_withdraw': str(MIN_WITHDRAW),
            'max_bots_per_user': str(MAX_BOTS_PER_USER),
        }
        
        for key, value in default_settings.items():
            self.execute("INSERT OR IGNORE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
                        (key, value, datetime.now().isoformat()))
        
        # ایجاد ایندکس‌ها
        self.execute("CREATE INDEX IF NOT EXISTS idx_users_subscription ON users(subscription_status, subscription_expiry)")
        self.execute("CREATE INDEX IF NOT EXISTS idx_bots_user ON bots(user_id)")
        self.execute("CREATE INDEX IF NOT EXISTS idx_executions_user ON executions(user_id, started_at)")
        
        self.conn.commit()
    
    def get_setting(self, key):
        cached = self.cache.get(f"setting_{key}")
        if cached:
            return cached
        
        result = self.execute("SELECT value FROM settings WHERE key = ?", (key,))
        if result:
            value = result[0]['value']
            self.cache.set(f"setting_{key}", value, 3600)
            return value
        return None
    
    def update_setting(self, key, value):
        self.execute("UPDATE settings SET value = ?, updated_at = ? WHERE key = ?",
                    (str(value), datetime.now().isoformat(), key))
        self.cache.delete(f"setting_{key}")
        return True
    
    def get_user(self, user_id):
        cached = self.cache.get(f"user_{user_id}")
        if cached:
            return cached
        
        result = self.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        if result:
            user = dict(result[0])
            self.cache.set(f"user_{user_id}", user, 300)
            return user
        return None
    
    def create_user(self, user_id, username, first_name, last_name, referred_by=None):
        now = datetime.now().isoformat()
        referral_code = hashlib.md5(f"{user_id}_{time.time()}_{secrets.token_hex(4)}".encode()).hexdigest()[:12]
        
        self.execute('''
            INSERT OR IGNORE INTO users 
            (user_id, username, first_name, last_name, referral_code, referred_by, created_at, last_active, 
             subscription_status, wallet_balance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'inactive', 0)
        ''', (user_id, username, first_name, last_name, referral_code, referred_by, now, now))
        
        if referred_by and referred_by != user_id:
            self.execute('UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = ?', (referred_by,))
        
        self.cache.delete(f"user_{user_id}")
        return True
    
    def check_subscription(self, user_id):
        """بررسی اشتراک پولی"""
        user = self.get_user(user_id)
        if not user:
            return False
        
        if user['subscription_status'] == 'active':
            expiry = datetime.fromisoformat(user['subscription_expiry'])
            if expiry > datetime.now():
                return True
        
        return False
    
    def activate_subscription(self, user_id, months=1):
        """فعال‌سازی اشتراک پولی"""
        user = self.get_user(user_id)
        now = datetime.now()
        
        if user and user['subscription_status'] == 'active' and user['subscription_expiry']:
            new_expiry = datetime.fromisoformat(user['subscription_expiry']) + timedelta(days=30*months)
        else:
            new_expiry = now + timedelta(days=30*months)
        
        self.execute('''
            UPDATE users 
            SET subscription_status = 'active', subscription_expiry = ?
            WHERE user_id = ?
        ''', (new_expiry.isoformat(), user_id))
        
        # به‌روزرسانی آمار
        today = datetime.now().date().isoformat()
        self.execute('''
            INSERT INTO daily_stats (date, new_subscriptions, total_revenue) 
            VALUES (?, 1, ?) 
            ON CONFLICT(date) DO UPDATE SET 
                new_subscriptions = new_subscriptions + 1, 
                total_revenue = total_revenue + ?
        ''', (today, SUBSCRIPTION_PRICE, SUBSCRIPTION_PRICE))
        
        self.cache.delete(f"user_{user_id}")
        return new_expiry
    
    def get_user_bots_count(self, user_id):
        cached = self.cache.get(f"user_bots_{user_id}")
        if cached is not None:
            return cached
        
        result = self.execute("SELECT COUNT(*) as c FROM bots WHERE user_id = ?", (user_id,))
        count = result[0]['c'] if result else 0
        self.cache.set(f"user_bots_{user_id}", count, 60)
        return count
    
    def can_create_bot(self, user_id):
        """بررسی محدودیت ۳ ربات"""
        max_bots = int(self.get_setting('max_bots_per_user') or 3)
        current_bots = self.get_user_bots_count(user_id)
        return current_bots < max_bots, max_bots, current_bots
    
    def add_bot(self, bot_id, user_id, token, name, username, file_path=None, folder_path=None, folder_id=None):
        now = datetime.now().isoformat()
        self.execute('''
            INSERT INTO bots (id, user_id, token, name, username, file_path, folder_path, folder_id, 
                            status, created_at, last_active, execution_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'stopped', ?, ?, 0)
        ''', (bot_id, user_id, token, name, username, file_path, folder_path, folder_id, now, now))
        
        self.execute('UPDATE users SET bots_count = bots_count + 1, total_builds = total_builds + 1 WHERE user_id = ?', (user_id,))
        
        today = datetime.now().date().isoformat()
        self.execute('''
            INSERT INTO daily_stats (date, new_bots) VALUES (?, 1)
            ON CONFLICT(date) DO UPDATE SET new_bots = new_bots + 1
        ''', (today,))
        
        self.cache.delete(f"user_bots_{user_id}")
        return True
    
    def delete_bot(self, bot_id, user_id):
        self.execute('DELETE FROM bots WHERE id = ? AND user_id = ?', (bot_id, user_id))
        self.execute('UPDATE users SET bots_count = bots_count - 1 WHERE user_id = ?', (user_id,))
        self.cache.delete(f"user_bots_{user_id}")
        self.cache.delete(f"user_{user_id}")
        return True
    
    def add_execution(self, exec_id, user_id, bot_id):
        now = datetime.now().isoformat()
        self.execute('''
            INSERT INTO executions (id, user_id, bot_id, status, started_at)
            VALUES (?, ?, ?, 'running', ?)
        ''', (exec_id, user_id, bot_id, now))
        
        self.execute('UPDATE users SET total_executions = total_executions + 1 WHERE user_id = ?', (user_id,))
        
        today = datetime.now().date().isoformat()
        self.execute('''
            INSERT INTO daily_stats (date, total_executions) VALUES (?, 1)
            ON CONFLICT(date) DO UPDATE SET total_executions = total_executions + 1
        ''', (today,))
        
        return True

db = AdvancedDatabase()

# ==================== موتور اجرای ایزوله ====================
class IsolatedExecutionEngine:
    """موتور اجرای ایزوله با محدودیت‌های سخت‌افزاری"""
    
    def __init__(self):
        self.active_executions = {}
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_EXECUTIONS)
        self._start_monitor()
    
    def _start_monitor(self):
        def monitor():
            while True:
                try:
                    with self.lock:
                        for bot_id, info in list(self.active_executions.items()):
                            if info.get('process') and info['process'].poll() is not None:
                                del self.active_executions[bot_id]
                    time.sleep(10)
                except:
                    time.sleep(30)
        
        threading.Thread(target=monitor, daemon=True).start()
    
    def _create_isolated_env(self, bot_id):
        """ایجاد محیط ایزوله برای ربات"""
        env_dir = os.path.join(DIRS['ISOLATED'], bot_id)
        os.makedirs(env_dir, exist_ok=True)
        
        # ایجاد فایل محدودیت‌ها
        limits_script = os.path.join(env_dir, 'limits.py')
        with open(limits_script, 'w') as f:
            f.write('''
import resource
import signal
import sys
import os

# محدودیت حافظه
try:
    resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))  # 256MB
    resource.setrlimit(resource.RLIMIT_CPU, (300, 300))  # 5 minutes
    resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))  # 256 files
except:
    pass

def timeout_handler(signum, frame):
    print("⏰ زمان اجرا به پایان رسید!", file=sys.stderr)
    sys.exit(1)

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(300)
''')
        
        return env_dir
    
    def execute_bot(self, bot_id, user_id, code, folder_path=None):
        """اجرای ربات در محیط ایزوله"""
        exec_id = str(uuid.uuid4())[:8]
        
        # ذخیره اجرا
        db.add_execution(exec_id, user_id, bot_id)
        
        # ایجاد محیط ایزوله
        env_dir = self._create_isolated_env(bot_id)
        
        # ذخیره کد
        code_path = os.path.join(env_dir, 'bot.py')
        with open(code_path, 'w', encoding='utf-8') as f:
            f.write(code)
        
        # مسیر اجرا
        cwd = folder_path if folder_path and os.path.exists(folder_path) else env_dir
        
        # اجرا با محدودیت
        try:
            process = subprocess.Popen(
                [sys.executable, code_path],
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None,
                env={**os.environ, 'PYTHONPATH': ''}
            )
            
            with self.lock:
                self.active_executions[bot_id] = {
                    'process': process,
                    'exec_id': exec_id,
                    'pid': process.pid,
                    'started_at': time.time(),
                    'user_id': user_id
                }
            
            db.execute('UPDATE bots SET status = "running", pid = ?, last_execution = ?, execution_count = execution_count + 1 WHERE id = ?',
                      (process.pid, datetime.now().isoformat(), bot_id))
            
            return exec_id, True, None
            
        except Exception as e:
            return exec_id, False, str(e)
    
    def stop_execution(self, bot_id):
        """توقف اجرا"""
        with self.lock:
            if bot_id in self.active_executions:
                info = self.active_executions[bot_id]
                try:
                    os.killpg(os.getpgid(info['pid']), signal.SIGTERM)
                except:
                    try:
                        info['process'].terminate()
                    except:
                        pass
                
                del self.active_executions[bot_id]
        
        db.execute('UPDATE bots SET status = "stopped" WHERE id = ?', (bot_id,))
        return True
    
    def get_status(self, bot_id):
        """وضعیت اجرا"""
        with self.lock:
            if bot_id in self.active_executions:
                info = self.active_executions[bot_id]
                if info['process'].poll() is None:
                    uptime = int(time.time() - info['started_at'])
                    return {'running': True, 'uptime': uptime, 'pid': info['pid']}
                else:
                    del self.active_executions[bot_id]
        
        return {'running': False, 'uptime': 0}
    
    def get_stats(self):
        with self.lock:
            return {
                'active': len(self.active_executions),
                'max': MAX_CONCURRENT_EXECUTIONS
            }

# ==================== مدیریت پوشه‌ها ====================
class FolderManager:
    def create_folder(self, user_id, folder_name, parent_id=None):
        folder_path = os.path.join(DIRS['FOLDERS'], str(user_id), folder_name)
        if parent_id:
            folders = db.execute("SELECT folder_path FROM folders WHERE id = ?", (parent_id,))
            if folders:
                folder_path = os.path.join(folders[0]['folder_path'], folder_name)
        
        if os.path.exists(folder_path):
            return None, "پوشه وجود دارد"
        
        os.makedirs(folder_path, exist_ok=True)
        folder_id = hashlib.md5(f"{user_id}_{folder_name}_{time.time()}".encode()).hexdigest()[:12]
        
        db.execute('''
            INSERT INTO folders (id, user_id, folder_name, folder_path, parent_id, structure, created_at, file_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        ''', (folder_id, user_id, folder_name, folder_path, parent_id, json.dumps({'files': []}), datetime.now().isoformat()))
        
        return folder_id, "پوشه ساخته شد"
    
    def add_file(self, folder_id, file_name, content):
        folders = db.execute("SELECT folder_path, structure FROM folders WHERE id = ?", (folder_id,))
        if not folders:
            return False, "پوشه یافت نشد"
        
        folder = folders[0]
        file_path = os.path.join(folder['folder_path'], file_name)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        structure = json.loads(folder['structure'])
        structure['files'].append({
            'name': file_name,
            'added_at': datetime.now().isoformat(),
            'size': len(content)
        })
        
        db.execute('UPDATE folders SET structure = ?, file_count = file_count + 1 WHERE id = ?',
                  (json.dumps(structure), folder_id))
        
        db.execute('INSERT INTO folder_files (folder_id, file_name, file_path, content, added_at) VALUES (?, ?, ?, ?, ?)',
                  (folder_id, file_name, file_path, content[:500], datetime.now().isoformat()))
        
        return True, "فایل اضافه شد"
    
    def get_files(self, folder_id):
        result = db.execute("SELECT file_name, added_at FROM folder_files WHERE folder_id = ?", (folder_id,))
        return [dict(r) for r in result]
    
    def read_file(self, folder_id, file_name):
        result = db.execute("SELECT file_path FROM folder_files WHERE folder_id = ? AND file_name = ?", (folder_id, file_name))
        if result and os.path.exists(result[0]['file_path']):
            with open(result[0]['file_path'], 'r', encoding='utf-8') as f:
                return f.read()
        return None

# ==================== کتابخانه منیجر ====================
class LibraryManager:
    def __init__(self):
        self.installing = set()
        self.install_queue = queue.Queue()
        self._start_worker()
    
    def _start_worker(self):
        def worker():
            while True:
                try:
                    lib, chat_id, msg_id, bot_instance = self.install_queue.get(timeout=1)
                    self._install_library(lib, chat_id, msg_id, bot_instance)
                    self.install_queue.task_done()
                except queue.Empty:
                    time.sleep(0.5)
                except:
                    pass
        
        threading.Thread(target=worker, daemon=True).start()
    
    def _install_library(self, lib, chat_id, msg_id, bot_instance):
        if lib in self.installing:
            return
        
        self.installing.add(lib)
        
        try:
            bot_instance.edit_message_text(f"📦 در حال نصب {lib}...", chat_id, msg_id)
            
            process = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', lib, '--quiet'],
                capture_output=True, text=True, timeout=180
            )
            
            if process.returncode == 0:
                # دریافت نسخه
                ver_result = subprocess.run([sys.executable, '-m', 'pip', 'show', lib],
                                           capture_output=True, text=True, timeout=10)
                version = "نامشخص"
                for line in ver_result.stdout.split('\n'):
                    if line.startswith('Version:'):
                        version = line.split(':', 1)[1].strip()
                        break
                
                db.execute("INSERT OR IGNORE INTO libraries (name, version, installed_at) VALUES (?, ?, ?)",
                          (lib, version, datetime.now().isoformat()))
                
                bot_instance.edit_message_text(f"✅ {lib} نسخه {version} نصب شد!", chat_id, msg_id)
            else:
                error = process.stderr[:200] if process.stderr else "خطا"
                bot_instance.edit_message_text(f"❌ خطا: {error}", chat_id, msg_id)
        except subprocess.TimeoutExpired:
            bot_instance.edit_message_text("❌ زمان نصب تمام شد!", chat_id, msg_id)
        except Exception as e:
            bot_instance.edit_message_text(f"❌ خطا: {str(e)[:100]}", chat_id, msg_id)
        finally:
            self.installing.discard(lib)
    
    def install(self, lib, chat_id, msg_id, bot_instance):
        self.install_queue.put((lib, chat_id, msg_id, bot_instance))
        return True
    
    def get_available(self):
        return {
            'وب': {'Flask': 'flask', 'FastAPI': 'fastapi', 'Django': 'django'},
            'Async': {'aiohttp': 'aiohttp', 'httpx': 'httpx', 'aiogram': 'aiogram'},
            'دیتابیس': {'SQLAlchemy': 'sqlalchemy', 'asyncpg': 'asyncpg', 'redis': 'redis'},
            'ابزارها': {'requests': 'requests', 'beautifulsoup4': 'beautifulsoup4', 'numpy': 'numpy', 'pandas': 'pandas'}
        }

# ==================== ربات اصلی ====================
bot = telebot.TeleBot(BOT_TOKEN)
bot.remove_webhook()

executor = IsolatedExecutionEngine()
folder_manager = FolderManager()
library_manager = LibraryManager()

# ==================== منوها ====================
def escape_markdown(text):
    """فرار دادن کاراکترهای Markdown"""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join('\\' + c if c in escape_chars else c for c in str(text))

def get_main_menu(user_id):
    is_admin = user_id in ADMIN_IDS
    has_subscription = db.check_subscription(user_id)
    
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = []
    
    if has_subscription:
        buttons = [
            types.KeyboardButton('🤖 ساخت ربات جدید'),
            types.KeyboardButton('📁 مدیریت پوشه‌ها'),
            types.KeyboardButton('▶️ اجرای ربات'),
            types.KeyboardButton('🛑 توقف ربات'),
            types.KeyboardButton('📋 لیست ربات‌ها'),
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
            types.KeyboardButton('📢 پیام همگانی')
        ])
    
    markup.add(*buttons)
    return markup

# ==================== دستور start ====================
@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or ""
    username = message.from_user.username or ""
    
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
    
    db.create_user(user_id, username, first_name, message.from_user.last_name or "", referred_by)
    user = db.get_user(user_id)
    bot_username = bot.get_me().username
    referral_link = f"https://t.me/{bot_username}?start={user['referral_code']}"
    
    has_subscription = db.check_subscription(user_id)
    
    text = f"""🚀 **به ربات مادر خوش آمدید {escape_markdown(first_name)}**!

👤 شناسه: `{user_id}`
🎁 کد معرف: `{user['referral_code']}`
🔗 لینک دعوت: {referral_link}
💰 موجودی: {user['wallet_balance']:,} تومان

"""
    
    if has_subscription:
        expiry = datetime.fromisoformat(user['subscription_expiry'])
        text += f"✅ اشتراک فعال تا: {expiry.strftime('%Y-%m-%d')}\n"
        text += f"🤖 ربات ساخته شده: {db.get_user_bots_count(user_id)}/{db.get_setting('max_bots_per_user')}\n\n"
        text += "📤 از دکمه `🤖 ساخت ربات جدید` استفاده کنید."
    else:
        text += f"❌ **اشتراک شما فعال نیست!**\n"
        text += f"💰 قیمت اشتراک: {db.get_setting('subscription_price_str')}\n\n"
        text += "برای فعال‌سازی از دکمه `💰 خرید اشتراک` استفاده کنید."
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📋 کپی لینک", callback_data=f"copy_{user['referral_code']}"))
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=get_main_menu(user_id))

@bot.callback_query_handler(func=lambda call: call.data.startswith('copy_'))
def copy_link(call):
    code = call.data.replace('copy_', '')
    link = f"https://t.me/{bot.get_me().username}?start={code}"
    bot.answer_callback_query(call.id, f"✅ لینک کپی شد!\n{link}", show_alert=True)

# ==================== خرید اشتراک ====================
@bot.message_handler(func=lambda m: m.text == '💰 خرید اشتراک')
def buy_subscription(message):
    user_id = message.from_user.id
    
    if db.check_subscription(user_id):
        bot.send_message(message.chat.id, "✅ شما قبلاً اشتراک فعال دارید!")
        return
    
    price = db.get_setting('subscription_price_str')
    card = db.get_setting('card_number_display')
    holder = db.get_setting('card_holder')
    bank = db.get_setting('card_bank')
    
    text = f"""💳 **خرید اشتراک ماهیانه**

💰 مبلغ: {price}

🏦 **اطلاعات کارت:**
`{card}`
👤 {holder}
🏦 {bank}

📌 **نحوه پرداخت:**
1️⃣ مبلغ را به کارت فوق واریز کنید
2️⃣ رسید را به صورت عکس ارسال کنید
3️⃣ پس از تایید، اشتراک شما فعال می‌شود

⏱ زمان بررسی: حداکثر ۲۴ ساعت

⚠️ **توجه:** پس از فعال‌سازی، می‌توانید تا ۳ ربات بسازید!"""
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== فیش پرداخت ====================
@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    
    pending = db.execute("SELECT id FROM receipts WHERE user_id = ? AND status = 'pending'", (user_id,))
    if pending:
        bot.reply_to(message, "⏳ فیش قبلی در انتظار تایید است")
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
        ''', (user_id, SUBSCRIPTION_PRICE, receipt_path, payment_code, transaction_id, datetime.now().isoformat()))
        
        bot.reply_to(message, 
                    f"✅ **فیش شما دریافت شد!**\n\n"
                    f"💰 مبلغ: {SUBSCRIPTION_PRICE_STR}\n"
                    f"🆔 کد پیگیری: `{payment_code}`\n"
                    f"🔑 شناسه تراکنش: `{transaction_id}`\n\n"
                    f"⏱ ظرف ۲۴ ساعت بررسی می‌شود.")
        
        # اطلاع به ادمین
        user = db.get_user(user_id)
        for admin_id in ADMIN_IDS:
            try:
                with open(receipt_path, 'rb') as f:
                    bot.send_photo(admin_id, f, 
                                  caption=f"📸 فیش جدید\n👤 {user['first_name']}\n🆔 {user_id}\n💰 {SUBSCRIPTION_PRICE_STR}")
            except:
                pass
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")

# ==================== ساخت ربات جدید ====================
@bot.message_handler(func=lambda m: m.text == '🤖 ساخت ربات جدید')
def new_bot(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or ""
    
    if not db.check_subscription(user_id):
        text = f"""🌟 **ساخت ربات جدید**

کاربر گرامی {escape_markdown(first_name)}

❌ **اشتراک شما فعال نیست!**

💰 قیمت اشتراک: {db.get_setting('subscription_price_str')}

📌 **برای ساخت ربات، ابتدا:**
1️⃣ از دکمه `💰 خرید اشتراک` استفاده کنید
2️⃣ مبلغ را واریز کنید
3️⃣ رسید را ارسال کنید
4️⃣ پس از تایید، اشتراک شما فعال می‌شود

⚠️ **توجه:** هر کاربر می‌تواند حداکثر ۳ ربات داشته باشد!"""
        
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
                    f"📤 **ارسال فایل ربات**\n\n"
                    f"فایل `.py` یا `.zip` خود را ارسال کنید.\n"
                    f"✅ حداکثر حجم: ۵۰ مگابایت\n"
                    f"✅ توکن داخل کد باشد\n"
                    f"✅ حداکثر {max_bots} ربات فعال",
                    parse_mode='Markdown')

# ==================== آپلود فایل ====================
@bot.message_handler(content_types=['document'])
def handle_build_file(message):
    user_id = message.from_user.id
    file_name = message.document.file_name
    
    if not db.check_subscription(user_id):
        bot.reply_to(message, "❌ اشتراک فعال نیست!\nاز دکمه `💰 خرید اشتراک` استفاده کنید.", parse_mode='Markdown')
        return
    
    if not (file_name.endswith('.py') or file_name.endswith('.zip')):
        bot.reply_to(message, "❌ فقط فایل‌های `.py` یا `.zip` مجاز هستند!")
        return
    
    if message.document.file_size > 50 * 1024 * 1024:
        bot.reply_to(message, "❌ حجم بیشتر از ۵۰ مگابایت!")
        return
    
    can_create, max_bots, current_bots = db.can_create_bot(user_id)
    if not can_create:
        bot.reply_to(message, f"❌ حداکثر {max_bots} ربات!", parse_mode='Markdown')
        return
    
    status_msg = bot.reply_to(message, "🔄 در حال پردازش فایل...")
    
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
            bot.edit_message_text("❌ فایل پایتون پیدا نشد!", message.chat.id, status_msg.message_id)
            return
        
        # استخراج توکن
        token_patterns = [
            r'token\s*=\s*["\']([^"\']+)["\']',
            r'TOKEN\s*=\s*["\']([^"\']+)["\']',
            r'BOT_TOKEN\s*=\s*["\']([^"\']+)["\']',
        ]
        token = None
        for pattern in token_patterns:
            match = re.search(pattern, code, re.IGNORECASE)
            if match:
                token = match.group(1)
                break
        
        if not token:
            bot.edit_message_text("❌ توکن در کد پیدا نشد!", message.chat.id, status_msg.message_id)
            return
        
        # بررسی توکن
        try:
            resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
            if resp.status_code != 200:
                bot.edit_message_text("❌ توکن نامعتبر!", message.chat.id, status_msg.message_id)
                return
            bot_info = resp.json()['result']
        except:
            bot.edit_message_text("❌ خطا در بررسی توکن!", message.chat.id, status_msg.message_id)
            return
        
        # ایجاد ربات
        bot_id = hashlib.md5(f"{user_id}{token}{time.time()}".encode()).hexdigest()[:12]
        db.add_bot(bot_id, user_id, token, bot_info['first_name'], bot_info['username'], file_path)
        
        # اجرا
        exec_id, success, error = executor.execute_bot(bot_id, user_id, code)
        
        if success:
            reply = f"✅ **ربات ساخته شد!**\n\n"
            reply += f"🤖 نام: {bot_info['first_name']}\n"
            reply += f"🔗 t.me/{bot_info['username']}\n"
            reply += f"🆔 `{bot_id}`\n\n"
            reply += f"✅ ربات در حال اجراست!\n"
            reply += f"برای توقف از منوی `🛑 توقف ربات` استفاده کنید."
            
            bot.edit_message_text(reply, message.chat.id, status_msg.message_id, parse_mode='Markdown')
        else:
            bot.edit_message_text(f"❌ خطا در اجرا: {error}", message.chat.id, status_msg.message_id)
        
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)[:200]}", message.chat.id, status_msg.message_id)

# ==================== سایر منوها (ساده‌شده برای جلوگیری از خطا) ====================

@bot.message_handler(func=lambda m: m.text == '📋 لیست ربات‌ها')
def list_bots(message):
    user_id = message.from_user.id
    bots = db.execute("SELECT id, name, username, status, created_at FROM bots WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما هیچ رباتی ندارید!")
        return
    
    text = "🤖 **لیست ربات‌های شما**\n\n"
    for b in bots:
        status = executor.get_status(b['id'])
        status_text = "🟢 فعال" if status['running'] else "🔴 متوقف"
        text += f"**{b['name']}**\n🔗 t.me/{b['username']}\n📊 {status_text}\n📅 {b['created_at'][:10]}\n\n"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '▶️ اجرای ربات')
def run_prompt(message):
    user_id = message.from_user.id
    bots = db.execute("SELECT id, name, status FROM bots WHERE user_id = ?", (user_id,))
    
    if not bots:
        bot.send_message(message.chat.id, "📋 رباتی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        is_running = executor.get_status(b['id'])['running']
        emoji = "🟢" if is_running else "🔴"
        markup.add(types.InlineKeyboardButton(f"{emoji} {b['name']}", callback_data=f"run_{b['id']}"))
    
    bot.send_message(message.chat.id, "▶️ انتخاب ربات:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('run_'))
def run_bot(call):
    bot_id = call.data.replace('run_', '')
    user_id = call.from_user.id
    
    if not db.check_subscription(user_id):
        bot.answer_callback_query(call.id, "❌ اشتراک فعال نیست!", show_alert=True)
        return
    
    status = executor.get_status(bot_id)
    if status['running']:
        bot.answer_callback_query(call.id, "ربات در حال اجراست!", show_alert=True)
        return
    
    bot_info = db.execute("SELECT file_path, folder_path, token FROM bots WHERE id = ? AND user_id = ?", (bot_id, user_id))
    if not bot_info:
        bot.answer_callback_query(call.id, "ربات یافت نشد!", show_alert=True)
        return
    
    bot_info = dict(bot_info[0])
    
    code = None
    if bot_info.get('folder_path') and os.path.exists(bot_info['folder_path']):
        main_path = os.path.join(bot_info['folder_path'], 'main.py')
        if os.path.exists(main_path):
            with open(main_path, 'r', encoding='utf-8') as f:
                code = f.read()
    elif bot_info.get('file_path') and os.path.exists(bot_info['file_path']):
        with open(bot_info['file_path'], 'r', encoding='utf-8') as f:
            code = f.read()
    
    if not code:
        bot.answer_callback_query(call.id, "فایل ربات یافت نشد!", show_alert=True)
        return
    
    exec_id, success, error = executor.execute_bot(bot_id, user_id, code, bot_info.get('folder_path'))
    
    if success:
        bot.answer_callback_query(call.id, "✅ ربات اجرا شد!", show_alert=True)
    else:
        bot.answer_callback_query(call.id, f"❌ {error[:50]}", show_alert=True)
    
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: m.text == '🛑 توقف ربات')
def stop_prompt(message):
    user_id = message.from_user.id
    bots = db.execute("SELECT id, name FROM bots WHERE user_id = ?", (user_id,))
    
    if not bots:
        bot.send_message(message.chat.id, "📋 رباتی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        if executor.get_status(b['id'])['running']:
            markup.add(types.InlineKeyboardButton(f"🛑 {b['name']}", callback_data=f"stop_{b['id']}"))
    
    if not markup.keyboard:
        bot.send_message(message.chat.id, "📋 هیچ ربات در حال اجرایی ندارید!")
        return
    
    bot.send_message(message.chat.id, "🛑 انتخاب ربات:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('stop_'))
def stop_bot(call):
    bot_id = call.data.replace('stop_', '')
    executor.stop_execution(bot_id)
    bot.answer_callback_query(call.id, "✅ ربات متوقف شد!", show_alert=True)
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: m.text == '🗑 حذف ربات')
def delete_prompt(message):
    user_id = message.from_user.id
    bots = db.execute("SELECT id, name FROM bots WHERE user_id = ?", (user_id,))
    
    if not bots:
        bot.send_message(message.chat.id, "📋 رباتی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        markup.add(types.InlineKeyboardButton(f"🗑 {b['name']}", callback_data=f"del_{b['id']}"))
    
    bot.send_message(message.chat.id, "🗑 انتخاب ربات:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('del_'))
def confirm_delete(call):
    bot_id = call.data.replace('del_', '')
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ بله", callback_data=f"confirm_del_{bot_id}"),
              types.InlineKeyboardButton("❌ انصراف", callback_data="cancel_del"))
    bot.edit_message_text("⚠️ اطمینان دارید؟", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_del_'))
def do_delete(call):
    bot_id = call.data.replace('confirm_del_', '')
    executor.stop_execution(bot_id)
    db.delete_bot(bot_id, call.from_user.id)
    bot.edit_message_text("✅ ربات حذف شد!", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "cancel_del")
def cancel_delete(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: m.text == '💰 کیف پول')
def wallet(message):
    user = db.get_user(message.from_user.id)
    text = f"💰 **کیف پول شما**\n\n"
    text += f"👤 {user['first_name']}\n"
    text += f"💵 موجودی: {user['wallet_balance']:,} تومان\n"
    text += f"👥 دعوت‌ها: {user['referrals_count']}\n"
    text += f"💰 کمیسیون: {db.get_setting('withdraw_percent')}%\n"
    text += f"💸 حداقل برداشت: {int(db.get_setting('min_withdraw')):,} تومان"
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '👥 دعوت دوستان')
def invite(message):
    user = db.get_user(message.from_user.id)
    bot_username = bot.get_me().username
    link = f"https://t.me/{bot_username}?start={user['referral_code']}"
    
    text = f"👥 **دعوت دوستان**\n\n"
    text += f"🎁 کد: `{user['referral_code']}`\n"
    text += f"🔗 لینک: {link}\n"
    text += f"📊 دعوت‌ها: {user['referrals_count']}\n"
    text += f"💰 هر دعوت: {db.get_setting('withdraw_percent')}% کمیسیون"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📋 کپی لینک", callback_data=f"copy_{user['referral_code']}"))
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == '💸 درخواست برداشت')
def withdraw_request(message):
    user = db.get_user(message.from_user.id)
    min_w = int(db.get_setting('min_withdraw'))
    
    if user['wallet_balance'] < min_w:
        bot.send_message(message.chat.id, f"❌ موجودی کمتر از حداقل برداشت ({min_w:,} تومان)")
        return
    
    msg = bot.send_message(message.chat.id, "💳 شماره کارت (۱۶ رقم):")
    bot.register_next_step_handler(msg, process_withdraw_card, user)

def process_withdraw_card(message, user):
    card = message.text.strip().replace(' ', '')
    if len(card) != 16 or not card.isdigit():
        bot.reply_to(message, "❌ شماره کارت نامعتبر!")
        return
    
    msg = bot.send_message(message.chat.id, "👤 نام صاحب کارت:")
    bot.register_next_step_handler(msg, process_withdraw_holder, user, card)

def process_withdraw_holder(message, user, card):
    holder = message.text.strip()
    
    tracking_code = hashlib.md5(f"{user['user_id']}_{card}_{time.time()}".encode()).hexdigest()[:12].upper()
    
    db.execute('''
        INSERT INTO withdraw_requests (user_id, amount, card_number, card_holder, tracking_code, created_at, status)
        VALUES (?, ?, ?, ?, ?, ?, 'pending')
    ''', (user['user_id'], user['wallet_balance'], card, holder, tracking_code, datetime.now().isoformat()))
    
    db.execute('UPDATE users SET wallet_balance = 0 WHERE user_id = ?', (user['user_id'],))
    
    bot.reply_to(message, f"✅ درخواست برداشت {user['wallet_balance']:,} تومان ثبت شد!\n🔑 کد رهگیری: {tracking_code}")
    
    for admin_id in ADMIN_IDS:
        bot.send_message(admin_id, f"💰 درخواست برداشت\n👤 {user['first_name']}\n🆔 {user['user_id']}\n💰 {user['wallet_balance']:,} تومان")

@bot.message_handler(func=lambda m: m.text == '📦 کتابخانه‌ها')
def libraries_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("📚 لیست کتابخانه‌ها", callback_data="lib_list"))
    markup.add(types.InlineKeyboardButton("🔧 نصب دستی", callback_data="lib_manual"))
    markup.add(types.InlineKeyboardButton("✅ نصب شده‌ها", callback_data="lib_installed"))
    
    bot.send_message(message.chat.id, "📦 **مدیریت کتابخانه‌ها**", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "lib_list")
def lib_list(call):
    libs = library_manager.get_available()
    markup = types.InlineKeyboardMarkup(row_width=2)
    for cat in libs.keys():
        markup.add(types.InlineKeyboardButton(f"📁 {cat}", callback_data=f"lib_cat_{cat}"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="lib_back"))
    bot.edit_message_text("📚 دسته‌بندی:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lib_cat_'))
def lib_category(call):
    cat = call.data.replace('lib_cat_', '')
    libs = library_manager.get_available()
    if cat not in libs:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for name, lib in libs[cat].items():
        markup.add(types.InlineKeyboardButton(f"📦 {name}", callback_data=f"install_lib_{lib}"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="lib_list"))
    bot.edit_message_text(f"📁 {cat}:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('install_lib_'))
def install_lib(call):
    lib = call.data.replace('install_lib_', '')
    status_msg = bot.send_message(call.message.chat.id, f"🔄 در حال نصب {lib}...")
    library_manager.install(lib, call.message.chat.id, status_msg.message_id, bot)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "lib_manual")
def lib_manual(call):
    msg = bot.send_message(call.message.chat.id, "🔧 نام کتابخانه:")
    bot.register_next_step_handler(msg, process_manual_install)
    bot.answer_callback_query(call.id)

def process_manual_install(message):
    lib = message.text.strip()
    status_msg = bot.reply_to(message, f"🔄 در حال نصب {lib}...")
    library_manager.install(lib, message.chat.id, status_msg.message_id, bot)

@bot.callback_query_handler(func=lambda call: call.data == "lib_installed")
def lib_installed(call):
    libs = db.execute("SELECT name, version, installed_at FROM libraries ORDER BY installed_at DESC")
    if not libs:
        bot.edit_message_text("📦 کتابخانه‌ای نصب نشده!", call.message.chat.id, call.message.message_id)
        return
    
    text = "✅ **کتابخانه‌های نصب شده**\n\n"
    for lib in libs:
        text += f"• `{lib['name']}` - {lib['version']}\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="lib_back"))
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "lib_back")
def lib_back(call):
    libraries_menu(call.message)

@bot.message_handler(func=lambda m: m.text == '📚 راهنما')
def guide(message):
    text = """📚 **راهنمای ربات مادر**

**🎯 نحوه ساخت ربات:**
1️⃣ از دکمه `💰 خرید اشتراک` اشتراک خود را فعال کنید
2️⃣ پس از فعال‌سازی، از `🤖 ساخت ربات جدید` استفاده کنید
3️⃣ فایل `.py` یا `.zip` خود را ارسال کنید
4️⃣ توکن داخل کد باشد

**💰 قیمت اشتراک:** ۲,۰۰۰,۰۰۰ تومان
**📌 محدودیت:** هر کاربر حداکثر ۳ ربات

**▶️ اجرای ربات:**
- ربات‌ها پس از ساخت خودکار اجرا می‌شوند
- برای توقف از `🛑 توقف ربات` استفاده کنید

**📦 کتابخانه‌ها:**
- می‌توانید هر کتابخانه پایتونی نصب کنید

**👥 دعوت دوستان:**
- هر دعوت ۷٪ کمیسیون
- حداقل برداشت ۲ میلیون تومان

**🆘 پشتیبانی:** @shahraghee13"""
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '📊 آمار')
def stats(message):
    users = db.execute("SELECT COUNT(*) as c FROM users")[0]['c']
    active_subs = db.execute("SELECT COUNT(*) as c FROM users WHERE subscription_status = 'active'")[0]['c']
    bots = db.execute("SELECT COUNT(*) as c FROM bots")[0]['c']
    running = executor.get_stats()['active']
    total_wallet = db.execute("SELECT SUM(wallet_balance) as t FROM users")[0]['t'] or 0
    
    text = f"📊 **آمار سیستم**\n\n"
    text += f"👥 کاربران: {users}\n"
    text += f"✅ اشتراک فعال: {active_subs}\n"
    text += f"🤖 ربات‌ها: {bots}\n"
    text += f"🟢 در حال اجرا: {running}\n"
    text += f"💰 موجودی کل: {total_wallet:,} تومان\n"
    text += f"📌 حداکثر ربات: ۳"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '⚡ وضعیت اجرا')
def exec_status(message):
    user_id = message.from_user.id
    bots = db.execute("SELECT id, name FROM bots WHERE user_id = ?", (user_id,))
    
    if not bots:
        bot.send_message(message.chat.id, "📋 رباتی ندارید!")
        return
    
    text = "⚡ **وضعیت اجرا**\n\n"
    for b in bots:
        status = executor.get_status(b['id'])
        if status['running']:
            text += f"🟢 {b['name']}: {status['uptime']} ثانیه\n"
        else:
            text += f"🔴 {b['name']}: متوقف\n"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '📞 پشتیبانی')
def support(message):
    bot.send_message(message.chat.id, "📞 **پشتیبانی:** @shahraghee13", parse_mode='Markdown')

# ==================== پنل مدیریت حرفه‌ای ====================
@bot.message_handler(func=lambda m: m.text == '👑 پنل مدیریت')
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📸 فیش‌ها", callback_data="admin_receipts"),
        types.InlineKeyboardButton("💰 برداشت‌ها", callback_data="admin_withdraws"),
        types.InlineKeyboardButton("👥 کاربران", callback_data="admin_users"),
        types.InlineKeyboardButton("🤖 ربات‌ها", callback_data="admin_bots"),
        types.InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings"),
        types.InlineKeyboardButton("📊 گزارش", callback_data="admin_report"),
        types.InlineKeyboardButton("🖥️ وضعیت سرور", callback_data="admin_server"),
        types.InlineKeyboardButton("🎁 فعال‌سازی", callback_data="admin_activate"),
    )
    
    bot.send_message(message.chat.id, "👑 **پنل مدیریت حرفه‌ای**", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_receipts")
def admin_receipts(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    receipts = db.execute("SELECT * FROM receipts WHERE status = 'pending' ORDER BY created_at")
    
    if not receipts:
        bot.send_message(call.message.chat.id, "📸 فیشی وجود ندارد")
        return
    
    for r in receipts:
        user = db.get_user(r['user_id'])
        text = f"📸 فیش #{r['id']}\n👤 {user['first_name'] if user else 'نامشخص'}\n💰 {r['amount']:,} تومان\n🆔 {r['payment_code']}"
        
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
    receipt = db.execute("SELECT user_id FROM receipts WHERE id = ?", (rid,))
    
    if receipt:
        user_id = receipt[0]['user_id']
        db.execute("UPDATE receipts SET status = 'approved', reviewed_by = ?, reviewed_at = ? WHERE id = ?",
                  (call.from_user.id, datetime.now().isoformat(), rid))
        expiry = db.activate_subscription(user_id)
        
        bot.send_message(user_id, 
                        f"✅ **اشتراک شما فعال شد!**\n\n"
                        f"📅 تا تاریخ: {expiry.strftime('%Y-%m-%d')}\n"
                        f"🤖 می‌توانید حداکثر ۳ ربات بسازید!\n\n"
                        f"از دکمه `🤖 ساخت ربات جدید` استفاده کنید.")
        
        bot.answer_callback_query(call.id, "✅ اشتراک فعال شد!")
        bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_receipt_'))
def reject_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    rid = int(call.data.replace('reject_receipt_', ''))
    receipt = db.execute("SELECT user_id, payment_code FROM receipts WHERE id = ?", (rid,))
    
    if receipt:
        db.execute("UPDATE receipts SET status = 'rejected', reviewed_by = ?, reviewed_at = ? WHERE id = ?",
                  (call.from_user.id, datetime.now().isoformat(), rid))
        
        bot.send_message(receipt[0]['user_id'], 
                        f"❌ **فیش شما رد شد!**\n\n"
                        f"🆔 کد پیگیری: {receipt[0]['payment_code']}\n\n"
                        f"لطفاً با پشتیبانی تماس بگیرید: @shahraghee13")
        
        bot.answer_callback_query(call.id, "❌ رد شد!")
        bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_withdraws")
def admin_withdraws(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    withdraws = db.execute("SELECT * FROM withdraw_requests WHERE status = 'pending' ORDER BY created_at")
    
    if not withdraws:
        bot.send_message(call.message.chat.id, "💰 درخواستی وجود ندارد")
        return
    
    for w in withdraws:
        user = db.get_user(w['user_id'])
        text = f"💰 برداشت #{w['id']}\n👤 {user['first_name']}\n💰 {w['amount']:,} تومان\n💳 {w['card_number']}\n👤 {w['card_holder']}\n🔑 {w['tracking_code']}"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_wd_{w['id']}"))
        bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_wd_'))
def approve_withdraw(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    wid = int(call.data.replace('approve_wd_', ''))
    db.execute("UPDATE withdraw_requests SET status = 'approved', processed_at = ? WHERE id = ?",
              (datetime.now().isoformat(), wid))
    
    bot.answer_callback_query(call.id, "✅ تایید شد!")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_users")
def admin_users(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    users = db.execute("SELECT user_id, first_name, subscription_status, wallet_balance, bots_count, created_at FROM users ORDER BY created_at DESC LIMIT 30")
    
    text = "👥 **کاربران اخیر**\n\n"
    for u in users:
        status = "✅ فعال" if u['subscription_status'] == 'active' else "❌ غیرفعال"
        text += f"👤 {u['first_name']}\n🆔 {u['user_id']}\n📊 {status}\n💰 {u['wallet_balance']:,} تومان\n🤖 {u['bots_count']} ربات\n📅 {u['created_at'][:10]}\n\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "admin_bots")
def admin_bots(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    bots = db.execute("SELECT id, name, user_id, status, created_at FROM bots ORDER BY created_at DESC LIMIT 30")
    
    if not bots:
        bot.send_message(call.message.chat.id, "🤖 رباتی وجود ندارد")
        return
    
    text = "🤖 **لیست ربات‌ها**\n\n"
    for b in bots:
        status = executor.get_status(b['id'])
        status_text = "🟢 فعال" if status['running'] else "🔴 متوقف"
        text += f"**{b['name']}**\n👤 {b['user_id']}\n📊 {status_text}\n📅 {b['created_at'][:10]}\n\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "admin_settings")
def admin_settings(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("💰 قیمت اشتراک", callback_data="admin_set_price"),
        types.InlineKeyboardButton("💳 اطلاعات کارت", callback_data="admin_set_card"),
        types.InlineKeyboardButton("📌 حداکثر ربات", callback_data="admin_set_max_bots"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    text = f"⚙️ **تنظیمات فعلی**\n\n"
    text += f"💰 قیمت: {db.get_setting('subscription_price_str')}\n"
    text += f"💳 کارت: {db.get_setting('card_number_display')}\n"
    text += f"📌 حداکثر ربات: {db.get_setting('max_bots_per_user')}"
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_price")
def admin_set_price(call):
    msg = bot.send_message(call.message.chat.id, "💰 قیمت جدید (تومان):")
    bot.register_next_step_handler(msg, process_set_price)
    bot.answer_callback_query(call.id)

def process_set_price(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        price = int(message.text.strip())
        db.update_setting('subscription_price', str(price))
        db.update_setting('subscription_price_str', f"{price:,} تومان")
        bot.reply_to(message, f"✅ قیمت به {price:,} تومان تغییر کرد!")
    except:
        bot.reply_to(message, "❌ عدد معتبر وارد کنید!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_card")
def admin_set_card(call):
    msg = bot.send_message(call.message.chat.id, "💳 شماره کارت جدید:")
    bot.register_next_step_handler(msg, process_set_card)
    bot.answer_callback_query(call.id)

def process_set_card(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    card = message.text.strip().replace(' ', '')
    if len(card) == 16 and card.isdigit():
        db.update_setting('card_number', card)
        display = ' '.join([card[i:i+4] for i in range(0, 16, 4)])
        db.update_setting('card_number_display', display)
        bot.reply_to(message, f"✅ کارت به {display} تغییر کرد!")
    else:
        bot.reply_to(message, "❌ شماره کارت باید ۱۶ رقم باشد!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_max_bots")
def admin_set_max_bots(call):
    msg = bot.send_message(call.message.chat.id, "📌 حداکثر ربات هر کاربر (1-10):")
    bot.register_next_step_handler(msg, process_set_max_bots)
    bot.answer_callback_query(call.id)

def process_set_max_bots(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        val = int(message.text.strip())
        if 1 <= val <= 10:
            db.update_setting('max_bots_per_user', str(val))
            bot.reply_to(message, f"✅ حداکثر ربات به {val} تغییر کرد!")
        else:
            bot.reply_to(message, "❌ عدد بین 1 تا 10")
    except:
        bot.reply_to(message, "❌ عدد معتبر وارد کنید!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_report")
def admin_report(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    users = db.execute("SELECT COUNT(*) as c FROM users")[0]['c']
    active_subs = db.execute("SELECT COUNT(*) as c FROM users WHERE subscription_status = 'active'")[0]['c']
    bots = db.execute("SELECT COUNT(*) as c FROM bots")[0]['c']
    running = executor.get_stats()['active']
    total_wallet = db.execute("SELECT SUM(wallet_balance) as t FROM users")[0]['t'] or 0
    total_revenue = db.execute("SELECT SUM(amount) as t FROM receipts WHERE status = 'approved'")[0]['t'] or 0
    pending_receipts = db.execute("SELECT COUNT(*) as c FROM receipts WHERE status = 'pending'")[0]['c']
    pending_withdraws = db.execute("SELECT COUNT(*) as c FROM withdraw_requests WHERE status = 'pending'")[0]['c']
    
    cache_stats = db.cache.get_stats()
    
    text = f"📊 **گزارش کامل سیستم**\n\n"
    text += f"👥 کاربران: {users}\n"
    text += f"✅ اشتراک فعال: {active_subs}\n"
    text += f"🤖 ربات‌ها: {bots}\n"
    text += f"🟢 در حال اجرا: {running}\n\n"
    
    text += f"💰 **مالی:**\n"
    text += f"   کیف پول کل: {total_wallet:,} تومان\n"
    text += f"   درآمد کل: {total_revenue:,} تومان\n"
    text += f"   فیش‌های در انتظار: {pending_receipts}\n"
    text += f"   برداشت‌های در انتظار: {pending_withdraws}\n\n"
    
    text += f"⚡ **آمار کش:**\n"
    text += f"   حجم کش: {cache_stats['size']}\n"
    text += f"   نرخ بازدید: {cache_stats['hit_rate']}%\n\n"
    
    text += f"⚙️ **تنظیمات:**\n"
    text += f"   قیمت اشتراک: {db.get_setting('subscription_price_str')}\n"
    text += f"   حداکثر ربات: {db.get_setting('max_bots_per_user')}"
    
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "admin_server")
def admin_server(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    try:
        import psutil
        cpu = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        exec_stats = executor.get_stats()
        
        text = f"🖥️ **وضعیت سرور**\n\n"
        text += f"**CPU:** {cpu}%\n"
        text += f"**RAM:** {memory.used // (1024**3)} GB / {memory.total // (1024**3)} GB ({memory.percent}%)\n"
        text += f"**Disk:** {disk.used // (1024**3)} GB / {disk.total // (1024**3)} GB ({disk.percent}%)\n\n"
        text += f"**ربات‌ها:**\n"
        text += f"   در حال اجرا: {exec_stats['active']}/{exec_stats['max']}\n\n"
        text += f"**کش:**\n"
        text += f"   نرخ بازدید: {db.cache.get_stats()['hit_rate']}%"
        
        bot.send_message(call.message.chat.id, text, parse_mode='Markdown')
    except:
        bot.send_message(call.message.chat.id, "❌ نصب psutil برای آمار سرور لازم است!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_activate")
def admin_activate_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, "🎁 **آیدی کاربر را وارد کنید:**")
    bot.register_next_step_handler(msg, process_admin_activate)
    bot.answer_callback_query(call.id)

def process_admin_activate(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        user_id = int(message.text.strip())
        expiry = db.activate_subscription(user_id)
        bot.reply_to(message, f"✅ اشتراک {user_id} تا {expiry.strftime('%Y-%m-%d')} فعال شد!")
        bot.send_message(user_id, f"✅ اشتراک شما توسط ادمین فعال شد!\n📅 تا {expiry.strftime('%Y-%m-%d')}\nحالا می‌توانید ربات بسازید.")
    except:
        bot.reply_to(message, "❌ خطا!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    admin_panel(call.message)

# ==================== پیام همگانی ====================
@bot.message_handler(func=lambda m: m.text == '📢 پیام همگانی')
def broadcast_prompt(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(message.chat.id, "📢 **متن پیام:**")
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    text = message.text
    users = db.execute("SELECT user_id FROM users")
    sent = 0
    
    status_msg = bot.reply_to(message, f"🔄 در حال ارسال به {len(users)} کاربر...")
    
    for user in users:
        try:
            bot.send_message(user['user_id'], f"📢 **پیام همگانی**\n\n{text}", parse_mode='Markdown')
            sent += 1
            time.sleep(0.05)
        except:
            pass
    
    bot.edit_message_text(f"✅ به {sent} کاربر ارسال شد!", message.chat.id, status_msg.message_id)

# ==================== مانیتورینگ ====================
def monitor_system():
    while True:
        try:
            # به‌روزرسانی آمار روزانه
            today = datetime.now().date().isoformat()
            active_users = db.execute("SELECT COUNT(*) as c FROM users WHERE last_active >= datetime('now', '-1 day')")[0]['c']
            active_bots = executor.get_stats()['active']
            
            db.execute('''
                INSERT INTO daily_stats (date, active_users, active_bots) 
                VALUES (?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET 
                    active_users = ?, active_bots = ?
            ''', (today, active_users, active_bots, active_users, active_bots))
            
            time.sleep(3600)  # هر 1 ساعت
        except:
            time.sleep(60)

threading.Thread(target=monitor_system, daemon=True).start()

# ==================== اجرا ====================
if __name__ == "__main__":
    print("=" * 70)
    print("╔═════════════════════════════════════════════════════════════════════╗")
    print("║     🚀 ULTRA MOTHER BOT - ENTERPRISE EDITION v10.0                 ║")
    print("║     ⚡ High Performance - Isolated Execution - Advanced Caching    ║")
    print("║     💰 Commercial Version - Price: 2,000,000 Toman                 ║")
    print("╚═════════════════════════════════════════════════════════════════════╝")
    print("=" * 70)
    print(f"👑 ادمین: {ADMIN_IDS}")
    print(f"🤖 @{bot.get_me().username}")
    print(f"💰 قیمت اشتراک: {SUBSCRIPTION_PRICE_STR}")
    print(f"📌 حداکثر ربات: {MAX_BOTS_PER_USER}")
    print(f"⚡ کش: فعال (نرخ بازدید: {db.cache.get_stats()['hit_rate']}%)")
    print(f"🔒 ایزوله‌سازی: فعال (محدودیت CPU/RAM)")
    print("=" * 70)
    print("🔥 ربات با موفقیت راه‌اندازی شد!")
    print("=" * 70)
    
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=60)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)