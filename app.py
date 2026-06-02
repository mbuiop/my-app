#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ربات مادر نهایی - نسخه 9.0 نهایی
با تمام قابلیت‌های مورد نیاز - کاملاً پایدار
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
import psutil
import secrets
import logging
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ==================== تنظیمات پایه ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "database")
FILES_DIR = os.path.join(BASE_DIR, "user_files")
RUNNING_DIR = os.path.join(BASE_DIR, "running_bots")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
RECEIPTS_DIR = os.path.join(BASE_DIR, "receipts")
FOLDERS_DIR = os.path.join(BASE_DIR, "user_folders")

for d in [DB_DIR, FILES_DIR, RUNNING_DIR, LOGS_DIR, RECEIPTS_DIR, FOLDERS_DIR]:
    os.makedirs(d, exist_ok=True)

# ==================== توکن ربات مادر ====================
BOT_TOKEN = "7685135237:AAEmsHktRw9cEqrHTkCoPZk-fBimK7TDjOo"
bot = telebot.TeleBot(BOT_TOKEN)
bot.remove_webhook()

# ==================== آیدی ادمین ====================
ADMIN_IDS = [327855654]

# ==================== اطلاعات کارت ====================
CARD_NUMBER = "5892101187322777"
CARD_HOLDER = "مرتضی نیکخو خنجری"
CARD_BANK = "بانک ملی"
PRICE = 50000  # قیمت 50 هزار تومان

# ==================== لاگینگ ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            os.path.join(LOGS_DIR, 'mother_bot.log'),
            maxBytes=10485760,
            backupCount=10,
            encoding='utf-8'
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== دیتابیس ====================
DB_PATH = os.path.join(DB_DIR, 'mother_bot.db')

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

# ایجاد جداول
with get_db() as conn:
    # کاربران
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            balance INTEGER DEFAULT 0,
            bots_count INTEGER DEFAULT 0,
            max_bots INTEGER DEFAULT 3,
            referral_code TEXT UNIQUE,
            referred_by INTEGER,
            referrals_count INTEGER DEFAULT 0,
            verified_referrals INTEGER DEFAULT 0,
            payment_status TEXT DEFAULT 'approved',
            payment_date TIMESTAMP,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP,
            last_active TIMESTAMP
        )
    ''')
    
    # ربات‌ها
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
            created_at TIMESTAMP,
            last_active TIMESTAMP,
            execution_count INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    ''')
    
    # پوشه‌های کاربران
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_folders (
            id TEXT PRIMARY KEY,
            user_id INTEGER,
            folder_name TEXT,
            folder_path TEXT,
            parent_id TEXT,
            created_at TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    ''')
    
    # فایل‌های داخل پوشه‌ها
    conn.execute('''
        CREATE TABLE IF NOT EXISTS folder_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folder_id TEXT,
            file_name TEXT,
            file_path TEXT,
            content TEXT,
            added_at TIMESTAMP,
            FOREIGN KEY(folder_id) REFERENCES user_folders(id) ON DELETE CASCADE
        )
    ''')
    
    # فیش‌ها
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
    
    # درخواست‌های برداشت
    conn.execute('''
        CREATE TABLE IF NOT EXISTS withdraw_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            card_number TEXT,
            card_holder TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP,
            processed_at TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')
    
    # کتابخانه‌های نصب شده
    conn.execute('''
        CREATE TABLE IF NOT EXISTS installed_libraries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            version TEXT,
            installed_at TIMESTAMP
        )
    ''')
    
    conn.commit()

# ==================== توابع کمکی ====================

def generate_referral_code(user_id):
    return hashlib.md5(f"{user_id}_{time.time()}_{secrets.token_hex(4)}".encode()).hexdigest()[:10]

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
                (user_id, username, first_name, last_name, referral_code, referred_by, created_at, last_active, payment_status, max_bots)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name, referral_code, referred_by, now, now, 'approved', 3))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error create_user: {e}")
        return False

def check_payment(user_id):
    """بررسی پرداخت - همیشه فعال برای تست"""
    return True

def get_user_bots_count(user_id):
    try:
        with get_db() as conn:
            result = conn.execute('SELECT COUNT(*) as c FROM bots WHERE user_id = ?', (user_id,)).fetchone()
            return result['c'] if result else 0
    except:
        return 0

def check_bot_limit(user_id):
    """بررسی محدودیت ربات (حداکثر ۳ تا)"""
    try:
        with get_db() as conn:
            user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
            if not user:
                return True, 3, 0
            
            max_bots = 3
            current_bots = get_user_bots_count(user_id)
            return current_bots < max_bots, max_bots, current_bots
    except:
        return True, 3, 0

def get_user_bots(user_id):
    try:
        with get_db() as conn:
            bots = conn.execute('SELECT * FROM bots WHERE user_id = ? ORDER BY created_at DESC', (user_id,)).fetchall()
            return [dict(bot) for bot in bots]
    except:
        return []

def get_bot(bot_id):
    try:
        with get_db() as conn:
            bot = conn.execute('SELECT * FROM bots WHERE id = ?', (bot_id,)).fetchone()
            return dict(bot) if bot else None
    except:
        return None

def delete_bot(bot_id, user_id):
    try:
        with get_db() as conn:
            bot = conn.execute('SELECT * FROM bots WHERE id = ? AND user_id = ?', (bot_id, user_id)).fetchone()
            if not bot:
                return False
            
            if bot['pid']:
                try:
                    os.kill(bot['pid'], signal.SIGTERM)
                except:
                    pass
            
            if bot['file_path'] and os.path.exists(bot['file_path']):
                os.remove(bot['file_path'])
            
            if bot['folder_path'] and os.path.exists(bot['folder_path']):
                shutil.rmtree(bot['folder_path'])
            
            conn.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
            conn.execute('UPDATE users SET bots_count = bots_count - 1 WHERE user_id = ?', (user_id,))
            conn.commit()
            return True
    except:
        return False

