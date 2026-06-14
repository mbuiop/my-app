#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ربات مادر حرفه‌ای - نسخه نهایی با سیستم توزیع بار، هوش مصنوعی، و مدیریت پیشرفته
نسخه 10.0 - Enterprise Ready
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
import aiohttp
import socket
import dns.resolver
import ping3
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from contextlib import contextmanager
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import psutil
import redis
from celery import Celery
import jwt
from cryptography.fernet import Fernet
import bcrypt
from ratelimit import limits, sleep_and_retry
import ast
import astor
from bandit import Bandit
import radon
from radon.complexity import cc_visit
from radon.metrics import mi_visit
import black
from pylint import lint
from pylint.reporters import BaseReporter
import subprocess
from io import StringIO

# ==================== تنظیمات پایه ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "database")
FILES_DIR = os.path.join(BASE_DIR, "user_files")
RUNNING_DIR = os.path.join(BASE_DIR, "running_bots")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
RECEIPTS_DIR = os.path.join(BASE_DIR, "receipts")
PENDING_FILES_DIR = os.path.join(BASE_DIR, "pending_files")
SERVERS_DIR = os.path.join(BASE_DIR, "servers")
SSL_DIR = os.path.join(BASE_DIR, "ssl")

for dir_path in [DB_DIR, FILES_DIR, RUNNING_DIR, LOGS_DIR, RECEIPTS_DIR, PENDING_FILES_DIR, SERVERS_DIR, SSL_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# ==================== توکن و امنیت ====================
BOT_TOKEN = os.environ.get("7685135237:AAEmsHktRw9cEqrHTkCoPZk-fBimK7TDjOo", "7685135237:AAEmsHktRw9cEqrHTkCoPZk-fBimK7TDjOo")
bot = telebot.TeleBot(BOT_TOKEN)
bot.delete_webhook()

ADMIN_IDS = [int(id.strip()) for id in os.environ.get("327855654", "327855654").split(",")]

# کلید رمزگذاری
ENCRYPTION_KEY = Fernet.generate_key()
cipher = Fernet(ENCRYPTION_KEY)

# ==================== دیتابیس پیشرفته با Redis Cache ====================
DB_PATH = os.path.join(DB_DIR, 'mother_bot.db')

# اتصال Redis برای کش (در صورت وجود)
try:
    redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True, socket_connect_timeout=2)
    redis_client.ping()
    REDIS_AVAILABLE = True
    print("✅ Redis متصل شد - کش فعال است")
except:
    REDIS_AVAILABLE = False
    print("⚠️ Redis یافت نشد - از کش دیتابیس استفاده می‌شود")

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=60, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA cache_size=-131072")  # 128MB cache
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# ==================== مدل‌های دیتابیس ====================

def init_database():
    """ایجاد تمام جداول با ساختار پیشرفته"""
    with get_db() as conn:
        # جدول سرورها
        conn.execute('''
            CREATE TABLE IF NOT EXISTS servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                host TEXT UNIQUE,
                port INTEGER DEFAULT 22,
                username TEXT,
                password_encrypted TEXT,
                ssh_key TEXT,
                status TEXT DEFAULT 'active',
                cpu_usage REAL DEFAULT 0,
                memory_usage REAL DEFAULT 0,
                disk_usage REAL DEFAULT 0,
                load_average REAL DEFAULT 0,
                running_bots INTEGER DEFAULT 0,
                max_bots INTEGER DEFAULT 10,
                last_check TIMESTAMP,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        ''')
        
        # جدول کاربران پیشرفته
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                email TEXT,
                phone TEXT,
                active_subscription INTEGER DEFAULT 0,
                subscription_type TEXT DEFAULT 'monthly',
                subscription_start TIMESTAMP,
                subscription_end TIMESTAMP,
                balance INTEGER DEFAULT 0,
                created_at TIMESTAMP,
                last_active TIMESTAMP,
                is_banned INTEGER DEFAULT 0,
                ban_reason TEXT
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
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        # جدول ربات‌ها با پشتیبانی از سرورهای مختلف
        conn.execute('''
            CREATE TABLE IF NOT EXISTS bots (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                server_id INTEGER,
                subscription_id INTEGER,
                token TEXT,
                name TEXT,
                username TEXT,
                file_path TEXT,
                folder_path TEXT,
                pid INTEGER,
                port INTEGER,
                status TEXT DEFAULT 'stopped',
                created_at TIMESTAMP,
                last_active TIMESTAMP,
                expires_at TIMESTAMP,
                warning_sent INTEGER DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY(server_id) REFERENCES servers(id),
                FOREIGN KEY(subscription_id) REFERENCES subscriptions(id)
            )
        ''')
        
        # جدول فایل‌های در انتظار با سیستم AI
        conn.execute('''
            CREATE TABLE IF NOT EXISTS pending_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                subscription_id INTEGER,
                file_path TEXT,
                file_name TEXT,
                status TEXT DEFAULT 'pending',
                ai_score REAL DEFAULT 0,
                ai_report TEXT,
                security_level TEXT,
                submitted_at TIMESTAMP,
                reviewed_at TIMESTAMP,
                review_note TEXT,
                auto_approved INTEGER DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(subscription_id) REFERENCES subscriptions(id)
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
                created_at TIMESTAMP,
                reviewed_at TIMESTAMP,
                reviewed_by INTEGER
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
                is_installed INTEGER DEFAULT 0
            )
        ''')
        
        # جدول لاگ‌های امنیتی
        conn.execute('''
            CREATE TABLE IF NOT EXISTS security_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                file_name TEXT,
                ai_score REAL,
                verdict TEXT,
                created_at TIMESTAMP
            )
        ''')
        
        # ایجاد ایندکس‌ها
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_subscription ON users(active_subscription, subscription_end)",
            "CREATE INDEX IF NOT EXISTS idx_bots_user ON bots(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_bots_server ON bots(server_id, status)",
            "CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id, status)",
            "CREATE INDEX IF NOT EXISTS idx_pending_files_status ON pending_files(status, ai_score)",
            "CREATE INDEX IF NOT EXISTS idx_servers_status ON servers(status, load_average)"
        ]
        
        for idx in indexes:
            conn.execute(idx)
        
        conn.commit()
        
        # پر کردن کتابخانه‌های پیش‌فرض
        populate_libraries(conn)

def populate_libraries(conn):
    """پر کردن جدول کتابخانه‌ها با ۱۰۰+ کتابخانه کاربردی"""
    libraries = [
        # وب و API
        ("requests", "2.31.0", "HTTP library for Python", "web"),
        ("aiohttp", "3.9.0", "Async HTTP client/server", "web"),
        ("fastapi", "0.104.0", "Modern web framework", "web"),
        ("flask", "3.0.0", "Micro web framework", "web"),
        ("django", "5.0.0", "High-level web framework", "web"),
        ("httpx", "0.25.0", "Next-gen HTTP client", "web"),
        ("websockets", "12.0", "WebSocket implementation", "web"),
        ("sanic", "23.12.0", "Async web framework", "web"),
        
        # دیتابیس
        ("sqlalchemy", "2.0.23", "SQL toolkit", "database"),
        ("asyncpg", "0.29.0", "PostgreSQL driver", "database"),
        ("aiomysql", "0.2.0", "MySQL driver", "database"),
        ("redis", "5.0.1", "Redis client", "database"),
        ("motor", "3.3.2", "MongoDB driver", "database"),
        ("peewee", "3.17.0", "Small ORM", "database"),
        
        # علم داده و AI
        ("numpy", "1.26.0", "Numerical computing", "data"),
        ("pandas", "2.1.0", "Data analysis", "data"),
        ("scikit-learn", "1.3.0", "Machine learning", "ai"),
        ("tensorflow", "2.13.0", "Deep learning", "ai"),
        ("torch", "2.1.0", "PyTorch", "ai"),
        ("transformers", "4.35.0", "Hugging Face", "ai"),
        ("langchain", "0.0.340", "LLM framework", "ai"),
        ("openai", "1.3.0", "OpenAI API", "ai"),
        ("anthropic", "0.7.0", "Claude API", "ai"),
        
        # پردازش تصویر و ویدیو
        ("pillow", "10.1.0", "Image processing", "media"),
        ("opencv-python", "4.8.1", "Computer vision", "media"),
        ("moviepy", "1.0.3", "Video editing", "media"),
        ("qrcode", "7.4.2", "QR code generation", "media"),
        ("pywhatkit", "5.4", "WhatsApp automation", "media"),
        
        # تلگرام
        ("pyTelegramBotAPI", "4.13.0", "Telegram Bot API", "telegram"),
        ("aiogram", "3.1.1", "Async Telegram Bot", "telegram"),
        ("python-telegram-bot", "20.6", "Telegram Bot API", "telegram"),
        ("telethon", "1.34.0", "Telegram client", "telegram"),
        
        # اسکرپینگ
        ("beautifulsoup4", "4.12.2", "HTML parsing", "scraping"),
        ("selenium", "4.15.0", "Browser automation", "scraping"),
        ("scrapy", "2.11.0", "Web crawling", "scraping"),
        ("playwright", "1.40.0", "Browser automation", "scraping"),
        
        # امنیت
        ("cryptography", "41.0.7", "Cryptographic recipes", "security"),
        ("pyjwt", "2.8.0", "JWT implementation", "security"),
        ("passlib", "1.7.4", "Password hashing", "security"),
        ("bcrypt", "4.0.1", "Password hashing", "security"),
        
        # یوتیوب و دانلود
        ("yt-dlp", "2023.11.16", "YouTube downloader", "download"),
        ("pytube", "15.0.0", "YouTube downloader", "download"),
        ("requests-html", "0.10.0", "HTML parsing", "scraping"),
        
        # مالی و ارز
        ("forex-python", "1.8", "Forex rates", "finance"),
        ("cryptocompare", "0.7", "Crypto prices", "finance"),
        
        # ابزارها
        ("loguru", "0.7.2", "Logging made easy", "tools"),
        ("tqdm", "4.66.1", "Progress bars", "tools"),
        ("click", "8.1.7", "CLI framework", "tools"),
        ("rich", "13.7.0", "Rich text formatting", "tools"),
        ("colorama", "0.4.6", "ANSI colors", "tools"),
        ("python-dotenv", "1.0.0", "Environment variables", "tools"),
        ("schedule", "1.2.0", "Task scheduling", "tools"),
        ("apscheduler", "3.10.4", "Advanced scheduling", "tools"),
        ("celery", "5.3.4", "Task queue", "tools"),
        
        # بین‌المللی
        ("jdatetime", "4.1.0", "Jalali calendar", "i18n"),
        ("pytz", "2023.3", "Timezones", "i18n"),
        ("babel", "2.13.0", "Internationalization", "i18n"),
        
        # OCR و تشخیص
        ("pytesseract", "0.3.10", "OCR engine", "ocr"),
        ("easyocr", "1.7.1", "OCR made easy", "ocr"),
        
        # صدا
        ("pydub", "0.25.1", "Audio processing", "audio"),
        ("speechrecognition", "3.10.0", "Speech recognition", "audio"),
        ("pyttsx3", "2.90", "Text-to-speech", "audio"),
        
        # اکسل و گزارش
        ("openpyxl", "3.1.2", "Excel files", "office"),
        ("pandas", "2.1.0", "Excel/CSV", "office"),
        ("reportlab", "4.0.4", "PDF generation", "office"),
        ("weasyprint", "60.1", "HTML to PDF", "office"),
        
        # شبکه
        ("scapy", "2.5.0", "Packet manipulation", "network"),
        ("paramiko", "3.4.0", "SSH client", "network"),
        ("netmiko", "4.3.0", "Network automation", "network"),
        
        # تست
        ("pytest", "7.4.3", "Testing framework", "testing"),
        ("unittest2", "1.1.0", "Unit testing", "testing"),
        
        # گرافیک
        ("matplotlib", "3.8.0", "Plotting", "graphics"),
        ("plotly", "5.18.0", "Interactive plots", "graphics"),
        ("seaborn", "0.13.0", "Statistical viz", "graphics"),
    ]
    
    for name, version, desc, category in libraries:
        conn.execute('''
            INSERT OR IGNORE INTO libraries (name, version, description, category, install_count, is_installed)
            VALUES (?, ?, ?, ?, 0, 0)
        ''', (name, version, desc, category))
    
    conn.commit()

