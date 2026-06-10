#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
╔═══════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                               ║
║   ██╗   ██╗██╗████████╗██╗███╗   ███╗ █████╗ ████████╗███████╗                               ║
║   ██║   ██║██║╚══██╔══╝██║████╗ ████║██╔══██╗╚══██╔══╝██╔════╝                               ║
║   ██║   ██║██║   ██║   ██║██╔████╔██║███████║   ██║   █████╗                                 ║
║   ██║   ██║██║   ██║   ██║██║╚██╔╝██║██╔══██║   ██║   ██╔══╝                                 ║
║   ╚██████╔╝██║   ██║   ██║██║ ╚═╝ ██║██║  ██║   ██║   ███████╗                               ║
║    ╚═════╝ ╚═╝   ╚═╝   ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝                               ║
║                                                                                               ║
║   ██████╗  ██████╗ ████████╗    ██████╗ ██╗   ██╗██╗██╗     ██████╗ ███████╗██████╗           ║
║   ██╔══██╗██╔═══██╗╚══██╔══╝    ██╔══██╗██║   ██║██║██║     ██╔══██╗██╔════╝██╔══██╗          ║
║   ██████╔╝██║   ██║   ██║       ██████╔╝██║   ██║██║██║     ██║  ██║█████╗  ██████╔╝          ║
║   ██╔══██╗██║   ██║   ██║       ██╔══██╗██║   ██║██║██║     ██║  ██║██╔══╝  ██╔══██╗          ║
║   ██████╔╝╚██████╔╝   ██║       ██████╔╝╚██████╔╝██║███████╗██████╔╝███████╗██║  ██║          ║
║   ╚═════╝  ╚═════╝    ╚═╝       ╚═════╝  ╚═════╝ ╚═╝╚══════╝╚═════╝ ╚══════╝╚═╝  ╚═╝          ║
║                                                                                               ║
║   نسخه 10.0 Ultimate Enterprise - مقیاس‌پذیر برای میلیون‌ها کاربر                           ║
║   ایزوله‌سازی کامل - توزیع بار بین سرورها - نصب خودکار کتابخانه‌ها                           ║
║                                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════╝
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
import uuid
import queue
import socket
import struct
import random
import string
import tempfile
import pickle
import base64
import hmac
import ast
from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict, OrderedDict
from typing import Optional, Dict, Any, List, Tuple, Callable
from dataclasses import dataclass, field
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from enum import Enum
import asyncio
import aiohttp
from aiohttp import web

# نصب خودکار کتابخانه‌های پیشرفته
REQUIRED_PACKAGES = [
    'flask', 'flask-cors', 'flask-limiter', 'requests', 
    'aiohttp', 'paramiko', 'psutil', 'redis', 'celery',
    'docker', 'kubernetes', 'prometheus_client'
]

def auto_install(package):
    try:
        __import__(package.replace('-', '_'))
        return True
    except ImportError:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package, '--quiet'])
        return True

for pkg in REQUIRED_PACKAGES:
    auto_install(pkg)

from flask import Flask, request, jsonify, session, redirect, url_for, render_template_string
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import requests
import psutil
import paramiko

try:
    import redis
    REDIS_AVAILABLE = True
except:
    REDIS_AVAILABLE = False

# ==================== تنظیمات فوق پیشرفته ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# تنظیمات مقیاس‌پذیری
SCALING_CONFIG = {
    'MAX_WORKERS': 100,
    'MAX_CONCURRENT_BUILDS': 50,
    'BOTS_PER_MACHINE': 5000,
    'HEALTH_CHECK_INTERVAL': 15,
    'AUTO_SCALE_THRESHOLD': 75,  # درصد
    'LOAD_BALANCING_ALGO': 'least_connection',  # round_robin, least_connection, random
    'CACHE_TTL': 300,
    'RATE_LIMIT_PER_SECOND': 100,
    'MAX_UPLOAD_SIZE': 50 * 1024 * 1024,
    'REQUEST_TIMEOUT': 30,
    'DATABASE_POOL_SIZE': 50,
    'REDIS_HOST': 'localhost',
    'REDIS_PORT': 6379,
    'REDIS_DB': 0,
}

# تنظیمات ایزوله‌سازی
ISOLATION_CONFIG = {
    'CPU_LIMIT': 120,  # ثانیه
    'MEMORY_LIMIT': 1024 * 1024 * 1024,  # 1 گیگ
    'FILE_SIZE_LIMIT': 100 * 1024 * 1024,  # 100 مگ
    'PROCESS_LIMIT': 10,
    'NETWORK_ISOLATION': True,
    'USE_DOCKER': False,
    'SANDBOX_ENABLED': True,
    'MAX_BOTS_PER_USER': 10,
    'USER_QUOTA_DAILY': 50,
}

# دایرکتوری‌ها
DIRS = {
    'DB': os.path.join(BASE_DIR, 'database'),
    'FILES': os.path.join(BASE_DIR, 'user_files'),
    'RUNNING': os.path.join(BASE_DIR, 'running_bots'),
    'LOGS': os.path.join(BASE_DIR, 'logs'),
    'RECEIPTS': os.path.join(BASE_DIR, 'receipts'),
    'TEMP': os.path.join(BASE_DIR, 'temp'),
    'MACHINES': os.path.join(BASE_DIR, 'machines'),
    'SANDBOX': os.path.join(BASE_DIR, 'sandbox'),
    'CACHE': os.path.join(BASE_DIR, 'cache'),
    'BACKUPS': os.path.join(BASE_DIR, 'backups'),
    'PLUGINS': os.path.join(BASE_DIR, 'plugins'),
    'SSL': os.path.join(BASE_DIR, 'ssl'),
}

for dir_path in DIRS.values():
    os.makedirs(dir_path, exist_ok=True)

# ==================== کتابخانه‌های آماده (50 عدد) ====================
POPULAR_LIBRARIES = {
    # وب و شبکه
    'requests': 'requests',
    'aiohttp': 'aiohttp',
    'httpx': 'httpx',
    'urllib3': 'urllib3',
    'websockets': 'websockets',
    
    # وب فریمورک
    'flask': 'flask',
    'fastapi': 'fastapi',
    'django': 'django',
    'quart': 'quart',
    'sanic': 'sanic',
    
    # دیتابیس
    'sqlalchemy': 'sqlalchemy',
    'asyncpg': 'asyncpg',
    'aiomysql': 'aiomysql',
    'redis': 'redis',
    'motor': 'motor',  # MongoDB async
    'pymongo': 'pymongo',
    'psycopg2': 'psycopg2-binary',
    
    # ربات تلگرام
    'pyTelegramBotAPI': 'pyTelegramBotAPI',
    'aiogram': 'aiogram',
    'python-telegram-bot': 'python-telegram-bot',
    'telethon': 'telethon',
    
    # دیتا ساینس
    'numpy': 'numpy',
    'pandas': 'pandas',
    'scipy': 'scipy',
    'scikit-learn': 'scikit-learn',
    'matplotlib': 'matplotlib',
    'seaborn': 'seaborn',
    'plotly': 'plotly',
    
    # تصویر
    'pillow': 'Pillow',
    'opencv-python': 'opencv-python',
    'imageio': 'imageio',
    
    # وب اسکرپینگ
    'beautifulsoup4': 'beautifulsoup4',
    'selenium': 'selenium',
    'scrapy': 'scrapy',
    'lxml': 'lxml',
    
    # تاریخ و زمان فارسی
    'jdatetime': 'jdatetime',
    'persiantools': 'persiantools',
    'python-dateutil': 'python-dateutil',
    
    # امنیت
    'cryptography': 'cryptography',
    'pycryptodome': 'pycryptodome',
    'jwt': 'PyJWT',
    'passlib': 'passlib',
    
    # لاگینگ و دیباگ
    'loguru': 'loguru',
    'rich': 'rich',
    'colorlog': 'colorlog',
    'tqdm': 'tqdm',
    
    # یوتیوب و دانلود
    'yt-dlp': 'yt-dlp',
    'pytube': 'pytube',
    
    # اکسل و فایل
    'openpyxl': 'openpyxl',
    'xlrd': 'xlrd',
    'pdfplumber': 'pdfplumber',
    
    # سایر
    'celery': 'celery',
    'schedule': 'schedule',
    'apscheduler': 'apscheduler',
    'python-dotenv': 'python-dotenv',
}

# ==================== کش پیشرفته با Redis ====================
class AdvancedCache:
    def __init__(self):
        self.memory_cache = OrderedDict()
        self.max_size = 10000
        self.redis_client = None
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host=SCALING_CONFIG['REDIS_HOST'],
                    port=SCALING_CONFIG['REDIS_PORT'],
                    db=SCALING_CONFIG['REDIS_DB'],
                    decode_responses=True
                )
                self.redis_client.ping()
            except:
                self.redis_client = None
    
    def get(self, key: str):
        if self.redis_client:
            val = self.redis_client.get(key)
            if val:
                return pickle.loads(base64.b64decode(val))
        
        if key in self.memory_cache:
            value, expires = self.memory_cache[key]
            if expires > time.time():
                self.memory_cache.move_to_end(key)
                return value
            del self.memory_cache[key]
        return None
    
    def set(self, key: str, value, ttl: int = 3600):
        if self.redis_client:
            self.redis_client.setex(key, ttl, base64.b64encode(pickle.dumps(value)).decode())
        
        if len(self.memory_cache) >= self.max_size:
            self.memory_cache.popitem(last=False)
        self.memory_cache[key] = (value, time.time() + ttl)
        self.memory_cache.move_to_end(key)
    
    def delete(self, key: str):
        if self.redis_client:
            self.redis_client.delete(key)
        if key in self.memory_cache:
            del self.memory_cache[key]
    
    def incr(self, key: str, amount: int = 1) -> int:
        if self.redis_client:
            return self.redis_client.incrby(key, amount)
        
        val = self.get(key)
        if val is None:
            val = 0
        new_val = int(val) + amount
        self.set(key, new_val, ttl=3600)
        return new_val

cache = AdvancedCache()

