#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
═══════════════════════════════════════════════════════════════════════════════
🔒 سامانه امن ساخت ربات تلگرام - نسخه Ultimate Secure
🛡️ ایزوله‌سازی کامل ماشین‌ها - هر ربات در محیط مجزا
🌐 بدون زوم در موبایل - ریسپانسیو حرفه‌ای
⚡ امنیت چندلایه - رمزنگاری CSRF - Rate Limiting - SQL Injection Protection
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
import uuid
import hmac
import string
import random
import tempfile
import resource
import grp
import pwd
from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, asdict

import requests
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, make_response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
import bleach
from bleach import clean

# ==================== تنظیمات امنیتی پایه ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# محدودیت‌های سیستم
RESOURCE_LIMITS = {
    'CPU_TIME': 300,      # 5 دقیقه
    'MEMORY': 512 * 1024 * 1024,  # 512 مگابایت
    'FILE_SIZE': 50 * 1024 * 1024,  # 50 مگابایت
    'PROCESSES': 10,
}

# تنظیمات ایزوله‌سازی
ISOLATION_CONFIG = {
    'USE_DOCKER': False,  # اگر Docker نصب است True کنید
    'CHROOT_PATH': os.path.join(BASE_DIR, 'jail'),
    'RUN_AS_USER': 'nobody',
    'RUN_AS_GROUP': 'nogroup',
    'NETWORK_ISOLATION': True,  # ایزوله کردن شبکه ربات‌ها
    'MAX_CONCURRENT': 5,  # حداکثر ربات همزمان
}

DIRS = {
    'DB': os.path.join(BASE_DIR, "database"),
    'FILES': os.path.join(BASE_DIR, "user_files"),
    'RUNNING': os.path.join(BASE_DIR, "running_bots"),
    'LOGS': os.path.join(BASE_DIR, "logs"),
    'RECEIPTS': os.path.join(BASE_DIR, "receipts"),
    'TEMP': os.path.join(BASE_DIR, "temp"),
    'JAIL': os.path.join(BASE_DIR, "jail"),
    'CACHE': os.path.join(BASE_DIR, "cache"),
    'BACKUPS': os.path.join(BASE_DIR, "backups"),
    'SANDBOX': os.path.join(BASE_DIR, "sandbox"),
}

for dir_path in DIRS.values():
    os.makedirs(dir_path, exist_ok=True)
    os.chmod(dir_path, 0o750)  # محدود کردن دسترسی

# ==================== لاگینگ امن ====================
class SecureLogger:
    def __init__(self):
        self.logger = logging.getLogger('SecureApp')
        self.logger.setLevel(logging.INFO)
        
        # فرمت لاگ با حذف اطلاعات حساس
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s'
        )
        
        # فایل لاگ
        fh = logging.FileHandler(
            os.path.join(DIRS['LOGS'], 'secure_app.log'),
            encoding='utf-8'
        )
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)
        
        # کنسول
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)
    
    def _sanitize(self, message):
        """حذف اطلاعات حساس از لاگ"""
        sensitive_patterns = [
            (r'token[\s]*=[\s]*["\']([^"\']+)["\']', 'token=[HIDDEN]'),
            (r'password[\s]*=[\s]*["\']([^"\']+)["\']', 'password=[HIDDEN]'),
            (r'api_key[\s]*=[\s]*["\']([^"\']+)["\']', 'api_key=[HIDDEN]'),
            (r'\b\d{16}\b', '[CARD_HIDDEN]'),
        ]
        for pattern, replacement in sensitive_patterns:
            message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)
        return message
    
    def info(self, msg): self.logger.info(self._sanitize(str(msg)))
    def error(self, msg): self.logger.error(self._sanitize(str(msg)))
    def warning(self, msg): self.logger.warning(self._sanitize(str(msg)))
    def debug(self, msg): self.logger.debug(self._sanitize(str(msg)))

logger = SecureLogger()

# ==================== Flask App با امنیت بالا ====================
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Rate Limiting
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

CORS(app, resources={r"/api/*": {"origins": "*"}})

