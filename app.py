#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
═══════════════════════════════════════════════════════════════════════════════
🚀 ربات مادر نهایی - نسخه 18.0 Enterprise
⚡ دارای: سیستم اشتراک ماهیانه + رفرال ۷٪ + پنل مدیریت کامل
═══════════════════════════════════════════════════════════════════════════════
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
import queue
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from concurrent.futures import ThreadPoolExecutor
from functools import wraps

# ==================== تنظیمات پایه ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DIRS = {
    'DB': os.path.join(BASE_DIR, "database"),
    'FILES': os.path.join(BASE_DIR, "user_files"),
    'RUNNING': os.path.join(BASE_DIR, "running_bots"),
    'LOGS': os.path.join(BASE_DIR, "logs"),
    'RECEIPTS': os.path.join(BASE_DIR, "receipts"),
    'TEMP': os.path.join(BASE_DIR, "temp"),
    'MACHINES': os.path.join(BASE_DIR, "machines"),
    'CACHE': os.path.join(BASE_DIR, "cache")
}

for dir_path in DIRS.values():
    os.makedirs(dir_path, exist_ok=True)

# ==================== توکن و تنظیمات ====================
BOT_TOKEN = "8541672444:AAF4PBn7-XqiXUgaK0arVajyZfcMWqbxSJ0"
ADMIN_IDS = [327855654]

# تنظیمات پیش‌فرض (قابل تغییر در پنل مدیریت)
SETTINGS = {
    'card_number': "5892101187322777",
    'card_number_display': "5892 1011 8732 2777",
    'card_holder': "مرتضی نیکخو خنجری",
    'card_bank': "بانک ملی - سپهر",
    'subscription_price': 2000000,
    'subscription_price_str': "۲,۰۰۰,۰۰۰ تومان",
    'withdraw_percent': 7,  # درصد کمیسیون رفرال
    'min_withdraw': 2000000,  # حداقل برداشت ۲ میلیون
    'guide_text': "📚 راهنمای استفاده\n\n1️⃣ برای ساخت ربات، فایل .py یا .zip خود را ارسال کنید\n2️⃣ پس از پرداخت اشتراک ماهیانه، می‌توانید ربات بسازید\n3️⃣ هر کاربر می‌تواند تا سقف نامحدود ربات بسازد\n4️⃣ با دعوت دوستان، ۷٪ کمیسیون دریافت کنید\n5️⃣ پس از رسیدن به ۲ میلیون تومان، می‌توانید برداشت کنید"
}

# ==================== تنظیمات خوشه‌ای ====================
CLUSTER_CONFIG = {
    'TOTAL_MACHINES': 50,
    'BOTS_PER_MACHINE': 3000,
    'MAX_CONCURRENT_BUILDS': 100,
    'RATE_LIMIT': 100,
    'CACHE_TTL': 600,
    'WORKER_THREADS': 1000,
    'DB_POOL_SIZE': 50,
    'MAX_MEMORY_PER_BOT': 256,
    'TOTAL_MEMORY': 165 * 1024,
}

# ==================== لاگینگ ====================
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            os.path.join(DIRS['LOGS'], 'mother_bot.log'),
            maxBytes=100*1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
    ]
)
logger = logging.getLogger('MotherBot')

