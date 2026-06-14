#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ربات مادر حرفه‌ای Ultimate - نسخه نهایی
با سیستم توزیع بار، هوش مصنوعی، مدیریت پیشرفته، امنیت بالا
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
import ast
import tempfile
from collections import defaultdict
import queue
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Optional, Any
import socket
import struct
import random

# ==================== تنظیمات پایه ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "database")
FILES_DIR = os.path.join(BASE_DIR, "user_files")
RUNNING_DIR = os.path.join(BASE_DIR, "running_bots")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
RECEIPTS_DIR = os.path.join(BASE_DIR, "receipts")
PENDING_FILES_DIR = os.path.join(BASE_DIR, "pending_files")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
CACHE_DIR = os.path.join(BASE_DIR, "cache")

for dir_path in [DB_DIR, FILES_DIR, RUNNING_DIR, LOGS_DIR, RECEIPTS_DIR, 
                 PENDING_FILES_DIR, BACKUP_DIR, CACHE_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# ==================== توکن و تنظیمات ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_IDS = [int(x.strip()) for x in os.environ.get("ADMIN_IDS", "YOUR_ADMIN_ID").split(",")]

PRICE = 200000
CARD_NUMBER = "5892101187322777"
CARD_HOLDER = "مرتضی نیکخو خنجری"

# ==================== لاگینگ حرفه‌ای ====================
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

file_handler = RotatingFileHandler(
    os.path.join(LOGS_DIR, 'mother_bot.log'),
    maxBytes=10485760,
    backupCount=10
)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

# ==================== دیتابیس پیشرفته ====================
DB_PATH = os.path.join(DB_DIR, 'mother_bot.db')

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# ==================== کلاس‌های دیتابیس ====================

class DatabaseManager:
    """مدیریت پیشرفته دیتابیس"""
    
    @staticmethod
    def init_db():
        with get_db() as conn:
            # جدول کاربران
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    phone TEXT,
                    email TEXT,
                    balance INTEGER DEFAULT 0,
                    active_subscription INTEGER DEFAULT 0,
                    subscription_type TEXT DEFAULT 'monthly',
                    subscription_start TIMESTAMP,
                    subscription_end TIMESTAMP,
                    created_at TIMESTAMP,
                    last_active TIMESTAMP,
                    is_banned INTEGER DEFAULT 0,
                    ban_reason TEXT,
                    total_bots INTEGER DEFAULT 0,
                    total_spent INTEGER DEFAULT 0
                )
            ''')
            
            # جدول اشتراک‌ها
            conn.execute('''
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    subscription_code TEXT UNIQUE,
                    type TEXT DEFAULT 'monthly',
                    amount INTEGER,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP,
                    expires_at TIMESTAMP,
                    paid_at TIMESTAMP,
                    transaction_id TEXT,
                    payment_method TEXT DEFAULT 'card',
                    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
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
                    folder_path TEXT,
                    pid INTEGER,
                    port INTEGER,
                    status TEXT DEFAULT 'stopped',
                    version INTEGER DEFAULT 1,
                    cpu_usage REAL DEFAULT 0,
                    memory_usage REAL DEFAULT 0,
                    created_at TIMESTAMP,
                    expires_at TIMESTAMP,
                    last_active TIMESTAMP,
                    restart_count INTEGER DEFAULT 0,
                    error_log TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            ''')
            
            # جدول فایل‌های در انتظار
            conn.execute('''
                CREATE TABLE IF NOT EXISTS pending_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    subscription_id INTEGER,
                    file_path TEXT,
                    file_name TEXT,
                    file_size INTEGER,
                    file_hash TEXT,
                    status TEXT DEFAULT 'pending',
                    security_score INTEGER DEFAULT 0,
                    security_level TEXT,
                    security_report TEXT,
                    dangerous_patterns TEXT,
                    submitted_at TIMESTAMP,
                    reviewed_at TIMESTAMP,
                    review_note TEXT,
                    auto_approved INTEGER DEFAULT 0,
                    ip_address TEXT,
                    user_agent TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
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
                    transaction_id TEXT,
                    bank_name TEXT,
                    created_at TIMESTAMP,
                    reviewed_at TIMESTAMP,
                    reviewed_by INTEGER,
                    rejection_reason TEXT
                )
            ''')
            
            # جدول کتابخانه‌ها
            conn.execute('''
                CREATE TABLE IF NOT EXISTS libraries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    version TEXT,
                    description TEXT,
                    category TEXT,
                    install_count INTEGER DEFAULT 0,
                    is_installed INTEGER DEFAULT 0,
                    last_updated TIMESTAMP
                )
            ''')
            
            # جدول سرورها
            conn.execute('''
                CREATE TABLE IF NOT EXISTS servers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    host TEXT UNIQUE,
                    port INTEGER DEFAULT 22,
                    username TEXT,
                    password_encrypted TEXT,
                    status TEXT DEFAULT 'active',
                    cpu_usage REAL DEFAULT 0,
                    memory_usage REAL DEFAULT 0,
                    disk_usage REAL DEFAULT 0,
                    load_average REAL DEFAULT 0,
                    running_bots INTEGER DEFAULT 0,
                    max_bots INTEGER DEFAULT 50,
                    location TEXT,
                    created_at TIMESTAMP,
                    last_check TIMESTAMP
                )
            ''')
            
            # جدول لاگ‌های امنیتی
            conn.execute('''
                CREATE TABLE IF NOT EXISTS security_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT,
                    file_name TEXT,
                    security_score INTEGER,
                    verdict TEXT,
                    ip_address TEXT,
                    created_at TIMESTAMP
                )
            ''')
            
            # جدول تراکنش‌ها
            conn.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount INTEGER,
                    type TEXT,
                    description TEXT,
                    status TEXT,
                    created_at TIMESTAMP
                )
            ''')
            
            # جدول سیستم
            conn.execute('''
                CREATE TABLE IF NOT EXISTS system_config (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP
                )
            ''')
            
            # ایجاد ایندکس‌ها
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_subscription ON users(active_subscription, subscription_end)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_bots_user ON bots(user_id, status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pending_status ON pending_files(status, security_score)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_receipts_status ON receipts(status, created_at)")
            
            conn.commit()
            
            # پر کردن داده‌های اولیه
            DatabaseManager.populate_initial_data(conn)
    
    @staticmethod
    def populate_initial_data(conn):
        # پر کردن کتابخانه‌ها
        libraries = [
            ("requests", "2.31.0", "HTTP library for Python", "web"),
            ("aiohttp", "3.9.0", "Async HTTP client/server", "web"),
            ("fastapi", "0.104.0", "Modern web framework", "web"),
            ("flask", "3.0.0", "Micro web framework", "web"),
            ("django", "5.0.0", "High-level web framework", "web"),
            ("numpy", "1.26.0", "Numerical computing", "data"),
            ("pandas", "2.1.0", "Data analysis", "data"),
            ("scikit-learn", "1.3.0", "Machine learning", "ai"),
            ("tensorflow", "2.13.0", "Deep learning", "ai"),
            ("torch", "2.1.0", "PyTorch", "ai"),
            ("pillow", "10.1.0", "Image processing", "media"),
            ("opencv-python", "4.8.1", "Computer vision", "media"),
            ("beautifulsoup4", "4.12.2", "HTML parsing", "scraping"),
            ("selenium", "4.15.0", "Browser automation", "scraping"),
            ("scrapy", "2.11.0", "Web crawling", "scraping"),
            ("pyTelegramBotAPI", "4.13.0", "Telegram Bot API", "telegram"),
            ("aiogram", "3.1.1", "Async Telegram Bot", "telegram"),
            ("python-telegram-bot", "20.6", "Telegram Bot API", "telegram"),
            ("telethon", "1.34.0", "Telegram client", "telegram"),
            ("cryptography", "41.0.7", "Cryptographic recipes", "security"),
            ("pyjwt", "2.8.0", "JWT implementation", "security"),
            ("bcrypt", "4.0.1", "Password hashing", "security"),
            ("yt-dlp", "2023.11.16", "YouTube downloader", "download"),
            ("pytube", "15.0.0", "YouTube downloader", "download"),
            ("jdatetime", "4.1.0", "Jalali calendar", "i18n"),
            ("pytz", "2023.3", "Timezones", "i18n"),
            ("openpyxl", "3.1.2", "Excel files", "office"),
            ("reportlab", "4.0.4", "PDF generation", "office"),
            ("matplotlib", "3.8.0", "Plotting", "graphics"),
            ("plotly", "5.18.0", "Interactive plots", "graphics"),
            ("seaborn", "0.13.0", "Statistical viz", "graphics"),
            ("loguru", "0.7.2", "Logging made easy", "tools"),
            ("tqdm", "4.66.1", "Progress bars", "tools"),
            ("rich", "13.7.0", "Rich text formatting", "tools"),
            ("click", "8.1.7", "CLI framework", "tools"),
            ("python-dotenv", "1.0.0", "Environment variables", "tools"),
            ("schedule", "1.2.0", "Task scheduling", "tools"),
            ("celery", "5.3.4", "Task queue", "tools"),
            ("redis", "5.0.1", "Redis client", "database"),
            ("sqlalchemy", "2.0.23", "SQL toolkit", "database"),
            ("motor", "3.3.2", "MongoDB driver", "database"),
            ("paramiko", "3.4.0", "SSH client", "network"),
            ("netmiko", "4.3.0", "Network automation", "network"),
            ("scapy", "2.5.0", "Packet manipulation", "network"),
            ("pytest", "7.4.3", "Testing framework", "testing"),
            ("qrcode", "7.4.2", "QR code generation", "media"),
            ("moviepy", "1.0.3", "Video editing", "media"),
            ("pydub", "0.25.1", "Audio processing", "audio"),
            ("speechrecognition", "3.10.0", "Speech recognition", "audio"),
            ("pytesseract", "0.3.10", "OCR engine", "ocr"),
            ("easyocr", "1.7.1", "OCR made easy", "ocr"),
            ("forex-python", "1.8", "Forex rates", "finance"),
            ("cryptocompare", "0.7", "Crypto prices", "finance"),
            ("babel", "2.13.0", "Internationalization", "i18n"),
        ]
        
        for lib in libraries:
            conn.execute('''
                INSERT OR IGNORE INTO libraries (name, version, description, category, install_count, is_installed)
                VALUES (?, ?, ?, ?, 0, 0)
            ''', lib)
        
        # تنظیمات سیستم
        default_config = [
            ("welcome_text", "🚀 به ربات سازنده خوش آمدید!"),
            ("price", str(PRICE)),
            ("card_number", CARD_NUMBER),
            ("card_holder", CARD_HOLDER),
            ("maintenance_mode", "0"),
        ]
        
        for key, value in default_config:
            conn.execute('''
                INSERT OR IGNORE INTO system_config (key, value, updated_at)
                VALUES (?, ?, ?)
            ''', (key, value, datetime.now().isoformat()))
        
        conn.commit()

# ==================== سیستم امنیت پیشرفته ====================

class AdvancedSecurityChecker:
    """سیستم بررسی امنیت پیشرفته با تحلیل هوشمند"""
    
    def __init__(self):
        self.dangerous_patterns = {
            'critical': [
                (r'os\.system\s*\(', "اجرای مستقیم دستور سیستمی"),
                (r'subprocess\.(call|Popen|run|check_output)\s*\(', "اجرای زیرپروسس"),
                (r'eval\s*\(', "اجرای کد پویا eval"),
                (r'exec\s*\(', "اجرای کد پویا exec"),
                (r'__import__\s*\(', "ایمپورت پویا"),
                (r'base64\.b64decode\s*\(', "کد انکود شده"),
                (r'compile\s*\(', "کامپایل پویا"),
                (r'globals\(\)\[', "دسترسی به متغیرهای سراسری"),
                (r'locals\(\)\[', "دسترسی به متغیرهای محلی"),
                (r'getattr\(.*,\s*["\']__', "دسترسی به متدهای داخلی"),
            ],
            'high': [
                (r'open\s*\([\'\"](/etc/|/root/|/home/|C:\\|\.\./)', "دسترسی به فایل حساس"),
                (r'socket\.', "اتصال شبکه مستقیم"),
                (r'rm\s+-rf', "حذف فایل‌ها"),
                (r'wget|curl', "دانلود فایل"),
                (r'mkfifo|nc\s+-e', "بکدور شل"),
                (r'chmod\s+777', "تغییر دسترسی فایل"),
                (r'\.onion', "اتصال به دارک وب"),
            ],
            'medium': [
                (r'pickle\.loads?', "دسریالایز خطرناک pickle"),
                (r'yaml\.load\s*\([^,]*$', "YAML خطرناک"),
                (r'globals\(\)\.update', "تغییر متغیرهای سراسری"),
                (r'setattr|getattr', "دسترسی داینامیک"),
                (r'__getattr__|__setattr__', "اوورراید متدها"),
            ],
            'low': [
                (r'while\s+True:', "حلقه بی‌نهایت احتمالی"),
                (r'time\.sleep\s*\(\s*[0-9]{3,}', "تاخیر طولانی"),
                (r'for.*in.*range\([0-9]{6,}\)', "حلقه بزرگ"),
                (r'\.pop\(\)|\.remove\(\)', "حذف از لیست"),
            ]
        }
        
        self.allowed_imports = {
            'telebot', 'types', 'time', 'datetime', 'random', 'json', 
            're', 'math', 'string', 'collections', 'itertools', 'functools',
            'requests', 'beautifulsoup4', 'bs4', 'numpy', 'pandas'
        }
    
    def analyze(self, code: str, file_name: str = "") -> Dict:
        """تحلیل کامل امنیتی کد"""
        result = {
            'is_safe': True,
            'score': 100,
            'security_level': 'عالی',
            'issues': [],
            'critical_issues': [],
            'high_issues': [],
            'medium_issues': [],
            'low_issues': [],
            'warnings': [],
            'statistics': {
                'lines': len(code.split('\n')),
                'functions': 0,
                'classes': 0,
                'imports': 0,
                'dangerous_imports': 0
            },
            'has_token': False,
            'has_valid_token': False,
            'recommendations': []
        }
        
        # تحلیل AST
        try:
            tree = ast.parse(code)
            
            # شمارش توابع و کلاس‌ها
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    result['statistics']['functions'] += 1
                elif isinstance(node, ast.ClassDef):
                    result['statistics']['classes'] += 1
                elif isinstance(node, ast.Import):
                    result['statistics']['imports'] += 1
                elif isinstance(node, ast.ImportFrom):
                    result['statistics']['imports'] += 1
        except SyntaxError as e:
            result['issues'].append(f"خطای نحوی در کد: {str(e)}")
            result['score'] -= 30
        
        # بررسی الگوهای خطرناک
        for level, patterns in self.dangerous_patterns.items():
            for pattern, description in patterns:
                if re.search(pattern, code, re.IGNORECASE):
                    result[f'{level}_issues'].append(description)
                    result['issues'].append(f"[{level.upper()}] {description}")
                    
                    if level == 'critical':
                        result['is_safe'] = False
                        result['score'] -= 35
                    elif level == 'high':
                        result['score'] -= 20
                    elif level == 'medium':
                        result['score'] -= 10
                    elif level == 'low':
                        result['score'] -= 5
        
        # بررسی وجود توکن
        token_patterns = [
            r'TOKEN\s*=\s*["\']([^"\']{30,50})["\']',
            r'token\s*=\s*["\']([^"\']{30,50})["\']',
            r'BOT_TOKEN\s*=\s*["\']([^"\']{30,50})["\']',
            r'API_TOKEN\s*=\s*["\']([^"\']{30,50})["\']',
            r'bot\s*=\s*telebot\.TeleBot\(\s*["\']([^"\']{30,50})["\']\s*\)'
        ]
        
        for pattern in token_patterns:
            match = re.search(pattern, code)
            if match:
                result['has_token'] = True
                token = match.group(1)
                # بررسی اعتبار توکن
                try:
                    response = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=3)
                    if response.status_code == 200:
                        result['has_valid_token'] = True
                        bot_info = response.json().get('result', {})
                        result['bot_name'] = bot_info.get('first_name', 'Unknown')
                        result['bot_username'] = bot_info.get('username', 'Unknown')
                except:
                    pass
                break
        
        # امتیاز نهایی
        result['score'] = max(0, min(100, result['score']))
        
        # تعیین سطح امنیت
        if result['score'] >= 85:
            result['security_level'] = 'عالی'
            result['is_safe'] = True
        elif result['score'] >= 70:
            result['security_level'] = 'خوب'
            result['is_safe'] = True
        elif result['score'] >= 50:
            result['security_level'] = 'متوسط'
            result['is_safe'] = False
        else:
            result['security_level'] = 'ضعیف'
            result['is_safe'] = False
        
        # پیشنهادات
        if not result['has_token']:
            result['recommendations'].append("توکن در کد یافت نشد. لطفاً توکن ربات را در کد قرار دهید.")
        
        if result['critical_issues']:
            result['recommendations'].append("کد حاوی دستورات خطرناک است. لطفاً آنها را حذف کنید.")
        
        if result['statistics']['lines'] > 2000:
            result['recommendations'].append("کد بسیار بزرگ است. بهتر است به چند فایل تقسیم شود.")
        
        if result['statistics']['functions'] == 0:
            result['recommendations'].append("کد فاقد تابع است. بهتر است از تابع main استفاده کنید.")
        
        return result
    
    def generate_report(self, analysis: Dict) -> str:
        """تولید گزارش خوانا"""
        report = "🔍 **گزارش تحلیل امنیتی هوشمند**\n\n"
        report += f"📊 **امتیاز کلی:** {analysis['score']}/100\n"
        report += f"🛡️ **سطح امنیت:** {analysis['security_level']}\n"
        report += f"✅ **وضعیت:** {'امن ✅' if analysis['is_safe'] else 'نیاز به بررسی ⚠️'}\n\n"
        
        report += f"📏 **آمار کد:**\n"
        report += f"• خطوط کد: {analysis['statistics']['lines']}\n"
        report += f"• توابع: {analysis['statistics']['functions']}\n"
        report += f"• کلاس‌ها: {analysis['statistics']['classes']}\n"
        report += f"• ایمپورت‌ها: {analysis['statistics']['imports']}\n\n"
        
        if analysis.get('critical_issues'):
            report += "🔴 **مشکلات بحرانی:**\n"
            for issue in analysis['critical_issues'][:5]:
                report += f"• {issue}\n"
            report += "\n"
        
        if analysis.get('high_issues'):
            report += "🟠 **مشکلات بالا:**\n"
            for issue in analysis['high_issues'][:5]:
                report += f"• {issue}\n"
            report += "\n"
        
        if analysis.get('medium_issues'):
            report += "🟡 **مشکلات متوسط:**\n"
            for issue in analysis['medium_issues'][:3]:
                report += f"• {issue}\n"
            report += "\n"
        
        if analysis.get('recommendations'):
            report += "💡 **پیشنهادات:**\n"
            for rec in analysis['recommendations'][:3]:
                report += f"• {rec}\n"
        
        return report