# ==================== هوش مصنوعی بررسی کد ====================

class AICodeAnalyzer:
    """سیستم هوشمند بررسی امنیت کد با استفاده از چندین روش"""
    
    def __init__(self):
        self.dangerous_patterns = {
            'critical': [
                (r'os\.system\s*\(', "اجرای دستورات سیستمی"),
                (r'subprocess\.(call|Popen|run)\s*\(', "اجرای زیرپروسس"),
                (r'eval\s*\(', "اجرای کد پویا - خطرناک"),
                (r'exec\s*\(', "اجرای کد پویا - خطرناک"),
                (r'__import__\s*\(', "ایمپورت پویا"),
                (r'base64\.b64decode\s*\(.*\)', "کد انکود شده"),
                (r'compile\s*\(', "کامپایل پویا"),
            ],
            'high': [
                (r'open\s*\([\'\"](/etc/|/root/|/home/|C:\\|\.\./)', "دسترسی به فایل‌های حساس"),
                (r'requests\.(get|post).*\.onion', "اتصال به دارک وب"),
                (r'socket\.', "اتصال شبکه مستقیم"),
                (r'telegram\.Bot.*polling', "ربات تو در تو"),
                (r'rm\s+-rf', "حذف فایل‌ها"),
                (r'wget|curl', "دانلود فایل"),
            ],
            'medium': [
                (r'pickle\.loads?', "دسریالایز خطرناک"),
                (r'yaml\.load\s*\([^,]*$', "YAML خطرناک"),
                (r'globals\(\)\.update', "تغییر متغیرهای سراسری"),
                (r'setattr|getattr', "دسترسی داینامیک به attribute"),
            ],
            'low': [
                (r'while\s+True:', "حلقه بی‌نهایت احتمالی"),
                (r'time\.sleep\s*\(\s*[0-9]{3,}', "تاخیر طولانی"),
                (r'for.*in.*range\([0-9]{6,}\)', "حلقه بزرگ"),
            ]
        }
        
        self.safe_patterns = [
            r'bot\.send_message',
            r'bot\.reply_to',
            r'types\.InlineKeyboardButton',
            r'@bot\.message_handler',
            r'telebot\.TeleBot',
        ]
    
    def analyze(self, code: str) -> Dict:
        """تحلیل کامل امنیتی کد"""
        result = {
            'is_safe': True,
            'score': 100,
            'critical_issues': [],
            'high_issues': [],
            'medium_issues': [],
            'low_issues': [],
            'warnings': [],
            'complexity_score': 0,
            'maintainability_score': 0,
            'has_token': False,
            'has_webhook': False,
            'lines_of_code': len(code.split('\n')),
            'functions_count': 0,
            'classes_count': 0,
            'recommendations': []
        }
        
        # بررسی الگوهای خطرناک
        for level, patterns in self.dangerous_patterns.items():
            for pattern, description in patterns:
                if re.search(pattern, code, re.IGNORECASE):
                    result[f'{level}_issues'].append(description)
                    if level == 'critical':
                        result['is_safe'] = False
                        result['score'] -= 30
                    elif level == 'high':
                        result['score'] -= 15
                    elif level == 'medium':
                        result['score'] -= 5
                    elif level == 'low':
                        result['score'] -= 2
        
        # بررسی وجود توکن
        token_patterns = [
            r'TOKEN\s*=\s*["\']([^"\']{30,50})["\']',
            r'token\s*=\s*["\']([^"\']{30,50})["\']',
            r'BOT_TOKEN\s*=\s*["\']([^"\']{30,50})["\']',
        ]
        
        for pattern in token_patterns:
            if re.search(pattern, code):
                result['has_token'] = True
                break
        
        # بررسی webhook
        if 'set_webhook' in code or 'delete_webhook' in code:
            result['has_webhook'] = True
        
        # تحلیل پیچیدگی کد
        try:
            tree = ast.parse(code)
            result['functions_count'] = sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))
            result['classes_count'] = sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
            
            # محاسبه پیچیدگی سایکلوماتیک
            complexity = 0
            for node in ast.walk(tree):
                if isinstance(node, (ast.If, ast.While, ast.For, ast.Try, ast.ExceptHandler)):
                    complexity += 1
                elif isinstance(node, ast.BoolOp):
                    complexity += len(node.values) - 1
            
            result['complexity_score'] = min(complexity, 100)
            
            # امتیاز نگهداری
            loc = result['lines_of_code']
            if loc < 100:
                result['maintainability_score'] = 90
            elif loc < 500:
                result['maintainability_score'] = 70
            else:
                result['maintainability_score'] = 50
            
        except Exception as e:
            result['warnings'].append(f"خطا در parsing کد: {str(e)}")
        
        # پیشنهادات امنیتی
        if result['has_token']:
            result['recommendations'].append("توکن در کد مشخص شده - برای امنیت بیشتر از متغیر محیطی استفاده کنید")
        
        if result['complexity_score'] > 30:
            result['recommendations'].append("کد پیچیده است - بهتر است ساده‌تر شود")
        
        if result['functions_count'] == 0:
            result['recommendations'].append("کد فاقد تابع main است - بهتر است ساختار مناسب داشته باشد")
        
        # امتیاز نهایی
        result['score'] = max(0, min(100, result['score']))
        
        # تعیین سطح امنیت
        if result['score'] >= 90:
            result['security_level'] = 'عالی'
        elif result['score'] >= 70:
            result['security_level'] = 'خوب'
        elif result['score'] >= 50:
            result['security_level'] = 'متوسط'
        else:
            result['security_level'] = 'ضعیف'
            result['is_safe'] = False
        
        return result
    
    def generate_report(self, analysis: Dict) -> str:
        """تولید گزارش خوانا"""
        report = "🔍 **گزارش تحلیل امنیتی هوشمند**\n\n"
        report += f"📊 **امتیاز کلی:** {analysis['score']}/100\n"
        report += f"🛡️ **سطح امنیت:** {analysis['security_level']}\n"
        report += f"✅ **وضعیت:** {'امن ✅' if analysis['is_safe'] else 'مشکوک ⚠️'}\n\n"
        
        report += f"📏 **آمار کد:**\n"
        report += f"• خطوط کد: {analysis['lines_of_code']}\n"
        report += f"• توابع: {analysis['functions_count']}\n"
        report += f"• کلاس‌ها: {analysis['classes_count']}\n"
        report += f"• پیچیدگی: {analysis['complexity_score']}\n\n"
        
        if analysis['critical_issues']:
            report += "🔴 **مشکلات بحرانی:**\n"
            for issue in analysis['critical_issues']:
                report += f"• {issue}\n"
            report += "\n"
        
        if analysis['high_issues']:
            report += "🟠 **مشکلات بالا:**\n"
            for issue in analysis['high_issues']:
                report += f"• {issue}\n"
            report += "\n"
        
        if analysis['warnings']:
            report += "⚠️ **هشدارها:**\n"
            for warn in analysis['warnings']:
                report += f"• {warn}\n"
            report += "\n"
        
        if analysis['recommendations']:
            report += "💡 **پیشنهادات:**\n"
            for rec in analysis['recommendations']:
                report += f"• {rec}\n"
        
        return report

ai_analyzer = AICodeAnalyzer()

# ==================== مدیریت سرورهای توزیع بار ====================

