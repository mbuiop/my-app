#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ربات مادر نهایی - نسخه 9.0
با سیستم اشتراک، پنل مدیریت کامل، و امنیت بالا
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
from pathlib import Path
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
import asyncio
from functools import wraps

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
BOT_TOKEN = "7685135237:AAEmsHktRw9cEqrHTkCoPZk-fBimK7TDjOo"
bot = telebot.TeleBot(BOT_TOKEN, num_threads=100)
bot.delete_webhook()

# ==================== آیدی ادمین ====================
ADMIN_IDS = [327855654]

# ==================== تنظیمات پیش‌فرض (قابل تغییر توسط ادمین) ====================
class Config:
    def __init__(self):
        self.welcome_text = """🚀 به ربات سازنده ربات خوش آمدید!

👤 کاربر عزیز، شما می‌توانید با خرید اشتراک، ربات تلگرامی خود را بسازید.

📌 نحوه کار:
1️⃣ خرید اشتراک
2️⃣ ارسال فایل ربات برای بررسی امنیتی
3️⃣ پس از تایید فایل و فیش، ربات ساخته می‌شود

💰 هر اشتراک = ۱ ربات
برای ربات دوم نیاز به خرید اشتراک جدید دارید

@{} - پشتیبانی"""
        
        self.price = 2000000
        self.card_number = "5892101187322777"
        self.card_holder = "مرتضی نیکخو خنجری"
        
        self.guide_text = """📚 راهنمای استفاده

1️⃣ خرید اشتراک:
   • مبلغ: {} تومان
   • شماره کارت: {}
   • به نام: {}

2️⃣ ارسال فایل:
   • فایل ربات خود را برای پشتیبانی بفرستید
   • پس از بررسی امنیتی، به شما اعلام می‌شود

3️⃣ ساخت ربات:
   • پس از تایید فایل و فیش، ربات شما ساخته می‌شود
   • لینک ربات و اطلاعات آن به شما ارسال می‌شود

⚠️ نکات امنیتی:
• فایل شما توسط تیم بررسی می‌شود
• کدهای مخرب مجاز نیستند
• اطلاعات شما محفوظ است

@{} - پشتیبانی"""
    
    def load_from_db(self):
        try:
            with get_db() as conn:
                config_data = conn.execute("SELECT key, value FROM config").fetchall()
                for row in config_data:
                    if row['key'] == 'welcome_text':
                        self.welcome_text = row['value']
                    elif row['key'] == 'price':
                        self.price = int(row['value'])
                    elif row['key'] == 'card_number':
                        self.card_number = row['value']
                    elif row['key'] == 'card_holder':
                        self.card_holder = row['value']
                    elif row['key'] == 'guide_text':
                        self.guide_text = row['value']
        except Exception as e:
            logger.error(f"خطا در بارگذاری تنظیمات: {e}")
    
    def save_to_db(self):
        with get_db() as conn:
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('welcome_text', self.welcome_text))
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('price', str(self.price)))
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('card_number', self.card_number))
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('card_holder', self.card_holder))
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('guide_text', self.guide_text))
            conn.commit()

config = Config()

# ==================== لاگینگ پیشرفته ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            os.path.join(LOGS_DIR, 'mother_bot.log'),
            maxBytes=10485760,
            backupCount=20
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== دیتابیس فوق پیشرفته ====================
DB_PATH = os.path.join(DB_DIR, 'mother_bot.db')

