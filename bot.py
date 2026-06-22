#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ربات مادر نسخه ۲۱.۱ - رفع باگ تایید فایل + ساخت اتوماتیک فایل‌های آماده
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
import random
import string
import gc
import psutil
import uuid

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
CACHE_DIR = os.path.join(BASE_DIR, "cache")
TEMP_DIR = os.path.join(BASE_DIR, "temp")
READY_FILES_DIR = os.path.join(BASE_DIR, "ready_files")

for dir_path in [DB_DIR, FILES_DIR, RUNNING_DIR, LOGS_DIR, RECEIPTS_DIR, PENDING_FILES_DIR, SERVERS_DIR, BACKUP_DIR, REQUIREMENTS_DIR, CACHE_DIR, TEMP_DIR, READY_FILES_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# ==================== توکن ربات مادر ====================
BOT_TOKEN = "8787172986:AAHtlVXWZTTFUrvWc0OcVI-CehKxkPmF7nA"

# ==================== آیدی ادمین ====================
ADMIN_IDS = [327855654]

# ==================== قیمت اشتراک ====================
SUBSCRIPTION_PRICE = 3000000  # ۳ میلیون تومان

# ==================== صف ساخت ====================
build_queue = Queue()
queue_thread_running = True
active_builds = {}
server_connections = {}

# ==================== تابع ایمن‌سازی Markdown ====================
def safe_markdown(text):
    if not text:
        return text
    chars = ['_', '*', '[', ']', '(', ')', '~', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for ch in chars:
        text = text.replace(ch, f'\\{ch}')
    return text

def safe_send(chat_id, text, parse_mode="Markdown", reply_markup=None, disable_web_page_preview=None):
    try:
        if parse_mode == "Markdown":
            safe_text = safe_markdown(text)
            return bot.send_message(chat_id, safe_text, parse_mode="Markdown", reply_markup=reply_markup, disable_web_page_preview=disable_web_page_preview)
        else:
            return bot.send_message(chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup, disable_web_page_preview=disable_web_page_preview)
    except Exception as e:
        try:
            return bot.send_message(chat_id, text, parse_mode=None, reply_markup=reply_markup, disable_web_page_preview=disable_web_page_preview)
        except:
            return bot.send_message(chat_id, "⚠️ خطا در ارسال پیام", parse_mode=None)

def safe_edit(chat_id, message_id, text, parse_mode="Markdown", reply_markup=None):
    try:
        if parse_mode == "Markdown":
            safe_text = safe_markdown(text)
            return bot.edit_message_text(safe_text, chat_id, message_id, parse_mode="Markdown", reply_markup=reply_markup)
        else:
            return bot.edit_message_text(text, chat_id, message_id, parse_mode=parse_mode, reply_markup=reply_markup)
    except telebot.apihelper.ApiTelegramException as e:
        if "message is not modified" in str(e):
            return True
        elif "can't parse entities" in str(e):
            try:
                return bot.edit_message_text(text, chat_id, message_id, parse_mode=None, reply_markup=reply_markup)
            except:
                return False
        elif "message to edit not found" in str(e):
            return False
        else:
            return False
    except Exception as e:
        return False

# ==================== دیتابیس ====================
class DatabaseManager:
    def __init__(self):
        self.db_path = os.path.join(DB_DIR, 'mother_bot.db')
        self.cache = {}
        self.cache_ttl = {}
        self.cache_lock = threading.RLock()
        self.write_lock = threading.RLock()
        self.connection_pool = []
        self.pool_size = 50
        self.max_connections = 100
        self._init_pool()
        self._init_tables()
        self._init_indexes()
        self._init_triggers()
        self._cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self._cleanup_thread.start()
    
    def _init_pool(self):
        for _ in range(self.pool_size):
            conn = self._create_connection()
            self.connection_pool.append(conn)
    
    def _create_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=300, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA wal_autocheckpoint=1000")
        conn.execute("PRAGMA cache_size=-2097152")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA mmap_size=536870912")
        conn.execute("PRAGMA page_size=4096")
        conn.execute("PRAGMA max_page_count=1073741823")
        return conn
    
    def get_connection(self):
        with self.cache_lock:
            if self.connection_pool:
                conn = self.connection_pool.pop()
                try:
                    conn.execute("SELECT 1").fetchone()
                    return conn
                except:
                    conn.close()
                    return self._create_connection()
            return self._create_connection()
    
    def return_connection(self, conn):
        with self.cache_lock:
            if len(self.connection_pool) < self.pool_size:
                try:
                    self.connection_pool.append(conn)
                except:
                    conn.close()
            else:
                conn.close()
    
    @contextmanager
    def get_db(self):
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            self.return_connection(conn)
    
    def _init_tables(self):
        with self.get_db() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    referral_code TEXT UNIQUE,
                    referred_by INTEGER,
                    balance INTEGER DEFAULT 0,
                    total_earned INTEGER DEFAULT 0,
                    active_subscription INTEGER DEFAULT 0,
                    subscription_expire TIMESTAMP,
                    subscription_id INTEGER,
                    total_bots INTEGER DEFAULT 0,
                    created_at TIMESTAMP,
                    last_seen TIMESTAMP,
                    is_locked INTEGER DEFAULT 0,
                    lock_reason TEXT
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    subscription_code TEXT UNIQUE,
                    status TEXT DEFAULT 'pending',
                    amount INTEGER,
                    payment_method TEXT DEFAULT 'card',
                    payment_url TEXT,
                    authority TEXT,
                    created_at TIMESTAMP,
                    paid_at TIMESTAMP,
                    expires_at TIMESTAMP,
                    auto_renew INTEGER DEFAULT 0,
                    is_verified INTEGER DEFAULT 0
                )
            ''')
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
                    is_active INTEGER DEFAULT 1,
                    is_ready INTEGER DEFAULT 0,
                    ready_file_id INTEGER DEFAULT 0
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS servers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    ip TEXT UNIQUE,
                    port INTEGER,
                    username TEXT,
                    password TEXT,
                    status TEXT DEFAULT 'active',
                    current_load INTEGER DEFAULT 0,
                    max_load INTEGER DEFAULT 50,
                    created_at TIMESTAMP,
                    last_heartbeat TIMESTAMP,
                    installed_libs TEXT,
                    is_active INTEGER DEFAULT 1,
                    cpu_usage INTEGER DEFAULT 0,
                    memory_usage INTEGER DEFAULT 0
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS bots (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    subscription_id INTEGER,
                    server_id INTEGER,
                    token TEXT,
                    name TEXT,
                    username TEXT,
                    file_path TEXT,
                    pid INTEGER,
                    status TEXT DEFAULT 'stopped',
                    created_at TIMESTAMP,
                    expires_at TIMESTAMP,
                    requirements TEXT,
                    start_count INTEGER DEFAULT 0,
                    last_start TIMESTAMP,
                    is_deleted INTEGER DEFAULT 0,
                    bot_type TEXT DEFAULT 'custom'
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS ready_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    file_name TEXT,
                    file_path TEXT,
                    description TEXT,
                    price INTEGER DEFAULT 3000000,
                    created_at TIMESTAMP,
                    is_active INTEGER DEFAULT 1
                )
            ''')
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
                    is_verified INTEGER DEFAULT 0
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS withdraw_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount INTEGER,
                    card_number TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP,
                    processed_at TIMESTAMP,
                    is_verified INTEGER DEFAULT 0
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS broadcast_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER,
                    message_text TEXT,
                    sent_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP,
                    is_active INTEGER DEFAULT 1
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS build_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER,
                    user_id INTEGER,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    error_message TEXT,
                    bot_name TEXT,
                    bot_username TEXT,
                    is_active INTEGER DEFAULT 1
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS installed_libraries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    library_name TEXT UNIQUE,
                    installed_at TIMESTAMP,
                    server_id INTEGER,
                    status TEXT DEFAULT 'installed',
                    version TEXT
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS texts (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS referral_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER,
                    referred_id INTEGER,
                    status TEXT DEFAULT 'registered',
                    created_at TIMESTAMP,
                    subscription_bought_at TIMESTAMP,
                    is_active INTEGER DEFAULT 1,
                    bonus_amount INTEGER DEFAULT 0,
                    is_paid INTEGER DEFAULT 0
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount INTEGER,
                    type TEXT,
                    description TEXT,
                    created_at TIMESTAMP,
                    is_verified INTEGER DEFAULT 1,
                    reference_id TEXT
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS backups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT,
                    created_at TIMESTAMP,
                    size INTEGER,
                    is_active INTEGER DEFAULT 1
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT,
                    message TEXT,
                    created_at TIMESTAMP,
                    source TEXT
                )
            ''')
            conn.commit()
    
    def _init_indexes(self):
        try:
            with self.get_db() as conn:
                conn.execute('CREATE INDEX IF NOT EXISTS idx_users_referral_code ON users(referral_code)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_users_referred_by ON users(referred_by)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_users_active_sub ON users(active_subscription)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_users_balance ON users(balance)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_bots_user_id ON bots(user_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_bots_status ON bots(status)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_bots_server_id ON bots(server_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_bots_created_at ON bots(created_at)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_pending_files_user_id ON pending_files(user_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_pending_files_status ON pending_files(status)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_withdraw_requests_user_id ON withdraw_requests(user_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_withdraw_requests_status ON withdraw_requests(status)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_referral_logs_referrer ON referral_logs(referrer_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_referral_logs_referred ON referral_logs(referred_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_servers_status ON servers(status)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_build_queue_status ON build_queue(status)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_ready_files_is_active ON ready_files(is_active)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_pending_files_is_ready ON pending_files(is_ready)')
                conn.commit()
        except Exception as e:
            print(f"⚠️ خطا در ایجاد ایندکس‌ها: {e}")
    
    def _init_triggers(self):
        try:
            with self.get_db() as conn:
                conn.execute('''
                    CREATE TRIGGER IF NOT EXISTS update_user_last_seen
                    AFTER UPDATE ON users
                    WHEN NEW.last_seen IS NULL
                    BEGIN
                        UPDATE users SET last_seen = CURRENT_TIMESTAMP WHERE user_id = NEW.user_id;
                    END
                ''')
                conn.commit()
        except Exception as e:
            print(f"⚠️ خطا در ایجاد تریگرها: {e}")
    
    def _cleanup_worker(self):
        while True:
            try:
                time.sleep(3600)
                with self.get_db() as conn:
                    conn.execute("VACUUM")
                    conn.execute("DELETE FROM build_queue WHERE is_active = 0 AND created_at < datetime('now', '-7 days')")
                    conn.execute("DELETE FROM pending_files WHERE is_active = 0 AND submitted_at < datetime('now', '-30 days')")
                    conn.execute("DELETE FROM system_logs WHERE created_at < datetime('now', '-90 days')")
                    conn.commit()
                with self.cache_lock:
                    now = time.time()
                    for key in list(self.cache_ttl.keys()):
                        if self.cache_ttl[key] < now:
                            del self.cache[key]
                            del self.cache_ttl[key]
                gc.collect()
                logger.info("🧹 پاکسازی و بهینه‌سازی دیتابیس انجام شد")
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
    
    def get_cached(self, key, max_age=300):
        with self.cache_lock:
            if key in self.cache and self.cache_ttl.get(key, 0) > time.time():
                return self.cache[key]
            return None
    
    def set_cached(self, key, value, ttl=300):
        with self.cache_lock:
            self.cache[key] = value
            self.cache_ttl[key] = time.time() + ttl

db_manager = DatabaseManager()

@contextmanager
def get_db():
    with db_manager.get_db() as conn:
        yield conn

# ==================== لیست کتابخانه‌های پرکاربرد ====================
POPULAR_LIBRARIES = [
    "pyTelegramBotAPI", "python-telegram-bot", "telethon", "aiogram", "pyrogram",
    "requests", "aiohttp", "httpx", "urllib3", "websocket-client", "websockets",
    "numpy", "pandas", "scipy", "scikit-learn", "statsmodels", "sympy", "networkx", "polars", "dask",
    "nltk", "spacy", "transformers", "torch", "tensorflow", "keras",
    "matplotlib", "seaborn", "plotly", "Pillow", "opencv-python", "imageio", "scikit-image", "bokeh", "dash", "altair",
    "beautifulsoup4", "lxml", "selenium", "scrapy", "requests-html", "mechanize",
    "sqlalchemy", "pymongo", "redis", "psycopg2-binary", "asyncpg", "aiosqlite", "peewee", "mysql-connector-python", "pymysql",
    "celery", "pika", "rq", "dramatiq",
    "cryptography", "PyJWT", "python-jose", "passlib", "bcrypt", "oauthlib", "authlib", "pycryptodome",
    "python-dotenv", "pyyaml", "loguru", "rich", "tqdm", "click", "colorama", "cachetools", "lru-dict", "faker",
    "python-dateutil", "pytz", "arrow", "pendulum", "humanize", "emoji",
    "jdatetime", "persiantools", "hazm", "persian-validator",
    "youtube-dl", "yt-dlp", "pytube", "spotipy", "moviepy", "pydub", "SpeechRecognition", "pyttsx3", "ffmpeg-python", "librosa", "pyaudio",
    "openpyxl", "xlrd", "xlwt", "xlsxwriter", "reportlab", "pdfkit", "weasyprint", "tabulate",
    "qrcode", "pyqrcode", "python-barcode",
    "flask", "django", "fastapi", "uvicorn", "tornado", "quart", "sanic",
    "paramiko", "scp", "fabric", "netmiko",
    "jinja2", "markdown", "playwright", "pyautogui", "pyperclip", "python-magic", "chardet", "ftfy", "unidecode"
]

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
    'pprint', 'reprlib', 'weakref', 'copyreg', 'shelve',
    'dbm', 'cProfile', 'profile', 'pstats', 'filecmp', 'linecache',
    'textwrap', 'stringprep', 'readline', 'rlcompleter', 'telnetlib',
    'curses', 'pty', 'tty', 'fcntl', 'pipes', 'posix', 'grp', 'pwd',
    'spwd', 'resource', 'nis', 'termios', 'tty', 'syslog'
}

# ==================== مپینگ کتابخانه‌ها ====================
LIBRARY_MAPPING = {
    "telebot": "pyTelegramBotAPI",
    "pyTelegramBotAPI": "pyTelegramBotAPI",
    "telethon": "telethon",
    "aiogram": "aiogram",
    "pyrogram": "pyrogram",
    "python-telegram-bot": "python-telegram-bot",
    "telegram": "python-telegram-bot",
    "telegram.ext": "python-telegram-bot",
    "telegram.bot": "python-telegram-bot",
    "requests": "requests",
    "aiohttp": "aiohttp",
    "httpx": "httpx",
    "urllib3": "urllib3",
    "websocket": "websocket-client",
    "websockets": "websockets",
    "numpy": "numpy",
    "pandas": "pandas",
    "scipy": "scipy",
    "scikit-learn": "scikit-learn",
    "sklearn": "scikit-learn",
    "statsmodels": "statsmodels",
    "sympy": "sympy",
    "networkx": "networkx",
    "nltk": "nltk",
    "spacy": "spacy",
    "transformers": "transformers",
    "torch": "torch",
    "tensorflow": "tensorflow",
    "keras": "keras",
    "polars": "polars",
    "dask": "dask",
    "matplotlib": "matplotlib",
    "seaborn": "seaborn",
    "plotly": "plotly",
    "PIL": "Pillow",
    "Pillow": "Pillow",
    "opencv-python": "opencv-python",
    "cv2": "opencv-python",
    "imageio": "imageio",
    "scikit-image": "scikit-image",
    "bokeh": "bokeh",
    "dash": "dash",
    "altair": "altair",
    "beautifulsoup4": "beautifulsoup4",
    "bs4": "beautifulsoup4",
    "lxml": "lxml",
    "selenium": "selenium",
    "scrapy": "scrapy",
    "requests-html": "requests-html",
    "mechanize": "mechanize",
    "sqlalchemy": "sqlalchemy",
    "pymongo": "pymongo",
    "redis": "redis",
    "psycopg2": "psycopg2-binary",
    "psycopg2-binary": "psycopg2-binary",
    "asyncpg": "asyncpg",
    "aiosqlite": "aiosqlite",
    "peewee": "peewee",
    "mysql-connector-python": "mysql-connector-python",
    "pymysql": "pymysql",
    "celery": "celery",
    "pika": "pika",
    "rq": "rq",
    "dramatiq": "dramatiq",
    "cryptography": "cryptography",
    "PyJWT": "PyJWT",
    "jwt": "PyJWT",
    "passlib": "passlib",
    "bcrypt": "bcrypt",
    "python-jose": "python-jose",
    "oauthlib": "oauthlib",
    "authlib": "authlib",
    "pycryptodome": "pycryptodome",
    "python-dotenv": "python-dotenv",
    "pyyaml": "pyyaml",
    "loguru": "loguru",
    "rich": "rich",
    "tqdm": "tqdm",
    "click": "click",
    "colorama": "colorama",
    "cachetools": "cachetools",
    "lru-dict": "lru-dict",
    "faker": "faker",
    "python-dateutil": "python-dateutil",
    "pytz": "pytz",
    "arrow": "arrow",
    "pendulum": "pendulum",
    "humanize": "humanize",
    "emoji": "emoji",
    "jdatetime": "jdatetime",
    "persiantools": "persiantools",
    "hazm": "hazm",
    "persian-validator": "persian-validator",
    "youtube-dl": "youtube-dl",
    "yt-dlp": "yt-dlp",
    "pytube": "pytube",
    "spotipy": "spotipy",
    "moviepy": "moviepy",
    "pydub": "pydub",
    "SpeechRecognition": "SpeechRecognition",
    "pyttsx3": "pyttsx3",
    "ffmpeg-python": "ffmpeg-python",
    "librosa": "librosa",
    "pyaudio": "pyaudio",
    "openpyxl": "openpyxl",
    "xlrd": "xlrd",
    "xlwt": "xlwt",
    "xlsxwriter": "xlsxwriter",
    "reportlab": "reportlab",
    "pdfkit": "pdfkit",
    "weasyprint": "weasyprint",
    "tabulate": "tabulate",
    "qrcode": "qrcode",
    "pyqrcode": "pyqrcode",
    "python-barcode": "python-barcode",
    "flask": "flask",
    "django": "django",
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "tornado": "tornado",
    "quart": "quart",
    "sanic": "sanic",
    "paramiko": "paramiko",
    "scp": "scp",
    "fabric": "fabric",
    "netmiko": "netmiko",
    "jinja2": "jinja2",
    "markdown": "markdown",
    "playwright": "playwright",
    "pyautogui": "pyautogui",
    "pyperclip": "pyperclip",
    "python-magic": "python-magic",
    "chardet": "chardet",
    "ftfy": "ftfy",
    "unidecode": "unidecode",
}

# ==================== تنظیمات متون ====================
class Texts:
    def __init__(self):
        self.welcome_text = """🚀 به ربات سازنده ربات حرفه‌ای خوش آمدید!

👤 کاربر عزیز، شما می‌توانید با خرید اشتراک، ربات تلگرامی خود را بسازید.

📌 نحوه کار:
1️⃣ خرید اشتراک (۳,۰۰۰,۰۰۰ تومان)
2️⃣ انتخاب نوع ساخت (فایل شخصی یا فایل آماده)
3️⃣ پس از تایید، ربات ساخته می‌شود

💰 هر اشتراک = ۱ ربات (به مدت ۳۰ روز)
🎁 سیستم رفرال: ۱۰٪ از درآمد دوستانتان به شما تعلق می‌گیرد

@{} - پشتیبانی"""
        
        self.subscription_text = """💰 **خرید اشتراک**

💳 شماره کارت: {}
👤 به نام: {}

📌 مراحل:
1️⃣ مبلغ ۳,۰۰۰,۰۰۰ تومان را به کارت بالا واریز کنید
2️⃣ کد زیر را در رسید یادداشت کنید
3️⃣ تصویر فیش را ارسال کنید

🆔 کد پیگیری: `{}`
💰 مبلغ: {} تومان
⏰ مدت اشتراک: {} روز

🎁 پاداش رفرال: ۱۰%"""
        
        self.guide_text = """📚 **راهنمای کامل**

1️⃣ **خرید اشتراک:**
   • روی دکمه خرید اشتراک کلیک کنید
   • مبلغ ۳,۰۰۰,۰۰۰ تومان را واریز کنید
   • فیش را ارسال کنید

2️⃣ **سیستم رفرال:**
   • لینک اختصاصی خود را به دوستان بدهید
   • از هر خرید دوستان، ۱۰٪ به حساب شما واریز می‌شود
   • پس از رسیدن موجودی به ۲,۰۰۰,۰۰۰ تومان می‌توانید برداشت کنید

3️⃣ **ساخت ربات:**
   • گزینه «ساخت ربات جدید» را انتخاب کنید
   • می‌توانید فایل شخصی ارسال کنید یا از فایل‌های آماده استفاده کنید

4️⃣ **مدیریت ربات:**
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
        self.price = 3000000
        self.card_number = "5892101187322777"
        self.card_holder = "مرتضی نیکخو خنجری"
        self.subscription_days = 30
        self.zarinpal_merchant = ""
        self.zarinpal_callback = ""
        self.auto_install_libs = True
        self.referral_bonus = 10
        self.min_withdraw = 2000000
        self.min_deposit = 3000000
    
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
                    elif row['key'] == 'referral_bonus':
                        self.referral_bonus = int(row['value'])
                    elif row['key'] == 'min_withdraw':
                        self.min_withdraw = int(row['value'])
                    elif row['key'] == 'min_deposit':
                        self.min_deposit = int(row['value'])
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
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('referral_bonus', str(self.referral_bonus)))
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('min_withdraw', str(self.min_withdraw)))
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('min_deposit', str(self.min_deposit)))
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

# ==================== توابع دیتابیس ====================

def generate_referral_code(user_id):
    return hashlib.md5(f"REFERRAL_{user_id}_2024_MASTER".encode()).hexdigest()[:10].upper()

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
            conn.execute('INSERT INTO users (user_id, username, first_name, last_name, referral_code, referred_by, created_at, last_seen) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', 
                        (user_id, username, first_name, last_name, referral_code, referred_by, now, now))
            conn.commit()
            
            if referred_by and referred_by != user_id:
                conn.execute('INSERT INTO referral_logs (referrer_id, referred_id, status, created_at) VALUES (?, ?, ?, ?)', 
                           (referred_by, user_id, 'registered', now))
                conn.commit()
                
                try:
                    bot.send_message(referred_by, 
                        f"🎉 یک کاربر جدید با رفرال شما وارد شد!\n\n"
                        f"👤 نام: {first_name}\n"
                        f"🆔 آیدی: {user_id}\n"
                        f"💰 اگر اشتراک بخرد، {config.referral_bonus}% پاداش دریافت می‌کنید."
                    )
                except:
                    pass
                
                try:
                    bot.send_message(user_id,
                        f"🎉 شما با لینک رفرال وارد شدید!\n\n"
                        f"اگر اشتراک بخرید، دوست شما {config.referral_bonus}% پاداش می‌گیرد.\n"
                        f"🎁 لینک رفرال خودتان: {referral_code}"
                    )
                except:
                    pass
            
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
            users = conn.execute('SELECT user_id FROM users WHERE is_locked = 0').fetchall()
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
            subscription_code = hashlib.md5(f"{user_id}_{time.time()}_{random.randint(1000,9999)}".encode()).hexdigest()[:16].upper()
            now = datetime.now().isoformat()
            expires_at = (datetime.now() + timedelta(days=config.subscription_days)).isoformat()
            conn.execute('INSERT INTO subscriptions (user_id, subscription_code, amount, payment_method, created_at, expires_at, status, is_verified) VALUES (?, ?, ?, ?, ?, ?, "pending", 0)', 
                        (user_id, subscription_code, amount, payment_method, now, expires_at))
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
            conn.execute('UPDATE users SET active_subscription = 1, subscription_expire = ?, subscription_id = ? WHERE user_id = ?', 
                        (expires_at, subscription_id, user_id))
            conn.execute('UPDATE subscriptions SET status = "active", paid_at = ?, is_verified = 1 WHERE id = ?', 
                        (datetime.now().isoformat(), subscription_id))
            
            user = conn.execute('SELECT referred_by FROM users WHERE user_id = ?', (user_id,)).fetchone()
            if user and user['referred_by']:
                bonus = int(amount * (config.referral_bonus / 100))
                conn.execute('UPDATE users SET balance = balance + ?, total_earned = total_earned + ? WHERE user_id = ?', 
                           (bonus, bonus, user['referred_by']))
                conn.execute('UPDATE referral_logs SET status = "subscribed", subscription_bought_at = ?, bonus_amount = ?, is_paid = 1 WHERE referrer_id = ? AND referred_id = ? AND status = "registered"', 
                           (datetime.now().isoformat(), bonus, user['referred_by'], user_id))
                
                try:
                    bot.send_message(user['referred_by'],
                        f"💰 پاداش رفرال!\n\n"
                        f"👤 کاربری که معرفی کردید اشتراک خرید!\n"
                        f"💰 مبلغ خرید: {amount:,} تومان\n"
                        f"🎁 پاداش شما ({config.referral_bonus}%): {bonus:,} تومان\n"
                        f"📊 موجودی جدید: {get_user_balance(user['referred_by']):,} تومان"
                    )
                except:
                    pass
                
                try:
                    bot.send_message(user_id,
                        f"🎉 تبریک!\n\n"
                        f"شما اشتراک خریدید و دوست شما {bonus:,} تومان پاداش دریافت کرد.\n"
                        f"🎁 لینک رفرال شما: {generate_referral_code(user_id)}"
                    )
                except:
                    pass
            
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"activate_subscription error: {e}")
        return False

def get_user_balance(user_id):
    try:
        with get_db() as conn:
            user = conn.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,)).fetchone()
            return user['balance'] if user else 0
    except:
        return 0

def update_user_balance(user_id, amount, description=None):
    try:
        with get_db() as conn:
            conn.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
            if description:
                ref_id = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:12]
                conn.execute('INSERT INTO transactions (user_id, amount, type, description, created_at, reference_id) VALUES (?, ?, ?, ?, ?, ?)',
                           (user_id, amount, 'balance', description, datetime.now().isoformat(), ref_id))
            conn.commit()
            return True
    except:
        return False

def can_create_bot(user_id):
    try:
        with get_db() as conn:
            return has_active_subscription(user_id)
    except:
        return False

def add_bot(user_id, subscription_id, server_id, bot_id, token, name, username, file_path, pid=None, requirements=None, bot_type='custom'):
    try:
        with get_db() as conn:
            now = datetime.now().isoformat()
            expires_at = (datetime.now() + timedelta(days=config.subscription_days)).isoformat()
            conn.execute('INSERT INTO bots (id, user_id, subscription_id, server_id, token, name, username, file_path, pid, status, created_at, expires_at, requirements, start_count, last_start, is_deleted, bot_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, "running", ?, ?, ?, 1, ?, 0, ?)', 
                        (bot_id, user_id, subscription_id, server_id, token, name, username, file_path, pid, now, expires_at, requirements, now, bot_type))
            conn.execute('UPDATE users SET total_bots = total_bots + 1 WHERE user_id = ?', (user_id,))
            conn.commit()
            return True
    except:
        return False

def get_user_bots(user_id):
    try:
        with get_db() as conn:
            bots = conn.execute('SELECT * FROM bots WHERE user_id = ? AND status NOT IN ("deleted", "deleted_by_user") AND is_deleted = 0 ORDER BY created_at DESC', (user_id,)).fetchall()
            return [dict(bot) for bot in bots]
    except:
        return []

def get_bot_by_id(bot_id):
    try:
        with get_db() as conn:
            bot = conn.execute('SELECT * FROM bots WHERE id = ? AND is_deleted = 0', (bot_id,)).fetchone()
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

def update_bot_start_count(bot_id):
    try:
        with get_db() as conn:
            conn.execute('UPDATE bots SET start_count = start_count + 1, last_start = ? WHERE id = ?', 
                        (datetime.now().isoformat(), bot_id))
            conn.commit()
            return True
    except:
        return False

def delete_bot_complete(bot_id, user_id):
    try:
        with get_db() as conn:
            bot = conn.execute('SELECT * FROM bots WHERE id = ? AND user_id = ? AND is_deleted = 0', (bot_id, user_id)).fetchone()
            if not bot:
                return False
            
            stop_bot_on_mother(bot_id)
            
            bot_dir = os.path.join(RUNNING_DIR, bot_id)
            if os.path.exists(bot_dir):
                shutil.rmtree(bot_dir, ignore_errors=True)
            
            conn.execute('UPDATE bots SET status = "deleted_by_user", is_deleted = 1 WHERE id = ?', (bot_id,))
            conn.commit()
            return True
    except:
        return False

def save_pending_file(user_id, subscription_id, file_path, file_name, file_hash, is_ready=0, ready_file_id=0):
    try:
        with get_db() as conn:
            now = datetime.now().isoformat()
            conn.execute('INSERT INTO pending_files (user_id, subscription_id, file_path, file_name, file_hash, submitted_at, is_active, is_ready, ready_file_id) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)', 
                        (user_id, subscription_id, file_path, file_name, file_hash, now, is_ready, ready_file_id))
            conn.commit()
            return conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    except:
        return None

def get_pending_files():
    try:
        with get_db() as conn:
            files = conn.execute('SELECT * FROM pending_files WHERE status = "pending" AND is_active = 1 ORDER BY submitted_at DESC').fetchall()
            return [dict(f) for f in files]
    except:
        return []

def get_pending_file_by_id(file_id):
    try:
        with get_db() as conn:
            file = conn.execute('SELECT * FROM pending_files WHERE id = ? AND is_active = 1', (file_id,)).fetchone()
            return dict(file) if file else None
    except:
        return None

def update_pending_file_status(file_id, status):
    try:
        with get_db() as conn:
            conn.execute('UPDATE pending_files SET status = ?, reviewed_at = ?, is_active = 0 WHERE id = ?', 
                        (status, datetime.now().isoformat(), file_id))
            conn.commit()
            return True
    except:
        return False

def add_to_build_queue(file_id, user_id):
    try:
        with get_db() as conn:
            conn.execute('INSERT INTO build_queue (file_id, user_id, created_at, is_active) VALUES (?, ?, ?, 1)', 
                        (file_id, user_id, datetime.now().isoformat()))
            conn.commit()
            queue_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            build_queue.put(queue_id)
            return queue_id
    except:
        return None

def update_build_queue_status(queue_id, status, error_message=None, bot_name=None, bot_username=None):
    try:
        with get_db() as conn:
            conn.execute('UPDATE build_queue SET status = ?, completed_at = ?, error_message = ?, bot_name = ?, bot_username = ? WHERE id = ?', 
                        (status, datetime.now().isoformat(), error_message, bot_name, bot_username, queue_id))
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
            conn.execute('INSERT OR REPLACE INTO installed_libraries (library_name, installed_at, server_id, status) VALUES (?, ?, ?, "installed")', 
                        (library_name, datetime.now().isoformat(), server_id))
            conn.commit()
            return True
    except:
        return False

def get_referral_stats(user_id):
    try:
        with get_db() as conn:
            referral_count = conn.execute('SELECT COUNT(*) FROM referral_logs WHERE referrer_id = ? AND status = "registered" AND is_active = 1', (user_id,)).fetchone()[0]
            subscribed_count = conn.execute('SELECT COUNT(*) FROM referral_logs WHERE referrer_id = ? AND status = "subscribed" AND is_active = 1', (user_id,)).fetchone()[0]
            total_bonus = conn.execute('SELECT COALESCE(SUM(bonus_amount), 0) FROM referral_logs WHERE referrer_id = ? AND is_paid = 1', (user_id,)).fetchone()[0]
            return referral_count, subscribed_count, total_bonus
    except:
        return 0, 0, 0

# ==================== توابع فایل‌های آماده ====================

def add_ready_file(name, file_name, file_path, description=""):
    try:
        with get_db() as conn:
            now = datetime.now().isoformat()
            conn.execute('INSERT INTO ready_files (name, file_name, file_path, description, price, created_at, is_active) VALUES (?, ?, ?, ?, ?, ?, 1)', 
                        (name, file_name, file_path, description, SUBSCRIPTION_PRICE, now))
            conn.commit()
            return True
    except:
        return False

def get_ready_files():
    try:
        with get_db() as conn:
            files = conn.execute('SELECT * FROM ready_files WHERE is_active = 1 ORDER BY created_at DESC').fetchall()
            return [dict(f) for f in files]
    except:
        return []

def get_ready_file_by_id(file_id):
    try:
        with get_db() as conn:
            file = conn.execute('SELECT * FROM ready_files WHERE id = ? AND is_active = 1', (file_id,)).fetchone()
            return dict(file) if file else None
    except:
        return None

def delete_ready_file(file_id):
    try:
        with get_db() as conn:
            file = conn.execute('SELECT * FROM ready_files WHERE id = ? AND is_active = 1', (file_id,)).fetchone()
            if file:
                if os.path.exists(file['file_path']):
                    os.remove(file['file_path'])
                conn.execute('UPDATE ready_files SET is_active = 0 WHERE id = ?', (file_id,))
                conn.commit()
                return True
        return False
    except:
        return False

# ==================== سیستم نصب کتابخانه‌ها ====================

def get_pip_command():
    try:
        result = subprocess.run(['pip3', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return 'pip3'
    except:
        pass
    try:
        result = subprocess.run(['pip', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return 'pip'
    except:
        pass
    return f'{sys.executable} -m pip'

def get_correct_library_name(lib_name):
    lib_lower = lib_name.lower().strip()
    
    if lib_lower in LIBRARY_MAPPING:
        return LIBRARY_MAPPING[lib_lower]
    
    for key, value in LIBRARY_MAPPING.items():
        if key.lower().replace('_', '').replace('-', '').replace('.', '') == lib_lower.replace('_', '').replace('-', '').replace('.', ''):
            return value
    
    return lib_name

def check_library_installed(library_name):
    try:
        pip_cmd = get_pip_command()
        result = subprocess.run(
            f'{pip_cmd} show {library_name} 2>/dev/null | grep -E "^(Name|Version)"',
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return True
    except:
        pass
    
    try:
        import importlib
        importlib.import_module(library_name.replace('-', '_'))
        return True
    except:
        pass
    
    return False

def install_library_advanced(library_name, max_retries=5):
    correct_name = get_correct_library_name(library_name)
    pip_cmd = get_pip_command()
    
    if check_library_installed(correct_name):
        logger.info(f"✅ کتابخانه {correct_name} قبلاً نصب شده است")
        mark_library_installed(correct_name, 0)
        return True, correct_name
    
    for retry in range(max_retries):
        logger.info(f"📦 در حال نصب {correct_name} (تلاش {retry + 1}/{max_retries})")
        
        methods = [
            f'{pip_cmd} install {correct_name} --no-cache-dir --default-timeout=100',
            f'{pip_cmd} install --upgrade {correct_name} --no-cache-dir',
            f'{pip_cmd} install {correct_name} --no-deps --no-cache-dir',
            f'{sys.executable} -m pip install {correct_name} --no-cache-dir --default-timeout=100',
        ]
        
        if sys.platform != 'win32':
            methods.append(f'sudo {pip_cmd} install {correct_name} --no-cache-dir --default-timeout=100')
        
        for method_idx, method_cmd in enumerate(methods):
            if method_cmd is None:
                continue
                
            try:
                logger.info(f"  🔄 روش {method_idx + 1}: {method_cmd[:50]}...")
                result = subprocess.run(
                    method_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=180
                )
                
                if result.returncode == 0:
                    logger.info(f"✅ کتابخانه {correct_name} با موفقیت نصب شد (روش {method_idx + 1})")
                    mark_library_installed(correct_name, 0)
                    return True, correct_name
                else:
                    error_msg = result.stderr[:200] if result.stderr else "خطای ناشناخته"
                    logger.warning(f"  ❌ روش {method_idx + 1} ناموفق: {error_msg}")
                    
            except subprocess.TimeoutExpired:
                logger.warning(f"  ⏰ Timeout در روش {method_idx + 1} برای {correct_name}")
            except Exception as e:
                logger.warning(f"  ❌ خطا در روش {method_idx + 1}: {str(e)}")
            
            time.sleep(2)
        
        if retry < max_retries - 1:
            logger.info(f"⏳ صبر قبل از تلاش مجدد برای {correct_name}...")
            time.sleep(3)
    
    logger.error(f"❌ نصب {correct_name} پس از {max_retries} تلاش ناموفق بود")
    return False, None

def install_multiple_libraries_advanced(libraries, progress_callback=None):
    installed = []
    failed = []
    
    unique_libs = []
    for lib in libraries:
        lib_clean = lib.strip().lower()
        if lib_clean not in STD_LIBRARIES and lib_clean not in unique_libs:
            unique_libs.append(lib_clean)
    
    total = len(unique_libs)
    logger.info(f"📦 شروع نصب {total} کتابخانه...")
    
    for i, lib in enumerate(unique_libs):
        if progress_callback:
            progress_callback(i + 1, total, lib)
        
        success, installed_lib = install_library_advanced(lib)
        if success:
            installed.append(installed_lib)
        else:
            failed.append(lib)
        
        time.sleep(0.5)
    
    logger.info(f"✅ نصب کامل شد: {len(installed)} موفق، {len(failed)} ناموفق")
    return installed, failed

def install_libraries_on_mother_advanced(libraries, chat_id=None, message_id=None):
    if not libraries:
        return [], []
    
    installed = []
    failed = []
    status_msg = None
    
    def send_progress(current, total, lib):
        if chat_id and status_msg:
            try:
                percent = int(current / total * 100)
                bar = "█" * int(percent / 5) + "░" * (20 - int(percent / 5))
                text = f"📦 **نصب کتابخانه‌ها**\n\n`[{bar}]` {percent}%\n\n"
                text += f"در حال نصب [{current}/{total}]: `{lib}`\n\n"
                text += f"✅ نصب شده: {len(installed)}\n"
                text += f"❌ ناموفق: {len(failed)}"
                
                safe_edit(chat_id, status_msg.message_id, text, parse_mode="Markdown")
            except:
                pass
        print(f"📦 نصب [{current}/{total}]: {lib}")
    
    if chat_id:
        try:
            status_msg = bot.send_message(
                chat_id,
                f"📦 **در حال نصب {len(libraries)} کتابخانه...**\n⏳ لطفاً شکیبا باشید...",
                parse_mode="Markdown"
            )
        except:
            pass
    
    installed, failed = install_multiple_libraries_advanced(libraries, send_progress)
    
    if chat_id and status_msg:
        result_text = f"✅ **نصب کتابخانه‌ها کامل شد!**\n\n"
        result_text += f"📦 **نصب شده ({len(installed)} مورد):**\n"
        if installed:
            result_text += f"`{', '.join(installed[:30])}`"
            if len(installed) > 30:
                result_text += f"\n... و {len(installed) - 30} مورد دیگر"
        else:
            result_text += "• هیچ کتابخانه‌ای نصب نشد"
        
        if failed:
            result_text += f"\n\n❌ **ناموفق ({len(failed)} مورد):**\n"
            result_text += f"`{', '.join(failed[:20])}`"
            if len(failed) > 20:
                result_text += f"\n... و {len(failed) - 20} مورد دیگر"
            result_text += f"\n\n⚠️ **توجه:** برخی کتابخانه‌ها ممکن است نیاز به نصب دستی داشته باشند.\n"
            result_text += f"برای نصب دستی: `pip3 install {failed[0]}`"
        
        safe_edit(chat_id, status_msg.message_id, result_text, parse_mode="Markdown")
    
    return installed, failed

# ==================== توابع ربات ====================

def detect_requirements_from_code(code):
    imports = set()
    lines = code.split('\n')
    
    for line in lines:
        line = line.strip()
        
        if line.startswith('import '):
            parts = line.split()
            if len(parts) > 1:
                lib = parts[1].split('.')[0].split(' as ')[0]
                if lib not in STD_LIBRARIES and not lib.startswith('_'):
                    imports.add(lib)
        
        elif line.startswith('from '):
            parts = line.split()
            if len(parts) > 1:
                lib = parts[1].split('.')[0]
                if lib not in STD_LIBRARIES and not lib.startswith('_') and lib != '':
                    imports.add(lib)
    
    final_libs = []
    for lib in imports:
        if lib in STD_LIBRARIES:
            continue
        correct = get_correct_library_name(lib)
        if correct not in final_libs:
            final_libs.append(correct)
    
    return final_libs

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

def extract_admin_id(code):
    patterns = [
        r'ADMIN_ID\s*=\s*(\d+)',
        r'admin_id\s*=\s*(\d+)',
        r'ADMIN\s*=\s*(\d+)',
        r'admin\s*=\s*(\d+)',
        r'OWNER_ID\s*=\s*(\d+)',
        r'owner_id\s*=\s*(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, code)
        if match:
            return int(match.group(1))
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

def run_bot_on_mother_server(bot_id, code, token, chat_id=None):
    max_attempts = 3
    attempt = 0
    
    while attempt < max_attempts:
        attempt += 1
        try:
            bot_dir = os.path.join(RUNNING_DIR, bot_id)
            os.makedirs(bot_dir, exist_ok=True)
            
            code_path = os.path.join(bot_dir, 'bot.py')
            with open(code_path, 'w', encoding='utf-8') as f:
                f.write(code)
            
            libraries = detect_requirements_from_code(code)
            
            if libraries and config.auto_install_libs and attempt == 1:
                installed, failed = install_libraries_on_mother_advanced(libraries, chat_id)
                if failed:
                    logger.warning(f"کتابخانه‌های نصب نشده: {failed}")
            
            log_file = os.path.join(bot_dir, 'bot.log')
            
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
            
            time.sleep(5)
            
            if process.poll() is None:
                return process.pid, None
            else:
                with open(log_file, 'r') as f:
                    error = f.read()[-500:]
                if attempt < max_attempts:
                    logger.info(f"تلاش مجدد برای اجرای ربات {bot_id} (تلاش {attempt + 1})")
                    continue
                return None, error if error else "خطای ناشناخته در اجرا"
        except Exception as e:
            if attempt < max_attempts:
                logger.info(f"تلاش مجدد برای اجرای ربات {bot_id} (تلاش {attempt + 1})")
                continue
            return None, str(e)
    
    return None, "خطا در اجرا بعد از ۳ بار تلاش"

def stop_bot_on_mother(bot_id):
    try:
        with get_db() as conn:
            bot = conn.execute('SELECT pid FROM bots WHERE id = ? AND is_deleted = 0', (bot_id,)).fetchone()
            if bot and bot['pid']:
                try:
                    os.kill(bot['pid'], signal.SIGTERM)
                except:
                    pass
                return True
        return False
    except:
        return False

def stop_bot_on_server(server, bot_id):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(server['ip'], port=server['port'], username=server['username'], password=server['password'], timeout=10)
        client.exec_command(f'pkill -f "python.*{bot_id}"')
        client.close()
        return True
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
    
    update_bot_start_count(bot_id)
    pid, error = run_bot_on_mother_server(bot_info['id'], code, bot_info['token'], chat_id)
    if pid:
        update_bot_status(bot_id, 'running')
        return True, "ربات فعال شد"
    else:
        return False, error

# ✅ تابع اصلاح شده برای ساخت ربات از فایل در انتظار
def build_bot_from_pending(file_id, queue_id=None, chat_id=None, auto_build=False):
    result = {'success': False, 'error': None, 'name': None, 'username': None, 'bot_id': None}
    
    pending = get_pending_file_by_id(file_id)
    if not pending:
        result['error'] = "فایل پیدا نشد"
        if queue_id:
            update_build_queue_status(queue_id, 'failed', error_message=result['error'])
        return result
    
    # اگر فایل آماده است و اشتراک فعال دارد، خودکار بساز
    if pending.get('is_ready', 0) == 1 and auto_build:
        # بررسی اشتراک فعال
        if not has_active_subscription(pending['user_id']):
            result['error'] = "اشتراک فعال ندارید!"
            return result
        
        # بررسی اینکه آیا قبلاً ربات ساخته شده
        if not can_create_bot(pending['user_id']):
            result['error'] = "قبلاً با این اشتراک ربات ساخته‌اید!"
            return result
    
    code = None
    if pending['file_name'].endswith('.zip'):
        extract_dir = os.path.join(TEMP_DIR, f"extract_{file_id}_{uuid.uuid4().hex[:8]}")
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
    
    token = extract_token(code)
    if not token:
        result['error'] = "توکن ربات پیدا نشد"
        if queue_id:
            update_build_queue_status(queue_id, 'failed', error_message=result['error'])
        return result
    
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
    
    bot_id = hashlib.md5(f"{pending['user_id']}_{token}_{time.time()}_{uuid.uuid4().hex[:8]}".encode()).hexdigest()[:12]
    
    pid, error = run_bot_on_mother_server(bot_id, code, token, chat_id)
    
    if pid:
        libraries = detect_requirements_from_code(code)
        requirements = ','.join(libraries)
        bot_type = 'ready' if pending.get('is_ready', 0) == 1 else 'custom'
        add_bot(pending['user_id'], pending['subscription_id'], 0, bot_id, token, bot_name, bot_username, pending['file_path'], pid, requirements, bot_type)
        update_pending_file_status(file_id, 'approved')
        result['success'] = True
        result['name'] = bot_name
        result['username'] = bot_username
        result['bot_id'] = bot_id
        if queue_id:
            update_build_queue_status(queue_id, 'completed', bot_name=bot_name, bot_username=bot_username)
        try:
            safe_send(
                pending['user_id'], 
                f"✅ ربات شما با موفقیت ساخته شد!\n\n"
                f"🤖 نام: {bot_name}\n"
                f"🔗 لینک: https://t.me/{bot_username}\n"
                f"🆔 آیدی: {bot_id}\n\n"
                f"از منوی مدیریت ربات می‌توانید آن را فعال/غیرفعال یا حذف کنید.",
                parse_mode=None
            )
        except:
            pass
    else:
        result['error'] = error or "خطا در اجرای ربات"
        if queue_id:
            update_build_queue_status(queue_id, 'failed', error_message=result['error'])
        try:
            safe_send(
                pending['user_id'], 
                f"❌ خطا در ساخت ربات!\n\n"
                f"خطا: {result['error'][:200]}\n\n"
                f"لطفاً با پشتیبانی تماس بگیرید.",
                parse_mode=None
            )
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
        conn.execute('INSERT INTO broadcast_messages (admin_id, message_text, sent_count, created_at, is_active) VALUES (?, ?, ?, ?, 1)', 
                    (admin_id, message_text, sent_count, datetime.now().isoformat()))
        conn.commit()
    return sent_count

def update_countdown(chat_id, message_id, queue_id, start_time):
    try:
        queue_item = get_build_queue_item(queue_id)
        if not queue_item or queue_item['status'] != 'pending':
            return
        
        created_at = datetime.fromisoformat(queue_item['created_at'])
        elapsed = (datetime.now() - created_at).total_seconds()
        total_time = 120
        
        if elapsed >= total_time:
            try:
                bot.send_message(chat_id, "🔄 در حال ساخت نهایی ربات...")
            except:
                pass
            
            result = build_bot_from_pending(queue_item['file_id'], queue_id, chat_id)
            
            if result['success']:
                try:
                    safe_send(
                        chat_id, 
                        f"✅ ربات با موفقیت ساخته شد!\n\n"
                        f"🤖 نام: {result['name']}\n"
                        f"🔗 لینک: https://t.me/{result['username']}\n"
                        f"🆔 آیدی: {result['bot_id']}\n\n"
                        f"🎉 ربات شما آماده استفاده است!",
                        parse_mode=None
                    )
                except:
                    bot.send_message(
                        chat_id, 
                        f"✅ ربات با موفقیت ساخته شد!\n\n"
                        f"🤖 نام: {result['name']}\n"
                        f"🔗 لینک: https://t.me/{result['username']}\n\n"
                        f"🎉 ربات شما آماده استفاده است!"
                    )
            else:
                safe_send(
                    chat_id, 
                    f"❌ خطا در ساخت ربات!\n\n"
                    f"⚠️ خطا: {result['error'][:200]}\n\n"
                    f"لطفاً با پشتیبانی تماس بگیرید.",
                    parse_mode=None
                )
            
            if queue_id in active_builds:
                del active_builds[queue_id]
            return
        
        remaining = int(total_time - elapsed)
        minutes = remaining // 60
        seconds = remaining % 60
        progress = int((elapsed / total_time) * 20)
        bar = "█" * progress + "░" * (20 - progress)
        
        if elapsed < 60:
            phase = "📦 مرحله ۱/۲: آماده‌سازی فایل‌ها"
        else:
            phase = "📚 مرحله ۲/۲: نصب کتابخانه‌ها"
        
        text = f"🔄 ساخت ربات در حال انجام...\n\n{phase}\n⏳ زمان باقی‌مانده: {minutes:02d}:{seconds:02d}\n\n[{bar}]\n\n🔍 در حال پردازش و نصب کتابخانه‌های مورد نیاز...\n🙏 لطفاً شکیبا باشید..."
        
        safe_edit(chat_id, message_id, text, parse_mode=None)
        
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
                    queue_item = conn.execute('SELECT * FROM build_queue WHERE id = ? AND status = "pending" AND is_active = 1', (queue_id,)).fetchone()
                    if queue_item and queue_id in active_builds:
                        build_info = active_builds[queue_id]
                        update_countdown(build_info['chat_id'], build_info['message_id'], queue_id, build_info['start_time'])
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"queue_worker error: {e}")
            time.sleep(1)

def restore_all_bots():
    try:
        with get_db() as conn:
            running_bots = conn.execute("SELECT * FROM bots WHERE (status = 'running' OR status = 'stopped') AND is_deleted = 0").fetchall()
        
        restored_count = 0
        for bot_info in running_bots:
            bot_info = dict(bot_info)
            if os.path.exists(bot_info['file_path']):
                with open(bot_info['file_path'], 'r', encoding='utf-8') as f:
                    code = f.read()
                
                pid, error = run_bot_on_mother_server(bot_info['id'], code, bot_info['token'])
                if pid:
                    with get_db() as conn:
                        conn.execute('UPDATE bots SET status = "running", pid = ? WHERE id = ?', (pid, bot_info['id']))
                        conn.commit()
                    restored_count += 1
                    logger.info(f"ربات {bot_info['id']} ({bot_info['name']}) بازگردانی شد")
                else:
                    with get_db() as conn:
                        conn.execute('UPDATE bots SET status = "stopped" WHERE id = ?', (bot_info['id'],))
                        conn.commit()
                    logger.warning(f"ربات {bot_info['id']} بازگردانی نشد: {error}")
        
        logger.info(f"✅ {restored_count} ربات بازگردانی شدند")
    except Exception as e:
        logger.error(f"خطا در بازگردانی ربات‌ها: {e}")

def restart_all_bots():
    try:
        with get_db() as conn:
            all_bots = conn.execute("SELECT * FROM bots WHERE status NOT IN ('deleted', 'deleted_by_user') AND is_deleted = 0").fetchall()
        
        restarted_count = 0
        for bot_info in all_bots:
            bot_info = dict(bot_info)
            stop_bot_on_mother(bot_info['id'])
            
            if os.path.exists(bot_info['file_path']):
                with open(bot_info['file_path'], 'r', encoding='utf-8') as f:
                    code = f.read()
                
                pid, error = run_bot_on_mother_server(bot_info['id'], code, bot_info['token'])
                if pid:
                    with get_db() as conn:
                        conn.execute('UPDATE bots SET status = "running", pid = ? WHERE id = ?', (pid, bot_info['id']))
                        conn.commit()
                    restarted_count += 1
                    logger.info(f"ربات {bot_info['id']} ریستارت شد")
                else:
                    with get_db() as conn:
                        conn.execute('UPDATE bots SET status = "stopped" WHERE id = ?', (bot_info['id'],))
                        conn.commit()
                    logger.warning(f"ربات {bot_info['id']} ریستارت نشد: {error}")
        
        return restarted_count
    except Exception as e:
        logger.error(f"خطا در ریستارت ربات‌ها: {e}")
        return 0

# ==================== ایجاد و تنظیم ربات ====================
def setup_bot():
    bot_instance = telebot.TeleBot(BOT_TOKEN, num_threads=200)
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
        types.KeyboardButton('🤖 ساخت ربات جدید'),
        types.KeyboardButton('⚙️ مدیریت ربات'),
        types.KeyboardButton('💰 برداشت از کیف پول'),
        types.KeyboardButton('📚 راهنما'),
        types.KeyboardButton('📞 پشتیبانی'),
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
    
    msg = bot.send_message(message.chat.id, 
        "💰 خرید اشتراک\n\n"
        f"💳 شماره کارت: {config.card_number}\n"
        f"👤 به نام: {config.card_holder}\n\n"
        "📌 مبلغ: ۳,۰۰۰,۰۰۰ تومان\n\n"
        "🔹 پس از واریز، فیش را ارسال کنید."
    )
    bot.register_next_step_handler(msg, process_subscription_amount)

def process_subscription_amount(message):
    user_id = message.from_user.id
    
    try:
        amount = SUBSCRIPTION_PRICE
        
        sub_id, sub_code = create_subscription(user_id, amount, 'card')
        if not sub_id:
            bot.reply_to(message, "❌ خطا در ایجاد اشتراک!")
            return
        
        subscription_text = texts.subscription_text.format(
            config.card_number,
            config.card_holder,
            sub_code,
            amount,
            config.subscription_days
        )
        
        safe_send(message.chat.id, subscription_text, parse_mode="Markdown")
        
        bot.send_message(message.chat.id, 
            "📸 پس از واریز، لطفاً تصویر فیش را ارسال کنید.\n\n"
            f"🆔 کد پیگیری: {sub_code}\n"
            f"💰 مبلغ: {amount:,} تومان"
        )
        
    except ValueError:
        bot.reply_to(message, "❌ لطفاً یک عدد معتبر وارد کنید!")

@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    
    with get_db() as conn:
        pending_sub = conn.execute('SELECT * FROM subscriptions WHERE user_id = ? AND status = "pending" AND payment_method = "card" ORDER BY created_at DESC LIMIT 1', (user_id,)).fetchone()
    
    if not pending_sub:
        bot.reply_to(message, "❌ اشتراک در انتظاری ندارید.\nلطفاً ابتدا از دکمه خرید اشتراک استفاده کنید.")
        return
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        payment_code = hashlib.md5(f"{user_id}_{time.time()}_{random.randint(1000,9999)}".encode()).hexdigest()[:12].upper()
        receipt_path = os.path.join(RECEIPTS_DIR, f"{user_id}_{payment_code}.jpg")
        with open(receipt_path, 'wb') as f:
            f.write(downloaded_file)
        
        with get_db() as conn:
            conn.execute('INSERT INTO receipts (user_id, subscription_id, amount, receipt_path, payment_code, created_at, is_verified) VALUES (?, ?, ?, ?, ?, ?, 0)', 
                        (user_id, pending_sub['id'], pending_sub['amount'], receipt_path, payment_code, datetime.now().isoformat()))
            conn.commit()
        
        bot.reply_to(message, 
            f"✅ فیش شما با موفقیت ارسال شد!\n\n"
            f"🆔 کد پیگیری: {payment_code}\n"
            f"💰 مبلغ: {pending_sub['amount']:,} تومان\n"
            f"⏳ پس از تایید، اشتراک شما فعال می‌شود."
        )
        
        for admin_id in ADMIN_IDS:
            try:
                bot.send_photo(admin_id, open(receipt_path, 'rb'), 
                    caption=f"📸 فیش جدید\n\n"
                    f"👤 کاربر: {user_id}\n"
                    f"💰 مبلغ: {pending_sub['amount']:,} تومان\n"
                    f"🆔 کد: {payment_code}\n"
                    f"📅 زمان: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                )
            except:
                pass
                
    except Exception as e:
        bot.reply_to(message, f"❌ خطا در ارسال فیش: {str(e)[:100]}")

@bot.message_handler(func=lambda m: m.text == '🤖 ساخت ربات جدید')
def build_new_bot(message):
    user_id = message.from_user.id
    
    if not has_active_subscription(user_id):
        bot.send_message(message.chat.id, 
            f"❌ **اشتراک فعال ندارید!**\n\n"
            f"💰 برای خرید اشتراک از دکمه زیر استفاده کنید:\n"
            f"🛒 خرید اشتراک",
            parse_mode="Markdown"
        )
        return
    
    if not can_create_bot(user_id):
        bot.send_message(message.chat.id, 
            f"❌ **شما قبلاً با این اشتراک ربات ساخته‌اید!**\n\n"
            f"💰 برای ساخت ربات جدید، اشتراک جدید بخرید.",
            parse_mode="Markdown"
        )
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📤 ارسال فایل شخصی", callback_data="build_custom"),
        types.InlineKeyboardButton("📦 استفاده از فایل آماده", callback_data="build_ready")
    )
    
    bot.send_message(message.chat.id, 
        "🤖 **ساخت ربات جدید**\n\n"
        "لطفاً روش ساخت را انتخاب کنید:\n\n"
        "📤 **فایل شخصی:** فایل .py یا .zip خود را ارسال کنید\n"
        "📦 **فایل آماده:** از فایل‌های آماده استفاده کنید",
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "build_custom")
def build_custom(call):
    user_id = call.from_user.id
    
    if not has_active_subscription(user_id):
        bot.answer_callback_query(call.id, "❌ اشتراک فعال ندارید!", show_alert=True)
        return
    
    if not can_create_bot(user_id):
        bot.answer_callback_query(call.id, "❌ قبلاً ربات ساخته‌اید!", show_alert=True)
        return
    
    bot.answer_callback_query(call.id, "📤 لطفاً فایل ربات خود را ارسال کنید")
    
    bot.send_message(call.message.chat.id, 
        "📤 **ارسال فایل ربات**\n\n"
        "فایل `.py` یا `.zip` خود را ارسال کنید.\n\n"
        "✅ پس از تایید ادمین، ربات ساخته می‌شود.\n"
        "📦 کتابخانه‌های مورد نیاز به صورت خودکار نصب می‌شوند."
    )

@bot.callback_query_handler(func=lambda call: call.data == "build_ready")
def build_ready(call):
    user_id = call.from_user.id
    
    if not has_active_subscription(user_id):
        bot.answer_callback_query(call.id, "❌ اشتراک فعال ندارید!", show_alert=True)
        return
    
    if not can_create_bot(user_id):
        bot.answer_callback_query(call.id, "❌ قبلاً ربات ساخته‌اید!", show_alert=True)
        return
    
    ready_files = get_ready_files()
    
    if not ready_files:
        bot.answer_callback_query(call.id, "❌ هیچ فایل آماده‌ای وجود ندارد!", show_alert=True)
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for file in ready_files:
        markup.add(types.InlineKeyboardButton(
            f"📦 {file['name']}", 
            callback_data=f"select_ready_{file['id']}"
        ))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_build"))
    
    bot.edit_message_text(
        "📦 **انتخاب فایل آماده**\n\n"
        "یکی از فایل‌های زیر را انتخاب کنید:\n\n"
        "⚠️ قیمت: ۳,۰۰۰,۰۰۰ تومان",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('select_ready_'))
def select_ready_file(call):
    file_id = int(call.data.replace('select_ready_', ''))
    user_id = call.from_user.id
    
    if not has_active_subscription(user_id):
        bot.answer_callback_query(call.id, "❌ اشتراک فعال ندارید!", show_alert=True)
        return
    
    if not can_create_bot(user_id):
        bot.answer_callback_query(call.id, "❌ قبلاً ربات ساخته‌اید!", show_alert=True)
        return
    
    ready_file = get_ready_file_by_id(file_id)
    if not ready_file:
        bot.answer_callback_query(call.id, "❌ فایل پیدا نشد!", show_alert=True)
        return
    
    bot.answer_callback_query(call.id, f"📦 {ready_file['name']} انتخاب شد")
    
    msg = bot.send_message(
        call.message.chat.id,
        f"📦 **فایل آماده انتخاب شد:** {ready_file['name']}\n\n"
        f"📝 توضیحات: {ready_file['description'] or 'بدون توضیحات'}\n"
        f"💰 قیمت: {ready_file['price']:,} تومان\n\n"
        f"لطفاً **توکن ربات** خود را ارسال کنید:\n"
        f"(توکنی که از @BotFather دریافت کرده‌اید)",
        parse_mode="Markdown"
    )
    
    bot.register_next_step_handler(msg, process_ready_token, ready_file)

def process_ready_token(message, ready_file):
    user_id = message.from_user.id
    token = message.text.strip()
    
    if not re.match(r'^[0-9]{8,10}:[A-Za-z0-9_-]{35}$', token):
        bot.reply_to(message, "❌ توکن نامعتبر است! لطفاً توکن صحیح را ارسال کنید.")
        return
    
    msg = bot.reply_to(
        message,
        f"✅ توکن دریافت شد!\n\n"
        f"لطفاً **آیدی عددی ادمین** ربات را ارسال کنید:\n"
        f"(مثال: 123456789)",
        parse_mode="Markdown"
    )
    
    bot.register_next_step_handler(msg, process_ready_admin, ready_file, token)

def process_ready_admin(message, ready_file, token):
    user_id = message.from_user.id
    admin_id_text = message.text.strip()
    
    try:
        admin_id = int(admin_id_text)
    except:
        bot.reply_to(message, "❌ آیدی ادمین نامعتبر است! لطفاً یک عدد صحیح ارسال کنید.")
        return
    
    # کد فایل آماده را بخوانیم
    try:
        with open(ready_file['file_path'], 'r', encoding='utf-8') as f:
            code = f.read()
    except:
        bot.reply_to(message, "❌ خطا در خواندن فایل آماده!")
        return
    
    # جایگزینی توکن و ایدی ادمین در کد
    code = re.sub(r'BOT_TOKEN\s*=\s*["\'][^"\']*["\']', f'BOT_TOKEN = "{token}"', code)
    code = re.sub(r'TOKEN\s*=\s*["\'][^"\']*["\']', f'TOKEN = "{token}"', code)
    code = re.sub(r'API_TOKEN\s*=\s*["\'][^"\']*["\']', f'API_TOKEN = "{token}"', code)
    code = re.sub(r'ADMIN_ID\s*=\s*\d+', f'ADMIN_ID = {admin_id}', code)
    code = re.sub(r'admin_id\s*=\s*\d+', f'admin_id = {admin_id}', code)
    code = re.sub(r'ADMIN\s*=\s*\d+', f'ADMIN = {admin_id}', code)
    code = re.sub(r'admin\s*=\s*\d+', f'admin = {admin_id}', code)
    code = re.sub(r'OWNER_ID\s*=\s*\d+', f'OWNER_ID = {admin_id}', code)
    code = re.sub(r'owner_id\s*=\s*\d+', f'owner_id = {admin_id}', code)
    
    # ذخیره فایل موقت برای کاربر
    user_file_dir = os.path.join(PENDING_FILES_DIR, str(user_id))
    os.makedirs(user_file_dir, exist_ok=True)
    
    file_name = f"ready_{ready_file['id']}_{int(time.time())}.py"
    file_path = os.path.join(user_file_dir, file_name)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(code)
    
    file_hash = hashlib.sha256(open(file_path, 'rb').read()).hexdigest()
    
    # پیدا کردن اشتراک فعال کاربر
    with get_db() as conn:
        sub = conn.execute('SELECT id FROM subscriptions WHERE user_id = ? AND status = "active" ORDER BY paid_at DESC LIMIT 1', (user_id,)).fetchone()
        if not sub:
            bot.reply_to(message, "❌ اشتراک فعال پیدا نشد!")
            return
        subscription_id = sub['id']
    
    # ✅ ذخیره در pending_files با علامت is_ready=1
    file_id = save_pending_file(user_id, subscription_id, file_path, file_name, file_hash, is_ready=1, ready_file_id=ready_file['id'])
    
    if not file_id:
        bot.reply_to(message, "❌ خطا در ذخیره فایل!")
        return
    
    bot.reply_to(message, 
        f"✅ **فایل آماده با موفقیت ثبت شد!**\n\n"
        f"📦 نام: {ready_file['name']}\n"
        f"🤖 توکن: `{token[:10]}...`\n"
        f"👤 ادمین: {admin_id}\n\n"
        f"🔄 **ربات شما به صورت خودکار ساخته می‌شود!**\n"
        f"⏳ لطفاً چند لحظه صبر کنید...",
        parse_mode="Markdown"
    )
    
    # ✅ ساخت خودکار ربات برای فایل آماده
    threading.Thread(target=auto_build_ready_bot, args=(file_id, user_id, call.message.chat.id)).start()

# ✅ تابع ساخت خودکار ربات برای فایل‌های آماده
def auto_build_ready_bot(file_id, user_id, chat_id):
    try:
        time.sleep(3)  # کمی صبر برای اطمینان از ذخیره در دیتابیس
        
        # بررسی مجدد اشتراک
        if not has_active_subscription(user_id):
            bot.send_message(chat_id, "❌ اشتراک شما منقضی شده است!")
            return
        
        if not can_create_bot(user_id):
            bot.send_message(chat_id, "❌ قبلاً با این اشتراک ربات ساخته‌اید!")
            return
        
        bot.send_message(chat_id, "🔄 **در حال ساخت خودکار ربات شما...**\n⏳ لطفاً شکیبا باشید...")
        
        result = build_bot_from_pending(file_id, None, chat_id, auto_build=True)
        
        if result['success']:
            bot.send_message(chat_id, 
                f"✅ **ربات شما با موفقیت ساخته شد!**\n\n"
                f"🤖 نام: {result['name']}\n"
                f"🔗 لینک: https://t.me/{result['username']}\n"
                f"🆔 آیدی: `{result['bot_id']}`\n\n"
                f"از منوی مدیریت ربات می‌توانید آن را مدیریت کنید.",
                parse_mode="Markdown"
            )
        else:
            bot.send_message(chat_id, 
                f"❌ **خطا در ساخت خودکار ربات!**\n\n"
                f"⚠️ خطا: {result['error'][:200]}\n\n"
                f"لطفاً با پشتیبانی تماس بگیرید.",
                parse_mode="Markdown"
            )
            
        # اطلاع به ادمین
        for admin in ADMIN_IDS:
            try:
                bot.send_message(admin,
                    f"{'✅' if result['success'] else '❌'} **ساخت خودکار ربات آماده**\n\n"
                    f"👤 کاربر: {user_id}\n"
                    f"📦 فایل: {get_ready_file_by_id(file_id)['name'] if file_id else 'نامشخص'}\n"
                    f"🔄 وضعیت: {'موفق' if result['success'] else 'ناموفق'}\n"
                    f"📝 پیام: {result.get('error', 'ساخته شد')[:100]}",
                    parse_mode="Markdown"
                )
            except:
                pass
                
    except Exception as e:
        logger.error(f"auto_build_ready_bot error: {e}")
        bot.send_message(chat_id, f"❌ خطا در ساخت خودکار: {str(e)[:100]}")

@bot.callback_query_handler(func=lambda call: call.data == "back_to_build")
def back_to_build(call):
    bot.answer_callback_query(call.id, "🔙 بازگشت")
    build_new_bot(call.message)

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
        bot.reply_to(message, "❌ فقط فایل .py یا .zip مجاز است!")
        return
    if message.document.file_size > 20 * 1024 * 1024:
        bot.reply_to(message, "❌ حجم بیشتر از ۲۰ مگابایت!")
        return
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        user_file_dir = os.path.join(PENDING_FILES_DIR, str(user_id))
        os.makedirs(user_file_dir, exist_ok=True)
        
        file_path = os.path.join(user_file_dir, f"{int(time.time())}_{file_name}")
        with open(file_path, 'wb') as f:
            f.write(downloaded_file)
        file_hash = hashlib.sha256(open(file_path, 'rb').read()).hexdigest()
        
        with get_db() as conn:
            sub = conn.execute('SELECT id FROM subscriptions WHERE user_id = ? AND status = "active" ORDER BY paid_at DESC LIMIT 1', (user_id,)).fetchone()
            if not sub:
                bot.reply_to(message, "❌ اشتراک فعال پیدا نشد!")
                return
            subscription_id = sub['id']
        
        save_pending_file(user_id, subscription_id, file_path, file_name, file_hash, is_ready=0)
        bot.reply_to(message, 
            f"✅ فایل {file_name} دریافت شد!\n\n"
            f"⏳ در لیست انتظار بررسی قرار گرفت.\n"
            f"📦 کتابخانه‌های مورد نیاز هنگام ساخت به صورت خودکار نصب می‌شوند."
        )
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)[:100]}")

@bot.message_handler(func=lambda m: m.text == '⚙️ مدیریت ربات')
def manage_bot(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    
    if not bots:
        bot.send_message(message.chat.id, 
            "📋 شما رباتی ندارید!\n\n"
            "برای ساخت ربات، ابتدا اشتراک بخرید و سپس از گزینه «ساخت ربات جدید» استفاده کنید."
        )
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for b in bots:
        status_emoji = "🟢" if b['status'] == 'running' else "🔴"
        status_text = "فعال" if b['status'] == 'running' else "غیرفعال"
        markup.add(types.InlineKeyboardButton(
            f"{status_emoji} {b['name']} ({status_text})", 
            callback_data=f"toggle_bot_{b['id']}"
        ))
    
    markup.row(
        types.InlineKeyboardButton("🗑️ حذف ربات", callback_data="delete_bot_menu")
    )
    
    bot.send_message(message.chat.id, 
        "🤖 **مدیریت ربات‌های شما**\n\n"
        "برای فعال/غیرفعال کردن هر ربات، روی آن کلیک کنید:\n"
        "برای حذف ربات، از دکمه پایین استفاده کنید.",
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "delete_bot_menu")
def delete_bot_menu(call):
    user_id = call.from_user.id
    bots = get_user_bots(user_id)
    
    if not bots:
        bot.answer_callback_query(call.id, "❌ رباتی برای حذف وجود ندارد!", show_alert=True)
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for b in bots:
        markup.add(types.InlineKeyboardButton(
            f"🗑️ {b['name']}", 
            callback_data=f"confirm_delete_{b['id']}"
        ))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_manage"))
    
    bot.edit_message_text(
        "🗑️ **حذف ربات**\n\n"
        "روی رباتی که می‌خواهید حذف کنید کلیک کنید:\n\n"
        "⚠️ **توجه:** این عمل غیرقابل بازگشت است!",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_delete_'))
def confirm_delete_bot(call):
    bot_id = call.data.replace('confirm_delete_', '')
    user_id = call.from_user.id
    
    bot_info = get_bot_by_id(bot_id)
    if not bot_info or bot_info['user_id'] != user_id:
        bot.answer_callback_query(call.id, "❌ ربات پیدا نشد!", show_alert=True)
        return
    
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ بله، حذف کن", callback_data=f"delete_now_{bot_id}"),
        types.InlineKeyboardButton("❌ انصراف", callback_data="back_to_manage")
    )
    
    bot.edit_message_text(
        f"⚠️ **تأیید حذف ربات**\n\n"
        f"🤖 نام: {bot_info['name']}\n"
        f"🆔 آیدی: {bot_id}\n\n"
        f"آیا از حذف این ربات مطمئن هستید؟\n"
        f"این عمل غیرقابل بازگشت است!",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_now_'))
def delete_now_bot(call):
    bot_id = call.data.replace('delete_now_', '')
    user_id = call.from_user.id
    
    if delete_bot_complete(bot_id, user_id):
        bot.answer_callback_query(call.id, "✅ ربات با موفقیت حذف شد!", show_alert=True)
        bot.edit_message_text(
            f"✅ **ربات با موفقیت حذف شد!**\n\n"
            f"🆔 آیدی: {bot_id}\n\n"
            f"تمام فایل‌های مربوط به ربات پاک شد.",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
    else:
        bot.answer_callback_query(call.id, "❌ خطا در حذف ربات!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_manage")
def back_to_manage(call):
    bot.answer_callback_query(call.id, "🔙 بازگشت")
    manage_bot(call.message)

@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_bot_'))
def toggle_bot(call):
    bot_id = call.data.replace('toggle_bot_', '')
    user_id = call.from_user.id
    bot_info = get_bot_by_id(bot_id)
    
    if not bot_info or bot_info['user_id'] != user_id:
        bot.answer_callback_query(call.id, "❌ ربات پیدا نشد!")
        return
    
    if bot_info['status'] == 'running':
        if stop_user_bot(bot_id):
            bot.answer_callback_query(call.id, "🛑 ربات غیرفعال شد")
            safe_edit(
                call.message.chat.id, 
                call.message.message_id,
                f"🛑 ربات {bot_info['name']} غیرفعال شد.\n\n"
                f"برای فعال کردن دوباره از منوی مدیریت استفاده کنید.",
                parse_mode=None
            )
        else:
            bot.answer_callback_query(call.id, "❌ خطا در غیرفعال کردن")
    else:
        days_left = get_subscription_days_left(user_id)
        if days_left <= 0:
            bot.answer_callback_query(call.id, "❌ اشتراک شما منقضی شده است!")
            safe_edit(
                call.message.chat.id, 
                call.message.message_id,
                f"❌ اشتراک شما منقضی شده است.\n\n"
                f"لطفاً برای فعال کردن ربات، اشتراک جدید بخرید.",
                parse_mode=None
            )
            return
        
        success, msg = start_user_bot(bot_id, call.message.chat.id)
        if success:
            bot.answer_callback_query(call.id, "✅ ربات فعال شد")
            safe_edit(
                call.message.chat.id, 
                call.message.message_id,
                f"✅ ربات {bot_info['name']} فعال شد.\n\n"
                f"برای غیرفعال کردن از منوی مدیریت استفاده کنید.",
                parse_mode=None
            )
        else:
            bot.answer_callback_query(call.id, f"❌ {msg[:30]}")

@bot.message_handler(func=lambda m: m.text == '💰 برداشت از کیف پول')
def wallet(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    balance = get_user_balance(user_id)
    bot_username = bot.get_me().username
    
    if not user:
        bot.send_message(message.chat.id, "❌ /start را بزنید")
        return
    
    referral_count, subscribed_count, total_bonus = get_referral_stats(user_id)
    
    with get_db() as conn:
        total_bots = conn.execute('SELECT COUNT(*) FROM bots WHERE user_id = ? AND status NOT IN ("deleted", "deleted_by_user") AND is_deleted = 0', (user_id,)).fetchone()[0]
    
    text = f"💰 کیف پول شما\n\n"
    text += f"👤 کاربر: {user['first_name']}\n"
    text += f"💰 موجودی: {balance:,} تومان\n"
    text += f"📈 کل درآمد: {user['total_earned']:,} تومان\n"
    text += f"🎁 تعداد رفرال: {referral_count} نفر\n"
    text += f"✅ اشتراک خرید: {subscribed_count} نفر\n"
    text += f"💵 پاداش دریافتی: {total_bonus:,} تومان\n"
    text += f"🤖 تعداد ربات: {total_bots} عدد\n"
    text += f"🎯 حداقل برداشت: {config.min_withdraw:,} تومان\n\n"
    text += f"🎁 لینک رفرال:\nhttps://t.me/{bot_username}?start={user['referral_code']}"
    
    markup = types.InlineKeyboardMarkup()
    
    if balance >= config.min_withdraw:
        markup.add(types.InlineKeyboardButton("🏧 برداشت (فعال)", callback_data="withdraw_active"))
        text += f"\n\n✅ وضعیت برداشت: فعال (موجودی کافی)"
    else:
        markup.add(types.InlineKeyboardButton("🏧 برداشت (غیرفعال)", callback_data="withdraw_inactive"))
        text += f"\n\n❌ وضعیت برداشت: غیرفعال (نیاز به {config.min_withdraw - balance:,} تومان بیشتر)"
    
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "withdraw_inactive")
def withdraw_inactive(call):
    user_id = call.from_user.id
    balance = get_user_balance(user_id)
    
    bot.answer_callback_query(call.id, 
        f"❌ موجودی کافی نیست!\n"
        f"نیاز به {config.min_withdraw - balance:,} تومان بیشتر دارید.",
        show_alert=True
    )

@bot.callback_query_handler(func=lambda call: call.data == "withdraw_active")
def withdraw_active(call):
    user_id = call.from_user.id
    balance = get_user_balance(user_id)
    
    if balance < config.min_withdraw:
        bot.answer_callback_query(call.id, 
            f"❌ موجودی کافی نیست!\n"
            f"موجودی فعلی: {balance:,} تومان",
            show_alert=True
        )
        return
    
    msg = bot.send_message(call.message.chat.id, 
        f"💰 برداشت از کیف پول\n\n"
        f"💰 موجودی قابل برداشت: {balance:,} تومان\n"
        f"💳 لطفاً شماره کارت (۱۶ رقم) خود را وارد کنید:"
    )
    bot.register_next_step_handler(msg, process_withdraw)

def process_withdraw(message):
    user_id = message.from_user.id
    card = message.text.strip().replace(' ', '')
    
    if not re.match(r'^\d{16}$', card):
        bot.reply_to(message, "❌ شماره کارت نامعتبر است! لطفاً ۱۶ رقم را وارد کنید.")
        return
    
    balance = get_user_balance(user_id)
    
    if balance < config.min_withdraw:
        bot.reply_to(message, f"❌ موجودی کافی نیست! ({balance:,} تومان)")
        return
    
    with get_db() as conn:
        conn.execute('INSERT INTO withdraw_requests (user_id, amount, card_number, created_at, is_verified) VALUES (?, ?, ?, ?, 0)', 
                    (user_id, balance, card, datetime.now().isoformat()))
        conn.execute('UPDATE users SET balance = 0 WHERE user_id = ?', (user_id,))
        conn.commit()
    
    bot.reply_to(message,
        f"✅ درخواست برداشت ثبت شد!\n\n"
        f"💰 مبلغ: {balance:,} تومان\n"
        f"💳 شماره کارت: {card}\n"
        f"⏳ زمان تقریبی واریز: ۲۴-۴۸ ساعت\n\n"
        f"🔔 پس از واریز به شما اطلاع داده می‌شود."
    )
    
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id,
                f"💰 درخواست برداشت جدید\n\n"
                f"👤 کاربر: {user_id}\n"
                f"💰 مبلغ: {balance:,} تومان\n"
                f"💳 کارت: {card}\n"
                f"📅 زمان: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
        except:
            pass

@bot.message_handler(func=lambda m: m.text == '📚 راهنما')
def guide(message):
    bot_username = bot.get_me().username
    guide_text = texts.guide_text.format(config.price, config.card_number, config.card_holder, bot_username)
    safe_send(message.chat.id, guide_text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == '📞 پشتیبانی')
def support(message):
    bot.send_message(message.chat.id, "📞 پشتیبانی: @shahraghee13")

@bot.message_handler(func=lambda m: m.text and m.text.startswith('📅'))
def show_days(message):
    days = get_subscription_days_left(message.from_user.id)
    bot.send_message(message.chat.id, f"📅 {days} روز مونده" if days > 0 else "❌ اشتراک فعال ندارید")

# ==================== پنل ادمین ====================

@bot.message_handler(func=lambda m: m.text == '👑 پنل ادمین')
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    with get_db() as conn:
        total_users = conn.execute('SELECT COUNT(*) FROM users WHERE is_locked = 0').fetchone()[0]
        active_subs = conn.execute('SELECT COUNT(*) FROM users WHERE active_subscription = 1 AND is_locked = 0').fetchone()[0]
        running_bots = conn.execute('SELECT COUNT(*) FROM bots WHERE status = "running" AND is_deleted = 0').fetchone()[0]
        pending_files = conn.execute('SELECT COUNT(*) FROM pending_files WHERE status = "pending" AND is_active = 1').fetchone()[0]
        pending_receipts = conn.execute('SELECT COUNT(*) FROM receipts WHERE status = "pending" AND is_verified = 0').fetchone()[0]
        queue_size = conn.execute('SELECT COUNT(*) FROM build_queue WHERE status = "pending" AND is_active = 1').fetchone()[0]
        total_balance = conn.execute('SELECT COALESCE(SUM(balance), 0) FROM users WHERE is_locked = 0').fetchone()[0]
        referral_count = conn.execute('SELECT COUNT(*) FROM referral_logs WHERE status = "registered" AND is_active = 1').fetchone()[0]
        subscribed_count = conn.execute('SELECT COUNT(*) FROM referral_logs WHERE status = "subscribed" AND is_active = 1').fetchone()[0]
        servers_count = conn.execute('SELECT COUNT(*) FROM servers WHERE status = "active" AND is_active = 1').fetchone()[0]
        total_bots = conn.execute('SELECT COUNT(*) FROM bots WHERE is_deleted = 0').fetchone()[0]
        ready_files_count = conn.execute('SELECT COUNT(*) FROM ready_files WHERE is_active = 1').fetchone()[0]
        
        today = datetime.now().strftime('%Y-%m-%d')
        today_users = conn.execute('SELECT COUNT(*) FROM users WHERE DATE(created_at) = ?', (today,)).fetchone()[0]
        today_subs = conn.execute('SELECT COUNT(*) FROM subscriptions WHERE DATE(paid_at) = ? AND status = "active"', (today,)).fetchone()[0]
    
    text = f"""
👑 پنل مدیریت پیشرفته

📊 آمار کلی:
👥 کل کاربران: {total_users}
✅ اشتراک فعال: {active_subs}
🤖 ربات‌های در حال اجرا: {running_bots}
📦 کل ربات‌های ساخته شده: {total_bots}
📥 فایل‌های در انتظار: {pending_files}
📸 فیش‌های در انتظار: {pending_receipts}
⏳ صف ساخت: {queue_size}
💰 مجموع موجودی: {total_balance:,} تومان
🎁 رفرال ثبت: {referral_count}
🎁 اشتراک خرید رفرال: {subscribed_count}
🖥️ سرورهای فعال: {servers_count}
📦 فایل‌های آماده: {ready_files_count}

📈 آمار امروز:
👤 کاربران جدید: {today_users}
🛒 اشتراک فروخته: {today_subs}
    """
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📸 فیش‌ها", callback_data="admin_receipts"),
        types.InlineKeyboardButton("📥 فایل‌ها", callback_data="admin_files"),
        types.InlineKeyboardButton("➕ افزودن سرور", callback_data="admin_add_server"),
        types.InlineKeyboardButton("💰 برداشت‌ها", callback_data="admin_withdraws"),
        types.InlineKeyboardButton("📢 پیام همگانی", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("📝 تنظیم متون", callback_data="admin_texts"),
        types.InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings"),
        types.InlineKeyboardButton("🎁 تایید اشتراک", callback_data="admin_manual_sub"),
        types.InlineKeyboardButton("📦 مدیریت کتابخانه‌ها", callback_data="admin_libraries"),
        types.InlineKeyboardButton("📦 مدیریت فایل‌های آماده", callback_data="admin_ready_files"),
        types.InlineKeyboardButton("🔄 ریستارت ربات‌ها", callback_data="admin_restart_bots"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    bot.send_message(message.chat.id, text, reply_markup=markup)

# ==================== مدیریت فایل‌های آماده ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_ready_files")
def admin_ready_files(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    ready_files = get_ready_files()
    
    text = "📦 **مدیریت فایل‌های آماده**\n\n"
    if ready_files:
        for f in ready_files:
            text += f"🆔 {f['id']} - {f['name']}\n"
            text += f"   📄 {f['file_name']}\n"
            text += f"   💰 {f['price']:,} تومان\n\n"
    else:
        text += "• هیچ فایل آماده‌ای وجود ندارد\n"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📤 آپلود فایل آماده", callback_data="upload_ready_file"),
        types.InlineKeyboardButton("🗑️ حذف فایل آماده", callback_data="delete_ready_file"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    safe_edit(
        call.message.chat.id,
        call.message.message_id,
        text,
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "upload_ready_file")
def upload_ready_file(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(
        call.message.chat.id,
        "📤 **آپلود فایل آماده**\n\n"
        "لطفاً نام فایل را وارد کنید:\n"
        "مثال: فروشگاهی",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_ready_file_name)

def process_ready_file_name(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    name = message.text.strip()
    if not name:
        bot.reply_to(message, "❌ نام نمی‌تواند خالی باشد!")
        return
    
    msg = bot.reply_to(
        message,
        f"✅ نام ثبت شد: {name}\n\n"
        f"📤 لطفاً فایل `.py` یا `.zip` را ارسال کنید:",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_ready_file_upload, name)

def process_ready_file_upload(message, name):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    if not message.document:
        bot.reply_to(message, "❌ لطفاً یک فایل ارسال کنید!")
        return
    
    file_name = message.document.file_name
    if not (file_name.endswith('.py') or file_name.endswith('.zip')):
        bot.reply_to(message, "❌ فقط فایل .py یا .zip مجاز است!")
        return
    
    if message.document.file_size > 20 * 1024 * 1024:
        bot.reply_to(message, "❌ حجم بیشتر از ۲۰ مگابایت!")
        return
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        ready_file_path = os.path.join(READY_FILES_DIR, f"{int(time.time())}_{file_name}")
        with open(ready_file_path, 'wb') as f:
            f.write(downloaded_file)
        
        msg = bot.reply_to(
            message,
            f"✅ فایل دریافت شد!\n\n"
            f"📝 توضیحات (اختیاری) را وارد کنید:\n"
            f"(برای رد شدن، «-» بفرستید)",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, process_ready_file_desc, name, file_name, ready_file_path)
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)[:100]}")

def process_ready_file_desc(message, name, file_name, ready_file_path):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    description = message.text.strip()
    if description == '-':
        description = ""
    
    if add_ready_file(name, file_name, ready_file_path, description):
        bot.reply_to(
            message,
            f"✅ **فایل آماده با موفقیت اضافه شد!**\n\n"
            f"📦 نام: {name}\n"
            f"📄 فایل: {file_name}\n"
            f"💰 قیمت: {SUBSCRIPTION_PRICE:,} تومان\n"
            f"📝 توضیحات: {description or 'بدون توضیحات'}"
        )
        
        for admin in ADMIN_IDS:
            try:
                bot.send_message(admin,
                    f"✅ **فایل آماده جدید اضافه شد!**\n\n"
                    f"📦 نام: {name}\n"
                    f"📄 فایل: {file_name}"
                )
            except:
                pass
    else:
        bot.reply_to(message, "❌ خطا در ذخیره فایل!")

@bot.callback_query_handler(func=lambda call: call.data == "delete_ready_file")
def delete_ready_file_menu(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    ready_files = get_ready_files()
    
    if not ready_files:
        bot.answer_callback_query(call.id, "❌ هیچ فایل آماده‌ای وجود ندارد!", show_alert=True)
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for f in ready_files:
        markup.add(types.InlineKeyboardButton(
            f"🗑️ {f['name']}", 
            callback_data=f"confirm_delete_ready_{f['id']}"
        ))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_ready_files"))
    
    bot.edit_message_text(
        "🗑️ **حذف فایل آماده**\n\n"
        "روی فایلی که می‌خواهید حذف کنید کلیک کنید:\n\n"
        "⚠️ این عمل غیرقابل بازگشت است!",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_delete_ready_'))
def confirm_delete_ready(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    file_id = int(call.data.replace('confirm_delete_ready_', ''))
    
    if delete_ready_file(file_id):
        bot.answer_callback_query(call.id, "✅ فایل با موفقیت حذف شد!", show_alert=True)
        bot.edit_message_text(
            f"✅ **فایل آماده با موفقیت حذف شد!**\n\n"
            f"🆔 آیدی: {file_id}",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
    else:
        bot.answer_callback_query(call.id, "❌ خطا در حذف فایل!", show_alert=True)

# ==================== سایر هندلرهای ادمین ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_restart_bots")
def admin_restart_bots(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, 
        "🔄 در حال ریستارت تمام ربات‌ها...\n⏳ لطفاً شکیبا باشید..."
    )
    
    restarted = restart_all_bots()
    
    safe_edit(
        call.message.chat.id, 
        msg.message_id,
        f"✅ ریستارت کامل شد!\n\n"
        f"🔄 {restarted} ربات با موفقیت راه‌اندازی مجدد شدند.\n"
        f"📊 تمام ربات‌های مرده دوباره فعال شدند.",
        parse_mode=None
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_add_server")
def admin_add_server(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, 
        "➕ افزودن سرور جدید\n\n"
        "لطفاً IP سرور را وارد کنید:\n"
        "مثال: 82.115.20.73"
    )
    bot.register_next_step_handler(msg, process_server_ip)

def process_server_ip(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    ip = message.text.strip()
    if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
        bot.reply_to(message, "❌ IP نامعتبر است!")
        return
    
    msg = bot.reply_to(message, f"✅ IP ثبت شد: {ip}\n\nلطفاً رمز SSH را وارد کنید:")
    bot.register_next_step_handler(msg, lambda m: process_server_password(m, ip))

def process_server_password(message, ip):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    password = message.text.strip()
    if not password:
        bot.reply_to(message, "❌ رمز نمی‌تواند خالی باشد!")
        return
    
    msg = bot.reply_to(message, 
        "🔄 در حال اتصال به سرور و نصب کتابخانه‌ها...\n"
        "⏳ این عملیات چند دقیقه طول می‌کشد..."
    )
    
    required_libs = [
        "pyTelegramBotAPI", "python-telegram-bot", "psycopg2-binary",
        "paramiko", "requests", "sqlalchemy", "redis", "pymongo",
        "numpy", "pandas", "loguru", "rich", "tqdm", "click"
    ]
    
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip, port=22, username='root', password=password, timeout=30)
        client.close()
        
        installed, failed = install_libraries_on_server(ip, 22, 'root', password, required_libs)
        
        if add_server_to_db(f"Server_{ip}", ip, 22, 'root', password, installed):
            safe_edit(
                message.chat.id, 
                msg.message_id,
                f"✅ سرور با موفقیت اضافه شد!\n\n"
                f"🖥️ IP: {ip}\n"
                f"📦 کتابخانه‌های نصب شده: {len(installed)} مورد\n"
                f"❌ ناموفق: {len(failed)} مورد\n\n"
                f"✅ سرور آماده استفاده است!",
                parse_mode=None
            )
            
            for admin_id in ADMIN_IDS:
                try:
                    bot.send_message(admin_id,
                        f"✅ سرور جدید اضافه شد!\n\n"
                        f"🖥️ IP: {ip}\n"
                        f"📦 کتابخانه‌ها: {', '.join(installed[:10])}..."
                    )
                except:
                    pass
        else:
            safe_edit(
                message.chat.id, 
                msg.message_id,
                f"❌ خطا در ذخیره سرور!\n\n"
                f"اتصال برقرار بود اما ذخیره در دیتابیس انجام نشد.",
                parse_mode=None
            )
            
    except Exception as e:
        safe_edit(
            message.chat.id, 
            msg.message_id,
            f"❌ خطا در اتصال به سرور!\n\n"
            f"⚠️ خطا: {str(e)[:200]}\n\n"
            f"لطفاً IP و رمز را بررسی کنید.",
            parse_mode=None
        )

def install_libraries_on_server(server_ip, server_port, server_username, server_password, libraries):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(server_ip, port=server_port, username=server_username, password=server_password, timeout=30)
        
        client.exec_command('pip3 install --upgrade pip')
        time.sleep(2)
        
        installed = []
        failed = []
        
        for lib in libraries:
            try:
                stdin, stdout, stderr = client.exec_command(f'pip3 install {lib} --quiet')
                exit_status = stdout.channel.recv_exit_status()
                if exit_status == 0:
                    installed.append(lib)
                    logger.info(f"✅ کتابخانه {lib} روی سرور {server_ip} نصب شد")
                else:
                    failed.append(lib)
                    logger.warning(f"❌ خطا در نصب {lib} روی سرور {server_ip}")
            except Exception as e:
                failed.append(lib)
                logger.error(f"خطا در نصب {lib}: {e}")
            time.sleep(0.5)
        
        client.close()
        return installed, failed
    except Exception as e:
        logger.error(f"خطا در اتصال به سرور {server_ip}: {e}")
        return [], [str(e)]

def add_server_to_db(name, ip, port, username, password, installed_libs=None):
    try:
        with get_db() as conn:
            now = datetime.now().isoformat()
            if installed_libs:
                libs_str = ','.join(installed_libs)
            else:
                libs_str = ''
            conn.execute('INSERT INTO servers (name, ip, port, username, password, created_at, last_heartbeat, installed_libs, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)', 
                        (name, ip, port, username, password, now, now, libs_str))
            conn.commit()
            return True
    except:
        return False

@bot.callback_query_handler(func=lambda call: call.data == "admin_receipts")
def admin_receipts_list(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    with get_db() as conn:
        receipts = conn.execute('SELECT * FROM receipts WHERE status = "pending" AND is_verified = 0 ORDER BY created_at DESC').fetchall()
    
    if not receipts:
        bot.send_message(call.message.chat.id, "📸 فیشی وجود ندارد")
        return
    
    for r in receipts:
        text = f"📸 فیش #{r['id']}\n\n"
        text += f"👤 کاربر: {r['user_id']}\n"
        text += f"💰 مبلغ: {r['amount']:,} تومان\n"
        text += f"🆔 کد: {r['payment_code']}\n"
        text += f"📅 زمان: {r['created_at'][:10]}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید و فعال‌سازی", callback_data=f"approve_payment_{r['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"reject_payment_{r['id']}")
        )
        if os.path.exists(r['receipt_path']):
            with open(r['receipt_path'], 'rb') as f:
                bot.send_photo(call.message.chat.id, f, caption=text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_payment_'))
def approve_payment(call):
    receipt_id = int(call.data.replace('approve_payment_', ''))
    
    with get_db() as conn:
        receipt = conn.execute('SELECT * FROM receipts WHERE id = ? AND is_verified = 0', (receipt_id,)).fetchone()
        if receipt:
            success = activate_subscription(receipt['subscription_id'], receipt['user_id'], receipt['amount'])
            
            if success:
                conn.execute('UPDATE receipts SET status = "approved", is_verified = 1 WHERE id = ?', (receipt_id,))
                conn.commit()
                
                bot.answer_callback_query(call.id, "✅ تایید و فعال‌سازی شد!")
                
                bot.send_message(receipt['user_id'], 
                    f"✅ اشتراک شما فعال شد!\n\n"
                    f"📅 {config.subscription_days} روز اعتبار.\n"
                    f"🤖 از منوی «ساخت ربات جدید» استفاده کنید.",
                    parse_mode="Markdown"
                )
                
                bot.delete_message(call.message.chat.id, call.message.message_id)
            else:
                bot.answer_callback_query(call.id, "❌ خطا در فعال‌سازی!")
        else:
            bot.answer_callback_query(call.id, "❌ فیش پیدا نشد!")

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_payment_'))
def reject_payment(call):
    receipt_id = int(call.data.replace('reject_payment_', ''))
    
    with get_db() as conn:
        conn.execute('UPDATE receipts SET status = "rejected", is_verified = 1 WHERE id = ?', (receipt_id,))
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
        # مشخص کردن نوع فایل
        file_type = "📦 آماده" if f.get('is_ready', 0) == 1 else "📤 شخصی"
        
        text = f"📥 فایل #{f['id']} [{file_type}]\n\n"
        text += f"👤 کاربر: {f['user_id']}\n"
        text += f"📄 نام: {f['file_name']}\n"
        text += f"📅 زمان: {f['submitted_at'][:10]}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید و ساخت", callback_data=f"build_file_{f['id']}"),
            types.InlineKeyboardButton("❌ حذف", callback_data=f"delete_file_{f['id']}")
        )
        if os.path.exists(f['file_path']):
            with open(f['file_path'], 'rb') as file:
                bot.send_document(call.message.chat.id, file, caption=text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('build_file_'))
def build_file(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    file_id = int(call.data.replace('build_file_', ''))
    pending = get_pending_file_by_id(file_id)
    
    if not pending:
        bot.answer_callback_query(call.id, "❌ فایل پیدا نشد!", show_alert=True)
        return
    
    # اگر فایل آماده است، ساخت خودکار انجام می‌شود
    if pending.get('is_ready', 0) == 1:
        bot.answer_callback_query(call.id, "✅ این فایل آماده است و خودکار ساخته می‌شود!")
        
        # ساخت خودکار
        threading.Thread(target=auto_build_ready_bot, args=(file_id, pending['user_id'], call.message.chat.id)).start()
        
        bot.edit_message_text(
            f"🔄 **ساخت خودکار فایل آماده در حال انجام...**\n\n"
            f"📦 فایل: {pending['file_name']}\n"
            f"👤 کاربر: {pending['user_id']}\n\n"
            f"⏳ لطفاً شکیبا باشید...",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
        return
    
    # فایل شخصی - اضافه به صف
    msg = bot.send_message(call.message.chat.id, 
        "🔄 در حال افزودن به صف ساخت...\n\n"
        "⏳ لطفاً شکیبا باشید...\n"
        "📦 کتابخانه‌های مورد نیاز به صورت خودکار نصب خواهند شد."
    )
    queue_id = add_to_build_queue(file_id, call.from_user.id)
    
    if queue_id:
        active_builds[queue_id] = {
            'chat_id': call.message.chat.id,
            'message_id': msg.message_id,
            'start_time': datetime.now(),
            'file_id': file_id,
            'user_id': call.from_user.id
        }
        update_countdown(call.message.chat.id, msg.message_id, queue_id, datetime.now())
        safe_edit(
            call.message.chat.id, 
            call.message.message_id,
            f"✅ فایل به صف ساخت اضافه شد\n\n"
            f"🆔 شماره صف: {queue_id}\n"
            f"🕐 زمان ساخت: حدود ۲ دقیقه\n"
            f"📦 کتابخانه‌های مورد نیاز به صورت خودکار نصب می‌شوند\n\n"
            f"⏳ در حال نمایش ثانیه‌شمار...",
            parse_mode=None
        )
    else:
        safe_edit(
            call.message.chat.id, 
            call.message.message_id,
            "🔄 در حال ساخت مستقیم ربات...\n"
            "📦 در حال نصب کتابخانه‌ها...",
            parse_mode=None
        )
        result = build_bot_from_pending(file_id, None, call.message.chat.id)
        if result['success']:
            safe_edit(
                call.message.chat.id, 
                call.message.message_id,
                f"✅ ربات ساخته شد!\n\n"
                f"🤖 {result['name']}\n"
                f"🔗 https://t.me/{result['username']}\n\n"
                f"📦 کتابخانه‌های مورد نیاز نصب شدند.",
                parse_mode=None
            )
        else:
            safe_edit(
                call.message.chat.id, 
                call.message.message_id,
                f"❌ خطا: {result['error']}",
                parse_mode=None
            )

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_file_'))
def delete_file(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    file_id = int(call.data.replace('delete_file_', ''))
    update_pending_file_status(file_id, 'deleted')
    bot.answer_callback_query(call.id, "❌ حذف شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_withdraws")
def admin_withdraws_list(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    with get_db() as conn:
        withdraws = conn.execute('SELECT * FROM withdraw_requests WHERE status = "pending" AND is_verified = 0 ORDER BY created_at DESC').fetchall()
    
    if not withdraws:
        bot.send_message(call.message.chat.id, "💰 درخواستی وجود ندارد")
        return
    
    for w in withdraws:
        text = f"💰 درخواست برداشت #{w['id']}\n\n"
        text += f"👤 کاربر: {w['user_id']}\n"
        text += f"💰 مبلغ: {w['amount']:,} تومان\n"
        text += f"💳 کارت: {w['card_number']}\n"
        text += f"📅 زمان: {w['created_at'][:10]}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید و پرداخت", callback_data=f"approve_withdraw_{w['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"reject_withdraw_{w['id']}")
        )
        bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_withdraw_'))
def approve_withdraw(call):
    wid = int(call.data.replace('approve_withdraw_', ''))
    
    with get_db() as conn:
        conn.execute('UPDATE withdraw_requests SET status = "approved", processed_at = ?, is_verified = 1 WHERE id = ?', 
                    (datetime.now().isoformat(), wid))
        conn.commit()
    
    bot.answer_callback_query(call.id, "✅ تایید و پرداخت شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_withdraw_'))
def reject_withdraw(call):
    wid = int(call.data.replace('reject_withdraw_', ''))
    
    with get_db() as conn:
        w = conn.execute('SELECT * FROM withdraw_requests WHERE id = ? AND is_verified = 0', (wid,)).fetchone()
        if w:
            conn.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (w['amount'], w['user_id']))
            conn.execute('UPDATE withdraw_requests SET status = "rejected", is_verified = 1 WHERE id = ?', (wid,))
            conn.commit()
    
    bot.answer_callback_query(call.id, "❌ رد شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_texts")
def admin_texts(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("💰 متن خرید اشتراک", callback_data="edit_subscription"),
        types.InlineKeyboardButton("📚 متن راهنما", callback_data="edit_guide"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    safe_edit(
        call.message.chat.id, 
        call.message.message_id,
        "📝 مدیریت متون\n\n"
        "هر کدام از متون زیر را می‌توانید تغییر دهید:",
        parse_mode=None,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "edit_subscription")
def edit_subscription(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, 
        f"💰 متن جدید خرید اشتراک را ارسال کنید:\n\n"
        f"متن فعلی:\n{texts.subscription_text[:200]}"
    )
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
    msg = bot.send_message(call.message.chat.id, 
        f"📚 متن جدید راهنما را ارسال کنید:\n\n"
        f"متن فعلی:\n{texts.guide_text[:200]}"
    )
    bot.register_next_step_handler(msg, save_guide_text)

def save_guide_text(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    texts.guide_text = message.text
    texts.save_to_db()
    bot.reply_to(message, "✅ متن راهنما تغییر کرد!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_settings")
def admin_settings(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💰 تغییر قیمت", callback_data="set_price"),
        types.InlineKeyboardButton("💳 تغییر کارت", callback_data="set_card"),
        types.InlineKeyboardButton("👤 تغییر صاحب کارت", callback_data="set_holder"),
        types.InlineKeyboardButton("⏰ تغییر مدت اشتراک", callback_data="set_duration"),
        types.InlineKeyboardButton("💰 حداقل برداشت", callback_data="set_min_withdraw"),
        types.InlineKeyboardButton("🎁 پاداش رفرال", callback_data="set_referral_bonus"),
        types.InlineKeyboardButton("⚙️ نصب خودکار کتابخانه", callback_data="toggle_auto_install"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    auto_status = "✅ فعال" if config.auto_install_libs else "❌ غیرفعال"
    text = f"""
⚙️ تنظیمات

💰 قیمت: {config.price:,} تومان
💳 کارت: {config.card_number}
👤 صاحب کارت: {config.card_holder}
⏰ مدت اشتراک: {config.subscription_days} روز
💰 حداقل برداشت: {config.min_withdraw:,} تومان
🎁 پاداش رفرال: {config.referral_bonus}%
📦 نصب خودکار کتابخانه: {auto_status}
    """
    
    safe_edit(
        call.message.chat.id, 
        call.message.message_id,
        text,
        parse_mode=None,
        reply_markup=markup
    )

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

@bot.callback_query_handler(func=lambda call: call.data == "set_min_withdraw")
def set_min_withdraw(call):
    msg = bot.send_message(call.message.chat.id, f"💰 حداقل برداشت جدید (فعلی: {config.min_withdraw:,}):")
    bot.register_next_step_handler(msg, lambda m: set_config(m, 'min_withdraw', int))

@bot.callback_query_handler(func=lambda call: call.data == "set_referral_bonus")
def set_referral_bonus(call):
    msg = bot.send_message(call.message.chat.id, f"🎁 پاداش رفرال جدید (فعلی: {config.referral_bonus}%):")
    bot.register_next_step_handler(msg, lambda m: set_config(m, 'referral_bonus', int))

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
    msg = bot.send_message(call.message.chat.id, "🎁 آیدی کاربر را وارد کنید:")
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

@bot.callback_query_handler(func=lambda call: call.data == "admin_libraries")
def admin_libraries(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    with get_db() as conn:
        installed = conn.execute('SELECT library_name, installed_at FROM installed_libraries ORDER BY installed_at DESC LIMIT 50').fetchall()
    
    text = "📦 **مدیریت کتابخانه‌ها**\n\n"
    text += "🔧 کتابخانه‌های نصب شده:\n"
    if installed:
        for lib in installed[:20]:
            text += f"• `{lib['library_name']}`\n"
    else:
        text += "• هیچ کتابخانه‌ای نصب نشده است\n"
    text += f"\n📚 تعداد کل کتابخانه‌های قابل نصب: {len(POPULAR_LIBRARIES)}\n"
    text += "\n💡 **هر کتابخانه‌ای که کاربر وارد کند نصب می‌شود!**\n"
    text += "🔧 با ۵ روش مختلف و ۵ بار تلاش مجدد"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📦 نصب کتابخانه جدید", callback_data="install_new_library"),
        types.InlineKeyboardButton("🔧 نصب همه کتابخانه‌ها", callback_data="install_all_libs"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    safe_edit(
        call.message.chat.id,
        call.message.message_id,
        text,
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "install_new_library")
def install_new_library(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ دسترسی غیرمجاز!", show_alert=True)
        return
    
    msg = bot.send_message(
        call.message.chat.id,
        "📦 **نصب کتابخانه جدید**\n\n"
        "لطفاً نام کتابخانه مورد نظر را وارد کنید:\n"
        "مثال: `numpy` یا `requests`\n\n"
        "⚠️ می‌توانید چند کتابخانه را با فاصله وارد کنید:\n"
        "مثال: `numpy pandas requests aiohttp`\n\n"
        "🔧 **تضمین نصب:** با ۵ روش مختلف و ۵ بار تلاش مجدد",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_install_library)

def process_install_library(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    libraries = message.text.strip().split()
    
    if not libraries:
        bot.reply_to(message, "❌ هیچ کتابخانه‌ای وارد نشد!")
        return
    
    status_msg = bot.reply_to(
        message,
        f"🔄 **در حال نصب {len(libraries)} کتابخانه...**\n\n"
        f"⏳ لطفاً شکیبا باشید...\n"
        f"🔧 با ۵ روش مختلف و ۵ بار تلاش مجدد",
        parse_mode="Markdown"
    )
    
    installed, failed = install_libraries_on_mother_advanced(
        libraries,
        chat_id=message.chat.id,
        message_id=status_msg.message_id
    )
    
    result_text = f"✅ **نصب کتابخانه‌ها کامل شد!**\n\n"
    result_text += f"📦 **نصب شده ({len(installed)} مورد):**\n"
    if installed:
        result_text += f"`{', '.join(installed[:20])}`"
        if len(installed) > 20:
            result_text += f"\n... و {len(installed) - 20} مورد دیگر"
    else:
        result_text += "• هیچ کتابخانه‌ای نصب نشد"
    
    if failed:
        result_text += f"\n\n❌ **ناموفق ({len(failed)} مورد):**\n"
        result_text += f"`{', '.join(failed[:20])}`"
        if len(failed) > 20:
            result_text += f"\n... و {len(failed) - 20} مورد دیگر"
        result_text += f"\n\n⚠️ **برای نصب دستی:**\n"
        result_text += f"`pip3 install {' '.join(failed)}`"
    
    safe_edit(message.chat.id, status_msg.message_id, result_text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "install_all_libs")
def install_all_libs(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    status_msg = bot.send_message(
        call.message.chat.id,
        f"🔄 **در حال نصب {len(POPULAR_LIBRARIES)} کتابخانه پرکاربرد...**\n\n"
        f"⏳ این عملیات ممکن است ۲۰-۳۰ دقیقه طول بکشد...\n"
        f"📦 لطفاً شکیبا باشید...\n"
        f"🔧 با ۵ روش مختلف و ۵ بار تلاش مجدد برای هر کتابخانه",
        parse_mode="Markdown"
    )
    
    installed, failed = install_libraries_on_mother_advanced(
        POPULAR_LIBRARIES,
        chat_id=call.message.chat.id,
        message_id=status_msg.message_id
    )
    
    result_text = f"✅ **نصب همه کتابخانه‌ها کامل شد!**\n\n"
    result_text += f"📦 **نصب شده ({len(installed)} مورد):**\n"
    if installed:
        result_text += f"`{', '.join(installed[:30])}`"
        if len(installed) > 30:
            result_text += f"\n... و {len(installed) - 30} مورد دیگر"
    else:
        result_text += "• هیچ کتابخانه‌ای نصب نشد"
    
    if failed:
        result_text += f"\n\n❌ **ناموفق ({len(failed)} مورد):**\n"
        result_text += f"`{', '.join(failed[:20])}`"
        if len(failed) > 20:
            result_text += f"\n... و {len(failed) - 20} مورد دیگر"
        result_text += f"\n\n⚠️ **برای نصب دستی:**\n"
        result_text += f"`pip3 install {' '.join(failed[:5])}`"
        if len(failed) > 5:
            result_text += f"\n... و {len(failed) - 5} مورد دیگر"
    
    safe_edit(call.message.chat.id, status_msg.message_id, result_text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast")
def admin_broadcast(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, 
        "📢 متن پیام همگانی را ارسال کنید:\n\n(برای ارسال به همه کاربران)"
    )
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    text = message.text
    status_msg = bot.reply_to(message, "🔄 در حال ارسال پیام همگانی...")
    sent_count = send_broadcast(text, message.from_user.id)
    safe_edit(
        message.chat.id, 
        status_msg.message_id,
        f"✅ پیام همگانی ارسال شد!\n\n"
        f"📨 تعداد دریافت‌کنندگان: {sent_count} نفر",
        parse_mode=None
    )

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
                expired = conn.execute('SELECT user_id FROM users WHERE active_subscription = 1 AND julianday(subscription_expire) - julianday("now") < 0 AND is_locked = 0').fetchall()
                for user in expired:
                    conn.execute('UPDATE users SET active_subscription = 0 WHERE user_id = ?', (user['user_id'],))
                    bots = conn.execute('SELECT id, server_id FROM bots WHERE user_id = ? AND status = "running" AND is_deleted = 0', (user['user_id'],)).fetchall()
                    for bot_info in bots:
                        stop_bot_on_mother(bot_info['id'])
                        conn.execute('UPDATE bots SET status = "expired" WHERE id = ?', (bot_info['id'],))
                    try:
                        bot.send_message(user['user_id'], 
                            "❌ اشتراک شما منقضی شد!\n\n"
                            "ربات شما غیرفعال شد.\n"
                            "برای ادامه، اشتراک جدید بخرید."
                        )
                    except:
                        pass
                
                warning = conn.execute('SELECT user_id, subscription_expire FROM users WHERE active_subscription = 1 AND julianday(subscription_expire) - julianday("now") BETWEEN 0 AND 3 AND is_locked = 0').fetchall()
                for user in warning:
                    days_left = (datetime.fromisoformat(user['subscription_expire']) - datetime.now()).days
                    if days_left > 0:
                        try:
                            bot.send_message(user['user_id'], 
                                f"⚠️ {days_left} روز تا اتمام اشتراک!\n\n"
                                f"لطفاً تمدید کنید تا ربات شما غیرفعال نشود."
                            )
                        except:
                            pass
                
                conn.commit()
            time.sleep(3600)
        except Exception as e:
            logger.error(f"check_expired error: {e}")
            time.sleep(3600)

# ==================== بکاپ خودکار ====================

def auto_backup():
    while True:
        try:
            backup_file = os.path.join(BACKUP_DIR, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
            shutil.copy2(os.path.join(DB_DIR, 'mother_bot.db'), backup_file)
            
            with get_db() as conn:
                conn.execute('INSERT INTO backups (file_path, created_at, size, is_active) VALUES (?, ?, ?, 1)', 
                            (backup_file, datetime.now().isoformat(), os.path.getsize(backup_file)))
                conn.commit()
            
            backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.startswith('backup_')])
            if len(backups) > 20:
                for old_file in backups[:-20]:
                    os.remove(os.path.join(BACKUP_DIR, old_file))
            
            logger.info(f"✅ بکاپ خودکار انجام شد: {backup_file}")
            time.sleep(3600 * 6)
        except Exception as e:
            logger.error(f"auto_backup error: {e}")
            time.sleep(3600)

# ==================== اجرا ====================

if __name__ == "__main__":
    check_and_create_pid()
    
    print("=" * 80)
    print("🚀 ربات مادر نسخه ۲۱.۱ - رفع باگ تایید فایل + ساخت خودکار")
    print("=" * 80)
    print(f"✅ ادمین: {ADMIN_IDS}")
    print(f"✅ قیمت اشتراک: {SUBSCRIPTION_PRICE:,} تومان")
    print(f"✅ مدت اشتراک: {config.subscription_days} روز")
    print(f"✅ حداقل برداشت: {config.min_withdraw:,} تومان")
    print(f"✅ پاداش رفرال: {config.referral_bonus}%")
    print(f"✅ نصب خودکار کتابخانه: {'فعال' if config.auto_install_libs else 'غیرفعال'}")
    print(f"✅ کتابخانه‌های قابل نصب: {len(POPULAR_LIBRARIES)} مورد")
    print(f"✅ روش‌های نصب: ۵ روش مختلف")
    print(f"✅ تلاش مجدد: ۵ بار برای هر کتابخانه")
    print(f"✅ ایزوله‌سازی کامل فایل‌ها با UUID")
    print(f"✅ پشتیبانی از فایل‌های آماده با ساخت خودکار")
    print(f"✅ حذف کامل ربات با پاک کردن فایل‌ها")
    print("=" * 80)
    print("🟢 در حال بازیابی ربات‌های قبلی...")
    
    restore_all_bots()
    
    print("✅ ربات‌ها بازیابی شدند!")
    print("🟢 ربات مادر در حال اجراست...")
    print("=" * 80)
    print("📌 ویژگی‌های نسخه ۲۱.۱:")
    print("🔹 رفع باگ دکمه تایید فایل")
    print("🔹 ساخت خودکار فایل‌های آماده بعد از دریافت توکن و ایدی")
    print("🔹 نصب تضمینی کتابخانه‌ها با ۵ روش مختلف")
    print("🔹 ۵ بار تلاش مجدد برای هر کتابخانه")
    print("🔹 ایزوله‌سازی کامل فایل‌ها با UUID")
    print("🔹 دکمه حذف ربات با پاک کردن کامل فایل‌ها")
    print("🔹 هر اشتراک = ۱ ربات (قابل تمدید با خرید مجدد)")
    print("🔹 قیمت اشتراک: ۳,۰۰۰,۰۰۰ تومان")
    print("=" * 80)
    
    expiry_thread = threading.Thread(target=check_expired, daemon=True)
    expiry_thread.start()
    
    backup_thread = threading.Thread(target=auto_backup, daemon=True)
    backup_thread.start()
    
    queue_worker_thread = threading.Thread(target=queue_worker, daemon=True)
    queue_worker_thread.start()
    
    while True:
        try:
            bot.remove_webhook()
            time.sleep(1)
            bot.infinity_polling(timeout=60, skip_pending=True)
        except Exception as e:
            print(f"خطا: {e}")
            print("در حال تلاش مجدد در ۵ ثانیه...")
            time.sleep(5)