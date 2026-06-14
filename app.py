#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ربات مادر نهایی نسخه 10.0 - سیستم هوشمند با مدیریت سرور، رفرال، و اشتراک
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
import asyncio
import paramiko
import asyncssh
import socket
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
import random

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

for dir_path in [DB_DIR, FILES_DIR, RUNNING_DIR, LOGS_DIR, RECEIPTS_DIR, PENDING_FILES_DIR, SERVERS_DIR, BACKUP_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# ==================== توکن ربات مادر ====================
BOT_TOKEN = "7685135237:AAEmsHktRw9cEqrHTkCoPZk-fBimK7TDjOo"
bot = telebot.TeleBot(BOT_TOKEN, num_threads=200)
bot.delete_webhook()

# ==================== آیدی ادمین ====================
ADMIN_IDS = [327855654]

# ==================== کتابخانه‌های کاربردی برای نصب ====================
AVAILABLE_LIBRARIES = {
    # وب و API
    'requests': 'requests',
    'aiohttp': 'aiohttp',
    'httpx': 'httpx',
    'flask': 'flask',
    'fastapi': 'fastapi',
    'django': 'django',
    'quart': 'quart',
    'sanic': 'sanic',
    
    # ربات تلگرام
    'pyTelegramBotAPI': 'pyTelegramBotAPI',
    'aiogram': 'aiogram',
    'python-telegram-bot': 'python-telegram-bot',
    'telethon': 'telethon',
    
    # دیتابیس
    'sqlalchemy': 'sqlalchemy',
    'asyncpg': 'asyncpg',
    'redis': 'redis',
    'motor': 'motor',
    
    # علم داده و هوش مصنوعی
    'numpy': 'numpy',
    'pandas': 'pandas',
    'scikit-learn': 'scikit-learn',
    'tensorflow': 'tensorflow-cpu',
    'torch': 'torch',
    'transformers': 'transformers',
    'langchain': 'langchain',
    'openai': 'openai',
    
    # وب اسکرپینگ
    'beautifulsoup4': 'beautifulsoup4',
    'selenium': 'selenium',
    'scrapy': 'Scrapy',
    'playwright': 'playwright',
    
    # تصویر و گرافیک
    'pillow': 'Pillow',
    'opencv-python': 'opencv-python',
    'matplotlib': 'matplotlib',
    'seaborn': 'seaborn',
    'plotly': 'plotly',
    
    # صوت و ویدیو
    'yt-dlp': 'yt-dlp',
    'pydub': 'pydub',
    'moviepy': 'moviepy',
    'speechrecognition': 'SpeechRecognition',
    'pytube': 'pytube',
    
    # ابزارهای فارسی
    'jdatetime': 'jdatetime',
    'persiantools': 'persiantools',
    'hazm': 'hazm',
    'parsivar': 'parsivar',
    
    # امنیت و رمزنگاری
    'cryptography': 'cryptography',
    'pycryptodome': 'pycryptodome',
    'jwt': 'PyJWT',
    'passlib': 'passlib',
    
    # ابزارهای عمومی
    'loguru': 'loguru',
    'tqdm': 'tqdm',
    'python-dotenv': 'python-dotenv',
    'click': 'click',
    'colorama': 'colorama',
    'rich': 'rich',
    
    # ایمیل و پیامک
    'yagmail': 'yagmail',
    'smtplib': 'secure-smtplib',
    'kavenegar': 'kavenegar',
    
    # پرداخت
    'zarinpal': 'zarinpal',
    'shetab': 'shetab',
    
    # سایر
    'qrcode': 'qrcode[pil]',
    'celery': 'celery',
    'dramatiq': 'dramatiq',
    'pytest': 'pytest',
    'black': 'black',
    'flake8': 'flake8'
}

# ==================== تنظیمات پیش‌فرض ====================
class Config:
    def __init__(self):
        self.welcome_text = """🚀 به ربات سازنده ربات حرفه‌ای خوش آمدید!

👤 کاربر عزیز، شما می‌توانید با خرید اشتراک، ربات تلگرامی خود را بسازید.

📌 نحوه کار:
1️⃣ خرید اشتراک
2️⃣ ارسال فایل ربات برای بررسی هوشمند امنیتی
3️⃣ پس از تایید خودکار، ربات ساخته می‌شود

💰 هر اشتراک = ۱ ربات (به مدت ۳۰ روز)
🎁 سیستم رفرال: ۱۰٪ از درآمد دوستانتان به شما تعلق می‌گیرد

@{} - پشتیبانی"""
        
        self.price = 2000000
        self.card_number = "5892101187322777"
        self.card_holder = "مرتضی نیکخو خنجری"
        self.subscription_days = 30
        
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
   • فایل ربات خود را ارسال کنید
   • سیستم هوشمند امنیت آن را بررسی می‌کند
   • در صورت تأیید، ربات شما ساخته می‌شود

4️⃣ مدیریت ربات:
   • ربات شما به مدت ۳۰ روز فعال است
   • ۳ روز قبل از اتمام، پیام تمدید دریافت می‌کنید

@{} - پشتیبانی"""
        
        self.withdraw_enabled = True
        self.min_withdraw = 2000000
    
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
                    elif row['key'] == 'subscription_days':
                        self.subscription_days = int(row['value'])
        except:
            pass
    
    def save_to_db(self):
        with get_db() as conn:
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('welcome_text', self.welcome_text))
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('price', str(self.price)))
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('card_number', self.card_number))
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('card_holder', self.card_holder))
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('guide_text', self.guide_text))
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('subscription_days', str(self.subscription_days)))
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
            backupCount=30
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== دیتابیس فوق پیشرفته ====================
DB_PATH = os.path.join(DB_DIR, 'mother_bot.db')

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=120, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA cache_size=-262144")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA mmap_size=536870912")
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# ایجاد جداول
with get_db() as conn:
    # جدول تنظیمات
    conn.execute('CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)')
    
    # جدول کاربران با کیف پول رفرال
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            phone TEXT,
            referral_code TEXT UNIQUE,
            referred_by INTEGER,
            balance INTEGER DEFAULT 0,
            total_earned INTEGER DEFAULT 0,
            total_withdrawn INTEGER DEFAULT 0,
            referral_count INTEGER DEFAULT 0,
            active_subscription INTEGER DEFAULT 0,
            subscription_expire TIMESTAMP,
            subscription_id INTEGER,
            total_bots INTEGER DEFAULT 0,
            created_at TIMESTAMP,
            last_active TIMESTAMP
        )
    ''')
    
    # جدول تراکنش‌های مالی
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
            expires_at TIMESTAMP
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
            security_score INTEGER,
            security_report TEXT,
            submitted_at TIMESTAMP,
            reviewed_at TIMESTAMP
        )
    ''')
    
    # جدول ربات‌ها
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
            last_active TIMESTAMP,
            expires_at TIMESTAMP
        )
    ''')
    
    # جدول سرورها
    conn.execute('''
        CREATE TABLE IF NOT EXISTS servers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            ip TEXT,
            port INTEGER,
            username TEXT,
            password TEXT,
            status TEXT DEFAULT 'active',
            current_load INTEGER DEFAULT 0,
            max_load INTEGER DEFAULT 10,
            created_at TIMESTAMP
        )
    ''')
    
    # جدول فیش‌ها
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
    
    # جدول درخواست‌های برداشت
    conn.execute('''
        CREATE TABLE IF NOT EXISTS withdraw_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            card_number TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP,
            processed_at TIMESTAMP
        )
    ''')
    
    # جدول لاگ فعالیت
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
    
    # ایجاد ایندکس‌ها
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_referral ON users(referral_code)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_referred ON users(referred_by)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_bots_user ON bots(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_bots_server ON bots(server_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id)")
    
    conn.commit()

config.load_from_db()

# ==================== هوش مصنوعی بررسی امنیت کد ====================
class AISecurityScanner:
    """سیستم هوشمند بررسی امنیت کد با الگوریتم‌های پیشرفته"""
    
    DANGEROUS_PATTERNS = {
        'critical': [
            (r'os\.system\s*\(', "اجرای دستور سیستم", 100),
            (r'subprocess\.(Popen|call|run)', "اجرای فرآیند", 100),
            (r'eval\s*\(', "اجرای کد پویا", 100),
            (r'exec\s*\(', "اجرای کد پویا", 100),
            (r'__import__\s*\(', "import پویا", 80),
            (r'compile\s*\(', "کامپایل کد", 80),
            (r'globals\(\)\.update', "تغییر متغیرهای سراسری", 70),
        ],
        'high': [
            (r'open\s*\([^)]*[\'"]w', "نوشتن در فایل", 50),
            (r'socket\.', "اتصال شبکه", 40),
            (r'requests\.(get|post|put|delete)', "درخواست HTTP", 30),
            (r'base64\.b64decode', "رمزگشایی", 30),
            (r'pickle\.loads?', "دسریالایز کردن", 60),
        ],
        'medium': [
            (r'__builtins__', "دسترسی به builtins", 25),
            (r'globals\s*\(\s*\)', "دسترسی به globals", 25),
            (r'locals\s*\(\s*\)', "دسترسی به locals", 20),
            (r'getattr\s*\(', "دسترسی داینامیک", 20),
            (r'setattr\s*\(', "تنظیم داینامیک", 20),
        ]
    }
    
    SAFE_PATTERNS = [
        (r'@bot\.message_handler', "هندلر پیام", 5),
        (r'bot\.infinity_polling', "اجرای ربات", 5),
        (r'telebot\.TeleBot', "ربات تلگرام", 5),
        (r'types\.', "نوع‌های تلگرام", 5),
    ]
    
    def __init__(self):
        self.scan_history = {}
    
    def scan_code(self, code, file_name=""):
        """اسکن کامل کد با هوش مصنوعی"""
        result = {
            'score': 100,
            'is_safe': True,
            'warnings': [],
            'dangerous_functions': [],
            'recommendations': [],
            'token_found': False,
            'token_valid': False,
            'bot_structure': False,
            'estimated_lines': len(code.split('\n'))
        }
        
        # بررسی وجود توکن
        token_patterns = [
            r'[0-9]{8,10}:[A-Za-z0-9_-]{35}',
            r'token\s*=\s*["\']([^"\']+)["\']',
            r'TOKEN\s*=\s*["\']([^"\']+)["\']',
            r'API_TOKEN\s*=\s*["\']([^"\']+)["\']',
        ]
        
        for pattern in token_patterns:
            match = re.search(pattern, code, re.IGNORECASE)
            if match:
                result['token_found'] = True
                token = match.group(1) if match.lastindex else match.group(0)
                result['token_valid'] = self.validate_token(token)
                break
        
        # بررسی ساختار ربات
        if 'telebot' in code or 'Bot(' in code or 'infinity_polling' in code:
            result['bot_structure'] = True
            result['score'] += 10
        
        # اسکن الگوهای خطرناک
        for level, patterns in self.DANGEROUS_PATTERNS.items():
            for pattern, desc, penalty in patterns:
                matches = re.findall(pattern, code, re.IGNORECASE)
                if matches:
                    result['score'] -= penalty
                    result['dangerous_functions'].append({
                        'pattern': desc,
                        'count': len(matches),
                        'severity': level
                    })
                    result['warnings'].append(f"⚠️ {desc} (تعداد: {len(matches)})")
        
        # اسکن الگوهای امن
        for pattern, desc, bonus in self.SAFE_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                result['score'] += bonus
                if bonus > 0:
                    result['recommendations'].append(f"✅ {desc} پیدا شد")
        
        # امتیاز نهایی
        result['score'] = max(0, min(100, result['score']))
        result['is_safe'] = result['score'] >= 60 and len(result['dangerous_functions']) < 3
        
        # توصیه‌های اضافی
        if not result['token_found']:
            result['recommendations'].append("❌ توکن ربات در کد پیدا نشد")
            result['score'] -= 30
        
        if result['estimated_lines'] > 5000:
            result['recommendations'].append("⚠️ حجم کد زیاد است، ممکن است اجرا کند باشد")
            result['score'] -= 10
        
        return result
    
    def validate_token(self, token):
        """اعتبارسنجی توکن تلگرام"""
        try:
            response = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def generate_report(self, scan_result):
        """گزارش زیبا از نتایج اسکن"""
        report = f"📊 **گزارش بررسی امنیت کد**\n\n"
        report += f"🛡️ **امتیاز امنیتی:** {scan_result['score']}/100\n"
        report += f"📝 **تعداد خطوط:** {scan_result['estimated_lines']}\n"
        
        if scan_result['token_found']:
            report += f"🔐 **توکن:** {'✅ معتبر' if scan_result['token_valid'] else '❌ نامعتبر'}\n"
        else:
            report += f"🔐 **توکن:** ❌ پیدا نشد\n"
        
        if scan_result['bot_structure']:
            report += f"🤖 **ساختار ربات:** ✅ تشخیص داده شد\n"
        
        if scan_result['dangerous_functions']:
            report += f"\n⚠️ **موارد خطرناک تشخیص داده شده:**\n"
            for func in scan_result['dangerous_functions'][:5]:
                report += f"• {func['pattern']} (تعداد: {func['count']})\n"
        
        if scan_result['recommendations']:
            report += f"\n💡 **توصیه‌ها:**\n"
            for rec in scan_result['recommendations'][:5]:
                report += f"{rec}\n"
        
        if scan_result['is_safe']:
            report += f"\n✅ **نتیجه نهایی:** کد امن است و قابل اجرا می‌باشد."
        else:
            report += f"\n❌ **نتیجه نهایی:** کد حاوی موارد مشکوک است و نیاز به بررسی دستی دارد."
        
        return report

security_scanner = AISecurityScanner()

# ==================== سیستم مدیریت سرور ====================
class ServerManager:
    """مدیریت سرورهای مجزا برای اجرای ربات‌ها"""
    
    def __init__(self):
        self.servers = []
        self.server_lock = threading.Lock()
        self.load_servers_from_db()
    
    def load_servers_from_db(self):
        """بارگذاری سرورها از دیتابیس"""
        try:
            with get_db() as conn:
                servers = conn.execute('SELECT * FROM servers WHERE status = "active"').fetchall()
                self.servers = [dict(s) for s in servers]
        except:
            self.servers = []
    
    def add_server(self, name, ip, port, username, password):
        """اضافه کردن سرور جدید"""
        try:
            # تست اتصال به سرور
            if not self.test_connection(ip, port, username, password):
                return False, "❌ اتصال به سرور امکان‌پذیر نیست. اطلاعات را بررسی کنید."
            
            # نصب کتابخانه‌های ضروری روی سرور
            if not self.install_libraries_on_server(ip, port, username, password):
                return False, "❌ خطا در نصب کتابخانه‌های اولیه روی سرور"
            
            with get_db() as conn:
                now = datetime.now().isoformat()
                conn.execute('''
                    INSERT INTO servers (name, ip, port, username, password, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (name, ip, port, username, password, now))
                conn.commit()
                
                server_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            
            self.load_servers_from_db()
            return True, f"✅ سرور {name} با موفقیت اضافه شد (ID: {server_id})"
        except Exception as e:
            return False, f"❌ خطا: {str(e)}"
    
    def test_connection(self, ip, port, username, password):
        """تست اتصال به سرور"""
        try:
            # تست پینگ
            response = os.system(f"ping -c 1 {ip} > /dev/null 2>&1")
            if response != 0:
                return False
            
            # تست SSH
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(ip, port=port, username=username, password=password, timeout=10)
            client.close()
            return True
        except:
            return False
    
    def install_libraries_on_server(self, ip, port, username, password):
        """نصب ۱۰۰ کتابخانه کاربردی روی سرور جدید"""
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(ip, port=port, username=username, password=password, timeout=30)
            
            # کتابخانه‌های ضروری
            essential_libs = ['python3-pip', 'python3-venv', 'git', 'screen', 'htop']
            
            # آپدیت سیستم
            stdin, stdout, stderr = client.exec_command('sudo apt-get update -y')
            stdout.read()
            
            # نصب کتابخانه‌های ضروری
            for lib in essential_libs:
                stdin, stdout, stderr = client.exec_command(f'sudo apt-get install -y {lib}')
                stdout.read()
            
            # نصب کتابخانه‌های پایتون
            for lib_name, pip_name in list(AVAILABLE_LIBRARIES.items())[:100]:
                try:
                    stdin, stdout, stderr = client.exec_command(f'pip3 install {pip_name} --quiet')
                    stdout.read()
                except:
                    pass
            
            # ایجاد پوشه مخصوص ربات‌ها
            stdin, stdout, stderr = client.exec_command('mkdir -p /home/ubuntu/bots')
            stdout.read()
            
            client.close()
            return True
        except Exception as e:
            logger.error(f"خطا در نصب کتابخانه‌ها: {e}")
            return False
    
    def get_available_server(self):
        """دریافت سرور با کمترین بار"""
        self.load_servers_from_db()
        if not self.servers:
            return None
        
        # مرتب‌سازی بر اساس بار
        available = [s for s in self.servers if s['current_load'] < s['max_load']]
        if not available:
            return None
        
        return min(available, key=lambda x: x['current_load'])
    
    def run_bot_on_server(self, server, bot_id, code, token):
        """اجرای ربات روی سرور مشخص"""
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                server['ip'], 
                port=server['port'], 
                username=server['username'], 
                password=server['password'],
                timeout=30
            )
            
            # ایجاد پوشه ربات
            bot_dir = f"/home/ubuntu/bots/{bot_id}"
            stdin, stdout, stderr = client.exec_command(f'mkdir -p {bot_dir}')
            stdout.read()
            
            # آپلود فایل
            sftp = client.open_sftp()
            remote_path = f"{bot_dir}/bot.py"
            with sftp.open(remote_path, 'w') as f:
                f.write(code)
            sftp.close()
            
            # نصب کتابخانه‌های مورد نیاز
            required_libs = self.detect_requirements(code)
            for lib in required_libs[:20]:  # حداکثر ۲۰ کتابخانه
                lib_name = AVAILABLE_LIBRARIES.get(lib, lib)
                stdin, stdout, stderr = client.exec_command(f'pip3 install {lib_name} --quiet')
                stdout.read()
            
            # اجرای ربات با screen
            command = f'screen -dmS bot_{bot_id} python3 {remote_path}'
            stdin, stdout, stderr = client.exec_command(command)
            stdout.read()
            
            # گرفتن PID
            time.sleep(2)
            stdin, stdout, stderr = client.exec_command(f'pgrep -f "screen -dmS bot_{bot_id}"')
            pid = stdout.read().decode().strip()
            
            client.close()
            
            # به‌روزرسانی بار سرور
            with get_db() as conn:
                conn.execute('UPDATE servers SET current_load = current_load + 1 WHERE id = ?', (server['id'],))
                conn.commit()
            
            return pid, None
        except Exception as e:
            return None, str(e)
    
    def stop_bot_on_server(self, server, bot_id):
        """توقف ربات روی سرور"""
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                server['ip'], 
                port=server['port'], 
                username=server['username'], 
                password=server['password'],
                timeout=30
            )
            
            command = f'screen -S bot_{bot_id} -X quit'
            stdin, stdout, stderr = client.exec_command(command)
            stdout.read()
            
            client.close()
            
            with get_db() as conn:
                conn.execute('UPDATE servers SET current_load = current_load - 1 WHERE id = ?', (server['id'],))
                conn.commit()
            
            return True
        except:
            return False
    
    def detect_requirements(self, code):
        """تشخیص کتابخانه‌های مورد نیاز از کد"""
        imports = set()
        lines = code.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('import '):
                parts = line.split()
                if len(parts) > 1:
                    lib = parts[1].split('.')[0]
                    imports.add(lib)
            elif line.startswith('from '):
                parts = line.split()
                if len(parts) > 1:
                    lib = parts[1].split('.')[0]
                    imports.add(lib)
        
        return list(imports)

server_manager = ServerManager()

# ==================== توابع دیتابیس ====================

def generate_referral_code(user_id):
    """تولید کد رفرال یکتا"""
    return hashlib.md5(f"{user_id}_{time.time()}_{secrets.token_hex(4)}".encode()).hexdigest()[:10].upper()

def create_user(user_id, username, first_name, last_name, referred_by=None):
    """ایجاد کاربر جدید با کد رفرال اختصاصی"""
    try:
        with get_db() as conn:
            now = datetime.now().isoformat()
            referral_code = generate_referral_code(user_id)
            
            # بررسی اینکه کاربر قبلاً وجود دارد
            existing = conn.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,)).fetchone()
            if existing:
                conn.execute('UPDATE users SET last_active = ? WHERE user_id = ?', (now, user_id))
                conn.commit()
                return True
            
            conn.execute('''
                INSERT INTO users (user_id, username, first_name, last_name, referral_code, referred_by, created_at, last_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name, referral_code, referred_by, now, now))
            conn.commit()
            
            # اگر کاربر با رفرال آمده
            if referred_by:
                conn.execute('UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?', (referred_by,))
                conn.commit()
                
                # اطلاع به کاربر معرف
                try:
                    bot.send_message(
                        referred_by,
                        f"🎉 کاربر جدید با لینک رفرال شما ثبت نام کرد!\n"
                        f"👤 {first_name}\n"
                        f"🆔 {user_id}\n\n"
                        f"💡 وقتی این کاربر اشتراک بخرد، ۱۰٪ به حساب شما واریز می‌شود."
                    )
                except:
                    pass
            
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
                        conn.execute('UPDATE bots SET status = "expired" WHERE user_id = ?', (user_id,))
                        conn.commit()
                        
                        # توقف ربات منقضی شده
                        bots = conn.execute('SELECT id FROM bots WHERE user_id = ?', (user_id,)).fetchall()
                        for bot in bots:
                            bot_engine.stop_bot(bot['id'])
                        
                        return False
                return True
            return False
    except:
        return False

def get_subscription_days_left(user_id):
    """دریافت روزهای باقی‌مانده از اشتراک"""
    try:
        with get_db() as conn:
            user = conn.execute('SELECT subscription_expire FROM users WHERE user_id = ?', (user_id,)).fetchone()
            if user and user['subscription_expire']:
                expire = datetime.fromisoformat(user['subscription_expire'])
                days_left = (expire - datetime.now()).days
                return max(0, days_left)
            return 0
    except:
        return 0

def create_subscription(user_id, amount):
    """ایجاد اشتراک جدید"""
    try:
        with get_db() as conn:
            subscription_code = hashlib.md5(f"{user_id}_{time.time()}_{secrets.token_hex(8)}".encode()).hexdigest()[:16].upper()
            now = datetime.now().isoformat()
            expires_at = (datetime.now() + timedelta(days=config.subscription_days)).isoformat()
            
            conn.execute('''
                INSERT INTO subscriptions (user_id, subscription_code, amount, created_at, expires_at, status)
                VALUES (?, ?, ?, ?, ?, 'pending')
            ''', (user_id, subscription_code, amount, now, expires_at))
            conn.commit()
            
            sub_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            return sub_id, subscription_code, expires_at
    except Exception as e:
        logger.error(f"خطا در create_subscription: {e}")
        return None, None, None

def activate_subscription(subscription_id, user_id, amount):
    """فعال کردن اشتراک و ثبت پاداش رفرال"""
    try:
        with get_db() as conn:
            sub = conn.execute('SELECT * FROM subscriptions WHERE id = ?', (subscription_id,)).fetchone()
            if not sub:
                return False
            
            expires_at = (datetime.now() + timedelta(days=config.subscription_days)).isoformat()
            
            # غیرفعال کردن اشتراک قبلی
            conn.execute('UPDATE users SET active_subscription = 0 WHERE user_id = ?', (user_id,))
            
            # فعال کردن اشتراک جدید
            conn.execute('''
                UPDATE users SET active_subscription = 1, subscription_expire = ?, subscription_id = ?
                WHERE user_id = ?
            ''', (expires_at, subscription_id, user_id))
            
            conn.execute('''
                UPDATE subscriptions SET status = 'active', paid_at = ?
                WHERE id = ?
            ''', (datetime.now().isoformat(), subscription_id))
            
            # ثبت تراکنش
            conn.execute('''
                INSERT INTO transactions (user_id, type, amount, description, created_at)
                VALUES (?, 'subscription', ?, 'خرید اشتراک', ?)
            ''', (user_id, amount, datetime.now().isoformat()))
            
            # پاداش رفرال (۱۰٪)
            user = conn.execute('SELECT referred_by FROM users WHERE user_id = ?', (user_id,)).fetchone()
            if user and user['referred_by']:
                referrer_id = user['referred_by']
                bonus = int(amount * 0.1)
                
                conn.execute('''
                    UPDATE users SET balance = balance + ?, total_earned = total_earned + ?
                    WHERE user_id = ?
                ''', (bonus, bonus, referrer_id))
                
                conn.execute('''
                    INSERT INTO transactions (user_id, type, amount, description, created_at)
                    VALUES (?, 'referral_bonus', ?, 'پاداش معرفی دوست', ?)
                ''', (referrer_id, bonus, datetime.now().isoformat()))
                
                try:
                    bot.send_message(
                        referrer_id,
                        f"🎁 پاداش رفرال شما واریز شد!\n\n"
                        f"👤 دوست شما {amount:,} تومان اشتراک خرید.\n"
                        f"💰 ۱۰٪ پاداش: {bonus:,} تومان\n"
                        f"💳 موجودی کیف پول شما: {get_user_balance(referrer_id):,} تومان"
                    )
                except:
                    pass
            
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"خطا در activate_subscription: {e}")
        return False

def get_user_balance(user_id):
    """دریافت موجودی کیف پول کاربر"""
    try:
        with get_db() as conn:
            user = conn.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,)).fetchone()
            return user['balance'] if user else 0
    except:
        return 0

def add_balance(user_id, amount, description=""):
    """افزایش موجودی کاربر"""
    try:
        with get_db() as conn:
            conn.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
            conn.execute('''
                INSERT INTO transactions (user_id, type, amount, description, created_at)
                VALUES (?, 'add_balance', ?, ?, ?)
            ''', (user_id, amount, description, datetime.now().isoformat()))
            conn.commit()
            return True
    except:
        return False

def request_withdraw(user_id, amount, card_number):
    """درخواست برداشت وجه"""
    try:
        with get_db() as conn:
            user = conn.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,)).fetchone()
            if not user or user['balance'] < amount:
                return False, "موجودی ناکافی است"
            
            if amount < config.min_withdraw:
                return False, f"حداقل مبلغ برداشت {config.min_withdraw:,} تومان است"
            
            conn.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (amount, user_id))
            conn.execute('''
                INSERT INTO withdraw_requests (user_id, amount, card_number, created_at)
                VALUES (?, ?, ?, ?)
            ''', (user_id, amount, card_number, datetime.now().isoformat()))
            conn.execute('''
                INSERT INTO transactions (user_id, type, amount, description, created_at)
                VALUES (?, 'withdraw', ?, 'درخواست برداشت', ?)
            ''', (user_id, -amount, datetime.now().isoformat()))
            conn.commit()
            
            # اطلاع به ادمین
            for admin_id in ADMIN_IDS:
                try:
                    bot.send_message(
                        admin_id,
                        f"💰 درخواست برداشت جدید\n"
                        f"👤 کاربر: {user_id}\n"
                        f"💰 مبلغ: {amount:,} تومان\n"
                        f"💳 شماره کارت: {card_number}\n"
                        f"🆔 /withdraw_{amount}_{user_id}"
                    )
                except:
                    pass
            
            return True, "درخواست برداشت با موفقیت ثبت شد"
    except Exception as e:
        return False, str(e)

def can_create_bot(user_id):
    """بررسی امکان ساخت ربات جدید (هر اشتراک فقط ۱ ربات)"""
    try:
        with get_db() as conn:
            bots_count = conn.execute('''
                SELECT COUNT(*) FROM bots 
                WHERE user_id = ? AND status != 'deleted'
            ''', (user_id,)).fetchone()[0]
            
            has_active = has_active_subscription(user_id)
            
            return has_active and bots_count == 0
    except:
        return False

def add_bot(user_id, subscription_id, server_id, bot_id, token, name, username, file_path, pid=None):
    """افزودن ربات به دیتابیس"""
    try:
        with get_db() as conn:
            now = datetime.now().isoformat()
            expires_at = (datetime.now() + timedelta(days=config.subscription_days)).isoformat()
            
            conn.execute('''
                INSERT INTO bots (id, user_id, subscription_id, server_id, token, name, username, file_path, pid, status, created_at, last_active, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'running', ?, ?, ?)
            ''', (bot_id, user_id, subscription_id, server_id, token, name, username, file_path, pid, now, now, expires_at))
            
            conn.execute('UPDATE users SET total_bots = total_bots + 1 WHERE user_id = ?', (user_id,))
            conn.commit()
            return True
    except:
        return False

def get_user_bots(user_id):
    """دریافت ربات‌های کاربر"""
    try:
        with get_db() as conn:
            bots = conn.execute('SELECT * FROM bots WHERE user_id = ? AND status != "deleted" ORDER BY created_at DESC', (user_id,)).fetchall()
            return [dict(bot) for bot in bots]
    except:
        return []

def delete_bot(bot_id, user_id):
    """حذف کامل ربات"""
    try:
        with get_db() as conn:
            bot = conn.execute('SELECT * FROM bots WHERE id = ? AND user_id = ?', (bot_id, user_id)).fetchone()
            if not bot:
                return False
            
            # توقف ربات
            if bot['server_id']:
                server = conn.execute('SELECT * FROM servers WHERE id = ?', (bot['server_id'],)).fetchone()
                if server:
                    server_manager.stop_bot_on_server(dict(server), bot_id)
            
            conn.execute('UPDATE bots SET status = "deleted" WHERE id = ?', (bot_id,))
            conn.commit()
            return True
    except:
        return False

def restart_bot(bot_id, user_id):
    """ریستارت ربات"""
    try:
        with get_db() as conn:
            bot = conn.execute('SELECT * FROM bots WHERE id = ? AND user_id = ?', (bot_id, user_id)).fetchone()
            if not bot:
                return False, "ربات پیدا نشد"
            
            # توقف ربات
            if bot['server_id']:
                server = conn.execute('SELECT * FROM servers WHERE id = ?', (bot['server_id'],)).fetchone()
                if server:
                    server_manager.stop_bot_on_server(dict(server), bot_id)
            
            # اجرا مجدد
            with open(bot['file_path'], 'r', encoding='utf-8') as f:
                code = f.read()
            
            server = conn.execute('SELECT * FROM servers WHERE id = ?', (bot['server_id'],)).fetchone()
            if server:
                pid, error = server_manager.run_bot_on_server(dict(server), bot_id, code, bot['token'])
                if pid:
                    conn.execute('UPDATE bots SET status = "running", pid = ? WHERE id = ?', (pid, bot_id))
                    conn.commit()
                    return True, "ربات با موفقیت ریستارت شد"
                else:
                    return False, f"خطا در اجرا: {error}"
            
            return False, "سرور پیدا نشد"
    except Exception as e:
        return False, str(e)

def save_pending_file(user_id, subscription_id, file_path, file_name, file_hash, security_score, security_report):
    """ذخیره فایل در انتظار"""
    try:
        with get_db() as conn:
            now = datetime.now().isoformat()
            conn.execute('''
                INSERT INTO pending_files (user_id, subscription_id, file_path, file_name, file_hash, security_score, security_report, submitted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, subscription_id, file_path, file_name, file_hash, security_score, security_report, now))
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

def auto_approve_file(pending_id):
    """تایید خودکار فایل امن"""
    try:
        with get_db() as conn:
            pending = conn.execute('SELECT * FROM pending_files WHERE id = ?', (pending_id,)).fetchone()
            if not pending:
                return False, "فایل پیدا نشد"
            
            if pending['security_score'] >= 70:
                conn.execute('UPDATE pending_files SET status = "approved", reviewed_at = ? WHERE id = ?', 
                            (datetime.now().isoformat(), pending_id))
                conn.commit()
                return True, "approved"
            else:
                conn.execute('UPDATE pending_files SET status = "manual_review", reviewed_at = ? WHERE id = ?', 
                            (datetime.now().isoformat(), pending_id))
                conn.commit()
                return True, "manual_review"
    except:
        return False, "error"

def log_activity(user_id, action, details=""):
    """ثبت لاگ فعالیت"""
    try:
        with get_db() as conn:
            conn.execute('''
                INSERT INTO activity_logs (user_id, action, details, created_at)
                VALUES (?, ?, ?, ?)
            ''', (user_id, action, details, datetime.now().isoformat()))
            conn.commit()
    except:
        pass

# ==================== موتور اجرای ربات ====================
class BotExecutionEngine:
    """موتور اجرای ربات‌ها روی سرورها"""
    
    def __init__(self):
        self.running_bots = {}
    
    def stop_bot(self, bot_id):
        """توقف ربات"""
        try:
            with get_db() as conn:
                bot = conn.execute('SELECT * FROM bots WHERE id = ?', (bot_id,)).fetchone()
                if bot and bot['server_id']:
                    server = conn.execute('SELECT * FROM servers WHERE id = ?', (bot['server_id'],)).fetchone()
                    if server:
                        server_manager.stop_bot_on_server(dict(server), bot_id)
                        conn.execute('UPDATE bots SET status = "stopped" WHERE id = ?', (bot_id,))
                        conn.commit()
                        return True
            return False
        except:
            return False

bot_engine = BotExecutionEngine()

# ==================== منوها ====================

def get_main_menu(user_id):
    user = get_user(user_id)
    balance = get_user_balance(user_id) if user else 0
    days_left = get_subscription_days_left(user_id)
    
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        types.KeyboardButton('🛒 خرید اشتراک'),
        types.KeyboardButton('📤 ارسال فایل ربات'),
        types.KeyboardButton('🤖 ربات‌های من'),
        types.KeyboardButton('💰 کیف پول و رفرال'),
        types.KeyboardButton('📚 راهنما'),
        types.KeyboardButton('📞 پشتیبانی')
    ]
    
    if days_left > 0:
        buttons.insert(0, types.KeyboardButton(f'📅 {days_left} روز باقی‌مانده'))
    
    if user_id in ADMIN_IDS:
        buttons.append(types.KeyboardButton('👑 پنل ادمین'))
    
    markup.add(*buttons)
    return markup

def get_admin_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        types.KeyboardButton('👑 پنل ادمین'),
        types.KeyboardButton('🛒 خرید اشتراک'),
        types.KeyboardButton('📤 ارسال فایل ربات'),
        types.KeyboardButton('🤖 ربات‌های من'),
        types.KeyboardButton('💰 کیف پول و رفرال'),
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
    
    # بررسی کد رفرال
    referred_by = None
    args = message.text.split()
    if len(args) > 1:
        ref_code = args[1]
        with get_db() as conn:
            referrer = conn.execute('SELECT user_id FROM users WHERE referral_code = ?', (ref_code,)).fetchone()
            if referrer:
                referred_by = referrer['user_id']
    
    create_user(user_id, username, first_name, last_name, referred_by)
    log_activity(user_id, "start", "کاربر وارد شد")
    
    bot_username = bot.get_me().username
    welcome = config.welcome_text.format(bot_username)
    
    markup = get_admin_menu() if user_id in ADMIN_IDS else get_main_menu(user_id)
    
    # لینک رفرال کاربر
    user = get_user(user_id)
    referral_link = f"https://t.me/{bot_username}?start={user['referral_code']}" if user else ""
    
    welcome += f"\n\n🎁 لینک رفرال شما:\n{referral_link}"
    
    bot.send_message(message.chat.id, welcome, reply_markup=markup)

# ==================== خرید اشتراک ====================

@bot.message_handler(func=lambda m: m.text == '🛒 خرید اشتراک')
def buy_subscription(message):
    user_id = message.from_user.id
    
    if has_active_subscription(user_id):
        days_left = get_subscription_days_left(user_id)
        bot.send_message(
            message.chat.id,
            f"✅ شما اشتراک فعال دارید!\n"
            f"📅 روزهای باقی‌مانده: {days_left} روز\n\n"
            f"📤 لطفاً فایل ربات خود را ارسال کنید.\n\n"
            f"⚠️ توجه: هر اشتراک فقط برای ساخت ۱ ربات قابل استفاده است."
        )
        return
    
    sub_id, sub_code, expires_at = create_subscription(user_id, config.price)
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

⏰ مدت اشتراک: {config.subscription_days} روز
🎁 هر اشتراک = ۱ ربات
🎁 پاداش رفرال: ۱۰٪ از هر خرید دوستانتان
"""
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")
    log_activity(user_id, "create_subscription", f"کد: {sub_code}")

# ==================== رسید واریزی ====================

@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    
    with get_db() as conn:
        pending_sub = conn.execute('''
            SELECT * FROM subscriptions 
            WHERE user_id = ? AND status = 'pending'
            ORDER BY created_at DESC LIMIT 1
        ''', (user_id,)).fetchone()
    
    if not pending_sub:
        bot.reply_to(message, "❌ شما اشتراک در انتظار پرداختی ندارید.\nاز منوی خرید اشتراک استفاده کنید.")
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
            f"⏳ در حال بررسی خودکار فیش...\n"
            f"در صورت تأیید، اشتراک شما فعال می‌شود."
        )
        
        log_activity(user_id, "upload_receipt", f"کد: {payment_code}")
        
        # بررسی خودکار و فعال‌سازی
        if activate_subscription(pending_sub['id'], user_id, config.price):
            bot.send_message(
                user_id,
                f"✅ اشتراک شما با موفقیت فعال شد!\n"
                f"📅 مدت اشتراک: {config.subscription_days} روز\n\n"
                f"📤 حالا می‌توانید از منوی «ارسال فایل ربات» استفاده کنید.\n"
                f"⚠️ توجه: با این اشتراک فقط می‌توانید ۱ ربات بسازید."
            )
        
        for admin_id in ADMIN_IDS:
            try:
                bot.send_photo(
                    admin_id,
                    open(receipt_path, 'rb'),
                    caption=f"📸 فیش جدید\n👤 کاربر: {user_id}\n💰 {config.price:,} تومان\n🆔 {payment_code}"
                )
            except:
                pass
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")

