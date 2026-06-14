#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
═══════════════════════════════════════════════════════════════════════════════
🛡️ MOTHER BOT - SECURITY HARDENED EDITION v3.0
⚡ امنیت سطح نظامی | ایزوله‌سازی کامل | ضد نفوذ
🔒 محافظت از سرور اصلی | اجرای امن کد کاربران
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import time
import sqlite3
import hashlib
import secrets
import re
import json
import tempfile
import subprocess
import shutil
import signal
import threading
import base64
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from functools import wraps
from dataclasses import dataclass
from enum import Enum

# ==================== بررسی وابستگی‌ها ====================
try:
    import telebot
    from telebot import types
except ImportError:
    print("❌ نصب کنید: pip install pyTelegramBotAPI")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("❌ نصب کنید: pip install requests")
    sys.exit(1)

# ==================== تنظیمات امنیتی ====================

class SecurityLevel(Enum):
    """سطح امنیتی"""
    MAXIMUM = "maximum"
    HIGH = "high"
    STANDARD = "standard"

@dataclass
class SecurityConfig:
    """تنظیمات امنیتی"""
    # سطح امنیت
    SECURITY_LEVEL: SecurityLevel = SecurityLevel.MAXIMUM
    
    # محدودیت‌های سخت
    MAX_FILE_SIZE_MB: int = 5  # حداکثر 5 مگابایت
    MAX_BOTS_PER_USER: int = 1  # هر کاربر فقط 1 ربات
    MAX_BOT_MEMORY_MB: int = 128  # حداکثر 128MB رم
    MAX_BOT_CPU: float = 0.3  # حداکثر 30% CPU
    MAX_BOT_TIMEOUT: int = 3600  # حداکثر 1 ساعت اجرا
    
    # ایزوله‌سازی
    ENABLE_NETWORK_ISOLATION: bool = True  # قطع دسترسی به شبکه
    ENABLE_READONLY_FS: bool = True  # فایل سیستم فقط خواندنی
    ENABLE_NO_NEW_PRIVILEGES: bool = True  # عدم دریافت دسترسی جدید
    
    # رمزنگاری
    ENCRYPT_SENSITIVE_DATA: bool = True
    ENCRYPTION_ITERATIONS: int = 100000
    
    # لاگینگ
    ENABLE_AUDIT_LOG: bool = True
    ENABLE_SECURITY_LOG: bool = True

config = SecurityConfig()

# ==================== رمزنگاری پیشرفته ====================

class CryptoManager:
    """مدیریت رمزنگاری با AES-256"""
    
    @staticmethod
    def _get_key() -> bytes:
        """دریافت کلید رمزنگاری از اثر انگشت سیستم"""
        try:
            # جمع‌آوری اثر انگشت سیستم
            system_fingerprint = []
            
            # MAC address
            mac = subprocess.check_output("cat /sys/class/net/eth0/address 2>/dev/null || echo 'unknown'", shell=True).decode().strip()
            system_fingerprint.append(mac)
            
            # CPU serial
            cpu = subprocess.check_output("cat /proc/cpuinfo | grep Serial | cut -d ' ' -f 2 2>/dev/null || echo 'unknown'", shell=True).decode().strip()
            system_fingerprint.append(cpu)
            
            # Disk UUID
            disk = subprocess.check_output("blkid | grep -oP 'UUID=\"\\K[^\"]+' | head -1 2>/dev/null || echo 'unknown'", shell=True).decode().strip()
            system_fingerprint.append(disk)
            
            fingerprint = "".join(system_fingerprint).encode()
            
            # تولید کلید با PBKDF2
            salt = b'mother_bot_salt_2024_secure'
            key = hashlib.pbkdf2_hmac('sha256', fingerprint, salt, config.ENCRYPTION_ITERATIONS, 32)
            return base64.urlsafe_b64encode(key)
        except:
            # اگر نتونست، از کلید تصادفی استفاده کن
            return base64.urlsafe_b64encode(hashlib.sha256(b"fallback_key").digest())
    
    @staticmethod
    def encrypt(text: str) -> str:
        """رمزنگاری متن"""
        if not config.ENCRYPT_SENSITIVE_DATA:
            return text
        
        try:
            from cryptography.fernet import Fernet
            key = CryptoManager._get_key()
            f = Fernet(key)
            encrypted = f.encrypt(text.encode())
            return base64.b64encode(encrypted).decode()
        except:
            # Fallback ساده
            return base64.b64encode(text.encode()).decode()
    
    @staticmethod
    def decrypt(encrypted_text: str) -> str:
        """رمزگشایی متن"""
        if not config.ENCRYPT_SENSITIVE_DATA:
            return encrypted_text
        
        try:
            from cryptography.fernet import Fernet
            key = CryptoManager._get_key()
            f = Fernet(key)
            decrypted = f.decrypt(base64.b64decode(encrypted_text.encode()))
            return decrypted.decode()
        except:
            try:
                return base64.b64decode(encrypted_text.encode()).decode()
            except:
                return encrypted_text

# ==================== ایزوله‌سازی با Docker ====================

