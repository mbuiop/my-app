#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
═══════════════════════════════════════════════════════════════════════════════
🌐 سامانه کامل ساخت ربات تلگرام - بدون نیاز به ربات تلگرام
📱 پنل مدیریت، ساخت ربات، کیف پول، اشتراک و همه چیز در سایت
⚡ با قابلیت اجرای ربات‌های تلگرام روی سرور
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
from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict
from typing import Optional, Dict, Any, List
from pathlib import Path

import requests
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS

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
}

for dir_path in DIRS.values():
    os.makedirs(dir_path, exist_ok=True)

# ==================== لاگینگ ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(DIRS['LOGS'], 'web_app.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('WebApp')

# ==================== تنظیمات ====================
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"  # تغییر دهید
ADMIN_USERNAME_2 = "mortaza"
ADMIN_PASSWORD_2 = "13741374"

# تنظیمات پیش‌فرض
DEFAULT_SETTINGS = {
    'trc20_address': "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A",
    'card_number': "5892101187322777",
    'card_number_display': "5892 1011 8732 2777",
    'card_holder': "مرتضی نیکخو خنجری",
    'card_bank': "بانک ملی - سپهر",
    'subscription_price': 2000000,
    'subscription_price_str': "۲,۰۰۰,۰۰۰ تومان",
    'withdraw_percent': 7,
    'min_withdraw': 2000000,
    'max_bots_per_subscription': 3,
    'max_users_capacity': 10000,
    'guide_text': "📚 راهنمای ساخت ربات\n\n1️⃣ فایل .py یا .zip خود را ارسال کنید\n2️⃣ پس از پرداخت اشتراک ماهیانه، می‌توانید ربات بسازید\n3️⃣ هر کاربر می‌تواند تا ۳ ربات بسازد\n4️⃣ با دعوت دوستان، ۷٪ کمیسیون دریافت کنید",
    'welcome_text': "🚀 به سامانه ساخت ربات تلگرام خوش آمدید",
    'max_builds_per_day': 10,
    'health_check_interval': 30,
}

# ==================== دیتابیس ====================
class Database:
    def __init__(self):
        self.conn = None
        self._init_db()
        self._init_tables()
    
    def _init_db(self):
        db_path = os.path.join(DIRS['DB'], 'web_app.db')
        self.conn = sqlite3.connect(db_path, timeout=60, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
    
    def execute(self, query, params=()):
        try:
            cursor = self.conn.execute(query, params)
            self.conn.commit()
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"DB error: {e}")
            return []
    
    def _init_tables(self):
        # کاربران
        self.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
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
                error_message TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        
        # فیش‌های پرداخت
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
        
        # تنظیمات سیستم
        self.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
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
                new_bots INTEGER DEFAULT 0,
                new_subscriptions INTEGER DEFAULT 0,
                total_revenue INTEGER DEFAULT 0
            )
        ''')
        
        # تنظیمات پیش‌فرض
        for key, value in DEFAULT_SETTINGS.items():
            self.execute('INSERT OR IGNORE INTO system_settings (key, value, updated_at) VALUES (?, ?, ?)',
                        (key, str(value), datetime.now().isoformat()))
        
        # ایجاد ادمین پیش‌فرض
        admin_exists = self.execute("SELECT * FROM users WHERE username = ?", (ADMIN_USERNAME,))
        if not admin_exists:
            self.execute('''
                INSERT INTO users (username, password, full_name, is_admin, wallet_balance, created_at, max_bots)
                VALUES (?, ?, ?, 1, 0, ?, 100)
            ''', (ADMIN_USERNAME, hashlib.md5(ADMIN_PASSWORD.encode()).hexdigest(), "مدیر سیستم", datetime.now().isoformat()))

db = Database()

# ==================== توابع کمکی ====================
def get_setting(key):
    result = db.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
    if result:
        val = result[0]['value']
        if key in ['subscription_price', 'withdraw_percent', 'min_withdraw', 'max_bots_per_subscription', 'max_builds_per_day', 'max_users_capacity']:
            try:
                return int(val)
            except:
                return DEFAULT_SETTINGS.get(key)
        return val
    return DEFAULT_SETTINGS.get(key)

def update_setting(key, value):
    db.execute("UPDATE system_settings SET value = ?, updated_at = ? WHERE key = ?",
               (str(value), datetime.now().isoformat(), key))

def get_user(user_id):
    users = db.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    return dict(users[0]) if users else None

def get_user_by_username(username):
    users = db.execute('SELECT * FROM users WHERE username = ?', (username,))
    return dict(users[0]) if users else None

def create_user(username, password, full_name, email=None, phone=None, referred_by=None):
    now = datetime.now().isoformat()
    referral_code = hashlib.md5(f"{username}_{time.time()}".encode()).hexdigest()[:12]
    max_bots = get_setting('max_bots_per_subscription')
    
    db.execute('''
        INSERT INTO users (username, password, full_name, email, phone, referral_code, referred_by, created_at, max_bots)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (username, hashlib.md5(password.encode()).hexdigest(), full_name, email, phone, referral_code, referred_by, now, max_bots))
    
    return True

def authenticate(username, password):
    user = get_user_by_username(username)
    if user and user['password'] == hashlib.md5(password.encode()).hexdigest():
        return user
    return None

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
    
    max_bots = user.get('max_bots', get_setting('max_bots_per_subscription'))
    if check_subscription(user_id):
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
    
    # اضافه کردن کمیسیون به معرف
    if user and user.get('referred_by'):
        commission_percent = get_setting('withdraw_percent')
        price = get_setting('subscription_price')
        commission = int(price * commission_percent / 100)
        
        db.execute('UPDATE users SET wallet_balance = wallet_balance + ?, total_commission = total_commission + ? WHERE id = ?',
                  (commission, commission, user['referred_by']))
    
    logger.info(f"Subscription activated for user {user_id}")

def add_wallet_balance(user_id, amount):
    db.execute('UPDATE users SET wallet_balance = wallet_balance + ? WHERE id = ?', (amount, user_id))