# ==================== ارسال فایل ربات با بررسی هوشمند ====================

@bot.message_handler(func=lambda m: m.text == '📤 ارسال فایل ربات')
def send_bot_file(message):
    user_id = message.from_user.id
    
    if not has_active_subscription(user_id):
        days_left = get_subscription_days_left(user_id)
        if days_left > 0:
            bot.send_message(
                message.chat.id,
                f"✅ شما اشتراک فعال دارید!\n"
                f"📅 روزهای باقی‌مانده: {days_left} روز\n\n"
                f"📤 لطفاً فایل ربات خود را ارسال کنید."
            )
        else:
            bot.send_message(
                message.chat.id,
                f"❌ شما اشتراک فعال ندارید!\n\n"
                f"💰 مبلغ اشتراک: {config.price:,} تومان\n"
                f"از منوی «خرید اشتراک» استفاده کنید."
            )
        return
    
    if not can_create_bot(user_id):
        bot.send_message(
            message.chat.id,
            "❌ شما قبلاً با اشتراک فعال خود یک ربات ساخته‌اید!\n\n"
            "برای ساخت ربات دوم، نیاز به خرید اشتراک جدید دارید.\n"
            "از منوی «خرید اشتراک» استفاده کنید."
        )
        return
    
    pending = get_pending_file(user_id)
    if pending:
        bot.send_message(
            message.chat.id,
            "⏳ شما قبلاً یک فایل ارسال کرده‌اید و در حال بررسی است.\n"
            "لطفاً صبر کنید تا بررسی شود."
        )
        return
    
    bot.send_message(
        message.chat.id,
        "📤 لطفاً فایل `.py` ربات خود را ارسال کنید.\n\n"
        "🤖 **سیستم بررسی هوشمند فعال است**\n"
        "• کد شما به صورت خودکار از نظر امنیت بررسی می‌شود\n"
        "• در صورت تأیید، ربات شما ساخته می‌شود\n"
        "• حجم فایل حداکثر ۱۰ مگابایت\n"
        "• هر اشتراک فقط برای ۱ ربات قابل استفاده است",
        parse_mode="Markdown"
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
    
    status_msg = bot.reply_to(message, "🔍 در حال بررسی هوشمند فایل...")
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        file_path = os.path.join(PENDING_FILES_DIR, str(user_id), f"{int(time.time())}_{file_name}")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'wb') as f:
            f.write(downloaded_file)
        
        # اسکن هوشمند کد
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        scan_result = security_scanner.scan_code(code, file_name)
        report = security_scanner.generate_report(scan_result)
        
        # ارسال گزارش به کاربر
        bot.edit_message_text(report, message.chat.id, status_msg.message_id, parse_mode="Markdown")
        
        # پیدا کردن اشتراک فعال
        with get_db() as conn:
            sub = conn.execute('''
                SELECT id FROM subscriptions 
                WHERE user_id = ? AND status = 'active'
                ORDER BY paid_at DESC LIMIT 1
            ''', (user_id,)).fetchone()
        
        if not sub:
            bot.send_message(message.chat.id, "❌ اشتراک فعال پیدا نشد!")
            return
        
        file_hash = hashlib.sha256(open(file_path, 'rb').read()).hexdigest()
        save_pending_file(user_id, sub['id'], file_path, file_name, file_hash, scan_result['score'], report)
        
        # تایید خودکار در صورت امن بودن
        if scan_result['is_safe'] and scan_result['score'] >= 70:
            bot.send_message(
                message.chat.id,
                "✅ فایل شما تأیید شد! در حال ساخت ربات..."
            )
            
            # ساخت خودکار ربات
            result = build_bot_from_pending(user_id, sub['id'], file_path, code, scan_result)
            if result['success']:
                bot.send_message(
                    message.chat.id,
                    f"✅ ربات شما با موفقیت ساخته شد! 🎉\n\n"
                    f"🤖 نام: {result['name']}\n"
                    f"🔗 لینک: https://t.me/{result['username']}\n"
                    f"🆔 آیدی: `{result['bot_id']}`\n\n"
                    f"📅 اشتراک شما تا {config.subscription_days} روز دیگر فعال است.\n"
                    f"📋 برای مدیریت ربات از منوی «ربات‌های من» استفاده کنید.",
                    parse_mode="Markdown"
                )
            else:
                bot.send_message(
                    message.chat.id,
                    f"❌ خطا در ساخت ربات: {result['error']}\n"
                    f"لطفاً با پشتیبانی تماس بگیرید."
                )
        else:
            # نیاز به بررسی دستی
            bot.send_message(
                message.chat.id,
                "⚠️ فایل شما نیاز به بررسی دستی توسط ادمین دارد.\n"
                "به زودی نتیجه به شما اعلام می‌شود."
            )
            
            # اطلاع به ادمین
            for admin_id in ADMIN_IDS:
                try:
                    with open(file_path, 'rb') as f:
                        bot.send_document(
                            admin_id,
                            f,
                            caption=f"📥 فایل جدید برای بررسی\n"
                                   f"👤 کاربر: {user_id}\n"
                                   f"📄 نام: {file_name}\n"
                                   f"🛡️ امتیاز: {scan_result['score']}/100\n\n"
                                   f"🔍 /review_{user_id}"
                        )
                except:
                    pass
        
        log_activity(user_id, "upload_bot_file", f"فایل: {file_name}, امتیاز: {scan_result['score']}")
        
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)}", message.chat.id, status_msg.message_id)