# ==================== دیتابیس ====================
class Database:
    def __init__(self):
        self.conn = None
        self._init_db()
        self._init_tables()
    
    def _init_db(self):
        self.conn = sqlite3.connect(
            os.path.join(DIRS['DB'], 'mother_bot.db'),
            timeout=30,
            check_same_thread=False
        )
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA cache_size=-200000")
    
    def execute(self, query, params=()):
        try:
            cursor = self.conn.execute(query, params)
            self.conn.commit()
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"DB error: {e}")
            return []
    
    def _init_tables(self):
        # کاربران
        self.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                bots_count INTEGER DEFAULT 0,
                subscription_status TEXT DEFAULT 'inactive',
                subscription_expiry TIMESTAMP,
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                referrals_count INTEGER DEFAULT 0,
                verified_referrals INTEGER DEFAULT 0,
                wallet_balance INTEGER DEFAULT 0,
                created_at TIMESTAMP,
                last_active TIMESTAMP,
                warning_sent INTEGER DEFAULT 0
            )
        ''')
        
        # ربات‌ها
        self.execute('''
            CREATE TABLE IF NOT EXISTS bots (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                token TEXT,
                name TEXT,
                username TEXT,
                file_path TEXT,
                folder_path TEXT,
                pid INTEGER,
                machine_id INTEGER,
                port INTEGER,
                status TEXT DEFAULT 'stopped',
                created_at TIMESTAMP,
                last_active TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        # ماشین‌ها
        self.execute('''
            CREATE TABLE IF NOT EXISTS machines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                status TEXT DEFAULT 'active',
                current_bots INTEGER DEFAULT 0,
                max_bots INTEGER DEFAULT 3000,
                memory_used INTEGER DEFAULT 0,
                max_memory INTEGER DEFAULT 165000,
                last_heartbeat TIMESTAMP,
                created_at TIMESTAMP
            )
        ''')
        
        # فیش‌ها
        self.execute('''
            CREATE TABLE IF NOT EXISTS receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                receipt_path TEXT,
                status TEXT DEFAULT 'pending',
                payment_code TEXT UNIQUE,
                reviewed_by INTEGER,
                reviewed_at TIMESTAMP,
                created_at TIMESTAMP
            )
        ''')
        
        # درخواست‌های برداشت
        self.execute('''
            CREATE TABLE IF NOT EXISTS withdraw_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                card_number TEXT,
                card_holder TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP,
                processed_at TIMESTAMP
            )
        ''')
        
        # خطاها
        self.execute('''
            CREATE TABLE IF NOT EXISTS errors (
                id TEXT PRIMARY KEY,
                type TEXT,
                message TEXT,
                user_id INTEGER,
                bot_id TEXT,
                timestamp TIMESTAMP,
                resolved BOOLEAN DEFAULT 0
            )
        ''')
        
        # تنظیمات سیستم
        self.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # ذخیره تنظیمات پیش‌فرض
        for key, value in SETTINGS.items():
            self.execute('INSERT OR IGNORE INTO system_settings (key, value) VALUES (?, ?)', (key, str(value)))
        
        # ایجاد ماشین‌ها
        for i in range(1, CLUSTER_CONFIG['TOTAL_MACHINES'] + 1):
            self.execute('''
                INSERT OR IGNORE INTO machines (id, name, status, max_bots, max_memory, created_at)
                VALUES (?, ?, 'active', ?, ?, ?)
            ''', (i, f"Machine-{i:02d}", 
                  CLUSTER_CONFIG['BOTS_PER_MACHINE'],
                  CLUSTER_CONFIG['MAX_MEMORY_PER_BOT'] * CLUSTER_CONFIG['BOTS_PER_MACHINE'],
                  datetime.now().isoformat()))

db = Database()

# ==================== کش ====================
class SimpleCache:
    def __init__(self, ttl=600):
        self.cache = {}
        self.ttl = ttl
    
    def set(self, key, value):
        self.cache[key] = {'value': value, 'expires': time.time() + self.ttl}
    
    def get(self, key):
        item = self.cache.get(key)
        if item and item['expires'] > time.time():
            return item['value']
        if key in self.cache:
            del self.cache[key]
        return None
    
    def delete(self, key):
        if key in self.cache:
            del self.cache[key]

cache = SimpleCache(ttl=CLUSTER_CONFIG['CACHE_TTL'])

# ==================== مدیریت ماشین‌ها ====================
class MachineManager:
    def __init__(self):
        self.port_counter = 8000
        self.processes = {}
        self.lock = threading.RLock()
    
    def get_available_machine(self):
        machines = db.execute("SELECT * FROM machines WHERE status = 'active' ORDER BY current_bots ASC")
        for m in machines:
            if m['current_bots'] < m['max_bots']:
                return m['id']
        return None
    
    def get_available_port(self):
        with self.lock:
            port = self.port_counter
            self.port_counter += 1
            if self.port_counter > 9000:
                self.port_counter = 8000
            return port
    
    def assign_bot(self, bot_id, machine_id):
        db.execute("UPDATE machines SET current_bots = current_bots + 1 WHERE id = ?", (machine_id,))
    
    def release_bot(self, bot_id, machine_id):
        db.execute("UPDATE machines SET current_bots = current_bots - 1 WHERE id = ?", (machine_id,))
    
    def run_bot(self, bot_id, code, token):
        try:
            machine_id = self.get_available_machine()
            if not machine_id:
                return {'success': False, 'error': 'همه ماشین‌ها پر هستند'}
            
            port = self.get_available_port()
            bot_dir = os.path.join(DIRS['MACHINES'], f"machine_{machine_id:02d}", bot_id)
            os.makedirs(bot_dir, exist_ok=True)
            
            code_path = os.path.join(bot_dir, 'bot.py')
            with open(code_path, 'w', encoding='utf-8') as f:
                f.write(code)
            
            log_file = os.path.join(DIRS['LOGS'], f"bot_{bot_id}.log")
            
            process = subprocess.Popen(
                [sys.executable, code_path],
                stdout=open(log_file, 'a'),
                stderr=subprocess.STDOUT,
                cwd=bot_dir,
                start_new_session=True
            )
            
            time.sleep(1)
            
            if process.poll() is None:
                with self.lock:
                    self.processes[bot_id] = {
                        'process': process,
                        'pid': process.pid,
                        'machine_id': machine_id,
                        'port': port,
                        'dir': bot_dir,
                        'start_time': time.time()
                    }
                self.assign_bot(bot_id, machine_id)
                return {'success': True, 'pid': process.pid, 'machine_id': machine_id}
            else:
                return {'success': False, 'error': 'خطا در اجرای ربات'}
        except Exception as e:
            return {'success': False, 'error': str(e)[:100]}
    
    def stop_bot(self, bot_id):
        with self.lock:
            if bot_id in self.processes:
                try:
                    info = self.processes[bot_id]
                    os.kill(info['pid'], signal.SIGTERM)
                    time.sleep(0.5)
                    self.release_bot(bot_id, info['machine_id'])
                    del self.processes[bot_id]
                    db.execute("UPDATE bots SET status = 'stopped', last_active = ? WHERE id = ?",
                              (datetime.now().isoformat(), bot_id))
                    return True
                except:
                    pass
        return False
    
    def get_status(self, bot_id):
        with self.lock:
            if bot_id in self.processes:
                info = self.processes[bot_id]
                try:
                    os.kill(info['pid'], 0)
                    return {'running': True, 'pid': info['pid'], 'machine_id': info['machine_id'],
                            'uptime': time.time() - info['start_time']}
                except:
                    if bot_id in self.processes:
                        del self.processes[bot_id]
                        self.release_bot(bot_id, info['machine_id'])
                        db.execute("UPDATE bots SET status = 'stopped' WHERE id = ?", (bot_id,))
        return {'running': False}
    
    def get_stats(self):
        machines = db.execute("SELECT * FROM machines WHERE status = 'active'")
        total_bots = sum(m['current_bots'] for m in machines)
        total_capacity = sum(m['max_bots'] for m in machines)
        return {
            'total': len(list(machines)),
            'total_bots': total_bots,
            'total_capacity': total_capacity,
            'available': total_capacity - total_bots
        }

machine_manager = MachineManager()

# ==================== ربات تلگرام ====================
bot = telebot.TeleBot(BOT_TOKEN)
bot.delete_webhook()

# ==================== توابع کمکی ====================

def get_setting(key):
    result = db.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
    if result:
        val = result[0]['value']
        if key in ['subscription_price', 'withdraw_percent', 'min_withdraw']:
            return int(val)
        return val
    return SETTINGS.get(key)

def update_setting(key, value):
    db.execute("UPDATE system_settings SET value = ? WHERE key = ?", (str(value), key))

def generate_referral_code(user_id):
    return hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:12]

def get_user(user_id):
    cached = cache.get(f"user_{user_id}")
    if cached:
        return cached
    users = db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    if users:
        user = dict(users[0])
        cache.set(f"user_{user_id}", user)
        return user
    return None

def create_user(user_id, username, first_name, last_name, referred_by=None):
    now = datetime.now().isoformat()
    referral_code = generate_referral_code(user_id)
    
    db.execute('''
        INSERT OR IGNORE INTO users 
        (user_id, username, first_name, last_name, referral_code, referred_by, created_at, last_active, subscription_status, wallet_balance)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'inactive', 0)
    ''', (user_id, username, first_name, last_name, referral_code, referred_by, now, now))
    
    db.execute('UPDATE users SET last_active = ? WHERE user_id = ?', (now, user_id))
    
    if referred_by:
        db.execute('UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = ?', (referred_by,))
    
    cache.delete(f"user_{user_id}")
    return True

