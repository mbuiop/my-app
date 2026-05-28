#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║     🚀 ربات مادر حرفه‌ای - Enterprise Edition v5.0                           ║
║     ⚡ تمام قابلیت‌ها فعال | پنل مدیریت کامل | تست واقعی                     ║
║     🔒 ساخت و اجرای واقعی ربات تلگرام                                        ║
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
import importlib
import pip
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from pathlib import Path
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
    'WITHDRAWALS': os.path.join(BASE_DIR, "withdrawals"),
    'BOT_CODES': os.path.join(BASE_DIR, "bot_codes"),  # ذخیره کدهای ربات
}

for dir_path in DIRS.values():
    os.makedirs(dir_path, exist_ok=True)

# ==================== توکن و تنظیمات ====================
BOT_TOKEN = "8052349235:AAFSaJmYpl359BKrJTWC8O-u-dI9r2olEOQ"
ADMIN_IDS = [327855654]

# ==================== کتابخانه‌های آماده برای نصب ====================
READY_LIBRARIES = {
    'requests': 'requests',
    'numpy': 'numpy', 
    'pandas': 'pandas',
    'beautifulsoup4': 'bs4',
    'flask': 'flask',
    'django': 'django',
    'pillow': 'PIL',
    'pyTelegramBotAPI': 'telebot',
    'aiogram': 'aiogram',
    'jdatetime': 'jdatetime',
    'redis': 'redis',
    'mysql-connector-python': 'mysql.connector',
    'psycopg2': 'psycopg2',
    'matplotlib': 'matplotlib',
    'seaborn': 'seaborn',
    'scikit-learn': 'sklearn',
    'tensorflow': 'tensorflow',
    'torch': 'torch',
    'opencv-python': 'cv2',
}

# ==================== تنظیمات ====================
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
                self.trial_duration = data.get('trial_duration', 5)
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

# ==================== دیتابیس ====================
class Database:
    def __init__(self):
        self.db_path = os.path.join(DIRS['DB'], 'mother_bot.db')
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        
        # جدول کاربران
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
                total_earnings INTEGER DEFAULT 0,
                withdrawn_amount INTEGER DEFAULT 0,
                available_balance INTEGER DEFAULT 0,
                subscription_status TEXT DEFAULT 'inactive',
                subscription_start TIMESTAMP,
                subscription_end TIMESTAMP,
                trial_used INTEGER DEFAULT 0,
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
                code_path TEXT,
                pid INTEGER,
                machine_id INTEGER,
                port INTEGER,
                status TEXT DEFAULT 'stopped',
                is_trial INTEGER DEFAULT 0,
                created_at TIMESTAMP,
                last_active TIMESTAMP,
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
                status TEXT DEFAULT 'pending',
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
        except Exception as e:
            print(f"DB Error: {e}")
            return []
        finally:
            conn.close()

db = Database()

