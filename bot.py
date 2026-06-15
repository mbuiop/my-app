#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ربات مادر نهایی نسخه 19.0 - نصب هوشمند و تضمینی تمام کتابخانه‌ها
"""

import telebot
from telebot import types
import sqlite3
import os
import subprocess
import sys
import time
import hashlib
import threading
import shutil
import re
import requests
import signal
import logging
import json
import zipfile
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from contextlib import contextmanager
import paramiko
from queue import Queue


def safe_edit_message(chat_id, message_id, text, parse_mode=None, reply_markup=None):
    """ویرایش امن پیام بدون خطای تکرار محتوا"""
    try:
        if not message_id:
            return False
        bot.edit_message_text(text, chat_id, message_id, parse_mode=parse_mode, reply_markup=reply_markup)
        return True
    except telebot.apihelper.ApiTelegramException as e:
        if "message is not modified" in str(e) or "can't parse entities" in str(e):
            return False
        elif "message to edit not found" in str(e):
            return False
        else:
            logger.warning(f"خطا در ویرایش پیام: {e}")
            return False
    except Exception as e:
        logger.warning(f"خطای غیرمنتظره: {e}")
        return False

# ==================== فایل PID ====================
PID_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot.pid")

def check_and_create_pid():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, 'r') as f:
                old_pid = int(f.read().strip())
            try:
                os.kill(old_pid, 0)
                print(f"❌ نمونه دیگری از ربات با PID {old_pid} در حال اجراست!")
                sys.exit(1)
            except:
                os.remove(PID_FILE)
        except:
            os.remove(PID_FILE)
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    print(f"✅ PID {os.getpid()} ذخیره شد")

# ==================== تنظیمات پایه ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "database")
FILES_DIR = os.path.join(BASE_DIR, "user_files")
RUNNING_DIR = os.path.join(BASE_DIR, "running_bots")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
RECEIPTS_DIR = os.path.join(BASE_DIR, "receipts")
PENDING_FILES_DIR = os.path.join(BASE_DIR, "pending_files")
SERVERS_DIR = os.path.join(BASE_DIR, "servers")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
REQUIREMENTS_DIR = os.path.join(BASE_DIR, "requirements")

for dir_path in [DB_DIR, FILES_DIR, RUNNING_DIR, LOGS_DIR, RECEIPTS_DIR, PENDING_FILES_DIR, SERVERS_DIR, BACKUP_DIR, REQUIREMENTS_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# ==================== توکن ربات مادر ====================
BOT_TOKEN = "8691128478:AAE7eZ0vo5kkFcvrerHt3vjw-mvJ3CqxpWE"

# ==================== آیدی ادمین ====================
ADMIN_IDS = [327855654]

# ==================== صف ساخت ====================
build_queue = Queue()
queue_thread_running = True
active_builds = {}

# ==================== دیتابیس کامل کتابخانه‌ها ====================
LIBRARY_MAPPING = {
    # کتابخانه‌های تلگرام
    "telebot": "pyTelegramBotAPI",
    "pyTelegramBotAPI": "pyTelegramBotAPI",
    "telethon": "telethon",
    "pyrogram": "pyrogram",
    "aiogram": "aiogram",
    "python-telegram-bot": "python-telegram-bot",
    "telegram": "python-telegram-bot",
    "telegram.ext": "python-telegram-bot",
    "telegram.bot": "python-telegram-bot",
    
    # کتابخانه‌های وب
    "requests": "requests",
    "aiohttp": "aiohttp",
    "httpx": "httpx",
    "urllib3": "urllib3",
    
    # کتابخانه‌های پردازش داده
    "numpy": "numpy",
    "pandas": "pandas",
    "scipy": "scipy",
    "scikit-learn": "scikit-learn",
    "sklearn": "scikit-learn",
    
    # کتابخانه‌های گرافیکی
    "matplotlib": "matplotlib",
    "seaborn": "seaborn",
    "plotly": "plotly",
    "PIL": "Pillow",
    "Pillow": "Pillow",
    "opencv-python": "opencv-python",
    "cv2": "opencv-python",
    
    # کتابخانه‌های وب اسکرپینگ
    "beautifulsoup4": "beautifulsoup4",
    "bs4": "beautifulsoup4",
    "lxml": "lxml",
    "selenium": "selenium",
    "scrapy": "scrapy",
    
    # کتابخانه‌های دیتابیس
    "sqlalchemy": "sqlalchemy",
    "pymongo": "pymongo",
    "redis": "redis",
    "psycopg2": "psycopg2-binary",
    "psycopg2-binary": "psycopg2-binary",
    
    # کتابخانه‌های صف و پردازش
    "celery": "celery",
    "kafka-python": "kafka-python",
    "rabbitmq": "pika",
    "pika": "pika",
    
    # کتابخانه‌های امنیتی
    "cryptography": "cryptography",
    "PyJWT": "PyJWT",
    "jwt": "PyJWT",
    "passlib": "passlib",
    "bcrypt": "bcrypt",
    
    # کتابخانه‌های کاربردی
    "python-dotenv": "python-dotenv",
    "pyyaml": "pyyaml",
    "loguru": "loguru",
    "rich": "rich",
    "tqdm": "tqdm",
    "click": "click",
    "colorama": "colorama",
    
    # کتابخانه‌های فارسی
    "jdatetime": "jdatetime",
    "persiantools": "persiantools",
    "persian": "persiantools",
    "emoji": "emoji",
    "hazm": "hazm",
    
    # کتابخانه‌های صوتی/تصویری
    "youtube-dl": "youtube-dl",
    "yt-dlp": "yt-dlp",
    "pytube": "pytube",
    "spotipy": "spotipy",
    "moviepy": "moviepy",
    "pydub": "pydub",
    "SpeechRecognition": "SpeechRecognition",
    "speech_recognition": "SpeechRecognition",
    "pyttsx3": "pyttsx3",
    "ffmpeg-python": "ffmpeg-python",
    
    # کتابخانه‌های اکسل و گزارش
    "openpyxl": "openpyxl",
    "xlrd": "xlrd",
    "xlwt": "xlwt",
    "reportlab": "reportlab",
    
    # کتابخانه‌های QR و بارکد
    "qrcode": "qrcode",
    "pyqrcode": "pyqrcode",
    
    # کتابخانه‌های ایمیل
    "yagmail": "yagmail",
    "smtplib": "secure-smtplib",
    
    # کتابخانه‌های تست
    "pytest": "pytest",
    "unittest": "unittest",  # استاندارد
    "black": "black",
    "flake8": "flake8",
    "mypy": "mypy",
    
    # کتابخانه‌های فریمورک
    "flask": "flask",
    "django": "django",
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "tornado": "tornado",
    
    # کتابخانه‌های async
    "asyncio": "asyncio",  # استاندارد
    "aiofiles": "aiofiles",
    "websockets": "websockets",
    
    # کتابخانه‌های SSH و شبکه
    "paramiko": "paramiko",
    "scp": "scp",
    "fabric": "fabric",
    
    # کتابخانه‌های سایر
    "jinja2": "jinja2",
    "markdown": "markdown",
    "weasyprint": "weasyprint",
    "playwright": "playwright",
    "selenium": "selenium",
}

# کتابخانه‌های استاندارد پایتون (نیاز به نصب ندارند)
STD_LIBRARIES = {
    'os', 'sys', 'time', 'datetime', 'json', 're', 'math', 'random',
    'string', 'collections', 'itertools', 'functools', 'typing',
    'argparse', 'logging', 'socket', 'ssl', 'hashlib', 'base64',
    'urllib', 'http', 'xml', 'html', 'csv', 'sqlite3', 'pickle',
    'copy', 'glob', 'gzip', 'zipfile', 'tarfile', 'shutil', 'tempfile',
    'threading', 'multiprocessing', 'subprocess', 'signal', 'getpass',
    'platform', 'inspect', 'traceback', 'warnings', 'contextlib',
    'abc', 'enum', 'struct', 'array', 'queue', 'heapq', 'bisect',
    'calendar', 'uuid', 'secrets', 'statistics', 'dataclasses',
    'asyncio', 'concurrent', 'unittest', 'doctest', 'pdb',
    'ctypes', 'gc', 'sysconfig', 'builtins', '__future__', '__main__',
    'pathlib', 'io', 'codecs', 'tokenize', 'keyword', 'ast', 'symtable',
    'pprint', 'reprlib', 'enum', 'weakref', 'copyreg', 'shelve',
    'dbm', 'cProfile', 'profile', 'pstats', 'filecmp', 'linecache',
    'textwrap', 'stringprep', 'readline', 'rlcompleter', 'telnetlib',
    'curses', 'pty', 'tty', 'fcntl', 'pipes', 'posix', 'grp', 'pwd',
    'spwd', 'resource', 'nis', 'termios', 'tty', 'syslog'
}

# لیست کتابخانه‌های محبوب برای نصب سریع
POPULAR_LIBRARIES = [
    "pyTelegramBotAPI", "python-telegram-bot", "telethon", "aiogram",
    "requests", "aiohttp", "beautifulsoup4", "selenium",
    "numpy", "pandas", "matplotlib", "seaborn",
    "Pillow", "opencv-python", "moviepy",
    "flask", "django", "fastapi",
    "sqlalchemy", "pymongo", "redis",
    "paramiko", "cryptography", "PyJWT",
    "jdatetime", "persiantools", "emoji",
    "youtube-dl", "pytube", "spotipy",
    "openpyxl", "reportlab", "qrcode",
    "loguru", "rich", "tqdm", "click"
]

# ==================== تنظیمات متون ====================
class Texts:
    def __init__(self):
        self.welcome_text = """🚀 به ربات سازنده ربات حرفه‌ای خوش آمدید!

👤 کاربر عزیز، شما می‌توانید با خرید اشتراک، ربات تلگرامی خود را بسازید.

📌 نحوه کار:
1️⃣ خرید اشتراک
2️⃣ ارسال فایل ربات (ZIP یا PY)
3️⃣ پس از تایید، ربات ساخته می‌شود

💰 هر اشتراک = ۱ ربات (به مدت ۳۰ روز)
🎁 سیستم رفرال: ۱۰٪ از درآمد دوستانتان به شما تعلق می‌گیرد

@{} - پشتیبانی"""
        
        self.subscription_text = """💰 خرید اشتراک

مبلغ: {} تومان
شماره کارت: {}
به نام: {}

🆔 کد: `{}`

📌 مراحل:
1️⃣ مبلغ را واریز کنید
2️⃣ کد اشتراک را در رسید یادداشت کنید
3️⃣ تصویر فیش را ارسال کنید

⏰ مدت اشتراک: {} روز
🎁 هر اشتراک = ۱ ربات
🎁 پاداش رفرال: ۱۰%"""
        
        self.guide_text = """📚 راهنمای کامل

1️⃣ خرید اشتراک:
   • مبلغ: {} تومان
   • شماره کارت: {}
   • به نام: {}

2️⃣ سیستم رفرال:
   • لینک اختصاصی خود را به دوستان بدهید
   • از هر خرید دوستان، ۱۰٪ به حساب شما واریز می‌شود
   • پس از رسیدن موجودی به ۲,۰۰۰,۰۰۰ تومان می‌توانید برداشت کنید

3️⃣ ارسال فایل:
   • می‌توانید فایل PY یا ZIP ارسال کنید
   • در صورت ZIP، تمام فایل‌ها استخراج می‌شوند
   • فایل اصلی باید bot.py یا main.py باشد

4️⃣ مدیریت ربات:
   • ربات شما به مدت ۳۰ روز فعال است
   • می‌توانید ربات را فعال/غیرفعال یا حذف کنید

