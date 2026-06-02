#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║     🚀 ULTRA MOTHER BOT - ENTERPRISE EDITION v9.0                           ║
║     ⚡ Advanced Multi-Machine Architecture - High Performance               ║
║     💰 Professional Bot Management System                                   ║
╚═══════════════════════════════════════════════════════════════════════════════╝

نسخه نهایی - با تمام قابلیت‌های حرفه‌ای
- پنل مدیریت پیشرفته
- سیستم برداشت با کمیسیون ۷٪
- مدیریت ماشین‌های سخت‌افزاری
- کش و ایزوله‌سازی حرفه‌ای
- مدیریت پوشه و فایل
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
import tempfile
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from functools import wraps
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

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
    'ISOLATED': os.path.join(BASE_DIR, "isolated_envs"),
    'FOLDERS': os.path.join(BASE_DIR, "user_folders"),
    'BACKUPS': os.path.join(BASE_DIR, "backups"),
}

for dir_path in DIRS.values():
    os.makedirs(dir_path, exist_ok=True)

# ==================== توکن ربات مادر ====================
BOT_TOKEN = "7685135237:AAEmsHktRw9cEqrHTkCoPZk-fBimK7TDjOo"
ADMIN_IDS = [327855654]
BOT_USERNAME = "ROBTTSAZE_bot"

# ==================== تنظیمات مالی ====================
SUBSCRIPTION_PRICE = 2000000  # 2 میلیون تومان
SUBSCRIPTION_PRICE_STR = "۲,۰۰۰,۰۰۰ تومان"
CARD_NUMBER = "5892101187322777"
CARD_NUMBER_DISPLAY = "5892 1011 8732 2777"
CARD_HOLDER = "مرتضی نیکخو خنجری"
CARD_BANK = "بانک ملی"
WITHDRAW_PERCENT = 7  # 7 درصد کمیسیون
MIN_WITHDRAW = 2000000  # حداقل برداشت 2 میلیون

# ==================== تنظیمات سخت‌افزاری ====================
MAX_BOTS_PER_USER = 3
MAX_CONCURRENT_EXECUTIONS = 100
CACHE_TTL = 3600

# تنظیمات ایزوله‌سازی
ISOLATION_SETTINGS = {
    'max_memory_mb': 256,  # حداکثر حافظه 256 مگابایت
    'max_cpu_percent': 50,  # حداکثر مصرف CPU 50%
    'max_processes': 10,    # حداکثر تعداد پروسس
    'max_files': 100,       # حداکثر تعداد فایل
}

# تنظیمات ماشین‌ها
MACHINES = {
    1: {'name': 'Machine-001', 'status': 'active', 'max_bots': 5000, 'current_bots': 0, 'ip': '127.0.0.1', 'port': 8000},
    2: {'name': 'Machine-002', 'status': 'active', 'max_bots': 5000, 'current_bots': 0, 'ip': '127.0.0.2', 'port': 8001},
    3: {'name': 'Machine-003', 'status': 'active', 'max_bots': 5000, 'current_bots': 0, 'ip': '127.0.0.3', 'port': 8002},
}

# ==================== دیتابیس پیشرفته ====================
DB_PATH = os.path.join(DIRS['DB'], 'mother_bot.db')

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-500000")
    return conn