def check_subscription(user_id):
    user = get_user(user_id)
    if not user:
        return False
    
    if user['subscription_status'] == 'active':
        expiry = datetime.fromisoformat(user['subscription_expiry'])
        if expiry > datetime.now():
            return True
        else:
            db.execute('UPDATE users SET subscription_status = "inactive", warning_sent = 0 WHERE user_id = ?', (user_id,))
            cache.delete(f"user_{user_id}")
    
    # بررسی اخطار
    warning_sent = user.get('warning_sent', 0)
    if warning_sent == 0:
        bot.send_message(user_id, f"⚠️ اشتراک شما منقضی شده است!\n💰 قیمت اشتراک: {get_setting('subscription_price_str')}\nلطفاً ظرف ۲۴ ساعت پرداخت کنید، در غیر این صورت ربات‌های شما متوقف می‌شوند.")
        db.execute('UPDATE users SET warning_sent = 1 WHERE user_id = ?', (user_id,))
    elif warning_sent == 1:
        # بعد از ۲۴ ساعت ربات‌ها را متوقف کن
        expiry = datetime.fromisoformat(user['subscription_expiry']) if user['subscription_expiry'] else datetime.now() - timedelta(days=1)
        if datetime.now() - expiry > timedelta(hours=24):
            for bot_rec in db.execute('SELECT id FROM bots WHERE user_id = ? AND status = "running"', (user_id,)):
                machine_manager.stop_bot(bot_rec['id'])
            db.execute('UPDATE users SET warning_sent = 2 WHERE user_id = ?', (user_id,))
            bot.send_message(user_id, "❌ ربات‌های شما به دلیل عدم تمدید اشتراک متوقف شدند.")
    
    return False

def activate_subscription(user_id, months=1):
    user = get_user(user_id)
    now = datetime.now()
    if user and user['subscription_status'] == 'active' and user['subscription_expiry']:
        new_expiry = datetime.fromisoformat(user['subscription_expiry']) + timedelta(days=30*months)
    else:
        new_expiry = now + timedelta(days=30*months)
    
    db.execute('''
        UPDATE users 
        SET subscription_status = 'active', subscription_expiry = ?, warning_sent = 0 
        WHERE user_id = ?
    ''', (new_expiry.isoformat(), user_id))
    cache.delete(f"user_{user_id}")
    
    bot.send_message(user_id, f"✅ اشتراک شما تا {new_expiry.strftime('%Y-%m-%d')} فعال شد!")

def add_wallet_balance(user_id, amount):
    user = get_user(user_id)
    new_balance = user['wallet_balance'] + amount
    db.execute('UPDATE users SET wallet_balance = ? WHERE user_id = ?', (new_balance, user_id))
    cache.delete(f"user_{user_id}")
    return new_balance

def check_bot_limit(user_id):
    if not check_subscription(user_id):
        return False, 0, 0
    bots = db.execute('SELECT COUNT(*) as count FROM bots WHERE user_id = ?', (user_id,))
    current_bots = bots[0]['count'] if bots else 0
    return True, 999999, current_bots

