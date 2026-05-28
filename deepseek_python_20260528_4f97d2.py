#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║     🚀 ربات مادر حرفه‌ای - Enterprise Edition v4.0                           ║
║     ⚡ اشتراک ماهانه | سیستم رفرال قدرتمند | برداشت خودکار                   ║
║     🔒 تست رایگان ۵ دقیقه | مدیریت کامل توسط ادمین                           ║
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
import psutil
import secrets
import logging
import queue
import random
import string
import ast
import tempfile
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from typing import Dict, Any, Optional, List, Tuple

# ==================== تنظیمات پایه ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DIRS = {
    'DB': os.path.join(BASE_DIR, "database"),
    'USERS_DATA': os.path.join(BASE_DIR, "users_data"),
    'FILES': os.path.join(BASE_DIR, "user_files"),
    'RUNNING': os.path.join(BASE_DIR, "running_bots"),
    'LOGS': os.path.join(BASE_DIR, "logs"),
    'RECEIPTS': os.path.join(BASE_DIR, "receipts"),
    'TEMP': os.path.join(BASE_DIR, "temp"),
    'MACHINES': os.path.join(BASE_DIR, "machines"),
    'CACHE': os.path.join(BASE_DIR, "cache"),
    'WITHDRAWALS': os.path.join(BASE_DIR, "withdrawals"),  # درخواست‌های برداشت
}

for dir_path in DIRS.values():
    os.makedirs(dir_path, exist_ok=True)

# ==================== توکن و تنظیمات ====================
BOT_TOKEN = "8541672444:AAF4PBn7-XqiXUgaK0arVajyZfcMWqbxSJ0"
ADMIN_IDS = [327855654]

# تنظیمات قابل تغییر توسط ادمین
class Config:
    def __init__(self):
        self.config_file = os.path.join(BASE_DIR, 'config.json')
        self.load_config()
    
    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.welcome_text = data.get('welcome_text', self.get_default_welcome())
                self.card_number = data.get('card_number', "5892101187322777")
                self.card_holder = data.get('card_holder', "مرتضی نیکخو خنجری")
                self.card_bank = data.get('card_bank', "بانک ملی - سپهر")
                self.subscription_price = data.get('subscription_price', 2000000)
                self.trial_duration = data.get('trial_duration', 5)  # دقیقه
                self.withdrawal_min_amount = data.get('withdrawal_min_amount', 2000000)
        else:
            self.reset_to_default()
    
    def reset_to_default(self):
        self.welcome_text = self.get_default_welcome()
        self.card_number = "5892101187322777"
        self.card_holder = "مرتضی نیکخو خنجری"
        self.card_bank = "بانک ملی - سپهر"
        self.subscription_price = 2000000
        self.trial_duration = 5
        self.withdrawal_min_amount = 2000000
        self.save_config()
    
    def get_default_welcome(self):
        return """🚀 به ربات سازنده ربات تلگرام خوش آمدید!

✨ امکانات:
• ساخت ربات تلگرام با آپلود فایل
• تست رایگان ۵ دقیقه‌ای
• اشتراک ماهانه با قیمت مناسب
• سیستم رفرال و کسب درآمد

📤 برای شروع، فایل ربات خود را ارسال کنید
یا از دکمه 🎁 تست رایگان استفاده کنید"""

    def save_config(self):
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump({
                'welcome_text': self.welcome_text,
                'card_number': self.card_number,
                'card_holder': self.card_holder,
                'card_bank': self.card_bank,
                'subscription_price': self.subscription_price,
                'trial_duration': self.trial_duration,
                'withdrawal_min_amount': self.withdrawal_min_amount
            }, f, ensure_ascii=False, indent=2)

config = Config()

# ==================== تنظیمات خوشه‌ای ====================
CLUSTER_CONFIG = {
    'TOTAL_MACHINES': 50,
    'USERS_PER_MACHINE': 200,
    'MAX_CONCURRENT_BUILDS': 100,
    'RATE_LIMIT': 100,
    'CACHE_TTL': 600,
    'WORKER_THREADS': 1000,
    'DB_POOL_SIZE': 50,
    'MAX_MEMORY_PER_BOT': 512,
    'TOTAL_MEMORY': 165 * 1024,
    'SANDBOX_TIMEOUT': 30,
    'MAX_CODE_SIZE': 10 * 1024 * 1024,
}

# ==================== دیتابیس پیشرفته ====================
class Database:
    def __init__(self):
        self.db_path = os.path.join(DIRS['DB'], 'mother_bot.db')
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        
        # جدول کاربران با فیلدهای اشتراک و رفرال
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                machine_id INTEGER,
                bots_count INTEGER DEFAULT 0,
                max_bots INTEGER DEFAULT 1,
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                referrals_count INTEGER DEFAULT 0,
                verified_referrals INTEGER DEFAULT 0,
                total_earnings INTEGER DEFAULT 0,           -- کل درآمد از رفرال
                withdrawn_amount INTEGER DEFAULT 0,         -- مبلغ برداشت شده
                available_balance INTEGER DEFAULT 0,        -- موجودی قابل برداشت
                subscription_status TEXT DEFAULT 'inactive', -- active, inactive, trial
                subscription_start TIMESTAMP,
                subscription_end TIMESTAMP,
                trial_used INTEGER DEFAULT 0,               -- 0=استفاده نشده, 1=استفاده شده
                trial_start TIMESTAMP,
                trial_end TIMESTAMP,
                payment_status TEXT DEFAULT 'pending',
                created_at TIMESTAMP,
                last_active TIMESTAMP
            )
        ''')
        
        # جدول ربات‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bots (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                token TEXT,
                name TEXT,
                username TEXT,
                file_path TEXT,
                machine_id INTEGER,
                status TEXT DEFAULT 'stopped',
                created_at TIMESTAMP,
                last_active TIMESTAMP,
                is_trial INTEGER DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        # جدول فیش‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                receipt_path TEXT,
                status TEXT DEFAULT 'pending',
                payment_code TEXT UNIQUE,
                reviewed_by INTEGER,
                reviewed_at TIMESTAMP,
                created_at TIMESTAMP
            )
        ''')
        
        # جدول درخواست‌های برداشت
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                card_number TEXT,
                card_holder TEXT,
                status TEXT DEFAULT 'pending',  -- pending, approved, rejected
                reviewed_by INTEGER,
                reviewed_at TIMESTAMP,
                created_at TIMESTAMP,
                transaction_id TEXT UNIQUE
            )
        ''')
        
        # جدول تراکنش‌های رفرال
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referral_earnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                referred_user_id INTEGER,
                amount INTEGER,
                percent INTEGER,
                bot_id TEXT,
                created_at TIMESTAMP,
                status TEXT DEFAULT 'pending'
            )
        ''')
        
        # جدول لاگ‌های سیستم
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT,
                admin_id INTEGER,
                target_user_id INTEGER,
                details TEXT,
                created_at TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def execute(self, query, params=()):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor.fetchall()
        finally:
            conn.close()

db = Database()

