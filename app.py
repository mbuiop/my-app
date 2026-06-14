#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ربات مادر نهایی نسخه 11.0 - با بررسی امنیتی واقعی و توزیع بار روی سرورها
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
import paramiko
import socket
import ast

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

# ==================== کتابخانه‌های مجاز (امن) ====================
SAFE_LIBRARIES = {
    'requests', 'aiohttp', 'httpx', 'flask', 'fastapi', 'quart', 'sanic',
    'pyTelegramBotAPI', 'aiogram', 'python-telegram-bot', 'telethon',
    'sqlalchemy', 'asyncpg', 'redis', 'motor',
    'numpy', 'pandas', 'beautifulsoup4', 'pillow', 'matplotlib',
    'jdatetime', 'persiantools', 'cryptography', 'loguru', 'tqdm',
    'python-dotenv', 'click', 'colorama', 'rich', 'yt-dlp', 'pydub',
    'opencv-python', 'scikit-learn', 'transformers', 'langchain'
}

# ==================== تنظیمات پیش‌فرض ====================
class Config:
    def __init__(self):
        self.welcome_text = """🚀 به ربات سازنده ربات حرفه‌ای خوش آمدید!
        
👤 کاربر عزیز، شما می‌توانید با خرید اشتراک، ربات تلگرامی خود را بسازید.

📌 نحوه کار:
1️⃣ خرید اشتراک
2️⃣ ارسال فایل ربات برای بررسی امنیتی هوشمند
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

# ==================== لاگینگ ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(os.path.join(LOGS_DIR, 'mother_bot.log'), maxBytes=10485760, backupCount=30),
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
    conn.execute("PRAGMA cache_size=-262144")
    conn.execute("PRAGMA synchronous=NORMAL")
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
    conn.execute('CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)')
    
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
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            details TEXT,
            created_at TIMESTAMP
        )
    ''')
    
    # ایندکس‌ها
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_referral ON users(referral_code)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_bots_user ON bots(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_bots_server ON bots(server_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_servers_status ON servers(status)")
    
    conn.commit()

config.load_from_db()

# ==================== سیستم بررسی امنیتی واقعی ====================
class RealSecurityScanner:
    """بررسی امنیتی واقعی و دقیق کد"""
    
    # الگوهای خطرناک (قطعاً مخرب)
    CRITICAL_PATTERNS = [
        (r'os\.system\s*\(', "اجرای دستور سیستم", 100, True),
        (r'subprocess\.(Popen|call|run|check_output)', "اجرای فرآیند", 100, True),
        (r'eval\s*\(', "اجرای کد پویا", 100, True),
        (r'exec\s*\(', "اجرای کد پویا", 100, True),
        (r'__import__\s*\(', "import پویا", 90, True),
        (r'compile\s*\(', "کامپایل کد", 90, True),
        (r'globals\(\)\.update', "تغییر متغیرهای سراسری", 85, True),
        (r'locals\(\)\.update', "تغییر متغیرهای محلی", 85, True),
        (r'__builtins__\s*\[', "دسترسی به builtins", 80, True),
        (r'open\s*\([^)]*[\'"]w', "نوشتن در فایل (حالت نوشتن)", 70, True),
    ]
    
    # الگوهای پرخطر
    HIGH_RISK_PATTERNS = [
        (r'socket\.', "اتصال سوکت", 50, False),
        (r'requests\.(get|post|put|delete|patch)', "درخواست HTTP خارجی", 40, False),
        (r'base64\.b64decode', "رمزگشایی base64", 35, False),
        (r'pickle\.loads?', "دسریالایز کردن", 60, False),
        (r'executemany|executescript', "اجرای چندگانه SQL", 30, False),
        (r'urllib\.request', "درخواست URL", 30, False),
        (r'ftp\.', "اتصال FTP", 45, False),
        (r'telnet\.', "اتصال Telnet", 45, False),
    ]
    
    # الگوهای متوسط
    MEDIUM_RISK_PATTERNS = [
        (r'getattr\s*\(', "دسترسی داینامیک", 25, False),
        (r'setattr\s*\(', "تنظیم داینامیک", 25, False),
        (r'delattr\s*\(', "حذف داینامیک", 25, False),
        (r'__getitem__', "دسترسی داینامیک به آیتم", 15, False),
        (r'__setitem__', "تنظیم داینامیک آیتم", 15, False),
    ]
    
    def __init__(self):
        self.scan_history = {}
    
    def deep_scan(self, code, file_name=""):
        """اسکن عمیق و واقعی کد"""
        result = {
            'score': 100,
            'is_safe': True,
            'critical_issues': [],
            'high_risk_issues': [],
            'medium_risk_issues': [],
            'warnings': [],
            'token_found': False,
            'token_valid': False,
            'bot_structure': False,
            'imported_libs': [],
            'suspicious_imports': [],
            'estimated_lines': len(code.split('\n')),
            'file_hash': hashlib.sha256(code.encode()).hexdigest()
        }
        
        # بررسی importهای کد
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        lib = alias.name.split('.')[0]
                        result['imported_libs'].append(lib)
                        if lib not in SAFE_LIBRARIES and not lib.startswith('telebot'):
                            result['suspicious_imports'].append(lib)
                            result['warnings'].append(f"⚠️ کتابخانه غیرمجاز: {lib}")
                            result['score'] -= 15
                elif isinstance(node, ast.ImportFrom):
                    lib = node.module.split('.')[0] if node.module else ""
                    if lib and lib not in SAFE_LIBRARIES and not lib.startswith('telebot'):
                        result['suspicious_imports'].append(lib)
                        result['warnings'].append(f"⚠️ کتابخانه غیرمجاز: {lib}")
                        result['score'] -= 15
        except:
            pass
        
        # بررسی الگوهای بحرانی
        for pattern, desc, penalty, is_critical in self.CRITICAL_PATTERNS:
            matches = re.findall(pattern, code, re.IGNORECASE)
            if matches:
                issue = {'pattern': desc, 'count': len(matches), 'penalty': penalty}
                if is_critical:
                    result['critical_issues'].append(issue)
                    result['score'] -= penalty
                    result['warnings'].append(f"🚨 بحرانی: {desc} (تعداد: {len(matches)})")
                else:
                    result['high_risk_issues'].append(issue)
                    result['score'] -= penalty
                    result['warnings'].append(f"⚠️ خطرناک: {desc} (تعداد: {len(matches)})")
        
        # بررسی الگوهای پرخطر
        for pattern, desc, penalty, _ in self.HIGH_RISK_PATTERNS:
            matches = re.findall(pattern, code, re.IGNORECASE)
            if matches:
                result['high_risk_issues'].append({'pattern': desc, 'count': len(matches), 'penalty': penalty})
                result['score'] -= penalty
                result['warnings'].append(f"⚠️ پرخطر: {desc} (تعداد: {len(matches)})")
        
        # بررسی الگوهای متوسط
        for pattern, desc, penalty, _ in self.MEDIUM_RISK_PATTERNS:
            matches = re.findall(pattern, code, re.IGNORECASE)
            if matches:
                result['medium_risk_issues'].append({'pattern': desc, 'count': len(matches), 'penalty': penalty})
                result['score'] -= penalty // 2
                result['warnings'].append(f"⚠️ متوسط: {desc} (تعداد: {len(matches)})")
        
        # بررسی وجود توکن
        token_patterns = [
            r'[0-9]{8,10}:[A-Za-z0-9_-]{35}',
            r'token\s*=\s*["\']([^"\']+)["\']',
            r'TOKEN\s*=\s*["\']([^"\']+)["\']',
            r'API_TOKEN\s*=\s*["\']([^"\']+)["\']',
            r'BOT_TOKEN\s*=\s*["\']([^"\']+)["\']',
            r'bot\s*=\s*telebot\.TeleBot\(\s*["\']([^"\']+)["\']\s*\)',
        ]
        
        for pattern in token_patterns:
            match = re.search(pattern, code, re.IGNORECASE)
            if match:
                result['token_found'] = True
                token = match.group(1) if match.lastindex else match.group(0)
                result['token_valid'] = self.validate_token(token)
                if result['token_valid']:
                    result['score'] += 20
                else:
                    result['score'] -= 30
                    result['warnings'].append("❌ توکن نامعتبر است")
                break
        
        if not result['token_found']:
            result['score'] -= 40
            result['warnings'].append("❌ توکن در کد پیدا نشد")
        
        # بررسی ساختار ربات
        if 'telebot' in code or 'Bot(' in code or 'infinity_polling' in code or 'polling' in code:
            result['bot_structure'] = True
            result['score'] += 15
        
        # محدودیت حجم کد
        if result['estimated_lines'] > 5000:
            result['score'] -= 10
            result['warnings'].append("⚠️ حجم کد زیاد است (>5000 خط)")
        
        # امتیاز نهایی (بین 0 تا 100)
        result['score'] = max(0, min(100, result['score']))
        
        # تصمیم نهایی: کد امن است اگر:
        # 1. امتیاز >= 60
        # 2. مشکل بحرانی نداشته باشد
        # 3. توکن معتبر داشته باشد (یا حداقل پیدا شده باشد)
        result['is_safe'] = (
            result['score'] >= 60 and 
            len(result['critical_issues']) == 0 and
            result['token_found']
        )
        
        return result
    
    def validate_token(self, token):
        """اعتبارسنجی توکن تلگرام"""
        try:
            response = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def generate_report(self, scan_result):
        """گزارش کامل امنیتی"""
        report = f"📊 **گزارش بررسی امنیتی**\n\n"
        report += f"🛡️ **امتیاز نهایی:** {scan_result['score']}/100\n"
        report += f"📝 **تعداد خطوط:** {scan_result['estimated_lines']}\n"
        report += f"🔐 **توکن:** {'✅ یافت شد و معتبر' if scan_result.get('token_valid') else ('✅ یافت شد' if scan_result.get('token_found') else '❌ یافت نشد')}\n"
        report += f"🤖 **ساختار ربات:** {'✅ تشخیص داده شد' if scan_result.get('bot_structure') else '❌ تشخیص داده نشد'}\n\n"
        
        if scan_result.get('imported_libs'):
            report += f"📦 **کتابخانه‌های استفاده شده:**\n"
            for lib in scan_result['imported_libs'][:10]:
                report += f"• {lib}\n"
            if len(scan_result['imported_libs']) > 10:
                report += f"• و {len(scan_result['imported_libs'])-10} کتابخانه دیگر\n"
            report += "\n"
        
        if scan_result.get('suspicious_imports'):
            report += f"⚠️ **کتابخانه‌های غیرمجاز:**\n"
            for lib in scan_result['suspicious_imports'][:5]:
                report += f"• {lib}\n"
            report += "\n"
        
        if scan_result.get('critical_issues'):
            report += f"🚨 **مشکلات بحرانی (رد خودکار):**\n"
            for issue in scan_result['critical_issues']:
                report += f"• {issue['pattern']} (تعداد: {issue['count']})\n"
            report += "\n"
        
        if scan_result.get('high_risk_issues'):
            report += f"⚠️ **مشکلات پرخطر:**\n"
            for issue in scan_result['high_risk_issues'][:5]:
                report += f"• {issue['pattern']} (تعداد: {issue['count']})\n"
            report += "\n"
        
        if scan_result.get('warnings'):
            report += f"💡 **هشدارها:**\n"
            for warn in scan_result['warnings'][:5]:
                report += f"{warn}\n"
            report += "\n"
        
        if scan_result['is_safe']:
            report += f"✅ **نتیجه نهایی:** کد امن است و قابل اجرا می‌باشد."
            report += f"\n\n🔄 ربات شما در حال ساخت است..."
        else:
            if scan_result.get('critical_issues'):
                report += f"❌ **نتیجه نهایی:** کد حاوی موارد مخرب است و رد می‌شود."
            elif not scan_result.get('token_found'):
                report += f"❌ **نتیجه نهایی:** توکن ربات در کد پیدا نشد."
            else:
                report += f"❌ **نتیجه نهایی:** کد نیاز به بررسی دستی دارد."
        
        return report

security_scanner = RealSecurityScanner()

# ==================== سیستم مدیریت سرور ====================
class ServerManager:
    """مدیریت سرورها و توزیع بار"""
    
    def __init__(self):
        self.servers_cache = []
        self.last_load_time = 0
        self.cache_lock = threading.Lock()
    
    def get_available_servers(self):
        """دریافت لیست سرورهای فعال با بار کمتر"""
        with get_db() as conn:
            servers = conn.execute('''
                SELECT * FROM servers 
                WHERE status = 'active' AND current_load < max_load
                ORDER BY current_load ASC
            ''').fetchall()
            return [dict(s) for s in servers]
    
    def get_best_server(self):
        """بهترین سرور برای اجرای ربات جدید (کمترین بار)"""
        servers = self.get_available_servers()
        if not servers:
            return None
        return servers[0]  # مرتب شده بر اساس بار صعودی
    
    def add_server(self, name, ip, port, username, password):
        """اضافه کردن سرور جدید"""
        try:
            # تست اتصال
            if not self.test_connection(ip, port, username, password):
                return False, "❌ اتصال به سرور امکان‌پذیر نیست"
            
            with get_db() as conn:
                now = datetime.now().isoformat()
                conn.execute('''
                    INSERT INTO servers (name, ip, port, username, password, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (name, ip, port, username, password, now))
                conn.commit()
                
                server_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            
            # نصب کتابخانه‌های اولیه
            self.install_base_libraries(ip, port, username, password)
            
            return True, f"✅ سرور {name} با موفقیت اضافه شد (ID: {server_id})"
        except Exception as e:
            return False, f"❌ خطا: {str(e)}"
    
    def test_connection(self, ip, port, username, password):
        """تست اتصال به سرور"""
        try:
            # تست پینگ ساده
            response = os.system(f"ping -c 1 -W 2 {ip} > /dev/null 2>&1")
            
            # تست SSH
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(ip, port=port, username=username, password=password, timeout=10)
            client.close()
            return True
        except Exception as e:
            logger.error(f"خطا در تست اتصال: {e}")
            return False
    
    def install_base_libraries(self, ip, port, username, password):
        """نصب کتابخانه‌های ضروری روی سرور"""
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(ip, port=port, username=username, password=password, timeout=30)
            
            # نصب pip و کتابخانه‌های پایه
            commands = [
                'pip3 install --upgrade pip --quiet',
                'pip3 install pyTelegramBotAPI requests paramiko --quiet',
                'mkdir -p /home/ubuntu/bots /home/ubuntu/logs'
            ]
            
            for cmd in commands:
                stdin, stdout, stderr = client.exec_command(cmd)
                stdout.read()
            
            client.close()
            return True
        except Exception as e:
            logger.error(f"خطا در نصب کتابخانه‌ها: {e}")
            return False
    
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
            for lib in required_libs[:10]:
                lib_name = SAFE_LIBRARIES.intersection({lib})
                if lib_name:
                    stdin, stdout, stderr = client.exec_command(f'pip3 install {list(lib_name)[0]} --quiet')
                    stdout.read()
            
            # اجرا با screen
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
        """تشخیص کتابخانه‌های مورد نیاز"""
        imports = set()
        lines = code.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('import '):
                parts = line.split()
                if len(parts) > 1:
                    lib = parts[1].split('.')[0]
                    if lib not in ['os', 'sys', 'time', 'datetime', 'json', 're']:
                        imports.add(lib)
            elif line.startswith('from '):
                parts = line.split()
                if len(parts) > 1:
                    lib = parts[1].split('.')[0]
                    if lib not in ['os', 'sys', 'time', 'datetime', 'json', 're']:
                        imports.add(lib)
        
        return list(imports)

server_manager = ServerManager()

# ==================== توابع دیتابیس ====================

def generate_referral_code(user_id):
    return hashlib.md5(f"{user_id}_{time.time()}_{secrets.token_hex(4)}".encode()).hexdigest()[:10].upper()

def create_user(user_id, username, first_name, last_name, referred_by=None):
    try:
        with get_db() as conn:
            now = datetime.now().isoformat()
            referral_code = generate_referral_code(user_id)
            
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
            
            if referred_by:
                conn.execute('UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?', (referred_by,))
                conn.commit()
                
                try:
                    bot.send_message(
                        referred_by,
                        f"🎉 کاربر جدید با لینک رفرال شما ثبت نام کرد!\n👤 {first_name}\n🆔 {user_id}"
                    )
                except:
                    pass
            
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
                days_left = (expire - datetime.now()).days
                return max(0, days_left)
            return 0
    except:
        return 0

def create_subscription(user_id, amount):
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
    try:
        with get_db() as conn:
            sub = conn.execute('SELECT * FROM subscriptions WHERE id = ?', (subscription_id,)).fetchone()
            if not sub:
                return False
            
            expires_at = (datetime.now() + timedelta(days=config.subscription_days)).isoformat()
            
            conn.execute('UPDATE users SET active_subscription = 0 WHERE user_id = ?', (user_id,))
            conn.execute('''
                UPDATE users SET active_subscription = 1, subscription_expire = ?, subscription_id = ?
                WHERE user_id = ?
            ''', (expires_at, subscription_id, user_id))
            
            conn.execute('''
                UPDATE subscriptions SET status = 'active', paid_at = ?
                WHERE id = ?
            ''', (datetime.now().isoformat(), subscription_id))
            
            conn.execute('''
                INSERT INTO transactions (user_id, type, amount, description, created_at)
                VALUES (?, 'subscription', ?, 'خرید اشتراک', ?)
            ''', (user_id, amount, datetime.now().isoformat()))
            
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
                        f"🎁 پاداش رفرال شما واریز شد!\n👤 دوست شما {amount:,} تومان اشتراک خرید.\n💰 پاداش: {bonus:,} تومان"
                    )
                except:
                    pass
            
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"خطا در activate_subscription: {e}")
        return False

def get_user_balance(user_id):
    try:
        with get_db() as conn:
            user = conn.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,)).fetchone()
            return user['balance'] if user else 0
    except:
        return 0

def request_withdraw(user_id, amount, card_number):
    try:
        with get_db() as conn:
            user = conn.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,)).fetchone()
            if not user or user['balance'] < amount:
                return False, "موجودی ناکافی است"
            
            if amount < 2000000:
                return False, "حداقل مبلغ برداشت ۲,۰۰۰,۰۰۰ تومان است"
            
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
            
            for admin_id in ADMIN_IDS:
                try:
                    bot.send_message(
                        admin_id,
                        f"💰 درخواست برداشت جدید\n👤 کاربر: {user_id}\n💰 مبلغ: {amount:,} تومان\n💳 کارت: {card_number}"
                    )
                except:
                    pass
            
            return True, "درخواست برداشت ثبت شد"
    except Exception as e:
        return False, str(e)

def can_create_bot(user_id):
    try:
        with get_db() as conn:
            bots_count = conn.execute('SELECT COUNT(*) FROM bots WHERE user_id = ? AND status != "deleted"', (user_id,)).fetchone()[0]
            has_active = has_active_subscription(user_id)
            return has_active and bots_count == 0
    except:
        return False

def add_bot(user_id, subscription_id, server_id, bot_id, token, name, username, file_path, pid=None):
    try:
        with get_db() as conn:
            now = datetime.now().isoformat()
            expires_at = (datetime.now() + timedelta(days=config.subscription_days)).isoformat()
            
            conn.execute('''
                INSERT INTO bots (id, user_id, subscription_id, server_id, token, name, username, file_path, pid, status, created_at, last_active, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'running', ?, ?, ?)
            ''', (bot_id, user_id, subscription_id, server_id, token, name, username, file_path, pid, now, now, expires_at))
            
            conn.execute('UPDATE users SET total_bots = total_bots + 1, active_subscription = 0 WHERE user_id = ?', (user_id,))
            conn.commit()
            return True
    except:
        return False

def get_user_bots(user_id):
    try:
        with get_db() as conn:
            bots = conn.execute('SELECT * FROM bots WHERE user_id = ? AND status != "deleted" ORDER BY created_at DESC', (user_id,)).fetchall()
            return [dict(bot) for bot in bots]
    except:
        return []

def delete_bot(bot_id, user_id):
    try:
        with get_db() as conn:
            bot = conn.execute('SELECT * FROM bots WHERE id = ? AND user_id = ?', (bot_id, user_id)).fetchone()
            if not bot:
                return False
            
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
    try:
        with get_db() as conn:
            bot = conn.execute('SELECT * FROM bots WHERE id = ? AND user_id = ?', (bot_id, user_id)).fetchone()
            if not bot:
                return False, "ربات پیدا نشد"
            
            if bot['server_id']:
                server = conn.execute('SELECT * FROM servers WHERE id = ?', (bot['server_id'],)).fetchone()
                if server:
                    server_manager.stop_bot_on_server(dict(server), bot_id)
            
            with open(bot['file_path'], 'r', encoding='utf-8') as f:
                code = f.read()
            
            server = conn.execute('SELECT * FROM servers WHERE id = ?', (bot['server_id'],)).fetchone()
            if server:
                pid, error = server_manager.run_bot_on_server(dict(server), bot_id, code, bot['token'])
                if pid:
                    conn.execute('UPDATE bots SET status = "running", pid = ? WHERE id = ?', (pid, bot_id))
                    conn.commit()
                    return True, "ربات ریستارت شد"
                else:
                    return False, f"خطا: {error}"
            
            return False, "سرور پیدا نشد"
    except Exception as e:
        return False, str(e)

def save_pending_file(user_id, subscription_id, file_path, file_name, file_hash, security_score, security_report):
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
    try:
        with get_db() as conn:
            pending = conn.execute('''
                SELECT * FROM pending_files WHERE user_id = ? AND status = 'pending' ORDER BY submitted_at DESC LIMIT 1
            ''', (user_id,)).fetchone()
            return dict(pending) if pending else None
    except:
        return None

def log_activity(user_id, action, details=""):
    try:
        with get_db() as conn:
            conn.execute('INSERT INTO activity_logs (user_id, action, details, created_at) VALUES (?, ?, ?, ?)',
                        (user_id, action, details, datetime.now().isoformat()))
            conn.commit()
    except:
        pass

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
        with get_db() as conn:
            referrer = conn.execute('SELECT user_id FROM users WHERE referral_code = ?', (ref_code,)).fetchone()
            if referrer:
                referred_by = referrer['user_id']
    
    create_user(user_id, username, first_name, last_name, referred_by)
    log_activity(user_id, "start", "کاربر وارد شد")
    
    bot_username = bot.get_me().username
    welcome = config.welcome_text.format(bot_username)
    
    markup = get_main_menu(user_id)
    
    user = get_user(user_id)
    if user:
        referral_link = f"https://t.me/{bot_username}?start={user['referral_code']}"
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
            f"✅ شما اشتراک فعال دارید!\n📅 روزهای باقی‌مانده: {days_left} روز\n\n📤 لطفاً فایل ربات خود را ارسال کنید."
        )
        return
    
    sub_id, sub_code, expires_at = create_subscription(user_id, config.price)
    if not sub_id:
        bot.send_message(message.chat.id, "❌ خطا در ایجاد اشتراک")
        return
    
    text = f"""💰 خرید اشتراک

