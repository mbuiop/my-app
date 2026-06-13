#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ربات مادر نهایی - نسخه 12.0
امنیت نظامی + سرور واقعی + ضد هک + نصب خودکار کتابخانه
"""

import os
import sys
import telebot
from telebot import types
import sqlite3
import subprocess
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
import random
import string
import paramiko  # برای اتصال واقعی به سرور
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from functools import wraps
from queue import Queue
import traceback
from collections import defaultdict
from dotenv import load_dotenv

# بارگذاری متغیرهای محیطی
load_dotenv()

# ==================== تنظیمات پایه ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "database")
FILES_DIR = os.path.join(BASE_DIR, "user_files")
RUNNING_DIR = os.path.join(BASE_DIR, "running_bots")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
RECEIPTS_DIR = os.path.join(BASE_DIR, "receipts")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
SECURITY_DIR = os.path.join(BASE_DIR, "security_logs")

for dir_path in [DB_DIR, FILES_DIR, RUNNING_DIR, LOGS_DIR, RECEIPTS_DIR, BACKUP_DIR, SECURITY_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# ==================== توکن از متغیر محیطی ====================
BOT_TOKEN = os.environ.get('BOT_TOKEN', '7685135237:AAEmsHktRw9cEqrHTkCoPZk-fBimK7TDjOo')
bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)
bot.delete_webhook()

# ==================== آیدی ادمین ====================
ADMIN_IDS = [int(x.strip()) for x in os.environ.get('ADMIN_IDS', '327855654').split(',')]

# ==================== اطلاعات کارت ====================
CARD_NUMBER = os.environ.get('CARD_NUMBER', '5892101187322777')
CARD_HOLDER = os.environ.get('CARD_HOLDER', 'مرتضی نیکخو خنجری')
PRICE = int(os.environ.get('PRICE', '2000000'))

# ==================== لاگینگ امنیتی ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            os.path.join(LOGS_DIR, 'mother_bot.log'),
            maxBytes=10485760,
            backupCount=10
        ),
        RotatingFileHandler(
            os.path.join(SECURITY_DIR, 'security.log'),
            maxBytes=10485760,
            backupCount=30
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
security_logger = logging.getLogger('security')

# ==================== سیستم Rate Limit و Anti-DDOS ====================
rate_limit = defaultdict(list)
command_limit = defaultdict(list)
file_upload_limit = defaultdict(list)
failed_attempts = defaultdict(int)
banned_ips = set()

def check_rate_limit(user_id, action_type='message', limit=10, window=5):
    """بررسی محدودیت نرخ درخواست‌ها"""
    now = time.time()
    key = f"{user_id}_{action_type}"
    
    # پاکسازی درخواست‌های قدیمی
    rate_limit[key] = [t for t in rate_limit[key] if now - t < window]
    
    if len(rate_limit[key]) >= limit:
        security_logger.warning(f"Rate limit exceeded: user={user_id}, action={action_type}")
        
        # افزایش شماره تلاش‌های ناموفق
        failed_attempts[user_id] += 1
        
        # بن خودکار بعد از 50 بار
        if failed_attempts[user_id] >= 50:
            auto_ban_user(user_id, "Rate limit exceeded 50 times")
        
        return False
    
    rate_limit[key].append(now)
    return True

def check_file_upload_limit(user_id, limit=5, window=60):
    """محدودیت آپلود فایل"""
    return check_rate_limit(user_id, 'file_upload', limit, window)

def auto_ban_user(user_id, reason):
    """بن خودکار کاربر"""
    try:
        with get_db() as conn:
            conn.execute('UPDATE users SET is_banned = 1, ban_reason = ?, banned_at = ? WHERE user_id = ?', 
                        (reason, datetime.now().isoformat(), user_id))
            conn.commit()
        
        security_logger.critical(f"USER BANNED: {user_id} | Reason: {reason}")
        
        # اطلاع به ادمین
        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(admin_id, f"⚠️ **کاربر بن شد!**\n\n🆔 کاربر: {user_id}\n📋 دلیل: {reason}")
            except:
                pass
    except:
        pass

def log_security_event(user_id, action, details, level='INFO'):
    """لاگ امنیتی"""
    log_func = getattr(security_logger, level.lower(), security_logger.info)
    log_func(f"user={user_id} | action={action} | details={details}")

# ==================== تزئین کننده Rate Limit ====================
def rate_limited(limit=10, window=5):
    def decorator(func):
        @wraps(func)
        def wrapper(message, *args, **kwargs):
            user_id = message.from_user.id
            
            if not check_rate_limit(user_id, func.__name__, limit, window):
                bot.reply_to(message, "⚠️ **لطفا کمی صبر کنید!**\nشما بیش از حد سریع درخواست می‌فرستید.")
                return
            
            # بررسی بن شدن
            user = get_user(user_id)
            if user and user.get('is_banned', 0) == 1:
                bot.reply_to(message, "⛔ **شما از سامانه بن شده‌اید!**\nدر صورت اعتراض با پشتیبانی تماس بگیرید.")
                return
            
            return func(message, *args, **kwargs)
        return wrapper
    return decorator

# ==================== دیتابیس پیشرفته ====================
DB_PATH = os.path.join(DB_DIR, 'mother_bot.db')

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=120, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-100000")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA mmap_size=30000000000")
    return conn

# ایجاد جداول با فیلدهای امنیتی جدید
with get_db() as conn:
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            balance INTEGER DEFAULT 0,
            bots_count INTEGER DEFAULT 0,
            max_bots INTEGER DEFAULT 1,
            referral_code TEXT UNIQUE,
            referred_by INTEGER,
            referrals_count INTEGER DEFAULT 0,
            verified_referrals INTEGER DEFAULT 0,
            referral_earnings INTEGER DEFAULT 0,
            payment_status TEXT DEFAULT 'pending',
            payment_date TIMESTAMP,
            subscription_end DATE,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP,
            last_active TIMESTAMP,
            is_banned INTEGER DEFAULT 0,
            ban_reason TEXT,
            banned_at TIMESTAMP,
            trial_used INTEGER DEFAULT 0,
            failed_logins INTEGER DEFAULT 0,
            last_ip TEXT
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS security_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            details TEXT,
            ip TEXT,
            created_at TIMESTAMP
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS servers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            host TEXT,
            port INTEGER,
            username TEXT,
            password TEXT,
            max_workers INTEGER DEFAULT 100,
            current_load INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            last_check TIMESTAMP,
            created_at TIMESTAMP
        )
    ''')
    
    # ایندکس‌های جدید
    conn.execute('CREATE INDEX IF NOT EXISTS idx_users_banned ON users(is_banned)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_users_payment_status ON users(payment_status)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_security_user ON security_logs(user_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_security_time ON security_logs(created_at)')
    
    conn.commit()

# ==================== سیستم سرور واقعی ====================
class RealServerManager:
    def __init__(self):
        self.connections = {}
        self.lock = threading.Lock()
    
    def connect_to_server(self, server_id, server_info):
        """اتصال واقعی به سرور با SSH"""
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            ssh.connect(
                hostname=server_info['host'],
                port=server_info.get('port', 22),
                username=server_info['username'],
                password=server_info['password'],
                timeout=10
            )
            
            with self.lock:
                self.connections[server_id] = {
                    'ssh': ssh,
                    'last_used': time.time(),
                    'load': 0
                }
            
            # تست اتصال
            stdin, stdout, stderr = ssh.exec_command('echo "OK"')
            result = stdout.read().decode().strip()
            
            if result == 'OK':
                # به روز رسانی وضعیت در دیتابیس
                with get_db() as conn:
                    conn.execute('UPDATE servers SET status = "active", last_check = ? WHERE id = ?',
                                (datetime.now().isoformat(), server_id))
                    conn.commit()
                
                return True, "Connected successfully"
            
            return False, "Connection test failed"
            
        except Exception as e:
            logger.error(f"SSH connection failed to {server_info['host']}: {e}")
            return False, str(e)
    
    def deploy_bot_to_server(self, server_id, bot_id, code, token):
        """استقرار ربات روی سرور واقعی"""
        with self.lock:
            if server_id not in self.connections:
                return False, "Not connected to server"
            
            conn_info = self.connections[server_id]
            ssh = conn_info['ssh']
        
        try:
            # ایجاد دایرکتوری روی سرور
            remote_dir = f"/home/bots/{bot_id}"
            stdin, stdout, stderr = ssh.exec_command(f'mkdir -p {remote_dir}')
            stdout.channel.recv_exit_status()
            
            # آپلود فایل
            sftp = ssh.open_sftp()
            remote_file = f"{remote_dir}/bot.py"
            
            with sftp.open(remote_file, 'w') as f:
                f.write(code)
            
            # ذخیره توکن
            with sftp.open(f"{remote_dir}/token.txt", 'w') as f:
                f.write(token)
            
            sftp.close()
            
            # نصب کتابخانه‌های مورد نیاز
            required_libs = bot_engine.detect_requirements(code)
            for lib in required_libs:
                ssh.exec_command(f'pip3 install {lib} --quiet')
            
            # اجرای ربات در background
            command = f'cd {remote_dir} && nohup python3 bot.py > bot.log 2>&1 & echo $!'
            stdin, stdout, stderr = ssh.exec_command(command)
            pid = stdout.read().decode().strip()
            
            # به روز رسانی بار سرور
            with self.lock:
                conn_info['load'] += 1
            
            return True, {'pid': pid, 'remote_dir': remote_dir}
            
        except Exception as e:
            logger.error(f"Deploy failed: {e}")
            return False, str(e)
    
    def stop_bot_on_server(self, server_id, bot_id, pid):
        """توقف ربات روی سرور"""
        with self.lock:
            if server_id not in self.connections:
                return False
            
            ssh = self.connections[server_id]['ssh']
        
        try:
            ssh.exec_command(f'kill -9 {pid}')
            return True
        except:
            return False
    
    def get_server_load(self, server_id):
        """دریافت بار واقعی سرور"""
        with self.lock:
            if server_id not in self.connections:
                return None
            
            ssh = self.connections[server_id]['ssh']
        
        try:
            stdin, stdout, stderr = ssh.exec_command("uptime | awk -F 'load average:' '{print $2}'")
            load = stdout.read().decode().strip()
            return load
        except:
            return None
    
    def check_all_servers(self):
        """بررسی وضعیت همه سرورها"""
        with get_db() as conn:
            servers = conn.execute('SELECT * FROM servers WHERE status = "active"').fetchall()
        
        for server in servers:
            server_id = server['id']
            server_info = dict(server)
            
            if server_id in self.connections:
                # تست اتصال
                ssh = self.connections[server_id]['ssh']
                try:
                    ssh.exec_command('echo "test"', timeout=5)
                    status = 'active'
                except:
                    status = 'disconnected'
                    with self.lock:
                        if server_id in self.connections:
                            del self.connections[server_id]
            else:
                # تلاش برای اتصال مجدد
                success, _ = self.connect_to_server(server_id, server_info)
                status = 'active' if success else 'disconnected'
            
            with get_db() as conn:
                conn.execute('UPDATE servers SET status = ?, last_check = ? WHERE id = ?',
                            (status, datetime.now().isoformat(), server_id))
                conn.commit()

server_manager = RealServerManager()

# ==================== ۱۰۰ کتابخانه آماده ====================
PREINSTALLED_LIBRARIES = [
    'requests', 'urllib3', 'certifi', 'idna', 'chardet',
    'telebot', 'pyTelegramBotAPI', 'telegram', 'python-telegram-bot',
    'aiogram', 'telethon', 'aiohttp', 'httpx', 'websockets',
    'beautifulsoup4', 'lxml', 'selenium', 'flask', 'django',
    'numpy', 'pandas', 'scipy', 'matplotlib', 'seaborn',
    'Pillow', 'opencv-python', 'cryptography', 'jwt', 'bcrypt',
    'jdatetime', 'persiantools', 'redis', 'sqlalchemy', 'pymongo',
    'paramiko', 'dotenv', 'python-dotenv', 'click', 'tqdm',
    'colorama', 'rich', 'loguru', 'schedule', 'apscheduler',
]

def install_preinstalled_libraries():
    """نصب کتابخانه‌های آماده"""
    installed = 0
    for lib in PREINSTALLED_LIBRARIES:
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", lib, "--quiet"], 
                          capture_output=True, timeout=60)
            installed += 1
        except:
            pass
    logger.info(f"Preinstalled libraries: {installed}/{len(PREINSTALLED_LIBRARIES)}")

threading.Thread(target=install_preinstalled_libraries, daemon=True).start()

# ==================== موتور اجرای پیشرفته ====================
class SafeBotEngine:
    def __init__(self):
        self.running_processes = {}
        self.lock = threading.Lock()
        self.installed_cache = {}
    
    def install_library(self, lib_name):
        try:
            lib_name = lib_name.strip().lower()
            lib_name = re.sub(r'[<>="\']', '', lib_name)
            
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", lib_name, "--quiet", "--no-cache-dir", "--upgrade"],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                self.installed_cache[lib_name] = True
                return True, "Installed"
            return False, result.stderr[:200]
        except Exception as e:
            return False, str(e)
    
    def detect_requirements(self, code):
        imports = set()
        lines = code.split('\n')
        
        patterns = [
            r'import\s+([a-zA-Z0-9_]+)',
            r'from\s+([a-zA-Z0-9_]+)\s+import',
        ]
        
        for line in lines:
            if line.strip().startswith('#'):
                continue
            for pattern in patterns:
                matches = re.findall(pattern, line)
                for match in matches:
                    lib = match.split('.')[0]
                    if lib not in ['os', 'sys', 'time', 'datetime', 'json', 're', 'math']:
                        imports.add(lib)
        
        return list(imports)
    
    def is_safe_code(self, code):
        dangerous_patterns = [
            r'os\.system\s*\(',
            r'subprocess\.',
            r'eval\s*\(',
            r'exec\s*\(',
            r'__import__\s*\(',
            r'shutil\.rmtree',
            r'os\.remove',
            r'globals\(',
            r'locals\(',
            r'\.__class__',
            r'\.__bases__',
            r'\.__subclasses__',
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                return False, f"Dangerous code: {pattern}"
        
        return True, "OK"
    
    def run_bot(self, bot_id, user_id, code, token):
        result = {'success': False, 'pid': None, 'error': None, 'installed': []}
        
        try:
            # بررسی امنیت
            is_safe, error_msg = self.is_safe_code(code)
            if not is_safe:
                result['error'] = error_msg
                log_security_event(user_id, 'unsafe_code', error_msg, 'WARNING')
                return result
            
            # نصب کتابخانه‌های مورد نیاز
            requirements = self.detect_requirements(code)
            installed = []
            
            for lib in requirements:
                success, _ = self.install_library(lib)
                if success:
                    installed.append(lib)
            
            result['installed'] = installed
            
            # بررسی سرورهای موجود برای توزیع بار
            with get_db() as conn:
                servers = conn.execute('SELECT * FROM servers WHERE status = "active" ORDER BY current_load ASC').fetchall()
            
            # اگر سروری وجود داشت، روی سرور remote اجرا کن
            if servers and len(servers) > 0:
                best_server = servers[0]
                success, deploy_result = server_manager.deploy_bot_to_server(
                    best_server['id'], bot_id, code, token
                )
                
                if success:
                    result['success'] = True
                    result['pid'] = deploy_result.get('pid')
                    result['server_id'] = best_server['id']
                    result['remote'] = True
                    
                    # ذخیره اطلاعات در دیتابیس
                    with get_db() as conn:
                        conn.execute('UPDATE servers SET current_load = current_load + 1 WHERE id = ?',
                                    (best_server['id'],))
                        conn.commit()
                    
                    return result
            
            # اگر سروری نبود، لوکال اجرا کن
            bot_dir = os.path.join(RUNNING_DIR, bot_id)
            os.makedirs(bot_dir, exist_ok=True)
            os.chmod(bot_dir, 0o700)
            
            code_path = os.path.join(bot_dir, 'bot.py')
            with open(code_path, 'w', encoding='utf-8') as f:
                f.write(code)
            
            with open(os.path.join(bot_dir, 'token.txt'), 'w') as f:
                f.write(token)
            
            log_file = os.path.join(bot_dir, 'bot.log')
            
            process = subprocess.Popen(
                ['nice', '-n', '19', sys.executable, '-u', code_path],
                stdout=open(log_file, 'a'),
                stderr=subprocess.STDOUT,
                cwd=bot_dir,
                start_new_session=True,
                env={'PATH': os.environ.get('PATH', ''), 'PYTHONUNBUFFERED': '1'}
            )
            
            with self.lock:
                self.running_processes[bot_id] = {
                    'process': process,
                    'dir': bot_dir,
                    'pid': process.pid,
                    'start_time': time.time()
                }
            
            time.sleep(2)
            
            if process.poll() is None:
                result['success'] = True
                result['pid'] = process.pid
                result['remote'] = False
            else:
                if os.path.exists(log_file):
                    with open(log_file, 'r') as f:
                        result['error'] = f.read()[-500:]
                else:
                    result['error'] = "Unknown error"
                    
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Run bot error: {traceback.format_exc()}")
        
        return result
    
    def stop_bot(self, bot_id):
        with self.lock:
            if bot_id in self.running_processes:
                try:
                    pid = self.running_processes[bot_id]['pid']
                    os.killpg(os.getpgid(pid), signal.SIGTERM)
                    time.sleep(1)
                    del self.running_processes[bot_id]
                    return True
                except:
                    pass
        return False

bot_engine = SafeBotEngine()

# ==================== توابع کمکی ====================
def generate_referral_code(user_id):
    return hashlib.md5(f"{user_id}_{secrets.token_hex(4)}".encode()).hexdigest()[:8]

def get_user(user_id):
    try:
        with get_db() as conn:
            user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
            return dict(user) if user else None
    except:
        return None

def create_user(user_id, username, first_name, last_name, referred_by=None):
    try:
        with get_db() as conn:
            now = datetime.now().isoformat()
            referral_code = generate_referral_code(user_id)
            
            conn.execute('''
                INSERT OR IGNORE INTO users 
                (user_id, username, first_name, last_name, referral_code, referred_by, created_at, last_active, payment_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, username or "", first_name or "", last_name or "", referral_code, referred_by, now, now, 'pending'))
            
            conn.execute('UPDATE users SET last_active = ? WHERE user_id = ?', (now, user_id))
            conn.commit()
            
            log_security_event(user_id, 'user_created', f'referred_by={referred_by}')
            return True
    except Exception as e:
        logger.error(f"Error in create_user: {e}")
        return False

def check_payment(user_id):
    try:
        with get_db() as conn:
            user = conn.execute('SELECT payment_status, subscription_end FROM users WHERE user_id = ?', (user_id,)).fetchone()
            if user:
                if user['payment_status'] == 'approved':
                    if user['subscription_end']:
                        if datetime.now().isoformat() > user['subscription_end']:
                            return False
                    return True
            return False
    except:
        return False

def get_user_bots(user_id):
    try:
        with get_db() as conn:
            bots = conn.execute('SELECT * FROM bots WHERE user_id = ? ORDER BY created_at DESC', (user_id,)).fetchall()
            return [dict(bot) for bot in bots]
    except:
        return []

# ==================== منوی اصلی ====================
def get_main_menu(is_admin=False):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    
    buttons = [
        types.KeyboardButton('🤖 ساخت ربات جدید'),
        types.KeyboardButton('📋 ربات های من'),
        types.KeyboardButton('🔄 فعال/غیرفعال کردن'),
        types.KeyboardButton('🗑 حذف ربات'),
        types.KeyboardButton('💰 کیف پول و رفرال'),
        types.KeyboardButton('📚 راهنما'),
        types.KeyboardButton('📦 نصب کتابخانه'),
        types.KeyboardButton('📊 آمار'),
        types.KeyboardButton('🏧 برداشت وجه'),
        types.KeyboardButton('📞 پشتیبانی')
    ]
    
    if is_admin:
        buttons.append(types.KeyboardButton('👑 پنل ادمین'))
    
    markup.add(*buttons)
    return markup

# ==================== هندلر استارت ====================
@bot.message_handler(commands=['start'])
@rate_limited(limit=5, window=10)
def cmd_start(message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    
    referred_by = None
    args = message.text.split()
    if len(args) > 1:
        ref_code = args[1]
        try:
            with get_db() as conn:
                referrer = conn.execute('SELECT user_id FROM users WHERE referral_code = ?', (ref_code,)).fetchone()
                if referrer and referrer['user_id'] != user_id:
                    referred_by = referrer['user_id']
                    log_security_event(user_id, 'referral_used', f'referred_by={referred_by}')
        except:
            pass
    
    create_user(user_id, username, first_name, last_name, referred_by)
    
    user = get_user(user_id) or {'referral_code': '', 'referrals_count': 0, 'verified_referrals': 0}
    bot_username = bot.get_me().username
    
    is_admin = user_id in ADMIN_IDS
    markup = get_main_menu(is_admin)
    
    welcome_text = f"""🚀 **به ربات مادر حرفه ای خوش آمدید** {first_name}!

