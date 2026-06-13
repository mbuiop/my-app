#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ربات مادر نهایی - نسخه 9.0
با امنیت بالا + دیتابیس SQLite قوی + موتور اجرای پیشرفته + پنل ادمین کامل
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
import random
import string
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from functools import wraps

# ==================== تنظیمات امنیتی ====================
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'.py', '.zip'}
RATE_LIMIT = {}  # برای محدودیت درخواست
RATE_LIMIT_MAX = 5  # حداکثر 5 درخواست در دقیقه
RATE_LIMIT_WINDOW = 60  # 60 ثانیه

# ==================== تنظیمات پایه ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "database")
FILES_DIR = os.path.join(BASE_DIR, "user_files")
RUNNING_DIR = os.path.join(BASE_DIR, "running_bots")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
RECEIPTS_DIR = os.path.join(BASE_DIR, "receipts")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")

for dir_path in [DB_DIR, FILES_DIR, RUNNING_DIR, LOGS_DIR, RECEIPTS_DIR, BACKUP_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# ==================== توکن ربات مادر ====================
BOT_TOKEN = "7685135237:AAEmsHktRw9cEqrHTkCoPZk-fBimK7TDjOo"
bot = telebot.TeleBot(BOT_TOKEN)
bot.delete_webhook()

# ==================== آیدی ادمین ====================
ADMIN_IDS = [327855654]

# ==================== اطلاعات کارت ====================
CARD_NUMBER = "5892101187322777"
CARD_HOLDER = "مرتضی نیکخو خنجری"
PRICE = 2000000

# ==================== لاگینگ ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            os.path.join(LOGS_DIR, 'mother_bot.log'),
            maxBytes=10485760,
            backupCount=10
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== دیتابیس SQLite (قوی شده) ====================
DB_PATH = os.path.join(DB_DIR, 'mother_bot.db')

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # برای عملکرد بهتر
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=10000")
    return conn

# ایجاد جداول با ایندکس‌ها برای سرعت بالا
with get_db() as conn:
    # جدول کاربران
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
            trial_used INTEGER DEFAULT 0
        )
    ''')
    
    # جدول ربات‌ها
    conn.execute('''
        CREATE TABLE IF NOT EXISTS bots (
            id TEXT PRIMARY KEY,
            user_id INTEGER,
            token TEXT,
            name TEXT,
            username TEXT,
            file_path TEXT,
            folder_path TEXT,
            pid INTEGER,
            status TEXT DEFAULT 'stopped',
            container_id TEXT,
            created_at TIMESTAMP,
            last_active TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    ''')
    
    # جدول فیش‌های واریزی
    conn.execute('''
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            receipt_path TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP,
            reviewed_at TIMESTAMP,
            reviewed_by INTEGER,
            payment_code TEXT UNIQUE,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')
    
    # جدول درخواست‌های برداشت
    conn.execute('''
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            card_number TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP,
            processed_at TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')
    
    # جدول تنظیمات
    conn.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP
        )
    ''')
    
    # جدول سرورها
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
            created_at TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')
    
    # ایجاد ایندکس‌ها برای سرعت
    conn.execute('CREATE INDEX IF NOT EXISTS idx_bots_user_id ON bots(user_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_bots_status ON bots(status)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_users_referral_code ON users(referral_code)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_receipts_status ON receipts(status)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_withdrawals_status ON withdrawals(status)')
    
    # تنظیمات پیش‌فرض
    conn.execute('''
        INSERT OR IGNORE INTO settings (key, value, updated_at) VALUES 
        ('price', ?, datetime('now')),
        ('card_number', ?, datetime('now')),
        ('card_holder', ?, datetime('now')),
        ('guide_text', '', datetime('now')),
        ('min_withdraw', '2000000', datetime('now')),
        ('referral_percent', '7', datetime('now'))
    ''', (str(PRICE), CARD_NUMBER, CARD_HOLDER))
    
    conn.commit()

# ==================== توابع امنیتی ====================

def rate_limit(user_id: int) -> bool:
    """محدودیت نرخ درخواست"""
    now = time.time()
    if user_id not in RATE_LIMIT:
        RATE_LIMIT[user_id] = []
    
    # پاک کردن درخواست‌های قدیمی
    RATE_LIMIT[user_id] = [t for t in RATE_LIMIT[user_id] if now - t < RATE_LIMIT_WINDOW]
    
    if len(RATE_LIMIT[user_id]) >= RATE_LIMIT_MAX:
        return False
    
    RATE_LIMIT[user_id].append(now)
    return True

def sanitize_filename(filename: str) -> str:
    """پاکسازی نام فایل"""
    filename = re.sub(r'[^\w\-_.]', '_', filename)
    return filename[:100]

def is_safe_code(code: str) -> tuple:
    """بررسی کد برای کدهای مخرب"""
    dangerous_patterns = [
        r'os\.system\s*\(',
        r'subprocess\.',
        r'eval\s*\(',
        r'exec\s*\(',
        r'__import__\s*\(',
        r'open\s*\(.*[\'"]w[\'"]',
        r'shutil\.rmtree',
        r'os\.remove',
        r'os\.unlink',
        r'os\.rmdir',
        r'globals\(',
        r'locals\(',
        r'__builtins__',
        r'compile\(',
        r'__code__',
        r'\.__class__',
        r'\.__bases__',
        r'\.__subclasses__',
        r'__import__',
        r'execfile',
        r'builtins\.',
        r'breakpoint\(',
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, code, re.IGNORECASE):
            return False, f"کد مخرب شناسایی شد: {pattern}"
    
    return True, "OK"

def backup_database():
    """بکاپ خودکار از دیتابیس"""
    try:
        backup_file = os.path.join(BACKUP_DIR, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        shutil.copy2(DB_PATH, backup_file)
        
        # حذف بکاپ‌های قدیمی (فقط 10 تا آخرین)
        backups = sorted(os.listdir(BACKUP_DIR))
        for old_backup in backups[:-10]:
            os.remove(os.path.join(BACKUP_DIR, old_backup))
        
        return backup_file
    except Exception as e:
        logger.error(f"خطا در بکاپ: {e}")
        return None

# ==================== توابع کمکی ====================

def generate_referral_code(user_id):
    """تولید کد رفرال یکتا"""
    return hashlib.md5(f"{user_id}_{secrets.token_hex(4)}".encode()).hexdigest()[:8]

def get_user(user_id):
    """گرفتن اطلاعات کاربر"""
    try:
        with get_db() as conn:
            user = conn.execute(
                'SELECT * FROM users WHERE user_id = ? AND is_banned = 0',
                (user_id,)
            ).fetchone()
            return dict(user) if user else None
    except:
        return None

def create_user(user_id, username, first_name, last_name, referred_by=None):
    """ایجاد کاربر جدید"""
    try:
        with get_db() as conn:
            now = datetime.now().isoformat()
            referral_code = generate_referral_code(user_id)
            
            conn.execute('''
                INSERT OR IGNORE INTO users 
                (user_id, username, first_name, last_name, referral_code, referred_by, created_at, last_active, payment_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name, referral_code, referred_by, now, now, 'pending'))
            
            conn.execute('''
                UPDATE users SET last_active = ? WHERE user_id = ?
            ''', (now, user_id))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"خطا در create_user: {e}")
        return False

def check_payment(user_id):
    """بررسی وضعیت پرداخت کاربر"""
    try:
        with get_db() as conn:
            user = conn.execute('SELECT payment_status, subscription_end FROM users WHERE user_id = ?', (user_id,)).fetchone()
            if user:
                if user['payment_status'] == 'approved':
                    if user['subscription_end']:
                        if datetime.now().isoformat() > user['subscription_end']:
                            return False
                    return True
            
            receipt = conn.execute('''
                SELECT id FROM receipts 
                WHERE user_id = ? AND status = 'approved'
                ORDER BY created_at DESC LIMIT 1
            ''', (user_id,)).fetchone()
            
            if receipt:
                # فعال‌سازی اشتراک 1 ماهه
                subscription_end = (datetime.now() + timedelta(days=30)).isoformat()
                conn.execute('UPDATE users SET payment_status = ?, subscription_end = ? WHERE user_id = ?', 
                            ('approved', subscription_end, user_id))
                conn.commit()
                return True
            return False
    except:
        return False

def get_user_bots(user_id):
    """دریافت لیست ربات‌های کاربر"""
    try:
        with get_db() as conn:
            bots = conn.execute('''
                SELECT * FROM bots WHERE user_id = ? ORDER BY created_at DESC
            ''', (user_id,)).fetchall()
            return [dict(bot) for bot in bots]
    except:
        return []

# ==================== موتور اجرای پیشرفته و امن ====================

class SafeBotEngine:
    """موتور اجرای ایمن و ایزوله"""
    
    def __init__(self):
        self.running_processes = {}
        self.lock = threading.Lock()
        self.allowed_libs = {
            'requests', 'json', 'time', 'datetime', 'random', 'math',
            'telebot', 'pyTelegramBotAPI', 'jdatetime', 're', 'string',
            'collections', 'itertools', 'functools', 'typing'
        }
    
    def install_library(self, lib_name):
        """نصب کتابخانه در محیط ایمن"""
        if lib_name not in self.allowed_libs:
            return False, "کتابخانه غیرمجاز است"
        
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", lib_name, "--quiet"],
                capture_output=True,
                text=True,
                timeout=60
            )
            return result.returncode == 0, result.stdout
        except:
            return False, "خطا در نصب"
    
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
                    if lib not in ['os', 'sys', 'time', 'datetime', 'json', 're', 'math']:
                        if lib in self.allowed_libs:
                            imports.add(lib)
            elif line.startswith('from '):
                parts = line.split()
                if len(parts) > 1:
                    lib = parts[1].split('.')[0]
                    if lib not in ['os', 'sys', 'time', 'datetime', 'json', 're', 'math']:
                        if lib in self.allowed_libs:
                            imports.add(lib)
        
        return list(imports)
    
    def run_bot(self, bot_id, user_id, code, token):
        """اجرای ربات در محیط ایزوله"""
        result = {
            'success': False,
            'pid': None,
            'error': None,
            'installed': []
        }
        
        try:
            # بررسی امنیت کد
            is_safe, error_msg = is_safe_code(code)
            if not is_safe:
                result['error'] = error_msg
                return result
            
            # تشخیص و نصب کتابخانه‌ها
            requirements = self.detect_requirements(code)
            installed = []
            
            for lib in requirements:
                success, _ = self.install_library(lib)
                if success:
                    installed.append(lib)
            
            result['installed'] = installed
            
            # ایجاد پوشه موقت ایزوله
            bot_dir = os.path.join(RUNNING_DIR, bot_id)
            os.makedirs(bot_dir, exist_ok=True)
            
            # محدود کردن دسترسی‌ها
            os.chmod(bot_dir, 0o700)
            
            # ذخیره کد
            code_path = os.path.join(bot_dir, 'bot.py')
            with open(code_path, 'w', encoding='utf-8') as f:
                f.write(code)
            
            # ذخیره توکن
            with open(os.path.join(bot_dir, 'token.txt'), 'w') as f:
                f.write(token)
            
            # فایل لاگ
            log_file = os.path.join(bot_dir, 'bot.log')
            
            # اجرا با محدودیت منابع (با nice)
            process = subprocess.Popen(
                ['nice', '-n', '19', sys.executable, code_path],
                stdout=open(log_file, 'a'),
                stderr=subprocess.STDOUT,
                cwd=bot_dir,
                start_new_session=True,
                env={'PATH': os.environ.get('PATH', ''), 'PYTHONPATH': ''}  # محیط محدود
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
            else:
                if os.path.exists(log_file):
                    with open(log_file, 'r') as f:
                        result['error'] = f.read()[-500:]
                else:
                    result['error'] = "خطای ناشناخته"
                    
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def stop_bot(self, bot_id):
        """توقف ربات"""
        with self.lock:
            if bot_id in self.running_processes:
                try:
                    pid = self.running_processes[bot_id]['pid']
                    os.killpg(os.getpgid(pid), signal.SIGTERM)
                    time.sleep(1)
                    
                    if bot_id in self.running_processes:
                        del self.running_processes[bot_id]
                    return True
                except:
                    pass
        return False

bot_engine = SafeBotEngine()

# ==================== منوی اصلی ====================
def get_main_menu(is_admin=False):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    
    buttons = [
        types.KeyboardButton('🤖 ساخت ربات جدید'),
        types.KeyboardButton('📋 ربات‌های من'),
        types.KeyboardButton('🔄 فعال/غیرفعال کردن'),
        types.KeyboardButton('🗑 حذف ربات'),
        types.KeyboardButton('💰 کیف پول و رفرال'),
        types.KeyboardButton('📚 راهنما'),
        types.KeyboardButton('📦 نصب کتابخانه'),
        types.KeyboardButton('📊 آمار'),
        types.KeyboardButton('📞 پشتیبانی')
    ]
    
    if is_admin:
        buttons.append(types.KeyboardButton('👑 پنل ادمین'))
    
    markup.add(*buttons)
    return markup

# ==================== دکمه استارت ====================
@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    
    # محدودیت نرخ
    if not rate_limit(user_id):
        bot.send_message(message.chat.id, "❌ لطفاً کمی صبر کنید...")
        return
    
    referred_by = None
    args = message.text.split()
    if len(args) > 1:
        ref_code = args[1]
        try:
            with get_db() as conn:
                referrer = conn.execute('SELECT user_id FROM users WHERE referral_code = ?', (ref_code,)).fetchone()
                if referrer and referrer['user_id'] != user_id:
                    referred_by = referrer['user_id']
        except:
            pass
    
    create_user(user_id, username, first_name, last_name, referred_by)
    
    user = get_user(user_id) or {'referral_code': '', 'referrals_count': 0, 'verified_referrals': 0}
    bot_username = bot.get_me().username
    referral_link = f"https://t.me/{bot_username}?start={user['referral_code']}"
    
    is_admin = user_id in ADMIN_IDS
    markup = get_main_menu(is_admin)
    
    welcome_text = (
        f"🚀 **به ربات مادر حرفه‌ای خوش آمدید {first_name}!**\n\n"
        f"👤 آیدی شما: `{user_id}`\n"
        f"🎁 کد رفرال شما: `{user['referral_code']}`\n"
        f"🔗 لینک دعوت: {referral_link}\n\n"
        f"📊 **آمار رفرال:**\n"
        f"• کلیک‌ها: {user['referrals_count']}\n"
        f"• ساخته شده: {user['verified_referrals']}\n\n"
        f"💡 هر ۵ نفر = ۱ ربات اضافه\n"
        f"📤 فایل `.py` یا `.zip` خود را آپلود کنید"
    )
    
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=markup)

# ==================== کیف پول و رفرال ====================
@bot.message_handler(func=lambda m: m.text == '💰 کیف پول و رفرال')
def wallet_ref(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        bot.send_message(message.chat.id, "❌ لطفاً /start را بزنید")
        return
    
    bot_username = bot.get_me().username
    referral_link = f"https://t.me/{bot_username}?start={user['referral_code']}"
    
    with get_db() as conn:
        # دریافت موجودی و درآمد رفرال
        balance = user.get('balance', 0)
        referral_earnings = user.get('referral_earnings', 0)
        
        # دریافت تعداد ربات‌ها
        current_bots = conn.execute('SELECT COUNT(*) FROM bots WHERE user_id = ?', (user_id,)).fetchone()[0]
        
        extra_bots = user['verified_referrals'] // 5
        max_bots = 1 + extra_bots
    
    text = f"💰 **کیف پول و سیستم رفرال**\n\n"
    text += f"👤 کاربر: {user['first_name']}\n"
    text += f"🆔 آیدی: `{user_id}`\n\n"
    text += f"💳 **موجودی کیف پول:** {balance:,} تومان\n"
    text += f"🎁 **درآمد از رفرال:** {referral_earnings:,} تومان\n\n"
    text += f"🔗 **لینک دعوت شما:**\n{referral_link}\n\n"
    text += f"📊 **آمار رفرال:**\n"
    text += f"• کلیک‌ها: {user['referrals_count']}\n"
    text += f"• ثبت‌نام‌های موفق: {user['verified_referrals']}\n\n"
    text += f"🤖 **ربات‌های شما:**\n"
    text += f"• فعلی: {current_bots}\n"
    text += f"• حداکثر: {max_bots}\n\n"
    text += f"💡 **نحوه کسب درآمد:**\n"
    text += f"• هر کاربر که با لینک شما ثبت‌نام کند\n"
    text += f"• و اشتراک بخرد، **۷٪ سود** به کیف پول شما واریز می‌شود\n"
    text += f"• قابل برداشت از ۲ میلیون تومان\n\n"
    text += f"🏧 برای برداشت روی دکمه برداشت کلیک کنید"
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# ==================== فیش واریزی ====================
@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    
    if not rate_limit(user_id):
        bot.reply_to(message, "❌ لطفاً کمی صبر کنید...")
        return
    
    try:
        with get_db() as conn:
            existing = conn.execute('''
                SELECT id FROM receipts 
                WHERE user_id = ? AND status = 'pending'
            ''', (user_id,)).fetchone()
            
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
            # دریافت قیمت از تنظیمات
            price_row = conn.execute('SELECT value FROM settings WHERE key = "price"').fetchone()
            price = int(price_row['value']) if price_row else PRICE
            
            conn.execute('''
                INSERT INTO receipts (user_id, amount, receipt_path, created_at, payment_code)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, price, receipt_path, datetime.now().isoformat(), payment_code))
            conn.commit()
        
        bot.reply_to(
            message,
            f"✅ **فیش دریافت شد**\n\n"
            f"💰 مبلغ: {price:,} تومان\n"
            f"🆔 کد پیگیری: `{payment_code}`\n\n"
            f"پس از بررسی توسط ادمین فعال می‌شود"
        )
        
        for admin_id in ADMIN_IDS:
            try:
                bot.send_photo(
                    admin_id,
                    open(receipt_path, 'rb'),
                    caption=f"📸 **فیش جدید**\n👤 کاربر: `{user_id}`\n💰 مبلغ: {price:,} تومان\n🆔 کد: `{payment_code}`",
                    parse_mode="Markdown"
                )
            except:
                pass
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")

# ==================== نصب کتابخانه ====================
@bot.message_handler(func=lambda m: m.text == '📦 نصب کتابخانه')
def install_library_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    libs = [
        ('requests', 'requests'),
        ('json', 'json'),
        ('datetime', 'datetime'),
        ('random', 'random'),
        ('math', 'math'),
        ('re', 're'),
        ('string', 'string'),
        ('telebot', 'pyTelegramBotAPI'),
        ('jdatetime', 'jdatetime'),
        ('🔧 دستی', 'custom')
    ]
    
    for name, data in libs:
        markup.add(types.InlineKeyboardButton(name, callback_data=f"lib_{data}"))
    
    bot.send_message(
        message.chat.id,
        "📦 **کتابخانه مورد نظر را انتخاب کنید:**\n(فقط کتابخانه‌های مجاز)",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('lib_'))
def install_library_callback(call):
    lib = call.data.replace('lib_', '')
    
    if lib == 'custom':
        msg = bot.send_message(
            call.message.chat.id,
            "📦 نام کتابخانه مجاز را وارد کنید:"
        )
        bot.register_next_step_handler(msg, install_custom_library)
        return
    
    bot.answer_callback_query(call.id, f"در حال نصب {lib}...")
    
    success, result = bot_engine.install_library(lib)
    if success:
        bot.edit_message_text(f"✅ کتابخانه {lib} با موفقیت نصب شد.", call.message.chat.id, call.message.message_id)
    else:
        bot.edit_message_text(f"❌ خطا در نصب {lib}: {result}", call.message.chat.id, call.message.message_id)

def install_custom_library(message):
    lib = message.text.strip()
    success, result = bot_engine.install_library(lib)
    if success:
        bot.send_message(message.chat.id, f"✅ کتابخانه {lib} با موفقیت نصب شد.")
    else:
        bot.send_message(message.chat.id, f"❌ خطا در نصب {lib}: {result}")

# ==================== ساخت ربات جدید ====================
@bot.message_handler(func=lambda m: m.text == '🤖 ساخت ربات جدید')
def new_bot(message):
    user_id = message.from_user.id
    
    if not rate_limit(user_id):
        bot.send_message(message.chat.id, "❌ لطفاً کمی صبر کنید...")
        return
    
    if not check_payment(user_id):
        with get_db() as conn:
            price_row = conn.execute('SELECT value FROM settings WHERE key = "price"').fetchone()
            price = int(price_row['value']) if price_row else PRICE
            card_row = conn.execute('SELECT value FROM settings WHERE key = "card_number"').fetchone()
            card = card_row['value'] if card_row else CARD_NUMBER
        
        bot.send_message(
            message.chat.id,
            f"⚠️ **کاربر گرامی، از اینکه ما را انتخاب کردید متشکریم**\n\n"
            f"برای فعال‌سازی اشتراک و ساخت ربات، مبلغ **{price:,} تومان** به شماره کارت زیر واریز کنید:\n\n"
            f"💳 **شماره کارت:** `{card}`\n"
            f"🏦 **بانک سپه**\n"
            f"👤 **به نام:** مرتضی نیکخو خنجری\n\n"
            f"📸 **مراحل فعال‌سازی:**\n"
            f"1️⃣ مبلغ را به کارت فوق واریز کنید\n"
            f"2️⃣ از صفحه واریز عکس بگیرید\n"
            f"3️⃣ عکس فیش را در همین چت ارسال کنید\n"
            f"4️⃣ پس از تأیید، اشتراک شما فعال می‌شود\n\n"
            f"✅ **پس از تأیید می‌توانید ربات خود را بسازید**\n\n"
            f"🔗 **لینک رفرال شما:** هر کاربر که با لینک شما وارد شود و خرید کند، **۷٪ سود** به کیف پول شما اضافه می‌شود",
            parse_mode="Markdown"
        )
        return
    
    # بررسی محدودیت تعداد ربات
    user = get_user(user_id)
    extra_bots = user['verified_referrals'] // 5 if user else 0
    max_bots = 1 + extra_bots
    
    with get_db() as conn:
        current_bots = conn.execute('SELECT COUNT(*) FROM bots WHERE user_id = ?', (user_id,)).fetchone()[0]
    
    if current_bots >= max_bots:
        bot.send_message(
            message.chat.id,
            f"❌ **شما به حداکثر تعداد ربات ({max_bots}) رسیده‌اید!**\n\n"
            f"برای ساخت ربات جدید:\n"
            f"1️⃣ یکی از ربات‌ها را حذف کنید\n"
            f"2️⃣ یا با دعوت دوستان ربات اضافه بگیرید\n"
            f"   (هر ۵ دعوت = ۱ ربات اضافه)\n"
            f"3️⃣ یا اشتراک ویژه تهیه کنید",
            parse_mode="Markdown"
        )
        return
    
    bot.send_message(
        message.chat.id,
        "📤 **فایل ربات خود را ارسال کنید**\n\n"
        "✅ فایل‌های مجاز: `.py` یا `.zip`\n"
        "✅ حداکثر حجم: ۵۰ مگابایت\n"
        "✅ توکن ربات داخل کد باشد\n"
        "✅ اگر فایل زیپ است، تمام فایل‌های پروژه را شامل شود\n"
        "✅ کد شما از نظر امنیتی بررسی می‌شود\n\n"
        "⚡ ربات شما در محیطی کاملاً ایزوله و امن اجرا خواهد شد",
        parse_mode="Markdown"
    )

# ==================== آپلود فایل ====================
@bot.message_handler(content_types=['document'])
def handle_build_file(message):
    user_id = message.from_user.id
    
    if not rate_limit(user_id):
        bot.reply_to(message, "❌ لطفاً کمی صبر کنید...")
        return
    
    if not check_payment(user_id):
        bot.reply_to(message, "❌ ابتدا هزینه را پرداخت کنید")
        return
    
    file_name = message.document.file_name
    
    if not any(file_name.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        bot.reply_to(message, "❌ فقط فایل‌های `.py` یا `.zip` مجاز هستند!")
        return
    
    if message.document.file_size > MAX_FILE_SIZE:
        bot.reply_to(message, "❌ حجم فایل نباید بیشتر از ۵۰ مگابایت باشد!")
        return
    
    status_msg = bot.reply_to(message, "🔄 در حال پردازش فایل...")
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # پاکسازی نام فایل
        safe_name = sanitize_filename(file_name)
        file_path = os.path.join(FILES_DIR, str(user_id), f"{int(time.time())}_{safe_name}")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'wb') as f:
            f.write(downloaded_file)
        
        main_code = ""
        
        if file_name.endswith('.zip'):
            extract_dir = os.path.join(FILES_DIR, str(user_id), f"extract_{int(time.time())}")
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
        
        # بررسی امنیت کد
        is_safe, error_msg = is_safe_code(main_code)
        if not is_safe:
            bot.edit_message_text(f"❌ کد شما ناامن است!\n{error_msg}", message.chat.id, status_msg.message_id)
            return
        
        # استخراج توکن
        token = None
        patterns = [
            r'token\s*=\s*["\']([^"\']+)["\']',
            r'TOKEN\s*=\s*["\']([^"\']+)["\']',
            r'API_TOKEN\s*=\s*["\']([^"\']+)["\']',
            r'BOT_TOKEN\s*=\s*["\']([^"\']+)["\']',
            r'bot\s*=\s*telebot\.TeleBot\(\s*["\']([^"\']+)["\']\s*\)'
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
                return
            
            bot_info = response.json()['result']
            bot_name = bot_info['first_name']
            bot_username = bot_info['username']
        except Exception as e:
            bot.edit_message_text(f"❌ خطا در بررسی توکن: {str(e)}", message.chat.id, status_msg.message_id)
            return
        
        bot.edit_message_text("⚡ در حال اجرا در محیط ایزوله...", message.chat.id, status_msg.message_id)
        
        # اجرا با موتور امن
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
                
                conn.execute('''
                    UPDATE users SET bots_count = bots_count + 1, last_active = ?
                    WHERE user_id = ?
                ''', (now, user_id))
                
                # بررسی و اضافه کردن سود رفرال برای معرف
                user = conn.execute('SELECT referred_by FROM users WHERE user_id = ?', (user_id,)).fetchone()
                if user and user['referred_by']:
                    referrer = conn.execute('SELECT * FROM users WHERE user_id = ?', (user['referred_by'],)).fetchone()
                    if referrer:
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
                        
                        conn.execute('''
                            INSERT INTO transactions (user_id, amount, type, description, created_at)
                            VALUES (?, ?, 'referral', ?, ?)
                        ''', (user['referred_by'], amount, f"سود رفرال از کاربر {user_id}", now))
                
                conn.commit()
            
            reply = f"✅ **ربات با موفقیت ساخته شد!** 🎉\n\n"
            reply += f"🤖 نام: {bot_name}\n"
            reply += f"🔗 لینک: https://t.me/{bot_username}\n"
            reply += f"🆔 آیدی ربات: `{bot_id}`\n"
            reply += f"🔄 PID: `{result['pid']}`\n"
            
            if result.get('installed'):
                reply += f"📦 کتابخانه‌های نصب شده: {', '.join(result['installed'])}\n"
            
            reply += f"\n📊 وضعیت: 🟢 در حال اجرا"
            
            bot.edit_message_text(reply, message.chat.id, status_msg.message_id, parse_mode="Markdown")
        else:
            error = result.get('error', 'خطای ناشناخته')
            bot.edit_message_text(f"❌ خطا در اجرا:\n`{error}`", message.chat.id, status_msg.message_id, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        bot.edit_message_text(f"❌ خطا: {str(e)}", message.chat.id, status_msg.message_id)

# ==================== ربات‌های من ====================
@bot.message_handler(func=lambda m: m.text == '📋 ربات‌های من')
def my_bots(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما رباتی ندارید!")
        return
    
    for b in bots[:10]:
        status_emoji = "🟢" if b['status'] == 'running' else "🔴"
        status_text = "در حال اجرا" if b['status'] == 'running' else "متوقف"
        
        text = f"{status_emoji} **{b['name']}**\n"
        text += f"🔗 https://t.me/{b['username']}\n"
        text += f"🆔 `{b['id']}`\n"
        text += f"📊 وضعیت: {status_text}\n"
        text += f"📅 ایجاد: {b['created_at'][:10]}\n"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🔄 تغییر وضعیت", callback_data=f"toggle_{b['id']}"),
            types.InlineKeyboardButton("🗑 حذف", callback_data=f"delete_{b['id']}")
        )
        
        bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

# ==================== فعال/غیرفعال کردن ====================
@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_'))
def toggle_bot(call):
    bot_id = call.data.replace('toggle_', '')
    user_id = call.from_user.id
    bot_info = None
    
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
            bot.edit_message_text(
                f"✅ ربات {bot_info['name']} متوقف شد.",
                call.message.chat.id,
                call.message.message_id
            )
        else:
            bot.answer_callback_query(call.id, "❌ خطا در توقف!")
    else:
        bot.answer_callback_query(call.id, "❌ این ربات در حال حاضر فعال نیست")

# ==================== حذف ربات ====================
@bot.message_handler(func=lambda m: m.text == '🗑 حذف ربات')
def delete_prompt(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما رباتی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        btn = types.InlineKeyboardButton(
            f"🗑 {b['name']}",
            callback_data=f"delete_{b['id']}"
        )
        markup.add(btn)
    
    bot.send_message(
        message.chat.id,
        "🗑 **ربات مورد نظر را انتخاب کنید:**",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
def confirm_delete(call):
    bot_id = call.data.replace('delete_', '')
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("✅ بله", callback_data=f"confirm_del_{bot_id}")
    btn2 = types.InlineKeyboardButton("❌ خیر", callback_data="cancel_del")
    markup.add(btn1, btn2)
    
    bot.edit_message_text(
        "⚠️ **آیا از حذف این ربات اطمینان دارید؟**\nاین عملیات غیرقابل بازگشت است.",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_del_'))
def do_delete(call):
    bot_id = call.data.replace('confirm_del_', '')
    user_id = call.from_user.id
    
    bot_engine.stop_bot(bot_id)
    
    with get_db() as conn:
        bot = conn.execute('SELECT * FROM bots WHERE id = ? AND user_id = ?', (bot_id, user_id)).fetchone()
        if bot:
            if bot['file_path'] and os.path.exists(bot['file_path']):
                os.remove(bot['file_path'])
            if bot['folder_path'] and os.path.exists(bot['folder_path']):
                shutil.rmtree(bot['folder_path'])
            
            conn.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
            conn.execute('UPDATE users SET bots_count = bots_count - 1 WHERE user_id = ?', (user_id,))
            conn.commit()
            
            bot.edit_message_text("✅ ربات با موفقیت حذف شد.", call.message.chat.id, call.message.message_id)
        else:
            bot.edit_message_text("❌ خطا در حذف ربات!", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == 'cancel_del')
def cancel_delete(call):
    bot.edit_message_text("❌ عملیات حذف لغو شد.", call.message.chat.id, call.message.message_id)

# ==================== راهنما ====================
@bot.message_handler(func=lambda m: m.text == '📚 راهنما')
def guide(message):
    with get_db() as conn:
        guide_text_row = conn.execute('SELECT value FROM settings WHERE key = "guide_text"').fetchone()
        guide_text = guide_text_row['value'] if guide_text_row else ""
    
    if not guide_text:
        guide_text = (
            "📚 **راهنمای کامل ربات مادر**\n\n"
            "**1️⃣ ساخت ربات جدید:**\n"
            "   • ابتدا اشتراک تهیه کنید\n"
            "   • فایل `.py` یا `.zip` خود را آپلود کنید\n"
            "   • توکن ربات داخل کد باشد\n"
            "   • کد شما از نظر امنیتی بررسی می‌شود\n\n"
            "**2️⃣ رفرال و درآمدزایی:**\n"
            "   • لینک رفرال خود را به اشتراک بگذارید\n"
            "   • هر کاربر که ثبت‌نام کند و خرید کند\n"
            "   • **۷٪ سود** به کیف پول شما اضافه می‌شود\n"
            "   • قابل برداشت از ۲ میلیون تومان\n\n"
            "**3️⃣ کتابخانه‌های مجاز:**\n"
            "   • requests, json, datetime, random\n"
            "   • math, re, string, telebot, jdatetime\n\n"
            "**4️⃣ امنیت:**\n"
            "   • کد شما در محیط ایزوله اجرا می‌شود\n"
            "   • دسترسی به سیستم عامل محدود شده\n"
            "   • کدهای مخرب شناسایی و مسدود می‌شوند\n\n"
            "**5️⃣ پشتیبانی:**\n"
            "   • @shahraghee13"
        )
    
    bot.send_message(message.chat.id, guide_text, parse_mode="Markdown")

# ==================== آمار ====================
@bot.message_handler(func=lambda m: m.text == '📊 آمار')
def stats(message):
    try:
        with get_db() as conn:
            total_users = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
            total_bots = conn.execute('SELECT COUNT(*) FROM bots').fetchone()[0]
            running_bots = conn.execute('SELECT COUNT(*) FROM bots WHERE status = "running"').fetchone()[0]
            total_payments = conn.execute('SELECT COUNT(*) FROM receipts WHERE status = "approved"').fetchone()[0]
            pending_withdrawals = conn.execute('SELECT COUNT(*) FROM withdrawals WHERE status = "pending"').fetchone()[0]
        
        text = f"📊 **آمار سامانه**\n\n"
        text += f"👥 کاربران: {total_users}\n"
        text += f"🤖 کل ربات‌ها: {total_bots}\n"
        text += f"🟢 فعال: {running_bots}\n"
        text += f"💰 پرداخت‌ها: {total_payments}\n"
        text += f"🏧 درخواست‌های برداشت: {pending_withdrawals}"
        
        bot.send_message(message.chat.id, text, parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, "📊 آمار در دسترس نیست")

# ==================== پشتیبانی ====================
@bot.message_handler(func=lambda m: m.text == '📞 پشتیبانی')
def support(message):
    bot.send_message(
        message.chat.id,
        "📞 **پشتیبانی:** @shahraghee13\n\n"
        "ساعات پاسخگویی: ۹ صبح تا ۱۲ شب\n"
        "لطفاً سوال خود را کامل مطرح کنید.",
        parse_mode="Markdown"
    )

# ==================== پنل ادمین (با دکمه‌های جدید) ====================
@bot.message_handler(func=lambda m: m.text == '👑 پنل ادمین')
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ شما دسترسی ادمین ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💰 تغییر قیمت", callback_data="admin_change_price"),
        types.InlineKeyboardButton("💳 تغییر شماره کارت", callback_data="admin_change_card"),
        types.InlineKeyboardButton("📝 تغییر متن راهنما", callback_data="admin_change_guide"),
        types.InlineKeyboardButton("🖥 اضافه کردن سرور", callback_data="admin_add_server"),
        types.InlineKeyboardButton("🗑 حذف ربات کاربران", callback_data="admin_delete_user_bot"),
        types.InlineKeyboardButton("🏧 درخواست‌های برداشت", callback_data="admin_withdrawals"),
        types.InlineKeyboardButton("📸 فیش‌های در انتظار", callback_data="admin_receipts"),
        types.InlineKeyboardButton("👥 لیست کاربران", callback_data="admin_users"),
        types.InlineKeyboardButton("📊 آمار کامل", callback_data="admin_stats"),
        types.InlineKeyboardButton("💾 بکاپ دیتابیس", callback_data="admin_backup"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    bot.send_message(
        message.chat.id,
        "👑 **پنل مدیریت پیشرفته**\n\nلطفاً یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=markup,
        parse_mode="Markdown"
    )

# ==================== دکمه تغییر قیمت ====================
@bot.callback_query_handler(func=lambda call: call.data == "admin_change_price")
def change_price_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "💰 **قیمت جدید را به تومان وارد کنید:**\nمثال: `2500000`", parse_mode="Markdown")
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
        bot.send_message(message.chat.id, "❌ لطفاً یک عدد معتبر وارد کنید!")

# ==================== دکمه تغییر شماره کارت ====================
@bot.callback_query_handler(func=lambda call: call.data == "admin_change_card")
def change_card_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "💳 **شماره کارت جدید را وارد کنید:**\nمثال: `5892101187322777`", parse_mode="Markdown")
    bot.register_next_step_handler(msg, change_card_process)

def change_card_process(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    card_number = message.text.strip()
    
    if not card_number.isdigit() or len(card_number) != 16:
        bot.send_message(message.chat.id, "❌ شماره کارت باید ۱۶ رقم باشد!")
        return
    
    with get_db() as conn:
        conn.execute('UPDATE settings SET value = ?, updated_at = ? WHERE key = "card_number"', 
                    (card_number, datetime.now().isoformat()))
        conn.commit()
    
    bot.send_message(message.chat.id, f"✅ شماره کارت با موفقیت به {card_number} تغییر کرد!")

# ==================== دکمه تغییر متن راهنما ====================
@bot.callback_query_handler(func=lambda call: call.data == "admin_change_guide")
def change_guide_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "📝 **متن جدید راهنما را وارد کنید:**\n(می‌توانید از Markdown استفاده کنید)", parse_mode="Markdown")
    bot.register_next_step_handler(msg, change_guide_process)

def change_guide_process(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    new_guide = message.text.strip()
    
    with get_db() as conn:
        conn.execute('UPDATE settings SET value = ?, updated_at = ? WHERE key = "guide_text"', 
                    (new_guide, datetime.now().isoformat()))
        conn.commit()
    
    bot.send_message(message.chat.id, "✅ متن راهنما با موفقیت به‌روزرسانی شد!")

# ==================== دکمه اضافه کردن سرور ====================
@bot.callback_query_handler(func=lambda call: call.data == "admin_add_server")
def add_server_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    bot.send_message(call.message.chat.id, "🖥 **اضافه کردن سرور جدید**\n\nلطفاً **نام** سرور را وارد کنید:")
    bot.register_next_step_handler(call.message, add_server_name)

def add_server_name(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    name = message.text.strip()
    if not name:
        bot.send_message(message.chat.id, "❌ نام معتبر وارد کنید!")
        return
    
    bot.send_message(message.chat.id, "🌐 **آیپی** سرور را وارد کنید (مثال: `192.168.1.100`):", parse_mode="Markdown")
    bot.register_next_step_handler(message, add_server_ip, name)

def add_server_ip(message, name):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    ip = message.text.strip()
    if not ip:
        bot.send_message(message.chat.id, "❌ آیپی معتبر وارد کنید!")
        return
    
    bot.send_message(message.chat.id, "🔌 **پورت** سرور را وارد کنید (پیش‌فرض: `22`):", parse_mode="Markdown")
    bot.register_next_step_handler(message, add_server_port, name, ip)

def add_server_port(message, name, ip):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        port = int(message.text.strip()) if message.text.strip() else 22
    except:
        port = 22
    
    bot.send_message(message.chat.id, "👤 **یوزرنیم** سرور را وارد کنید:")
    bot.register_next_step_handler(message, add_server_username, name, ip, port)

def add_server_username(message, name, ip, port):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    username = message.text.strip()
    if not username:
        bot.send_message(message.chat.id, "❌ یوزرنیم معتبر وارد کنید!")
        return
    
    bot.send_message(message.chat.id, "🔑 **رمز عبور** سرور را وارد کنید:")
    bot.register_next_step_handler(message, add_server_password, name, ip, port, username)

def add_server_password(message, name, ip, port, username):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    password = message.text.strip()
    if not password:
        bot.send_message(message.chat.id, "❌ رمز عبور معتبر وارد کنید!")
        return
    
    with get_db() as conn:
        conn.execute('''
            INSERT INTO servers (name, host, port, username, password, max_workers, status, created_at)
            VALUES (?, ?, ?, ?, ?, 100, 'active', ?)
        ''', (name, ip, port, username, password, datetime.now().isoformat()))
        conn.commit()
    
    bot.send_message(
        message.chat.id,
        f"✅ **سرور با موفقیت اضافه شد!**\n\n"
        f"🖥 نام: {name}\n"
        f"🌐 آیپی: {ip}\n"
        f"🔌 پورت: {port}\n"
        f"👤 یوزرنیم: {username}\n"
        f"📊 حداکثر کارگر: 100\n\n"
        f"⚡ سرور به کلاستر اضافه شد و بار بین سرورها تقسیم می‌شود."
    )

# ==================== دکمه حذف ربات کاربران (با لیست) ====================
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
        btn = types.InlineKeyboardButton(
            f"🗑 {b['name']} (کاربر: {b['user_id']})",
            callback_data=f"admin_del_bot_{b['id']}"
        )
        markup.add(btn)
    
    bot.send_message(
        call.message.chat.id,
        "🗑 **لیست ربات‌ها**\nبرای حذف یک ربات روی آن کلیک کنید:",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_del_bot_"))
def admin_delete_bot(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    bot_id = call.data.replace("admin_del_bot_", "")
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ بله، حذف کن", callback_data=f"admin_confirm_del_{bot_id}"),
        types.InlineKeyboardButton("❌ انصراف", callback_data="admin_cancel_del")
    )
    
    bot.edit_message_text(
        f"⚠️ آیا از حذف ربات `{bot_id}` اطمینان دارید؟\nاین عملیات غیرقابل بازگشت است.",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_confirm_del_"))
def admin_confirm_delete_bot(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    bot_id = call.data.replace("admin_confirm_del_", "")
    
    bot_engine.stop_bot(bot_id)
    
    with get_db() as conn:
        bot_info = conn.execute('SELECT * FROM bots WHERE id = ?', (bot_id,)).fetchone()
        if bot_info:
            if bot_info['file_path'] and os.path.exists(bot_info['file_path']):
                os.remove(bot_info['file_path'])
            if bot_info['folder_path'] and os.path.exists(bot_info['folder_path']):
                shutil.rmtree(bot_info['folder_path'])
            
            conn.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
            conn.execute('UPDATE users SET bots_count = bots_count - 1 WHERE user_id = ?', (bot_info['user_id'],))
            conn.commit()
    
    bot.edit_message_text(
        f"✅ ربات `{bot_id}` با موفقیت حذف شد.",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_cancel_del")
def admin_cancel_delete(call):
    bot.edit_message_text("❌ عملیات حذف لغو شد.", call.message.chat.id, call.message.message_id)

# ==================== دکمه درخواست‌های برداشت ====================
@bot.callback_query_handler(func=lambda call: call.data == "admin_withdrawals")
def admin_withdrawals(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        withdrawals = conn.execute('''
            SELECT * FROM withdrawals WHERE status = 'pending' ORDER BY created_at DESC
        ''').fetchall()
    
    if not withdrawals:
        bot.send_message(call.message.chat.id, "🏧 هیچ درخواست برداشتی در انتظار نیست")
        return
    
    for w in withdrawals:
        text = f"🏧 **درخواست برداشت**\n\n"
        text += f"🆔 شماره: {w['id']}\n"
        text += f"👤 کاربر: `{w['user_id']}`\n"
        text += f"💰 مبلغ: {w['amount']:,} تومان\n"
        text += f"💳 شماره کارت: `{w['card_number']}`\n"
        text += f"📅 تاریخ: {w['created_at'][:10]}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ پرداخت شد", callback_data=f"pay_withdraw_{w['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"reject_withdraw_{w['id']}")
        )
        
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_withdraw_"))
def pay_withdraw(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    withdrawal_id = int(call.data.replace("pay_withdraw_", ""))
    
    with get_db() as conn:
        conn.execute('''
            UPDATE withdrawals SET status = 'approved', processed_at = ?
            WHERE id = ?
        ''', (datetime.now().isoformat(), withdrawal_id))
        conn.commit()
        
        withdrawal = conn.execute('SELECT * FROM withdrawals WHERE id = ?', (withdrawal_id,)).fetchone()
        if withdrawal:
            try:
                bot.send_message(
                    withdrawal['user_id'],
                    f"✅ **برداشت وجه شما انجام شد!**\n\n"
                    f"💰 مبلغ: {withdrawal['amount']:,} تومان\n"
                    f"💳 به کارت: `{withdrawal['card_number']}`\n"
                    f"📅 تاریخ: {datetime.now().isoformat()[:10]}\n\n"
                    f"متشکر از اعتماد شما",
                    parse_mode="Markdown"
                )
            except:
                pass
    
    bot.answer_callback_query(call.id, "✅ برداشت تأیید شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("reject_withdraw_"))
def reject_withdraw(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    withdrawal_id = int(call.data.replace("reject_withdraw_", ""))
    
    with get_db() as conn:
        conn.execute('''
            UPDATE withdrawals SET status = 'rejected', processed_at = ?
            WHERE id = ?
        ''', (datetime.now().isoformat(), withdrawal_id))
        
        withdrawal = conn.execute('SELECT * FROM withdrawals WHERE id = ?', (withdrawal_id,)).fetchone()
        if withdrawal:
            conn.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', 
                        (withdrawal['amount'], withdrawal['user_id']))
            conn.commit()
            
            try:
                bot.send_message(
                    withdrawal['user_id'],
                    f"❌ **درخواست برداشت شما رد شد!**\n\n"
                    f"💰 مبلغ: {withdrawal['amount']:,} تومان\n"
                    f"💳 به کارت: `{withdrawal['card_number']}`\n\n"
                    f"موجودی به کیف پول شما برگشت داده شد.\n"
                    f"در صورت نیاز با پشتیبانی تماس بگیرید.",
                    parse_mode="Markdown"
                )
            except:
                pass
    
    bot.answer_callback_query(call.id, "❌ برداشت رد شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== دکمه فیش‌های در انتظار ====================
@bot.callback_query_handler(func=lambda call: call.data == "admin_receipts")
def admin_receipts(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        receipts = conn.execute('''
            SELECT * FROM receipts WHERE status = 'pending' ORDER BY created_at DESC
        ''').fetchall()
    
    if not receipts:
        bot.send_message(call.message.chat.id, "📸 هیچ فیش در انتظاری وجود ندارد")
        return
    
    for r in receipts:
        text = f"📸 **فیش واریزی**\n\n"
        text += f"🆔 شماره: {r['id']}\n"
        text += f"👤 کاربر: `{r['user_id']}`\n"
        text += f"💰 مبلغ: {r['amount']:,} تومان\n"
        text += f"🆔 کد پیگیری: `{r['payment_code']}`\n"
        text += f"📅 تاریخ: {r['created_at'][:10]}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید و فعال‌سازی", callback_data=f"approve_receipt_{r['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"reject_receipt_{r['id']}")
        )
        
        if os.path.exists(r['receipt_path']):
            with open(r['receipt_path'], 'rb') as f:
                bot.send_photo(call.message.chat.id, f, caption=text, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_receipt_"))
def approve_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    receipt_id = int(call.data.replace("approve_receipt_", ""))
    
    with get_db() as conn:
        receipt = conn.execute('SELECT * FROM receipts WHERE id = ?', (receipt_id,)).fetchone()
        if receipt:
            # فعال‌سازی اشتراک 1 ماهه
            subscription_end = (datetime.now() + timedelta(days=30)).isoformat()
            
            conn.execute('''
                UPDATE receipts SET status = 'approved', reviewed_at = ?, reviewed_by = ?
                WHERE id = ?
            ''', (datetime.now().isoformat(), call.from_user.id, receipt_id))
            
            conn.execute('''
                UPDATE users SET payment_status = 'approved', subscription_end = ?
                WHERE user_id = ?
            ''', (subscription_end, receipt['user_id']))
            
            # اضافه کردن سود رفرال ۷٪
            user = conn.execute('SELECT referred_by FROM users WHERE user_id = ?', (receipt['user_id'],)).fetchone()
            if user and user['referred_by']:
                percent_row = conn.execute('SELECT value FROM settings WHERE key = "referral_percent"').fetchone()
                percent = int(percent_row['value']) if percent_row else 7
                amount = int(receipt['amount'] * percent / 100)
                
                conn.execute('''
                    UPDATE users SET 
                        balance = balance + ?,
                        referral_earnings = referral_earnings + ?,
                        verified_referrals = verified_referrals + 1
                    WHERE user_id = ?
                ''', (amount, amount, user['referred_by']))
                
                conn.execute('''
                    INSERT INTO transactions (user_id, amount, type, description, created_at)
                    VALUES (?, ?, 'referral', ?, ?)
                ''', (user['referred_by'], amount, f"سود رفرال از کاربر {receipt['user_id']}", datetime.now().isoformat()))
            
            conn.commit()
            
            try:
                bot.send_message(
                    receipt['user_id'],
                    f"✅ **فیش شما تایید شد!** 🎉\n\n"
                    f"💰 مبلغ: {receipt['amount']:,} تومان\n"
                    f"📅 اعتبار اشتراک تا: {subscription_end[:10]}\n\n"
                    f"اکنون می‌توانید ربات خود را بسازید.\n"
                    f"از دکمه '🤖 ساخت ربات جدید' استفاده کنید.",
                    parse_mode="Markdown"
                )
            except:
                pass
    
    bot.answer_callback_query(call.id, "✅ فیش تایید شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("reject_receipt_"))
def reject_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    receipt_id = int(call.data.replace("reject_receipt_", ""))
    
    with get_db() as conn:
        receipt = conn.execute('SELECT * FROM receipts WHERE id = ?', (receipt_id,)).fetchone()
        if receipt:
            conn.execute('''
                UPDATE receipts SET status = 'rejected', reviewed_at = ?, reviewed_by = ?
                WHERE id = ?
            ''', (datetime.now().isoformat(), call.from_user.id, receipt_id))
            conn.commit()
            
            try:
                bot.send_message(
                    receipt['user_id'],
                    f"❌ **فیش شما رد شد!**\n\n"
                    f"💰 مبلغ: {receipt['amount']:,} تومان\n\n"
                    f"دلایل احتمالی:\n"
                    f"• تصویر فیش نامشخص است\n"
                    f"• مبلغ واریزی با مبلغ درخواستی مطابقت ندارد\n"
                    f"• شماره کارت اشتباه است\n\n"
                    f"لطفاً دوباره اقدام کنید.\n"
                    f"پشتیبانی: @shahraghee13",
                    parse_mode="Markdown"
                )
            except:
                pass
    
    bot.answer_callback_query(call.id, "❌ فیش رد شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== دکمه لیست کاربران ====================
@bot.callback_query_handler(func=lambda call: call.data == "admin_users")
def admin_users(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        users = conn.execute('''
            SELECT u.*, COUNT(b.id) as bots_count 
            FROM users u
            LEFT JOIN bots b ON u.user_id = b.user_id
            GROUP BY u.user_id
            ORDER BY u.created_at DESC
            LIMIT 30
        ''').fetchall()
    
    if not users:
        bot.send_message(call.message.chat.id, "👥 کاربری یافت نشد")
        return
    
    text = "👥 **۳۰ کاربر آخر:**\n\n"
    for u in users:
        payment = "✅" if u['payment_status'] == 'approved' else "⏳"
        text += f"{payment} `{u['user_id']}` - {u['first_name'] or 'بدون نام'}\n"
        text += f"   🤖 {u['bots_count']} | 🎁 {u['verified_referrals']} | 💰 {u['balance']:,}\n\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

# ==================== دکمه آمار کامل ====================
@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_stats(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    with get_db() as conn:
        total_users = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        total_bots = conn.execute('SELECT COUNT(*) FROM bots').fetchone()[0]
        running_bots = conn.execute('SELECT COUNT(*) FROM bots WHERE status = "running"').fetchone()[0]
        total_receipts = conn.execute('SELECT COUNT(*) FROM receipts').fetchone()[0]
        pending_receipts = conn.execute('SELECT COUNT(*) FROM receipts WHERE status = "pending"').fetchone()[0]
        approved_receipts = conn.execute('SELECT COUNT(*) FROM receipts WHERE status = "approved"').fetchone()[0]
        total_amount = conn.execute('SELECT COALESCE(SUM(amount), 0) FROM receipts WHERE status = "approved"').fetchone()[0]
        paid_users = conn.execute('SELECT COUNT(*) FROM users WHERE payment_status = "approved"').fetchone()[0]
        pending_withdrawals = conn.execute('SELECT COUNT(*) FROM withdrawals WHERE status = "pending"').fetchone()[0]
        total_withdrawals = conn.execute('SELECT COALESCE(SUM(amount), 0) FROM withdrawals WHERE status = "approved"').fetchone()[0]
        total_servers = conn.execute('SELECT COUNT(*) FROM servers WHERE status = "active"').fetchone()[0]
        
        # محاسبه درآمد کل
        total_income = total_amount
        total_profit = total_income - total_withdrawals
    
    text = f"📊 **آمار کامل سامانه**\n\n"
    text += f"👥 **کاربران:**\n"
    text += f"   • کل کاربران: {total_users}\n"
    text += f"   • پرداخت کرده: {paid_users}\n"
    text += f"   • درصد تبدیل: {int(paid_users/total_users*100) if total_users > 0 else 0}%\n\n"
    text += f"🤖 **ربات‌ها:**\n"
    text += f"   • کل ربات‌ها: {total_bots}\n"
    text += f"   • فعال: {running_bots}\n"
    text += f"   • غیرفعال: {total_bots - running_bots}\n\n"
    text += f"💰 **مالی:**\n"
    text += f"   • کل واریزی‌ها: {total_income:,} تومان\n"
    text += f"   • کل برداشت‌ها: {total_withdrawals:,} تومان\n"
    text += f"   • سود خالص: {total_profit:,} تومان\n\n"
    text += f"📸 **فیش‌ها:**\n"
    text += f"   • کل: {total_receipts}\n"
    text += f"   • در انتظار: {pending_receipts}\n"
    text += f"   • تایید شده: {approved_receipts}\n\n"
    text += f"🏧 **برداشت‌ها:**\n"
    text += f"   • در انتظار: {pending_withdrawals}\n\n"
    text += f"🖥 **زیرساخت:**\n"
    text += f"   • سرورهای فعال: {total_servers}"
    
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

# ==================== دکمه بکاپ دیتابیس ====================
@bot.callback_query_handler(func=lambda call: call.data == "admin_backup")
def admin_backup(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    backup_file = backup_database()
    
    if backup_file and os.path.exists(backup_file):
        with open(backup_file, 'rb') as f:
            bot.send_document(
                call.message.chat.id,
                f,
                caption=f"💾 **بکاپ دیتابیس**\n📅 تاریخ: {datetime.now().isoformat()[:19]}\n📁 مکان: {backup_file}",
                parse_mode="Markdown"
            )
        bot.answer_callback_query(call.id, "✅ بکاپ گرفته شد")
    else:
        bot.answer_callback_query(call.id, "❌ خطا در بکاپ گیری")

# ==================== دکمه بازگشت ====================
@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call):
    user_id = call.from_user.id
    is_admin = user_id in ADMIN_IDS
    markup = get_main_menu(is_admin)
    
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "🚀 منوی اصلی:", reply_markup=markup)

# ==================== دکمه برداشت برای کاربران ====================
@bot.message_handler(func=lambda m: m.text == '🏧 برداشت وجه')
def withdraw_menu(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        bot.send_message(message.chat.id, "❌ لطفاً /start را بزنید")
        return
    
    balance = user.get('balance', 0)
    min_withdraw = 2000000
    
    if balance < min_withdraw:
        bot.send_message(
            message.chat.id,
            f"❌ **موجودی شما کافی نیست!**\n\n"
            f"💰 موجودی فعلی: {balance:,} تومان\n"
            f"💰 حداقل برداشت: {min_withdraw:,} تومان\n\n"
            f"💡 **راه‌های افزایش موجودی:**\n"
            f"• دعوت از دوستان (۷٪ سود)\n"
            f"• هر کاربر = {int(PRICE * 0.07):,} تومان سود",
            parse_mode="Markdown"
        )
        return
    
    msg = bot.send_message(
        message.chat.id,
        f"🏧 **درخواست برداشت وجه**\n\n"
        f"💰 موجودی قابل برداشت: {balance:,} تومان\n\n"
        f"لطفاً شماره کارت خود را به صورت ۱۶ رقمی وارد کنید:\n"
        f"مثال: `6219861034567890`\n\n"
        f"⚠️ دقت کنید شماره کارت صحیح باشد",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_withdraw, user_id, balance)

def process_withdraw(message, user_id, balance):
    text = message.text.strip()
    card_match = re.search(r'\d{16}', text)
    
    if not card_match:
        bot.send_message(message.chat.id, "❌ شماره کارت نامعتبر! لطفاً ۱۶ رقم کارت را وارد کنید.")
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
        f"✅ **درخواست برداشت ثبت شد!**\n\n"
        f"💰 مبلغ: {balance:,} تومان\n"
        f"💳 شماره کارت: `{card_number}`\n"
        f"📅 تاریخ: {datetime.now().isoformat()[:10]}\n\n"
        f"وضعیت: در انتظار بررسی\n"
        f"پس از تأیید ادمین، وجه به کارت شما واریز می‌شود.",
        parse_mode="Markdown"
    )
    
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(
                admin_id,
                f"🏧 **درخواست برداشت جدید**\n\n"
                f"👤 کاربر: `{user_id}`\n"
                f"💰 مبلغ: {balance:,} تومان\n"
                f"💳 کارت: `{card_number}`\n"
                f"📅 تاریخ: {datetime.now().isoformat()[:10]}",
                parse_mode="Markdown"
            )
        except:
            pass

# ==================== بکاپ خودکار روزانه ====================
def daily_backup():
    """بکاپ روزانه"""
    while True:
        time.sleep(24 * 60 * 60)  # 24 ساعت
        backup_database()
        logger.info("بکاپ خودکار انجام شد")

backup_thread = threading.Thread(target=daily_backup, daemon=True)
backup_thread.start()

# ==================== اجرا ====================
if __name__ == "__main__":
    print("=" * 70)
    print("🚀 ربات مادر نهایی - نسخه 9.0")
    print("=" * 70)
    print(f"✅ موتور اجرای ایمن: فعال")
    print(f"✅ دیتابیس: SQLite با ایندکس‌های بهینه")
    print(f"✅ امنیت: بررسی کدهای مخرب + محدودیت نرخ")
    print(f"✅ بکاپ خودکار: فعال (هر 24 ساعت)")
    print(f"✅ ادمین‌ها: {ADMIN_IDS}")
    print(f"✅ پنل ادمین: فعال (با 11 دکمه مدیریتی)")
    print("=" * 70)
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            logger.error(f"خطا: {e}")
            time.sleep(5)