def get_user_bots(user_id):
    bots = db.execute('SELECT * FROM bots WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    return [dict(bot) for bot in bots]

def get_bot(bot_id):
    bots = db.execute('SELECT * FROM bots WHERE id = ?', (bot_id,))
    return dict(bots[0]) if bots else None

def delete_bot(bot_id, user_id):
    bot_rec = get_bot(bot_id)
    if not bot_rec or bot_rec['user_id'] != user_id:
        return False
    
    machine_manager.stop_bot(bot_id)
    
    if bot_rec.get('file_path') and os.path.exists(bot_rec['file_path']):
        os.remove(bot_rec['file_path'])
    
    bot_dir = os.path.join(DIRS['MACHINES'], f"machine_{bot_rec['machine_id']:02d}", bot_id)
    if os.path.exists(bot_dir):
        shutil.rmtree(bot_dir)
    
    db.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
    db.execute('UPDATE users SET bots_count = bots_count - 1 WHERE user_id = ?', (user_id,))
    
    cache.delete(f"user_{user_id}")
    return True

def extract_token_from_code(code):
    patterns = [
        r'token\s*=\s*["\']([^"\']+)["\']',
        r'TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'BOT_TOKEN\s*=\s*["\']([^"\']+)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, code)
        if match:
            return match.group(1)
    return None

def add_bot(user_id, bot_id, token, name, username, file_path, pid=None, machine_id=None):
    now = datetime.now().isoformat()
    db.execute('''
        INSERT INTO bots 
        (id, user_id, token, name, username, file_path, pid, machine_id, status, created_at, last_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'running', ?, ?)
    ''', (bot_id, user_id, token, name, username, file_path, pid, machine_id, now, now))
    db.execute('UPDATE users SET bots_count = bots_count + 1, last_active = ? WHERE user_id = ?', (now, user_id))
    cache.delete(f"user_{user_id}")
    return True

def log_error(error_type, message, user_id=None, bot_id=None):
    error_id = hashlib.md5(f"{time.time()}_{user_id}_{bot_id}".encode()).hexdigest()[:16]
    db.execute('''
        INSERT INTO errors (id, type, message, user_id, bot_id, timestamp, resolved)
        VALUES (?, ?, ?, ?, ?, ?, 0)
    ''', (error_id, error_type, message[:500], user_id, bot_id, datetime.now().isoformat()))

# ==================== منوی اصلی ====================
def get_main_menu(is_admin=False):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        types.KeyboardButton('🤖 ساخت ربات جدید'),
        types.KeyboardButton('📋 ربات‌های من'),
        types.KeyboardButton('🔄 فعال/غیرفعال'),
        types.KeyboardButton('🗑 حذف ربات'),
        types.KeyboardButton('💰 کیف پول و اشتراک'),
        types.KeyboardButton('📚 راهنما'),
        types.KeyboardButton('👥 دعوت دوستان'),
        types.KeyboardButton('💸 درخواست برداشت'),
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

# ==================== دستورات ====================

@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or ""
    
    referred_by = None
    args = message.text.split()
    if len(args) > 1:
        users = db.execute('SELECT user_id FROM users WHERE referral_code = ?', (args[1],))
        if users and users[0]['user_id'] != user_id:
            referred_by = users[0]['user_id']
            bot.send_message(referred_by, f"🎉 {first_name} با لینک شما وارد شد!")
    
    create_user(user_id, message.from_user.username or "", first_name, message.from_user.last_name or "", referred_by)
    
    user = get_user(user_id)
    bot_username = bot.get_me().username
    referral_link = f"https://t.me/{bot_username}?start={user['referral_code']}"
    
    text = (f"🚀 خوش آمدید {first_name}!\n\n"
            f"👤 ID: {user_id}\n"
            f"🎁 کد معرف: {user['referral_code']}\n"
            f"🔗 لینک دعوت: {referral_link}\n"
            f"📊 تعداد دعوت‌ها: {user['referrals_count']}\n"
            f"💰 موجودی کیف پول: {user['wallet_balance']:,} تومان\n\n"
            f"📤 برای ساخت ربات، فایل .py یا .zip خود را ارسال کنید")
    
    bot.send_message(message.chat.id, text, reply_markup=get_main_menu(user_id in ADMIN_IDS))

# ==================== کیف پول و اشتراک ====================
@bot.message_handler(func=lambda m: m.text == '💰 کیف پول و اشتراک')
def wallet(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        bot.send_message(message.chat.id, "❌ /start بزنید")
        return
    
    is_subscribed = check_subscription(user_id)
    expiry = "ندارد"
    if user['subscription_expiry']:
        expiry = datetime.fromisoformat(user['subscription_expiry']).strftime('%Y-%m-%d')
    
    text = (f"💰 کیف پول و اشتراک\n\n"
            f"👤 {user['first_name']}\n"
            f"💳 وضعیت اشتراک: {'✅ فعال' if is_subscribed else '❌ غیرفعال'}\n"
            f"📅 تاریخ انقضا: {expiry}\n"
            f"💰 موجودی کیف پول: {user['wallet_balance']:,} تومان\n"
            f"👥 تعداد دعوت‌ها: {user['referrals_count']}\n"
            f"⭐ کمیسیون هر دعوت: {get_setting('withdraw_percent')}%\n\n")
    
    if not is_subscribed:
        text += (f"💳 برای فعالسازی اشتراک ماهیانه مبلغ {get_setting('subscription_price_str')} را به کارت زیر واریز کنید:\n\n"
                f"💳 شماره کارت: {get_setting('card_number_display')}\n"
                f"👤 به نام: {get_setting('card_holder')}\n"
                f"🏦 بانک: {get_setting('card_bank')}\n\n"
                f"📸 پس از واریز، تصویر فیش را ارسال کنید")
    else:
        text += "✅ اشتراک شما فعال است. می‌توانید ربات بسازید."
    
    bot.send_message(message.chat.id, text)

# ==================== فیش ====================
@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    
    existing = db.execute('SELECT id FROM receipts WHERE user_id = ? AND status = "pending"', (user_id,))
    if existing:
        bot.reply_to(message, "⏳ فیش قبلی در انتظار تایید است")
        return
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        payment_code = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:8].upper()
        receipt_path = os.path.join(DIRS['RECEIPTS'], f"{user_id}_{payment_code}.jpg")
        
        with open(receipt_path, 'wb') as f:
            f.write(downloaded)
        
        db.execute('''
            INSERT INTO receipts (user_id, amount, receipt_path, payment_code, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, get_setting('subscription_price'), receipt_path, payment_code, datetime.now().isoformat()))
        
        bot.reply_to(message, f"✅ فیش دریافت شد\n💰 {get_setting('subscription_price_str')}\n🆔 {payment_code}\n⏳ پس از تایید، اشتراک شما فعال می‌شود.")
        
        for admin_id in ADMIN_IDS:
            try:
                with open(receipt_path, 'rb') as f:
                    bot.send_photo(admin_id, f, caption=f"📸 فیش جدید\n👤 {message.from_user.first_name}\n🆔 {user_id}\n💰 {get_setting('subscription_price_str')}\n🆔 {payment_code}")
            except:
                pass
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")
        log_error("receipt_error", str(e), user_id)

# ==================== دعوت دوستان ====================
@bot.message_handler(func=lambda m: m.text == '👥 دعوت دوستان')
def invite(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    bot_username = bot.get_me().username
    referral_link = f"https://t.me/{bot_username}?start={user['referral_code']}"
    
    text = (f"👥 سیستم دعوت دوستان\n\n"
            f"🎁 کد معرف شما: {user['referral_code']}\n"
            f"🔗 لینک دعوت: {referral_link}\n"
            f"📊 تعداد دعوت‌ها: {user['referrals_count']}\n"
            f"💰 کمیسیون هر دعوت: {get_setting('withdraw_percent')}% مبلغ اشتراک\n"
            f"⭐ برای هر دوستی که اشتراک بخرد، {get_setting('withdraw_percent')}% مبلغ به کیف پول شما اضافه می‌شود.\n\n"
            f"لینک خود را به اشتراک بگذارید و از دوستان خود دعوت کنید!")
    
    bot.send_message(message.chat.id, text)

# ==================== درخواست برداشت ====================
@bot.message_handler(func=lambda m: m.text == '💸 درخواست برداشت')
def withdraw_request(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if user['wallet_balance'] < get_setting('min_withdraw'):
        bot.send_message(message.chat.id, f"❌ موجودی کیف پول شما ({user['wallet_balance']:,} تومان) کمتر از حداقل برداشت ({get_setting('min_withdraw'):,} تومان) است.")
        return
    
    msg = bot.send_message(message.chat.id, "💳 شماره کارت خود را وارد کنید:")
    bot.register_next_step_handler(msg, process_withdraw_card, user)

def process_withdraw_card(message, user):
    card_number = message.text.strip()
    msg = bot.send_message(message.chat.id, "👤 نام صاحب کارت را وارد کنید:")
    bot.register_next_step_handler(msg, process_withdraw_holder, user, card_number)

def process_withdraw_holder(message, user, card_number):
    card_holder = message.text.strip()
    
    db.execute('''
        INSERT INTO withdraw_requests (user_id, amount, card_number, card_holder, created_at, status)
        VALUES (?, ?, ?, ?, ?, 'pending')
    ''', (user['user_id'], user['wallet_balance'], card_number, card_holder, datetime.now().isoformat()))
    
    # کاهش موقت موجودی
    db.execute('UPDATE users SET wallet_balance = 0 WHERE user_id = ?', (user['user_id'],))
    cache.delete(f"user_{user['user_id']}")
    
    bot.send_message(message.chat.id, f"✅ درخواست برداشت به مبلغ {user['wallet_balance']:,} تومان ثبت شد. پس از تایید مدیر، مبلغ به کارت شما واریز می‌شود.")
    
    for admin_id in ADMIN_IDS:
        bot.send_message(admin_id, f"💰 درخواست برداشت جدید\n👤 {user['first_name']}\n🆔 {user['user_id']}\n💰 {user['wallet_balance']:,} تومان\n💳 {card_number}\n👤 {card_holder}")

# ==================== ساخت ربات جدید ====================
@bot.message_handler(func=lambda m: m.text == '🤖 ساخت ربات جدید')
def new_bot(message):
    user_id = message.from_user.id
    
    if not check_subscription(user_id):
        bot.send_message(message.chat.id, f"❌ اشتراک شما فعال نیست.\n💰 برای فعالسازی {get_setting('subscription_price_str')} واریز کنید.")
        return
    
    can_create, max_bots, current_bots = check_bot_limit(user_id)
    if not can_create:
        bot.send_message(message.chat.id, f"❌ به حداکثر تعداد ربات رسیده‌اید.")
        return
    
    bot.send_message(message.chat.id, "📤 فایل .py یا .zip ربات خود را ارسال کنید.")

# ==================== آپلود فایل ====================
@bot.message_handler(content_types=['document'])
def handle_build_file(message):
    user_id = message.from_user.id
    
    if not check_subscription(user_id):
        bot.reply_to(message, "❌ اشتراک شما فعال نیست. ابتدا اشتراک بخرید.")
        return
    
    file_name = message.document.file_name
    
    if not (file_name.endswith('.py') or file_name.endswith('.zip')):
        bot.reply_to(message, "❌ فقط فایل‌های .py یا .zip پشتیبانی می‌شوند.")
        return
    
    if message.document.file_size > 50 * 1024 * 1024:
        bot.reply_to(message, "❌ حجم فایل نباید بیشتر از ۵۰ مگابایت باشد.")
        return
    
    status_msg = bot.reply_to(message, "🔄 در حال پردازش...")
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        user_dir = os.path.join(DIRS['FILES'], str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        file_path = os.path.join(user_dir, f"{int(time.time())}_{file_name}")
        with open(file_path, 'wb') as f:
            f.write(downloaded)
        
        main_code = ""
        
        if file_name.endswith('.zip'):
            extract_dir = os.path.join(DIRS['TEMP'], f"extract_{user_id}_{int(time.time())}")
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            for root, _, files in os.walk(extract_dir):
                for f in files:
                    if f.endswith('.py'):
                        with open(os.path.join(root, f), 'r', encoding='utf-8', errors='ignore') as code_f:
                            main_code = code_f.read()
                            break
                if main_code:
                    break
            
            shutil.rmtree(extract_dir, ignore_errors=True)
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                main_code = f.read()
        
        if not main_code:
            bot.edit_message_text("❌ فایل پایتون معتبری پیدا نشد.", message.chat.id, status_msg.message_id)
            return
        
        token = extract_token_from_code(main_code)
        if not token:
            bot.edit_message_text("❌ توکن ربات در کد پیدا نشد.", message.chat.id, status_msg.message_id)
            return
        
        # بررسی توکن
        resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        if resp.status_code != 200:
            bot.edit_message_text("❌ توکن نامعتبر است.", message.chat.id, status_msg.message_id)
            return
        
        bot_info = resp.json()['result']
        
        bot_id = hashlib.md5(f"{user_id}{token}{time.time()}".encode()).hexdigest()[:16]
        
        result = machine_manager.run_bot(bot_id, main_code, token)
        
        if result['success']:
            add_bot(user_id, bot_id, token, bot_info['first_name'], bot_info['username'], file_path, result['pid'], result['machine_id'])
            
            # اضافه کردن کمیسیون به معرف
            user = get_user(user_id)
            if user and user['referred_by']:
                commission = int(get_setting('subscription_price') * get_setting('withdraw_percent') / 100)
                add_wallet_balance(user['referred_by'], commission)
                bot.send_message(user['referred_by'], f"🎉 {user['first_name']} اشترک خرید! {commission:,} تومان به کیف پول شما اضافه شد.")
            
            bot.edit_message_text(f"✅ ربات {bot_info['first_name']} با موفقیت ساخته شد!", message.chat.id, status_msg.message_id)
        else:
            bot.edit_message_text(f"❌ خطا: {result.get('error', 'مشخص نشده')}", message.chat.id, status_msg.message_id)
            
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)[:100]}", message.chat.id, status_msg.message_id)
        log_error("build_error", str(e), user_id)

# ==================== ربات‌های من ====================
@bot.message_handler(func=lambda m: m.text == '📋 ربات‌های من')
def my_bots(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما هیچ رباتی ندارید.")
        return
    
    for b in bots[:10]:
        status = machine_manager.get_status(b['id'])
        emoji = "🟢" if status.get('running') else "🔴"
        text = f"{emoji} {b['name']}\n🆔 {b['id']}\n🔗 t.me/{b['username']}"
        bot.send_message(message.chat.id, text)

# ==================== فعال/غیرفعال ====================
@bot.message_handler(func=lambda m: m.text == '🔄 فعال/غیرفعال')
def toggle_prompt(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    if not bots:
        bot.send_message(message.chat.id, "📋 شما هیچ رباتی ندارید.")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        status = machine_manager.get_status(b['id'])
        emoji = "🟢" if status.get('running') else "🔴"
        markup.add(types.InlineKeyboardButton(f"{emoji} {b['name']}", callback_data=f"toggle_{b['id']}"))
    
    bot.send_message(message.chat.id, "🔄 ربات مورد نظر را انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_'))
def toggle_bot(call):
    bot_id = call.data.replace('toggle_', '')
    bot_rec = get_bot(bot_id)
    
    if not bot_rec or bot_rec['user_id'] != call.from_user.id:
        bot.answer_callback_query(call.id, "❌ ربات یافت نشد")
        return
    
    status = machine_manager.get_status(bot_id)
    
    if status.get('running'):
        if machine_manager.stop_bot(bot_id):
            bot.answer_callback_query(call.id, "✅ ربات متوقف شد")
        else:
            bot.answer_callback_query(call.id, "❌ خطا در توقف")
    else:
        if os.path.exists(bot_rec['file_path']):
            try:
                with open(bot_rec['file_path'], 'r', encoding='utf-8', errors='ignore') as f:
                    code = f.read()
                result = machine_manager.run_bot(bot_id, code, bot_rec['token'])
                if result['success']:
                    db.execute("UPDATE bots SET machine_id = ?, pid = ? WHERE id = ?", (result['machine_id'], result['pid'], bot_id))
                    bot.answer_callback_query(call.id, "✅ ربات فعال شد")
                else:
                    bot.answer_callback_query(call.id, f"❌ {result.get('error', 'خطا')}")
            except Exception as e:
                bot.answer_callback_query(call.id, "❌ خطا در اجرا")
        else:
            bot.answer_callback_query(call.id, "❌ فایل ربات یافت نشد")

# ==================== حذف ربات ====================
@bot.message_handler(func=lambda m: m.text == '🗑 حذف ربات')
def delete_prompt(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    if not bots:
        bot.send_message(message.chat.id, "📋 شما هیچ رباتی ندارید.")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        markup.add(types.InlineKeyboardButton(f"🗑 {b['name']}", callback_data=f"delete_{b['id']}"))
    
    bot.send_message(message.chat.id, "🗑 ربات مورد نظر را انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
def confirm_delete(call):
    bot_id = call.data.replace('delete_', '')
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ بله، حذف کن", callback_data=f"confirm_del_{bot_id}"),
        types.InlineKeyboardButton("❌ انصراف", callback_data="cancel_del")
    )
    bot.edit_message_text("⚠️ آیا از حذف این ربات اطمینان دارید؟", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_del_'))
def do_delete(call):
    bot_id = call.data.replace('confirm_del_', '')
    if delete_bot(bot_id, call.from_user.id):
        bot.edit_message_text("✅ ربات با موفقیت حذف شد.", call.message.chat.id, call.message.message_id)
    else:
        bot.edit_message_text("❌ خطا در حذف ربات.", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == 'cancel_del')
def cancel_delete(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== راهنما ====================
@bot.message_handler(func=lambda m: m.text == '📚 راهنما')
def guide(message):
    bot.send_message(message.chat.id, get_setting('guide_text'))

# ==================== آمار ====================
@bot.message_handler(func=lambda m: m.text == '📊 آمار')
def stats(message):
    users = db.execute('SELECT COUNT(*) as count FROM users')[0]['count']
    active_subs = db.execute('SELECT COUNT(*) as count FROM users WHERE subscription_status = "active"')[0]['count']
    bots = db.execute('SELECT COUNT(*) as count FROM bots')[0]['count']
    running_bots = db.execute('SELECT COUNT(*) as count FROM bots WHERE status = "running"')[0]['count']
    pending_withdraw = db.execute('SELECT COUNT(*) as count FROM withdraw_requests WHERE status = "pending"')[0]['count']
    total_wallet = db.execute('SELECT SUM(wallet_balance) as total FROM users')[0]['total'] or 0
    
    text = (f"📊 آمار کلی\n\n"
            f"👥 کل کاربران: {users:,}\n"
            f"✅ اشتراک فعال: {active_subs:,}\n"
            f"🤖 کل ربات‌ها: {bots:,}\n"
            f"🟢 ربات فعال: {running_bots:,}\n"
            f"💰 موجودی کیف پول کل: {total_wallet:,} تومان\n"
            f"💸 درخواست برداشت: {pending_withdraw}\n\n"
            f"🖥️ وضعیت ماشین‌ها: {machine_manager.get_stats()['available']} ظرفیت خالی از {CLUSTER_CONFIG['TOTAL_MACHINES'] * CLUSTER_CONFIG['BOTS_PER_MACHINE']:,}")
    
    bot.send_message(message.chat.id, text)

# ==================== پشتیبانی ====================
@bot.message_handler(func=lambda m: m.text == '📞 پشتیبانی')
def support(message):
    bot.send_message(message.chat.id, "📞 پشتیبانی: @shahraghee13")

# ==================== پنل مدیریت ====================
@bot.message_handler(func=lambda m: m.text == '👑 پنل مدیریت')
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📸 تایید فیش", callback_data="admin_receipts"),
        types.InlineKeyboardButton("💰 تایید برداشت", callback_data="admin_withdraws"),
        types.InlineKeyboardButton("👥 مدیریت کاربران", callback_data="admin_users"),
        types.InlineKeyboardButton("🤖 مدیریت ربات‌ها", callback_data="admin_bots"),
        types.InlineKeyboardButton("⚙️ تنظیمات سیستم", callback_data="admin_settings"),
        types.InlineKeyboardButton("🔧 رفع خطاها", callback_data="admin_errors"),
        types.InlineKeyboardButton("📊 گزارش کامل", callback_data="admin_report"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    bot.send_message(message.chat.id, "👑 پنل مدیریت:", reply_markup=markup)

# ==================== کال‌بک‌های مدیریت ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_receipts")
def admin_receipts(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی محدود")
        return
    
    receipts = db.execute('SELECT * FROM receipts WHERE status = "pending" ORDER BY created_at')
    
    if not receipts:
        bot.send_message(call.message.chat.id, "📸 هیچ فیش در انتظاری وجود ندارد.")
        return
    
    for r in receipts:
        user = get_user(r['user_id'])
        text = f"📸 فیش جدید\n👤 {user['first_name'] if user else 'نامشخص'}\n🆔 {r['user_id']}\n💰 {r['amount']:,} تومان\n🆔 {r['payment_code']}"
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید اشتراک", callback_data=f"approve_receipt_{r['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"reject_receipt_{r['id']}")
        )
        if os.path.exists(r['receipt_path']):
            with open(r['receipt_path'], 'rb') as f:
                bot.send_photo(call.message.chat.id, f, caption=text, reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_receipt_'))
def approve_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی محدود")
        return
    
    rid = int(call.data.replace('approve_receipt_', ''))
    r = db.execute('SELECT user_id FROM receipts WHERE id = ?', (rid,))
    if r:
        user_id = r[0]['user_id']
        db.execute('UPDATE receipts SET status = "approved", reviewed_by = ?, reviewed_at = ? WHERE id = ?',
                  (call.from_user.id, datetime.now().isoformat(), rid))
        activate_subscription(user_id)
        bot.answer_callback_query(call.id, "✅ اشتراک کاربر فعال شد")
        bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_receipt_'))
def reject_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی محدود")
        return
    
    rid = int(call.data.replace('reject_receipt_', ''))
    db.execute('UPDATE receipts SET status = "rejected", reviewed_by = ?, reviewed_at = ? WHERE id = ?',
              (call.from_user.id, datetime.now().isoformat(), rid))
    bot.answer_callback_query(call.id, "❌ فیش رد شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_withdraws")
def admin_withdraws(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی محدود")
        return
    
    withdraws = db.execute('SELECT * FROM withdraw_requests WHERE status = "pending" ORDER BY created_at')
    
    if not withdraws:
        bot.send_message(call.message.chat.id, "💰 هیچ درخواست برداشتی وجود ندارد.")
        return
    
    for w in withdraws:
        user = get_user(w['user_id'])
        text = (f"💰 درخواست برداشت\n"
                f"👤 {user['first_name'] if user else 'نامشخص'}\n"
                f"🆔 {w['user_id']}\n"
                f"💰 {w['amount']:,} تومان\n"
                f"💳 {w['card_number']}\n"
                f"👤 {w['card_holder']}")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ تایید واریز", callback_data=f"approve_withdraw_{w['id']}"))
        bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_withdraw_'))
def approve_withdraw(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی محدود")
        return
    
    wid = int(call.data.replace('approve_withdraw_', ''))
    db.execute('UPDATE withdraw_requests SET status = "approved", processed_at = ? WHERE id = ?',
              (datetime.now().isoformat(), wid))
    bot.answer_callback_query(call.id, "✅ درخواست برداشت تایید شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_users")
def admin_users(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی محدود")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🔍 جستجوی کاربر", callback_data="admin_search_user"),
        types.InlineKeyboardButton("🗑 حذف کاربر", callback_data="admin_delete_user"),
        types.InlineKeyboardButton("💰 افزایش موجودی", callback_data="admin_add_balance"),
        types.InlineKeyboardButton("🎁 فعالسازی اشتراک", callback_data="admin_activate_sub"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    bot.send_message(call.message.chat.id, "👥 مدیریت کاربران:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_search_user")
def admin_search_user(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "🔍 آیدی عددی کاربر را وارد کنید:")
    bot.register_next_step_handler(msg, process_admin_search)

def process_admin_search(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        uid = int(message.text.strip())
        user = get_user(uid)
        if user:
            bots = db.execute('SELECT COUNT(*) as count FROM bots WHERE user_id = ?', (uid,))
            text = (f"👤 اطلاعات کاربر\n"
                    f"🆔 {user['user_id']}\n"
                    f"👤 {user['first_name']}\n"
                    f"🎁 کد معرف: {user['referral_code']}\n"
                    f"📊 دعوت‌ها: {user['referrals_count']}\n"
                    f"💰 موجودی: {user['wallet_balance']:,} تومان\n"
                    f"✅ اشتراک: {'فعال' if user['subscription_status'] == 'active' else 'غیرفعال'}\n"
                    f"📅 انقضا: {user['subscription_expiry'] or 'ندارد'}\n"
                    f"🤖 تعداد ربات: {bots[0]['count']}")
            bot.reply_to(message, text)
        else:
            bot.reply_to(message, "❌ کاربر یافت نشد")
    except:
        bot.reply_to(message, "❌ آیدی نامعتبر")

@bot.callback_query_handler(func=lambda call: call.data == "admin_delete_user")
def admin_delete_user(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "🗑 آیدی عددی کاربر مورد نظر را وارد کنید:")
    bot.register_next_step_handler(msg, process_admin_delete)

def process_admin_delete(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        uid = int(message.text.strip())
        # توقف همه ربات‌های کاربر
        for bot_rec in db.execute('SELECT id FROM bots WHERE user_id = ?', (uid,)):
            machine_manager.stop_bot(bot_rec['id'])
        # حذف کاربر
        db.execute('DELETE FROM users WHERE user_id = ?', (uid,))
        bot.reply_to(message, f"✅ کاربر {uid} حذف شد")
    except:
        bot.reply_to(message, "❌ خطا در حذف")

@bot.callback_query_handler(func=lambda call: call.data == "admin_add_balance")
def admin_add_balance(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "💰 آیدی کاربر و مبلغ (مثال: 123456 100000):")
    bot.register_next_step_handler(msg, process_add_balance)

def process_add_balance(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        parts = message.text.strip().split()
        uid = int(parts[0])
        amount = int(parts[1])
        add_wallet_balance(uid, amount)
        bot.reply_to(message, f"✅ {amount:,} تومان به کیف پول کاربر {uid} اضافه شد")
        bot.send_message(uid, f"💰 {amount:,} تومان به کیف پول شما اضافه شد.")
    except:
        bot.reply_to(message, "❌ فرمت نامعتبر")

@bot.callback_query_handler(func=lambda call: call.data == "admin_activate_sub")
def admin_activate_sub(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "🎁 آیدی کاربر را وارد کنید:")
    bot.register_next_step_handler(msg, process_activate_sub)

def process_activate_sub(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        uid = int(message.text.strip())
        activate_subscription(uid)
        bot.reply_to(message, f"✅ اشتراک کاربر {uid} فعال شد")
    except:
        bot.reply_to(message, "❌ خطا")

@bot.callback_query_handler(func=lambda call: call.data == "admin_bots")
def admin_bots(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📋 لیست همه ربات‌ها", callback_data="admin_list_bots"),
        types.InlineKeyboardButton("🗑 حذف ربات", callback_data="admin_delete_bot"),
        types.InlineKeyboardButton("🔄 ریستارت ربات مشکل‌دار", callback_data="admin_fix_bot"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    bot.send_message(call.message.chat.id, "🤖 مدیریت ربات‌ها:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_list_bots")
def admin_list_bots(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    bots = db.execute('SELECT * FROM bots ORDER BY created_at DESC LIMIT 50')
    if not bots:
        bot.send_message(call.message.chat.id, "📋 هیچ رباتی وجود ندارد")
        return
    for b in bots:
        text = f"🤖 {b['name']}\n🆔 {b['id']}\n👤 کاربر: {b['user_id']}\n🔄 وضعیت: {b['status']}"
        bot.send_message(call.message.chat.id, text)

@bot.callback_query_handler(func=lambda call: call.data == "admin_delete_bot")
def admin_delete_bot(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "🗑 آیدی ربات را وارد کنید:")
    bot.register_next_step_handler(msg, process_admin_delete_bot)

def process_admin_delete_bot(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    bot_id = message.text.strip()
    if delete_bot(bot_id, None):
        bot.reply_to(message, f"✅ ربات {bot_id} حذف شد")
    else:
        bot.reply_to(message, "❌ ربات یافت نشد")

@bot.callback_query_handler(func=lambda call: call.data == "admin_fix_bot")
def admin_fix_bot(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "🔧 آیدی ربات مشکل‌دار را وارد کنید:")
    bot.register_next_step_handler(msg, process_fix_bot)

def process_fix_bot(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    bot_id = message.text.strip()
    bot_rec = get_bot(bot_id)
    if not bot_rec:
        bot.reply_to(message, "❌ ربات یافت نشد")
        return
    
    machine_manager.stop_bot(bot_id)
    time.sleep(1)
    
    if os.path.exists(bot_rec['file_path']):
        with open(bot_rec['file_path'], 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()
        result = machine_manager.run_bot(bot_id, code, bot_rec['token'])
        if result['success']:
            db.execute("UPDATE bots SET machine_id = ?, pid = ?, status = 'running' WHERE id = ?",
                      (result['machine_id'], result['pid'], bot_id))
            bot.reply_to(message, f"✅ ربات {bot_id} با موفقیت ریستارت شد")
        else:
            bot.reply_to(message, f"❌ خطا: {result.get('error')}")
    else:
        bot.reply_to(message, "❌ فایل ربات یافت نشد")

@bot.callback_query_handler(func=lambda call: call.data == "admin_settings")
def admin_settings(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("💳 تغییر شماره کارت", callback_data="admin_set_card"),
        types.InlineKeyboardButton("💰 تغییر قیمت اشتراک", callback_data="admin_set_price"),
        types.InlineKeyboardButton("📝 تغییر متن راهنما", callback_data="admin_set_guide"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    bot.send_message(call.message.chat.id, "⚙️ تنظیمات سیستم:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_card")
def admin_set_card(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "💳 شماره کارت جدید را وارد کنید:")
    bot.register_next_step_handler(msg, process_set_card)

def process_set_card(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    card = message.text.strip()
    update_setting('card_number', card)
    display = ' '.join([card[i:i+4] for i in range(0, len(card), 4)])
    update_setting('card_number_display', display)
    bot.reply_to(message, f"✅ شماره کارت به {display} تغییر کرد")

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_price")
def admin_set_price(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "💰 قیمت جدید اشتراک (تومان) را وارد کنید:")
    bot.register_next_step_handler(msg, process_set_price)

def process_set_price(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        price = int(message.text.strip())
        update_setting('subscription_price', price)
        price_str = f"{price:,} تومان"
        update_setting('subscription_price_str', price_str)
        bot.reply_to(message, f"✅ قیمت اشتراک به {price_str} تغییر کرد")
    except:
        bot.reply_to(message, "❌ عدد نامعتبر")

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_guide")
def admin_set_guide(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "📝 متن جدید راهنما را ارسال کنید:")
    bot.register_next_step_handler(msg, process_set_guide)

def process_set_guide(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    update_setting('guide_text', message.text.strip())
    bot.reply_to(message, "✅ متن راهنما ذخیره شد")

@bot.callback_query_handler(func=lambda call: call.data == "admin_errors")
def admin_errors(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    errors = db.execute('SELECT * FROM errors WHERE resolved = 0 ORDER BY timestamp DESC LIMIT 20')
    if not errors:
        bot.send_message(call.message.chat.id, "✅ هیچ خطای ثبت‌شده‌ای وجود ندارد")
        return
    
    for e in errors:
        text = (f"⚠️ خطا: {e['type']}\n"
                f"📝 {e['message'][:200]}\n"
                f"🆔 کاربر: {e['user_id'] or 'نامشخص'}\n"
                f"🤖 ربات: {e['bot_id'] or 'نامشخص'}\n"
                f"🕐 {e['timestamp']}")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ رفع شد", callback_data=f"resolve_error_{e['id']}"))
        bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('resolve_error_'))
def resolve_error(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    eid = call.data.replace('resolve_error_', '')
    db.execute('UPDATE errors SET resolved = 1 WHERE id = ?', (eid,))
    bot.answer_callback_query(call.id, "✅ خطا به عنوان رفع‌شده علامت‌گذاری شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_report")
def admin_report(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    users = db.execute('SELECT COUNT(*) as count FROM users')[0]['count']
    active_subs = db.execute('SELECT COUNT(*) as count FROM users WHERE subscription_status = "active"')[0]['count']
    bots = db.execute('SELECT COUNT(*) as count FROM bots')[0]['count']
    running = db.execute('SELECT COUNT(*) as count FROM bots WHERE status = "running"')[0]['count']
    pending_receipts = db.execute('SELECT COUNT(*) as count FROM receipts WHERE status = "pending"')[0]['count']
    pending_withdraws = db.execute('SELECT COUNT(*) as count FROM withdraw_requests WHERE status = "pending"')[0]['count']
    total_wallet = db.execute('SELECT SUM(wallet_balance) as total FROM users')[0]['total'] or 0
    total_referrals = db.execute('SELECT SUM(referrals_count) as total FROM users')[0]['total'] or 0
    
    text = (f"📊 گزارش کامل سیستم\n\n"
            f"👥 کل کاربران: {users}\n"
            f"✅ اشتراک فعال: {active_subs}\n"
            f"🤖 کل ربات‌ها: {bots}\n"
            f"🟢 ربات فعال: {running}\n"
            f"📸 فیش در انتظار: {pending_receipts}\n"
            f"💰 برداشت در انتظار: {pending_withdraws}\n"
            f"💎 موجودی کل کیف پول: {total_wallet:,} تومان\n"
            f"👥 کل دعوت‌ها: {total_referrals}\n"
            f"🖥️ ظرفیت خالی: {machine_manager.get_stats()['available']}\n\n"
            f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    bot.send_message(call.message.chat.id, text)

@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "🚀 منوی اصلی:", reply_markup=get_main_menu(True))

# ==================== پیام همگانی ====================
@bot.message_handler(func=lambda m: m.text == '📢 پیام همگانی')
def broadcast_prompt(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(message.chat.id, "📢 متن پیام همگانی را ارسال کنید:")
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    text = message.text
    users = db.execute("SELECT user_id FROM users")
    sent = 0
    for user in users:
        try:
            bot.send_message(user['user_id'], text)
            sent += 1
        except:
            pass
    bot.reply_to(message, f"✅ پیام به {sent} کاربر ارسال شد.")

# ==================== مانیتورینگ ====================
def monitor_system():
    while True:
        try:
            # پاکسازی کش
            # چک کردن اشتراک‌های منقضی شده و ارسال اخطار
            for user in db.execute('SELECT user_id, subscription_expiry, subscription_status, warning_sent FROM users WHERE subscription_status = "active"'):
                if user['subscription_expiry']:
                    expiry = datetime.fromisoformat(user['subscription_expiry'])
                    if expiry < datetime.now():
                        db.execute('UPDATE users SET subscription_status = "inactive", warning_sent = 0 WHERE user_id = ?', (user['user_id'],))
                        bot.send_message(user['user_id'], f"⚠️ اشتراک شما منقضی شد! لطفاً برای ادامه فعالیت، اشتراک خود را تمدید کنید.\n💰 {get_setting('subscription_price_str')}")
            
            time.sleep(60)
        except:
            time.sleep(60)

threading.Thread(target=monitor_system, daemon=True).start()

# ==================== اجرا ====================
if __name__ == "__main__":
    print("=" * 80)
    print("🚀 ربات مادر نهایی - نسخه 18.0 Enterprise".center(80))
    print("=" * 80)
    print(f"👑 ادمین‌ها: {ADMIN_IDS}")
    print(f"💰 قیمت اشتراک: {get_setting('subscription_price_str')}")
    print(f"⭐ کمیسیون رفرال: {get_setting('withdraw_percent')}%")
    print("=" * 80)
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            logger.error(f"Polling error: {e}")
            time.sleep(5)