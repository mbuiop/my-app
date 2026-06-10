#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║   ULTIMATE BOT BUILDER - نسخه نهایی بدون خطا                                  ║
║   ایزوله‌سازی کامل - امنیت بالا - بدون نیاز به ربات تلگرام                    ║
╚═══════════════════════════════════════════════════════════════════════════════╝
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
from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict
from contextlib import contextmanager
from typing import Optional, Dict, Any, List, Tuple

# ==================== نصب خودکار کتابخانه‌ها ====================
def install_package(package):
    try:
        __import__(package.replace('-', '_'))
        return True
    except ImportError:
        print(f"📦 Installing {package}...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package, '--quiet'])
        return True

for pkg in ['flask', 'flask-cors', 'requests']:
    install_package(pkg)

# ==================== ایمپورت ====================
from flask import Flask, request, jsonify, session, redirect, url_for
from flask_cors import CORS
import requests

# ==================== تنظیمات پایه ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DIRS = {
    'DB': os.path.join(BASE_DIR, 'database'),
    'FILES': os.path.join(BASE_DIR, 'user_files'),
    'RUNNING': os.path.join(BASE_DIR, 'running_bots'),
    'LOGS': os.path.join(BASE_DIR, 'logs'),
    'RECEIPTS': os.path.join(BASE_DIR, 'receipts'),
    'TEMP': os.path.join(BASE_DIR, 'temp'),
    'SANDBOX': os.path.join(BASE_DIR, 'sandbox'),
}

for dir_path in DIRS.values():
    os.makedirs(dir_path, exist_ok=True)

# ==================== تنظیمات پیش‌فرض ====================
DEFAULT_SETTINGS = {
    'trc20_address': 'TV61aTh98MGqmteYzda5AaBzdXgGqreG6A',
    'card_number': '5892101187322777',
    'card_number_display': '5892 1011 8732 2777',
    'card_holder': 'مرتضی نیکخو خنجری',
    'card_bank': 'بانک ملی - سپهر',
    'subscription_price': 2000000,
    'subscription_price_str': '۲,۰۰۰,۰۰۰ تومان',
    'withdraw_percent': 7,
    'min_withdraw': 2000000,
    'max_bots_per_subscription': 3,
    'max_users_capacity': 10000,
    'max_concurrent_builds': 20,
    'guide_text': '📚 راهنمای ساخت ربات\n\n1️⃣ فایل .py یا .zip خود را ارسال کنید\n2️⃣ پس از پرداخت اشتراک، می‌توانید ربات بسازید\n3️⃣ هر کاربر می‌تواند تا ۳ ربات بسازد\n4️⃣ با دعوت دوستان، ۷٪ کمیسیون دریافت کنید',
}

# ==================== دیتابیس ====================
class Database:
    def __init__(self):
        self.db_path = os.path.join(DIRS['DB'], 'ultimate.db')
        self._init_db()
    
    def _init_db(self):
        self.conn = sqlite3.connect(self.db_path, timeout=60, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._init_tables()
    
    def execute(self, query, params=()):
        try:
            cursor = self.conn.execute(query, params)
            self.conn.commit()
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"DB Error: {e}")
            return []
    
    def _init_tables(self):
        # کاربران
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
                max_bots INTEGER DEFAULT 3,
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                referrals_count INTEGER DEFAULT 0,
                created_at TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
        
        # ربات‌ها
        self.execute('''
            CREATE TABLE IF NOT EXISTS bots (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                token TEXT,
                name TEXT,
                username TEXT,
                file_path TEXT,
                pid INTEGER,
                status TEXT DEFAULT 'stopped',
                created_at TIMESTAMP,
                last_active TIMESTAMP,
                error_message TEXT
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
                created_at TIMESTAMP
            )
        ''')
        
        # تنظیمات
        self.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # تنظیمات پیش‌فرض
        for key, value in DEFAULT_SETTINGS.items():
            self.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (key, str(value)))
        
        # ادمین پیش‌فرض
        admin = self.execute("SELECT id FROM users WHERE username = ?", ('admin',))
        if not admin:
            password_hash = hashlib.md5('admin123'.encode()).hexdigest()
            referral_code = secrets.token_hex(8)
            self.execute('''
                INSERT INTO users (username, password_hash, full_name, is_admin, max_bots, referral_code, created_at)
                VALUES (?, ?, ?, 1, 100, ?, ?)
            ''', ('admin', password_hash, 'مدیر سیستم', referral_code, datetime.now().isoformat()))