def get_user_bots(user_id):
    bots = db.execute('SELECT * FROM bots WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    return [dict(bot) for bot in bots]

def get_bot(bot_id):
    bots = db.execute('SELECT * FROM bots WHERE id = ?', (bot_id,))
    return dict(bots[0]) if bots else None

def delete_bot(bot_id, user_id):
    bot_rec = get_bot(bot_id)
    if not bot_rec or bot_rec['user_id'] != user_id:
        return False
    
    # توقف ربات اگر در حال اجراست
    if bot_id in machine_manager.processes:
        machine_manager.stop_bot(bot_id)
    
    # حذف فایل
    if bot_rec.get('file_path') and os.path.exists(bot_rec['file_path']):
        try:
            os.remove(bot_rec['file_path'])
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

def add_bot(user_id, bot_id, token, name, username, file_path, pid=None):
    now = datetime.now().isoformat()
    db.execute('''
        INSERT INTO bots (id, user_id, token, name, username, file_path, pid, status, created_at, last_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'running', ?, ?)
    ''', (bot_id, user_id, token, name, username, file_path, pid, now, now))
    db.execute('UPDATE users SET bots_count = bots_count + 1 WHERE id = ?', (user_id,))
    return True

# ==================== مدیریت اجرای ربات‌ها ====================
class MachineManager:
    def __init__(self):
        self.processes = {}
        self.lock = threading.RLock()
        self._restore_bots()
    
    def _restore_bots(self):
        """بازیابی ربات‌ها پس از ریستارت"""
        try:
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
                    else:
                        db.execute('UPDATE bots SET status = "stopped" WHERE id = ?', (bot_id,))
            logger.info(f"✅ Restored {restored} bots")
        except Exception as e:
            logger.error(f"Restore failed: {e}")
    
    def run_bot(self, bot_id, code, token, restore=False):
        try:
            # ایجاد دایرکتوری برای ربات
            bot_dir = os.path.join(DIRS['RUNNING'], bot_id)
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
                        'dir': bot_dir,
                        'start_time': time.time()
                    }
                
                if not restore:
                    db.execute("UPDATE bots SET status = 'running', pid = ?, last_active = ? WHERE id = ?",
                              (process.pid, datetime.now().isoformat(), bot_id))
                
                return {'success': True, 'pid': process.pid}
            else:
                return {'success': False, 'error': 'ربات با خطا مواجه شد'}
        except Exception as e:
            return {'success': False, 'error': str(e)[:100]}
    
    def stop_bot(self, bot_id):
        with self.lock:
            if bot_id in self.processes:
                try:
                    info = self.processes[bot_id]
                    os.kill(info['pid'], signal.SIGTERM)
                    time.sleep(1)
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
                    return {'running': True, 'pid': info['pid'], 'uptime': time.time() - info['start_time']}
                except:
                    if bot_id in self.processes:
                        del self.processes[bot_id]
                        db.execute("UPDATE bots SET status = 'stopped' WHERE id = ?", (bot_id,))
        return {'running': False}
    
    def restart_all_dead_bots(self):
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

# ==================== Flask App ====================
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "web_app_secret_key_2024")
CORS(app)

machine_manager = MachineManager()

# ==================== دکوراتورهای احراز هویت ====================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        user = get_user(session['user_id'])
        if not user or user.get('is_admin', 0) != 1:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== صفحات HTML ====================

