#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ربات مادر نهایی - نسخه 10.0 نهایی با رفع تمام مشکلات
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
import logging
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
import secrets

# ==================== تنظیمات پایه ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "database")
FILES_DIR = os.path.join(BASE_DIR, "user_files")
RUNNING_DIR = os.path.join(BASE_DIR, "running_bots")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
RECEIPTS_DIR = os.path.join(BASE_DIR, "receipts")

os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(FILES_DIR, exist_ok=True)
os.makedirs(RUNNING_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(RECEIPTS_DIR, exist_ok=True)

# ==================== توکن ربات مادر ====================
BOT_TOKEN = "7685135237:AAEmsHktRw9cEqrHTkCoPZk-fBimK7TDjOo"
bot = telebot.TeleBot(BOT_TOKEN)
bot.delete_webhook()

# ==================== تنظیمات متغیر ====================
ADMIN_IDS = [327855654]
CARD_NUMBER = "5892101187322777"
CARD_HOLDER = "مرتضی نیکخو خنجری"
PRICE_PER_MONTH = 2000000
PRICE_3_MONTHS = 5000000
MIN_WITHDRAW_AMOUNT = 2000000
REFERRAL_COMMISSION_PERCENT = 7
TRIAL_HOURS = 24

GUIDE_TEXT = """📚 راهنمای کامل ربات مادر

1️⃣ ساخت ربات:
   • ابتدا اشتراک خود را فعال کنید یا از تست ۲۴ ساعته استفاده کنید
   • فایل .py یا .zip خود را آپلود کنید
   • توکن ربات باید داخل کد باشد

2️⃣ انواع اشتراک:
   • ماهانه: 2,000,000 تومان
   • سه ماهه: 5,000,000 تومان
   • تست رایگان: 24 ساعت (فقط یک بار)

3️⃣ سیستم رفرال:
   • هر نفر 7% پورسانت خرید
   • لینک اختصاصی خود را به اشتراک بگذارید

4️⃣ برداشت وجه:
   • حداقل مبلغ برداشت: 2,000,000 تومان
   • از طریق بخش برداشت اقدام کنید

5️⃣ پشتیبانی:
   • @shahraghee13
"""

# ==================== لاگینگ ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(os.path.join(LOGS_DIR, 'mother_bot.log'), maxBytes=10485760, backupCount=10),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== دیتابیس ====================
DB_PATH = os.path.join(DB_DIR, 'mother_bot.db')

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

# ایجاد تمام جداول
with get_db() as conn:
    # جدول کاربران
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            balance INTEGER DEFAULT 0,
            bots_count INTEGER DEFAULT 0,
            max_bots INTEGER DEFAULT 1,
            referral_code TEXT UNIQUE,
            referred_by INTEGER,
            referrals_count INTEGER DEFAULT 0,
            verified_referrals INTEGER DEFAULT 0,
            payment_status TEXT DEFAULT 'pending',
            payment_date TIMESTAMP,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP,
            last_active TIMESTAMP
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
            pid INTEGER,
            status TEXT DEFAULT 'stopped',
            created_at TIMESTAMP,
            last_active TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    ''')
    
    # جدول فیش‌های واریزی
    conn.execute('''
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            plan_type TEXT,
            receipt_path TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP,
            reviewed_at TIMESTAMP,
            reviewed_by INTEGER,
            payment_code TEXT UNIQUE,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')
    
    # جدول اشتراک‌ها
    conn.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            plan_type TEXT,
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            is_active INTEGER DEFAULT 1,
            paid_amount INTEGER,
            created_at TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')
    
    # جدول تست 24 ساعته
    conn.execute('''
        CREATE TABLE IF NOT EXISTS trial_usage (
            user_id INTEGER PRIMARY KEY,
            start_time TIMESTAMP,
            bot_id TEXT,
            is_active INTEGER DEFAULT 1,
            used_before INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')
    
    # جدول کمیسیون‌ها
    conn.execute('''
        CREATE TABLE IF NOT EXISTS commissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            reason TEXT,
            from_user_id INTEGER,
            created_at TIMESTAMP,
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
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP,
            processed_at TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')
    
    # جدول تنظیمات
    conn.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    conn.commit()

# ==================== کلاس مدیریت امنیت ====================
class SecurityManager:
    @staticmethod
    def validate_code(code):
        dangerous = ['os.system', 'subprocess', 'eval(', 'exec(', '__import__', 'open(', 'socket.']
        errors = []
        for item in dangerous:
            if item in code.lower():
                errors.append(f"کد خطرناک: {item}")
        return len(errors) == 0, errors

# ==================== کلاس مدیریت داکر (ساده شده) ====================
class BotRunner:
    @staticmethod
    def run_bot(bot_id, code, token):
        try:
            bot_dir = os.path.join(RUNNING_DIR, bot_id)
            os.makedirs(bot_dir, exist_ok=True)
            
            code_path = os.path.join(bot_dir, 'bot.py')
            with open(code_path, 'w', encoding='utf-8') as f:
                f.write(code)
            
            log_file = os.path.join(bot_dir, 'bot.log')
            
            process = subprocess.Popen(
                [sys.executable, code_path],
                stdout=open(log_file, 'a'),
                stderr=subprocess.STDOUT,
                cwd=bot_dir,
                start_new_session=True
            )
            
            time.sleep(2)
            
            if process.poll() is None:
                return {'success': True, 'pid': process.pid}
            else:
                with open(log_file, 'r') as f:
                    error = f.read()[-500:]
                return {'success': False, 'error': error}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def stop_bot(bot_id):
        try:
            with get_db() as conn:
                bot_info = conn.execute('SELECT pid FROM bots WHERE id = ?', (bot_id,)).fetchone()
                if bot_info and bot_info['pid']:
                    os.kill(bot_info['pid'], signal.SIGTERM)
                    return True
        except:
            pass
        return False

# ==================== کلاس مدیریت اشتراک ====================
class SubscriptionManager:
    
    @staticmethod
    def has_active_subscription(user_id):
        with get_db() as conn:
            row = conn.execute('''
                SELECT end_date FROM subscriptions 
                WHERE user_id = ? AND is_active = 1 AND end_date > datetime('now')
            ''', (user_id,)).fetchone()
            return row is not None
    
    @staticmethod
    def activate_subscription(user_id, plan_type, paid_amount):
        with get_db() as conn:
            now = datetime.now()
            
            if plan_type == 'monthly':
                end_date = now + timedelta(days=30)
            elif plan_type == '3months':
                end_date = now + timedelta(days=90)
            else:
                return False
            
            conn.execute('UPDATE subscriptions SET is_active = 0 WHERE user_id = ?', (user_id,))
            
            conn.execute('''
                INSERT INTO subscriptions (user_id, plan_type, start_date, end_date, is_active, paid_amount, created_at)
                VALUES (?, ?, ?, ?, 1, ?, ?)
            ''', (user_id, plan_type, now.isoformat(), end_date.isoformat(), paid_amount, now.isoformat()))
            
            conn.execute('UPDATE users SET payment_status = ?, payment_date = ? WHERE user_id = ?',
                        ('approved', now.isoformat(), user_id))
            conn.commit()
            return True
    
    @staticmethod
    def can_use_trial(user_id):
        """بررسی آیا کاربر می‌تواند از تست 24 ساعته استفاده کند"""
        with get_db() as conn:
            row = conn.execute('SELECT used_before FROM trial_usage WHERE user_id = ?', (user_id,)).fetchone()
            if row and row['used_before'] == 1:
                return False, "شما قبلاً از تست ۲۴ ساعته استفاده کرده‌اید!"
            return True, "میتوانید استفاده کنید"
    
    @staticmethod
    def activate_trial(user_id):
        """فعال کردن تست 24 ساعته"""
        with get_db() as conn:
            now = datetime.now()
            conn.execute('''
                INSERT OR REPLACE INTO trial_usage (user_id, start_time, is_active, used_before)
                VALUES (?, ?, 1, 1)
            ''', (user_id, now.isoformat()))
            conn.commit()
            return True
    
    @staticmethod
    def is_trial_active(user_id):
        """بررسی آیا تست 24 ساعته فعال است"""
        with get_db() as conn:
            row = conn.execute('''
                SELECT start_time FROM trial_usage 
                WHERE user_id = ? AND is_active = 1
            ''', (user_id,)).fetchone()
            
            if not row:
                return False
            
            start_time = datetime.fromisoformat(row['start_time'])
            if datetime.now() - start_time > timedelta(hours=TRIAL_HOURS):
                conn.execute('UPDATE trial_usage SET is_active = 0 WHERE user_id = ?', (user_id,))
                conn.commit()
                return False
            return True
    
    @staticmethod
    def can_create_bot(user_id):
        """بررسی مجوز ساخت ربات"""
        # اول چک کن اشتراک فعال داره؟
        if SubscriptionManager.has_active_subscription(user_id):
            return True, 'subscription'
        
        # بعد چک کن تست 24 ساعته فعال داره؟
        if SubscriptionManager.is_trial_active(user_id):
            return True, 'trial'
        
        # هیچکدام
        return False, None

# ==================== کلاس مدیریت رفرال و کمیسیون ====================
class ReferralManager:
    
    @staticmethod
    def generate_referral_code(user_id):
        return hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:8]
    
    @staticmethod
    def get_referral_link(user_id):
        with get_db() as conn:
            user = conn.execute('SELECT referral_code FROM users WHERE user_id = ?', (user_id,)).fetchone()
            if user:
                bot_username = bot.get_me().username
                return f"https://t.me/{bot_username}?start={user['referral_code']}"
        return None
    
    @staticmethod
    def process_purchase_commission(buyer_id, paid_amount):
        """پرداخت 7% کمیسیون به رفرال دهنده"""
        with get_db() as conn:
            buyer = conn.execute('SELECT referred_by FROM users WHERE user_id = ?', (buyer_id,)).fetchone()
            
            if buyer and buyer['referred_by']:
                referrer_id = buyer['referred_by']
                commission = int(paid_amount * REFERRAL_COMMISSION_PERCENT / 100)
                
                if commission > 0:
                    # اضافه کردن به جدول کمیسیون
                    conn.execute('''
                        INSERT INTO commissions (user_id, amount, reason, from_user_id, created_at)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (referrer_id, commission, f'پورسانت {REFERRAL_COMMISSION_PERCENT}% از خرید کاربر {buyer_id}', buyer_id, datetime.now().isoformat()))
                    
                    # اضافه کردن به کیف پول
                    conn.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (commission, referrer_id))
                    
                    # افزایش آمار رفرال
                    conn.execute('UPDATE users SET verified_referrals = verified_referrals + 1 WHERE user_id = ?', (referrer_id,))
                    
                    conn.commit()
                    
                    # اطلاع به رفرال دهنده
                    try:
                        bot.send_message(
                            referrer_id,
                            f"🎉 {commission:,} تومان پورسانت به کیف پول شما اضافه شد!\n"
                            f"👤 خریدار: {buyer_id}\n"
                            f"💰 مبلغ خرید: {paid_amount:,} تومان\n"
                            f"📊 درصد: {REFERRAL_COMMISSION_PERCENT}%"
                        )
                    except:
                        pass
                    
                    return commission
        return 0
    
    @staticmethod
    def get_balance(user_id):
        with get_db() as conn:
            user = conn.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,)).fetchone()
            return user['balance'] if user else 0

# ==================== کلاس مدیریت برداشت ====================
class WithdrawManager:
    
    @staticmethod
    def request_withdraw(user_id, amount, card_number):
        if amount < MIN_WITHDRAW_AMOUNT:
            return False, f"حداقل مبلغ برداشت {MIN_WITHDRAW_AMOUNT:,} تومان است"
        
        with get_db() as conn:
            balance = conn.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,)).fetchone()
            
            if not balance or balance['balance'] < amount:
                return False, "موجودی کیف پول کافی نیست"
            
            conn.execute('''
                INSERT INTO withdraw_requests (user_id, amount, card_number, created_at)
                VALUES (?, ?, ?, ?)
            ''', (user_id, amount, card_number, datetime.now().isoformat()))
            
            conn.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (amount, user_id))
            conn.commit()
            
            for admin_id in ADMIN_IDS:
                try:
                    bot.send_message(
                        admin_id,
                        f"💰 درخواست برداشت جدید\n"
                        f"👤 کاربر: {user_id}\n"
                        f"💰 مبلغ: {amount:,} تومان\n"
                        f"💳 کارت: {card_number}"
                    )
                except:
                    pass
            
            return True, "درخواست برداشت ثبت شد. پس از بررسی، مبلغ به کارت شما واریز می‌شود."
    
    @staticmethod
    def get_withdraw_requests(status='pending'):
        with get_db() as conn:
            rows = conn.execute('''
                SELECT * FROM withdraw_requests WHERE status = ? ORDER BY created_at DESC
            ''', (status,)).fetchall()
            return [dict(row) for row in rows]
    
    @staticmethod
    def process_withdraw(request_id, action):
        with get_db() as conn:
            request = conn.execute('SELECT * FROM withdraw_requests WHERE id = ?', (request_id,)).fetchone()
            if not request:
                return False, "درخواست یافت نشد"
            
            if action == 'approve':
                conn.execute('''
                    UPDATE withdraw_requests SET status = 'approved', processed_at = ?
                    WHERE id = ?
                ''', (datetime.now().isoformat(), request_id))
                
                try:
                    bot.send_message(
                        request['user_id'],
                        f"✅ درخواست برداشت شما تایید شد!\n💰 مبلغ: {request['amount']:,} تومان\n💳 به کارت {request['card_number']} واریز شد."
                    )
                except:
                    pass
                
            elif action == 'reject':
                conn.execute('''
                    UPDATE withdraw_requests SET status = 'rejected', processed_at = ?
                    WHERE id = ?
                ''', (datetime.now().isoformat(), request_id))
                
                # برگردوندن موجودی
                conn.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', 
                            (request['amount'], request['user_id']))
                
                try:
                    bot.send_message(
                        request['user_id'],
                        f"❌ درخواست برداشت شما رد شد.\n💰 مبلغ {request['amount']:,} تومان به کیف پول شما برگشت."
                    )
                except:
                    pass
            
            conn.commit()
            return True, "عملیات با موفقیت انجام شد"

# ==================== توابع کمکی ====================

def create_user(user_id, username, first_name, last_name, referred_by=None):
    try:
        with get_db() as conn:
            now = datetime.now().isoformat()
            referral_code = ReferralManager.generate_referral_code(user_id)
            
            conn.execute('''
                INSERT OR IGNORE INTO users 
                (user_id, username, first_name, last_name, referral_code, referred_by, created_at, last_active, payment_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name, referral_code, referred_by, now, now, 'pending'))
            
            conn.execute('UPDATE users SET last_active = ? WHERE user_id = ?', (now, user_id))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"خطا در create_user: {e}")
        return False

