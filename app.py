#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ربات مادر نهایی - نسخه طلایی
با نصب خودکار کتابخانه‌ها و تضمین اجرای ربات
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
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from contextlib import contextmanager

# ==================== تنظیمات پایه ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "database")
FILES_DIR = os.path.join(BASE_DIR, "user_files")
RUNNING_DIR = os.path.join(BASE_DIR, "running_bots")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
RECEIPTS_DIR = os.path.join(BASE_DIR, "receipts")
PENDING_FILES_DIR = os.path.join(BASE_DIR, "pending_files")

for dir_path in [DB_DIR, FILES_DIR, RUNNING_DIR, LOGS_DIR, RECEIPTS_DIR, PENDING_FILES_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# ==================== توکن ربات مادر ====================
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # 🔴 توکن خودت رو اینجا بزار
ADMIN_IDS = [YOUR_ADMIN_ID]  # 🔴 آیدی ادمین خودت رو اینجا بزار

PRICE = 200000
CARD_NUMBER = "5892101187322777"
CARD_HOLDER = "مرتضی نیکخو خنجری"

# ==================== لاگینگ ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, 'mother_bot.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== دیتابیس ====================
DB_PATH = os.path.join(DB_DIR, 'mother_bot.db')

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        # کاربران
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                active_subscription INTEGER DEFAULT 0,
                subscription_end TIMESTAMP,
                created_at TIMESTAMP,
                last_active TIMESTAMP
            )
        ''')
        
        # اشتراک‌ها
        conn.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                subscription_code TEXT UNIQUE,
                amount INTEGER,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP,
                expires_at TIMESTAMP,
                paid_at TIMESTAMP
            )
        ''')
        
        # فایل‌های در انتظار
        conn.execute('''
            CREATE TABLE IF NOT EXISTS pending_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                subscription_id INTEGER,
                file_path TEXT,
                file_name TEXT,
                status TEXT DEFAULT 'pending',
                security_score INTEGER DEFAULT 0,
                security_level TEXT,
                submitted_at TIMESTAMP,
                reviewed_at TIMESTAMP
            )
        ''')
        
        # ربات‌ها
        conn.execute('''
            CREATE TABLE IF NOT EXISTS bots (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                subscription_id INTEGER,
                token TEXT,
                name TEXT,
                username TEXT,
                file_path TEXT,
                folder_path TEXT,
                pid INTEGER,
                status TEXT DEFAULT 'stopped',
                created_at TIMESTAMP,
                expires_at TIMESTAMP,
                last_active TIMESTAMP
            )
        ''')
        
        # فیش‌ها
        conn.execute('''
            CREATE TABLE IF NOT EXISTS receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                subscription_id INTEGER,
                amount INTEGER,
                receipt_path TEXT,
                status TEXT DEFAULT 'pending',
                payment_code TEXT UNIQUE,
                created_at TIMESTAMP,
                reviewed_at TIMESTAMP
            )
        ''')
        
        # کتابخانه‌ها
        conn.execute('''
            CREATE TABLE IF NOT EXISTS libraries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                version TEXT,
                category TEXT,
                install_count INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()
        
        # اضافه کردن کتابخانه‌های پیش‌فرض
        libs = [
            ('requests', '2.31.0', 'web'),
            ('aiohttp', '3.9.0', 'web'),
            ('flask', '3.0.0', 'web'),
            ('numpy', '1.26.0', 'data'),
            ('pandas', '2.1.0', 'data'),
            ('pillow', '10.1.0', 'media'),
            ('beautifulsoup4', '4.12.2', 'scraping'),
            ('selenium', '4.15.0', 'scraping'),
            ('pyTelegramBotAPI', '4.13.0', 'telegram'),
            ('aiogram', '3.1.1', 'telegram'),
            ('cryptography', '41.0.7', 'security'),
            ('jdatetime', '4.1.0', 'i18n'),
            ('yt-dlp', '2023.11.16', 'download'),
            ('openpyxl', '3.1.2', 'office'),
            ('matplotlib', '3.8.0', 'graphics'),
            ('paramiko', '3.4.0', 'network'),
            ('redis', '5.0.1', 'database'),
        ]
        
        for name, ver, cat in libs:
            conn.execute('INSERT OR IGNORE INTO libraries (name, version, category) VALUES (?, ?, ?)', (name, ver, cat))
        
        conn.commit()

init_db()

# ==================== سیستم تحلیل امنیت متعادل ====================

def analyze_code_security(code):
    """تحلیل امنیت کد - متعادل و واقع بینانه"""
    
    result = {
        'is_safe': True,
        'score': 100,
        'issues': [],
        'warnings': [],
        'has_token': False,
        'token': None,
        'bot_info': None,
        'is_telegram_bot': False,
        'required_libs': []
    }
    
    # 1. تشخیص ربات تلگرام
    bot_patterns = [
        r'telebot\.TeleBot',
        r'Bot\(.*token',
        r'@bot\.message_handler',
        r'bot\.infinity_polling',
        r'bot\.polling',
        r'Updater',
        r'Dispatcher',
        r'Application\(\)',
        r'Client\(.*api_id'
    ]
    
    for pattern in bot_patterns:
        if re.search(pattern, code, re.IGNORECASE):
            result['is_telegram_bot'] = True
            break
    
    # 2. استخراج توکن
    token_patterns = [
        r'TOKEN\s*=\s*["\']([^"\']{30,50})["\']',
        r'token\s*=\s*["\']([^"\']{30,50})["\']',
        r'BOT_TOKEN\s*=\s*["\']([^"\']{30,50})["\']',
        r'API_TOKEN\s*=\s*["\']([^"\']{30,50})["\']',
        r'bot\s*=\s*telebot\.TeleBot\(\s*["\']([^"\']{30,50})["\']\s*\)',
        r'Bot\(["\']([^"\']{30,50})["\']\)',
    ]
    
    for pattern in token_patterns:
        match = re.search(pattern, code)
        if match:
            result['has_token'] = True
            result['token'] = match.group(1)
            break
    
    # 3. بررسی کتابخانه‌های مورد نیاز
    lib_patterns = {
        'requests': r'import requests|from requests',
        'aiohttp': r'import aiohttp|from aiohttp',
        'flask': r'import flask|from flask',
        'beautifulsoup4': r'import bs4|from bs4|BeautifulSoup',
        'selenium': r'import selenium|from selenium',
        'numpy': r'import numpy|from numpy',
        'pandas': r'import pandas|from pandas',
        'pillow': r'import PIL|from PIL',
        'cryptography': r'import cryptography|from cryptography',
        'jdatetime': r'import jdatetime|from jdatetime',
        'yt-dlp': r'yt_dlp|youtube_dl',
        'paramiko': r'import paramiko|from paramiko',
        'redis': r'import redis|from redis',
        'openpyxl': r'import openpyxl|from openpyxl',
        'matplotlib': r'import matplotlib|from matplotlib',
        'aiogram': r'aiogram|from aiogram',
        'pyTelegramBotAPI': r'telebot|from telebot',
    }
    
    for lib, pattern in lib_patterns.items():
        if re.search(pattern, code, re.IGNORECASE):
            result['required_libs'].append(lib)
    
    # 4. بررسی کدهای واقعاً خطرناک (نه سخت‌گیرانه)
    dangerous_patterns = [
        (r'os\.system\s*\(\s*["\']rm\s+-rf\s+/', "حذف فایل‌های سیستم - خطرناک"),
        (r'subprocess\.call\s*\(\s*["\'].*rm\s+-rf', "حذف فایل از طریق زیرپروسس - خطرناک"),
        (r'eval\s*\(\s*input\s*\(', "اجرای کد ورودی کاربر - خطرناک"),
        (r'exec\s*\(\s*input\s*\(', "اجرای کد ورودی کاربر - خطرناک"),
        (r'base64\.b64decode.*exec', "کد انکود شده مخرب"),
        (r'socket\.socket.*\.connect.*\.onion', "اتصال به دارک وب"),
    ]
    
    for pattern, msg in dangerous_patterns:
        if re.search(pattern, code, re.IGNORECASE):
            result['issues'].append(msg)
            result['score'] -= 50
            result['is_safe'] = False
    
    # 5. بررسی هشدارها (با کاهش امتیاز کم)
    warning_patterns = [
        (r'os\.system\s*\(', "استفاده از دستور سیستم (در صورت نیاز مجاز است)"),
        (r'eval\s*\(', "استفاده از eval (در صورت نیاز مجاز است)"),
        (r'exec\s*\(', "استفاده از exec (در صورت نیاز مجاز است)"),
        (r'__import__\s*\(', "ایمپورت پویا (معمولاً مجاز است)"),
        (r'socket\.', "استفاده از سوکت (برای ربات‌های معمول مجاز است)"),
    ]
    
    for pattern, msg in warning_patterns:
        if re.search(pattern, code, re.IGNORECASE):
            result['warnings'].append(msg)
            result['score'] -= 5
    
    # 6. امتیاز مثبت برای ربات‌های خوب
    if result['is_telegram_bot']:
        result['score'] += 15
    
    if result['has_token']:
        result['score'] += 10
        # بررسی اعتبار توکن
        try:
            resp = requests.get(f"https://api.telegram.org/bot{result['token']}/getMe", timeout=3)
            if resp.status_code == 200:
                result['bot_info'] = resp.json().get('result', {})
                result['score'] += 15
        except:
            pass
    
    # 7. امتیاز نهایی
    result['score'] = max(0, min(100, result['score']))
    
    # 8. سطح امنیت
    if result['score'] >= 70:
        result['security_level'] = 'امن'
        result['is_safe'] = True
    elif result['score'] >= 50:
        result['security_level'] = 'قابل قبول'
        result['is_safe'] = True
    else:
        result['security_level'] = 'نیاز به بررسی'
        result['is_safe'] = False
    
    return result

# ==================== نصب خودکار کتابخانه‌ها ====================

def install_required_libraries(libraries, chat_id=None):
    """نصب خودکار کتابخانه‌های مورد نیاز"""
    results = []
    
    for lib in libraries:
        try:
            # بررسی نصب بودن
            check = subprocess.run(
                [sys.executable, "-c", f"import {lib.replace('-', '_')}"],
                capture_output=True,
                timeout=5
            )
            
            if check.returncode == 0:
                results.append(f"✅ {lib} (قبلاً نصب شده)")
                continue
        except:
            pass
        
        # نصب کتابخانه
        try:
            process = subprocess.Popen(
                [sys.executable, "-m", "pip", "install", lib, "--quiet"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(timeout=60)
            
            if process.returncode == 0:
                results.append(f"✅ {lib} (نصب شد)")
            else:
                results.append(f"❌ {lib} (خطا: {stderr[:50]})")
        except Exception as e:
            results.append(f"❌ {lib} (خطا: {str(e)[:50]})")
    
    return results

def run_bot_with_auto_install(file_path, bot_id, bot_dir):
    """اجرای ربات با نصب خودکار کتابخانه‌های مورد نیاز"""
    
    try:
        # خواندن کد
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # تحلیل و استخراج کتابخانه‌های مورد نیاز
        analysis = analyze_code_security(code)
        
        # نصب کتابخانه‌های مورد نیاز
        if analysis['required_libs']:
            for lib in analysis['required_libs']:
                try:
                    subprocess.run(
                        [sys.executable, "-m", "pip", "install", lib, "--quiet"],
                        capture_output=True,
                        timeout=60
                    )
                except:
                    pass
        
        # ایجاد پوشه ربات
        os.makedirs(bot_dir, exist_ok=True)
        
        # کپی فایل
        dest_path = os.path.join(bot_dir, 'bot.py')
        shutil.copy(file_path, dest_path)
        
        # ایجاد فایل requirements.txt
        if analysis['required_libs']:
            with open(os.path.join(bot_dir, 'requirements.txt'), 'w') as f:
                f.write('\n'.join(analysis['required_libs']))
        
        # فایل لاگ
        log_file = os.path.join(bot_dir, 'bot.log')
        error_file = os.path.join(bot_dir, 'error.log')
        
        # اجرا
        process = subprocess.Popen(
            [sys.executable, dest_path],
            stdout=open(log_file, 'a'),
            stderr=open(error_file, 'a'),
            cwd=bot_dir,
            start_new_session=True,
            preexec_fn=os.setsid if hasattr(os, 'setsid') else None
        )
        
        time.sleep(3)
        
        if process.poll() is None:
            return True, process.pid, None
        else:
            error_msg = ""
            if os.path.exists(error_file):
                with open(error_file, 'r') as f:
                    error_msg = f.read()[-500:]
            if not error_msg and os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    error_msg = f.read()[-500:]
            
            return False, None, error_msg or "خطای ناشناخته"
            
    except Exception as e:
        return False, None, str(e)

# ==================== توابع کمکی ====================

def create_user(user_id, username, first_name, last_name):
    with get_db() as conn:
        now = datetime.now().isoformat()
        conn.execute('INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, created_at, last_active) VALUES (?, ?, ?, ?, ?, ?)',
                    (user_id, username, first_name, last_name, now, now))
        conn.execute('UPDATE users SET last_active = ? WHERE user_id = ?', (now, user_id))

def has_active_subscription(user_id):
    with get_db() as conn:
        user = conn.execute('SELECT active_subscription, subscription_end FROM users WHERE user_id = ?', (user_id,)).fetchone()
        if user and user['active_subscription'] == 1:
            if user['subscription_end']:
                expire = datetime.fromisoformat(user['subscription_end'])
                if expire > datetime.now():
                    return True
                else:
                    conn.execute('UPDATE users SET active_subscription = 0 WHERE user_id = ?', (user_id,))
                    conn.commit()
                    return False
            return True
        return False

def create_subscription(user_id, amount):
    with get_db() as conn:
        sub_code = hashlib.md5(f"{user_id}_{time.time()}_{secrets.token_hex(4)}".encode()).hexdigest()[:12].upper()
        now = datetime.now().isoformat()
        expires_at = (datetime.now() + timedelta(days=30)).isoformat()
        conn.execute('INSERT INTO subscriptions (user_id, subscription_code, amount, created_at, expires_at, status) VALUES (?, ?, ?, ?, ?, 'pending')',
                    (user_id, sub_code, amount, now, expires_at))
        conn.commit()
        return conn.execute('SELECT last_insert_rowid()').fetchone()[0], sub_code

def activate_subscription(sub_id):
    with get_db() as conn:
        sub = conn.execute('SELECT * FROM subscriptions WHERE id = ?', (sub_id,)).fetchone()
        if sub:
            expires_at = (datetime.now() + timedelta(days=30)).isoformat()
            conn.execute('UPDATE users SET active_subscription = 1, subscription_end = ? WHERE user_id = ?', (expires_at, sub['user_id']))
            conn.execute('UPDATE subscriptions SET status = 'active', paid_at = ? WHERE id = ?', (datetime.now().isoformat(), sub_id))
            conn.commit()
            return True
        return False

def save_uploaded_file(user_id, file_data, file_name):
    user_dir = os.path.join(PENDING_FILES_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    file_path = os.path.join(user_dir, f"{int(time.time())}_{file_name}")
    with open(file_path, 'wb') as f:
        f.write(file_data)
    return file_path

def get_user_bots(user_id):
    with get_db() as conn:
        return [dict(b) for b in conn.execute('SELECT * FROM bots WHERE user_id = ? ORDER BY created_at DESC', (user_id,)).fetchall()]

def stop_bot(pid):
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(1)
        return True
    except:
        return False

# ==================== منوها ====================

def get_main_menu(is_admin=False):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        types.KeyboardButton('🛒 خرید اشتراک'),
        types.KeyboardButton('📤 ارسال فایل ربات'),
        types.KeyboardButton('🤖 ربات‌های من'),
        types.KeyboardButton('📚 راهنما'),
        types.KeyboardButton('📞 پشتیبانی')
    ]
    if is_admin:
        buttons.append(types.KeyboardButton('👑 پنل ادمین'))
    markup.add(*buttons)
    return markup

# ==================== ربات ====================

bot = telebot.TeleBot(BOT_TOKEN)

# هندلر استارت
@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    create_user(user_id, message.from_user.username or "", message.from_user.first_name or "", message.from_user.last_name or "")
    
    is_admin = user_id in ADMIN_IDS
    markup = get_main_menu(is_admin)
    
    bot.send_message(message.chat.id, 
        f"🚀 به ربات سازنده خوش آمدید!\n\n"
        f"💰 قیمت اشتراک: {PRICE:,} تومان\n"
        f"📞 پشتیبانی: @shahraghee13",
        reply_markup=markup)

# خرید اشتراک
@bot.message_handler(func=lambda m: m.text == '🛒 خرید اشتراک')
def buy_subscription(message):
    user_id = message.from_user.id
    
    if has_active_subscription(user_id):
        bot.send_message(message.chat.id, "✅ شما اشتراک فعال دارید! لطفاً فایل ربات خود را ارسال کنید.")
        return
    
    sub_id, sub_code = create_subscription(user_id, PRICE)
    
    bot.send_message(message.chat.id,
        f"💰 خرید اشتراک ماهانه\n\n"
        f"مبلغ: {PRICE:,} تومان\n"
        f"شماره کارت: {CARD_NUMBER}\n"
        f"به نام: {CARD_HOLDER}\n\n"
        f"🆔 کد اشتراک: {sub_code}\n\n"
        f"پس از واریز، تصویر فیش را ارسال کنید.",
        parse_mode="Markdown")

# دریافت فیش
@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    
    with get_db() as conn:
        pending = conn.execute('SELECT * FROM subscriptions WHERE user_id = ? AND status = 'pending' ORDER BY created_at DESC LIMIT 1', (user_id,)).fetchone()
    
    if not pending:
        bot.reply_to(message, "❌ اشتراک در انتظار پرداختی ندارید")
        return
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        payment_code = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:8].upper()
        receipt_path = os.path.join(RECEIPTS_DIR, f"{user_id}_{payment_code}.jpg")
        
        with open(receipt_path, 'wb') as f:
            f.write(downloaded)
        
        with get_db() as conn:
            conn.execute('INSERT INTO receipts (user_id, subscription_id, amount, receipt_path, payment_code, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                        (user_id, pending['id'], PRICE, receipt_path, payment_code, datetime.now().isoformat()))
            conn.commit()
        
        bot.reply_to(message, f"✅ فیش دریافت شد! کد پیگیری: {payment_code}\n⏳ پس از تأیید ادمین فعال می‌شود.")
        
        for admin_id in ADMIN_IDS:
            try:
                with open(receipt_path, 'rb') as f:
                    bot.send_photo(admin_id, f, caption=f"📸 فیش جدید\n👤 {user_id}\n💰 {PRICE:,} تومان")
            except:
                pass
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")

# ارسال فایل ربات
@bot.message_handler(func=lambda m: m.text == '📤 ارسال فایل ربات')
def send_bot_file(message):
    user_id = message.from_user.id
    
    if not has_active_subscription(user_id):
        bot.send_message(message.chat.id, f"❌ اشتراک فعال ندارید! قیمت: {PRICE:,} تومان")
        return
    
    bot.send_message(message.chat.id, "📤 فایل `.py` ربات خود را ارسال کنید.\n\n🔍 فایل از نظر امنیت بررسی می‌شود.")

@bot.message_handler(content_types=['document'])
def handle_bot_file(message):
    user_id = message.from_user.id
    file_name = message.document.file_name
    
    if not file_name.endswith('.py'):
        bot.reply_to(message, "❌ فقط فایل‌های .py مجاز هستند!")
        return
    
    status_msg = bot.reply_to(message, "🔄 در حال بررسی فایل...")
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        file_path = save_uploaded_file(user_id, downloaded, file_name)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # تحلیل امنیت
        analysis = analyze_code_security(code)
        
        # گرفتن اشتراک
        with get_db() as conn:
            sub = conn.execute('SELECT id FROM subscriptions WHERE user_id = ? AND status = 'active' ORDER BY paid_at DESC LIMIT 1', (user_id,)).fetchone()
        
        if not sub:
            bot.edit_message_text("❌ اشتراک فعال پیدا نشد!", message.chat.id, status_msg.message_id)
            return
        
        # ذخیره در pending
        with get_db() as conn:
            conn.execute('INSERT INTO pending_files (user_id, subscription_id, file_path, file_name, security_score, security_level, submitted_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                        (user_id, sub['id'], file_path, file_name, analysis['score'], analysis['security_level'], datetime.now().isoformat()))
            pending_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            conn.commit()
        
        # نمایش نتیجه
        result_text = f"🔍 **نتیجه بررسی:**\n\n"
        result_text += f"📊 امتیاز: {analysis['score']}/100\n"
        result_text += f"🛡️ سطح: {analysis['security_level']}\n"
        
        if analysis['has_token'] and analysis['bot_info']:
            result_text += f"🤖 ربات: @{analysis['bot_info'].get('username', 'نامشخص')}\n"
        
        if analysis['required_libs']:
            result_text += f"\n📦 کتابخانه‌های مورد نیاز: {', '.join(analysis['required_libs'][:5])}\n"
        
        bot.edit_message_text(result_text, message.chat.id, status_msg.message_id, parse_mode="Markdown")
        
        # اگر امن بود، خودکار تایید کن
        if analysis['score'] >= 60:
            bot.send_message(message.chat.id, "✅ فایل امن تشخیص داده شد! در حال ساخت ربات...")
            auto_approve_and_build(pending_id, user_id, file_path, code, message.chat.id)
        else:
            # ارسال به ادمین
            for admin_id in ADMIN_IDS:
                try:
                    with open(file_path, 'rb') as f:
                        bot.send_document(admin_id, f, caption=f"📥 فایل جدید\n👤 {user_id}\n📄 {file_name}\n🤖 امتیاز: {analysis['score']}/100\n🆔 {pending_id}")
                except:
                    pass
            
            bot.send_message(message.chat.id, f"✅ فایل به ادمین ارسال شد. پس از تایید ساخته می‌شود.")
            
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)}", message.chat.id, status_msg.message_id)

# ==================== تابع اصلی تایید و ساخت ربات ====================

def auto_approve_and_build(pending_id, user_id, file_path, code, chat_id):
    """تایید خودکار و ساخت ربات با نصب کتابخانه‌ها"""
    
    try:
        # استخراج توکن
        token = None
        token_patterns = [
            r'TOKEN\s*=\s*["\']([^"\']{30,50})["\']',
            r'token\s*=\s*["\']([^"\']{30,50})["\']',
            r'BOT_TOKEN\s*=\s*["\']([^"\']{30,50})["\']',
            r'bot\s*=\s*telebot\.TeleBot\(\s*["\']([^"\']{30,50})["\']\s*\)',
        ]
        
        for pattern in token_patterns:
            match = re.search(pattern, code)
            if match:
                token = match.group(1)
                break
        
        if not token:
            bot.send_message(chat_id, "❌ توکن در کد پیدا نشد!")
            return
        
        # بررسی اعتبار توکن
        try:
            resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
            if resp.status_code != 200:
                bot.send_message(chat_id, f"❌ توکن معتبر نیست! خطا: {resp.text[:100]}")
                return
            bot_data = resp.json()['result']
        except Exception as e:
            bot.send_message(chat_id, f"❌ خطا در بررسی توکن: {str(e)}")
            return
        
        # تحلیل و نصب کتابخانه‌های مورد نیاز
        analysis = analyze_code_security(code)
        
        if analysis['required_libs']:
            bot.send_message(chat_id, f"📦 در حال نصب کتابخانه‌های مورد نیاز: {', '.join(analysis['required_libs'][:5])}...")
            
            install_results = install_required_libraries(analysis['required_libs'], chat_id)
            
            # نمایش نتیجه نصب
            success_count = sum(1 for r in install_results if '✅' in r)
            bot.send_message(chat_id, f"📦 نصب کتابخانه‌ها: {success_count}/{len(analysis['required_libs'])} موفق")
        
        # ساخت ربات
        bot_id = hashlib.md5(f"{user_id}_{token}_{time.time()}".encode()).hexdigest()[:10]
        bot_dir = os.path.join(RUNNING_DIR, bot_id)
        
        bot.send_message(chat_id, "🔄 در حال اجرای ربات...")
        
        success, pid, error = run_bot_with_auto_install(file_path, bot_id, bot_dir)
        
        if success:
            expires_at = (datetime.now() + timedelta(days=30)).isoformat()
            
            with get_db() as conn:
                conn.execute('UPDATE pending_files SET status = 'approved', reviewed_at = ? WHERE id = ?', (datetime.now().isoformat(), pending_id))
                conn.execute('''
                    INSERT INTO bots (id, user_id, subscription_id, token, name, username, file_path, folder_path, pid, status, created_at, expires_at)
                    VALUES (?, ?, (SELECT subscription_id FROM pending_files WHERE id = ?), ?, ?, ?, ?, ?, ?, 'running', ?, ?)
                ''', (bot_id, user_id, pending_id, token, bot_data['first_name'], bot_data['username'], file_path, bot_dir, pid, datetime.now().isoformat(), expires_at))
                conn.commit()
            
            # پیام موفقیت به کاربر
            try:
                bot.send_message(user_id,
                    f"✅ **ربات شما با موفقیت ساخته شد!** 🎉\n\n"
                    f"🤖 **نام:** {bot_data['first_name']}\n"
                    f"🔗 **لینک:** https://t.me/{bot_data['username']}\n"
                    f"🆔 **آیدی:** `{bot_id}`\n"
                    f"📅 **اعتبار:** ۳۰ روز\n\n"
                    f"از منوی «ربات‌های من» می‌توانید آن را مدیریت کنید.",
                    parse_mode="Markdown")
            except:
                pass
            
            bot.send_message(chat_id,
                f"✅ **ربات با موفقیت ساخته شد!**\n\n"
                f"🤖 {bot_data['first_name']}\n"
                f"🔗 https://t.me/{bot_data['username']}\n"
                f"🆔 `{bot_id}`",
                parse_mode="Markdown")
        else:
            bot.send_message(chat_id,
                f"❌ **خطا در اجرای ربات!**\n\n"
                f"خطا:\n```\n{error[:300]}\n```\n\n"
                f"💡 **راهکار:**\n"
                f"1. کد ربات را بررسی کنید\n"
                f"2. مطمئن شوید توکن معتبر است\n"
                f"3. کتابخانه‌های مورد نیاز را نصب کنید",
                parse_mode="Markdown")
            
    except Exception as e:
        bot.send_message(chat_id, f"❌ خطا: {str(e)}")

# ==================== تایید دستی توسط ادمین ====================

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_file_'))
def admin_approve_file(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    pending_id = int(call.data.replace('approve_file_', ''))
    
    status_msg = bot.send_message(call.message.chat.id, "🔄 در حال ساخت ربات...")
    
    with get_db() as conn:
        pending = conn.execute('SELECT * FROM pending_files WHERE id = ?', (pending_id,)).fetchone()
        if not pending:
            bot.edit_message_text("❌ فایل پیدا نشد!", call.message.chat.id, status_msg.message_id)
            return
        
        # خواندن کد
        try:
            with open(pending['file_path'], 'r', encoding='utf-8') as f:
                code = f.read()
        except:
            with open(pending['file_path'], 'r', encoding='cp1256') as f:
                code = f.read()
        
        # استخراج توکن
        token = None
        token_patterns = [
            r'TOKEN\s*=\s*["\']([^"\']{30,50})["\']',
            r'token\s*=\s*["\']([^"\']{30,50})["\']',
            r'BOT_TOKEN\s*=\s*["\']([^"\']{30,50})["\']',
            r'bot\s*=\s*telebot\.TeleBot\(\s*["\']([^"\']{30,50})["\']\s*\)',
        ]
        
        for pattern in token_patterns:
            match = re.search(pattern, code)
            if match:
                token = match.group(1)
                break
        
        if not token:
            bot.edit_message_text("❌ توکن در کد پیدا نشد!", call.message.chat.id, status_msg.message_id)
            return
        
        # بررسی توکن
        try:
            resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
            if resp.status_code != 200:
                bot.edit_message_text(f"❌ توکن معتبر نیست!", call.message.chat.id, status_msg.message_id)
                return
            bot_data = resp.json()['result']
        except Exception as e:
            bot.edit_message_text(f"❌ خطا: {str(e)}", call.message.chat.id, status_msg.message_id)
            return
        
        # تحلیل و نصب کتابخانه‌ها
        analysis = analyze_code_security(code)
        
        if analysis['required_libs']:
            bot.edit_message_text(f"📦 در حال نصب {len(analysis['required_libs'])} کتابخانه...", 
                                 call.message.chat.id, status_msg.message_id)
            install_required_libraries(analysis['required_libs'])
        
        # ساخت ربات
        bot_id = hashlib.md5(f"{pending['user_id']}_{token}_{time.time()}".encode()).hexdigest()[:10]
        bot_dir = os.path.join(RUNNING_DIR, bot_id)
        
        bot.edit_message_text("🔄 در حال اجرای ربات...", call.message.chat.id, status_msg.message_id)
        
        success, pid, error = run_bot_with_auto_install(pending['file_path'], bot_id, bot_dir)
        
        if success:
            expires_at = (datetime.now() + timedelta(days=30)).isoformat()
            
            conn.execute('UPDATE pending_files SET status = 'approved', reviewed_at = ? WHERE id = ?', (datetime.now().isoformat(), pending_id))
            conn.execute('''
                INSERT INTO bots (id, user_id, subscription_id, token, name, username, file_path, folder_path, pid, status, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'running', ?, ?)
            ''', (bot_id, pending['user_id'], pending['subscription_id'], token, bot_data['first_name'], 
                  bot_data['username'], pending['file_path'], bot_dir, pid, datetime.now().isoformat(), expires_at))
            conn.commit()
            
            # پیام به کاربر
            try:
                bot.send_message(pending['user_id'], 
                    f"✅ **ربات شما با موفقیت ساخته شد!** 🎉\n\n"
                    f"🤖 **نام:** {bot_data['first_name']}\n"
                    f"🔗 **لینک:** https://t.me/{bot_data['username']}\n"
                    f"📅 **اعتبار:** ۳۰ روز\n\n"
                    f"از منوی «ربات‌های من» مدیریت کنید.",
                    parse_mode="Markdown")
            except:
                pass
            
            bot.edit_message_text(
                f"✅ **ربات ساخته شد!**\n\n"
                f"🤖 {bot_data['first_name']}\n"
                f"🔗 https://t.me/{bot_data['username']}",
                call.message.chat.id, status_msg.message_id)
        else:
            bot.edit_message_text(
                f"❌ **خطا در اجرا!**\n\n```\n{error[:300]}\n```",
                call.message.chat.id, status_msg.message_id, parse_mode="Markdown")

# ==================== ربات‌های من ====================

@bot.message_handler(func=lambda m: m.text == '🤖 ربات‌های من')
def my_bots(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما رباتی ندارید!")
        return
    
    for b in bots:
        is_running = False
        if b['pid']:
            try:
                os.kill(b['pid'], 0)
                is_running = True
            except:
                pass
        
        status = "🟢 در حال اجرا" if is_running else "🔴 متوقف"
        
        text = f"{status}\n"
        text += f"🤖 **{b['name']}**\n"
        text += f"🔗 https://t.me/{b['username']}\n"
        text += f"🆔 `{b['id']}`\n"
        text += f"📅 انقضا: {b['expires_at'][:10] if b['expires_at'] else 'نامحدود'}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🔄 توقف/اجرا", callback_data=f"toggle_{b['id']}"),
            types.InlineKeyboardButton("🗑 حذف", callback_data=f"delete_{b['id']}")
        )
        
        bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_'))
def toggle_bot(call):
    bot_id = call.data.replace('toggle_', '')
    user_id = call.from_user.id
    
    with get_db() as conn:
        bot_info = conn.execute('SELECT * FROM bots WHERE id = ? AND user_id = ?', (bot_id, user_id)).fetchone()
    
    if not bot_info:
        bot.answer_callback_query(call.id, "❌ پیدا نشد!")
        return
    
    if bot_info['status'] == 'running':
        if stop_bot(bot_info['pid']):
            conn.execute('UPDATE bots SET status = 'stopped' WHERE id = ?', (bot_id,))
            conn.commit()
            bot.answer_callback_query(call.id, "✅ متوقف شد")
        else:
            bot.answer_callback_query(call.id, "❌ خطا!")
    else:
        success, pid, error = run_bot_with_auto_install(bot_info['file_path'], bot_id, bot_info['folder_path'])
        if success:
            conn.execute('UPDATE bots SET status = 'running', pid = ? WHERE id = ?', (pid, bot_id))
            conn.commit()
            bot.answer_callback_query(call.id, "✅ اجرا شد")
        else:
            bot.answer_callback_query(call.id, f"❌ {error[:50]}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
def delete_bot(call):
    bot_id = call.data.replace('delete_', '')
    user_id = call.from_user.id
    
    with get_db() as conn:
        bot_info = conn.execute('SELECT * FROM bots WHERE id = ? AND user_id = ?', (bot_id, user_id)).fetchone()
        if bot_info:
            stop_bot(bot_info['pid'])
            if bot_info['folder_path'] and os.path.exists(bot_info['folder_path']):
                shutil.rmtree(bot_info['folder_path'])
            conn.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
            conn.commit()
            bot.answer_callback_query(call.id, "✅ حذف شد")
        else:
            bot.answer_callback_query(call.id, "❌ پیدا نشد!")

# ==================== پنل ادمین ====================

@bot.message_handler(func=lambda m: m.text == '👑 پنل ادمین')
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        pending_files = conn.execute('SELECT * FROM pending_files WHERE status = 'pending' ORDER BY submitted_at DESC').fetchall()
        pending_receipts = conn.execute('SELECT * FROM receipts WHERE status = 'pending' ORDER BY created_at DESC').fetchall()
        total_users = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        total_bots = conn.execute('SELECT COUNT(*) FROM bots').fetchone()[0]
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(f"📥 فایل‌ها ({len(pending_files)})", callback_data="admin_pending_files"),
        types.InlineKeyboardButton(f"📸 فیش‌ها ({len(pending_receipts)})", callback_data="admin_receipts"),
        types.InlineKeyboardButton(f"👥 کاربران ({total_users})", callback_data="admin_users"),
        types.InlineKeyboardButton(f"🤖 ربات‌ها ({total_bots})", callback_data="admin_bots"),
        types.InlineKeyboardButton("📊 آمار", callback_data="admin_stats"),
        types.InlineKeyboardButton("💰 تایید دستی", callback_data="admin_manual")
    )
    
    bot.send_message(message.chat.id, "👑 پنل مدیریت:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_pending_files")
def admin_pending_files(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        files = conn.execute('''
            SELECT pf.*, u.first_name 
            FROM pending_files pf 
            JOIN users u ON pf.user_id = u.user_id 
            WHERE pf.status = 'pending' 
            ORDER BY pf.submitted_at ASC
        ''').fetchall()
    
    if not files:
        bot.send_message(call.message.chat.id, "📥 هیچ فایل در انتظاری نیست")
        return
    
    for f in files:
        text = f"📥 فایل از: {f['first_name']}\n📄 {f['file_name']}\n🤖 امتیاز: {f['security_score']}/100\n🆔 {f['id']}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_file_{f['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"reject_file_{f['id']}")
        )
        
        with open(f['file_path'], 'rb') as file:
            bot.send_document(call.message.chat.id, file, caption=text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_receipts")
def admin_receipts(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        receipts = conn.execute('SELECT * FROM receipts WHERE status = 'pending' ORDER BY created_at DESC').fetchall()
    
    if not receipts:
        bot.send_message(call.message.chat.id, "📸 هیچ فیشی نیست")
        return
    
    for r in receipts:
        text = f"📸 فیش\n👤 {r['user_id']}\n💰 {r['amount']:,} تومان\n🆔 {r['payment_code']}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_pay_{r['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"reject_pay_{r['id']}")
        )
        
        if os.path.exists(r['receipt_path']):
            with open(r['receipt_path'], 'rb') as f:
                bot.send_photo(call.message.chat.id, f, caption=text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_pay_'))
def approve_payment(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    receipt_id = int(call.data.replace('approve_pay_', ''))
    
    with get_db() as conn:
        receipt = conn.execute('SELECT * FROM receipts WHERE id = ?', (receipt_id,)).fetchone()
        if receipt:
            activate_subscription(receipt['subscription_id'])
            conn.execute('UPDATE receipts SET status = 'approved', reviewed_at = ? WHERE id = ?', (datetime.now().isoformat(), receipt_id))
            conn.commit()
            
            try:
                bot.send_message(receipt['user_id'], "✅ پرداخت شما تایید شد! حالا می‌توانید فایل ربات خود را ارسال کنید.")
            except:
                pass
    
    bot.answer_callback_query(call.id, "✅ تایید شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_pay_'))
def reject_payment(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    receipt_id = int(call.data.replace('reject_pay_', ''))
    
    with get_db() as conn:
        conn.execute('UPDATE receipts SET status = 'rejected', reviewed_at = ? WHERE id = ?', (datetime.now().isoformat(), receipt_id))
        conn.commit()
    
    bot.answer_callback_query(call.id, "❌ رد شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_users")
def admin_users(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        users = conn.execute('SELECT user_id, first_name, active_subscription, subscription_end FROM users ORDER BY created_at DESC LIMIT 20').fetchall()
    
    text = "👥 ۲۰ کاربر آخر:\n\n"
    for u in users:
        status = "✅" if u['active_subscription'] else "❌"
        expire = u['subscription_end'][:10] if u['subscription_end'] else "ندارد"
        text += f"{status} {u['first_name']} (🆔 {u['user_id']}) - انقضا: {expire}\n"
    
    bot.send_message(call.message.chat.id, text)

@bot.callback_query_handler(func=lambda call: call.data == "admin_bots")
def admin_bots(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        bots = conn.execute('SELECT id, user_id, name, status FROM bots ORDER BY created_at DESC LIMIT 20').fetchall()
    
    text = "🤖 ۲۰ ربات آخر:\n\n"
    for b in bots:
        text += f"{'🟢' if b['status'] == 'running' else '🔴'} {b['name']} - 👤 {b['user_id']}\n"
    
    bot.send_message(call.message.chat.id, text)

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_stats(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        total_users = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        active_subs = conn.execute('SELECT COUNT(*) FROM users WHERE active_subscription = 1').fetchone()[0]
        total_bots = conn.execute('SELECT COUNT(*) FROM bots').fetchone()[0]
        running_bots = conn.execute('SELECT COUNT(*) FROM bots WHERE status = 'running'').fetchone()[0]
        total_payments = conn.execute('SELECT COUNT(*) FROM receipts WHERE status = 'approved'').fetchone()[0]
        total_amount = conn.execute('SELECT COALESCE(SUM(amount), 0) FROM receipts WHERE status = 'approved'').fetchone()[0]
        pending_files = conn.execute('SELECT COUNT(*) FROM pending_files WHERE status = 'pending'').fetchone()[0]
    
    text = f"📊 آمار:\n\n"
    text += f"👥 کاربران: {total_users}\n"
    text += f"✅ اشتراک فعال: {active_subs}\n"
    text += f"🤖 کل ربات‌ها: {total_bots}\n"
    text += f"🟢 در حال اجرا: {running_bots}\n"
    text += f"💰 مجموع فروش: {total_amount:,} تومان\n"
    text += f"📥 فایل‌های در انتظار: {pending_files}"
    
    bot.send_message(call.message.chat.id, text)

@bot.callback_query_handler(func=lambda call: call.data == "admin_manual")
def admin_manual(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "🆔 آیدی کاربر را برای فعال‌سازی دستی اشتراک وارد کنید:")
    bot.register_next_step_handler(msg, process_manual_activate)

def process_manual_activate(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        user_id = int(message.text.strip())
        
        sub_id, sub_code = create_subscription(user_id, PRICE)
        activate_subscription(sub_id)
        
        try:
            bot.send_message(user_id, "✅ اشتراک شما به صورت دستی فعال شد! حالا می‌توانید فایل ربات خود را ارسال کنید.")
        except:
            pass
        
        bot.reply_to(message, f"✅ اشتراک کاربر {user_id} فعال شد")
    except:
        bot.reply_to(message, "❌ آیدی نامعتبر!")

# ==================== راهنما و پشتیبانی ====================

@bot.message_handler(func=lambda m: m.text == '📚 راهنما')
def guide(message):
    bot.send_message(message.chat.id,
        f"📚 راهنما:\n\n"
        f"1️⃣ خرید اشتراک: {PRICE:,} تومان\n"
        f"2️⃣ ارسال فایل .py ربات\n"
        f"3️⃣ پس از تایید، ربات ساخته می‌شود\n\n"
        f"📞 پشتیبانی: @shahraghee13")

@bot.message_handler(func=lambda m: m.text == '📞 پشتیبانی')
def support(message):
    bot.send_message(message.chat.id, "📞 پشتیبانی: @shahraghee13")

# ==================== تسک زمانبندی ====================

def check_subscriptions():
    while True:
        try:
            with get_db() as conn:
                # غیرفعال کردن اشتراک‌های منقضی
                conn.execute('''
                    UPDATE users SET active_subscription = 0 
                    WHERE active_subscription = 1 AND datetime(subscription_end) <= datetime('now')
                ''')
                
                # توقف ربات‌های منقضی
                expired_bots = conn.execute('''
                    SELECT b.id, b.pid FROM bots b
                    JOIN users u ON b.user_id = u.user_id
                    WHERE u.active_subscription = 0 AND b.status = 'running'
                ''').fetchall()
                
                for bot in expired_bots:
                    stop_bot(bot['pid'])
                    conn.execute('UPDATE bots SET status = 'expired' WHERE id = ?', (bot['id'],))
                
                conn.commit()
            
            time.sleep(3600)
        except Exception as e:
            logger.error(f"خطا: {e}")
            time.sleep(300)

# ==================== اجرا ====================

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 ربات مادر - نسخه نهایی")
    print("=" * 60)
    print(f"✅ ادمین: {ADMIN_IDS}")
    print(f"✅ قیمت: {PRICE:,} تومان")
    print("=" * 60)
    
    # شروع تسک
    thread = threading.Thread(target=check_subscriptions, daemon=True)
    thread.start()
    
    # اجرا
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            print(f"خطا: {e}")
            time.sleep(5)