class ServerManager:
    """مدیریت پیشرفته سرورها با توزیع بار هوشمند"""
    
    def __init__(self):
        self.servers_cache = {}
        self.server_locks = {}
        self.executor = ThreadPoolExecutor(max_workers=20)
    
    def test_server_connection(self, host: str, username: str, password: str = None, port: int = 22) -> Tuple[bool, str, Dict]:
        """تست اتصال به سرور با روش‌های مختلف"""
        results = {
            'ping': None,
            'ssh': None,
            'system_info': None,
            'resources': None
        }
        
        # 1. تست پینگ
        try:
            ping_time = ping3.ping(host, timeout=3)
            results['ping'] = ping_time is not None
        except:
            results['ping'] = False
        
        # 2. تست پورت SSH
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        ssh_port_open = sock.connect_ex((host, port)) == 0
        sock.close()
        results['ssh'] = ssh_port_open
        
        if not ssh_port_open:
            return False, "پورت SSH باز نیست یا سرور در دسترس نیست", results
        
        # 3. اتصال SSH و دریافت اطلاعات
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if password:
                ssh.connect(host, port=port, username=username, password=password, timeout=10)
            else:
                # تلاش با کلید SSH
                key_path = os.path.join(SSL_DIR, f"{host}_key")
                if os.path.exists(key_path):
                    key = paramiko.RSAKey.from_private_key_file(key_path)
                    ssh.connect(host, port=port, username=username, pkey=key, timeout=10)
                else:
                    return False, "رمز یا کلید SSH ارائه نشده", results
            
            # دریافت اطلاعات سیستم
            commands = {
                'hostname': 'hostname',
                'os': 'cat /etc/os-release | grep PRETTY_NAME | cut -d"=" -f2',
                'cpu': "nproc",
                'memory': "free -m | awk '/^Mem:/{print $2}'",
                'disk': "df -h / | awk 'NR==2 {print $5}' | tr -d '%'",
                'load': "uptime | awk -F 'load average:' '{print $2}' | cut -d',' -f1",
                'python_version': "python3 --version 2>/dev/null || echo 'Not installed'"
            }
            
            system_info = {}
            for key, cmd in commands.items():
                try:
                    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=5)
                    output = stdout.read().decode().strip()
                    system_info[key] = output
                except:
                    system_info[key] = "Unknown"
            
            results['system_info'] = system_info
            
            # نصب کتابخانه‌های ضروری
            essential_libs = ['python3', 'python3-pip', 'git', 'screen', 'tmux']
            for lib in essential_libs:
                ssh.exec_command(f"which {lib} || (apt-get update && apt-get install -y {lib})", timeout=30)
            
            # نصب 100 کتابخانه اصلی
            self.install_core_libraries(ssh)
            
            ssh.close()
            
            return True, "اتصال برقرار شد", results
            
        except paramiko.AuthenticationException:
            return False, "نام کاربری یا رمز اشتباه است", results
        except paramiko.SSHException as e:
            return False, f"خطای SSH: {str(e)}", results
        except Exception as e:
            return False, f"خطا: {str(e)}", results
    
    def install_core_libraries(self, ssh):
        """نصب کتابخانه‌های اصلی روی سرور"""
        libraries = [
            'requests', 'aiohttp', 'flask', 'fastapi', 'numpy', 'pandas',
            'beautifulsoup4', 'selenium', 'scrapy', 'pillow', 'opencv-python',
            'pyTelegramBotAPI', 'aiogram', 'python-telegram-bot', 'telethon',
            'redis', 'sqlalchemy', 'motor', 'cryptography', 'pyjwt',
            'yt-dlp', 'pytube', 'jdatetime', 'pytz', 'loguru', 'tqdm',
            'schedule', 'celery', 'paramiko', 'netmiko', 'openpyxl',
            'matplotlib', 'plotly', 'rich', 'click', 'python-dotenv'
        ]
        
        for lib in libraries:
            try:
                ssh.exec_command(f"pip3 install {lib} --quiet", timeout=60)
            except:
                pass
    
    def add_server(self, name: str, host: str, username: str, password: str, port: int = 22) -> Dict:
        """افزودن سرور جدید به سیستم"""
        # تست اتصال
        is_connected, message, details = self.test_server_connection(host, username, password, port)
        
        if not is_connected:
            return {'success': False, 'message': message}
        
        # رمزگذاری رمز
        encrypted_password = cipher.encrypt(password.encode()).decode()
        
        with get_db() as conn:
            # بررسی تکراری نبودن
            existing = conn.execute('SELECT id FROM servers WHERE host = ?', (host,)).fetchone()
            if existing:
                return {'success': False, 'message': 'این سرور قبلاً اضافه شده است'}
            
            now = datetime.now().isoformat()
            conn.execute('''
                INSERT INTO servers (name, host, port, username, password_encrypted, status, created_at, updated_at, last_check)
                VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?)
            ''', (name, host, port, username, encrypted_password, now, now, now))
            conn.commit()
            
            server_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        
        return {
            'success': True,
            'message': f'سرور {name} با موفقیت اضافه شد',
            'server_id': server_id,
            'details': details
        }
    
    def get_best_server(self) -> Optional[Dict]:
        """انتخاب بهترین سرور برای اجرای ربات جدید (توزیع بار هوشمند)"""
        with get_db() as conn:
            servers = conn.execute('''
                SELECT * FROM servers 
                WHERE status = 'active' 
                ORDER BY 
                    load_average ASC,
                    running_bots ASC,
                    cpu_usage ASC
                LIMIT 1
            ''').fetchall()
            
            if not servers:
                return None
            
            best = dict(servers[0])
            
            # بروزرسانی آمار
            if best['running_bots'] >= best['max_bots']:
                return None
            
            return best
    
    def update_server_stats(self, server_id: int):
        """بروزرسانی آمار سرور"""
        with get_db() as conn:
            server = conn.execute('SELECT * FROM servers WHERE id = ?', (server_id,)).fetchone()
            if not server:
                return
            
            try:
                # اتصال به سرور و دریافت آمار
                password = cipher.decrypt(server['password_encrypted'].encode()).decode()
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(
                    server['host'], 
                    port=server['port'], 
                    username=server['username'], 
                    password=password,
                    timeout=5
                )
                
                # دریافت آمار
                stdin, stdout, stderr = ssh.exec_command("""
                    echo "CPU: $(top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1)"
                    echo "RAM: $(free | grep Mem | awk '{print ($3/$2) * 100.0}')"
                    echo "DISK: $(df -h / | awk 'NR==2 {print $5}' | tr -d '%')"
                    echo "LOAD: $(uptime | awk -F 'load average:' '{print $2}' | cut -d',' -f1)"
                """, timeout=10)
                
                output = stdout.read().decode()
                
                cpu = 0.0
                ram = 0.0
                disk = 0.0
                load = 0.0
                
                for line in output.split('\n'):
                    if 'CPU:' in line:
                        cpu = float(line.split(':')[1].strip())
                    elif 'RAM:' in line:
                        ram = float(line.split(':')[1].strip())
                    elif 'DISK:' in line:
                        disk = float(line.split(':')[1].strip())
                    elif 'LOAD:' in line:
                        load = float(line.split(':')[1].strip())
                
                ssh.close()
                
                now = datetime.now().isoformat()
                conn.execute('''
                    UPDATE servers 
                    SET cpu_usage = ?, memory_usage = ?, disk_usage = ?, load_average = ?, last_check = ?
                    WHERE id = ?
                ''', (cpu, ram, disk, load, now, server_id))
                conn.commit()
                
            except Exception as e:
                print(f"خطا در بروزرسانی سرور {server_id}: {e}")

server_manager = ServerManager()

# ==================== سیستم اشتراک با اخطار ====================

class SubscriptionManager:
    """مدیریت اشتراک‌ها و ارسال اخطار"""
    
    def __init__(self):
        self.warning_days = 3
        self.check_interval = 3600  # هر ساعت یکبار
    
    def create_subscription(self, user_id: int, sub_type: str = 'monthly') -> Tuple[Optional[int], Optional[str]]:
        """ایجاد اشتراک جدید"""
        prices = {'monthly': 200000, 'yearly': 2000000}
        amount = prices.get(sub_type, 200000)
        
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
    
    def activate_subscription(self, subscription_id: int):
        """فعال کردن اشتراک"""
        with get_db() as conn:
            sub = conn.execute('SELECT * FROM subscriptions WHERE id = ?', (subscription_id,)).fetchone()
            if not sub:
                return False
            
            now = datetime.now().isoformat()
            expires_at = (datetime.now() + timedelta(days=30 if sub['type'] == 'monthly' else 365)).isoformat()
            
            conn.execute('''
                UPDATE users 
                SET active_subscription = 1, subscription_type = ?, subscription_start = ?, subscription_end = ?
                WHERE user_id = ?
            ''', (sub['type'], now, expires_at, sub['user_id']))
            
            conn.execute('''
                UPDATE subscriptions SET status = 'active', paid_at = ? WHERE id = ?
            ''', (now, subscription_id))
            conn.commit()
            
            return True
    
    def check_expiring_subscriptions(self):
        """بررسی اشتراک‌های در حال انقضا و ارسال اخطار"""
        with get_db() as conn:
            users = conn.execute('''
                SELECT user_id, subscription_end, username, first_name
                FROM users 
                WHERE active_subscription = 1 
                AND datetime(subscription_end) <= datetime('now', '+3 days')
                AND datetime(subscription_end) > datetime('now')
            ''').fetchall()
            
            for user in users:
                expire_date = datetime.fromisoformat(user['subscription_end'])
                days_left = (expire_date - datetime.now()).days
                
                try:
                    bot.send_message(
                        user['user_id'],
                        f"⚠️ **اخطار انقضای اشتراک** ⚠️\n\n"
                        f"👤 {user['first_name']} عزیز\n\n"
                        f"اشتراک شما در **{days_left} روز دیگر** منقضی می‌شود.\n"
                        f"📅 تاریخ انقضا: {expire_date.strftime('%Y-%m-%d')}\n\n"
                        f"💰 برای تمدید اشتراک:\n"
                        f"مبلغ: 200,000 تومان (ماهانه)\n"
                        f"شماره کارت: `5892101187322777`\n\n"
                        f"پس از واریز، فیش را ارسال کنید.\n\n"
                        f"در صورت عدم تمدید، ربات شما متوقف خواهد شد.",
                        parse_mode="Markdown"
                    )
                    
                    # ثبت در دیتابیس که اخطار فرستاده شده
                    conn.execute('''
                        UPDATE bots SET warning_sent = 1 
                        WHERE user_id = ? AND expires_at <= datetime('now', '+3 days')
                    ''', (user['user_id'],))
                    conn.commit()
                    
                except Exception as e:
                    print(f"خطا در ارسال اخطار به {user['user_id']}: {e}")
    
    def expire_subscriptions(self):
        """باطل کردن اشتراک‌های منقضی شده"""
        with get_db() as conn:
            # غیرفعال کردن اشتراک‌های منقضی
            conn.execute('''
                UPDATE users 
                SET active_subscription = 0 
                WHERE active_subscription = 1 
                AND datetime(subscription_end) <= datetime('now')
            ''')
            
            # توقف ربات‌های منقضی شده
            expired_bots = conn.execute('''
                SELECT b.id, b.user_id, b.server_id, b.pid
                FROM bots b
                JOIN users u ON b.user_id = u.user_id
                WHERE u.active_subscription = 0 OR datetime(b.expires_at) <= datetime('now')
            ''').fetchall()
            
            for bot in expired_bots:
                # توقف ربات
                if bot['pid']:
                    try:
                        os.kill(bot['pid'], signal.SIGTERM)
                    except:
                        pass
                
                # بروزرسانی وضعیت
                conn.execute('UPDATE bots SET status = "expired" WHERE id = ?', (bot['id'],))
                
                # اطلاع به کاربر
                try:
                    bot.send_message(
                        bot['user_id'],
                        f"❌ ربات شما به دلیل انقضای اشتراک متوقف شد.\n\n"
                        f"برای فعالسازی مجدد، لطفاً اشتراک خود را تمدید کنید."
                    )
                except:
                    pass
            
            conn.commit()

subscription_manager = SubscriptionManager()