def extract_token_from_code(code):
    patterns = [
        r'token\s*=\s*["\']([^"\']+)["\']',
        r'TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'API_TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'BOT_TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'bot\s*=\s*telebot\.TeleBot\(\s*["\']([^"\']+)["\']\s*\)'
    ]
    for pattern in patterns:
        match = re.search(pattern, code, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

def add_bot(user_id, bot_id, token, name, username, file_path, folder_path=None, pid=None):
    try:
        with get_db() as conn:
            now = datetime.now().isoformat()
            status = 'running' if pid else 'stopped'
            
            conn.execute('''
                INSERT INTO bots 
                (id, user_id, token, name, username, file_path, folder_path, pid, status, created_at, last_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (bot_id, user_id, token, name, username, file_path, folder_path, pid, status, now, now))
            
            conn.execute('UPDATE users SET bots_count = bots_count + 1, last_active = ? WHERE user_id = ?', (now, user_id))
            conn.commit()
            return True
    except:
        return False

def add_wallet_balance(user_id, amount):
    try:
        with get_db() as conn:
            user = conn.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,)).fetchone()
            new_balance = (user['balance'] if user else 0) + amount
            conn.execute('UPDATE users SET balance = ? WHERE user_id = ?', (new_balance, user_id))
            conn.commit()
            return new_balance
    except:
        return None

# ==================== موتور اجرای پیشرفته ====================
class AdvancedBotEngine:
    def __init__(self):
        self.running_processes = {}
        self.lock = threading.Lock()
    
    def install_library(self, lib_name):
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", lib_name, "--quiet"],
                capture_output=True,
                text=True,
                timeout=60
            )
            return result.returncode == 0
        except:
            return False
    
    def detect_requirements(self, code):
        imports = set()
        lines = code.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('import '):
                parts = line.split()
                if len(parts) > 1:
                    lib = parts[1].split('.')[0]
                    if lib not in ['os', 'sys', 'time', 'datetime', 'json', 're', 'math', 'typing']:
                        imports.add(lib)
            elif line.startswith('from '):
                parts = line.split()
                if len(parts) > 1:
                    lib = parts[1].split('.')[0]
                    if lib not in ['os', 'sys', 'time', 'datetime', 'json', 're', 'math', 'typing']:
                        imports.add(lib)
        return list(imports)
    
    def run_bot(self, bot_id, user_id, code, token):
        result = {'success': False, 'pid': None, 'error': None, 'installed': []}
        
        try:
            requirements = self.detect_requirements(code)
            installed = []
            
            for lib in requirements:
                try:
                    __import__(lib)
                except ImportError:
                    if self.install_library(lib):
                        installed.append(lib)
            
            result['installed'] = installed
            
            bot_dir = os.path.join(RUNNING_DIR, bot_id)
            os.makedirs(bot_dir, exist_ok=True)
            
            code_path = os.path.join(bot_dir, 'bot.py')
            with open(code_path, 'w', encoding='utf-8') as f:
                f.write(code)
            
            log_file = os.path.join(bot_dir, 'bot.log')
            
            process = subprocess.Popen(
                [sys.executable, code_path],
                stdout=open(log_file, 'a'),
                stderr=subprocess.STDOUT,
                cwd=bot_dir,
                start_new_session=True
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
        with self.lock:
            if bot_id in self.running_processes:
                try:
                    process = self.running_processes[bot_id]['process']
                    process.terminate()
                    time.sleep(1)
                    if process.poll() is None:
                        process.kill()
                    del self.running_processes[bot_id]
                    return True
                except:
                    pass
        return False
    
    def get_status(self, bot_id):
        with self.lock:
            if bot_id in self.running_processes:
                process = self.running_processes[bot_id]['process']
                if process.poll() is None:
                    try:
                        p = psutil.Process(process.pid)
                        return {
                            'running': True,
                            'pid': process.pid,
                            'cpu': p.cpu_percent(),
                            'memory': p.memory_percent(),
                            'uptime': int(time.time() - self.running_processes[bot_id]['start_time'])
                        }
                    except:
                        return {'running': True, 'pid': process.pid}
        return {'running': False}

bot_engine = AdvancedBotEngine()

# ==================== کتابخانه منیجر ====================
class LibraryManager:
    def __init__(self):
        self.common_libs = {
            'requests': 'requests',
            'numpy': 'numpy',
            'pandas': 'pandas',
            'flask': 'flask',
            'django': 'django',
            'pillow': 'Pillow',
            'beautifulsoup4': 'beautifulsoup4',
            'selenium': 'selenium',
            'pyTelegramBotAPI': 'pyTelegramBotAPI',
            'aiogram': 'aiogram',
            'aiohttp': 'aiohttp',
            'fastapi': 'fastapi',
            'jdatetime': 'jdatetime',
            'cryptography': 'cryptography',
            'loguru': 'loguru'
        }
    
    def install(self, lib_name, chat_id, message_id=None):
        try:
            msg = bot.send_message(chat_id, f"🔄 در حال نصب {lib_name}...")
            
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", lib_name, "--quiet"],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                version = subprocess.run([sys.executable, "-m", "pip", "show", lib_name],
                                        capture_output=True, text=True, timeout=10)
                ver = "نامشخص"
                for line in version.stdout.split('\n'):
                    if line.startswith('Version:'):
                        ver = line.split(':', 1)[1].strip()
                        break
                
                with get_db() as conn:
                    conn.execute('INSERT OR IGNORE INTO installed_libraries (name, version, installed_at) VALUES (?, ?, ?)',
                                (lib_name, ver, datetime.now().isoformat()))
                    conn.commit()
                
                bot.edit_message_text(f"✅ {lib_name} نسخه {ver} نصب شد!", chat_id, msg.message_id)
                return True
            else:
                error = result.stderr[:200] if result.stderr else "خطا"
                bot.edit_message_text(f"❌ خطا: {error}", chat_id, msg.message_id)
                return False
        except subprocess.TimeoutExpired:
            bot.send_message(chat_id, f"❌ زمان نصب تمام شد!")
            return False
        except Exception as e:
            bot.send_message(chat_id, f"❌ خطا: {str(e)}")
            return False

library_manager = LibraryManager()

# ==================== مدیریت پوشه‌ها ====================
class FolderManager:
    def create_folder(self, user_id, folder_name, parent_id=None):
        folder_path = os.path.join(FOLDERS_DIR, str(user_id), folder_name)
        if parent_id:
            with get_db() as conn:
                parent = conn.execute('SELECT folder_path FROM user_folders WHERE id = ?', (parent_id,)).fetchone()
                if parent:
                    folder_path = os.path.join(parent['folder_path'], folder_name)
        
        if os.path.exists(folder_path):
            return None, "پوشه وجود دارد"
        
        os.makedirs(folder_path, exist_ok=True)
        folder_id = hashlib.md5(f"{user_id}_{folder_name}_{time.time()}".encode()).hexdigest()[:12]
        
        with get_db() as conn:
            conn.execute('INSERT INTO user_folders (id, user_id, folder_name, folder_path, parent_id, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                        (folder_id, user_id, folder_name, folder_path, parent_id, datetime.now().isoformat()))
            conn.commit()
        
        return folder_id, "پوشه ساخته شد"
    
    def add_file(self, folder_id, file_name, content):
        with get_db() as conn:
            folder = conn.execute('SELECT folder_path FROM user_folders WHERE id = ?', (folder_id,)).fetchone()
            if not folder:
                return False, "پوشه یافت نشد"
            
            file_path = os.path.join(folder['folder_path'], file_name)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            conn.execute('INSERT INTO folder_files (folder_id, file_name, file_path, content, added_at) VALUES (?, ?, ?, ?, ?)',
                        (folder_id, file_name, file_path, content[:1000], datetime.now().isoformat()))
            conn.commit()
            return True, "فایل اضافه شد"
    
    def get_files(self, folder_id):
        with get_db() as conn:
            files = conn.execute('SELECT file_name, added_at FROM folder_files WHERE folder_id = ?', (folder_id,)).fetchall()
            return [dict(f) for f in files]
    
    def read_file(self, folder_id, file_name):
        with get_db() as conn:
            file_info = conn.execute('SELECT file_path FROM folder_files WHERE folder_id = ? AND file_name = ?', (folder_id, file_name)).fetchone()
            if file_info and os.path.exists(file_info['file_path']):
                with open(file_info['file_path'], 'r', encoding='utf-8') as f:
                    return f.read()
        return None

folder_manager = FolderManager()

# ==================== منوی اصلی ====================
def get_main_menu(is_admin=False):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    
    buttons = [
        types.KeyboardButton('🤖 ساخت ربات جدید'),
        types.KeyboardButton('📋 ربات‌های من'),
        types.KeyboardButton('🔄 توقف/اجرا'),
        types.KeyboardButton('🗑 حذف ربات'),
        types.KeyboardButton('📁 مدیریت پوشه‌ها'),
        types.KeyboardButton('💰 کیف پول'),
        types.KeyboardButton('👥 دعوت دوستان'),
        types.KeyboardButton('💸 درخواست برداشت'),
        types.KeyboardButton('📦 کتابخانه‌ها'),
        types.KeyboardButton('📚 راهنما'),
        types.KeyboardButton('📊 آمار'),
        types.KeyboardButton('📞 پشتیبانی')
    ]
    
    if is_admin:
        buttons.extend([
            types.KeyboardButton('👑 پنل مدیریت'),
            types.KeyboardButton('📢 پیام همگانی')
        ])
    
    markup.add(*buttons)
    return markup

# ==================== دستور start ====================
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
        try:
            with get_db() as conn:
                referrer = conn.execute('SELECT user_id FROM users WHERE referral_code = ?', (ref_code,)).fetchone()
                if referrer and referrer['user_id'] != user_id:
                    referred_by = referrer['user_id']
                    try:
                        bot.send_message(referred_by, f"🎉 {first_name} با لینک شما وارد شد!")
                    except:
                        pass
        except:
            pass
    
    create_user(user_id, username, first_name, last_name, referred_by)
    user = get_user(user_id)
    bot_username = bot.get_me().username
    referral_link = f"https://t.me/{bot_username}?start={user['referral_code']}"
    
    text = f"""🚀 **خوش آمدید {first_name}**!

👤 شناسه: `{user_id}`
🎁 کد معرف: `{user['referral_code']}`
🔗 لینک دعوت: `{referral_link}`
💰 موجودی: {user['balance']:,} تومان

✅ **اشتراک شما فعال است!**
📌 حداکثر ۳ ربات
🔓 ربات‌های شما همیشه فعال هستند

📤 از دکمه `🤖 ساخت ربات جدید` استفاده کنید."""
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📋 کپی لینک", callback_data=f"copy_{user['referral_code']}"))
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=get_main_menu(user_id in ADMIN_IDS))

@bot.callback_query_handler(func=lambda call: call.data.startswith('copy_'))
def copy_link(call):
    code = call.data.replace('copy_', '')
    link = f"https://t.me/{bot.get_me().username}?start={code}"
    bot.answer_callback_query(call.id, f"✅ لینک کپی شد!\n{link}", show_alert=True)

# ==================== کیف پول ====================
@bot.message_handler(func=lambda m: m.text == '💰 کیف پول')
def wallet(message):
    user = get_user(message.from_user.id)
    if not user:
        bot.send_message(message.chat.id, "❌ /start بزنید")
        return
    
    can_create, max_bots, current_bots = check_bot_limit(message.from_user.id)
    
    text = f"💰 **کیف پول شما**\n\n"
    text += f"👤 {user['first_name']}\n"
    text += f"💵 موجودی: {user['balance']:,} تومان\n"
    text += f"👥 دعوت‌ها: {user['referrals_count']}\n"
    text += f"🎁 تایید شده: {user['verified_referrals']}\n"
    text += f"🤖 ربات‌ها: {current_bots}/{max_bots}\n\n"
    text += f"💡 هر ۵ دعوت = ۱ ربات اضافه"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== دعوت دوستان ====================
@bot.message_handler(func=lambda m: m.text == '👥 دعوت دوستان')
def invite(message):
    user = get_user(message.from_user.id)
    bot_username = bot.get_me().username
    link = f"https://t.me/{bot_username}?start={user['referral_code']}"
    
    text = f"👥 **دعوت دوستان**\n\n"
    text += f"🎁 کد: `{user['referral_code']}`\n"
    text += f"🔗 لینک: `{link}`\n"
    text += f"📊 دعوت‌ها: {user['referrals_count']}\n"
    text += f"✅ تایید شده: {user['verified_referrals']}\n\n"
    text += f"💰 هر دعوت: {user['verified_referrals'] * 5000:,} تومان پاداش\n"
    text += f"💡 هر ۵ دعوت = ۱ ربات اضافه"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📋 کپی لینک", callback_data=f"copy_{user['referral_code']}"))
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

# ==================== درخواست برداشت ====================
@bot.message_handler(func=lambda m: m.text == '💸 درخواست برداشت')
def withdraw_request(message):
    user = get_user(message.from_user.id)
    
    if user['balance'] < 50000:
        bot.send_message(message.chat.id, f"❌ موجودی کمتر از ۵۰,۰۰۰ تومان")
        return
    
    msg = bot.send_message(message.chat.id, "💳 شماره کارت (۱۶ رقم):")
    bot.register_next_step_handler(msg, process_withdraw_card, user)

def process_withdraw_card(message, user):
    card = message.text.strip().replace(' ', '')
    if len(card) != 16 or not card.isdigit():
        bot.reply_to(message, "❌ شماره کارت نامعتبر!")
        return
    
    msg = bot.send_message(message.chat.id, "👤 نام صاحب کارت:")
    bot.register_next_step_handler(msg, process_withdraw_holder, user, card)

def process_withdraw_holder(message, user, card):
    holder = message.text.strip()
    
    with get_db() as conn:
        conn.execute('''
            INSERT INTO withdraw_requests (user_id, amount, card_number, card_holder, created_at, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
        ''', (user['user_id'], user['balance'], card, holder, datetime.now().isoformat()))
        conn.execute('UPDATE users SET balance = 0 WHERE user_id = ?', (user['user_id'],))
        conn.commit()
    
    bot.reply_to(message, f"✅ درخواست برداشت {user['balance']:,} تومان ثبت شد!")
    
    for admin_id in ADMIN_IDS:
        bot.send_message(admin_id, f"💰 درخواست برداشت\n👤 {user['first_name']}\n🆔 {user['user_id']}\n💰 {user['balance']:,} تومان")

# ==================== مدیریت پوشه‌ها ====================
@bot.message_handler(func=lambda m: m.text == '📁 مدیریت پوشه‌ها')
def manage_folders(message):
    user_id = message.from_user.id
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📁➕ ساخت پوشه جدید", callback_data="create_folder"),
        types.InlineKeyboardButton("📂 لیست پوشه‌ها", callback_data="list_folders")
    )
    
    bot.send_message(message.chat.id, "📁 **مدیریت پوشه‌ها**\n\nمی‌توانید فایل‌های خود را در پوشه‌ها سازماندهی کنید.", 
                    parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "create_folder")
def create_folder_prompt(call):
    msg = bot.send_message(call.message.chat.id, "📁 **نام پوشه:**\n(فقط حروف انگلیسی)")
    bot.register_next_step_handler(msg, process_create_folder)
    bot.answer_callback_query(call.id)

def process_create_folder(message):
    user_id = message.from_user.id
    name = message.text.strip()
    
    if not re.match(r'^[a-zA-Z0-9_\-]+$', name):
        bot.reply_to(message, "❌ نام نامعتبر!")
        return
    
    folder_id, result = folder_manager.create_folder(user_id, name)
    if folder_id:
        bot.reply_to(message, f"✅ {result}\n🆔 `{folder_id}`", parse_mode='Markdown')
    else:
        bot.reply_to(message, f"❌ {result}")

@bot.callback_query_handler(func=lambda call: call.data == "list_folders")
def list_folders(call):
    user_id = call.from_user.id
    
    with get_db() as conn:
        folders = conn.execute('SELECT id, folder_name, created_at FROM user_folders WHERE user_id = ?', (user_id,)).fetchall()
    
    if not folders:
        bot.send_message(call.message.chat.id, "📂 پوشه‌ای ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for f in folders:
        markup.add(types.InlineKeyboardButton(f"📂 {f['folder_name']}", callback_data=f"view_folder_{f['id']}"))
    
    bot.edit_message_text("📂 **پوشه‌های شما:**", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('view_folder_'))
def view_folder(call):
    folder_id = call.data.replace('view_folder_', '')
    files = folder_manager.get_files(folder_id)
    
    with get_db() as conn:
        folder = conn.execute('SELECT folder_name FROM user_folders WHERE id = ?', (folder_id,)).fetchone()
    
    if not folder:
        bot.answer_callback_query(call.id, "پوشه یافت نشد!")
        return
    
    text = f"📁 **{folder['folder_name']}**\n🆔 `{folder_id}`\n📄 فایل‌ها: {len(files)}\n\n"
    
    if files:
        text += "**فایل‌ها:**\n"
        for f in files:
            text += f"• `{f['file_name']}`\n"
    else:
        text += "📂 فایلی وجود ندارد"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("📄 افزودن فایل", callback_data=f"add_file_{folder_id}"))
    markup.add(types.InlineKeyboardButton("▶️ اجرا", callback_data=f"run_folder_{folder_id}"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="list_folders"))
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('add_file_'))
def add_file_prompt(call):
    folder_id = call.data.replace('add_file_', '')
    msg = bot.send_message(call.message.chat.id, "📄 **نام فایل:**\n(مثال: main.py)")
    bot.register_next_step_handler(msg, process_add_file_name, folder_id)
    bot.answer_callback_query(call.id)

def process_add_file_name(message, folder_id):
    file_name = message.text.strip()
    if not file_name.endswith('.py'):
        bot.reply_to(message, "❌ فقط فایل‌های .py مجاز!")
        return
    
    msg = bot.send_message(message.chat.id, f"📝 **محتوای {file_name} را ارسال کنید:**")
    bot.register_next_step_handler(msg, process_add_file_content, folder_id, file_name)

def process_add_file_content(message, folder_id, file_name):
    content = message.text
    success, result = folder_manager.add_file(folder_id, file_name, content)
    bot.reply_to(message, f"✅ {result}" if success else f"❌ {result}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('run_folder_'))
def run_folder(call):
    user_id = call.from_user.id
    folder_id = call.data.replace('run_folder_', '')
    
    code = folder_manager.read_file(folder_id, 'main.py')
    if not code:
        bot.answer_callback_query(call.id, "فایل main.py یافت نشد!", show_alert=True)
        return
    
    token = extract_token_from_code(code)
    if not token:
        bot.answer_callback_query(call.id, "توکن پیدا نشد!", show_alert=True)
        return
    
    try:
        resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        if resp.status_code != 200:
            bot.answer_callback_query(call.id, "توکن نامعتبر!", show_alert=True)
            return
        bot_info = resp.json()['result']
    except:
        bot.answer_callback_query(call.id, "خطا در بررسی توکن!", show_alert=True)
        return
    
    can_create, max_bots, current_bots = check_bot_limit(user_id)
    if not can_create:
        bot.answer_callback_query(call.id, f"حداکثر {max_bots} ربات!", show_alert=True)
        return
    
    bot_id = hashlib.md5(f"{user_id}_{token}_{time.time()}".encode()).hexdigest()[:12]
    result = bot_engine.run_bot(bot_id, user_id, code, token)
    
    if result['success']:
        add_bot(user_id, bot_id, token, bot_info['first_name'], bot_info['username'], None, None, result['pid'])
        bot.answer_callback_query(call.id, "✅ ربات اجرا شد!", show_alert=True)
        bot.edit_message_text(f"✅ ربات {bot_info['first_name']} اجرا شد!", call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, f"❌ {result['error'][:50]}", show_alert=True)

# ==================== ساخت ربات جدید ====================
@bot.message_handler(func=lambda m: m.text == '🤖 ساخت ربات جدید')
def new_bot(message):
    user_id = message.from_user.id
    
    can_create, max_bots, current_bots = check_bot_limit(user_id)
    if not can_create:
        bot.send_message(message.chat.id, f"❌ شما به حداکثر {max_bots} ربات رسیده‌اید!")
        return
    
    bot.send_message(message.chat.id, "📤 فایل `.py` یا `.zip` خود را ارسال کنید\n✅ حداکثر ۵۰ مگابایت\n✅ توکن داخل کد باشد")

# ==================== آپلود فایل ====================
@bot.message_handler(content_types=['document'])
def handle_build_file(message):
    user_id = message.from_user.id
    file_name = message.document.file_name
    
    if not (file_name.endswith('.py') or file_name.endswith('.zip')):
        bot.reply_to(message, "❌ فقط فایل‌های .py یا .zip مجاز هستند!")
        return
    
    if message.document.file_size > 50 * 1024 * 1024:
        bot.reply_to(message, "❌ حجم بیشتر از ۵۰ مگابایت!")
        return
    
    status_msg = bot.reply_to(message, "🔄 در حال پردازش...")
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        user_dir = os.path.join(FILES_DIR, str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        file_path = os.path.join(user_dir, f"{int(time.time())}_{file_name}")
        
        with open(file_path, 'wb') as f:
            f.write(downloaded)
        
        # استخراج کد
        code = ""
        if file_name.endswith('.zip'):
            extract_dir = os.path.join(FILES_DIR, str(user_id), f"extract_{int(time.time())}")
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(file_path, 'r') as zf:
                zf.extractall(extract_dir)
            
            for root, _, files in os.walk(extract_dir):
                for f in files:
                    if f.endswith('.py'):
                        with open(os.path.join(root, f), 'r', encoding='utf-8', errors='ignore') as cf:
                            code = cf.read()
                            break
                if code:
                    break
            shutil.rmtree(extract_dir, ignore_errors=True)
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
        
        if not code:
            bot.edit_message_text("❌ فایل پایتون پیدا نشد!", message.chat.id, status_msg.message_id)
            return
        
        token = extract_token_from_code(code)
        if not token:
            bot.edit_message_text("❌ توکن پیدا نشد!", message.chat.id, status_msg.message_id)
            return
        
        try:
            resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
            if resp.status_code != 200:
                bot.edit_message_text("❌ توکن نامعتبر!", message.chat.id, status_msg.message_id)
                return
            bot_info = resp.json()['result']
        except:
            bot.edit_message_text("❌ خطا در بررسی توکن!", message.chat.id, status_msg.message_id)
            return
        
        can_create, max_bots, current_bots = check_bot_limit(user_id)
        if not can_create:
            bot.edit_message_text(f"❌ حداکثر {max_bots} ربات!", message.chat.id, status_msg.message_id)
            return
        
        bot_id = hashlib.md5(f"{user_id}_{token}_{time.time()}".encode()).hexdigest()[:12]
        result = bot_engine.run_bot(bot_id, user_id, code, token)
        
        if result['success']:
            add_bot(user_id, bot_id, token, bot_info['first_name'], bot_info['username'], file_path, None, result['pid'])
            
            reply = f"✅ **ربات ساخته شد!**\n\n"
            reply += f"🤖 نام: {bot_info['first_name']}\n"
            reply += f"🔗 t.me/{bot_info['username']}\n"
            reply += f"🆔 `{bot_id}`\n\n"
            
            if result.get('installed'):
                reply += f"📦 کتابخانه‌ها: {', '.join(result['installed'])}\n"
            
            bot.edit_message_text(reply, message.chat.id, status_msg.message_id, parse_mode='Markdown')
        else:
            bot.edit_message_text(f"❌ خطا: {result['error'][:200]}", message.chat.id, status_msg.message_id)
        
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)[:200]}", message.chat.id, status_msg.message_id)

# ==================== ربات‌های من ====================
@bot.message_handler(func=lambda m: m.text == '📋 ربات‌های من')
def my_bots(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما رباتی ندارید!")
        return
    
    for b in bots[:10]:
        status = bot_engine.get_status(b['id'])
        emoji = "🟢" if status['running'] else "🔴"
        
        text = f"{emoji} **{b['name']}**\n"
        text += f"🔗 t.me/{b['username']}\n"
        text += f"🆔 `{b['id'][:8]}`\n"
        if status['running']:
            text += f"💻 CPU: {status.get('cpu', 0):.1f}%\n"
            text += f"🧠 RAM: {status.get('memory', 0):.1f}%\n"
        text += f"📅 {b['created_at'][:10]}"
        
        bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== توقف/اجرا ====================
@bot.message_handler(func=lambda m: m.text == '🔄 توقف/اجرا')
def toggle_prompt(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    
    if not bots:
        bot.send_message(message.chat.id, "📋 رباتی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        status = bot_engine.get_status(b['id'])
        emoji = "🟢" if status['running'] else "🔴"
        action = "توقف" if status['running'] else "اجرا"
        markup.add(types.InlineKeyboardButton(f"{emoji} {b['name']} - {action}", callback_data=f"toggle_{b['id']}"))
    
    bot.send_message(message.chat.id, "🔄 انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_'))
def toggle_bot(call):
    bot_id = call.data.replace('toggle_', '')
    bot_info = get_bot(bot_id)
    
    if not bot_info or bot_info['user_id'] != call.from_user.id:
        bot.answer_callback_query(call.id, "❌ یافت نشد!")
        return
    
    is_running = bot_engine.get_status(bot_id)['running']
    
    if is_running:
        if bot_engine.stop_bot(bot_id):
            with get_db() as conn:
                conn.execute('UPDATE bots SET status = "stopped" WHERE id = ?', (bot_id,))
                conn.commit()
            bot.answer_callback_query(call.id, "✅ ربات متوقف شد!")
        else:
            bot.answer_callback_query(call.id, "❌ خطا!")
    else:
        if os.path.exists(bot_info['file_path']):
            with open(bot_info['file_path'], 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
            result = bot_engine.run_bot(bot_id, call.from_user.id, code, bot_info['token'])
            if result['success']:
                with get_db() as conn:
                    conn.execute('UPDATE bots SET status = "running", pid = ?, execution_count = execution_count + 1 WHERE id = ?',
                                (result['pid'], bot_id))
                    conn.commit()
                bot.answer_callback_query(call.id, "✅ ربات اجرا شد!")
            else:
                bot.answer_callback_query(call.id, f"❌ {result['error'][:50]}")
        else:
            bot.answer_callback_query(call.id, "❌ فایل یافت نشد!")
    
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== حذف ربات ====================
@bot.message_handler(func=lambda m: m.text == '🗑 حذف ربات')
def delete_prompt(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    
    if not bots:
        bot.send_message(message.chat.id, "📋 رباتی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        markup.add(types.InlineKeyboardButton(f"🗑 {b['name']}", callback_data=f"delete_{b['id']}"))
    
    bot.send_message(message.chat.id, "🗑 انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
def confirm_delete(call):
    bot_id = call.data.replace('delete_', '')
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ بله", callback_data=f"confirm_del_{bot_id}"),
              types.InlineKeyboardButton("❌ انصراف", callback_data="cancel_del"))
    bot.edit_message_text("⚠️ اطمینان دارید؟", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_del_'))
def do_delete(call):
    bot_id = call.data.replace('confirm_del_', '')
    if delete_bot(bot_id, call.from_user.id):
        bot.edit_message_text("✅ حذف شد!", call.message.chat.id, call.message.message_id)
    else:
        bot.edit_message_text("❌ خطا!", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "cancel_del")
def cancel_delete(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== کتابخانه‌ها ====================
@bot.message_handler(func=lambda m: m.text == '📦 کتابخانه‌ها')
def libraries_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    libs = [
        ('requests', 'requests'), ('numpy', 'numpy'), ('pandas', 'pandas'),
        ('flask', 'flask'), ('django', 'django'), ('pillow', 'Pillow'),
        ('beautifulsoup4', 'beautifulsoup4'), ('selenium', 'selenium'),
        ('pyTelegramBotAPI', 'pyTelegramBotAPI'), ('aiogram', 'aiogram'),
        ('jdatetime', 'jdatetime'), ('🔧 دستی', 'custom')
    ]
    
    for name, data in libs:
        markup.add(types.InlineKeyboardButton(name, callback_data=f"lib_{data}"))
    
    markup.add(types.InlineKeyboardButton("✅ نصب شده‌ها", callback_data="lib_installed"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="lib_back"))
    
    bot.send_message(message.chat.id, "📦 **کتابخانه مورد نظر را انتخاب کنید:**", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lib_'))
def library_callback(call):
    lib = call.data.replace('lib_', '')
    
    if lib == 'custom':
        msg = bot.send_message(call.message.chat.id, "🔧 نام کتابخانه:")
        bot.register_next_step_handler(msg, install_custom_library)
        bot.answer_callback_query(call.id)
        return
    elif lib == 'installed':
        show_installed_libraries(call)
        return
    elif lib == 'back':
        libraries_menu(call.message)
        return
    
    bot.answer_callback_query(call.id, f"🔄 در حال نصب {lib}...")
    library_manager.install(lib, call.message.chat.id)

def install_custom_library(message):
    lib = message.text.strip()
    library_manager.install(lib, message.chat.id)

def show_installed_libraries(call):
    with get_db() as conn:
        libs = conn.execute('SELECT name, version, installed_at FROM installed_libraries ORDER BY installed_at DESC').fetchall()
    
    if not libs:
        bot.edit_message_text("📦 کتابخانه‌ای نصب نشده!", call.message.chat.id, call.message.message_id)
        return
    
    text = "✅ **کتابخانه‌های نصب شده**\n\n"
    for lib in libs:
        text += f"• `{lib['name']}` - {lib['version']}\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="lib_back"))
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)

# ==================== راهنما ====================
@bot.message_handler(func=lambda m: m.text == '📚 راهنما')
def guide(message):
    text = """📚 **راهنمای ربات مادر**

**🎯 ساخت ربات:**
• از دکمه `🤖 ساخت ربات جدید` استفاده کنید
• فایل .py یا .zip خود را ارسال کنید
• توکن داخل کد باشد

**📁 پوشه‌ها:**
• می‌توانید فایل‌ها را در پوشه‌ها سازماندهی کنید
• فایل اصلی باید main.py باشد

**📦 کتابخانه‌ها:**
• کتابخانه‌های مورد نیاز خودکار نصب می‌شوند
• می‌توانید کتابخانه دلخواه نصب کنید

**👥 دعوت دوستان:**
• هر دعوت ۵,۰۰۰ تومان پاداش
• هر ۵ دعوت = ۱ ربات اضافه

**🆘 پشتیبانی:** @shahraghee13"""
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== آمار ====================
@bot.message_handler(func=lambda m: m.text == '📊 آمار')
def stats(message):
    with get_db() as conn:
        users = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        bots = conn.execute('SELECT COUNT(*) FROM bots').fetchone()[0]
        running = sum(1 for b in get_user_bots(message.from_user.id) if bot_engine.get_status(b['id'])['running'])
        total_wallet = conn.execute('SELECT SUM(balance) FROM users').fetchone()[0] or 0
    
    text = f"📊 **آمار**\n\n"
    text += f"👥 کاربران: {users}\n"
    text += f"🤖 ربات‌ها: {bots}\n"
    text += f"🟢 فعال: {running}\n"
    text += f"💰 کیف پول کل: {total_wallet:,} تومان\n"
    text += f"📌 حداکثر ربات: ۳"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== پشتیبانی ====================
@bot.message_handler(func=lambda m: m.text == '📞 پشتیبانی')
def support(message):
    bot.send_message(message.chat.id, "📞 **پشتیبانی:** @shahraghee13", parse_mode='Markdown')

# ==================== پنل مدیریت ====================
@bot.message_handler(func=lambda m: m.text == '👑 پنل مدیریت')
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📸 فیش‌ها", callback_data="admin_receipts"),
        types.InlineKeyboardButton("💰 برداشت‌ها", callback_data="admin_withdraws"),
        types.InlineKeyboardButton("👥 کاربران", callback_data="admin_users"),
        types.InlineKeyboardButton("🎁 فعال‌سازی", callback_data="admin_activate"),
        types.InlineKeyboardButton("📊 آمار کامل", callback_data="admin_stats"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    bot.send_message(message.chat.id, "👑 **پنل مدیریت**", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_receipts")
def admin_receipts(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    with get_db() as conn:
        receipts = conn.execute('SELECT * FROM receipts WHERE status = "pending" ORDER BY created_at DESC').fetchall()
    
    if not receipts:
        bot.send_message(call.message.chat.id, "📸 فیشی وجود ندارد")
        return
    
    for r in receipts:
        text = f"📸 فیش {r['id']}\n👤 {r['user_id']}\n💰 {r['amount']:,} تومان\n🆔 {r['payment_code']}"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_{r['id']}"),
                  types.InlineKeyboardButton("❌ رد", callback_data=f"reject_{r['id']}"))
        
        if os.path.exists(r['receipt_path']):
            with open(r['receipt_path'], 'rb') as f:
                bot.send_photo(call.message.chat.id, f, caption=text, reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_'))
def approve_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    rid = int(call.data.replace('approve_', ''))
    
    with get_db() as conn:
        receipt = conn.execute('SELECT user_id FROM receipts WHERE id = ?', (rid,)).fetchone()
        if receipt:
            conn.execute('UPDATE receipts SET status = "approved", reviewed_by = ?, reviewed_at = ? WHERE id = ?',
                        (call.from_user.id, datetime.now().isoformat(), rid))
            conn.execute('UPDATE users SET payment_status = "approved", payment_date = ? WHERE user_id = ?',
                        (datetime.now().isoformat(), receipt['user_id']))
            conn.commit()
            
            try:
                bot.send_message(receipt['user_id'], "✅ **فیش شما تایید شد!**\nاکنون می‌توانید ربات بسازید.", parse_mode='Markdown')
            except:
                pass
    
    bot.answer_callback_query(call.id, "✅ تایید شد!")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_'))
def reject_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    rid = int(call.data.replace('reject_', ''))
    
    with get_db() as conn:
        receipt = conn.execute('SELECT user_id FROM receipts WHERE id = ?', (rid,)).fetchone()
        if receipt:
            conn.execute('UPDATE receipts SET status = "rejected", reviewed_by = ?, reviewed_at = ? WHERE id = ?',
                        (call.from_user.id, datetime.now().isoformat(), rid))
            conn.commit()
            
            try:
                bot.send_message(receipt['user_id'], "❌ **فیش شما رد شد!**\nبا پشتیبانی تماس بگیرید: @shahraghee13", parse_mode='Markdown')
            except:
                pass
    
    bot.answer_callback_query(call.id, "❌ رد شد!")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_withdraws")
def admin_withdraws(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    with get_db() as conn:
        withdraws = conn.execute('SELECT * FROM withdraw_requests WHERE status = "pending" ORDER BY created_at DESC').fetchall()
    
    if not withdraws:
        bot.send_message(call.message.chat.id, "💰 درخواستی وجود ندارد")
        return
    
    for w in withdraws:
        text = f"💰 برداشت\n👤 {w['user_id']}\n💰 {w['amount']:,} تومان\n💳 {w['card_number']}\n👤 {w['card_holder']}"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_wd_{w['id']}"))
        bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_wd_'))
def approve_withdraw(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    wid = int(call.data.replace('approve_wd_', ''))
    
    with get_db() as conn:
        conn.execute('UPDATE withdraw_requests SET status = "approved", processed_at = ? WHERE id = ?',
                    (datetime.now().isoformat(), wid))
        conn.commit()
    
    bot.answer_callback_query(call.id, "✅ تایید شد!")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_users")
def admin_users(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    with get_db() as conn:
        users = conn.execute('SELECT user_id, first_name, bots_count, balance, created_at FROM users ORDER BY created_at DESC LIMIT 20').fetchall()
    
    text = "👥 **۲۰ کاربر آخر**\n\n"
    for u in users:
        text += f"👤 {u['first_name']}\n🆔 {u['user_id']}\n🤖 {u['bots_count']} ربات | 💰 {u['balance']:,} تومان\n📅 {u['created_at'][:10]}\n\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "admin_activate")
def admin_activate_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(call.message.chat.id, "🎁 **آیدی کاربر را وارد کنید:**")
    bot.register_next_step_handler(msg, process_admin_activate)
    bot.answer_callback_query(call.id)

def process_admin_activate(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        user_id = int(message.text.strip())
        with get_db() as conn:
            conn.execute('UPDATE users SET payment_status = "approved", payment_date = ? WHERE user_id = ?',
                        (datetime.now().isoformat(), user_id))
            conn.commit()
        
        bot.reply_to(message, f"✅ اشتراک {user_id} فعال شد!")
        bot.send_message(user_id, "✅ اشتراک شما توسط ادمین فعال شد!\nحالا می‌توانید ربات بسازید.")
    except:
        bot.reply_to(message, "❌ خطا!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_stats(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    with get_db() as conn:
        users = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        paid = conn.execute('SELECT COUNT(*) FROM users WHERE payment_status = "approved"').fetchone()[0]
        bots = conn.execute('SELECT COUNT(*) FROM bots').fetchone()[0]
        receipts = conn.execute('SELECT COUNT(*) FROM receipts').fetchone()[0]
        pending = conn.execute('SELECT COUNT(*) FROM receipts WHERE status = "pending"').fetchone()[0]
        total_amount = conn.execute('SELECT SUM(amount) FROM receipts WHERE status = "approved"').fetchone()[0] or 0
        total_wallet = conn.execute('SELECT SUM(balance) FROM users').fetchone()[0] or 0
    
    text = f"📊 **آمار کامل**\n\n"
    text += f"👥 کاربران: {users}\n"
    text += f"✅ پرداخت کرده: {paid}\n"
    text += f"🤖 ربات‌ها: {bots}\n"
    text += f"📸 فیش‌ها: {receipts}\n"
    text += f"⏳ در انتظار: {pending}\n"
    text += f"💰 درآمد: {total_amount:,} تومان\n"
    text += f"💵 کیف پول: {total_wallet:,} تومان"
    
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    admin_panel(call.message)

# ==================== پیام همگانی ====================
@bot.message_handler(func=lambda m: m.text == '📢 پیام همگانی')
def broadcast_prompt(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(message.chat.id, "📢 **متن پیام:**")
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    text = message.text
    
    with get_db() as conn:
        users = conn.execute('SELECT user_id FROM users').fetchall()
    
    sent = 0
    status_msg = bot.reply_to(message, f"🔄 ارسال به {len(users)} کاربر...")
    
    for user in users:
        try:
            bot.send_message(user['user_id'], f"📢 **پیام همگانی**\n\n{text}", parse_mode='Markdown')
            sent += 1
            time.sleep(0.05)
        except:
            pass
    
    bot.edit_message_text(f"✅ به {sent} کاربر ارسال شد!", message.chat.id, status_msg.message_id)

# ==================== مانیتورینگ ====================
def monitor_bots():
    while True:
        try:
            with get_db() as conn:
                running_bots = conn.execute('SELECT id FROM bots WHERE status = "running"').fetchall()
                for bot in running_bots:
                    if not bot_engine.get_status(bot['id'])['running']:
                        conn.execute('UPDATE bots SET status = "stopped" WHERE id = ?', (bot['id'],))
                        conn.commit()
            time.sleep(30)
        except:
            time.sleep(60)

threading.Thread(target=monitor_bots, daemon=True).start()

# ==================== اجرا ====================
if __name__ == "__main__":
    print("=" * 60)
    print("🚀 ربات مادر نهایی - نسخه نهایی")
    print("=" * 60)
    print(f"✅ موتور اجرا: فعال")
    print(f"✅ مدیریت پوشه: فعال")
    print(f"✅ کتابخانه منیجر: فعال")
    print(f"👑 ادمین: {ADMIN_IDS}")
    print(f"💰 قیمت: {PRICE:,} تومان")
    print("=" * 60)
    
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=60)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)