security_checker = AdvancedSecurityChecker()

# ==================== سیستم مدیریت ربات‌ها ====================

class BotManager:
    """مدیریت پیشرفته ربات‌ها"""
    
    def __init__(self):
        self.running_bots = {}
        self.bot_lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=10)
    
    def run_bot(self, bot_id: str, file_path: str, bot_dir: str) -> Tuple[bool, Optional[int], Optional[str]]:
        """اجرای ربات با نظارت"""
        try:
            # کپی فایل به پوشه ربات
            dest_path = os.path.join(bot_dir, 'bot.py')
            shutil.copy(file_path, dest_path)
            
            # فایل لاگ
            log_file = os.path.join(bot_dir, 'bot.log')
            
            # اجرا با nohup برای پایداری
            process = subprocess.Popen(
                [sys.executable, dest_path],
                stdout=open(log_file, 'a'),
                stderr=subprocess.STDOUT,
                cwd=bot_dir,
                start_new_session=True,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )
            
            time.sleep(3)
            
            if process.poll() is None:
                with self.bot_lock:
                    self.running_bots[bot_id] = {
                        'process': process,
                        'pid': process.pid,
                        'dir': bot_dir,
                        'start_time': time.time(),
                        'restart_count': 0
                    }
                return True, process.pid, None
            else:
                # خواندن خطا
                with open(log_file, 'r') as f:
                    error = f.read()[-500:]
                return False, None, error or "خطای ناشناخته"
                
        except Exception as e:
            return False, None, str(e)
    
    def stop_bot(self, bot_id: str, pid: int) -> bool:
        """توقف ربات"""
        try:
            # SIGTERM بفرست
            os.kill(pid, signal.SIGTERM)
            
            # صبر برای بسته شدن
            for _ in range(10):
                try:
                    os.kill(pid, 0)
                    time.sleep(0.5)
                except OSError:
                    break
            
            # اگر هنوز باز بود، SIGKILL بفرست
            try:
                os.kill(pid, signal.SIGKILL)
            except:
                pass
            
            with self.bot_lock:
                if bot_id in self.running_bots:
                    del self.running_bots[bot_id]
            
            return True
        except:
            return False
    
    def get_bot_status(self, bot_id: str, pid: int) -> bool:
        """بررسی وضعیت ربات"""
        try:
            os.kill(pid, 0)
            return True
        except:
            return False
    
    def restart_bot(self, bot_id: str, user_id: int, file_path: str, pid: int) -> Tuple[bool, str]:
        """ریستارت ربات"""
        # توقف قبلی
        if pid:
            self.stop_bot(bot_id, pid)
        
        # پوشه جدید
        bot_dir = os.path.join(RUNNING_DIR, bot_id)
        os.makedirs(bot_dir, exist_ok=True)
        
        # اجرا مجدد
        success, new_pid, error = self.run_bot(bot_id, file_path, bot_dir)
        
        if success:
            with get_db() as conn:
                conn.execute('''
                    UPDATE bots SET status = 'running', pid = ?, last_active = ?, restart_count = restart_count + 1
                    WHERE id = ?
                ''', (new_pid, datetime.now().isoformat(), bot_id))
                conn.commit()
            return True, "ربات با موفقیت ریستارت شد"
        else:
            return False, f"خطا در ریستارت: {error}"