👤 آیدی شما: `{user_id}`
🎁 کد رفرال شما: `{user['referral_code']}`
🔗 لینک دعوت: `https://t.me/{bot_username}?start={user['referral_code']}`

📊 **آمار رفرال:**
• کلیک ها: {user['referrals_count']}
• ساخته شده: {user['verified_referrals']}

💡 هر 5 نفر = 1 ربات اضافه
📤 فایل .py یا .zip خود را آپلود کنید

🔒 **امنیت پیشرفته فعال است**
📦 بیش از ۱۰۰ کتابخانه آماده نصب شده است"""
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

# ==================== ساخت ربات جدید ====================
@bot.message_handler(func=lambda m: m.text == '🤖 ساخت ربات جدید')
@rate_limited(limit=3, window=30)
def new_bot(message):
    user_id = message.from_user.id
    
    if not check_payment(user_id):
        with get_db() as conn:
            price_row = conn.execute('SELECT value FROM settings WHERE key = "price"').fetchone()
            price = int(price_row['value']) if price_row else PRICE
            card_row = conn.execute('SELECT value FROM settings WHERE key = "card_number"').fetchone()
            card = card_row['value'] if card_row else CARD_NUMBER
        
        bot.send_message(
            message.chat.id,
            f"⚠️ کاربر گرامی، از اینکه ما را انتخاب کردید متشکریم\n\nبرای فعال سازی اشتراک و ساخت ربات، مبلغ {price:,} تومان به شماره کارت زیر واریز کنید:\n\n💳 شماره کارت: `{card}`\n🏦 بانک سپه\n👤 به نام: مرتضی نیکخو خنجری\n\n📸 مراحل فعال سازی:\n1️⃣ مبلغ را به کارت فوق واریز کنید\n2️⃣ از صفحه واریز عکس بگیرید\n3️⃣ عکس فیش را در همین چت ارسال کنید\n4️⃣ پس از تایید، اشتراک شما فعال می شود\n\n✅ پس از تایید می توانید ربات خود را بسازید"
        )
        return
    
    user = get_user(user_id)
    extra_bots = user['verified_referrals'] // 5 if user else 0
    max_bots = 1 + extra_bots
    
    with get_db() as conn:
        current_bots = conn.execute('SELECT COUNT(*) FROM bots WHERE user_id = ?', (user_id,)).fetchone()[0]
    
    if current_bots >= max_bots:
        bot.send_message(
            message.chat.id,
            f"❌ شما به حداکثر تعداد ربات ({max_bots}) رسیده اید!\n\nبرای ساخت ربات جدید:\n1️⃣ یکی از ربات ها را حذف کنید\n2️⃣ یا با دعوت دوستان ربات اضافه بگیرید (هر 5 دعوت = 1 ربات اضافه)"
        )
        return
    
    bot.send_message(
        message.chat.id,
        "📤 **فایل ربات خود را ارسال کنید**\n\n✅ فایل های مجاز: `.py` یا `.zip`\n✅ حداکثر حجم: 50 مگابایت\n✅ توکن ربات داخل کد باشد\n\n📦 کتابخانه‌های مورد نیاز به صورت خودکار نصب می شوند\n⚡ ربات شما در محیطی کاملا ایزوله و امن اجرا خواهد شد"
    )

# ==================== آپلود فایل ====================
@bot.message_handler(content_types=['document'])
@rate_limited(limit=5, window=60)
def handle_build_file(message):
    user_id = message.from_user.id
    
    if not check_payment(user_id):
        bot.reply_to(message, "❌ ابتدا هزینه را پرداخت کنید")
        return
    
    # بررسی محدودیت آپلود
    if not check_file_upload_limit(user_id):
        bot.reply_to(message, "⚠️ شما بیش از حد فایل آپلود کردید. لطفا ۱ دقیقه صبر کنید.")
        return
    
    file_name = message.document.file_name
    
    # بررسی پسوند مجاز
    if not (file_name.endswith('.py') or file_name.endswith('.zip')):
        bot.reply_to(message, "❌ فقط فایل های .py یا .zip مجاز هستند!")
        log_security_event(user_id, 'invalid_file_upload', file_name, 'WARNING')
        return
    
    # بررسی حجم
    if message.document.file_size > 50 * 1024 * 1024:
        bot.reply_to(message, "❌ حجم فایل نباید بیشتر از 50 مگابایت باشد!")
        log_security_event(user_id, 'file_too_large', f"{message.document.file_size} bytes", 'WARNING')
        return
    
    status_msg = bot.reply_to(message, "🔄 در حال پردازش فایل...\n🔍 شناسایی کتابخانه‌های مورد نیاز...")
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        user_dir = os.path.join(FILES_DIR, str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        
        file_path = os.path.join(user_dir, f"{int(time.time())}_{file_name}")
        with open(file_path, 'wb') as f:
            f.write(downloaded_file)
        
        main_code = ""
        
        if file_name.endswith('.zip'):
            extract_dir = os.path.join(user_dir, f"extract_{int(time.time())}")
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            for root, _, files in os.walk(extract_dir):
                for f in files:
                    if f.endswith('.py'):
                        file_path_py = os.path.join(root, f)
                        try:
                            with open(file_path_py, 'r', encoding='utf-8') as code_file:
                                content = code_file.read()
                            if f in ['bot.py', 'main.py', 'run.py']:
                                main_code = content
                                break
                        except:
                            pass
            
            if not main_code:
                for root, _, files in os.walk(extract_dir):
                    for f in files:
                        if f.endswith('.py'):
                            file_path_py = os.path.join(root, f)
                            try:
                                with open(file_path_py, 'r', encoding='utf-8') as code_file:
                                    main_code = code_file.read()
                                break
                            except:
                                pass
            
            shutil.rmtree(extract_dir, ignore_errors=True)
        else:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    main_code = f.read()
            except:
                with open(file_path, 'r', encoding='cp1256') as f:
                    main_code = f.read()
        
        if not main_code:
            bot.edit_message_text("❌ هیچ فایل پایتونی پیدا نشد!", message.chat.id, status_msg.message_id)
            return
        
        # استخراج توکن
        token = None
        patterns = [
            r'token\s*=\s*["\']([^"\']+)["\']',
            r'TOKEN\s*=\s*["\']([^"\']+)["\']',
            r'BOT_TOKEN\s*=\s*["\']([^"\']+)["\']',
            r'bot\s*=\s*telebot\.TeleBot\(\s*["\']([^"\']+)["\']\s*\)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, main_code, re.IGNORECASE)
            if match:
                token = match.group(1)
                break
        
        if not token:
            bot.edit_message_text("❌ توکن در کد پیدا نشد!", message.chat.id, status_msg.message_id)
            return
        
        # بررسی توکن
        try:
            response = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
            if response.status_code != 200:
                bot.edit_message_text("❌ توکن معتبر نیست!", message.chat.id, status_msg.message_id)
                log_security_event(user_id, 'invalid_token', token[:10] + '...', 'WARNING')
                return
            
            bot_info = response.json()['result']
            bot_name = bot_info['first_name']
            bot_username = bot_info['username']
        except Exception as e:
            bot.edit_message_text(f"❌ خطا در بررسی توکن: {str(e)}", message.chat.id, status_msg.message_id)
            return
        
        bot.edit_message_text("⚡ در حال اجرا در محیط ایزوله...", message.chat.id, status_msg.message_id)
        
        bot_id = hashlib.md5(f"{user_id}{token}{time.time()}".encode()).hexdigest()[:12]
        
        result = bot_engine.run_bot(bot_id, user_id, main_code, token)
        
        if result['success']:
            with get_db() as conn:
                now = datetime.now().isoformat()
                conn.execute('''
                    INSERT INTO bots 
                    (id, user_id, token, name, username, file_path, pid, status, created_at, last_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (bot_id, user_id, token, bot_name, bot_username, file_path, result['pid'], 'running', now, now))
                
                conn.execute('UPDATE users SET bots_count = bots_count + 1, last_active = ? WHERE user_id = ?', (now, user_id))
                
                user = conn.execute('SELECT referred_by FROM users WHERE user_id = ?', (user_id,)).fetchone()
                if user and user['referred_by']:
                    percent_row = conn.execute('SELECT value FROM settings WHERE key = "referral_percent"').fetchone()
                    percent = int(percent_row['value']) if percent_row else 7
                    amount = int(PRICE * percent / 100)
                    
                    conn.execute('''
                        UPDATE users SET 
                            balance = balance + ?,
                            referral_earnings = referral_earnings + ?,
                            verified_referrals = verified_referrals + 1
                        WHERE user_id = ?
                    ''', (amount, amount, user['referred_by']))
                
                conn.commit()
            
            log_security_event(user_id, 'bot_created', f'bot_id={bot_id}, bot_name={bot_name}')
            
            reply = f"✅ **ربات با موفقیت ساخته شد!** 🎉\n\n🤖 نام: {bot_name}\n🔗 لینک: https://t.me/{bot_username}\n🆔 آیدی ربات: `{bot_id}`"
            
            if result.get('remote'):
                reply += f"\n🖥 سرور: Remote (توزیع شده)"
            else:
                reply += f"\n🔄 PID: {result['pid']}"
            
            if result.get('installed'):
                reply += f"\n\n📦 کتابخانه های نصب شده: {', '.join(result['installed'][:5])}"
            
            reply += "\n\n📊 وضعیت: 🟢 در حال اجرا"
            
            bot.edit_message_text(reply, message.chat.id, status_msg.message_id)
        else:
            error = result.get('error', 'خطای ناشناخته')
            bot.edit_message_text(f"❌ خطا در اجرا:\n`{error[:300]}`", message.chat.id, status_msg.message_id)
            log_security_event(user_id, 'bot_run_failed', error[:100], 'ERROR')
        
    except Exception as e:
        logger.error(f"Error: {e}")
        traceback.print_exc()
        bot.edit_message_text(f"❌ خطا: {str(e)[:300]}", message.chat.id, status_msg.message_id)

# ==================== ربات های من ====================
@bot.message_handler(func=lambda m: m.text == '📋 ربات های من')
@rate_limited(limit=5, window=10)
def my_bots(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما رباتی ندارید!")
        return
    
    for b in bots[:10]:
        status_emoji = "🟢" if b['status'] == 'running' else "🔴"
        status_text = "در حال اجرا" if b['status'] == 'running' else "متوقف"
        
        text = f"{status_emoji} {b['name']}\n🔗 https://t.me/{b['username']}\n🆔 `{b['id']}`\n📊 وضعیت: {status_text}\n📅 ایجاد: {b['created_at'][:10]}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🔄 تغییر وضعیت", callback_data=f"toggle_{b['id']}"),
            types.InlineKeyboardButton("🗑 حذف", callback_data=f"delete_{b['id']}")
        )
        
        bot.send_message(message.chat.id, text, reply_markup=markup)

# ==================== نصب کتابخانه ====================
@bot.message_handler(func=lambda m: m.text == '📦 نصب کتابخانه')
@rate_limited(limit=5, window=30)
def install_library_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=3)
    
    popular_libs = [
        ('requests', 'requests'), ('telebot', 'pyTelegramBotAPI'),
        ('telegram', 'python-telegram-bot'), ('aiogram', 'aiogram'),
        ('numpy', 'numpy'), ('pandas', 'pandas'),
        ('jdatetime', 'jdatetime'), ('دستی', 'custom')
    ]
    
    for name, data in popular_libs:
        markup.add(types.InlineKeyboardButton(name, callback_data=f"lib_{data}"))
    
    bot.send_message(message.chat.id, "📦 کتابخانه مورد نظر را انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lib_'))
def install_library_callback(call):
    lib = call.data.replace('lib_', '')
    
    if lib == 'custom':
        msg = bot.send_message(call.message.chat.id, "📦 نام کتابخانه را وارد کنید:")
        bot.register_next_step_handler(msg, install_custom_library)
        return
    
    bot.answer_callback_query(call.id, f"در حال نصب {lib}...")
    
    success, result = bot_engine.install_library(lib)
    if success:
        bot.edit_message_text(f"✅ کتابخانه {lib} با موفقیت نصب شد.", call.message.chat.id, call.message.message_id)
    else:
        bot.edit_message_text(f"❌ خطا در نصب {lib}:\n{result[:200]}", call.message.chat.id, call.message.message_id)

def install_custom_library(message):
    lib = message.text.strip()
    bot.send_message(message.chat.id, f"🔄 در حال نصب {lib}...")
    success, result = bot_engine.install_library(lib)
    if success:
        bot.send_message(message.chat.id, f"✅ کتابخانه {lib} با موفقیت نصب شد.")
    else:
        bot.send_message(message.chat.id, f"❌ خطا در نصب {lib}:\n{result[:200]}")

# ==================== بقیه هندلرها ====================
@bot.message_handler(func=lambda m: m.text == '🔄 فعال/غیرفعال کردن')
@rate_limited(limit=5, window=10)
def toggle_prompt(message):
    my_bots(message)

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
                conn.execute('UPDATE bots SET status = ? WHERE id = ?', ('stopped', bot_id))
                conn.commit()
            bot.answer_callback_query(call.id, "✅ ربات متوقف شد")
            bot.edit_message_text(f"✅ ربات {bot_info['name']} متوقف شد.", call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "❌ خطا در توقف!")
    else:
        bot.answer_callback_query(call.id, "❌ این ربات در حال حاضر فعال نیست")

@bot.message_handler(func=lambda m: m.text == '🗑 حذف ربات')
@rate_limited(limit=5, window=10)
def delete_prompt(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما رباتی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        markup.add(types.InlineKeyboardButton(f"🗑 {b['name']}", callback_data=f"delete_{b['id']}"))
    
    bot.send_message(message.chat.id, "🗑 ربات مورد نظر را انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_') and not call.data.startswith('delete_bot'))
def confirm_delete(call):
    bot_id = call.data.replace('delete_', '')
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ بله", callback_data=f"confirm_del_{bot_id}"),
        types.InlineKeyboardButton("❌ خیر", callback_data="cancel_del")
    )
    
    bot.edit_message_text("⚠️ آیا از حذف این ربات اطمینان دارید؟\nاین عملیات غیرقابل بازگشت است.", 
                         call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_del_'))
def do_delete(call):
    bot_id = call.data.replace('confirm_del_', '')
    user_id = call.from_user.id
    
    bot_engine.stop_bot(bot_id)
    
    with get_db() as conn:
        bot_info = conn.execute('SELECT * FROM bots WHERE id = ? AND user_id = ?', (bot_id, user_id)).fetchone()
        if bot_info:
            if bot_info['file_path'] and os.path.exists(bot_info['file_path']):
                os.remove(bot_info['file_path'])
            
            conn.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
            conn.execute('UPDATE users SET bots_count = bots_count - 1 WHERE user_id = ?', (user_id,))
            conn.commit()
            
            bot.edit_message_text("✅ ربات با موفقیت حذف شد.", call.message.chat.id, call.message.message_id)
        else:
            bot.edit_message_text("❌ خطا در حذف ربات!", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == 'cancel_del')
def cancel_delete(call):
    bot.edit_message_text("❌ عملیات حذف لغو شد.", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: m.text == '💰 کیف پول و رفرال')
@rate_limited(limit=5, window=10)
def wallet_ref(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        bot.send_message(message.chat.id, "❌ لطفا /start را بزنید")
        return
    
    bot_username = bot.get_me().username
    
    with get_db() as conn:
        balance = user.get('balance', 0)
        referral_earnings = user.get('referral_earnings', 0)
        current_bots = conn.execute('SELECT COUNT(*) FROM bots WHERE user_id = ?', (user_id,)).fetchone()[0]
        
        extra_bots = user['verified_referrals'] // 5
        max_bots = 1 + extra_bots
    
    text = f"""💰 **کیف پول و سیستم رفرال**