HTML_LOGIN = '''
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ورود | سامانه ساخت ربات تلگرام</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { font-family: 'Vazirmatn', 'Tahoma', sans-serif; }
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .login-card {
            background: rgba(255,255,255,0.95);
            border-radius: 30px;
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25);
            padding: 40px;
            max-width: 450px;
            width: 100%;
            animation: fadeIn 0.5s ease;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .login-card h2 {
            color: #4a5568;
            margin-bottom: 30px;
            text-align: center;
        }
        .form-control {
            border-radius: 12px;
            padding: 12px 15px;
            border: 2px solid #e2e8f0;
        }
        .form-control:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102,126,234,0.1);
        }
        .btn-login {
            background: linear-gradient(135deg, #667eea, #764ba2);
            border: none;
            border-radius: 12px;
            padding: 12px;
            font-weight: 600;
            width: 100%;
            color: white;
        }
        .btn-login:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102,126,234,0.4);
        }
        .register-link {
            text-align: center;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="login-card">
        <div class="text-center mb-4">
            <i class="fas fa-robot" style="font-size: 64px; color: #667eea;"></i>
            <h2 class="mt-3">ساخت ربات تلگرام</h2>
            <p class="text-muted">وارد شوید تا ربات خود را بسازید</p>
        </div>
        <form action="/login" method="POST">
            <div class="mb-3">
                <label class="form-label">نام کاربری</label>
                <input type="text" name="username" class="form-control" required autofocus>
            </div>
            <div class="mb-3">
                <label class="form-label">رمز عبور</label>
                <input type="password" name="password" class="form-control" required>
            </div>
            <button type="submit" class="btn btn-login">
                <i class="fas fa-sign-in-alt me-2"></i>
                ورود
            </button>
        </form>
        <div class="register-link">
            <a href="/register" class="text-decoration-none">ثبت نام نکرده‌اید؟ ثبت نام کنید</a>
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
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ثبت نام | سامانه ساخت ربات تلگرام</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { font-family: 'Vazirmatn', 'Tahoma', sans-serif; }
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .register-card {
            background: rgba(255,255,255,0.95);
            border-radius: 30px;
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25);
            padding: 40px;
            max-width: 500px;
            width: 100%;
            animation: fadeIn 0.5s ease;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .form-control {
            border-radius: 12px;
            padding: 12px 15px;
            border: 2px solid #e2e8f0;
        }
        .btn-register {
            background: linear-gradient(135deg, #667eea, #764ba2);
            border: none;
            border-radius: 12px;
            padding: 12px;
            font-weight: 600;
            width: 100%;
            color: white;
        }
    </style>
</head>
<body>
    <div class="register-card">
        <div class="text-center mb-4">
            <i class="fas fa-user-plus" style="font-size: 64px; color: #667eea;"></i>
            <h2 class="mt-3">ثبت نام</h2>
        </div>
        <form action="/register" method="POST">
            <div class="mb-3">
                <label class="form-label">نام کاربری</label>
                <input type="text" name="username" class="form-control" required>
            </div>
            <div class="mb-3">
                <label class="form-label">رمز عبور</label>
                <input type="password" name="password" class="form-control" required>
            </div>
            <div class="mb-3">
                <label class="form-label">نام کامل</label>
                <input type="text" name="full_name" class="form-control" required>
            </div>
            <div class="mb-3">
                <label class="form-label">ایمیل (اختیاری)</label>
                <input type="email" name="email" class="form-control">
            </div>
            <div class="mb-3">
                <label class="form-label">شماره موبایل (اختیاری)</label>
                <input type="tel" name="phone" class="form-control">
            </div>
            <div class="mb-3">
                <label class="form-label">کد معرف (در صورت داشتن)</label>
                <input type="text" name="referral_code" class="form-control">
            </div>
            <button type="submit" class="btn btn-register">
                <i class="fas fa-check-circle me-2"></i>
                ثبت نام
            </button>
        </form>
        <div class="text-center mt-3">
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
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <title>ساخت ربات تلگرام | پنل کاربری</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { font-family: 'Vazirmatn', 'Tahoma', sans-serif; }
        body {
            background: #f5f7fb;
            min-height: 100vh;
        }
        .sidebar {
            background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: white;
            position: fixed;
            right: 0;
            top: 0;
            width: 260px;
            z-index: 100;
        }
        .sidebar .nav-link {
            color: rgba(255,255,255,0.8);
            padding: 12px 20px;
            margin: 5px 10px;
            border-radius: 12px;
            transition: all 0.3s;
        }
        .sidebar .nav-link:hover, .sidebar .nav-link.active {
            background: rgba(255,255,255,0.2);
            color: white;
        }
        .sidebar .nav-link i {
            margin-left: 10px;
            width: 24px;
        }
        .main-content {
            margin-right: 260px;
            padding: 20px;
        }
        .card-stats {
            background: white;
            border: none;
            border-radius: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            transition: transform 0.3s;
        }
        .card-stats:hover {
            transform: translateY(-5px);
        }
        .btn-primary {
            background: linear-gradient(135deg, #667eea, #764ba2);
            border: none;
            border-radius: 12px;
            padding: 10px 20px;
        }
        .bot-card {
            background: white;
            border-radius: 16px;
            padding: 15px;
            margin-bottom: 15px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            transition: all 0.3s;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .status-running { background: #28a74520; color: #28a745; }
        .status-stopped { background: #dc354520; color: #dc3545; }
        .code-area {
            font-family: monospace;
            background: #1e1e2e;
            color: #fff;
            padding: 15px;
            border-radius: 12px;
            font-size: 0.85rem;
        }
        @media (max-width: 768px) {
            .sidebar {
                position: fixed;
                right: -260px;
                transition: 0.3s;
                z-index: 1000;
            }
            .sidebar.open {
                right: 0;
            }
            .main-content {
                margin-right: 0;
            }
            .menu-toggle {
                display: block;
                position: fixed;
                top: 15px;
                right: 15px;
                z-index: 1001;
                background: #667eea;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px;
            }
        }
        .menu-toggle { display: none; }
        .toast-notify {
            position: fixed;
            bottom: 20px;
            left: 20px;
            right: 20px;
            background: #333;
            color: white;
            padding: 12px 20px;
            border-radius: 12px;
            text-align: center;
            z-index: 1100;
            display: none;
        }
    </style>
</head>
<body>

<button class="menu-toggle" onclick="toggleSidebar()">
    <i class="fas fa-bars"></i>
</button>

<div class="sidebar" id="sidebar">
    <div class="text-center py-4">
        <i class="fas fa-robot" style="font-size: 48px;"></i>
        <h5 class="mt-2" id="userName">کاربر</h5>
        <small id="userSubStatus"></small>
    </div>
    <hr style="background: rgba(255,255,255,0.2);">
    <nav class="nav flex-column">
        <a class="nav-link" href="#" onclick="showPage('dashboard')">
            <i class="fas fa-tachometer-alt"></i> داشبورد
        </a>
        <a class="nav-link" href="#" onclick="showPage('build')">
            <i class="fas fa-plus-circle"></i> ساخت ربات
        </a>
        <a class="nav-link" href="#" onclick="showPage('bots')">
            <i class="fas fa-robot"></i> ربات‌های من
        </a>
        <a class="nav-link" href="#" onclick="showPage('wallet')">
            <i class="fas fa-wallet"></i> کیف پول
        </a>
        <a class="nav-link" href="#" onclick="showPage('referrals')">
            <i class="fas fa-users"></i> دعوت دوستان
        </a>
        <a class="nav-link" href="#" onclick="showPage('guide')">
            <i class="fas fa-book"></i> راهنما
        </a>
        <hr style="background: rgba(255,255,255,0.2);">
        <a class="nav-link" href="#" onclick="showPage('settings')">
            <i class="fas fa-cog"></i> تنظیمات
        </a>
        <a class="nav-link" href="/logout" onclick="return confirm('خروج از حساب؟')">
            <i class="fas fa-sign-out-alt"></i> خروج
        </a>
    </nav>
</div>

<div class="main-content" id="mainContent">
    <div id="page-dashboard" class="page-content">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h3><i class="fas fa-tachometer-alt me-2"></i>داشبورد</h3>
            <span id="currentTime" class="text-muted"></span>
        </div>
        
        <div class="row g-4 mb-4" id="statsCards">
            <div class="col-md-3 col-6">
                <div class="card-stats card p-3 text-center">
                    <i class="fas fa-wallet" style="font-size: 28px; color: #667eea;"></i>
                    <h4 class="mt-2 mb-0" id="walletBalance">0</h4>
                    <small class="text-muted">تومان</small>
                </div>
            </div>
            <div class="col-md-3 col-6">
                <div class="card-stats card p-3 text-center">
                    <i class="fas fa-calendar-check" style="font-size: 28px; color: #28a745;"></i>
                    <h4 class="mt-2 mb-0" id="subStatus">غیرفعال</h4>
                    <small class="text-muted">اشتراک</small>
                </div>
            </div>
            <div class="col-md-3 col-6">
                <div class="card-stats card p-3 text-center">
                    <i class="fas fa-robot" style="font-size: 28px; color: #764ba2;"></i>
                    <h4 class="mt-2 mb-0" id="botsCount">0</h4>
                    <small class="text-muted">ربات‌ها</small>
                </div>
            </div>
            <div class="col-md-3 col-6">
                <div class="card-stats card p-3 text-center">
                    <i class="fas fa-chart-line" style="font-size: 28px; color: #ffc107;"></i>
                    <h4 class="mt-2 mb-0" id="remainingBots">0</h4>
                    <small class="text-muted">ظرفیت باقی</small>
                </div>
            </div>
        </div>
        
        <div class="row">
            <div class="col-md-8">
                <div class="card border-0 rounded-4 shadow-sm">
                    <div class="card-body">
                        <h5><i class="fas fa-chart-pie me-2"></i>آخرین ربات‌های ساخته شده</h5>
                        <div id="recentBotsList" class="mt-3"></div>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card border-0 rounded-4 shadow-sm">
                    <div class="card-body">
                        <h5><i class="fas fa-gift me-2"></i>کد معرف شما</h5>
                        <div class="bg-light p-3 rounded-3 text-center mt-2">
                            <code id="referralCode" style="font-size: 1.2rem;"></code>
                            <button class="btn btn-sm btn-outline-primary mt-2" onclick="copyReferralLink()">
                                <i class="fas fa-copy"></i> کپی لینک
                            </button>
                        </div>
                        <hr>
                        <h6>افراد معرفی شده</h6>
                        <h3 id="referralsCount">0</h3>
                        <small class="text-muted">هر معرف 7% کمیسیون</small>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div id="page-build" class="page-content" style="display: none;">
        <div class="card border-0 rounded-4 shadow-sm">
            <div class="card-body p-4">
                <h4><i class="fas fa-microchip me-2"></i>ساخت ربات جدید</h4>
                <hr>
                
                <div class="alert alert-warning" id="buildWarning" style="display: none;"></div>
                
                <ul class="nav nav-tabs mb-4">
                    <li class="nav-item">
                        <a class="nav-link active" data-bs-toggle="tab" href="#uploadTab">آپلود فایل</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" data-bs-toggle="tab" href="#codeTab">کد مستقیم</a>
                    </li>
                </ul>
                
                <div class="tab-content">
                    <div class="tab-pane fade show active" id="uploadTab">
                        <div class="border rounded-3 p-4 text-center" style="border-style: dashed;">
                            <i class="fas fa-cloud-upload-alt" style="font-size: 48px; color: #667eea;"></i>
                            <p class="mt-2">فایل .py یا .zip خود را انتخاب کنید</p>
                            <small class="text-muted">حداکثر حجم: 50 مگابایت</small>
                            <input type="file" id="botFile" class="form-control mt-3" accept=".py,.zip" style="display: none;">
                            <button class="btn btn-primary mt-3" onclick="$('#botFile').click()">
                                <i class="fas fa-folder-open me-2"></i> انتخاب فایل
                            </button>
                        </div>
                    </div>
                    <div class="tab-pane fade" id="codeTab">
                        <textarea id="botCode" class="form-control code-area" rows="12" placeholder="# کد ربات خود را اینجا وارد کنید
import telebot

TOKEN = 'YOUR_BOT_TOKEN_HERE'
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, 'سلام! ربات من با موفقیت ساخته شد!')

@bot.message_handler(func=lambda m: True)
def echo(message):
    bot.reply_to(message, message.text)

print('ربات در حال اجراست...')
bot.infinity_polling()"></textarea>
                        <small class="text-muted mt-2 d-block">
                            <i class="fas fa-info-circle"></i> توکن ربات را در کد قرار دهید (از @BotFather دریافت کنید)
                        </small>
                    </div>
                </div>
                
                <div class="mt-4">
                    <button class="btn btn-primary btn-lg w-100" onclick="buildBot()" id="buildBtn">
                        <i class="fas fa-play me-2"></i> ساخت ربات
                    </button>
                </div>
                
                <div id="buildStatus" class="mt-3" style="display: none;"></div>
            </div>
        </div>
    </div>

    <div id="page-bots" class="page-content" style="display: none;">
        <div class="card border-0 rounded-4 shadow-sm">
            <div class="card-body p-4">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h4><i class="fas fa-list me-2"></i>ربات‌های من</h4>
                    <button class="btn btn-sm btn-outline-primary" onclick="loadBots()">
                        <i class="fas fa-sync-alt"></i> بروزرسانی
                    </button>
                </div>
                <div id="botsList"></div>
            </div>
        </div>
    </div>

    <div id="page-wallet" class="page-content" style="display: none;">
        <div class="card border-0 rounded-4 shadow-sm mb-4">
            <div class="card-body p-4">
                <h4><i class="fas fa-wallet me-2"></i>کیف پول</h4>
                <hr>
                <div class="row">
                    <div class="col-md-6">
                        <div class="bg-light p-4 rounded-3 text-center">
                            <small class="text-muted">موجودی قابل برداشت</small>
                            <h2 class="mb-0" id="walletDetailBalance">0</h2>
                            <small>تومان</small>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="bg-light p-4 rounded-3 text-center">
                            <small class="text-muted">وضعیت اشتراک</small>
                            <h2 class="mb-0" id="walletSubStatus">❌ غیرفعال</h2>
                            <small id="walletExpiryDate"></small>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="card border-0 rounded-4 shadow-sm mb-4">
            <div class="card-body p-4">
                <h5><i class="fas fa-credit-card me-2"></i>خرید اشتراک ماهیانه</h5>
                <hr>
                <div class="alert alert-info">
                    <strong>💰 هزینه اشتراک:</strong> <span id="priceDisplay"></span>
                </div>
                <div class="border rounded-3 p-3 mb-3">
                    <p class="mb-1"><i class="fas fa-credit-card me-2"></i>شماره کارت:</p>
                    <code class="d-block p-2 bg-light rounded" id="cardNumber"></code>
                    <p class="mb-1 mt-2"><i class="fas fa-user me-2"></i>نام دارنده حساب:</p>
                    <code class="d-block p-2 bg-light rounded" id="cardHolder"></code>
                    <p class="mb-1 mt-2"><i class="fas fa-university me-2"></i>بانک:</p>
                    <code class="d-block p-2 bg-light rounded" id="cardBank"></code>
                </div>
                <button class="btn btn-success w-100" onclick="showReceiptUpload()">
                    <i class="fas fa-upload me-2"></i> ارسال فیش واریز
                </button>
            </div>
        </div>
        
        <div class="card border-0 rounded-4 shadow-sm">
            <div class="card-body p-4">
                <h5><i class="fas fa-history me-2"></i>تراکنش‌های اخیر</h5>
                <div id="transactionsList"></div>
            </div>
        </div>
    </div>

    <div id="page-referrals" class="page-content" style="display: none;">
        <div class="card border-0 rounded-4 shadow-sm">
            <div class="card-body p-4 text-center">
                <i class="fas fa-share-alt" style="font-size: 64px; color: #667eea;"></i>
                <h4 class="mt-3">دعوت از دوستان</h4>
                <p>با دعوت دوستان خود، از هر اشتراک 7% کمیسیون دریافت کنید</p>
                <div class="bg-light p-3 rounded-3 d-inline-block mx-auto">
                    <code id="refLink" style="font-size: 1.1rem;"></code>
                </div>
                <div class="mt-3">
                    <button class="btn btn-primary" onclick="copyReferralLink()">
                        <i class="fas fa-copy me-2"></i> کپی لینک دعوت
                    </button>
                </div>
                <hr class="my-4">
                <h5>افراد دعوت شده: <span id="refCount">0</span></h5>
                <h5>کمیسیون کل: <span id="totalCommission">0</span> تومان</h5>
            </div>
        </div>
    </div>

    <div id="page-guide" class="page-content" style="display: none;">
        <div class="card border-0 rounded-4 shadow-sm">
            <div class="card-body p-4">
                <h4><i class="fas fa-book me-2"></i>راهنمای استفاده</h4>
                <hr>
                <div id="guideText"></div>
            </div>
        </div>
    </div>

    <div id="page-settings" class="page-content" style="display: none;">
        <div class="card border-0 rounded-4 shadow-sm">
            <div class="card-body p-4">
                <h4><i class="fas fa-user-cog me-2"></i>تنظیمات حساب</h4>
                <hr>
                <form id="profileForm">
                    <div class="mb-3">
                        <label>نام کامل</label>
                        <input type="text" name="full_name" id="profileFullName" class="form-control">
                    </div>
                    <div class="mb-3">
                        <label>ایمیل</label>
                        <input type="email" name="email" id="profileEmail" class="form-control">
                    </div>
                    <div class="mb-3">
                        <label>شماره موبایل</label>
                        <input type="tel" name="phone" id="profilePhone" class="form-control">
                    </div>
                    <div class="mb-3">
                        <label>رمز عبور جدید (در صورت تغییر)</label>
                        <input type="password" name="password" class="form-control" placeholder="رمزی که نمی‌خواهید تغییر دهید را خالی بگذارید">
                    </div>
                    <button type="submit" class="btn btn-primary">ذخیره تغییرات</button>
                </form>
            </div>
        </div>
    </div>
    
    <!-- پنل ادمین (فقط برای ادمین‌ها) -->
    <div id="page-admin" class="page-content" style="display: none;">
        <div class="card border-0 rounded-4 shadow-sm mb-4">
            <div class="card-body p-4">
                <h4><i class="fas fa-chart-line me-2"></i>آمار سیستم</h4>
                <div id="adminStats" class="row g-3"></div>
            </div>
        </div>
        <div class="card border-0 rounded-4 shadow-sm mb-4">
            <div class="card-body p-4">
                <h4><i class="fas fa-users me-2"></i>مدیریت کاربران</h4>
                <div id="usersList"></div>
            </div>
        </div>
        <div class="card border-0 rounded-4 shadow-sm mb-4">
            <div class="card-body p-4">
                <h4><i class="fas fa-money-bill me-2"></i>درخواست‌های برداشت</h4>
                <div id="withdrawRequests"></div>
            </div>
        </div>
        <div class="card border-0 rounded-4 shadow-sm mb-4">
            <div class="card-body p-4">
                <h4><i class="fas fa-image me-2"></i>فیش‌های پرداخت</h4>
                <div id="receiptRequests"></div>
            </div>
        </div>
        <div class="card border-0 rounded-4 shadow-sm">
            <div class="card-body p-4">
                <h4><i class="fas fa-envelope me-2"></i>ارسال پیام همگانی</h4>
                <textarea id="broadcastMsg" class="form-control mb-2" rows="3" placeholder="متن پیام..."></textarea>
                <button class="btn btn-primary" onclick="sendBroadcast()">ارسال به همه کاربران</button>
            </div>
        </div>
    </div>
</div>

<div id="toast" class="toast-notify"></div>

<!-- مودال آپلود فیش -->
<div class="modal fade" id="receiptModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">ارسال فیش واریز</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <p>لطفاً تصویر تراکنش خود را ارسال کنید</p>
                <input type="file" id="receiptFile" class="form-control" accept="image/*">
                <div id="receiptProgress" class="mt-2" style="display: none;">
                    <div class="progress"><div class="progress-bar" style="width: 0%"></div></div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" data-bs-dismiss="modal">انصراف</button>
                <button class="btn btn-primary" onclick="uploadReceipt()">ارسال</button>
            </div>
        </div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
<script>
    let currentUser = null;
    let isAdmin = false;
    
    function showToast(msg, isError = false) {
        $('#toast').text(msg).css('background-color', isError ? '#dc3545' : '#28a745').fadeIn();
        setTimeout(() => $('#toast').fadeOut(), 3000);
    }
    
    function toggleSidebar() {
        $('#sidebar').toggleClass('open');
    }
    
    function showPage(page) {
        $('.page-content').hide();
        $(`#page-${page}`).show();
        $('.sidebar .nav-link').removeClass('active');
        $(`.sidebar .nav-link[onclick="showPage('${page}')"]`).addClass('active');
        
        if (page === 'bots') loadBots();
        if (page === 'wallet') loadWallet();
        if (page === 'referrals') loadReferrals();
        if (page === 'guide') loadGuide();
        if (page === 'admin' && isAdmin) loadAdminPanel();
        if (page === 'dashboard') loadDashboard();
        
        if (window.innerWidth < 768) toggleSidebar();
    }
    
    async function loadUserData() {
        try {
            const res = await fetch('/api/user');
            if (res.ok) {
                currentUser = await res.json();
                isAdmin = currentUser.is_admin;
                
                $('#userName').text(currentUser.full_name || currentUser.username);
                $('#userSubStatus').html(currentUser.subscription_active ? '✅ اشتراک فعال' : '❌ اشتراک غیرفعال');
                $('#walletBalance').text(currentUser.wallet_balance.toLocaleString());
                $('#botsCount').text(currentUser.bots_count);
                $('#remainingBots').text(currentUser.remaining_bots);
                $('#subStatus').html(currentUser.subscription_active ? '<span class="text-success">فعال</span>' : '<span class="text-danger">غیرفعال</span>');
                
                if (isAdmin) {
                    const adminNav = '<a class="nav-link" href="#" onclick="showPage(\'admin\')"><i class="fas fa-shield-alt"></i> پنل مدیریت</a>';
                    $('.sidebar nav').find('hr:last').before(adminNav);
                }
            }
        } catch(e) { console.error(e); }
    }
    
    async function loadDashboard() {
        await loadUserData();
        try {
            const res = await fetch('/api/bots');
            if (res.ok) {
                const bots = await res.json();
                const recent = bots.slice(0, 5);
                let html = '';
                for (const bot of recent) {
                    html += `
                        <div class="d-flex justify-content-between align-items-center border-bottom py-2">
                            <div>
                                <i class="fab fa-telegram me-2"></i>
                                <strong>${bot.name || 'ربات'}</strong>
                                <br><small class="text-muted">@${bot.username || 'نامشخص'}</small>
                            </div>
                            <span class="status-badge ${bot.status === 'running' ? 'status-running' : 'status-stopped'}">
                                ${bot.status === 'running' ? '🟢 فعال' : '🔴 متوقف'}
                            </span>
                        </div>
                    `;
                }
                $('#recentBotsList').html(html || '<p class="text-muted">هنوز رباتی ساخته نشده</p>');
            }
            
            const refRes = await fetch('/api/referrals');
            if (refRes.ok) {
                const refData = await refRes.json();
                $('#referralCode').text(refData.referral_code);
                $('#referralsCount').text(refData.count);
            }
        } catch(e) { console.error(e); }
    }
    
    async function loadBots() {
        try {
            const res = await fetch('/api/bots');
            if (res.ok) {
                const bots = await res.json();
                if (bots.length === 0) {
                    $('#botsList').html('<div class="text-center py-5"><i class="fas fa-robot fa-3x text-muted"></i><p class="mt-2">رباتی ساخته نشده است</p><button class="btn btn-primary btn-sm" onclick="showPage(\'build\')">ساخت ربات جدید</button></div>');
                    return;
                }
                
                let html = '';
                for (const bot of bots) {
                    html += `
                        <div class="bot-card">
                            <div class="d-flex justify-content-between align-items-start">
                                <div>
                                    <h6><i class="fab fa-telegram me-1"></i> ${bot.name || bot.username || 'ربات'}</h6>
                                    <small class="text-muted">@${bot.username || 'نامشخص'}</small>
                                    <div class="mt-1">
                                        <span class="status-badge ${bot.status === 'running' ? 'status-running' : 'status-stopped'}">
                                            ${bot.status === 'running' ? '🟢 فعال' : '🔴 متوقف'}
                                        </span>
                                    </div>
                                    ${bot.error_message ? `<small class="text-danger d-block mt-1"><i class="fas fa-exclamation-triangle"></i> ${bot.error_message.substring(0, 50)}</small>` : ''}
                                </div>
                                <div>
                                    <button class="btn btn-sm btn-outline-${bot.status === 'running' ? 'warning' : 'success'} me-1" onclick="toggleBot('${bot.id}')">
                                        <i class="fas fa-${bot.status === 'running' ? 'stop' : 'play'}"></i>
                                    </button>
                                    <button class="btn btn-sm btn-outline-danger" onclick="deleteBot('${bot.id}')">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            </div>
                        </div>
                    `;
                }
                $('#botsList').html(html);
            }
        } catch(e) { showToast('خطا در بارگذاری', true); }
    }
    
    async function toggleBot(botId) {
        try {
            const res = await fetch(`/api/bots/${botId}/toggle`, { method: 'POST' });
            const data = await res.json();
            if (res.ok) showToast(data.message);
            else showToast(data.error, true);
            loadBots();
            loadDashboard();
        } catch(e) { showToast('خطا', true); }
    }
    
    async function deleteBot(botId) {
        if (!confirm('آیا از حذف این ربات اطمینان دارید؟')) return;
        try {
            const res = await fetch(`/api/bots/${botId}`, { method: 'DELETE' });
            if (res.ok) {
                showToast('ربات حذف شد');
                loadBots();
                loadDashboard();
                loadUserData();
            }
        } catch(e) { showToast('خطا', true); }
    }
    
    async function buildBot() {
        const buildBtn = $('#buildBtn');
        const fileInput = document.getElementById('botFile');
        const code = $('#botCode').val();
        
        if (!code.trim() && (!fileInput.files || fileInput.files.length === 0)) {
            showToast('لطفاً کد را وارد کنید یا فایل را آپلود کنید', true);
            return;
        }
        
        buildBtn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm me-2"></span> در حال ساخت...');
        
        try {
            let response;
            if (fileInput.files.length > 0) {
                const formData = new FormData();
                formData.append('file', fileInput.files[0]);
                response = await fetch('/api/build/upload', { method: 'POST', body: formData });
            } else {
                response = await fetch('/api/build/code', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ code: code })
                });
            }
            
            const data = await response.json();
            if (response.ok) {
                showToast('ربات با موفقیت ساخته شد!');
                $('#buildStatus').html(`<div class="alert alert-success">✅ ربات ${data.bot_name} ساخته شد!<br>🔗 t.me/${data.username}</div>`);
                $('#botCode').val('');
                $('#botFile').val('');
                loadBots();
                loadDashboard();
                loadUserData();
                showPage('bots');
            } else {
                $('#buildStatus').html(`<div class="alert alert-danger">❌ خطا: ${data.error}</div>`);
                showToast(data.error, true);
            }
        } catch(e) {
            $('#buildStatus').html(`<div class="alert alert-danger">❌ خطا: ${e.message}</div>`);
            showToast('خطا در ارتباط با سرور', true);
        } finally {
            buildBtn.prop('disabled', false).html('<i class="fas fa-play me-2"></i> ساخت ربات');
            setTimeout(() => $('#buildStatus').fadeOut(3000), 5000);
        }
    }
    
    async function loadWallet() {
        try {
            const res = await fetch('/api/wallet');
            const data = await res.json();
            $('#walletDetailBalance').text(data.balance.toLocaleString());
            $('#walletSubStatus').html(data.subscription_active ? '✅ فعال' : '❌ غیرفعال');
            $('#walletExpiryDate').text(data.expiry_date ? `اعتبار تا: ${data.expiry_date}` : '');
            $('#priceDisplay').text(data.price_str);
            $('#cardNumber').text(data.card_number);
            $('#cardHolder').text(data.card_holder);
            $('#cardBank').text(data.card_bank);
            
            const txRes = await fetch('/api/transactions');
            if (txRes.ok) {
                const txs = await txRes.json();
                let html = '<div class="list-group">';
                for (const tx of txs) {
                    html += `<div class="list-group-item">💰 ${tx.amount.toLocaleString()} تومان - ${tx.status} - ${tx.created_at.substring(0, 10)}</div>`;
                }
                html += '</div>';
                $('#transactionsList').html(html || '<p class="text-muted">تراکنشی وجود ندارد</p>');
            }
        } catch(e) { console.error(e); }
    }
    
    async function loadReferrals() {
        try {
            const res = await fetch('/api/referrals');
            const data = await res.json();
            $('#refLink').text(data.referral_link);
            $('#refCount').text(data.count);
            $('#totalCommission').text(data.total_commission.toLocaleString());
        } catch(e) { console.error(e); }
    }
    
    async function loadGuide() {
        try {
            const res = await fetch('/api/guide');
            const data = await res.json();
            $('#guideText').html(data.guide_text.replace(/\\n/g, '<br>'));
        } catch(e) { console.error(e); }
    }
    
    function copyReferralLink() {
        const link = $('#refLink').text();
        navigator.clipboard.writeText(link);
        showToast('لینک کپی شد');
    }
    
    let receiptModal;
    function showReceiptUpload() {
        receiptModal = new bootstrap.Modal(document.getElementById('receiptModal'));
        receiptModal.show();
    }
    
    async function uploadReceipt() {
        const fileInput = document.getElementById('receiptFile');
        if (!fileInput.files.length) {
            showToast('لطفاً تصویر را انتخاب کنید', true);
            return;
        }
        
        const formData = new FormData();
        formData.append('receipt', fileInput.files[0]);
        
        try {
            const res = await fetch('/api/upload-receipt', { method: 'POST', body: formData });
            const data = await res.json();
            if (res.ok) {
                showToast('فیش با موفقیت ارسال شد، در انتظار تایید');
                receiptModal.hide();
            } else {
                showToast(data.error, true);
            }
        } catch(e) {
            showToast('خطا', true);
        }
    }
    
    async function loadAdminPanel() {
        if (!isAdmin) return;
        try {
            const statsRes = await fetch('/api/admin/stats');
            if (statsRes.ok) {
                const stats = await statsRes.json();
                $('#adminStats').html(`
                    <div class="col-md-3"><div class="card p-3 text-center"><h4>${stats.users_count}</h4><small>کاربران</small></div></div>
                    <div class="col-md-3"><div class="card p-3 text-center"><h4>${stats.active_subs}</h4><small>اشتراک فعال</small></div></div>
                    <div class="col-md-3"><div class="card p-3 text-center"><h4>${stats.total_bots}</h4><small>ربات‌ها</small></div></div>
                    <div class="col-md-3"><div class="card p-3 text-center"><h4>${stats.running_bots}</h4><small>ربات فعال</small></div></div>
                `);
            }
            
            const usersRes = await fetch('/api/admin/users');
            if (usersRes.ok) {
                const users = await usersRes.json();
                let html = '<table class="table table-sm"><thead><tr><th>کاربر</th><th>موجودی</th><th>اشتراک</th><th>عملیات</th></tr></thead><tbody>';
                for (const u of users) {
                    html += `<tr>
                        <td>${u.full_name || u.username}</td>
                        <td>${u.wallet_balance.toLocaleString()}</td>
                        <td>${u.subscription_active ? '✅' : '❌'}</td>
                        <td><button class="btn btn-sm btn-danger" onclick="banUser(${u.id})">مسدود</button></td>
                    </tr>`;
                }
                html += '</tbody></table>';
                $('#usersList').html(html);
            }
            
            const withdrawRes = await fetch('/api/admin/withdraws');
            if (withdrawRes.ok) {
                const withdraws = await withdrawRes.json();
                let html = '';
                for (const w of withdraws) {
                    html += `<div class="border p-2 mb-2 rounded">
                        <strong>کاربر ${w.user_id}</strong> - ${w.amount.toLocaleString()} تومان<br>
                        آدرس: ${w.address}<br>
                        <button class="btn btn-sm btn-success" onclick="approveWithdraw(${w.id})">تایید واریز شد</button>
                    </div>`;
                }
                $('#withdrawRequests').html(html || '<p class="text-muted">درخواستی وجود ندارد</p>');
            }
            
            const receiptsRes = await fetch('/api/admin/receipts');
            if (receiptsRes.ok) {
                const receipts = await receiptsRes.json();
                let html = '';
                for (const r of receipts) {
                    html += `<div class="border p-2 mb-2 rounded">
                        کاربر ${r.user_id} - ${r.amount.toLocaleString()} تومان<br>
                        <button class="btn btn-sm btn-success" onclick="approveReceipt(${r.id})">تایید</button>
                        <button class="btn btn-sm btn-danger" onclick="rejectReceipt(${r.id})">رد</button>
                    </div>`;
                }
                $('#receiptRequests').html(html || '<p class="text-muted">فیشی وجود ندارد</p>');
            }
        } catch(e) { console.error(e); }
    }
    
    async function sendBroadcast() {
        const msg = $('#broadcastMsg').val();
        if (!msg) return;
        const res = await fetch('/api/admin/broadcast', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: msg })
        });
        const data = await res.json();
        showToast(`پیام به ${data.sent} نفر ارسال شد`);
        $('#broadcastMsg').val('');
    }
    
    function approveWithdraw(id) {
        fetch(`/api/admin/withdraw/${id}/approve`, { method: 'POST' }).then(() => loadAdminPanel());
    }
    
    function approveReceipt(id) {
        fetch(`/api/admin/receipt/${id}/approve`, { method: 'POST' }).then(() => loadAdminPanel());
    }
    
    function rejectReceipt(id) {
        fetch(`/api/admin/receipt/${id}/reject`, { method: 'POST' }).then(() => loadAdminPanel());
    }
    
    function banUser(id) {
        if (confirm('مسدود شود؟')) fetch(`/api/admin/users/${id}/ban`, { method: 'POST' }).then(() => loadAdminPanel());
    }
    
    $('#profileForm').on('submit', async function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        const data = Object.fromEntries(formData);
        const res = await fetch('/api/update-profile', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
        if (res.ok) showToast('پروفایل بروزرسانی شد');
        else showToast('خطا', true);
    });
    
    setInterval(() => {
        const now = new Date();
        $('#currentTime').text(now.toLocaleTimeString('fa-IR'));
    }, 1000);
    
    loadUserData();
    loadDashboard();
</script>
</body>
</html>
'''