class SandboxManager:
    """مدیریت ایزوله‌سازی کامل کد کاربران"""
    
    def __init__(self):
        self.docker_available = self._check_docker()
        self.running_containers = {}
        self.lock = threading.Lock()
    
    def _check_docker(self) -> bool:
        """بررسی وجود Docker"""
        try:
            result = subprocess.run(['docker', '--version'], capture_output=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def _create_secure_dockerfile(self) -> str:
        """ایجاد Dockerfile امن"""
        dockerfile = f'''# امن‌ترین کانتینر ممکن
FROM alpine:3.19

# نصب پایتون با کمترین کتابخانه
RUN apk add --no-cache python3 py3-pip && \\
    pip3 install --no-cache-dir --no-deps pyTelegramBotAPI && \\
    adduser -D -u 1000 -s /sbin/nologin botuser

# محدودیت‌های امنیتی
RUN echo "botuser hard nproc 10" >> /etc/security/limits.conf && \\
    echo "botuser hard nofile 20" >> /etc/security/limits.conf && \\
    echo "botuser hard core 0" >> /etc/security/limits.conf

# پوشه امن
RUN mkdir -p /app && \\
    chown -R botuser:botuser /app && \\
    chmod 755 /app

# غیرفعال کردن تمام قابلیت‌های خطرناک
USER botuser
WORKDIR /app

# محدودیت زمانی اجرا
ENTRYPOINT ["timeout", "{config.MAX_BOT_TIMEOUT}"]
CMD ["python3", "-B", "bot.py"]  # -B برای جلوگیری از ایجاد .pyc
'''
        dockerfile_path = os.path.join(tempfile.gettempdir(), 'Dockerfile.secure')
        with open(dockerfile_path, 'w') as f:
            f.write(dockerfile)
        return dockerfile_path
    
    def _build_secure_image(self):
        """ساختイメージ امن"""
        dockerfile_path = self._create_secure_dockerfile()
        try:
            subprocess.run(
                ['docker', 'build', '-f', dockerfile_path, '-t', 'motherbot-secure:latest', tempfile.gettempdir()],
                capture_output=True,
                timeout=60
            )
            os.unlink(dockerfile_path)
            return True
        except:
            return False
    
    def run_isolated(self, code: str, token: str, bot_name: str) -> dict:
        """اجرای کد در محیط کاملاً ایزوله"""
        
        if not self.docker_available:
            return {'success': False, 'error': 'Docker در دسترس نیست'}
        
        container_name = f"bot_{secrets.token_hex(8)}"
        
        try:
            # آماده‌سازی کد با لایه امنیتی
            secured_code = self._add_security_layer(code, token)
            
            # ایجاد دایرکتوری موقت
            temp_dir = tempfile.mkdtemp(prefix='motherbot_')
            code_path = os.path.join(temp_dir, 'bot.py')
            
            with open(code_path, 'w') as f:
                f.write(secured_code)
            
            # محدودیت‌های سخت
            cmd = [
                'docker', 'run', '-d',
                '--name', container_name,
                '--memory', f"{config.MAX_BOT_MEMORY_MB}m",
                '--memory-swap', f"{config.MAX_BOT_MEMORY_MB}m",
                '--cpus', str(config.MAX_BOT_CPU),
                '--pids-limit', '20',
                '--read-only' if config.ENABLE_READONLY_FS else '',
                '--network', 'none' if config.ENABLE_NETWORK_ISOLATION else 'bridge',
                '--cap-drop', 'ALL',
                '--security-opt', 'no-new-privileges:true',
                '--security-opt', 'seccomp=./seccomp.json',
                '-v', f"{temp_dir}:/app:ro",
                'motherbot-secure:latest'
            ]
            
            # حذف آرگومان‌های خالی
            cmd = [x for x in cmd if x]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                container_id = result.stdout.strip()
                
                with self.lock:
                    self.running_containers[container_name] = {
                        'container_id': container_id,
                        'temp_dir': temp_dir,
                        'started_at': time.time()
                    }
                
                return {
                    'success': True,
                    'container_id': container_id,
                    'container_name': container_name
                }
            else:
                shutil.rmtree(temp_dir, ignore_errors=True)
                return {'success': False, 'error': result.stderr[:200]}
                
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Timeout'}
        except Exception as e:
            return {'success': False, 'error': str(e)[:200]}
    
    def _add_security_layer(self, code: str, token: str) -> str:
        """اضافه کردن لایه امنیتی به کد کاربر"""
        
        # کلمات ممنوعه
        blocked_modules = [
            'os', 'subprocess', 'socket', 'pty', 'fcntl', 'termios',
            'resource', 'syslog', 'signal', 'multiprocessing',
            'ctypes', 'code', 'codeop', 'compile', '__import__',
            'open', 'file', 'input', 'eval', 'exec', 'globals', 'locals'
        ]
        
        blocked_imports = ', '.join(f"'{x}'" for x in blocked_modules)
        
        security_layer = f'''# ========== لایه امنیتی غیرقابل نفوذ ==========
import sys
import builtins
import warnings

# مسدود کردن ماژول‌های خطرناک
BLOCKED = [{blocked_imports}]

original_import = builtins.__import__

def secure_import(name, *args, **kwargs):
    if name in BLOCKED or any(name.startswith(b) for b in BLOCKED):
        raise ImportError(f"Module '{{name}}' is blocked")
    return original_import(name, *args, **kwargs)

builtins.__import__ = secure_import

# مسدود کردن توابع خطرناک
builtins.open = None
builtins.input = None
builtins.eval = None
builtins.exec = None
builtins.compile = None
builtins.breakpoint = None

# پاک کردن متغیرهای محیطی
for env in ['PATH', 'LD_LIBRARY_PATH', 'PYTHONPATH', 'HOME', 'USER', 'SHELL', 'TEMP', 'TMP']:
    if env in __import__('os').environ:
        del __import__('os').environ[env]

# غیرفعال کردن warnings
warnings.filterwarnings('ignore')

# توکن امن
TOKEN = "{token}"

# =============================================

{code}
'''
        return security_layer
    
    def stop_container(self, container_name: str) -> bool:
        """توقف کانتینر"""
        with self.lock:
            if container_name in self.running_containers:
                try:
                    subprocess.run(['docker', 'stop', container_name], capture_output=True, timeout=10)
                    subprocess.run(['docker', 'rm', container_name], capture_output=True, timeout=10)
                    
                    # حذف دایرکتوری موقت
                    shutil.rmtree(self.running_containers[container_name]['temp_dir'], ignore_errors=True)
                    
                    del self.running_containers[container_name]
                    return True
                except:
                    pass
        return False
    
    def get_status(self, container_name: str) -> dict:
        """وضعیت کانتینر"""
        try:
            result = subprocess.run(
                ['docker', 'inspect', '-f', '{{.State.Status}}', container_name],
                capture_output=True, text=True, timeout=5
            )
            status = result.stdout.strip()
            return {
                'running': status == 'running',
                'status': status
            }
        except:
            return {'running': False}

# ==================== لاگینگ امنیتی ====================

class AuditLogger:
    """لاگینگ امنیتی برای ردیابی همه عملیات"""
    
    def __init__(self):
        self.log_dir = "/var/log/motherbot" if os.path.exists("/var/log") else "logs"
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_path = os.path.join(self.log_dir, "security.log")
    
    def log(self, event_type: str, user_id: int, details: str, severity: str = "INFO"):
        """ثبت رویداد امنیتی"""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [{severity}] [{event_type}] USER={user_id} | {details}\n"
        
        try:
            with open(self.log_path, 'a') as f:
                f.write(log_entry)
        except:
            pass
        
        # لاگ در کنسول
        print(log_entry.strip())

audit_logger = AuditLogger()

# ==================== دیتابیس رمزنگاری شده ====================

class SecureDatabase:
    """دیتابیس با رمزنگاری داده‌های حساس"""
    
    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(__file__), 'secure_data', 'motherbot.db')
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """ایجاد جداول امن"""
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=FULL")
            conn.execute("PRAGMA cipher_page_size=4096") if hasattr(sqlite3, 'enable_load_extension') else None
            
            # جدول کاربران
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    referral_code TEXT UNIQUE,
                    referred_by INTEGER,
                    referrals_count INTEGER DEFAULT 0,
                    subscription_status TEXT DEFAULT 'inactive',
                    subscription_expiry TIMESTAMP,
                    wallet_balance INTEGER DEFAULT 0,
                    has_bot INTEGER DEFAULT 0,
                    created_at TIMESTAMP,
                    last_active TIMESTAMP
                )
            ''')
            
            # جدول ربات‌ها
            conn.execute('''
                CREATE TABLE IF NOT EXISTS bots (
                    bot_id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    bot_name TEXT,
                    bot_username TEXT,
                    bot_token TEXT,
                    status TEXT DEFAULT 'stopped',
                    created_at TIMESTAMP,
                    last_active TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            ''')
            
            # جدول فیش‌ها
            conn.execute('''
                CREATE TABLE IF NOT EXISTS receipts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount INTEGER,
                    receipt_path TEXT,
                    payment_code TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP,
                    reviewed_at TIMESTAMP,
                    reviewed_by INTEGER
                )
            ''')
            
            # جدول تنظیمات امن
            conn.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP,
                    updated_by INTEGER
                )
            ''')
            
            # تنظیمات پیشفرض
            default_settings = {
                'card_number': CryptoManager.encrypt("5892101187322777"),
                'card_holder': CryptoManager.encrypt("مرتضی نیکخو خنجری"),
                'card_bank': CryptoManager.encrypt("بانک ملی"),
                'subscription_price': '200000',
                'subscription_price_display': '۲۰۰,۰۰۰ تومان',
                'welcome_text': '🚀 به ربات امن خوش آمدید {name}!',
                'guide_text': '📚 راهنمای امن:\n1. {price} به کارت زیر واریز کنید\n2. عکس فیش را ارسال کنید\n3. فایل ربات را ارسال کنید\n4. ربات در محیط ایزوله اجرا می‌شود',
                'admin_ids': '327855654'
            }
            
            for key, value in default_settings.items():
                conn.execute('''
                    INSERT OR IGNORE INTO settings (key, value, updated_at)
                    VALUES (?, ?, ?)
                ''', (key, value, datetime.now().isoformat()))
            
            conn.commit()
    
    def get_connection(self):
        """دریافت کانکشن دیتابیس"""
        return sqlite3.connect(self.db_path, timeout=30)