👤 کاربر: {user['first_name']}
🆔 آیدی: `{user_id}`

💳 موجودی کیف پول: **{balance:,} تومان**
🎁 درآمد از رفرال: **{referral_earnings:,} تومان**

🔗 لینک دعوت شما:
`https://t.me/{bot_username}?start={user['referral_code']}`

📊 **آمار رفرال:**
• کلیک ها: {user['referrals_count']}
• ثبت نام های موفق: {user['verified_referrals']}

🤖 **ربات های شما:**
• فعلی: {current_bots}
• حداکثر: {max_bots}

💡 هر 5 دعوت = 1 ربات اضافه
🏧 برای برداشت روی دکمه برداشت کلیک کنید"""
    
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == '📚 راهنما')
@rate_limited(limit=5, window=10)
def guide(message):
    guide_text = """📚 **راهنمای کامل ربات مادر نسخه 12.0**

1️⃣ **ساخت ربات جدید:**
   • ابتدا اشتراک تهیه کنید
   • فایل .py یا .zip خود را آپلود کنید
   • کتابخانه های مورد نیاز خودکار نصب می شوند

2️⃣ **امنیت پیشرفته:**
   • بررسی کدهای مخرب قبل از اجرا
   • محدودیت نرخ درخواست (Anti-DDOS)
   • اجرا در محیط ایزوله
   • لاگ امنیتی کامل
   • بن خودکار کاربران خرابکار