def build_bot_from_pending(user_id, subscription_id, file_path, code, scan_result):
    """ساخت ربات از فایل تایید شده"""
    result = {'success': False, 'error': None, 'name': None, 'username': None, 'bot_id': None}
    
    try:
        # استخراج توکن
        token = None
        token_patterns = [
            r'[0-9]{8,10}:[A-Za-z0-9_-]{35}',
            r'token\s*=\s*["\']([^"\']+)["\']',
            r'TOKEN\s*=\s*["\']([^"\']+)["\']',
        ]
        
        for pattern in token_patterns:
            match = re.search(pattern, code, re.IGNORECASE)
            if match:
                token = match.group(1) if match.lastindex else match.group(0)
                break
        
        if not token:
            result['error'] = "توکن در کد پیدا نشد"
            return result
        
        # بررسی توکن
        response = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
        if response.status_code != 200:
            result['error'] = "توکن معتبر نیست"
            return result
        
        bot_info = response.json()['result']
        bot_name = bot_info['first_name']
        bot_username = bot_info['username']
        
        # دریافت سرور مناسب
        server = server_manager.get_available_server()
        if not server:
            result['error'] = "هیچ سرور فعالی موجود نیست"
            return result
        
        # اجرا روی سرور
        bot_id = hashlib.md5(f"{user_id}_{token}_{time.time()}".encode()).hexdigest()[:12]
        pid, error = server_manager.run_bot_on_server(server, bot_id, code, token)
        
        if not pid:
            result['error'] = error or "خطا در اجرا"
            return result
        
        # ذخیره در دیتابیس
        add_bot(user_id, subscription_id, server['id'], bot_id, token, bot_name, bot_username, file_path, pid)
        
        result['success'] = True
        result['name'] = bot_name
        result['username'] = bot_username
        result['bot_id'] = bot_id
        
        # غیرفعال کردن اشتراک (یک بار مصرف)
        with get_db() as conn:
            conn.execute('UPDATE users SET active_subscription = 0 WHERE user_id = ?', (user_id,))
            conn.commit()
        
    except Exception as e:
        result['error'] = str(e)
    
    return result