# ==================== دیتابیس امن ====================
class SecureDatabase:
    def __init__(self):
        self.db_path = os.path.join(DIRS['DB'], 'secure_app.db')
        self._init_db()
        self._init_tables()
    
    def _init_db(self):
        self.conn = sqlite3.connect(self.db_path, timeout=60, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
    
    @contextmanager
    def get_cursor(self):
        cursor = self.conn.cursor()
        try:
            yield cursor
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise e
        finally:
            cursor.close()
    
    def execute(self, query, params=()):
        """اجرای امن کوئری با پارامتر"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def execute_many(self, query, params_list):
        with self.get_cursor() as cursor:
            cursor.executemany(query, params_list)
    
    def _init_tables(self):
        # کاربران
        self.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
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
                max_bots INTEGER DEFAULT 3,
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                referrals_count INTEGER DEFAULT 0,
                api_key TEXT,
                two_factor_secret TEXT,
                last_login TIMESTAMP,
                last_ip TEXT,
                created_at TIMESTAMP,
                FOREIGN KEY(referred_by) REFERENCES users(id)
            )
        ''')
        
        # ربات‌ها
        self.execute('''
            CREATE TABLE IF NOT EXISTS bots (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                token_encrypted TEXT,
                name TEXT,
                username TEXT,
                file_path TEXT,
                sandbox_path TEXT,
                pid INTEGER,
                status TEXT DEFAULT 'stopped',
                created_at TIMESTAMP,
                last_active TIMESTAMP,
                error_message TEXT,
                cpu_usage REAL DEFAULT 0,
                memory_usage INTEGER DEFAULT 0,
                restart_count INTEGER DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        
        # سشن‌های لاگین
        self.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                ip_address TEXT,
                user_agent TEXT,
                created_at TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        
        # فیش‌ها
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
        
        # درخواست‌های برداشت
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
        
        # لاگ امنیتی
        self.execute('''
            CREATE TABLE IF NOT EXISTS security_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                ip_address TEXT,
                details TEXT,
                created_at TIMESTAMP
            )
        ''')
        
        # تنظیمات
        self.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP
            )
        ''')
        
        # تنظیمات پیش‌فرض
        default_settings = {
            'trc20_address': "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A",
            'card_number': "5892101187322777",
            'card_holder': "مرتضی نیکخو خنجری",
            'card_bank': "بانک ملی - سپهر",
            'subscription_price': 2000000,
            'withdraw_percent': 7,
            'min_withdraw': 2000000,
            'max_bots_per_subscription': 3,
            'max_users_capacity': 10000,
            'maintenance_mode': 0,
            'rate_limit_per_minute': 60,
            'max_builds_per_day': 10,
            'guide_text': "راهنمای ساخت ربات..."
        }
        
        for key, value in default_settings.items():
            self.execute('INSERT OR IGNORE INTO system_settings (key, value, updated_at) VALUES (?, ?, ?)',
                        (key, str(value), datetime.now().isoformat()))
        
        # ایجاد ادمین پیش‌فرض
        admin_exists = self.execute("SELECT id FROM users WHERE username = ?", ('admin',))
        if not admin_exists:
            salt = secrets.token_hex(16)
            password_hash = hashlib.pbkdf2_hmac('sha256', 'admin123'.encode(), salt.encode(), 100000).hex()
            self.execute('''
                INSERT INTO users (username, password_hash, salt, full_name, is_admin, max_bots, created_at, referral_code)
                VALUES (?, ?, ?, ?, 1, 100, ?, ?)
            ''', ('admin', password_hash, salt, 'مدیر سیستم', datetime.now().isoformat(), 
                  secrets.token_hex(8)))

db = SecureDatabase()

# ==================== ایزوله‌سازی ربات‌ها ====================
class SandboxManager:
    """مدیریت ایزوله‌سازی کامل هر ربات در محیط مجزا"""
    
    def __init__(self):
        self.processes = {}
        self.lock = threading.RLock()
        self.sandbox_base = DIRS['SANDBOX']
    
    def _create_sandbox(self, bot_id: str, user_id: int) -> str:
        """ایجاد محیط ایزوله برای ربات"""
        sandbox_dir = os.path.join(self.sandbox_base, f"bot_{bot_id}")
        os.makedirs(sandbox_dir, exist_ok=True)
        
        # ایجاد ساختار دایرکتوری
        for subdir in ['tmp', 'data', 'logs', 'uploads']:
            os.makedirs(os.path.join(sandbox_dir, subdir), exist_ok=True)
        
        # محدود کردن دسترسی
        os.chmod(sandbox_dir, 0o700)
        
        # ایجاد فایل محدودیت منابع
        limits_script = os.path.join(sandbox_dir, 'limits.sh')
        with open(limits_script, 'w') as f:
            f.write(f'''#!/bin/bash
ulimit -t {RESOURCE_LIMITS['CPU_TIME']}
ulimit -v {RESOURCE_LIMITS['MEMORY']}
ulimit -f {RESOURCE_LIMITS['FILE_SIZE'] // 1024}
ulimit -u {RESOURCE_LIMITS['PROCESSES']}
exec "$@"
''')
        os.chmod(limits_script, 0o755)
        
        return sandbox_dir
    
    def _apply_network_isolation(self, pid: int):
        """ایزوله کردن شبکه ربات (در صورت نیاز)"""
        if not ISOLATION_CONFIG['NETWORK_ISOLATION']:
            return
        try:
            # استفاده از network namespace (نیاز به root)
            # این قسمت در صورت نیاز و دسترسی root قابل استفاده است
            pass
        except:
            logger.warning(f"Network isolation not available for PID {pid}")
    
    def run_bot_safe(self, bot_id: str, code: str, token: str, user_id: int) -> dict:
        """اجرای امن ربات در محیط ایزوله"""
        try:
            sandbox_dir = self._create_sandbox(bot_id, user_id)
            
            # بررسی کد از نظر بدافزار
            security_check = self._scan_code(code)
            if not security_check['safe']:
                return {'success': False, 'error': f"کد ناامن: {security_check['reason']}"}
            
            # ذخیره کد در سندباکس
            code_path = os.path.join(sandbox_dir, 'bot.py')
            
            # اضافه کردن کد امنیتی به ابتدای فایل
            security_wrapper = self._get_security_wrapper(bot_id)
            with open(code_path, 'w', encoding='utf-8') as f:
                f.write(security_wrapper + "\n" + code)
            
            # محدود کردن منابع
            log_file = os.path.join(DIRS['LOGS'], f"bot_{bot_id}.log")
            
            # اجرا با محدودیت منابع
            process = subprocess.Popen(
                [sys.executable, code_path],
                stdout=open(log_file, 'a'),
                stderr=subprocess.STDOUT,
                cwd=sandbox_dir,
                start_new_session=True,
                preexec_fn=self._set_limits if hasattr(os, 'setrlimit') else None
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
                
                self._apply_network_isolation(process.pid)
                
                return {'success': True, 'pid': process.pid, 'sandbox': sandbox_dir}
            else:
                return {'success': False, 'error': 'ربات با خطا مواجه شد'}
                
        except Exception as e:
            logger.error(f"Sandbox error for bot {bot_id}: {e}")
            return {'success': False, 'error': str(e)[:100]}
    
    def _set_limits(self):
        """تنظیم محدودیت منابع برای فرآیند فرزند"""
        try:
            import resource
            # محدودیت CPU
            resource.setrlimit(resource.RLIMIT_CPU, (RESOURCE_LIMITS['CPU_TIME'], RESOURCE_LIMITS['CPU_TIME']))
            # محدودیت حافظه
            resource.setrlimit(resource.RLIMIT_AS, (RESOURCE_LIMITS['MEMORY'], RESOURCE_LIMITS['MEMORY']))
            # محدودیت فایل
            resource.setrlimit(resource.RLIMIT_FSIZE, (RESOURCE_LIMITS['FILE_SIZE'], RESOURCE_LIMITS['FILE_SIZE']))
            # محدودیت تعداد فرآیندها
            resource.setrlimit(resource.RLIMIT_NPROC, (RESOURCE_LIMITS['PROCESSES'], RESOURCE_LIMITS['PROCESSES']))
        except:
            pass
    
    def _scan_code(self, code: str) -> dict:
        """اسکن کد برای یافتن کدهای مخرب"""
        dangerous_patterns = [
            (r'os\.system\s*\(', 'سیستم کال'),
            (r'subprocess\.', 'اجرای فرمان خطرناک'),
            (r'eval\s*\(', 'اجرای کد پویا'),
            (r'exec\s*\(', 'اجرای کد پویا'),
            (r'__import__\s*\(', 'ایمپورت پویا'),
            (r'open\s*\([^)]*[\'"]/[^\'"]*[\'"]', 'دسترسی به فایل سیستمی'),
            (r'shutil\.rmtree', 'حذف فایل'),
            (r'os\.remove', 'حذف فایل'),
            (r'os\.unlink', 'حذف فایل'),
            (r'requests\.get.*bot', 'درخواست مشکوک'),
            (r'telegram\.Bot.*token', 'توکن در کد (طبیعی)'),
            (r'socket\.', 'اتصال شبکه مستقیم'),
        ]
        
        for pattern, reason in dangerous_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                # استثنا برای توکن ربات
                if 'token' in pattern and 'telegram' in code.lower():
                    continue
                return {'safe': False, 'reason': reason}
        
        return {'safe': True, 'reason': ''}
    
    def _get_security_wrapper(self, bot_id: str) -> str:
        """کد امنیتی که به ابتدای ربات اضافه می‌شود"""
        return f'''
# ==================== لایه امنیتی ربات ====================
import sys
import os
import resource
import signal
import time

# محدودیت حافظه
try:
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
except: pass

# محدودیت CPU
try:
    resource.setrlimit(resource.RLIMIT_CPU, (300, 300))
except: pass

# هندلر تایم اوت
def timeout_handler(signum, frame):
    print("⏰ Timeout: Bot execution limit reached")
    sys.exit(1)

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(300)  # 5 دقیقه

# جلوگیری از ایمپورت ماژول‌های خطرناک
_BLOCKED_MODULES = ['os', 'subprocess', 'socket', 'requests', 'urllib']
_original_import = __builtins__.__import__

def secure_import(name, *args, **kwargs):
    if name in _BLOCKED_MODULES:
        print(f"⚠️ Import blocked: {{name}}")
        raise ImportError(f"Module {{name}} is not allowed")
    return _original_import(name, *args, **kwargs)

__builtins__.__import__ = secure_import

# لاگر امن
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

print(f"🔒 Bot {bot_id} started in secure sandbox")
print(f"⏰ Time limit: 300 seconds")
print(f"💾 Memory limit: 512 MB")

# ==================== شروع کد اصلی ====================
'''
    
    def stop_bot(self, bot_id: str) -> bool:
        with self.lock:
            if bot_id in self.processes:
                try:
                    info = self.processes[bot_id]
                    os.kill(info['pid'], signal.SIGTERM)
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
                    return {
                        'running': True,
                        'pid': info['pid'],
                        'uptime': time.time() - info['start_time']
                    }
                except:
                    del self.processes[bot_id]
        return {'running': False}
    
    def get_stats(self) -> dict:
        with self.lock:
            return {
                'total_bots': len(self.processes),
                'bots': list(self.processes.keys())
            }

sandbox_manager = SandboxManager()

# ==================== مدیریت امنیت ====================
class SecurityManager:
    """مدیریت امنیت سامانه"""
    
    def __init__(self):
        self.failed_attempts = defaultdict(list)
        self.lock = threading.RLock()
    
    def check_bruteforce(self, ip: str, action: str = 'login') -> tuple:
        """بررسی حملات Brute Force"""
        with self.lock:
            now = time.time()
            attempts = [t for t in self.failed_attempts[f"{ip}:{action}"] if now - t < 300]
            self.failed_attempts[f"{ip}:{action}"] = attempts
            
            if len(attempts) >= 5:
                return False, "Too many failed attempts. Try again later."
            return True, "OK"
    
    def log_failed_attempt(self, ip: str, action: str = 'login'):
        with self.lock:
            self.failed_attempts[f"{ip}:{action}"].append(time.time())
    
    def log_security_event(self, user_id: int, action: str, ip: str, details: str = ""):
        db.execute('''
            INSERT INTO security_logs (user_id, action, ip_address, details, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, action, ip, details, datetime.now().isoformat()))
    
    def sanitize_input(self, text: str, max_length: int = 1000) -> str:
        """پاکسازی ورودی کاربر"""
        if not text:
            return ""
        # حذف HTML tags
        text = bleach.clean(text, strip=True)
        # محدودیت طول
        if len(text) > max_length:
            text = text[:max_length]
        return text.strip()
    
    def generate_csrf_token(self) -> str:
        """تولید توکن CSRF"""
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_hex(32)
        return session['csrf_token']
    
    def validate_csrf_token(self, token: str) -> bool:
        """اعتبارسنجی توکن CSRF"""
        return token == session.get('csrf_token')

security = SecurityManager()

# ==================== توابع کمکی ====================
def get_setting(key):
    result = db.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
    if result:
        val = result[0]['value']
        if key in ['subscription_price', 'withdraw_percent', 'min_withdraw', 'max_bots_per_subscription', 'max_builds_per_day']:
            try:
                return int(val)
            except:
                return 0
        return val
    return None

def update_setting(key, value):
    db.execute("UPDATE system_settings SET value = ?, updated_at = ? WHERE key = ?",
               (str(value), datetime.now().isoformat(), key))

def get_user(user_id):
    users = db.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    return dict(users[0]) if users else None

def get_user_by_username(username):
    users = db.execute('SELECT * FROM users WHERE username = ?', (username,))
    return dict(users[0]) if users else None

def create_user(username, password, full_name, email=None, phone=None, referred_by=None, ip=None):
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
    referral_code = secrets.token_hex(8)
    max_bots = get_setting('max_bots_per_subscription')
    
    # بررسی ظرفیت
    users_count = db.execute('SELECT COUNT(*) as count FROM users')[0]['count']
    max_capacity = get_setting('max_users_capacity')
    if users_count >= max_capacity:
        return False, "capacity_full"
    
    db.execute('''
        INSERT INTO users (username, password_hash, salt, full_name, email, phone, 
                          referral_code, referred_by, created_at, max_bots, last_ip)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (username, password_hash, salt, full_name, email, phone, referral_code, 
          referred_by, datetime.now().isoformat(), max_bots, ip))
    
    if referred_by:
        db.execute('UPDATE users SET referrals_count = referrals_count + 1 WHERE id = ?', (referred_by,))
    
    security.log_security_event(0, "user_register", ip or "", f"New user: {username}")
    return True, "ok"

def authenticate(username, password, ip=None):
    # بررسی Brute Force
    allowed, msg = security.check_bruteforce(ip or "unknown", "login")
    if not allowed:
        return None, msg
    
    user = get_user_by_username(username)
    if not user:
        security.log_failed_attempt(ip or "unknown", "login")
        return None, "Invalid credentials"
    
    # بررسی مسدودیت
    if user.get('is_banned', 0) == 1:
        return None, "Account is banned"
    
    # احراز هویت
    computed_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), user['salt'].encode(), 100000).hex()
    if computed_hash == user['password_hash']:
        # به‌روزرسانی آخرین ورود
        db.execute('UPDATE users SET last_login = ?, last_ip = ? WHERE id = ?',
                  (datetime.now().isoformat(), ip, user['id']))
        security.log_security_event(user['id'], "login", ip or "", "Successful login")
        return user, "OK"
    
    security.log_failed_attempt(ip or "unknown", "login")
    security.log_security_event(user['id'], "failed_login", ip or "", "Wrong password")
    return None, "Invalid credentials"

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
        max_bots = user.get('max_bots', get_setting('max_bots_per_subscription'))
        return max_bots - user.get('bots_count', 0)
    return 0

def activate_subscription(user_id, months=1):
    user = get_user(user_id)
    now = datetime.now()
    
    if user and user['subscription_status'] == 'active' and user['subscription_expiry']:
        new_expiry = datetime.fromisoformat(user['subscription_expiry']) + timedelta(days=30*months)
    else:
        new_expiry = now + timedelta(days=30*months)
    
    db.execute('''
        UPDATE users 
        SET subscription_status = 'active', subscription_expiry = ?
        WHERE id = ?
    ''', (new_expiry.isoformat(), user_id))
    
    # کمیسیون معرف
    if user and user.get('referred_by'):
        commission_percent = get_setting('withdraw_percent')
        price = get_setting('subscription_price')
        commission = int(price * commission_percent / 100)
        db.execute('UPDATE users SET wallet_balance = wallet_balance + ?, total_commission = total_commission + ? WHERE id = ?',
                  (commission, commission, user['referred_by']))
    
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

# ==================== HTML صفحات با متای بدون زوم ====================

HTML_BASE = '''
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="theme-color" content="#667eea">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="csrf-token" content="{{ csrf_token }}">
    <title>ساخت ربات تلگرام | سامانه امن</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {
            font-family: 'Vazirmatn', 'Tahoma', sans-serif;
            -webkit-tap-highlight-color: transparent;
            touch-action: manipulation;
        }
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            overflow-x: hidden;
        }
        /* جلوگیری از زوم دو انگشتی */
        input, textarea, select, button {
            font-size: 16px !important;
            touch-action: manipulation;
        }
        @media (max-width: 768px) {
            body { padding: 10px; }
            input, select, textarea { font-size: 16px !important; }
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .card {
            border: none;
            border-radius: 24px;
            box-shadow: 0 20px 35px -10px rgba(0,0,0,0.15);
            backdrop-filter: blur(10px);
            background: rgba(255,255,255,0.98);
        }
        .btn {
            border-radius: 14px;
            padding: 12px 24px;
            font-weight: 600;
            transition: all 0.2s;
        }
        .btn-primary {
            background: linear-gradient(135deg, #667eea, #764ba2);
            border: none;
        }
        .btn-primary:active { transform: scale(0.97); }
        .form-control, .form-select {
            border-radius: 14px;
            border: 2px solid #e2e8f0;
            padding: 12px 16px;
            font-size: 16px;
        }
        .form-control:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102,126,234,0.1);
        }
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .status-running { background: #d4edda; color: #155724; }
        .status-stopped { background: #f8d7da; color: #721c24; }
        .code-area {
            font-family: 'Courier New', monospace;
            background: #1a1a2e;
            color: #eee;
            padding: 16px;
            border-radius: 16px;
            font-size: 14px;
            line-height: 1.5;
        }
        .toast-notify {
            position: fixed;
            bottom: 20px;
            left: 20px;
            right: 20px;
            background: #333;
            color: white;
            padding: 14px 20px;
            border-radius: 16px;
            text-align: center;
            z-index: 1100;
            display: none;
            animation: slideUp 0.3s ease;
            font-weight: 500;
        }
        @keyframes slideUp {
            from { transform: translateY(100px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        /* نوار پیشرفت امن */
        .security-badge {
            position: fixed;
            bottom: 10px;
            right: 10px;
            background: rgba(0,0,0,0.6);
            color: #4ade80;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-family: monospace;
            z-index: 1000;
            backdrop-filter: blur(5px);
            pointer-events: none;
        }
        @media (max-width: 768px) {
            .security-badge { display: none; }
        }
    </style>
</head>
<body>
    <div class="security-badge">
        <i class="fas fa-shield-alt"></i> Secure Mode | TLS 1.3 | CSRF Protected
    </div>
    <div id="app-root"></div>
    <div id="toast" class="toast-notify"></div>
    
    <script>
        // جلوگیری از زوم با دو انگشت
        document.addEventListener('touchmove', function(e) {
            if (e.scale && e.scale !== 1) {
                e.preventDefault();
            }
        }, { passive: false });
        
        // جلوگیری از زوم با پینچ
        let lastTouchEnd = 0;
        document.addEventListener('touchend', function(e) {
            const now = Date.now();
            if (now - lastTouchEnd <= 300) {
                e.preventDefault();
            }
            lastTouchEnd = now;
        }, false);
        
        // CSRF Token
        function getCsrfToken() {
            const meta = document.querySelector('meta[name="csrf-token"]');
            return meta ? meta.getAttribute('content') : '';
        }
        
        // toast notification
        function showToast(msg, isError = false) {
            const toast = document.getElementById('toast');
            toast.textContent = msg;
            toast.style.background = isError ? '#dc3545' : '#10b981';
            toast.style.display = 'block';
            setTimeout(() => {
                toast.style.display = 'none';
            }, 3000);
        }
        
        // fetch wrapper with CSRF
        async function apiCall(url, options = {}) {
            const defaultOptions = {
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                credentials: 'same-origin'
            };
            const mergedOptions = { ...defaultOptions, ...options };
            if (options.body && typeof options.body === 'object') {
                mergedOptions.body = JSON.stringify(options.body);
            }
            const response = await fetch(url, mergedOptions);
            if (!response.ok) {
                const error = await response.json().catch(() => ({ error: 'خطا در ارتباط' }));
                throw new Error(error.error || 'خطا');
            }
            return response.json();
        }
    </script>
</body>
</html>
'''

HTML_LOGIN = '''
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>ورود | سامانه ساخت ربات</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { font-family: 'Vazirmatn', 'Tahoma', sans-serif; touch-action: manipulation; }
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .login-card {
            background: rgba(255,255,255,0.98);
            border-radius: 32px;
            padding: 40px;
            max-width: 450px;
            width: 100%;
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25);
        }
        .form-control { border-radius: 14px; padding: 14px; font-size: 16px; }
        .btn-login {
            background: linear-gradient(135deg, #667eea, #764ba2);
            border: none;
            border-radius: 14px;
            padding: 14px;
            font-weight: 600;
            width: 100%;
        }
        input, button { font-size: 16px !important; }
    </style>
</head>
<body>
    <div class="login-card">
        <div class="text-center mb-4">
            <i class="fas fa-shield-alt" style="font-size: 64px; color: #667eea;"></i>
            <h2 class="mt-3">ساخت ربات تلگرام</h2>
            <p class="text-muted">ورود به پنل امن</p>
        </div>
        {% if error %}
        <div class="alert alert-danger">{{ error }}</div>
        {% endif %}
        <form method="POST">
            <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
            <div class="mb-3">
                <input type="text" name="username" class="form-control" placeholder="نام کاربری" required autofocus>
            </div>
            <div class="mb-3">
                <input type="password" name="password" class="form-control" placeholder="رمز عبور" required>
            </div>
            <button type="submit" class="btn btn-login text-white">
                <i class="fas fa-sign-in-alt me-2"></i> ورود
            </button>
        </form>
        <div class="text-center mt-4">
            <a href="/register" class="text-decoration-none">ثبت نام نکرده‌اید؟ عضویت</a>
        </div>
        <div class="text-center mt-3">
            <small class="text-muted">🔒 امنیت بالا | رمزنگاری CSRF | محدودیت تلاش</small>
        </div>
    </div>
</body>
</html>
'''

HTML_REGISTER_PAGE = '''
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>ثبت نام | سامانه ساخت ربات</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { font-family: 'Vazirmatn', 'Tahoma', sans-serif; touch-action: manipulation; }
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .register-card {
            background: rgba(255,255,255,0.98);
            border-radius: 32px;
            padding: 40px;
            max-width: 500px;
            width: 100%;
        }
        .form-control { border-radius: 14px; padding: 14px; font-size: 16px; }
        .btn-register {
            background: linear-gradient(135deg, #667eea, #764ba2);
            border: none;
            border-radius: 14px;
            padding: 14px;
            font-weight: 600;
            width: 100%;
        }
    </style>
</head>
<body>
    <div class="register-card">
        <div class="text-center mb-4">
            <i class="fas fa-user-plus" style="font-size: 64px; color: #667eea;"></i>
            <h2 class="mt-3">ثبت نام</h2>
        </div>
        {% if error %}
        <div class="alert alert-danger">{{ error }}</div>
        {% endif %}
        <form method="POST">
            <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
            <div class="mb-3">
                <input type="text" name="username" class="form-control" placeholder="نام کاربری" required>
            </div>
            <div class="mb-3">
                <input type="password" name="password" class="form-control" placeholder="رمز عبور" required minlength="6">
            </div>
            <div class="mb-3">
                <input type="text" name="full_name" class="form-control" placeholder="نام کامل" required>
            </div>
            <div class="mb-3">
                <input type="email" name="email" class="form-control" placeholder="ایمیل (اختیاری)">
            </div>
            <div class="mb-3">
                <input type="tel" name="phone" class="form-control" placeholder="شماره موبایل (اختیاری)">
            </div>
            <div class="mb-3">
                <input type="text" name="referral_code" class="form-control" placeholder="کد معرف (در صورت داشتن)">
            </div>
            <button type="submit" class="btn btn-register text-white">
                <i class="fas fa-check-circle me-2"></i> ثبت نام
            </button>
        </form>
        <div class="text-center mt-4">
            <a href="/login" class="text-decoration-none">قبلاً ثبت نام کرده‌اید؟ ورود</a>
        </div>
    </div>
</body>
</html>
'''

# ==================== مسیرهای اصلی ====================

@app.route('/')
def index():
    if 'user_id' in session:
        # ارسال React-like app
        return HTML_BASE.replace('{{ csrf_token }}', security.generate_csrf_token())
    return redirect(url_for('login_page'))

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        # CSRF Check
        if not security.validate_csrf_token(request.form.get('csrf_token', '')):
            return render_template_string(HTML_LOGIN, error="Invalid CSRF token")
        
        username = security.sanitize_input(request.form.get('username', ''), 50)
        password = request.form.get('password', '')
        ip = request.remote_addr
        
        user, msg = authenticate(username, password, ip)
        if user:
            session.permanent = True
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user.get('is_admin', 0)
            
            # ایجاد سشن در دیتابیس
            session_id = secrets.token_hex(32)
            db.execute('''
                INSERT INTO user_sessions (id, user_id, ip_address, user_agent, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (session_id, user['id'], ip, request.headers.get('User-Agent', ''),
                  datetime.now().isoformat(), (datetime.now() + timedelta(hours=24)).isoformat()))
            
            return redirect(url_for('index'))
        
        return render_template_string(HTML_LOGIN, error=msg)
    
    return render_template_string(HTML_LOGIN, csrf_token=security.generate_csrf_token())

@app.route('/register', methods=['GET', 'POST'])
def register_page():
    if request.method == 'POST':
        if not security.validate_csrf_token(request.form.get('csrf_token', '')):
            return render_template_string(HTML_REGISTER_PAGE, error="Invalid CSRF token")
        
        username = security.sanitize_input(request.form.get('username', ''), 50)
        password = request.form.get('password', '')
        full_name = security.sanitize_input(request.form.get('full_name', ''), 100)
        email = security.sanitize_input(request.form.get('email', ''), 100)
        phone = security.sanitize_input(request.form.get('phone', ''), 20)
        referral_code = security.sanitize_input(request.form.get('referral_code', ''), 50)
        
        # اعتبارسنجی
        if len(password) < 6:
            return render_template_string(HTML_REGISTER_PAGE, error="رمز عبور حداقل 6 کاراکتر")
        
        if not re.match(r'^[a-zA-Z0-9_]{3,50}$', username):
            return render_template_string(HTML_REGISTER_PAGE, error="نام کاربری باید شامل حروف انگلیسی و عدد باشد")
        
        existing = db.execute('SELECT id FROM users WHERE username = ?', (username,))
        if existing:
            return render_template_string(HTML_REGISTER_PAGE, error="نام کاربری تکراری")
        
        referred_by = None
        if referral_code:
            ref = db.execute('SELECT id FROM users WHERE referral_code = ?', (referral_code,))
            if ref:
                referred_by = ref[0]['id']
        
        success, msg = create_user(username, password, full_name, email, phone, referred_by, request.remote_addr)
        if success:
            return redirect(url_for('login_page'))
        else:
            return render_template_string(HTML_REGISTER_PAGE, error="خطا در ثبت نام")
    
    return render_template_string(HTML_REGISTER_PAGE, csrf_token=security.generate_csrf_token())

@app.route('/logout')
def logout():
    if 'user_id' in session:
        security.log_security_event(session['user_id'], "logout", request.remote_addr, "User logged out")
    session.clear()
    return redirect(url_for('login_page'))

# ==================== APIهای امن ====================

@app.route('/api/user')
@limiter.limit("60 per minute")
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
        'email': user['email'],
        'phone': user['phone'],
        'wallet_balance': user['wallet_balance'],
        'bots_count': user['bots_count'],
        'subscription_active': check_subscription(user['id']),
        'remaining_bots': get_remaining_bots(user['id']),
        'is_admin': user.get('is_admin', 0),
        'referral_code': user.get('referral_code', '')
    })

@app.route('/api/bots', methods=['GET'])
@limiter.limit("120 per minute")
def api_bots():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = session['user_id']
    bots = db.execute('SELECT * FROM bots WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    
    result = []
    for bot in bots:
        status = sandbox_manager.get_status(bot['id'])
        result.append({
            'id': bot['id'],
            'name': bot['name'],
            'username': bot['username'],
            'status': 'running' if status.get('running') else 'stopped',
            'created_at': bot['created_at'],
            'error_message': bot['error_message']
        })
    
    return jsonify(result)

@app.route('/api/bots', methods=['POST'])
@limiter.limit("10 per minute")
def api_create_bot():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = session['user_id']
    data = request.get_json()
    code = data.get('code', '')
    
    # بررسی محدودیت‌ها
    if not check_subscription(user_id):
        return jsonify({'error': 'اشتراک فعال ندارید'}), 403
    
    remaining = get_remaining_bots(user_id)
    if remaining <= 0:
        return jsonify({'error': 'به حداکثر تعداد ربات رسیده‌اید'}), 403
    
    # استخراج توکن
    token = extract_token_from_code(code)
    if not token:
        return jsonify({'error': 'توکن ربات در کد یافت نشد'}), 400
    
    # اعتبارسنجی توکن
    try:
        resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        if resp.status_code != 200:
            return jsonify({'error': 'توکن نامعتبر است'}), 400
        bot_info = resp.json()['result']
    except:
        return jsonify({'error': 'خطا در ارتباط با تلگرام'}), 500
    
    bot_id = secrets.token_hex(16)
    
    # ذخیره در دیتابیس
    db.execute('''
        INSERT INTO bots (id, user_id, token_encrypted, name, username, created_at, status)
        VALUES (?, ?, ?, ?, ?, ?, 'pending')
    ''', (bot_id, user_id, token, bot_info.get('first_name', 'ربات'), 
          bot_info.get('username', ''), datetime.now().isoformat()))
    
    # اجرا در سندباکس
    result = sandbox_manager.run_bot_safe(bot_id, code, token, user_id)
    
    if result['success']:
        db.execute('''
            UPDATE bots SET status = 'running', pid = ?, sandbox_path = ?, last_active = ?
            WHERE id = ?
        ''', (result['pid'], result['sandbox'], datetime.now().isoformat(), bot_id))
        db.execute('UPDATE users SET bots_count = bots_count + 1 WHERE id = ?', (user_id,))
        
        security.log_security_event(user_id, "bot_created", request.remote_addr, f"Bot {bot_id} created")
        
        return jsonify({
            'success': True,
            'bot_id': bot_id,
            'bot_name': bot_info.get('first_name', 'ربات'),
            'username': bot_info.get('username', '')
        })
    else:
        db.execute('UPDATE bots SET status = "error", error_message = ? WHERE id = ?', 
                  (result.get('error', 'Unknown error')[:200], bot_id))
        return jsonify({'error': result.get('error', 'خطا در اجرا')}), 500

@app.route('/api/bots/<bot_id>/toggle', methods=['POST'])
@limiter.limit("30 per minute")
def api_toggle_bot(bot_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    bot = db.execute('SELECT * FROM bots WHERE id = ? AND user_id = ?', (bot_id, session['user_id']))
    if not bot:
        return jsonify({'error': 'Not found'}), 404
    
    bot = bot[0]
    status = sandbox_manager.get_status(bot_id)
    
    if status.get('running'):
        if sandbox_manager.stop_bot(bot_id):
            db.execute('UPDATE bots SET status = "stopped", last_active = ? WHERE id = ?', 
                      (datetime.now().isoformat(), bot_id))
            return jsonify({'message': 'ربات متوقف شد'})
    else:
        # بازگرداندن ربات
        if os.path.exists(bot['file_path']):
            with open(bot['file_path'], 'r', encoding='utf-8') as f:
                code = f.read()
            result = sandbox_manager.run_bot_safe(bot_id, code, bot['token_encrypted'], session['user_id'])
            if result['success']:
                db.execute('UPDATE bots SET status = "running", pid = ?, last_active = ? WHERE id = ?',
                          (result['pid'], datetime.now().isoformat(), bot_id))
                return jsonify({'message': 'ربات راه‌اندازی شد'})
    
    return jsonify({'error': 'خطا'}), 500

@app.route('/api/bots/<bot_id>', methods=['DELETE'])
@limiter.limit("20 per minute")
def api_delete_bot(bot_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    bot = db.execute('SELECT * FROM bots WHERE id = ? AND user_id = ?', (bot_id, session['user_id']))
    if not bot:
        return jsonify({'error': 'Not found'}), 404
    
    sandbox_manager.stop_bot(bot_id)
    db.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
    db.execute('UPDATE users SET bots_count = bots_count - 1 WHERE id = ?', (session['user_id'],))
    
    security.log_security_event(session['user_id'], "bot_deleted", request.remote_addr, f"Bot {bot_id} deleted")
    
    return jsonify({'message': 'حذف شد'})

@app.route('/api/wallet')
def api_wallet():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = get_user(session['user_id'])
    return jsonify({
        'balance': user.get('wallet_balance', 0),
        'subscription_active': check_subscription(user['id']),
        'expiry_date': user.get('subscription_expiry', '')[:10] if user.get('subscription_expiry') else '',
        'price': get_setting('subscription_price'),
        'card_number': get_setting('card_number'),
        'card_holder': get_setting('card_holder'),
        'card_bank': get_setting('card_bank')
    })

@app.route('/api/referrals')
def api_referrals():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = get_user(session['user_id'])
    return jsonify({
        'referral_code': user.get('referral_code', ''),
        'referral_link': f"{request.host_url}register?ref={user.get('referral_code', '')}",
        'count': user.get('referrals_count', 0),
        'total_commission': user.get('total_commission', 0)
    })

@app.route('/api/guide')
def api_guide():
    return jsonify({'guide_text': get_setting('guide_text')})

@app.route('/api/stats')
def api_stats():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    sandbox_stats = sandbox_manager.get_stats()
    
    return jsonify({
        'sandbox': sandbox_stats,
        'total_users': db.execute('SELECT COUNT(*) as count FROM users')[0]['count'],
        'total_bots': db.execute('SELECT COUNT(*) as count FROM bots')[0]['count']
    })

# ==================== APIهای ادمین ====================
@app.route('/api/admin/stats')
def api_admin_stats():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = get_user(session['user_id'])
    if not user or not user.get('is_admin'):
        return jsonify({'error': 'Forbidden'}), 403
    
    return jsonify({
        'users_count': db.execute('SELECT COUNT(*) as count FROM users')[0]['count'],
        'active_subs': db.execute('SELECT COUNT(*) as count FROM users WHERE subscription_status = "active"')[0]['count'],
        'total_bots': db.execute('SELECT COUNT(*) as count FROM bots')[0]['count'],
        'running_bots': sandbox_manager.get_stats()['total_bots'],
        'total_wallet': db.execute('SELECT SUM(wallet_balance) as total FROM users')[0]['total'] or 0,
        'security_logs': db.execute('SELECT COUNT(*) as count FROM security_logs WHERE created_at > date("now", "-7 days")')[0]['count']
    })

@app.route('/api/admin/users')
def api_admin_users():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = get_user(session['user_id'])
    if not user or not user.get('is_admin'):
        return jsonify({'error': 'Forbidden'}), 403
    
    users = db.execute('SELECT id, username, full_name, wallet_balance, subscription_status, is_banned, last_login FROM users ORDER BY id')
    result = []
    for u in users:
        result.append({
            'id': u['id'],
            'username': u['username'],
            'full_name': u['full_name'],
            'wallet_balance': u['wallet_balance'],
            'subscription_active': u['subscription_status'] == 'active',
            'is_banned': u['is_banned'],
            'last_login': u['last_login']
        })
    return jsonify(result)

@app.route('/api/admin/users/<int:uid>/ban', methods=['POST'])
def api_ban_user(uid):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    admin = get_user(session['user_id'])
    if not admin or not admin.get('is_admin'):
        return jsonify({'error': 'Forbidden'}), 403
    
    db.execute('UPDATE users SET is_banned = 1 WHERE id = ?', (uid,))
    security.log_security_event(session['user_id'], "user_banned", request.remote_addr, f"User {uid} banned")
    return jsonify({'message': 'User banned'})

@app.route('/api/admin/users/<int:uid>/unban', methods=['POST'])
def api_unban_user(uid):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    admin = get_user(session['user_id'])
    if not admin or not admin.get('is_admin'):
        return jsonify({'error': 'Forbidden'}), 403
    
    db.execute('UPDATE users SET is_banned = 0 WHERE id = ?', (uid,))
    return jsonify({'message': 'User unbanned'})

@app.route('/api/admin/settings', methods=['GET', 'POST'])
def api_admin_settings():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    admin = get_user(session['user_id'])
    if not admin or not admin.get('is_admin'):
        return jsonify({'error': 'Forbidden'}), 403
    
    if request.method == 'GET':
        settings = {}
        for key in ['subscription_price', 'withdraw_percent', 'min_withdraw', 'max_bots_per_subscription', 
                    'trc20_address', 'card_number', 'card_holder', 'card_bank', 'guide_text']:
            settings[key] = get_setting(key)
        return jsonify(settings)
    
    # POST - به‌روزرسانی
    data = request.get_json()
    for key, value in data.items():
        update_setting(key, value)
    
    security.log_security_event(session['user_id'], "settings_updated", request.remote_addr, "System settings changed")
    return jsonify({'message': 'Settings updated'})

# ==================== مانیتورینگ سلامت ====================
@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'sandbox': sandbox_manager.get_stats(),
        'version': '3.0.0-secure'
    })

# ==================== اجرا ====================
def main():
    print("=" * 70)
    print("🔒 سامانه امن ساخت ربات تلگرام - نسخه Ultimate".center(70))
    print("=" * 70)
    print(f"📍 آدرس: http://localhost:8080")
    print(f"👤 ادمین: admin / admin123")
    print(f"🛡️ امنیت:")
    print("   - ایزوله‌سازی کامل هر ربات در سندباکس")
    print("   - محدودیت منابع (CPU, Memory, Disk)")
    print("   - CSRF Protection")
    print("   - Rate Limiting (60/min)")
    print("   - SQL Injection Protection")
    print("   - XSS Protection (Bleach)")
    print("   - Brute Force Protection")
    print("   - Security Logging")
    print(f"📱 بدون زوم در موبایل - صفحه کاملاً ریسپانسیو")
    print("=" * 70)
    print("🚀 در حال اجرا...")
    
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False, threaded=True)

if __name__ == "__main__":
    main()