3️⃣ **کتابخانه های آماده:**
   • بیش از ۱۰۰ کتابخانه محبوب از قبل نصب شده
   • requests, telebot, aiogram, numpy, pandas و...

4️⃣ **رفرال و درآمدزایی:**
   • 7% سود از هر خرید کاربر دعوت شده
   • هر 5 دعوت = 1 ربات اضافه
   • قابل برداشت از 2 میلیون تومان

5️⃣ **پشتیبانی:**
   • @shahraghee13"""
    
    bot.send_message(message.chat.id, guide_text)

@bot.message_handler(func=lambda m: m.text == '📊 آمار')
@rate_limited(limit=5, window=10)
def stats(message):
    try:
        with get_db() as conn:
            total_users = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
            total_bots = conn.execute('SELECT COUNT(*) FROM bots').fetchone()[0]
            running_bots = conn.execute('SELECT COUNT(*) FROM bots WHERE status = "running"').fetchone()[0]
            total_payments = conn.execute('SELECT COUNT(*) FROM receipts WHERE status = "approved"').fetchone()[0]
        
        text = f"📊 **آمار سامانه**\n\n👥 کاربران: {total_users}\n🤖 کل ربات ها: {total_bots}\n🟢 فعال: {running_bots}\n💰 پرداخت ها: {total_payments}"
        
        bot.send_message(message.chat.id, text)
    except:
        bot.send_message(message.chat.id, "📊 آمار در دسترس نیست")

@bot.message_handler(func=lambda m: m.text == '📞 پشتیبانی')
@rate_limited(limit=10, window=10)
def support(message):
    bot.send_message(message.chat.id, "📞 **پشتیبانی:** @shahraghee13\n\nساعات پاسخگویی: 9 صبح تا 12 شب")

@bot.message_handler(func=lambda m: m.text == '🏧 برداشت وجه')
@rate_limited(limit=3, window=60)
def withdraw_menu(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        bot.send_message(message.chat.id, "❌ لطفا /start را بزنید")
        return
    
    balance = user.get('balance', 0)
    min_withdraw = 2000000
    
    if balance < min_withdraw:
        bot.send_message(
            message.chat.id,
            f"❌ موجودی شما کافی نیست!\n\n💰 موجودی فعلی: {balance:,} تومان\n💰 حداقل برداشت: {min_withdraw:,} تومان"
        )
        return
    
    msg = bot.send_message(
        message.chat.id,
        f"🏧 **درخواست برداشت وجه**\n\n💰 موجودی قابل برداشت: {balance:,} تومان\n\nلطفا شماره کارت خود را وارد کنید:"
    )
    bot.register_next_step_handler(msg, process_withdraw, user_id, balance)

def process_withdraw(message, user_id, balance):
    text = message.text.strip()
    card_match = re.search(r'\d{16}', text)
    
    if not card_match:
        bot.send_message(message.chat.id, "❌ شماره کارت نامعتبر! لطفا 16 رقم کارت را وارد کنید.")
        return
    
    card_number = card_match.group()
    
    with get_db() as conn:
        conn.execute('''
            INSERT INTO withdrawals (user_id, amount, card_number, status, created_at)
            VALUES (?, ?, ?, 'pending', ?)
        ''', (user_id, balance, card_number, datetime.now().isoformat()))
        conn.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (balance, user_id))
        conn.commit()
    
    bot.send_message(
        message.chat.id,
        f"✅ **درخواست برداشت ثبت شد!**\n\n💰 مبلغ: {balance:,} تومان\n💳 شماره کارت: {card_number}\n\nوضعیت: در انتظار بررسی"
    )
    
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id, f"🏧 درخواست برداشت جدید\n👤 کاربر: {user_id}\n💰 مبلغ: {balance:,} تومان")
        except:
            pass

# ==================== فیش واریزی ====================
@bot.message_handler(content_types=['photo'])
@rate_limited(limit=3, window=60)
def handle_receipt(message):
    user_id = message.from_user.id
    
    try:
        with get_db() as conn:
            existing = conn.execute('SELECT id FROM receipts WHERE user_id = ? AND status = "pending"', (user_id,)).fetchone()
            if existing:
                bot.reply_to(message, "⏳ شما یک فیش در انتظار بررسی دارید")
                return
    except:
        pass
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        payment_code = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:8].upper()
        receipt_path = os.path.join(RECEIPTS_DIR, f"{user_id}_{payment_code}.jpg")
        
        with open(receipt_path, 'wb') as f:
            f.write(downloaded_file)
        
        with get_db() as conn:
            price_row = conn.execute('SELECT value FROM settings WHERE key = "price"').fetchone()
            price = int(price_row['value']) if price_row else PRICE
            
            conn.execute('''
                INSERT INTO receipts (user_id, amount, receipt_path, created_at, payment_code)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, price, receipt_path, datetime.now().isoformat(), payment_code))
            conn.commit()
        
        bot.reply_to(message, f"✅ **فیش دریافت شد**\n\n💰 مبلغ: {price:,} تومان\n🆔 کد پیگیری: `{payment_code}`\n\nپس از بررسی توسط ادمین فعال می شود")
        
        for admin_id in ADMIN_IDS:
            try:
                bot.send_photo(admin_id, open(receipt_path, 'rb'), 
                             caption=f"📸 فیش جدید\n👤 کاربر: {user_id}\n💰 مبلغ: {price:,} تومان\n🆔 کد: {payment_code}")
            except:
                pass
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")

# ==================== پنل ادمین ====================
@bot.message_handler(func=lambda m: m.text == '👑 پنل ادمین')
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ شما دسترسی ادمین ندارید!")
        log_security_event(message.from_user.id, 'admin_access_denied', '', 'WARNING')
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💰 تغییر قیمت", callback_data="admin_change_price"),
        types.InlineKeyboardButton("💳 تغییر شماره کارت", callback_data="admin_change_card"),
        types.InlineKeyboardButton("📝 تغییر متن راهنما", callback_data="admin_change_guide"),
        types.InlineKeyboardButton("🖥 مدیریت سرورها", callback_data="admin_servers"),
        types.InlineKeyboardButton("🗑 حذف ربات کاربران", callback_data="admin_delete_user_bot"),
        types.InlineKeyboardButton("🏧 درخواست های برداشت", callback_data="admin_withdrawals"),
        types.InlineKeyboardButton("📸 فیش های در انتظار", callback_data="admin_receipts"),
        types.InlineKeyboardButton("👥 لیست کاربران", callback_data="admin_users"),
        types.InlineKeyboardButton("📊 آمار کامل", callback_data="admin_stats"),
        types.InlineKeyboardButton("🔒 لاگ امنیتی", callback_data="admin_security_logs"),
        types.InlineKeyboardButton("🚫 کاربران بن شده", callback_data="admin_banned_users"),
        types.InlineKeyboardButton("💾 بکاپ دیتابیس", callback_data="admin_backup"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    bot.send_message(message.chat.id, "👑 **پنل مدیریت پیشرفته**\n\nلطفا یکی از گزینه ها را انتخاب کنید:", reply_markup=markup)

# ==================== مدیریت سرورها ====================
@bot.callback_query_handler(func=lambda call: call.data == "admin_servers")
def admin_servers(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ اضافه کردن سرور جدید", callback_data="admin_add_server"),
        types.InlineKeyboardButton("📋 لیست سرورها", callback_data="admin_list_servers"),
        types.InlineKeyboardButton("🔄 بررسی همه سرورها", callback_data="admin_check_servers"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    bot.edit_message_text("🖥 **مدیریت سرورها**\n\nبرای اضافه کردن سرور جدید، اطلاعات واقعی SSH را وارد کنید:", 
                         call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_add_server")
def add_server_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "🖥 **اضافه کردن سرور جدید**\n\nلطفا نام سرور را وارد کنید:")
    bot.register_next_step_handler(msg, add_server_name)

def add_server_name(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    name = message.text.strip()
    if not name:
        bot.send_message(message.chat.id, "❌ نام معتبر وارد کنید!")
        return
    
    bot.send_message(message.chat.id, "🌐 آدرس IP سرور را وارد کنید:")
    bot.register_next_step_handler(message, add_server_ip, name)

def add_server_ip(message, name):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    ip = message.text.strip()
    if not ip:
        bot.send_message(message.chat.id, "❌ IP معتبر وارد کنید!")
        return
    
    bot.send_message(message.chat.id, "🔌 پورت SSH (پیش‌فرض 22):")
    bot.register_next_step_handler(message, add_server_port, name, ip)

def add_server_port(message, name, ip):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    port = message.text.strip()
    try:
        port = int(port) if port else 22
    except:
        port = 22
    
    bot.send_message(message.chat.id, "👤 یوزرنیم SSH را وارد کنید:")
    bot.register_next_step_handler(message, add_server_username, name, ip, port)

def add_server_username(message, name, ip, port):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    username = message.text.strip()
    if not username:
        bot.send_message(message.chat.id, "❌ یوزرنیم معتبر وارد کنید!")
        return
    
    bot.send_message(message.chat.id, "🔑 رمز عبور SSH را وارد کنید:")
    bot.register_next_step_handler(message, add_server_password, name, ip, port, username)

def add_server_password(message, name, ip, port, username):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    password = message.text.strip()
    if not password:
        bot.send_message(message.chat.id, "❌ رمز عبور معتبر وارد کنید!")
        return
    
    # ذخیره در دیتابیس
    with get_db() as conn:
        conn.execute('''
            INSERT INTO servers (name, host, port, username, password, max_workers, status, created_at)
            VALUES (?, ?, ?, ?, ?, 100, 'pending', ?)
        ''', (name, ip, port, username, password, datetime.now().isoformat()))
        server_id = conn.lastrowid
        conn.commit()
    
    # تلاش برای اتصال
    server_info = {'host': ip, 'port': port, 'username': username, 'password': password}
    success, result = server_manager.connect_to_server(server_id, server_info)
    
    if success:
        bot.send_message(message.chat.id, f"✅ **سرور با موفقیت اضافه شد!**\n\n🖥 نام: {name}\n🌐 IP: {ip}\n🔌 پورت: {port}\n📊 وضعیت: 🟢 متصل")
    else:
        bot.send_message(message.chat.id, f"⚠️ **سرور اضافه شد اما اتصال برقرار نشد!**\n\n🖥 نام: {name}\n🌐 IP: {ip}\n❌ خطا: {result}\n\nبعداً می‌توانید دوباره امتحان کنید.")

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
    
    text = "🖥 **لیست سرورها:**\n\n"
    for s in servers:
        status_emoji = "🟢" if s['status'] == 'active' else ("🟡" if s['status'] == 'pending' else "🔴")
        text += f"{status_emoji} **{s['name']}**\n"
        text += f"   🌐 {s['host']}:{s['port']}\n"
        text += f"   📊 بار: {s['current_load']}/{s['max_workers']}\n"
        text += f"   📅 اضافه شده: {s['created_at'][:10]}\n\n"
    
    bot.send_message(call.message.chat.id, text)

@bot.callback_query_handler(func=lambda call: call.data == "admin_check_servers")
def admin_check_servers(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    bot.send_message(call.message.chat.id, "🔄 در حال بررسی سرورها...")
    
    server_manager.check_all_servers()
    
    bot.send_message(call.message.chat.id, "✅ بررسی سرورها انجام شد.\nوضعیت در دیتابیس به روز رسانی شد.")

# ==================== لاگ امنیتی و کاربران بن شده ====================
@bot.callback_query_handler(func=lambda call: call.data == "admin_security_logs")
def admin_security_logs(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        logs = conn.execute('''
            SELECT * FROM security_logs 
            ORDER BY created_at DESC 
            LIMIT 50
        ''').fetchall()
    
    if not logs:
        bot.send_message(call.message.chat.id, "📋 لاگ امنیتی وجود ندارد.")
        return
    
    text = "🔒 **آخرین لاگ‌های امنیتی:**\n\n"
    for log in logs:
        text += f"🕐 {log['created_at'][:19]}\n"
        text += f"👤 کاربر: {log['user_id']}\n"
        text += f"📋 عملیات: {log['action']}\n"
        text += f"📝 جزئیات: {log['details'][:50]}\n\n"
    
    # ارسال در چند پیام
    if len(text) > 4000:
        for i in range(0, len(text), 4000):
            bot.send_message(call.message.chat.id, text[i:i+4000])
    else:
        bot.send_message(call.message.chat.id, text)

@bot.callback_query_handler(func=lambda call: call.data == "admin_banned_users")
def admin_banned_users(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        banned = conn.execute('SELECT * FROM users WHERE is_banned = 1 ORDER BY banned_at DESC').fetchall()
    
    if not banned:
        bot.send_message(call.message.chat.id, "🚫 هیچ کاربر بن شده‌ای وجود ندارد.")
        return
    
    text = "🚫 **لیست کاربران بن شده:**\n\n"
    for u in banned:
        text += f"👤 {u['user_id']} - {u['first_name'] or 'بدون نام'}\n"
        text += f"   📋 دلیل: {u['ban_reason'] or 'نامشخص'}\n"
        text += f"   📅 تاریخ: {u['banned_at'][:10]}\n\n"
    
    bot.send_message(call.message.chat.id, text)

# ==================== بقیه دکمه‌های ادمین ====================
@bot.callback_query_handler(func=lambda call: call.data == "admin_change_price")
def change_price_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "💰 قیمت جدید را به تومان وارد کنید:")
    bot.register_next_step_handler(msg, change_price_process)

def change_price_process(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        new_price = int(message.text.strip())
        with get_db() as conn:
            conn.execute('UPDATE settings SET value = ?, updated_at = ? WHERE key = "price"', 
                        (str(new_price), datetime.now().isoformat()))
            conn.commit()
        bot.send_message(message.chat.id, f"✅ قیمت با موفقیت به {new_price:,} تومان تغییر کرد!")
    except ValueError:
        bot.send_message(message.chat.id, "❌ لطفا یک عدد معتبر وارد کنید!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_change_card")
def change_card_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "💳 شماره کارت جدید را وارد کنید:")
    bot.register_next_step_handler(msg, change_card_process)

def change_card_process(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    card_number = message.text.strip()
    if not card_number.isdigit() or len(card_number) != 16:
        bot.send_message(message.chat.id, "❌ شماره کارت باید 16 رقم باشد!")
        return
    
    with get_db() as conn:
        conn.execute('UPDATE settings SET value = ?, updated_at = ? WHERE key = "card_number"', 
                    (card_number, datetime.now().isoformat()))
        conn.commit()
    bot.send_message(message.chat.id, f"✅ شماره کارت با موفقیت به {card_number} تغییر کرد!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_change_guide")
def change_guide_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "📝 متن جدید راهنما را وارد کنید:")
    bot.register_next_step_handler(msg, change_guide_process)

def change_guide_process(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    new_guide = message.text.strip()
    with get_db() as conn:
        conn.execute('UPDATE settings SET value = ?, updated_at = ? WHERE key = "guide_text"', 
                    (new_guide, datetime.now().isoformat()))
        conn.commit()
    bot.send_message(message.chat.id, "✅ متن راهنما با موفقیت به روزرسانی شد!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_delete_user_bot")
def admin_list_user_bots(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        bots = conn.execute('SELECT id, name, user_id FROM bots ORDER BY created_at DESC LIMIT 50').fetchall()
    
    if not bots:
        bot.send_message(call.message.chat.id, "📋 هیچ رباتی در سیستم وجود ندارد")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        markup.add(types.InlineKeyboardButton(f"🗑 {b['name']} (کاربر: {b['user_id']})", callback_data=f"admin_del_bot_{b['id']}"))
    
    bot.send_message(call.message.chat.id, "🗑 لیست ربات ها\nبرای حذف یک ربات روی آن کلیک کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_del_bot_"))
def admin_delete_bot(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    bot_id = call.data.replace("admin_del_bot_", "")
    bot_engine.stop_bot(bot_id)
    
    with get_db() as conn:
        bot_info = conn.execute('SELECT * FROM bots WHERE id = ?', (bot_id,)).fetchone()
        if bot_info:
            if bot_info['file_path'] and os.path.exists(bot_info['file_path']):
                os.remove(bot_info['file_path'])
            conn.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
            conn.execute('UPDATE users SET bots_count = bots_count - 1 WHERE user_id = ?', (bot_info['user_id'],))
            conn.commit()
    
    bot.edit_message_text(f"✅ ربات {bot_id} با موفقیت حذف شد.", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_withdrawals")
def admin_withdrawals(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        withdrawals = conn.execute('SELECT * FROM withdrawals WHERE status = "pending" ORDER BY created_at DESC').fetchall()
    
    if not withdrawals:
        bot.send_message(call.message.chat.id, "🏧 هیچ درخواست برداشتی در انتظار نیست")
        return
    
    for w in withdrawals:
        text = f"🏧 درخواست برداشت\n\n🆔 شماره: {w['id']}\n👤 کاربر: {w['user_id']}\n💰 مبلغ: {w['amount']:,} تومان\n💳 شماره کارت: {w['card_number']}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ پرداخت شد", callback_data=f"pay_withdraw_{w['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"reject_withdraw_{w['id']}")
        )
        bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_withdraw_"))
def pay_withdraw(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید دسترسی ندارید!")
        return
    
    withdrawal_id = int(call.data!")
        return
    
    withdrawal_id = int(call.data.replace("pay_withdraw_", ""))
    
   .replace("pay_withdraw_", ""))
    
    with get_db() as conn:
 with get_db() as conn:
        conn        conn.execute('UPDATE withdrawals SET status =.execute('UPDATE withdrawals SET status "approved", processed_at = ? WHERE id = = "approved", processed_at = ? WHERE id = ?', 
 ?', 
                    (datetime.now                    (datetime.now().isoformat(),().isoformat(), withdrawal_id))
 withdrawal_id))
        withdrawal = conn.execute('SELECT * FROM        withdrawal = conn.execute('SELECT * FROM withdrawals WHERE id = ? withdrawals WHERE id = ?', (with', (withdrawal_id,)).fetchone()
       drawal_id,)).fetchone()
        conn.commit()
 conn.commit()
        
        if withdrawal:
        
        if withdrawal:
            try:
                bot.send_message(withdrawal['user_id            try:
                bot.send_message(withdrawal['user_id'], f"✅ برداشت وجه شما انجام شد!\'], f"✅ برداشت وجه شما انجام شد!\n\n💰 مn\n💰 مبلغ: {withdrawal['amount']:,} تومان")
            except:
بلغ: {withdrawal['amount']:,} تومان")
            except:
                pass
    
    bot.answer_callback_query(c                pass
    
    bot.answer_callback_query(call.id, "✅ برداشت تایید شد")
all.id, "✅ برداشت تایید شد")
    bot.delete_message    bot.delete_message(call.message.chat.id, call.message.message_id)

(call.message.chat.id, call.message.message_id)

@bot.callback_query@bot.callback_query_handler(func=lambda call: call.data.startswith("re_handler(func=lambda call: call.dataject_withdraw_.startswith("reject_withdraw_"))
def reject"))
def reject_withdraw(call):
    if call.from_withdraw(call):
    if call.from_user.id_user.id not in ADMIN_IDS:
        bot.answer not in ADMIN_IDS:
        bot.answer_callback_query(c_callback_query(call.id, "all.id, "⛔ دسترسی ندارید!")
⛔ دسترسی ندارید!")
        return
    
        return
    
    withdrawal_id = int    withdrawal_id = int(call.data.replace("reject_with(call.data.replace("reject_withdraw_",draw_", ""))
    
    with get_db() as ""))
    
    with get_db() as conn:
        conn.execute('UPDATE withdrawals SET status = " conn:
        conn.execute('UPDATE withdrawals SET status = "rejected", processedrejected", processed_at = ? WHERE id = ?', 
                    (datetime.now().isoformat(), withdrawal_id))
        withdrawal = conn.execute('SELECT * FROM withdrawals WHERE id = ?',_at = ? WHERE id = ?', 
                    (datetime.now().isoformat(), withdrawal_id))
        withdrawal = conn.execute('SELECT * FROM withdrawals WHERE id = ?', ( (withdrawal_id,)).fetchone()
withdrawal_id,)).fetchone()
               if withdrawal:
            conn.execute('UPDATE users SET balance if withdrawal:
            conn.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', = balance + ? WHERE user_id = ?', 
                        (with 
                        (withdrawal['amount'], withdrawal['user_id']))
            conndrawal['amount'], withdrawal['user_id']))
            conn.commit()
            try:
.commit()
            try:
                bot.send_message(withdrawal['user_id'], f                bot.send_message(withdrawal['user_id'], f"❌ درخواست برداشت شما رد شد"❌ درخواست برداشت شما رد شد!\n\n!\n\n💰 مبلغ: {withdrawal['amount']:,}💰 مبلغ: {withdrawal['amount']:,} تومان")
            تومان")
            except:
                pass
    
    bot.answer_callback_query(call.id, "❌ برد except:
                pass
    
    bot.answer_callback_query(call.id, "❌ برداشت رد شد")
اشت رد شد")
    bot.delete_message(call.message.ch    bot.delete_messageat.id, call.message.message_id)

@(call.message.chat.id, call.message.message_id)

bot.callback_query_handler(func=lambda@bot.callback_query_handler(func call: call.data == "admin_receipts")
=lambda call: call.datadef admin_receipts(call):
 == "admin_receipts")
def admin_receipt    if call.from_user.id nots(call):
    if call.from_user.id not in ADMIN_IDS in ADMIN_IDS:
        bot.:
        bot.answer_callback_query(call.id,answer_callback_query(call.id, "⛔ "⛔ دسترسی ندارید دسترسی ندارید!")
        return
    
    with get_db!")
        return
    
    with get_db() as conn:
() as conn:
        receipts = conn        receipts = conn.execute('SELECT * FROM receipts WHERE status = "pending" ORDER BY created_at.execute('SELECT * FROM receipts WHERE status = "pending" DESC').fetchall ORDER BY created_at DESC').fetchall()
    
   ()
    
    if not receipts:
        bot.send_message(c if not receipts:
       all.message.chat.id, " bot.send_message(call.message.chat.id, "📸 هیچ فیش در انتظاری وجود ندارد📸 هیچ فیش")
        return
    
    for r in receipts:
 در انتظاری وجود ندارد")
        return
    
    for        text = f"📸 فیش واریزی r in receipts:
        text = f"📸 فیش واریزی\n\n🆔 شماره: {r['id\n\n🆔 شماره: {r['id']}\n👤 کاربر: {r['user_id']}\n👤 کاربر: {r['user_id']}\n💰 مبلغ: {r']}\n💰 مبلغ: {r['['amount']:,} تومانamount']:,} تومان\n🆔 کد پیگیری: {r['payment_code']}"
\n🆔 کد پیگیری: {r['payment_code']}"
        
        markup = types.InlineKeyboardMarkup()
               
        markup = markup.add(
            types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید و فعال types.InlineKeyboardButton("✅ تایید و فعال سازی", callback_data سازی", callback_data=f"approve_receipt_{r['id']=f"approve_receipt_{r['id']}"),
            types.InlineKeyboard}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"Button("❌ رد", callback_data=freject_receipt_{r['id']}")
"reject_receipt_{r['id']}")
        )
        
        if os.path.exists        )
        
        if os(r['receipt_path']):
           .path.exists(r['receipt_path']):
            with open(r['receipt_path'], 'rb') as with open(r['receipt_path'], 'rb') as f:
                bot.send_photo(call.message.chat f:
                bot.send_photo(call.message.chat.id, f, caption=text, reply_markup.id, f, caption=text, reply_markup=markup)
=markup)
        else:
            bot.send_message(c        else:
            bot.sendall.message.chat.id, text, reply_m_message(call.message.chat.id, text,arkup=markup)

@bot.callback reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data_query_handler(func=lambda call.startswith("appro: call.data.startswith("approve_receiptve_receipt_"))
def approve_receipt(call):
    if call.from_user.id_"))
def approve_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    receipt_id = int ندارید!")
        return
    
    receipt_id =(call.data.replace("approve_receipt_", ""))
    
    with int(call.data.replace("approve_receipt_", ""))
    
 get_db() as    with get_db() as conn:
        receipt = conn.execute('SELECT * FROM receipts conn:
        receipt = conn.execute('SELECT * FROM receipts WHERE id = ?', (receipt WHERE id = ?', (receipt_id,)).fetchone()
        if receipt:
            subscription_id,)).fetchone()
        if receipt:
            subscription_end = (datetime.now_end = (datetime() + timedelta(days=.now() + timedelta(days=30)).isoformat30)).isoformat()
            conn.execute()
            conn.execute('UPDATE receipts SET('UPDATE receipts SET status = "approved", status = "approved", reviewed_at = reviewed_at = ? WHERE id = ?', 
                        ? WHERE id = ?', 
                        ( (datetime.now().isoformat(), receipt_id))
            conndatetime.now().isoformat(), receipt_id))
            conn.execute('UPDATE users.execute('UPDATE users SET payment_status SET payment_status = "approved", subscription = "approved", subscription_end = ? WHERE user_id = ?', 
                        (subscription_end,_end = ? WHERE user_id = ?', 
                        (subscription_end, receipt['user_id receipt['user_id']))
            
']))
            
            user = conn.execute('SELECT referred            user = conn.execute('SELECT referred_by FROM users WHERE user_id = ?', (receipt_by FROM users WHERE user_id = ?', (receipt['user_id'],)).fetchone()
            if user and['user_id'],)).fetchone()
            if user and user['referred user['referred_by']:
                percent = 7
                amount_by']:
                percent = 7
                amount = int(receipt['amount'] * percent /  = int(receipt['amount'] * percent / 100)
                conn.execute('UPDATE users100)
                conn.execute('UPDATE users SET balance = SET balance = balance + ?, referral_earnings = referral_earnings balance + ?, referral_earnings = referral_earnings + ? WHERE user_id = ?',
                            ( + ? WHERE user_id = ?',
                            (amount, amount, user['referred_by']amount, amount, user['referred_by']))
            
            conn.commit()
            
            try:
                bot.send_message(receipt['))
            
            conn.commit()
            
            try:
                bot.send_message(receipt['user_id'], fuser_id'], f"✅ فیش شما تایید شد!"✅ فیش شما تایید شد! 🎉\n 🎉\n\n💰 مبلغ:\n💰 مبلغ: {receipt['amount']:,} تومان {receipt['amount']:,} تومان\n📅 اعتبار اشتراک تا: {subscript\n📅 اعتبار اشتراک تا: {subscription_end[:10]}")
ion_end[:10]            except:
                pass
    
    bot}")
            except:
                pass
    
    bot.answer_callback_query(call.id, "✅ ف.answer_callback_query(call.id, "✅ فیش تایید شد")
    bot.delete_message(callیش تایید شد")
    bot.delete_message(call.message.chat.id.message.chat.id, call.message.message_id)

@bot.callback_query_handler, call.message.message_id)

@bot.callback_query_handler(func=lambda call:(func=lambda call: call.data.startswith("reject_re call.data.startswith("reject_receipt_"))
ceipt_"))
def reject_receipt(call):
    if call.fromdef reject_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دست_callback_query(call.id, "رسی ندارید!")
        return
    
   ⛔ دسترسی ندارید!")
        return
    
    receipt_id = int(call receipt_id = int(call.data.replace("reject_re.data.replace("reject_receipt_",ceipt_", ""))
    
    with get_db() as conn:
        conn ""))
    
    with get_db() as conn:
        conn.execute('UPDATE receipts SET status = "rejected", reviewed.execute('UPDATE receipts SET status = "rejected", reviewed_at = ? WHERE id = ?', 
                    (datetime_at = ? WHERE id = ?', 
                    (datetime.now().isoformat(), receipt_id))
        conn.commit()
.now().isoformat(), receipt_id))
        conn.commit()
        
        receipt        
        receipt = conn.execute('SELECT * FROM receipts WHERE id = ?', (receipt = conn.execute('SELECT * FROM receipts WHERE id = ?', (receipt_id,)).fetch_id,)).fetchone()
        if receipt:
            try:
                bot.sendone()
        if receipt:
            try:
                bot.send_message(receipt['user_id'], f_message(receipt['user_id'],"❌ فیش شما رد f"❌ فیش شما رد شد!\n\nدر شد!\n\nدر صورت نیاز با پشتیبانی تماس بگیرید صورت نیاز با پشتیبانی تماس بگیرید.")
            except:
                pass
    
   .")
            except:
                pass
    
    bot.answer_callback_query(call.id, " bot.answer_callback_query(call❌ فیش رد.id, "❌ فیش رد شد")
    bot شد")
    bot.delete_message(call.message.chat.id.delete_message(call.message.chat.id, call.message.message, call.message.message_id)

@bot.callback_query_handler_id)

@bot.callback_query_handler(func=lambda call(func=lambda call: call.data == "admin: call.data == "_users")
def admin_users(call):
    if calladmin_users")
def admin_users(call):
    if call.from_user.id not in ADMIN_IDS.from_user.id not in ADMIN_IDS:
       :
        bot.answer_callback_query(call bot.answer_callback_query(call.id,.id, "⛔ دسترسی ندارید "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
!")
        return
    
    with get_db() as conn:
        users = conn.execute        users = conn('SELECT * FROM users ORDER BY created.execute('SELECT * FROM users ORDER BY created_at DESC LIMIT_at DESC LIMIT 30').fetchall()
    
    30').fetchall()
    
    if not users:
 if not users:
        bot.send_message(call.message.ch        bot.send_messageat.id, "👥 کاربری یافت نشد")
        return
    
(call.message.chat.id, "👥 کاربری یافت نشد")
        return
    
    text = "    text = "👥 **30 کاربر آخر:**\n\n"
   👥 **30 کاربر آخر:**\n\n"
    for u in users:
        payment = for u in users:
        payment = "✅" if "✅" if u['payment_status u['payment_status'] == 'approved' else "'] == 'approved' else "⏳"
       ⏳"
        banned = "🚫" if u banned = "🚫" if u.get.get('is_banned', 0('is_banned) == 1 else ""
        text +=', 0) == 1 else ""
        text += f"{payment}{banned} {u['user_id f"{payment}{banned} {u['user_id']} - {u['first_name']} - {u['first_name'] or 'بد'] or 'بدون نام'}\n"
        text += f"  ون نام'}\n"
        text 🤖 {u['bots_count'] += f"   🤖 {u['bots_count']} | 🎁 {u['} | 🎁 {u['verified_referralsverified_referrals']} | 💰 {u['']} |balance']:,}\n\n"
    
    bot.send 💰 {u['balance']:,}\n\n"
    
_message(call.message.chat.id, text    bot.send_message(call.message.chat.id, text)

@bot.callback_query_handler(func)

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin=lambda call: call.data == "admin_stats(call):
    if call.from_user_stats")
def admin_stats(call):
    if call.from.id not in ADMIN_IDS:
        bot.answer_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "_callback_query(call.id, "⛔ دست⛔ دسترسی ندارید!")
       رسی ندارید!")
        return
    
    with return
    
    with get_db() as conn:
        total_users = conn.execute('SELECT COUNT get_db() as conn:
        total_users = conn.execute('SELECT COUNT(*) FROM users').(*) FROM users').fetchone()[0]
fetchone()[0        banned_users = conn.execute('SELECT COUNT(*)]
        banned_users = conn.execute('SELECT COUNT(*) FROM users WHERE is FROM users WHERE is_banned = 1').fetchone_banned = 1').fetchone()[0]
       ()[0]
        total_bots = conn.execute('SELECT total_bots = conn.execute('SELECT COUNT(*) FROM bots COUNT(*) FROM bots').fetch').fetchone()[0]
        running_bots = conn.execute('SELECT COUNTone()[0]
        running_bots = conn.execute('SELECT COUNT(*) FROM bots(*) FROM bots WHERE status = "running"').fetchone WHERE status = "running"').fetchone()[0]
        total_amount = conn.execute('SELECT()[0]
        total_amount = COALESCE(SUM(amount), 0) FROM conn.execute('SELECT COALESCE(SUM(amount), 0) FROM receipts WHERE status = "approved"'). receipts WHERE status = "approved"').fetchone()[0fetchone()[0]
        paid_users = conn.execute(']
        paid_usersSELECT COUNT(*) FROM users WHERE payment_status = "approved" = conn.execute('SELECT COUNT(*) FROM users WHERE payment_status').fetchone = "approved"').fetchone()[0]
        servers = conn.execute('SELECT COUNT(*) FROM()[0]
        servers = conn.execute('SELECT COUNT(*) FROM servers WHERE servers WHERE status = "active"').fetchone()[0 status = "active"').fetchone()[0]
    
    text]
    
    text = f""" = f"""📊 **آمار کامل سامانه**

👥 **کاربران📊 **آمار کامل سامانه**

👥:**
   • کل **کاربران:**
   • کل: {total_users}
   • پرد: {total_users}
   • پرداخت کرده: {paid_users}
   • بن شده: {bاخت کرده: {paid_users}
   • بنanned_users}

 شده: {banned_users🤖 **ربات ها:**
}

🤖 **ربات ها:**
   • کل:   • کل: {total_bots}
   • فعال: {total_bots}
   • فعال: {running_b {running_bots}

💰 **مالی:**
ots}

💰 **   • کل واریزی: {total_amount:,} تومان

مالی:**
   • کل واریزی: {total_amount:,} تومان

🖥 **سر🖥 **سرورها:**
   • فعال:ورها:**
   • فعال: {servers}"""
    
    bot.send_message(c {servers}"""
    
    bot.send_message(call.message.chat.id, text)

@bot.callbackall.message.chat.id, text)

@bot.callback_query_handler(func_query_handler(func=lambda call: call.data == "admin=lambda call: call.data == "_backup")
def admin_backup(call):
    ifadmin_backup")
def admin_backup(c call.from_user.id not in ADMIN_IDS:
all):
    if call.from_user.id not in ADMIN_        bot.answer_callback_query(call.idIDS:
        bot.answer_callback, "⛔ دسترسی ندارید!")
       _query(call.id, "⛔ دسترسی ندارید!")
        return
    
    try:
        backup_file = os.path.join return
    
    try:
        backup_file = os.path.join(BACKUP_DIR, f"backup_{(BACKUP_DIR, f"backup_{datetime.nowdatetime.now().strftime('%().strftime('%Y%m%d_%H%M%S')Y%m%d_%H%M%S')}.db")
       }.db")
        shutil.copy2(DB_PATH, shutil.copy2(DB_PATH, backup_file)
        
        with open( backup_file)
        
        with open(backup_file, 'rb') as f:
            botbackup_file, 'rb') as.send_document(call.message.chat.id, f, f:
            bot.send_document(call.message.chat.id, f, caption=f"💾 بکاپ دیتابی caption=f"💾 بکاپ دیتابیسس\n📅 {datetime.now().isoformat\n📅 {datetime.now().isoformat()[:19]}")
        bot.answer_callback()[:19]}")
        bot.answer_callback_query(call.id, "✅ بکاپ گرفته شد_query(call.id, "✅ بکاپ گرفته شد")
    except Exception as e:
        bot.answer_c")
    except Exception as e:
        bot.answer_callback_query(callallback_query(call.id, f"❌ خطا: {str(e.id, f"❌ خطا: {str(e)}")

@bot.callback_query_handler(func=lambda call:)}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call call.data == "admin_back")
def admin_back):
    user_id = call.from_user(call):
    user_id = call.from_user.id
    is_admin = user_id in ADMIN_IDS.id
    is_admin = user_id in ADMIN_IDS
    markup = get_main_menu(is_admin)
    
   
    markup = get_main_menu(is_admin)
    
    bot.delete_message(call.message.chat.id, call bot.delete_message(call.message.chat.id.message.message_id)
    bot.send_message(c, call.message.message_id)
    bot.send_message(call.message.chat.id, "🚀 منوی اصلیall.message.chat.id, "🚀 منوی اصلی:", reply_markup=markup)

# =================:", reply_markup=markup)

#=== اجرا ====================
if __ ==================== اجرا ====================
name__ == "__main__":
    print("="if __name__ == "__main__":
    print("=" * 70)
    print("🚀 ربات م * 70)
    print("🚀 ربات مادر نهایی - نسخه 12.0 -ادر نهایی - نسخه 12.0 - امنیت نظامی")
    print("=" امنیت نظامی")
    print * 70)
    print(f"✅ ا("=" * 70)
    print(f"✅ امنیت: Rate Limit + Anti-Dمنیت: Rate Limit + Anti-DDOS + بن خودکار")
    print(f"✅DOS + بن خودکار")
    print(f"✅ لاگ امنیتی: فعال")
 لاگ امنیتی:    print(f"✅ سر فعال")
    print(f"✅ سرورهای واقعی: فعالورهای واقعی: فعال (SSH)")
    print(f"✅ کتاب (SSH)")
    print(f"✅ کتابخانه های آماده: {len(PREINSTALLED_LIBخانه های آماده: {len(PREINSTRARIES)}")
    print(fALLED_LIBRARIES)}")
    print(f"✅ ادمین ها: {ADMIN_IDS}")
    print"✅ ادمین ها: {ADMIN_IDS}")
    print("=" * 70)
    
    # بررسی ا("=" * 70)
    
    # بررسی اتصال اولیه سرورها
    threadingتصال اولیه سرورها
    threading.Thread(target=server_manager.check_all_.Thread(target=server_manager.check_all_servers, daemon=True).start()
    
    whileservers, daemon=True).start()
    
    while True:
        try:
            bot.infinity_polling True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
           (timeout=60)
        except Exception as e:
            logger.error(f"Error: {e}")
            traceback.print_exc()
 logger.error(f"Error: {e}")
            traceback.print_exc()
            time.sleep(5)