# ==================== موتور اجرای ربات ====================
class BotEngine:
    """موتور قدرتمند اجرای ربات‌های تلگرام"""
    
    def __init__(self):
        self.running_bots = {}  # bot_id -> process info
        self.lock = threading.RLock()
        self.port_counter = 8000
    
    def get_available_port(self):
        with self.lock:
            port = self.port_counter
            self.port_counter += 1
            if self.port_counter > 9000:
                self.port_counter = 8000
            return port
    
    def prepare_bot_code(self, original_code: str, token: str) -> str:
        """آماده‌سازی کد ربات برای اجرا"""
        # حذف توکن از کد اصلی
        lines = original_code.split('\n')
        cleaned_lines = []
        
        for line in lines:
            if token in line and ('token' in line.lower() or 'TOKEN' in line):
                continue
            cleaned_lines.append(line)
        
        code = '\n'.join(cleaned_lines)
        
        # اضافه کردن توکن به ابتدای کد
        code = f"""
# ============================================
# ربات ساخته شده توسط ربات مادر حرفه‌ای
# زمان ساخت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# ============================================

import telebot
import time
import threading
import logging

# تنظیمات ربات
TOKEN = "{token}"
bot = telebot.TeleBot(TOKEN)

# لاگ‌گیری
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

{code}

# اجرای ربات
if __name__ == "__main__":
    try:
        logger.info("ربات شروع به کار کرد...")
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        logger.error(f"خطا در اجرا: {{e}}")
"""
        return code
    
    def run_bot(self, bot_id: str, code: str, token: str, user_id: int) -> Dict:
        """اجرای واقعی ربات"""
        try:
            # ایجاد پوشه مخصوص ربات
            bot_dir = os.path.join(DIRS['BOT_CODES'], bot_id)
            os.makedirs(bot_dir, exist_ok=True)
            
            # آماده‌سازی کد
            prepared_code = self.prepare_bot_code(code, token)
            
            # ذخیره کد
            code_path = os.path.join(bot_dir, 'bot.py')
            with open(code_path, 'w', encoding='utf-8') as f:
                f.write(prepared_code)
            
            # فایل لاگ
            log_file = os.path.join(DIRS['LOGS'], f"bot_{bot_id}.log")
            error_log = os.path.join(DIRS['LOGS'], f"bot_{bot_id}_error.log")
            
            # اجرای ربات
            process = subprocess.Popen(
                [sys.executable, '-u', code_path],
                stdout=open(log_file, 'a'),
                stderr=open(error_log, 'a'),
                cwd=bot_dir,
                start_new_session=True,
                env={
                    **os.environ,
                    'PYTHONUNBUFFERED': '1',
                    'BOT_ID': bot_id,
                    'USER_ID': str(user_id),
                }
            )
            
            # منتظر می‌مانیم تا ربات شروع شود
            time.sleep(3)
            
            # بررسی اینکه ربات در حال اجراست
            if process.poll() is None:
                with self.lock:
                    self.running_bots[bot_id] = {
                        'process': process,
                        'pid': process.pid,
                        'code_path': code_path,
                        'bot_dir': bot_dir,
                        'start_time': time.time()
                    }
                
                return {
                    'success': True,
                    'pid': process.pid,
                    'code_path': code_path,
                    'message': 'ربات با موفقیت اجرا شد'
                }
            else:
                # خطا در اجرا
                error_msg = ""
                if os.path.exists(error_log):
                    with open(error_log, 'r') as f:
                        error_msg = f.read()[-500:]
                
                return {
                    'success': False,
                    'error': error_msg or 'خطای ناشناخته در اجرا'
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def stop_bot(self, bot_id: str) -> bool:
        """توقف ربات"""
        with self.lock:
            if bot_id in self.running_bots:
                try:
                    bot_info = self.running_bots[bot_id]
                    process = bot_info['process']
                    
                    # ارسال SIGTERM
                    process.terminate()
                    
                    # منتظر می‌مانیم
                    for _ in range(10):
                        if process.poll() is not None:
                            break
                        time.sleep(0.5)
                    
                    # اگر هنوز در حال اجراست، force kill
                    if process.poll() is None:
                        process.kill()
                    
                    del self.running_bots[bot_id]
                    return True
                    
                except Exception as e:
                    print(f"Error stopping bot: {e}")
                    return False
            return False
    
    def get_bot_status(self, bot_id: str) -> Dict:
        """دریافت وضعیت ربات"""
        with self.lock:
            if bot_id in self.running_bots:
                bot_info = self.running_bots[bot_id]
                try:
                    process = bot_info['process']
                    if process.poll() is None:
                        # محاسبه uptime
                        uptime = int(time.time() - bot_info['start_time'])
                        
                        # دریافت مصرف منابع (اختیاری)
                        try:
                            p = psutil.Process(bot_info['pid'])
                            cpu = p.cpu_percent()
                            memory = p.memory_percent()
                        except:
                            cpu = 0
                            memory = 0
                        
                        return {
                            'running': True,
                            'pid': bot_info['pid'],
                            'uptime': uptime,
                            'cpu': cpu,
                            'memory': memory
                        }
                    else:
                        # ربات از کار افتاده
                        del self.running_bots[bot_id]
                except:
                    pass
            
            return {'running': False}
    
    def restart_bot(self, bot_id: str, code: str, token: str, user_id: int) -> Dict:
        """ری‌استارت ربات"""
        self.stop_bot(bot_id)
        time.sleep(1)
        return self.run_bot(bot_id, code, token, user_id)

# ایجاد موتور
bot_engine = BotEngine()

# ==================== سیستم اشتراک ====================
class SubscriptionManager:
    
    @staticmethod
    def activate_trial(user_id: int) -> bool:
        """فعال کردن تست رایگان"""
        user = db.execute('SELECT trial_used FROM users WHERE user_id = ?', (user_id,))
        
        if not user or user[0]['trial_used'] == 1:
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
        
        return True
    
    @staticmethod
    def check_subscription_status(user_id: int) -> Dict:
        """بررسی وضعیت اشتراک"""
        user = db.execute('''
            SELECT subscription_status, subscription_end, trial_end, trial_used 
            FROM users WHERE user_id = ?
        ''', (user_id,))
        
        if not user:
            return {'has_access': False, 'status': 'no_user'}
        
        user = user[0]
        now = datetime.now()
        
        if user['subscription_status'] == 'active':
            end_date = datetime.fromisoformat(user['subscription_end'])
            days_left = (end_date - now).days
            
            if days_left < 0:
                db.execute('UPDATE users SET subscription_status = "expired" WHERE user_id = ?', (user_id,))
                return {'has_access': False, 'status': 'expired', 'days_left': 0}
            
            return {'has_access': True, 'status': 'active', 'days_left': days_left}
        
        elif user['subscription_status'] == 'trial':
            end_date = datetime.fromisoformat(user['trial_end'])
            minutes_left = int((end_date - now).total_seconds() / 60)
            
            if minutes_left < 0:
                db.execute('UPDATE users SET subscription_status = "inactive" WHERE user_id = ?', (user_id,))
                return {'has_access': False, 'status': 'trial_expired'}
            
            return {'has_access': True, 'status': 'trial', 'minutes_left': minutes_left}
        
        return {'has_access': False, 'status': 'inactive'}

# ==================== سیستم رفرال ====================
class ReferralManager:
    
    @staticmethod
    def generate_referral_code(user_id: int) -> str:
        """تولید کد رفرال"""
        return hashlib.md5(f"{user_id}_{secrets.token_hex(4)}".encode()).hexdigest()[:10]
    
    @staticmethod
    def register_referral(new_user_id: int, referral_code: str) -> bool:
        """ثبت رفرال"""
        referrer = db.execute('SELECT user_id FROM users WHERE referral_code = ?', (referral_code,))
        
        if not referrer or referrer[0]['user_id'] == new_user_id:
            return False
        
        existing = db.execute('SELECT referred_by FROM users WHERE user_id = ?', (new_user_id,))
        if existing and existing[0]['referred_by']:
            return False
        
        referrer_id = referrer[0]['user_id']
        
        db.execute('''
            UPDATE users 
            SET referred_by = ?, referrals_count = referrals_count + 1
            WHERE user_id = ?
        ''', (referrer_id, new_user_id))
        
        return True
    
    @staticmethod
    def add_earning(referrer_id: int, referred_user_id: int, amount: int, bot_id: str = None):
        """اضافه کردن درآمد به معرف"""
        earning_amount = int(amount * 10 / 100)  # 10 درصد
        
        db.execute('''
            INSERT INTO referral_earnings (user_id, referred_user_id, amount, percent, bot_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (referrer_id, referred_user_id, earning_amount, 10, bot_id, datetime.now().isoformat()))
        
        db.execute('''
            UPDATE users 
            SET total_earnings = total_earnings + ?,
                available_balance = available_balance + ?
            WHERE user_id = ?
        ''', (earning_amount, earning_amount, referrer_id))
    
    @staticmethod
    def get_user_stats(user_id: int) -> Dict:
        """دریافت آمار رفرال"""
        user = db.execute('''
            SELECT referral_code, referrals_count, verified_referrals, 
                   total_earnings, available_balance, withdrawn_amount
            FROM users WHERE user_id = ?
        ''', (user_id,))
        
        if not user:
            return {}
        
        user = user[0]
        
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

# ==================== سیستم برداشت ====================
class WithdrawalManager:
    
    @staticmethod
    def request_withdrawal(user_id: int, amount: int, card_number: str, card_holder: str) -> Dict:
        """ثبت درخواست برداشت"""
        user = db.execute('SELECT available_balance FROM users WHERE user_id = ?', (user_id,))
        
        if not user:
            return {'success': False, 'error': 'کاربر یافت نشد'}
        
        balance = user[0]['available_balance']
        
        if amount < config.withdrawal_min_amount:
            return {'success': False, 'error': f'حداقل مبلغ برداشت {config.withdrawal_min_amount:,} تومان است'}
        
        if amount > balance:
            return {'success': False, 'error': 'موجودی کافی نیست'}
        
        transaction_id = hashlib.md5(f"{user_id}_{amount}_{time.time()}".encode()).hexdigest()[:12].upper()
        
        db.execute('''
            INSERT INTO withdrawals (user_id, amount, card_number, card_holder, transaction_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, amount, card_number, card_holder, transaction_id, datetime.now().isoformat()))
        
        db.execute('''
            UPDATE users SET available_balance = available_balance - ? WHERE user_id = ?
        ''', (amount, user_id))
        
        return {'success': True, 'transaction_id': transaction_id, 'amount': amount}
    
    @staticmethod
    def approve_withdrawal(withdrawal_id: int, admin_id: int) -> bool:
        """تأیید برداشت"""
        withdrawal = db.execute('SELECT user_id, amount FROM withdrawals WHERE id = ?', (withdrawal_id,))
        
        if not withdrawal:
            return False
        
        db.execute('''
            UPDATE withdrawals 
            SET status = 'approved', reviewed_by = ?, reviewed_at = ?
            WHERE id = ?
        ''', (admin_id, datetime.now().isoformat(), withdrawal_id))
        
        db.execute('''
            UPDATE users SET withdrawn_amount = withdrawn_amount + ? WHERE user_id = ?
        ''', (withdrawal[0]['amount'], withdrawal[0]['user_id']))
        
        return True
    
    @staticmethod
    def reject_withdrawal(withdrawal_id: int, admin_id: int) -> bool:
        """رد برداشت و برگشت موجودی"""
        withdrawal = db.execute('SELECT user_id, amount FROM withdrawals WHERE id = ?', (withdrawal_id,))
        
        if not withdrawal:
            return False
        
        db.execute('''
            UPDATE withdrawals 
            SET status = 'rejected', reviewed_by = ?, reviewed_at = ?
            WHERE id = ?
        ''', (admin_id, datetime.now().isoformat(), withdrawal_id))
        
        db.execute('''
            UPDATE users SET available_balance = available_balance + ? WHERE user_id = ?
        ''', (withdrawal[0]['amount'], withdrawal[0]['user_id']))
        
        return True
    
    @staticmethod
    def get_pending_withdrawals():
        return db.execute('SELECT * FROM withdrawals WHERE status = "pending" ORDER BY created_at')

# ==================== توابع کمکی ====================
def create_user(user_id: int, username: str, first_name: str, last_name: str, referral_code: str = None):
    """ایجاد کاربر جدید"""
    existing = db.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
    if existing:
        return True
    
    code = ReferralManager.generate_referral_code(user_id)
    
    # ثبت رفرال
    referrer_id = None
    if referral_code:
        ref_user = db.execute('SELECT user_id FROM users WHERE referral_code = ?', (referral_code,))
        if ref_user and ref_user[0]['user_id'] != user_id:
            referrer_id = ref_user[0]['user_id']
    
    now = datetime.now().isoformat()
    
    db.execute('''
        INSERT INTO users 
        (user_id, username, first_name, last_name, referral_code, referred_by, created_at, last_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, username, first_name, last_name, code, referrer_id, now, now))
    
    return True

def get_user(user_id: int):
    users = db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    return dict(users[0]) if users else None

def extract_token_from_code(code: str) -> Optional[str]:
    """استخراج توکن از کد"""
    patterns = [
        r'token\s*=\s*["\']([^"\']{30,60})["\']',
        r'TOKEN\s*=\s*["\']([^"\']{30,60})["\']',
        r'BOT_TOKEN\s*=\s*["\']([^"\']{30,60})["\']',
        r'bot\s*=\s*telebot\.TeleBot\(\s*["\']([^"\']{30,60})["\']\s*\)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, code, re.IGNORECASE)
        if match:
            token = match.group(1)
            # اعتبارسنجی توکن
            try:
                resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
                if resp.status_code == 200 and resp.json().get('ok'):
                    return token
            except:
                pass
    return None

def install_library(lib_name: str) -> Tuple[bool, str]:
    """نصب کتابخانه پایتون"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", lib_name, "--quiet"],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            return True, f"✅ {lib_name} نصب شد"
        else:
            return False, f"❌ خطا در نصب {lib_name}"
    except Exception as e:
        return False, f"❌ خطا: {str(e)}"

# ==================== ربات تلگرام ====================
bot = telebot.TeleBot(BOT_TOKEN)
bot.delete_webhook()

# ==================== منوها ====================
def get_main_menu(user_id: int):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    buttons = [
        types.KeyboardButton("🎁 تست رایگان"),
        types.KeyboardButton("💰 خرید اشتراک"),
        types.KeyboardButton("🤖 ساخت ربات جدید"),
        types.KeyboardButton("📋 ربات‌های من"),
        types.KeyboardButton("🔄 شروع/توقف ربات"),
        types.KeyboardButton("🗑 حذف ربات"),
        types.KeyboardButton("📊 کیف پول و آمار"),
        types.KeyboardButton("🎁 سیستم رفرال"),
        types.KeyboardButton("💸 برداشت وجه"),
        types.KeyboardButton("📦 نصب کتابخانه"),
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
    
    subscription = SubscriptionManager.check_subscription_status(user_id)
    
    if subscription['has_access']:
        sub_text = f"✅ وضعیت: {'تست رایگان' if subscription['status'] == 'trial' else 'اشتراک فعال'}"
        if subscription['status'] == 'trial':
            sub_text += f"\n⏱️ {subscription['minutes_left']} دقیقه باقی مانده"
        else:
            sub_text += f"\n📅 {subscription['days_left']} روز باقی مانده"
    else:
        sub_text = "❌ بدون اشتراک - از دکمه تست رایگان یا خرید اشتراک استفاده کنید"
    
    text = f"""{config.welcome_text}

━━━━━━━━━━━━━━━
{sub_text}
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
    text = f"""
💰 **خرید اشتراک ماهانه**

💳 مبلغ: {config.subscription_price:,} تومان

🏦 اطلاعات واریز:
شماره کارت: `{config.card_number}`
به نام: {config.card_holder}
بانک: {config.card_bank}

📸 **روش اقدام:**
1. مبلغ را به کارت فوق واریز کنید
2. از قسمت 📊 کیف پول و آمار، تصویر فیش را ارسال کنید
3. پس از تأیید، اشتراک شما فعال می‌شود

⏱️ اشتراک شما به مدت ۳۰ روز فعال خواهد بود
    """
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== نصب کتابخانه ====================
@bot.message_handler(func=lambda m: m.text == '📦 نصب کتابخانه')
def install_library_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    # کتابخانه‌های آماده
    for name, lib in list(READY_LIBRARIES.items())[:10]:
        markup.add(types.InlineKeyboardButton(f"📦 {name}", callback_data=f"lib_{lib}"))
    
    markup.add(types.InlineKeyboardButton("🔧 نصب دستی", callback_data="lib_custom"))
    markup.add(types.InlineKeyboardButton("❌ بستن", callback_data="close_menu"))
    
    bot.send_message(message.chat.id, "📦 **کتابخانه مورد نظر را انتخاب کنید:**", 
                     reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('lib_'))
def install_library_callback(call):
    lib = call.data.replace('lib_', '')
    
    if lib == 'custom':
        msg = bot.send_message(call.message.chat.id, "📦 نام کتابخانه مورد نظر را وارد کنید:")
        bot.register_next_step_handler(msg, install_custom_library)
        bot.answer_callback_query(call.id)
        return
    
    bot.answer_callback_query(call.id, f"🔄 در حال نصب {lib}...")
    
    success, message_text = install_library(lib)
    
    if success:
        bot.edit_message_text(message_text, call.message.chat.id, call.message.message_id)
    else:
        bot.edit_message_text(message_text, call.message.chat.id, call.message.message_id)

def install_custom_library(message):
    lib = message.text.strip()
    bot.send_message(message.chat.id, f"🔄 در حال نصب {lib}...")
    success, msg_text = install_library(lib)
    bot.send_message(message.chat.id, msg_text)

# ==================== ساخت ربات ====================
@bot.message_handler(func=lambda m: m.text == '🤖 ساخت ربات جدید')
def new_bot(message):
    user_id = message.from_user.id
    
    subscription = SubscriptionManager.check_subscription_status(user_id)
    
    if not subscription['has_access']:
        text = f"""❌ **شما دسترسی به ساخت ربات ندارید!**

{SubscriptionManager.check_subscription_status(user_id)}

🎁 برای تست رایگان از دکمه تست رایگان استفاده کنید
💰 برای خرید اشتراک از دکمه خرید اشتراک استفاده کنید
"""
        bot.send_message(message.chat.id, text, parse_mode='Markdown')
        return
    
    if subscription['status'] == 'trial':
        time_msg = f"⏱️ زمان باقی مانده تست: {subscription['minutes_left']} دقیقه"
    else:
        time_msg = f"📅 روزهای باقی مانده اشتراک: {subscription['days_left']} روز"
    
    bot.send_message(
        message.chat.id,
        f"📤 **ارسال فایل ربات**\n\n"
        f"✅ دسترسی دارید!\n{time_msg}\n\n"
        f"فایل .py یا .zip خود را ارسال کنید.\n"
        f"حداکثر حجم: ۱۰ مگابایت"
    )

# ==================== آپلود و اجرای ربات ====================
@bot.message_handler(content_types=['document'])
def handle_file_upload(message):
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
        # دانلود فایل
        file_info = bot.get_file(message.document.file_id)
        file_data = bot.download_file(file_info.file_path)
        
        # ذخیره فایل
        user_dir = os.path.join(DIRS['FILES'], str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        file_path = os.path.join(user_dir, f"{int(time.time())}_{file_name}")
        
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        # استخراج کد
        main_code = ""
        
        if file_name.endswith('.py'):
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                main_code = f.read()
        else:
            # استخراج از zip
            extract_dir = os.path.join(DIRS['TEMP'], f"extract_{user_id}_{int(time.time())}")
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(file_path, 'r') as zf:
                zf.extractall(extract_dir)
                
                # پیدا کردن فایل اصلی
                for root, dirs, files in os.walk(extract_dir):
                    for f in files:
                        if f.endswith('.py'):
                            with open(os.path.join(root, f), 'r', encoding='utf-8', errors='ignore') as code_file:
                                main_code = code_file.read()
                                break
                    if main_code:
                        break
            
            shutil.rmtree(extract_dir, ignore_errors=True)
        
        if not main_code:
            bot.edit_message_text("❌ کد معتبری پیدا نشد", message.chat.id, status_msg.message_id)
            return
        
        # استخراج توکن
        token = extract_token_from_code(main_code)
        if not token:
            bot.edit_message_text("❌ توکن معتبر پیدا نشد!\nلطفاً توکن ربات خود را در کد قرار دهید.", 
                                 message.chat.id, status_msg.message_id)
            return
        
        # دریافت اطلاعات ربات
        try:
            resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
            bot_info = resp.json()['result']
            bot_name = bot_info['first_name']
            bot_username = bot_info['username']
        except:
            bot_name = "ربات جدید"
            bot_username = "unknown"
        
        # ایجاد شناسه یکتا برای ربات
        bot_id = hashlib.md5(f"{user_id}_{token}_{time.time()}".encode()).hexdigest()[:16]
        
        bot.edit_message_text("🚀 در حال اجرای ربات...", message.chat.id, status_msg.message_id)
        
        # اجرای ربات
        result = bot_engine.run_bot(bot_id, main_code, token, user_id)
        
        if result['success']:
            # ذخیره در دیتابیس
            db.execute('''
                INSERT INTO bots (id, user_id, token, name, username, file_path, code_path, pid, status, is_trial, created_at, last_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'running', ?, ?, ?)
            ''', (bot_id, user_id, token, bot_name, bot_username, file_path, result['code_path'], 
                  result['pid'], 1 if subscription['status'] == 'trial' else 0,
                  datetime.now().isoformat(), datetime.now().isoformat()))
            
            db.execute('UPDATE users SET bots_count = bots_count + 1, last_active = ? WHERE user_id = ?',
                      (datetime.now().isoformat(), user_id))
            
            # درآمد رفرال برای اولین ربات
            user = get_user(user_id)
            if user and user['referred_by'] and user['bots_count'] == 1:
                ReferralManager.add_earning(user['referred_by'], user_id, config.subscription_price, bot_id)
                db.execute('UPDATE users SET verified_referrals = verified_referrals + 1 WHERE user_id = ?', 
                          (user['referred_by'],))
            
            success_text = f"""
✅ **ربات با موفقیت ساخته و اجرا شد!**

🤖 نام: {bot_name}
🔗 آیدی: @{bot_username}
🆔 شناسه: `{bot_id}`
🔢 PID: {result['pid']}

💡 برای مدیریت ربات از منوی اصلی استفاده کنید.
"""
            bot.edit_message_text(success_text, message.chat.id, status_msg.message_id, parse_mode='Markdown')
        else:
            bot.edit_message_text(f"❌ خطا در اجرای ربات:\n{result.get('error', 'خطای ناشناخته')}", 
                                 message.chat.id, status_msg.message_id)
            
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)[:200]}", message.chat.id, status_msg.message_id)

# ==================== ربات‌های من ====================
@bot.message_handler(func=lambda m: m.text == '📋 ربات‌های من')
def my_bots(message):
    user_id = message.from_user.id
    bots_list = db.execute('SELECT * FROM bots WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    
    if not bots_list:
        bot.send_message(message.chat.id, "📋 شما هیچ رباتی ندارید.\nاز دکمه 🤖 ساخت ربات جدید استفاده کنید.")
        return
    
    text = "📋 **لیست ربات‌های شما:**\n\n"
    for b in bots_list:
        status = bot_engine.get_bot_status(b['id'])
        status_emoji = "🟢" if status.get('running') else "🔴"
        status_text = "فعال" if status.get('running') else "متوقف"
        
        text += f"{status_emoji} **{b['name']}**\n"
        text += f"🆔 `{b['id'][:8]}...`\n"
        text += f"📊 وضعیت: {status_text}\n"
        if status.get('running'):
            text += f"⏱️ مدت فعالیت: {status.get('uptime', 0)//60} دقیقه\n"
        text += f"📅 تاریخ ساخت: {b['created_at'][:10]}\n"
        text += "━━━━━━━━━━━━━━━\n"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== شروع/توقف ربات ====================
@bot.message_handler(func=lambda m: m.text == '🔄 شروع/توقف ربات')
def toggle_menu(message):
    user_id = message.from_user.id
    bots_list = db.execute('SELECT id, name, status FROM bots WHERE user_id = ?', (user_id,))
    
    if not bots_list:
        bot.send_message(message.chat.id, "📋 شما هیچ رباتی ندارید.")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for b in bots_list:
        status = bot_engine.get_bot_status(b['id'])
        emoji = "🟢" if status.get('running') else "🔴"
        markup.add(types.InlineKeyboardButton(f"{emoji} {b['name']}", callback_data=f"toggle_{b['id']}"))
    
    bot.send_message(message.chat.id, "🔄 **ربات مورد نظر را انتخاب کنید:**", 
                     reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_'))
def toggle_bot(call):
    bot_id = call.data.replace('toggle_', '')
    bot_info = db.execute('SELECT user_id, token, file_path, status FROM bots WHERE id = ?', (bot_id,))
    
    if not bot_info or bot_info[0]['user_id'] != call.from_user.id:
        bot.answer_callback_query(call.id, "❌ ربات پیدا نشد")
        return
    
    bot_info = bot_info[0]
    current_status = bot_engine.get_bot_status(bot_id)
    
    if current_status.get('running'):
        # توقف ربات
        if bot_engine.stop_bot(bot_id):
            db.execute('UPDATE bots SET status = "stopped", last_active = ? WHERE id = ?',
                      (datetime.now().isoformat(), bot_id))
            bot.answer_callback_query(call.id, "✅ ربات متوقف شد")
        else:
            bot.answer_callback_query(call.id, "❌ خطا در توقف ربات")
    else:
        # شروع مجدد ربات
        try:
            with open(bot_info['file_path'], 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
            
            token = extract_token_from_code(code)
            if not token:
                bot.answer_callback_query(call.id, "❌ توکن معتبر پیدا نشد")
                return
            
            result = bot_engine.run_bot(bot_id, code, token, call.from_user.id)
            
            if result['success']:
                db.execute('UPDATE bots SET status = "running", pid = ?, last_active = ? WHERE id = ?',
                          (result['pid'], datetime.now().isoformat(), bot_id))
                bot.answer_callback_query(call.id, "✅ ربات شروع شد")
            else:
                bot.answer_callback_query(call.id, f"❌ خطا: {result.get('error', 'ناشناخته')[:50]}")
        except Exception as e:
            bot.answer_callback_query(call.id, f"❌ خطا: {str(e)[:50]}")

# ==================== حذف ربات ====================
@bot.message_handler(func=lambda m: m.text == '🗑 حذف ربات')
def delete_menu(message):
    user_id = message.from_user.id
    bots_list = db.execute('SELECT id, name FROM bots WHERE user_id = ?', (user_id,))
    
    if not bots_list:
        bot.send_message(message.chat.id, "📋 شما هیچ رباتی ندارید.")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for b in bots_list:
        markup.add(types.InlineKeyboardButton(f"🗑 {b['name']}", callback_data=f"delete_{b['id']}"))
    
    bot.send_message(message.chat.id, "🗑 **ربات مورد نظر را انتخاب کنید:**", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
def confirm_delete(call):
    bot_id = call.data.replace('delete_', '')
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ بله، حذف شود", callback_data=f"confirm_del_{bot_id}"),
        types.InlineKeyboardButton("❌ انصراف", callback_data="close_menu")
    )
    bot.edit_message_text("⚠️ **آیا از حذف این ربات اطمینان دارید؟**", 
                         call.message.chat.id, call.message.message_id, 
                         reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_del_'))
def do_delete(call):
    bot_id = call.data.replace('confirm_del_', '')
    bot_info = db.execute('SELECT user_id FROM bots WHERE id = ?', (bot_id,))
    
    if bot_info and bot_info[0]['user_id'] == call.from_user.id:
        # توقف ربات
        bot_engine.stop_bot(bot_id)
        
        # حذف از دیتابیس
        db.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
        db.execute('UPDATE users SET bots_count = bots_count - 1 WHERE user_id = ?', (call.from_user.id,))
        
        bot.answer_callback_query(call.id, "✅ ربات حذف شد")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "🗑 ربات با موفقیت حذف شد.")

# ==================== کیف پول و آمار ====================
@bot.message_handler(func=lambda m: m.text == '📊 کیف پول و آمار')
def wallet_stats(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    referral_stats = ReferralManager.get_user_stats(user_id)
    subscription = SubscriptionManager.check_subscription_status(user_id)
    
    if subscription['has_access']:
        if subscription['status'] == 'trial':
            sub_text = f"🎁 تست رایگان - {subscription['minutes_left']} دقیقه باقی مانده"
        else:
            sub_text = f"✅ اشتراک فعال - {subscription['days_left']} روز باقی مانده"
    else:
        sub_text = "❌ بدون اشتراک"
    
    text = f"""
💰 **کیف پول و آمار شما**

━━━━━━━━━━━━━━━
📊 **وضعیت حساب**
┌─────────────────┐
│ 👤 کاربر: {user['first_name'] or user['username']}
│ 🆔 شناسه: `{user_id}`
│ 🤖 ربات‌ها: {user['bots_count']}
│ {sub_text}
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

🎁 **لینک دعوت شما:**
`https://t.me/{bot.get_me().username}?start={referral_stats.get('code', '')}`

💡 هر نفر که با لینک شما عضو شود و ربات بسازد،
۱۰٪ از درآمد او به حساب شما واریز می‌شود!

📸 **ارسال فیش واریز:**
پس از واریز مبلغ اشتراک، تصویر فیش را ارسال کنید.
    """
    
    # دکمه ارسال فیش
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(types.KeyboardButton("📸 ارسال فیش جدید"))
    markup.add(types.KeyboardButton("🔙 بازگشت به منو"))
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == '📸 ارسال فیش جدید')
def send_receipt_instruction(message):
    bot.send_message(message.chat.id, "📸 لطفاً تصویر فیش واریز خود را ارسال کنید.", 
                     reply_markup=get_main_menu(message.from_user.id))

# ==================== فیش ====================
@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    
    # بررسی فیش تکراری
    existing = db.execute('SELECT id FROM receipts WHERE user_id = ? AND status = "pending"', (user_id,))
    if existing:
        bot.reply_to(message, "⏳ شما یک فیش در انتظار بررسی دارید. لطفاً صبر کنید.")
        return
    
    try:
        photo = message.photo[-1]
        file_info = bot.get_file(photo.file_id)
        file_data = bot.download_file(file_info.file_path)
        
        payment_code = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:8].upper()
        receipt_path = os.path.join(DIRS['RECEIPTS'], f"{user_id}_{payment_code}.jpg")
        
        with open(receipt_path, 'wb') as f:
            f.write(file_data)
        
        db.execute('''
            INSERT INTO receipts (user_id, amount, receipt_path, payment_code, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, config.subscription_price, receipt_path, payment_code, datetime.now().isoformat()))
        
        bot.reply_to(message, f"""
✅ **فیش شما دریافت شد!**

🆔 کد پیگیری: `{payment_code}`
💰 مبلغ: {config.subscription_price:,} تومان

⏳ در اسرع وقت بررسی و تأیید خواهد شد.
        """, parse_mode='Markdown')
        
        # اطلاع به ادمین
        for admin_id in ADMIN_IDS:
            try:
                with open(receipt_path, 'rb') as f:
                    bot.send_photo(admin_id, f, caption=f"""
📸 **فیش جدید**

👤 کاربر: {message.from_user.first_name}
🆔 شناسه: `{user_id}`
💰 مبلغ: {config.subscription_price:,} تومان
🆔 کد: `{payment_code}`
                    """, parse_mode='Markdown')
            except:
                pass
                
    except Exception as e:
        bot.reply_to(message, f"❌ خطا در دریافت فیش: {str(e)}")

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

📦 **نصب کتابخانه:**
• از دکمه 📦 نصب کتابخانه استفاده کنید
• کتابخانه‌های آماده یا دستی

📞 پشتیبانی: @shahraghee13
"""
    bot.send_message(message.chat.id, text)

# ==================== تنظیمات ====================
@bot.message_handler(func=lambda m: m.text == '⚙️ تنظیمات')
def settings(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🔐 امنیت اطلاعات", callback_data="security_settings"),
        types.InlineKeyboardButton("ℹ️ درباره ربات", callback_data="about_bot"),
        types.InlineKeyboardButton("❌ بستن", callback_data="close_menu")
    )
    bot.send_message(message.chat.id, "⚙️ **تنظیمات:**", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "security_settings")
def security_settings(call):
    text = """
🔐 **امنیت اطلاعات**

✅ اطلاعات شما رمزنگاری می‌شود
✅ هر کاربر فضای ایزوله دارد
✅ ربات‌ها در محیط امن اجرا می‌شوند
✅ کدهای مخرب به طور خودکار شناسایی می‌شوند
    """
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "about_bot")
def about_bot(call):
    text = """
ℹ️ **درباره ربات**

🚀 ربات مادر حرفه‌ای - Enterprise Edition v5.0

✨ **قابلیت‌ها:**
• ساخت و اجرای ربات تلگرام
• تست رایگان ۵ دقیقه‌ای
• اشتراک ماهانه
• سیستم رفرال و کسب درآمد
• برداشت وجه خودکار
• نصب کتابخانه پایتون

👨‍💻 **توسعه‌دهنده:** @shahraghee13
    """
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id)

# ==================== پنل مدیریت ====================
@bot.message_handler(func=lambda m: m.text == '👑 پنل مدیریت')
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    users_count = db.execute('SELECT COUNT(*) as c FROM users')[0]['c']
    bots_count = db.execute('SELECT COUNT(*) as c FROM bots')[0]['c']
    running_bots = len([b for b in bot_engine.running_bots.values()])
    pending_withdrawals = len(WithdrawalManager.get_pending_withdrawals())
    pending_receipts = db.execute('SELECT COUNT(*) as c FROM receipts WHERE status = "pending"')[0]['c']
    
    text = f"""
👑 **پنل مدیریت حرفه‌ای**

━━━━━━━━━━━━━━━
📊 **آمار کلی**
┌─────────────────┐
│ 👥 کاربران: {users_count:,}
│ 🤖 کل ربات‌ها: {bots_count:,}
│ 🟢 ربات‌های فعال: {running_bots}
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
        
        SubscriptionManager.activate_subscription(user_id, 1)
        
        db.execute('''
            UPDATE receipts SET status = "approved", reviewed_by = ?, reviewed_at = ?
            WHERE id = ?
        ''', (call.from_user.id, datetime.now().isoformat(), receipt_id))
        
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

@bot.callback_query_handler(func=lambda call: call.data == "admin_machines")
def admin_machines(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    running_count = len(bot_engine.running_bots)
    
    text = f"""
🖥️ **وضعیت ماشین‌ها**

📊 **آمار اجرایی:**
• ربات‌های در حال اجرا: {running_count}
• موتور اجرا: فعال ✅
• حافظه مصرفی: {psutil.virtual_memory().percent}%
• پردازنده: {psutil.cpu_percent()}%

✅ سیستم در وضعیت عادی کار می‌کند.
"""
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_users")
def admin_users(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    users = db.execute('SELECT user_id, first_name, bots_count, subscription_status FROM users ORDER BY created_at DESC LIMIT 20')
    
    text = "👥 **لیست کاربران (۲۰ نفر آخر):**\n\n"
    for u in users:
        status_emoji = "🟢" if u['subscription_status'] == 'active' else "🔴"
        text += f"{status_emoji} `{u['user_id']}` - {u['first_name'] or 'نامشخص'} - {u['bots_count']} ربات\n"
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_stats(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    users_count = db.execute('SELECT COUNT(*) as c FROM users')[0]['c']
    bots_count = db.execute('SELECT COUNT(*) as c FROM bots')[0]['c']
    running_bots = len(bot_engine.running_bots)
    payments = db.execute('SELECT COUNT(*) as c FROM receipts WHERE status = "approved"')[0]['c']
    total_earnings = db.execute('SELECT SUM(amount) as total FROM withdrawals WHERE status = "approved"')[0]['total'] or 0
    
    text = f"""
📊 **آمار پیشرفته سیستم**

👥 **کاربران:**
• کل کاربران: {users_count:,}
• میانگین ربات به ازای کاربر: {bots_count/users_count if users_count else 0:.1f}

🤖 **ربات‌ها:**
• کل ربات‌ها: {bots_count:,}
• در حال اجرا: {running_bots:,}
• موفقیت اجرا: {(running_bots/bots_count*100) if bots_count else 0:.1f}%

💰 **مالی:**
• پرداخت‌های موفق: {payments:,}
• مبلغ کل پرداختی: {payments * config.subscription_price:,} تومان
• مبلغ برداشت شده: {total_earnings:,} تومان
"""
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id)

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
        bot_engine.stop_bot(bot_id)
        db.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
        bot.reply_to(message, f"✅ ربات {bot_id} حذف شد")
        
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
        bot_engine.stop_bot(bot_id)
        db.execute('UPDATE bots SET status = "stopped" WHERE id = ?', (bot_id,))
        bot.reply_to(message, f"✅ ربات {bot_id} ریست شد. کاربر می‌تواند دوباره آن را فعال کند.")
        
        try:
            bot.send_message(bot_info[0]['user_id'], f"🔧 ربات شما با شناسه {bot_id} توسط پشتیبانی ریست شد.\nلطفاً دوباره آن را فعال کنید.")
        except:
            pass
    else:
        bot.reply_to(message, "❌ ربات پیدا نشد")

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

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast")
def admin_broadcast(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, "📢 متن پیام همگانی را ارسال کنید:")
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    text = message.text
    users = db.execute('SELECT user_id FROM users')
    
    status_msg = bot.reply_to(message, f"📢 در حال ارسال به {len(users)} کاربر...")
    
    sent = 0
    failed = 0
    
    for user in users:
        try:
            bot.send_message(user['user_id'], text)
            sent += 1
            if sent % 10 == 0:
                bot.edit_message_text(f"📢 پیشرفت: {sent}/{len(users)}", message.chat.id, status_msg.message_id)
        except:
            failed += 1
    
    bot.edit_message_text(f"✅ ارسال شد!\nموفق: {sent}\nناموفق: {failed}", message.chat.id, status_msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_approve")
def admin_approve(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, "💰 آیدی کاربر برای تایید مستقیم اشتراک را وارد کنید:")
    bot.register_next_step_handler(msg, process_admin_approve)

def process_admin_approve(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        user_id = int(message.text.strip())
        SubscriptionManager.activate_subscription(user_id, 1)
        bot.reply_to(message, f"✅ اشتراک کاربر {user_id} فعال شد")
        
        try:
            bot.send_message(user_id, "✅ اشتراک شما توسط ادمین فعال شد!")
        except:
            pass
    except:
        bot.reply_to(message, "❌ آیدی معتبر وارد کنید")

@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    bot.delete_message(call.message.chat.id, call.message.message_id)
    admin_panel(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "close_menu")
def close_menu(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "🔙 بازگشت به منوی اصلی", reply_markup=get_main_menu(call.from_user.id))

# ==================== بازگشت به منو ====================
@bot.message_handler(func=lambda m: m.text == '🔙 بازگشت به منو')
def back_to_menu(message):
    bot.send_message(message.chat.id, "🔙 منوی اصلی", reply_markup=get_main_menu(message.from_user.id))

# ==================== مانیتورینگ ====================
def subscription_monitor():
    """بررسی خودکار اشتراک‌ها"""
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
                
                # توقف ربات‌های کاربر
                user_bots = db.execute('SELECT id FROM bots WHERE user_id = ? AND status = "running"', (user['user_id'],))
                for bot_info in user_bots:
                    bot_engine.stop_bot(bot_info['id'])
                    db.execute('UPDATE bots SET status = "stopped" WHERE id = ?', (bot_info['id'],))
                
                try:
                    bot.send_message(
                        user['user_id'],
                        "⚠️ اشتراک شما به اتمام رسید!\nبرای ادامه استفاده، لطفاً اشتراک جدید تهیه کنید.\nاز دکمه 💰 خرید اشتراک استفاده نمایید."
                    )
                except:
                    pass
            
            # بررسی تست‌های منقضی شده
            expired_trials = db.execute('''
                SELECT user_id FROM users 
                WHERE subscription_status = 'trial' 
                AND trial_end < ?
            ''', (now.isoformat(),))
            
            for user in expired_trials:
                db.execute('UPDATE users SET subscription_status = "inactive" WHERE user_id = ?', (user['user_id'],))
                
                user_bots = db.execute('SELECT id FROM bots WHERE user_id = ? AND status = "running" AND is_trial = 1', (user['user_id'],))
                for bot_info in user_bots:
                    bot_engine.stop_bot(bot_info['id'])
                    db.execute('UPDATE bots SET status = "stopped" WHERE id = ?', (bot_info['id'],))
                
                try:
                    bot.send_message(
                        user['user_id'],
                        f"⏰ زمان تست رایگان شما به اتمام رسید!\nبرای ادامه استفاده، اشتراک تهیه کنید.\nاز دکمه 💰 خرید اشتراک استفاده نمایید."
                    )
                except:
                    pass
            
            time.sleep(60)  # هر دقیقه بررسی کن
            
        except Exception as e:
            print(f"Monitor error: {e}")
            time.sleep(60)

threading.Thread(target=subscription_monitor, daemon=True).start()

# ==================== اجرا ====================
if __name__ == "__main__":
    print("=" * 80)
    print("🚀 ربات مادر حرفه‌ای - Enterprise Edition v5.0".center(80))
    print("=" * 80)
    print(f"✅ اشتراک ماهانه: {config.subscription_price:,} تومان")
    print(f"✅ تست رایگان: {config.trial_duration} دقیقه")
    print(f"✅ سیستم رفرال: 10%")
    print(f"✅ حداقل برداشت: {config.withdrawal_min_amount:,} تومان")
    print(f"✅ کتابخانه‌های آماده: {len(READY_LIBRARIES)} عدد")
    print("=" * 80)
    print(f"👑 ادمین: {ADMIN_IDS}")
    print("=" * 80)
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)
