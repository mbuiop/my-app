#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import json
import secrets
import hashlib
import sqlite3
import threading
import subprocess
import zipfile
import shutil
import re
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, request, jsonify, session, redirect, url_for, render_template_string
from flask_cors import CORS
import requests

# ==================== تنظیمات ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DIRS = {
    'DB': os.path.join(BASE_DIR, 'database'),
    'FILES': os.path.join(BASE_DIR, 'user_files'),
    'LOGS': os.path.join(BASE_DIR, 'logs'),
    'RECEIPTS': os.path.join(BASE_DIR, 'receipts'),
    'TEMP': os.path.join(BASE_DIR, 'temp'),
    'SANDBOX': os.path.join(BASE_DIR, 'sandbox'),
}

for d in DIRS.values():
    os.makedirs(d, exist_ok=True)

# ==================== دیتابیس ====================
db_path = os.path.join(DIRS['DB'], 'app.db')
conn = sqlite3.connect(db_path, check_same_thread=False)
conn.row_factory = sqlite3.Row

def init_db():
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            full_name TEXT,
            is_admin INTEGER DEFAULT 0,
            wallet_balance INTEGER DEFAULT 0,
            total_commission INTEGER DEFAULT 0,
            subscription_status TEXT DEFAULT 'inactive',
            subscription_expiry TEXT,
            bots_count INTEGER DEFAULT 0,
            max_bots INTEGER DEFAULT 3,
            referral_code TEXT,
            referred_by INTEGER,
            referrals_count INTEGER DEFAULT 0,
            created_at TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS bots (
            id TEXT PRIMARY KEY,
            user_id INTEGER,
            token TEXT,
            name TEXT,
            username TEXT,
            file_path TEXT,
            pid INTEGER,
            status TEXT DEFAULT 'stopped',
            created_at TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            receipt_path TEXT,
            tx_hash TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS withdraw_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            address TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    conn.commit()
    
    # تنظیمات پیش‌فرض
    settings = {
        'card_number': '5892101187322777',
        'card_holder': 'مرتضی نیکخو خنجری',
        'card_bank': 'بانک ملی',
        'subscription_price': '2000000',
        'subscription_price_str': '۲,۰۰۰,۰۰۰ تومان',
        'withdraw_percent': '7',
        'min_withdraw': '2000000',
        'guide_text': '📚 راهنمای ساخت ربات\n1. فایل .py یا .zip خود را ارسال کنید\n2. پس از پرداخت اشتراک، ربات بسازید\n3. هر کاربر ۳ ربات میتواند بسازد',
        'admin_password': '123456',
        'max_bots': '3',
    }
    for k, v in settings.items():
        conn.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (k, v))
    conn.commit()
    
    # ادمین پیش‌فرض
    admin = conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone()
    if not admin:
        conn.execute('''
            INSERT INTO users (username, password, full_name, is_admin, referral_code, created_at, max_bots)
            VALUES (?, ?, ?, 1, ?, ?, 100)
        ''', ('admin', hashlib.md5('admin123'.encode()).hexdigest(), 'مدیر سیستم', 
              secrets.token_hex(8), datetime.now().isoformat()))
        conn.commit()

init_db()

def get_setting(key):
    r = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return r['value'] if r else None

def get_user(user_id):
    r = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(r) if r else None

def get_user_by_username(username):
    r = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    return dict(r) if r else None

def check_subscription(user_id):
    user = get_user(user_id)
    if not user:
        return False
    if user['subscription_status'] == 'active':
        if user['subscription_expiry']:
            expiry = datetime.fromisoformat(user['subscription_expiry'])
            if expiry > datetime.now():
                return True
            else:
                conn.execute("UPDATE users SET subscription_status = 'inactive' WHERE id = ?", (user_id,))
                conn.commit()
    return False

def get_remaining_bots(user_id):
    user = get_user(user_id)
    if not user:
        return 0
    max_bots = int(get_setting('max_bots') or 3)
    if check_subscription(user_id):
        return max_bots - user.get('bots_count', 0)
    return 0

def activate_subscription(user_id):
    user = get_user(user_id)
    now = datetime.now()
    new_expiry = now + timedelta(days=30)
    conn.execute("UPDATE users SET subscription_status = 'active', subscription_expiry = ? WHERE id = ?",
                (new_expiry.isoformat(), user_id))
    conn.commit()
    
    if user and user.get('referred_by'):
        commission_percent = int(get_setting('withdraw_percent') or 7)
        price = int(get_setting('subscription_price') or 2000000)
        commission = int(price * commission_percent / 100)
        conn.execute("UPDATE users SET wallet_balance = wallet_balance + ?, total_commission = total_commission + ? WHERE id = ?",
                    (commission, commission, user['referred_by']))
        conn.commit()
    return True