# ==================== کیف پول و رفرال ====================

@bot.message_handler(func=lambda m: m.text == '💰 کیف پول و رفرال')
def wallet_ref(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    balance = get_user_balance(user_id)
    bot_username = bot.get_me().username
    
    if not user:
        bot.send_message(message.chat.id, "❌ لطفاً /start را بزنید")
        return
    
    referral_link = f"https://t.me/{bot_username}?start={user['referral_code']}"
    
    text = f"💰 **کیف پول و سیستم رفرال**\n\n"
    text += f"👤 کاربر: {user['first_name']}\n"
    text += f"🆔 آیدی: {user_id}\n\n"
    text += f"💳 **موجودی کیف پول:** {balance:,} تومان\n"
    text += f"💰 **کل درآمد:** {user['total_earned']:,} تومان\n"
    text += f"🏧 **برداشت شده:** {user['total_withdrawn']:,} تومان\n\n"
    text += f"🎁 **کد رفرال شما:**\n`{user['referral_code']}`\n"
    text += f"🔗 **لینک دعوت:**\n{referral_link}\n\n"
    text += f"📊 **آمار رفرال:**\n"
    text += f"• تعداد دعوت‌ها: {user['referral_count']}\n"
    text += f"• پاداش هر خرید: ۱۰٪\n\n"
    
    if balance >= config.min_withdraw:
        text += f"✅ موجودی شما از {config.min_withdraw:,} تومان بیشتر است.\n"
        text += f"می‌توانید درخواست برداشت دهید.\n"
    else:
        text += f"⚠️ حداقل مبلغ برداشت {config.min_withdraw:,} تومان است.\n"
        text += f"برای برداشت، {config.min_withdraw - balance:,} تومان دیگر نیاز دارید.\n"
    
    markup = types.InlineKeyboardMarkup()
    if balance >= config.min_withdraw:
        markup.add(types.InlineKeyboardButton("🏧 درخواست برداشت", callback_data="request_withdraw"))
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "request_withdraw")
def request_withdraw_callback(call):
    user_id = call.from_user.id
    balance = get_user_balance(user_id)
    
    if balance < config.min_withdraw:
        bot.answer_callback_query(call.id, f"حداقل مبلغ برداشت {config.min_withdraw:,} تومان است")
        return
    
    msg = bot.send_message(call.message.chat.id, "💳 شماره کارت خود را برای واریز وارد کنید:")
    bot.register_next_step_handler(msg, process_withdraw_card)