# ==================== سیستم اشتراک و رفرال ====================
class SubscriptionManager:
    """مدیریت اشتراک کاربران"""
    
    @staticmethod
    def activate_trial(user_id: int) -> bool:
        """فعال کردن تست رایگان ۵ دقیقه‌ای"""
        user = db.execute('SELECT trial_used, subscription_status FROM users WHERE user_id = ?', (user_id,))
        
        if not user:
            return False
        
        user = user[0]
        
        if user['trial_used'] == 1:
            return False
        
        now = datetime.now()
        trial_end = now + timedelta(minutes=config.trial_duration)
        
        db.execute('''
            UPDATE users 
            SET trial_used = 1, 
                subscription_status = 'trial',
                subscription_start = ?,
                subscription_end = ?,
                trial_start = ?,
                trial_end = ?
            WHERE user_id = ?
        ''', (now.isoformat(), trial_end.isoformat(), now.isoformat(), trial_end.isoformat(), user_id))
        
        # فعال کردن همه ربات‌های کاربر به صورت تستی
        db.execute('''
            UPDATE bots SET status = 'running', is_trial = 1 
            WHERE user_id = ? AND status = 'stopped'
        ''', (user_id,))
        
        return True
    
    @staticmethod
    def activate_subscription(user_id: int, months: int = 1) -> bool:
        """فعال کردن اشتراک ماهانه"""
        now = datetime.now()
        subscription_end = now + timedelta(days=30 * months)
        
        db.execute('''
            UPDATE users 
            SET subscription_status = 'active',
                subscription_start = ?,
                subscription_end = ?,
                payment_status = 'approved'
            WHERE user_id = ?
        ''', (now.isoformat(), subscription_end.isoformat(), user_id))
        
        # فعال کردن ربات‌های کاربر
        db.execute('''
            UPDATE bots SET status = 'running', is_trial = 0 
            WHERE user_id = ? AND status = 'stopped'
        ''', (user_id,))
        
        return True
    
    @staticmethod
    def check_subscription_status(user_id: int) -> Dict:
        """بررسی وضعیت اشتراک کاربر"""
        user = db.execute('''
            SELECT subscription_status, subscription_end, trial_end, trial_used 
            FROM users WHERE user_id = ?
        ''', (user_id,))
        
        if not user:
            return {'has_access': False, 'status': 'no_user', 'days_left': 0}
        
        user = user[0]
        now = datetime.now()
        
        if user['subscription_status'] == 'active':
            end_date = datetime.fromisoformat(user['subscription_end'])
            days_left = (end_date - now).days
            
            if days_left <= 0:
                # اشتراک منقضی شده
                db.execute('UPDATE users SET subscription_status = "expired" WHERE user_id = ?', (user_id,))
                SubscriptionManager.deactivate_user_bots(user_id)
                return {'has_access': False, 'status': 'expired', 'days_left': 0}
            
            # هشدار ۲۴ ساعت قبل از اتمام
            if days_left <= 1:
                return {'has_access': True, 'status': 'expiring_soon', 'days_left': days_left}
            
            return {'has_access': True, 'status': 'active', 'days_left': days_left}
        
        elif user['subscription_status'] == 'trial':
            end_date = datetime.fromisoformat(user['trial_end'])
            minutes_left = int((end_date - now).total_seconds() / 60)
            
            if minutes_left <= 0:
                # تست به اتمام رسیده
                db.execute('UPDATE users SET subscription_status = "inactive" WHERE user_id = ?', (user_id,))
                SubscriptionManager.deactivate_user_bots(user_id)
                return {'has_access': False, 'status': 'trial_expired', 'minutes_left': 0}
            
            return {'has_access': True, 'status': 'trial', 'minutes_left': minutes_left}
        
        return {'has_access': False, 'status': 'inactive', 'days_left': 0}
    
    @staticmethod
    def deactivate_user_bots(user_id: int):
        """غیرفعال کردن همه ربات‌های کاربر"""
        db.execute('UPDATE bots SET status = "stopped" WHERE user_id = ? AND status = "running"', (user_id,))
    
    @staticmethod
    def get_subscription_text(user_id: int) -> str:
        """گرفتن متن وضعیت اشتراک"""
        status = SubscriptionManager.check_subscription_status(user_id)
        
        if status['has_access']:
            if status['status'] == 'active':
                return f"✅ اشتراک فعال\n📅 {status['days_left']} روز باقی مانده"
            elif status['status'] == 'trial':
                return f"🎁 تست رایگان\n⏱️ {status['minutes_left']} دقیقه باقی مانده"
            elif status['status'] == 'expiring_soon':
                return f"⚠️ اشتراک در حال اتمام\n📅 {status['days_left']} روز باقی مانده\nلطفاً تمدید کنید"
        else:
            if status['status'] == 'expired':
                return "❌ اشتراک شما منقضی شده است\nبرای ادامه استفاده، اشتراک تهیه کنید"
            elif status['status'] == 'trial_expired':
                return "❌ زمان تست رایگان شما به اتمام رسید\nبرای ادامه استفاده، اشتراک تهیه کنید"
            else:
                return "❌ اشتراک فعال نیست\nاز دکمه 🎁 تست رایگان یا 💰 خرید اشتراک استفاده کنید"
        
        return "❌ اشتراک فعال نیست"