# ==================== سیستم مدیریت ربات‌ها روی سرورها ====================

class BotManager:
    """مدیریت اجرای ربات‌ها روی سرورهای مختلف"""
    
    def __init__(self):
        self.running_bots = {}
        self.bot_lock = threading.Lock()
    
    def deploy_bot_on_server(self, bot_id: str, server_id: int, code: str, token: str) -> Tuple[bool, str, Optional[int]]:
        """اجرای ربات روی سرور مشخص"""
        with get_db() as conn:
            server = conn.execute('SELECT * FROM servers WHERE id = ?', (server_id,)).fetchone()
            if not server:
                return False, "سرور یافت نشد", None
            
            # اتصال به سرور
            try:
                password = cipher.decrypt(server['password_encrypted'].encode()).decode()
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(
                    server['host'],
                    port=server['port'],
                    username=server['username'],
                    password=password,
                    timeout=10
                )
                
                # ایجاد پوشه ربات
                bot_path = f"/home/{server['username']}/bots/{bot_id}"
                ssh.exec_command(f"mkdir -p {bot_path}")
                
                # آپلود کد
                with ssh.open_sftp() as sftp:
                    remote_file = f"{bot_path}/bot.py"
                    with sftp.file(remote_file, 'w') as f:
                        f.write(code)
                
                # ایجاد فایل سرویس systemd
                service_content = f"""
[Unit]
Description=Telegram Bot {bot_id}
After=network.target

[Service]
Type=simple
User={server['username']}
WorkingDirectory={bot_path}
ExecStart=/usr/bin/python3 {bot_path}/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
                
                service_file = f"/etc/systemd/system/bot_{bot_id}.service"
                with ssh.open_sftp() as sftp:
                    with sftp.file(service_file, 'w') as f:
                        f.write(service_content)
                
                # فعال کردن و اجرای سرویس
                ssh.exec_command(f"sudo systemctl daemon-reload")
                ssh.exec_command(f"sudo systemctl enable bot_{bot_id}.service")
                ssh.exec_command(f"sudo systemctl start bot_{bot_id}.service")
                
                # دریافت PID
                stdin, stdout, stderr = ssh.exec_command(f"sudo systemctl show -p MainPID bot_{bot_id}.service | cut -d= -f2")
                pid = int(stdout.read().decode().strip())
                
                ssh.close()
                
                # بروزرسانی دیتابیس
                conn.execute('''
                    UPDATE bots 
                    SET server_id = ?, status = 'running', pid = ?
                    WHERE id = ?
                ''', (server_id, pid, bot_id))
                
                conn.execute('''
                    UPDATE servers SET running_bots = running_bots + 1
                    WHERE id = ?
                ''', (server_id,))
                conn.commit()
                
                return True, f"ربات روی سرور {server['name']} اجرا شد", pid
                
            except Exception as e:
                return False, f"خطا: {str(e)}", None
    
    def stop_bot_on_server(self, bot_id: str, server_id: int):
        """توقف ربات روی سرور"""
        with get_db() as conn:
            server = conn.execute('SELECT * FROM servers WHERE id = ?', (server_id,)).fetchone()
            if not server:
                return False
            
            try:
                password = cipher.decrypt(server['password_encrypted'].encode()).decode()
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(
                    server['host'],
                    port=server['port'],
                    username=server['username'],
                    password=password,
                    timeout=10
                )
                
                ssh.exec_command(f"sudo systemctl stop bot_{bot_id}.service")
                ssh.exec_command(f"sudo systemctl disable bot_{bot_id}.service")
                ssh.exec_command(f"rm -f /etc/systemd/system/bot_{bot_id}.service")
                ssh.exec_command(f"sudo systemctl daemon-reload")
                
                ssh.close()
                
                conn.execute('UPDATE bots SET status = "stopped" WHERE id = ?', (bot_id,))
                conn.execute('UPDATE servers SET running_bots = running_bots - 1 WHERE id = ?', (server_id,))
                conn.commit()
                
                return True
            except:
                return False
    
    def restart_bot(self, bot_id: str, user_id: int):
        """ریستارت ربات (برای ادمین)"""
        with get_db() as conn:
            bot = conn.execute('SELECT * FROM bots WHERE id = ? AND user_id = ?', (bot_id, user_id)).fetchone()
            if not bot:
                return False, "ربات یافت نشد"
            
            if bot['server_id']:
                # ریستارت روی سرور
                try:
                    server = conn.execute('SELECT * FROM servers WHERE id = ?', (bot['server_id'],)).fetchone()
                    password = cipher.decrypt(server['password_encrypted'].encode()).decode()
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(
                        server['host'],
                        port=server['port'],
                        username=server['username'],
                        password=password,
                        timeout=10
                    )
                    
                    ssh.exec_command(f"sudo systemctl restart bot_{bot_id}.service")
                    ssh.close()
                    
                    conn.execute('UPDATE bots SET status = "running", last_active = ? WHERE id = ?', 
                                (datetime.now().isoformat(), bot_id))
                    conn.commit()
                    
                    return True, "ربات با موفقیت ریستارت شد"
                except Exception as e:
                    return False, f"خطا: {str(e)}"
            else:
                # ریستارت لوکال
                try:
                    if bot['pid']:
                        os.kill(bot['pid'], signal.SIGTERM)
                    
                    with open(bot['file_path'], 'r', encoding='utf-8') as f:
                        code = f.read()
                    
                    bot_dir = os.path.join(RUNNING_DIR, bot_id)
                    os.makedirs(bot_dir, exist_ok=True)
                    
                    process = subprocess.Popen(
                        [sys.executable, bot['file_path']],
                        cwd=bot_dir,
                        start_new_session=True
                    )
                    
                    conn.execute('UPDATE bots SET status = "running", pid = ?, last_active = ? WHERE id = ?',
                                (process.pid, datetime.now().isoformat(), bot_id))
                    conn.commit()
                    
                    return True, "ربات با موفقیت ریستارت شد"
                except Exception as e:
                    return False, f"خطا: {str(e)}"

bot_manager = BotManager()

# ==================== کتابخانه منیجر پیشرفته ====================

class AdvancedLibraryManager:
    """مدیریت نصب 100+ کتابخانه"""
    
    def __init__(self):
        self.libraries_cache = {}
        self.load_libraries()
    
    def load_libraries(self):
        """بارگذاری لیست کتابخانه‌ها از دیتابیس"""
        with get_db() as conn:
            libs = conn.execute('SELECT * FROM libraries ORDER BY category, name').fetchall()
            self.libraries_cache = [dict(lib) for lib in libs]
    
    def get_libraries_by_category(self) -> Dict:
        """دسته‌بندی کتابخانه‌ها"""
        categories = {}
        for lib in self.libraries_cache:
            cat = lib['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(lib)
        return categories
    
    def install_library(self, lib_name: str, chat_id: int) -> Tuple[bool, str]:
        """نصب کتابخانه با نمایش پیشرفت"""
        try:
            msg = bot.send_message(chat_id, f"📦 در حال نصب {lib_name}...")
            
            process = subprocess.Popen(
                [sys.executable, "-m", "pip", "install", lib_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(timeout=120)
            
            if process.returncode == 0:
                # بروزرسانی دیتابیس
                with get_db() as conn:
                    conn.execute('''
                        UPDATE libraries SET install_count = install_count + 1, is_installed = 1
                        WHERE name = ?
                    ''', (lib_name,))
                    conn.commit()
                
                bot.edit_message_text(
                    f"✅ کتابخانه {lib_name} با موفقیت نصب شد!",
                    chat_id,
                    msg.message_id
                )
                return True, stdout
            else:
                bot.edit_message_text(
                    f"❌ خطا در نصب {lib_name}:\n{stderr[:200]}",
                    chat_id,
                    msg.message_id
                )
                return False, stderr
                
        except subprocess.TimeoutExpired:
            bot.send_message(chat_id, f"❌ زمان نصب {lib_name} بیش از حد طول کشید")
            return False, "Timeout"
        except Exception as e:
            bot.send_message(chat_id, f"❌ خطا: {str(e)}")
            return False, str(e)

lib_manager = AdvancedLibraryManager()

# ==================== منوهای پیشرفته ====================

def get_main_menu(is_admin=False):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    
    buttons = [
        types.KeyboardButton('🛒 خرید اشتراک'),
        types.KeyboardButton('📤 ارسال فایل ربات'),
        types.KeyboardButton('🤖 ربات‌های من'),
        types.KeyboardButton('📚 راهنما'),
        types.KeyboardButton('📦 نصب کتابخانه'),
        types.KeyboardButton('📞 پشتیبانی')
    ]
    
    if is_admin:
        buttons.append(types.KeyboardButton('👑 پنل ادمین'))
    
    markup.add(*buttons)
    return markup

def get_admin_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🖥️ مدیریت سرورها", callback_data="admin_servers"),
        types.InlineKeyboardButton("📸 فیش‌های واریز", callback_data="admin_receipts"),
        types.InlineKeyboardButton("📥 فایل‌های در انتظار", callback_data="admin_pending"),
        types.InlineKeyboardButton("👥 مدیریت کاربران", callback_data="admin_users"),
        types.InlineKeyboardButton("🤖 مدیریت ربات‌ها", callback_data="admin_bots"),
        types.InlineKeyboardButton("📊 آمار پیشرفته", callback_data="admin_stats"),
        types.InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    return markup

# ==================== هندلر استارت ====================

@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    
    with get_db() as conn:
        now = datetime.now().isoformat()
        conn.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, created_at, last_active)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name, now, now))
        conn.execute('UPDATE users SET last_active = ? WHERE user_id = ?', (now, user_id))
        conn.commit()
    
    is_admin = user_id in ADMIN_IDS
    markup = get_main_menu(is_admin)
    bot_username = bot.get_me().username
    
    welcome_text = f"""🚀 **به ربات سازنده حرفه‌ای خوش آمدید!**

👤 {first_name} عزیز

✅ امکانات پیشرفته:
• 📤 ساخت ربات تلگرامی با ارسال فایل
• 🔒 بررسی امنیتی با هوش مصنوعی
• 🌐 توزیع بار روی چندین سرور
• 📦 نصب خودکار ۱۰۰+ کتابخانه
• ⏰ مدیریت اشتراک و ارسال اخطار

💰 **قیمت اشتراک:** ۲۰۰,۰۰۰ تومان (ماهانه)