# ==================== مسیرهای API ====================

@app.route('/')
def index():
    if 'user_id' in session:
        return HTML_INDEX
    return redirect(url_for('login_page'))

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = authenticate(username, password)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            db.execute('UPDATE users SET last_login = ? WHERE id = ?', (datetime.now().isoformat(), user['id']))
            return redirect(url_for('index'))
        return render_template_string(HTML_LOGIN.replace('نام کاربری یا رمز عبور اشتباه است', 'خطا: نام کاربری یا رمز عبور اشتباه است'))
    return HTML_LOGIN

@app.route('/register', methods=['GET', 'POST'])
def register_page():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        referral_code = request.form.get('referral_code')
        
        existing = db.execute('SELECT id FROM users WHERE username = ?', (username,))
        if existing:
            return render_template_string(HTML_REGISTER.replace('ثبت نام', 'نام کاربری تکراری است'))
        
        referred_by = None
        if referral_code:
            ref_user = db.execute('SELECT id FROM users WHERE referral_code = ?', (referral_code,))
            if ref_user:
                referred_by = ref_user[0]['id']
        
        create_user(username, password, full_name, email, phone, referred_by)
        return redirect(url_for('login_page'))
    return HTML_REGISTER

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

# API Routes
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
        'email': user['email'],
        'phone': user['phone'],
        'wallet_balance': user['wallet_balance'],
        'bots_count': user['bots_count'],
        'subscription_active': check_subscription(user['id']),
        'remaining_bots': get_remaining_bots(user['id']),
        'is_admin': user.get('is_admin', 0),
        'referral_code': user.get('referral_code', '')
    })