class ReferralManager:
    """مدیریت سیستم رفرال پیشرفته"""
    
    REFERRAL_PERCENT = 10  # ۱۰ درصد از درآمد کاربر معرفی شده
    
    @staticmethod
    def generate_referral_code(user_id: int) -> str:
        """تولید کد رفرال یکتا"""
        return hashlib.md5(f"{user_id}_{secrets.token_hex(8)}".encode()).hexdigest()[:12]
    
    @staticmethod
    def register_referral(new_user_id: int, referral_code: str) -> bool:
        """ثبت رفرال برای کاربر جدید"""
        # پیدا کردن کاربر معرف
        referrer = db.execute('SELECT user_id FROM users WHERE referral_code = ?', (referral_code,))
        
        if not referrer:
            return False
        
        referrer_id = referrer[0]['user_id']
        
        # جلوگیری از معرفی خود
        if referrer_id == new_user_id:
            return False
        
        # بررسی اینکه کاربر قبلاً توسط کسی معرفی نشده
        existing = db.execute('SELECT referred_by FROM users WHERE user_id = ?', (new_user_id,))
        if existing and existing[0]['referred_by']:
            return False
        
        # ثبت معرف
        db.execute('''
            UPDATE users 
            SET referred_by = ?, referrals_count = referrals_count + 1
            WHERE user_id = ?
        ''', (referrer_id, new_user_id))
        
        return True
    
    @staticmethod
    def add_earning(referrer_id: int, referred_user_id: int, amount: int, bot_id: str = None):
        """اضافه کردن درآمد به حساب کاربر معرف"""
        earning_amount = int(amount * ReferralManager.REFERRAL_PERCENT / 100)
        
        # ثبت تراکنش
        db.execute('''
            INSERT INTO referral_earnings (user_id, referred_user_id, amount, percent, bot_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (referrer_id, referred_user_id, earning_amount, ReferralManager.REFERRAL_PERCENT, 
              bot_id, datetime.now().isoformat()))
        
        # به‌روزرسانی موجودی کاربر
        db.execute('''
            UPDATE users 
            SET total_earnings = total_earnings + ?,
                available_balance = available_balance + ?
            WHERE user_id = ?
        ''', (earning_amount, earning_amount, referrer_id))
        
        return earning_amount
    
    @staticmethod
    def get_user_stats(user_id: int) -> Dict:
        """دریافت آمار رفرال کاربر"""
        user = db.execute('''
            SELECT referral_code, referrals_count, verified_referrals, 
                   total_earnings, available_balance, withdrawn_amount
            FROM users WHERE user_id = ?
        ''', (user_id,))
        
        if not user:
            return {}
        
        user = user[0]
        
        # دریافت لیست افراد معرفی شده
        referrals = db.execute('''
            SELECT user_id, first_name, username, created_at
            FROM users WHERE referred_by = ?
        ''', (user_id,))
        
        return {
            'code': user['referral_code'],
            'count': user['referrals_count'],
            'verified': user['verified_referrals'],
            'total_earnings': user['total_earnings'],
            'available_balance': user['available_balance'],
            'withdrawn_amount': user['withdrawn_amount'],
            'referrals_list': [dict(r) for r in referrals]
        }
    
    @staticmethod
    def verify_referral_earning(user_id: int, referred_user_id: int):
        """تأیید درآمد رفرال (زمانی که کاربر معرف شده ربات می‌سازد)"""
        # به‌روزرسانی تعداد تأیید شده‌ها
        db.execute('''
            UPDATE users SET verified_referrals = verified_referrals + 1
            WHERE user_id = ?
        ''', (user_id,))
        
        # به‌روزرسانی وضعیت تراکنش‌های pending
        db.execute('''
            UPDATE referral_earnings SET status = 'approved'
            WHERE user_id = ? AND referred_user_id = ? AND status = 'pending'
        ''', (user_id, referred_user_id))

class WithdrawalManager:
    """مدیریت درخواست‌های برداشت"""
    
    @staticmethod
    def request_withdrawal(user_id: int, amount: int, card_number: str, card_holder: str) -> Dict:
        """ثبت درخواست برداشت"""
        # بررسی موجودی کاربر
        user = db.execute('SELECT available_balance FROM users WHERE user_id = ?', (user_id,))
        
        if not user:
            return {'success': False, 'error': 'کاربر یافت نشد'}
        
        balance = user[0]['available_balance']
        
        if amount < config.withdrawal_min_amount:
            return {'success': False, 'error': f'حداقل مبلغ برداشت {config.withdrawal_min_amount:,} تومان است'}
        
        if amount > balance:
            return {'success': False, 'error': 'موجودی کافی نیست'}
        
        # ایجاد کد تراکنش یکتا
        transaction_id = hashlib.md5(f"{user_id}_{amount}_{time.time()}".encode()).hexdigest()[:12].upper()
        
        # ثبت درخواست
        db.execute('''
            INSERT INTO withdrawals (user_id, amount, card_number, card_holder, transaction_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, amount, card_number, card_holder, transaction_id, datetime.now().isoformat()))
        
        # قفل کردن موجودی (منتظر تأیید ادمین)
        db.execute('''
            UPDATE users SET available_balance = available_balance - ? WHERE user_id = ?
        ''', (amount, user_id))
        
        # لاگ
        db.execute('''
            INSERT INTO system_logs (action, admin_id, target_user_id, details, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', ('withdrawal_request', None, user_id, f"درخواست برداشت {amount:,} تومان", datetime.now().isoformat()))
        
        return {
            'success': True, 
            'transaction_id': transaction_id,
            'amount': amount
        }
    
    @staticmethod
    def approve_withdrawal(withdrawal_id: int, admin_id: int) -> bool:
        """تأیید درخواست برداشت توسط ادمین"""
        withdrawal = db.execute('SELECT user_id, amount FROM withdrawals WHERE id = ?', (withdrawal_id,))
        
        if not withdrawal:
            return False
        
        withdrawal = withdrawal[0]
        
        db.execute('''
            UPDATE withdrawals 
            SET status = 'approved', reviewed_by = ?, reviewed_at = ?
            WHERE id = ?
        ''', (admin_id, datetime.now().isoformat(), withdrawal_id))
        
        db.execute('''
            UPDATE users SET withdrawn_amount = withdrawn_amount + ? WHERE user_id = ?
        ''', (withdrawal['amount'], withdrawal['user_id']))
        
        # لاگ
        db.execute('''
            INSERT INTO system_logs (action, admin_id, target_user_id, details, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', ('withdrawal_approved', admin_id, withdrawal['user_id'], 
              f"برداشت {withdrawal['amount']:,} تومان تأیید شد", datetime.now().isoformat()))
        
        return True
    
    @staticmethod
    def reject_withdrawal(withdrawal_id: int, admin_id: int) -> bool:
        """رد درخواست برداشت و برگشت موجودی"""
        withdrawal = db.execute('SELECT user_id, amount FROM withdrawals WHERE id = ?', (withdrawal_id,))
        
        if not withdrawal:
            return False
        
        withdrawal = withdrawal[0]
        
        db.execute('''
            UPDATE withdrawals 
            SET status = 'rejected', reviewed_by = ?, reviewed_at = ?
            WHERE id = ?
        ''', (admin_id, datetime.now().isoformat(), withdrawal_id))
        
        # برگشت موجودی
        db.execute('''
            UPDATE users SET available_balance = available_balance + ? WHERE user_id = ?
        ''', (withdrawal['amount'], withdrawal['user_id']))
        
        return True
    
    @staticmethod
    def get_pending_withdrawals() -> List:
        """دریافت درخواست‌های برداشت در انتظار"""
        return db.execute('SELECT * FROM withdrawals WHERE status = "pending" ORDER BY created_at')

# ==================== ربات اصلی ====================
bot = telebot.TeleBot(BOT_TOKEN)
bot.delete_webhook()

# ==================== کلاس ماشین (ساده شده) ====================
class SimpleMachine:
    def __init__(self, machine_id: int):
        self.machine_id = machine_id
        self.bots = {}
    
    def run_bot(self, user_id: int, bot_id: str, code: str, token: str) -> Dict:
        # نسخه ساده برای تست
        return {'success': True, 'pid': 12345, 'machine_id': self.machine_id}
    
    def stop_bot(self, bot_id: str) -> bool:
        return True

class ClusterManager:
    def __init__(self):
        self.machines = {i: SimpleMachine(i) for i in range(1, 51)}
    
    def get_user_machine(self, user_id: int):
        return self.machines[1]
    
    def run_bot_on_user_machine(self, user_id: int, bot_id: str, code: str, token: str):
        return self.machines[1].run_bot(user_id, bot_id, code, token)
    
    def stop_bot(self, user_id: int, bot_id: str):
        return self.machines[1].stop_bot(bot_id)
    
    def get_cluster_stats(self):
        return {'total_machines': 50, 'active_machines': 50, 'total_users': 0, 'total_bots': 0, 'available_capacity': 10000, 'machines_detail': []}

cluster_manager = ClusterManager()