def get_user(user_id):
    try:
        with get_db() as conn:
            user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
            return dict(user) if user else None
    except:
        return None

def extract_token_from_code(code):
    patterns = [
        r'token\s*=\s*["\']([^"\']+)["\']',
        r'TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'API_TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'BOT_TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'bot\s*=\s*telebot\.TeleBot\(\s*["\']([^"\']+)["\']\s*\)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, code, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

def extract_files_from_zip(zip_path, extract_to):
    py_files = []
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        
        for root, _, files in os.walk(extract_to):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        py_files.append({'name': file, 'path': file_path, 'content': content})
                    except:
                        pass
    except Exception as e:
        logger.error(f"Zip extract error: {e}")
    return py_files

def save_uploaded_file(user_id, file_data, file_name):
    try:
        user_dir = os.path.join(FILES_DIR, str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        timestamp = int(time.time())
        file_path = os.path.join(user_dir, f"{timestamp}_{file_name}")
        with open(file_path, 'wb') as f:
            f.write(file_data)
        return file_path
    except:
        return None

def add_bot_to_db(user_id, bot_id, token, name, username, file_path, pid=None):
    try:
        with get_db() as conn:
            now = datetime.now().isoformat()
            conn.execute('''
                INSERT INTO bots (id, user_id, token, name, username, file_path, pid, status, created_at, last_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (bot_id, user_id, token, name, username, file_path, pid, 'running', now, now))
            
            conn.execute('UPDATE users SET bots_count = bots_count + 1, last_active = ? WHERE user_id = ?', (now, user_id))
            conn.commit()
            return True
    except:
        return False

def get_user_bots(user_id):
    try:
        with get_db() as conn:
            bots = conn.execute('SELECT * FROM bots WHERE user_id = ? ORDER BY created_at DESC', (user_id,)).fetchall()
            return [dict(bot) for bot in bots]
    except:
        return []

def get_bot(bot_id):
    try:
        with get_db() as conn:
            bot_info = conn.execute('SELECT * FROM bots WHERE id = ?', (bot_id,)).fetchone()
            return dict(bot_info) if bot_info else None
    except:
        return None

def update_bot_status(bot_id, status):
    try:
        with get_db() as conn:
            conn.execute('UPDATE bots SET status = ?, last_active = ? WHERE id = ?', 
                        (status, datetime.now().isoformat(), bot_id))
            conn.commit()
            return True
    except:
        return False

def delete_bot_from_db(bot_id, user_id):
    try:
        with get_db() as conn:
            bot = conn.execute('SELECT * FROM bots WHERE id = ? AND user_id = ?', (bot_id, user_id)).fetchone()
            if not bot:
                return False
            
            BotRunner.stop_bot(bot_id)
            
            if bot['file_path'] and os.path.exists(bot['file_path']):
                os.remove(bot['file_path'])
            
            bot_dir = os.path.join(RUNNING_DIR, bot_id)
            if os.path.exists(bot_dir):
                shutil.rmtree(bot_dir, ignore_errors=True)
            
            conn.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
            conn.execute('UPDATE users SET bots_count = bots_count - 1 WHERE user_id = ?', (user_id,))
            conn.commit()
            return True
    except:
        return False

# ==================== منوی اصلی ====================
def get_main_menu(is_admin=False):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    
    buttons = [
        types.KeyboardButton('🤖 ساخت ربات جدید'),
        types.KeyboardButton('📋 ربات‌های من'),
        types.KeyboardButton('🔄 فعال/غیرفعال کردن'),
        types.KeyboardButton('🗑 حذف ربات'),
        types.KeyboardButton('💰 کیف پول و رفرال'),
        types.KeyboardButton('🎁 اشتراک و تست ۲۴ ساعته'),
        types.KeyboardButton('💳 برداشت وجه'),
        types.KeyboardButton('📚 راهنما'),
        types.KeyboardButton('📦 نصب کتابخانه'),
        types.KeyboardButton('📊 آمار'),
        types.KeyboardButton('📞 پشتیبانی')
    ]
    
    if is_admin:
        buttons.append(types.KeyboardButton('👑 پنل ادمین'))
    
    markup.add(*buttons)
    return markup

# ==================== هندلر استارت ====================
@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    
    referred_by = None
    args = message.text.split()
    if len(args) > 1:
        ref_code = args[1]
        try:
            with get_db() as conn:
                referrer = conn.execute('SELECT user_id FROM users WHERE referral_code = ?', (ref_code,)).fetchone()
                if referrer and referrer['user_id'] != user_id:
                    referred_by = referrer['user_id']
                    try:
                        bot.send_message(
                            referred_by,
                            f"🎉 یک نفر با لینک رفرال شما وارد شد!\n👤 {first_name}\n🆔 {user_id}"
                        )
                    except:
                        pass
        except:
            pass
    
    create_user(user_id, username, first_name, last_name, referred_by)
    
    user = get_user(user_id) or {'referral_code': '', 'referrals_count': 0, 'verified_referrals': 0}
    referral_link = ReferralManager.get_referral_link(user_id)
    balance = ReferralManager.get_balance(user_id)
    
    is_admin = user_id in ADMIN_IDS
    markup = get_main_menu(is_admin)
    
    welcome_text = (
        f"🚀 به ربات مادر نهایی خوش آمدید {first_name}!\n\n"
        f"👤 آیدی شما: {user_id}\n"
        f"🎁 کد رفرال شما: {user['referral_code']}\n"
        f"🔗 لینک دعوت: {referral_link}\n\n"
        f"💰 موجودی کیف پول: {balance:,} تومان\n\n"
        f"💡 هر خرید از لینک شما = ۷٪ پورسانت\n"
        f"🎁 تست ۲۴ ساعته رایگان (فقط یک بار)\n"
        f"📤 برای ساخت ربات از گزینه «ساخت ربات جدید» استفاده کنید"
    )
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

# ==================== اشتراک و تست ۲۴ ساعته ====================
@bot.message_handler(func=lambda m: m.text == '🎁 اشتراک و تست ۲۴ ساعته')
def subscription_menu(message):
    user_id = message.from_user.id
    
    has_sub = SubscriptionManager.has_active_subscription(user_id)
    trial_active = SubscriptionManager.is_trial_active(user_id)
    can_trial, trial_msg = SubscriptionManager.can_use_trial(user_id)
    
    text = f"🎁 **مدیریت اشتراک و تست**\n\n"
    text += f"📊 وضعیت فعلی:\n"
    text += f"{'✅ اشتراک فعال' if has_sub else '❌ بدون اشتراک فعال'}\n"
    text += f"{'✅ تست ۲۴ ساعته فعال' if trial_active else '❌ تست فعال نیست'}\n\n"
    text += f"💰 **قیمت اشتراک:**\n"
    text += f"• ماهانه: {PRICE_PER_MONTH:,} تومان\n"
    text += f"• سه ماهه: {PRICE_3_MONTHS:,} تومان (تخفیف ویژه)\n\n"
    text += f"🎁 **تست رایگان ۲۴ ساعته:**\n"
    text += f"• بدون پرداخت هزینه\n"
    text += f"• فقط یک بار قابل استفاده\n"
    text += f"• بعد از ۲۴ ساعت ربات متوقف می‌شود\n"
    text += f"• {trial_msg}\n\n"
    text += f"💳 شماره کارت: `{CARD_NUMBER}`\n"
    text += f"🏦 به نام: {CARD_HOLDER}"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💰 خرید ماهانه", callback_data="buy_monthly"),
        types.InlineKeyboardButton("💰 خرید سه ماهه", callback_data="buy_3months")
    )
    
    if can_trial and not trial_active:
        markup.add(types.InlineKeyboardButton("🎁 فعال‌سازی تست ۲۴ ساعته", callback_data="activate_trial"))
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ['buy_monthly', 'buy_3months'])
def buy_subscription(call):
    if call.data == 'buy_monthly':
        amount = PRICE_PER_MONTH
        plan = 'monthly'
    else:
        amount = PRICE_3_MONTHS
        plan = '3months'
    
    text = (
        f"💰 **خرید اشتراک {plan}**\n\n"
        f"مبلغ: {amount:,} تومان\n"
        f"شماره کارت: `{CARD_NUMBER}`\n"
        f"به نام: {CARD_HOLDER}\n\n"
        f"📸 پس از واریز، تصویر فیش را همراه با ذکر نوع اشتراک ارسال کنید\n"
        f"💡 مثال کپشن: خرید اشتراک {plan}\n\n"
        f"🆔 کد پیگیری شما: {hashlib.md5(f'{call.from_user.id}_{time.time()}'.encode()).hexdigest()[:8].upper()}"
    )
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == 'activate_trial')
def activate_trial(call):
    user_id = call.from_user.id
    
    can_trial, msg = SubscriptionManager.can_use_trial(user_id)
    if not can_trial:
        bot.answer_callback_query(call.id, msg)
        return
    
    if SubscriptionManager.is_trial_active(user_id):
        bot.answer_callback_query(call.id, "❌ تست ۲۴ ساعته در حال حاضر فعال است!")
        return
    
    SubscriptionManager.activate_trial(user_id)
    
    bot.edit_message_text(
        f"🎁 **تست ۲۴ ساعته فعال شد!**\n\n"
        f"✅ می‌توانید یک ربات بسازید\n"
        f"⏰ زمان باقی‌مانده: {TRIAL_HOURS} ساعت\n"
        f"💡 برای استفاده دائمی، اشتراک تهیه کنید\n\n"
        f"🤖 از گزینه «ساخت ربات جدید» استفاده کنید.",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown"
    )

# ==================== کیف پول و رفرال ====================
@bot.message_handler(func=lambda m: m.text == '💰 کیف پول و رفرال')
def wallet_ref(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        bot.send_message(message.chat.id, "❌ لطفاً /start را بزنید")
        return
    
    referral_link = ReferralManager.get_referral_link(user_id)
    balance = ReferralManager.get_balance(user_id)
    
    # دریافت کل کمیسیون‌ها
    with get_db() as conn:
        commissions = conn.execute('SELECT SUM(amount) as total FROM commissions WHERE user_id = ?', (user_id,)).fetchone()
        total_commission = commissions['total'] if commissions['total'] else 0
    
    text = f"💰 **کیف پول و سیستم رفرال**\n\n"
    text += f"👤 کاربر: {user['first_name']}\n"
    text += f"🆔 آیدی: {user_id}\n\n"
    text += f"💳 **موجودی قابل برداشت:** {balance:,} تومان\n"
    text += f"📊 **کل پورسانت دریافتی:** {total_commission:,} تومان\n\n"
    text += f"🎁 **لینک رفرال شما:**\n`{referral_link}`\n\n"
    text += f"📊 **آمار رفرال:**\n"
    text += f"• کلیک‌ها: {user['referrals_count']}\n"
    text += f"• خریدهای موفق: {user['verified_referrals']}\n\n"
    text += f"💰 **پورسانت:**\n"
    text += f"• هر خرید از لینک شما = {REFERRAL_COMMISSION_PERCENT}% به کیف پول شما\n"
    text += f"• پورسانت بلافاصله بعد از خرید واریز می‌شود\n\n"
    text += f"💡 هر ۵ خرید موفق = ۱ ربات اضافه"
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# ==================== برداشت وجه ====================
@bot.message_handler(func=lambda m: m.text == '💳 برداشت وجه')
def withdraw_menu(message):
    user_id = message.from_user.id
    balance = ReferralManager.get_balance(user_id)
    
    text = (
        f"💳 **برداشت وجه**\n\n"
        f"💰 موجودی قابل برداشت: {balance:,} تومان\n"
        f"📌 حداقل مبلغ برداشت: {MIN_WITHDRAW_AMOUNT:,} تومان\n\n"
        f"⚠️ لطفاً مبلغ و شماره کارت خود را به صورت زیر ارسال کنید:\n\n"
        f"`مبلغ|شماره کارت`\n\n"
        f"مثال: `2000000|6037991234567890`"
    )
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")
    bot.register_next_step_handler(message, process_withdraw)

def process_withdraw(message):
    user_id = message.from_user.id
    
    try:
        parts = message.text.split('|')
        if len(parts) != 2:
            bot.reply_to(message, "❌ فرمت صحیح نیست! مثال: `2000000|6037991234567890`", parse_mode="Markdown")
            return
        
        amount = int(parts[0].strip())
        card_number = parts[1].strip()
        
        success, msg = WithdrawManager.request_withdraw(user_id, amount, card_number)
        bot.reply_to(message, msg)
        
    except ValueError:
        bot.reply_to(message, "❌ مبلغ باید عدد باشد!")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")

# ==================== فیش واریزی (اصلاح شده با پلن) ====================
@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    
    # تشخیص پلن از کپشن
    plan_type = 'monthly'
    amount = PRICE_PER_MONTH
    if message.caption:
        caption_lower = message.caption.lower()
        if 'سه ماهه' in caption_lower or '3ماه' in caption_lower or '3month' in caption_lower:
            plan_type = '3months'
            amount = PRICE_3_MONTHS
    
    try:
        with get_db() as conn:
            existing = conn.execute('''
                SELECT id FROM receipts 
                WHERE user_id = ? AND status = 'pending'
            ''', (user_id,)).fetchone()
            
            if existing:
                bot.reply_to(message, "⏳ شما یک فیش در انتظار بررسی دارید. لطفاً صبر کنید.")
                return
    except:
        pass
    
    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    payment_code = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:8].upper()
    receipt_path = os.path.join(RECEIPTS_DIR, f"{user_id}_{payment_code}.jpg")
    
    with open(receipt_path, 'wb') as f:
        f.write(downloaded_file)
    
    with get_db() as conn:
        conn.execute('''
            INSERT INTO receipts (user_id, amount, plan_type, receipt_path, created_at, payment_code)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, amount, plan_type, receipt_path, datetime.now().isoformat(), payment_code))
        conn.commit()
    
    bot.reply_to(
        message,
        f"✅ فیش شما دریافت شد!\n\n"
        f"💰 مبلغ: {amount:,} تومان\n"
        f"📋 نوع اشتراک: {plan_type}\n"
        f"🆔 کد پیگیری: {payment_code}\n\n"
        f"⏳ پس از بررسی توسط ادمین، اشتراک شما فعال می‌شود."
    )
    
    for admin_id in ADMIN_IDS:
        try:
            bot.send_photo(
                admin_id,
                photo=open(receipt_path, 'rb'),
                caption=f"📸 **فیش جدید**\n"
                       f"👤 کاربر: {user_id}\n"
                       f"💰 مبلغ: {amount:,} تومان\n"
                       f"📋 نوع: {plan_type}\n"
                       f"🆔 کد: {payment_code}\n"
                       f"👤 نام: {message.from_user.first_name}",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"خطا در ارسال فیش به ادمین: {e}")

# ==================== ساخت ربات جدید ====================
@bot.message_handler(func=lambda m: m.text == '🤖 ساخت ربات جدید')
def new_bot(message):
    user_id = message.from_user.id
    
    can_create, reason = SubscriptionManager.can_create_bot(user_id)
    
    if not can_create:
        text = (
            f"❌ **شما دسترسی به ساخت ربات ندارید!**\n\n"
            f"برای ساخت ربات می‌توانید:\n\n"
            f"1️⃣ **فعال‌سازی تست ۲۴ ساعته (رایگان)**\n"
            f"   • فقط یک بار قابل استفاده\n"
            f"   • از قسمت «اشتراک و تست ۲۴ ساعته» فعال کنید\n\n"
            f"2️⃣ **خرید اشتراک**\n"
            f"   • ماهانه: {PRICE_PER_MONTH:,} تومان\n"
            f"   • سه ماهه: {PRICE_3_MONTHS:,} تومان\n\n"
            f"💳 شماره کارت: `{CARD_NUMBER}`\n"
            f"🏦 به نام: {CARD_HOLDER}"
        )
        bot.send_message(message.chat.id, text, parse_mode="Markdown")
        return
    
    text = (
        f"🤖 **ساخت ربات جدید**\n\n"
        f"کاربر گرامی، از اینکه ما را انتخاب کردید متشکرم!\n\n"
        f"📤 **مراحل ساخت ربات:**\n"
        f"1️⃣ فایل `.py` یا `.zip` خود را ارسال کنید\n"
        f"2️⃣ توکن ربات باید داخل کد باشد\n"
        f"3️⃣ حداکثر حجم: ۵۰ مگابایت\n"
        f"4️⃣ در صورت وجود چند فایل، آنها را zip کنید\n\n"
        f"✅ **نوع دسترسی:** {reason}\n"
        f"🔒 کد شما از نظر امنیت بررسی می‌شود"
    )
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# ==================== آپلود و اجرای ربات ====================
@bot.message_handler(content_types=['document'])
def handle_build_file(message):
    user_id = message.from_user.id
    
    can_create, reason = SubscriptionManager.can_create_bot(user_id)
    if not can_create:
        bot.reply_to(message, "❌ ابتدا اشتراک خود را فعال کنید یا تست ۲۴ ساعته را فعال نمایید!")
        return
    
    file_name = message.document.file_name
    
    if not (file_name.endswith('.py') or file_name.endswith('.zip')):
        bot.reply_to(message, "❌ فقط فایل‌های `.py` یا `.zip` مجاز هستند!")
        return
    
    if message.document.file_size > 50 * 1024 * 1024:
        bot.reply_to(message, "❌ حجم فایل نباید بیشتر از ۵۰ مگابایت باشد!")
        return
    
    status_msg = bot.reply_to(message, "🔄 در حال پردازش فایل...")
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        file_path = save_uploaded_file(user_id, downloaded_file, file_name)
        if not file_path:
            bot.edit_message_text("❌ خطا در ذخیره فایل", message.chat.id, status_msg.message_id)
            return
        
        main_code = ""
        
        if file_name.endswith('.zip'):
            extract_dir = os.path.join(FILES_DIR, str(user_id), f"extract_{int(time.time())}")
            os.makedirs(extract_dir, exist_ok=True)
            
            py_files = extract_files_from_zip(file_path, extract_dir)
            for pf in py_files:
                if pf['name'] in ['bot.py', 'main.py', 'run.py', '__init__.py']:
                    main_code = pf['content']
                    break
            
            if not main_code and py_files:
                main_code = py_files[0]['content']
            
            shutil.rmtree(extract_dir, ignore_errors=True)
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                main_code = f.read()
        
        if not main_code:
            bot.edit_message_text("❌ هیچ فایل پایتونی پیدا نشد!", message.chat.id, status_msg.message_id)
            return
        
        # بررسی امنیت
        is_safe, errors = SecurityManager.validate_code(main_code)
        if not is_safe:
            bot.edit_message_text(
                f"❌ **کد شما از نظر امنیتی مشکل دارد!**\n\n⚠️ خطاها:\n" + "\n".join(errors),
                message.chat.id,
                status_msg.message_id,
                parse_mode="Markdown"
            )
            return
        
        token = extract_token_from_code(main_code)
        if not token:
            bot.edit_message_text("❌ توکن در کد پیدا نشد!", message.chat.id, status_msg.message_id)
            return
        
        # بررسی توکن
        try:
            response = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
            if response.status_code != 200:
                bot.edit_message_text("❌ توکن معتبر نیست!", message.chat.id, status_msg.message_id)
                return
            bot_info = response.json()['result']
            bot_name = bot_info['first_name']
            bot_username = bot_info['username']
        except Exception as e:
            bot.edit_message_text(f"❌ خطا در بررسی توکن: {str(e)}", message.chat.id, status_msg.message_id)
            return
        
        bot.edit_message_text("⚡ در حال اجرای ربات...", message.chat.id, status_msg.message_id)
        
        # اجرا
        bot_id = hashlib.md5(f"{user_id}{token}{time.time()}".encode()).hexdigest()[:10]
        result = BotRunner.run_bot(bot_id, main_code, token)
        
        if result['success']:
            add_bot_to_db(user_id, bot_id, token, bot_name, bot_username, file_path, result.get('pid'))
            
            reply = f"✅ **ربات با موفقیت ساخته شد!** 🎉\n\n"
            reply += f"🤖 نام: {bot_name}\n"
            reply += f"🔗 لینک: https://t.me/{bot_username}\n"
            reply += f"🆔 آیدی: `{bot_id}`\n"
            reply += f"🔄 وضعیت: در حال اجرا\n\n"
            
            if reason == 'trial':
                with get_db() as conn:
                    conn.execute('UPDATE trial_usage SET bot_id = ? WHERE user_id = ?', (bot_id, user_id))
                    conn.commit()
                reply += f"⏰ **تست ۲۴ ساعته فعال است**\n"
                reply += f"⏳ بعد از {TRIAL_HOURS} ساعت ربات متوقف می‌شود\n"
                reply += f"💡 برای ادامه، اشتراک تهیه کنید"
            
            bot.edit_message_text(reply, message.chat.id, status_msg.message_id, parse_mode="Markdown")
        else:
            bot.edit_message_text(f"❌ خطا در اجرا:\n{result.get('error', 'خطای ناشناخته')}", message.chat.id, status_msg.message_id)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        bot.edit_message_text(f"❌ خطا: {str(e)}", message.chat.id, status_msg.message_id)

# ==================== ربات‌های من ====================
@bot.message_handler(func=lambda m: m.text == '📋 ربات‌های من')
def my_bots(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما رباتی ندارید!\nبرای ساخت ربات از گزینه «ساخت ربات جدید» استفاده کنید")
        return
    
    for b in bots[:10]:
        status_emoji = "🟢" if b['status'] == 'running' else "🔴"
        status_text = "در حال اجرا" if b['status'] == 'running' else "متوقف"
        
        text = f"{status_emoji} **{b['name']}**\n"
        text += f"🔗 https://t.me/{b['username']}\n"
        text += f"🆔 `{b['id']}`\n"
        text += f"📊 وضعیت: {status_text}\n"
        text += f"📅 {b['created_at'][:10]}"
        
        bot.send_message(message.chat.id, text, parse_mode="Markdown")

# ==================== فعال/غیرفعال کردن ====================
@bot.message_handler(func=lambda m: m.text == '🔄 فعال/غیرفعال کردن')
def toggle_prompt(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما رباتی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        status = "🟢" if b['status'] == 'running' else "🔴"
        markup.add(types.InlineKeyboardButton(f"{status} {b['name']}", callback_data=f"toggle_{b['id']}"))
    
    bot.send_message(message.chat.id, "🔄 ربات مورد نظر را انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_'))
def toggle_bot(call):
    bot_id = call.data.replace('toggle_', '')
    user_id = call.from_user.id
    
    with get_db() as conn:
        bot_info = conn.execute('SELECT * FROM bots WHERE id = ? AND user_id = ?', (bot_id, user_id)).fetchone()
        if not bot_info:
            bot.answer_callback_query(call.id, "❌ ربات پیدا نشد!")
            return
        
        if bot_info['status'] == 'running':
            BotRunner.stop_bot(bot_id)
            update_bot_status(bot_id, 'stopped')
            bot.answer_callback_query(call.id, "✅ ربات متوقف شد")
            bot.edit_message_text(f"✅ ربات {bot_info['name']} متوقف شد.", call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "❌ ربات در حال حاضر متوقف است")

# ==================== حذف ربات ====================
@bot.message_handler(func=lambda m: m.text == '🗑 حذف ربات')
def delete_prompt(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما رباتی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        markup.add(types.InlineKeyboardButton(f"🗑 {b['name']}", callback_data=f"delete_{b['id']}"))
    
    bot.send_message(message.chat.id, "⚠️ ربات مورد نظر را انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
def confirm_delete(call):
    bot_id = call.data.replace('delete_', '')
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ بله", callback_data=f"confirm_del_{bot_id}"),
        types.InlineKeyboardButton("❌ خیر", callback_data="cancel_del")
    )
    bot.edit_message_text("⚠️ آیا از حذف این ربات اطمینان دارید؟", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_del_'))
def do_delete(call):
    bot_id = call.data.replace('confirm_del_', '')
    user_id = call.from_user.id
    
    if delete_bot_from_db(bot_id, user_id):
        bot.edit_message_text("✅ ربات با موفقیت حذف شد.", call.message.chat.id, call.message.message_id)
    else:
        bot.edit_message_text("❌ خطا در حذف ربات!", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == 'cancel_del')
def cancel_delete(call):
    bot.edit_message_text("❌ عملیات حذف لغو شد.", call.message.chat.id, call.message.message_id)

# ==================== راهنما ====================
@bot.message_handler(func=lambda m: m.text == '📚 راهنما')
def guide(message):
    bot.send_message(message.chat.id, GUIDE_TEXT, parse_mode="Markdown")

# ==================== نصب کتابخانه ====================
@bot.message_handler(func=lambda m: m.text == '📦 نصب کتابخانه')
def install_library_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    libs = [
        ('requests', 'requests'), ('numpy', 'numpy'), ('pandas', 'pandas'),
        ('flask', 'flask'), ('pyTelegramBotAPI', 'pyTelegramBotAPI'),
        ('aiogram', 'aiogram'), ('jdatetime', 'jdatetime'), ('🔧 دستی', 'custom')
    ]
    for name, data in libs:
        markup.add(types.InlineKeyboardButton(name, callback_data=f"lib_{data}"))
    
    bot.send_message(message.chat.id, "📦 کتابخانه مورد نظر را انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lib_'))
def install_library_callback(call):
    lib = call.data.replace('lib_', '')
    
    if lib == 'custom':
        msg = bot.send_message(call.message.chat.id, "📦 نام کتابخانه را وارد کنید:")
        bot.register_next_step_handler(msg, install_custom_library)
        return
    
    bot.answer_callback_query(call.id, f"در حال نصب {lib}...")
    
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "install", lib], capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            bot.send_message(call.message.chat.id, f"✅ کتابخانه {lib} با موفقیت نصب شد.")
        else:
            bot.send_message(call.message.chat.id, f"❌ خطا در نصب:\n{result.stderr[:200]}")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ خطا: {str(e)}")

def install_custom_library(message):
    lib = message.text.strip()
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "install", lib], capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            bot.send_message(message.chat.id, f"✅ کتابخانه {lib} با موفقیت نصب شد.")
        else:
            bot.send_message(message.chat.id, f"❌ خطا در نصب:\n{result.stderr[:200]}")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطا: {str(e)}")

# ==================== آمار ====================
@bot.message_handler(func=lambda m: m.text == '📊 آمار')
def stats(message):
    try:
        with get_db() as conn:
            total_users = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
            total_bots = conn.execute('SELECT COUNT(*) FROM bots').fetchone()[0]
            running_bots = conn.execute('SELECT COUNT(*) FROM bots WHERE status = "running"').fetchone()[0]
            total_payments = conn.execute('SELECT COUNT(*) FROM receipts WHERE status = "approved"').fetchone()[0]
            total_withdraw = conn.execute('SELECT SUM(amount) FROM withdraw_requests WHERE status = "pending"').fetchone()[0] or 0
            trial_users = conn.execute('SELECT COUNT(*) FROM trial_usage WHERE is_active = 1').fetchone()[0]
        
        text = f"📊 **آمار کلی**\n\n"
        text += f"👥 کل کاربران: {total_users}\n"
        text += f"🤖 کل ربات‌ها: {total_bots}\n"
        text += f"🟢 فعال: {running_bots}\n"
        text += f"💰 پرداخت‌ها: {total_payments}\n"
        text += f"🎁 تست فعال: {trial_users}\n"
        text += f"💳 درخواست برداشت: {total_withdraw:,} تومان"
        
        bot.send_message(message.chat.id, text, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, f"📊 آمار در دسترس نیست\nخطا: {e}")

# ==================== پشتیبانی ====================
@bot.message_handler(func=lambda m: m.text == '📞 پشتیبانی')
def support(message):
    bot.send_message(message.chat.id, "📞 **پشتیبانی:** @shahraghee13", parse_mode="Markdown")

# ==================== پنل ادمین کامل ====================
@bot.message_handler(func=lambda m: m.text == '👑 پنل ادمین')
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ شما دسترسی ادمین ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📸 فیش‌ها", callback_data="admin_receipts"),
        types.InlineKeyboardButton("👥 کاربران", callback_data="admin_users"),
        types.InlineKeyboardButton("📊 آمار کامل", callback_data="admin_stats"),
        types.InlineKeyboardButton("💰 تایید پرداخت مستقیم", callback_data="admin_approve"),
        types.InlineKeyboardButton("💳 تغییر قیمت", callback_data="admin_change_price"),
        types.InlineKeyboardButton("🏧 تغییر شماره کارت", callback_data="admin_change_card"),
        types.InlineKeyboardButton("🖨 تغییر متن راهنما", callback_data="admin_change_guide"),
        types.InlineKeyboardButton("🗑 حذف ربات کاربران", callback_data="admin_delete_user_bot"),
        types.InlineKeyboardButton("💰 لیست برداشت‌ها", callback_data="admin_withdraw_list"),
        types.InlineKeyboardButton("📊 گزارش کمیسیون‌ها", callback_data="admin_commissions"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    bot.send_message(message.chat.id, "👑 **پنل مدیریت پیشرفته**", parse_mode="Markdown", reply_markup=markup)

# ==================== هندلرهای پنل ادمین ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_receipts")
def admin_receipts(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        receipts = conn.execute('SELECT * FROM receipts WHERE status = "pending" ORDER BY created_at DESC').fetchall()
    
    if not receipts:
        bot.send_message(call.message.chat.id, "📸 هیچ فیش در انتظاری نیست")
        return
    
    for r in receipts:
        text = f"📸 **فیش شماره {r['id']}**\n"
        text += f"👤 کاربر: {r['user_id']}\n"
        text += f"💰 مبلغ: {r['amount']:,} تومان\n"
        text += f"📋 نوع: {r['plan_type']}\n"
        text += f"🆔 کد: `{r['payment_code']}`\n"
        text += f"📅 تاریخ: {r['created_at'][:19]}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید و فعال‌سازی", callback_data=f"approve_receipt_{r['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"reject_receipt_{r['id']}")
        )
        
        if os.path.exists(r['receipt_path']):
            with open(r['receipt_path'], 'rb') as f:
                bot.send_photo(call.message.chat.id, f, caption=text, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_receipt_'))
def approve_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    receipt_id = int(call.data.replace('approve_receipt_', ''))
    
    with get_db() as conn:
        receipt = conn.execute('SELECT * FROM receipts WHERE id = ?', (receipt_id,)).fetchone()
        if receipt:
            # بروزرسانی وضعیت فیش
            conn.execute('''
                UPDATE receipts SET status = "approved", reviewed_at = ?, reviewed_by = ? 
                WHERE id = ?
            ''', (datetime.now().isoformat(), call.from_user.id, receipt_id))
            
            # فعال کردن اشتراک
            SubscriptionManager.activate_subscription(receipt['user_id'], receipt['plan_type'], receipt['amount'])
            
            # پرداخت کمیسیون به رفرال دهنده
            ReferralManager.process_purchase_commission(receipt['user_id'], receipt['amount'])
            
            conn.commit()
            
            # ارسال پیام به کاربر
            try:
                bot.send_message(
                    receipt['user_id'],
                    f"✅ **اشتراک شما فعال شد!**\n\n"
                    f"💰 مبلغ: {receipt['amount']:,} تومان\n"
                    f"📋 نوع: {receipt['plan_type']}\n"
                    f"🎉 می‌توانید ربات خود را بسازید.\n\n"
                    f"🤖 از گزینه «ساخت ربات جدید» استفاده کنید.",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"خطا در ارسال پیام به کاربر: {e}")
    
    bot.answer_callback_query(call.id, "✅ فیش تایید و اشتراک فعال شد!")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_receipt_'))
def reject_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    receipt_id = int(call.data.replace('reject_receipt_', ''))
    
    with get_db() as conn:
        receipt = conn.execute('SELECT * FROM receipts WHERE id = ?', (receipt_id,)).fetchone()
        if receipt:
            conn.execute('''
                UPDATE receipts SET status = "rejected", reviewed_at = ?, reviewed_by = ? 
                WHERE id = ?
            ''', (datetime.now().isoformat(), call.from_user.id, receipt_id))
            conn.commit()
            
            try:
                bot.send_message(
                    receipt['user_id'],
                    f"❌ **فیش شما رد شد**\n\n"
                    f"دلیل احتمالی:\n"
                    f"• تصویر نامشخص\n"
                    f"• مبلغ اشتباه\n"
                    f"• اطلاعات ناقص\n\n"
                    f"لطفاً با پشتیبانی تماس بگیرید: @shahraghee13"
                )
            except:
                pass
    
    bot.answer_callback_query(call.id, "❌ فیش رد شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_change_price")
def admin_change_price(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "💰 **تغییر قیمت‌ها**\n\nلطفاً قیمت جدید ماهانه را وارد کنید (تومان):\nمثال: 2500000")
    bot.register_next_step_handler(msg, process_price_change)

def process_price_change(message):
    global PRICE_PER_MONTH, PRICE_3_MONTHS
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        new_price = int(message.text.strip())
        PRICE_PER_MONTH = new_price
        PRICE_3_MONTHS = int(new_price * 2.5)
        bot.reply_to(message, f"✅ قیمت با موفقیت تغییر کرد!\n💰 ماهانه: {PRICE_PER_MONTH:,} تومان\n💰 سه ماهه: {PRICE_3_MONTHS:,} تومان")
    except:
        bot.reply_to(message, "❌ عدد معتبر وارد کنید!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_change_card")
def admin_change_card(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "🏧 **تغییر شماره کارت**\n\nلطفاً شماره کارت جدید را وارد کنید:\n(۱۶ رقم)")
    bot.register_next_step_handler(msg, process_card_change)

def process_card_change(message):
    global CARD_NUMBER
    if message.from_user.id not in ADMIN_IDS:
        return
    
    CARD_NUMBER = message.text.strip()
    bot.reply_to(message, f"✅ شماره کارت با موفقیت تغییر کرد!\n🏧 شماره جدید: {CARD_NUMBER}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_change_guide")
def admin_change_guide(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "📝 **تغییر متن راهنما**\n\nلطفاً متن جدید راهنما را ارسال کنید:")
    bot.register_next_step_handler(msg, process_guide_change)

def process_guide_change(message):
    global GUIDE_TEXT
    if message.from_user.id not in ADMIN_IDS:
        return
    
    GUIDE_TEXT = message.text
    bot.reply_to(message, "✅ متن راهنما با موفقیت تغییر کرد!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_delete_user_bot")
def admin_delete_user_bot(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        bots = conn.execute('''
            SELECT b.id, b.name, b.username, u.user_id, u.first_name 
            FROM bots b JOIN users u ON b.user_id = u.user_id
        ''').fetchall()
    
    if not bots:
        bot.send_message(call.message.chat.id, "📋 هیچ رباتی وجود ندارد")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        markup.add(types.InlineKeyboardButton(f"🗑 {b['name']} (کاربر: {b['first_name']})", callback_data=f"admin_del_bot_{b['id']}"))
    
    bot.send_message(call.message.chat.id, "🗑 ربات مورد نظر برای حذف را انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_del_bot_'))
def admin_confirm_delete_bot(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    bot_id = call.data.replace('admin_del_bot_', '')
    
    with get_db() as conn:
        bot_info = conn.execute('SELECT * FROM bots WHERE id = ?', (bot_id,)).fetchone()
        if bot_info:
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("✅ بله", callback_data=f"admin_confirm_del_{bot_id}"),
                types.InlineKeyboardButton("❌ خیر", callback_data="admin_cancel_del")
            )
            bot.edit_message_text(
                f"⚠️ آیا از حذف ربات **{bot_info['name']}** (کاربر: {bot_info['user_id']}) اطمینان دارید؟",
                call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown"
            )

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_confirm_del_'))
def admin_do_delete_bot(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    bot_id = call.data.replace('admin_confirm_del_', '')
    
    with get_db() as conn:
        bot_info = conn.execute('SELECT user_id FROM bots WHERE id = ?', (bot_id,)).fetchone()
        if bot_info:
            BotRunner.stop_bot(bot_id)
            conn.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
            conn.execute('UPDATE users SET bots_count = bots_count - 1 WHERE user_id = ?', (bot_info['user_id'],))
            conn.commit()
    
    bot.edit_message_text("✅ ربات با موفقیت حذف شد.", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_withdraw_list")
def admin_withdraw_list(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    withdraws = WithdrawManager.get_withdraw_requests('pending')
    
    if not withdraws:
        bot.send_message(call.message.chat.id, "💰 هیچ درخواست برداشتی وجود ندارد")
        return
    
    for w in withdraws:
        text = f"💰 **درخواست برداشت #{w['id']}**\n"
        text += f"👤 کاربر: {w['user_id']}\n"
        text += f"💰 مبلغ: {w['amount']:,} تومان\n"
        text += f"💳 کارت: `{w['card_number']}`\n"
        text += f"📅 تاریخ: {w['created_at'][:19]}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید واریز", callback_data=f"withdraw_approve_{w['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"withdraw_reject_{w['id']}")
        )
        
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('withdraw_approve_'))
def withdraw_approve(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    withdraw_id = int(call.data.replace('withdraw_approve_', ''))
    success, msg = WithdrawManager.process_withdraw(withdraw_id, 'approve')
    
    bot.answer_callback_query(call.id, "✅ تایید شد" if success else msg)
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('withdraw_reject_'))
def withdraw_reject(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    withdraw_id = int(call.data.replace('withdraw_reject_', ''))
    success, msg = WithdrawManager.process_withdraw(withdraw_id, 'reject')
    
    bot.answer_callback_query(call.id, "❌ رد شد" if success else msg)
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_stats(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        total_users = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        total_bots = conn.execute('SELECT COUNT(*) FROM bots').fetchone()[0]
        running_bots = conn.execute('SELECT COUNT(*) FROM bots WHERE status = "running"').fetchone()[0]
        total_receipts = conn.execute('SELECT COUNT(*) FROM receipts').fetchone()[0]
        pending = conn.execute('SELECT COUNT(*) FROM receipts WHERE status = "pending"').fetchone()[0]
        approved = conn.execute('SELECT COUNT(*) FROM receipts WHERE status = "approved"').fetchone()[0]
        total_amount = conn.execute('SELECT SUM(amount) FROM receipts WHERE status = "approved"').fetchone()[0] or 0
        paid_users = conn.execute('SELECT COUNT(*) FROM users WHERE payment_status = "approved"').fetchone()[0]
        total_withdraw_pending = conn.execute('SELECT SUM(amount) FROM withdraw_requests WHERE status = "pending"').fetchone()[0] or 0
        total_balance = conn.execute('SELECT SUM(balance) FROM users').fetchone()[0] or 0
        trial_active = conn.execute('SELECT COUNT(*) FROM trial_usage WHERE is_active = 1').fetchone()[0]
        total_commissions = conn.execute('SELECT SUM(amount) FROM commissions').fetchone()[0] or 0
    
    text = f"📊 **آمار کامل سیستم**\n\n"
    text += f"👥 کل کاربران: {total_users}\n"
    text += f"✅ پرداخت کرده: {paid_users}\n"
    text += f"🎁 تست فعال: {trial_active}\n"
    text += f"🤖 کل ربات‌ها: {total_bots}\n"
    text += f"🟢 فعال: {running_bots}\n"
    text += f"📸 کل فیش‌ها: {total_receipts}\n"
    text += f"⏳ در انتظار: {pending}\n"
    text += f"✅ تایید شده: {approved}\n"
    text += f"💰 مجموع واریزی: {total_amount:,} تومان\n"
    text += f"💳 درخواست برداشت: {total_withdraw_pending:,} تومان\n"
    text += f"🏦 موجودی کاربران: {total_balance:,} تومان\n"
    text += f"🎁 کل کمیسیون‌ها: {total_commissions:,} تومان"
    
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_users")
def admin_users(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        users = conn.execute('''
            SELECT user_id, username, first_name, bots_count, verified_referrals, 
                   payment_status, balance, created_at
            FROM users ORDER BY created_at DESC LIMIT 20
        ''').fetchall()
    
    text = "👥 **۲۰ کاربر آخر:**\n\n"
    for u in users:
        payment = "✅" if u['payment_status'] == 'approved' else "⏳"
        text += f"{payment} `{u['user_id']}` - {u['first_name']}\n"
        text += f"   🤖 {u['bots_count']} ربات | 🎁 {u['verified_referrals']} رفرال | 💰 {u['balance']:,} تومان\n\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_commissions")
def admin_commissions(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        commissions = conn.execute('''
            SELECT c.*, u.first_name as user_name 
            FROM commissions c 
            JOIN users u ON c.user_id = u.user_id 
            ORDER BY c.created_at DESC LIMIT 30
        ''').fetchall()
    
    if not commissions:
        bot.send_message(call.message.chat.id, "📊 هیچ کمیسیونی ثبت نشده است")
        return
    
    text = "💰 **۳۰ کمیسیون آخر:**\n\n"
    for c in commissions:
        text += f"👤 {c['user_name']} (`{c['user_id']}`)\n"
        text += f"💰 {c['amount']:,} تومان - {c['reason']}\n"
        text += f"📅 {c['created_at'][:10]}\n\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_approve")
def admin_approve_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "💰 **تایید دستی پرداخت**\n\nلطفاً آیدی کاربر را وارد کنید:")
    bot.register_next_step_handler(msg, process_admin_approve)

def process_admin_approve(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        user_id = int(message.text.strip())
        with get_db() as conn:
            conn.execute('UPDATE users SET payment_status = "approved", payment_date = ? WHERE user_id = ?',
                        (datetime.now().isoformat(), user_id))
            conn.commit()
        
        bot.reply_to(message, f"✅ پرداخت کاربر {user_id} تایید شد")
        try:
            bot.send_message(user_id, f"✅ پرداخت شما تایید شد!\nاکنون می‌توانید ربات بسازید.")
        except:
            pass
    except:
        bot.reply_to(message, "❌ آیدی باید عدد باشد")

@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call):
    user_id = call.from_user.id
    is_admin = user_id in ADMIN_IDS
    markup = get_main_menu(is_admin)
    
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "🚀 منوی اصلی:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_cancel_del")
def admin_cancel_del(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== مانیتورینگ تست‌های ۲۴ ساعته ====================
def monitor_trials():
    while True:
        try:
            with get_db() as conn:
                trials = conn.execute('SELECT user_id, bot_id FROM trial_usage WHERE is_active = 1').fetchall()
                for trial in trials:
                    if not SubscriptionManager.is_trial_active(trial['user_id']):
                        if trial['bot_id']:
                            BotRunner.stop_bot(trial['bot_id'])
                            update_bot_status(trial['bot_id'], 'stopped')
                            logger.info(f"تست ۲۴ ساعته کاربر {trial['user_id']} به پایان رسید - ربات {trial['bot_id']} متوقف شد")
                            
                            try:
                                bot.send_message(
                                    trial['user_id'],
                                    f"⏰ **تست ۲۴ ساعته شما به پایان رسید!**\n\n"
                                    f"🤖 ربات شما متوقف شد.\n"
                                    f"💡 برای ادامه استفاده، اشتراک تهیه کنید:\n"
                                    f"• ماهانه: {PRICE_PER_MONTH:,} تومان\n"
                                    f"• سه ماهه: {PRICE_3_MONTHS:,} تومان",
                                    parse_mode="Markdown"
                                )
                            except:
                                pass
            
            time.sleep(1800)  # هر 30 دقیقه چک کن
        except Exception as e:
            logger.error(f"خطا در مانیتورینگ تست‌ها: {e}")
            time.sleep(60)

# شروع ترد مانیتورینگ
monitor_thread = threading.Thread(target=monitor_trials, daemon=True)
monitor_thread.start()

# ==================== اجرا ====================
if __name__ == "__main__":
    print("=" * 70)
    print("🚀 ربات مادر نهایی - نسخه 10.0 نهایی")
    print("=" * 70)
    print(f"✅ ادمین: {ADMIN_IDS}")
    print(f"✅ قیمت ماهانه: {PRICE_PER_MONTH:,} تومان")
    print(f"✅ قیمت سه ماهه: {PRICE_3_MONTHS:,} تومان")
    print(f"✅ حداقل برداشت: {MIN_WITHDRAW_AMOUNT:,} تومان")
    print(f"✅ پورسانت رفرال: {REFERRAL_COMMISSION_PERCENT}%")
    print(f"✅ تست ۲۴ ساعته: فعال")
    print("=" * 70)
    print("ربات در حال اجراست...")
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            logger.error(f"خطا: {e}")
            time.sleep(5)