@app.route('/api/bots')
def api_bots():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    bots = get_user_bots(session['user_id'])
    result = []
    for bot in bots:
        status = machine_manager.get_status(bot['id'])
        result.append({
            'id': bot['id'],
            'name': bot.get('name', ''),
            'username': bot.get('username', ''),
            'status': 'running' if status.get('running') else 'stopped',
            'created_at': bot.get('created_at', ''),
            'error_message': bot.get('error_message', '')
        })
    return jsonify(result)

@app.route('/api/bots/<bot_id>/toggle', methods=['POST'])
def api_toggle_bot(bot_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    bot_rec = get_bot(bot_id)
    if not bot_rec or bot_rec['user_id'] != session['user_id']:
        return jsonify({'error': 'Not found'}), 404
    
    status = machine_manager.get_status(bot_id)
    if status.get('running'):
        if machine_manager.stop_bot(bot_id):
            return jsonify({'message': 'ربات متوقف شد'})
        return jsonify({'error': 'خطا'}), 500
    else:
        if os.path.exists(bot_rec['file_path']):
            with open(bot_rec['file_path'], 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
            result = machine_manager.run_bot(bot_id, code, bot_rec['token'])
            if result['success']:
                db.execute("UPDATE bots SET status = 'running', pid = ?, error_message = NULL WHERE id = ?",
                          (result['pid'], bot_id))
                return jsonify({'message': 'ربات راه‌اندازی شد'})
        return jsonify({'error': 'خطا در اجرا'}), 500

@app.route('/api/bots/<bot_id>', methods=['DELETE'])
def api_delete_bot(bot_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    if delete_bot(bot_id, session['user_id']):
        return jsonify({'message': 'حذف شد'})
    return jsonify({'error': 'خطا'}), 500

@app.route('/api/build/code', methods=['POST'])
def api_build_code():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = session['user_id']
    data = request.get_json()
    code = data.get('code', '')
    
    return process_build(user_id, code, None, None)

@app.route('/api/build/upload', methods=['POST'])
def api_build_upload():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = session['user_id']
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    file_content = file.read()
    filename = file.filename
    
    return process_build(user_id, None, file_content, filename)

def process_build(user_id, code_text, file_content, filename):
    can_create, reason = can_create_bot(user_id)
    if not can_create:
        if reason == "no_subscription":
            return jsonify({'error': 'ابتدا اشتراک خود را فعال کنید'}), 403
        return jsonify({'error': 'به حداکثر تعداد ربات مجاز رسیده‌اید'}), 403
    
    try:
        if code_text:
            token = extract_token_from_code(code_text)
            main_code = code_text
        else:
            temp_path = os.path.join(DIRS['TEMP'], f"build_{user_id}_{int(time.time())}_{filename}")
            with open(temp_path, 'wb') as f:
                f.write(file_content)
            
            if filename.endswith('.zip'):
                extract_dir = os.path.join(DIRS['TEMP'], f"extract_{user_id}_{int(time.time())}")
                os.makedirs(extract_dir, exist_ok=True)
                with zipfile.ZipFile(temp_path, 'r') as zf:
                    zf.extractall(extract_dir)
                main_code = ""
                for root, dirs, files in os.walk(extract_dir):
                    for f in files:
                        if f.endswith('.py'):
                            with open(os.path.join(root, f), 'r', encoding='utf-8', errors='ignore') as code_f:
                                main_code = code_f.read()
                                break
                    if main_code:
                        break
                shutil.rmtree(extract_dir, ignore_errors=True)
            else:
                with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                    main_code = f.read()
            os.remove(temp_path)
            token = extract_token_from_code(main_code)
        
        if not token:
            return jsonify({'error': 'توکن ربات در کد پیدا نشد'}), 400
        
        try:
            resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
            if resp.status_code != 200:
                return jsonify({'error': 'توکن نامعتبر است'}), 400
            bot_info = resp.json()['result']
        except:
            return jsonify({'error': 'خطا در ارتباط با تلگرام'}), 500
        
        bot_id = hashlib.md5(f"{user_id}{token}{time.time()}".encode()).hexdigest()[:16]
        
        user_dir = os.path.join(DIRS['FILES'], str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        file_path = os.path.join(user_dir, f"{bot_id}.py")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(main_code)
        
        result = machine_manager.run_bot(bot_id, main_code, token)
        
        if result['success']:
            add_bot(user_id, bot_id, token,
                   bot_info.get('first_name', 'ربات'),
                   bot_info.get('username', ''),
                   file_path, result['pid'])
            return jsonify({'success': True, 'bot_name': bot_info.get('first_name', 'ربات'), 'username': bot_info.get('username', '')})
        else:
            return jsonify({'error': result.get('error', 'خطا در اجرا')}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)[:200]}), 500

@app.route('/api/wallet')
def api_wallet():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
    return jsonify({
        'balance': user.get('wallet_balance', 0),
        'subscription_active': check_subscription(user['id']),
        'expiry_date': user.get('subscription_expiry', '')[:10] if user.get('subscription_expiry') else '',
        'price_str': get_setting('subscription_price_str'),
        'card_number': get_setting('card_number_display'),
        'card_holder': get_setting('card_holder'),
        'card_bank': get_setting('card_bank')
    })

@app.route('/api/transactions')
def api_transactions():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    receipts = db.execute('SELECT * FROM receipts WHERE user_id = ? ORDER BY created_at DESC LIMIT 20', (session['user_id'],))
    result = []
    for r in receipts:
        result.append({
            'amount': r['amount'],
            'status': r['status'],
            'created_at': r['created_at']
        })
    return jsonify(result)

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

@app.route('/api/upload-receipt', methods=['POST'])
def api_upload_receipt():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if 'receipt' not in request.files:
        return jsonify({'error': 'No file'}), 400
    
    file = request.files['receipt']
    if file.filename == '':
        return jsonify({'error': 'No file'}), 400
    
    user_id = session['user_id']
    tx_hash = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:16].upper()
    receipt_path = os.path.join(DIRS['RECEIPTS'], f"{user_id}_{tx_hash}.jpg")
    file.save(receipt_path)
    
    db.execute('''
        INSERT INTO receipts (user_id, amount, receipt_path, tx_hash, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, get_setting('subscription_price'), receipt_path, tx_hash, datetime.now().isoformat()))
    
    return jsonify({'message': 'Receipt uploaded'})

@app.route('/api/update-profile', methods=['POST'])
def api_update_profile():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    user_id = session['user_id']
    
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
        updates.append('password = ?')
        params.append(hashlib.md5(data['password'].encode()).hexdigest())
    
    if updates:
        params.append(user_id)
        db.execute(f'UPDATE users SET {", ".join(updates)} WHERE id = ?', params)
    
    return jsonify({'message': 'Updated'})

# ==================== APIهای ادمین ====================
@app.route('/api/admin/stats')
def api_admin_stats():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
    if not user or not user.get('is_admin'):
        return jsonify({'error': 'Forbidden'}), 403
    
    users_count = db.execute('SELECT COUNT(*) as count FROM users')[0]['count']
    active_subs = db.execute('SELECT COUNT(*) as count FROM users WHERE subscription_status = "active"')[0]['count']
    total_bots = db.execute('SELECT COUNT(*) as count FROM bots')[0]['count']
    running_bots = db.execute('SELECT COUNT(*) as count FROM bots WHERE status = "running"')[0]['count']
    total_wallet = db.execute('SELECT SUM(wallet_balance) as total FROM users')[0]['total'] or 0
    
    return jsonify({
        'users_count': users_count,
        'active_subs': active_subs,
        'total_bots': total_bots,
        'running_bots': running_bots,
        'total_wallet': total_wallet
    })

@app.route('/api/admin/users')
def api_admin_users():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
    if not user or not user.get('is_admin'):
        return jsonify({'error': 'Forbidden'}), 403
    
    users = db.execute('SELECT id, username, full_name, wallet_balance, subscription_status, subscription_expiry FROM users ORDER BY id')
    result = []
    for u in users:
        result.append({
            'id': u['id'],
            'username': u['username'],
            'full_name': u['full_name'],
            'wallet_balance': u['wallet_balance'],
            'subscription_active': u['subscription_status'] == 'active'
        })
    return jsonify(result)

@app.route('/api/admin/withdraws')
def api_admin_withdraws():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
    if not user or not user.get('is_admin'):
        return jsonify({'error': 'Forbidden'}), 403
    
    withdraws = db.execute('SELECT * FROM withdraw_requests WHERE status = "pending" ORDER BY created_at')
    result = []
    for w in withdraws:
        result.append({
            'id': w['id'],
            'user_id': w['user_id'],
            'amount': w['amount'],
            'address': w['address']
        })
    return jsonify(result)

@app.route('/api/admin/receipts')
def api_admin_receipts():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
    if not user or not user.get('is_admin'):
        return jsonify({'error': 'Forbidden'}), 403
    
    receipts = db.execute('SELECT * FROM receipts WHERE status = "pending" ORDER BY created_at')
    result = []
    for r in receipts:
        result.append({
            'id': r['id'],
            'user_id': r['user_id'],
            'amount': r['amount']
        })
    return jsonify(result)

@app.route('/api/admin/withdraw/<int:wid>/approve', methods=['POST'])
def api_approve_withdraw(wid):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
    if not user or not user.get('is_admin'):
        return jsonify({'error': 'Forbidden'}), 403
    
    db.execute('UPDATE withdraw_requests SET status = "approved", processed_at = ? WHERE id = ?', (datetime.now().isoformat(), wid))
    return jsonify({'message': 'Approved'})

@app.route('/api/admin/receipt/<int:rid>/approve', methods=['POST'])
def api_approve_receipt(rid):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
    if not user or not user.get('is_admin'):
        return jsonify({'error': 'Forbidden'}), 403
    
    r = db.execute('SELECT user_id FROM receipts WHERE id = ?', (rid,))
    if r:
        db.execute('UPDATE receipts SET status = "approved", reviewed_by = ?, reviewed_at = ? WHERE id = ?',
                  (session['user_id'], datetime.now().isoformat(), rid))
        activate_subscription(r[0]['user_id'])
    return jsonify({'message': 'Approved'})

@app.route('/api/admin/receipt/<int:rid>/reject', methods=['POST'])
def api_reject_receipt(rid):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
    if not user or not user.get('is_admin'):
        return jsonify({'error': 'Forbidden'}), 403
    
    db.execute('UPDATE receipts SET status = "rejected", reviewed_by = ?, reviewed_at = ? WHERE id = ?',
              (session['user_id'], datetime.now().isoformat(), rid))
    return jsonify({'message': 'Rejected'})

@app.route('/api/admin/users/<int:uid>/ban', methods=['POST'])
def api_ban_user(uid):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
    if not user or not user.get('is_admin'):
        return jsonify({'error': 'Forbidden'}), 403
    
    db.execute('UPDATE users SET is_banned = 1 WHERE id = ?', (uid,))
    return jsonify({'message': 'Banned'})

@app.route('/api/admin/broadcast', methods=['POST'])
def api_broadcast():
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
        # در اینجا می‌توانید ایمیل یا نوتیفیکیشن ارسال کنید
        # برای نمونه فقط لاگ می‌شود
        sent += 1
    
    return jsonify({'sent': sent})

# ==================== مانیتورینگ ====================
def system_monitor():
    while True:
        try:
            # بررسی انقضای اشتراک
            for user in db.execute('SELECT id, subscription_expiry FROM users WHERE subscription_status = "active"'):
                if user['subscription_expiry']:
                    expiry = datetime.fromisoformat(user['subscription_expiry'])
                    if expiry < datetime.now():
                        db.execute('UPDATE users SET subscription_status = "inactive" WHERE id = ?', (user['id'],))
                        logger.info(f"Subscription expired for user {user['id']}")
            
            time.sleep(60)
        except Exception as e:
            logger.error(f"Monitor error: {e}")
            time.sleep(60)

def can_create_bot(user_id):
    if not check_subscription(user_id):
        return False, "no_subscription"
    remaining = get_remaining_bots(user_id)
    if remaining <= 0:
        return False, "limit_reached"
    return True, "ok"

# ==================== اجرا ====================
if __name__ == "__main__":
    threading.Thread(target=system_monitor, daemon=True).start()
    
    print("=" * 70)
    print("🌐 سامانه کامل ساخت ربات تلگرام".center(70))
    print("=" * 70)
    print(f"📍 آدرس سایت: http://localhost:8080")
    print(f"👤 ادمین: {ADMIN_USERNAME} / {ADMIN_PASSWORD}")
    print(f"📁 دایرکتوری: {BASE_DIR}")
    print("=" * 70)
    print("✅ ویژگی‌ها:")
    print("   - ساخت ربات با آپلود فایل یا کد مستقیم")
    print("   - پنل کاربری کامل")
    print("   - پنل مدیریت (مدیریت کاربران، فیش‌ها، برداشت‌ها)")
    print("   - سیستم اشتراک و کیف پول")
    print("   - سیستم معرف دوستان")
    print("   - مدیریت ربات‌ها (شروع/توقف/حذف)")
    print("=" * 70)
    print("🚀 در حال اجرا...")
    
    app.run(host='0.0.0.0', port=8080, debug=True, use_reloader=False)