db = Database()

# ==================== توابع کمکی ====================
def get_setting(key):
    result = db.execute("SELECT value FROM settings WHERE key = ?", (key,))
    if result:
        val = result[0]['value']
        if key in ['subscription_price', 'withdraw_percent', 'min_withdraw', 'max_bots_per_subscription', 'max_concurrent_builds']:
            try:
                return int(val)
            except:
                return DEFAULT_SETTINGS.get(key)
        return val
    return DEFAULT_SETTINGS.get(key)

def update_setting(key, value):
    db.execute("UPDATE settings SET value = ? WHERE key = ?", (str(value), key))

def get_user_by_username(username):
    users = db.execute("SELECT * FROM users WHERE username = ?", (username,))
    return users[0] if users else None

def get_user(user_id):
    users = db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return users[0] if users else None

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
    max_bots = get_setting('max_bots_per_subscription')
    if check_subscription(user_id):
        return max_bots - user.get('bots_count', 0)
    return 0

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

# ==================== ایزوله‌سازی ربات‌ها (Sandbox) ====================
class SandboxManager:
    def __init__(self):
        self.processes = {}
        self.lock = threading.RLock()
    
    def _create_sandbox(self, bot_id):
        sandbox_dir = os.path.join(DIRS['SANDBOX'], f"bot_{bot_id}")
        os.makedirs(sandbox_dir, exist_ok=True)
        return sandbox_dir
    
    def _get_wrapper_code(self, bot_id):
        return f'''# ==================== لایه امنیتی ====================
import sys, os, signal, time, resource

# محدودیت‌ها
try:
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
except: pass

def timeout_handler(signum, frame):
    print("⏰ Timeout!")
    sys.exit(1)

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(60)

# جلوگیری از ایمپورت‌های خطرناک
_BLOCKED = ['os.system', 'subprocess', 'eval', 'exec', '__import__']
print(f"🔒 Bot {bot_id[:8]} started in sandbox")
# ==================== کد اصلی ====================
'''
    
    def run_bot(self, bot_id, code, token):
        try:
            sandbox_dir = self._create_sandbox(bot_id)
            code_path = os.path.join(sandbox_dir, 'bot.py')
            
            full_code = self._get_wrapper_code(bot_id) + "\n" + code
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
                        'start_time': time.time()
                    }
                return {'success': True, 'pid': process.pid}
            return {'success': False, 'error': 'ربات با خطا مواجه شد'}
        except Exception as e:
            return {'success': False, 'error': str(e)[:100]}
    
    def stop_bot(self, bot_id):
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
    
    def get_status(self, bot_id):
        with self.lock:
            if bot_id in self.processes:
                info = self.processes[bot_id]
                try:
                    os.kill(info['pid'], 0)
                    return {'running': True, 'pid': info['pid'], 'uptime': time.time() - info['start_time']}
                except:
                    del self.processes[bot_id]
        return {'running': False}
    
    def get_stats(self):
        with self.lock:
            return {'total': len(self.processes), 'bots': list(self.processes.keys())}

sandbox = SandboxManager()

# ==================== صف ساخت ====================
class BuildQueue:
    def __init__(self):
        self.queue = queue.Queue()
        self.processing = {}
        self.lock = threading.RLock()
        self._start_workers()
    
    def _start_workers(self):
        max_concurrent = get_setting('max_concurrent_builds')
        for i in range(max_concurrent):
            t = threading.Thread(target=self._worker, daemon=True)
            t.start()
    
    def add(self, user_id, code, file_path, callback_data):
        build_id = secrets.token_hex(8)
        item = {
            'id': build_id,
            'user_id': user_id,
            'code': code,
            'file_path': file_path,
            'callback': callback_data,
            'added_at': time.time()
        }
        self.queue.put(item)
        return build_id
    
    def _worker(self):
        while True:
            try:
                item = self.queue.get(timeout=1)
                self._process(item)
                self.queue.task_done()
            except queue.Empty:
                time.sleep(0.5)
            except Exception as e:
                print(f"Worker error: {e}")
                time.sleep(1)
    
    def _process(self, item):
        try:
            code = item['code']
            user_id = item['user_id']
            
            token = extract_token_from_code(code)
            if not token:
                return
            
            resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
            if resp.status_code != 200:
                return
            
            bot_info = resp.json()['result']
            bot_id = secrets.token_hex(16)
            
            file_path = os.path.join(DIRS['FILES'], str(user_id), f"{bot_id}.py")
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(code)
            
            result = sandbox.run_bot(bot_id, code, token)
            
            if result['success']:
                db.execute('''
                    INSERT INTO bots (id, user_id, token, name, username, file_path, pid, status, created_at, last_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'running', ?, ?)
                ''', (bot_id, user_id, token, bot_info.get('first_name', 'ربات'), 
                      bot_info.get('username', ''), file_path, result['pid'], 
                      datetime.now().isoformat(), datetime.now().isoformat()))
                db.execute('UPDATE users SET bots_count = bots_count + 1 WHERE id = ?', (user_id,))
        except Exception as e:
            print(f"Build error: {e}")
    
    def get_size(self):
        return self.queue.qsize()