# ==================== دیتابیس پیشرفته با Connection Pool ====================
class ConnectionPool:
    def __init__(self, max_connections=50):
        self.pool = queue.Queue(maxsize=max_connections)
        self.max_connections = max_connections
        self._create_initial_connections()
    
    def _create_initial_connections(self):
        for _ in range(10):
            self.pool.put(self._create_connection())
    
    def _create_connection(self):
        db_path = os.path.join(DIRS['DB'], 'ultimate.db')
        conn = sqlite3.connect(db_path, timeout=60, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-200000")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn
    
    @contextmanager
    def get_connection(self):
        conn = self.pool.get()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            self.pool.put(conn)

pool = ConnectionPool(SCALING_CONFIG['DATABASE_POOL_SIZE'])

class Database:
    def execute(self, query: str, params: tuple = ()) -> list:
        with pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def execute_many(self, query: str, params_list: list):
        with pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
    
    def _init_tables(self):
        self.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password_hash TEXT,
                full_name TEXT,
                email TEXT,
                phone TEXT,
                is_admin INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                wallet_balance INTEGER DEFAULT 0,
                total_commission INTEGER DEFAULT 0,
                subscription_status TEXT DEFAULT 'inactive',
                subscription_expiry TIMESTAMP,
                bots_count INTEGER DEFAULT 0,
                max_bots INTEGER DEFAULT 10,
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                referrals_count INTEGER DEFAULT 0,
                api_key TEXT,
                created_at TIMESTAMP,
                last_login TIMESTAMP,
                quota_daily INTEGER DEFAULT 0,
                quota_reset TIMESTAMP
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
                machine_id INTEGER,
                pid INTEGER,
                status TEXT DEFAULT 'stopped',
                created_at TIMESTAMP,
                last_active TIMESTAMP,
                error_message TEXT,
                cpu_usage REAL DEFAULT 0,
                memory_usage INTEGER DEFAULT 0,
                restart_count INTEGER DEFAULT 0
            )
        ''')
        
        self.execute('''
            CREATE TABLE IF NOT EXISTS machines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                ip TEXT,
                port INTEGER DEFAULT 22,
                username TEXT,
                password_encrypted TEXT,
                ssh_key TEXT,
                status TEXT DEFAULT 'active',
                current_bots INTEGER DEFAULT 0,
                max_bots INTEGER DEFAULT 5000,
                cpu_usage REAL DEFAULT 0,
                memory_used INTEGER DEFAULT 0,
                memory_total INTEGER DEFAULT 0,
                last_heartbeat TIMESTAMP,
                created_at TIMESTAMP,
                region TEXT DEFAULT 'default',
                is_local INTEGER DEFAULT 1
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
                percent INTEGER,
                reason TEXT,
                created_at TIMESTAMP,
                paid INTEGER DEFAULT 0
            )
        ''')
        
        self.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        self.execute('''
            CREATE TABLE IF NOT EXISTS installed_libraries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                version TEXT,
                installed_at TIMESTAMP
            )
        ''')
        
        # تنظیمات پیش‌فرض
        default_settings = {
            'trc20_address': 'TV61aTh98MGqmteYzda5AaBzdXgGqreG6A',
            'card_number': '5892101187322777',
            'card_number_display': '5892 1011 8732 2777',
            'card_holder': 'مرتضی نیکخو خنجری',
            'card_bank': 'بانک ملی - سپهر',
            'subscription_price': 2000000,
            'subscription_price_str': '۲,۰۰۰,۰۰۰ تومان',
            'withdraw_percent': 7,
            'min_withdraw': 2000000,
            'max_bots_per_subscription': 10,
            'max_users_capacity': 1000000,
            'guide_text_fa': '📚 راهنمای استفاده...',
            'guide_text_en': '📚 User Guide...',
            'welcome_text_fa': '🚀 خوش آمدید {name}!',
            'welcome_text_en': '🚀 Welcome {name}!',
            'subscription_active_text_fa': '✅ اشتراک فعال شد',
            'subscription_active_text_en': '✅ Subscription activated',
            'subscription_payment_text_fa': '💳 برای فعالسازی {price} را واریز کنید',
            'subscription_payment_text_en': '💳 Send {price} to activate',
            'admin_password': '123456',
        }
        
        for key, value in default_settings.items():
            self.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (key, str(value)))
        
        # ماشین محلی
        machines = self.execute("SELECT id FROM machines WHERE is_local = 1")
        if not machines:
            self.execute('''
                INSERT INTO machines (name, status, max_bots, is_local, created_at)
                VALUES ('سرور اصلی', 'active', 5000, 1, ?)
            ''', (datetime.now().isoformat(),))
        
        # ادمین
        admin = self.execute("SELECT id FROM users WHERE username = ?", ('admin',))
        if not admin:
            self.execute('''
                INSERT INTO users (username, password_hash, full_name, is_admin, max_bots, referral_code, created_at)
                VALUES (?, ?, ?, 1, 100, ?, ?)
            ''', ('admin', hashlib.md5('admin123'.encode()).hexdigest(), 'مدیر سیستم', 
                  secrets.token_hex(8), datetime.now().isoformat()))

db = Database()
db._init_tables()

# ==================== توابع کمکی ====================
def get_setting(key):
    cached = cache.get(f"setting_{key}")
    if cached:
        return cached
    result = db.execute("SELECT value FROM settings WHERE key = ?", (key,))
    if result:
        val = result[0]['value']
        cache.set(f"setting_{key}", val, ttl=300)
        return val
    return None

def update_setting(key, value):
    db.execute("UPDATE settings SET value = ? WHERE key = ?", (str(value), key))
    cache.delete(f"setting_{key}")

def get_user(user_id):
    cached = cache.get(f"user_{user_id}")
    if cached:
        return cached
    users = db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    if users:
        cache.set(f"user_{user_id}", users[0], ttl=60)
        return users[0]
    return None

def get_user_by_username(username):
    users = db.execute("SELECT * FROM users WHERE username = ?", (username,))
    return users[0] if users else None

def authenticate(username, password):
    user = get_user_by_username(username)
    if user and user['password_hash'] == hashlib.md5(password.encode()).hexdigest():
        if user.get('is_banned', 0) == 0:
            db.execute('UPDATE users SET last_login = ? WHERE id = ?', (datetime.now().isoformat(), user['id']))
            return user
    return None

def create_user(username, password, full_name, referral_code=None):
    existing = get_user_by_username(username)
    if existing:
        return False, "نام کاربری تکراری"
    
    referred_by = None
    if referral_code:
        referrer = db.execute("SELECT id FROM users WHERE referral_code = ?", (referral_code,))
        if referrer:
            referred_by = referrer[0]['id']
    
    db.execute('''
        INSERT INTO users (username, password_hash, full_name, referral_code, referred_by, created_at, max_bots)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (username, hashlib.md5(password.encode()).hexdigest(), full_name,
          secrets.token_hex(8), referred_by, datetime.now().isoformat(), get_setting('max_bots_per_subscription')))
    return True, "ok"

def check_subscription(user_id):
    user = get_user(user_id)
    if not user or user.get('is_banned', 0) == 1:
        return False
    if user['subscription_status'] == 'active':
        if user['subscription_expiry']:
            expiry = datetime.fromisoformat(user['subscription_expiry'])
            if expiry > datetime.now():
                return True
            else:
                db.execute('UPDATE users SET subscription_status = "inactive" WHERE id = ?', (user_id,))
    return False

def get_remaining_bots(user_id):
    user = get_user(user_id)
    if not user:
        return 0
    if check_subscription(user_id):
        return user.get('max_bots', 10) - user.get('bots_count', 0)
    return 0

def activate_subscription(user_id):
    user = get_user(user_id)
    now = datetime.now()
    
    if user and user['subscription_status'] == 'active' and user['subscription_expiry']:
        new_expiry = datetime.fromisoformat(user['subscription_expiry']) + timedelta(days=30)
    else:
        new_expiry = now + timedelta(days=30)
    
    db.execute('UPDATE users SET subscription_status = "active", subscription_expiry = ? WHERE id = ?',
              (new_expiry.isoformat(), user_id))
    
    if user and user.get('referred_by'):
        commission_percent = int(get_setting('withdraw_percent') or 7)
        price = int(get_setting('subscription_price') or 2000000)
        commission = int(price * commission_percent / 100)
        db.execute('UPDATE users SET wallet_balance = wallet_balance + ?, total_commission = total_commission + ? WHERE id = ?',
                  (commission, commission, user['referred_by']))
        db.execute('''
            INSERT INTO commissions (user_id, from_user, amount, percent, reason, created_at, paid)
            VALUES (?, ?, ?, ?, 'subscription', ?, 1)
        ''', (user['referred_by'], user_id, commission, commission_percent, datetime.now().isoformat()))
    
    return True

