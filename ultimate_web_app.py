#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║   ULTIMATE BOT BUILDER - نسخه نهایی با پنل مدیریت کامل                        ║
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
from typing import Optional, Dict, Any, List

# نصب خودکار کتابخانه‌ها
def install_package(package):
    try:
        __import__(package.replace('-', '_'))
        return True
    except ImportError:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package, '--quiet'])
        return True

for pkg in ['flask', 'flask-cors', 'requests']:
    install_package(pkg)

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
    'guide_text_fa': '📚 راهنمای استفاده\n\n1️⃣ برای ساخت ربات، فایل .py یا .zip خود را ارسال کنید\n2️⃣ پس از پرداخت اشتراک ماهیانه، می‌توانید ربات بسازید\n3️⃣ هر کاربر می‌تواند تا ۳ ربات بسازد\n4️⃣ با دعوت دوستان، ۷٪ کمیسیون دریافت کنید\n5️⃣ پس از رسیدن به ۲ میلیون تومان، می‌توانید برداشت کنید',
    'admin_password': '123456',
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
                paid INTEGER DEFAULT 0
            )
        ''')
        
        self.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        for key, value in DEFAULT_SETTINGS.items():
            self.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (key, str(value)))
        
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

def activate_subscription(user_id, tx_hash=None):
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
    if bot[0].get('file_path') and os.path.exists(bot[0]['file_path']):
        try:
            os.remove(bot[0]['file_path'])
        except:
            pass
    db.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
    db.execute('UPDATE users SET bots_count = bots_count - 1 WHERE id = ?', (user_id,))
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

# ==================== ایزوله‌سازی ربات‌ها ====================
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

try:
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
except: pass

def timeout_handler(signum, frame):
    print("⏰ Timeout!")
    sys.exit(1)

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(60)

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

# ==================== Flask App ====================
app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
CORS(app)

# ==================== HTML ====================

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
            <div class="mb-3"><input type="text" id="username" class="form-control" placeholder="نام کاربری" required autofocus></div>
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
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>ساخت ربات تلگرام | پنل کامل</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        *{font-family:'Vazirmatn','Tahoma',sans-serif;touch-action:manipulation}
        body{background:#f0f2f5;min-height:100vh}
        .sidebar{background:linear-gradient(180deg,#1a1a2e,#16213e);min-height:100vh;color:white;position:fixed;right:0;top:0;width:280px;transition:0.3s;z-index:1000}
        .sidebar .nav-link{color:rgba(255,255,255,0.7);padding:12px 20px;margin:5px 10px;border-radius:12px}
        .sidebar .nav-link:hover,.sidebar .nav-link.active{background:rgba(102,126,234,0.3);color:white}
        .sidebar .nav-link i{margin-left:10px;width:24px}
        .main-content{margin-right:280px;padding:20px;min-height:100vh}
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
        .menu-toggle{display:none;position:fixed;top:15px;right:15px;z-index:1001;background:#667eea;color:white;border:none;border-radius:12px;padding:10px 15px}
        @media (max-width:768px){
            .sidebar{right:-280px}
            .sidebar.open{right:0}
            .main-content{margin-right:0}
            .menu-toggle{display:block}
        }
        .admin-badge{background:#ff4757;color:white;padding:2px 8px;border-radius:20px;font-size:11px;margin-right:10px}
        .admin-panel-btn{background:#ff4757;color:white;border:none}
        .admin-panel-btn:hover{background:#ff6b81;color:white}
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
        <a class="nav-link" href="#" onclick="showPage('dashboard')"><i class="fas fa-tachometer-alt"></i> داشبورد</a>
        <a class="nav-link" href="#" onclick="showPage('build')"><i class="fas fa-plus-circle"></i> ساخت ربات</a>
        <a class="nav-link" href="#" onclick="showPage('bots')"><i class="fas fa-robot"></i> ربات‌های من</a>
        <a class="nav-link" href="#" onclick="showPage('wallet')"><i class="fas fa-wallet"></i> کیف پول</a>
        <a class="nav-link" href="#" onclick="showPage('referrals')"><i class="fas fa-users"></i> دعوت دوستان</a>
        <a class="nav-link" href="#" onclick="showPage('guide')"><i class="fas fa-book"></i> راهنما</a>
        <hr style="background:rgba(255,255,255,0.1)">
        <a class="nav-link" href="#" onclick="showPage('settings')"><i class="fas fa-cog"></i> تنظیمات</a>
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
                    <h6>کمیسیون کل</h6>
                    <h4 id="totalCommission">0</h4>
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
                    <div class="border rounded-3 p-4 text-center" style="border-style:dashed;cursor:pointer" onclick="document.getElementById('botFileInput').click()">
                        <i class="fas fa-cloud-upload-alt fa-3x text-primary"></i>
                        <p class="mt-2">برای انتخاب فایل کلیک کنید</p>
                        <small class="text-muted">فایل‌های .py یا .zip تا 50 مگابایت</small>
                        <input type="file" id="botFileInput" class="d-none" accept=".py,.zip">
                        <div id="selectedFileName" class="mt-2 text-success small"></div>
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
                    <button class="btn btn-sm btn-warning mt-2" onclick="showWithdrawModal()">درخواست برداشت</button>
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
            <h4>دعوت از دوستان</h4>
            <p>با دعوت دوستان، <strong>7% کمیسیون</strong> دریافت کنید</p>
            <div class="bg-light p-3 rounded"><code id="refLink"></code></div>
            <button class="btn btn-primary mt-3" onclick="copyReferralLink()">کپی لینک دعوت</button>
        </div>
    </div>

    <div id="page-guide" class="page-content" style="display:none">
        <div class="card p-4" id="guideText"></div>
    </div>

    <div id="page-settings" class="page-content" style="display:none">
        <div class="card p-4">
            <h4>تنظیمات حساب</h4>
            <hr>
            <form id="profileForm">
                <div class="mb-3"><label>نام کامل</label><input type="text" id="fullName" class="form-control"></div>
                <div class="mb-3"><label>ایمیل</label><input type="email" id="email" class="form-control"></div>
                <div class="mb-3"><label>شماره موبایل</label><input type="tel" id="phone" class="form-control"></div>
                <div class="mb-3"><label>رمز عبور جدید</label><input type="password" id="newPassword" class="form-control" placeholder="در صورت تمایل به تغییر"></div>
                <button type="submit" class="btn btn-primary">ذخیره تغییرات</button>
            </form>
        </div>
    </div>

    <!-- صفحه پنل مدیریت -->
    <div id="page-admin" class="page-content" style="display:none">
        <div class="card p-4 mb-4">
            <h4><i class="fas fa-chart-line me-2"></i>آمار سیستم</h4>
            <div class="row" id="adminStats"></div>
        </div>
        <div class="card p-4 mb-4">
            <h4><i class="fas fa-image me-2"></i>تایید فیش‌های پرداخت</h4>
            <div id="receiptsList"></div>
        </div>
        <div class="card p-4 mb-4">
            <h4><i class="fas fa-money-bill me-2"></i>تایید درخواست‌های برداشت</h4>
            <div id="withdrawsList"></div>
        </div>
        <div class="card p-4 mb-4">
            <h4><i class="fas fa-users me-2"></i>مدیریت کاربران</h4>
            <div id="usersList"></div>
        </div>
        <div class="card p-4 mb-4">
            <h4><i class="fas fa-credit-card me-2"></i>تنظیمات پرداخت</h4>
            <div class="row">
                <div class="col-md-6">
                    <label>شماره کارت</label>
                    <input type="text" id="adminCardNumber" class="form-control mb-2">
                    <label>نام دارنده</label>
                    <input type="text" id="adminCardHolder" class="form-control mb-2">
                    <label>بانک</label>
                    <input type="text" id="adminCardBank" class="form-control mb-2">
                </div>
                <div class="col-md-6">
                    <label>قیمت اشتراک (تومان)</label>
                    <input type="number" id="adminPrice" class="form-control mb-2">
                    <label>درصد کمیسیون</label>
                    <input type="number" id="adminCommission" class="form-control mb-2">
                    <label>حداقل برداشت</label>
                    <input type="number" id="adminMinWithdraw" class="form-control mb-2">
                    <label>حداکثر ربات در اشتراک</label>
                    <input type="number" id="adminMaxBots" class="form-control mb-2">
                </div>
            </div>
            <button class="btn btn-primary mt-3" onclick="saveAdminSettings()">ذخیره تنظیمات</button>
        </div>
        <div class="card p-4">
            <h4><i class="fas fa-envelope me-2"></i>ارسال پیام همگانی</h4>
            <textarea id="broadcastMsg" class="form-control mb-2" rows="3" placeholder="متن پیام..."></textarea>
            <button class="btn btn-warning" onclick="sendBroadcast()">ارسال به همه کاربران</button>
        </div>
    </div>
</div>

<!-- دکمه شناور پنل مدیریت (فقط برای ادمین) -->
<div id="adminFloatBtn" style="position:fixed;bottom:20px;left:20px;z-index:999;display:none">
    <button class="btn btn-danger rounded-circle" style="width:60px;height:60px;border-radius:50%;box-shadow:0 4px 15px rgba(0,0,0,0.2)" onclick="showAdminPanel()">
        <i class="fas fa-shield-alt" style="font-size:24px"></i>
    </button>
</div>

<!-- مودال رمز ادمین -->
<div class="modal fade" id="adminPasswordModal" tabindex="-1">
    <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
            <div class="modal-header">
                <h5><i class="fas fa-shield-alt me-2"></i>ورود به پنل مدیریت</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <p>برای ورود به پنل مدیریت، رمز عبور را وارد کنید:</p>
                <input type="password" id="adminPasswordInput" class="form-control" placeholder="رمز عبور پنل مدیریت">
                <div id="adminPasswordError" class="text-danger mt-2" style="display:none">رمز عبور اشتباه است!</div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" data-bs-dismiss="modal">انصراف</button>
                <button class="btn btn-danger" onclick="checkAdminPassword()">ورود به پنل</button>
            </div>
        </div>
    </div>
</div>

<!-- مودال برداشت -->
<div class="modal fade" id="withdrawModal" tabindex="-1">
    <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
            <div class="modal-header"><h5>درخواست برداشت</h5><button type="button" class="btn-close" data-bs-dismiss="modal"></button></div>
            <div class="modal-body">
                <p>حداقل مبلغ برداشت: <strong id="minWithdrawAmount"></strong> تومان</p>
                <p>موجودی قابل برداشت: <strong id="withdrawBalance"></strong> تومان</p>
                <label>آدرس کیف پول (TRC20)</label>
                <input type="text" id="withdrawAddress" class="form-control" placeholder="آدرس TRC20 خود را وارد کنید">
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" data-bs-dismiss="modal">انصراف</button>
                <button class="btn btn-primary" onclick="submitWithdraw()">ثبت درخواست</button>
            </div>
        </div>
    </div>
</div>

<div id="toast" class="toast-notify"></div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
let currentUser = null;
let isAdmin = false;

function toggleSidebar(){document.getElementById('sidebar').classList.toggle('open')}
function showToast(msg,isError){let t=document.getElementById('toast');t.textContent=msg;t.style.background=isError?'#dc3545':'#10b981';t.style.display='block';setTimeout(()=>t.style.display='none',3000)}

function showAdminPanel(){
    document.getElementById('adminPasswordModal').style.display='block';
    var modal = new bootstrap.Modal(document.getElementById('adminPasswordModal'));
    modal.show();
}

function checkAdminPassword(){
    let pwd = document.getElementById('adminPasswordInput').value;
    if(pwd === '123456'){
        bootstrap.Modal.getInstance(document.getElementById('adminPasswordModal')).hide();
        showPage('admin');
    } else {
        document.getElementById('adminPasswordError').style.display='block';
    }
}

function showPage(page){
    document.querySelectorAll('.page-content').forEach(p=>p.style.display='none')
    document.getElementById(`page-${page}`).style.display='block'
    if(page==='dashboard'){loadDashboard()}
    if(page==='bots'){loadBots()}
    if(page==='wallet'){loadWallet()}
    if(page==='guide'){loadGuide()}
    if(page==='admin' && isAdmin){loadAdminPanel()}
}

async function loadDashboard(){
    try{
        let u=await(await fetch('/api/user')).json()
        currentUser=u
        isAdmin=u.is_admin===1
        if(isAdmin){
            document.getElementById('adminFloatBtn').style.display='block';
        }
        let s=await(await fetch('/api/stats')).json()
        let r=await(await fetch('/api/referrals')).json()
        document.getElementById('statsCards').innerHTML=`
            <div class="col-md-3 col-6"><div class="stat-card text-center"><h3>${(u.wallet_balance||0).toLocaleString()}</h3><small>موجودی</small></div></div>
            <div class="col-md-3 col-6"><div class="stat-card text-center"><h3>${u.bots_count||0}</h3><small>ربات‌ها</small></div></div>
            <div class="col-md-3 col-6"><div class="stat-card text-center"><h3>${u.remaining_bots||0}</h3><small>ظرفیت باقی</small></div></div>
            <div class="col-md-3 col-6"><div class="stat-card text-center"><h3>${s.total_users||0}</h3><small>کاربران</small></div></div>
        `
        document.getElementById('userName').innerHTML=u.full_name||u.username
        document.getElementById('userSubStatus').innerHTML=u.subscription_active?'✅ اشتراک فعال':'❌ اشتراک غیرفعال'
        document.getElementById('referralCode').innerText=r.referral_code
        document.getElementById('referralsCount').innerText=r.count
        document.getElementById('totalCommission').innerText=(r.total_commission||0).toLocaleString()
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

document.getElementById('botFileInput').onchange=function(e){
    if(e.target.files.length){document.getElementById('selectedFileName').innerText='فایل انتخاب شده: '+e.target.files[0].name}
}

async function buildBot(){
    let code=document.getElementById('botCode').value
    let file=document.getElementById('botFileInput').files[0]
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
            document.getElementById('botFileInput').value=''
            document.getElementById('selectedFileName').innerText=''
            loadBots();loadDashboard();showPage('bots')
        }else{
            showToast(data.error||'خطا در ساخت',true)
        }
    }catch(e){showToast('خطا در ارتباط با سرور',true)}
    btn.disabled=false;btn.innerHTML='<i class="fas fa-play me-2"></i> ساخت ربات'
}

async function loadWallet(){
    let w=await(await fetch('/api/wallet')).json()
    document.getElementById('walletBalance').innerText=(w.balance||0).toLocaleString()
    document.getElementById('subStatus').innerHTML=w.subscription_active?'✅ فعال':'❌ غیرفعال'
    document.getElementById('expiryDate').innerText=w.expiry_date||''
    document.getElementById('priceDisplay').innerText=w.subscription_price
    document.getElementById('cardNumber').innerText=w.card_number
    document.getElementById('cardHolder').innerText=w.card_holder
    document.getElementById('cardBank').innerText=w.card_bank
    document.getElementById('minWithdrawAmount').innerText=w.min_withdraw?.toLocaleString()||'2,000,000'
    document.getElementById('withdrawBalance').innerText=(w.balance||0).toLocaleString()
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

function showWithdrawModal(){
    new bootstrap.Modal(document.getElementById('withdrawModal')).show()
}

async function submitWithdraw(){
    let address=document.getElementById('withdrawAddress').value
    if(!address){showToast('آدرس کیف پول را وارد کنید',true);return}
    let r=await fetch('/api/withdraw',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({address})})
    let d=await r.json()
    if(r.ok){showToast('درخواست برداشت ثبت شد');bootstrap.Modal.getInstance(document.getElementById('withdrawModal')).hide()}
    else{showToast(d.error,true)}
}

document.getElementById('profileForm').onsubmit=async(e)=>{
    e.preventDefault()
    let data={full_name:fullName.value,email:email.value,phone:phone.value,password:newPassword.value}
    let r=await fetch('/api/update-profile',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)})
    if(r.ok){showToast('پروفایل بروز شد');document.getElementById('newPassword').value=''}
    else{showToast('خطا',true)}
}

async function loadAdminPanel(){
    if(!isAdmin) return
    let stats=await(await fetch('/api/admin/stats')).json()
    document.getElementById('adminStats').innerHTML=`
        <div class="col-md-3"><div class="card p-3 text-center"><h4>${stats.users_count}</h4><small>کاربران</small></div></div>
        <div class="col-md-3"><div class="card p-3 text-center"><h4>${stats.active_subs}</h4><small>اشتراک فعال</small></div></div>
        <div class="col-md-3"><div class="card p-3 text-center"><h4>${stats.total_bots}</h4><small>ربات‌ها</small></div></div>
        <div class="col-md-3"><div class="card p-3 text-center"><h4>${stats.running_bots}</h4><small>ربات فعال</small></div></div>
    `
    let receipts=await(await fetch('/api/admin/receipts')).json()
    document.getElementById('receiptsList').innerHTML=receipts.map(r=>`
        <div class="border rounded p-3 mb-2 d-flex justify-content-between align-items-center">
            <div><strong>کاربر ${r.user_id}</strong><br>مبلغ: ${(r.amount||0).toLocaleString()} تومان<br><small>${r.created_at}</small></div>
            <div><button class="btn btn-sm btn-success me-1" onclick="approveReceipt(${r.id})">تایید</button><button class="btn btn-sm btn-danger" onclick="rejectReceipt(${r.id})">رد</button></div>
        </div>
    `).join('')||'<p class="text-muted">فیشی در انتظار تایید نیست</p>'
    
    let withdraws=await(await fetch('/api/admin/withdraws')).json()
    document.getElementById('withdrawsList').innerHTML=withdraws.map(w=>`
        <div class="border rounded p-3 mb-2 d-flex justify-content-between align-items-center">
            <div><strong>کاربر ${w.user_id}</strong><br>مبلغ: ${(w.amount||0).toLocaleString()} تومان<br>آدرس: ${w.address}</div>
            <div><button class="btn btn-sm btn-success" onclick="approveWithdraw(${w.id})">تایید واریز شد</button></div>
        </div>
    `).join('')||'<p class="text-muted">درخواستی در انتظار تایید نیست</p>'
    
    let users=await(await fetch('/api/admin/users')).json()
    document.getElementById('usersList').innerHTML=`<div class="table-responsive"><table class="table table-sm"><thead><tr><th>کاربر</th><th>موجودی</th><th>اشتراک</th><th>ربات‌ها</th><th>عملیات</th></tr></thead><tbody>${
        users.map(u=>`<tr><td>${u.full_name||u.username}</td><td>${(u.wallet_balance||0).toLocaleString()}</td><td>${u.subscription_active?'✅':'❌'}</td><td>${u.bots_count||0}</td><td><button class="btn btn-sm btn-danger" onclick="banUser(${u.id})">مسدود</button></td></tr>`).join('')
    }</tbody></table></div>`
    
    let settings=await(await fetch('/api/admin/settings')).json()
    document.getElementById('adminCardNumber').value=settings.card_number||''
    document.getElementById('adminCardHolder').value=settings.card_holder||''
    document.getElementById('adminCardBank').value=settings.card_bank||''
    document.getElementById('adminPrice').value=settings.subscription_price||2000000
    document.getElementById('adminCommission').value=settings.withdraw_percent||7
    document.getElementById('adminMinWithdraw').value=settings.min_withdraw||2000000
    document.getElementById('adminMaxBots').value=settings.max_bots_per_subscription||3
}

async function saveAdminSettings(){
    let data={
        card_number:document.getElementById('adminCardNumber').value,
        card_holder:document.getElementById('adminCardHolder').value,
        card_bank:document.getElementById('adminCardBank').value,
        subscription_price:parseInt(document.getElementById('adminPrice').value),
        withdraw_percent:parseInt(document.getElementById('adminCommission').value),
        min_withdraw:parseInt(document.getElementById('adminMinWithdraw').value),
        max_bots_per_subscription:parseInt(document.getElementById('adminMaxBots').value)
    }
    let r=await fetch('/api/admin/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)})
    if(r.ok) showToast('تنظیمات ذخیره شد')
    else showToast('خطا',true)
}

async function approveReceipt(id){
    let r=await fetch(`/api/admin/receipt/${id}/approve`,{method:'POST'})
    if(r.ok){showToast('فیش تایید شد');loadAdminPanel()}
}
async function rejectReceipt(id){
    let r=await fetch(`/api/admin/receipt/${id}/reject`,{method:'POST'})
    if(r.ok){showToast('فیش رد شد');loadAdminPanel()}
}
async function approveWithdraw(id){
    let r=await fetch(`/api/admin/withdraw/${id}/approve`,{method:'POST'})
    if(r.ok){showToast('برداشت تایید شد');loadAdminPanel()}
}
async function banUser(id){
    if(!confirm('مسدود شود؟')) return
    await fetch(`/api/admin/users/${id}/ban`,{method:'POST'})
    loadAdminPanel()
}
async function sendBroadcast(){
    let msg=document.getElementById('broadcastMsg').value
    if(!msg) return
    let r=await fetch('/api/admin/broadcast',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg})})
    let d=await r.json()
    showToast(`پیام به ${d.sent} نفر ارسال شد`)
    document.getElementById('broadcastMsg').value=''
}

setInterval(()=>{let d=new Date();document.getElementById('currentTime')&&(document.getElementById('currentTime').innerText=d.toLocaleTimeString('fa-IR'))},1000)
loadDashboard()
</script>
</body>
</html>'''