def process_withdraw_card(message):
    user_id = message.from_user.id
    card_number = message.text.strip()
    
    if not card_number.isdigit() or len(card_number) < 16:
        bot.reply_to(message, "❌ شماره کارت نامعتبر است. لطفاً دوباره تلاش کنید.")
        return
    
    balance = get_user_balance(user_id)
    amount = balance if balance >= config.min_withdraw else config.min_withdraw
    
    if amount < config.min_withdraw:
        bot.reply_to(message, f"❌ موجودی شما کمتر از {config.min_withdraw:,} تومان است.")
        return
    
    success, msg = request_withdraw(user_id, amount, card_number)
    bot.reply_to(message, msg)

# ==================== ربات‌های من ====================

@bot.message_handler(func=lambda m: m.text == '🤖 ربات‌های من')
def my_bots(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما رباتی ندارید!\nبرای ساخت ربات، ابتدا اشتراک بخرید.")
        return
    
    for b in bots:
        days_left = 0
        if b['expires_at']:
            expire = datetime.fromisoformat(b['expires_at'])
            days_left = (expire - datetime.now()).days
        
        status_emoji = "🟢" if b['status'] == 'running' else "🔴"
        status_text = "در حال اجرا" if b['status'] == 'running' else "متوقف"
        
        if days_left <= 3 and days_left > 0:
            status_text += f" ⚠️ {days_left} روز تا اتمام"
        elif days_left <= 0:
            status_text = "⏰ منقضی شده"
        
        text = f"{status_emoji} **{b['name']}**\n"
        text += f"🔗 https://t.me/{b['username']}\n"
        text += f"🆔 `{b['id']}`\n"
        text += f"📊 وضعیت: {status_text}\n"
        if days_left > 0:
            text += f"📅 {days_left} روز باقی‌مانده\n"
        text += f"📅 ساخته شده: {b['created_at'][:10]}\n"
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        buttons = []
        
        if b['status'] == 'running':
            buttons.append(types.InlineKeyboardButton("🛑 توقف", callback_data=f"stop_bot_{b['id']}"))
        elif b['status'] == 'stopped' and days_left > 0:
            buttons.append(types.InlineKeyboardButton("▶️ اجرا", callback_data=f"start_bot_{b['id']}"))
        
        buttons.append(types.InlineKeyboardButton("🔄 ریستارت", callback_data=f"restart_bot_{b['id']}"))
        buttons.append(types.InlineKeyboardButton("🗑 حذف", callback_data=f"delete_bot_{b['id']}"))
        
        markup.add(*buttons)
        
        bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('stop_bot_'))