# ایجاد جداول
with get_db() as conn:
    # جدول کاربران
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            phone TEXT,
            balance INTEGER DEFAULT 0,
            bots_count INTEGER DEFAULT 0,
            max_bots INTEGER DEFAULT 3,
            referral_code TEXT UNIQUE,
            referred_by INTEGER,
            referrals_count INTEGER DEFAULT 0,
            verified_referrals INTEGER DEFAULT 0,
            subscription_status TEXT DEFAULT 'inactive',
            subscription_expiry TIMESTAMP,
            payment_status TEXT DEFAULT 'pending',
            payment_date TIMESTAMP,
            is_banned INTEGER DEFAULT 0,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP,
            last_active TIMESTAMP,
            total_executions INTEGER DEFAULT 0,
            total_builds INTEGER DEFAULT 0
        )
    ''')
    
    # جدول ربات‌ها
    conn.execute('''
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
    
    # جدول پوشه‌ها
    conn.execute('''
        CREATE TABLE IF NOT EXISTS folders (
            id TEXT PRIMARY KEY,
            user_id INTEGER,
            folder_name TEXT,
            folder_path TEXT,
            parent_id TEXT,
            created_at TIMESTAMP,
            file_count INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    ''')
    
    # جدول فایل‌های پوشه
    conn.execute('''
        CREATE TABLE IF NOT EXISTS folder_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folder_id TEXT,
            file_name TEXT,
            file_path TEXT,
            file_size INTEGER,
            added_at TIMESTAMP,
            FOREIGN KEY(folder_id) REFERENCES folders(id) ON DELETE CASCADE
        )
    ''')
    
    # جدول ماشین‌ها
    conn.execute('''
        CREATE TABLE IF NOT EXISTS machines (
            id INTEGER PRIMARY KEY,
            name TEXT,
            status TEXT DEFAULT 'active',
            max_bots INTEGER DEFAULT 5000,
            current_bots INTEGER DEFAULT 0,
            ip TEXT,
            port INTEGER,
            last_heartbeat TIMESTAMP,
            created_at TIMESTAMP
        )
    ''')
    
    # جدول اجراها
    conn.execute('''
        CREATE TABLE IF NOT EXISTS executions (
            id TEXT PRIMARY KEY,
            user_id INTEGER,
            bot_id TEXT,
            machine_id INTEGER,
            status TEXT,
            started_at TIMESTAMP,
            ended_at TIMESTAMP,
            duration INTEGER,
            memory_used INTEGER,
            cpu_used REAL,
            FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    ''')
    
    # جدول فیش‌ها
    conn.execute('''
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            receipt_path TEXT,
            status TEXT DEFAULT 'pending',
            payment_code TEXT UNIQUE,
            created_at TIMESTAMP,
            reviewed_at TIMESTAMP,
            reviewed_by INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')
    
    # جدول درخواست‌های برداشت
    conn.execute('''
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
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')
    
    # جدول کتابخانه‌ها
    conn.execute('''
        CREATE TABLE IF NOT EXISTS libraries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            version TEXT,
            installed_at TIMESTAMP
        )
    ''')
    
    # جدول تنظیمات
    conn.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP
        )
    ''')
    
    # جدول آمار روزانه
    conn.execute('''
        CREATE TABLE IF NOT EXISTS daily_stats (
            date TEXT PRIMARY KEY,
            new_users INTEGER DEFAULT 0,
            active_users INTEGER DEFAULT 0,
            new_bots INTEGER DEFAULT 0,
            active_bots INTEGER DEFAULT 0,
            new_subscriptions INTEGER DEFAULT 0,
            total_revenue INTEGER DEFAULT 0,
            total_withdraw INTEGER DEFAULT 0
        )
    ''')
    
    # جدول خطاهای سیستم
    conn.execute('''
        CREATE TABLE IF NOT EXISTS system_errors (
            id TEXT PRIMARY KEY,
            type TEXT,
            message TEXT,
            user_id INTEGER,
            timestamp TIMESTAMP,
            resolved INTEGER DEFAULT 0
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
        'max_concurrent_executions': str(MAX_CONCURRENT_EXECUTIONS),
        'isolation_memory_mb': str(ISOLATION_SETTINGS['max_memory_mb']),
        'isolation_cpu_percent': str(ISOLATION_SETTINGS['max_cpu_percent']),
    }
    
    for key, value in default_settings.items():
        conn.execute("INSERT OR IGNORE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
                    (key, value, datetime.now().isoformat()))
    
    # اضافه کردن ماشین‌ها
    for mid, machine in MACHINES.items():
        conn.execute('''
            INSERT OR IGNORE INTO machines (id, name, status, max_bots, current_bots, ip, port, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (mid, machine['name'], machine['status'], machine['max_bots'], 
              machine['current_bots'], machine['ip'], machine['port'], datetime.now().isoformat()))
    
    conn.commit()

# ==================== سیستم کش پیشرفته ====================
class AdvancedCache:
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
                            self.cache.pop(k, None)
                            self.ttl.pop(k, None)
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
                    self.cache.pop(key, None)
                    self.ttl.pop(key, None)
            self.misses += 1
            return None
    
    def set(self, key, value, ttl=CACHE_TTL):
        with self.lock:
            if len(self.cache) >= self.max_size:
                oldest = min(self.ttl.items(), key=lambda x: x[1])[0]
                self.cache.pop(oldest, None)
                self.ttl.pop(oldest, None)
            self.cache[key] = value
            self.ttl[key] = time.time() + ttl
    
    def delete(self, key):
        with self.lock:
            self.cache.pop(key, None)
            self.ttl.pop(key, None)
    
    def clear(self):
        with self.lock:
            self.cache.clear()
            self.ttl.clear()
    
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

cache = AdvancedCache()

# ==================== موتور اجرای ایزوله ====================
class IsolatedExecutionEngine:
    def __init__(self):
        self.active_processes = {}
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_EXECUTIONS)
        self._start_monitor()
    
    def _start_monitor(self):
        def monitor():
            while True:
                try:
                    with self.lock:
                        for bot_id, info in list(self.active_processes.items()):
                            if info.get('process') and info['process'].poll() is not None:
                                del self.active_processes[bot_id]
                    time.sleep(10)
                except:
                    time.sleep(30)
        threading.Thread(target=monitor, daemon=True).start()
    
    def _create_isolated_env(self, bot_id):
        env_dir = os.path.join(DIRS['ISOLATED'], bot_id)
        os.makedirs(env_dir, exist_ok=True)
        
        # ایجاد فایل محدودیت‌ها
        limits_file = os.path.join(env_dir, 'limits.py')
        with open(limits_file, 'w', encoding='utf-8') as f:
            f.write(f'''
import resource
import signal
import sys
import os

# محدودیت‌های سخت‌افزاری
try:
    # محدودیت حافظه
    resource.setrlimit(resource.RLIMIT_AS, ({ISOLATION_SETTINGS['max_memory_mb'] * 1024 * 1024}, 
                                            {ISOLATION_SETTINGS['max_memory_mb'] * 1024 * 1024}))
    # محدودیت CPU
    resource.setrlimit(resource.RLIMIT_CPU, (300, 300))
    # محدودیت تعداد فایل
    resource.setrlimit(resource.RLIMIT_NOFILE, ({ISOLATION_SETTINGS['max_files']}, {ISOLATION_SETTINGS['max_files']}))
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
        exec_id = str(uuid.uuid4())[:8]
        env_dir = self._create_isolated_env(bot_id)
        
        # ذخیره کد
        code_path = os.path.join(env_dir, 'bot.py')
        with open(code_path, 'w', encoding='utf-8') as f:
            f.write(code)
        
        cwd = folder_path if folder_path and os.path.exists(folder_path) else env_dir
        
        try:
            process = subprocess.Popen(
                [sys.executable, code_path],
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )
            
            with self.lock:
                self.active_processes[bot_id] = {
                    'process': process,
                    'pid': process.pid,
                    'started_at': time.time(),
                    'user_id': user_id
                }
            
            return exec_id, True, None
        except Exception as e:
            return exec_id, False, str(e)
    
    def stop_bot(self, bot_id):
        with self.lock:
            if bot_id in self.active_processes:
                try:
                    process = self.active_processes[bot_id]['process']
                    process.terminate()
                    time.sleep(1)
                    if process.poll() is None:
                        process.kill()
                    del self.active_processes[bot_id]
                    return True
                except:
                    pass
        return False
    
    def get_status(self, bot_id):
        with self.lock:
            if bot_id in self.active_processes:
                process = self.active_processes[bot_id]['process']
                if process.poll() is None:
                    uptime = int(time.time() - self.active_processes[bot_id]['started_at'])
                    return {'running': True, 'uptime': uptime}
        return {'running': False}
    
    def get_stats(self):
        with self.lock:
            return {
                'active': len(self.active_processes),
                'max': MAX_CONCURRENT_EXECUTIONS
            }

engine = IsolatedExecutionEngine()

# ==================== مدیریت ماشین‌ها ====================
class MachineManager:
    def __init__(self):
        self.machines = {}
        self._load_machines()
    
    def _load_machines(self):
        with get_db() as conn:
            machines = conn.execute("SELECT * FROM machines").fetchall()
            for m in machines:
                self.machines[m['id']] = dict(m)
    
    def get_available_machine(self):
        for mid, machine in self.machines.items():
            if machine['status'] == 'active' and machine['current_bots'] < machine['max_bots']:
                return mid
        return None
    
    def add_machine(self, name, ip, port, max_bots=5000):
        with get_db() as conn:
            mid = len(self.machines) + 1
            conn.execute('''
                INSERT INTO machines (id, name, status, max_bots, current_bots, ip, port, created_at)
                VALUES (?, ?, 'active', ?, 0, ?, ?, ?)
            ''', (mid, name, max_bots, ip, port, datetime.now().isoformat()))
            conn.commit()
        self._load_machines()
        return mid
    
    def assign_bot(self, bot_id, machine_id):
        with get_db() as conn:
            conn.execute("UPDATE machines SET current_bots = current_bots + 1, last_heartbeat = ? WHERE id = ?",
                        (datetime.now().isoformat(), machine_id))
            conn.execute("UPDATE bots SET machine_id = ? WHERE id = ?", (machine_id, bot_id))
            conn.commit()
    
    def release_bot(self, bot_id):
        with get_db() as conn:
            conn.execute("UPDATE machines SET current_bots = current_bots - 1 WHERE id = (SELECT machine_id FROM bots WHERE id = ?)", (bot_id,))
            conn.execute("UPDATE bots SET machine_id = NULL WHERE id = ?", (bot_id,))
            conn.commit()
    
    def get_stats(self):
        total_bots = sum(m['current_bots'] for m in self.machines.values())
        total_capacity = sum(m['max_bots'] for m in self.machines.values())
        return {
            'total_machines': len(self.machines),
            'total_bots': total_bots,
            'total_capacity': total_capacity,
            'available': total_capacity - total_bots,
            'usage_percent': (total_bots / total_capacity * 100) if total_capacity > 0 else 0
        }

machine_manager = MachineManager()

# ==================== مدیریت پوشه‌ها ====================
class FolderManager:
    def create_folder(self, user_id, folder_name, parent_id=None):
        folder_path = os.path.join(DIRS['FOLDERS'], str(user_id), folder_name)
        if parent_id:
            with get_db() as conn:
                parent = conn.execute("SELECT folder_path FROM folders WHERE id = ?", (parent_id,)).fetchone()
                if parent:
                    folder_path = os.path.join(parent['folder_path'], folder_name)
        
        if os.path.exists(folder_path):
            return None, "پوشه وجود دارد"
        
        os.makedirs(folder_path, exist_ok=True)
        folder_id = hashlib.md5(f"{user_id}_{folder_name}_{time.time()}".encode()).hexdigest()[:12]
        
        with get_db() as conn:
            conn.execute('''
                INSERT INTO folders (id, user_id, folder_name, folder_path, parent_id, created_at, file_count)
                VALUES (?, ?, ?, ?, ?, ?, 0)
            ''', (folder_id, user_id, folder_name, folder_path, parent_id, datetime.now().isoformat()))
            conn.commit()
        
        return folder_id, "پوشه ساخته شد"
    
    def add_file(self, folder_id, file_name, content):
        with get_db() as conn:
            folder = conn.execute("SELECT folder_path FROM folders WHERE id = ?", (folder_id,)).fetchone()
            if not folder:
                return False, "پوشه یافت نشد"
            
            file_path = os.path.join(folder['folder_path'], file_name)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            conn.execute('''
                INSERT INTO folder_files (folder_id, file_name, file_path, file_size, added_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (folder_id, file_name, file_path, len(content), datetime.now().isoformat()))
            
            conn.execute("UPDATE folders SET file_count = file_count + 1 WHERE id = ?", (folder_id,))
            conn.commit()
            return True, "فایل اضافه شد"
    
    def get_files(self, folder_id):
        with get_db() as conn:
            files = conn.execute("SELECT file_name, file_size, added_at FROM folder_files WHERE folder_id = ?", (folder_id,)).fetchall()
            return [dict(f) for f in files]
    
    def read_file(self, folder_id, file_name):
        with get_db() as conn:
            file_info = conn.execute("SELECT file_path FROM folder_files WHERE folder_id = ? AND file_name = ?", (folder_id, file_name)).fetchone()
            if file_info and os.path.exists(file_info['file_path']):
                with open(file_info['file_path'], 'r', encoding='utf-8') as f:
                    return f.read()
        return None
    
    def delete_file(self, folder_id, file_name):
        with get_db() as conn:
            file_info = conn.execute("SELECT file_path FROM folder_files WHERE folder_id = ? AND file_name = ?", (folder_id, file_name)).fetchone()
            if file_info and os.path.exists(file_info['file_path']):
                os.remove(file_info['file_path'])
            conn.execute("DELETE FROM folder_files WHERE folder_id = ? AND file_name = ?", (folder_id, file_name))
            conn.execute("UPDATE folders SET file_count = file_count - 1 WHERE id = ?", (folder_id,))
            conn.commit()
            return True
        return False

folder_manager = FolderManager()

# ==================== کتابخانه منیجر ====================
class LibraryManager:
    def __init__(self):
        self.installing = set()
        self.common_libs = {
            'requests': 'requests',
            'numpy': 'numpy',
            'pandas': 'pandas',
            'flask': 'flask',
            'django': 'django',
            'pillow': 'Pillow',
            'beautifulsoup4': 'beautifulsoup4',
            'selenium': 'selenium',
            'pyTelegramBotAPI': 'pyTelegramBotAPI',
            'aiogram': 'aiogram',
            'aiohttp': 'aiohttp',
            'fastapi': 'fastapi',
            'jdatetime': 'jdatetime',
            'cryptography': 'cryptography',
            'loguru': 'loguru'
        }
    
    def install(self, lib_name, chat_id, message_id=None):
        if lib_name in self.installing:
            return False
        
        self.installing.add(lib_name)
        
        def install_thread():
            try:
                msg = bot.send_message(chat_id, f"🔄 در حال نصب {lib_name}...")
                
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", lib_name, "--quiet"],
                    capture_output=True,
                    text=True,
                    timeout=180
                )
                
                if result.returncode == 0:
                    version = subprocess.run([sys.executable, "-m", "pip", "show", lib_name],
                                            capture_output=True, text=True, timeout=10)
                    ver = "نامشخص"
                    for line in version.stdout.split('\n'):
                        if line.startswith('Version:'):
                            ver = line.split(':', 1)[1].strip()
                            break
                    
                    with get_db() as conn:
                        conn.execute("INSERT OR IGNORE INTO libraries (name, version, installed_at) VALUES (?, ?, ?)",
                                    (lib_name, ver, datetime.now().isoformat()))
                        conn.commit()
                    
                    bot.edit_message_text(f"✅ {lib_name} نسخه {ver} نصب شد!", chat_id, msg.message_id)
                else:
                    error = result.stderr[:200] if result.stderr else "خطا"
                    bot.edit_message_text(f"❌ خطا: {error}", chat_id, msg.message_id)
            except subprocess.TimeoutExpired:
                bot.send_message(chat_id, f"❌ زمان نصب {lib_name} تمام شد!")
            except Exception as e:
                bot.send_message(chat_id, f"❌ خطا: {str(e)}")
            finally:
                self.installing.discard(lib_name)
        
        threading.Thread(target=install_thread, daemon=True).start()
        return True

library_manager = LibraryManager()

# ==================== ربات اصلی ====================
bot = telebot.TeleBot(BOT_TOKEN)
bot.remove_webhook()

# ==================== توابع کمکی ====================
def get_setting(key):
    cached = cache.get(f"setting_{key}")
    if cached:
        return cached
    with get_db() as conn:
        result = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        if result:
            value = result['value']
            cache.set(f"setting_{key}", value, 3600)
            return value
    return None

def get_user(user_id):
    cached = cache.get(f"user_{user_id}")
    if cached:
        return cached
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if user:
            user_dict = dict(user)
            cache.set(f"user_{user_id}", user_dict, 300)
            return user_dict
    return None

def create_user(user_id, username, first_name, last_name, referred_by=None):
    now = datetime.now().isoformat()
    referral_code = hashlib.md5(f"{user_id}_{time.time()}_{secrets.token_hex(4)}".encode()).hexdigest()[:12]
    
    with get_db() as conn:
        conn.execute('''
            INSERT OR IGNORE INTO users 
            (user_id, username, first_name, last_name, referral_code, referred_by, created_at, last_active, subscription_status, payment_status, max_bots)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'inactive', 'pending', ?)
        ''', (user_id, username, first_name, last_name, referral_code, referred_by, now, now, MAX_BOTS_PER_USER))
        conn.commit()
        
        if referred_by and referred_by != user_id:
            conn.execute("UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = ?", (referred_by,))
            conn.commit()
    
    cache.delete(f"user_{user_id}")
    return True

def check_subscription(user_id):
    user = get_user(user_id)
    if not user:
        return False
    if user['subscription_status'] == 'active':
        if user['subscription_expiry']:
            expiry = datetime.fromisoformat(user['subscription_expiry'])
            if expiry > datetime.now():
                return True
    return False

def activate_subscription(user_id):
    expiry = datetime.now() + timedelta(days=30)
    with get_db() as conn:
        conn.execute('''
            UPDATE users SET subscription_status = 'active', subscription_expiry = ?, payment_status = 'approved', payment_date = ?
            WHERE user_id = ?
        ''', (expiry.isoformat(), datetime.now().isoformat(), user_id))
        conn.commit()
    
    cache.delete(f"user_{user_id}")
    return expiry

def add_wallet_balance(user_id, amount):
    with get_db() as conn:
        conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
    cache.delete(f"user_{user_id}")

def get_user_bots_count(user_id):
    with get_db() as conn:
        result = conn.execute("SELECT COUNT(*) as c FROM bots WHERE user_id = ?", (user_id,)).fetchone()
        return result['c'] if result else 0

def can_create_bot(user_id):
    max_bots = int(get_setting('max_bots_per_user') or 3)
    current_bots = get_user_bots_count(user_id)
    return current_bots < max_bots, max_bots, current_bots

def extract_token_from_code(code):
    patterns = [
        r'token\s*=\s*["\']([^"\']+)["\']',
        r'TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'BOT_TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'API_TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'bot\s*=\s*telebot\.TeleBot\(\s*["\']([^"\']+)["\']\s*\)'
    ]
    for pattern in patterns:
        match = re.search(pattern, code, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

def verify_token(token):
    try:
        resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        if resp.status_code == 200:
            return True, resp.json().get('result', {})
        return False, {}
    except:
        return False, {}

def log_error(error_type, message, user_id=None):
    error_id = hashlib.md5(f"{time.time()}_{user_id}_{secrets.token_hex(4)}".encode()).hexdigest()[:12]
    with get_db() as conn:
        conn.execute('''
            INSERT INTO system_errors (id, type, message, user_id, timestamp, resolved)
            VALUES (?, ?, ?, ?, ?, 0)
        ''', (error_id, error_type, message[:500], user_id, datetime.now().isoformat()))
        conn.commit()

# ==================== منوی اصلی ====================
def get_main_menu(user_id):
    is_admin = user_id in ADMIN_IDS
    has_subscription = check_subscription(user_id)
    
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    
    if has_subscription:
        buttons = [
            types.KeyboardButton('🤖 ساخت ربات جدید'),
            types.KeyboardButton('📁 مدیریت پوشه'),
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
        with get_db() as conn:
            referrer = conn.execute("SELECT user_id FROM users WHERE referral_code = ?", (code,)).fetchone()
            if referrer and referrer['user_id'] != user_id:
                referred_by = referrer['user_id']
                try:
                    bot.send_message(referred_by, f"🎉 {first_name} با لینک شما وارد شد!")
                except:
                    pass
    
    create_user(user_id, username, first_name, message.from_user.last_name or "", referred_by)
    user = get_user(user_id)
    bot_username = bot.get_me().username
    referral_link = f"https://t.me/{bot_username}?start={user['referral_code']}"
    
    has_subscription = check_subscription(user_id)
    
    text = f"""🚀 **به ربات مادر خوش آمدید {first_name}**!

👤 شناسه: `{user_id}`
🎁 کد معرف: `{user['referral_code']}`
🔗 لینک دعوت: {referral_link}
💰 موجودی: {user['balance']:,} تومان

"""
    if has_subscription:
        expiry = datetime.fromisoformat(user['subscription_expiry'])
        text += f"✅ اشتراک فعال تا: {expiry.strftime('%Y-%m-%d')}\n"
        text += f"🤖 ربات ساخته شده: {get_user_bots_count(user_id)}/{get_setting('max_bots_per_user')}"
    else:
        text += f"❌ **اشتراک شما فعال نیست!**\n"
        text += f"💰 قیمت اشتراک: {get_setting('subscription_price_str')}\n\n"
        text += "برای فعال‌سازی از دکمه `💰 خرید اشتراک` استفاده کنید."
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📋 کپی لینک", callback_data=f"copy_{user['referral_code']}"))
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)
    bot.send_message(message.chat.id, "🚀 منوی اصلی:", reply_markup=get_main_menu(user_id))

@bot.callback_query_handler(func=lambda call: call.data.startswith('copy_'))
def copy_link(call):
    code = call.data.replace('copy_', '')
    link = f"https://t.me/{bot.get_me().username}?start={code}"
    bot.answer_callback_query(call.id, f"✅ لینک کپی شد!\n{link}", show_alert=True)

# ==================== خرید اشتراک ====================
@bot.message_handler(func=lambda m: m.text == '💰 خرید اشتراک')
def buy_subscription(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if check_subscription(user_id):
        bot.send_message(message.chat.id, "✅ شما قبلاً اشتراک فعال دارید!")
        return
    
    price = get_setting('subscription_price_str')
    card = get_setting('card_number_display')
    holder = get_setting('card_holder')
    bank = get_setting('card_bank')
    
    text = f"""
💳 **خرید اشتراک ماهیانه**

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

⚠️ **توجه:** پس از فعال‌سازی، می‌توانید تا {get_setting('max_bots_per_user')} ربات بسازید!
"""
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== فیش پرداخت ====================
@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    
    with get_db() as conn:
        pending = conn.execute("SELECT id FROM receipts WHERE user_id = ? AND status = 'pending'", (user_id,)).fetchone()
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
        
        with get_db() as conn:
            conn.execute('''
                INSERT INTO receipts (user_id, amount, receipt_path, payment_code, created_at, status)
                VALUES (?, ?, ?, ?, ?, 'pending')
            ''', (user_id, SUBSCRIPTION_PRICE, receipt_path, payment_code, datetime.now().isoformat()))
            conn.commit()
        
        bot.reply_to(message, 
                    f"✅ **فیش شما دریافت شد!**\n\n"
                    f"💰 مبلغ: {SUBSCRIPTION_PRICE_STR}\n"
                    f"🆔 کد پیگیری: `{payment_code}`\n\n"
                    f"⏱ ظرف ۲۴ ساعت بررسی می‌شود.")
        
        for admin_id in ADMIN_IDS:
            try:
                with open(receipt_path, 'rb') as f:
                    bot.send_photo(admin_id, f, caption=f"📸 فیش جدید\n👤 {user_id}\n💰 {SUBSCRIPTION_PRICE_STR}")
            except:
                pass
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")
        log_error('receipt_error', str(e), user_id)

# ==================== ساخت ربات جدید ====================
@bot.message_handler(func=lambda m: m.text == '🤖 ساخت ربات جدید')
def new_bot(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or ""
    
    if not check_subscription(user_id):
        text = f"""🌟 **ساخت ربات جدید**

کاربر گرامی {first_name}

❌ **اشتراک شما فعال نیست!**

💰 قیمت اشتراک: {get_setting('subscription_price_str')}

📌 **برای ساخت ربات، ابتدا:**
1️⃣ از دکمه `💰 خرید اشتراک` استفاده کنید
2️⃣ مبلغ را واریز کنید
3️⃣ رسید را ارسال کنید
4️⃣ پس از تایید، اشتراک شما فعال می‌شود

⚠️ **توجه:** هر کاربر می‌تواند حداکثر {get_setting('max_bots_per_user')} ربات داشته باشد!"""
        
        bot.send_message(message.chat.id, text, parse_mode='Markdown')
        return
    
    can_create, max_bots, current_bots = can_create_bot(user_id)
    if not can_create:
        bot.send_message(message.chat.id, 
                        f"⚠️ **شما به حداکثر مجاز {max_bots} ربات رسیده‌اید!**\n\n"
                        f"برای ساخت ربات جدید، ابتدا یکی از ربات‌های خود را حذف کنید.",
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
    
    if not check_subscription(user_id):
        bot.reply_to(message, "❌ اشتراک فعال نیست!", parse_mode='Markdown')
        return
    
    if not (file_name.endswith('.py') or file_name.endswith('.zip')):
        bot.reply_to(message, "❌ فقط فایل‌های `.py` یا `.zip` مجاز هستند!")
        return
    
    if message.document.file_size > 50 * 1024 * 1024:
        bot.reply_to(message, "❌ حجم بیشتر از ۵۰ مگابایت!")
        return
    
    can_create, max_bots, current_bots = can_create_bot(user_id)
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
        
        token = extract_token_from_code(code)
        if not token:
            bot.edit_message_text("❌ توکن در کد پیدا نشد!", message.chat.id, status_msg.message_id)
            return
        
        valid, bot_info = verify_token(token)
        if not valid:
            bot.edit_message_text("❌ توکن نامعتبر است!", message.chat.id, status_msg.message_id)
            return
        
        # پیدا کردن ماشین مناسب
        machine_id = machine_manager.get_available_machine()
        if not machine_id:
            bot.edit_message_text("❌ همه سرورها پر هستند! لطفاً بعداً تلاش کنید.", message.chat.id, status_msg.message_id)
            return
        
        # ایجاد ربات
        bot_id = hashlib.md5(f"{user_id}{token}{time.time()}".encode()).hexdigest()[:12]
        
        with get_db() as conn:
            conn.execute('''
                INSERT INTO bots (id, user_id, token, name, username, file_path, status, created_at, last_active, execution_count)
                VALUES (?, ?, ?, ?, ?, ?, 'stopped', ?, ?, 0)
            ''', (bot_id, user_id, token, bot_info['first_name'], bot_info['username'], file_path, 
                  datetime.now().isoformat(), datetime.now().isoformat()))
            
            conn.execute("UPDATE users SET bots_count = bots_count + 1, total_builds = total_builds + 1 WHERE user_id = ?", (user_id,))
            conn.commit()
        
        machine_manager.assign_bot(bot_id, machine_id)
        
        # اجرا
        exec_id, success, error = engine.execute_bot(bot_id, user_id, code)
        
        if success:
            with get_db() as conn:
                conn.execute("UPDATE bots SET status = 'running' WHERE id = ?", (bot_id,))
                conn.commit()
            
            # اضافه کردن کمیسیون به معرف (7 درصد)
            user = get_user(user_id)
            if user and user.get('referred_by'):
                commission = int(SUBSCRIPTION_PRICE * WITHDRAW_PERCENT / 100)
                add_wallet_balance(user['referred_by'], commission)
                try:
                    bot.send_message(user['referred_by'], 
                                   f"🎉 **کمیسیون دعوت!**\n\n"
                                   f"کاربر {user['first_name']} اشتراک خرید.\n"
                                   f"💰 مبلغ کمیسیون: {commission:,} تومان\n"
                                   f"🙏 سپاس از شما!")
                except:
                    pass
            
            reply = f"✅ **ربات ساخته شد!** 🎉\n\n"
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
        log_error('build_error', str(e), user_id)

# ==================== مدیریت پوشه ====================
@bot.message_handler(func=lambda m: m.text == '📁 مدیریت پوشه')
def manage_folders(message):
    user_id = message.from_user.id
    
    if not check_subscription(user_id):
        bot.send_message(message.chat.id, "❌ ابتدا اشتراک خود را فعال کنید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📁➕ ساخت پوشه جدید", callback_data="create_folder"),
        types.InlineKeyboardButton("📂 لیست پوشه‌ها", callback_data="list_folders")
    )
    
    bot.send_message(message.chat.id, "📁 **مدیریت پوشه‌ها**\n\nمی‌توانید فایل‌های خود را در پوشه‌ها سازماندهی کنید.", 
                    parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "create_folder")
def create_folder_prompt(call):
    msg = bot.send_message(call.message.chat.id, "📁 **نام پوشه:**\n(فقط حروف انگلیسی)")
    bot.register_next_step_handler(msg, process_create_folder)
    bot.answer_callback_query(call.id)

def process_create_folder(message):
    user_id = message.from_user.id
    name = message.text.strip()
    
    if not re.match(r'^[a-zA-Z0-9_\-]+$', name):
        bot.reply_to(message, "❌ نام نامعتبر!")
        return
    
    folder_id, result = folder_manager.create_folder(user_id, name)
    if folder_id:
        bot.reply_to(message, f"✅ {result}\n🆔 `{folder_id}`", parse_mode='Markdown')
    else:
        bot.reply_to(message, f"❌ {result}")

@bot.callback_query_handler(func=lambda call: call.data == "list_folders")
def list_folders(call):
    user_id = call.from_user.id
    
    with get_db() as conn:
        folders = conn.execute("SELECT id, folder_name, file_count FROM folders WHERE user_id = ?", (user_id,)).fetchall()
    
    if not folders:
        bot.send_message(call.message.chat.id, "📂 پوشه‌ای ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for f in folders:
        markup.add(types.InlineKeyboardButton(f"📂 {f['folder_name']} ({f['file_count']} فایل)", 
                                             callback_data=f"view_folder_{f['id']}"))
    
    bot.edit_message_text("📂 **پوشه‌های شما:**", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('view_folder_'))
def view_folder(call):
    folder_id = call.data.replace('view_folder_', '')
    files = folder_manager.get_files(folder_id)
    
    with get_db() as conn:
        folder = conn.execute("SELECT folder_name FROM folders WHERE id = ?", (folder_id,)).fetchone()
    
    if not folder:
        bot.answer_callback_query(call.id, "پوشه یافت نشد!")
        return
    
    text = f"📁 **{folder['folder_name']}**\n🆔 `{folder_id}`\n📄 فایل‌ها: {len(files)}\n\n"
    
    if files:
        text += "**📄 فایل‌ها:**\n"
        for f in files:
            text += f"• `{f['file_name']}` ({f['file_size']} بایت)\n"
    else:
        text += "📂 فایلی وجود ندارد"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("📄 افزودن فایل", callback_data=f"add_file_{folder_id}"))
    markup.add(types.InlineKeyboardButton("▶️ اجرا", callback_data=f"run_folder_{folder_id}"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="list_folders"))
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('add_file_'))
def add_file_prompt(call):
    folder_id = call.data.replace('add_file_', '')
    msg = bot.send_message(call.message.chat.id, "📄 **نام فایل:**\n(مثال: main.py)")
    bot.register_next_step_handler(msg, process_add_file_name, folder_id)
    bot.answer_callback_query(call.id)

def process_add_file_name(message, folder_id):
    file_name = message.text.strip()
    if not file_name.endswith('.py'):
        bot.reply_to(message, "❌ فقط فایل‌های .py مجاز!")
        return
    
    msg = bot.send_message(message.chat.id, f"📝 **محتوای {file_name} را ارسال کنید:**")
    bot.register_next_step_handler(msg, process_add_file_content, folder_id, file_name)

def process_add_file_content(message, folder_id, file_name):
    content = message.text
    success, result = folder_manager.add_file(folder_id, file_name, content)
    bot.reply_to(message, f"✅ {result}" if success else f"❌ {result}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('run_folder_'))
def run_folder(call):
    user_id = call.from_user.id
    folder_id = call.data.replace('run_folder_', '')
    
    if not check_subscription(user_id):
        bot.answer_callback_query(call.id, "❌ اشتراک فعال نیست!", show_alert=True)
        return
    
    code = folder_manager.read_file(folder_id, 'main.py')
    if not code:
        bot.answer_callback_query(call.id, "❌ فایل main.py یافت نشد!", show_alert=True)
        return
    
    token = extract_token_from_code(code)
    if not token:
        bot.answer_callback_query(call.id, "❌ توکن پیدا نشد!", show_alert=True)
        return
    
    valid, bot_info = verify_token(token)
    if not valid:
        bot.answer_callback_query(call.id, "❌ توکن نامعتبر!", show_alert=True)
        return
    
    can_create, max_bots, current_bots = can_create_bot(user_id)
    if not can_create:
        bot.answer_callback_query(call.id, f"❌ حداکثر {max_bots} ربات!", show_alert=True)
        return
    
    # پیدا کردن ماشین
    machine_id = machine_manager.get_available_machine()
    if not machine_id:
        bot.answer_callback_query(call.id, "❌ همه سرورها پر هستند!", show_alert=True)
        return
    
    with get_db() as conn:
        folder = conn.execute("SELECT folder_path FROM folders WHERE id = ?", (folder_id,)).fetchone()
        folder_path = folder['folder_path'] if folder else None
    
    bot_id = hashlib.md5(f"{user_id}{token}{time.time()}".encode()).hexdigest()[:12]
    
    with get_db() as conn:
        conn.execute('''
            INSERT INTO bots (id, user_id, token, name, username, folder_path, folder_id, status, created_at, last_active, execution_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'stopped', ?, ?, 0)
        ''', (bot_id, user_id, token, bot_info['first_name'], bot_info['username'], folder_path, folder_id,
              datetime.now().isoformat(), datetime.now().isoformat()))
        conn.execute("UPDATE users SET bots_count = bots_count + 1 WHERE user_id = ?", (user_id,))
        conn.commit()
    
    machine_manager.assign_bot(bot_id, machine_id)
    
    exec_id, success, error = engine.execute_bot(bot_id, user_id, code, folder_path)
    
    if success:
        with get_db() as conn:
            conn.execute("UPDATE bots SET status = 'running' WHERE id = ?", (bot_id,))
            conn.commit()
        
        bot.answer_callback_query(call.id, "✅ ربات اجرا شد!", show_alert=True)
        bot.edit_message_text(f"✅ ربات {bot_info['first_name']} اجرا شد!", call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, f"❌ {error[:50]}", show_alert=True)

# ==================== لیست ربات‌ها ====================
@bot.message_handler(func=lambda m: m.text == '📋 لیست ربات‌ها')
def list_bots(message):
    user_id = message.from_user.id
    
    with get_db() as conn:
        bots = conn.execute("SELECT id, name, username, status, created_at, execution_count FROM bots WHERE user_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما هیچ رباتی ندارید!")
        return
    
    text = "🤖 **لیست ربات‌های شما**\n\n"
    for b in bots:
        status = engine.get_status(b['id'])
        status_text = "🟢 فعال" if status['running'] else "🔴 متوقف"
        text += f"**{b['name']}**\n"
        text += f"🔗 t.me/{b['username']}\n"
        text += f"📊 {status_text}\n"
        text += f"▶️ اجراها: {b['execution_count']}\n"
        text += f"📅 {b['created_at'][:10]}\n\n"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== اجرای ربات ====================
@bot.message_handler(func=lambda m: m.text == '▶️ اجرای ربات')
def run_prompt(message):
    user_id = message.from_user.id
    
    with get_db() as conn:
        bots = conn.execute("SELECT id, name FROM bots WHERE user_id = ?", (user_id,)).fetchall()
    
    if not bots:
        bot.send_message(message.chat.id, "📋 رباتی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        status = engine.get_status(b['id'])
        emoji = "🟢" if status['running'] else "🔴"
        markup.add(types.InlineKeyboardButton(f"{emoji} {b['name']}", callback_data=f"run_bot_{b['id']}"))
    
    bot.send_message(message.chat.id, "▶️ انتخاب ربات:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('run_bot_'))
def run_bot(call):
    bot_id = call.data.replace('run_bot_', '')
    user_id = call.from_user.id
    
    if not check_subscription(user_id):
        bot.answer_callback_query(call.id, "❌ اشتراک فعال نیست!", show_alert=True)
        return
    
    status = engine.get_status(bot_id)
    if status['running']:
        bot.answer_callback_query(call.id, "ربات در حال اجراست!", show_alert=True)
        return
    
    with get_db() as conn:
        bot_info = conn.execute("SELECT file_path, folder_path, token FROM bots WHERE id = ? AND user_id = ?", (bot_id, user_id)).fetchone()
    
    if not bot_info:
        bot.answer_callback_query(call.id, "ربات یافت نشد!", show_alert=True)
        return
    
    code = None
    if bot_info['folder_path'] and os.path.exists(bot_info['folder_path']):
        main_path = os.path.join(bot_info['folder_path'], 'main.py')
        if os.path.exists(main_path):
            with open(main_path, 'r', encoding='utf-8') as f:
                code = f.read()
    elif bot_info['file_path'] and os.path.exists(bot_info['file_path']):
        with open(bot_info['file_path'], 'r', encoding='utf-8') as f:
            code = f.read()
    
    if not code:
        bot.answer_callback_query(call.id, "فایل ربات یافت نشد!", show_alert=True)
        return
    
    exec_id, success, error = engine.execute_bot(bot_id, user_id, code, bot_info['folder_path'])
    
    if success:
        with get_db() as conn:
            conn.execute("UPDATE bots SET status = 'running', execution_count = execution_count + 1 WHERE id = ?", (bot_id,))
            conn.commit()
        bot.answer_callback_query(call.id, "✅ ربات اجرا شد!", show_alert=True)
    else:
        bot.answer_callback_query(call.id, f"❌ {error[:50]}", show_alert=True)
    
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== توقف ربات ====================
@bot.message_handler(func=lambda m: m.text == '🛑 توقف ربات')
def stop_prompt(message):
    user_id = message.from_user.id
    
    with get_db() as conn:
        bots = conn.execute("SELECT id, name FROM bots WHERE user_id = ?", (user_id,)).fetchall()
    
    if not bots:
        bot.send_message(message.chat.id, "📋 رباتی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        if engine.get_status(b['id'])['running']:
            markup.add(types.InlineKeyboardButton(f"🛑 {b['name']}", callback_data=f"stop_bot_{b['id']}"))
    
    if not markup.keyboard:
        bot.send_message(message.chat.id, "📋 هیچ ربات در حال اجرایی ندارید!")
        return
    
    bot.send_message(message.chat.id, "🛑 انتخاب ربات:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('stop_bot_'))
def stop_bot(call):
    bot_id = call.data.replace('stop_bot_', '')
    engine.stop_bot(bot_id)
    
    with get_db() as conn:
        conn.execute("UPDATE bots SET status = 'stopped' WHERE id = ?", (bot_id,))
        conn.commit()
    
    bot.answer_callback_query(call.id, "✅ ربات متوقف شد!", show_alert=True)
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== حذف ربات ====================
@bot.message_handler(func=lambda m: m.text == '🗑 حذف ربات')
def delete_prompt(message):
    user_id = message.from_user.id
    
    with get_db() as conn:
        bots = conn.execute("SELECT id, name FROM bots WHERE user_id = ?", (user_id,)).fetchall()
    
    if not bots:
        bot.send_message(message.chat.id, "📋 رباتی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        markup.add(types.InlineKeyboardButton(f"🗑 {b['name']}", callback_data=f"del_bot_{b['id']}"))
    
    bot.send_message(message.chat.id, "🗑 انتخاب ربات:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('del_bot_'))
def confirm_delete(call):
    bot_id = call.data.replace('del_bot_', '')
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ بله", callback_data=f"confirm_del_{bot_id}"),
              types.InlineKeyboardButton("❌ انصراف", callback_data="cancel_del"))
    bot.edit_message_text("⚠️ اطمینان دارید؟", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_del_'))
def do_delete(call):
    bot_id = call.data.replace('confirm_del_', '')
    user_id = call.from_user.id
    
    engine.stop_bot(bot_id)
    machine_manager.release_bot(bot_id)
    
    with get_db() as conn:
        conn.execute("DELETE FROM bots WHERE id = ? AND user_id = ?", (bot_id, user_id))
        conn.execute("UPDATE users SET bots_count = bots_count - 1 WHERE user_id = ?", (user_id,))
        conn.commit()
    
    bot.edit_message_text("✅ ربات حذف شد!", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "cancel_del")
def cancel_delete(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== کیف پول ====================
@bot.message_handler(func=lambda m: m.text == '💰 کیف پول')
def wallet(message):
    user = get_user(message.from_user.id)
    if not user:
        bot.send_message(message.chat.id, "❌ /start بزنید")
        return
    
    can_create, max_bots, current_bots = can_create_bot(message.from_user.id)
    withdraw_percent = get_setting('withdraw_percent')
    min_withdraw = get_setting('min_withdraw')
    
    text = f"💰 **کیف پول شما**\n\n"
    text += f"👤 {user['first_name']}\n"
    text += f"💵 موجودی: {user['balance']:,} تومان\n"
    text += f"👥 دعوت‌ها: {user['referrals_count']}\n"
    text += f"✅ تایید شده: {user['verified_referrals']}\n"
    text += f"🤖 ربات‌ها: {current_bots}/{max_bots}\n\n"
    text += f"💰 **کمیسیون دعوت:** {withdraw_percent}%\n"
    text += f"💸 **حداقل برداشت:** {int(min_withdraw):,} تومان\n\n"
    text += f"💡 هر دعوت = {int(SUBSCRIPTION_PRICE * int(withdraw_percent) / 100):,} تومان پاداش"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== دعوت دوستان ====================
@bot.message_handler(func=lambda m: m.text == '👥 دعوت دوستان')
def invite(message):
    user = get_user(message.from_user.id)
    bot_username = bot.get_me().username
    link = f"https://t.me/{bot_username}?start={user['referral_code']}"
    withdraw_percent = get_setting('withdraw_percent')
    
    commission = int(SUBSCRIPTION_PRICE * int(withdraw_percent) / 100)
    
    text = f"👥 **دعوت دوستان**\n\n"
    text += f"🎁 کد: `{user['referral_code']}`\n"
    text += f"🔗 لینک: {link}\n"
    text += f"📊 دعوت‌ها: {user['referrals_count']}\n"
    text += f"✅ تایید شده: {user['verified_referrals']}\n\n"
    text += f"💰 **هر دعوت:** {commission:,} تومان پاداش\n"
    text += f"📌 **کمیسیون:** {withdraw_percent}% از مبلغ اشتراک\n\n"
    text += f"💡 هر دوست شما که اشتراک بخرد، {withdraw_percent}% به حساب شما واریز می‌شود!"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📋 کپی لینک", callback_data=f"copy_{user['referral_code']}"))
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

# ==================== درخواست برداشت ====================
@bot.message_handler(func=lambda m: m.text == '💸 درخواست برداشت')
def withdraw_request(message):
    user = get_user(message.from_user.id)
    min_w = int(get_setting('min_withdraw'))
    
    if user['balance'] < min_w:
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
    
    msg = bot.send_message(message.chat.id, "🏦 نام بانک:")
    bot.register_next_step_handler(msg, process_withdraw_bank, user, card, holder)

def process_withdraw_bank(message, user, card, holder):
    bank = message.text.strip()
    tracking_code = hashlib.md5(f"{user['user_id']}_{card}_{time.time()}".encode()).hexdigest()[:12].upper()
    
    with get_db() as conn:
        conn.execute('''
            INSERT INTO withdraw_requests (user_id, amount, card_number, card_holder, bank_name, tracking_code, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
        ''', (user['user_id'], user['balance'], card, holder, bank, tracking_code, datetime.now().isoformat()))
        
        conn.execute("UPDATE users SET balance = 0 WHERE user_id = ?", (user['user_id'],))
        conn.commit()
    
    bot.reply_to(message, 
                f"✅ **درخواست برداشت ثبت شد!**\n\n"
                f"💰 مبلغ: {user['balance']:,} تومان\n"
                f"💳 کارت: {card[:4]}****{card[-4:]}\n"
                f"🏦 بانک: {bank}\n"
                f"🔑 کد رهگیری: `{tracking_code}`\n\n"
                f"پس از بررسی، مبلغ به کارت شما واریز می‌شود.", parse_mode='Markdown')
    
    for admin_id in ADMIN_IDS:
        bot.send_message(admin_id, f"💰 درخواست برداشت\n👤 {user['first_name']}\n🆔 {user['user_id']}\n💰 {user['balance']:,} تومان")

# ==================== کتابخانه‌ها ====================
@bot.message_handler(func=lambda m: m.text == '📦 کتابخانه‌ها')
def libraries_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    libs = library_manager.common_libs
    for name in list(libs.keys())[:12]:
        markup.add(types.InlineKeyboardButton(f"📦 {name}", callback_data=f"install_{libs[name]}"))
    markup.add(types.InlineKeyboardButton("🔧 نصب دستی", callback_data="install_custom"))
    markup.add(types.InlineKeyboardButton("✅ نصب شده‌ها", callback_data="installed_libs"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="lib_back"))
    
    bot.send_message(message.chat.id, "📦 **کتابخانه‌های محبوب**", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('install_'))
def install_lib(call):
    lib = call.data.replace('install_', '')
    if lib == 'custom':
        msg = bot.send_message(call.message.chat.id, "🔧 نام کتابخانه:")
        bot.register_next_step_handler(msg, install_custom)
        bot.answer_callback_query(call.id)
        return
    elif lib == 'back':
        libraries_menu(call.message)
        return
    
    library_manager.install(lib, call.message.chat.id)
    bot.answer_callback_query(call.id, f"🔄 در حال نصب {lib}...")

def install_custom(message):
    lib = message.text.strip()
    library_manager.install(lib, message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data == "installed_libs")
def show_installed(call):
    with get_db() as conn:
        libs = conn.execute("SELECT name, version, installed_at FROM libraries ORDER BY installed_at DESC").fetchall()
    
    if not libs:
        bot.edit_message_text("📦 کتابخانه‌ای نصب نشده!", call.message.chat.id, call.message.message_id)
        return
    
    text = "✅ **کتابخانه‌های نصب شده**\n\n"
    for lib in libs:
        text += f"• `{lib['name']}` - {lib['version']}\n"
        text += f"  📅 {lib['installed_at'][:10]}\n\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="install_back"))
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "lib_back")
def lib_back(call):
    libraries_menu(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "install_back")
def install_back(call):
    libraries_menu(call.message)

# ==================== راهنما ====================
@bot.message_handler(func=lambda m: m.text == '📚 راهنما')
def guide(message):
    text = """📚 **راهنمای جامع ربات مادر**

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

**👥 دعوت دوستان:**
- هر دعوت ۷٪ کمیسیون
- حداقل برداشت ۲ میلیون تومان

**📦 کتابخانه‌ها:**
- می‌توانید هر کتابخانه پایتونی نصب کنید

**🆘 پشتیبانی:** @shahraghee13"""
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== آمار ====================
@bot.message_handler(func=lambda m: m.text == '📊 آمار')
def stats(message):
    with get_db() as conn:
        users = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()['c']
        active_subs = conn.execute("SELECT COUNT(*) as c FROM users WHERE subscription_status = 'active'").fetchone()['c']
        bots = conn.execute("SELECT COUNT(*) as c FROM bots").fetchone()['c']
        total_wallet = conn.execute("SELECT SUM(balance) as t FROM users").fetchone()['t'] or 0
    
    running = engine.get_stats()['active']
    machine_stats = machine_manager.get_stats()
    cache_stats = cache.get_stats()
    
    text = f"📊 **آمار سیستم**\n\n"
    text += f"👥 کاربران: {users}\n"
    text += f"✅ اشتراک فعال: {active_subs}\n"
    text += f"🤖 ربات‌ها: {bots}\n"
    text += f"🟢 در حال اجرا: {running}\n"
    text += f"💰 موجودی کل: {total_wallet:,} تومان\n\n"
    text += f"🖥️ **سرورها:**\n"
    text += f"   تعداد ماشین‌ها: {machine_stats['total_machines']}\n"
    text += f"   ظرفیت کل: {machine_stats['total_capacity']:,}\n"
    text += f"   استفاده: {machine_stats['usage_percent']:.1f}%\n\n"
    text += f"⚡ **کش:**\n"
    text += f"   حجم: {cache_stats['size']}\n"
    text += f"   نرخ بازدید: {cache_stats['hit_rate']}%\n\n"
    text += f"📌 حداکثر ربات: {get_setting('max_bots_per_user')}"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== وضعیت اجرا ====================
@bot.message_handler(func=lambda m: m.text == '⚡ وضعیت اجرا')
def exec_status(message):
    user_id = message.from_user.id
    
    with get_db() as conn:
        bots = conn.execute("SELECT id, name FROM bots WHERE user_id = ?", (user_id,)).fetchall()
    
    if not bots:
        bot.send_message(message.chat.id, "📋 رباتی ندارید!")
        return
    
    text = "⚡ **وضعیت اجرا**\n\n"
    for b in bots:
        status = engine.get_status(b['id'])
        if status['running']:
            text += f"🟢 {b['name']}: {status['uptime']} ثانیه\n"
        else:
            text += f"🔴 {b['name']}: متوقف\n"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== پشتیبانی ====================
@bot.message_handler(func=lambda m: m.text == '📞 پشتیبانی')
def support(message):
    bot.send_message(message.chat.id, "📞 **پشتیبانی:** @shahraghee13\n\nسوالات خود را بپرسید.", parse_mode='Markdown')

# ==================== پیام همگانی ====================
@bot.message_handler(func=lambda m: m.text == '📢 پیام همگانی')
def broadcast_prompt(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(message.chat.id, "📢 **متن پیام همگانی را ارسال کنید:**\n(می‌توانید از Markdown استفاده کنید)")
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    text = message.text
    
    with get_db() as conn:
        users = conn.execute("SELECT user_id FROM users WHERE is_banned = 0").fetchall()
    
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
                         message.chat.id, status_msg.message_id, parse_mode='Markdown')

# ==================== پنل مدیریت حرفه‌ای ====================
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
        types.InlineKeyboardButton("🖥️ مدیریت ماشین", callback_data="admin_machines"),
        types.InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings"),
        types.InlineKeyboardButton("📊 گزارش کامل", callback_data="admin_report"),
        types.InlineKeyboardButton("🔄 کش سیستم", callback_data="admin_cache"),
        types.InlineKeyboardButton("🎁 فعال‌سازی", callback_data="admin_activate"),
        types.InlineKeyboardButton("🔧 خطاها", callback_data="admin_errors"),
        types.InlineKeyboardButton("💾 پشتیبان", callback_data="admin_backup"),
        types.InlineKeyboardButton("➕ ماشین جدید", callback_data="admin_add_machine"),
    )
    
    bot.send_message(message.chat.id, "👑 **پنل مدیریت پیشرفته**", parse_mode='Markdown', reply_markup=markup)

# ==================== مدیریت کاربران ====================
@bot.callback_query_handler(func=lambda call: call.data == "admin_users")
def admin_users(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🔍 جستجوی کاربر", callback_data="admin_search_user"),
        types.InlineKeyboardButton("🗑 حذف کاربر", callback_data="admin_delete_user"),
        types.InlineKeyboardButton("💰 افزایش موجودی", callback_data="admin_add_balance"),
        types.InlineKeyboardButton("📋 لیست کاربران", callback_data="admin_list_users"),
        types.InlineKeyboardButton("👥 برترین دعوت‌ها", callback_data="admin_top_users"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    bot.edit_message_text("👥 **مدیریت کاربران**", call.message.chat.id, call.message.message_id, reply_markup=markup)

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
            with get_db() as conn:
                bots = conn.execute("SELECT COUNT(*) as c FROM bots WHERE user_id = ?", (user_id,)).fetchone()['c']
                receipts = conn.execute("SELECT SUM(amount) as t FROM receipts WHERE user_id = ? AND status = 'approved'", (user_id,)).fetchone()['t'] or 0
            
            text = f"👤 **اطلاعات کاربر**\n\n"
            text += f"نام: {user['first_name']}\n"
            text += f"نام کاربری: @{user['username'] if user['username'] else 'ندارد'}\n"
            text += f"🆔 `{user_id}`\n\n"
            text += f"💰 موجودی: {user['balance']:,} تومان\n"
            text += f"💳 کل پرداخت: {receipts:,} تومان\n\n"
            text += f"✅ اشتراک: {'فعال' if check_subscription(user_id) else 'غیرفعال'}\n"
            if user['subscription_expiry']:
                text += f"📅 انقضا: {user['subscription_expiry'][:16]}\n\n"
            text += f"🤖 ربات‌ها: {bots}\n"
            text += f"👥 دعوت‌ها: {user['referrals_count']}\n"
            text += f"🎁 کد معرف: `{user['referral_code']}`\n"
            text += f"📅 عضویت: {user['created_at'][:16]}"
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("💰 افزایش موجودی", callback_data=f"add_balance_{user_id}"))
            markup.add(types.InlineKeyboardButton("🎁 فعال‌سازی اشتراک", callback_data=f"activate_user_{user_id}"))
            markup.add(types.InlineKeyboardButton("🗑 حذف کاربر", callback_data=f"delete_user_{user_id}"))
            
            bot.reply_to(message, text, parse_mode='Markdown', reply_markup=markup)
        else:
            bot.reply_to(message, "❌ کاربر یافت نشد!")
    except:
        bot.reply_to(message, "❌ آیدی نامعتبر!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_delete_user")
def admin_delete_user(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, "🗑 **آیدی کاربر را وارد کنید:**")
    bot.register_next_step_handler(msg, process_delete_user)
    bot.answer_callback_query(call.id)

def process_delete_user(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        user_id = int(message.text.strip())
        
        # توقف همه ربات‌های کاربر
        with get_db() as conn:
            bots = conn.execute("SELECT id FROM bots WHERE user_id = ?", (user_id,)).fetchall()
            for bot in bots:
                engine.stop_bot(bot['id'])
            conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            conn.commit()
        
        bot.reply_to(message, f"✅ کاربر {user_id} با موفقیت حذف شد!")
    except:
        bot.reply_to(message, "❌ خطا!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_add_balance")
def admin_add_balance(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, "💰 **فرمت: آیدی کاربر مبلغ**\nمثال: `123456789 100000`")
    bot.register_next_step_handler(msg, process_add_balance)
    bot.answer_callback_query(call.id)

def process_add_balance(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        parts = message.text.strip().split()
        user_id = int(parts[0])
        amount = int(parts[1])
        
        add_wallet_balance(user_id, amount)
        bot.reply_to(message, f"✅ {amount:,} تومان به کیف پول کاربر {user_id} اضافه شد!")
        
        try:
            bot.send_message(user_id, f"💰 مبلغ {amount:,} تومان به کیف پول شما اضافه شد!")
        except:
            pass
    except:
        bot.reply_to(message, "❌ فرمت نامعتبر!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_list_users")
def admin_list_users(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    with get_db() as conn:
        users = conn.execute("SELECT user_id, first_name, balance, subscription_status, created_at FROM users ORDER BY created_at DESC LIMIT 20").fetchall()
    
    if not users:
        bot.send_message(call.message.chat.id, "📋 کاربری وجود ندارد")
        return
    
    text = "👥 **۲۰ کاربر آخر**\n\n"
    for u in users:
        status = "✅" if u['subscription_status'] == 'active' else "❌"
        text += f"{status} `{u['user_id']}` - {u['first_name']}\n"
        text += f"   💰 {u['balance']:,} تومان\n"
        text += f"   📅 {u['created_at'][:10]}\n\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "admin_top_users")
def admin_top_users(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    with get_db() as conn:
        users = conn.execute("SELECT user_id, first_name, referrals_count, balance FROM users ORDER BY referrals_count DESC LIMIT 10").fetchall()
    
    text = "🏆 **برترین دعوت‌کنندگان**\n\n"
    for i, u in enumerate(users, 1):
        text += f"{i}. {u['first_name']}\n"
        text += f"   🆔 `{u['user_id']}`\n"
        text += f"   👥 {u['referrals_count']} دعوت\n"
        text += f"   💰 {u['balance']:,} تومان\n\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

# ==================== مدیریت ربات‌ها ====================
@bot.callback_query_handler(func=lambda call: call.data == "admin_bots")
def admin_bots(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    with get_db() as conn:
        bots = conn.execute("SELECT id, name, user_id, status, created_at FROM bots ORDER BY created_at DESC LIMIT 30").fetchall()
    
    if not bots:
        bot.send_message(call.message.chat.id, "🤖 رباتی وجود ندارد")
        return
    
    text = "🤖 **لیست ربات‌ها**\n\n"
    for b in bots:
        status = engine.get_status(b['id'])
        status_text = "🟢" if status['running'] else "🔴"
        text += f"{status_text} **{b['name']}**\n"
        text += f"   👤 کاربر: {b['user_id']}\n"
        text += f"   📅 {b['created_at'][:10]}\n\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

# ==================== تایید فیش ====================
@bot.callback_query_handler(func=lambda call: call.data == "admin_receipts")
def admin_receipts(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    with get_db() as conn:
        receipts = conn.execute("SELECT * FROM receipts WHERE status = 'pending' ORDER BY created_at").fetchall()
    
    if not receipts:
        bot.send_message(call.message.chat.id, "📸 فیشی وجود ندارد")
        return
    
    for r in receipts:
        text = f"📸 فیش #{r['id']}\n👤 {r['user_id']}\n💰 {r['amount']:,} تومان\n🆔 {r['payment_code']}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_recipt_{r['id']}"),
                  types.InlineKeyboardButton("❌ رد", callback_data=f"reject_recipt_{r['id']}"))
        
        if os.path.exists(r['receipt_path']):
            with open(r['receipt_path'], 'rb') as f:
                bot.send_photo(call.message.chat.id, f, caption=text, reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_recipt_'))
def approve_receipt_admin(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    rid = int(call.data.replace('approve_recipt_', ''))
    
    with get_db() as conn:
        receipt = conn.execute("SELECT user_id FROM receipts WHERE id = ?", (rid,)).fetchone()
        if receipt:
            conn.execute("UPDATE receipts SET status = 'approved', reviewed_by = ?, reviewed_at = ? WHERE id = ?",
                        (call.from_user.id, datetime.now().isoformat(), rid))
            expiry = activate_subscription(receipt['user_id'])
            conn.commit()
            
            bot.send_message(receipt['user_id'], 
                            f"✅ **اشتراک شما فعال شد!**\n\n"
                            f"📅 تا تاریخ: {expiry.strftime('%Y-%m-%d')}\n"
                            f"🤖 می‌توانید حداکثر ۳ ربات بسازید!")
            
            bot.answer_callback_query(call.id, "✅ اشتراک فعال شد!")
            bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_recipt_'))
def reject_receipt_admin(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    rid = int(call.data.replace('reject_recipt_', ''))
    
    with get_db() as conn:
        receipt = conn.execute("SELECT user_id, payment_code FROM receipts WHERE id = ?", (rid,)).fetchone()
        if receipt:
            conn.execute("UPDATE receipts SET status = 'rejected', reviewed_by = ?, reviewed_at = ? WHERE id = ?",
                        (call.from_user.id, datetime.now().isoformat(), rid))
            conn.commit()
            
            bot.send_message(receipt['user_id'], 
                            f"❌ **فیش شما رد شد!**\n\n"
                            f"🆔 کد پیگیری: {receipt['payment_code']}\n\n"
                            f"لطفاً با پشتیبانی تماس بگیرید: @shahraghee13")
            
            bot.answer_callback_query(call.id, "❌ رد شد!")
            bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== تایید برداشت ====================
@bot.callback_query_handler(func=lambda call: call.data == "admin_withdraws")
def admin_withdraws(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    with get_db() as conn:
        withdraws = conn.execute("SELECT * FROM withdraw_requests WHERE status = 'pending' ORDER BY created_at").fetchall()
    
    if not withdraws:
        bot.send_message(call.message.chat.id, "💰 درخواستی وجود ندارد")
        return
    
    for w in withdraws:
        user = get_user(w['user_id'])
        text = f"💰 برداشت #{w['id']}\n"
        text += f"👤 {user['first_name'] if user else 'نامشخص'}\n"
        text += f"🆔 {w['user_id']}\n"
        text += f"💰 {w['amount']:,} تومان\n"
        text += f"💳 {w['card_number']}\n"
        text += f"👤 {w['card_holder']}\n"
        text += f"🏦 {w['bank_name']}\n"
        text += f"🔑 {w['tracking_code']}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ تایید واریز", callback_data=f"approve_withdraw_{w['id']}"))
        
        bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_withdraw_'))
def approve_withdraw_admin(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    wid = int(call.data.replace('approve_withdraw_', ''))
    
    with get_db() as conn:
        conn.execute("UPDATE withdraw_requests SET status = 'approved', processed_at = ? WHERE id = ?",
                    (datetime.now().isoformat(), wid))
        conn.commit()
    
    bot.answer_callback_query(call.id, "✅ برداشت تایید شد!")
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== مدیریت ماشین ====================
@bot.callback_query_handler(func=lambda call: call.data == "admin_machines")
def admin_machines(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    machine_stats = machine_manager.get_stats()
    
    with get_db() as conn:
        machines = conn.execute("SELECT * FROM machines").fetchall()
    
    text = f"🖥️ **وضعیت ماشین‌ها**\n\n"
    text += f"📊 **آمار کلی:**\n"
    text += f"   تعداد ماشین‌ها: {machine_stats['total_machines']}\n"
    text += f"   ظرفیت کل: {machine_stats['total_capacity']:,}\n"
    text += f"   ربات‌های فعال: {machine_stats['total_bots']}\n"
    text += f"   فضای خالی: {machine_stats['available']}\n"
    text += f"   درصد استفاده: {machine_stats['usage_percent']:.1f}%\n\n"
    
    text += f"📋 **جزئیات ماشین‌ها:**\n"
    for m in machines:
        status_emoji = "🟢" if m['status'] == 'active' else "🔴"
        usage = (m['current_bots'] / m['max_bots'] * 100) if m['max_bots'] > 0 else 0
        text += f"{status_emoji} **{m['name']}**\n"
        text += f"   🤖 {m['current_bots']}/{m['max_bots']} ({usage:.1f}%)\n"
        text += f"   🌐 {m['ip']}:{m['port']}\n"
        text += f"   🕐 آخرین ارتباط: {m['last_heartbeat'][:16] if m['last_heartbeat'] else '---'}\n\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("➕ اضافه کردن ماشین", callback_data="admin_add_machine"))
    markup.add(types.InlineKeyboardButton("🔄 بروزرسانی", callback_data="admin_machines"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back"))
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_add_machine")
def admin_add_machine(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("➕ ماشین پیش‌فرض", callback_data="add_machine_default"),
        types.InlineKeyboardButton("📝 سفارشی", callback_data="add_machine_custom"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_machines")
    )
    
    bot.edit_message_text("➕ **اضافه کردن ماشین جدید**\n\n"
                         "برای مقیاس‌پذیری بالاتر، می‌توانید ماشین جدید اضافه کنید.\n\n"
                         "**ماشین پیش‌فرض:**\n"
                         "• نام: Machine-New\n"
                         "• IP: 127.0.0.1\n"
                         "• پورت: 8000\n"
                         "• ظرفیت: 5000 ربات",
                         call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "add_machine_default")
def add_machine_default(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    machine_id = machine_manager.add_machine("Machine-New", "127.0.0.1", 8000, 5000)
    
    bot.edit_message_text(f"✅ ماشین جدید با موفقیت اضافه شد!\n\n"
                         f"🆔 آیدی: {machine_id}\n"
                         f"📌 نام: Machine-New\n"
                         f"🌐 IP: 127.0.0.1:8000\n"
                         f"🤖 ظرفیت: 5000 ربات",
                         call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "add_machine_custom")
def add_machine_custom(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, "📝 **اطلاعات ماشین جدید را وارد کنید:**\n\n"
                         "فرمت: `نام|IP|پورت|ظرفیت`\n"
                         "مثال: `Machine-004|192.168.1.100|8000|5000`")
    bot.register_next_step_handler(msg, process_add_machine)
    bot.answer_callback_query(call.id)

def process_add_machine(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        parts = message.text.strip().split('|')
        name = parts[0]
        ip = parts[1]
        port = int(parts[2])
        max_bots = int(parts[3])
        
        machine_id = machine_manager.add_machine(name, ip, port, max_bots)
        
        bot.reply_to(message, f"✅ ماشین {name} با موفقیت اضافه شد!\n🆔 آیدی: {machine_id}")
    except:
        bot.reply_to(message, "❌ فرمت نامعتبر!")

# ==================== تنظیمات ====================
@bot.callback_query_handler(func=lambda call: call.data == "admin_settings")
def admin_settings(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("💰 قیمت اشتراک", callback_data="admin_set_price"),
        types.InlineKeyboardButton("💳 اطلاعات کارت", callback_data="admin_set_card"),
        types.InlineKeyboardButton("📌 حداکثر ربات", callback_data="admin_set_max_bots"),
        types.InlineKeyboardButton("🔄 ایزوله‌سازی", callback_data="admin_set_isolation"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    text = f"⚙️ **تنظیمات فعلی**\n\n"
    text += f"💰 قیمت اشتراک: {get_setting('subscription_price_str')}\n"
    text += f"💳 کارت: {get_setting('card_number_display')}\n"
    text += f"📌 حداکثر ربات: {get_setting('max_bots_per_user')}\n"
    text += f"🔒 حافظه مجاز: {ISOLATION_SETTINGS['max_memory_mb']} MB\n"
    text += f"📊 کمیسیون: {get_setting('withdraw_percent')}%\n"
    text += f"💸 حداقل برداشت: {int(get_setting('min_withdraw')):,} تومان"
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_price")
def admin_set_price(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, "💰 **قیمت جدید (تومان):**")
    bot.register_next_step_handler(msg, process_admin_set_price)
    bot.answer_callback_query(call.id)

def process_admin_set_price(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        price = int(message.text.strip())
        with get_db() as conn:
            conn.execute("UPDATE settings SET value = ?, updated_at = ? WHERE key = 'subscription_price'", (str(price), datetime.now().isoformat()))
            conn.execute("UPDATE settings SET value = ?, updated_at = ? WHERE key = 'subscription_price_str'", (f"{price:,} تومان", datetime.now().isoformat()))
            conn.commit()
        
        cache.delete("setting_subscription_price")
        cache.delete("setting_subscription_price_str")
        
        bot.reply_to(message, f"✅ قیمت به {price:,} تومان تغییر کرد!")
    except:
        bot.reply_to(message, "❌ عدد معتبر وارد کنید!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_card")
def admin_set_card(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, "💳 **شماره کارت جدید (۱۶ رقم):**")
    bot.register_next_step_handler(msg, process_admin_set_card_num)
    bot.answer_callback_query(call.id)

def process_admin_set_card_num(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    card = message.text.strip().replace(' ', '')
    if len(card) == 16 and card.isdigit():
        with get_db() as conn:
            conn.execute("UPDATE settings SET value = ?, updated_at = ? WHERE key = 'card_number'", (card, datetime.now().isoformat()))
            display = ' '.join([card[i:i+4] for i in range(0, 16, 4)])
            conn.execute("UPDATE settings SET value = ?, updated_at = ? WHERE key = 'card_number_display'", (display, datetime.now().isoformat()))
            conn.commit()
        
        cache.delete("setting_card_number")
        cache.delete("setting_card_number_display")
        
        msg = bot.send_message(message.chat.id, "👤 **نام صاحب کارت:**")
        bot.register_next_step_handler(msg, process_admin_set_card_holder)
    else:
        bot.reply_to(message, "❌ شماره کارت باید ۱۶ رقم باشد!")

def process_admin_set_card_holder(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    holder = message.text.strip()
    with get_db() as conn:
        conn.execute("UPDATE settings SET value = ?, updated_at = ? WHERE key = 'card_holder'", (holder, datetime.now().isoformat()))
        conn.commit()
    
    cache.delete("setting_card_holder")
    bot.reply_to(message, f"✅ اطلاعات کارت به‌روزرسانی شد!\n\n`{get_setting('card_number_display')}`\n👤 {get_setting('card_holder')}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_max_bots")
def admin_set_max_bots(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, "📌 **حداکثر ربات هر کاربر (۱-۱۰):**")
    bot.register_next_step_handler(msg, process_admin_set_max_bots)
    bot.answer_callback_query(call.id)

def process_admin_set_max_bots(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        max_bots = int(message.text.strip())
        if 1 <= max_bots <= 10:
            with get_db() as conn:
                conn.execute("UPDATE settings SET value = ?, updated_at = ? WHERE key = 'max_bots_per_user'", (str(max_bots), datetime.now().isoformat()))
                conn.commit()
            
            cache.delete("setting_max_bots_per_user")
            bot.reply_to(message, f"✅ حداکثر ربات به {max_bots} تغییر کرد!")
        else:
            bot.reply_to(message, "❌ عدد بین 1 تا 10")
    except:
        bot.reply_to(message, "❌ عدد معتبر وارد کنید!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_isolation")
def admin_set_isolation(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("💾 حداکثر حافظه", callback_data="admin_set_memory"),
        types.InlineKeyboardButton("🔒 حداکثر CPU", callback_data="admin_set_cpu"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_settings")
    )
    
    text = f"🔒 **تنظیمات ایزوله‌سازی**\n\n"
    text += f"💾 حداکثر حافظه: {ISOLATION_SETTINGS['max_memory_mb']} MB\n"
    text += f"🔒 حداکثر CPU: {ISOLATION_SETTINGS['max_cpu_percent']}%\n"
    text += f"📄 حداکثر فایل: {ISOLATION_SETTINGS['max_files']}\n"
    text += f"⚙️ حداکثر پروسس: {ISOLATION_SETTINGS['max_processes']}"
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)

# ==================== گزارش کامل ====================
@bot.callback_query_handler(func=lambda call: call.data == "admin_report")
def admin_report(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    with get_db() as conn:
        total_users = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()['c']
        active_subs = conn.execute("SELECT COUNT(*) as c FROM users WHERE subscription_status = 'active'").fetchone()['c']
        total_bots = conn.execute("SELECT COUNT(*) as c FROM bots").fetchone()['c']
        total_folders = conn.execute("SELECT COUNT(*) as c FROM folders").fetchone()['c']
        total_executions = conn.execute("SELECT COUNT(*) as c FROM executions").fetchone()['c']
        total_wallet = conn.execute("SELECT SUM(balance) as t FROM users").fetchone()['t'] or 0
        total_revenue = conn.execute("SELECT SUM(amount) as t FROM receipts WHERE status = 'approved'").fetchone()['t'] or 0
        pending_receipts = conn.execute("SELECT COUNT(*) as c FROM receipts WHERE status = 'pending'").fetchone()['c']
        pending_withdraws = conn.execute("SELECT COUNT(*) as c FROM withdraw_requests WHERE status = 'pending'").fetchone()['c']
        total_libs = conn.execute("SELECT COUNT(*) as c FROM libraries").fetchone()['c']
    
    machine_stats = machine_manager.get_stats()
    exec_stats = engine.get_stats()
    cache_stats = cache.get_stats()
    
    today = datetime.now().date().isoformat()
    daily = conn.execute("SELECT * FROM daily_stats WHERE date = ?", (today,)).fetchone()
    
    text = f"📊 **گزارش کامل سیستم**\n\n"
    text += f"═══════════════════════\n"
    text += f"👥 **کاربران**\n"
    text += f"   کل کاربران: {total_users}\n"
    text += f"   اشتراک فعال: {active_subs}\n"
    text += f"   نرخ فعال‌سازی: {(active_subs/total_users*100):.1f}%\n\n"
    
    text += f"🤖 **ربات‌ها**\n"
    text += f"   کل ربات‌ها: {total_bots}\n"
    text += f"   در حال اجرا: {exec_stats['active']}\n"
    text += f"   میانگین هر کاربر: {(total_bots/total_users):.1f}\n\n"
    
    text += f"📁 **پوشه‌ها**\n"
    text += f"   کل پوشه‌ها: {total_folders}\n\n"
    
    text += f"▶️ **اجراها**\n"
    text += f"   کل اجراها: {total_executions}\n\n"
    
    text += f"📦 **کتابخانه‌ها**\n"
    text += f"   نصب شده: {total_libs}\n\n"
    
    text += f"💰 **مالی**\n"
    text += f"   موجودی کل: {total_wallet:,} تومان\n"
    text += f"   درآمد کل: {total_revenue:,} تومان\n"
    text += f"   فیش‌های در انتظار: {pending_receipts}\n"
    text += f"   برداشت‌های در انتظار: {pending_withdraws}\n\n"
    
    if daily:
        text += f"📈 **آمار امروز ({today})**\n"
        text += f"   کاربران جدید: {daily['new_users']}\n"
        text += f"   ربات‌های جدید: {daily['new_bots']}\n"
        text += f"   اشتراک‌های جدید: {daily['new_subscriptions']}\n"
        text += f"   درآمد امروز: {daily['total_revenue']:,} تومان\n\n"
    
    text += f"🖥️ **سخت‌افزار**\n"
    text += f"   ماشین‌ها: {machine_stats['total_machines']}\n"
    text += f"   ظرفیت کل: {machine_stats['total_capacity']:,}\n"
    text += f"   استفاده: {machine_stats['usage_percent']:.1f}%\n\n"
    
    text += f"⚡ **کش**\n"
    text += f"   حجم: {cache_stats['size']}\n"
    text += f"   نرخ بازدید: {cache_stats['hit_rate']}%"
    
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

# ==================== مدیریت کش ====================
@bot.callback_query_handler(func=lambda call: call.data == "admin_cache")
def admin_cache(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    stats = cache.get_stats()
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🗑 پاک کردن کش", callback_data="admin_clear_cache"),
        types.InlineKeyboardButton("📊 آمار کش", callback_data="admin_cache_stats"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    text = f"🗄️ **مدیریت کش سیستم**\n\n"
    text += f"📊 **آمار فعلی:**\n"
    text += f"   حجم کش: {stats['size']}\n"
    text += f"   بازدیدها: {stats['hits']}\n"
    text += f"   از دست رفته: {stats['misses']}\n"
    text += f"   نرخ بازدید: {stats['hit_rate']}%\n\n"
    text += f"💡 پاک کردن کش باعث آزاد شدن حافظه می‌شود."
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_clear_cache")
def admin_clear_cache(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    cache.clear()
    bot.answer_callback_query(call.id, "✅ کش با موفقیت پاک شد!")
    admin_cache(call)

# ==================== خطاهای سیستم ====================
@bot.callback_query_handler(func=lambda call: call.data == "admin_errors")
def admin_errors(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    with get_db() as conn:
        errors = conn.execute("SELECT * FROM system_errors WHERE resolved = 0 ORDER BY timestamp DESC LIMIT 20").fetchall()
    
    if not errors:
        bot.send_message(call.message.chat.id, "✅ خطایی وجود ندارد!")
        return
    
    text = "⚠️ **خطاهای سیستم (حل‌نشده)**\n\n"
    for e in errors:
        text += f"**{e['type']}**\n"
        text += f"📝 {e['message'][:100]}...\n"
        text += f"👤 کاربر: {e['user_id'] if e['user_id'] else 'سیستم'}\n"
        text += f"🕐 {e['timestamp'][:16]}\n"
        text += f"🔑 `{e['id']}`\n\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ علامت‌گذاری همه به عنوان حل شده", callback_data="admin_resolve_errors"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back"))
    
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_resolve_errors")
def admin_resolve_errors(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    with get_db() as conn:
        conn.execute("UPDATE system_errors SET resolved = 1 WHERE resolved = 0")
        conn.commit()
    
    bot.answer_callback_query(call.id, "✅ تمام خطاها به عنوان حل شده علامت‌گذاری شدند!")

# ==================== پشتیبان ====================
@bot.callback_query_handler(func=lambda call: call.data == "admin_backup")
def admin_backup(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    backup_dir = os.path.join(DIRS['BACKUPS'], datetime.now().strftime("%Y%m%d_%H%M%S"))
    os.makedirs(backup_dir, exist_ok=True)
    
    status_msg = bot.send_message(call.message.chat.id, "🔄 در حال ایجاد پشتیبان...")
    
    try:
        # کپی دیتابیس
        shutil.copy2(DB_PATH, os.path.join(backup_dir, 'database.db'))
        
        # کپی فایل‌های مهم
        for dir_name in ['user_files', 'receipts', 'user_folders']:
            src = DIRS.get(dir_name.upper())
            if src and os.path.exists(src):
                dst = os.path.join(backup_dir, dir_name)
                shutil.copytree(src, dst, ignore_dangling_symlinks=True)
        
        # اطلاعات پشتیبان
        backup_size = sum(os.path.getsize(os.path.join(backup_dir, f)) for f in os.listdir(backup_dir) if os.path.isfile(os.path.join(backup_dir, f)))
        
        bot.edit_message_text(f"✅ **پشتیبان با موفقیت ایجاد شد!**\n\n"
                             f"📁 مسیر: `{backup_dir}`\n"
                             f"📦 حجم: {backup_size / (1024**2):.1f} MB\n"
                             f"🕐 زمان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                             call.message.chat.id, status_msg.message_id, parse_mode='Markdown')
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)}", call.message.chat.id, status_msg.message_id)

# ==================== فعال‌سازی دستی ====================
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
        expiry = activate_subscription(user_id)
        bot.reply_to(message, f"✅ اشتراک {user_id} تا {expiry.strftime('%Y-%m-%d')} فعال شد!")
        bot.send_message(user_id, f"✅ اشتراک شما توسط ادمین فعال شد!\n📅 تا {expiry.strftime('%Y-%m-%d')}\nحالا می‌توانید ربات بسازید.")
    except:
        bot.reply_to(message, "❌ خطا!")

# ==================== بازگشت به عقب ====================
@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    admin_panel(call.message)

# ==================== مانیتورینگ سیستم ====================
def monitor_system():
    while True:
        try:
            today = datetime.now().date().isoformat()
            active_users = 0
            with get_db() as conn:
                # به‌روزرسانی آمار روزانه
                conn.execute('''
                    INSERT INTO daily_stats (date, new_users, active_users, new_bots, active_bots, new_subscriptions, total_revenue, total_withdraw)
                    VALUES (?, 0, 0, 0, 0, 0, 0, 0)
                    ON CONFLICT(date) DO NOTHING
                ''', (today,))
                conn.commit()
            
            time.sleep(3600)
        except:
            time.sleep(60)

threading.Thread(target=monitor_system, daemon=True).start()

# ==================== اجرا ====================
if __name__ == "__main__":
    print("=" * 70)
    print("╔═════════════════════════════════════════════════════════════════════╗")
    print("║     🚀 ULTRA MOTHER BOT - ENTERPRISE EDITION v9.0                  ║")
    print("║     ⚡ Advanced Multi-Machine - High Performance                    ║")
    print("║     💰 Professional Bot Management System                          ║")
    print("╚═════════════════════════════════════════════════════════════════════╝")
    print("=" * 70)
    print(f"👑 ادمین: {ADMIN_IDS}")
    print(f"🤖 @{bot.get_me().username}")
    print(f"💰 قیمت اشتراک: {SUBSCRIPTION_PRICE_STR}")
    print(f"📌 حداکثر ربات: {MAX_BOTS_PER_USER}")
    print(f"💰 کمیسیون دعوت: {WITHDRAW_PERCENT}%")
    print(f"🖥️ ماشین‌ها: {len(MACHINES)} عدد")
    print(f"⚡ کش: فعال")
    print(f"🔒 ایزوله‌سازی: فعال")
    print("=" * 70)
    print("🔥 ربات با موفقیت راه‌اندازی شد!")
    print("=" * 70)
    
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=60)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)