# ==================== توابع کمکی ====================
def create_user(user_id: int, username: str, first_name: str, last_name: str, referred_by: str = None):
    """ایجاد کاربر جدید"""
    # بررسی وجود کاربر
    existing = db.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
    if existing:
        return True
    
    referral_code = ReferralManager.generate_referral_code(user_id)
    
    # ثبت رفرال اگر وجود داشته باشد
    referrer_id = None
    if referred_by:
        ref_user = db.execute('SELECT user_id FROM users WHERE referral_code = ?', (referred_by,))
        if ref_user and ref_user[0]['user_id'] != user_id:
            referrer_id = ref_user[0]['user_id']
    
    now = datetime.now().isoformat()
    
    db.execute('''
        INSERT INTO users 
        (user_id, username, first_name, last_name, referral_code, referred_by, created_at, last_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, username, first_name, last_name, referral_code, referrer_id, now, now))
    
    return True

def get_user(user_id: int):
    users = db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    return dict(users[0]) if users else None

# ==================== منوها ====================
def get_main_menu(user_id: int):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    subscription_status = SubscriptionManager.check_subscription_status(user_id)
    
    buttons = [
        types.KeyboardButton("🎁 تست رایگان"),
        types.KeyboardButton("💰 خرید اشتراک"),
        types.KeyboardButton("🤖 ساخت ربات جدید"),
        types.KeyboardButton("📋 ربات‌های من"),
        types.KeyboardButton("🔄 شروع/توقف"),
        types.KeyboardButton("🗑 حذف ربات"),
        types.KeyboardButton("📊 کیف پول و آمار"),
        types.KeyboardButton("🎁 سیستم رفرال"),
        types.KeyboardButton("💸 برداشت وجه"),
        types.KeyboardButton("📚 راهنما"),
        types.KeyboardButton("⚙️ تنظیمات")
    ]
    
    if user_id in ADMIN_IDS:
        buttons.append(types.KeyboardButton("👑 پنل مدیریت"))
    
    markup.add(*buttons)
    return markup

def get_admin_panel():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📸 مدیریت فیش‌ها", callback_data="admin_receipts"),
        types.InlineKeyboardButton("🖥️ وضعیت ماشین‌ها", callback_data="admin_machines"),
        types.InlineKeyboardButton("👥 لیست کاربران", callback_data="admin_users"),
        types.InlineKeyboardButton("📊 آمار پیشرفته", callback_data="admin_stats"),
        types.InlineKeyboardButton("🗑 حذف ربات کاربر", callback_data="admin_delete_bot"),
        types.InlineKeyboardButton("🔧 رفع مشکل ربات", callback_data="admin_fix_bot"),
        types.InlineKeyboardButton("💳 تغییر قیمت", callback_data="admin_change_price"),
        types.InlineKeyboardButton("📝 تغییر متن خوش‌آمدگویی", callback_data="admin_change_welcome"),
        types.InlineKeyboardButton("🏦 تغییر شماره کارت", callback_data="admin_change_card"),
        types.InlineKeyboardButton("💸 درخواست‌های برداشت", callback_data="admin_withdrawals"),
        types.InlineKeyboardButton("📢 پیام همگانی", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("💰 تایید پرداخت مستقیم", callback_data="admin_approve"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    return markup

# ==================== هندلرها ====================

@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    
    # استخراج کد رفرال
    referral_code = None
    args = message.text.split()
    if len(args) > 1:
        referral_code = args[1]
    
    create_user(
        user_id,
        message.from_user.username or "",
        message.from_user.first_name or "",
        message.from_user.last_name or "",
        referral_code
    )
    
    # اختصاص ماشین
    cluster_manager.get_user_machine(user_id)
    
    subscription_text = SubscriptionManager.get_subscription_text(user_id)
    
    text = f"""{config.welcome_text}

━━━━━━━━━━━━━━━
{subscription_text}
━━━━━━━━━━━━━━━

👤 شناسه: `{user_id}`
    """
    
    bot.send_message(message.chat.id, text, reply_markup=get_main_menu(user_id), parse_mode='Markdown')

# ==================== تست رایگان ====================
@bot.message_handler(func=lambda m: m.text == '🎁 تست رایگان')
def free_trial(message):
    user_id = message.from_user.id
    
    user = get_user(user_id)
    if not user:
        bot.send_message(message.chat.id, "❌ لطفاً /start را بزنید")
        return
    
    if user['trial_used'] == 1:
        bot.send_message(message.chat.id, "❌ شما قبلاً از تست رایگان استفاده کرده‌اید.\nبرای ادامه از 💰 خرید اشتراک استفاده کنید.")
        return
    
    if SubscriptionManager.activate_trial(user_id):
        bot.send_message(
            message.chat.id,
            f"✅ تست رایگان {config.trial_duration} دقیقه‌ای فعال شد!\n\n"
            f"⏱️ شما {config.trial_duration} دقیقه فرصت دارید ربات خود را تست کنید.\n"
            f"پس از اتمام زمان، برای ادامه استفاده اشتراک تهیه کنید.\n\n"
            f"📤 حالا فایل ربات خود را ارسال کنید."
        )
    else:
        bot.send_message(message.chat.id, "❌ خطا در فعال‌سازی تست رایگان")

# ==================== خرید اشتراک ====================
@bot.message_handler(func=lambda m: m.text == '💰 خرید اشتراک')
def buy_subscription(message):
    user_id = message.from_user.id
    
    text = f"""
💰 **خرید اشتراک ماهانه**

💳 مبلغ: {config.subscription_price:,} تومان

🏦 اطلاعات واریز:
شماره کارت: `{config.card_number}`
به نام: {config.card_holder}
بانک: {config.card_bank}

📸 **روش اقدام:**
1. مبلغ را به کارت فوق واریز کنید
2. از قسمت 💰 کیف پول و آمار، تصویر فیش را ارسال کنید
3. پس از تأیید، اشتراک شما فعال می‌شود

⏱️ اشتراک شما به مدت ۳۰ روز فعال خواهد بود
    """
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== ساخت ربات ====================
@bot.message_handler(func=lambda m: m.text == '🤖 ساخت ربات جدید')
def new_bot(message):
    user_id = message.from_user.id
    
    # بررسی وضعیت اشتراک
    subscription = SubscriptionManager.check_subscription_status(user_id)
    
    if not subscription['has_access']:
        text = f"""❌ **شما دسترسی به ساخت ربات ندارید!**

{SubscriptionManager.get_subscription_text(user_id)}

🎁 برای تست رایگان از دکمه تست رایگان استفاده کنید
💰 برای خرید اشتراک از دکمه خرید اشتراک استفاده کنید
"""
        bot.send_message(message.chat.id, text, parse_mode='Markdown')
        return
    
    # نمایش زمان باقی مانده
    if subscription['status'] == 'trial':
        time_msg = f"⏱️ زمان باقی مانده تست: {subscription['minutes_left']} دقیقه"
    else:
        time_msg = f"📅 روزهای باقی مانده اشتراک: {subscription['days_left']} روز"
    
    bot.send_message(
        message.chat.id,
        f"📤 **ارسال فایل ربات**\n\n"
        f"✅ دسترسی دارید!\n"
        f"{time_msg}\n\n"
        f"فایل .py یا .zip خود را ارسال کنید.\n"
        f"حداکثر حجم: ۱۰ مگابایت"
    )

# ==================== آپلود فایل ====================
@bot.message_handler(content_types=['document'])
def handle_file(message):
    user_id = message.from_user.id
    
    # بررسی دسترسی
    subscription = SubscriptionManager.check_subscription_status(user_id)
    
    if not subscription['has_access']:
        bot.reply_to(message, "❌ شما دسترسی ندارید. ابتدا تست رایگان یا اشتراک تهیه کنید.")
        return
    
    file_name = message.document.file_name
    
    if not (file_name.endswith('.py') or file_name.endswith('.zip')):
        bot.reply_to(message, "❌ فقط فایل‌های .py یا .zip پشتیبانی می‌شوند")
        return
    
    status_msg = bot.reply_to(message, "🔄 در حال پردازش فایل...")
    
    try:
        # دانلود فایل (ساده شده)
        file_info = bot.get_file(message.document.file_id)
        file_data = bot.download_file(file_info.file_path)
        
        # ذخیره فایل
        user_dir = os.path.join(DIRS['FILES'], str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        file_path = os.path.join(user_dir, f"{int(time.time())}_{file_name}")
        
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        # استخراج توکن (ساده شده)
        token = "TEST_TOKEN_12345"
        
        # ایجاد ربات
        bot_id = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:16]
        
        # اجرا
        result = cluster_manager.run_bot_on_user_machine(user_id, bot_id, "", token)
        
        if result['success']:
            # ذخیره در دیتابیس
            db.execute('''
                INSERT INTO bots (id, user_id, token, name, username, file_path, status, created_at, last_active)
                VALUES (?, ?, ?, ?, ?, ?, 'running', ?, ?)
            ''', (bot_id, user_id, token, "ربات جدید", "new_bot", file_path, 
                  datetime.now().isoformat(), datetime.now().isoformat()))
            
            # اگر کاربر توسط کسی معرفی شده و این اولین رباتش است
            user = get_user(user_id)
            if user and user['referred_by'] and user['bots_count'] == 0:
                # اضافه کردن درآمد به معرف
                ReferralManager.add_earning(user['referred_by'], user_id, config.subscription_price, bot_id)
                ReferralManager.verify_referral_earning(user['referred_by'], user_id)
            
            # به‌روزرسانی آمار کاربر
            db.execute('UPDATE users SET bots_count = bots_count + 1 WHERE user_id = ?', (user_id,))
            
            bot.edit_message_text(f"✅ ربات با موفقیت ساخته شد!\n\n🆔 {bot_id}", 
                                 message.chat.id, status_msg.message_id)
        else:
            bot.edit_message_text("❌ خطا در ساخت ربات", message.chat.id, status_msg.message_id)
            
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)}", message.chat.id, status_msg.message_id)

# ==================== کیف پول و آمار ====================
@bot.message_handler(func=lambda m: m.text == '📊 کیف پول و آمار')
def wallet_stats(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    referral_stats = ReferralManager.get_user_stats(user_id)
    subscription_status = SubscriptionManager.get_subscription_text(user_id)
    
    text = f"""
💰 **کیف پول و آمار شما**

━━━━━━━━━━━━━━━
📊 **وضعیت حساب**
┌─────────────────┐
│ 👤 کاربر: {user['first_name'] or user['username']}
│ 🆔 شناسه: `{user_id}`
│ 🤖 ربات‌ها: {user['bots_count']}
│ 💳 وضعیت پرداخت: {"✅ تأیید" if user['payment_status'] == 'approved' else "⏳ در انتظار"}
└─────────────────┘

━━━━━━━━━━━━━━━
🎁 **سیستم رفرال**
┌─────────────────┐
│ 📊 تعداد معرف‌ها: {referral_stats.get('count', 0)}
│ ✅ معرف‌های فعال: {referral_stats.get('verified', 0)}
│ 💰 کل درآمد: {referral_stats.get('total_earnings', 0):,} تومان
│ 💵 موجودی قابل برداشت: {referral_stats.get('available_balance', 0):,} تومان
│ 💸 برداشت شده: {referral_stats.get('withdrawn_amount', 0):,} تومان
└─────────────────┘

━━━━━━━━━━━━━━━
📅 **اشتراک**
┌─────────────────┐
│ {subscription_status}
└─────────────────┘

🎁 **لینک دعوت شما:**
`https://t.me/{bot.get_me().username}?start={referral_stats.get('code', '')}`

💡 هر نفر که با لینک شما عضو شود و ربات بسازد،
۱۰٪ از درآمد او به حساب شما واریز می‌شود!
    """
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== سیستم رفرال ====================
@bot.message_handler(func=lambda m: m.text == '🎁 سیستم رفرال')
def referral_system(message):
    user_id = message.from_user.id
    referral_stats = ReferralManager.get_user_stats(user_id)
    
    text = f"""
🎁 **سیستم رفرال و کسب درآمد**

📊 **آمار شما:**
• افراد دعوت شده: {referral_stats.get('count', 0)} نفر
• افراد فعال (ساخته‌اند ربات): {referral_stats.get('verified', 0)} نفر
• کل درآمد: {referral_stats.get('total_earnings', 0):,} تومان
• موجودی قابل برداشت: {referral_stats.get('available_balance', 0):,} تومان

💰 **نحوه کسب درآمد:**
هر کاربری که با لینک دعوت شما عضو شود و اشتراک بخرد،
۱۰٪ از مبلغ پرداختی او به حساب شما واریز می‌شود.

🎁 **لینک دعوت شما:**
`https://t.me/{bot.get_me().username}?start={referral_stats.get('code', '')}`

📋 **لیست افراد دعوت شده شما:**
"""
    
    referrals = referral_stats.get('referrals_list', [])
    if referrals:
        for ref in referrals[:10]:
            text += f"\n• {ref['first_name'] or ref['username'] or ref['user_id']}"
    else:
        text += "\n• هنوز کسی دعوت نکرده‌اید"
    
    text += "\n\n💡 هرچه بیشتر دعوت کنید، درآمد بیشتری کسب می‌کنید!"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== برداشت وجه ====================
@bot.message_handler(func=lambda m: m.text == '💸 برداشت وجه')
def withdraw_money(message):
    user_id = message.from_user.id
    referral_stats = ReferralManager.get_user_stats(user_id)
    
    balance = referral_stats.get('available_balance', 0)
    
    if balance < config.withdrawal_min_amount:
        bot.send_message(
            message.chat.id,
            f"❌ موجودی شما برای برداشت کافی نیست!\n\n"
            f"💰 موجودی فعلی: {balance:,} تومان\n"
            f"💰 حداقل مبلغ برداشت: {config.withdrawal_min_amount:,} تومان\n\n"
            f"💡 با دعوت دوستان خود، موجودی خود را افزایش دهید."
        )
        return
    
    msg = bot.send_message(
        message.chat.id,
        f"💰 **فرم برداشت وجه**\n\n"
        f"موجودی قابل برداشت: {balance:,} تومان\n"
        f"حداقل برداشت: {config.withdrawal_min_amount:,} تومان\n\n"
        f"مبلغ مورد نظر خود را به تومان وارد کنید:",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(msg, process_withdrawal_amount)

def process_withdrawal_amount(message):
    user_id = message.from_user.id
    try:
        amount = int(message.text.replace(',', '').replace('تومان', '').strip())
        
        referral_stats = ReferralManager.get_user_stats(user_id)
        balance = referral_stats.get('available_balance', 0)
        
        if amount < config.withdrawal_min_amount:
            bot.send_message(message.chat.id, f"❌ حداقل مبلغ برداشت {config.withdrawal_min_amount:,} تومان است")
            return
        
        if amount > balance:
            bot.send_message(message.chat.id, f"❌ موجودی شما کافی نیست!\nموجودی: {balance:,} تومان")
            return
        
        msg = bot.send_message(
            message.chat.id,
            f"💰 مبلغ {amount:,} تومان\n\n"
            f"لطفاً شماره کارت خود را وارد کنید:",
            parse_mode='Markdown'
        )
        bot.register_next_step_handler(msg, lambda m: process_withdrawal_card(m, amount))
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ لطفاً یک عدد معتبر وارد کنید")

def process_withdrawal_card(message, amount):
    card_number = message.text.replace(' ', '').replace('-', '').strip()
    
    if not card_number.isdigit() or len(card_number) < 16:
        bot.send_message(message.chat.id, "❌ شماره کارت نامعتبر است. لطفاً مجدداً تلاش کنید.")
        return
    
    msg = bot.send_message(
        message.chat.id,
        f"💰 مبلغ: {amount:,} تومان\n"
        f"🏦 شماره کارت: {card_number}\n\n"
        f"لطفاً نام صاحب حساب را وارد کنید:",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(msg, lambda m: process_withdrawal_holder(m, amount, card_number))

def process_withdrawal_holder(message, amount, card_number):
    card_holder = message.text.strip()
    
    result = WithdrawalManager.request_withdrawal(message.from_user.id, amount, card_number, card_holder)
    
    if result['success']:
        bot.send_message(
            message.chat.id,
            f"✅ درخواست برداشت شما ثبت شد!\n\n"
            f"💰 مبلغ: {amount:,} تومان\n"
            f"🆔 کد پیگیری: `{result['transaction_id']}`\n\n"
            f"⏳ پس از تأیید ادمین، مبلغ به حساب شما واریز خواهد شد.",
            parse_mode='Markdown'
        )
        
        # اطلاع به ادمین
        for admin_id in ADMIN_IDS:
            bot.send_message(
                admin_id,
                f"💸 **درخواست برداشت جدید**\n\n"
                f"👤 کاربر: {message.from_user.first_name}\n"
                f"🆔 شناسه: `{message.from_user.id}`\n"
                f"💰 مبلغ: {amount:,} تومان\n"
                f"🏦 شماره کارت: {card_number}\n"
                f"👤 صاحب حساب: {card_holder}\n"
                f"🆔 کد: `{result['transaction_id']}`",
                parse_mode='Markdown'
            )
    else:
        bot.send_message(message.chat.id, f"❌ خطا: {result['error']}")

# ==================== ربات‌های من ====================
@bot.message_handler(func=lambda m: m.text == '📋 ربات‌های من')
def my_bots(message):
    user_id = message.from_user.id
    bots = db.execute('SELECT * FROM bots WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما هیچ رباتی ندارید.\nاز دکمه 🤖 ساخت ربات جدید استفاده کنید.")
        return
    
    text = "📋 **لیست ربات‌های شما:**\n\n"
    for b in bots:
        status_emoji = "🟢" if b['status'] == 'running' else "🔴"
        text += f"{status_emoji} **{b['name']}**\n🆔 `{b['id'][:8]}...`\n📅 {b['created_at'][:10]}\n\n"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== شروع/توقف ====================
@bot.message_handler(func=lambda m: m.text == '🔄 شروع/توقف')
def toggle_menu(message):
    user_id = message.from_user.id
    bots = db.execute('SELECT id, name, status FROM bots WHERE user_id = ?', (user_id,))
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما هیچ رباتی ندارید.")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for b in bots:
        emoji = "🟢" if b['status'] == 'running' else "🔴"
        markup.add(types.InlineKeyboardButton(f"{emoji} {b['name']}", callback_data=f"toggle_{b['id']}"))
    
    bot.send_message(message.chat.id, "🔄 انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_'))
def toggle_bot(call):
    bot_id = call.data.replace('toggle_', '')
    bot_info = db.execute('SELECT user_id, status FROM bots WHERE id = ?', (bot_id,))
    
    if not bot_info or bot_info[0]['user_id'] != call.from_user.id:
        bot.answer_callback_query(call.id, "❌ پیدا نشد")
        return
    
    new_status = "stopped" if bot_info[0]['status'] == 'running' else "running"
    db.execute('UPDATE bots SET status = ? WHERE id = ?', (new_status, bot_id))
    
    bot.answer_callback_query(call.id, f"✅ ربات {new_status == 'running' and 'فعال' or 'متوقف'} شد")

# ==================== حذف ربات ====================
@bot.message_handler(func=lambda m: m.text == '🗑 حذف ربات')
def delete_menu(message):
    user_id = message.from_user.id
    bots = db.execute('SELECT id, name FROM bots WHERE user_id = ?', (user_id,))
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما هیچ رباتی ندارید.")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for b in bots:
        markup.add(types.InlineKeyboardButton(f"🗑 {b['name']}", callback_data=f"delete_{b['id']}"))
    
    bot.send_message(message.chat.id, "🗑 انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
def confirm_delete(call):
    bot_id = call.data.replace('delete_', '')
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ بله", callback_data=f"confirm_del_{bot_id}"),
        types.InlineKeyboardButton("❌ خیر", callback_data="cancel_del")
    )
    bot.edit_message_text("⚠️ اطمینان دارید؟", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_del_'))
def do_delete(call):
    bot_id = call.data.replace('confirm_del_', '')
    db.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
    db.execute('UPDATE users SET bots_count = bots_count - 1 WHERE user_id = ?', (call.from_user.id,))
    bot.answer_callback_query(call.id, "✅ حذف شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == 'cancel_del')
def cancel_delete(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== راهنما ====================
@bot.message_handler(func=lambda m: m.text == '📚 راهنما')
def guide(message):
    text = f"""
📚 **راهنمای کامل ربات**

🤖 **ساخت ربات:**
• فایل .py یا .zip را ارسال کنید
• پس از بررسی، ربات اجرا می‌شود

🎁 **تست رایگان:**
• {config.trial_duration} دقیقه رایگان
• برای تست عملکرد سیستم

💰 **اشتراک ماهانه:**
• مبلغ: {config.subscription_price:,} تومان
• اعتبار: ۳۰ روز

🎁 **سیستم رفرال:**
• هر کاربر دعوت کنید، ۱۰٪ درآمد او به شما می‌رسد
• موجودی قابل برداشت از {config.withdrawal_min_amount:,} تومان

📞 پشتیبانی: @shahraghee13
"""
    bot.send_message(message.chat.id, text)

# ==================== تنظیمات ====================
@bot.message_handler(func=lambda m: m.text == '⚙️ تنظیمات')
def settings(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🔐 امنیت اطلاعات", callback_data="security_settings"),
        types.InlineKeyboardButton("❌ بستن", callback_data="close_menu")
    )
    bot.send_message(message.chat.id, "⚙️ تنظیمات:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "security_settings")
def security_settings(call):
    text = """
🔐 **امنیت اطلاعات**

✅ اطلاعات شما رمزنگاری می‌شود
✅ هر کاربر فضای ایزوله دارد
✅ ربات‌ها در محیط امن اجرا می‌شوند
    """
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id)

# ==================== پنل مدیریت ====================
@bot.message_handler(func=lambda m: m.text == '👑 پنل مدیریت')
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    cluster_stats = cluster_manager.get_cluster_stats()
    users_count = db.execute('SELECT COUNT(*) as c FROM users')[0]['c']
    bots_count = db.execute('SELECT COUNT(*) as c FROM bots')[0]['c']
    pending_withdrawals = len(WithdrawalManager.get_pending_withdrawals())
    pending_receipts = db.execute('SELECT COUNT(*) as c FROM receipts WHERE status = "pending"')[0]['c']
    
    text = f"""
👑 **پنل مدیریت حرفه‌ای**

━━━━━━━━━━━━━━━
📊 **آمار کلی**
┌─────────────────┐
│ 👥 کاربران: {users_count:,}
│ 🤖 ربات‌ها: {bots_count:,}
│ 🖥️ ماشین‌ها: {cluster_stats['total_machines']}
│ ⏳ فیش‌های待: {pending_receipts}
│ 💸 درخواست‌های برداشت: {pending_withdrawals}
└─────────────────┘

━━━━━━━━━━━━━━━
⚙️ **تنظیمات فعلی**
┌─────────────────┐
│ 💰 قیمت اشتراک: {config.subscription_price:,} تومان
│ ⏱️ زمان تست: {config.trial_duration} دقیقه
│ 💳 شماره کارت: {config.card_number}
│ 💸 حداقل برداشت: {config.withdrawal_min_amount:,} تومان
└─────────────────┘
"""
    
    bot.send_message(message.chat.id, text, reply_markup=get_admin_panel(), parse_mode='Markdown')

# ==================== کال‌بک‌های مدیریت ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_receipts")
def admin_receipts(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    receipts = db.execute('SELECT * FROM receipts WHERE status = "pending" ORDER BY created_at')
    
    if not receipts:
        bot.send_message(call.message.chat.id, "📸 هیچ فیش جدیدی وجود ندارد")
        return
    
    for r in receipts:
        text = f"🆔 {r['id']}\n👤 کاربر: {r['user_id']}\n💰 مبلغ: {r['amount']:,}\n🆔 کد: {r['payment_code']}"
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید و فعال‌سازی اشتراک", callback_data=f"approve_payment_{r['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"reject_payment_{r['id']}")
        )
        
        if os.path.exists(r['receipt_path']):
            with open(r['receipt_path'], 'rb') as f:
                bot.send_photo(call.message.chat.id, f, caption=text, reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_payment_'))
def approve_payment(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    receipt_id = int(call.data.replace('approve_payment_', ''))
    receipt = db.execute('SELECT user_id FROM receipts WHERE id = ?', (receipt_id,))
    
    if receipt:
        user_id = receipt[0]['user_id']
        
        # فعال‌سازی اشتراک
        SubscriptionManager.activate_subscription(user_id, 1)
        
        # بروزرسانی فیش
        db.execute('''
            UPDATE receipts SET status = "approved", reviewed_by = ?, reviewed_at = ?
            WHERE id = ?
        ''', (call.from_user.id, datetime.now().isoformat(), receipt_id))
        
        # پیام به کاربر
        try:
            bot.send_message(user_id, f"✅ پرداخت شما تأیید شد!\nاشتراک ماهانه شما فعال شد.\nاز خدمات ما لذت ببرید 🚀")
        except:
            pass
        
        bot.answer_callback_query(call.id, "✅ اشتراک کاربر فعال شد")
        bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_payment_'))
def reject_payment(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    receipt_id = int(call.data.replace('reject_payment_', ''))
    receipt = db.execute('SELECT user_id FROM receipts WHERE id = ?', (receipt_id,))
    
    if receipt:
        user_id = receipt[0]['user_id']
        
        db.execute('UPDATE receipts SET status = "rejected", reviewed_by = ?, reviewed_at = ? WHERE id = ?',
                  (call.from_user.id, datetime.now().isoformat(), receipt_id))
        
        try:
            bot.send_message(user_id, "❌ متأسفانه فیش پرداخت شما تأیید نشد.\nلطفاً با پشتیبانی تماس بگیرید.")
        except:
            pass
        
        bot.answer_callback_query(call.id, "❌ فیش رد شد")

@bot.callback_query_handler(func=lambda call: call.data == "admin_withdrawals")
def admin_withdrawals(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    withdrawals = WithdrawalManager.get_pending_withdrawals()
    
    if not withdrawals:
        bot.send_message(call.message.chat.id, "💸 هیچ درخواست برداشتی وجود ندارد")
        return
    
    for w in withdrawals:
        text = f"""
💸 **درخواست برداشت**

🆔 شماره: {w['id']}
👤 کاربر: {w['user_id']}
💰 مبلغ: {w['amount']:,} تومان
🏦 شماره کارت: {w['card_number']}
👤 صاحب حساب: {w['card_holder']}
🆔 کد: `{w['transaction_id']}`
📅 تاریخ: {w['created_at'][:10]}
"""
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید واریز", callback_data=f"approve_withdrawal_{w['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"reject_withdrawal_{w['id']}")
        )
        
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_withdrawal_'))
def approve_withdrawal(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    withdrawal_id = int(call.data.replace('approve_withdrawal_', ''))
    
    if WithdrawalManager.approve_withdrawal(withdrawal_id, call.from_user.id):
        # اطلاع به کاربر
        withdrawal = db.execute('SELECT user_id, amount FROM withdrawals WHERE id = ?', (withdrawal_id,))
        if withdrawal:
            try:
                bot.send_message(
                    withdrawal[0]['user_id'],
                    f"✅ درخواست برداشت شما تأیید شد!\n💰 مبلغ {withdrawal[0]['amount']:,} تومان به حساب شما واریز شد."
                )
            except:
                pass
        
        bot.answer_callback_query(call.id, "✅ برداشت تأیید شد")
        bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_withdrawal_'))
def reject_withdrawal(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    withdrawal_id = int(call.data.replace('reject_withdrawal_', ''))
    
    if WithdrawalManager.reject_withdrawal(withdrawal_id, call.from_user.id):
        # اطلاع به کاربر
        withdrawal = db.execute('SELECT user_id, amount FROM withdrawals WHERE id = ?', (withdrawal_id,))
        if withdrawal:
            try:
                bot.send_message(
                    withdrawal[0]['user_id'],
                    f"❌ متأسفانه درخواست برداشت شما رد شد.\n💰 مبلغ {withdrawal[0]['amount']:,} تومان به موجودی شما برگشت داده شد."
                )
            except:
                pass
        
        bot.answer_callback_query(call.id, "❌ برداشت رد شد")
        bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_change_price")
def admin_change_price(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, "💰 قیمت جدید اشتراک را به تومان وارد کنید:")
    bot.register_next_step_handler(msg, process_price_change)

def process_price_change(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        new_price = int(message.text.replace(',', '').strip())
        config.subscription_price = new_price
        config.save_config()
        bot.reply_to(message, f"✅ قیمت اشتراک به {new_price:,} تومان تغییر کرد")
    except:
        bot.reply_to(message, "❌ عدد معتبر وارد کنید")

@bot.callback_query_handler(func=lambda call: call.data == "admin_change_welcome")
def admin_change_welcome(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, "📝 متن جدید خوش‌آمدگویی را ارسال کنید:")
    bot.register_next_step_handler(msg, process_welcome_change)

def process_welcome_change(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    config.welcome_text = message.text
    config.save_config()
    bot.reply_to(message, "✅ متن خوش‌آمدگویی تغییر کرد")

@bot.callback_query_handler(func=lambda call: call.data == "admin_change_card")
def admin_change_card(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, "🏦 شماره کارت جدید را وارد کنید (۱۶ رقم):")
    bot.register_next_step_handler(msg, process_card_change)

def process_card_change(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    card = message.text.replace(' ', '').replace('-', '').strip()
    if card.isdigit() and len(card) >= 16:
        config.card_number = card
        config.save_config()
        bot.reply_to(message, f"✅ شماره کارت به {card[:4]}****{card[-4:]} تغییر کرد")
    else:
        bot.reply_to(message, "❌ شماره کارت نامعتبر است")

@bot.callback_query_handler(func=lambda call: call.data == "admin_delete_bot")
def admin_delete_bot(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, "🆔 شناسه ربات مورد نظر برای حذف را وارد کنید:")
    bot.register_next_step_handler(msg, process_admin_delete_bot)

def process_admin_delete_bot(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    bot_id = message.text.strip()
    bot_info = db.execute('SELECT user_id FROM bots WHERE id = ?', (bot_id,))
    
    if bot_info:
        db.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
        bot.reply_to(message, f"✅ ربات {bot_id} حذف شد")
        
        # لاگ
        db.execute('''
            INSERT INTO system_logs (action, admin_id, target_user_id, details, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', ('delete_bot', message.from_user.id, bot_info[0]['user_id'], f"ربات {bot_id} حذف شد", datetime.now().isoformat()))
    else:
        bot.reply_to(message, "❌ ربات پیدا نشد")

@bot.callback_query_handler(func=lambda call: call.data == "admin_fix_bot")
def admin_fix_bot(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, "🆔 شناسه ربات برای رفع مشکل را وارد کنید:")
    bot.register_next_step_handler(msg, process_admin_fix_bot)

def process_admin_fix_bot(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    bot_id = message.text.strip()
    bot_info = db.execute('SELECT user_id, status FROM bots WHERE id = ?', (bot_id,))
    
    if bot_info:
        # ریست کردن وضعیت ربات
        db.execute('UPDATE bots SET status = "stopped" WHERE id = ?', (bot_id,))
        bot.reply_to(message, f"✅ ربات {bot_id} ریست شد. کاربر می‌تواند دوباره آن را فعال کند.")
        
        # اطلاع به کاربر
        try:
            bot.send_message(bot_info[0]['user_id'], f"🔧 ربات شما با شناسه {bot_id} توسط پشتیبانی ریست شد.\nلطفاً دوباره آن را فعال کنید.")
        except:
            pass
    else:
        bot.reply_to(message, "❌ ربات پیدا نشد")

@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    bot.delete_message(call.message.chat.id, call.message.message_id)
    admin_panel(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "close_menu")
def close_menu(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== مانیتورینگ اشتراک ====================
def subscription_monitor():
    """بررسی خودکار اشتراک‌ها و غیرفعال کردن ربات‌های منقضی شده"""
    while True:
        try:
            now = datetime.now()
            
            # بررسی کاربرانی که اشتراکشان منقضی شده
            expired_users = db.execute('''
                SELECT user_id FROM users 
                WHERE subscription_status = 'active' 
                AND subscription_end < ?
            ''', (now.isoformat(),))
            
            for user in expired_users:
                db.execute('UPDATE users SET subscription_status = "expired" WHERE user_id = ?', (user['user_id'],))
                SubscriptionManager.deactivate_user_bots(user['user_id'])
                
                # اطلاع به کاربر
                try:
                    bot.send_message(
                        user['user_id'],
                        "⚠️ اشتراک شما به اتمام رسید!\nبرای ادامه استفاده، لطفاً اشتراک جدید تهیه کنید.\nاز دکمه 💰 خرید اشتراک استفاده نمایید."
                    )
                except:
                    pass
            
            # بررسی کاربرانی که ۲۴ ساعت به اتمام اشتراکشان مانده
            expiring_soon = db.execute('''
                SELECT user_id, subscription_end FROM users 
                WHERE subscription_status = 'active' 
                AND julianday(subscription_end) - julianday(?) <= 1
                AND julianday(subscription_end) - julianday(?) > 0
            ''', (now.isoformat(), now.isoformat()))
            
            for user in expiring_soon:
                end_date = datetime.fromisoformat(user['subscription_end'])
                hours_left = int((end_date - now).total_seconds() / 3600)
                
                try:
                    bot.send_message(
                        user['user_id'],
                        f"⚠️ **هشدار اتمام اشتراک!**\n\n"
                        f"اشتراک شما {hours_left} ساعت دیگر به اتمام می‌رسد.\n"
                        f"برای تمدید، از دکمه 💰 خرید اشتراک استفاده کنید.\n\n"
                        f"در غیر این صورت پس از اتمام زمان، ربات‌های شما غیرفعال خواهند شد.",
                        parse_mode='Markdown'
                    )
                except:
                    pass
            
            time.sleep(3600)  # هر ساعت یکبار بررسی کن
            
        except Exception as e:
            print(f"Monitor error: {e}")
            time.sleep(3600)

threading.Thread(target=subscription_monitor, daemon=True).start()

# ==================== اجرا ====================
if __name__ == "__main__":
    print("=" * 80)
    print("🚀 ربات مادر حرفه‌ای - Enterprise Edition v4.0".center(80))
    print("=" * 80)
    print(f"✅ اشتراک ماهانه: {config.subscription_price:,} تومان")
    print(f"✅ تست رایگان: {config.trial_duration} دقیقه")
    print(f"✅ سیستم رفرال: {ReferralManager.REFERRAL_PERCENT}%")
    print(f"✅ حداقل برداشت: {config.withdrawal_min_amount:,} تومان")
    print("=" * 80)
    print(f"👑 ادمین: {ADMIN_IDS}")
    print("=" * 80)
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)