@shahraghee13 - پشتیبانی"""

    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=markup)

# ==================== خرید اشتراک ====================

@bot.message_handler(func=lambda m: m.text == '🛒 خرید اشتراک')
def buy_subscription(message):
    user_id = message.from_user.id
    
    with get_db() as conn:
        user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
        if user and user['active_subscription']:
            end_date = datetime.fromisoformat(user['subscription_end']).strftime('%Y-%m-%d')
            bot.send_message(
                message.chat.id,
                f"✅ شما اشتراک فعال دارید!\n"
                f"📅 تاریخ انقضا: {end_date}\n\n"
                f"📤 لطفاً فایل ربات خود را ارسال کنید."
            )
            return
    
    sub_id, sub_code = subscription_manager.create_subscription(user_id)
    
    text = f"""💰 **خرید اشتراک ماهانه**

💳 **مبلغ:** ۲۰۰,۰۰۰ تومان
🏦 **شماره کارت:** `5892101187322777`
👤 **به نام:** مرتضی نیکخو خنجری

🆔 **کد اشتراک:** `{sub_code}`

📌 **مراحل:**
1️⃣ مبلغ را به کارت فوق واریز کنید
2️⃣ کد اشتراک را در رسید یادداشت کنید
3️⃣ تصویر فیش را ارسال کنید

⏳ پس از تایید، می‌توانید فایل ربات خود را ارسال کنید