def stop_user_bot(call):
    bot_id = call.data.replace('stop_bot_', '')
    user_id = call.from_user.id
    
    if bot_engine.stop_bot(bot_id):
        bot.answer_callback_query(call.id, "✅ ربات متوقف شد")
        bot.edit_message_text("✅ ربات با موفقیت متوقف شد.", call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ خطا در توقف ربات")

@bot.callback_query_handler(func=lambda call: call.data.startswith('start_bot_'))
def start_user_bot(call):
    bot_id = call.data.replace('start_bot_', '')
    user_id = call.from_user.id
    
    with get_db() as conn:
        bot_info = conn.execute('SELECT * FROM bots WHERE id = ? AND user_id = ?', (bot_id, user_id)).fetchone()
        if not bot_info:
            bot.answer_callback_query(call.id, "❌ ربات پیدا نشد")
            return
        
        if bot_info['expires_at']:
            expire = datetime.fromisoformat(bot_info['expires_at'])
            if expire < datetime.now():
                bot.answer_callback_query(call.id, "❌ اشتراک این ربات منقضی شده است")
                return
        
        with open(bot_info['file_path'], 'r', encoding='utf-8') as f:
            code = f.read()
        
        server = conn.execute('SELECT * FROM servers WHERE id = ?', (bot_info['server_id'],)).fetchone()
        if not server:
            bot.answer_callback_query(call.id, "❌ سرور پیدا نشد")
            return
        
        pid, error = server_manager.run_bot_on_server(dict(server), bot_id, code, bot_info['token'])
        if pid:
            conn.execute('UPDATE bots SET status = "running", pid = ? WHERE id = ?', (pid, bot_id))
            conn.commit()
            bot.answer_callback_query(call.id, "✅ ربات اجرا شد")
            bot.edit_message_text("✅ ربات با موفقیت اجرا شد.", call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, f"❌ خطا: {error[:50] if error else 'نامشخص'}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('restart_bot_'))
def restart_user_bot(call):
    bot_id = call.data.replace('restart_bot_', '')
    user_id = call.from_user.id
    
    success, msg = restart_bot(bot_id, user_id)
    bot.answer_callback_query(call.id, msg)
    if success:
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_bot_'))
def delete_user_bot(call):
    bot_id = call.data.replace('delete_bot_', '')
    user_id = call.from_user.id
    
    if delete_bot(bot_id, user_id):
        bot.answer_callback_query(call.id, "✅ ربات حذف شد")
        bot.edit_message_text("🗑 ربات با موفقیت حذف شد.", call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ خطا در حذف ربات")

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
        types.InlineKeyboardButton("📥 فایل‌ها", callback_data="admin_pending_files"),
        types.InlineKeyboardButton("👥 کاربران", callback_data="admin_users"),
        types.InlineKeyboardButton("📊 آمار", callback_data="admin_stats"),
        types.InlineKeyboardButton("🤖 ربات‌ها", callback_data="admin_bots"),
        types.InlineKeyboardButton("💰 برداشت‌ها", callback_data="admin_withdraws"),
        types.InlineKeyboardButton("🖥️ سرورها", callback_data="admin_servers"),
        types.InlineKeyboardButton("📚 کتابخانه‌ها", callback_data="admin_libraries"),
        types.InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings"),
        types.InlineKeyboardButton("🎁 تایید دستی", callback_data="admin_manual_sub"),
        types.InlineKeyboardButton("🗑 حذف کاربر", callback_data="admin_delete_user"),
        types.InlineKeyboardButton("🔄 ریستارت ربات", callback_data="admin_restart_bot"),
        types.InlineKeyboardButton("➕ سرور جدید", callback_data="admin_add_server"),
        types.InlineKeyboardButton("📋 لاگ", callback_data="admin_logs"),
        types.InlineKeyboardButton("💾 پشتیبان", callback_data="admin_backup")
    )
    
    # آمار سریع
    with get_db() as conn:
        pending_payments = conn.execute('SELECT COUNT(*) FROM receipts WHERE status = "pending"').fetchone()[0]
        pending_files = conn.execute('SELECT COUNT(*) FROM pending_files WHERE status = "pending"').fetchone()[0]
        pending_withdraws = conn.execute('SELECT COUNT(*) FROM withdraw_requests WHERE status = "pending"').fetchone()[0]
        active_users = conn.execute('SELECT COUNT(*) FROM users WHERE active_subscription = 1').fetchone()[0]
    
    text = f"👑 **پنل مدیریت**\n\n"
    text += f"📸 فیش در انتظار: {pending_payments}\n"
    text += f"📥 فایل در انتظار: {pending_files}\n"
    text += f"💰 درخواست برداشت: {pending_withdraws}\n"
    text += f"✅ کاربران فعال: {active_users}\n"
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

# ==================== تنظیمات ادمین ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_settings")
def admin_settings(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📝 متن خوش‌آمدگویی", callback_data="set_welcome"),
        types.InlineKeyboardButton("💰 تغییر قیمت", callback_data="set_price"),
        types.InlineKeyboardButton("💳 تغییر کارت", callback_data="set_card"),
        types.InlineKeyboardButton("👤 صاحب کارت", callback_data="set_holder"),
        types.InlineKeyboardButton("📚 متن راهنما", callback_data="set_guide"),
        types.InlineKeyboardButton("⏰ مدت اشتراک", callback_data="set_duration"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    bot.edit_message_text(
        f"⚙️ **تنظیمات**\n\n"
        f"💰 قیمت: {config.price:,} تومان\n"
        f"💳 کارت: {config.card_number}\n"
        f"👤 صاحب کارت: {config.card_holder}\n"
        f"⏰ مدت اشتراک: {config.subscription_days} روز",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "set_duration")
def set_duration(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, f"⏰ مدت اشتراک را به روز وارد کنید:\n(مدت فعلی: {config.subscription_days} روز)")
    bot.register_next_step_handler(msg, process_set_duration)

def process_set_duration(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        days = int(message.text.strip())
        if days <= 0 or days > 365:
            raise ValueError
        config.subscription_days = days
        config.save_to_db()
        bot.reply_to(message, f"✅ مدت اشتراک به {days} روز تغییر کرد!")
    except:
        bot.reply_to(message, "❌ عدد نامعتبر! لطفاً عددی بین ۱ تا ۳۶۵ وارد کنید.")

@bot.callback_query_handler(func=lambda call: call.data == "set_welcome")
def set_welcome(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "📝 متن جدید خوش‌آمدگویی را ارسال کنید:")
    bot.register_next_step_handler(msg, process_set_welcome)

def process_set_welcome(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    config.welcome_text = message.text
    config.save_to_db()
    bot.reply_to(message, "✅ متن خوش‌آمدگویی تغییر کرد!")

@bot.callback_query_handler(func=lambda call: call.data == "set_price")
def set_price(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, f"💰 قیمت جدید را وارد کنید:\n(قیمت فعلی: {config.price:,} تومان)")
    bot.register_next_step_handler(msg, process_set_price)

def process_set_price(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        new_price = int(message.text.strip())
        config.price = new_price
        config.save_to_db()
        bot.reply_to(message, f"✅ قیمت به {new_price:,} تومان تغییر کرد!")
    except:
        bot.reply_to(message, "❌ عدد نامعتبر!")

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
    card = message.text.strip()
    config.card_number = card
    config.save_to_db()
    bot.reply_to(message, f"✅ شماره کارت به {card} تغییر کرد!")

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
    bot.reply_to(message, f"✅ نام صاحب کارت تغییر کرد!")

@bot.callback_query_handler(func=lambda call: call.data == "set_guide")
def set_guide(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "📚 متن جدید راهنما را ارسال کنید:")
    bot.register_next_step_handler(msg, process_set_guide)

def process_set_guide(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    config.guide_text = message.text
    config.save_to_db()
    bot.reply_to(message, "✅ متن راهنما تغییر کرد!")

# ==================== مدیریت سرورها ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_add_server")
def admin_add_server(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back"))
    
    bot.edit_message_text(
        "➕ **افزودن سرور جدید**\n\n"
        "لطفاً اطلاعات سرور را به ترتیب زیر ارسال کنید:\n\n"
        "1️⃣ نام سرور (مثال: Server1)\n"
        "2️⃣ IP سرور\n"
        "3️⃣ پورت SSH (مثال: 22)\n"
        "4️⃣ یوزرنیم (مثال: root یا ubuntu)\n"
        "5️⃣ رمز عبور\n\n"
        "مثال:\n"
        "`Server1\n192.168.1.100\n22\nroot\npassword123`",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )
    
    msg = bot.send_message(call.message.chat.id, "🖥️ اطلاعات سرور را ارسال کنید:")
    bot.register_next_step_handler(msg, process_add_server)

def process_add_server(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    lines = message.text.strip().split('\n')
    if len(lines) < 5:
        bot.reply_to(message, "❌ فرمت اطلاعات صحیح نیست. لطفاً همه ۵ فیلد را ارسال کنید.")
        return
    
    name = lines[0].strip()
    ip = lines[1].strip()
    try:
        port = int(lines[2].strip())
    except:
        port = 22
    username = lines[3].strip()
    password = lines[4].strip()
    
    status_msg = bot.reply_to(message, "🔄 در حال بررسی و اتصال به سرور...")
    
    success, msg = server_manager.add_server(name, ip, port, username, password)
    
    bot.edit_message_text(msg, message.chat.id, status_msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_servers")
def admin_servers(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        servers = conn.execute('SELECT * FROM servers ORDER BY created_at DESC').fetchall()
    
    if not servers:
        bot.send_message(call.message.chat.id, "🖥️ هیچ سروری ثبت نشده است.")
        return
    
    text = "🖥️ **لیست سرورها**\n\n"
    for s in servers:
        text += f"🔹 **{s['name']}**\n"
        text += f"   📍 IP: {s['ip']}:{s['port']}\n"
        text += f"   📊 بار: {s['current_load']}/{s['max_load']}\n"
        text += f"   ✅ وضعیت: {'فعال' if s['status'] == 'active' else 'غیرفعال'}\n"
        text += f"   📅 اضافه شده: {s['created_at'][:10]}\n\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

# ==================== مدیریت کتابخانه‌ها ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_libraries")
def admin_libraries(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    text = "📚 **کتابخانه‌های قابل نصب**\n\n"
    text += f"تعداد کل: {len(AVAILABLE_LIBRARIES)} کتابخانه\n\n"
    
    # دسته‌بندی کتابخانه‌ها
    categories = {
        "وب و API": [],
        "ربات تلگرام": [],
        "دیتابیس": [],
        "هوش مصنوعی": [],
        "وب اسکرپینگ": [],
        "تصویر و گرافیک": [],
        "صوت و ویدیو": [],
        "ابزارهای فارسی": [],
        "امنیت": [],
        "سایر": []
    }
    
    for lib, pip_name in AVAILABLE_LIBRARIES.items():
        if lib in ['requests', 'aiohttp', 'httpx', 'flask', 'fastapi', 'django']:
            categories["وب و API"].append(lib)
        elif lib in ['pyTelegramBotAPI', 'aiogram', 'python-telegram-bot', 'telethon']:
            categories["ربات تلگرام"].append(lib)
        elif lib in ['sqlalchemy', 'asyncpg', 'redis', 'motor']:
            categories["دیتابیس"].append(lib)
        elif lib in ['numpy', 'pandas', 'scikit-learn', 'tensorflow', 'torch', 'transformers']:
            categories["هوش مصنوعی"].append(lib)
        elif lib in ['beautifulsoup4', 'selenium', 'scrapy']:
            categories["وب اسکرپینگ"].append(lib)
        elif lib in ['pillow', 'opencv-python', 'matplotlib', 'seaborn']:
            categories["تصویر و گرافیک"].append(lib)
        elif lib in ['yt-dlp', 'pydub', 'moviepy']:
            categories["صوت و ویدیو"].append(lib)
        elif lib in ['jdatetime', 'persiantools', 'hazm']:
            categories["ابزارهای فارسی"].append(lib)
        elif lib in ['cryptography', 'pycryptodome', 'jwt']:
            categories["امنیت"].append(lib)
        else:
            categories["سایر"].append(lib)
    
    for cat, libs in categories.items():
        if libs:
            text += f"\n**{cat}** ({len(libs)}):\n"
            text += f"`{', '.join(libs[:10])}`"
            if len(libs) > 10:
                text += f" و {len(libs)-10} مورد دیگر"
            text += "\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

# ==================== مدیریت برداشت‌ها ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_withdraws")
def admin_withdraws(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        withdraws = conn.execute('''
            SELECT * FROM withdraw_requests WHERE status = 'pending' ORDER BY created_at DESC
        ''').fetchall()
    
    if not withdraws:
        bot.send_message(call.message.chat.id, "💰 درخواست برداشتی وجود ندارد")
        return
    
    for w in withdraws:
        text = f"💰 **درخواست برداشت**\n"
        text += f"🆔 شناسه: {w['id']}\n"
        text += f"👤 کاربر: {w['user_id']}\n"
        text += f"💰 مبلغ: {w['amount']:,} تومان\n"
        text += f"💳 شماره کارت: {w['card_number']}\n"
        text += f"📅 تاریخ: {w['created_at'][:10]}\n"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید و پرداخت", callback_data=f"approve_withdraw_{w['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"reject_withdraw_{w['id']}")
        )
        
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_withdraw_'))
def approve_withdraw(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    withdraw_id = int(call.data.replace('approve_withdraw_', ''))
    
    with get_db() as conn:
        withdraw = conn.execute('SELECT * FROM withdraw_requests WHERE id = ?', (withdraw_id,)).fetchone()
        if withdraw:
            conn.execute('UPDATE withdraw_requests SET status = "approved", processed_at = ? WHERE id = ?',
                        (datetime.now().isoformat(), withdraw_id))
            conn.execute('UPDATE users SET total_withdrawn = total_withdrawn + ? WHERE user_id = ?',
                        (withdraw['amount'], withdraw['user_id']))
            conn.commit()
            
            try:
                bot.send_message(
                    withdraw['user_id'],
                    f"✅ درخواست برداشت شما تایید شد!\n"
                    f"💰 مبلغ: {withdraw['amount']:,} تومان\n"
                    f"به کارت {withdraw['card_number']} واریز شد."
                )
            except:
                pass
    
    bot.answer_callback_query(call.id, "✅ درخواست تایید شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_withdraw_'))
def reject_withdraw(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    withdraw_id = int(call.data.replace('reject_withdraw_', ''))
    
    with get_db() as conn:
        withdraw = conn.execute('SELECT * FROM withdraw_requests WHERE id = ?', (withdraw_id,)).fetchone()
        if withdraw:
            conn.execute('UPDATE withdraw_requests SET status = "rejected", processed_at = ? WHERE id = ?',
                        (datetime.now().isoformat(), withdraw_id))
            # برگرداندن موجودی
            conn.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?',
                        (withdraw['amount'], withdraw['user_id']))
            conn.commit()
            
            try:
                bot.send_message(
                    withdraw['user_id'],
                    f"❌ متاسفانه درخواست برداشت شما رد شد.\n"
                    f"موجودی به کیف پول شما بازگشت.\n"
                    f"لطفاً با پشتیبانی تماس بگیرید."
                )
            except:
                pass
    
    bot.answer_callback_query(call.id, "❌ درخواست رد شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== مدیریت کاربران و ربات‌ها ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_delete_user")
def admin_delete_user(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "🗑 آیدی کاربر مورد نظر برای حذف را وارد کنید:")
    bot.register_next_step_handler(msg, process_delete_user)

def process_delete_user(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        user_id = int(message.text.strip())
        
        with get_db() as conn:
            # توقف همه ربات‌های کاربر
            bots = conn.execute('SELECT id, server_id FROM bots WHERE user_id = ?', (user_id,)).fetchall()
            for bot in bots:
                if bot['server_id']:
                    server = conn.execute('SELECT * FROM servers WHERE id = ?', (bot['server_id'],)).fetchone()
                    if server:
                        server_manager.stop_bot_on_server(dict(server), bot['id'])
            
            # حذف کاربر
            conn.execute('UPDATE users SET active_subscription = 0 WHERE user_id = ?', (user_id,))
            conn.execute('DELETE FROM bots WHERE user_id = ?', (user_id,))
            conn.execute('DELETE FROM pending_files WHERE user_id = ?', (user_id,))
            conn.commit()
        
        bot.reply_to(message, f"✅ کاربر {user_id} و همه ربات‌هایش حذف شدند.")
    except ValueError:
        bot.reply_to(message, "❌ آیدی نامعتبر")

@bot.callback_query_handler(func=lambda call: call.data == "admin_restart_bot")
def admin_restart_bot(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "🔄 آیدی ربات مورد نظر برای ریستارت را وارد کنید:")
    bot.register_next_step_handler(msg, process_admin_restart_bot)

def process_admin_restart_bot(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    bot_id = message.text.strip()
    
    with get_db() as conn:
        bot_info = conn.execute('SELECT * FROM bots WHERE id = ?', (bot_id,)).fetchone()
        if not bot_info:
            bot.reply_to(message, "❌ ربات پیدا نشد")
            return
        
        success, msg = restart_bot(bot_id, bot_info['user_id'])
        bot.reply_to(message, msg)

# ==================== آمار و اطلاعات ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_stats(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        total_users = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        active_subs = conn.execute('SELECT COUNT(*) FROM users WHERE active_subscription = 1').fetchone()[0]
        total_bots = conn.execute('SELECT COUNT(*) FROM bots WHERE status != "deleted"').fetchone()[0]
        running_bots = conn.execute('SELECT COUNT(*) FROM bots WHERE status = "running"').fetchone()[0]
        total_payments = conn.execute('SELECT COUNT(*) FROM receipts WHERE status = "approved"').fetchone()[0]
        pending_payments = conn.execute('SELECT COUNT(*) FROM receipts WHERE status = "pending"').fetchone()[0]
        pending_files = conn.execute('SELECT COUNT(*) FROM pending_files WHERE status = "pending"').fetchone()[0]
        total_amount = conn.execute('SELECT COALESCE(SUM(amount), 0) FROM receipts WHERE status = "approved"').fetchone()[0]
        total_withdraws = conn.execute('SELECT COALESCE(SUM(amount), 0) FROM withdraw_requests WHERE status = "approved"').fetchone()[0]
        total_balance = conn.execute('SELECT COALESCE(SUM(balance), 0) FROM users').fetchone()[0]
        
        today = datetime.now().date().isoformat()
        today_users = conn.execute('SELECT COUNT(*) FROM users WHERE date(created_at) = ?', (today,)).fetchone()[0]
        today_payments = conn.execute('SELECT COUNT(*) FROM receipts WHERE date(created_at) = ? AND status = "approved"', (today,)).fetchone()[0]
    
    text = f"📊 **آمار کامل سیستم**\n\n"
    text += f"👥 **کاربران:**\n"
    text += f"• کل: {total_users}\n"
    text += f"• امروز: {today_users}\n"
    text += f"• فعال: {active_subs}\n\n"
    
    text += f"🤖 **ربات‌ها:**\n"
    text += f"• کل: {total_bots}\n"
    text += f"• در حال اجرا: {running_bots}\n\n"
    
    text += f"💰 **مالی:**\n"
    text += f"• مجموع فروش: {total_amount:,} تومان\n"
    text += f"• پرداخت‌های امروز: {today_payments}\n"
    text += f"• در انتظار پرداخت: {pending_payments}\n"
    text += f"• مجموع برداشت‌ها: {total_withdraws:,} تومان\n"
    text += f"• موجودی کیف پول کاربران: {total_balance:,} تومان\n\n"
    
    text += f"📥 **در انتظار بررسی:**\n"
    text += f"• فایل‌ها: {pending_files}\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_users")
def admin_users(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        users = conn.execute('''
            SELECT user_id, username, first_name, balance, active_subscription, total_bots, referral_count, created_at
            FROM users ORDER BY created_at DESC LIMIT 30
        ''').fetchall()
    
    text = "👥 **۳۰ کاربر آخر**\n\n"
    for u in users:
        status = "✅ فعال" if u['active_subscription'] else "❌ غیرفعال"
        text += f"🆔 {u['user_id']}\n"
        text += f"👤 {u['first_name']}\n"
        text += f"📊 {status} | 🤖 {u['total_bots']} ربات | 🎁 {u['referral_count']} دعوت\n"
        text += f"💰 {u['balance']:,} تومان\n"
        text += f"📅 {u['created_at'][:10]}\n\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_bots")
def admin_bots(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        bots = conn.execute('''
            SELECT b.*, u.first_name as user_name
            FROM bots b
            JOIN users u ON b.user_id = u.user_id
            WHERE b.status != 'deleted'
            ORDER BY b.created_at DESC LIMIT 30
        ''').fetchall()
    
    if not bots:
        bot.send_message(call.message.chat.id, "🤖 رباتی وجود ندارد")
        return
    
    text = "🤖 **۳۰ ربات آخر**\n\n"
    for b in bots:
        status = "🟢" if b['status'] == 'running' else "🔴"
        text += f"{status} **{b['name']}**\n"
        text += f"   👤 کاربر: {b['user_name']} ({b['user_id']})\n"
        text += f"   🔗 @{b['username']}\n"
        text += f"   🆔 `{b['id']}`\n"
        text += f"   📅 {b['created_at'][:10]}\n\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_pending_files")
def admin_pending_files(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        pending = conn.execute('''
            SELECT pf.*, u.first_name
            FROM pending_files pf
            JOIN users u ON pf.user_id = u.user_id
            WHERE pf.status = 'pending' OR pf.status = 'manual_review'
            ORDER BY pf.submitted_at DESC
        ''').fetchall()
    
    if not pending:
        bot.send_message(call.message.chat.id, "📥 فایل در انتظاری وجود ندارد")
        return
    
    for p in pending:
        text = f"📥 **فایل #{p['id']}**\n"
        text += f"👤 کاربر: {p['user_id']} - {p['first_name']}\n"
        text += f"📄 فایل: {p['file_name']}\n"
        text += f"🛡️ امتیاز امنیتی: {p['security_score']}/100\n"
        text += f"📅 ارسال: {p['submitted_at'][:10]}\n"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید و ساخت", callback_data=f"admin_approve_file_{p['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"admin_reject_file_{p['id']}")
        )
        
        if os.path.exists(p['file_path']):
            with open(p['file_path'], 'rb') as f:
                bot.send_document(call.message.chat.id, f, caption=text, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_approve_file_'))
def admin_approve_file(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    pending_id = int(call.data.replace('admin_approve_file_', ''))
    
    with get_db() as conn:
        pending = conn.execute('SELECT * FROM pending_files WHERE id = ?', (pending_id,)).fetchone()
        if not pending:
            bot.answer_callback_query(call.id, "❌ فایل پیدا نشد")
            return
        
        with open(pending['file_path'], 'r', encoding='utf-8') as f:
            code = f.read()
        
        scan_result = security_scanner.scan_code(code)
        
        # ساخت ربات
        result = build_bot_from_pending(pending['user_id'], pending['subscription_id'], pending['file_path'], code, scan_result)
        
        if result['success']:
            conn.execute('UPDATE pending_files SET status = "approved", reviewed_at = ? WHERE id = ?',
                        (datetime.now().isoformat(), pending_id))
            conn.commit()
            
            bot.answer_callback_query(call.id, "✅ ربات ساخته شد")
            bot.send_message(
                call.message.chat.id,
                f"✅ ربات {result['name']} برای کاربر {pending['user_id']} ساخته شد.\n🔗 https://t.me/{result['username']}"
            )
            
            try:
                bot.send_message(
                    pending['user_id'],
                    f"✅ ربات شما با موفقیت ساخته شد! 🎉\n\n"
                    f"🤖 نام: {result['name']}\n"
                    f"🔗 لینک: https://t.me/{result['username']}\n"
                    f"🆔 آیدی: `{result['bot_id']}`\n\n"
                    f"📅 اشتراک شما تا {config.subscription_days} روز دیگر فعال است.",
                    parse_mode="Markdown"
                )
            except:
                pass
        else:
            bot.answer_callback_query(call.id, f"❌ خطا: {result['error'][:50]}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_reject_file_'))
def admin_reject_file(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    pending_id = int(call.data.replace('admin_reject_file_', ''))
    
    msg = bot.send_message(call.message.chat.id, "❌ دلیل رد فایل را وارد کنید:")
    bot.register_next_step_handler(msg, lambda m: process_admin_reject_file(m, pending_id, call))

def process_admin_reject_file(message, pending_id, original_call):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    reason = message.text
    
    with get_db() as conn:
        pending = conn.execute('SELECT user_id FROM pending_files WHERE id = ?', (pending_id,)).fetchone()
        if pending:
            conn.execute('UPDATE pending_files SET status = "rejected", reviewed_at = ?, review_note = ? WHERE id = ?',
                        (datetime.now().isoformat(), reason, pending_id))
            conn.commit()
            
            try:
                bot.send_message(
                    pending['user_id'],
                    f"❌ متاسفانه فایل ربات شما تایید نشد.\n\n"
                    f"دلیل: {reason}\n\n"
                    f"لطفاً فایل را اصلاح کرده و دوباره ارسال کنید."
                )
            except:
                pass
    
    bot.reply_to(message, f"✅ فایل رد شد")
    try:
        bot.delete_message(original_call.message.chat.id, original_call.message.message_id)
    except:
        pass

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
        text = f"📸 **فیش #{r['id']}**\n"
        text += f"👤 کاربر: {r['user_id']}\n"
        text += f"💰 مبلغ: {r['amount']:,} تومان\n"
        text += f"🆔 کد اشتراک: {r['subscription_code']}\n"
        text += f"🆔 کد پرداخت: {r['payment_code']}\n"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید", callback_data=f"admin_approve_payment_{r['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"admin_reject_payment_{r['id']}")
        )
        
        if os.path.exists(r['receipt_path']):
            with open(r['receipt_path'], 'rb') as f:
                bot.send_photo(call.message.chat.id, f, caption=text, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_approve_payment_'))
def admin_approve_payment(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    receipt_id = int(call.data.replace('admin_approve_payment_', ''))
    
    with get_db() as conn:
        receipt = conn.execute('SELECT * FROM receipts WHERE id = ?', (receipt_id,)).fetchone()
        if receipt:
            if activate_subscription(receipt['subscription_id'], receipt['user_id'], receipt['amount']):
                conn.execute('UPDATE receipts SET status = "approved", reviewed_at = ?, reviewed_by = ? WHERE id = ?',
                            (datetime.now().isoformat(), call.from_user.id, receipt_id))
                conn.commit()
                
                bot.answer_callback_query(call.id, "✅ پرداخت تایید شد")
                bot.send_message(
                    receipt['user_id'],
                    f"✅ پرداخت شما تایید شد!\n"
                    f"اشتراک شما فعال شد.\n\n"
                    f"📤 حالا می‌توانید از منوی «ارسال فایل ربات» استفاده کنید."
                )
            else:
                bot.answer_callback_query(call.id, "❌ خطا در فعال‌سازی")
        
        bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_reject_payment_'))
def admin_reject_payment(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    receipt_id = int(call.data.replace('admin_reject_payment_', ''))
    
    with get_db() as conn:
        receipt = conn.execute('SELECT * FROM receipts WHERE id = ?', (receipt_id,)).fetchone()
        if receipt:
            conn.execute('UPDATE receipts SET status = "rejected", reviewed_at = ?, reviewed_by = ? WHERE id = ?',
                        (datetime.now().isoformat(), call.from_user.id, receipt_id))
            conn.execute('DELETE FROM subscriptions WHERE id = ?', (receipt['subscription_id'],))
            conn.commit()
            
            try:
                bot.send_message(
                    receipt['user_id'],
                    f"❌ متاسفانه پرداخت شما تایید نشد.\n"
                    f"لطفاً با پشتیبانی تماس بگیرید."
                )
            except:
                pass
            
            bot.answer_callback_query(call.id, "❌ پرداخت رد شد")
            bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_manual_sub")
def admin_manual_sub(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "💰 آیدی کاربر را برای تایید دستی اشتراک وارد کنید:")
    bot.register_next_step_handler(msg, process_admin_manual_sub)

def process_admin_manual_sub(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        user_id = int(message.text.strip())
        
        sub_id, sub_code, expires_at = create_subscription(user_id, config.price)
        if sub_id:
            if activate_subscription(sub_id, user_id, config.price):
                bot.reply_to(message, f"✅ اشتراک کاربر {user_id} فعال شد")
                try:
                    bot.send_message(
                        user_id,
                        f"✅ اشتراک شما به صورت دستی فعال شد!\n\n"
                        f"📤 حالا می‌توانید از منوی «ارسال فایل ربات» استفاده کنید."
                    )
                except:
                    pass
            else:
                bot.reply_to(message, "❌ خطا در فعال‌سازی")
        else:
            bot.reply_to(message, "❌ خطا در ایجاد اشتراک")
    except ValueError:
        bot.reply_to(message, "❌ آیدی نامعتبر")

@bot.callback_query_handler(func=lambda call: call.data == "admin_logs")
def admin_logs(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        logs = conn.execute('''
            SELECT * FROM activity_logs ORDER BY created_at DESC LIMIT 30
        ''').fetchall()
    
    if not logs:
        bot.send_message(call.message.chat.id, "📋 لاگی وجود ندارد")
        return
    
    text = "📋 **۳۰ فعالیت آخر**\n\n"
    for log in logs:
        text += f"👤 {log['user_id']} - {log['action']}\n"
        text += f"   📅 {log['created_at'][:16]}\n"
        if log['details']:
            text += f"   📝 {log['details'][:50]}\n"
        text += "\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_backup")
def admin_backup(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    try:
        backup_file = os.path.join(BACKUP_DIR, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        shutil.copy2(DB_PATH, backup_file)
        
        bot.send_message(
            call.message.chat.id,
            f"✅ پشتیبان تهیه شد!\n"
            f"📁 فایل: {backup_file}"
        )
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ خطا: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call):
    user_id = call.from_user.id
    markup = get_admin_menu() if user_id in ADMIN_IDS else get_main_menu(user_id)
    
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    bot.send_message(call.message.chat.id, "🚀 منوی اصلی:", reply_markup=markup)

# ==================== نمایش روزهای باقی‌مانده ====================

@bot.message_handler(func=lambda m: m.text and m.text.startswith('📅') and 'روز' in m.text)
def show_remaining_days(message):
    user_id = message.from_user.id
    days_left = get_subscription_days_left(user_id)
    
    if days_left > 0:
        bot.send_message(
            message.chat.id,
            f"📅 **اشتراک شما**\n\n"
            f"✅ اشتراک فعال دارید!\n"
            f"⏰ روزهای باقی‌مانده: **{days_left} روز**\n\n"
            f"⚠️ {days_left - 3} روز دیگر تمدید کنید تا ربات شما قطع نشود.",
            parse_mode="Markdown"
        )
    else:
        bot.send_message(
            message.chat.id,
            f"❌ شما اشتراک فعال ندارید!\n"
            f"از منوی «خرید اشتراک» استفاده کنید."
        )

# ==================== چک کننده انقضای اشتراک ====================

def check_expired_subscriptions():
    """بررسی خودکار اشتراک‌های منقضی شده"""
    while True:
        try:
            with get_db() as conn:
                # پیدا کردن اشتراک‌های در حال انقضا (۳ روز مونده)
                expire_soon = conn.execute('''
                    SELECT user_id, subscription_expire FROM users 
                    WHERE active_subscription = 1 
                    AND julianday(subscription_expire) - julianday('now') BETWEEN 0 AND 3
                ''').fetchall()
                
                for user in expire_soon:
                    days_left = (datetime.fromisoformat(user['subscription_expire']) - datetime.now()).days
                    if days_left <= 3 and days_left > 0:
                        try:
                            bot.send_message(
                                user['user_id'],
                                f"⚠️ **اخطار انقضای اشتراک**\n\n"
                                f"اشتراک شما {days_left} روز دیگر به پایان می‌رسد.\n"
                                f"لطفاً برای ادامه فعالیت ربات خود، اشتراک را تمدید کنید.\n\n"
                                f"💰 مبلغ تمدید: {config.price:,} تومان\n"
                                f"از منوی «خرید اشتراک» استفاده کنید.",
                                parse_mode="Markdown"
                            )
                        except:
                            pass
                
                # غیرفعال کردن اشتراک‌های منقضی شده
                expired = conn.execute('''
                    SELECT user_id, subscription_expire FROM users 
                    WHERE active_subscription = 1 
                    AND julianday(subscription_expire) - julianday('now') < 0
                ''').fetchall()
                
                for user in expired:
                    conn.execute('UPDATE users SET active_subscription = 0 WHERE user_id = ?', (user['user_id'],))
                    conn.execute('UPDATE bots SET status = "expired" WHERE user_id = ?', (user['user_id'],))
                    
                    # توقف ربات‌های منقضی شده
                    bots = conn.execute('SELECT id, server_id FROM bots WHERE user_id = ?', (user['user_id'],)).fetchall()
                    for bot in bots:
                        if bot['server_id']:
                            server = conn.execute('SELECT * FROM servers WHERE id = ?', (bot['server_id'],)).fetchone()
                            if server:
                                server_manager.stop_bot_on_server(dict(server), bot['id'])
                    
                    try:
                        bot.send_message(
                            user['user_id'],
                            f"❌ **اشتراک شما منقضی شد!**\n\n"
                            f"ربات شما متوقف شد.\n"
                            f"برای ادامه فعالیت، لطفاً اشتراک جدید خریداری کنید.\n\n"
                            f"💰 مبلغ اشتراک: {config.price:,} تومان\n"
                            f"از منوی «خرید اشتراک» استفاده کنید.",
                            parse_mode="Markdown"
                        )
                    except:
                        pass
                
                conn.commit()
            
            time.sleep(3600)  # هر ۱ ساعت یکبار بررسی کن
        except Exception as e:
            logger.error(f"خطا در بررسی انقضا: {e}")
            time.sleep(3600)

# ==================== اجرا ====================

if __name__ == "__main__":
    print("=" * 70)
    print("🚀 ربات مادر نهایی - نسخه 10.0 فوق پیشرفته")
    print("=" * 70)
    print(f"✅ دیتابیس: بهینه شده برای میلیون‌ها کاربر")
    print(f"✅ هوش مصنوعی بررسی کد: فعال")
    print(f"✅ مدیریت سرور: فعال")
    print(f"✅ سیستم رفرال: فعال (۱۰٪ پاداش)")
    print(f"✅ کیف پول و برداشت: فعال")
    print(f"✅ ادمین‌ها: {ADMIN_IDS}")
    print(f"✅ قیمت فعلی: {config.price:,} تومان")
    print(f"✅ مدت اشتراک: {config.subscription_days} روز")
    print("=" * 70)
    print("🟢 ربات در حال اجراست...")
    print("=" * 70)
    
    # شروع ترد بررسی انقضای اشتراک
    expiry_thread = threading.Thread(target=check_expired_subscriptions, daemon=True)
    expiry_thread.start()
    
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=30)
        except Exception as e:
            logger.error(f"خطا در اجرا: {e}")
            time.sleep(5)