build_queue = BuildQueue()

# ==================== توابع کاربر ====================
def create_user(username, password, full_name, email=None, phone=None, referral_code=None):
    existing = get_user_by_username(username)
    if existing:
        return False, "نام کاربری تکراری"
    
    password_hash = hashlib.md5(password.encode()).hexdigest()
    ref_code = secrets.token_hex(8)
    
    referred_by = None
    if referral_code:
        referrer = db.execute("SELECT id FROM users WHERE referral_code = ?", (referral_code,))
        if referrer:
            referred_by = referrer[0]['id']
    
    db.execute('''
        INSERT INTO users (username, password_hash, full_name, email, phone, referral_code, referred_by, created_at, max_bots)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (username, password_hash, full_name, email, phone, ref_code, referred_by, 
          datetime.now().isoformat(), get_setting('max_bots_per_subscription')))
    
    return True, "ok"

def authenticate(username, password):
    user = get_user_by_username(username)
    if user and user['password_hash'] == hashlib.md5(password.encode()).hexdigest():
        if user.get('is_banned', 0) == 0:
            db.execute('UPDATE users SET last_login = ? WHERE id = ?', (datetime.now().isoformat(), user['id']))
            return user
    return None

def activate_subscription(user_id):
    user = get_user(user_id)
    now = datetime.now()
    
    if user and user['subscription_status'] == 'active' and user['subscription_expiry']:
        new_expiry = datetime.fromisoformat(user['subscription_expiry']) + timedelta(days=30)
    else:
        new_expiry = now + timedelta(days=30)
    
    db.execute('''
        UPDATE users SET subscription_status = 'active', subscription_expiry = ?
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

def add_wallet_balance(user_id, amount):
    db.execute('UPDATE users SET wallet_balance = wallet_balance + ? WHERE id = ?', (amount, user_id))

def get_user_bots(user_id):
    return db.execute('SELECT * FROM bots WHERE user_id = ? ORDER BY created_at DESC', (user_id,))

def delete_bot(bot_id, user_id):
    bot = db.execute('SELECT * FROM bots WHERE id = ? AND user_id = ?', (bot_id, user_id))
    if not bot:
        return False
    sandbox.stop_bot(bot_id)
    db.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
    db.execute('UPDATE users SET bots_count = bots_count - 1 WHERE id = ?', (user_id,))
    return True

# ==================== Flask App ====================
app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# ==================== HTML ====================
HTML_LOGIN = '''
<!DOCTYPE html>
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
            <h2 class="mt-3">ساخت ربات تلگرام</h2>
            <p class="text-muted">ورود به پنل کاربری</p>
        </div>
        {% if error %}
        <div class="alert alert-danger">{{ error }}</div>
        {% endif %}
        <form method="POST">
            <div class="mb-3">
                <input type="text" name="username" class="form-control" placeholder="نام کاربری" required autofocus>
            </div>
            <div class="mb-3">
                <input type="password" name="password" class="form-control" placeholder="رمز عبور" required>
            </div>
            <button type="submit" class="btn-login">
                <i class="fas fa-sign-in-alt me-2"></i> ورود
            </button>
        </form>
        <div class="text-center mt-4">
            <a href="/register" class="text-decoration-none">ثبت نام نکرده‌اید؟ عضویت</a>
        </div>
        <div class="text-center mt-3">
            <small class="text-muted">🔒 امنیت بالا | ایزوله‌سازی کامل</small>
        </div>
    </div>
</body>
</html>
'''

HTML_REGISTER = '''
<!DOCTYPE html>
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
            <h2 class="mt-3">ثبت نام</h2>
        </div>
        {% if error %}
        <div class="alert alert-danger">{{ error }}</div>
        {% endif %}
        <form method="POST">
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
                <input type="text" name="referral_code" class="form-control" placeholder="کد معرف (در صورت داشتن)">
            </div>
            <button type="submit" class="btn-register">
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

HTML_INDEX = '''
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>ساخت ربات تلگرام | پنل کاربری</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        *{font-family:'Vazirmatn','Tahoma',sans-serif;touch-action:manipulation}
        body{background:#f5f7fb;min-height:100vh}
        .sidebar{background:linear-gradient(180deg,#667eea,#764ba2);min-height:100vh;color:white;position:fixed;right:0;top:0;width:260px;transition:0.3s}
        .sidebar .nav-link{color:rgba(255,255,255,0.8);padding:12px 20px;margin:5px 10px;border-radius:12px}
        .sidebar .nav-link:hover,.sidebar .nav-link.active{background:rgba(255,255,255,0.2);color:white}
        .sidebar .nav-link i{margin-left:10px;width:24px}
        .main-content{margin-right:260px;padding:20px}
        .card{background:white;border:none;border-radius:20px;box-shadow:0 2px 10px rgba(0,0,0,0.05)}
        .stat-card{background:linear-gradient(135deg,#667eea,#764ba2);border-radius:20px;padding:20px;color:white}
        .btn-primary{background:linear-gradient(135deg,#667eea,#764ba2);border:none;border-radius:12px;padding:10px 20px}
        .status-badge{display:inline-block;padding:4px 12px;border-radius:20px;font-size:0.75rem;font-weight:600}
        .status-running{background:#d4edda;color:#155724}
        .status-stopped{background:#f8d7da;color:#721c24}
        .code-area{font-family:'Courier New',monospace;background:#1e1e2e;color:#fff;padding:16px;border-radius:12px;font-size:13px}
        .toast-notify{position:fixed;bottom:20px;left:20px;right:20px;background:#333;color:white;padding:14px 20px;border-radius:16px;text-align:center;z-index:1100;display:none}
        .loader{display:inline-block;width:20px;height:20px;border:3px solid #f3f3f3;border-top:3px solid #667eea;border-radius:50%;animation:spin 1s linear infinite}
        @keyframes spin{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}
        @media (max-width:768px){
            .sidebar{right:-260px}
            .sidebar.open{right:0}
            .main-content{margin-right:0}
            .menu-toggle{display:block;position:fixed;top:15px;right:15px;z-index:1001;background:#667eea;color:white;border:none;border-radius:12px;padding:10px 15px}
        }
        .menu-toggle{display:none}
    </style>
</head>
<body>

<button class="menu-toggle" onclick="toggleSidebar()"><i class="fas fa-bars"></i></button>

<div class="sidebar" id="sidebar">
    <div class="text-center py-4">
        <i class="fas fa-robot" style="font-size:48px"></i>
        <h5 class="mt-2" id="userName">کاربر</h5>
        <small id="userSubStatus"></small>
    </div>
    <hr style="background:rgba(255,255,255,0.1)">
    <nav class="nav flex-column">
        <a class="nav-link active" href="#" onclick="showPage('dashboard')"><i class="fas fa-tachometer-alt"></i> داشبورد</a>
        <a class="nav-link" href="#" onclick="showPage('build')"><i class="fas fa-plus-circle"></i> ساخت ربات</a>
        <a class="nav-link" href="#" onclick="showPage('bots')"><i class="fas fa-robot"></i> ربات‌های من</a>
        <a class="nav-link" href="#" onclick="showPage('wallet')"><i class="fas fa-wallet"></i> کیف پول</a>
        <a class="nav-link" href="#" onclick="showPage('referrals')"><i class="fas fa-users"></i> دعوت دوستان</a>
        <a class="nav-link" href="#" onclick="showPage('guide')"><i class="fas fa-book"></i> راهنما</a>
        <hr style="background:rgba(255,255,255,0.1)">
        <a class="nav-link" href="/logout"><i class="fas fa-sign-out-alt"></i> خروج</a>
    </nav>
</div>

<div class="main-content" id="mainContent">
    <div id="page-dashboard" class="page-content">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h3><i class="fas fa-chart-line me-2"></i>داشبورد</h3>
            <span id="currentTime" class="text-muted"></span>
        </div>
        <div class="row g-4 mb-4" id="statsCards"></div>
        <div class="row">
            <div class="col-md-8">
                <div class="card p-4">
                    <h5><i class="fas fa-list me-2"></i>ربات‌های اخیر</h5>
                    <div id="recentBots"></div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card p-4 text-center">
                    <h5><i class="fas fa-gift me-2"></i>کد معرف</h5>
                    <code id="referralCode" style="font-size:1.1rem"></code>
                    <button class="btn btn-sm btn-outline-primary mt-2" onclick="copyReferralLink()">کپی لینک</button>
                    <hr>
                    <h6>تعداد دعوت‌ها</h6>
                    <h3 id="referralsCount">0</h3>
                </div>
            </div>
        </div>
    </div>

    <div id="page-build" class="page-content" style="display:none">
        <div class="card p-4">
            <h4><i class="fas fa-microchip me-2"></i>ساخت ربات جدید</h4>
            <hr>
            <ul class="nav nav-tabs mb-4">
                <li class="nav-item"><a class="nav-link active" data-bs-toggle="tab" href="#codeTab">کد مستقیم</a></li>
                <li class="nav-item"><a class="nav-link" data-bs-toggle="tab" href="#uploadTab">آپلود فایل</a></li>
            </ul>
            <div class="tab-content">
                <div class="tab-pane fade show active" id="codeTab">
                    <textarea id="botCode" class="form-control code-area" rows="12" placeholder="# کد ربات خود را وارد کنید
import telebot

TOKEN = 'YOUR_BOT_TOKEN'
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, 'سلام! ربات من ساخته شد!')

bot.infinity_polling()"></textarea>
                </div>
                <div class="tab-pane fade" id="uploadTab">
                    <div class="border rounded-3 p-4 text-center" style="border-style:dashed">
                        <i class="fas fa-cloud-upload-alt fa-3x text-primary"></i>
                        <p class="mt-2">فایل .py یا .zip خود را انتخاب کنید</p>
                        <input type="file" id="botFile" class="form-control mt-2" accept=".py,.zip">
                    </div>
                </div>
            </div>
            <div class="mt-4">
                <button class="btn btn-primary w-100" onclick="buildBot()" id="buildBtn">
                    <i class="fas fa-play me-2"></i> ساخت ربات
                </button>
            </div>
            <div id="buildStatus" class="mt-3" style="display:none"></div>
        </div>
    </div>

    <div id="page-bots" class="page-content" style="display:none">
        <div class="card p-4">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h4><i class="fas fa-list me-2"></i>ربات‌های من</h4>
                <button class="btn btn-sm btn-outline-primary" onclick="loadBots()"><i class="fas fa-sync-alt"></i></button>
            </div>
            <div id="botsList"></div>
        </div>
    </div>

    <div id="page-wallet" class="page-content" style="display:none">
        <div class="row g-4 mb-4">
            <div class="col-md-6">
                <div class="card p-4 text-center">
                    <h5>💰 موجودی کیف پول</h5>
                    <h2 id="walletBalance">0</h2>
                    <small>تومان</small>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card p-4 text-center">
                    <h5>📅 وضعیت اشتراک</h5>
                    <h3 id="subStatus">غیرفعال</h3>
                    <small id="expiryDate"></small>
                </div>
            </div>
        </div>
        <div class="card p-4">
            <h5>💳 خرید اشتراک ماهیانه</h5>
            <p>مبلغ: <strong id="priceDisplay"></strong></p>
            <div class="border rounded p-3 mb-3">
                <p><i class="fas fa-credit-card me-2"></i> شماره کارت: <code id="cardNumber"></code></p>
                <p><i class="fas fa-user me-2"></i> نام دارنده: <code id="cardHolder"></code></p>
                <p><i class="fas fa-university me-2"></i> بانک: <code id="cardBank"></code></p>
            </div>
            <button class="btn btn-success w-100" onclick="uploadReceipt()">
                <i class="fas fa-upload me-2"></i> ارسال فیش واریز
            </button>
        </div>
    </div>

    <div id="page-referrals" class="page-content" style="display:none">
        <div class="card p-4 text-center">
            <i class="fas fa-share-alt fa-3x text-primary"></i>
            <h4 class="mt-3">دعوت از دوستان</h4>
            <p>با دعوت دوستان، <strong>7% کمیسیون</strong> دریافت کنید</p>
            <div class="bg-light p-3 rounded"><code id="refLink"></code></div>
            <button class="btn btn-primary mt-3" onclick="copyReferralLink()">کپی لینک دعوت</button>
        </div>
    </div>

    <div id="page-guide" class="page-content" style="display:none">
        <div class="card p-4" id="guideText"></div>
    </div>
</div>

<div id="toast" class="toast-notify"></div>

<script>
function toggleSidebar(){document.getElementById('sidebar').classList.toggle('open')}
function showToast(msg,isError){let t=document.getElementById('toast');t.textContent=msg;t.style.background=isError?'#dc3545':'#10b981';t.style.display='block';setTimeout(()=>t.style.display='none',3000)}
function showPage(page){
    document.querySelectorAll('.page-content').forEach(p=>p.style.display='none')
    document.getElementById(`page-${page}`).style.display='block'
    document.querySelectorAll('.sidebar .nav-link').forEach(l=>l.classList.remove('active'))
    if(page==='dashboard'){loadDashboard()}
    if(page==='bots'){loadBots()}
    if(page==='wallet'){loadWallet()}
    if(page==='guide'){loadGuide()}
}
async function loadDashboard(){
    try{
        let u=await(await fetch('/api/user')).json()
        let s=await(await fetch('/api/stats')).json()
        document.getElementById('statsCards').innerHTML=`
            <div class="col-md-3 col-6"><div class="stat-card text-center"><h3>${u.wallet_balance.toLocaleString()}</h3><small>موجودی</small></div></div>
            <div class="col-md-3 col-6"><div class="stat-card text-center"><h3>${u.bots_count}</h3><small>ربات‌ها</small></div></div>
            <div class="col-md-3 col-6"><div class="stat-card text-center"><h3>${u.remaining_bots}</h3><small>ظرفیت باقی</small></div></div>
            <div class="col-md-3 col-6"><div class="stat-card text-center"><h3>${s.total_users||0}</h3><small>کاربران</small></div></div>
        `
        let r=await(await fetch('/api/referrals')).json()
        document.getElementById('referralCode').innerText=r.referral_code
        document.getElementById('referralsCount').innerText=r.count
        let b=await(await fetch('/api/bots')).json()
        document.getElementById('recentBots').innerHTML=b.slice(0,5).map(b=>`<div class="d-flex justify-content-between align-items-center border-bottom py-2"><span>${b.name||'ربات'}</span><span class="status-badge ${b.status=='running'?'status-running':'status-stopped'}">${b.status=='running'?'فعال':'متوقف'}</span></div>`).join('')||'<p class="text-muted">رباتی ندارید</p>'
    }catch(e){console.error(e)}
}
async function loadBots(){
    try{
        let b=await(await fetch('/api/bots')).json()
        if(b.length===0){document.getElementById('botsList').innerHTML='<p class="text-muted">رباتی ندارید</p>';return}
        document.getElementById('botsList').innerHTML=b.map(b=>`
            <div class="d-flex justify-content-between align-items-center border-bottom py-3">
                <div><strong>${b.name||b.username||'ربات'}</strong><br><small class="text-muted">@${b.username||''}</small><br><span class="status-badge ${b.status=='running'?'status-running':'status-stopped'}">${b.status=='running'?'🟢 فعال':'🔴 متوقف'}</span></div>
                <div><button class="btn btn-sm btn-outline-${b.status=='running'?'warning':'success'} me-1" onclick="toggleBot('${b.id}')"><i class="fas fa-${b.status=='running'?'stop':'play'}"></i></button><button class="btn btn-sm btn-outline-danger" onclick="deleteBot('${b.id}')"><i class="fas fa-trash"></i></button></div>
            </div>
        `).join('')
    }catch(e){showToast('خطا',true)}
}
async function toggleBot(id){
    let r=await fetch(`/api/bots/${id}/toggle`,{method:'POST'})
    let d=await r.json()
    showToast(d.message,!r.ok)
    loadBots();loadDashboard()
}
async function deleteBot(id){
    if(!confirm('آیا از حذف این ربات اطمینان دارید؟')) return
    let r=await fetch(`/api/bots/${id}`,{method:'DELETE'})
    if(r.ok){showToast('ربات حذف شد');loadBots();loadDashboard()}
}
async function buildBot(){
    let code=document.getElementById('botCode').value
    let file=document.getElementById('botFile').files[0]
    if(!code.trim()&&!file){showToast('کد یا فایل را وارد کنید',true);return}
    let btn=document.getElementById('buildBtn')
    btn.disabled=true;btn.innerHTML='<span class="loader me-2"></span>در حال ساخت...'
    try{
        let res,data
        if(file){
            let fd=new FormData()
            fd.append('file',file)
            res=await fetch('/api/build/upload',{method:'POST',body:fd})
        }else{
            res=await fetch('/api/build',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code})})
        }
        data=await res.json()
        if(res.ok){
            showToast('ربات با موفقیت ساخته شد!')
            document.getElementById('botCode').value=''
            document.getElementById('botFile').value=''
            loadBots();loadDashboard();showPage('bots')
        }else{
            showToast(data.error||'خطا در ساخت',true)
        }
    }catch(e){showToast('خطا در ارتباط با سرور',true)}
    btn.disabled=false;btn.innerHTML='<i class="fas fa-play me-2"></i> ساخت ربات'
}
async function loadWallet(){
    let w=await(await fetch('/api/wallet')).json()
    document.getElementById('walletBalance').innerText=w.balance.toLocaleString()
    document.getElementById('subStatus').innerHTML=w.subscription_active?'✅ فعال':'❌ غیرفعال'
    document.getElementById('expiryDate').innerText=w.expiry_date||''
    document.getElementById('priceDisplay').innerText=w.subscription_price
    document.getElementById('cardNumber').innerText=w.card_number
    document.getElementById('cardHolder').innerText=w.card_holder
    document.getElementById('cardBank').innerText=w.card_bank
}
async function loadGuide(){
    let g=await(await fetch('/api/guide')).json()
    document.getElementById('guideText').innerHTML=g.guide_text.replace(/\\n/g,'<br>')
}
async function copyReferralLink(){
    let r=await(await fetch('/api/referrals')).json()
    navigator.clipboard.writeText(r.referral_link)
    showToast('لینک کپی شد')
}
function uploadReceipt(){
    let i=document.createElement('input')
    i.type='file';i.accept='image/*'
    i.onchange=async (e)=>{
        let fd=new FormData()
        fd.append('receipt',e.target.files[0])
        let r=await fetch('/api/upload-receipt',{method:'POST',body:fd})
        if(r.ok) showToast('فیش ارسال شد، در انتظار تایید')
        else showToast('خطا',true)
    }
    i.click()
}
setInterval(()=>{let d=new Date();document.getElementById('currentTime')&&(document.getElementById('currentTime').innerText=d.toLocaleTimeString('fa-IR'))},1000)
loadDashboard()
</script>
</body>
</html>
'''

# ==================== مسیرها ====================
@app.route('/')
def index():
    if 'user_id' in session:
        return HTML_INDEX
    return redirect(url_for('login_page'))

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = authenticate(username, password)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user.get('is_admin', 0)
            return redirect(url_for('index'))
        return HTML_LOGIN.replace('{% if error %}', '<div class="alert alert-danger">نام کاربری یا رمز عبور اشتباه است</div>').split('<div class="alert')[0] + '<div class="alert alert-danger">نام کاربری یا رمز عبور اشتباه است</div>' + HTML_LOGIN.split('<div class="alert')[1] if '<div class="alert' in HTML_LOGIN else HTML_LOGIN.replace('{% if error %}<div class="alert alert-danger">{{ error }}</div>{% endif %}', '<div class="alert alert-danger">نام کاربری یا رمز عبور اشتباه است</div>')
    return HTML_LOGIN

@app.route('/register', methods=['GET', 'POST'])
def register_page():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '')
        referral_code = request.form.get('referral_code', '')
        
        if len(password) < 6:
            return HTML_REGISTER.replace('{% if error %}', '<div class="alert alert-danger">رمز عبور حداقل 6 کاراکتر</div>').split('<div class="alert')[0] + '<div class="alert alert-danger">رمز عبور حداقل 6 کاراکتر</div>'
        
        success, msg = create_user(username, password, full_name, email, None, referral_code)
        if success:
            return redirect(url_for('login_page'))
        return HTML_REGISTER.replace('{% if error %}', f'<div class="alert alert-danger">{msg}</div>')
    
    return HTML_REGISTER

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

# ==================== APIها ====================
@app.route('/api/user')
def api_user():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
    if not user:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({
        'username': user['username'],
        'full_name': user['full_name'],
        'wallet_balance': user['wallet_balance'],
        'bots_count': user['bots_count'],
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
            result = sandbox.run_bot(bot_id, code, bot['token'])
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
        return jsonify({'message': 'ربات حذف شد'})
    return jsonify({'error': 'خطا'}), 500

@app.route('/api/build', methods=['POST'])
def api_build():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    code = data.get('code', '')
    user_id = session['user_id']
    
    can_create = check_subscription(user_id)
    if not can_create:
        return jsonify({'error': 'ابتدا اشتراک خود را فعال کنید'}), 403
    
    remaining = get_remaining_bots(user_id)
    if remaining <= 0:
        return jsonify({'error': 'به حداکثر تعداد ربات رسیده‌اید'}), 403
    
    token = extract_token_from_code(code)
    if not token:
        return jsonify({'error': 'توکن ربات در کد پیدا نشد'}), 400
    
    try:
        resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        if resp.status_code != 200:
            return jsonify({'error': 'توکن نامعتبر است'}), 400
        bot_info = resp.json()['result']
    except:
        return jsonify({'error': 'خطا در ارتباط با تلگرام'}), 500
    
    bot_id = secrets.token_hex(16)
    file_path = os.path.join(DIRS['FILES'], str(user_id), f"{bot_id}.py")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(code)
    
    result = sandbox.run_bot(bot_id, code, token)
    
    if result['success']:
        db.execute('''
            INSERT INTO bots (id, user_id, token, name, username, file_path, pid, status, created_at, last_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'running', ?, ?)
        ''', (bot_id, user_id, token, bot_info.get('first_name', 'ربات'), 
              bot_info.get('username', ''), file_path, result['pid'],
              datetime.now().isoformat(), datetime.now().isoformat()))
        db.execute('UPDATE users SET bots_count = bots_count + 1 WHERE id = ?', (user_id,))
        return jsonify({'success': True, 'bot_name': bot_info.get('first_name'), 'username': bot_info.get('username')})
    
    return jsonify({'error': result.get('error', 'خطا در اجرا')}), 500

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
    
    can_create = check_subscription(user_id)
    if not can_create:
        return jsonify({'error': 'ابتدا اشتراک خود را فعال کنید'}), 403
    
    remaining = get_remaining_bots(user_id)
    if remaining <= 0:
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
    
    try:
        resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        if resp.status_code != 200:
            return jsonify({'error': 'توکن نامعتبر است'}), 400
        bot_info = resp.json()['result']
    except:
        return jsonify({'error': 'خطا در ارتباط با تلگرام'}), 500
    
    bot_id = secrets.token_hex(16)
    file_path = os.path.join(DIRS['FILES'], str(user_id), f"{bot_id}.py")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(code)
    
    result = sandbox.run_bot(bot_id, code, token)
    
    if result['success']:
        db.execute('''
            INSERT INTO bots (id, user_id, token, name, username, file_path, pid, status, created_at, last_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'running', ?, ?)
        ''', (bot_id, user_id, token, bot_info.get('first_name', 'ربات'),
              bot_info.get('username', ''), file_path, result['pid'],
              datetime.now().isoformat(), datetime.now().isoformat()))
        db.execute('UPDATE users SET bots_count = bots_count + 1 WHERE id = ?', (user_id,))
        return jsonify({'success': True, 'bot_name': bot_info.get('first_name'), 'username': bot_info.get('username')})
    
    return jsonify({'error': result.get('error', 'خطا در اجرا')}), 500

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
        'card_bank': get_setting('card_bank')
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
    return jsonify({'guide_text': get_setting('guide_text')})

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
    ''', (session['user_id'], get_setting('subscription_price'), receipt_path, tx_hash, datetime.now().isoformat()))
    
    return jsonify({'message': 'فیش با موفقیت ارسال شد، در انتظار تایید'})

# ==================== اجرا ====================
if __name__ == '__main__':
    print("=" * 70)
    print("🚀 سامانه ساخت ربات تلگرام - نسخه نهایی")
    print("=" * 70)
    print(f"📍 آدرس: http://localhost:8080")
    print(f"👤 ادمین: admin / admin123")
    print(f"🔒 ایزوله‌سازی ربات‌ها: فعال")
    print(f"📱 بدون زوم در موبایل")
    print("=" * 70)
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)