@shahraghee13 - پشتیبانی"""
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# ==================== دریافت فیش ====================

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
            ''', (user_id, pending_sub['id'], pending_sub['amount'], receipt_path, payment_code, datetime.now().isoformat()))
            conn.commit()
        
        bot.reply_to(
            message,
            f"✅ فیش شما دریافت شد!\n"
            f"💰 مبلغ: {pending_sub['amount']:,} تومان\n"
            f"🆔 کد پیگیری: {payment_code}\n\n"
            f"⏳ پس از تأیید ادمین، اشتراک شما فعال می‌شود."
        )
        
        for admin_id in ADMIN_IDS:
            try:
                with open(receipt_path, 'rb') as f:
                    bot.send_photo(
                        admin_id,
                        f,
                        caption=f"📸 فیش جدید\n👤 کاربر: {user_id}\n💰 مبلغ: {pending_sub['amount']:,}\n🆔 کد: {payment_code}"
                    )
            except:
                pass
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")

# ==================== ارسال فایل با AI Checker ====================

@bot.message_handler(func=lambda m: m.text == '📤 ارسال فایل ربات')
def send_bot_file(message):
    user_id = message.from_user.id
    
    with get_db() as conn:
        user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
        if not user or not user['active_subscription']:
            bot.send_message(
                message.chat.id,
                f"❌ شما اشتراک فعال ندارید!\n\n"
                f"💰 مبلغ اشتراک: ۲۰۰,۰۰۰ تومان\n"
                f"از منوی «خرید اشتراک» استفاده کنید."
            )
            return
    
    bot.send_message(
        message.chat.id,
        "📤 لطفاً فایل `.py` ربات خود را ارسال کنید.\n\n"
        "🔍 **فایل شما با هوش مصنوعی بررسی می‌شود:**\n"
        "• بررسی کدهای مخرب\n"
        "• تحلیل امنیتی پیشرفته\n"
        "• اگر امن باشد، خودکار ساخته می‌شود\n\n"
        "⚠️ حجم فایل حداکثر ۱۰ مگابایت"
    )

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
        
        file_path = save_uploaded_file(user_id, downloaded_file, file_name)
        if not file_path:
            bot.edit_message_text("❌ خطا در ذخیره فایل", message.chat.id, status_msg.message_id)
            return
        
        # خواندن کد
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # تحلیل با هوش مصنوعی
        analysis = ai_analyzer.analyze(code)
        report = ai_analyzer.generate_report(analysis)
        
        bot.edit_message_text(
            f"🔍 **تحلیل هوش مصنوعی کامل شد!**\n\n{report}",
            message.chat.id,
            status_msg.message_id,
            parse_mode="Markdown"
        )
        
        # ثبت در امنیت لاگ
        with get_db() as conn:
            conn.execute('''
                INSERT INTO security_logs (user_id, action, file_name, ai_score, verdict, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, 'upload', file_name, analysis['score'], 'safe' if analysis['is_safe'] else 'suspicious', datetime.now().isoformat()))
            conn.commit()
        
        # گرفتن اشتراک فعال
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
            now = datetime.now().isoformat()
            conn.execute('''
                INSERT INTO pending_files (user_id, subscription_id, file_path, file_name, ai_score, ai_report, security_level, submitted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, sub['id'], file_path, file_name, analysis['score'], report, analysis['security_level'], now))
            
            pending_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            conn.commit()
        
        # اگر امنیت عالی بود، خودکار تایید کن
        if analysis['is_safe'] and analysis['score'] >= 85:
            bot.send_message(message.chat.id, "✅ **فایل شما امن تشخیص داده شد!**\nدر حال ساخت خودکار ربات...")
            auto_approve_file(pending_id, user_id, file_path, code, message.chat.id)
        else:
            # ارسال به ادمین برای بررسی دستی
            for admin_id in ADMIN_IDS:
                try:
                    with open(file_path, 'rb') as f:
                        bot.send_document(
                            admin_id,
                            f,
                            caption=f"📥 **فایل جدید نیاز به بررسی**\n\n"
                                   f"👤 کاربر: {user_id}\n"
                                   f"📄 فایل: {file_name}\n"
                                   f"🤖 امتیاز AI: {analysis['score']}/100\n"
                                   f"🛡️ سطح: {analysis['security_level']}\n"
                                   f"🆔 ID: {pending_id}\n\n"
                                   f"{report}",
                            parse_mode="Markdown"
                        )
                except:
                    pass
            
            bot.send_message(
                message.chat.id,
                f"✅ فایل شما دریافت و به ادمین ارسال شد.\n"
                f"🔍 امتیاز امنیتی: {analysis['score']}/100\n"
                f"⏳ پس از بررسی ادمین، نتیجه به شما اعلام می‌شود."
            )
            
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)}", message.chat.id, status_msg.message_id)

def auto_approve_file(pending_id, user_id, file_path, code, chat_id):
    """تایید خودکار فایل امن و ساخت ربات"""
    try:
        # استخراج توکن
        token = ai_analyzer.extract_token_from_code(code)  # باید این متد رو اضافه کنم
        if not token:
            bot.send_message(chat_id, "❌ توکن در کد پیدا نشد!")
            return
        
        # بررسی توکن
        response = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
        if response.status_code != 200:
            bot.send_message(chat_id, "❌ توکن معتبر نیست!")
            return
        
        bot_info = response.json()['result']
        bot_name = bot_info['first_name']
        bot_username = bot_info['username']
        
        # انتخاب بهترین سرور
        best_server = server_manager.get_best_server()
        
        bot_id = hashlib.md5(f"{user_id}_{token}_{time.time()}".encode()).hexdigest()[:10]
        
        if best_server:
            # اجرا روی سرور
            success, msg, pid = bot_manager.deploy_bot_on_server(bot_id, best_server['id'], code, token)
            
            if success:
                expires_at = (datetime.now() + timedelta(days=30)).isoformat()
                with get_db() as conn:
                    now = datetime.now().isoformat()
                    conn.execute('''
                        UPDATE pending_files SET status = 'approved', reviewed_at = ?, auto_approved = 1
                        WHERE id = ?
                    ''', (now, pending_id))
                    
                    conn.execute('''
                        INSERT INTO bots (id, user_id, server_id, token, name, username, file_path, status, created_at, expires_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 'running', ?, ?)
                    ''', (bot_id, user_id, best_server['id'], token, bot_name, bot_username, file_path, now, expires_at))
                    conn.commit()
                
                bot.send_message(
                    chat_id,
                    f"✅ **ربات شما با موفقیت ساخته شد!** 🎉\n\n"
                    f"🤖 نام: {bot_name}\n"
                    f"🔗 لینک: https://t.me/{bot_username}\n"
                    f"🆔 آیدی: {bot_id}\n"
                    f"🖥️ سرور: {best_server['name']}\n"
                    f"📅 اعتبار: ۳۰ روز\n\n"
                    f"از منوی «ربات‌های من» می‌توانید آن را مدیریت کنید."
                )
            else:
                bot.send_message(chat_id, f"❌ خطا در ساخت ربات: {msg}")
        else:
            # اجرا لوکال
            bot_dir = os.path.join(RUNNING_DIR, bot_id)
            os.makedirs(bot_dir, exist_ok=True)
            
            process = subprocess.Popen(
                [sys.executable, file_path],
                cwd=bot_dir,
                start_new_session=True
            )
            
            pid = process.pid
            expires_at = (datetime.now() + timedelta(days=30)).isoformat()
            
            with get_db() as conn:
                now = datetime.now().isoformat()
                conn.execute('''
                    UPDATE pending_files SET status = 'approved', reviewed_at = ?, auto_approved = 1
                    WHERE id = ?
                ''', (now, pending_id))
                
                conn.execute('''
                    INSERT INTO bots (id, user_id, token, name, username, file_path, folder_path, pid, status, created_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'running', ?, ?)
                ''', (bot_id, user_id, token, bot_name, bot_username, file_path, bot_dir, pid, now, expires_at))
                conn.commit()
            
            bot.send_message(
                chat_id,
                f"✅ **ربات شما با موفقیت ساخته شد!** 🎉\n\n"
                f"🤖 نام: {bot_name}\n"
                f"🔗 لینک: https://t.me/{bot_username}\n"
                f"🆔 آیدی: {bot_id}\n"
                f"📅 اعتبار: ۳۰ روز\n\n"
                f"از منوی «ربات‌های من» می‌توانید آن را مدیریت کنید."
            )
            
    except Exception as e:
        bot.send_message(chat_id, f"❌ خطا در ساخت خودکار: {str(e)}")

# ==================== ربات‌های من (رفع مشکل حذف) ====================

@bot.message_handler(func=lambda m: m.text == '🤖 ربات‌های من')
def my_bots(message):
    user_id = message.from_user.id
    
    with get_db() as conn:
        bots = conn.execute('''
            SELECT * FROM bots WHERE user_id = ? ORDER BY created_at DESC
        ''', (user_id,)).fetchall()
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما رباتی ندارید!\nبرای ساخت ربات، ابتدا اشتراک بخرید.")
        return
    
    for b in bots:
        b = dict(b)
        
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
        
        # تاریخ انقضا
        expires = datetime.fromisoformat(b['expires_at']).strftime('%Y-%m-%d')
        
        text = f"{status_emoji} **{b['name']}**\n"
        text += f"🔗 https://t.me/{b['username']}\n"
        text += f"🆔 `{b['id']}`\n"
        text += f"📊 وضعیت: {status_text}\n"
        text += f"📅 انقضا: {expires}\n"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🔄 توقف/اجرا", callback_data=f"user_toggle_{b['id']}"),
            types.InlineKeyboardButton("🗑 حذف", callback_data=f"user_delete_{b['id']}")
        )
        
        bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('user_toggle_'))
def user_toggle_bot(call):
    bot_id = call.data.replace('user_toggle_', '')
    user_id = call.from_user.id
    
    with get_db() as conn:
        bot_info = conn.execute('SELECT * FROM bots WHERE id = ? AND user_id = ?', (bot_id, user_id)).fetchone()
    
    if not bot_info:
        bot.answer_callback_query(call.id, "❌ ربات پیدا نشد!")
        return
    
    bot_info = dict(bot_info)
    
    if bot_info['status'] == 'running':
        if bot_info['server_id']:
            success = bot_manager.stop_bot_on_server(bot_id, bot_info['server_id'])
        else:
            try:
                os.kill(bot_info['pid'], signal.SIGTERM)
                success = True
            except:
                success = False
        
        if success:
            with get_db() as conn:
                conn.execute('UPDATE bots SET status = "stopped" WHERE id = ?', (bot_id,))
                conn.commit()
            bot.answer_callback_query(call.id, "✅ ربات متوقف شد")
        else:
            bot.answer_callback_query(call.id, "❌ خطا در توقف!")
    else:
        # راه‌اندازی مجدد
        if bot_info['server_id']:
            success, msg, _ = bot_manager.deploy_bot_on_server(bot_id, bot_info['server_id'], None, bot_info['token'])
        else:
            try:
                process = subprocess.Popen(
                    [sys.executable, bot_info['file_path']],
                    cwd=bot_info['folder_path'] or RUNNING_DIR,
                    start_new_session=True
                )
                with get_db() as conn:
                    conn.execute('UPDATE bots SET status = "running", pid = ? WHERE id = ?', (process.pid, bot_id))
                    conn.commit()
                success = True
            except Exception as e:
                success = False
        
        if success:
            bot.answer_callback_query(call.id, "✅ ربات اجرا شد")
        else:
            bot.answer_callback_query(call.id, "❌ خطا در اجرا!")

@bot.callback_query_handler(func=lambda call: call.data.startswith('user_delete_'))
def user_delete_bot(call):
    bot_id = call.data.replace('user_delete_', '')
    user_id = call.from_user.id
    
    # توقف ربات
    with get_db() as conn:
        bot_info = conn.execute('SELECT * FROM bots WHERE id = ? AND user_id = ?', (bot_id, user_id)).fetchone()
    
    if not bot_info:
        bot.answer_callback_query(call.id, "❌ ربات پیدا نشد!")
        return
    
    bot_info = dict(bot_info)
    
    if bot_info['server_id']:
        bot_manager.stop_bot_on_server(bot_id, bot_info['server_id'])
    else:
        try:
            os.kill(bot_info['pid'], signal.SIGTERM)
        except:
            pass
    
    # حذف فایل‌ها
    if bot_info['file_path'] and os.path.exists(bot_info['file_path']):
        os.remove(bot_info['file_path'])
    
    if bot_info['folder_path'] and os.path.exists(bot_info['folder_path']):
        shutil.rmtree(bot_info['folder_path'])
    
    # حذف از دیتابیس
    with get_db() as conn:
        conn.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
        conn.commit()
    
    bot.answer_callback_query(call.id, "✅ ربات با موفقیت حذف شد")
    bot.edit_message_text("🗑 ربات حذف شد.", call.message.chat.id, call.message.message_id)

# ==================== نصب کتابخانه ====================

@bot.message_handler(func=lambda m: m.text == '📦 نصب کتابخانه')
def install_library_menu(message):
    categories = lib_manager.get_libraries_by_category()
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    category_names = {
        'web': '🌐 وب و API',
        'database': '🗄️ دیتابیس',
        'ai': '🤖 هوش مصنوعی',
        'data': '📊 علم داده',
        'media': '🎬 پردازش رسانه',
        'telegram': '📱 تلگرام',
        'scraping': '🕷️ اسکرپینگ',
        'security': '🔒 امنیت',
        'download': '⬇️ دانلود',
        'finance': '💰 مالی',
        'tools': '🛠️ ابزارها',
        'i18n': '🌍 بین‌المللی',
        'ocr': '📖 OCR',
        'audio': '🎵 صدا',
        'office': '📄 آفیس',
        'network': '🌐 شبکه',
        'testing': '🧪 تست',
        'graphics': '🎨 گرافیک'
    }
    
    for cat in categories.keys():
        name = category_names.get(cat, cat)
        markup.add(types.InlineKeyboardButton(name, callback_data=f"lib_cat_{cat}"))
    
    markup.add(types.InlineKeyboardButton("🔍 جستجوی کتابخانه", callback_data="lib_search"))
    markup.add(types.InlineKeyboardButton("📋 کتابخانه‌های نصب شده", callback_data="lib_installed"))
    
    bot.send_message(message.chat.id, "📦 **کتابخانه مورد نظر را انتخاب کنید:**", parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lib_cat_'))
def show_category_libs(call):
    category = call.data.replace('lib_cat_', '')
    
    with get_db() as conn:
        libs = conn.execute('SELECT * FROM libraries WHERE category = ? ORDER BY name', (category,)).fetchall()
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for lib in libs:
        installed = "✅ " if lib['is_installed'] else ""
        markup.add(types.InlineKeyboardButton(
            f"{installed}{lib['name']} ({lib['version']})",
            callback_data=f"lib_install_{lib['name']}"
        ))
    
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="lib_back"))
    
    bot.edit_message_text(
        f"📦 کتابخانه‌های دسته {category}:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('lib_install_'))
def install_lib_callback(call):
    lib_name = call.data.replace('lib_install_', '')
    
    bot.answer_callback_query(call.id, f"در حال نصب {lib_name}...")
    
    success, output = lib_manager.install_library(lib_name, call.message.chat.id)
    
    if success:
        # به‌روزرسانی دکمه
        with get_db() as conn:
            lib = conn.execute('SELECT * FROM libraries WHERE name = ?', (lib_name,)).fetchone()
            if lib:
                markup = types.InlineKeyboardMarkup(row_width=1)
                markup.add(types.InlineKeyboardButton(
                    f"✅ {lib['name']} (نصب شده)",
                    callback_data=f"lib_installed_{lib['name']}"
                ))
                markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="lib_back"))
                
                try:
                    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)
                except:
                    pass

@bot.callback_query_handler(func=lambda call: call.data == "lib_back")
def lib_back(call):
    install_library_menu(call.message)

# ==================== پنل ادمین - مدیریت سرورها ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_servers")
def admin_servers(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("➕ افزودن سرور جدید", callback_data="admin_add_server"),
        types.InlineKeyboardButton("📋 لیست سرورها", callback_data="admin_list_servers"),
        types.InlineKeyboardButton("🔄 بروزرسانی آمار سرورها", callback_data="admin_refresh_servers"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    bot.edit_message_text(
        "🖥️ **مدیریت سرورها**\n\n"
        "از این بخش می‌توانید سرورهای جدید اضافه کنید و بار بین آنها را توزیع کنید.",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_add_server")
def admin_add_server_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ انصراف", callback_data="admin_servers"))
    
    msg = bot.send_message(
        call.message.chat.id,
        "🖥️ **افزودن سرور جدید**\n\n"
        "لطفاً اطلاعات سرور را به صورت زیر وارد کنید:\n\n"
        "`نام سرور|آیپی|پورت|نام کاربری|رمز`\n\n"
        "مثال:\n"
        "`Server1|192.168.1.100|22|root|my_password`",
        parse_mode="Markdown",
        reply_markup=markup
    )
    
    bot.register_next_step_handler(msg, process_add_server)

def process_add_server(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        parts = message.text.split('|')
        if len(parts) < 5:
            bot.reply_to(message, "❌ فرمت صحیح نیست! لطفاً به فرمت: `نام|آیپی|پورت|یوزرنیم|رمز`")
            return
        
        name = parts[0].strip()
        host = parts[1].strip()
        port = int(parts[2].strip())
        username = parts[3].strip()
        password = parts[4].strip()
        
        status_msg = bot.reply_to(message, "🔄 در حال بررسی و اتصال به سرور...")
        
        result = server_manager.add_server(name, host, username, password, port)
        
        if result['success']:
            details = result.get('details', {})
            sys_info = details.get('system_info', {})
            
            response = f"✅ **سرور با موفقیت اضافه شد!**\n\n"
            response += f"📛 نام: {name}\n"
            response += f"🌐 آیپی: {host}\n"
            response += f"💻 سیستمعامل: {sys_info.get('os', 'Unknown')}\n"
            response += f"🔢 هسته‌ها: {sys_info.get('cpu', 'Unknown')}\n"
            response += f"📦 رم: {sys_info.get('memory', 'Unknown')} MB\n"
            
            bot.edit_message_text(response, message.chat.id, status_msg.message_id, parse_mode="Markdown")
        else:
            bot.edit_message_text(f"❌ خطا: {result['message']}", message.chat.id, status_msg.message_id)
            
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
        bot.send_message(call.message.chat.id, "📋 هیچ سروری ثبت نشده است.")
        return
    
    for s in servers:
        s = dict(s)
        status_emoji = "🟢" if s['status'] == 'active' else "🔴"
        
        text = f"{status_emoji} **{s['name']}**\n"
        text += f"🌐 {s['host']}:{s['port']}\n"
        text += f"👤 {s['username']}\n"
        text += f"💻 CPU: {s['cpu_usage']:.1f}% | RAM: {s['memory_usage']:.1f}%\n"
        text += f"📊 بار: {s['load_average']} | ربات‌ها: {s['running_bots']}/{s['max_bots']}\n"
        text += f"📅 آخرین بررسی: {s['last_check'][:16] if s['last_check'] else 'ندارد'}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🗑 حذف", callback_data=f"admin_del_server_{s['id']}"),
            types.InlineKeyboardButton("🔄 آمار", callback_data=f"admin_refresh_server_{s['id']}")
        )
        
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

# ==================== پنل ادمین - مدیریت کاربران و ربات‌ها ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_users")
def admin_users(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📋 لیست کاربران", callback_data="admin_user_list"),
        types.InlineKeyboardButton("🚫 مسدود کردن کاربر", callback_data="admin_ban_user"),
        types.InlineKeyboardButton("✅ رفع مسدودیت", callback_data="admin_unban_user"),
        types.InlineKeyboardButton("🗑 حذف کاربر", callback_data="admin_delete_user"),
        types.InlineKeyboardButton("💰 تمدید اشتراک", callback_data="admin_extend_sub"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    bot.edit_message_text(
        "👥 **مدیریت کاربران**\n\n"
        "از این بخش می‌توانید کاربران را مدیریت کنید.",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_user_list")
def admin_user_list(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        users = conn.execute('''
            SELECT user_id, username, first_name, active_subscription, subscription_end, created_at, is_banned
            FROM users ORDER BY created_at DESC LIMIT 30
        ''').fetchall()
    
    text = "👥 **لیست کاربران (۳۰ نفر آخر)**\n\n"
    for u in users:
        status = "✅ فعال" if u['active_subscription'] else "❌ غیرفعال"
        banned = "🚫 مسدود" if u['is_banned'] else ""
        expire = datetime.fromisoformat(u['subscription_end']).strftime('%Y-%m-%d') if u['subscription_end'] else "ندارد"
        
        text += f"🆔 {u['user_id']} - {u['first_name']}\n"
        text += f"   {status} | {banned}\n"
        text += f"   📅 انقضا: {expire}\n"
        text += f"   📅 عضویت: {u['created_at'][:10]}\n\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_delete_user")
def admin_delete_user_prompt(call):
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
            # حذف ربات‌های کاربر
            bots = conn.execute('SELECT id, server_id, pid FROM bots WHERE user_id = ?', (user_id,)).fetchall()
            for bot in bots:
                if bot['server_id']:
                    bot_manager.stop_bot_on_server(bot['id'], bot['server_id'])
                else:
                    try:
                        os.kill(bot['pid'], signal.SIGTERM)
                    except:
                        pass
            
            # حذف کاربر
            conn.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
            conn.commit()
        
        bot.reply_to(message, f"✅ کاربر {user_id} و تمام ربات‌هایش حذف شدند.")
    except ValueError:
        bot.reply_to(message, "❌ آیدی باید عدد باشد.")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_bots")
def admin_bots(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📋 لیست ربات‌ها", callback_data="admin_bot_list"),
        types.InlineKeyboardButton("🔄 ریستارت ربات", callback_data="admin_restart_bot"),
        types.InlineKeyboardButton("🗑 حذف ربات", callback_data="admin_delete_bot"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    bot.edit_message_text(
        "🤖 **مدیریت ربات‌ها**\n\n"
        "از این بخش می‌توانید ربات‌های کاربران را مدیریت کنید.",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_bot_list")
def admin_bot_list(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        bots = conn.execute('''
            SELECT b.*, u.first_name, u.username
            FROM bots b
            JOIN users u ON b.user_id = u.user_id
            ORDER BY b.created_at DESC LIMIT 30
        ''').fetchall()
    
    if not bots:
        bot.send_message(call.message.chat.id, "📋 هیچ رباتی وجود ندارد.")
        return
    
    for b in bots:
        b = dict(b)
        text = f"🤖 **{b['name']}**\n"
        text += f"👤 کاربر: {b['first_name']} (🆔 {b['user_id']})\n"
        text += f"🔗 https://t.me/{b['username']}\n"
        text += f"📊 وضعیت: {b['status']}\n"
        text += f"📅 ساخته شده: {b['created_at'][:10]}\n"
        text += f"📅 انقضا: {b['expires_at'][:10] if b['expires_at'] else 'نامحدود'}\n"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🔄 ریستارت", callback_data=f"admin_restart_{b['id']}"),
            types.InlineKeyboardButton("🗑 حذف", callback_data=f"admin_del_bot_{b['id']}")
        )
        
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_restart_"))
def admin_restart_bot(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    bot_id = call.data.replace("admin_restart_", "")
    
    with get_db() as conn:
        bot_info = conn.execute('SELECT user_id FROM bots WHERE id = ?', (bot_id,)).fetchone()
    
    if not bot_info:
        bot.answer_callback_query(call.id, "❌ ربات پیدا نشد!")
        return
    
    success, msg = bot_manager.restart_bot(bot_id, bot_info['user_id'])
    
    if success:
        bot.answer_callback_query(call.id, "✅ ربات ریستارت شد")
    else:
        bot.answer_callback_query(call.id, f"❌ {msg[:50]}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_del_bot_"))
def admin_delete_bot(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    bot_id = call.data.replace("admin_del_bot_", "")
    
    with get_db() as conn:
        bot_info = conn.execute('SELECT user_id, server_id, pid, file_path, folder_path FROM bots WHERE id = ?', (bot_id,)).fetchone()
    
    if not bot_info:
        bot.answer_callback_query(call.id, "❌ ربات پیدا نشد!")
        return
    
    bot_info = dict(bot_info)
    
    # توقف ربات
    if bot_info['server_id']:
        bot_manager.stop_bot_on_server(bot_id, bot_info['server_id'])
    else:
        try:
            os.kill(bot_info['pid'], signal.SIGTERM)
        except:
            pass
    
    # حذف فایل‌ها
    if bot_info['file_path'] and os.path.exists(bot_info['file_path']):
        os.remove(bot_info['file_path'])
    
    if bot_info['folder_path'] and os.path.exists(bot_info['folder_path']):
        shutil.rmtree(bot_info['folder_path'])
    
    # حذف از دیتابیس
    with get_db() as conn:
        conn.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
        conn.commit()
    
    bot.answer_callback_query(call.id, "✅ ربات حذف شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== پنل ادمین - مدیریت فایل‌های در انتظار ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_pending")
def admin_pending_files(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        pending = conn.execute('''
            SELECT pf.*, u.first_name, u.username
            FROM pending_files pf
            JOIN users u ON pf.user_id = u.user_id
            WHERE pf.status = 'pending'
            ORDER BY pf.ai_score DESC, pf.submitted_at ASC
        ''').fetchall()
    
    if not pending:
        bot.send_message(call.message.chat.id, "📥 هیچ فایل در انتظاری وجود ندارد.")
        return
    
    for p in pending:
        p = dict(p)
        
        text = f"📥 **فایل در انتظار بررسی**\n\n"
        text += f"🆔 ID: {p['id']}\n"
        text += f"👤 کاربر: {p['first_name']} (🆔 {p['user_id']})\n"
        text += f"📄 فایل: {p['file_name']}\n"
        text += f"🤖 امتیاز AI: {p['ai_score']}/100\n"
        text += f"🛡️ سطح: {p['security_level']}\n"
        text += f"📅 ارسال: {p['submitted_at'][:16]}\n\n"
        text += f"{p['ai_report'][:500] if p['ai_report'] else 'گزارشی موجود نیست'}"
        
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

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_approve_file_"))
def admin_approve_file(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    pending_id = int(call.data.replace("admin_approve_file_", ""))
    
    with get_db() as conn:
        pending = conn.execute('''
            SELECT * FROM pending_files WHERE id = ?
        ''', (pending_id,)).fetchone()
    
    if not pending:
        bot.answer_callback_query(call.id, "❌ فایل پیدا نشد!")
        return
    
    pending = dict(pending)
    user_id = pending['user_id']
    file_path = pending['file_path']
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # استخراج توکن
        token = None
        patterns = [r'token\s*=\s*["\']([^"\']+)["\']', r'TOKEN\s*=\s*["\']([^"\']+)["\']']
        for pattern in patterns:
            match = re.search(pattern, code, re.IGNORECASE)
            if match:
                token = match.group(1)
                break
        
        if not token:
            bot.answer_callback_query(call.id, "❌ توکن در کد پیدا نشد!")
            return
        
        # بررسی توکن
        response = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
        if response.status_code != 200:
            bot.answer_callback_query(call.id, "❌ توکن معتبر نیست!")
            return
        
        bot_info = response.json()['result']
        
        # انتخاب سرور
        best_server = server_manager.get_best_server()
        
        bot_id = hashlib.md5(f"{user_id}_{token}_{time.time()}".encode()).hexdigest()[:10]
        expires_at = (datetime.now() + timedelta(days=30)).isoformat()
        
        if best_server:
            success, msg, pid = bot_manager.deploy_bot_on_server(bot_id, best_server['id'], code, token)
        else:
            # اجرا لوکال
            bot_dir = os.path.join(RUNNING_DIR, bot_id)
            os.makedirs(bot_dir, exist_ok=True)
            
            process = subprocess.Popen(
                [sys.executable, file_path],
                cwd=bot_dir,
                start_new_session=True
            )
            success = True
            pid = process.pid
            msg = ""
        
        if success:
            with get_db() as conn:
                now = datetime.now().isoformat()
                conn.execute('''
                    UPDATE pending_files SET status = 'approved', reviewed_at = ? WHERE id = ?
                ''', (now, pending_id))
                
                if best_server:
                    conn.execute('''
                        INSERT INTO bots (id, user_id, server_id, token, name, username, file_path, status, created_at, expires_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 'running', ?, ?)
                    ''', (bot_id, user_id, best_server['id'], token, bot_info['first_name'], bot_info['username'], file_path, now, expires_at))
                else:
                    conn.execute('''
                        INSERT INTO bots (id, user_id, token, name, username, file_path, folder_path, pid, status, created_at, expires_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'running', ?, ?)
                    ''', (bot_id, user_id, token, bot_info['first_name'], bot_info['username'], file_path, bot_dir, pid, now, expires_at))
                conn.commit()
            
            try:
                bot.send_message(
                    user_id,
                    f"✅ **ربات شما با موفقیت ساخته شد!** 🎉\n\n"
                    f"🤖 نام: {bot_info['first_name']}\n"
                    f"🔗 لینک: https://t.me/{bot_info['username']}\n"
                    f"🆔 آیدی: {bot_id}\n"
                    f"📅 اعتبار: ۳۰ روز\n\n"
                    f"از منوی «ربات‌های من» می‌توانید آن را مدیریت کنید."
                )
            except:
                pass
            
            bot.answer_callback_query(call.id, "✅ ربات ساخته شد")
            bot.delete_message(call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, f"❌ خطا: {msg[:50]}")
            
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ خطا: {str(e)[:50]}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_reject_file_"))
def admin_reject_file(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    pending_id = int(call.data.replace("admin_reject_file_", ""))
    
    msg = bot.send_message(call.message.chat.id, "❌ دلیل رد فایل را وارد کنید:")
    bot.register_next_step_handler(msg, lambda m: process_admin_reject_file(m, pending_id, call))

def process_admin_reject_file(message, pending_id, original_call):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    reason = message.text
    
    with get_db() as conn:
        pending = conn.execute('SELECT user_id FROM pending_files WHERE id = ?', (pending_id,)).fetchone()
        if pending:
            conn.execute('''
                UPDATE pending_files SET status = 'rejected', reviewed_at = ?, review_note = ?
                WHERE id = ?
            ''', (datetime.now().isoformat(), reason, pending_id))
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
    
    bot.reply_to(message, f"✅ فایل کاربر {pending['user_id'] if pending else 'ناشناس'} رد شد")
    try:
        bot.delete_message(original_call.message.chat.id, original_call.message.message_id)
    except:
        pass

# ==================== پنل ادمین - فیش‌ها و آمار ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_receipts")
def admin_receipts_list(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        receipts = conn.execute('''
            SELECT r.*, s.subscription_code, u.first_name
            FROM receipts r
            JOIN subscriptions s ON r.subscription_id = s.id
            JOIN users u ON r.user_id = u.user_id
            WHERE r.status = 'pending'
            ORDER BY r.created_at DESC
        ''').fetchall()
    
    if not receipts:
        bot.send_message(call.message.chat.id, "📸 هیچ فیش در انتظاری وجود ندارد.")
        return
    
    for r in receipts:
        r = dict(r)
        text = f"📸 **فیش واریز**\n\n"
        text += f"👤 کاربر: {r['first_name']} (🆔 {r['user_id']})\n"
        text += f"💰 مبلغ: {r['amount']:,} تومان\n"
        text += f"🆔 کد اشتراک: {r['subscription_code']}\n"
        text += f"🆔 کد پرداخت: {r['payment_code']}\n"
        text += f"📅 تاریخ: {r['created_at'][:16]}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید پرداخت", callback_data=f"admin_approve_payment_{r['id']}"),
            types.InlineKeyboardButton("❌ رد پرداخت", callback_data=f"admin_reject_payment_{r['id']}")
        )
        
        if os.path.exists(r['receipt_path']):
            with open(r['receipt_path'], 'rb') as f:
                bot.send_photo(call.message.chat.id, f, caption=text, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_approve_payment_"))
def admin_approve_payment(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    receipt_id = int(call.data.replace("admin_approve_payment_", ""))
    
    with get_db() as conn:
        receipt = conn.execute('SELECT * FROM receipts WHERE id = ?', (receipt_id,)).fetchone()
        if receipt:
            # فعال کردن اشتراک
            subscription_manager.activate_subscription(receipt['subscription_id'])
            
            # بروزرسانی فیش
            conn.execute('''
                UPDATE receipts SET status = 'approved', reviewed_at = ?, reviewed_by = ?
                WHERE id = ?
            ''', (datetime.now().isoformat(), call.from_user.id, receipt_id))
            conn.commit()
            
            try:
                bot.send_message(
                    receipt['user_id'],
                    f"✅ **پرداخت شما تایید شد!**\n\n"
                    f"اشتراک شما فعال شد.\n"
                    f"📅 اعتبار: ۳۰ روز\n\n"
                    f"📤 حالا می‌توانید از منوی «ارسال فایل ربات» استفاده کنید."
                )
            except:
                pass
    
    bot.answer_callback_query(call.id, "✅ پرداخت تایید شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_reject_payment_"))
def admin_reject_payment(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    receipt_id = int(call.data.replace("admin_reject_payment_", ""))
    
    with get_db() as conn:
        receipt = conn.execute('SELECT * FROM receipts WHERE id = ?', (receipt_id,)).fetchone()
        if receipt:
            conn.execute('''
                UPDATE receipts SET status = 'rejected', reviewed_at = ?, reviewed_by = ?
                WHERE id = ?
            ''', (datetime.now().isoformat(), call.from_user.id, receipt_id))
            conn.execute('DELETE FROM subscriptions WHERE id = ?', (receipt['subscription_id'],))
            conn.commit()
            
            try:
                bot.send_message(
                    receipt['user_id'],
                    f"❌ متاسفانه پرداخت شما تایید نشد.\n\n"
                    f"لطفاً با پشتیبانی تماس بگیرید: @shahraghee13"
                )
            except:
                pass
    
    bot.answer_callback_query(call.id, "❌ پرداخت رد شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_stats_full(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        # آمار کاربران
        total_users = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        active_subs = conn.execute('SELECT COUNT(*) FROM users WHERE active_subscription = 1').fetchone()[0]
        banned_users = conn.execute('SELECT COUNT(*) FROM users WHERE is_banned = 1').fetchone()[0]
        
        # آمار ربات‌ها
        total_bots = conn.execute('SELECT COUNT(*) FROM bots').fetchone()[0]
        running_bots = conn.execute('SELECT COUNT(*) FROM bots WHERE status = "running"').fetchone()[0]
        expired_bots = conn.execute('SELECT COUNT(*) FROM bots WHERE status = "expired"').fetchone()[0]
        
        # آمار سرورها
        total_servers = conn.execute('SELECT COUNT(*) FROM servers').fetchone()[0]
        active_servers = conn.execute('SELECT COUNT(*) FROM servers WHERE status = "active"').fetchone()[0]
        
        # آمار مالی
        total_payments = conn.execute('SELECT COUNT(*) FROM receipts WHERE status = "approved"').fetchone()[0]
        total_amount = conn.execute('SELECT COALESCE(SUM(amount), 0) FROM receipts WHERE status = "approved"').fetchone()[0]
        pending_payments = conn.execute('SELECT COUNT(*) FROM receipts WHERE status = "pending"').fetchone()[0]
        
        # آمار فایل‌ها
        pending_files = conn.execute('SELECT COUNT(*) FROM pending_files WHERE status = "pending"').fetchone()[0]
        approved_files = conn.execute('SELECT COUNT(*) FROM pending_files WHERE status = "approved"').fetchone()[0]
        rejected_files = conn.execute('SELECT COUNT(*) FROM pending_files WHERE status = "rejected"').fetchone()[0]
        
        # میانگین امتیاز AI
        avg_ai_score = conn.execute('SELECT COALESCE(AVG(ai_score), 0) FROM pending_files').fetchone()[0]
    
    text = f"📊 **آمار پیشرفته سیستم**\n\n"
    text += f"👥 **کاربران**\n"
    text += f"• کل کاربران: {total_users}\n"
    text += f"• اشتراک فعال: {active_subs}\n"
    text += f"• مسدود شده: {banned_users}\n\n"
    
    text += f"🤖 **ربات‌ها**\n"
    text += f"• کل ربات‌ها: {total_bots}\n"
    text += f"• در حال اجرا: {running_bots}\n"
    text += f"• منقضی شده: {expired_bots}\n\n"
    
    text += f"🖥️ **سرورها**\n"
    text += f"• کل سرورها: {total_servers}\n"
    text += f"• فعال: {active_servers}\n\n"
    
    text += f"💰 **مالی**\n"
    text += f"• مجموع فروش: {total_amount:,} تومان\n"
    text += f"• تعداد تراکنش‌ها: {total_payments}\n"
    text += f"• در انتظار: {pending_payments}\n\n"
    
    text += f"📥 **فایل‌ها**\n"
    text += f"• در انتظار بررسی: {pending_files}\n"
    text += f"• تایید شده: {approved_files}\n"
    text += f"• رد شده: {rejected_files}\n"
    text += f"• میانگین امتیاز AI: {avg_ai_score:.1f}/100"
    
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back_to_menu(call):
    user_id = call.from_user.id
    is_admin = user_id in ADMIN_IDS
    markup = get_main_menu(is_admin)
    
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "🚀 منوی اصلی:", reply_markup=markup)

# ==================== راهنما و پشتیبانی ====================

@bot.message_handler(func=lambda m: m.text == '📚 راهنما')
def show_guide(message):
    guide_text = """📚 **راهنمای کامل استفاده**