مبلغ: {config.price:,} تومان
شماره کارت: {config.card_number}
به نام: {config.card_holder}

🆔 کد اشتراک: `{sub_code}`

📌 مراحل:
1️⃣ مبلغ را واریز کنید
2️⃣ کد اشتراک را در رسید یادداشت کنید
3️⃣ تصویر فیش را ارسال کنید

⏰ مدت اشتراک: {config.subscription_days} روز
🎁 هر اشتراک = ۱ ربات
🎁 پاداش رفرال: ۱۰٪
"""
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# ==================== رسید واریزی ====================

@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    
    with get_db() as conn:
        pending_sub = conn.execute('''
            SELECT * FROM subscriptions WHERE user_id = ? AND status = 'pending' ORDER BY created_at DESC LIMIT 1
        ''', (user_id,)).fetchone()
    
    if not pending_sub:
        bot.reply_to(message, "❌ شما اشتراک در انتظار پرداختی ندارید.")
        return
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        payment_code = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:12].upper()
        receipt_path = os.path.join(RECEIPTS_DIR, f"{user_id}_{payment_code}.jpg")
        
        with open(receipt_path, 'wb') as f:
            f.write(downloaded_file)
        
        with get_db() as conn:
            conn.execute('''
                INSERT INTO receipts (user_id, subscription_id, amount, receipt_path, payment_code, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, pending_sub['id'], config.price, receipt_path, payment_code, datetime.now().isoformat()))
            conn.commit()
        
        bot.reply_to(message, f"✅ فیش دریافت شد\n💰 {config.price:,} تومان\n🆔 {payment_code}\n\n⏳ در حال بررسی...")
        
        # فعال‌سازی خودکار
        if activate_subscription(pending_sub['id'], user_id, config.price):
            bot.send_message(user_id, f"✅ اشتراک شما فعال شد!\n📅 مدت: {config.subscription_days} روز\n\n📤 فایل ربات خود را ارسال کنید.")
        
        for admin_id in ADMIN_IDS:
            try:
                bot.send_photo(admin_id, open(receipt_path, 'rb'), caption=f"📸 فیش جدید\n👤 {user_id}\n💰 {config.price:,} تومان")
            except:
                pass
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")

# ==================== ارسال فایل ربات با بررسی امنیتی واقعی ====================

@bot.message_handler(func=lambda m: m.text == '📤 ارسال فایل ربات')
def send_bot_file(message):
    user_id = message.from_user.id
    
    if not has_active_subscription(user_id):
        bot.send_message(message.chat.id, f"❌ اشتراک فعال ندارید!\n💰 {config.price:,} تومان\nاز منوی «خرید اشتراک» استفاده کنید.")
        return
    
    if not can_create_bot(user_id):
        bot.send_message(message.chat.id, "❌ قبلاً با این اشتراک ربات ساخته‌اید!\nبرای ربات دوم اشتراک جدید بخرید.")
        return
    
    pending = get_pending_file(user_id)
    if pending:
        bot.send_message(message.chat.id, "⏳ فایل قبلی در حال بررسی است.")
        return
    
    bot.send_message(message.chat.id, "📤 فایل `.py` خود را ارسال کنید.\n\n🔍 سیستم بررسی امنیتی فعال است.\n✅ پس از تأیید خودکار، ربات ساخته می‌شود.")

@bot.message_handler(content_types=['document'])
def handle_bot_file(message):
    user_id = message.from_user.id
    
    if not has_active_subscription(user_id):
        bot.reply_to(message, "❌ اشتراک فعال ندارید!")
        return
    
    if not can_create_bot(user_id):
        bot.reply_to(message, "❌ قبلاً ربات ساخته‌اید!")
        return
    
    pending = get_pending_file(user_id)
    if pending:
        bot.reply_to(message, "⏳ در انتظار بررسی فایل قبلی.")
        return
    
    file_name = message.document.file_name
    
    if not file_name.endswith('.py'):
        bot.reply_to(message, "❌ فقط فایل `.py` مجاز است!")
        return
    
    if message.document.file_size > 10 * 1024 * 1024:
        bot.reply_to(message, "❌ حجم فایل بیشتر از ۱۰ مگابایت است!")
        return
    
    status_msg = bot.reply_to(message, "🔍 در حال بررسی امنیتی فایل...")
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        file_path = os.path.join(PENDING_FILES_DIR, str(user_id), f"{int(time.time())}_{file_name}")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'wb') as f:
            f.write(downloaded_file)
        
        # خواندن و اسکن عمیق
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        scan_result = security_scanner.deep_scan(code, file_name)
        report = security_scanner.generate_report(scan_result)
        
        # ارسال گزارش به کاربر
        bot.edit_message_text(report, message.chat.id, status_msg.message_id, parse_mode="Markdown")
        
        # پیدا کردن اشتراک فعال
        with get_db() as conn:
            sub = conn.execute('SELECT id FROM subscriptions WHERE user_id = ? AND status = "active" ORDER BY paid_at DESC LIMIT 1', (user_id,)).fetchone()
        
        if not sub:
            bot.send_message(message.chat.id, "❌ اشتراک فعال پیدا نشد!")
            return
        
        file_hash = hashlib.sha256(open(file_path, 'rb').read()).hexdigest()
        save_pending_file(user_id, sub['id'], file_path, file_name, file_hash, scan_result['score'], report)
        
        # اگر کد امن است، خودکار ساخته شود
        if scan_result['is_safe'] and scan_result['score'] >= 70:
            bot.send_message(message.chat.id, "✅ فایل تأیید شد! در حال ساخت ربات...")
            
            # ساخت ربات
            result = build_bot_from_pending(user_id, sub['id'], file_path, code, scan_result)
            
            if result['success']:
                bot.send_message(
                    message.chat.id,
                    f"✅ ربات شما ساخته شد! 🎉\n\n"
                    f"🤖 نام: {result['name']}\n"
                    f"🔗 https://t.me/{result['username']}\n"
                    f"🆔 `{result['bot_id']}`\n\n"
                    f"📅 {config.subscription_days} روز اعتبار دارد.",
                    parse_mode="Markdown"
                )
            else:
                bot.send_message(message.chat.id, f"❌ خطا در ساخت: {result['error']}\nلطفاً با پشتیبانی تماس بگیرید.")
        else:
            bot.send_message(
                message.chat.id,
                "⚠️ فایل شما نیاز به بررسی دستی دارد.\nبه زودی نتیجه اعلام می‌شود."
            )
            
            for admin_id in ADMIN_IDS:
                try:
                    with open(file_path, 'rb') as f:
                        bot.send_document(
                            admin_id, f,
                            caption=f"📥 فایل جدید\n👤 {user_id}\n📄 {file_name}\n🛡️ امتیاز: {scan_result['score']}/100"
                        )
                except:
                    pass
        
        log_activity(user_id, "upload_bot_file", f"{file_name} - امتیاز: {scan_result['score']}")
        
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)}", message.chat.id, status_msg.message_id)

def build_bot_from_pending(user_id, subscription_id, file_path, code, scan_result):
    """ساخت ربات - فقط روی سرورهای اضافه شده"""
    result = {'success': False, 'error': None, 'name': None, 'username': None, 'bot_id': None}
    
    try:
        # استخراج توکن
        token = None
        token_patterns = [
            r'[0-9]{8,10}:[A-Za-z0-9_-]{35}',
            r'token\s*=\s*["\']([^"\']+)["\']',
            r'TOKEN\s*=\s*["\']([^"\']+)["\']',
            r'BOT_TOKEN\s*=\s*["\']([^"\']+)["\']',
        ]
        
        for pattern in token_patterns:
            match = re.search(pattern, code, re.IGNORECASE)
            if match:
                token = match.group(1) if match.lastindex else match.group(0)
                break
        
        if not token:
            result['error'] = "توکن پیدا نشد"
            return result
        
        # بررسی توکن
        response = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
        if response.status_code != 200:
            result['error'] = "توکن نامعتبر"
            return result
        
        bot_info = response.json()['result']
        bot_name = bot_info['first_name']
        bot_username = bot_info['username']
        
        # گرفتن بهترین سرور (کمترین بار)
        server = server_manager.get_best_server()
        
        if not server:
            result['error'] = "هیچ سرور فعالی موجود نیست. لطفاً ابتدا در پنل ادمین سرور اضافه کنید."
            return result
        
        # اجرا روی سرور
        bot_id = hashlib.md5(f"{user_id}_{token}_{time.time()}".encode()).hexdigest()[:12]
        pid, error = server_manager.run_bot_on_server(server, bot_id, code, token)
        
        if not pid:
            result['error'] = error or "خطا در اجرا"
            return result
        
        # ذخیره در دیتابیس
        add_bot(user_id, subscription_id, server['id'], bot_id, token, bot_name, bot_username, file_path, pid)
        
        # به‌روزرسانی وضعیت pending file
        with get_db() as conn:
            conn.execute('UPDATE pending_files SET status = "approved", reviewed_at = ? WHERE file_path = ?', 
                        (datetime.now().isoformat(), file_path))
            conn.commit()
        
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

# ==================== ربات‌های من ====================

@bot.message_handler(func=lambda m: m.text == '🤖 ربات‌های من')
def my_bots(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما رباتی ندارید!")
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
        
        text = f"{status_emoji} **{b['name']}**\n🔗 https://t.me/{b['username']}\n🆔 `{b['id']}`\n📊 {status_text}\n📅 {b['created_at'][:10]}"
        
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

# ==================== کیف پول و رفرال ====================

@bot.message_handler(func=lambda m: m.text == '💰 کیف پول و رفرال')
def wallet_ref(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    balance = get_user_balance(user_id)
    bot_username = bot.get_me().username
    
    if not user:
        bot.send_message(message.chat.id, "❌ /start را بزنید")
        return
    
    referral_link = f"https://t.me/{bot_username}?start={user['referral_code']}"
    
    text = f"💰 **کیف پول و رفرال**\n\n"
    text += f"👤 {user['first_name']}\n🆔 {user_id}\n\n"
    text += f"💳 موجودی: {balance:,} تومان\n"
    text += f"💰 کل درآمد: {user['total_earned']:,} تومان\n\n"
    text += f"🎁 کد رفرال: `{user['referral_code']}`\n"
    text += f"🔗 لینک: {referral_link}\n\n"
    text += f"📊 دعوت‌ها: {user['referral_count']}\n"
    text += f"🎁 پاداش هر خرید: ۱۰٪\n\n"
    
    if balance >= 2000000:
        text += f"✅ می‌توانید برداشت کنید.\n"
    else:
        text += f"⚠️ حداقل برداشت ۲,۰۰۰,۰۰۰ تومان\n"
    
    markup = types.InlineKeyboardMarkup()
    if balance >= 2000000:
        markup.add(types.InlineKeyboardButton("🏧 برداشت", callback_data="request_withdraw"))
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "request_withdraw")
def request_withdraw_callback(call):
    user_id = call.from_user.id
    balance = get_user_balance(user_id)
    
    if balance < 2000000:
        bot.answer_callback_query(call.id, "موجودی کافی نیست")
        return
    
    msg = bot.send_message(call.message.chat.id, "💳 شماره کارت خود را وارد کنید:")
    bot.register_next_step_handler(msg, process_withdraw_card)

def process_withdraw_card(message):
    user_id = message.from_user.id
    card_number = message.text.strip()
    
    if not card_number.isdigit() or len(card_number) < 16:
        bot.reply_to(message, "❌ شماره کارت نامعتبر")
        return
    
    balance = get_user_balance(user_id)
    success, msg = request_withdraw(user_id, balance, card_number)
    bot.reply_to(message, msg)

# ==================== دکمه‌های ربات ====================

@bot.callback_query_handler(func=lambda call: call.data.startswith('stop_bot_'))
def stop_user_bot(call):
    bot_id = call.data.replace('stop_bot_', '')
    user_id = call.from_user.id
    
    with get_db() as conn:
        bot_info = conn.execute('SELECT * FROM bots WHERE id = ? AND user_id = ?', (bot_id, user_id)).fetchone()
        if bot_info and bot_info['server_id']:
            server = conn.execute('SELECT * FROM servers WHERE id = ?', (bot_info['server_id'],)).fetchone()
            if server:
                server_manager.stop_bot_on_server(dict(server), bot_id)
                conn.execute('UPDATE bots SET status = "stopped" WHERE id = ?', (bot_id,))
                conn.commit()
                bot.answer_callback_query(call.id, "✅ ربات متوقف شد")
                bot.edit_message_text("✅ ربات متوقف شد.", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('start_bot_'))
def start_user_bot(call):
    bot_id = call.data.replace('start_bot_', '')
    user_id = call.from_user.id
    
    with get_db() as conn:
        bot_info = conn.execute('SELECT * FROM bots WHERE id = ? AND user_id = ?', (bot_id, user_id)).fetchone()
        if not bot_info:
            bot.answer_callback_query(call.id, "ربات پیدا نشد")
            return
        
        server = conn.execute('SELECT * FROM servers WHERE id = ?', (bot_info['server_id'],)).fetchone()
        if not server:
            bot.answer_callback_query(call.id, "سرور پیدا نشد")
            return
        
        with open(bot_info['file_path'], 'r', encoding='utf-8') as f:
            code = f.read()
        
        pid, error = server_manager.run_bot_on_server(dict(server), bot_id, code, bot_info['token'])
        if pid:
            conn.execute('UPDATE bots SET status = "running", pid = ? WHERE id = ?', (pid, bot_id))
            conn.commit()
            bot.answer_callback_query(call.id, "✅ ربات اجرا شد")
            bot.edit_message_text("✅ ربات اجرا شد.", call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, f"❌ خطا")

@bot.callback_query_handler(func=lambda call: call.data.startswith('restart_bot_'))
def restart_user_bot(call):
    bot_id = call.data.replace('restart_bot_', '')
    user_id = call.from_user.id
    success, msg = restart_bot(bot_id, user_id)
    bot.answer_callback_query(call.id, msg)

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_bot_'))
def delete_user_bot(call):
    bot_id = call.data.replace('delete_bot_', '')
    user_id = call.from_user.id
    if delete_bot(bot_id, user_id):
        bot.answer_callback_query(call.id, "✅ ربات حذف شد")
        bot.edit_message_text("🗑 ربات حذف شد.", call.message.chat.id, call.message.message_id)

# ==================== راهنما و پشتیبانی ====================

@bot.message_handler(func=lambda m: m.text == '📚 راهنما')
def guide(message):
    bot_username = bot.get_me().username
    text = config.guide_text.format(config.price, config.card_number, config.card_holder, bot_username)
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == '📞 پشتیبانی')
def support(message):
    bot.send_message(message.chat.id, "📞 @shahraghee13")

@bot.message_handler(func=lambda m: m.text and m.text.startswith('📅') and 'روز' in m.text)
def show_days(message):
    days_left = get_subscription_days_left(message.from_user.id)
    if days_left > 0:
        bot.send_message(message.chat.id, f"📅 {days_left} روز باقی‌مانده")
    else:
        bot.send_message(message.chat.id, "❌ اشتراک فعال ندارید")

# ==================== پنل ادمین ====================

@bot.message_handler(func=lambda m: m.text == '👑 پنل ادمین')
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ دسترسی ندارید!")
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
        types.InlineKeyboardButton("➕ سرور جدید", callback_data="admin_add_server"),
        types.InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings"),
        types.InlineKeyboardButton("🎁 تایید دستی", callback_data="admin_manual_sub"),
        types.InlineKeyboardButton("🗑 حذف کاربر", callback_data="admin_delete_user"),
        types.InlineKeyboardButton("🔄 ریستارت ربات", callback_data="admin_restart_bot"),
        types.InlineKeyboardButton("📋 لاگ", callback_data="admin_logs"),
        types.InlineKeyboardButton("💾 پشتیبان", callback_data="admin_backup")
    )
    
    with get_db() as conn:
        pending_payments = conn.execute('SELECT COUNT(*) FROM receipts WHERE status = "pending"').fetchone()[0]
        pending_files = conn.execute('SELECT COUNT(*) FROM pending_files WHERE status = "pending"').fetchone()[0]
        active_servers = conn.execute('SELECT COUNT(*) FROM servers WHERE status = "active"').fetchone()[0]
        total_load = conn.execute('SELECT SUM(current_load) FROM servers').fetchone()[0]
        max_load = conn.execute('SELECT SUM(max_load) FROM servers').fetchone()[0]
    
    text = f"👑 **پنل مدیریت**\n\n"
    text += f"📸 فیش در انتظار: {pending_payments}\n"
    text += f"📥 فایل در انتظار: {pending_files}\n"
    text += f"🖥️ سرورهای فعال: {active_servers}\n"
    text += f"📊 بار کل: {total_load}/{max_load}\n"
    
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
        types.InlineKeyboardButton("💰 قیمت", callback_data="set_price"),
        types.InlineKeyboardButton("💳 شماره کارت", callback_data="set_card"),
        types.InlineKeyboardButton("👤 صاحب کارت", callback_data="set_holder"),
        types.InlineKeyboardButton("📚 متن راهنما", callback_data="set_guide"),
        types.InlineKeyboardButton("⏰ مدت اشتراک", callback_data="set_duration"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    bot.edit_message_text(
        f"⚙️ **تنظیمات**\n\n💰 {config.price:,} تومان\n💳 {config.card_number}\n👤 {config.card_holder}\n⏰ {config.subscription_days} روز",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "set_welcome")
def set_welcome(call):
    msg = bot.send_message(call.message.chat.id, "📝 متن جدید خوش‌آمدگویی:")
    bot.register_next_step_handler(msg, lambda m: set_config_value(m, 'welcome_text'))

@bot.callback_query_handler(func=lambda call: call.data == "set_price")
def set_price(call):
    msg = bot.send_message(call.message.chat.id, f"💰 قیمت جدید (فعلی: {config.price:,}):")
    bot.register_next_step_handler(msg, lambda m: set_config_value(m, 'price', int))

@bot.callback_query_handler(func=lambda call: call.data == "set_card")
def set_card(call):
    msg = bot.send_message(call.message.chat.id, f"💳 شماره کارت جدید (فعلی: {config.card_number}):")
    bot.register_next_step_handler(msg, lambda m: set_config_value(m, 'card_number'))

@bot.callback_query_handler(func=lambda call: call.data == "set_holder")
def set_holder(call):
    msg = bot.send_message(call.message.chat.id, f"👤 نام صاحب کارت جدید (فعلی: {config.card_holder}):")
    bot.register_next_step_handler(msg, lambda m: set_config_value(m, 'card_holder'))

@bot.callback_query_handler(func=lambda call: call.data == "set_guide")
def set_guide(call):
    msg = bot.send_message(call.message.chat.id, "📚 متن جدید راهنما:")
    bot.register_next_step_handler(msg, lambda m: set_config_value(m, 'guide_text'))

@bot.callback_query_handler(func=lambda call: call.data == "set_duration")
def set_duration(call):
    msg = bot.send_message(call.message.chat.id, f"⏰ مدت اشتراک به روز (فعلی: {config.subscription_days}):")
    bot.register_next_step_handler(msg, lambda m: set_config_value(m, 'subscription_days', int))

def set_config_value(message, key, cast=None):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        value = cast(message.text) if cast else message.text
        setattr(config, key, value)
        config.save_to_db()
        bot.reply_to(message, f"✅ {key} تغییر کرد!")
    except:
        bot.reply_to(message, "❌ خطا")

# ==================== مدیریت سرورها ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_add_server")
def admin_add_server(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, 
        "➕ **افزودن سرور جدید**\n\n"
        "اطلاعات را به صورت زیر وارد کنید:\n\n"
        "`نام\nIP\nپورت\nیوزرنیم\nرمز`\n\n"
        "مثال:\n"
        "`Server1\n192.168.1.100\n22\nroot\npassword123`")
    
    bot.register_next_step_handler(msg, process_add_server)

def process_add_server(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    lines = message.text.strip().split('\n')
    if len(lines) < 5:
        bot.reply_to(message, "❌ فرمت صحیح نیست. ۵ خط اطلاعات وارد کنید.")
        return
    
    name = lines[0].strip()
    ip = lines[1].strip()
    try:
        port = int(lines[2].strip())
    except:
        port = 22
    username = lines[3].strip()
    password = lines[4].strip()
    
    status_msg = bot.reply_to(message, "🔄 در حال بررسی سرور...")
    
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
        bot.send_message(call.message.chat.id, "🖥️ هیچ سروری ثبت نشده است.\nاز دکمه «➕ سرور جدید» استفاده کنید.")
        return
    
    text = "🖥️ **سرورها**\n\n"
    for s in servers:
        text += f"🔹 **{s['name']}**\n"
        text += f"   📍 {s['ip']}:{s['port']}\n"
        text += f"   📊 {s['current_load']}/{s['max_load']}\n"
        text += f"   ✅ {s['status']}\n\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

# ==================== مدیریت فیش‌ها ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_receipts")
def admin_receipts(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    with get_db() as conn:
        receipts = conn.execute('SELECT * FROM receipts WHERE status = "pending" ORDER BY created_at DESC LIMIT 20').fetchall()
    
    if not receipts:
        bot.send_message(call.message.chat.id, "📸 فیشی وجود ندارد")
        return
    
    for r in receipts:
        text = f"📸 #{r['id']}\n👤 {r['user_id']}\n💰 {r['amount']:,} تومان"
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_payment_{r['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"reject_payment_{r['id']}")
        )
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
            bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_payment_'))
def reject_payment(call):
    receipt_id = int(call.data.replace('reject_payment_', ''))
    with get_db() as conn:
        conn.execute('UPDATE receipts SET status = "rejected" WHERE id = ?', (receipt_id,))
        conn.commit()
        bot.answer_callback_query(call.id, "❌ رد شد")
        bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== مدیریت فایل‌ها ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_pending_files")
def admin_pending_files(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    with get_db() as conn:
        pending = conn.execute('SELECT * FROM pending_files WHERE status = "pending" ORDER BY submitted_at DESC').fetchall()
    
    if not pending:
        bot.send_message(call.message.chat.id, "📥 فایلی وجود ندارد")
        return
    
    for p in pending:
        text = f"📥 #{p['id']}\n👤 {p['user_id']}\n📄 {p['file_name']}\n🛡️ {p['security_score']}/100"
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_file_{p['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"reject_file_{p['id']}")
        )
        if os.path.exists(p['file_path']):
            with open(p['file_path'], 'rb') as f:
                bot.send_document(call.message.chat.id, f, caption=text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_file_'))
def approve_file(call):
    pending_id = int(call.data.replace('approve_file_', ''))
    with get_db() as conn:
        pending = conn.execute('SELECT * FROM pending_files WHERE id = ?', (pending_id,)).fetchone()
        if pending:
            with open(pending['file_path'], 'r', encoding='utf-8') as f:
                code = f.read()
            
            scan_result = security_scanner.deep_scan(code)
            result = build_bot_from_pending(pending['user_id'], pending['subscription_id'], pending['file_path'], code, scan_result)
            
            if result['success']:
                conn.execute('UPDATE pending_files SET status = "approved" WHERE id = ?', (pending_id,))
                conn.commit()
                bot.answer_callback_query(call.id, "✅ ربات ساخته شد")
                bot.send_message(call.message.chat.id, f"✅ ربات {result['name']} ساخته شد")
            else:
                bot.answer_callback_query(call.id, f"❌ {result['error'][:30]}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_file_'))
def reject_file(call):
    pending_id = int(call.data.replace('reject_file_', ''))
    with get_db() as conn:
        conn.execute('UPDATE pending_files SET status = "rejected" WHERE id = ?', (pending_id,))
        conn.commit()
        bot.answer_callback_query(call.id, "❌ رد شد")

# ==================== سایر بخش‌های ادمین ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_users")
def admin_users(call):
    with get_db() as conn:
        users = conn.execute('SELECT user_id, first_name, balance, active_subscription, total_bots, created_at FROM users ORDER BY created_at DESC LIMIT 30').fetchall()
    
    text = "👥 **کاربران اخیر**\n\n"
    for u in users:
        status = "✅" if u['active_subscription'] else "❌"
        text += f"{status} {u['user_id']} - {u['first_name']}\n💰 {u['balance']:,} | 🤖 {u['total_bots']}\n📅 {u['created_at'][:10]}\n\n"
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_bots")
def admin_bots(call):
    with get_db() as conn:
        bots = conn.execute('SELECT b.*, u.first_name FROM bots b JOIN users u ON b.user_id = u.user_id WHERE b.status != "deleted" ORDER BY b.created_at DESC LIMIT 30').fetchall()
    
    if not bots:
        bot.send_message(call.message.chat.id, "🤖 رباتی وجود ندارد")
        return
    
    text = "🤖 **ربات‌ها**\n\n"
    for b in bots:
        status = "🟢" if b['status'] == 'running' else "🔴"
        text += f"{status} {b['name']} - {b['first_name']}\n🔗 @{b['username']}\n📅 {b['created_at'][:10]}\n\n"
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_withdraws")
def admin_withdraws(call):
    with get_db() as conn:
        withdraws = conn.execute('SELECT * FROM withdraw_requests WHERE status = "pending" ORDER BY created_at DESC').fetchall()
    
    if not withdraws:
        bot.send_message(call.message.chat.id, "💰 درخواستی وجود ندارد")
        return
    
    for w in withdraws:
        text = f"💰 #{w['id']}\n👤 {w['user_id']}\n💰 {w['amount']:,} تومان\n💳 {w['card_number']}"
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_withdraw_{w['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"reject_withdraw_{w['id']}")
        )
        bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_withdraw_'))
def approve_withdraw(call):
    withdraw_id = int(call.data.replace('approve_withdraw_', ''))
    with get_db() as conn:
        conn.execute('UPDATE withdraw_requests SET status = "approved", processed_at = ? WHERE id = ?', (datetime.now().isoformat(), withdraw_id))
        conn.commit()
        bot.answer_callback_query(call.id, "✅ تایید شد")

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_withdraw_'))
def reject_withdraw(call):
    withdraw_id = int(call.data.replace('reject_withdraw_', ''))
    with get_db() as conn:
        withdraw = conn.execute('SELECT * FROM withdraw_requests WHERE id = ?', (withdraw_id,)).fetchone()
        if withdraw:
            conn.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (withdraw['amount'], withdraw['user_id']))
            conn.execute('UPDATE withdraw_requests SET status = "rejected" WHERE id = ?', (withdraw_id,))
            conn.commit()
        bot.answer_callback_query(call.id, "❌ رد شد")

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_stats(call):
    with get_db() as conn:
        total_users = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        active_subs = conn.execute('SELECT COUNT(*) FROM users WHERE active_subscription = 1').fetchone()[0]
        total_bots = conn.execute('SELECT COUNT(*) FROM bots WHERE status != "deleted"').fetchone()[0]
        total_amount = conn.execute('SELECT COALESCE(SUM(amount), 0) FROM receipts WHERE status = "approved"').fetchone()[0]
        total_withdraws = conn.execute('SELECT COALESCE(SUM(amount), 0) FROM withdraw_requests WHERE status = "approved"').fetchone()[0]
        servers_count = conn.execute('SELECT COUNT(*) FROM servers WHERE status = "active"').fetchone()[0]
    
    text = f"📊 **آمار**\n\n"
    text += f"👥 کاربران: {total_users} (فعال: {active_subs})\n"
    text += f"🤖 ربات‌ها: {total_bots}\n"
    text += f"💰 فروش: {total_amount:,} تومان\n"
    text += f"🏧 برداشت: {total_withdraws:,} تومان\n"
    text += f"🖥️ سرورها: {servers_count}\n"
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_delete_user")
def admin_delete_user(call):
    msg = bot.send_message(call.message.chat.id, "🗑 آیدی کاربر:")
    bot.register_next_step_handler(msg, process_delete_user)

def process_delete_user(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        user_id = int(message.text.strip())
        with get_db() as conn:
            conn.execute('UPDATE users SET active_subscription = 0 WHERE user_id = ?', (user_id,))
            conn.execute('DELETE FROM bots WHERE user_id = ?', (user_id,))
            conn.commit()
        bot.reply_to(message, f"✅ کاربر {user_id} حذف شد")
    except:
        bot.reply_to(message, "❌ خطا")

@bot.callback_query_handler(func=lambda call: call.data == "admin_restart_bot")
def admin_restart_bot(call):
    msg = bot.send_message(call.message.chat.id, "🔄 آیدی ربات:")
    bot.register_next_step_handler(msg, process_restart_bot)

def process_restart_bot(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    bot_id = message.text.strip()
    with get_db() as conn:
        bot_info = conn.execute('SELECT user_id FROM bots WHERE id = ?', (bot_id,)).fetchone()
        if bot_info:
            success, msg = restart_bot(bot_id, bot_info['user_id'])
            bot.reply_to(message, msg)
        else:
            bot.reply_to(message, "❌ ربات پیدا نشد")

@bot.callback_query_handler(func=lambda call: call.data == "admin_logs")
def admin_logs(call):
    with get_db() as conn:
        logs = conn.execute('SELECT * FROM activity_logs ORDER BY created_at DESC LIMIT 30').fetchall()
    
    if not logs:
        bot.send_message(call.message.chat.id, "📋 لاگی وجود ندارد")
        return
    
    text = "📋 **فعالیت‌ها**\n\n"
    for log in logs:
        text += f"👤 {log['user_id']} - {log['action']}\n📅 {log['created_at'][:16]}\n"
        if log['details']:
            text += f"📝 {log['details'][:40]}\n"
        text += "\n"
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_backup")
def admin_backup(call):
    try:
        backup_file = os.path.join(BACKUP_DIR, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        shutil.copy2(DB_PATH, backup_file)
        bot.send_message(call.message.chat.id, f"✅ پشتیبان: {backup_file}")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ خطا: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_manual_sub")
def admin_manual_sub(call):
    msg = bot.send_message(call.message.chat.id, "🎁 آیدی کاربر:")
    bot.register_next_step_handler(msg, process_manual_sub)

def process_manual_sub(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        user_id = int(message.text.strip())
        sub_id, sub_code, expires_at = create_subscription(user_id, config.price)
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

# ==================== بررسی انقضای اشتراک ====================

def check_expired_subscriptions():
    while True:
        try:
            with get_db() as conn:
                expire_soon = conn.execute('''
                    SELECT user_id, subscription_expire FROM users 
                    WHERE active_subscription = 1 
                    AND julianday(subscription_expire) - julianday('now') BETWEEN 0 AND 3
                ''').fetchall()
                
                for user in expire_soon:
                    days_left = (datetime.fromisoformat(user['subscription_expire']) - datetime.now()).days
                    if days_left <= 3 and days_left > 0:
                        try:
                            bot.send_message(user['user_id'], f"⚠️ {days_left} روز تا اتمام اشتراک!\nلطفاً تمدید کنید.")
                        except:
                            pass
                
                expired = conn.execute('''
                    SELECT user_id FROM users 
                    WHERE active_subscription = 1 
                    AND julianday(subscription_expire) - julianday('now') < 0
                ''').fetchall()
                
                for user in expired:
                    conn.execute('UPDATE users SET active_subscription = 0 WHERE user_id = ?', (user['user_id'],))
                    conn.execute('UPDATE bots SET status = "expired" WHERE user_id = ?', (user['user_id'],))
                    
                    bots = conn.execute('SELECT id, server_id FROM bots WHERE user_id = ?', (user['user_id'],)).fetchall()
                    for bot in bots:
                        if bot['server_id']:
                            server = conn.execute('SELECT * FROM servers WHERE id = ?', (bot['server_id'],)).fetchone()
                            if server:
                                server_manager.stop_bot_on_server(dict(server), bot['id'])
                    
                    try:
                        bot.send_message(user['user_id'], "❌ اشتراک شما منقضی شد!\nبرای ادامه، اشتراک جدید بخرید.")
                    except:
                        pass
                
                conn.commit()
            time.sleep(3600)
        except Exception as e:
            logger.error(f"خطا: {e}")
            time.sleep(3600)

# ==================== اجرا ====================

if __name__ == "__main__":
    print("=" * 70)
    print("🚀 ربات مادر نسخه 11.0 - با بررسی امنیتی واقعی")
    print("=" * 70)
    print(f"✅ بررسی امنیتی: فعال (اسکن عمیق)")
    print(f"✅ مدیریت سرور: فعال")
    print(f"✅ توزیع بار: فعال")
    print(f"✅ کیف پول و برداشت: فعال")
    print(f"✅ ادمین: {ADMIN_IDS}")
    print("=" * 70)
    
    expiry_thread = threading.Thread(target=check_expired_subscriptions, daemon=True)
    expiry_thread.start()
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            logger.error(f"خطا: {e}")
            time.sleep(5)