bot_manager = BotManager()

# ==================== سیستم توزیع بار ====================

class LoadBalancer:
    """توزیع بار هوشمند بین سرورها"""
    
    def __init__(self):
        self.servers = []
        self.load_cache = {}
    
    def get_best_server(self) -> Optional[Dict]:
        """انتخاب بهترین سرور برای اجرای ربات"""
        with get_db() as conn:
            servers = conn.execute('''
                SELECT * FROM servers 
                WHERE status = 'active' 
                AND running_bots < max_bots
                ORDER BY 
                    load_average ASC,
                    running_bots ASC,
                    cpu_usage ASC
                LIMIT 1
            ''').fetchall()
            
            if servers:
                return dict(servers[0])
            
            # اگر سروری نبود، سرور لوکال
            return {
                'id': 0,
                'name': 'Local Server',
                'host': 'localhost',
                'running_bots': 0,
                'max_bots': 100
            }
        
        return None
    
    def add_server(self, name: str, host: str, port: int, username: str, password: str) -> Dict:
        """افزودن سرور جدید"""
        # تست اتصال
        try:
            import paramiko
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(host, port=port, username=username, password=password, timeout=10)
            
            # دریافت اطلاعات سیستم
            stdin, stdout, stderr = ssh.exec_command("nproc && free -m | awk '/^Mem:/{print $2}' && df -h / | awk 'NR==2 {print $5}'")
            output = stdout.read().decode().strip().split('\n')
            
            cpu_cores = int(output[0]) if output else 1
            memory_mb = int(output[1]) if len(output) > 1 else 1024
            disk_usage = output[2] if len(output) > 2 else "0%"
            
            ssh.close()
            
            # رمزگذاری رمز
            encrypted_password = self.encrypt_password(password)
            
            with get_db() as conn:
                now = datetime.now().isoformat()
                conn.execute('''
                    INSERT INTO servers (name, host, port, username, password_encrypted, status, max_bots, created_at, last_check)
                    VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?)
                ''', (name, host, port, username, encrypted_password, cpu_cores * 5, now, now))
                conn.commit()
                
                server_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            
            return {
                'success': True,
                'message': f'سرور {name} با موفقیت اضافه شد',
                'server_id': server_id,
                'cpu_cores': cpu_cores,
                'memory_mb': memory_mb
            }
            
        except Exception as e:
            return {'success': False, 'message': f'خطا در اتصال: {str(e)}'}
    
    def encrypt_password(self, password: str) -> str:
        """رمزگذاری ساده رمز"""
        key = hashlib.md5(b"secret_key_for_encryption").digest()
        result = []
        for i, char in enumerate(password):
            result.append(chr(ord(char) ^ key[i % len(key)]))
        return ''.join(result)
    
    def decrypt_password(self, encrypted: str) -> str:
        """رمزگشایی رمز"""
        key = hashlib.md5(b"secret_key_for_encryption").digest()
        result = []
        for i, char in enumerate(encrypted):
            result.append(chr(ord(char) ^ key[i % len(key)]))
        return ''.join(result)

load_balancer = LoadBalancer()

# ==================== سیستم مدیریت کاربران ====================