1️⃣ **خرید اشتراک**
   • از منوی «خرید اشتراک» استفاده کنید
   • مبلغ را به کارت اعلام شده واریز کنید
   • تصویر فیش را ارسال کنید

2️⃣ **ارسال فایل ربات**
   • پس از فعال شدن اشتراک
   • فایل `.py` خود را ارسال کنید
   • سیستم با AI امنیت را بررسی می‌کند

3️⃣ **مدیریت ربات‌ها**
   • از منوی «ربات‌های من»
   • مشاهده، توقف، اجرا و حذف ربات

4️⃣ **نصب کتابخانه**
   • از منوی «نصب کتابخانه»
   • ۱۰۰+ کتابخانه آماده نصب

5️⃣ **سیستم رفرال** (به زودی)
   • دعوت از دوستان
   • دریافت ربات اضافه

@shahraghee13 - پشتیبانی"""
    
    bot.send_message(message.chat.id, guide_text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == '📞 پشتیبانی')
def show_support(message):
    bot.send_message(
        message.chat.id,
        "📞 **پشتیبانی**\n\n"
        "آیدی پشتیبانی: @shahraghee13\n\n"
        "سوالات خود را بپرسید، در اسرع وقت پاسخ داده می‌شود."
    )

# ==================== تسک‌های زمانبندی شده ====================

def scheduled_tasks():
    """اجرای تسک‌های زمانبندی شده"""
    while True:
        try:
            # بررسی اشتراک‌های در حال انقضا (هر ساعت)
            subscription_manager.check_expiring_subscriptions()
            
            # باطل کردن اشتراک‌های منقضی (هر ۶ ساعت)
            if datetime.now().hour % 6 == 0:
                subscription_manager.expire_subscriptions()
            
            # بروزرسانی آمار سرورها (هر ۳۰ دقیقه)
            if datetime.now().minute % 30 == 0:
                with get_db() as conn:
                    servers = conn.execute('SELECT id FROM servers WHERE status = "active"').fetchall()
                    for server in servers:
                        server_manager.update_server_stats(server['id'])
            
            time.sleep(3600)  # هر ساعت یکبار
            
        except Exception as e:
            print(f"خطا در تسک زمانبندی: {e}")
            time.sleep(300)

# شروع تسک‌های زمانبندی
scheduler_thread = threading.Thread(target=scheduled_tasks, daemon=True)
scheduler_thread.start()

# ==================== اجرای اصلی ====================

if __name__ == "__main__":
    print("=" * 70)
    print("🚀 ربات مادر حرفه‌ای - نسخه نهایی Enterprise 10.0")
    print("=" * 70)
    print(f"✅ دیتابیس: SQLite با کش Redis")
    print(f"✅ هوش مصنوعی: فعال (بررسی امنیت کد)")
    print(f"✅ سیستم توزیع بار: فعال")
    print(f"✅ کتابخانه‌ها: ۱۰۰+ کتابخانه")
    print(f"✅ ادمین‌ها: {ADMIN_IDS}")
    print(f"✅ Redis: {'فعال' if REDIS_AVAILABLE else 'غیرفعال'}")
    print("=" * 70)
    
    # مقداردهی اولیه دیتابیس
    init_database()
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            print(f"خطا: {e}")
            time.sleep(5)