def extract_token(code):
    patterns = [
        r'token\s*=\s*["\']([^"\']+)["\']',
        r'TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'BOT_TOKEN\s*=\s*["\']([^"\']+)["\']',
    ]
    for p in patterns:
        m = re.search(p, code, re.IGNORECASE)
        if m:
            token = m.group(1)
            if re.match(r'^\d+:[\w\-]+$', token):
                return token
    return None

def run_bot(bot_id, code, token):
    try:
        bot_dir = os.path.join(DIRS['SANDBOX'], bot_id)
        os.makedirs(bot_dir, exist_ok=True)
        code_path = os.path.join(bot_dir, 'bot.py')
        with open(code_path, 'w', encoding='utf-8') as f:
            f.write(code)
        log_file = os.path.join(DIRS['LOGS'], f'bot_{bot_id}.log')
        process = subprocess.Popen([sys.executable, code_path], stdout=open(log_file, 'a'), stderr=subprocess.STDOUT, cwd=bot_dir, start_new_session=True)
        time.sleep(2)
        if process.poll() is None:
            return {'success': True, 'pid': process.pid}
        return {'success': False, 'error': 'ربات اجرا نشد'}
    except Exception as e:
        return {'success': False, 'error': str(e)[:100]}

def stop_bot(bot_id):
    try:
        bots = conn.execute("SELECT pid FROM bots WHERE id = ?", (bot_id,)).fetchone()
        if bots and bots['pid']:
            import signal
            os.kill(bots['pid'], signal.SIGTERM)
            time.sleep(1)
        conn.execute("UPDATE bots SET status = 'stopped' WHERE id = ?", (bot_id,))
        conn.commit()
        return True
    except:
        return False

def get_bot_status(bot_id):
    bot = conn.execute("SELECT pid, status FROM bots WHERE id = ?", (bot_id,)).fetchone()
    if bot and bot['pid']:
        try:
            os.kill(bot['pid'], 0)
            return {'running': True}
        except:
            conn.execute("UPDATE bots SET status = 'stopped' WHERE id = ?", (bot_id,))
            conn.commit()
    return {'running': False}

def delete_bot(bot_id, user_id):
    bot = conn.execute("SELECT * FROM bots WHERE id = ? AND user_id = ?", (bot_id, user_id)).fetchone()
    if not bot:
        return False
    stop_bot(bot_id)
    if bot['file_path'] and os.path.exists(bot['file_path']):
        os.remove(bot['file_path'])
    conn.execute("DELETE FROM bots WHERE id = ?", (bot_id,))
    conn.execute("UPDATE users SET bots_count = bots_count - 1 WHERE id = ?", (user_id,))
    conn.commit()
    return True

def get_user_bots(user_id):
    return [dict(r) for r in conn.execute("SELECT * FROM bots WHERE user_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()]

# ==================== Flask App ====================
app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# ==================== HTML ====================
LOGIN_HTML = '''
<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>ورود - ساخت ربات تلگرام</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body{background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px;font-family:'Vazirmatn',Tahoma,sans-serif}
        .card{background:white;border-radius:32px;padding:40px;max-width:450px;width:100%;box-shadow:0 25px 50px rgba(0,0,0,0.2)}
        .btn-primary{background:linear-gradient(135deg,#667eea,#764ba2);border:none;border-radius:14px;padding:12px;width:100%}
        .form-control{border-radius:14px;padding:12px}
    </style>
</head>
<body>
    <div class="card">
        <div class="text-center mb-4">
            <i class="fas fa-robot fa-3x" style="color:#667eea"></i>
            <h2 class="mt-3">ساخت ربات تلگرام</h2>
        </div>
        <div id="errorMsg" class="alert alert-danger" style="display:none"></div>
        <form id="loginForm">
            <input type="text" id="username" class="form-control mb-3" placeholder="نام کاربری" required>
            <input type="password" id="password" class="form-control mb-3" placeholder="رمز عبور" required>
            <button type="submit" class="btn-primary">ورود</button>
        </form>
        <div class="text-center mt-3"><a href="/register">ثبت نام</a></div>
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
            if(res.ok) location.href='/';
            else {errorMsg.style.display='block'; errorMsg.innerText=data.error;}
        };
    </script>
</body>
</html>
'''

REGISTER_HTML = '''
<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>ثبت نام - ساخت ربات تلگرام</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body{background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
        .card{background:white;border-radius:32px;padding:40px;max-width:500px;width:100%}
        .btn-primary{background:linear-gradient(135deg,#667eea,#764ba2);border:none;border-radius:14px;padding:12px;width:100%}
        .form-control{border-radius:14px;padding:12px}
    </style>
</head>
<body>
    <div class="card">
        <div class="text-center mb-4"><i class="fas fa-user-plus fa-3x" style="color:#667eea"></i><h2>ثبت نام</h2></div>
        <div id="errorMsg" class="alert alert-danger" style="display:none"></div>
        <form id="registerForm">
            <input type="text" id="username" class="form-control mb-3" placeholder="نام کاربری" required>
            <input type="password" id="password" class="form-control mb-3" placeholder="رمز عبور" required minlength="6">
            <input type="text" id="full_name" class="form-control mb-3" placeholder="نام کامل" required>
            <input type="text" id="referral_code" class="form-control mb-3" placeholder="کد معرف (اختیاری)">
            <button type="submit" class="btn-primary">ثبت نام</button>
        </form>
        <div class="text-center mt-3"><a href="/login">ورود</a></div>
    </div>
    <script>
        document.getElementById('registerForm').onsubmit = async (e) => {
            e.preventDefault();
            const res = await fetch('/api/register', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({username: username.value, password: password.value, full_name: full_name.value, referral_code: referral_code.value})
            });
            const data = await res.json();
            if(res.ok) location.href='/login';
            else {errorMsg.style.display='block'; errorMsg.innerText=data.error;}
        };
    </script>
</body>
</html>
'''

MAIN_HTML = '''
<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>ساخت ربات تلگرام - پنل کاربری</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        *{font-family:'Vazirmatn',Tahoma,sans-serif}
        body{background:#f0f2f5;padding-bottom:80px}
        .sidebar{background:linear-gradient(180deg,#1a1a2e,#16213e);min-height:100vh;color:white;position:fixed;right:0;top:0;width:280px;z-index:1000;transition:0.3s}
        .sidebar .nav-link{color:rgba(255,255,255,0.7);padding:12px 20px;margin:5px 10px;border-radius:12px}
        .sidebar .nav-link:hover,.sidebar .nav-link.active{background:rgba(102,126,234,0.3);color:white}
        .sidebar .nav-link i{margin-left:10px;width:24px}
        .main-content{margin-right:280px;padding:20px}
        .card{background:white;border:none;border-radius:20px;box-shadow:0 2px 10px rgba(0,0,0,0.05);margin-bottom:20px}
        .stat-card{background:linear-gradient(135deg,#667eea,#764ba2);border-radius:20px;padding:20px;color:white}
        .btn-primary{background:linear-gradient(135deg,#667eea,#764ba2);border:none;border-radius:12px;padding:10px 20px}
        .status-badge{display:inline-block;padding:4px 12px;border-radius:20px;font-size:0.75rem;font-weight:600}
        .status-running{background:#d4edda;color:#155724}
        .status-stopped{background:#f8d7da;color:#721c24}
        .code-area{font-family:monospace;background:#1e1e2e;color:#fff;padding:16px;border-radius:12px;font-size:13px}
        .toast-msg{position:fixed;bottom:20px;left:20px;right:20px;background:#333;color:white;padding:14px;border-radius:16px;text-align:center;z-index:1100;display:none}
        .menu-toggle{display:none;position:fixed;top:15px;right:15px;z-index:1001;background:#667eea;color:white;border:none;border-radius:12px;padding:10px}
        .admin-float{position:fixed;bottom:20px;left:20px;z-index:999}
        .admin-float button{width:55px;height:55px;border-radius:50%;background:#ff4757;border:none;color:white;box-shadow:0 4px 15px rgba(0,0,0,0.2)}
        @media (max-width:768px){
            .sidebar{right:-280px}
            .sidebar.open{right:0}
            .main-content{margin-right:0}
            .menu-toggle{display:block}
        }
        .loader{display:inline-block;width:20px;height:20px;border:3px solid #f3f3f3;border-top:3px solid #667eea;border-radius:50%;animation:spin 1s linear infinite}
        @keyframes spin{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}
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
        <a class="nav-link" href="#" onclick="showPage('guide')"><i class="fas fa-book"></i> راهنما</a>
        <hr>
        <a class="nav-link" href="#" onclick="showPage('settings')"><i class="fas fa-cog"></i> تنظیمات</a>
        <a class="nav-link" href="/logout"><i class="fas fa-sign-out-alt"></i> خروج</a>
    </nav>
</div>

<div class="main-content">
    <div id="page-dashboard">
        <div class="d-flex justify-content-between mb-4">
            <h3><i class="fas fa-chart-line me-2"></i>داشبورد</h3>
            <span id="currentTime"></span>
        </div>
        <div class="row g-4 mb-4" id="statsCards"></div>
        <div class="row">
            <div class="col-md-8">
                <div class="card p-4"><h5>ربات‌های اخیر</h5><div id="recentBots"></div></div>
            </div>
            <div class="col-md-4">
                <div class="card p-4 text-center">
                    <h5>کد معرف شما</h5>
                    <code id="referralCode"></code>
                    <button class="btn btn-sm btn-outline-primary mt-2" onclick="copyReferral()">کپی لینک</button>
                    <hr>
                    <h6>تعداد دعوت‌ها: <span id="refCount">0</span></h6>
                    <h6>کمیسیون کل: <span id="totalComm">0</span></h6>
                </div>
            </div>
        </div>
    </div>

    <div id="page-build" style="display:none">
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
                    <div class="border rounded p-4 text-center" style="border-style:dashed;cursor:pointer" onclick="document.getElementById('botFile').click()">
                        <i class="fas fa-cloud-upload-alt fa-3x text-primary"></i>
                        <p class="mt-2">برای انتخاب فایل کلیک کنید</p>
                        <input type="file" id="botFile" class="d-none" accept=".py,.zip">
                        <div id="fileName" class="mt-2 text-success small"></div>
                    </div>
                </div>
            </div>
            <div class="mt-4"><button class="btn btn-primary w-100" onclick="buildBot()" id="buildBtn">ساخت ربات</button></div>
            <div id="buildStatus" class="mt-3" style="display:none"></div>
        </div>
    </div>

    <div id="page-bots" style="display:none">
        <div class="card p-4">
            <div class="d-flex justify-content-between mb-3">
                <h4><i class="fas fa-list me-2"></i>ربات‌های من</h4>
                <button class="btn btn-sm btn-outline-primary" onclick="loadBots()"><i class="fas fa-sync-alt"></i></button>
            </div>
            <div id="botsList"></div>
        </div>
    </div>

    <div id="page-wallet" style="display:none">
        <div class="row g-4 mb-4">
            <div class="col-md-6"><div class="card p-4 text-center"><h5>موجودی کیف پول</h5><h2 id="walletBalance">0</h2><button class="btn btn-sm btn-warning mt-2" onclick="showWithdraw()">درخواست برداشت</button></div></div>
            <div class="col-md-6"><div class="card p-4 text-center"><h5>وضعیت اشتراک</h5><h3 id="subStatus">غیرفعال</h3><small id="expiryDate"></small></div></div>
        </div>
        <div class="card p-4">
            <h5>خرید اشتراک ماهیانه</h5>
            <p>مبلغ: <strong id="priceDisplay"></strong></p>
            <div class="border rounded p-3 mb-3">
                <p>شماره کارت: <code id="cardNumber"></code></p>
                <p>نام دارنده: <code id="cardHolder"></code></p>
                <p>بانک: <code id="cardBank"></code></p>
            </div>
            <button class="btn btn-success w-100" onclick="uploadReceipt()">ارسال فیش واریز</button>
        </div>
    </div>

    <div id="page-referrals" style="display:none">
        <div class="card p-4 text-center">
            <i class="fas fa-share-alt fa-3x text-primary"></i>
            <h4 class="mt-3">دعوت از دوستان</h4>
            <p>با دعوت دوستان، <strong>7% کمیسیون</strong> دریافت کنید</p>
            <div class="bg-light p-3 rounded"><code id="refLink"></code></div>
            <button class="btn btn-primary mt-3" onclick="copyReferral()">کپی لینک دعوت</button>
        </div>
    </div>

    <div id="page-guide" style="display:none">
        <div class="card p-4" id="guideText"></div>
    </div>

    <div id="page-settings" style="display:none">
        <div class="card p-4">
            <h4>تنظیمات حساب</h4>
            <form id="profileForm">
                <div class="mb-3"><label>نام کامل</label><input type="text" id="fullName" class="form-control"></div>
                <div class="mb-3"><label>رمز جدید</label><input type="password" id="newPass" class="form-control"></div>
                <button type="submit" class="btn btn-primary">ذخیره</button>
            </form>
        </div>
    </div>

    <div id="page-admin" style="display:none">
        <div class="card p-4 mb-4"><h4>آمار سیستم</h4><div class="row" id="adminStats"></div></div>
        <div class="card p-4 mb-4"><h4>تایید فیش‌ها</h4><div id="receiptsList"></div></div>
        <div class="card p-4 mb-4"><h4>تایید برداشت‌ها</h4><div id="withdrawsList"></div></div>
        <div class="card p-4 mb-4"><h4>مدیریت کاربران</h4><div id="usersList"></div></div>
        <div class="card p-4 mb-4">
            <h4>تنظیمات سایت</h4>
            <div class="row">
                <div class="col-md-6"><label>شماره کارت</label><input type="text" id="adminCard" class="form-control mb-2"></div>
                <div class="col-md-6"><label>نام دارنده</label><input type="text" id="adminHolder" class="form-control mb-2"></div>
                <div class="col-md-6"><label>بانک</label><input type="text" id="adminBank" class="form-control mb-2"></div>
                <div class="col-md-6"><label>قیمت اشتراک</label><input type="number" id="adminPrice" class="form-control mb-2"></div>
                <div class="col-md-6"><label>درصد کمیسیون</label><input type="number" id="adminCommission" class="form-control mb-2"></div>
                <div class="col-md-6"><label>حداقل برداشت</label><input type="number" id="adminMinWithdraw" class="form-control mb-2"></div>
            </div>
            <button class="btn btn-primary mt-3" onclick="saveSettings()">ذخیره تنظیمات</button>
        </div>
        <div class="card p-4"><h4>پیام همگانی</h4><textarea id="broadcastMsg" class="form-control mb-2" rows="3"></textarea><button class="btn btn-warning" onclick="sendBroadcast()">ارسال به همه</button></div>
    </div>
</div>

<div class="admin-float" id="adminBtn" style="display:none"><button onclick="showAdminPass()"><i class="fas fa-shield-alt fa-2x"></i></button></div>

<div class="modal fade" id="adminPassModal" tabindex="-1"><div class="modal-dialog modal-dialog-centered"><div class="modal-content"><div class="modal-header"><h5>پنل مدیریت</h5><button type="button" class="btn-close" data-bs-dismiss="modal"></button></div><div class="modal-body"><input type="password" id="adminPassInput" class="form-control" placeholder="رمز عبور"><div id="adminPassError" class="text-danger mt-2" style="display:none">رمز اشتباه است</div></div><div class="modal-footer"><button class="btn btn-secondary" data-bs-dismiss="modal">انصراف</button><button class="btn btn-danger" onclick="checkAdminPass()">ورود</button></div></div></div></div>

<div class="modal fade" id="withdrawModal" tabindex="-1"><div class="modal-dialog modal-dialog-centered"><div class="modal-content"><div class="modal-header"><h5>درخواست برداشت</h5><button type="button" class="btn-close" data-bs-dismiss="modal"></button></div><div class="modal-body"><p>حداقل برداشت: <span id="minWithdrawSpan"></span> تومان</p><p>موجودی: <span id="withdrawBalanceSpan"></span> تومان</p><input type="text" id="withdrawAddress" class="form-control" placeholder="آدرس کیف پول"></div><div class="modal-footer"><button class="btn btn-secondary" data-bs-dismiss="modal">انصراف</button><button class="btn btn-primary" onclick="submitWithdraw()">ثبت</button></div></div></div></div>

<div id="toast" class="toast-msg"></div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
let currentUser = null, isAdmin = false;

function toggleSidebar(){document.getElementById('sidebar').classList.toggle('open')}
function showToast(msg,err){let t=document.getElementById('toast');t.textContent=msg;t.style.background=err?'#dc3545':'#10b981';t.style.display='block';setTimeout(()=>t.style.display='none',3000)}

async function loadUser(){
    let r=await fetch('/api/user');
    if(r.ok){
        currentUser=await r.json();
        isAdmin=currentUser.is_admin===1;
        document.getElementById('userName').innerHTML=currentUser.full_name||currentUser.username;
        document.getElementById('userSubStatus').innerHTML=currentUser.subscription_active?'✅ اشتراک فعال':'❌ اشتراک غیرفعال';
        if(isAdmin) document.getElementById('adminBtn').style.display='block';
    }
}

function showPage(page){
    document.querySelectorAll('[id^="page-"]').forEach(p=>p.style.display='none');
    document.getElementById(`page-${page}`).style.display='block';
    if(page==='dashboard') loadDashboard();
    if(page==='bots') loadBots();
    if(page==='wallet') loadWallet();
    if(page==='referrals') loadReferrals();
    if(page==='guide') loadGuide();
    if(page==='admin' && isAdmin) loadAdminPanel();
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
    if(r.ok){showToast('ربات حذف شد');loadBots();loadDashboard();}
}

document.getElementById('botFile').onchange=function(e){
    if(e.target.files.length) document.getElementById('fileName').innerHTML=e.target.files[0].name;
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
        if(res.ok){showToast('ربات ساخته شد!');document.getElementById('botCode').value='';document.getElementById('botFile').value='';document.getElementById('fileName').innerHTML='';loadBots();loadDashboard();showPage('bots');}
        else{showToast(data.error||'خطا',true);}
    }catch(e){showToast('خطا در ارتباط با سرور',true);}
    btn.disabled=false;btn.innerHTML='ساخت ربات';
}

async function loadWallet(){
    let w=await(await fetch('/api/wallet')).json();
    document.getElementById('walletBalance').innerHTML=(w.balance||0).toLocaleString();
    document.getElementById('subStatus').innerHTML=w.subscription_active?'✅ فعال':'❌ غیرفعال';
    document.getElementById('expiryDate').innerHTML=w.expiry_date||'';
    document.getElementById('priceDisplay').innerHTML=w.subscription_price;
    document.getElementById('cardNumber').innerHTML=w.card_number;
    document.getElementById('cardHolder').innerHTML=w.card_holder;
    document.getElementById('cardBank').innerHTML=w.card_bank;
    document.getElementById('minWithdrawSpan').innerHTML=(w.min_withdraw||2000000).toLocaleString();
    document.getElementById('withdrawBalanceSpan').innerHTML=(w.balance||0).toLocaleString();
}

async function loadReferrals(){
    let r=await(await fetch('/api/referrals')).json();
    document.getElementById('refLink').innerHTML=r.referral_link;
}

async function loadGuide(){
    let g=await(await fetch('/api/guide')).json();
    document.getElementById('guideText').innerHTML=g.guide_text.replace(/\\n/g,'<br>');
}

function copyReferral(){
    let link=document.getElementById('refLink').innerHTML;
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
        if(r.ok) showToast('فیش ارسال شد');
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
    if(r.ok){showToast('درخواست برداشت ثبت شد');bootstrap.Modal.getInstance(document.getElementById('withdrawModal')).hide();loadWallet();}
    else{showToast(d.error,true);}
}

document.getElementById('profileForm').onsubmit=async(e)=>{
    e.preventDefault();
    let r=await fetch('/api/update-profile',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({full_name:fullName.value,password:newPass.value})});
    if(r.ok) showToast('پروفایل بروز شد');
};

function showAdminPass(){new bootstrap.Modal(document.getElementById('adminPassModal')).show();}
async function checkAdminPass(){
    let pwd=document.getElementById('adminPassInput').value;
    if(pwd==='123456'){
        bootstrap.Modal.getInstance(document.getElementById('adminPassModal')).hide();
        showPage('admin');
    }else{
        document.getElementById('adminPassError').style.display='block';
    }
}

async function loadAdminPanel(){
    let stats=await(await fetch('/api/admin/stats')).json();
    document.getElementById('adminStats').innerHTML=`
        <div class="col-md-3"><div class="card p-3 text-center"><h4>${stats.users_count}</h4><small>کاربران</small></div></div>
        <div class="col-md-3"><div class="card p-3 text-center"><h4>${stats.active_subs}</h4><small>اشتراک فعال</small></div></div>
        <div class="col-md-3"><div class="card p-3 text-center"><h4>${stats.total_bots}</h4><small>ربات‌ها</small></div></div>
        <div class="col-md-3"><div class="card p-3 text-center"><h4>${stats.running_bots}</h4><small>ربات فعال</small></div></div>
    `;
    let receipts=await(await fetch('/api/admin/receipts')).json();
    document.getElementById('receiptsList').innerHTML=receipts.map(r=>`
        <div class="border p-2 mb-2 d-flex justify-content-between"><div>کاربر ${r.user_id}<br>${(r.amount||0).toLocaleString()} تومان</div><div><button class="btn btn-sm btn-success" onclick="approveReceipt(${r.id})">تایید</button><button class="btn btn-sm btn-danger" onclick="rejectReceipt(${r.id})">رد</button></div></div>
    `).join('')||'<p>فیشی نیست</p>';
    let withdraws=await(await fetch('/api/admin/withdraws')).json();
    document.getElementById('withdrawsList').innerHTML=withdraws.map(w=>`
        <div class="border p-2 mb-2 d-flex justify-content-between"><div>کاربر ${w.user_id}<br>${(w.amount||0).toLocaleString()} تومان</div><div><button class="btn btn-sm btn-success" onclick="approveWithdraw(${w.id})">تایید</button></div></div>
    `).join('')||'<p>درخواستی نیست</p>';
    let users=await(await fetch('/api/admin/users')).json();
    document.getElementById('usersList').innerHTML=`<table class="table"><thead><tr><th>کاربر</th><th>موجودی</th><th>وضعیت</th><th>ربات‌ها</th><th>عملیات</th></tr></thead><tbody>${users.map(u=>`<tr><td>${u.full_name||u.username}</td><td>${(u.wallet_balance||0).toLocaleString()}</td><td>${u.subscription_active?'✅':'❌'}</td><td>${u.bots_count||0}</td><td><button class="btn btn-sm btn-danger" onclick="banUser(${u.id})">مسدود</button></td></tr>`).join('')}</tbody></table>`;
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
async function saveSettings(){
    let data={card_number:adminCard.value,card_holder:adminHolder.value,card_bank:adminBank.value,subscription_price:parseInt(adminPrice.value),withdraw_percent:parseInt(adminCommission.value),min_withdraw:parseInt(adminMinWithdraw.value)};
    await fetch('/api/admin/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    showToast('تنظیمات ذخیره شد');
}
async function sendBroadcast(){
    let msg=document.getElementById('broadcastMsg').value;
    if(!msg) return;
    let r=await fetch('/api/admin/broadcast',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg})});
    let d=await r.json();
    showToast(`پیام به ${d.sent} نفر ارسال شد`);
    document.getElementById('broadcastMsg').value='';
}

setInterval(()=>{let d=new Date();document.getElementById('currentTime')&&(document.getElementById('currentTime').innerHTML=d.toLocaleTimeString('fa-IR'));},1000);
loadUser().then(()=>{loadDashboard();});
</script>
</body>
</html>
'''

# ==================== API Routes ====================
@app.route('/')
def index():
    if 'user_id' in session:
        return MAIN_HTML
    return redirect(url_for('login_page'))

@app.route('/login')
def login_page():
    return LOGIN_HTML

@app.route('/register')
def register_page():
    return REGISTER_HTML

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('username', '')
    password = hashlib.md5(data.get('password', '').encode()).hexdigest()
    user = conn.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password)).fetchone()
    if user:
        session['user_id'] = user['id']
        session['is_admin'] = user['is_admin']
        return jsonify({'success': True})
    return jsonify({'error': 'نام کاربری یا رمز عبور اشتباه است'}), 401

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    username = data.get('username')
    password = hashlib.md5(data.get('password', '').encode()).hexdigest()
    full_name = data.get('full_name')
    referral_code = data.get('referral_code')
    
    existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if existing:
        return jsonify({'error': 'نام کاربری تکراری'}), 400
    
    ref_by = None
    if referral_code:
        ref_user = conn.execute("SELECT id FROM users WHERE referral_code = ?", (referral_code,)).fetchone()
        if ref_user:
            ref_by = ref_user['id']
    
    my_ref_code = secrets.token_hex(8)
    conn.execute('''
        INSERT INTO users (username, password, full_name, referral_code, referred_by, created_at, max_bots)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (username, password, full_name, my_ref_code, ref_by, datetime.now().isoformat(), int(get_setting('max_bots') or 3)))
    conn.commit()
    return jsonify({'success': True})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

@app.route('/api/user')
def api_user():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
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
    for b in bots:
        status = get_bot_status(b['id'])
        b['status'] = 'running' if status.get('running') else 'stopped'
    return jsonify(bots)

@app.route('/api/bots/<bot_id>/toggle', methods=['POST'])
def api_toggle_bot(bot_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    bot = conn.execute("SELECT * FROM bots WHERE id = ? AND user_id = ?", (bot_id, session['user_id'])).fetchone()
    if not bot:
        return jsonify({'error': 'Not found'}), 404
    
    status = get_bot_status(bot_id)
    if status.get('running'):
        if stop_bot(bot_id):
            return jsonify({'message': 'ربات متوقف شد'})
    else:
        if os.path.exists(bot['file_path']):
            with open(bot['file_path'], 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
            result = run_bot(bot_id, code, bot['token'])
            if result['success']:
                conn.execute("UPDATE bots SET status = 'running', pid = ? WHERE id = ?", (result['pid'], bot_id))
                conn.commit()
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
    
    token = extract_token(code)
    if not token:
        return jsonify({'error': 'توکن ربات در کد پیدا نشد. لطفا توکن را در کد قرار دهید.'}), 400
    
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
    
    result = run_bot(bot_id, code, token)
    
    if result['success']:
        conn.execute('''
            INSERT INTO bots (id, user_id, token, name, username, file_path, pid, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'running', ?)
        ''', (bot_id, user_id, token, bot_info.get('first_name', 'ربات'), bot_info.get('username', ''), file_path, result['pid'], datetime.now().isoformat()))
        conn.execute("UPDATE users SET bots_count = bots_count + 1 WHERE id = ?", (user_id,))
        conn.commit()
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
    
    token = extract_token(code)
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
    
    result = run_bot(bot_id, code, token)
    
    if result['success']:
        conn.execute('''
            INSERT INTO bots (id, user_id, token, name, username, file_path, pid, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'running', ?)
        ''', (bot_id, user_id, token, bot_info.get('first_name', 'ربات'), bot_info.get('username', ''), file_path, result['pid'], datetime.now().isoformat()))
        conn.execute("UPDATE users SET bots_count = bots_count + 1 WHERE id = ?", (user_id,))
        conn.commit()
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
        'card_number': get_setting('card_number'),
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
    return jsonify({'guide_text': get_setting('guide_text')})

@app.route('/api/stats')
def api_stats():
    users = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()
    bots = conn.execute("SELECT COUNT(*) as cnt FROM bots").fetchone()
    return jsonify({'total_users': users['cnt'], 'total_bots': bots['cnt']})

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
    
    conn.execute('''
        INSERT INTO receipts (user_id, amount, receipt_path, tx_hash, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (session['user_id'], int(get_setting('subscription_price') or 2000000), receipt_path, tx_hash, datetime.now().isoformat()))
    conn.commit()
    
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
    
    conn.execute('''
        INSERT INTO withdraw_requests (user_id, amount, address, created_at)
        VALUES (?, ?, ?, ?)
    ''', (session['user_id'], user['wallet_balance'], address, datetime.now().isoformat()))
    conn.execute("UPDATE users SET wallet_balance = 0 WHERE id = ?", (session['user_id'],))
    conn.commit()
    
    return jsonify({'message': 'درخواست برداشت ثبت شد'})

@app.route('/api/update-profile', methods=['POST'])
def api_update_profile():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    if data.get('full_name'):
        conn.execute("UPDATE users SET full_name = ? WHERE id = ?", (data['full_name'], session['user_id']))
    if data.get('password') and data['password'].strip():
        conn.execute("UPDATE users SET password = ? WHERE id = ?", (hashlib.md5(data['password'].encode()).hexdigest(), session['user_id']))
    conn.commit()
    return jsonify({'message': 'بروزرسانی شد'})

# ==================== Admin API ====================
@app.route('/api/admin/stats')
def api_admin_stats():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
    if not user or not user.get('is_admin'):
        return jsonify({'error': 'Forbidden'}), 403
    
    users = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()
    active = conn.execute("SELECT COUNT(*) as cnt FROM users WHERE subscription_status = 'active'").fetchone()
    bots = conn.execute("SELECT COUNT(*) as cnt FROM bots").fetchone()
    running = len([b for b in conn.execute("SELECT id FROM bots").fetchall() if get_bot_status(b['id']).get('running')])
    
    return jsonify({
        'users_count': users['cnt'],
        'active_subs': active['cnt'],
        'total_bots': bots['cnt'],
        'running_bots': running
    })

@app.route('/api/admin/users')
def api_admin_users():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
    if not user or not user.get('is_admin'):
        return jsonify({'error': 'Forbidden'}), 403
    
    users = conn.execute("SELECT id, username, full_name, wallet_balance, subscription_status, bots_count FROM users").fetchall()
    return jsonify([dict(u) for u in users])

@app.route('/api/admin/users/<int:uid>/ban', methods=['POST'])
def api_admin_ban_user(uid):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
    if not user or not user.get('is_admin'):
        return jsonify({'error': 'Forbidden'}), 403
    
    conn.execute("UPDATE users SET is_banned = 1 WHERE id = ?", (uid,))
    conn.commit()
    return jsonify({'message': 'User banned'})

@app.route('/api/admin/receipts')
def api_admin_receipts():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
    if not user or not user.get('is_admin'):
        return jsonify({'error': 'Forbidden'}), 403
    
    receipts = conn.execute("SELECT * FROM receipts WHERE status = 'pending' ORDER BY created_at").fetchall()
    return jsonify([dict(r) for r in receipts])

@app.route('/api/admin/receipt/<int:rid>/approve', methods=['POST'])
def api_admin_approve_receipt(rid):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
    if not user or not user.get('is_admin'):
        return jsonify({'error': 'Forbidden'}), 403
    
    receipt = conn.execute("SELECT user_id FROM receipts WHERE id = ?", (rid,)).fetchone()
    if receipt:
        conn.execute("UPDATE receipts SET status = 'approved' WHERE id = ?", (rid,))
        activate_subscription(receipt['user_id'])
        conn.commit()
    return jsonify({'message': 'Approved'})

@app.route('/api/admin/receipt/<int:rid>/reject', methods=['POST'])
def api_admin_reject_receipt(rid):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
    if not user or not user.get('is_admin'):
        return jsonify({'error': 'Forbidden'}), 403
    
    conn.execute("UPDATE receipts SET status = 'rejected' WHERE id = ?", (rid,))
    conn.commit()
    return jsonify({'message': 'Rejected'})

@app.route('/api/admin/withdraws')
def api_admin_withdraws():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
    if not user or not user.get('is_admin'):
        return jsonify({'error': 'Forbidden'}), 403
    
    withdraws = conn.execute("SELECT * FROM withdraw_requests WHERE status = 'pending' ORDER BY created_at").fetchall()
    return jsonify([dict(w) for w in withdraws])

@app.route('/api/admin/withdraw/<int:wid>/approve', methods=['POST'])
def api_admin_approve_withdraw(wid):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
    if not user or not user.get('is_admin'):
        return jsonify({'error': 'Forbidden'}), 403
    
    conn.execute("UPDATE withdraw_requests SET status = 'approved', processed_at = ? WHERE id = ?", (datetime.now().isoformat(), wid))
    conn.commit()
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
            'card_number': get_setting('card_number'),
            'card_holder': get_setting('card_holder'),
            'card_bank': get_setting('card_bank'),
            'subscription_price': int(get_setting('subscription_price') or 2000000),
            'withdraw_percent': int(get_setting('withdraw_percent') or 7),
            'min_withdraw': int(get_setting('min_withdraw') or 2000000)
        })
    
    data = request.get_json()
    conn.execute("UPDATE settings SET value = ? WHERE key = ?", (data.get('card_number', ''), 'card_number'))
    conn.execute("UPDATE settings SET value = ? WHERE key = ?", (data.get('card_holder', ''), 'card_holder'))
    conn.execute("UPDATE settings SET value = ? WHERE key = ?", (data.get('card_bank', ''), 'card_bank'))
    conn.execute("UPDATE settings SET value = ? WHERE key = ?", (str(data.get('subscription_price', 2000000)), 'subscription_price'))
    conn.execute("UPDATE settings SET value = ? WHERE key = ?", (str(data.get('withdraw_percent', 7)), 'withdraw_percent'))
    conn.execute("UPDATE settings SET value = ? WHERE key = ?", (str(data.get('min_withdraw', 2000000)), 'min_withdraw'))
    conn.execute("UPDATE settings SET value = ? WHERE key = ?", (f"{data.get('subscription_price', 2000000):,} تومان", 'subscription_price_str'))
    conn.commit()
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
    users = conn.execute("SELECT id FROM users WHERE is_banned = 0").fetchall()
    # در اینجا می‌توانید ایمیل یا نوتیفیکیشن ارسال کنید
    return jsonify({'sent': len(users)})

# ==================== اجرا ====================
if __name__ == '__main__':
    print("=" * 70)
    print("🚀 سامانه ساخت ربات تلگرام - نسخه کامل")
    print("=" * 70)
    print(f"📍 آدرس: http://localhost:8080")
    print(f"👤 ادمین: admin / admin123")
    print(f"🔑 رمز پنل مدیریت: 123456")
    print("=" * 70)
    print("✅ نحوه ورود به پنل مدیریت:")
    print("   1. با admin وارد شوید")
    print("   2. دکمه قرمز پایین سمت چپ را بزنید")
    print("   3. رمز 123456 را وارد کنید")
    print("=" * 70)
    
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)