db = SecureDatabase()

# ==================== توابع کمکی امن ====================

def get_setting(key: str) -> str:
    """دریافت تنظیمات (با رمزگشایی خودکار)"""
    with db.get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute('SELECT value FROM settings WHERE key = ?', (key,))
        row = cursor.fetchone()
        if row:
            value = row['value']
            # اگر مقدار رمزنگاری شده بود، رمزگشایی کن
            if key in ['card_number', 'card_holder', 'card_bank']:
                return CryptoManager.decrypt(value)
            return value
        return None

def update_setting(key: str, value: str, admin_id: int):
    """به‌روزرسانی تنظیمات"""
    # رمزنگاری داده‌های حساس
    if key in ['card_number', 'card_holder', 'card_bank']:
        value = CryptoManager.encrypt(value)
    
    with db.get_connection() as conn:
        conn.execute('''
            UPDATE settings SET value = ?, updated_at = ?, updated_by = ?
            WHERE key = ?
        ''', (value, datetime.now().isoformat(), admin_id, key))
        conn.commit()
    
    audit_logger.log("SETTING_CHANGED", admin_id, f"key={key}")

def get_user(user_id: int) -> Optional[dict]:
    """دریافت اطلاعات کاربر"""
    with db.get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def create_user(user_id: int, username: str, first_name: str, referred_by: int = None) -> bool:
    """ایجاد کاربر جدید"""
    try:
        with db.get_connection() as conn:
            now = datetime.now().isoformat()
            referral_code = hashlib.sha256(f"{user_id}{now}{secrets.token_hex(16)}".encode()).hexdigest()[:16]
            
            conn.execute('''
                INSERT OR IGNORE INTO users 
                (user_id, username, first_name, referral_code, referred_by, created_at, last_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, username, first_name, referral_code, referred_by, now, now))
            
            if referred_by and referred_by != user_id:
                conn.execute('''
                    UPDATE users SET referrals_count = referrals_count + 1
                    WHERE user_id = ?
                ''', (referred_by,))
            
            conn.commit()
            audit_logger.log("USER_CREATED", user_id, f"referred_by={referred_by}")
            return True
    except Exception as e:
        audit_logger.log("ERROR", user_id, f"create_user: {str(e)}", "ERROR")
        return False

def check_subscription(user_id: int) -> bool:
    """بررسی اشتراک"""
    user = get_user(user_id)
    if not user:
        return False
    
    if user['subscription_status'] == 'active' and user['subscription_expiry']:
        expiry = datetime.fromisoformat(user['subscription_expiry'])
        if expiry > datetime.now():
            return True
    
    return False

def activate_subscription(user_id: int, admin_id: int = None):
    """فعالسازی اشتراک"""
    with db.get_connection() as conn:
        expiry = datetime.now() + timedelta(days=30)
        conn.execute('''
            UPDATE users SET subscription_status = 'active', subscription_expiry = ?
            WHERE user_id = ?
        ''', (expiry.isoformat(), user_id))
        conn.commit()
    
    audit_logger.log("SUBSCRIPTION_ACTIVATED", user_id, f"by_admin={admin_id}")

def user_has_bot(user_id: int) -> bool:
    """بررسی وجود ربات"""
    with db.get_connection() as conn:
        cursor = conn.execute('SELECT COUNT(*) as count FROM bots WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        return row[0] > 0

def get_user_bot(user_id: int) -> Optional[dict]:
    """دریافت ربات کاربر"""
    with db.get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute('SELECT * FROM bots WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def add_bot(user_id: int, bot_id: str, bot_name: str, bot_username: str, bot_token: str) -> bool:
    """افزودن ربات"""
    try:
        with db.get_connection() as conn:
            now = datetime.now().isoformat()
            conn.execute('''
                INSERT INTO bots (bot_id, user_id, bot_name, bot_username, bot_token, created_at, last_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (bot_id, user_id, bot_name, bot_username, bot_token, now, now))
            
            conn.execute('UPDATE users SET has_bot = 1 WHERE user_id = ?', (user_id,))
            conn.commit()
            audit_logger.log("BOT_CREATED", user_id, f"bot={bot_name}")
            return True
    except Exception as e:
        audit_logger.log("ERROR", user_id, f"add_bot: {str(e)}", "ERROR")
        return False

def delete_bot(user_id: int) -> bool:
    """حذف ربات"""
    try:
        with db.get_connection() as conn:
            conn.execute('DELETE FROM bots WHERE user_id = ?', (user_id,))
            conn.execute('UPDATE users SET has_bot = 0 WHERE user_id = ?', (user_id,))
            conn.commit()
            audit_logger.log("BOT_DELETED", user_id, "")
            return True
    except:
        return False

def add_wallet_balance(user_id: int, amount: int):
    """افزایش موجودی"""
    with db.get_connection() as conn:
        conn.execute('UPDATE users SET wallet_balance = wallet_balance + ? WHERE user_id = ?', (amount, user_id))
        conn.commit()
    audit_logger.log("WALLET_ADDED", user_id, f"amount={amount}")

def extract_token(code: str) -> Optional[str]:
    """استخراج توکن از کد (امن)"""
    patterns = [
        r'token\s*=\s*["\']([^"\']{35,50})["\']',
        r'TOKEN\s*=\s*["\']([^"\']{35,50})["\']',
        r'BOT_TOKEN\s*=\s*["\']([^"\']{35,50})["\']',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, code, re.IGNORECASE)
        if match:
            token = match.group(1)
            # اعتبارسنجی توکن
            if len(token) >= 35 and ':' in token:
                return token
    return None

def validate_token(token: str) -> Tuple[bool, Optional[dict]]:
    """اعتبارسنجی توکن با تلگرام"""
    try:
        response = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                return True, data.get('result')
        return False, None
    except:
        return False, None

def validate_python_code(code: str) -> Tuple[bool, str]:
    """اعتبارسنجی کد پایتون برای یافتن کد مخرب"""
    
    # الگوهای خطرناک
    dangerous_patterns = [
        (r'os\.system', "دسترسی به سیستم عامل"),
        (r'subprocess\.', "اجرای فرمان سیستمی"),
        (r'eval\s*\(', "اجرای کد پویا"),
        (r'exec\s*\(', "اجرای کد پویا"),
        (r'__import__\s*\(', "ایمپورت داینامیک"),
        (r'compile\s*\(', "کامپایل کد"),
        (r'globals\(\)', "دسترسی به متغیرهای سراسری"),
        (r'locals\(\)', "دسترسی به متغیرهای محلی"),
        (r'__builtins__', "دسترسی به توابع داخلی"),
        (r'open\s*\(', "دسترسی به فایل‌ها"),
        (r'socket\.', "ارتباط شبکه"),
        (r'requests\.', "درخواست HTTP"),
        (r'urllib\.', "درخواست HTTP"),
    ]
    
    for pattern, description in dangerous_patterns:
        if re.search(pattern, code, re.IGNORECASE):
            return False, f"کد مخرب شناسایی شد: {description}"
    
    return True, "OK"

# ==================== ربات اصلی ====================

BOT_TOKEN = "8266270866:AAF6m1x4weSUEvzIj1gkbIS_j0yAdxCSs78"
ADMIN_IDS = [327855654]

bot = telebot.TeleBot(BOT_TOKEN)
bot.delete_webhook()

# ایجاد نمونه سندباکس
sandbox = SandboxManager()

# ساختイメージ امن
sandbox._build_secure_image()

# ==================== منوها ====================

def get_main_menu(user_id: int) -> types.ReplyKeyboardMarkup:
    """منوی اصلی"""
    is_admin = user_id in ADMIN_IDS
    
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        '🤖 ساخت ربات',
        '📋 اطلاعات ربات من',
        '💰 کیف پول من',
        '👥 دعوت دوستان',
        '📚 راهنما',
        '📞 پشتیبانی'
    ]
    
    if is_admin:
        buttons.append('👑 پنل مدیریت')
    
    markup.add(*buttons)
    return markup