@{} - پشتیبانی"""
    
    def load_from_db(self):
        try:
            with get_db() as conn:
                data = conn.execute("SELECT key, value FROM texts").fetchall()
                for row in data:
                    if row['key'] == 'welcome_text':
                        self.welcome_text = row['value']
                    elif row['key'] == 'subscription_text':
                        self.subscription_text = row['value']
                    elif row['key'] == 'guide_text':
                        self.guide_text = row['value']
        except:
            pass
    
    def save_to_db(self):
        with get_db() as conn:
            conn.execute("INSERT OR REPLACE INTO texts (key, value) VALUES (?, ?)", ('welcome_text', self.welcome_text))
            conn.execute("INSERT OR REPLACE INTO texts (key, value) VALUES (?, ?)", ('subscription_text', self.subscription_text))
            conn.execute("INSERT OR REPLACE INTO texts (key, value) VALUES (?, ?)", ('guide_text', self.guide_text))
            conn.commit()

texts = Texts()

# ==================== تنظیمات ====================
class Config:
    def __init__(self):
        self.price = 2000000
        self.card_number = "5892101187322777"
        self.card_holder = "مرتضی نیکخو خنجری"
        self.subscription_days = 30
        self.zarinpal_merchant = ""
        self.zarinpal_callback = ""
        self.auto_install_libs = True
    
    def load_from_db(self):
        try:
            with get_db() as conn:
                config_data = conn.execute("SELECT key, value FROM config").fetchall()
                for row in config_data:
                    if row['key'] == 'price':
                        self.price = int(row['value'])
                    elif row['key'] == 'card_number':
                        self.card_number = row['value']
                    elif row['key'] == 'card_holder':
                        self.card_holder = row['value']
                    elif row['key'] == 'subscription_days':
                        self.subscription_days = int(row['value'])
                    elif row['key'] == 'zarinpal_merchant':
                        self.zarinpal_merchant = row['value']
                    elif row['key'] == 'zarinpal_callback':
                        self.zarinpal_callback = row['value']
                    elif row['key'] == 'auto_install_libs':
                        self.auto_install_libs = row['value'] == 'True'
        except:
            pass
    
    def save_to_db(self):
        with get_db() as conn:
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('price', str(self.price)))
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('card_number', self.card_number))
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('card_holder', self.card_holder))
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('subscription_days', str(self.subscription_days)))
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('zarinpal_merchant', self.zarinpal_merchant))
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('zarinpal_callback', self.zarinpal_callback))
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('auto_install_libs', str(self.auto_install_libs)))
            conn.commit()

config = Config()

# ==================== لاگینگ ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(os.path.join(LOGS_DIR, 'mother_bot.log'), maxBytes=10485760, backupCount=50),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== دیتابیس ====================
DB_PATH = os.path.join(DB_DIR, 'mother_bot.db')

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=120, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA cache_size=-524288")
    conn.execute("PRAGMA synchronous=NORMAL")
    try:
        yield conn
        conn.commit()
    except:
        conn.rollback()
        raise
    finally:
        conn.close()

# ایجاد جداول
with get_db() as conn:
    conn.execute('CREATE TABLE IF NOT EXISTS texts (key TEXT PRIMARY KEY, value TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, last_name TEXT, referral_code TEXT UNIQUE, referred_by INTEGER, balance INTEGER DEFAULT 0, total_earned INTEGER DEFAULT 0, active_subscription INTEGER DEFAULT 0, subscription_expire TIMESTAMP, subscription_id INTEGER, total_bots INTEGER DEFAULT 0, created_at TIMESTAMP)')
    conn.execute('CREATE TABLE IF NOT EXISTS subscriptions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, subscription_code TEXT UNIQUE, status TEXT DEFAULT "pending", amount INTEGER, payment_method TEXT DEFAULT "card", payment_url TEXT, authority TEXT, created_at TIMESTAMP, paid_at TIMESTAMP, expires_at TIMESTAMP)')
    conn.execute('CREATE TABLE IF NOT EXISTS pending_files (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, subscription_id INTEGER, file_path TEXT, file_name TEXT, file_hash TEXT, status TEXT DEFAULT "pending", submitted_at TIMESTAMP, reviewed_at TIMESTAMP)')
    conn.execute('CREATE TABLE IF NOT EXISTS servers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, ip TEXT, port INTEGER, username TEXT, password TEXT, status TEXT DEFAULT "active", current_load INTEGER DEFAULT 0, max_load INTEGER DEFAULT 20, created_at TIMESTAMP)')
    conn.execute('CREATE TABLE IF NOT EXISTS bots (id TEXT PRIMARY KEY, user_id INTEGER, subscription_id INTEGER, server_id INTEGER, token TEXT, name TEXT, username TEXT, file_path TEXT, pid INTEGER, status TEXT DEFAULT "stopped", created_at TIMESTAMP, expires_at TIMESTAMP, requirements TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS receipts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, subscription_id INTEGER, amount INTEGER, receipt_path TEXT, status TEXT DEFAULT "pending", payment_code TEXT UNIQUE, created_at TIMESTAMP)')
    conn.execute('CREATE TABLE IF NOT EXISTS withdraw_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER, card_number TEXT, status TEXT DEFAULT "pending", created_at TIMESTAMP)')
    conn.execute('CREATE TABLE IF NOT EXISTS broadcast_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, admin_id INTEGER, message_text TEXT, sent_count INTEGER DEFAULT 0, created_at TIMESTAMP)')
    conn.execute('CREATE TABLE IF NOT EXISTS build_queue (id INTEGER PRIMARY KEY AUTOINCREMENT, file_id INTEGER, user_id INTEGER, status TEXT DEFAULT "pending", created_at TIMESTAMP, completed_at TIMESTAMP, error_message TEXT, bot_name TEXT, bot_username TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS installed_libraries (id INTEGER PRIMARY KEY AUTOINCREMENT, library_name TEXT UNIQUE, installed_at TIMESTAMP, server_id INTEGER, status TEXT DEFAULT "installed")')
    conn.commit()

config.load_from_db()
texts.load_from_db()

# ==================== توابع دیتابیس ====================

def generate_referral_code(user_id):
    return hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:10].upper()

def create_user(user_id, username, first_name, last_name, referred_by=None):
    try:
        with get_db() as conn:
            now = datetime.now().isoformat()
            referral_code = generate_referral_code(user_id)
            existing = conn.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,)).fetchone()
            if existing:
                return True
            if referred_by == user_id:
                referred_by = None
            conn.execute('INSERT INTO users (user_id, username, first_name, last_name, referral_code, referred_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)', (user_id, username, first_name, last_name, referral_code, referred_by, now))
            conn.commit()
            if referred_by and referred_by != user_id:
                conn.execute('UPDATE users SET balance = balance + 50000, total_earned = total_earned + 50000 WHERE user_id = ?', (referred_by,))
                conn.commit()
            return True
    except Exception as e:
        logger.error(f"create_user error: {e}")
        return False

def get_user(user_id):
    try:
        with get_db() as conn:
            user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
            return dict(user) if user else None
    except:
        return None

def get_all_users():
    try:
        with get_db() as conn:
            users = conn.execute('SELECT user_id FROM users').fetchall()
            return [u['user_id'] for u in users]
    except:
        return []

def has_active_subscription(user_id):
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

def get_subscription_days_left(user_id):
    try:
        with get_db() as conn:
            user = conn.execute('SELECT subscription_expire FROM users WHERE user_id = ?', (user_id,)).fetchone()
            if user and user['subscription_expire']:
                expire = datetime.fromisoformat(user['subscription_expire'])
                return max(0, (expire - datetime.now()).days)
            return 0
    except:
        return 0

def create_subscription(user_id, amount, payment_method='card'):
    try:
        with get_db() as conn:
            subscription_code = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:16].upper()
            now = datetime.now().isoformat()
            expires_at = (datetime.now() + timedelta(days=config.subscription_days)).isoformat()
            conn.execute('INSERT INTO subscriptions (user_id, subscription_code, amount, payment_method, created_at, expires_at, status) VALUES (?, ?, ?, ?, ?, ?, "pending")', (user_id, subscription_code, amount, payment_method, now, expires_at))
            conn.commit()
            sub_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            return sub_id, subscription_code
    except:
        return None, None

def activate_subscription(subscription_id, user_id, amount):
    try:
        with get_db() as conn:
            expires_at = (datetime.now() + timedelta(days=config.subscription_days)).isoformat()
            conn.execute('UPDATE users SET active_subscription = 0 WHERE user_id = ?', (user_id,))
            conn.execute('UPDATE users SET active_subscription = 1, subscription_expire = ?, subscription_id = ? WHERE user_id = ?', (expires_at, subscription_id, user_id))
            conn.execute('UPDATE subscriptions SET status = "active", paid_at = ? WHERE id = ?', (datetime.now().isoformat(), subscription_id))
            user = conn.execute('SELECT referred_by FROM users WHERE user_id = ?', (user_id,)).fetchone()
            if user and user['referred_by']:
                bonus = int(amount * 0.1)
                conn.execute('UPDATE users SET balance = balance + ?, total_earned = total_earned + ? WHERE user_id = ?', (bonus, bonus, user['referred_by']))
            conn.commit()
            return True
    except:
        return False

def get_user_balance(user_id):
    try:
        with get_db() as conn:
            user = conn.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,)).fetchone()
            return user['balance'] if user else 0
    except:
        return 0

def can_create_bot(user_id):
    try:
        with get_db() as conn:
            bots_count = conn.execute('SELECT COUNT(*) FROM bots WHERE user_id = ? AND status NOT IN ("deleted", "deleted_by_user")', (user_id,)).fetchone()[0]
            return has_active_subscription(user_id) and bots_count == 0
    except:
        return False

def add_bot(user_id, subscription_id, server_id, bot_id, token, name, username, file_path, pid=None, requirements=None):
    try:
        with get_db() as conn:
            now = datetime.now().isoformat()
            expires_at = (datetime.now() + timedelta(days=config.subscription_days)).isoformat()
            conn.execute('INSERT INTO bots (id, user_id, subscription_id, server_id, token, name, username, file_path, pid, status, created_at, expires_at, requirements) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, "running", ?, ?, ?)', (bot_id, user_id, subscription_id, server_id, token, name, username, file_path, pid, now, expires_at, requirements))
            conn.execute('UPDATE users SET total_bots = total_bots + 1, active_subscription = 0 WHERE user_id = ?', (user_id,))
            conn.commit()
            return True
    except:
        return False

def get_user_bots(user_id):
    try:
        with get_db() as conn:
            bots = conn.execute('SELECT * FROM bots WHERE user_id = ? AND status NOT IN ("deleted", "deleted_by_user") ORDER BY created_at DESC', (user_id,)).fetchall()
            return [dict(bot) for bot in bots]
    except:
        return []

def get_bot_by_id(bot_id):
    try:
        with get_db() as conn:
            bot = conn.execute('SELECT * FROM bots WHERE id = ?', (bot_id,)).fetchone()
            return dict(bot) if bot else None
    except:
        return None

def update_bot_status(bot_id, status):
    try:
        with get_db() as conn:
            conn.execute('UPDATE bots SET status = ? WHERE id = ?', (status, bot_id))
            conn.commit()
            return True
    except:
        return False

def delete_bot(bot_id, user_id):
    try:
        with get_db() as conn:
            bot = conn.execute('SELECT * FROM bots WHERE id = ? AND user_id = ?', (bot_id, user_id)).fetchone()
            if not bot:
                return False
            if bot['server_id'] and bot['server_id'] != 0:
                server = conn.execute('SELECT * FROM servers WHERE id = ?', (bot['server_id'],)).fetchone()
                if server:
                    stop_bot_on_server(dict(server), bot_id)
            else:
                stop_bot_on_mother(bot_id)
            conn.execute('UPDATE bots SET status = "deleted_by_user" WHERE id = ?', (bot_id,))
            conn.commit()
            return True
    except:
        return False

def save_pending_file(user_id, subscription_id, file_path, file_name, file_hash):
    try:
        with get_db() as conn:
            now = datetime.now().isoformat()
            conn.execute('INSERT INTO pending_files (user_id, subscription_id, file_path, file_name, file_hash, submitted_at) VALUES (?, ?, ?, ?, ?, ?)', (user_id, subscription_id, file_path, file_name, file_hash, now))
            conn.commit()
            return True
    except:
        return False

def get_pending_files():
    try:
        with get_db() as conn:
            files = conn.execute('SELECT * FROM pending_files WHERE status = "pending" ORDER BY submitted_at DESC').fetchall()
            return [dict(f) for f in files]
    except:
        return []

def get_pending_file_by_id(file_id):
    try:
        with get_db() as conn:
            file = conn.execute('SELECT * FROM pending_files WHERE id = ?', (file_id,)).fetchone()
            return dict(file) if file else None
    except:
        return None

def update_pending_file_status(file_id, status):
    try:
        with get_db() as conn:
            conn.execute('UPDATE pending_files SET status = ?, reviewed_at = ? WHERE id = ?', (status, datetime.now().isoformat(), file_id))
            conn.commit()
            return True
    except:
        return False

def add_to_build_queue(file_id, user_id):
    try:
        with get_db() as conn:
            conn.execute('INSERT INTO build_queue (file_id, user_id, created_at) VALUES (?, ?, ?)', (file_id, user_id, datetime.now().isoformat()))
            conn.commit()
            queue_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            build_queue.put(queue_id)
            return queue_id
    except:
        return None

def update_build_queue_status(queue_id, status, error_message=None, bot_name=None, bot_username=None):
    try:
        with get_db() as conn:
            conn.execute('UPDATE build_queue SET status = ?, completed_at = ?, error_message = ?, bot_name = ?, bot_username = ? WHERE id = ?', (status, datetime.now().isoformat(), error_message, bot_name, bot_username, queue_id))
            conn.commit()
            return True
    except:
        return False

def get_build_queue_item(queue_id):
    try:
        with get_db() as conn:
            item = conn.execute('SELECT * FROM build_queue WHERE id = ?', (queue_id,)).fetchone()
            return dict(item) if item else None
    except:
        return None

def mark_library_installed(library_name, server_id=0):
    try:
        with get_db() as conn:
            conn.execute('INSERT OR REPLACE INTO installed_libraries (library_name, installed_at, server_id, status) VALUES (?, ?, ?, "installed")', (library_name, datetime.now().isoformat(), server_id))
            conn.commit()
            return True
    except:
        return False

# ==================== سیستم نصب تضمینی کتابخانه‌ها ====================

def get_pip_command():
    """دریافت دستور pip صحیح"""
    try:
        result = subprocess.run(['pip3', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            return 'pip3'
    except:
        pass
    try:
        result = subprocess.run(['pip', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            return 'pip'
    except:
        pass
    return f'{sys.executable} -m pip'

def get_correct_library_name(lib_name):
    """دریافت نام صحیح کتابخانه برای نصب"""
    lib_lower = lib_name.lower().strip()
    
    # بررسی مستقیم
    if lib_lower in LIBRARY_MAPPING:
        return LIBRARY_MAPPING[lib_lower]
    
    # بررسی با حذف underscore و dash
    for key, value in LIBRARY_MAPPING.items():
        if key.lower().replace('_', '').replace('-', '') == lib_lower.replace('_', '').replace('-', ''):
            return value
    
    # بررسی جزئی
    if 'telegram' in lib_lower or 'bot' in lib_lower:
        if 'python-telegram-bot' not in lib_lower:
            return 'python-telegram-bot'
    elif 'telebot' in lib_lower:
        return 'pyTelegramBotAPI'
    elif 'beautifulsoup' in lib_lower or 'bs4' in lib_lower:
        return 'beautifulsoup4'
    elif 'cv2' in lib_lower or 'opencv' in lib_lower:
        return 'opencv-python'
    elif 'pil' in lib_lower:
        return 'Pillow'
    elif 'sklearn' in lib_lower:
        return 'scikit-learn'
    
    return lib_name

def install_library_with_retry(library_name, max_retries=3):
    """نصب کتابخانه با تلاش مجدد - تضمینی"""
    correct_name = get_correct_library_name(library_name)
    pip_cmd = get_pip_command()
    
    for retry in range(max_retries):
        try:
            # بررسی نصب بودن
            check = subprocess.run(f'{pip_cmd} show {correct_name} 2>/dev/null | grep Name', shell=True, capture_output=True, text=True)
            if check.returncode == 0 and check.stdout.strip():
                logger.info(f"✅ کتابخانه {correct_name} قبلاً نصب شده است")
                mark_library_installed(correct_name, 0)
                return True, correct_name
            
            # نصب کتابخانه
            logger.info(f"📦 در حال نصب {correct_name} (تلاش {retry + 1}/{max_retries})")
            result = subprocess.run(f'{pip_cmd} install {correct_name} --quiet --no-cache-dir --default-timeout=100', shell=True, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                logger.info(f"✅ کتابخانه {correct_name} با موفقیت نصب شد")
                mark_library_installed(correct_name, 0)
                return True, correct_name
            else:
                logger.warning(f"⚠️ خطا در نصب {correct_name}: {result.stderr[:200]}")
                
        except subprocess.TimeoutExpired:
            logger.warning(f"⏰ Timeout در نصب {correct_name} (تلاش {retry + 1})")
        except Exception as e:
            logger.warning(f"⚠️ خطا در نصب {correct_name}: {str(e)}")
        
        if retry < max_retries - 1:
            time.sleep(2)
    
    return False, None

def install_multiple_libraries(libraries, progress_callback=None):
    """نصب چند کتابخانه به صورت پشت سر هم"""
    installed = []
    failed = []
    
    # حذف کتابخانه‌های تکراری و استاندارد
    unique_libs = []
    for lib in libraries:
        if lib not in STD_LIBRARIES and lib not in unique_libs:
            unique_libs.append(lib)
    
    total = len(unique_libs)
    for i, lib in enumerate(unique_libs):
        if progress_callback:
            progress_callback(i + 1, total, lib)
        
        success, installed_lib = install_library_with_retry(lib)
        if success:
            installed.append(installed_lib)
        else:
            failed.append(lib)
        
        time.sleep(0.5)
    
    return installed, failed

def detect_requirements_from_code(code):
    """تشخیص پیشرفته کتابخانه‌های مورد نیاز از کد"""
    imports = set()
    lines = code.split('\n')
    
    for line in lines:
        line = line.strip()
        
        # import xyz
        if line.startswith('import '):
            parts = line.split()
            if len(parts) > 1:
                lib = parts[1].split('.')[0].split(' as ')[0]
                if lib not in STD_LIBRARIES and not lib.startswith('_'):
                    imports.add(lib)
        
        # from xyz import abc
        elif line.startswith('from '):
            parts = line.split()
            if len(parts) > 1:
                lib = parts[1].split('.')[0]
                if lib not in STD_LIBRARIES and not lib.startswith('_') and lib != '':
                    imports.add(lib)
        
        # try/except import
        elif 'import' in line and ('try:' in line or 'except' in line):
            import_match = re.search(r'import\s+([a-zA-Z0-9_]+)', line)
            if import_match:
                lib = import_match.group(1)
                if lib not in STD_LIBRARIES:
                    imports.add(lib)
        
        # from ... import ...
        elif line.startswith('from ') and ' import ' in line:
            match = re.search(r'from\s+([a-zA-Z0-9_.]+)\s+import', line)
            if match:
                lib = match.group(1).split('.')[0]
                if lib not in STD_LIBRARIES and not lib.startswith('_'):
                    imports.add(lib)
    
    # تبدیل به نام صحیح برای نصب
    final_libs = []
    for lib in imports:
        if lib in STD_LIBRARIES:
            continue
        correct = get_correct_library_name(lib)
        if correct not in final_libs:
            final_libs.append(correct)
    
    return final_libs

def install_libraries_on_mother(libraries, chat_id=None):
    """نصب کتابخانه‌ها روی سرور مادر"""
    if not libraries:
        return [], []
    
    installed = []
    failed = []
    
    def send_progress(current, total, lib):
        if chat_id:
            try:
                percent = int(current / total * 100)
                bar = "█" * int(percent / 5) + "░" * (20 - int(percent / 5))
                bot.edit_message_text(f"📦 **نصب کتابخانه‌ها**\n\n`[{bar}]` {percent}%\n\nدر حال نصب [{current}/{total}]: `{lib}`", chat_id, status_msg_id, parse_mode="Markdown")
            except:
                pass
        print(f"📦 نصب [{current}/{total}]: {lib}")
    
    # ارسال پیام اولیه
    status_msg = None
    if chat_id:
        try:
            status_msg = bot.send_message(chat_id, f"📦 در حال نصب {len(libraries)} کتابخانه مورد نیاز...\n⏳ لطفاً شکیبا باشید...", parse_mode="Markdown")
            status_msg_id = status_msg.message_id
        except:
            pass
    
    installed, failed = install_multiple_libraries(libraries, lambda c, t, l: send_progress(c, t, l))
    
    if chat_id and status_msg:
        if installed:
            bot.edit_message_text(f"✅ **نصب کتابخانه‌ها کامل شد!**\n\n📦 نصب شده: {len(installed)} مورد\n❌ ناموفق: {len(failed)} مورد\n\nکتابخانه‌های نصب شده:\n`{', '.join(installed[:15])}`", chat_id, status_msg_id, parse_mode="Markdown")
        else:
            bot.edit_message_text(f"❌ **خطا در نصب کتابخانه‌ها!**\n\nلطفاً به صورت دستی نصب کنید.", chat_id, status_msg_id, parse_mode="Markdown")
    
    return installed, failed

# ==================== سیستم مدیریت سرور و اجرا ====================

def get_available_servers():
    with get_db() as conn:
        servers = conn.execute('SELECT * FROM servers WHERE status = "active" AND current_load < max_load ORDER BY current_load ASC').fetchall()
        return [dict(s) for s in servers]

def get_best_server():
    servers = get_available_servers()
    return servers[0] if servers else None

def test_server_connection(ip, port, username, password):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip, port=port, username=username, password=password, timeout=10)
        client.close()
        return True
    except:
        return False

def add_new_server(name, ip, port, username, password):
    try:
        if not test_server_connection(ip, port, username, password):
            return False, "❌ اتصال به سرور امکان‌پذیر نیست"
        with get_db() as conn:
            now = datetime.now().isoformat()
            conn.execute('INSERT INTO servers (name, ip, port, username, password, created_at) VALUES (?, ?, ?, ?, ?, ?)', (name, ip, port, username, password, now))
            conn.commit()
            return True, f"✅ سرور {name} اضافه شد"
    except Exception as e:
        return False, f"❌ خطا: {str(e)}"

def run_bot_on_mother_server(bot_id, code, token, chat_id=None):
    """اجرای ربات روی سرور مادر"""
    try:
        bot_dir = os.path.join(RUNNING_DIR, bot_id)
        os.makedirs(bot_dir, exist_ok=True)
        
        code_path = os.path.join(bot_dir, 'bot.py')
        with open(code_path, 'w', encoding='utf-8') as f:
            f.write(code)
        
        # تشخیص و نصب کتابخانه‌های مورد نیاز
        libraries = detect_requirements_from_code(code)
        
        if libraries and config.auto_install_libs:
            installed, failed = install_libraries_on_mother(libraries, chat_id)
            if failed:
                logger.warning(f"کتابخانه‌های نصب نشده: {failed}")
        
        log_file = os.path.join(bot_dir, 'bot.log')
        
        # اجرای ربات
        if sys.platform == 'win32':
            process = subprocess.Popen(
                [sys.executable, code_path],
                stdout=open(log_file, 'a'),
                stderr=subprocess.STDOUT,
                cwd=bot_dir,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
        else:
            process = subprocess.Popen(
                [sys.executable, code_path],
                stdout=open(log_file, 'a'),
                stderr=subprocess.STDOUT,
                cwd=bot_dir,
                start_new_session=True
            )
        
        time.sleep(4)
        
        if process.poll() is None:
            return process.pid, None
        else:
            with open(log_file, 'r') as f:
                error = f.read()[-500:]
            return None, error if error else "خطای ناشناخته در اجرا"
    except Exception as e:
        return None, str(e)

def stop_bot_on_mother(bot_id):
    try:
        with get_db() as conn:
            bot = conn.execute('SELECT pid FROM bots WHERE id = ?', (bot_id,)).fetchone()
            if bot and bot['pid']:
                try:
                    os.kill(bot['pid'], signal.SIGTERM)
                except:
                    pass
                return True
        return False
    except:
        return False

def stop_user_bot(bot_id):
    bot_info = get_bot_by_id(bot_id)
    if not bot_info:
        return False
    return stop_bot_on_mother(bot_id)

def start_user_bot(bot_id, chat_id=None):
    bot_info = get_bot_by_id(bot_id)
    if not bot_info:
        return False, "ربات پیدا نشد"
    if not os.path.exists(bot_info['file_path']):
        return False, "فایل ربات پیدا نشد"
    with open(bot_info['file_path'], 'r', encoding='utf-8') as f:
        code = f.read()
    pid, error = run_bot_on_mother_server(bot_info['id'], code, bot_info['token'], chat_id)
    if pid:
        update_bot_status(bot_id, 'running')
        return True, "ربات فعال شد"
    else:
        return False, error

def extract_token(code):
    patterns = [
        r'[0-9]{8,10}:[A-Za-z0-9_-]{35}',
        r'token\s*=\s*["\']([^"\']+)["\']',
        r'TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'BOT_TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'API_TOKEN\s*=\s*["\']([^"\']+)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, code, re.IGNORECASE)
        if match:
            token = match.group(1) if match.lastindex else match.group(0)
            if len(token) > 30 and ':' in token:
                return token
    return None

def extract_from_zip(zip_path, extract_to):
    py_files = []
    main_code = None
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        for root, dirs, files in os.walk(extract_to):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        py_files.append({'name': file, 'path': file_path, 'content': content})
                    except:
                        pass
        for pf in py_files:
            if pf['name'] in ['bot.py', 'main.py', 'run.py']:
                main_code = pf['content']
                break
        if not main_code and py_files:
            main_code = py_files[0]['content']
        return main_code, py_files
    except Exception as e:
        return None, []

def build_bot_from_pending(file_id, queue_id=None, chat_id=None):
    result = {'success': False, 'error': None, 'name': None, 'username': None, 'bot_id': None}
    
    pending = get_pending_file_by_id(file_id)
    if not pending:
        result['error'] = "فایل پیدا نشد"
        if queue_id:
            update_build_queue_status(queue_id, 'failed', error_message=result['error'])
        return result
    
    # استخراج کد
    code = None
    if pending['file_name'].endswith('.zip'):
        extract_dir = os.path.join(PENDING_FILES_DIR, f"extract_{file_id}")
        os.makedirs(extract_dir, exist_ok=True)
        code, _ = extract_from_zip(pending['file_path'], extract_dir)
        shutil.rmtree(extract_dir, ignore_errors=True)
    else:
        with open(pending['file_path'], 'r', encoding='utf-8') as f:
            code = f.read()
    
    if not code:
        result['error'] = "خطا در خواندن فایل"
        if queue_id:
            update_build_queue_status(queue_id, 'failed', error_message=result['error'])
        return result
    
    # استخراج توکن
    token = extract_token(code)
    if not token:
        result['error'] = "توکن ربات پیدا نشد"
        if queue_id:
            update_build_queue_status(queue_id, 'failed', error_message=result['error'])
        return result
    
    # بررسی توکن
    try:
        response = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        if response.status_code != 200:
            result['error'] = "توکن نامعتبر است"
            if queue_id:
                update_build_queue_status(queue_id, 'failed', error_message=result['error'])
            return result
        bot_info = response.json()['result']
        bot_name = bot_info['first_name']
        bot_username = bot_info['username']
    except Exception as e:
        result['error'] = f"خطا در بررسی توکن: {str(e)[:50]}"
        if queue_id:
            update_build_queue_status(queue_id, 'failed', error_message=result['error'])
        return result
    
    # تشخیص کتابخانه‌ها
    libraries = detect_requirements_from_code(code)
    
    if libraries and config.auto_install_libs:
        if chat_id:
            try:
                bot.send_message(chat_id, f"📦 تشخیص {len(libraries)} کتابخانه مورد نیاز:\n`{', '.join(libraries[:15])}`\n\nدر حال نصب...", parse_mode="Markdown")
            except:
                pass
        installed, failed = install_libraries_on_mother(libraries, chat_id)
    
    bot_id = hashlib.md5(f"{pending['user_id']}_{token}_{time.time()}".encode()).hexdigest()[:12]
    
    pid, error = run_bot_on_mother_server(bot_id, code, token, chat_id)
    
    if pid:
        requirements = ','.join(libraries)
        add_bot(pending['user_id'], pending['subscription_id'], 0, bot_id, token, bot_name, bot_username, pending['file_path'], pid, requirements)
        update_pending_file_status(file_id, 'approved')
        result['success'] = True
        result['name'] = bot_name
        result['username'] = bot_username
        result['bot_id'] = bot_id
        if queue_id:
            update_build_queue_status(queue_id, 'completed', bot_name=bot_name, bot_username=bot_username)
        try:
            bot.send_message(pending['user_id'], f"✅ ربات شما با موفقیت ساخته شد!\n\n🤖 نام: {bot_name}\n🔗 لینک: https://t.me/{bot_username}\n🆔 آیدی: `{bot_id}`\n\nاز منوی «ربات‌های من» می‌توانید آن را مدیریت کنید.")
        except:
            pass
    else:
        result['error'] = error or "خطا در اجرای ربات"
        if queue_id:
            update_build_queue_status(queue_id, 'failed', error_message=result['error'])
        try:
            bot.send_message(pending['user_id'], f"❌ خطا در ساخت ربات!\n\nخطا: {result['error'][:200]}\n\nلطفاً با پشتیبانی تماس بگیرید.")
        except:
            pass
    
    return result

def send_broadcast(message_text, admin_id):
    users = get_all_users()
    sent_count = 0
    for user_id in users:
        try:
            bot.send_message(user_id, message_text)
            sent_count += 1
            time.sleep(0.03)
        except:
            pass
    with get_db() as conn:
        conn.execute('INSERT INTO broadcast_messages (admin_id, message_text, sent_count, created_at) VALUES (?, ?, ?, ?)', (admin_id, message_text, sent_count, datetime.now().isoformat()))
        conn.commit()
    return sent_count

# ==================== تابع ثانیه‌شمار پویا ====================

def update_countdown(chat_id, message_id, queue_id, start_time):
    try:
        queue_item = get_build_queue_item(queue_id)
        if not queue_item or queue_item['status'] != 'pending':
            return
        
        created_at = datetime.fromisoformat(queue_item['created_at'])
        elapsed = (datetime.now() - created_at).total_seconds()
        
        if elapsed >= 60:
            try:
                bot.send_message(chat_id, "🔄 **در حال ساخت ربات...**\n\n⏳ زمان ساخت به پایان رسید!\n📦 در حال نصب کتابخانه‌ها و اجرا...", parse_mode="Markdown")
            except:
                bot.send_message(chat_id, "🔄 در حال ساخت ربات... زمان ساخت به پایان رسید! در حال نصب کتابخانه‌ها و اجرا...")
            
            result = build_bot_from_pending(queue_item['file_id'], queue_id, chat_id)
            
            if result['success']:
                try:
                    bot.send_message(chat_id, f"✅ **ربات با موفقیت ساخته شد!**\n\n🤖 نام: {result['name']}\n🔗 لینک: https://t.me/{result['username']}\n🆔 آیدی: `{result['bot_id']}`\n\n🎉 ربات شما آماده استفاده است!", parse_mode="Markdown")
                except:
                    bot.send_message(chat_id, f"✅ ربات با موفقیت ساخته شد!\n\n🤖 نام: {result['name']}\n🔗 لینک: https://t.me/{result['username']}\n\n🎉 ربات شما آماده استفاده است!")
            else:
                bot.send_message(chat_id, f"❌ **خطا در ساخت ربات!**\n\n⚠️ خطا: {result['error'][:200]}\n\nلطفاً با پشتیبانی تماس بگیرید.")
            
            if queue_id in active_builds:
                del active_builds[queue_id]
            return
        
        remaining = int(60 - elapsed)
        minutes = remaining // 60
        seconds = remaining % 60
        progress = int((elapsed / 60) * 20)
        bar = "█" * progress + "░" * (20 - progress)
        
        text = f"🔄 **ساخت ربات در صف انتظار**\n\n📊 وضعیت: در حال آماده‌سازی\n⏳ زمان باقی‌مانده: {minutes:02d}:{seconds:02d}\n\n[{bar}]\n\n🔍 در حال بررسی و نصب کتابخانه‌های مورد نیاز...\n📦 پس از اتمام زمان، ربات شما ساخته می‌شود.\n🙏 لطفاً شکیبا باشید..."
        
        safe_edit_message(chat_id, message_id, text, parse_mode="Markdown")
        
        threading.Timer(1.0, update_countdown, args=(chat_id, message_id, queue_id, start_time)).start()
        
    except Exception as e:
        logger.error(f"update_countdown error: {e}")

def queue_worker():
    global queue_thread_running
    while queue_thread_running:
        try:
            if not build_queue.empty():
                queue_id = build_queue.get()
                with get_db() as conn:
                    queue_item = conn.execute('SELECT * FROM build_queue WHERE id = ? AND status = "pending"', (queue_id,)).fetchone()
                    if queue_item and queue_id in active_builds:
                        build_info = active_builds[queue_id]
                        update_countdown(build_info['chat_id'], build_info['message_id'], queue_id, build_info['start_time'])
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"queue_worker error: {e}")
            time.sleep(1)

# ==================== درگاه پرداخت زرین‌پال ====================

def create_zarinpal_payment(amount, description, user_id, subscription_id):
    if not config.zarinpal_merchant:
        return None, "مرچنت کد تنظیم نشده است"
    callback_url = config.zarinpal_callback or "https://your-domain.com/callback"
    data = {"merchant_id": config.zarinpal_merchant, "amount": amount, "callback_url": callback_url, "description": description, "metadata": {"user_id": user_id, "subscription_id": subscription_id}}
    try:
        response = requests.post("https://api.zarinpal.com/pg/v4/payment/request.json", json=data, timeout=30)
        result = response.json()
        if result.get("data", {}).get("code") == 100:
            authority = result["data"]["authority"]
            payment_url = f"https://www.zarinpal.com/pg/StartPay/{authority}"
            return payment_url, authority
        else:
            return None, result.get("errors", {}).get("message", "خطا در ایجاد پرداخت")
    except Exception as e:
        return None, str(e)

def verify_zarinpal_payment(amount, authority):
    if not config.zarinpal_merchant:
        return False, "مرچنت کد تنظیم نشده است"
    data = {"merchant_id": config.zarinpal_merchant, "amount": amount, "authority": authority}
    try:
        response = requests.post("https://api.zarinpal.com/pg/v4/payment/verify.json", json=data, timeout=30)
        result = response.json()
        if result.get("data", {}).get("code") == 100:
            return True, "پرداخت با موفقیت انجام شد"
        else:
            return False, result.get("errors", {}).get("message", "خطا در تایید پرداخت")
    except Exception as e:
        return False, str(e)

def update_subscription_payment_url(sub_id, authority, payment_url):
    try:
        with get_db() as conn:
            conn.execute('UPDATE subscriptions SET authority = ?, payment_url = ? WHERE id = ?', (authority, payment_url, sub_id))
            conn.commit()
            return True
    except:
        return False

# ==================== بازگردانی ربات‌ها بعد از ریستارت ====================

def restore_all_bots():
    try:
        with get_db() as conn:
            running_bots = conn.execute('SELECT * FROM bots WHERE status = "running" OR status = "stopped"').fetchall()
        for bot_info in running_bots:
            bot_info = dict(bot_info)
            if os.path.exists(bot_info['file_path']):
                with open(bot_info['file_path'], 'r', encoding='utf-8') as f:
                    code = f.read()
                pid, error = run_bot_on_mother_server(bot_info['id'], code, bot_info['token'])
                if pid:
                    conn.execute('UPDATE bots SET status = "running" WHERE id = ?', (bot_info['id'],))
                    conn.commit()
                    logger.info(f"ربات {bot_info['id']} بازگردانی شد")
    except Exception as e:
        logger.error(f"خطا در بازگردانی ربات‌ها: {e}")

# ==================== ایجاد و تنظیم ربات ====================
def setup_bot():
    bot_instance = telebot.TeleBot(BOT_TOKEN, num_threads=100)
    try:
        bot_instance.remove_webhook()
        time.sleep(1)
        bot_instance.delete_webhook()
        time.sleep(0.5)
    except Exception as e:
        print(f"⚠️ خطا در حذف وب‌هوک: {e}")
    return bot_instance

bot = setup_bot()

# ==================== منوها ====================

def get_main_menu(user_id):
    days_left = get_subscription_days_left(user_id)
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        types.KeyboardButton('🛒 خرید اشتراک'),
        types.KeyboardButton('📤 ارسال فایل ربات'),
        types.KeyboardButton('🤖 ربات‌های من'),
        types.KeyboardButton('💰 کیف پول'),
        types.KeyboardButton('📚 راهنما'),
        types.KeyboardButton('📞 پشتیبانی'),
        types.KeyboardButton('🗑 حذف ربات')
    ]
    if days_left > 0:
        buttons.insert(0, types.KeyboardButton(f'📅 {days_left} روز مونده'))
    if user_id in ADMIN_IDS:
        buttons.append(types.KeyboardButton('👑 پنل ادمین'))
    markup.add(*buttons)
    return markup

# ==================== هندلرها ====================

@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    referred_by = None
    args = message.text.split()
    if len(args) > 1:
        with get_db() as conn:
            referrer = conn.execute('SELECT user_id FROM users WHERE referral_code = ?', (args[1],)).fetchone()
            if referrer and referrer['user_id'] != user_id:
                referred_by = referrer['user_id']
    create_user(user_id, username, first_name, last_name, referred_by)
    bot_username = bot.get_me().username
    user = get_user(user_id)
    referral_link = f"https://t.me/{bot_username}?start={user['referral_code']}" if user else ""
    welcome = texts.welcome_text.format(bot_username)
    welcome += f"\n\n🎁 لینک رفرال شما:\n{referral_link}"
    bot.send_message(message.chat.id, welcome, reply_markup=get_main_menu(user_id))

@bot.message_handler(func=lambda m: m.text == '🛒 خرید اشتراک')
def buy_subscription(message):
    user_id = message.from_user.id
    if has_active_subscription(user_id):
        days_left = get_subscription_days_left(user_id)
        bot.send_message(message.chat.id, f"✅ اشتراک فعال دارید! {days_left} روز مونده.")
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("💳 کارت به کارت", callback_data="pay_card"), types.InlineKeyboardButton("💰 پرداخت آنلاین", callback_data="pay_online"))
    bot.send_message(message.chat.id, "💰 روش پرداخت را انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "pay_card")
def pay_with_card(call):
    user_id = call.from_user.id
    sub_id, sub_code = create_subscription(user_id, config.price, 'card')
    if not sub_id:
        bot.send_message(call.message.chat.id, "❌ خطا")
        return
    subscription_text = texts.subscription_text.format(config.price, config.card_number, config.card_holder, sub_code, config.subscription_days)
    bot.edit_message_text(subscription_text, call.message.chat.id, call.message.message_id, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "pay_online")
def pay_with_online(call):
    user_id = call.from_user.id
    sub_id, sub_code = create_subscription(user_id, config.price, 'online')
    if not sub_id:
        bot.send_message(call.message.chat.id, "❌ خطا")
        return
    payment_url, authority = create_zarinpal_payment(config.price, f"خرید اشتراک ربات ساز - کد {sub_code}", user_id, sub_id)
    if payment_url:
        update_subscription_payment_url(sub_id, authority, payment_url)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("💰 پرداخت آنلاین", url=payment_url), types.InlineKeyboardButton("🔄 بررسی پرداخت", callback_data="check_online_payment"))
        bot.edit_message_text(f"💰 پرداخت آنلاین\n\nمبلغ: {config.price:,} تومان\n\nبرای پرداخت روی دکمه زیر کلیک کنید:\n\n🆔 کد پیگیری: {sub_code}\n\nپس از پرداخت، دکمه بررسی را بزنید.", call.message.chat.id, call.message.message_id, reply_markup=markup)
    else:
        bot.edit_message_text(f"❌ خطا در ایجاد پرداخت: {authority}", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "check_online_payment")
def check_online_payment(call):
    with get_db() as conn:
        sub = conn.execute('SELECT * FROM subscriptions WHERE user_id = ? AND status = "pending" AND payment_method = "online" ORDER BY id DESC LIMIT 1', (call.from_user.id,)).fetchone()
        if sub and sub['authority']:
            success, msg = verify_zarinpal_payment(sub['amount'], sub['authority'])
            if success:
                activate_subscription(sub['id'], call.from_user.id, sub['amount'])
                bot.edit_message_text("✅ پرداخت با موفقیت انجام شد!\nاشتراک شما فعال شد.", call.message.chat.id, call.message.message_id)
                bot.send_message(call.from_user.id, f"✅ اشتراک شما فعال شد!\n📅 {config.subscription_days} روز اعتبار.\n📤 فایل ربات خود را ارسال کنید.")
            else:
                bot.answer_callback_query(call.id, f"❌ {msg}")
        else:
            bot.answer_callback_query(call.id, "❌ سفارش پرداختی پیدا نشد")

@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    with get_db() as conn:
        pending_sub = conn.execute('SELECT * FROM subscriptions WHERE user_id = ? AND status = "pending" AND payment_method = "card" ORDER BY created_at DESC LIMIT 1', (user_id,)).fetchone()
    if not pending_sub:
        bot.reply_to(message, "❌ اشتراک در انتظاری ندارید.")
        return
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        payment_code = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:12].upper()
        receipt_path = os.path.join(RECEIPTS_DIR, f"{user_id}_{payment_code}.jpg")
        with open(receipt_path, 'wb') as f:
            f.write(downloaded_file)
        with get_db() as conn:
            conn.execute('INSERT INTO receipts (user_id, subscription_id, amount, receipt_path, payment_code, created_at) VALUES (?, ?, ?, ?, ?, ?)', (user_id, pending_sub['id'], config.price, receipt_path, payment_code, datetime.now().isoformat()))
            conn.commit()
        bot.reply_to(message, f"✅ فیش شما با موفقیت ارسال شد.\n🆔 کد پیگیری: {payment_code}\n⏳ پس از تایید، اشتراک شما فعال می‌شود.")
        for admin_id in ADMIN_IDS:
            try:
                bot.send_photo(admin_id, open(receipt_path, 'rb'), caption=f"📸 فیش جدید\n👤 {user_id}\n💰 {config.price:,} تومان\n🆔 {payment_code}")
            except:
                pass
    except Exception as e:
        bot.reply_to(message, f"❌ خطا")

@bot.message_handler(func=lambda m: m.text == '📤 ارسال فایل ربات')
def send_bot_file(message):
    user_id = message.from_user.id
    if not has_active_subscription(user_id):
        bot.send_message(message.chat.id, f"❌ اشتراک فعال ندارید!\n💰 {config.price:,} تومان\nاز منوی خرید اشتراک استفاده کنید.")
        return
    if not can_create_bot(user_id):
        bot.send_message(message.chat.id, "❌ قبلاً با این اشتراک ربات ساخته‌اید!")
        return
    bot.send_message(message.chat.id, "📤 فایل `.py` یا `.zip` خود را ارسال کنید.\n\n✅ پس از تایید ادمین، ربات ساخته می‌شود.\n📦 کتابخانه‌های مورد نیاز به صورت خودکار نصب می‌شوند.")

@bot.message_handler(content_types=['document'])
def handle_bot_file(message):
    user_id = message.from_user.id
    if not has_active_subscription(user_id):
        bot.reply_to(message, "❌ اشتراک فعال ندارید!")
        return
    if not can_create_bot(user_id):
        bot.reply_to(message, "❌ قبلاً ربات ساخته‌اید!")
        return
    file_name = message.document.file_name
    if not (file_name.endswith('.py') or file_name.endswith('.zip')):
        bot.reply_to(message, "❌ فقط فایل `.py` یا `.zip` مجاز است!")
        return
    if message.document.file_size > 20 * 1024 * 1024:
        bot.reply_to(message, "❌ حجم بیشتر از ۲۰ مگابایت!")
        return
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        file_path = os.path.join(PENDING_FILES_DIR, str(user_id), f"{int(time.time())}_{file_name}")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'wb') as f:
            f.write(downloaded_file)
        file_hash = hashlib.sha256(open(file_path, 'rb').read()).hexdigest()
        with get_db() as conn:
            sub = conn.execute('SELECT id FROM subscriptions WHERE user_id = ? AND status = "active" ORDER BY paid_at DESC LIMIT 1', (user_id,)).fetchone()
            if not sub:
                bot.reply_to(message, "❌ اشتراک فعال پیدا نشد!")
                return
            subscription_id = sub['id']
        save_pending_file(user_id, subscription_id, file_path, file_name, file_hash)
        bot.reply_to(message, f"✅ فایل {file_name} دریافت شد.\n⏳ در لیست انتظار بررسی قرار گرفت.\n📦 کتابخانه‌های مورد نیاز هنگام ساخت به صورت خودکار نصب می‌شوند.")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا")

@bot.message_handler(func=lambda m: m.text == '🤖 ربات‌های من')
def my_bots(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    if not bots:
        bot.send_message(message.chat.id, "📋 شما رباتی ندارید!\nبرای ساخت ربات، ابتدا اشتراک بخرید.")
        return
    for b in bots:
        status_emoji = "🟢" if b['status'] == 'running' else "🔴"
        status_text = "فعال" if b['status'] == 'running' else "غیرفعال"
        text = f"{status_emoji} **{b['name']}**\n🔗 https://t.me/{b['username']}\n🆔 `{b['id']}`\n📊 وضعیت: {status_text}\n📅 ساخته شده: {b['created_at'][:10]}"
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton(f"🔍 مشاهده {b['name']}", callback_data=f"view_bot_{b['id']}"))
        if b['status'] == 'running':
            markup.add(types.InlineKeyboardButton("🛑 غیرفعال", callback_data=f"disable_bot_{b['id']}"))
        else:
            markup.add(types.InlineKeyboardButton("✅ فعال", callback_data=f"enable_bot_{b['id']}"))
        bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == '🗑 حذف ربات')
def delete_bot_menu(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    if not bots:
        bot.send_message(message.chat.id, "📋 شما رباتی برای حذف ندارید!")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        markup.add(types.InlineKeyboardButton(f"🗑 {b['name']}", callback_data=f"user_delete_bot_{b['id']}"))
    bot.send_message(message.chat.id, "🗑 لطفاً رباتی را که می‌خواهید حذف کنید انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('user_delete_bot_'))
def user_delete_bot_confirm(call):
    bot_id = call.data.replace('user_delete_bot_', '')
    user_id = call.from_user.id
    bot_info = get_bot_by_id(bot_id)
    if not bot_info or bot_info['user_id'] != user_id:
        bot.answer_callback_query(call.id, "❌ ربات پیدا نشد!")
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("✅ بله، حذف شود", callback_data=f"user_confirm_delete_{bot_id}"), types.InlineKeyboardButton("❌ انصراف", callback_data=f"user_cancel_delete_{bot_id}"))
    bot.edit_message_text(f"⚠️ **آیا از حذف ربات {bot_info['name']} اطمینان دارید؟**\n\nاین عمل غیرقابل بازگشت است.", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('user_confirm_delete_'))
def user_confirm_delete(call):
    bot_id = call.data.replace('user_confirm_delete_', '')
    user_id = call.from_user.id
    if delete_bot(bot_id, user_id):
        bot.answer_callback_query(call.id, "✅ ربات حذف شد")
        bot.edit_message_text("🗑 ربات با موفقیت حذف شد.", call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ خطا در حذف")

@bot.callback_query_handler(func=lambda call: call.data.startswith('user_cancel_delete_'))
def user_cancel_delete(call):
    bot.answer_callback_query(call.id, "❌ عملیات لغو شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('view_bot_'))
def view_bot_details(call):
    bot_id = call.data.replace('view_bot_', '')
    user_id = call.from_user.id
    bot_info = get_bot_by_id(bot_id)
    if not bot_info or bot_info['user_id'] != user_id:
        bot.answer_callback_query(call.id, "❌ ربات پیدا نشد!")
        return
    with get_db() as conn:
        total_bots = conn.execute('SELECT COUNT(*) FROM bots WHERE user_id = ? AND status NOT IN ("deleted", "deleted_by_user")', (user_id,)).fetchone()[0]
    days_left = get_subscription_days_left(user_id)
    expires_at = datetime.fromisoformat(bot_info['expires_at']) if bot_info['expires_at'] else None
    bot_days_left = max(0, (expires_at - datetime.now()).days) if expires_at else 0
    status_emoji = "🟢" if bot_info['status'] == 'running' else "🔴"
    status_text = "در حال اجرا" if bot_info['status'] == 'running' else "متوقف"
    text = f"🔍 **جزئیات ربات**\n\n{status_emoji} **نام:** {bot_info['name']}\n🔗 **لینک:** https://t.me/{bot_info['username']}\n🆔 **آیدی ربات:** `{bot_info['id']}`\n📊 **وضعیت:** {status_text}\n📅 **تاریخ ساخت:** {bot_info['created_at'][:10]}\n"
    if bot_days_left > 0:
        text += f"⏰ **اعتبار باقی‌مانده:** {bot_days_left} روز\n"
    else:
        text += f"⏰ **اعتبار:** منقضی شده\n"
    text += f"\n📊 **آمار شما:**\n• تعداد کل ربات‌ها: {total_bots}\n• اشتراک فعال: {'بله' if days_left > 0 else 'خیر'}\n"
    if days_left > 0:
        text += f"• اعتبار اشتراک: {days_left} روز\n"
    markup = types.InlineKeyboardMarkup(row_width=2)
    if bot_info['status'] == 'running':
        markup.add(types.InlineKeyboardButton("🛑 غیرفعال", callback_data=f"disable_bot_{bot_id}"))
    else:
        markup.add(types.InlineKeyboardButton("✅ فعال", callback_data=f"enable_bot_{bot_id}"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت به لیست", callback_data=f"back_to_bots"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_bots")
def back_to_bots(call):
    user_id = call.from_user.id
    bots = get_user_bots(user_id)
    if not bots:
        bot.edit_message_text("📋 شما رباتی ندارید!", call.message.chat.id, call.message.message_id)
        return
    bot.delete_message(call.message.chat.id, call.message.message_id)
    for b in bots:
        status_emoji = "🟢" if b['status'] == 'running' else "🔴"
        status_text = "فعال" if b['status'] == 'running' else "غیرفعال"
        text = f"{status_emoji} **{b['name']}**\n🔗 https://t.me/{b['username']}\n🆔 `{b['id']}`\n📊 وضعیت: {status_text}\n📅 ساخته شده: {b['created_at'][:10]}"
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton(f"🔍 مشاهده {b['name']}", callback_data=f"view_bot_{b['id']}"))
        if b['status'] == 'running':
            markup.add(types.InlineKeyboardButton("🛑 غیرفعال", callback_data=f"disable_bot_{b['id']}"))
        else:
            markup.add(types.InlineKeyboardButton("✅ فعال", callback_data=f"enable_bot_{b['id']}"))
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('disable_bot_'))
def disable_user_bot(call):
    bot_id = call.data.replace('disable_bot_', '')
    user_id = call.from_user.id
    bot_info = get_bot_by_id(bot_id)
    if not bot_info or bot_info['user_id'] != user_id:
        bot.answer_callback_query(call.id, "❌ ربات پیدا نشد!")
        return
    if stop_user_bot(bot_id):
        bot.answer_callback_query(call.id, "✅ ربات غیرفعال شد")
        bot.edit_message_text(f"🛑 ربات {bot_info['name']} غیرفعال شد.\nبرای فعال کردن دوباره به منوی ربات‌های من بروید.", call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ خطا در غیرفعال کردن")

@bot.callback_query_handler(func=lambda call: call.data.startswith('enable_bot_'))
def enable_user_bot(call):
    bot_id = call.data.replace('enable_bot_', '')
    user_id = call.from_user.id
    bot_info = get_bot_by_id(bot_id)
    if not bot_info or bot_info['user_id'] != user_id:
        bot.answer_callback_query(call.id, "❌ ربات پیدا نشد!")
        return
    days_left = get_subscription_days_left(user_id)
    if days_left <= 0:
        bot.answer_callback_query(call.id, "❌ اشتراک شما منقضی شده است!")
        bot.edit_message_text(f"❌ اشتراک شما منقضی شده است.\nلطفاً برای فعال کردن ربات، اشتراک جدید بخرید.", call.message.chat.id, call.message.message_id)
        return
    success, msg = start_user_bot(bot_id, call.message.chat.id)
    if success:
        bot.answer_callback_query(call.id, "✅ ربات فعال شد")
        bot.edit_message_text(f"✅ ربات {bot_info['name']} فعال شد.\nبرای غیرفعال کردن به منوی ربات‌های من بروید.", call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, f"❌ {msg[:30]}")

@bot.message_handler(func=lambda m: m.text == '💰 کیف پول')
def wallet(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    balance = get_user_balance(user_id)
    bot_username = bot.get_me().username
    if not user:
        bot.send_message(message.chat.id, "❌ /start را بزنید")
        return
    text = f"💰 کیف پول\n\nموجودی: {balance:,} تومان\nکل درآمد: {user['total_earned']:,} تومان\n\n🎁 لینک رفرال:\nhttps://t.me/{bot_username}?start={user['referral_code']}"
    markup = types.InlineKeyboardMarkup()
    if balance >= 2000000:
        markup.add(types.InlineKeyboardButton("🏧 برداشت", callback_data="withdraw"))
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "withdraw")
def withdraw_request(call):
    msg = bot.send_message(call.message.chat.id, "💳 لطفاً شماره کارت خود را وارد کنید:")
    bot.register_next_step_handler(msg, process_withdraw)

def process_withdraw(message):
    user_id = message.from_user.id
    card = message.text.strip()
    balance = get_user_balance(user_id)
    if not re.match(r'^\d{16}$', card.replace(' ', '')):
        bot.reply_to(message, "❌ شماره کارت نامعتبر است. لطفاً ۱۶ رقم کارت را وارد کنید.")
        return
    if balance < 2000000:
        bot.reply_to(message, f"❌ موجودی کافی نیست. حداقل برداشت ۲,۰۰۰,۰۰۰ تومان است.\nموجودی فعلی: {balance:,} تومان")
        return
    with get_db() as conn:
        conn.execute('INSERT INTO withdraw_requests (user_id, amount, card_number, created_at) VALUES (?, ?, ?, ?)', (user_id, balance, card, datetime.now().isoformat()))
        conn.execute('UPDATE users SET balance = 0 WHERE user_id = ?', (user_id,))
        conn.commit()
    bot.reply_to(message, f"✅ درخواست برداشت شما با موفقیت ثبت شد!\n\n💰 مبلغ: {balance:,} تومان\n💳 شماره کارت: {card}\n\n⏳ مبلغ ظرف ۲۴ ساعت آینده به کارت شما واریز خواهد شد.\n🙏 از شکیبایی شما متشکریم.")
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id, f"💰 درخواست برداشت جدید\n👤 کاربر: {user_id}\n💰 مبلغ: {balance:,} تومان\n💳 کارت: {card}")
        except:
            pass

@bot.message_handler(func=lambda m: m.text == '📚 راهنما')
def guide(message):
    bot_username = bot.get_me().username
    guide_text = texts.guide_text.format(config.price, config.card_number, config.card_holder, bot_username)
    bot.send_message(message.chat.id, guide_text)

@bot.message_handler(func=lambda m: m.text == '📞 پشتیبانی')
def support(message):
    bot.send_message(message.chat.id, "📞 پشتیبانی: @shahraghee13")

@bot.message_handler(func=lambda m: m.text and m.text.startswith('📅'))
def show_days(message):
    days = get_subscription_days_left(message.from_user.id)
    bot.send_message(message.chat.id, f"📅 {days} روز مونده" if days > 0 else "❌ اشتراک فعال ندارید")

@bot.message_handler(func=lambda m: m.text == '👑 پنل ادمین')
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    with get_db() as conn:
        pending_payments = conn.execute('SELECT COUNT(*) FROM receipts WHERE status = "pending"').fetchone()[0]
        pending_files = conn.execute('SELECT COUNT(*) FROM pending_files WHERE status = "pending"').fetchone()[0]
        servers_count = conn.execute('SELECT COUNT(*) FROM servers WHERE status = "active"').fetchone()[0]
        total_load = conn.execute('SELECT SUM(current_load) FROM servers').fetchone()[0] or 0
        max_load = conn.execute('SELECT SUM(max_load) FROM servers').fetchone()[0] or 0
        total_users = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        queue_size = conn.execute('SELECT COUNT(*) FROM build_queue WHERE status = "pending"').fetchone()[0]
    text = f"👑 پنل ادمین\n\n👥 کاربران: {total_users}\n📸 فیش: {pending_payments}\n📥 فایل: {pending_files}\n🖥️ سرور: {servers_count}\n📊 بار: {total_load}/{max_load}\n⏳ صف ساخت: {queue_size}"
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("📸 فیش‌ها", callback_data="admin_receipts"), types.InlineKeyboardButton("📥 فایل‌ها", callback_data="admin_files"), types.InlineKeyboardButton("🖥️ سرورها", callback_data="admin_servers"), types.InlineKeyboardButton("➕ سرور جدید", callback_data="admin_add_server"), types.InlineKeyboardButton("💰 برداشت‌ها", callback_data="admin_withdraws"), types.InlineKeyboardButton("📢 پیام همگانی", callback_data="admin_broadcast"), types.InlineKeyboardButton("📝 تنظیم متون", callback_data="admin_texts"), types.InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings"), types.InlineKeyboardButton("🎁 تایید اشتراک", callback_data="admin_manual_sub"), types.InlineKeyboardButton("💳 افزودن روش پرداخت", callback_data="admin_add_payment"), types.InlineKeyboardButton("✏️ تغییر متن خوش‌آمدگویی", callback_data="admin_edit_welcome"), types.InlineKeyboardButton("📦 مدیریت کتابخانه‌ها", callback_data="admin_libraries"))
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_libraries")
def admin_libraries(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    with get_db() as conn:
        installed = conn.execute('SELECT library_name, installed_at, server_id FROM installed_libraries ORDER BY installed_at DESC LIMIT 50').fetchall()
    text = "📦 **مدیریت کتابخانه‌ها**\n\n🔧 کتابخانه‌های نصب شده:\n"
    if installed:
        for lib in installed[:20]:
            text += f"• `{lib['library_name']}`\n"
    else:
        text += "• هیچ کتابخانه‌ای نصب نشده است\n"
    text += f"\n📚 تعداد کل کتابخانه‌های قابل نصب: {len(POPULAR_LIBRARIES)}\n"
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("📦 نصب کتابخانه جدید", callback_data="install_new_library"), types.InlineKeyboardButton("🔧 نصب کتابخانه‌های پرکاربرد", callback_data="install_common_libs"), types.InlineKeyboardButton("🔄 به‌روزرسانی کتابخانه‌ها", callback_data="update_libraries"), types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "install_new_library")
def install_new_library(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "📦 نام کتابخانه مورد نظر را وارد کنید:\n(مثال: requests, telebot, numpy, pandas, python-telegram-bot)")
    bot.register_next_step_handler(msg, process_install_library)

def process_install_library(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    lib_name = message.text.strip()
    if not lib_name:
        bot.reply_to(message, "❌ نام کتابخانه معتبر نیست!")
        return
    status_msg = bot.reply_to(message, f"🔄 در حال نصب کتابخانه {lib_name}...")
    try:
        success, installed_lib = install_library_with_retry(lib_name)
        if success:
            bot.edit_message_text(f"✅ کتابخانه {installed_lib} با موفقیت نصب شد!", message.chat.id, status_msg.message_id)
        else:
            bot.edit_message_text(f"❌ خطا در نصب {lib_name}!\nلطفاً نام کتابخانه را بررسی کنید.", message.chat.id, status_msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)}", message.chat.id, status_msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "install_common_libs")
def install_common_libs(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    status_msg = bot.send_message(call.message.chat.id, "🔄 در حال نصب کتابخانه‌های پرکاربرد...\nاین عملیات ممکن است چند دقیقه طول بکشد.")
    
    installed = []
    failed = []
    
    for i, lib in enumerate(POPULAR_LIBRARIES):
        try:
            bot.edit_message_text(f"🔄 در حال نصب [{i+1}/{len(POPULAR_LIBRARIES)}]: `{lib}`", call.message.chat.id, status_msg.message_id, parse_mode="Markdown")
            success, _ = install_library_with_retry(lib)
            if success:
                installed.append(lib)
            else:
                failed.append(lib)
            time.sleep(0.5)
        except:
            failed.append(lib)
    
    bot.edit_message_text(f"✅ نصب کتابخانه‌ها کامل شد!\n\n📦 نصب شده: {len(installed)} مورد\n❌ ناموفق: {len(failed)} مورد\n\nکتابخانه‌های نصب شده:\n`{', '.join(installed[:15])}`", call.message.chat.id, status_msg.message_id, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "update_libraries")
def update_libraries(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    status_msg = bot.send_message(call.message.chat.id, "🔄 در حال به‌روزرسانی pip...")
    pip_cmd = get_pip_command()
    subprocess.run(f'{pip_cmd} install --upgrade pip', shell=True, capture_output=True, text=True)
    bot.edit_message_text("✅ به‌روزرسانی pip انجام شد!\n\nبرای به‌روزرسانی کتابخانه خاص از گزینه «نصب کتابخانه جدید» استفاده کنید.", call.message.chat.id, status_msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_edit_welcome")
def admin_edit_welcome(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "📝 **تغییر متن خوش‌آمدگویی**\n\nمتن جدید را ارسال کنید.\n\n🔹 از `{}` برای نام ربات استفاده کنید.\n\n**متن فعلی:**\n" + texts.welcome_text[:300])
    bot.register_next_step_handler(msg, save_new_welcome_text)

def save_new_welcome_text(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    texts.welcome_text = message.text
    texts.save_to_db()
    bot.reply_to(message, "✅ متن خوش‌آمدگویی با موفقیت تغییر کرد!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_add_payment")
def admin_add_payment(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("💳 زرین‌پال", callback_data="payment_zarinpal"), types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back"))
    bot.edit_message_text("💳 **افزودن روش پرداخت**\n\nروش پرداخت مورد نظر را انتخاب کنید:\n\n🔹 زرین‌پال - درگاه پرداخت آنلاین\n🔹 کارت به کارت - روش سنتی (فعال)\n\nبرای فعال کردن زرین‌پال، مرچنت کد خود را وارد کنید.", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "payment_zarinpal")
def payment_zarinpal_config(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "💳 **تنظیمات زرین‌پال**\n\nمرچنت کد (Merchant ID) خود را وارد کنید:\nمثال: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`\n\nمرچنت فعلی: " + (config.zarinpal_merchant if config.zarinpal_merchant else "تنظیم نشده"))
    bot.register_next_step_handler(msg, set_zarinpal_merchant)

def set_zarinpal_merchant(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    merchant = message.text.strip()
    if not merchant:
        bot.reply_to(message, "❌ مرچنت کد معتبر نیست!")
        return
    config.zarinpal_merchant = merchant
    config.save_to_db()
    msg = bot.reply_to(message, f"✅ مرچنت کد ذخیره شد!\n\nحالا آدرس بازگشت (Callback URL) را وارد کنید:\nمثال: `https://your-domain.com/callback`")
    bot.register_next_step_handler(msg, set_zarinpal_callback)

def set_zarinpal_callback(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    callback = message.text.strip()
    if not callback:
        bot.reply_to(message, "❌ آدرس بازگشت معتبر نیست!")
        return
    config.zarinpal_callback = callback
    config.save_to_db()
    bot.reply_to(message, "✅ تنظیمات زرین‌پال با موفقیت ذخیره شد!\n\nاکنون کاربران می‌توانند به صورت آنلاین پرداخت کنند.")

@bot.callback_query_handler(func=lambda call: call.data == "admin_texts")
def admin_texts(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("💰 متن خرید اشتراک", callback_data="edit_subscription"), types.InlineKeyboardButton("📚 متن راهنما", callback_data="edit_guide"), types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back"))
    bot.edit_message_text("📝 **مدیریت متون**\n\nهر کدام از متون زیر را می‌توانید تغییر دهید:\n\n🔹 متن خرید اشتراک - هنگام درخواست اشتراک (کارت به کارت)\n🔹 متن راهنما - هنگام درخواست راهنما", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "edit_subscription")
def edit_subscription(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "💰 متن جدید خرید اشتراک را ارسال کنید:\n(از {} برای قیمت، {} برای کارت، {} برای صاحب کارت، {} برای کد، {} برای مدت استفاده کنید)\n\nمتن فعلی:\n" + texts.subscription_text[:200])
    bot.register_next_step_handler(msg, save_subscription_text)

def save_subscription_text(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    texts.subscription_text = message.text
    texts.save_to_db()
    bot.reply_to(message, "✅ متن خرید اشتراک تغییر کرد!")

@bot.callback_query_handler(func=lambda call: call.data == "edit_guide")
def edit_guide(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "📚 متن جدید راهنما را ارسال کنید:\n(از {} برای قیمت، {} برای کارت، {} برای صاحب کارت، {} برای نام ربات استفاده کنید)\n\nمتن فعلی:\n" + texts.guide_text[:200])
    bot.register_next_step_handler(msg, save_guide_text)

def save_guide_text(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    texts.guide_text = message.text
    texts.save_to_db()
    bot.reply_to(message, "✅ متن راهنما تغییر کرد!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast")
def admin_broadcast(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "📢 متن پیام همگانی را ارسال کنید:\n\n(برای ارسال به همه کاربران)")
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    text = message.text
    status_msg = bot.reply_to(message, "🔄 در حال ارسال پیام همگانی...")
    sent_count = send_broadcast(text, message.from_user.id)
    bot.edit_message_text(f"✅ پیام همگانی ارسال شد!\n\n📨 تعداد دریافت‌کنندگان: {sent_count} نفر", message.chat.id, status_msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_receipts")
def admin_receipts_list(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    with get_db() as conn:
        receipts = conn.execute('SELECT * FROM receipts WHERE status = "pending" ORDER BY created_at DESC').fetchall()
    if not receipts:
        bot.send_message(call.message.chat.id, "📸 فیشی وجود ندارد")
        return
    for r in receipts:
        text = f"📸 فیش #{r['id']}\n👤 {r['user_id']}\n💰 {r['amount']:,} تومان\n🆔 {r['payment_code']}"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_payment_{r['id']}"), types.InlineKeyboardButton("❌ رد", callback_data=f"reject_payment_{r['id']}"))
        if os.path.exists(r['receipt_path']):
            with open(r['receipt_path'], 'rb') as f:
                bot.send_photo(call.message.chat.id, f, caption=text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_payment_'))
def approve_payment(call):
    receipt_id = int(call.data.replace('approve_payment_', ''))
    with get_db() as conn:
        receipt = conn.execute('SELECT * FROM receipts WHERE id = ?', (receipt_id,)).fetchone()
        if receipt:
            activate_subscription(receipt['subscription_id'], receipt['user_id'], receipt['amount'])
            conn.execute('UPDATE receipts SET status = "approved" WHERE id = ?', (receipt_id,))
            conn.commit()
            bot.answer_callback_query(call.id, "✅ تایید شد")
            bot.send_message(receipt['user_id'], f"✅ اشتراک شما فعال شد!\n📅 {config.subscription_days} روز اعتبار.\n📤 فایل ربات خود را ارسال کنید.")
            bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_payment_'))
def reject_payment(call):
    receipt_id = int(call.data.replace('reject_payment_', ''))
    with get_db() as conn:
        conn.execute('UPDATE receipts SET status = "rejected" WHERE id = ?', (receipt_id,))
        conn.commit()
        bot.answer_callback_query(call.id, "❌ رد شد")
        bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_files")
def admin_files_list(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    files = get_pending_files()
    if not files:
        bot.send_message(call.message.chat.id, "📥 فایلی وجود ندارد")
        return
    for f in files:
        text = f"📥 فایل #{f['id']}\n👤 کاربر: {f['user_id']}\n📄 {f['file_name']}\n📅 {f['submitted_at'][:10]}"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ تایید و ساخت", callback_data=f"build_file_{f['id']}"), types.InlineKeyboardButton("❌ حذف", callback_data=f"delete_file_{f['id']}"))
        if os.path.exists(f['file_path']):
            with open(f['file_path'], 'rb') as file:
                bot.send_document(call.message.chat.id, file, caption=text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('build_file_'))
def build_file(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    file_id = int(call.data.replace('build_file_', ''))
    msg = bot.send_message(call.message.chat.id, "🔄 **در حال افزودن به صف ساخت...**\n\n⏳ لطفاً شکیبا باشید...\n📦 کتابخانه‌های مورد نیاز به صورت خودکار نصب خواهند شد.", parse_mode="Markdown")
    queue_id = add_to_build_queue(file_id, call.from_user.id)
    if queue_id:
        active_builds[queue_id] = {'chat_id': call.message.chat.id, 'message_id': msg.message_id, 'start_time': datetime.now(), 'file_id': file_id, 'user_id': call.from_user.id}
        update_countdown(call.message.chat.id, msg.message_id, queue_id, datetime.now())
        bot.edit_message_caption(f"✅ فایل به صف ساخت اضافه شد (شماره {queue_id})\n🕐 زمان ساخت: حدود ۶۰ ثانیه دیگر\n📦 کتابخانه‌های مورد نیاز به صورت خودکار نصب می‌شوند\n\n⏳ در حال نمایش ثانیه‌شمار...", call.message.chat.id, call.message.message_id)
    else:
        bot.edit_message_caption("🔄 در حال ساخت مستقیم ربات...\n📦 در حال نصب کتابخانه‌ها...", call.message.chat.id, call.message.message_id)
        result = build_bot_from_pending(file_id, None, call.message.chat.id)
        if result['success']:
            bot.edit_message_caption(f"✅ ربات ساخته شد!\n🤖 {result['name']}\n🔗 https://t.me/{result['username']}\n\n📦 کتابخانه‌های مورد نیاز نصب شدند.", call.message.chat.id, call.message.message_id)
        else:
            bot.edit_message_caption(f"❌ خطا: {result['error']}", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_file_'))
def delete_file(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    file_id = int(call.data.replace('delete_file_', ''))
    update_pending_file_status(file_id, 'deleted')
    bot.answer_callback_query(call.id, "❌ حذف شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_servers")
def admin_servers_list(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    with get_db() as conn:
        servers = conn.execute('SELECT * FROM servers ORDER BY created_at DESC').fetchall()
    if not servers:
        bot.send_message(call.message.chat.id, "🖥️ سروری وجود ندارد\nاز دکمه «➕ سرور جدید» استفاده کنید.")
        return
    text = "🖥️ **سرورها**\n\n"
    for s in servers:
        text += f"🔹 {s['name']}\n   📍 {s['ip']}:{s['port']}\n   📊 {s['current_load']}/{s['max_load']}\n   ✅ {s['status']}\n\n"
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_add_server")
def admin_add_server(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "➕ **افزودن سرور**\n\nاطلاعات را ارسال کنید:\n`نام\nIP\nپورت\nyوزرنیم\nرمز`\n\nمثال:\n`Server1\n192.168.1.100\n22\nroot\n123`")
    bot.register_next_step_handler(msg, process_add_server)

def process_add_server(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    lines = message.text.strip().split('\n')
    if len(lines) < 5:
        bot.reply_to(message, "❌ فرمت صحیح نیست")
        return
    name = lines[0].strip()
    ip = lines[1].strip()
    try:
        port = int(lines[2].strip())
    except:
        port = 22
    username = lines[3].strip()
    password = lines[4].strip()
    status_msg = bot.reply_to(message, "🔄 در حال بررسی...")
    success, msg = add_new_server(name, ip, port, username, password)
    bot.edit_message_text(msg, message.chat.id, status_msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_withdraws")
def admin_withdraws_list(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    with get_db() as conn:
        withdraws = conn.execute('SELECT * FROM withdraw_requests WHERE status = "pending" ORDER BY created_at DESC').fetchall()
    if not withdraws:
        bot.send_message(call.message.chat.id, "💰 درخواستی وجود ندارد")
        return
    for w in withdraws:
        text = f"💰 #{w['id']}\n👤 {w['user_id']}\n💰 {w['amount']:,} تومان\n💳 {w['card_number']}"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_withdraw_{w['id']}"), types.InlineKeyboardButton("❌ رد", callback_data=f"reject_withdraw_{w['id']}"))
        bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_withdraw_'))
def approve_withdraw(call):
    wid = int(call.data.replace('approve_withdraw_', ''))
    with get_db() as conn:
        conn.execute('UPDATE withdraw_requests SET status = "approved" WHERE id = ?', (wid,))
        conn.commit()
    bot.answer_callback_query(call.id, "✅ تایید شد")

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_withdraw_'))
def reject_withdraw(call):
    wid = int(call.data.replace('reject_withdraw_', ''))
    with get_db() as conn:
        w = conn.execute('SELECT * FROM withdraw_requests WHERE id = ?', (wid,)).fetchone()
        if w:
            conn.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (w['amount'], w['user_id']))
            conn.execute('UPDATE withdraw_requests SET status = "rejected" WHERE id = ?', (wid,))
            conn.commit()
    bot.answer_callback_query(call.id, "❌ رد شد")

@bot.callback_query_handler(func=lambda call: call.data == "admin_settings")
def admin_settings(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("💰 تغییر قیمت", callback_data="set_price"), types.InlineKeyboardButton("💳 تغییر کارت", callback_data="set_card"), types.InlineKeyboardButton("👤 تغییر صاحب کارت", callback_data="set_holder"), types.InlineKeyboardButton("⏰ تغییر مدت اشتراک", callback_data="set_duration"), types.InlineKeyboardButton("⚙️ نصب خودکار کتابخانه", callback_data="toggle_auto_install"), types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back"))
    auto_status = "✅ فعال" if config.auto_install_libs else "❌ غیرفعال"
    bot.edit_message_text(f"⚙️ تنظیمات\n\n💰 قیمت: {config.price:,} تومان\n💳 کارت: {config.card_number}\n👤 صاحب کارت: {config.card_holder}\n⏰ مدت اشتراک: {config.subscription_days} روز\n📦 نصب خودکار کتابخانه: {auto_status}", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "toggle_auto_install")
def toggle_auto_install(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    config.auto_install_libs = not config.auto_install_libs
    config.save_to_db()
    bot.answer_callback_query(call.id, f"نصب خودکار کتابخانه‌ها {'فعال' if config.auto_install_libs else 'غیرفعال'} شد")
    admin_settings(call)

@bot.callback_query_handler(func=lambda call: call.data == "set_price")
def set_price(call):
    msg = bot.send_message(call.message.chat.id, f"💰 قیمت جدید (فعلی: {config.price:,}):")
    bot.register_next_step_handler(msg, lambda m: set_config(m, 'price', int))

@bot.callback_query_handler(func=lambda call: call.data == "set_card")
def set_card(call):
    msg = bot.send_message(call.message.chat.id, f"💳 کارت جدید (فعلی: {config.card_number}):")
    bot.register_next_step_handler(msg, lambda m: set_config(m, 'card_number', str))

@bot.callback_query_handler(func=lambda call: call.data == "set_holder")
def set_holder(call):
    msg = bot.send_message(call.message.chat.id, f"👤 صاحب کارت جدید (فعلی: {config.card_holder}):")
    bot.register_next_step_handler(msg, lambda m: set_config(m, 'card_holder', str))

@bot.callback_query_handler(func=lambda call: call.data == "set_duration")
def set_duration(call):
    msg = bot.send_message(call.message.chat.id, f"⏰ مدت اشتراک به روز (فعلی: {config.subscription_days}):")
    bot.register_next_step_handler(msg, lambda m: set_config(m, 'subscription_days', int))

def set_config(message, key, cast):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        val = cast(message.text.strip())
        setattr(config, key, val)
        config.save_to_db()
        bot.reply_to(message, f"✅ {key} تغییر کرد")
    except:
        bot.reply_to(message, "❌ خطا")

@bot.callback_query_handler(func=lambda call: call.data == "admin_manual_sub")
def admin_manual_sub(call):
    msg = bot.send_message(call.message.chat.id, "🎁 آیدی کاربر:")
    bot.register_next_step_handler(msg, process_manual_sub)

def process_manual_sub(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        user_id = int(message.text.strip())
        sub_id, code = create_subscription(user_id, config.price, 'manual')
        if sub_id and activate_subscription(sub_id, user_id, config.price):
            bot.reply_to(message, f"✅ اشتراک {user_id} فعال شد")
            bot.send_message(user_id, f"✅ اشتراک شما فعال شد!\n📤 فایل ربات خود را ارسال کنید.")
        else:
            bot.reply_to(message, "❌ خطا")
    except:
        bot.reply_to(message, "❌ خطا")

@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call):
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    bot.send_message(call.message.chat.id, "🚀 منوی اصلی:", reply_markup=get_main_menu(call.from_user.id))

# ==================== بررسی انقضا ====================

def check_expired():
    while True:
        try:
            with get_db() as conn:
                expired = conn.execute('SELECT user_id FROM users WHERE active_subscription = 1 AND julianday(subscription_expire) - julianday("now") < 0').fetchall()
                for user in expired:
                    conn.execute('UPDATE users SET active_subscription = 0 WHERE user_id = ?', (user['user_id'],))
                    bots = conn.execute('SELECT id, server_id FROM bots WHERE user_id = ? AND status = "running"', (user['user_id'],)).fetchall()
                    for bot_info in bots:
                        stop_bot_on_mother(bot_info['id'])
                        conn.execute('UPDATE bots SET status = "expired" WHERE id = ?', (bot_info['id'],))
                    try:
                        bot.send_message(user['user_id'], "❌ اشتراک شما منقضی شد!\nربات شما غیرفعال شد.\nبرای ادامه، اشتراک جدید بخرید.")
                    except:
                        pass
                warning = conn.execute('SELECT user_id, subscription_expire FROM users WHERE active_subscription = 1 AND julianday(subscription_expire) - julianday("now") BETWEEN 0 AND 3').fetchall()
                for user in warning:
                    days_left = (datetime.fromisoformat(user['subscription_expire']) - datetime.now()).days
                    if days_left > 0:
                        try:
                            bot.send_message(user['user_id'], f"⚠️ {days_left} روز تا اتمام اشتراک!\nلطفاً تمدید کنید تا ربات شما غیرفعال نشود.")
                        except:
                            pass
                conn.commit()
            time.sleep(3600)
        except Exception as e:
            logger.error(f"check_expired error: {e}")
            time.sleep(3600)

# ==================== اجرا ====================

if __name__ == "__main__":
    check_and_create_pid()
    
    print("=" * 70)
    print("🚀 ربات مادر نسخه نهایی 19.0 - نصب تضمینی تمام کتابخانه‌ها")
    print("=" * 70)
    print(f"✅ ادمین: {ADMIN_IDS}")
    print(f"✅ قیمت: {config.price:,} تومان")
    print(f"✅ مدت اشتراک: {config.subscription_days} روز")
    print(f"✅ نصب خودکار کتابخانه: {'فعال' if config.auto_install_libs else 'غیرفعال'}")
    print(f"✅ کتابخانه‌های قابل نصب: {len(POPULAR_LIBRARIES)} مورد")
    print("=" * 70)
    print("🟢 در حال بازیابی ربات‌های قبلی...")
    
    restore_all_bots()
    
    print("✅ ربات‌ها بازیابی شدند!")
    print("🟢 ربات مادر در حال اجراست...")
    print("=" * 70)
    print("📌 ویژگی‌های جدید نسخه 19.0:")
    print("🔹 نصب خودکار python-telegram-bot و تمام کتابخانه‌های تلگرام")
    print("🔹 دیتابیس کامل 100+ کتابخانه با نام صحیح نصب")
    print("🔹 تشخیص هوشمند کتابخانه‌های مورد نیاز از کد")
    print("🔹 3 بار تلاش مجدد برای نصب هر کتابخانه")
    print("=" * 70)
    
    expiry_thread = threading.Thread(target=check_expired, daemon=True)
    expiry_thread.start()
    
    queue_worker_thread = threading.Thread(target=queue_worker, daemon=True)
    queue_worker_thread.start()
    
    while True:
        try:
            bot.remove_webhook()
            time.sleep(1)
            bot.infinity_polling(timeout=60, skip_pending=True)
        except Exception as e:
            print(f"خطا: {e}")
            print("در حال تلاش مجدد در 5 ثانیه...")
            time.sleep(5)
# ==================== دیتابیس قوی - جداول و توابع جدید ====================

with get_db() as conn:
    # جدول تراکنش‌های مالی
    conn.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            type TEXT,
            description TEXT,
            reference_id TEXT,
            balance_before INTEGER,
            balance_after INTEGER,
            created_at TIMESTAMP
        )
    ''')
    
    # جدول لاگ فعالیت‌ها
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            details TEXT,
            created_at TIMESTAMP
        )
    ''')
    
    # جدول تیکت پشتیبانی
    conn.execute('''
        CREATE TABLE IF NOT EXISTS support_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            subject TEXT,
            message TEXT,
            status TEXT DEFAULT 'open',
            admin_response TEXT,
            created_at TIMESTAMP,
            closed_at TIMESTAMP
        )
    ''')
    
    # جدول اعلان‌ها
    conn.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            message TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP
        )
    ''')
    
    # ایندکس‌های جدید
    conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id, created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_support_tickets_user ON support_tickets(user_id, status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_user_logs_user ON user_logs(user_id, created_at)")
    
    conn.commit()

# ==================== توابع جدید دیتابیس ====================

def log_transaction(user_id, amount, trans_type, description, reference_id=None):
    """ثبت تراکنش مالی"""
    try:
        with get_db() as conn:
            balance_before = get_user_balance(user_id)
            if trans_type == 'deposit':
                conn.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
            elif trans_type == 'withdraw':
                conn.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (amount, user_id))
            balance_after = get_user_balance(user_id)
            conn.execute('''
                INSERT INTO transactions (user_id, amount, type, description, reference_id, balance_before, balance_after, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, amount, trans_type, description, reference_id, balance_before, balance_after, datetime.now().isoformat()))
            conn.commit()
            return True
    except:
        return False

def get_transactions(user_id, limit=20):
    """دریافت تراکنش‌های کاربر"""
    try:
        with get_db() as conn:
            return [dict(t) for t in conn.execute('''
                SELECT * FROM transactions WHERE user_id = ? ORDER BY created_at DESC LIMIT ?
            ''', (user_id, limit)).fetchall()]
    except:
        return []

def log_user_action(user_id, action, details=None):
    """ثبت فعالیت کاربر"""
    try:
        with get_db() as conn:
            conn.execute('''
                INSERT INTO user_logs (user_id, action, details, created_at)
                VALUES (?, ?, ?, ?)
            ''', (user_id, action, details, datetime.now().isoformat()))
            conn.commit()
            return True
    except:
        return False

def create_ticket(user_id, subject, message):
    """ایجاد تیکت پشتیبانی"""
    try:
        with get_db() as conn:
            conn.execute('''
                INSERT INTO support_tickets (user_id, subject, message, created_at)
                VALUES (?, ?, ?, ?)
            ''', (user_id, subject, message, datetime.now().isoformat()))
            conn.commit()
            return conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    except:
        return None

def get_user_tickets(user_id):
    """دریافت تیکت‌های کاربر"""
    try:
        with get_db() as conn:
            return [dict(t) for t in conn.execute('''
                SELECT * FROM support_tickets WHERE user_id = ? ORDER BY created_at DESC
            ''', (user_id,)).fetchall()]
    except:
        return []

def add_notification(user_id, title, message):
    """ارسال اعلان به کاربر"""
    try:
        with get_db() as conn:
            conn.execute('''
                INSERT INTO notifications (user_id, title, message, created_at)
                VALUES (?, ?, ?, ?)
            ''', (user_id, title, message, datetime.now().isoformat()))
            conn.commit()
            return True
    except:
        return False

def get_notifications(user_id):
    """دریافت اعلان‌های کاربر"""
    try:
        with get_db() as conn:
            return [dict(n) for n in conn.execute('''
                SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 20
            ''', (user_id,)).fetchall()]
    except:
        return []

def mark_notification_read(notif_id):
    """علامت خوانده شدن اعلان"""
    try:
        with get_db() as conn:
            conn.execute('UPDATE notifications SET is_read = 1 WHERE id = ?', (notif_id,))
            conn.commit()
            return True
    except:
        return False

def get_user_stats_full(user_id):
    """آمار کامل کاربر"""
    try:
        with get_db() as conn:
            bot_count = conn.execute('SELECT COUNT(*) FROM bots WHERE user_id = ?', (user_id,)).fetchone()[0]
            total_withdraw = conn.execute('SELECT IFNULL(SUM(amount), 0) FROM withdraw_requests WHERE user_id = ? AND status = "approved"', (user_id,)).fetchone()[0]
            referral_count = conn.execute('SELECT COUNT(*) FROM users WHERE referred_by = ?', (user_id,)).fetchone()[0]
            return {
                'bot_count': bot_count,
                'total_withdraw': total_withdraw,
                'referral_count': referral_count
            }
    except:
        return {'bot_count': 0, 'total_withdraw': 0, 'referral_count': 0}

def get_database_info():
    """اطلاعات دیتابیس"""
    try:
        with get_db() as conn:
            return {
                'users': conn.execute('SELECT COUNT(*) FROM users').fetchone()[0],
                'bots': conn.execute('SELECT COUNT(*) FROM bots').fetchone()[0],
                'transactions': conn.execute('SELECT COUNT(*) FROM transactions').fetchone()[0],
                'total_balance': conn.execute('SELECT IFNULL(SUM(balance), 0) FROM users').fetchone()[0],
            }
    except:
        return {}

def weekly_optimize():
    """بهینه‌سازی هفتگی دیتابیس"""
    def optimize():
        while True:
            time.sleep(7 * 24 * 3600)
            try:
                with get_db() as conn:
                    conn.execute("VACUUM")
                    conn.execute("ANALYZE")
                    conn.execute("PRAGMA optimize")
                print("✅ دیتابیس بهینه شد")
            except: pass
    threading.Thread(target=optimize, daemon=True).start()

# شروع بهینه‌سازی خودکار
weekly_optimize()

# ==================== END دیتابیس قوی ====================            