@contextmanager
def get_db():
    """مدیریت اتصال دیتابیس با بهینه‌سازی برای میلیون‌ها کاربر"""
    conn = sqlite3.connect(DB_PATH, timeout=120, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA cache_size=-131072")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA mmap_size=268435456")
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# ایجاد جداول با ایندکس‌های بهینه
with get_db() as conn:
    # جدول تنظیمات
    conn.execute('''
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # جدول کاربران (بهینه شده برای میلیون‌ها رکورد)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            phone TEXT,
            active_subscription INTEGER DEFAULT 0,
            subscription_expire TIMESTAMP,
            total_bots INTEGER DEFAULT 0,
            created_at TIMESTAMP,
            last_active TIMESTAMP
        )
    ''')
    
    # جدول اشتراک‌ها
    conn.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            subscription_code TEXT UNIQUE,
            status TEXT DEFAULT 'pending',
            amount INTEGER,
            created_at TIMESTAMP,
            paid_at TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    ''')
    
    # جدول فایل‌های در انتظار بررسی
    conn.execute('''
        CREATE TABLE IF NOT EXISTS pending_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            subscription_id INTEGER,
            file_path TEXT,
            file_name TEXT,
            file_hash TEXT,
            status TEXT DEFAULT 'pending',
            submitted_at TIMESTAMP,
            reviewed_at TIMESTAMP,
            review_note TEXT,
            security_score INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(user_id),
            FOREIGN KEY(subscription_id) REFERENCES subscriptions(id)
        )
    ''')
    
    # جدول ربات‌ها
    conn.execute('''
        CREATE TABLE IF NOT EXISTS bots (
            id TEXT PRIMARY KEY,
            user_id INTEGER,
            subscription_id INTEGER,
            token TEXT,
            name TEXT,
            username TEXT,
            file_path TEXT,
            file_hash TEXT,
            pid INTEGER,
            status TEXT DEFAULT 'stopped',
            created_at TIMESTAMP,
            last_active TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY(subscription_id) REFERENCES subscriptions(id)
        )
    ''')
    
    # جدول فیش‌های واریزی
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
            reviewed_at TIMESTAMP,
            reviewed_by INTEGER
        )
    ''')
    
    # جدول تراکنش‌ها برای گزارش مالی
    conn.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,
            amount INTEGER,
            description TEXT,
            created_at TIMESTAMP
        )
    ''')
    
    # جدول لاگ فعالیت‌ها
    conn.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            details TEXT,
            ip TEXT,
            created_at TIMESTAMP
        )
    ''')
    
    # ایجاد ایندکس‌ها برای سرعت فوق‌العاده
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_subscription ON users(active_subscription, subscription_expire)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_user_status ON subscriptions(user_id, status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pending_files_status ON pending_files(status, submitted_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_bots_user_status ON bots(user_id, status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_receipts_status ON receipts(status, created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id, created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_logs_user ON activity_logs(user_id, created_at)")
    
    conn.commit()

# بارگذاری تنظیمات
config.load_from_db()

# ==================== موتور پیشرفته امنیتی ====================
class SecurityEngine:
    """موتور بررسی امنیتی فایل‌ها"""
    
    DANGEROUS_PATTERNS = [
        (r'os\.system\s*\(', "استفاده از os.system (اجرای دستورات سیستم)", 50),
        (r'subprocess\.', "استفاده از subprocess (اجرای فرآیند)", 40),
        (r'eval\s*\(', "استفاده از eval (اجرای کد داینامیک)", 60),
        (r'exec\s*\(', "استفاده از exec (اجرای کد داینامیک)", 60),
        (r'__import__\s*\(', "import پویا", 30),
        (r'open\s*\([^)]*[\'"]w', "نوشتن در فایل", 25),
        (r'requests\.', "درخواست شبکه", 10),
        (r'socket\.', "اتصال شبکه", 35),
        (r'base64\.b64decode', "رمزگشایی base64", 20),
        (r'compile\s*\(', "کامپایل کد", 45),
        (r'globals\s*\(\s*\)', "دسترسی به globals", 25),
        (r'__builtins__', "دسترسی به builtins", 30),
    ]
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=10)
    
    def analyze_code(self, code):
        """تحلیل امنیتی کد"""
        score = 100
        warnings = []
        
        for pattern, desc, penalty in self.DANGEROUS_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                score -= penalty
                warnings.append(f"⚠️ {desc} (-{penalty})")
        
        # بررسی حجم کد
        lines = len(code.split('\n'))
        if lines > 5000:
            score -= 20
            warnings.append(f"⚠️ حجم کد زیاد: {lines} خط (-20)")
        
        # بررسی توکن
        token_patterns = [
            r'[0-9]{8,10}:[A-Za-z0-9_-]{35}',
            r'\d{9,10}:[\w-]{35}'
        ]
        has_token = False
        for pattern in token_patterns:
            if re.search(pattern, code):
                has_token = True
                break
        
        if not has_token:
            score -= 30
            warnings.append("⚠️ توکن ربات در کد پیدا نشد (-30)")
        
        return {
            'score': max(0, score),
            'warnings': warnings,
            'is_safe': score >= 60,
            'has_token': has_token
        }
    
    def extract_token(self, code):
        """استخراج توکن از کد با روش‌های پیشرفته"""
        patterns = [
            r'token\s*=\s*["\']([^"\']+)["\']',
            r'TOKEN\s*=\s*["\']([^"\']+)["\']',
            r'API_TOKEN\s*=\s*["\']([^"\']+)["\']',
            r'BOT_TOKEN\s*=\s*["\']([^"\']+)["\']',
            r'bot\s*=\s*telebot\.TeleBot\(\s*["\']([^"\']+)["\']\s*\)',
            r'Bot\(\s*["\']([^"\']+)["\']\s*\)',
            r'Client\(\s*["\']([^"\']+)["\']\s*\)',
            r'[\'"]([0-9]{8,10}:[A-Za-z0-9_-]{35})[\'"]',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, code, re.IGNORECASE)
            if match:
                token = match.group(1)
                if self.validate_token(token):
                    return token
        return None
    
    def validate_token(self, token):
        """اعتبارسنجی توکن ربات تلگرام"""
        try:
            response = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def calculate_file_hash(self, file_path):
        """محاسبه هش فایل برای جلوگیری از آپلود تکراری"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

security_engine = SecurityEngine()

# ==================== موتور اجرای ربات ====================
class BotExecutionEngine:
    """موتور اجرای پیشرفته ربات‌ها"""
    
    def __init__(self):
        self.running_bots = {}
        self.lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=50)
    
    def prepare_code(self, code, token):
        """آماده‌سازی کد برای اجرا"""
        # اضافه کردن هندلرهای لازم
        if 'if __name__ == "__main__"' not in code:
            code += '\n\nif __name__ == "__main__":\n    print("✅ ربات در حال اجراست...")\n    try:\n        bot.infinity_polling(timeout=30)\n    except Exception as e:\n        print(f"خطا: {e}")\n'
        
        return code
    
    def run_bot(self, bot_id, code, token):
        """اجرای ربات در محیط ایزوله"""
        try:
            bot_dir = os.path.join(RUNNING_DIR, bot_id)
            os.makedirs(bot_dir, exist_ok=True)
            
            code = self.prepare_code(code, token)
            
            code_path = os.path.join(bot_dir, 'bot.py')
            with open(code_path, 'w', encoding='utf-8') as f:
                f.write(code)
            
            log_file = os.path.join(bot_dir, 'bot.log')
            
            process = subprocess.Popen(
                [sys.executable, code_path],
                stdout=open(log_file, 'a'),
                stderr=subprocess.STDOUT,
                cwd=bot_dir,
                start_new_session=True,
                preexec_fn=os.setsid if os.name != 'nt' else None
            )
            
            time.sleep(3)
            
            if process.poll() is None:
                with self.lock:
                    self.running_bots[bot_id] = {
                        'process': process,
                        'pid': process.pid,
                        'dir': bot_dir,
                        'start_time': time.time()
                    }
                return process.pid, None
            else:
                error = ""
                if os.path.exists(log_file):
                    with open(log_file, 'r') as f:
                        error = f.read()[-500:]
                return None, error or "خطای ناشناخته"
                
        except Exception as e:
            return None, str(e)
    
    def stop_bot(self, bot_id):
        """توقف ربات"""
        with self.lock:
            if bot_id in self.running_bots:
                try:
                    pid = self.running_bots[bot_id]['pid']
                    if os.name != 'nt':
                        os.killpg(os.getpgid(pid), signal.SIGTERM)
                    else:
                        os.kill(pid, signal.SIGTERM)
                    time.sleep(1)
                    del self.running_bots[bot_id]
                    return True
                except:
                    pass
        return False
    
    def get_bot_status(self, bot_id, pid):
        """گرفتن وضعیت ربات"""
        with self.lock:
            if bot_id in self.running_bots:
                process = self.running_bots[bot_id]['process']
                if process.poll() is None:
                    return True
                else:
                    del self.running_bots[bot_id]
        return False

bot_engine = BotExecutionEngine()

# ==================== توابع دیتابیس ====================

def create_user(user_id, username, first_name, last_name, phone=None):
    """ایجاد کاربر جدید"""
    try:
        with get_db() as conn:
            now = datetime.now().isoformat()
            conn.execute('''
                INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, phone, created_at, last_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name, phone, now, now))
            
            conn.execute('UPDATE users SET last_active = ? WHERE user_id = ?', (now, user_id))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"خطا در create_user: {e}")
        return False

def get_user(user_id):
    """گرفتن اطلاعات کاربر"""
    try:
        with get_db() as conn:
            user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
            return dict(user) if user else None
    except:
        return None

def can_create_bot(user_id):
    """بررسی امکان ساخت ربات جدید (فقط ۱ ربات با هر اشتراک)"""
    try:
        with get_db() as conn:
            # تعداد ربات‌های ساخته شده با اشتراک فعال
            bots_count = conn.execute('''
                SELECT COUNT(*) FROM bots 
                WHERE user_id = ? AND subscription_id IN (
                    SELECT id FROM subscriptions WHERE user_id = ? AND status = 'active'
                )
            ''', (user_id, user_id)).fetchone()[0]
            
            return bots_count == 0
    except:
        return False

def has_active_subscription(user_id):
    """بررسی اشتراک فعال کاربر"""
    try:
        with get_db() as conn:
            user = conn.execute('SELECT active_subscription, subscription_expire FROM users WHERE user_id = ?', (user_id,)).fetchone()
            if user and user['active_subscription'] == 1:
                if user['subscription_expire']:
                    expire = datetime.fromisoformat(user['subscription_expire'])
                    if expire > datetime.now():
                        return True
                    else:
                        conn.execute('UPDATE users SET active_subscription = 0 WHERE user_id = ?', (user_id,))
                        conn.commit()
                        return False
                return True
            return False
    except:
        return False

def create_subscription(user_id, amount):
    """ایجاد اشتراک جدید"""
    try:
        with get_db() as conn:
            subscription_code = hashlib.md5(f"{user_id}_{time.time()}_{secrets.token_hex(8)}".encode()).hexdigest()[:16].upper()
            now = datetime.now().isoformat()
            
            conn.execute('''
                INSERT INTO subscriptions (user_id, subscription_code, amount, created_at, status)
                VALUES (?, ?, ?, ?, 'pending')
            ''', (user_id, subscription_code, amount, now))
            conn.commit()
            
            sub_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            return sub_id, subscription_code
    except Exception as e:
        logger.error(f"خطا در create_subscription: {e}")
        return None, None

def activate_subscription(subscription_id):
    """فعال کردن اشتراک"""
    try:
        with get_db() as conn:
            sub = conn.execute('SELECT * FROM subscriptions WHERE id = ?', (subscription_id,)).fetchone()
            if sub:
                expire_time = (datetime.now() + timedelta(days=365)).isoformat()
                conn.execute('''
                    UPDATE users SET active_subscription = 1, subscription_expire = ?
                    WHERE user_id = ?
                ''', (expire_time, sub['user_id']))
                
                conn.execute('''
                    UPDATE subscriptions SET status = 'active', paid_at = ?
                    WHERE id = ?
                ''', (datetime.now().isoformat(), subscription_id))
                conn.commit()
                return True
            return False
    except:
        return False

def get_user_bots(user_id):
    """دریافت ربات‌های کاربر"""
    try:
        with get_db() as conn:
            bots = conn.execute('SELECT * FROM bots WHERE user_id = ? ORDER BY created_at DESC', (user_id,)).fetchall()
            return [dict(bot) for bot in bots]
    except:
        return []

def add_bot(user_id, subscription_id, bot_id, token, name, username, file_path, file_hash, pid=None):
    """افزودن ربات به دیتابیس"""
    try:
        with get_db() as conn:
            now = datetime.now().isoformat()
            conn.execute('''
                INSERT INTO bots (id, user_id, subscription_id, token, name, username, file_path, file_hash, pid, status, created_at, last_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'running', ?, ?)
            ''', (bot_id, user_id, subscription_id, token, name, username, file_path, file_hash, pid, now, now))
            
            conn.execute('UPDATE users SET total_bots = total_bots + 1, active_subscription = 0 WHERE user_id = ?', (user_id,))
            conn.commit()
            return True
    except:
        return False

def get_pending_file(user_id):
    """دریافت فایل در انتظار کاربر"""
    try:
        with get_db() as conn:
            pending = conn.execute('''
                SELECT * FROM pending_files 
                WHERE user_id = ? AND status = 'pending'
                ORDER BY submitted_at DESC LIMIT 1
            ''', (user_id,)).fetchone()
            return dict(pending) if pending else None
    except:
        return None

def save_pending_file(user_id, subscription_id, file_path, file_name, file_hash, security_score):
    """ذخیره فایل در انتظار"""
    try:
        with get_db() as conn:
            now = datetime.now().isoformat()
            conn.execute('''
                INSERT INTO pending_files (user_id, subscription_id, file_path, file_name, file_hash, security_score, submitted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, subscription_id, file_path, file_name, file_hash, security_score, now))
            conn.commit()
            return True
    except:
        return False

def delete_bot(bot_id, user_id):
    """حذف کامل ربات"""
    try:
        with get_db() as conn:
            bot = conn.execute('SELECT * FROM bots WHERE id = ? AND user_id = ?', (bot_id, user_id)).fetchone()
            if not bot:
                return False
            
            if bot['pid']:
                bot_engine.stop_bot(bot_id)
            
            if bot['file_path'] and os.path.exists(bot['file_path']):
                os.remove(bot['file_path'])
            
            conn.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
            conn.commit()
            return True
    except:
        return False

def log_activity(user_id, action, details="", ip=""):
    """ثبت لاگ فعالیت"""
    try:
        with get_db() as conn:
            conn.execute('''
                INSERT INTO activity_logs (user_id, action, details, ip, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, action, details, ip, datetime.now().isoformat()))
            conn.commit()
    except:
        pass

def add_transaction(user_id, type, amount, description):
    """ثبت تراکنش مالی"""
    try:
        with get_db() as conn:
            conn.execute('''
                INSERT INTO transactions (user_id, type, amount, description, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, type, amount, description, datetime.now().isoformat()))
            conn.commit()
    except:
        pass

# ==================== منوها ====================

def get_main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        types.KeyboardButton('🛒 خرید اشتراک'),
        types.KeyboardButton('📤 ارسال فایل ربات'),
        types.KeyboardButton('🤖 ربات‌های من'),
        types.KeyboardButton('📚 راهنما'),
        types.KeyboardButton('📞 پشتیبانی')
    ]
    markup.add(*buttons)
    return markup

def get_admin_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        types.KeyboardButton('👑 پنل ادمین'),
        types.KeyboardButton('🛒 خرید اشتراک'),
        types.KeyboardButton('📤 ارسال فایل ربات'),
        types.KeyboardButton('🤖 ربات‌های من'),
        types.KeyboardButton('📚 راهنما'),
        types.KeyboardButton('📞 پشتیبانی')
    ]
    markup.add(*buttons)
    return markup

# ==================== هندلر استارت ====================

@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    
    create_user(user_id, username, first_name, last_name)
    log_activity(user_id, "start", "کاربر وارد شد")
    
    bot_username = bot.get_me().username
    welcome = config.welcome_text.format(bot_username)
    
    is_admin = user_id in ADMIN_IDS
    markup = get_admin_menu() if is_admin else get_main_menu()
    
    bot.send_message(message.chat.id, welcome, reply_markup=markup)

# ==================== خرید اشتراک ====================

@bot.message_handler(func=lambda m: m.text == '🛒 خرید اشتراک')
def buy_subscription(message):
    user_id = message.from_user.id
    
    if has_active_subscription(user_id):
        bot.send_message(
            message.chat.id,
            "✅ شما اشتراک فعال دارید!\n\n"
            "📤 لطفاً فایل ربات خود را ارسال کنید تا پس از بررسی ساخته شود.\n\n"
            "⚠️ توجه: با هر اشتراک فقط می‌توانید ۱ ربات بسازید."
        )
        return
    
    sub_id, sub_code = create_subscription(user_id, config.price)
    if not sub_id:
        bot.send_message(message.chat.id, "❌ خطا در ایجاد اشتراک. لطفاً دوباره تلاش کنید.")
        return
    
    text = f"""💰 خرید اشتراک

مبلغ: {config.price:,} تومان
شماره کارت: {config.card_number}
به نام: {config.card_holder}

🆔 کد اشتراک: `{sub_code}`

📌 مراحل:
1️⃣ مبلغ را به کارت فوق واریز کنید
2️⃣ کد اشتراک را در رسید یادداشت کنید
3️⃣ تصویر فیش را ارسال کنید

⚠️ پس از تایید فیش، می‌توانید فایل ربات خود را ارسال کنید
⚠️ هر اشتراک فقط برای ساخت ۱ ربات قابل استفاده است
"""
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")
    log_activity(user_id, "create_subscription", f"کد: {sub_code}")

# ==================== رسید واریزی ====================

@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    
    # بررسی وجود اشتراک در انتظار
    with get_db() as conn:
        pending_sub = conn.execute('''
            SELECT * FROM subscriptions 
            WHERE user_id = ? AND status = 'pending'
            ORDER BY created_at DESC LIMIT 1
        ''', (user_id,)).fetchone()
    
    if not pending_sub:
        bot.reply_to(message, "❌ شما اشتراک در انتظار پرداختی ندارید.\nاز منوی خرید اشتراق استفاده کنید.")
        return
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        payment_code = hashlib.md5(f"{user_id}_{time.time()}_{secrets.token_hex(4)}".encode()).hexdigest()[:12].upper()
        receipt_path = os.path.join(RECEIPTS_DIR, f"{user_id}_{payment_code}.jpg")
        
        with open(receipt_path, 'wb') as f:
            f.write(downloaded_file)
        
        with get_db() as conn:
            conn.execute('''
                INSERT INTO receipts (user_id, subscription_id, amount, receipt_path, payment_code, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, pending_sub['id'], config.price, receipt_path, payment_code, datetime.now().isoformat()))
            conn.commit()
        
        bot.reply_to(
            message,
            f"✅ فیش دریافت شد\n"
            f"💰 مبلغ: {config.price:,} تومان\n"
            f"🆔 کد پیگیری: {payment_code}\n\n"
            f"⏳ پس از بررسی توسط ادمین، اشتراک شما فعال می‌شود.\n"
            f"سپس می‌توانید فایل ربات خود را ارسال کنید."
        )
        
        log_activity(user_id, "upload_receipt", f"کد: {payment_code}")
        
        for admin_id in ADMIN_IDS:
            try:
                bot.send_photo(
                    admin_id,
                    open(receipt_path, 'rb'),
                    caption=f"📸 فیش جدید\n"
                           f"👤 کاربر: {user_id}\n"
                           f"💰 مبلغ: {config.price:,} تومان\n"
                           f"🆔 کد: {payment_code}\n"
                           f"🆔 اشتراک: {pending_sub['subscription_code']}"
                )
            except:
                pass
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")

# ==================== ارسال فایل ربات ====================

@bot.message_handler(func=lambda m: m.text == '📤 ارسال فایل ربات')
def send_bot_file(message):
    user_id = message.from_user.id
    
    if not has_active_subscription(user_id):
        bot.send_message(
            message.chat.id,
            f"❌ شما اشتراک فعال ندارید!\n\n"
            f"💰 مبلغ اشتراک: {config.price:,} تومان\n"
            f"از منوی «خرید اشتراک» استفاده کنید."
        )
        return
    
    # بررسی محدودیت ساخت ربات (فقط ۱ ربات با هر اشتراک)
    if not can_create_bot(user_id):
        bot.send_message(
            message.chat.id,
            "❌ شما قبلاً با اشتراک فعال خود یک ربات ساخته‌اید!\n\n"
            "برای ساخت ربات دوم، نیاز به خرید اشتراک جدید دارید.\n"
            "از منوی «خرید اشتراک» استفاده کنید."
        )
        return
    
    # بررسی فایل در انتظار قبلی
    pending = get_pending_file(user_id)
    if pending:
        bot.send_message(
            message.chat.id,
            "⏳ شما قبلاً یک فایل ارسال کرده‌اید و در انتظار بررسی است.\n"
            "لطفاً صبر کنید تا ادمین آن را بررسی کند."
        )
        return
    
    bot.send_message(
        message.chat.id,
        "📤 لطفاً فایل `.py` ربات خود را ارسال کنید.\n\n"
        "⚠️ توجه:\n"
        "• فایل شما توسط تیم بررسی امنیتی می‌شود\n"
        "• پس از تایید، ربات شما ساخته خواهد شد\n"
        "• حجم فایل حداکثر ۱۰ مگابایت\n"
        "• هر اشتراک فقط برای ۱ ربات قابل استفاده است"
    )

@bot.message_handler(content_types=['document'])
def handle_bot_file(message):
    user_id = message.from_user.id
    
    if not has_active_subscription(user_id):
        bot.reply_to(message, "❌ شما اشتراک فعال ندارید!")
        return
    
    if not can_create_bot(user_id):
        bot.reply_to(message, "❌ شما قبلاً با این اشتراک ربات ساخته‌اید!")
        return
    
    pending = get_pending_file(user_id)
    if pending:
        bot.reply_to(message, "⏳ شما در انتظار بررسی فایل قبلی هستید.")
        return
    
    file_name = message.document.file_name
    
    if not file_name.endswith('.py'):
        bot.reply_to(message, "❌ فقط فایل‌های `.py` مجاز هستند!")
        return
    
    if message.document.file_size > 10 * 1024 * 1024:
        bot.reply_to(message, "❌ حجم فایل نباید بیشتر از ۱۰ مگابایت باشد!")
        return
    
    status_msg = bot.reply_to(message, "🔄 در حال دریافت و بررسی فایل...")
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        file_path = save_uploaded_file(user_id, downloaded_file, file_name)
        if not file_path:
            bot.edit_message_text("❌ خطا در ذخیره فایل", message.chat.id, status_msg.message_id)
            return
        
        # خواندن و تحلیل امنیتی
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        security_result = security_engine.analyze_code(code)
        
        # پیدا کردن اشتراک فعال
        with get_db() as conn:
            sub = conn.execute('''
                SELECT id FROM subscriptions 
                WHERE user_id = ? AND status = 'active'
                ORDER BY paid_at DESC LIMIT 1
            ''', (user_id,)).fetchone()
        
        if not sub:
            bot.edit_message_text("❌ اشتراک فعال پیدا نشد!", message.chat.id, status_msg.message_id)
            return
        
        file_hash = security_engine.calculate_file_hash(file_path)
        save_pending_file(user_id, sub['id'], file_path, file_name, file_hash, security_result['score'])
        
        # ارسال نتیجه به کاربر
        result_text = f"✅ فایل شما دریافت شد!\n\n"
        result_text += f"📄 نام: {file_name}\n"
        result_text += f"🛡️ امتیاز امنیتی: {security_result['score']}/100\n"
        
        if security_result['warnings']:
            result_text += f"\n⚠️ موارد مشاهده شده:\n"
            for w in security_result['warnings'][:5]:
                result_text += f"{w}\n"
        
        result_text += f"\n⏳ فایل شما برای بررسی دقیق‌تر به ادمین ارسال شد.\n"
        result_text += f"پس از تایید نهایی، ربات شما ساخته خواهد شد."
        
        bot.edit_message_text(result_text, message.chat.id, status_msg.message_id)
        
        # ارسال به ادمین
        pending_id = None
        with get_db() as conn:
            pending = conn.execute('SELECT id FROM pending_files WHERE user_id = ? AND status = "pending" ORDER BY submitted_at DESC LIMIT 1', (user_id,)).fetchone()
            if pending:
                pending_id = pending['id']
        
        for admin_id in ADMIN_IDS:
            try:
                with open(file_path, 'rb') as f:
                    bot.send_document(
                        admin_id,
                        f,
                        caption=f"📥 فایل جدید برای بررسی\n"
                               f"👤 کاربر: {user_id}\n"
                               f"📄 نام: {file_name}\n"
                               f"🛡️ امتیاز امنیتی: {security_result['score']}/100\n"
                               f"⚠️ هشدارها: {len(security_result['warnings'])}\n"
                               f"🔐 توکن: {'✅ دارد' if security_result['has_token'] else '❌ ندارد'}\n\n"
                               f"🆔 شناسه: {pending_id}\n\n"
                               f"✅ /approve_{pending_id} - تایید و ساخت ربات\n"
                               f"❌ /reject_{pending_id} - رد فایل"
                    )
            except Exception as e:
                logger.error(f"خطا در ارسال به ادمین: {e}")
        
        log_activity(user_id, "upload_bot_file", f"فایل: {file_name}, امتیاز: {security_result['score']}")
                
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)}", message.chat.id, status_msg.message_id)

def save_uploaded_file(user_id, file_data, file_name):
    """ذخیره فایل آپلود شده"""
    try:
        user_dir = os.path.join(PENDING_FILES_DIR, str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        
        timestamp = int(time.time())
        file_path = os.path.join(user_dir, f"{timestamp}_{file_name}")
        
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        return file_path
    except:
        return None

# ==================== ربات‌های من ====================

@bot.message_handler(func=lambda m: m.text == '🤖 ربات‌های من')
def my_bots(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما رباتی ندارید!\nبرای ساخت ربات، ابتدا اشتراک بخرید.")
        return
    
    for b in bots:
        is_running = bot_engine.get_bot_status(b['id'], b['pid']) if b['pid'] else False
        if not is_running and b['status'] == 'running':
            with get_db() as conn:
                conn.execute('UPDATE bots SET status = "stopped" WHERE id = ?', (b['id'],))
                conn.commit()
            b['status'] = 'stopped'
        
        status_emoji = "🟢" if is_running else "🔴"
        status_text = "در حال اجرا" if is_running else "متوقف"
        
        text = f"{status_emoji} **{b['name']}**\n"
        text += f"🔗 https://t.me/{b['username']}\n"
        text += f"🆔 `{b['id']}`\n"
        text += f"📊 وضعیت: {status_text}\n"
        text += f"📅 {b['created_at'][:10]}\n"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 اجرا/توقف", callback_data=f"toggle_{b['id']}"))
        markup.add(types.InlineKeyboardButton("🗑 حذف", callback_data=f"delete_{b['id']}"))
        
        bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

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
        if bot_engine.stop_bot(bot_id):
            with get_db() as conn:
                conn.execute('UPDATE bots SET status = "stopped" WHERE id = ?', (bot_id,))
                conn.commit()
            bot.answer_callback_query(call.id, "✅ ربات متوقف شد")
            bot.edit_message_text(f"✅ ربات {bot_info['name']} متوقف شد.", call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "❌ خطا در توقف!")
    else:
        try:
            with open(bot_info['file_path'], 'r', encoding='utf-8') as f:
                code = f.read()
            
            pid, error = bot_engine.run_bot(bot_id, code, bot_info['token'])
            
            if pid:
                with get_db() as conn:
                    conn.execute('UPDATE bots SET status = "running", pid = ? WHERE id = ?', (pid, bot_id))
                    conn.commit()
                bot.answer_callback_query(call.id, "✅ ربات اجرا شد")
                bot.edit_message_text(f"✅ ربات {bot_info['name']} اجرا شد.", call.message.chat.id, call.message.message_id)
            else:
                bot.answer_callback_query(call.id, f"❌ خطا: {error[:50] if error else 'نامشخص'}")
        except Exception as e:
            bot.answer_callback_query(call.id, f"❌ خطا: {str(e)[:50]}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
def delete_bot_callback(call):
    bot_id = call.data.replace('delete_', '')
    user_id = call.from_user.id
    
    if delete_bot(bot_id, user_id):
        bot.answer_callback_query(call.id, "✅ ربات حذف شد")
        bot.edit_message_text("🗑 ربات با موفقیت حذف شد.", call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ خطا در حذف")

# ==================== راهنما ====================

@bot.message_handler(func=lambda m: m.text == '📚 راهنما')
def guide(message):
    bot_username = bot.get_me().username
    guide_text = config.guide_text.format(config.price, config.card_number, config.card_holder, bot_username)
    bot.send_message(message.chat.id, guide_text)

# ==================== پشتیبانی ====================

@bot.message_handler(func=lambda m: m.text == '📞 پشتیبانی')
def support(message):
    bot.send_message(message.chat.id, "📞 پشتیبانی: @shahraghee13")

# ==================== پنل ادمین کامل ====================

@bot.message_handler(func=lambda m: m.text == '👑 پنل ادمین')
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ شما دسترسی ادمین ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📸 فیش‌ها", callback_data="admin_receipts"),
        types.InlineKeyboardButton("📥 فایل‌های در انتظار", callback_data="admin_pending_files"),
        types.InlineKeyboardButton("👥 کاربران", callback_data="admin_users"),
        types.InlineKeyboardButton("📊 آمار", callback_data="admin_stats"),
        types.InlineKeyboardButton("🤖 ربات‌ها", callback_data="admin_bots"),
        types.InlineKeyboardButton("💰 تراکنش‌ها", callback_data="admin_transactions"),
        types.InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings"),
        types.InlineKeyboardButton("🎁 تایید دستی", callback_data="admin_manual_sub"),
        types.InlineKeyboardButton("📋 لاگ فعالیت", callback_data="admin_logs"),
        types.InlineKeyboardButton("🔄 پشتیبان", callback_data="admin_backup"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    # آمار سریع
    with get_db() as conn:
        pending_payments = conn.execute('SELECT COUNT(*) FROM receipts WHERE status = "pending"').fetchone()[0]
        pending_files = conn.execute('SELECT COUNT(*) FROM pending_files WHERE status = "pending"').fetchone()[0]
        active_users = conn.execute('SELECT COUNT(*) FROM users WHERE active_subscription = 1').fetchone()[0]
    
    text = f"👑 پنل مدیریت\n\n"
    text += f"📸 فیش در انتظار: {pending_payments}\n"
    text += f"📥 فایل در انتظار: {pending_files}\n"
    text += f"✅ کاربران فعال: {active_users}\n"
    
    bot.send_message(message.chat.id, text, reply_markup=markup)

# ==================== تنظیمات ادمین ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_settings")
def admin_settings(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📝 تغییر متن خوش‌آمدگویی", callback_data="set_welcome"),
        types.InlineKeyboardButton("💰 تغییر قیمت", callback_data="set_price"),
        types.InlineKeyboardButton("💳 تغییر شماره کارت", callback_data="set_card"),
        types.InlineKeyboardButton("👤 تغییر صاحب کارت", callback_data="set_holder"),
        types.InlineKeyboardButton("📚 تغییر متن راهنما", callback_data="set_guide"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    bot.edit_message_text(
        f"⚙️ تنظیمات:\n\n"
        f"💰 قیمت فعلی: {config.price:,} تومان\n"
        f"💳 شماره کارت: {config.card_number}\n"
        f"👤 صاحب کارت: {config.card_holder}",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "set_welcome")
def set_welcome(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "📝 متن جدید خوش‌آمدگویی را ارسال کنید:\n(از {} برای نام ربات استفاده کنید)\n\nمتن فعلی:\n" + config.welcome_text[:200])
    bot.register_next_step_handler(msg, process_set_welcome)

def process_set_welcome(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    config.welcome_text = message.text
    config.save_to_db()
    bot.reply_to(message, "✅ متن خوش‌آمدگویی با موفقیت تغییر کرد!")

@bot.callback_query_handler(func=lambda call: call.data == "set_price")
def set_price(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, f"💰 قیمت جدید را به تومان وارد کنید:\n(قیمت فعلی: {config.price:,} تومان)\nمثال: 250000")
    bot.register_next_step_handler(msg, process_set_price)

def process_set_price(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        new_price = int(message.text.strip())
        if new_price <= 0:
            raise ValueError
        config.price = new_price
        config.save_to_db()
        bot.reply_to(message, f"✅ قیمت با موفقیت به {new_price:,} تومان تغییر کرد!")
    except:
        bot.reply_to(message, "❌ قیمت نامعتبر! لطفاً یک عدد معتبر وارد کنید.")

@bot.callback_query_handler(func=lambda call: call.data == "set_card")
def set_card(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, f"💳 شماره کارت جدید را وارد کنید:\n(شماره فعلی: {config.card_number})")
    bot.register_next_step_handler(msg, process_set_card)

def process_set_card(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    card = message.text.strip().replace(" ", "")
    if len(card) >= 16 and card.isdigit():
        config.card_number = card
        config.save_to_db()
        bot.reply_to(message, f"✅ شماره کارت با موفقیت به {card} تغییر کرد!")
    else:
        bot.reply_to(message, "❌ شماره کارت نامعتبر! لطفاً یک شماره ۱۶ رقمی وارد کنید.")

@bot.callback_query_handler(func=lambda call: call.data == "set_holder")
def set_holder(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, f"👤 نام صاحب کارت جدید را وارد کنید:\n(نام فعلی: {config.card_holder})")
    bot.register_next_step_handler(msg, process_set_holder)

def process_set_holder(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    config.card_holder = message.text.strip()
    config.save_to_db()
    bot.reply_to(message, f"✅ نام صاحب کارت با موفقیت به {config.card_holder} تغییر کرد!")

@bot.callback_query_handler(func=lambda call: call.data == "set_guide")
def set_guide(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "📚 متن جدید راهنما را ارسال کنید:\n(از {} برای قیمت، {} برای شماره کارت، {} برای صاحب کارت، و {} برای نام ربات استفاده کنید)\n\nمتن فعلی:\n" + config.guide_text[:200])
    bot.register_next_step_handler(msg, process_set_guide)

def process_set_guide(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    config.guide_text = message.text
    config.save_to_db()
    bot.reply_to(message, "✅ متن راهنما با موفقیت تغییر کرد!")

# ==================== مدیریت فیش‌ها ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_receipts")
def admin_receipts(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        receipts = conn.execute('''
            SELECT r.*, s.subscription_code 
            FROM receipts r
            JOIN subscriptions s ON r.subscription_id = s.id
            WHERE r.status = 'pending'
            ORDER BY r.created_at DESC
            LIMIT 20
        ''').fetchall()
    
    if not receipts:
        bot.send_message(call.message.chat.id, "📸 فیش در انتظاری وجود ندارد")
        return
    
    for r in receipts:
        text = f"📸 فیش #{r['id']}\n"
        text += f"👤 کاربر: {r['user_id']}\n"
        text += f"💰 مبلغ: {r['amount']:,} تومان\n"
        text += f"🆔 کد اشتراک: {r['subscription_code']}\n"
        text += f"🆔 کد پرداخت: {r['payment_code']}\n"
        text += f"📅 تاریخ: {r['created_at'][:10]}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_payment_{r['id']}"),
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
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    receipt_id = int(call.data.replace('approve_payment_', ''))
    
    with get_db() as conn:
        receipt = conn.execute('SELECT * FROM receipts WHERE id = ?', (receipt_id,)).fetchone()
        if receipt:
            conn.execute('UPDATE receipts SET status = "approved", reviewed_at = ?, reviewed_by = ? WHERE id = ?',
                        (datetime.now().isoformat(), call.from_user.id, receipt_id))
            conn.execute('UPDATE subscriptions SET status = "active", paid_at = ? WHERE id = ?',
                        (datetime.now().isoformat(), receipt['subscription_id']))
            
            expire_time = (datetime.now() + timedelta(days=365)).isoformat()
            conn.execute('''
                UPDATE users SET active_subscription = 1, subscription_expire = ?
                WHERE user_id = ?
            ''', (expire_time, receipt['user_id']))
            conn.commit()
            
            add_transaction(receipt['user_id'], "subscription", receipt['amount'], "خرید اشتراک")
            log_activity(receipt['user_id'], "subscription_activated", f"اشتراک فعال شد", "")
            
            try:
                bot.send_message(
                    receipt['user_id'],
                    f"✅ پرداخت شما تایید شد!\n"
                    f"اشتراک شما فعال شد.\n\n"
                    f"📤 حالا می‌توانید از منوی «ارسال فایل ربات» استفاده کنید.\n\n"
                    f"⚠️ توجه: با این اشتراک فقط می‌توانید ۱ ربات بسازید."
                )
            except:
                pass
    
    bot.answer_callback_query(call.id, "✅ پرداخت تایید شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_payment_'))
def reject_payment(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    receipt_id = int(call.data.replace('reject_payment_', ''))
    
    with get_db() as conn:
        receipt = conn.execute('SELECT * FROM receipts WHERE id = ?', (receipt_id,)).fetchone()
        if receipt:
            conn.execute('UPDATE receipts SET status = "rejected", reviewed_at = ?, reviewed_by = ? WHERE id = ?',
                        (datetime.now().isoformat(), call.from_user.id, receipt_id))
            conn.execute('DELETE FROM subscriptions WHERE id = ?', (receipt['subscription_id'],))
            conn.commit()
            
            log_activity(receipt['user_id'], "payment_rejected", f"پرداخت رد شد", "")
            
            try:
                bot.send_message(
                    receipt['user_id'],
                    f"❌ متاسفانه پرداخت شما تایید نشد.\n"
                    f"لطفاً با پشتیبانی تماس بگیرید: @shahraghee13"
                )
            except:
                pass
    
    bot.answer_callback_query(call.id, "❌ پرداخت رد شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== مدیریت فایل‌های در انتظار ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_pending_files")
def admin_pending_files(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        pending = conn.execute('''
            SELECT pf.*, u.username, u.first_name
            FROM pending_files pf
            JOIN users u ON pf.user_id = u.user_id
            WHERE pf.status = 'pending'
            ORDER BY pf.submitted_at DESC
            LIMIT 20
        ''').fetchall()
    
    if not pending:
        bot.send_message(call.message.chat.id, "📥 فایل در انتظاری وجود ندارد")
        return
    
    for p in pending:
        text = f"📥 فایل #{p['id']}\n"
        text += f"👤 کاربر: {p['user_id']}\n"
        text += f"👤 نام: {p['first_name']}\n"
        text += f"📄 فایل: {p['file_name']}\n"
        text += f"🛡️ امتیاز امنیتی: {p['security_score']}/100\n"
        text += f"📅 تاریخ: {p['submitted_at'][:10]}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید و ساخت", callback_data=f"approve_file_{p['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"reject_file_{p['id']}")
        )
        
        if os.path.exists(p['file_path']):
            with open(p['file_path'], 'rb') as f:
                bot.send_document(call.message.chat.id, f, caption=text, reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_file_'))
def approve_file(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    pending_id = int(call.data.replace('approve_file_', ''))
    
    with get_db() as conn:
        pending = conn.execute('''
            SELECT pf.*, s.user_id as sub_user_id
            FROM pending_files pf
            JOIN subscriptions s ON pf.subscription_id = s.id
            WHERE pf.id = ?
        ''', (pending_id,)).fetchone()
        
        if not pending:
            bot.answer_callback_query(call.id, "❌ فایل پیدا نشد!")
            return
        
        # خواندن فایل و استخراج توکن
        try:
            with open(pending['file_path'], 'r', encoding='utf-8') as f:
                code = f.read()
            
            token = security_engine.extract_token(code)
            if not token:
                bot.answer_callback_query(call.id, "❌ توکن در کد پیدا نشد!")
                return
            
            # بررسی توکن
            response = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
            if response.status_code != 200:
                bot.answer_callback_query(call.id, "❌ توکن معتبر نیست!")
                return
            
            bot_info = response.json()['result']
            bot_name = bot_info['first_name']
            bot_username = bot_info['username']
            
            # ساخت ربات
            bot_id = hashlib.md5(f"{pending['user_id']}_{token}_{time.time()}_{secrets.token_hex(4)}".encode()).hexdigest()[:12]
            
            pid, error = bot_engine.run_bot(bot_id, code, token)
            
            if pid:
                now = datetime.now().isoformat()
                file_hash = security_engine.calculate_file_hash(pending['file_path'])
                
                conn.execute('UPDATE pending_files SET status = "approved", reviewed_at = ? WHERE id = ?', (now, pending_id))
                conn.execute('''
                    INSERT INTO bots (id, user_id, subscription_id, token, name, username, file_path, file_hash, pid, status, created_at, last_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'running', ?, ?)
                ''', (bot_id, pending['user_id'], pending['subscription_id'], token, bot_name, bot_username, pending['file_path'], file_hash, pid, now, now))
                conn.execute('UPDATE users SET total_bots = total_bots + 1, active_subscription = 0 WHERE user_id = ?', (pending['user_id'],))
                conn.commit()
                
                add_transaction(pending['user_id'], "bot_created", 0, f"ساخت ربات {bot_name}")
                log_activity(pending['user_id'], "bot_created", f"ربات ساخته شد: {bot_name}", "")
                
                try:
                    bot.send_message(
                        pending['user_id'],
                        f"✅ ربات شما با موفقیت ساخته شد! 🎉\n\n"
                        f"🤖 نام: {bot_name}\n"
                        f"🔗 لینک: https://t.me/{bot_username}\n"
                        f"🆔 آیدی: `{bot_id}`\n\n"
                        f"📋 برای مشاهده و مدیریت ربات‌های خود از منوی «ربات‌های من» استفاده کنید.\n\n"
                        f"⚠️ توجه: برای ساخت ربات دوم نیاز به خرید اشتراک جدید دارید.",
                        parse_mode="Markdown"
                    )
                except:
                    pass
                
                bot.answer_callback_query(call.id, "✅ ربات ساخته شد")
                bot.delete_message(call.message.chat.id, call.message.message_id)
            else:
                bot.answer_callback_query(call.id, f"❌ خطا در اجرا: {error[:50] if error else 'نامشخص'}")
                
        except Exception as e:
            bot.answer_callback_query(call.id, f"❌ خطا: {str(e)[:50]}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_file_'))
def reject_file_callback(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    pending_id = int(call.data.replace('reject_file_', ''))
    
    msg = bot.send_message(call.message.chat.id, "❌ دلیل رد فایل را وارد کنید:")
    bot.register_next_step_handler(msg, lambda m: process_reject_file(m, pending_id, call))

def process_reject_file(message, pending_id, original_call):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    reason = message.text
    
    with get_db() as conn:
        pending = conn.execute('SELECT user_id FROM pending_files WHERE id = ?', (pending_id,)).fetchone()
        if pending:
            conn.execute('UPDATE pending_files SET status = "rejected", reviewed_at = ?, review_note = ? WHERE id = ?',
                        (datetime.now().isoformat(), reason, pending_id))
            conn.execute('UPDATE users SET active_subscription = 0 WHERE user_id = ?', (pending['user_id'],))
            conn.commit()
            
            log_activity(pending['user_id'], "file_rejected", f"فایل رد شد: {reason}", "")
            
            try:
                bot.send_message(
                    pending['user_id'],
                    f"❌ متاسفانه فایل ربات شما تایید نشد.\n\n"
                    f"دلیل: {reason}\n\n"
                    f"لطفاً فایل را اصلاح کرده و دوباره ارسال کنید.\n"
                    f"اشتراک شما برای ارسال مجدد فعال است."
                )
            except:
                pass
    
    bot.reply_to(message, f"✅ فایل کاربر رد شد")
    try:
        bot.delete_message(original_call.message.chat.id, original_call.message.message_id)
    except:
        pass

# ==================== سایر بخش‌های ادمین ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_users")
def admin_users(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        users = conn.execute('''
            SELECT user_id, username, first_name, active_subscription, total_bots, created_at
            FROM users ORDER BY created_at DESC LIMIT 20
        ''').fetchall()
    
    text = "👥 ۲۰ کاربر آخر:\n\n"
    for u in users:
        status = "✅ فعال" if u['active_subscription'] else "❌ غیرفعال"
        text += f"🆔 {u['user_id']}\n"
        text += f"👤 {u['first_name']}\n"
        text += f"📊 {status} | 🤖 {u['total_bots']} ربات\n"
        text += f"📅 {u['created_at'][:10]}\n\n"
    
    bot.send_message(call.message.chat.id, text)

@bot.callback_query_handler(func=lambda call: call.data == "admin_bots")
def admin_bots(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        total_bots = conn.execute('SELECT COUNT(*) FROM bots').fetchone()[0]
        running_bots = conn.execute('SELECT COUNT(*) FROM bots WHERE status = "running"').fetchone()[0]
        
        latest_bots = conn.execute('''
            SELECT id, name, username, user_id, status, created_at
            FROM bots ORDER BY created_at DESC LIMIT 10
        ''').fetchall()
    
    text = f"🤖 آمار ربات‌ها\n\n"
    text += f"کل ربات‌ها: {total_bots}\n"
    text += f"در حال اجرا: {running_bots}\n\n"
    text += f"📋 ۱۰ ربات آخر:\n"
    
    for b in latest_bots:
        status = "🟢" if b['status'] == 'running' else "🔴"
        text += f"{status} {b['name']} - کاربر: {b['user_id']}\n"
    
    bot.send_message(call.message.chat.id, text)

@bot.callback_query_handler(func=lambda call: call.data == "admin_transactions")
def admin_transactions(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        total_income = conn.execute('SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type = "subscription"').fetchone()[0]
        total_subs = conn.execute('SELECT COUNT(*) FROM transactions WHERE type = "subscription"').fetchone()[0]
        
        latest = conn.execute('''
            SELECT * FROM transactions ORDER BY created_at DESC LIMIT 15
        ''').fetchall()
    
    text = f"💰 گزارش مالی\n\n"
    text += f"📊 مجموع درآمد: {total_income:,} تومان\n"
    text += f"📈 تعداد اشتراک‌ها: {total_subs}\n\n"
    text += f"📋 ۱۵ تراکنش آخر:\n"
    
    for t in latest:
        text += f"👤 {t['user_id']} - {t['amount']:,} تومان - {t['type']}\n"
        text += f"   📅 {t['created_at'][:10]}\n\n"
    
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
        running_bots = conn.execute('SELECT COUNT(*) FROM bots WHERE status = "running"').fetchone()[0]
        total_payments = conn.execute('SELECT COUNT(*) FROM receipts WHERE status = "approved"').fetchone()[0]
        pending_payments = conn.execute('SELECT COUNT(*) FROM receipts WHERE status = "pending"').fetchone()[0]
        pending_files = conn.execute('SELECT COUNT(*) FROM pending_files WHERE status = "pending"').fetchone()[0]
        total_amount = conn.execute('SELECT COALESCE(SUM(amount), 0) FROM receipts WHERE status = "approved"').fetchone()[0]
        
        today = datetime.now().date().isoformat()
        today_users = conn.execute('SELECT COUNT(*) FROM users WHERE date(created_at) = ?', (today,)).fetchone()[0]
        today_payments = conn.execute('SELECT COUNT(*) FROM receipts WHERE date(created_at) = ? AND status = "approved"', (today,)).fetchone()[0]
    
    text = f"📊 آمار کامل سیستم\n\n"
    text += f"👥 کاربران:\n"
    text += f"• کل: {total_users}\n"
    text += f"• امروز: {today_users}\n"
    text += f"• فعال: {active_subs}\n\n"
    
    text += f"🤖 ربات‌ها:\n"
    text += f"• کل: {total_bots}\n"
    text += f"• در حال اجرا: {running_bots}\n\n"
    
    text += f"💰 پرداخت‌ها:\n"
    text += f"• مجموع: {total_amount:,} تومان\n"
    text += f"• تایید شده: {total_payments}\n"
    text += f"• امروز: {today_payments}\n"
    text += f"• در انتظار: {pending_payments}\n\n"
    
    text += f"📥 فایل‌های در انتظار: {pending_files}"
    
    bot.send_message(call.message.chat.id, text)

@bot.callback_query_handler(func=lambda call: call.data == "admin_logs")
def admin_logs(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        logs = conn.execute('''
            SELECT * FROM activity_logs ORDER BY created_at DESC LIMIT 20
        ''').fetchall()
    
    if not logs:
        bot.send_message(call.message.chat.id, "📋 لاگی وجود ندارد")
        return
    
    text = "📋 ۲۰ فعالیت آخر:\n\n"
    for log in logs:
        text += f"👤 {log['user_id']} - {log['action']}\n"
        text += f"   📅 {log['created_at'][:16]}\n"
        if log['details']:
            text += f"   📝 {log['details'][:50]}\n"
        text += "\n"
    
    bot.send_message(call.message.chat.id, text)

@bot.callback_query_handler(func=lambda call: call.data == "admin_backup")
def admin_backup(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    try:
        backup_dir = os.path.join(BASE_DIR, "backups")
        os.makedirs(backup_dir, exist_ok=True)
        
        backup_file = os.path.join(backup_dir, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        shutil.copy2(DB_PATH, backup_file)
        
        bot.send_message(
            call.message.chat.id,
            f"✅ پشتیبان تهیه شد!\n"
            f"📁 مسیر: {backup_file}"
        )
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ خطا در تهیه پشتیبان: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_manual_sub")
def admin_manual_sub(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "💰 آیدی کاربر را برای تایید دستی اشتراک وارد کنید:")
    bot.register_next_step_handler(msg, process_manual_sub)

def process_manual_sub(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        user_id = int(message.text.strip())
        
        with get_db() as conn:
            # غیرفعال کردن اشتراک قبلی
            conn.execute('UPDATE users SET active_subscription = 0 WHERE user_id = ?', (user_id,))
            
            # ایجاد اشتراک جدید
            sub_code = hashlib.md5(f"manual_{user_id}_{time.time()}_{secrets.token_hex(4)}".encode()).hexdigest()[:16].upper()
            expire_time = (datetime.now() + timedelta(days=365)).isoformat()
            
            conn.execute('''
                INSERT INTO subscriptions (user_id, subscription_code, amount, status, paid_at)
                VALUES (?, ?, ?, 'active', ?)
            ''', (user_id, sub_code, config.price, datetime.now().isoformat()))
            
            sub_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            
            conn.execute('''
                UPDATE users SET active_subscription = 1, subscription_expire = ?
                WHERE user_id = ?
            ''', (expire_time, user_id))
            conn.commit()
            
            add_transaction(user_id, "subscription", config.price, "اشتراک دستی")
            log_activity(user_id, "manual_subscription", f"اشتراک دستی توسط ادمین", "")
            
            try:
                bot.send_message(
                    user_id,
                    f"✅ اشتراک شما به صورت دستی فعال شد!\n\n"
                    f"📤 حالا می‌توانید از منوی «ارسال فایل ربات» استفاده کنید.\n\n"
                    f"⚠️ توجه: با این اشتراک فقط می‌توانید ۱ ربات بسازید."
                )
            except:
                pass
        
        bot.reply_to(message, f"✅ اشتراک کاربر {user_id} فعال شد")
    except ValueError:
        bot.reply_to(message, "❌ آیدی باید عدد باشد")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call):
    user_id = call.from_user.id
    is_admin = user_id in ADMIN_IDS
    markup = get_admin_menu() if is_admin else get_main_menu()
    
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    bot.send_message(call.message.chat.id, "🚀 منوی اصلی:", reply_markup=markup)

# ==================== هندلرهای ادمین با کامند ====================

@bot.message_handler(commands=['approve'])
def approve_file_command(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "❌ استفاده: /approve [شناسه_فایل]")
        return
    
    try:
        pending_id = int(parts[1])
        
        with get_db() as conn:
            pending = conn.execute('SELECT * FROM pending_files WHERE id = ? AND status = "pending"', (pending_id,)).fetchone()
            if not pending:
                bot.reply_to(message, "❌ فایل پیدا نشد یا قبلاً بررسی شده")
                return
        
        # ادامه فرآیند تایید
        msg = bot.reply_to(message, "🔄 در حال ساخت ربات...")
        
        with open(pending['file_path'], 'r', encoding='utf-8') as f:
            code = f.read()
        
        token = security_engine.extract_token(code)
        if not token:
            bot.edit_message_text("❌ توکن در کد پیدا نشد!", message.chat.id, msg.message_id)
            return
        
        response = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
        if response.status_code != 200:
            bot.edit_message_text("❌ توکن معتبر نیست!", message.chat.id, msg.message_id)
            return
        
        bot_info = response.json()['result']
        bot_name = bot_info['first_name']
        bot_username = bot_info['username']
        
        bot_id = hashlib.md5(f"{pending['user_id']}_{token}_{time.time()}".encode()).hexdigest()[:12]
        
        pid, error = bot_engine.run_bot(bot_id, code, token)
        
        if pid:
            with get_db() as conn2:
                file_hash = security_engine.calculate_file_hash(pending['file_path'])
                now = datetime.now().isoformat()
                conn2.execute('UPDATE pending_files SET status = "approved", reviewed_at = ? WHERE id = ?', (now, pending_id))
                conn2.execute('''
                    INSERT INTO bots (id, user_id, subscription_id, token, name, username, file_path, file_hash, pid, status, created_at, last_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'running', ?, ?)
                ''', (bot_id, pending['user_id'], pending['subscription_id'], token, bot_name, bot_username, pending['file_path'], file_hash, pid, now, now))
                conn2.execute('UPDATE users SET total_bots = total_bots + 1, active_subscription = 0 WHERE user_id = ?', (pending['user_id'],))
                conn2.commit()
            
            bot.edit_message_text(f"✅ ربات ساخته شد!\n🤖 {bot_name}\n🔗 https://t.me/{bot_username}", message.chat.id, msg.message_id)
            
            try:
                bot.send_message(
                    pending['user_id'],
                    f"✅ ربات شما با موفقیت ساخته شد! 🎉\n\n"
                    f"🤖 نام: {bot_name}\n"
                    f"🔗 لینک: https://t.me/{bot_username}\n"
                    f"🆔 آیدی: `{bot_id}`",
                    parse_mode="Markdown"
                )
            except:
                pass
        else:
            bot.edit_message_text(f"❌ خطا در اجرا: {error}", message.chat.id, msg.message_id)
            
    except ValueError:
        bot.reply_to(message, "❌ شناسه نامعتبر")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")

@bot.message_handler(commands=['reject'])
def reject_file_command(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ استفاده: /reject [شناسه_فایل] [دلیل]")
        return
    
    try:
        pending_id = int(parts[1])
        reason = " ".join(parts[2:]) if len(parts) > 2 else "بدون دلیل"
        
        with get_db() as conn:
            pending = conn.execute('SELECT * FROM pending_files WHERE id = ? AND status = "pending"', (pending_id,)).fetchone()
            if pending:
                conn.execute('UPDATE pending_files SET status = "rejected", reviewed_at = ?, review_note = ? WHERE id = ?',
                            (datetime.now().isoformat(), reason, pending_id))
                conn.execute('UPDATE users SET active_subscription = 0 WHERE user_id = ?', (pending['user_id'],))
                conn.commit()
                
                try:
                    bot.send_message(
                        pending['user_id'],
                        f"❌ فایل ربات شما تایید نشد.\n\nدلیل: {reason}\n\nلطفاً فایل را اصلاح کنید."
                    )
                except:
                    pass
                
                bot.reply_to(message, f"✅ فایل رد شد\nدلیل: {reason}")
            else:
                bot.reply_to(message, "❌ فایل پیدا نشد")
    except ValueError:
        bot.reply_to(message, "❌ شناسه نامعتبر")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")

# ==================== اجرا ====================

if __name__ == "__main__":
    print("=" * 70)
    print("🚀 ربات مادر نهایی - نسخه 9.0 فوق قدرتمند")
    print("=" * 70)
    print(f"✅ دیتابیس: بهینه شده برای میلیون‌ها کاربر")
    print(f"✅ موتور امنیتی: فعال")
    print(f"✅ موتور اجرا: فعال")
    print(f"✅ ادمین‌ها: {ADMIN_IDS}")
    print(f"✅ قیمت فعلی: {config.price:,} تومان")
    print(f"✅ شماره کارت: {config.card_number}")
    print("=" * 70)
    print("🟢 ربات در حال اجراست...")
    print("=" * 70)
    
    # مانیتورینگ خودکار ربات‌ها
    def monitor_running_bots():
        while True:
            try:
                with get_db() as conn:
                    running = conn.execute('SELECT id, pid FROM bots WHERE status = "running"').fetchall()
                    for bot in running:
                        if not bot_engine.get_bot_status(bot['id'], bot['pid']):
                            conn.execute('UPDATE bots SET status = "stopped" WHERE id = ?', (bot['id'],))
                            conn.commit()
                            logger.info(f"ربات {bot['id']} متوقف شد")
                time.sleep(30)
            except Exception as e:
                logger.error(f"خطا در مانیتورینگ: {e}")
                time.sleep(60)
    
    monitor_thread = threading.Thread(target=monitor_running_bots, daemon=True)
    monitor_thread.start()
    
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=30)
        except Exception as e:
            logger.error(f"خطا در اجرا: {e}")
            time.sleep(5)