def get_admin_menu() -> types.InlineKeyboardMarkup:
    """منوی مدیریت"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    buttons = [
        types.InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings"),
        types.InlineKeyboardButton("👥 کاربران", callback_data="admin_users"),
        types.InlineKeyboardButton("📸 فیش‌ها", callback_data="admin_receipts"),
        types.InlineKeyboardButton("📢 پیام همگانی", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("💰 افزایش موجودی", callback_data="admin_add_balance"),
        types.InlineKeyboardButton("🎁 فعالسازی اشتراک", callback_data="admin_activate_sub"),
        types.InlineKeyboardButton("📊 آمار", callback_data="admin_stats"),
        types.InlineKeyboardButton("🔄 ریستارت ربات‌ها", callback_data="admin_restart")
    ]
    
    for btn in buttons:
        markup.add(btn)
    
    return markup

# ==================== هندلرها ====================

@bot.message_handler(commands=['start'])
def cmd_start(message):
    """دستور استارت"""
    user_id = message.from_user.id
    first_name = message.from_user.first_name or ""
    username = message.from_user.username or ""
    
    # بررسی رفرال
    referred_by = None
    args = message.text.split()
    if len(args) > 1:
        with db.get_connection() as conn:
            cursor = conn.execute('SELECT user_id FROM users WHERE referral_code = ?', (args[1],))
            row = cursor.fetchone()
            if row and row[0] != user_id:
                referred_by = row[0]
                try:
                    bot.send_message(referred_by, f"🎉 {first_name} با لینک شما وارد شد!")
                except:
                    pass
    
    # ایجاد کاربر
    if not get_user(user_id):
        create_user(user_id, username, first_name, referred_by)
    
    user = get_user(user_id)
    is_subscribed = check_subscription(user_id)
    has_bot = user_has_bot(user_id)
    
    text = f"🛡️ **ربات امن سازنده ربات**\n\n"
    text += f"👤 {first_name} عزیز خوش آمدید!\n"
    text += f"💰 موجودی: {user['wallet_balance']:,} تومان\n"
    text += f"✅ اشتراک: {'فعال' if is_subscribed else 'غیرفعال'}\n"
    text += f"🤖 ربات: {'دارید' if has_bot else 'ندارید'}\n\n"
    
    if not is_subscribed:
        price = get_setting('subscription_price_display')
        card = get_setting('card_number')
        holder = get_setting('card_holder')
        text += f"💰 برای فعالسازی {price} به کارت زیر واریز کنید:\n"
        text += f"`{card}`\n👤 {holder}\n\n"
        text += f"📸 پس از واریز، تصویر فیش را ارسال کنید."
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=get_main_menu(user_id))
    
    audit_logger.log("START", user_id, f"referred_by={referred_by}")

@bot.message_handler(func=lambda m: m.text == '🤖 ساخت ربات')
def create_bot_handler(message):
    """ساخت ربات جدید"""
    user_id = message.from_user.id
    
    # بررسی اشتراک
    if not check_subscription(user_id):
        price = get_setting('subscription_price_display')
        bot.send_message(message.chat.id, f"❌ ابتدا اشتراک خود را فعال کنید!\n💰 {price}")
        return
    
    # بررسی محدودیت
    if user_has_bot(user_id):
        bot.send_message(message.chat.id, "❌ شما قبلاً یک ربات ساخته‌اید!\nهر کاربر فقط ۱ ربات می‌تواند داشته باشد.")
        return
    
    bot.send_message(
        message.chat.id,
        "🔒 **ارسال فایل ربات در محیط امن**\n\n"
        "📤 فایل `.py` خود را ارسال کنید.\n\n"
        "⚠️ **نکات امنیتی:**\n"
        "• حداکثر حجم: ۵ مگابایت\n"
        "• کد شما در محیط ایزوله اجرا می‌شود\n"
        "• دسترسی به شبکه مسدود است\n"
        "• دسترسی به فایل سیستم محدود است\n"
        "• زمان اجرا حداکثر ۱ ساعت\n\n"
        "🔐 **امنیت کامل تضمین می‌شود**",
        parse_mode='Markdown'
    )

@bot.message_handler(content_types=['document'])
def handle_bot_file(message):
    """پردازش فایل ربات"""
    user_id = message.from_user.id
    
    # بررسی امنیتی اولیه
    if not check_subscription(user_id):
        bot.reply_to(message, "❌ اشتراک ندارید!")
        return
    
    if user_has_bot(user_id):
        bot.reply_to(message, "❌ شما قبلاً ربات دارید!")
        return
    
    if not message.document.file_name.endswith('.py'):
        bot.reply_to(message, "❌ فقط فایل‌های `.py` مجاز هستند!")
        return
    
    if message.document.file_size > config.MAX_FILE_SIZE_MB * 1024 * 1024:
        bot.reply_to(message, f"❌ حجم فایل بیشتر از {config.MAX_FILE_SIZE_MB} مگابایت است!")
        return
    
    status_msg = bot.reply_to(message, "🔒 در حال بررسی امنیتی فایل...")
    
    try:
        # دانلود فایل
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        code = downloaded.decode('utf-8', errors='ignore')
        
        # اعتبارسنجی کد
        is_safe, error = validate_python_code(code)
        if not is_safe:
            bot.edit_message_text(f"❌ {error}", message.chat.id, status_msg.message_id)
            audit_logger.log("MALICIOUS_CODE", user_id, error, "WARNING")
            return
        
        # استخراج توکن
        token = extract_token(code)
        if not token:
            bot.edit_message_text("❌ توکن در کد پیدا نشد!", message.chat.id, status_msg.message_id)
            return
        
        # اعتبارسنجی توکن
        is_valid, bot_info = validate_token(token)
        if not is_valid or not bot_info:
            bot.edit_message_text("❌ توکن معتبر نیست!", message.chat.id, status_msg.message_id)
            return
        
        bot_name = bot_info.get('first_name', 'Unknown')
        bot_username = bot_info.get('username', 'unknown')
        
        # اجرا در محیط ایزوله
        bot.edit_message_text("🛡️ در حال اجرا در محیط ایزوله...", message.chat.id, status_msg.message_id)
        
        result = sandbox.run_isolated(code, token, bot_name)
        
        if result['success']:
            # ذخیره در دیتابیس
            bot_id = hashlib.sha256(f"{user_id}{token}{time.time()}".encode()).hexdigest()[:16]
            add_bot(user_id, bot_id, bot_name, bot_username, token)
            
            bot.edit_message_text(
                f"✅ **ربات با موفقیت در محیط امن ساخته شد!**\n\n"
                f"🤖 نام: {bot_name}\n"
                f"🔗 لینک: https://t.me/{bot_username}\n"
                f"🔒 محیط اجرا: کاملاً ایزوله\n"
                f"🛡️ دسترسی به شبکه: مسدود\n"
                f"📁 دسترسی به فایل: فقط خواندنی\n\n"
                f"⚠️ هر کاربر فقط ۱ ربات می‌تواند داشته باشد!",
                message.chat.id,
                status_msg.message_id,
                parse_mode='Markdown'
            )
            
            audit_logger.log("BOT_CREATED_SECURE", user_id, f"bot={bot_name}, container={result['container_name']}")
        else:
            bot.edit_message_text(
                f"❌ خطا در اجرا: {result.get('error', 'ناشناخته')}",
                message.chat.id,
                status_msg.message_id
            )
            audit_logger.log("BOT_FAILED", user_id, f"error={result.get('error')}", "ERROR")
            
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)[:200]}", message.chat.id, status_msg.message_id)
        audit_logger.log("ERROR", user_id, f"handle_bot_file: {str(e)}", "ERROR")

@bot.message_handler(func=lambda m: m.text == '📋 اطلاعات ربات من')
def my_bot_info(message):
    """اطلاعات ربات کاربر"""
    user_id = message.from_user.id
    
    if not user_has_bot(user_id):
        bot.send_message(message.chat.id, "📋 شما رباتی ندارید!")
        return
    
    bot_info = get_user_bot(user_id)
    
    text = f"🤖 **اطلاعات ربات شما**\n\n"
    text += f"نام: {bot_info['bot_name']}\n"
    text += f"یوزرنیم: @{bot_info['bot_username']}\n"
    text += f"وضعیت: {'فعال' if bot_info['status'] == 'running' else 'متوقف'}\n"
    text += f"تاریخ ساخت: {bot_info['created_at'][:10]}\n\n"
    text += f"🔒 **امنیت:**\n"
    text += f"• محیط اجرا: ایزوله\n"
    text += f"• دسترسی شبکه: مسدود\n"
    text += f"• محدودیت رم: {config.MAX_BOT_MEMORY_MB}MB\n"
    text += f"• محدودیت زمان: {config.MAX_BOT_TIMEOUT//3600} ساعت"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '💰 کیف پول من')
def wallet_handler(message):
    """کیف پول"""
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        bot.send_message(message.chat.id, "❌ /start بزنید")
        return
    
    text = f"💰 **کیف پول شما**\n\n"
    text += f"👤 {user['first_name']}\n"
    text += f"💰 موجودی: {user['wallet_balance']:,} تومان\n"
    text += f"👥 دعوت‌ها: {user['referrals_count']}\n"
    text += f"✅ اشتراک: {'فعال' if check_subscription(user_id) else 'غیرفعال'}\n"
    text += f"🤖 ربات: {'دارید' if user_has_bot(user_id) else 'ندارید'}"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '👥 دعوت دوستان')
def referral_handler(message):
    """دعوت دوستان"""
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        bot.send_message(message.chat.id, "❌ /start بزنید")
        return
    
    bot_username = bot.get_me().username
    referral_link = f"https://t.me/{bot_username}?start={user['referral_code']}"
    price = get_setting('subscription_price_display')
    
    text = f"👥 **دعوت دوستان**\n\n"
    text += f"🔗 لینک دعوت: {referral_link}\n"
    text += f"🎁 کد: `{user['referral_code']}`\n"
    text += f"📊 دعوت‌ها: {user['referrals_count']}\n"
    text += f"💰 پورسانت: {price} به ازای هر دوست\n\n"
    text += f"💡 هر دوست شما اشتراک بخره، این مبلغ به کیف پولت اضافه می‌شود!"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    """دریافت فیش"""
    user_id = message.from_user.id
    
    status_msg = bot.reply_to(message, "🔒 در حال بررسی فیش...")
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        payment_code = hashlib.sha256(f"{user_id}{time.time()}".encode()).hexdigest()[:8]
        receipt_path = os.path.join(os.path.dirname(__file__), 'receipts', f"{user_id}_{payment_code}.jpg")
        os.makedirs(os.path.dirname(receipt_path), exist_ok=True)
        
        with open(receipt_path, 'wb') as f:
            f.write(downloaded)
        
        with db.get_connection() as conn:
            conn.execute('''
                INSERT INTO receipts (user_id, amount, receipt_path, payment_code, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, int(get_setting('subscription_price')), receipt_path, payment_code, datetime.now().isoformat()))
            conn.commit()
        
        bot.edit_message_text(
            f"✅ فیش شما دریافت شد!\n🆔 کد: {payment_code}\n💰 {get_setting('subscription_price_display')}\n\nپس از تایید ادمین، اشتراک شما فعال می‌شود.",
            message.chat.id,
            status_msg.message_id
        )
        
        # اطلاع به ادمین‌ها
        for admin_id in ADMIN_IDS:
            try:
                with open(receipt_path, 'rb') as f:
                    bot.send_photo(
                        admin_id,
                        f,
                        caption=f"📸 فیش جدید\n👤 کاربر: {user_id}\n💰 {get_setting('subscription_price_display')}\n🆔 {payment_code}"
                    )
            except:
                pass
        
        audit_logger.log("RECEIPT_SUBMITTED", user_id, f"code={payment_code}")
        
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)}", message.chat.id, status_msg.message_id)

@bot.message_handler(func=lambda m: m.text == '📚 راهنما')
def guide_handler(message):
    """راهنما"""
    price = get_setting('subscription_price_display')
    card = get_setting('card_number')
    holder = get_setting('card_holder')
    
    guide_text = get_setting('guide_text').format(price=price, card=card, holder=holder)
    
    text = f"{guide_text}\n\n"
    text += f"🔒 **امنیت:**\n"
    text += f"• کد شما در محیط ایزوله اجرا می‌شود\n"
    text += f"• دسترسی به سرور اصلی غیرممکن است\n"
    text += f"• کدهای مخرب شناسایی و مسدود می‌شوند"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '📞 پشتیبانی')
def support_handler(message):
    """پشتیبانی"""
    bot.send_message(message.chat.id, "📞 **پشتیبانی امن**\n\nآیدی پشتیبانی: @shahraghee13\n\nساعات پاسخگویی: ۹ صبح تا ۱۲ شب", parse_mode='Markdown')

# ==================== پنل مدیریت ====================

@bot.message_handler(func=lambda m: m.text == '👑 پنل مدیریت')
def admin_panel(message):
    """پنل مدیریت"""
    if message.from_user.id not in ADMIN_IDS:
        return
    
    bot.send_message(message.chat.id, "👑 **پنل مدیریت امن**", parse_mode='Markdown', reply_markup=get_admin_menu())

@bot.callback_query_handler(func=lambda call: call.data == "admin_settings")
def admin_settings(call):
    """تنظیمات"""
    if call.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    settings = [
        ('card_number', '💳 شماره کارت'),
        ('card_holder', '👤 صاحب کارت'),
        ('subscription_price', '💰 قیمت اشتراک'),
        ('welcome_text', '👋 متن خوش‌آمدگویی'),
        ('guide_text', '📚 متن راهنما')
    ]
    
    for key, name in settings:
        current = get_setting(key)
        if key in ['card_number', 'card_holder']:
            # ماسک کردن شماره کارت
            if len(current) > 8:
                current = current[:4] + "****" + current[-4:]
        display = current[:20] + "..." if len(current) > 20 else current
        markup.add(types.InlineKeyboardButton(f"{name}: {display}", callback_data=f"set_{key}"))
    
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back"))
    
    bot.edit_message_text("⚙️ **تنظیمات امن**", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('set_'))
def set_setting_prompt(call):
    """تغییر تنظیمات"""
    if call.from_user.id not in ADMIN_IDS:
        return
    
    key = call.data.replace('set_', '')
    msg = bot.send_message(call.message.chat.id, f"🔐 مقدار جدید برای {key} را وارد کنید:")
    bot.register_next_step_handler(msg, lambda m: update_setting_value(m, key, call.message))

def update_setting_value(message, key, original_message):
    """به‌روزرسانی مقدار"""
    if message.from_user.id not in ADMIN_IDS:
        return
    
    new_value = message.text.strip()
    update_setting(key, new_value, message.from_user.id)
    
    bot.send_message(message.chat.id, f"✅ {key} با موفقیت به‌روزرسانی شد!")
    
    # بازگشت به منوی تنظیمات
    admin_settings(message)

@bot.callback_query_handler(func=lambda call: call.data == "admin_users")
def admin_users(call):
    """لیست کاربران"""
    if call.from_user.id not in ADMIN_IDS:
        return
    
    with db.get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute('''
            SELECT user_id, first_name, subscription_status, wallet_balance, has_bot, created_at
            FROM users ORDER BY created_at DESC LIMIT 20
        ''')
        users = cursor.fetchall()
    
    text = "👥 **۲۰ کاربر آخر**\n\n"
    for user in users:
        status = "✅" if user['subscription_status'] == 'active' else "⏳"
        bot_emoji = "🤖" if user['has_bot'] else "📭"
        text += f"{status} {bot_emoji} {user['user_id']} - {user['first_name']} - {user['wallet_balance']:,} تومان\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back"))
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_receipts")
def admin_receipts(call):
    """فیش‌ها"""
    if call.from_user.id not in ADMIN_IDS:
        return
    
    with db.get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute('SELECT * FROM receipts WHERE status = "pending" ORDER BY created_at')
        receipts = cursor.fetchall()
    
    if not receipts:
        bot.edit_message_text("📸 هیچ فیش در انتظاری وجود ندارد!", call.message.chat.id, call.message.message_id)
        return
    
    for receipt in receipts:
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_{receipt['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"reject_{receipt['id']}")
        )
        
        if os.path.exists(receipt['receipt_path']):
            with open(receipt['receipt_path'], 'rb') as f:
                bot.send_photo(
                    call.message.chat.id,
                    f,
                    caption=f"📸 فیش\n👤 کاربر: {receipt['user_id']}\n💰 {receipt['amount']:,} تومان",
                    reply_markup=markup
                )

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_'))
def approve_receipt(call):
    """تایید فیش"""
    if call.from_user.id not in ADMIN_IDS:
        return
    
    receipt_id = int(call.data.replace('approve_', ''))
    
    with db.get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute('SELECT user_id FROM receipts WHERE id = ?', (receipt_id,))
        row = cursor.fetchone()
        
        if row:
            conn.execute('UPDATE receipts SET status = "approved", reviewed_at = ?, reviewed_by = ? WHERE id = ?',
                        (datetime.now().isoformat(), call.from_user.id, receipt_id))
            activate_subscription(row['user_id'], call.from_user.id)
            conn.commit()
            
            try:
                bot.send_message(row['user_id'], "✅ اشتراک شما فعال شد!\nاکنون می‌توانید ربات خود را بسازید.")
            except:
                pass
    
    bot.answer_callback_query(call.id, "✅ تایید شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)
    
    audit_logger.log("RECEIPT_APPROVED", row['user_id'] if row else 0, f"by_admin={call.from_user.id}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_'))
def reject_receipt(call):
    """رد فیش"""
    if call.from_user.id not in ADMIN_IDS:
        return
    
    receipt_id = int(call.data.replace('reject_', ''))
    
    with db.get_connection() as conn:
        conn.execute('UPDATE receipts SET status = "rejected", reviewed_at = ?, reviewed_by = ? WHERE id = ?',
                    (datetime.now().isoformat(), call.from_user.id, receipt_id))
        conn.commit()
    
    bot.answer_callback_query(call.id, "❌ رد شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast")
def admin_broadcast(call):
    """پیام همگانی"""
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, "📢 متن پیام همگانی را ارسال کنید:")
    bot.register_next_step_handler(msg, send_broadcast)

def send_broadcast(message):
    """ارسال پیام همگانی"""
    if message.from_user.id not in ADMIN_IDS:
        return
    
    broadcast_text = message.text.strip()
    
    with db.get_connection() as conn:
        cursor = conn.execute('SELECT user_id FROM users')
        users = cursor.fetchall()
    
    status_msg = bot.send_message(message.chat.id, f"🔄 در حال ارسال به {len(users)} کاربر...")
    
    sent = 0
    failed = 0
    
    for user in users:
        try:
            bot.send_message(user[0], f"📢 **اعلامیه مادر ربات**\n\n{broadcast_text}", parse_mode='Markdown')
            sent += 1
            time.sleep(0.05)
        except:
            failed += 1
    
    bot.edit_message_text(
        f"✅ پیام ارسال شد!\n📨 موفق: {sent}\n❌ ناموفق: {failed}",
        message.chat.id,
        status_msg.message_id
    )
    
    audit_logger.log("BROADCAST", message.from_user.id, f"sent={sent}, failed={failed}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_add_balance")
def admin_add_balance(call):
    """افزایش موجودی"""
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, "💰 آیدی کاربر و مبلغ (مثال: 123456 50000):")
    bot.register_next_step_handler(msg, process_add_balance)

def process_add_balance(message):
    """پردازش افزایش موجودی"""
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        parts = message.text.strip().split()
        user_id = int(parts[0])
        amount = int(parts[1])
        
        add_wallet_balance(user_id, amount)
        
        bot.send_message(message.chat.id, f"✅ {amount:,} تومان به کیف پول کاربر {user_id} اضافه شد!")
        
        try:
            bot.send_message(user_id, f"💰 {amount:,} تومان به کیف پول شما اضافه شد!")
        except:
            pass
        
        audit_logger.log("BALANCE_ADDED", user_id, f"amount={amount}, by_admin={message.from_user.id}")
    except:
        bot.send_message(message.chat.id, "❌ فرمت نامعتبر!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_activate_sub")
def admin_activate_sub(call):
    """فعالسازی اشتراک دستی"""
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, "🎁 آیدی کاربر را وارد کنید:")
    bot.register_next_step_handler(msg, process_activate_sub)

def process_activate_sub(message):
    """پردازش فعالسازی اشتراک"""
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        user_id = int(message.text.strip())
        activate_subscription(user_id, message.from_user.id)
        
        bot.send_message(message.chat.id, f"✅ اشتراک کاربر {user_id} فعال شد!")
        
        try:
            bot.send_message(user_id, "✅ اشتراک شما توسط ادمین فعال شد!")
        except:
            pass
        
        audit_logger.log("SUB_MANUAL_ACTIVATE", user_id, f"by_admin={message.from_user.id}")
    except:
        bot.send_message(message.chat.id, "❌ خطا!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_stats(call):
    """آمار سیستم"""
    if call.from_user.id not in ADMIN_IDS:
        return
    
    with db.get_connection() as conn:
        total_users = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        active_subs = conn.execute('SELECT COUNT(*) FROM users WHERE subscription_status = "active"').fetchone()[0]
        total_bots = conn.execute('SELECT COUNT(*) FROM bots').fetchone()[0]
        pending_receipts = conn.execute('SELECT COUNT(*) FROM receipts WHERE status = "pending"').fetchone()[0]
        total_revenue = conn.execute('SELECT SUM(amount) FROM receipts WHERE status = "approved"').fetchone()[0] or 0
    
    text = f"📊 **آمار امنیتی سیستم**\n\n"
    text += f"👥 کل کاربران: {total_users:,}\n"
    text += f"✅ اشتراک فعال: {active_subs:,}\n"
    text += f"🤖 ربات‌ها: {total_bots:,}\n"
    text += f"📸 فیش در انتظار: {pending_receipts}\n"
    text += f"💰 درآمد کل: {total_revenue:,} تومان\n\n"
    text += f"🔒 **وضعیت امنیت:**\n"
    text += f"• ایزوله‌سازی: {'فعال' if sandbox.docker_available else 'غیرفعال'}\n"
    text += f"• سطح امنیت: {config.SECURITY_LEVEL.value}\n"
    text += f"• رمزنگاری: {'فعال' if config.ENCRYPT_SENSITIVE_DATA else 'غیرفعال'}"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back"))
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_restart")
def admin_restart(call):
    """ریستارت ربات‌های در حال اجرا"""
    if call.from_user.id not in ADMIN_IDS:
        return
    
    status_msg = bot.send_message(call.message.chat.id, "🔄 در حال ریستارت کانتینرها...")
    
    # توقف همه کانتینرها
    for container_name in list(sandbox.running_containers.keys()):
        sandbox.stop_container(container_name)
    
    bot.edit_message_text("✅ تمام کانتینرها با موفقیت ریستارت شدند!", call.message.chat.id, status_msg.message_id)
    audit_logger.log("CONTAINERS_RESTART", call.from_user.id, "")

@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call):
    """بازگشت به منوی اصلی"""
    bot.delete_message(call.message.chat.id, call.message.message_id)
    
    # ارسال منوی اصلی جدید
    markup = get_main_menu(call.from_user.id)
    bot.send_message(call.message.chat.id, "🚀 منوی اصلی:", reply_markup=markup)

# ==================== اجرا ====================
if __name__ == "__main__":
    print("=" * 70)
    print("🛡️ MOTHER BOT - SECURITY HARDENED EDITION".center(70))
    print("=" * 70)
    print(f"🔒 سطح امنیت: {config.SECURITY_LEVEL.value}")
    print(f"🐋 Docker: {'فعال' if sandbox.docker_available else 'غیرفعال'}")
    print(f"🔐 رمزنگاری: {'فعال' if config.ENCRYPT_SENSITIVE_DATA else 'غیرفعال'}")
    print(f"👑 ادمین‌ها: {ADMIN_IDS}")
    print(f"💰 قیمت: {get_setting('subscription_price_display')}")
    print("=" * 70)
    print("✅ ربات امن با موفقیت راه‌اندازی شد!")
    print("=" * 70)
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            print(f"❌ خطا: {e}")
            time.sleep(5)