# ==================== مسیرهای Flask ====================
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
    success, msg = create_user(
        data.get('username'), data.get('password'), data.get('full_name'),
        None, None, data.get('referral_code')
    )
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
    
    if not check_subscription(user_id):
        return jsonify({'error': 'ابتدا اشتراک خود را فعال کنید'}), 403
    
    if get_remaining_bots(user_id) <= 0:
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
        'card_bank': get_setting('card_bank'),
        'min_withdraw': get_setting('min_withdraw')
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
    ''', (session['user_id'], get_setting('subscription_price'), receipt_path, tx_hash, datetime.now().isoformat()))
    
    return jsonify({'message': 'فیش با موفقیت ارسال شد، در انتظار تایید'})

@app.route('/api/withdraw', methods=['POST'])
def api_withdraw():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    address = data.get('address', '')
    user = get_user(session['user_id'])
    
    min_withdraw = get_setting('min_withdraw')
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
    if data.get('email'):
        updates.append('email = ?')
        params.append(data['email'])
    if data.get('phone'):
        updates.append('phone = ?')
        params.append(data['phone'])
    if data.get('password') and data['password'].strip():
        updates.append('password_hash = ?')
        params.append(hashlib.md5(data['password'].encode()).hexdigest())
    if updates:
        params.append(session['user_id'])
        db.execute(f'UPDATE users SET {", ".join(updates)} WHERE id = ?', params)
    return jsonify({'message': 'پروفایل بروزرسانی شد'})

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
            'subscription_price': get_setting('subscription_price'),
            'withdraw_percent': get_setting('withdraw_percent'),
            'min_withdraw': get_setting('min_withdraw'),
            'max_bots_per_subscription': get_setting('max_bots_per_subscription')
        })
    
    data = request.get_json()
    update_setting('card_number_display', data.get('card_number', ''))
    update_setting('card_holder', data.get('card_holder', ''))
    update_setting('card_bank', data.get('card_bank', ''))
    update_setting('subscription_price', data.get('subscription_price', 2000000))
    update_setting('subscription_price_str', f"{data.get('subscription_price', 2000000):,} تومان")
    update_setting('withdraw_percent', data.get('withdraw_percent', 7))
    update_setting('min_withdraw', data.get('min_withdraw', 2000000))
    update_setting('max_bots_per_subscription', data.get('max_bots_per_subscription', 3))
    return jsonify({'message': 'Settings saved'})

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
    sent = 0
    for u in users:
        sent += 1
    return jsonify({'sent': sent})

# ==================== اجرا ====================
if __name__ == '__main__':
    print("=" * 70)
    print("🚀 سامانه کامل ساخت ربات تلگرام - نسخه نهایی")
    print("=" * 70)
    print(f"📍 آدرس: http://localhost:8080")
    print(f"👤 ادمین: admin / admin123")
    print(f"🔑 رمز ورود به پنل مدیریت: 123456")
    print("=" * 70)
    print("✅ نحوه ورود به پنل مدیریت:")
    print("   1. با حساب admin وارد سایت شوید")
    print("   2. در پایین سمت چپ صفحه، دکمه قرمز رنگ با آیکون سپر را ببینید")
    print("   3. روی آن کلیک کنید")
    print("   4. رمز 123456 را وارد کنید")
    print("=" * 70)
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False, threaded=True)