class UserManager:
    """مدیریت کامل کاربران"""
    
    @staticmethod
    def create_user(user_id: int, username: str, first_name: str, last_name: str = "") -> bool:
        with get_db() as conn:
            now = datetime.now().isoformat()
            conn.execute('''
                INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, created_at, last_active)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name, now, now))
            conn.execute('UPDATE users SET last_active = ? WHERE user_id = ?', (now, user_id))
            conn.commit()
            return True
    
    @staticmethod
    def has_active_subscription(user_id: int) -> bool:
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
    
    @staticmethod
    def create_subscription(user_id: int, amount: int, sub_type: str = 'monthly') -> Tuple[Optional[int], Optional[str]]:
        with get_db() as conn:
            sub_code = hashlib.md5(f"{user_id}_{time.time()}_{secrets.token_hex(4)}".encode()).hexdigest()[:12].upper()
            now = datetime.now().isoformat()
            expires_at = (datetime.now() + timedelta(days=30 if sub_type == 'monthly' else 365)).isoformat()
            
            conn.execute('''
                INSERT INTO subscriptions (user_id, subscription_code, type, amount, status, created_at, expires_at)
                VALUES (?, ?, ?, ?, 'pending', ?, ?)
            ''', (user_id, sub_code, sub_type, amount, now, expires_at))
            conn.commit()
            
            sub_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            return sub_id, sub_code
    
    @staticmethod
    def activate_subscription(subscription_id: int) -> bool:
        with get_db() as conn:
            sub = conn.execute('SELECT * FROM subscriptions WHERE id = ?', (subscription_id,)).fetchone()
            if sub:
                expires_at = (datetime.now() + timedelta(days=30 if sub['type'] == 'monthly' else 365)).isoformat()
                conn.execute('UPDATE users SET active_subscription = 1, subscription_type = ?, subscription_start = ?, subscription_end = ? WHERE user_id = ?',
                           (sub['type'], datetime.now().isoformat(), expires_at, sub['user_id']))
                conn.execute('UPDATE subscriptions SET status = 'active', paid_at = ? WHERE id = ?',
                           (datetime.now().isoformat(), subscription_id))
                conn.commit()
                return True
            return False
    
    @staticmethod
    def get_user_bots(user_id: int) -> List[Dict]:
        with get_db() as conn:
            bots = conn.execute('SELECT * FROM bots WHERE user_id = ? ORDER BY created_at DESC', (user_id,)).fetchall()
            return [dict(bot) for bot in bots]
    
    @staticmethod
    def delete_user(user_id: int) -> bool:
        with get_db() as conn:
            # توقف ربات‌ها
            bots = conn.execute('SELECT id, pid FROM bots WHERE user_id = ?', (user_id,)).fetchall()
            for bot in bots:
                try:
                    os.kill(bot['pid'], signal.SIGTERM)
                except:
                    pass
            conn.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
            conn.commit()
            return True

user_manager = UserManager()

# ==================== کتابخانه منیجر ====================

class LibraryManager:
    """مدیریت نصب کتابخانه‌ها"""
    
    def __init__(self):
        self.installing = set()
    
    def get_all_libraries(self) -> List[Dict]:
        with get_db() as conn:
            libs = conn.execute('SELECT * FROM libraries ORDER BY category, name').fetchall()
            return [dict(lib) for lib in libs]
    
    def get_libraries_by_category(self) -> Dict:
        libs = self.get_all_libraries()
        categories = defaultdict(list)
        for lib in libs:
            categories[lib['category']].append(lib)
        return dict(categories)
    
    def install_library(self, lib_name: str, chat_id: int) -> Tuple[bool, str]:
        if lib_name in self.installing:
            return False, "کتابخانه در حال نصب است"
        
        self.installing.add(lib_name)
        
        try:
            process = subprocess.Popen(
                [sys.executable, "-m", "pip", "install", lib_name, "--quiet"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(timeout=120)
            
            if process.returncode == 0:
                with get_db() as conn:
                    conn.execute('''
                        UPDATE libraries SET install_count = install_count + 1, is_installed = 1, last_updated = ?
                        WHERE name = ?
                    ''', (datetime.now().isoformat(), lib_name))
                    conn.commit()
                return True, f"✅ کتابخانه {lib_name} با موفقیت نصب شد!"
            else:
                return False, f"❌ خطا: {stderr[:200]}"
                
        except subprocess.TimeoutExpired:
            process.kill()
            return False, "❌ زمان نصب بیش از حد طول کشید"
        except Exception as e:
            return False, f"❌ خطا: {str(e)}"
        finally:
            self.installing.discard(lib_name)

lib_manager = LibraryManager()

# ==================== سیستم اخطار اشتراک ====================

class SubscriptionNotifier:
    """مدیریت اخطارهای اشتراک"""
    
    @staticmethod
    def check_and_notify():
        """بررسی و ارسال اخطار"""
        with get_db() as conn:
            # اخطار 3 روز مونده
            warning_users = conn.execute('''
                SELECT user_id, subscription_end, first_name
                FROM users 
                WHERE active_subscription = 1 
                AND datetime(subscription_end) <= datetime('now', '+3 days')
                AND datetime(subscription_end) > datetime('now')
            ''').fetchall()
            
            for user in warning_users:
                end_date = datetime.fromisoformat(user['subscription_end']).strftime('%Y-%m-%d')
                try:
                    bot.send_message(
                        user['user_id'],
                        f"⚠️ **اخطار انقضای اشتراک** ⚠️\n\n"
                        f"👤 {user['first_name']} عزیز\n\n"
                        f"اشتراک شما در **{end_date}** منقضی می‌شود.\n"
                        f"لطفاً برای تمدید اقدام کنید.\n\n"
                        f"💰 مبلغ تمدید: {PRICE:,} تومان\n"
                        f"🏦 شماره کارت: `{CARD_NUMBER}`",
                        parse_mode="Markdown"
                    )
                except:
                    pass
            
            # غیرفعال کردن اشتراک‌های منقضی
            expired_users = conn.execute('''
                SELECT user_id FROM users 
                WHERE active_subscription = 1 
                AND datetime(subscription_end) <= datetime('now')
            ''').fetchall()
            
            for user in expired_users:
                conn.execute('UPDATE users SET active_subscription = 0 WHERE user_id = ?', (user['user_id'],))
                
                # توقف ربات‌ها
                bots = conn.execute('SELECT id, pid FROM bots WHERE user_id = ? AND status = "running"', (user['user_id'],)).fetchall()
                for bot in bots:
                    try:
                        os.kill(bot['pid'], signal.SIGTERM)
                    except:
                        pass
                    conn.execute('UPDATE bots SET status = "expired" WHERE id = ?', (bot['id'],))
                
                try:
                    bot.send_message(
                        user['user_id'],
                        f"❌ اشتراک شما به پایان رسید.\n\n"
                        f"برای استفاده مجدد، لطفاً اشتراک خود را تمدید کنید."
                    )
                except:
                    pass
            
            conn.commit()

# ==================== ربات ====================

bot = telebot.TeleBot(BOT_TOKEN)

# منوها
def get_main_menu(is_admin=False):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        types.KeyboardButton('🛒 خرید اشتراک'),
        types.KeyboardButton('📤 ارسال فایل ربات'),
        types.KeyboardButton('🤖 ربات‌های من'),
        types.KeyboardButton('📚 راهنما'),
        types.KeyboardButton('📦 نصب کتابخانه'),
        types.KeyboardButton('📊 وضعیت من'),
        types.KeyboardButton('📞 پشتیبانی')
    ]
    if is_admin:
        buttons.append(types.KeyboardButton('👑 پنل ادمین'))
    markup.add(*buttons)
    return markup

def get_admin_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📸 فیش‌های واریز", callback_data="admin_receipts"),
        types.InlineKeyboardButton("📥 فایل‌های در انتظار", callback_data="admin_pending"),
        types.InlineKeyboardButton("👥 مدیریت کاربران", callback_data="admin_users"),
        types.InlineKeyboardButton("🤖 مدیریت ربات‌ها", callback_data="admin_bots"),
        types.InlineKeyboardButton("🖥️ مدیریت سرورها", callback_data="admin_servers"),
        types.InlineKeyboardButton("📊 آمار پیشرفته", callback_data="admin_stats"),
        types.InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings"),
        types.InlineKeyboardButton("💰 تایید دستی اشتراک", callback_data="admin_manual")
    )
    return markup

# هندلر استارت
@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    
    user_manager.create_user(user_id, username, first_name, last_name)
    
    is_admin = user_id in ADMIN_IDS
    markup = get_main_menu(is_admin)
    
    welcome = f"""🚀 **ربات سازنده حرفه‌ای**

👤 {first_name} عزیز خوش آمدید!

✅ **امکانات پیشرفته:**
• 🤖 ساخت ربات تلگرامی با ارسال فایل
• 🔒 بررسی امنیت با هوش مصنوعی
• 📦 نصب خودکار ۱۰۰+ کتابخانه
• ⏰ مدیریت اشتراک و اخطار
• 🌐 توزیع بار روی سرورها

💰 **قیمت اشتراک:** {PRICE:,} تومان (ماهانه)

📞 پشتیبانی: @shahraghee13"""
    
    bot.send_message(message.chat.id, welcome, parse_mode="Markdown", reply_markup=markup)

# خرید اشتراک
@bot.message_handler(func=lambda m: m.text == '🛒 خرید اشتراک')
def buy_subscription(message):
    user_id = message.from_user.id
    
    if user_manager.has_active_subscription(user_id):
        bot.send_message(message.chat.id, "✅ شما اشتراک فعال دارید!\n📤 لطفاً فایل ربات خود را ارسال کنید.")
        return
    
    sub_id, sub_code = user_manager.create_subscription(user_id, PRICE)
    
    text = f"""💰 **خرید اشتراک ماهانه**

💳 **مبلغ:** {PRICE:,} تومان
🏦 **شماره کارت:** `{CARD_NUMBER}`
👤 **به نام:** {CARD_HOLDER}

🆔 **کد اشتراک:** `{sub_code}`

📌 **مراحل:**
1️⃣ مبلغ را واریز کنید
2️⃣ کد اشتراک را در رسید یادداشت کنید
3️⃣ تصویر فیش را ارسال کنید

⏳ پس از تأیید، می‌توانید فایل ربات خود را ارسال کنید"""
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# دریافت فیش
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
        bot.reply_to(message, "❌ شما اشتراک در انتظار پرداختی ندارید")
        return
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        payment_code = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:8].upper()
        receipt_path = os.path.join(RECEIPTS_DIR, f"{user_id}_{payment_code}.jpg")
        
        with open(receipt_path, 'wb') as f:
            f.write(downloaded_file)
        
        with get_db() as conn:
            conn.execute('''
                INSERT INTO receipts (user_id, subscription_id, amount, receipt_path, payment_code, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, pending_sub['id'], PRICE, receipt_path, payment_code, datetime.now().isoformat()))
            conn.commit()
        
        bot.reply_to(message, f"✅ فیش دریافت شد!\n💰 {PRICE:,} تومان\n🆔 {payment_code}\n\n⏳ پس از تأیید ادمین فعال می‌شود.")
        
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
    
    if not user_manager.has_active_subscription(user_id):
        bot.send_message(message.chat.id, f"❌ اشتراک فعال ندارید!\n💰 قیمت: {PRICE:,} تومان\nاز منوی خرید استفاده کنید.")
        return
    
    bot.send_message(message.chat.id, "📤 فایل `.py` ربات خود را ارسال کنید.\n\n🔍 فایل شما با هوش مصنوعی بررسی می‌شود.")