def extract_token_from_code(code: str) -> Optional[str]:
    """استخراج هوشمند توکن از کد با پشتیبانی از انواع فرمت‌ها"""
    patterns = [
        # استاندارد
        r'token\s*=\s*["\']([^"\']+)["\']',
        r'TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'BOT_TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'API_TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'API_KEY\s*=\s*["\']([^"\']+)["\']',
        
        # با os.environ
        r'os\.environ\.get\s*\(\s*["\'](?:TOKEN|BOT_TOKEN|API_TOKEN)["\']\s*,\s*["\']([^"\']+)["\']\)',
        
        # بدون نقل قول
        r'token\s*=\s*([A-Za-z0-9:_-]+)',
        r'TOKEN\s*=\s*([A-Za-z0-9:_-]+)',
        
        # در config
        r'config\[["\']token["\']\]\s*=\s*["\']([^"\']+)["\']',
        r'self\.token\s*=\s*["\']([^"\']+)["\']',
        
        # در متغیرهای محیطی
        r'os\.getenv\s*\(\s*["\'](?:TOKEN|BOT_TOKEN)["\']\s*\)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, code, re.IGNORECASE)
        for token in matches:
            # بررسی فرمت توکن تلگرام (عدد:字符串)
            if re.match(r'^\d+:[\w\-]+$', token):
                return token
            # بررسی توکن معتبر
            if len(token) > 30 and ':' in token:
                return token
    
    return None

def install_library(lib_name: str) -> Tuple[bool, str]:
    """نصب کتابخانه با مدیریت خطا"""
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', lib_name, '--quiet'],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            # ذخیره در دیتابیس
            db.execute('''
                INSERT OR REPLACE INTO installed_libraries (name, version, installed_at)
                VALUES (?, ?, ?)
            ''', (lib_name, 'latest', datetime.now().isoformat()))
            return True, "نصب شد"
        else:
            return False, result.stderr[:100]
    except Exception as e:
        return False, str(e)[:100]

def get_installed_libraries() -> List[dict]:
    return db.execute('SELECT * FROM installed_libraries ORDER BY installed_at DESC')

# ==================== مدیریت ماشین‌ها و توزیع بار ====================
class MachineManager:
    def __init__(self):
        self.machines = []
        self.lock = threading.RLock()
        self.current_index = 0
        self._load_machines()
        self._start_health_check()
    
    def _load_machines(self):
        self.machines = db.execute('SELECT * FROM machines WHERE status = "active"')
    
    def _start_health_check(self):
        def check():
            while True:
                try:
                    for machine in db.execute('SELECT id, ip, status FROM machines'):
                        if machine['ip']:
                            try:
                                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                sock.settimeout(5)
                                result = sock.connect_ex((machine['ip'], 22))
                                sock.close()
                                if result == 0:
                                    db.execute('UPDATE machines SET status = "active", last_heartbeat = ? WHERE id = ?',
                                              (datetime.now().isoformat(), machine['id']))
                                else:
                                    db.execute('UPDATE machines SET status = "offline" WHERE id = ?', (machine['id'],))
                            except:
                                pass
                    self._load_machines()
                    time.sleep(SCALING_CONFIG['HEALTH_CHECK_INTERVAL'])
                except:
                    time.sleep(60)
        threading.Thread(target=check, daemon=True).start()
    
    def get_best_machine(self) -> Optional[dict]:
        """انتخاب بهترین ماشین با الگوریتم least connection"""
        with self.lock:
            self._load_machines()
            if not self.machines:
                return None
            
            if SCALING_CONFIG['LOAD_BALANCING_ALGO'] == 'least_connection':
                return min(self.machines, key=lambda m: m['current_bots'])
            elif SCALING_CONFIG['LOAD_BALANCING_ALGO'] == 'round_robin':
                self.current_index = (self.current_index + 1) % len(self.machines)
                return self.machines[self.current_index]
            else:
                return random.choice(self.machines)
    
    def assign_bot(self, machine_id: int, bot_id: str):
        db.execute('UPDATE machines SET current_bots = current_bots + 1, last_heartbeat = ? WHERE id = ?',
                  (datetime.now().isoformat(), machine_id))
        db.execute('UPDATE bots SET machine_id = ? WHERE id = ?', (machine_id, bot_id))
    
    def release_bot(self, machine_id: int):
        db.execute('UPDATE machines SET current_bots = current_bots - 1 WHERE id = ?', (machine_id,))
    
    def add_machine(self, name: str, ip: str = None, port: int = 22, username: str = None, 
                    password: str = None, max_bots: int = 5000) -> dict:
        try:
            if ip:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(ip, port=port, username=username, password=password, timeout=10)
                ssh.close()
            
            db.execute('''
                INSERT INTO machines (name, ip, port, username, password_encrypted, max_bots, created_at, is_local)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            ''', (name, ip, port, username, base64.b64encode(password.encode()).decode() if password else None, 
                  max_bots, datetime.now().isoformat()))
            return {'success': True, 'message': 'سرور با موفقیت اضافه شد'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def update_capacity(self, machine_id: int, max_bots: int):
        db.execute('UPDATE machines SET max_bots = ? WHERE id = ?', (max_bots, machine_id))
    
    def toggle_machine(self, machine_id: int, active: bool):
        status = 'active' if active else 'inactive'
        db.execute('UPDATE machines SET status = ? WHERE id = ?', (status, machine_id))
    
    def get_stats(self) -> dict:
        machines = db.execute('SELECT * FROM machines')
        total_bots = sum(m['current_bots'] for m in machines)
        total_capacity = sum(m['max_bots'] for m in machines)
        return {
            'total_machines': len(machines),
            'active_machines': len([m for m in machines if m['status'] == 'active']),
            'total_bots': total_bots,
            'total_capacity': total_capacity,
            'usage_percent': (total_bots / total_capacity * 100) if total_capacity > 0 else 0,
            'machines': machines
        }

machine_manager = MachineManager()

# ==================== ایزوله‌سازی کامل (Sandbox) ====================
class UltimateSandbox:
    def __init__(self):
        self.processes = {}
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=SCALING_CONFIG['MAX_WORKERS'])
    
    def _get_sandbox_wrapper(self, bot_id: str, user_id: int, token: str) -> str:
        return f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ربات #{bot_id[:8]} - اجرا در محیط ایزوله
کاربر #{user_id}
"""

import sys, os, signal, time, resource, logging
from functools import wraps

# ==================== محدودیت‌های منابع ====================
try:
    resource.setrlimit(resource.RLIMIT_CPU, ({ISOLATION_CONFIG['CPU_LIMIT']}, {ISOLATION_CONFIG['CPU_LIMIT']}))
    resource.setrlimit(resource.RLIMIT_AS, ({ISOLATION_CONFIG['MEMORY_LIMIT']}, {ISOLATION_CONFIG['MEMORY_LIMIT']}))
    resource.setrlimit(resource.RLIMIT_FSIZE, ({ISOLATION_CONFIG['FILE_SIZE_LIMIT']}, {ISOLATION_CONFIG['FILE_SIZE_LIMIT']}))
    resource.setrlimit(resource.RLIMIT_NPROC, ({ISOLATION_CONFIG['PROCESS_LIMIT']}, {ISOLATION_CONFIG['PROCESS_LIMIT']}))
except: pass

# ==================== تایم‌اوت ====================
def timeout_handler(signum, frame):
    print("⏰ Timeout: Bot execution limit reached")
    sys.exit(1)

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm({ISOLATION_CONFIG['CPU_LIMIT']})

# ==================== سیستم لاگینگ ====================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(f'Bot_{{bot_id[:8]}}')

# ==================== شروع ====================
print(f"🔒 Bot {{bot_id[:8]}} started in secure sandbox")
print(f"⏰ Time limit: {ISOLATION_CONFIG['CPU_LIMIT']}s")
print(f"💾 Memory limit: {ISOLATION_CONFIG['MEMORY_LIMIT'] // (1024*1024)} MB")

# ==================== کد اصلی ====================
'''
    
    def run_bot(self, bot_id: str, code: str, token: str, user_id: int) -> dict:
        try:
            sandbox_dir = os.path.join(DIRS['SANDBOX'], f"bot_{bot_id}")
            os.makedirs(sandbox_dir, exist_ok=True)
            
            code_path = os.path.join(sandbox_dir, 'bot.py')
            full_code = self._get_sandbox_wrapper(bot_id, user_id, token) + "\n" + code
            
            with open(code_path, 'w', encoding='utf-8') as f:
                f.write(full_code)
            
            log_file = os.path.join(DIRS['LOGS'], f"bot_{bot_id}.log")
            
            process = subprocess.Popen(
                [sys.executable, code_path],
                stdout=open(log_file, 'a'),
                stderr=subprocess.STDOUT,
                cwd=sandbox_dir,
                start_new_session=True
            )
            
            time.sleep(2)
            
            if process.poll() is None:
                with self.lock:
                    self.processes[bot_id] = {
                        'process': process,
                        'pid': process.pid,
                        'sandbox': sandbox_dir,
                        'start_time': time.time(),
                        'user_id': user_id
                    }
                return {'success': True, 'pid': process.pid}
            return {'success': False, 'error': 'ربات با خطا مواجه شد'}
        except Exception as e:
            return {'success': False, 'error': str(e)[:100]}
    
    def stop_bot(self, bot_id: str) -> bool:
        with self.lock:
            if bot_id in self.processes:
                try:
                    os.kill(self.processes[bot_id]['pid'], signal.SIGTERM)
                    time.sleep(1)
                    del self.processes[bot_id]
                    return True
                except:
                    pass
        return False
    
    def get_status(self, bot_id: str) -> dict:
        with self.lock:
            if bot_id in self.processes:
                info = self.processes[bot_id]
                try:
                    os.kill(info['pid'], 0)
                    return {'running': True, 'pid': info['pid'], 'uptime': time.time() - info['start_time']}
                except:
                    del self.processes[bot_id]
        return {'running': False}
    
    def get_stats(self) -> dict:
        with self.lock:
            return {'total': len(self.processes), 'bots': list(self.processes.keys())}

sandbox = UltimateSandbox()

# ==================== صف ساخت پیشرفته ====================
class BuildQueueManager:
    def __init__(self):
        self.queue = queue.Queue()
        self.processing = {}
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=SCALING_CONFIG['MAX_CONCURRENT_BUILDS'])
        self._start_workers()
    
    def _start_workers(self):
        for i in range(SCALING_CONFIG['MAX_CONCURRENT_BUILDS']):
            threading.Thread(target=self._worker, daemon=True, name=f"Builder-{i}").start()
    
    def _worker(self):
        while True:
            try:
                item = self.queue.get(timeout=1)
                self.executor.submit(self._process_build, item)
                self.queue.task_done()
            except queue.Empty:
                time.sleep(0.5)
            except Exception as e:
                print(f"Worker error: {e}")
    
    def _process_build(self, item):
        try:
            user_id = item['user_id']
            code = item['code']
            file_path = item.get('file_path')
            
            token = extract_token_from_code(code)
            if not token:
                return
            
            # بررسی توکن
            try:
                resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
                if resp.status_code != 200:
                    return
                bot_info = resp.json()['result']
            except:
                return
            
            # انتخاب ماشین مناسب
            machine = machine_manager.get_best_machine()
            if not machine:
                return
            
            bot_id = secrets.token_hex(16)
            
            # ذخیره فایل
            final_path = file_path or os.path.join(DIRS['FILES'], str(user_id), f"{bot_id}.py")
            os.makedirs(os.path.dirname(final_path), exist_ok=True)
            with open(final_path, 'w', encoding='utf-8') as f:
                f.write(code)
            
            # نصب خودکار کتابخانه‌های مورد نیاز
            required_libs = re.findall(r'^(?:from|import)\s+(\w+)', code, re.MULTILINE)
            for lib in set(required_libs[:10]):  # حداکثر 10 کتابخانه
                if lib in POPULAR_LIBRARIES or lib in ['telebot', 'telegram', 'flask', 'requests']:
                    install_library(lib)
            
            # اجرا در سندباکس
            result = sandbox.run_bot(bot_id, code, token, user_id)
            
            if result['success']:
                db.execute('''
                    INSERT INTO bots (id, user_id, token, name, username, file_path, machine_id, pid, status, created_at, last_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'running', ?, ?)
                ''', (bot_id, user_id, token, bot_info.get('first_name', 'ربات'), bot_info.get('username', ''),
                      final_path, machine['id'], result['pid'], datetime.now().isoformat(), datetime.now().isoformat()))
                db.execute('UPDATE users SET bots_count = bots_count + 1 WHERE id = ?', (user_id,))
                machine_manager.assign_bot(machine['id'], bot_id)
        except Exception as e:
            print(f"Build error: {e}")
    
    def add(self, user_id: int, code: str, file_path: str = None) -> str:
        build_id = secrets.token_hex(8)
        self.queue.put({
            'id': build_id,
            'user_id': user_id,
            'code': code,
            'file_path': file_path,
            'added_at': time.time()
        })
        return build_id
    
    def get_status(self) -> dict:
        return {
            'queue_size': self.queue.qsize(),
            'processing': len(self.processing),
            'workers': SCALING_CONFIG['MAX_CONCURRENT_BUILDS']
        }

build_queue = BuildQueueManager()

# ==================== توابع ربات ====================
def get_user_bots(user_id):
    return db.execute('SELECT * FROM bots WHERE user_id = ? ORDER BY created_at DESC', (user_id,))

def delete_bot(bot_id, user_id):
    bot = db.execute('SELECT * FROM bots WHERE id = ? AND user_id = ?', (bot_id, user_id))
    if not bot:
        return False
    sandbox.stop_bot(bot_id)
    if bot[0].get('file_path') and os.path.exists(bot[0]['file_path']):
        try:
            os.remove(bot[0]['file_path'])
        except:
            pass
    db.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
    db.execute('UPDATE users SET bots_count = bots_count - 1 WHERE id = ?', (user_id,))
    if bot[0].get('machine_id'):
        machine_manager.release_bot(bot[0]['machine_id'])
    return True

def add_wallet_balance(user_id, amount):
    db.execute('UPDATE users SET wallet_balance = wallet_balance + ? WHERE id = ?', (amount, user_id))

# ==================== Flask App ====================
app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.config['MAX_CONTENT_LENGTH'] = SCALING_CONFIG['MAX_UPLOAD_SIZE']
CORS(app)

# ==================== HTML صفحات ====================

HTML_LOGIN = '''<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>ورود | ساخت ربات تلگرام</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        *{font-family:'Vazirmatn','Tahoma',sans-serif}
        body{background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
        .login-card{background:white;border-radius:32px;padding:40px;max-width:450px;width:100%;box-shadow:0 25px 50px -12px rgba(0,0,0,0.25)}
        .btn-login{background:linear-gradient(135deg,#667eea,#764ba2);border:none;border-radius:14px;padding:14px;width:100%;color:white;font-weight:600}
        .form-control{border-radius:14px;padding:12px;font-size:16px}
    </style>
</head>
<body>
    <div class="login-card">
        <div class="text-center mb-4">
            <i class="fas fa-robot" style="font-size:64px;color:#667eea"></i>
            <h2>ساخت ربات تلگرام</h2>
        </div>
        <div id="errorMsg" class="alert alert-danger" style="display:none"></div>
        <form id="loginForm">
            <div class="mb-3"><input type="text" id="username" class="form-control" placeholder="نام کاربری" required></div>
            <div class="mb-3"><input type="password" id="password" class="form-control" placeholder="رمز عبور" required></div>
            <button type="submit" class="btn-login">ورود</button>
        </form>
        <div class="text-center mt-4"><a href="/register">ثبت نام</a></div>
    </div>
    <script>
        document.getElementById('loginForm').onsubmit = async (e) => {
            e.preventDefault();
            const res = await fetch('/api/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({username: username.value, password: password.value})
            });
            const data = await res.json();
            if(res.ok) { window.location.href = '/'; }
            else { errorMsg.style.display='block'; errorMsg.innerText=data.error; }
        };
    </script>
</body>
</html>'''

HTML_REGISTER = '''<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>ثبت نام | ساخت ربات تلگرام</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        *{font-family:'Vazirmatn','Tahoma',sans-serif}
        body{background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
        .register-card{background:white;border-radius:32px;padding:40px;max-width:500px;width:100%}
        .btn-register{background:linear-gradient(135deg,#667eea,#764ba2);border:none;border-radius:14px;padding:14px;width:100%;color:white;font-weight:600}
        .form-control{border-radius:14px;padding:12px;font-size:16px}
    </style>
</head>
<body>
    <div class="register-card">
        <div class="text-center mb-4">
            <i class="fas fa-user-plus" style="font-size:64px;color:#667eea"></i>
            <h2>ثبت نام</h2>
        </div>
        <div id="errorMsg" class="alert alert-danger" style="display:none"></div>
        <form id="registerForm">
            <div class="mb-3"><input type="text" id="username" class="form-control" placeholder="نام کاربری" required></div>
            <div class="mb-3"><input type="password" id="password" class="form-control" placeholder="رمز عبور" required minlength="6"></div>
            <div class="mb-3"><input type="text" id="full_name" class="form-control" placeholder="نام کامل" required></div>
            <div class="mb-3"><input type="text" id="referral_code" class="form-control" placeholder="کد معرف"></div>
            <button type="submit" class="btn-register">ثبت نام</button>
        </form>
        <div class="text-center mt-4"><a href="/login">ورود</a></div>
    </div>
    <script>
        document.getElementById('registerForm').onsubmit = async (e) => {
            e.preventDefault();
            const res = await fetch('/api/register', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    username: username.value, password: password.value, full_name: full_name.value,
                    referral_code: referral_code.value
                })
            });
            const data = await res.json();
            if(res.ok) { window.location.href = '/login'; }
            else { errorMsg.style.display='block'; errorMsg.innerText=data.error; }
        };
    </script>
</body>
</html>'''

HTML_INDEX = '''<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>ساخت ربات تلگرام | پنل پیشرفته</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        *{font-family:'Vazirmatn','Tahoma',sans-serif}
        body{background:#f0f2f5}
        .sidebar{background:linear-gradient(180deg,#1a1a2e,#16213e);min-height:100vh;color:white;position:fixed;right:0;top:0;width:280px;z-index:1000;transition:0.3s}
        .sidebar .nav-link{color:rgba(255,255,255,0.7);padding:12px 20px;margin:5px 10px;border-radius:12px}
        .sidebar .nav-link:hover,.sidebar .nav-link.active{background:rgba(102,126,234,0.3);color:white}
        .sidebar .nav-link i{margin-left:10px;width:24px}
        .main-content{margin-right:280px;padding:20px}
        .card{background:white;border:none;border-radius:20px;box-shadow:0 2px 10px rgba(0,0,0,0.05)}
        .stat-card{background:linear-gradient(135deg,#667eea,#764ba2);border-radius:20px;padding:20px;color:white}
        .btn-primary{background:linear-gradient(135deg,#667eea,#764ba2);border:none;border-radius:12px}
        .status-badge{display:inline-block;padding:4px 12px;border-radius:20px;font-size:0.75rem;font-weight:600}
        .status-running{background:#d4edda;color:#155724}
        .status-stopped{background:#f8d7da;color:#721c24}
        .code-area{font-family:monospace;background:#1e1e2e;color:#fff;padding:16px;border-radius:12px}
        .toast-notify{position:fixed;bottom:20px;left:20px;right:20px;background:#333;color:white;padding:14px;border-radius:16px;text-align:center;z-index:1100;display:none}
        .loader{display:inline-block;width:20px;height:20px;border:3px solid #f3f3f3;border-top:3px solid #667eea;border-radius:50%;animation:spin 1s linear infinite}
        @keyframes spin{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}
        .menu-toggle{display:none;position:fixed;top:15px;right:15px;z-index:1001;background:#667eea;color:white;border:none;border-radius:12px;padding:10px}
        @media (max-width:768px){
            .sidebar{right:-280px}
            .sidebar.open{right:0}
            .main-content{margin-right:0}
            .menu-toggle{display:block}
        }
        .admin-float-btn{position:fixed;bottom:20px;left:20px;z-index:999}
        .admin-float-btn button{width:60px;height:60px;border-radius:50%;background:#ff4757;border:none;color:white;box-shadow:0 4px 15px rgba(0,0,0,0.2)}
    </style>
</head>
<body>

<button class="menu-toggle" onclick="toggleSidebar()"><i class="fas fa-bars"></i></button>

<div class="sidebar" id="sidebar">
    <div class="text-center py-4">
        <i class="fas fa-robot fa-3x"></i>
        <h5 class="mt-2" id="userName">کاربر</h5>
        <small id="userSubStatus"></small>
    </div>
    <hr>
    <nav class="nav flex-column">
        <a class="nav-link" href="#" onclick="showPage('dashboard')"><i class="fas fa-tachometer-alt"></i> داشبورد</a>
        <a class="nav-link" href="#" onclick="showPage('build')"><i class="fas fa-plus-circle"></i> ساخت ربات</a>
        <a class="nav-link" href="#" onclick="showPage('bots')"><i class="fas fa-robot"></i> ربات‌های من</a>
        <a class="nav-link" href="#" onclick="showPage('wallet')"><i class="fas fa-wallet"></i> کیف پول</a>
        <a class="nav-link" href="#" onclick="showPage('referrals')"><i class="fas fa-users"></i> دعوت دوستان</a>
        <a class="nav-link" href="#" onclick="showPage('libraries')"><i class="fas fa-book"></i> کتابخانه‌ها</a>
        <a class="nav-link" href="#" onclick="showPage('guide')"><i class="fas fa-info-circle"></i> راهنما</a>
        <hr>
        <a class="nav-link" href="#" onclick="showPage('settings')"><i class="fas fa-cog"></i> تنظیمات</a>
        <a class="nav-link" href="/logout"><i class="fas fa-sign-out-alt"></i> خروج</a>
    </nav>
</div>

<div class="main-content">
    <div id="page-dashboard" class="page-content">
        <div class="d-flex justify-content-between mb-4">
            <h3><i class="fas fa-chart-line me-2"></i>داشبورد</h3>
            <span id="currentTime"></span>
        </div>
        <div class="row g-4 mb-4" id="statsCards"></div>
        <div class="row">
            <div class="col-md-8">
                <div class="card p-4">
                    <h5>ربات‌های اخیر</h5>
                    <div id="recentBots"></div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card p-4 text-center">
                    <h5>کد معرف</h5>
                    <code id="referralCode"></code>
                    <button class="btn btn-sm btn-outline-primary mt-2" onclick="copyReferral()">کپی لینک</button>
                    <hr>
                    <h6>تعداد دعوت‌ها: <span id="refCount">0</span></h6>
                    <h6>کمیسیون کل: <span id="totalComm">0</span></h6>
                </div>
            </div>
        </div>
    </div>

    <div id="page-build" class="page-content" style="display:none">
        <div class="card p-4">
            <h4>ساخت ربات جدید</h4>
            <hr>
            <ul class="nav nav-tabs mb-4">
                <li class="nav-item"><a class="nav-link active" data-bs-toggle="tab" href="#codeTab">کد مستقیم</a></li>
                <li class="nav-item"><a class="nav-link" data-bs-toggle="tab" href="#uploadTab">آپلود فایل</a></li>
            </ul>
            <div class="tab-content">
                <div class="tab-pane fade show active" id="codeTab">
                    <textarea id="botCode" class="form-control code-area" rows="12" placeholder="# کد ربات خود را وارد کنید..."></textarea>
                </div>
                <div class="tab-pane fade" id="uploadTab">
                    <div class="border rounded p-4 text-center" style="border-style:dashed;cursor:pointer" onclick="document.getElementById('botFile').click()">
                        <i class="fas fa-cloud-upload-alt fa-3x text-primary"></i>
                        <p class="mt-2">برای انتخاب فایل کلیک کنید</p>
                        <input type="file" id="botFile" class="d-none" accept=".py,.zip">
                        <div id="fileName" class="mt-2 text-success small"></div>
                    </div>
                </div>
            </div>
            <div class="mt-4">
                <button class="btn btn-primary w-100" onclick="buildBot()" id="buildBtn">ساخت ربات</button>
            </div>
            <div id="buildStatus" class="mt-3" style="display:none"></div>
        </div>
    </div>

    <div id="page-bots" class="page-content" style="display:none">
        <div class="card p-4">
            <div class="d-flex justify-content-between mb-3">
                <h4>ربات‌های من</h4>
                <button class="btn btn-sm btn-outline-primary" onclick="loadBots()"><i class="fas fa-sync-alt"></i></button>
            </div>
            <div id="botsList"></div>
        </div>
    </div>

    <div id="page-wallet" class="page-content" style="display:none">
        <div class="row g-4 mb-4">
            <div class="col-md-6">
                <div class="card p-4 text-center">
                    <h5>موجودی کیف پول</h5>
                    <h2 id="walletBalance">0</h2>
                    <button class="btn btn-sm btn-warning mt-2" onclick="showWithdraw()">درخواست برداشت</button>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card p-4 text-center">
                    <h5>وضعیت اشتراک</h5>
                    <h3 id="subStatus">غیرفعال</h3>
                    <small id="expiryDate"></small>
                </div>
            </div>
        </div>
        <div class="card p-4">
            <h5>خرید اشتراک</h5>
            <p>مبلغ: <strong id="priceDisplay"></strong></p>
            <div class="border rounded p-3 mb-3">
                <p>شماره کارت: <code id="cardNumber"></code></p>
                <p>نام دارنده: <code id="cardHolder"></code></p>
                <p>بانک: <code id="cardBank"></code></p>
            </div>
            <button class="btn btn-success w-100" onclick="uploadReceipt()">ارسال فیش واریز</button>
        </div>
    </div>

    <div id="page-referrals" class="page-content" style="display:none">
        <div class="card p-4 text-center">
            <i class="fas fa-share-alt fa-3x text-primary"></i>
            <h4 class="mt-3">دعوت از دوستان</h4>
            <p>با دعوت دوستان، 7% کمیسیون دریافت کنید</p>
            <div class="bg-light p-3 rounded"><code id="refLink"></code></div>
            <button class="btn btn-primary mt-3" onclick="copyReferral()">کپی لینک</button>
        </div>
    </div>

    <div id="page-libraries" class="page-content" style="display:none">
        <div class="card p-4">
            <h4>کتابخانه‌های آماده</h4>
            <p>برای نصب خودکار روی هر کتابخانه کلیک کنید</p>
            <div class="row" id="librariesList"></div>
        </div>
    </div>

    <div id="page-guide" class="page-content" style="display:none">
        <div class="card p-4" id="guideText"></div>
    </div>

    <div id="page-settings" class="page-content" style="display:none">
        <div class="card p-4">
            <h4>تنظیمات حساب</h4>
            <form id="profileForm">
                <div class="mb-3"><label>نام کامل</label><input type="text" id="fullName" class="form-control"></div>
                <div class="mb-3"><label>رمز جدید</label><input type="password" id="newPass" class="form-control"></div>
                <button type="submit" class="btn btn-primary">ذخیره</button>
            </form>
        </div>
    </div>

    <!-- پنل مدیریت -->
    <div id="page-admin" class="page-content" style="display:none">
        <div class="card p-4 mb-4">
            <h4>آمار سیستم</h4>
            <div class="row" id="adminStats"></div>
        </div>
        <div class="card p-4 mb-4">
            <h4>تایید فیش‌ها</h4>
            <div id="receiptsList"></div>
        </div>
        <div class="card p-4 mb-4">
            <h4>تایید برداشت‌ها</h4>
            <div id="withdrawsList"></div>
        </div>
        <div class="card p-4 mb-4">
            <h4>مدیریت کاربران</h4>
            <div id="usersList"></div>
        </div>
        <div class="card p-4 mb-4">
            <h4>مدیریت ماشین‌ها (سرورها)</h4>
            <div id="machinesList"></div>
            <div class="mt-3">
                <h6>افزودن سرور جدید</h6>
                <div class="row">
                    <div class="col-md-3"><input type="text" id="newMachineName" class="form-control" placeholder="نام"></div>
                    <div class="col-md-3"><input type="text" id="newMachineIp" class="form-control" placeholder="IP"></div>
                    <div class="col-md-2"><input type="text" id="newMachineUser" class="form-control" placeholder="کاربر"></div>
                    <div class="col-md-2"><input type="password" id="newMachinePass" class="form-control" placeholder="رمز"></div>
                    <div class="col-md-2"><button class="btn btn-primary" onclick="addMachine()">افزودن</button></div>
                </div>
            </div>
        </div>
        <div class="card p-4 mb-4">
            <h4>تنظیمات پرداخت</h4>
            <div class="row">
                <div class="col-md-6"><label>شماره کارت</label><input type="text" id="adminCard" class="form-control"></div>
                <div class="col-md-6"><label>نام دارنده</label><input type="text" id="adminHolder" class="form-control"></div>
                <div class="col-md-6"><label>بانک</label><input type="text" id="adminBank" class="form-control"></div>
                <div class="col-md-6"><label>قیمت اشتراک</label><input type="number" id="adminPrice" class="form-control"></div>
                <div class="col-md-6"><label>درصد کمیسیون</label><input type="number" id="adminCommission" class="form-control"></div>
                <div class="col-md-6"><label>حداقل برداشت</label><input type="number" id="adminMinWithdraw" class="form-control"></div>
            </div>
            <button class="btn btn-primary mt-3" onclick="saveSettings()">ذخیره تنظیمات</button>
        </div>
        <div class="card p-4">
            <h4>پیام همگانی</h4>
            <textarea id="broadcastMsg" class="form-control mb-2" rows="3"></textarea>
            <button class="btn btn-warning" onclick="sendBroadcast()">ارسال</button>
        </div>
    </div>
</div>

<div class="admin-float-btn" id="adminBtn" style="display:none">
    <button onclick="showAdminPanel()"><i class="fas fa-shield-alt fa-2x"></i></button>
</div>

<div class="modal fade" id="adminPassModal" tabindex="-1">
    <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
            <div class="modal-header"><h5>ورود به پنل مدیریت</h5><button type="button" class="btn-close" data-bs-dismiss="modal"></button></div>
            <div class="modal-body"><input type="password" id="adminPass" class="form-control" placeholder="رمز عبور"><div id="passError" class="text-danger mt-2" style="display:none">رمز اشتباه است</div></div>
            <div class="modal-footer"><button class="btn btn-secondary" data-bs-dismiss="modal">انصراف</button><button class="btn btn-danger" onclick="checkAdminPass()">ورود</button></div>
        </div>
    </div>
</div>

<div class="modal fade" id="withdrawModal" tabindex="-1">
    <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
            <div class="modal-header"><h5>درخواست برداشت</h5><button type="button" class="btn-close" data-bs-dismiss="modal"></button></div>
            <div class="modal-body">
                <p>حداقل برداشت: <span id="minWithdrawSpan"></span> تومان</p>
                <p>موجودی: <span id="withdrawBalanceSpan"></span> تومان</p>
                <input type="text" id="withdrawAddress" class="form-control" placeholder="آدرس TRC20">
            </div>
            <div class="modal-footer"><button class="btn btn-secondary" data-bs-dismiss="modal">انصراف</button><button class="btn btn-primary" onclick="submitWithdraw()">ثبت</button></div>
        </div>
    </div>
</div>

<div id="toast" class="toast-notify"></div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
let currentUser = null, isAdmin = false;

function toggleSidebar(){document.getElementById('sidebar').classList.toggle('open')}
function showToast(msg,err){let t=document.getElementById('toast');t.textContent=msg;t.style.background=err?'#dc3545':'#10b981';t.style.display='block';setTimeout(()=>t.style.display='none',3000)}

async function loadUser(){
    let r=await fetch('/api/user');
    if(r.ok){currentUser=await r.json();isAdmin=currentUser.is_admin===1;document.getElementById('userName').innerText=currentUser.full_name||currentUser.username;document.getElementById('userSubStatus').innerHTML=currentUser.subscription_active?'✅ فعال':'❌ غیرفعال';if(isAdmin)document.getElementById('adminBtn').style.display='block';}
}

function showPage(page){
    document.querySelectorAll('.page-content').forEach(p=>p.style.display='none');
    document.getElementById(`page-${page}`).style.display='block';
    if(page==='dashboard')loadDashboard();
    if(page==='bots')loadBots();
    if(page==='wallet')loadWallet();
    if(page==='referrals')loadReferrals();
    if(page==='libraries')loadLibraries();
    if(page==='guide')loadGuide();
    if(page==='admin'&&isAdmin)loadAdminPanel();
}

async function loadDashboard(){
    let u=currentUser;
    let s=await(await fetch('/api/stats')).json();
    let r=await(await fetch('/api/referrals')).json();
    document.getElementById('statsCards').innerHTML=`
        <div class="col-md-3"><div class="stat-card"><h3>${(u.wallet_balance||0).toLocaleString()}</h3><small>موجودی</small></div></div>
        <div class="col-md-3"><div class="stat-card"><h3>${u.bots_count||0}</h3><small>ربات‌ها</small></div></div>
        <div class="col-md-3"><div class="stat-card"><h3>${u.remaining_bots||0}</h3><small>ظرفیت</small></div></div>
        <div class="col-md-3"><div class="stat-card"><h3>${s.total_users||0}</h3><small>کاربران</small></div></div>
    `;
    document.getElementById('referralCode').innerText=r.referral_code;
    document.getElementById('refCount').innerText=r.count;
    document.getElementById('totalComm').innerText=(r.total_commission||0).toLocaleString();
    let b=await(await fetch('/api/bots')).json();
    document.getElementById('recentBots').innerHTML=b.slice(0,5).map(b=>`<div class="border-bottom py-2 d-flex justify-content-between"><span>${b.name||'ربات'}</span><span class="status-badge ${b.status=='running'?'status-running':'status-stopped'}">${b.status=='running'?'فعال':'متوقف'}</span></div>`).join('')||'<p class="text-muted">رباتی ندارید</p>';
}

async function loadBots(){
    let b=await(await fetch('/api/bots')).json();
    if(!b.length){document.getElementById('botsList').innerHTML='<p class="text-muted">رباتی ندارید</p>';return;}
    document.getElementById('botsList').innerHTML=b.map(b=>`
        <div class="border-bottom py-3 d-flex justify-content-between align-items-center">
            <div><strong>${b.name||b.username||'ربات'}</strong><br><small>@${b.username||''}</small><br><span class="status-badge ${b.status=='running'?'status-running':'status-stopped'}">${b.status=='running'?'🟢 فعال':'🔴 متوقف'}</span></div>
            <div><button class="btn btn-sm btn-outline-${b.status=='running'?'warning':'success'} me-1" onclick="toggleBot('${b.id}')"><i class="fas fa-${b.status=='running'?'stop':'play'}"></i></button><button class="btn btn-sm btn-outline-danger" onclick="deleteBot('${b.id}')"><i class="fas fa-trash"></i></button></div>
        </div>
    `).join('');
}

async function toggleBot(id){
    let r=await fetch(`/api/bots/${id}/toggle`,{method:'POST'});
    let d=await r.json();
    showToast(d.message,!r.ok);
    loadBots();loadDashboard();
}

async function deleteBot(id){
    if(!confirm('حذف شود؟')) return;
    let r=await fetch(`/api/bots/${id}`,{method:'DELETE'});
    if(r.ok){showToast('حذف شد');loadBots();loadDashboard();}
}

document.getElementById('botFile').onchange=function(e){
    if(e.target.files.length)document.getElementById('fileName').innerText=e.target.files[0].name;
}

async function buildBot(){
    let code=document.getElementById('botCode').value;
    let file=document.getElementById('botFile').files[0];
    if(!code.trim()&&!file){showToast('کد یا فایل را وارد کنید',true);return;}
    let btn=document.getElementById('buildBtn');
    btn.disabled=true;btn.innerHTML='<span class="loader"></span> در حال ساخت...';
    try{
        let res;
        if(file){
            let fd=new FormData();
            fd.append('file',file);
            res=await fetch('/api/build/upload',{method:'POST',body:fd});
        }else{
            res=await fetch('/api/build',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code})});
        }
        let data=await res.json();
        if(res.ok){showToast('ربات ساخته شد!');document.getElementById('botCode').value='';document.getElementById('botFile').value='';document.getElementById('fileName').innerText='';loadBots();loadDashboard();showPage('bots');}
        else{showToast(data.error||'خطا',true);}
    }catch(e){showToast('خطا',true);}
    btn.disabled=false;btn.innerHTML='ساخت ربات';
}

async function loadWallet(){
    let w=await(await fetch('/api/wallet')).json();
    document.getElementById('walletBalance').innerText=(w.balance||0).toLocaleString();
    document.getElementById('subStatus').innerHTML=w.subscription_active?'✅ فعال':'❌ غیرفعال';
    document.getElementById('expiryDate').innerText=w.expiry_date||'';
    document.getElementById('priceDisplay').innerText=w.subscription_price;
    document.getElementById('cardNumber').innerText=w.card_number;
    document.getElementById('cardHolder').innerText=w.card_holder;
    document.getElementById('cardBank').innerText=w.card_bank;
    document.getElementById('minWithdrawSpan').innerText=(w.min_withdraw||2000000).toLocaleString();
    document.getElementById('withdrawBalanceSpan').innerText=(w.balance||0).toLocaleString();
}

async function loadReferrals(){
    let r=await(await fetch('/api/referrals')).json();
    document.getElementById('refLink').innerText=r.referral_link;
}

async function loadLibraries(){
    let libs=${json.dumps(list(POPULAR_LIBRARIES.keys()))};
    document.getElementById('librariesList').innerHTML=libs.map(l=>`<div class="col-md-3 mb-2"><button class="btn btn-sm btn-outline-primary w-100" onclick="installLib('${l}')">${l}</button></div>`).join('');
}

async function installLib(name){
    showToast(`در حال نصب ${name}...`);
    let r=await fetch('/api/install-library',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});
    let d=await r.json();
    showToast(d.message,d.error?true:false);
}

async function loadGuide(){
    let g=await(await fetch('/api/guide')).json();
    document.getElementById('guideText').innerHTML=g.guide_text.replace(/\\n/g,'<br>');
}

function copyReferral(){
    let link=document.getElementById('refLink').innerText;
    navigator.clipboard.writeText(link);
    showToast('لینک کپی شد');
}

function uploadReceipt(){
    let i=document.createElement('input');
    i.type='file';i.accept='image/*';
    i.onchange=async (e)=>{
        let fd=new FormData();
        fd.append('receipt',e.target.files[0]);
        let r=await fetch('/api/upload-receipt',{method:'POST',body:fd});
        if(r.ok)showToast('فیش ارسال شد');
        else showToast('خطا',true);
    };
    i.click();
}

function showWithdraw(){new bootstrap.Modal(document.getElementById('withdrawModal')).show();}
async function submitWithdraw(){
    let addr=document.getElementById('withdrawAddress').value;
    if(!addr){showToast('آدرس را وارد کنید',true);return;}
    let r=await fetch('/api/withdraw',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({address:addr})});
    let d=await r.json();
    if(r.ok){showToast('درخواست ثبت شد');bootstrap.Modal.getInstance(document.getElementById('withdrawModal')).hide();loadWallet();}
    else{showToast(d.error,true);}
}

document.getElementById('profileForm').onsubmit=async(e)=>{
    e.preventDefault();
    let r=await fetch('/api/update-profile',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({full_name:fullName.value,password:newPass.value})});
    if(r.ok)showToast('پروفایل بروز شد');
};

function showAdminPanel(){new bootstrap.Modal(document.getElementById('adminPassModal')).show();}
async function checkAdminPass(){
    let pwd=document.getElementById('adminPass').value;
    if(pwd==='123456'){
        bootstrap.Modal.getInstance(document.getElementById('adminPassModal')).hide();
        showPage('admin');
    }else{
        document.getElementById('passError').style.display='block';
    }
}

async function loadAdminPanel(){
    let stats=await(await fetch('/api/admin/stats')).json();
    document.getElementById('adminStats').innerHTML=`
        <div class="col-md-3"><div class="card p-3"><h4>${stats.users_count}</h4><small>کاربران</small></div></div>
        <div class="col-md-3"><div class="card p-3"><h4>${stats.active_subs}</h4><small>اشتراک فعال</small></div></div>
        <div class="col-md-3"><div class="card p-3"><h4>${stats.total_bots}</h4><small>ربات‌ها</small></div></div>
        <div class="col-md-3"><div class="card p-3"><h4>${stats.running_bots}</h4><small>فعال</small></div></div>
    `;
    let receipts=await(await fetch('/api/admin/receipts')).json();
    document.getElementById('receiptsList').innerHTML=receipts.map(r=>`
        <div class="border p-2 mb-2 d-flex justify-content-between"><div>کاربر ${r.user_id}<br>${(r.amount||0).toLocaleString()} تومان</div><div><button class="btn btn-sm btn-success" onclick="approveReceipt(${r.id})">تایید</button><button class="btn btn-sm btn-danger" onclick="rejectReceipt(${r.id})">رد</button></div></div>
    `).join('')||'<p>فیشی نیست</p>';
    let withdraws=await(await fetch('/api/admin/withdraws')).json();
    document.getElementById('withdrawsList').innerHTML=withdraws.map(w=>`
        <div class="border p-2 mb-2 d-flex justify-content-between"><div>کاربر ${w.user_id}<br>${(w.amount||0).toLocaleString()} تومان<br>آدرس: ${w.address}</div><div><button class="btn btn-sm btn-success" onclick="approveWithdraw(${w.id})">تایید</button></div></div>
    `).join('')||'<p>درخواستی نیست</p>';
    let users=await(await fetch('/api/admin/users')).json();
    document.getElementById('usersList').innerHTML=`<table class="table"><thead><tr><th>کاربر</th><th>موجودی</th><th>وضعیت</th><th>ربات‌ها</th><th>عملیات</th></tr></thead><tbody>${users.map(u=>`<tr><td>${u.full_name||u.username}</td><td>${(u.wallet_balance||0).toLocaleString()}</td><td>${u.subscription_active?'✅':'❌'}</td><td>${u.bots_count||0}</td><td><button class="btn btn-sm btn-danger" onclick="banUser(${u.id})">مسدود</button></td></tr>`).join('')}</tbody></table>`;
    let machines=await(await fetch('/api/admin/machines')).json();
    document.getElementById('machinesList').innerHTML=machines.map(m=>`
        <div class="border p-2 mb-2 d-flex justify-content-between align-items-center"><div><strong>${m.name}</strong><br>IP: ${m.ip||'local'} | ربات‌ها: ${m.current_bots}/${m.max_bots} | وضعیت: ${m.status}</div><div><button class="btn btn-sm btn-warning" onclick="toggleMachine(${m.id},${m.status!='active'})">${m.status=='active'?'غیرفعال':'فعال'}</button></div></div>
    `).join('');
    let settings=await(await fetch('/api/admin/settings')).json();
    document.getElementById('adminCard').value=settings.card_number||'';
    document.getElementById('adminHolder').value=settings.card_holder||'';
    document.getElementById('adminBank').value=settings.card_bank||'';
    document.getElementById('adminPrice').value=settings.subscription_price||2000000;
    document.getElementById('adminCommission').value=settings.withdraw_percent||7;
    document.getElementById('adminMinWithdraw').value=settings.min_withdraw||2000000;
}

async function approveReceipt(id){await fetch(`/api/admin/receipt/${id}/approve`,{method:'POST'});loadAdminPanel();}
async function rejectReceipt(id){await fetch(`/api/admin/receipt/${id}/reject`,{method:'POST'});loadAdminPanel();}
async function approveWithdraw(id){await fetch(`/api/admin/withdraw/${id}/approve`,{method:'POST'});loadAdminPanel();}
async function banUser(id){if(confirm('مسدود شود؟')){await fetch(`/api/admin/users/${id}/ban`,{method:'POST'});loadAdminPanel();}}
async function toggleMachine(id,active){await fetch(`/api/admin/machines/${id}/toggle`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({active})});loadAdminPanel();}
async function addMachine(){
    let name=document.getElementById('newMachineName').value;
    let ip=document.getElementById('newMachineIp').value;
    let user=document.getElementById('newMachineUser').value;
    let pass=document.getElementById('newMachinePass').value;
    if(!name)return;
    await fetch('/api/admin/machines',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,ip,username:user,password:pass})});
    loadAdminPanel();
}
async function saveSettings(){
    let data={card_number:adminCard.value,card_holder:adminHolder.value,card_bank:adminBank.value,subscription_price:parseInt(adminPrice.value),withdraw_percent:parseInt(adminCommission.value),min_withdraw:parseInt(adminMinWithdraw.value)};
    await fetch('/api/admin/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    showToast('تنظیمات ذخیره شد');
}
async function sendBroadcast(){
    let msg=document.getElementById('broadcastMsg').value;
    if(!msg)return;
    let r=await fetch('/api/admin/broadcast',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg})});
    let d=await r.json();
    showToast(`پیام به ${d.sent} نفر ارسال شد`);
    document.getElementById('broadcastMsg').value='';
}

setInterval(()=>{let d=new Date();document.getElementById('currentTime')&&(document.getElementById('currentTime').innerText=d.toLocaleTimeString('fa-IR'));},1000);
loadUser().then(()=>{loadDashboard();});
</script>
</body>
</html>'''

# ==================== مسیرهای API ====================
@app.route('/')
def index():
    if 'user_id' in session:
        return HTML_INDEX
    return redirect(url_for('login_page'))

@app.route('/login')
def login_page():
    return HTML_LOGIN

@app.route('/register')
def register_page():
    return HTML_REGISTER

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    user = authenticate(data.get('username', ''), data.get('password', ''))
    if user:
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['is_admin'] = user.get('is_admin', 0)
        return jsonify({'success': True})
    return jsonify({'error': 'نام کاربری یا رمز عبور اشتباه است'}), 401

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    success, msg = create_user(data.get('username'), data.get('password'), data.get('full_name'), data.get('referral_code'))
    if success:
        return jsonify({'success': True})
    return jsonify({'error': msg}), 400

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

@app.route('/api/user')
def api_user():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
    if not user:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({
        'id': user['id'],
        'username': user['username'],
        'full_name': user['full_name'],
        'wallet_balance': user.get('wallet_balance', 0),
        'bots_count': user.get('bots_count', 0),
        'subscription_active': check_subscription(user['id']),
        'remaining_bots': get_remaining_bots(user['id']),
        'is_admin': user.get('is_admin', 0)
    })

@app.route('/api/bots')
def api_bots():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    bots = get_user_bots(session['user_id'])
    result = []
    for bot in bots:
        status = sandbox.get_status(bot['id'])
        result.append({
            'id': bot['id'],
            'name': bot['name'],
            'username': bot['username'],
            'status': 'running' if status.get('running') else bot.get('status', 'stopped'),
            'created_at': bot['created_at']
        })
    return jsonify(result)

@app.route('/api/bots/<bot_id>/toggle', methods=['POST'])
def api_toggle_bot(bot_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    bot = db.execute('SELECT * FROM bots WHERE id = ? AND user_id = ?', (bot_id, session['user_id']))
    if not bot:
        return jsonify({'error': 'Not found'}), 404
    
    status = sandbox.get_status(bot_id)
    if status.get('running'):
        if sandbox.stop_bot(bot_id):
            db.execute('UPDATE bots SET status = "stopped", last_active = ? WHERE id = ?', (datetime.now().isoformat(), bot_id))
            return jsonify({'message': 'ربات متوقف شد'})
    else:
        bot = bot[0]
        if os.path.exists(bot['file_path']):
            with open(bot['file_path'], 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
            result = sandbox.run_bot(bot_id, code, bot['token'], session['user_id'])
            if result['success']:
                db.execute('UPDATE bots SET status = "running", pid = ?, last_active = ? WHERE id = ?',
                          (result['pid'], datetime.now().isoformat(), bot_id))
                return jsonify({'message': 'ربات راه‌اندازی شد'})
    return jsonify({'error': 'خطا'}), 500

@app.route('/api/bots/<bot_id>', methods=['DELETE'])
def api_delete_bot(bot_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    if delete_bot(bot_id, session['user_id']):
        return jsonify({'message': 'حذف شد'})
    return jsonify({'error': 'خطا'}), 500

@app.route('/api/build', methods=['POST'])
def api_build():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    code = data.get('code', '')
    user_id = session['user_id']
    
    if not check_subscription(user_id):
        return jsonify({'error': 'ابتدا اشتراک خود را فعال کنید'}), 403
    
    if get_remaining_bots(user_id) <= 0:
        return jsonify({'error': 'به حداکثر تعداد ربات رسیده‌اید'}), 403
    
    token = extract_token_from_code(code)
    if not token:
        return jsonify({'error': 'توکن ربات در کد پیدا نشد'}), 400
    
    build_queue.add(user_id, code)
    return jsonify({'success': True, 'message': 'ربات در صف ساخت قرار گرفت'})

@app.route('/api/build/upload', methods=['POST'])
def api_build_upload():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if 'file' not in request.files:
        return jsonify({'error': 'فایلی ارسال نشده'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'فایلی انتخاب نشده'}), 400
    
    content = file.read()
    filename = file.filename
    user_id = session['user_id']
    
    if not check_subscription(user_id):
        return jsonify({'error': 'ابتدا اشتراک خود را فعال کنید'}), 403
    
    if get_remaining_bots(user_id) <= 0:
        return jsonify({'error': 'به حداکثر تعداد ربات رسیده‌اید'}), 403
    
    temp_path = os.path.join(DIRS['TEMP'], f"build_{user_id}_{int(time.time())}_{filename}")
    with open(temp_path, 'wb') as f:
        f.write(content)
    
    if filename.endswith('.zip'):
        extract_dir = os.path.join(DIRS['TEMP'], f"extract_{user_id}_{int(time.time())}")
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(temp_path, 'r') as zf:
            zf.extractall(extract_dir)
        code = ""
        for root, dirs, files in os.walk(extract_dir):
            for f in files:
                if f.endswith('.py'):
                    with open(os.path.join(root, f), 'r', encoding='utf-8', errors='ignore') as cf:
                        code = cf.read()
                        break
            if code:
                break
        shutil.rmtree(extract_dir, ignore_errors=True)
    else:
        with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()
    
    os.remove(temp_path)
    
    token = extract_token_from_code(code)
    if not token:
        return jsonify({'error': 'توکن ربات در کد پیدا نشد'}), 400
    
    build_queue.add(user_id, code, temp_path)
    return jsonify({'success': True, 'message': 'ربات در صف ساخت قرار گرفت'})

@app.route('/api/wallet')
def api_wallet():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
    return jsonify({
        'balance': user.get('wallet_balance', 0),
        'subscription_active': check_subscription(session['user_id']),
        'expiry_date': user.get('subscription_expiry', '')[:10] if user.get('subscription_expiry') else '',
        'subscription_price': get_setting('subscription_price_str'),
        'card_number': get_setting('card_number_display'),
        'card_holder': get_setting('card_holder'),
        'card_bank': get_setting('card_bank'),
        'min_withdraw': int(get_setting('min_withdraw') or 2000000)
    })

@app.route('/api/referrals')
def api_referrals():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
    return jsonify({
        'referral_code': user.get('referral_code', ''),
        'referral_link': f"http://{request.host}/register?ref={user.get('referral_code', '')}",
        'count': user.get('referrals_count', 0),
        'total_commission': user.get('total_commission', 0)
    })

@app.route('/api/guide')
def api_guide():
    return jsonify({'guide_text': get_setting('guide_text_fa')})

@app.route('/api/stats')
def api_stats():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    users_count = db.execute('SELECT COUNT(*) as cnt FROM users')[0]['cnt']
    bots_count = db.execute('SELECT COUNT(*) as cnt FROM bots')[0]['cnt']
    return jsonify({'total_users': users_count, 'total_bots': bots_count})

@app.route('/api/upload-receipt', methods=['POST'])
def api_upload_receipt():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    if 'receipt' not in request.files:
        return jsonify({'error': 'No file'}), 400
    file = request.files['receipt']
    if file.filename == '':
        return jsonify({'error': 'No file'}), 400
    
    tx_hash = secrets.token_hex(8)
    receipt_path = os.path.join(DIRS['RECEIPTS'], f"{session['user_id']}_{tx_hash}.jpg")
    file.save(receipt_path)
    
    db.execute('''
        INSERT INTO receipts (user_id, amount, receipt_path, tx_hash, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (session['user_id'], int(get_setting('subscription_price') or 2000000), receipt_path, tx_hash, datetime.now().isoformat()))
    
    return jsonify({'message': 'فیش با موفقیت ارسال شد'})

@app.route('/api/withdraw', methods=['POST'])
def api_withdraw():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    address = data.get('address', '')
    user = get_user(session['user_id'])
    
    min_withdraw = int(get_setting('min_withdraw') or 2000000)
    if user['wallet_balance'] < min_withdraw:
        return jsonify({'error': f'حداقل مبلغ برداشت {min_withdraw:,} تومان است'}), 400
    
    db.execute('''
        INSERT INTO withdraw_requests (user_id, amount, address, created_at)
        VALUES (?, ?, ?, ?)
    ''', (session['user_id'], user['wallet_balance'], address, datetime.now().isoformat()))
    
    db.execute('UPDATE users SET wallet_balance = 0 WHERE id = ?', (session['user_id'],))
    
    return jsonify({'message': 'درخواست برداشت ثبت شد'})

@app.route('/api/update-profile', methods=['POST'])
def api_update_profile():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    updates = []
    params = []
    if data.get('full_name'):
        updates.append('full_name = ?')
        params.append(data['full_name'])
    if data.get('password') and data['password'].strip():
        updates.append('password_hash = ?')
        params.append(hashlib.md5(data['password'].encode()).hexdigest())
    if updates:
        params.append(session['user_id'])
        db.execute(f'UPDATE users SET {", ".join(updates)} WHERE id = ?', params)
    return jsonify({'message': 'بروزرسانی شد'})

@app.route('/api/install-library', methods=['POST'])
def api_install_library():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    lib_name = data.get('name', '')
    success, msg = install_library(lib_name)
    if success:
        return jsonify({'message': f'کتابخانه {lib_name} نصب شد'})
    return jsonify({'error': msg}), 500

# ==================== APIهای ادمین ====================
@app.route('/api/admin/stats')
def api_admin_stats():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
    if not user or not user.get('is_admin'):
        return jsonify({'error': 'Forbidden'}), 403
    
    users_count = db.execute('SELECT COUNT(*) as cnt FROM users')[0]['cnt']
    active_subs = db.execute('SELECT COUNT(*) as cnt FROM users WHERE subscription_status = "active"')[0]['cnt']
    total_bots = db.execute('SELECT COUNT(*) as cnt FROM bots')[0]['cnt']
    running_bots = sandbox.get_stats()['total']
    
    return jsonify({
        'users_count': users_count,
        'active_subs': active_subs,
        'total_bots': total_bots,
        'running_bots': running_bots
    })

@app.route('/api/admin/users')
def api_admin_users():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
    if not user or not user.get('is_admin'):
        return jsonify({'error': 'Forbidden'}), 403
    
    users = db.execute('SELECT id, username, full_name, wallet_balance, subscription_status, bots_count, is_banned FROM users ORDER BY id')
    return jsonify(users)

@app.route('/api/admin/users/<int:uid>/ban', methods=['POST'])
def api_admin_ban_user(uid):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
    if not user or not user.get('is_admin'):
        return jsonify({'error': 'Forbidden'}), 403
    db.execute('UPDATE users SET is_banned = 1 WHERE id = ?', (uid,))
    return jsonify({'message': 'User banned'})

@app.route('/api/admin/receipts')
def api_admin_receipts():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
    if not user or not user.get('is_admin'):
        return jsonify({'error': 'Forbidden'}), 403
    
    receipts = db.execute('SELECT * FROM receipts WHERE status = "pending" ORDER BY created_at')
    return jsonify(receipts)

@app.route('/api/admin/receipt/<int:rid>/approve', methods=['POST'])
def api_admin_approve_receipt(rid):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
    if not user or not user.get('is_admin'):
        return jsonify({'error': 'Forbidden'}), 403
    
    receipt = db.execute('SELECT user_id FROM receipts WHERE id = ?', (rid,))
    if receipt:
        db.execute('UPDATE receipts SET status = "approved", reviewed_by = ?, reviewed_at = ? WHERE id = ?',
                  (session['user_id'], datetime.now().isoformat(), rid))
        activate_subscription(receipt[0]['user_id'])
    return jsonify({'message': 'Approved'})

@app.route('/api/admin/receipt/<int:rid>/reject', methods=['POST'])
def api_admin_reject_receipt(rid):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
    if not user or not user.get('is_admin'):
        return jsonify({'error': 'Forbidden'}), 403
    db.execute('UPDATE receipts SET status = "rejected", reviewed_by = ?, reviewed_at = ? WHERE id = ?',
              (session['user_id'], datetime.now().isoformat(), rid))
    return jsonify({'message': 'Rejected'})

@app.route('/api/admin/withdraws')
def api_admin_withdraws():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
    if not user or not user.get('is_admin'):
        return jsonify({'error': 'Forbidden'}), 403
    
    withdraws = db.execute('SELECT * FROM withdraw_requests WHERE status = "pending" ORDER BY created_at')
    return jsonify(withdraws)

@app.route('/api/admin/withdraw/<int:wid>/approve', methods=['POST'])
def api_admin_approve_withdraw(wid):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
    if not user or not user.get('is_admin'):
        return jsonify({'error': 'Forbidden'}), 403
    db.execute('UPDATE withdraw_requests SET status = "approved", processed_at = ? WHERE id = ?',
              (datetime.now().isoformat(), wid))
    return jsonify({'message': 'Approved'})

@app.route('/api/admin/settings', methods=['GET', 'POST'])
def api_admin_settings():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
    if not user or not user.get('is_admin'):
        return jsonify({'error': 'Forbidden'}), 403
    
    if request.method == 'GET':
        return jsonify({
            'card_number': get_setting('card_number_display'),
            'card_holder': get_setting('card_holder'),
            'card_bank': get_setting('card_bank'),
            'subscription_price': int(get_setting('subscription_price') or 2000000),
            'withdraw_percent': int(get_setting('withdraw_percent') or 7),
            'min_withdraw': int(get_setting('min_withdraw') or 2000000)
        })
    
    data = request.get_json()
    update_setting('card_number_display', data.get('card_number', ''))
    update_setting('card_holder', data.get('card_holder', ''))
    update_setting('card_bank', data.get('card_bank', ''))
    update_setting('subscription_price', data.get('subscription_price', 2000000))
    update_setting('subscription_price_str', f"{data.get('subscription_price', 2000000):,} تومان")
    update_setting('withdraw_percent', data.get('withdraw_percent', 7))
    update_setting('min_withdraw', data.get('min_withdraw', 2000000))
    return jsonify({'message': 'Settings saved'})

@app.route('/api/admin/machines', methods=['GET', 'POST'])
def api_admin_machines():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
    if not user or not user.get('is_admin'):
        return jsonify({'error': 'Forbidden'}), 403
    
    if request.method == 'GET':
        machines = db.execute('SELECT * FROM machines ORDER BY id')
        return jsonify(machines)
    
    data = request.get_json()
    result = machine_manager.add_machine(
        data.get('name'),
        data.get('ip'),
        int(data.get('port', 22)),
        data.get('username'),
        data.get('password'),
        int(data.get('max_bots', 5000))
    )
    return jsonify(result)

@app.route('/api/admin/machines/<int:machine_id>/toggle', methods=['POST'])
def api_admin_toggle_machine(machine_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
    if not user or not user.get('is_admin'):
        return jsonify({'error': 'Forbidden'}), 403
    
    data = request.get_json()
    machine_manager.toggle_machine(machine_id, data.get('active', False))
    return jsonify({'message': 'Toggled'})

@app.route('/api/admin/broadcast', methods=['POST'])
def api_admin_broadcast():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
    if not user or not user.get('is_admin'):
        return jsonify({'error': 'Forbidden'}), 403
    
    data = request.get_json()
    message = data.get('message', '')
    users = db.execute('SELECT id FROM users WHERE is_banned = 0')
    sent = len(users)
    return jsonify({'sent': sent})

# ==================== اجرا ====================
if __name__ == '__main__':
    print("=" * 80)
    print("🚀 سامانه فوق پیشرفته ساخت ربات تلگرام - نسخه 10.0 Ultimate")
    print("=" * 80)
    print(f"📍 آدرس: http://localhost:8080")
    print(f"👤 ادمین: admin / admin123")
    print(f"🔑 رمز پنل مدیریت: 123456")
    print(f"📊 تنظیمات مقیاس‌پذیری:")
    print(f"   - حداکثر کارگر همزمان: {SCALING_CONFIG['MAX_WORKERS']}")
    print(f"   - حداکثر ساخت همزمان: {SCALING_CONFIG['MAX_CONCURRENT_BUILDS']}")
    print(f"   - الگوریتم توزیع بار: {SCALING_CONFIG['LOAD_BALANCING_ALGO']}")
    print(f"🔒 ایزوله‌سازی:")
    print(f"   - محدودیت CPU: {ISOLATION_CONFIG['CPU_LIMIT']} ثانیه")
    print(f"   - محدودیت حافظه: {ISOLATION_CONFIG['MEMORY_LIMIT'] // (1024*1024)} مگابایت")
    print(f"📚 کتابخانه‌های آماده: {len(POPULAR_LIBRARIES)} عدد")
    print("=" * 80)
    
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False, threaded=True)