# دریافت فایل
@bot.message_handler(content_types=['document'])
def handle_bot_file(message):
    user_id = message.from_user.id
    file_name = message.document.file_name
    
    if not file_name.endswith('.py'):
        bot.reply_to(message, "❌ فقط فایل‌های `.py` مجاز هستند!")
        return
    
    if message.document.file_size > 10 * 1024 * 1024:
        bot.reply_to(message, "❌ حجم فایل نباید بیشتر از ۱۰ مگابایت باشد!")
        return
    
    status_msg = bot.reply_to(message, "🔄 در حال بررسی فایل با هوش مصنوعی...")
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # ذخیره فایل
        user_dir = os.path.join(PENDING_FILES_DIR, str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        file_path = os.path.join(user_dir, f"{int(time.time())}_{file_name}")
        
        with open(file_path, 'wb') as f:
            f.write(downloaded_file)
        
        # خواندن کد
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # تحلیل امنیت
        analysis = security_checker.analyze(code, file_name)
        report = security_checker.generate_report(analysis)
        
        bot.edit_message_text(f"🔍 **تحلیل امنیت تکمیل شد!**\n\n{report}", 
                              message.chat.id, status_msg.message_id, parse_mode="Markdown")
        
        # گرفتن اشتراک
        with get_db() as conn:
            sub = conn.execute('''
                SELECT id FROM subscriptions 
                WHERE user_id = ? AND status = 'active'
                ORDER BY paid_at DESC LIMIT 1
            ''', (user_id,)).fetchone()
        
        if not sub:
            bot.send_message(message.chat.id, "❌ اشتراک فعال پیدا نشد!")
            return
        
        # ذخیره در pending
        with get_db() as conn:
            conn.execute('''
                INSERT INTO pending_files (user_id, subscription_id, file_path, file_name, file_size, 
                                          security_score, security_level, security_report, submitted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, sub['id'], file_path, file_name, message.document.file_size,
                  analysis['score'], analysis['security_level'], report, datetime.now().isoformat()))
            pending_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            conn.commit()
        
        # اگر امن بود خودکار تایید کن
        if analysis['is_safe'] and analysis['score'] >= 75:
            bot.send_message(message.chat.id, "✅ فایل شما امن تشخیص داده شد! در حال ساخت ربات...")
            auto_approve_bot(pending_id, user_id, file_path, code, message.chat.id)
        else:
            # ارسال به ادمین
            for admin_id in ADMIN_IDS:
                try:
                    with open(file_path, 'rb') as f:
                        bot.send_document(admin_id, f, 
                            caption=f"📥 فایل جدید\n👤 {user_id}\n📄 {file_name}\n🤖 امتیاز: {analysis['score']}/100\n🆔 {pending_id}\n\n{report[:500]}")
                except:
                    pass
            
            bot.send_message(message.chat.id, f"✅ فایل شما به ادمین ارسال شد.\nامتیاز امنیت: {analysis['score']}/100\nپس از تأیید ساخته می‌شود.")
            
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)}", message.chat.id, status_msg.message_id)

def auto_approve_bot(pending_id, user_id, file_path, code, chat_id):
    """تایید خودکار و ساخت ربات"""
    try:
        # استخراج توکن
        token = None
        token_patterns = [r'token\s*=\s*["\']([^"\']+)["\']', r'TOKEN\s*=\s*["\']([^"\']+)["\']']
        for pattern in token_patterns:
            match = re.search(pattern, code, re.IGNORECASE)
            if match:
                token = match.group(1)
                break
        
        if not token:
            bot.send_message(chat_id, "❌ توکن در کد پیدا نشد!")
            return
        
        # بررسی توکن
        response = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
        if response.status_code != 200:
            bot.send_message(chat_id, "❌ توکن معتبر نیست!")
            return
        
        bot_info = response.json()['result']
        
        # انتخاب سرور
        best_server = load_balancer.get_best_server()
        
        # ساخت ربات
        bot_id = hashlib.md5(f"{user_id}_{token}_{time.time()}".encode()).hexdigest()[:10]
        bot_dir = os.path.join(RUNNING_DIR, bot_id)
        os.makedirs(bot_dir, exist_ok=True)
        
        # اجرا
        success, pid, error = bot_manager.run_bot(bot_id, file_path, bot_dir)
        
        if success:
            expires_at = (datetime.now() + timedelta(days=30)).isoformat()
            
            with get_db() as conn:
                conn.execute('UPDATE pending_files SET status = 'approved', reviewed_at = ?, auto_approved = 1 WHERE id = ?',
                           (datetime.now().isoformat(), pending_id))
                conn.execute('''
                    INSERT INTO bots (id, user_id, subscription_id, token, name, username, file_path, 
                                    folder_path, pid, status, created_at, expires_at)
                    VALUES (?, ?, (SELECT subscription_id FROM pending_files WHERE id = ?), ?, ?, ?, ?, ?, ?, 'running', ?, ?)
                ''', (bot_id, user_id, pending_id, token, bot_info['first_name'], bot_info['username'],
                      file_path, bot_dir, pid, datetime.now().isoformat(), expires_at))
                conn.execute('UPDATE users SET total_bots = total_bots + 1 WHERE user_id = ?', (user_id,))
                conn.commit()
            
            bot.send_message(chat_id, f"✅ **ربات شما ساخته شد!** 🎉\n\n"
                             f"🤖 نام: {bot_info['first_name']}\n"
                             f"🔗 لینک: https://t.me/{bot_info['username']}\n"
                             f"🆔 آیدی: {bot_id}\n"
                             f"📅 اعتبار: ۳۰ روز\n\n"
                             f"از منوی «ربات‌های من» مدیریت کنید.")
        else:
            bot.send_message(chat_id, f"❌ خطا در اجرای ربات: {error}")
            
    except Exception as e:
        bot.send_message(chat_id, f"❌ خطا: {str(e)}")

# ربات‌های من
@bot.message_handler(func=lambda m: m.text == '🤖 ربات‌های من')
def my_bots(message):
    user_id = message.from_user.id
    bots = user_manager.get_user_bots(user_id)
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما رباتی ندارید!\nبرای ساخت ربات، ابتدا اشتراک بخرید.")
        return
    
    for b in bots:
        # بررسی وضعیت
        is_running = False
        if b['pid']:
            try:
                os.kill(b['pid'], 0)
                is_running = True
            except:
                pass
        
        status_emoji = "🟢" if is_running else "🔴"
        status_text = "در حال اجرا" if is_running else "متوقف"
        
        expires = datetime.fromisoformat(b['expires_at']).strftime('%Y-%m-%d') if b['expires_at'] else 'نامحدود'
        
        text = f"{status_emoji} **{b['name']}**\n"
        text += f"🔗 https://t.me/{b['username']}\n"
        text += f"🆔 `{b['id']}`\n"
        text += f"📊 وضعیت: {status_text}\n"
        text += f"📅 انقضا: {expires}\n"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🔄 توقف/اجرا", callback_data=f"toggle_bot_{b['id']}"),
            types.InlineKeyboardButton("🗑 حذف", callback_data=f"delete_bot_{b['id']}")
        )
        
        bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_bot_'))
def toggle_bot(call):
    bot_id = call.data.replace('toggle_bot_', '')
    user_id = call.from_user.id
    
    with get_db() as conn:
        bot_info = conn.execute('SELECT * FROM bots WHERE id = ? AND user_id = ?', (bot_id, user_id)).fetchone()
    
    if not bot_info:
        bot.answer_callback_query(call.id, "❌ ربات پیدا نشد!")
        return
    
    if bot_info['status'] == 'running':
        success = bot_manager.stop_bot(bot_id, bot_info['pid'])
        if success:
            with get_db() as conn:
                conn.execute('UPDATE bots SET status = 'stopped' WHERE id = ?', (bot_id,))
                conn.commit()
            bot.answer_callback_query(call.id, "✅ ربات متوقف شد")
        else:
            bot.answer_callback_query(call.id, "❌ خطا در توقف!")
    else:
        # ریستارت
        success, msg = bot_manager.restart_bot(bot_id, user_id, bot_info['file_path'], bot_info['pid'])
        if success:
            bot.answer_callback_query(call.id, "✅ ربات اجرا شد")
        else:
            bot.answer_callback_query(call.id, f"❌ {msg[:50]}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_bot_'))
def delete_bot_cmd(call):
    bot_id = call.data.replace('delete_bot_', '')
    user_id = call.from_user.id
    
    with get_db() as conn:
        bot_info = conn.execute('SELECT * FROM bots WHERE id = ? AND user_id = ?', (bot_id, user_id)).fetchone()
    
    if not bot_info:
        bot.answer_callback_query(call.id, "❌ ربات پیدا نشد!")
        return
    
    # توقف ربات
    if bot_info['pid']:
        bot_manager.stop_bot(bot_id, bot_info['pid'])
    
    # حذف فایل‌ها
    if bot_info['folder_path'] and os.path.exists(bot_info['folder_path']):
        shutil.rmtree(bot_info['folder_path'])
    
    with get_db() as conn:
        conn.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
        conn.commit()
    
    bot.answer_callback_query(call.id, "✅ ربات حذف شد")
    bot.edit_message_text("🗑 ربات حذف شد.", call.message.chat.id, call.message.message_id)

# نصب کتابخانه
@bot.message_handler(func=lambda m: m.text == '📦 نصب کتابخانه')
def install_library(message):
    categories = lib_manager.get_libraries_by_category()
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    category_names = {
        'web': '🌐 وب', 'data': '📊 داده', 'ai': '🤖 هوش مصنوعی',
        'media': '🎬 رسانه', 'telegram': '📱 تلگرام', 'scraping': '🕷️ اسکرپینگ',
        'security': '🔒 امنیت', 'download': '⬇️ دانلود', 'database': '🗄️ دیتابیس',
        'office': '📄 آفیس', 'graphics': '🎨 گرافیک', 'tools': '🛠️ ابزارها',
        'i18n': '🌍 بین‌المللی', 'network': '🌐 شبکه', 'testing': '🧪 تست',
        'finance': '💰 مالی', 'ocr': '📖 OCR', 'audio': '🎵 صدا'
    }
    
    for cat in categories.keys():
        name = category_names.get(cat, cat)
        markup.add(types.InlineKeyboardButton(name, callback_data=f"lib_cat_{cat}"))
    
    bot.send_message(message.chat.id, "📦 دسته کتابخانه را انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lib_cat_'))
def show_category_libs(call):
    category = call.data.replace('lib_cat_', '')
    
    libs = lib_manager.get_libraries_by_category().get(category, [])
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for lib in libs:
        installed = "✅ " if lib['is_installed'] else ""
        markup.add(types.InlineKeyboardButton(
            f"{installed}{lib['name']} v{lib['version']}",
            callback_data=f"install_lib_{lib['name']}"
        ))
    
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="lib_back"))
    
    bot.edit_message_text(f"📦 کتابخانه‌های دسته {category}:", 
                          call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('install_lib_'))
def install_lib_callback(call):
    lib_name = call.data.replace('install_lib_', '')
    
    bot.answer_callback_query(call.id, f"در حال نصب {lib_name}...")
    
    success, msg = lib_manager.install_library(lib_name, call.message.chat.id)
    
    if success:
        bot.send_message(call.message.chat.id, msg)
    else:
        bot.send_message(call.message.chat.id, msg)

@bot.callback_query_handler(func=lambda call: call.data == "lib_back")
def lib_back(call):
    install_library(call.message)

# وضعیت من
@bot.message_handler(func=lambda m: m.text == '📊 وضعیت من')
def my_status(message):
    user_id = message.from_user.id
    
    with get_db() as conn:
        user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
        bots_count = conn.execute('SELECT COUNT(*) FROM bots WHERE user_id = ?', (user_id,)).fetchone()[0]
        total_spent = conn.execute('SELECT COALESCE(SUM(amount), 0) FROM receipts WHERE user_id = ? AND status = 'approved'', (user_id,)).fetchone()[0]
    
    if user:
        has_sub = user['active_subscription'] == 1
        expire = datetime.fromisoformat(user['subscription_end']).strftime('%Y-%m-%d') if user['subscription_end'] else 'ندارد'
        
        text = f"📊 **وضعیت حساب شما**\n\n"
        text += f"👤 نام: {user['first_name']}\n"
        text += f"🆔 آیدی: {user_id}\n"
        text += f"✅ اشتراک: {'فعال' if has_sub else 'غیرفعال'}\n"
        text += f"📅 انقضا: {expire}\n"
        text += f"🤖 تعداد ربات‌ها: {bots_count}\n"
        text += f"💰 مجموع پرداختی: {total_spent:,} تومان\n"
        text += f"📅 تاریخ عضویت: {user['created_at'][:10] if user['created_at'] else 'ندارد'}"
        
        bot.send_message(message.chat.id, text, parse_mode="Markdown")

# راهنما
@bot.message_handler(func=lambda m: m.text == '📚 راهنما')
def guide(message):
    text = f"""📚 **راهنمای کامل**

1️⃣ **خرید اشتراک**
   • مبلغ: {PRICE:,} تومان
   • شماره کارت: `{CARD_NUMBER}`

2️⃣ **ارسال فایل ربات**
   • فایل `.py` خود را ارسال کنید
   • سیستم با AI بررسی می‌کند

3️⃣ **مدیریت ربات‌ها**
   • از منوی «ربات‌های من»
   • توقف، اجرا، حذف

4️⃣ **نصب کتابخانه**
   • ۱۰۰+ کتابخانه آماده
   • نصب خودکار با یک کلیک

📞 پشتیبانی: @shahraghee13"""
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# پشتیبانی
@bot.message_handler(func=lambda m: m.text == '📞 پشتیبانی')
def support(message):
    bot.send_message(message.chat.id, "📞 **پشتیبانی**\n\nآیدی: @shahraghee13\n\nسوالات خود را بپرسید.")

# پنل ادمین
@bot.message_handler(func=lambda m: m.text == '👑 پنل ادمین')
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ دسترسی ندارید!")
        return
    
    markup = get_admin_menu()
    bot.send_message(message.chat.id, "👑 **پنل مدیریت**", parse_mode="Markdown", reply_markup=markup)

# ادمین - فیش‌ها
@bot.callback_query_handler(func=lambda call: call.data == "admin_receipts")
def admin_receipts(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        receipts = conn.execute('''
            SELECT r.*, u.first_name, s.subscription_code
            FROM receipts r
            JOIN users u ON r.user_id = u.user_id
            JOIN subscriptions s ON r.subscription_id = s.id
            WHERE r.status = 'pending'
            ORDER BY r.created_at DESC
        ''').fetchall()
    
    if not receipts:
        bot.send_message(call.message.chat.id, "📸 هیچ فیش در انتظاری وجود ندارد")
        return
    
    for r in receipts:
        text = f"📸 **فیش واریز**\n\n"
        text += f"👤 کاربر: {r['first_name']} (🆔 {r['user_id']})\n"
        text += f"💰 مبلغ: {r['amount']:,} تومان\n"
        text += f"🆔 کد اشتراک: {r['subscription_code']}\n"
        text += f"🆔 کد پرداخت: {r['payment_code']}\n"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_pay_{r['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"reject_pay_{r['id']}")
        )
        
        if os.path.exists(r['receipt_path']):
            with open(r['receipt_path'], 'rb') as f:
                bot.send_photo(call.message.chat.id, f, caption=text, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_pay_'))
def approve_payment(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    receipt_id = int(call.data.replace('approve_pay_', ''))
    
    with get_db() as conn:
        receipt = conn.execute('SELECT * FROM receipts WHERE id = ?', (receipt_id,)).fetchone()
        if receipt:
            user_manager.activate_subscription(receipt['subscription_id'])
            conn.execute('UPDATE receipts SET status = 'approved', reviewed_at = ?, reviewed_by = ? WHERE id = ?',
                        (datetime.now().isoformat(), call.from_user.id, receipt_id))
            conn.commit()
            
            try:
                bot.send_message(receipt['user_id'], "✅ پرداخت شما تایید شد! اشتراک شما فعال شد.\n📤 حالا می‌توانید فایل ربات خود را ارسال کنید.")
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
    
    msg = bot.send_message(call.message.chat.id, "دلیل رد پرداخت را وارد کنید:")
    bot.register_next_step_handler(msg, lambda m: process_reject_payment(m, receipt_id, call))

def process_reject_payment(message, receipt_id, original_call):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    with get_db() as conn:
        receipt = conn.execute('SELECT user_id FROM receipts WHERE id = ?', (receipt_id,)).fetchone()
        if receipt:
            conn.execute('UPDATE receipts SET status = 'rejected', reviewed_at = ?, reviewed_by = ?, rejection_reason = ? WHERE id = ?',
                        (datetime.now().isoformat(), message.from_user.id, message.text, receipt_id))
            conn.commit()
            
            try:
                bot.send_message(receipt['user_id'], f"❌ پرداخت شما رد شد.\nدلیل: {message.text}\nبا پشتیبانی تماس بگیرید.")
            except:
                pass
    
    bot.reply_to(message, "✅ رد شد")
    try:
        bot.delete_message(original_call.message.chat.id, original_call.message.message_id)
    except:
        pass

# ادمین - فایل‌های در انتظار
@bot.callback_query_handler(func=lambda call: call.data == "admin_pending")
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
            ORDER BY pf.security_score DESC, pf.submitted_at ASC
        ''').fetchall()
    
    if not files:
        bot.send_message(call.message.chat.id, "📥 هیچ فایل در انتظاری وجود ندارد")
        return
    
    for f in files:
        text = f"📥 **فایل در انتظار**\n\n"
        text += f"👤 کاربر: {f['first_name']} (🆔 {f['user_id']})\n"
        text += f"📄 فایل: {f['file_name']}\n"
        text += f"🤖 امتیاز AI: {f['security_score']}/100\n"
        text += f"🛡️ سطح: {f['security_level']}\n"
        text += f"🆔 ID: {f['id']}\n\n"
        text += f"{f['security_report'][:300] if f['security_report'] else ''}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_file_{f['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"reject_file_{f['id']}")
        )
        
        if os.path.exists(f['file_path']):
            with open(f['file_path'], 'rb') as file:
                bot.send_document(call.message.chat.id, file, caption=text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_file_'))
def approve_file(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    pending_id = int(call.data.replace('approve_file_', ''))
    
    with get_db() as conn:
        pending = conn.execute('SELECT * FROM pending_files WHERE id = ?', (pending_id,)).fetchone()
        if not pending:
            bot.answer_callback_query(call.id, "❌ فایل پیدا نشد!")
            return
        
        # خواندن کد
        with open(pending['file_path'], 'r', encoding='utf-8') as f:
            code = f.read()
        
        # استخراج توکن
        token = None
        token_patterns = [r'token\s*=\s*["\']([^"\']+)["\']', r'TOKEN\s*=\s*["\']([^"\']+)["\']']
        for pattern in token_patterns:
            match = re.search(pattern, code, re.IGNORECASE)
            if match:
                token = match.group(1)
                break
        
        if not token:
            bot.answer_callback_query(call.id, "❌ توکن پیدا نشد!")
            return
        
        # بررسی توکن
        response = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
        if response.status_code != 200:
            bot.answer_callback_query(call.id, "❌ توکن نامعتبر!")
            return
        
        bot_data = response.json()['result']
        
        # ساخت ربات
        bot_id = hashlib.md5(f"{pending['user_id']}_{token}_{time.time()}".encode()).hexdigest()[:10]
        bot_dir = os.path.join(RUNNING_DIR, bot_id)
        os.makedirs(bot_dir, exist_ok=True)
        
        success, pid, error = bot_manager.run_bot(bot_id, pending['file_path'], bot_dir)
        
        if success:
            expires_at = (datetime.now() + timedelta(days=30)).isoformat()
            
            conn.execute('UPDATE pending_files SET status = 'approved', reviewed_at = ? WHERE id = ?',
                        (datetime.now().isoformat(), pending_id))
            conn.execute('''
                INSERT INTO bots (id, user_id, subscription_id, token, name, username, file_path, 
                                folder_path, pid, status, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'running', ?, ?)
            ''', (bot_id, pending['user_id'], pending['subscription_id'], token, bot_data['first_name'],
                  bot_data['username'], pending['file_path'], bot_dir, pid, datetime.now().isoformat(), expires_at))
            conn.execute('UPDATE users SET total_bots = total_bots + 1 WHERE user_id = ?', (pending['user_id'],))
            conn.commit()
            
            try:
                bot.send_message(pending['user_id'], f"✅ ربات شما ساخته شد! 🎉\n🤖 {bot_data['first_name']}\n🔗 https://t.me/{bot_data['username']}")
            except:
                pass
            
            bot.answer_callback_query(call.id, "✅ ربات ساخته شد")
            bot.delete_message(call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, f"❌ خطا: {error[:50]}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_file_'))
def reject_file(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    pending_id = int(call.data.replace('reject_file_', ''))
    
    msg = bot.send_message(call.message.chat.id, "دلیل رد فایل را وارد کنید:")
    bot.register_next_step_handler(msg, lambda m: process_reject_file(m, pending_id, call))

def process_reject_file(message, pending_id, original_call):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    with get_db() as conn:
        pending = conn.execute('SELECT user_id FROM pending_files WHERE id = ?', (pending_id,)).fetchone()
        if pending:
            conn.execute('UPDATE pending_files SET status = 'rejected', review_note = ?, reviewed_at = ? WHERE id = ?',
                        (message.text, datetime.now().isoformat(), pending_id))
            conn.commit()
            
            try:
                bot.send_message(pending['user_id'], f"❌ فایل شما رد شد.\nدلیل: {message.text}")
            except:
                pass
    
    bot.reply_to(message, "✅ رد شد")
    try:
        bot.delete_message(original_call.message.chat.id, original_call.message.message_id)
    except:
        pass

# ادمین - کاربران
@bot.callback_query_handler(func=lambda call: call.data == "admin_users")
def admin_users_menu(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📋 لیست کاربران", callback_data="admin_user_list"),
        types.InlineKeyboardButton("❌ حذف کاربر", callback_data="admin_user_delete"),
        types.InlineKeyboardButton("💰 افزایش اشتراک", callback_data="admin_user_extend"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    bot.edit_message_text("👥 **مدیریت کاربران**", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_user_list")
def admin_user_list(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        users = conn.execute('''
            SELECT user_id, first_name, active_subscription, subscription_end, total_bots, created_at
            FROM users ORDER BY created_at DESC LIMIT 30
        ''').fetchall()
    
    text = "👥 **۳۰ کاربر آخر**\n\n"
    for u in users:
        status = "✅" if u['active_subscription'] else "❌"
        expire = datetime.fromisoformat(u['subscription_end']).strftime('%Y-%m-%d') if u['subscription_end'] else 'ندارد'
        text += f"{status} {u['first_name']} (🆔 {u['user_id']})\n"
        text += f"   🤖 {u['total_bots']} | 📅 {expire}\n"
        text += f"   🗓️ {u['created_at'][:10]}\n\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_user_delete")
def admin_user_delete_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "🆔 آیدی کاربر مورد نظر برای حذف را وارد کنید:")
    bot.register_next_step_handler(msg, process_user_delete)

def process_user_delete(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        user_id = int(message.text.strip())
        user_manager.delete_user(user_id)
        bot.reply_to(message, f"✅ کاربر {user_id} و تمام ربات‌هایش حذف شدند.")
    except:
        bot.reply_to(message, "❌ خطا در حذف کاربر")

# ادمین - ربات‌ها
@bot.callback_query_handler(func=lambda call: call.data == "admin_bots")
def admin_bots_menu(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        bots = conn.execute('''
            SELECT b.*, u.first_name
            FROM bots b
            JOIN users u ON b.user_id = u.user_id
            ORDER BY b.created_at DESC LIMIT 30
        ''').fetchall()
    
    if not bots:
        bot.send_message(call.message.chat.id, "📋 هیچ رباتی وجود ندارد")
        return
    
    for b in bots:
        text = f"🤖 **{b['name']}**\n"
        text += f"👤 کاربر: {b['first_name']} (🆔 {b['user_id']})\n"
        text += f"📊 وضعیت: {b['status']}\n"
        text += f"📅 ساخته: {b['created_at'][:10]}\n"
        text += f"📅 انقضا: {b['expires_at'][:10] if b['expires_at'] else 'نامحدود'}\n"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🔄 ریستارت", callback_data=f"admin_restart_{b['id']}"),
            types.InlineKeyboardButton("🗑 حذف", callback_data=f"admin_del_bot_{b['id']}")
        )
        
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_restart_'))
def admin_restart_bot(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    bot_id = call.data.replace('admin_restart_', '')
    
    with get_db() as conn:
        bot_info = conn.execute('SELECT user_id, file_path, pid FROM bots WHERE id = ?', (bot_id,)).fetchone()
    
    if bot_info:
        success, msg = bot_manager.restart_bot(bot_id, bot_info['user_id'], bot_info['file_path'], bot_info['pid'])
        if success:
            bot.answer_callback_query(call.id, "✅ ربات ریستارت شد")
        else:
            bot.answer_callback_query(call.id, f"❌ {msg[:50]}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_del_bot_'))
def admin_delete_bot(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    bot_id = call.data.replace('admin_del_bot_', '')
    
    with get_db() as conn:
        bot_info = conn.execute('SELECT user_id, pid, folder_path FROM bots WHERE id = ?', (bot_id,)).fetchone()
    
    if bot_info:
        if bot_info['pid']:
            bot_manager.stop_bot(bot_id, bot_info['pid'])
        if bot_info['folder_path'] and os.path.exists(bot_info['folder_path']):
            shutil.rmtree(bot_info['folder_path'])
        conn.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
        conn.commit()
        bot.answer_callback_query(call.id, "✅ ربات حذف شد")
        bot.delete_message(call.message.chat.id, call.message.message_id)

# ادمین - سرورها
@bot.callback_query_handler(func=lambda call: call.data == "admin_servers")
def admin_servers_menu(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("➕ افزودن سرور", callback_data="admin_add_server"),
        types.InlineKeyboardButton("📋 لیست سرورها", callback_data="admin_list_servers"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    bot.edit_message_text("🖥️ **مدیریت سرورها**", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_add_server")
def admin_add_server_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, 
        "🖥️ **افزودن سرور جدید**\n\n"
        "اطلاعات را به صورت زیر وارد کنید:\n"
        "`نام|آیپی|پورت|یوزرنیم|رمز`\n\n"
        "مثال:\n"
        "`Server1|192.168.1.100|22|root|password123`")
    
    bot.register_next_step_handler(msg, process_add_server)

def process_add_server(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        parts = message.text.split('|')
        if len(parts) < 5:
            bot.reply_to(message, "❌ فرمت صحیح نیست! نام|آیپی|پورت|یوزرنیم|رمز")
            return
        
        name, host, port, username, password = parts[0].strip(), parts[1].strip(), int(parts[2].strip()), parts[3].strip(), parts[4].strip()
        
        status_msg = bot.reply_to(message, "🔄 در حال اتصال به سرور...")
        
        result = load_balancer.add_server(name, host, port, username, password)
        
        if result['success']:
            bot.edit_message_text(f"✅ {result['message']}\n💻 هسته‌ها: {result.get('cpu_cores', '?')}\n📦 رم: {result.get('memory_mb', '?')} MB", 
                                  message.chat.id, status_msg.message_id)
        else:
            bot.edit_message_text(f"❌ {result['message']}", message.chat.id, status_msg.message_id)
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_list_servers")
def admin_list_servers(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        servers = conn.execute('SELECT * FROM servers ORDER BY created_at DESC').fetchall()
    
    if not servers:
        bot.send_message(call.message.chat.id, "📋 هیچ سروری ثبت نشده است")
        return
    
    for s in servers:
        status = "🟢" if s['status'] == 'active' else "🔴"
        text = f"{status} **{s['name']}**\n"
        text += f"🌐 {s['host']}:{s['port']}\n"
        text += f"💻 CPU: {s['cpu_usage']:.1f}% | RAM: {s['memory_usage']:.1f}%\n"
        text += f"🤖 ربات‌ها: {s['running_bots']}/{s['max_bots']}\n"
        text += f"📊 بار: {s['load_average']}\n"
        
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

# ادمین - آمار
@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_stats_full(call):
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
        pending_payments = conn.execute('SELECT COUNT(*) FROM receipts WHERE status = 'pending'').fetchone()[0]
        pending_files = conn.execute('SELECT COUNT(*) FROM pending_files WHERE status = 'pending'').fetchone()[0]
        total_servers = conn.execute('SELECT COUNT(*) FROM servers').fetchone()[0]
    
    text = f"📊 **آمار پیشرفته**\n\n"
    text += f"👥 **کاربران**\n"
    text += f"• کل: {total_users}\n"
    text += f"• اشتراک فعال: {active_subs}\n\n"
    text += f"🤖 **ربات‌ها**\n"
    text += f"• کل: {total_bots}\n"
    text += f"• در حال اجرا: {running_bots}\n\n"
    text += f"💰 **مالی**\n"
    text += f"• مجموع فروش: {total_amount:,} تومان\n"
    text += f"• تراکنش‌ها: {total_payments}\n"
    text += f"• در انتظار: {pending_payments}\n\n"
    text += f"📥 **فایل‌های در انتظار**: {pending_files}\n"
    text += f"🖥️ **سرورها**: {total_servers}"
    
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

# ادمین - تایید دستی اشتراک
@bot.callback_query_handler(func=lambda call: call.data == "admin_manual")
def admin_manual_prompt(call):
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
        
        sub_id, sub_code = user_manager.create_subscription(user_id, PRICE)
        user_manager.activate_subscription(sub_id)
        
        try:
            bot.send_message(user_id, "✅ اشتراک شما به صورت دستی فعال شد! حالا می‌توانید فایل ربات خود را ارسال کنید.")
        except:
            pass
        
        bot.reply_to(message, f"✅ اشتراک کاربر {user_id} فعال شد")
    except:
        bot.reply_to(message, "❌ آیدی نامعتبر!")

# ادمین - تنظیمات
@bot.callback_query_handler(func=lambda call: call.data == "admin_settings")
def admin_settings(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("💰 تغییر قیمت", callback_data="admin_set_price"),
        types.InlineKeyboardButton("💳 تغییر شماره کارت", callback_data="admin_set_card"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    with get_db() as conn:
        price = conn.execute('SELECT value FROM system_config WHERE key = 'price'').fetchone()
        card = conn.execute('SELECT value FROM system_config WHERE key = 'card_number'').fetchone()
    
    text = f"⚙️ **تنظیمات**\n\n"
    text += f"💰 قیمت: {price['value'] if price else PRICE:,} تومان\n"
    text += f"💳 شماره کارت: `{card['value'] if card else CARD_NUMBER}`"
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_price")
def admin_set_price(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "💰 قیمت جدید را به تومان وارد کنید:")
    bot.register_next_step_handler(msg, process_set_price)

def process_set_price(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        new_price = int(message.text.strip())
        with get_db() as conn:
            conn.execute('UPDATE system_config SET value = ?, updated_at = ? WHERE key = 'price'', (str(new_price), datetime.now().isoformat()))
            conn.commit()
        bot.reply_to(message, f"✅ قیمت به {new_price:,} تومان تغییر کرد")
    except:
        bot.reply_to(message, "❌ قیمت نامعتبر!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_card")
def admin_set_card(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "💳 شماره کارت جدید را وارد کنید:")
    bot.register_next_step_handler(msg, process_set_card)

def process_set_card(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    card = message.text.strip()
    if len(card) >= 16 and card.isdigit():
        with get_db() as conn:
            conn.execute('UPDATE system_config SET value = ?, updated_at = ? WHERE key = 'card_number'', (card, datetime.now().isoformat()))
            conn.commit()
        bot.reply_to(message, f"✅ شماره کارت به {card} تغییر کرد")
    else:
        bot.reply_to(message, "❌ شماره کارت نامعتبر!")

# بازگشت
@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call):
    user_id = call.from_user.id
    is_admin = user_id in ADMIN_IDS
    markup = get_main_menu(is_admin)
    
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "🚀 منوی اصلی:", reply_markup=markup)

# ==================== تسک‌های زمانبندی ====================

def scheduled_tasks():
    """اجرای تسک‌های زمانبندی شده"""
    while True:
        try:
            SubscriptionNotifier.check_and_notify()
            time.sleep(3600)  # هر ساعت
        except Exception as e:
            logger.error(f"خطا در تسک زمانبندی: {e}")
            time.sleep(300)

# ==================== اجرا ====================

if __name__ == "__main__":
    print("=" * 70)
    print("🚀 ربات مادر Ultimate - نسخه نهایی حرفه‌ای")
    print("=" * 70)
    print(f"✅ دیتابیس: SQLite با WAL mode")
    print(f"✅ سیستم امنیت: هوش مصنوعی فعال")
    print(f"✅ مدیریت ربات: پیشرفته")
    print(f"✅ کتابخانه‌ها: ۱۰۰+ کتابخانه")
    print(f"✅ ادمین‌ها: {ADMIN_IDS}")
    print("=" * 70)
    
    # مقداردهی اولیه دیتابیس
    DatabaseManager.init_db()
    
    # شروع تسک زمانبندی
    scheduler = threading.Thread(target=scheduled_tasks, daemon=True)
    scheduler.start()
    
    # اجرای ربات
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            logger.error(f"خطا: {e}")
            time.sleep(5)