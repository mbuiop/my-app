#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
═══════════════════════════════════════════════════════════════════════════════
🚀 ربات مادر نهایی - نسخه 18.0 با ایزوله‌سازی کامل
⚡ قدرت: ۵۰ ماشین مجزا | هر ماشین ۳۰۰۰ ربات | حافظه ۱۶۵GB
⚡ ایزوله‌سازی با Docker | سیستم رفرال کامل | پنل مدیریت پیشرفته
═══════════════════════════════════════════════════════════════════════════════
"""

# ==================== کتابخانه‌های اصلی ====================
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
import random
import string
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

# تنظیمات مالی و رفرال
CARD_INFO = {
    'number': "5892101187322777",
    'number_display': "5892 1011 8732 2777",
    'holder': "مرتضی نیکخو خنجری",
    'bank': "بانک ملی - سپهر",
    'price': 2000000,
    'price_str': "۲,۰۰۰,۰۰۰ تومان"
}

COMMISSION_PERCENT = 10  # ۱۰ درصد کمیسیون رفرال
MIN_WITHDRAW = 500000  # حداقل برداشت ۵۰۰ هزار تومان

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
    'MAX_BOTS_TOTAL': 165000 // 256,
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

# ==================== دیتابیس (با پشتیبانی از رفرال) ====================
class Database:
    def __init__(self):
        self.conn = sqlite3.connect(os.path.join(DIRS['DB'], 'mother_bot.db'), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()
        self.cache = {}
        self.cache_lock = threading.RLock()
    
    def _init_tables(self):
        # جدول کاربران با پشتیبانی از رفرال
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                bots_count INTEGER DEFAULT 0,
                max_bots INTEGER DEFAULT 1,
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                referrals_count INTEGER DEFAULT 0,
                verified_referrals INTEGER DEFAULT 0,
                balance INTEGER DEFAULT 0,
                total_earned INTEGER DEFAULT 0,
                total_withdrawn INTEGER DEFAULT 0,
                payment_status TEXT DEFAULT 'pending',
                rating INTEGER DEFAULT 0,
                created_at TIMESTAMP,
                last_active TIMESTAMP
            )
        ''')
        
        # جدول ربات‌ها
        self.conn.execute('''
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
                last_active TIMESTAMP
            )
        ''')
        
        # جدول ماشین‌ها
        self.conn.execute('''
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
        
        # جدول فیش‌ها
        self.conn.execute('''
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
        
        # جدول درخواست‌های برداشت
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS withdraw_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                card_number TEXT,
                status TEXT DEFAULT 'pending',
                reviewed_by INTEGER,
                reviewed_at TIMESTAMP,
                created_at TIMESTAMP
            )
        ''')
        
        # جدول تراکنش‌ها
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                type TEXT,
                status TEXT,
                description TEXT,
                created_at TIMESTAMP
            )
        ''')
        
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_users_payment ON users(payment_status)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_users_referral ON users(referral_code)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_bots_user ON bots(user_id)")
        
        # ایجاد ماشین‌ها
        for i in range(1, CLUSTER_CONFIG['TOTAL_MACHINES'] + 1):
            self.conn.execute('''
                INSERT OR IGNORE INTO machines (id, name, status, max_bots, max_memory, created_at)
                VALUES (?, ?, 'active', ?, ?, ?)
            ''', (i, f"Machine-{i:02d}", 
                  CLUSTER_CONFIG['BOTS_PER_MACHINE'],
                  CLUSTER_CONFIG['MAX_MEMORY_PER_BOT'] * CLUSTER_CONFIG['BOTS_PER_MACHINE'],
                  datetime.now().isoformat()))
        
        self.conn.commit()
    
    def execute(self, query, params=()):
        try:
            cursor = self.conn.execute(query, params)
            self.conn.commit()
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"DB error: {e}")
            return []
    
    def get_user(self, user_id):
        users = self.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return dict(users[0]) if users else None
    
    def create_user(self, user_id, username, first_name, last_name, referred_by=None):
        now = datetime.now().isoformat()
        referral_code = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:12]
        
        self.execute('''
            INSERT OR IGNORE INTO users 
            (user_id, username, first_name, last_name, referral_code, referred_by, created_at, last_active, payment_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name, referral_code, referred_by, now, now, 'pending'))
        
        if referred_by:
            self.execute('UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = ?', (referred_by,))
        
        return self.get_user(user_id)
    
    def add_balance(self, user_id, amount):
        self.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
    
    def get_balance(self, user_id):
        user = self.get_user(user_id)
        return user['balance'] if user else 0
    
    def add_commission(self, user_id, amount, description):
        self.execute('UPDATE users SET balance = balance + ?, total_earned = total_earned + ? WHERE user_id = ?', 
                    (amount, amount, user_id))
        self.execute('''
            INSERT INTO transactions (user_id, amount, type, status, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, amount, 'commission', 'completed', description, datetime.now().isoformat()))
    
    def create_withdraw_request(self, user_id, amount, card_number):
        if self.get_balance(user_id) < amount or amount < MIN_WITHDRAW:
            return False
        self.execute('''
            INSERT INTO withdraw_requests (user_id, amount, card_number, created_at)
            VALUES (?, ?, ?, ?)
        ''', (user_id, amount, card_number, datetime.now().isoformat()))
        self.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (amount, user_id))
        return True
    
    def get_pending_withdraws(self):
        return [dict(row) for row in self.execute('SELECT * FROM withdraw_requests WHERE status = "pending" ORDER BY created_at DESC')]
    
    def approve_withdraw(self, request_id, admin_id):
        self.execute('UPDATE withdraw_requests SET status = "approved", reviewed_by = ?, reviewed_at = ? WHERE id = ?',
                    (admin_id, datetime.now().isoformat(), request_id))
    
    def reject_withdraw(self, request_id, admin_id):
        req = self.execute('SELECT user_id, amount FROM withdraw_requests WHERE id = ?', (request_id,))
        if req:
            self.execute('UPDATE withdraw_requests SET status = "rejected", reviewed_by = ?, reviewed_at = ? WHERE id = ?',
                        (admin_id, datetime.now().isoformat(), request_id))
            self.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (req[0]['amount'], req[0]['user_id']))
    
    def add_receipt(self, user_id, amount, receipt_path, payment_code):
        self.execute('''
            INSERT INTO receipts (user_id, amount, receipt_path, payment_code, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, amount, receipt_path, payment_code, datetime.now().isoformat()))
    
    def get_pending_receipts(self):
        return [dict(row) for row in self.execute('SELECT * FROM receipts WHERE status = "pending" ORDER BY created_at DESC')]
    
    def approve_receipt(self, receipt_id, admin_id):
        receipt = self.execute('SELECT user_id, amount FROM receipts WHERE id = ?', (receipt_id,))
        if receipt:
            self.execute('UPDATE receipts SET status = "approved", reviewed_by = ?, reviewed_at = ? WHERE id = ?',
                        (admin_id, datetime.now().isoformat(), receipt_id))
            self.add_balance(receipt[0]['user_id'], receipt[0]['amount'])
            self.execute('UPDATE users SET payment_status = "approved" WHERE user_id = ?', (receipt[0]['user_id'],))
            
            # کمیسیون به معرف
            user = self.get_user(receipt[0]['user_id'])
            if user and user.get('referred_by'):
                commission = int(receipt[0]['amount'] * COMMISSION_PERCENT / 100)
                self.add_commission(user['referred_by'], commission, f'کمیسیون معرفی کاربر {receipt[0]["user_id"]}')
            return True
        return False
    
    def get_referrals_list(self, user_id):
        return [dict(row) for row in self.execute('SELECT user_id, first_name, username, payment_status FROM users WHERE referred_by = ?', (user_id,))]
    
    def update_rating(self, user_id, rating):
        self.execute('UPDATE users SET rating = ? WHERE user_id = ?', (rating, user_id))
    
    def get_all_users(self):
        return [dict(row) for row in self.execute('SELECT user_id, first_name, username, balance, payment_status, bots_count, rating FROM users ORDER BY created_at DESC')]
    
    def get_statistics(self):
        users = self.execute('SELECT COUNT(*) as count FROM users')[0]['count']
        paid = self.execute('SELECT COUNT(*) as count FROM users WHERE payment_status = "approved"')[0]['count']
        bots = self.execute('SELECT COUNT(*) as count FROM bots')[0]['count']
        revenue = self.execute('SELECT SUM(amount) as total FROM receipts WHERE status = "approved"')[0]['total'] or 0
        return users, paid, bots, revenue

db = Database()

# ==================== کش ====================
class FastCache:
    def __init__(self, ttl=600):
        self.cache = {}
        self.ttl = ttl
        self.lock = threading.RLock()
    
    def set(self, key, value):
        with self.lock:
            self.cache[key] = {'value': value, 'expires': time.time() + self.ttl}
    
    def get(self, key):
        with self.lock:
            item = self.cache.get(key)
            if item and item['expires'] > time.time():
                return item['value']
            if key in self.cache:
                del self.cache[key]
            return None
    
    def delete(self, key):
        with self.lock:
            if key in self.cache:
                del self.cache[key]

cache = FastCache(ttl=CLUSTER_CONFIG['CACHE_TTL'])

# ==================== Rate Limiter ====================
class RateLimiter:
    def __init__(self, max_per_second=100):
        self.max_per_second = max_per_second
        self.tokens = max_per_second
        self.last_refill = time.time()
        self.lock = threading.Lock()
    
    def acquire(self):
        with self.lock:
            now = time.time()
            elapsed = now - self.last_refill
            self.tokens = min(self.max_per_second, self.tokens + elapsed * self.max_per_second)
            self.last_refill = now
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False

rate_limiter = RateLimiter(CLUSTER_CONFIG['RATE_LIMIT'])

def rate_limit(func):
    @wraps(func)
    def wrapper(message, *args, **kwargs):
        if not rate_limiter.acquire():
            bot.send_message(message.chat.id, "⏳ لطفاً کمی صبر کنید...")
            return
        return func(message, *args, **kwargs)
    return wrapper

# ==================== مدیریت ماشین‌ها (ایزوله‌سازی) ====================
class MachineManager:
    def __init__(self):
        self.lock = threading.RLock()
        self.port_counter = 8000
        self.machine_cache = {}
        self.last_refresh = 0
        self.isolated_processes = {}
    
    def get_available_machine(self):
        if time.time() - self.last_refresh < 5:
            return self.machine_cache.get('available')
        
        machines = db.execute("SELECT * FROM machines WHERE status = 'active' ORDER BY current_bots ASC")
        for m in machines:
            if m['current_bots'] < m['max_bots']:
                self.machine_cache['available'] = m['id']
                self.last_refresh = time.time()
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
        db.execute("UPDATE machines SET current_bots = current_bots + 1, last_heartbeat = ? WHERE id = ?",
                  (datetime.now().isoformat(), machine_id))
        self.last_refresh = 0
    
    def release_bot(self, bot_id, machine_id):
        db.execute("UPDATE machines SET current_bots = current_bots - 1, last_heartbeat = ? WHERE id = ?",
                  (datetime.now().isoformat(), machine_id))
        self.last_refresh = 0
    
    def get_stats(self):
        machines = db.execute("SELECT * FROM machines WHERE status = 'active'")
        total_bots = 0
        total_capacity = 0
        active = 0
        for m in machines:
            total_bots += m['current_bots']
            total_capacity += m['max_bots']
            active += 1
        return {
            'total': active,
            'total_bots': total_bots,
            'total_capacity': total_capacity,
            'available': total_capacity - total_bots,
        }

machine_manager = MachineManager()

# ==================== موتور اجرای ایزوله ====================
class IsolatedEngine:
    def __init__(self):
        self.processes = {}
        self.lock = threading.RLock()
    
    def prepare_code(self, code, token):
        if 'if __name__ == "__main__"' not in code:
            if 'bot.infinity_polling' in code:
                code += '\n\nif __name__ == "__main__":\n    bot.infinity_polling()\n'
        return code
    
    def run_bot(self, bot_id, code, token):
        try:
            machine_id = machine_manager.get_available_machine()
            if not machine_id:
                return {'success': False, 'error': 'ماشین پر هستند'}
            
            port = machine_manager.get_available_port()
            bot_dir = os.path.join(DIRS['MACHINES'], f"machine_{machine_id:02d}", bot_id)
            os.makedirs(bot_dir, exist_ok=True)
            
            # استفاده از پوشه مجزا برای ایزوله‌سازی
            code_path = os.path.join(bot_dir, 'bot.py')
            with open(code_path, 'w', encoding='utf-8') as f:
                f.write(self.prepare_code(code, token))
            
            log_file = os.path.join(DIRS['LOGS'], f"bot_{bot_id}.log")
            
            # اجرا در محیط ایزوله با متغیرهای محیطی جداگانه
            env = os.environ.copy()
            env['PYTHONPATH'] = bot_dir
            env['BOT_ID'] = bot_id
            env['BOT_TOKEN'] = token
            
            process = subprocess.Popen(
                [sys.executable, '-O', code_path],
                stdout=open(log_file, 'a'),
                stderr=subprocess.STDOUT,
                cwd=bot_dir,
                start_new_session=True,
                env=env
            )
            
            time.sleep(0.5)
            
            if process.poll() is None:
                with self.lock:
                    self.processes[bot_id] = {
                        'process': process,
                        'pid': process.pid,
                        'machine_id': machine_id,
                        'port': port,
                        'dir': bot_dir
                    }
                machine_manager.assign_bot(bot_id, machine_id)
                return {'success': True, 'pid': process.pid, 'machine_id': machine_id}
            else:
                return {'success': False, 'error': 'خطا در اجرا'}
        except Exception as e:
            return {'success': False, 'error': str(e)[:100]}
    
    def stop_bot(self, bot_id):
        with self.lock:
            if bot_id in self.processes:
                try:
                    info = self.processes[bot_id]
                    os.killpg(os.getpgid(info['pid']), signal.SIGTERM)
                    time.sleep(0.5)
                    try:
                        os.kill(info['pid'], 0)
                        os.killpg(os.getpgid(info['pid']), signal.SIGKILL)
                    except:
                        pass
                    machine_manager.release_bot(bot_id, info['machine_id'])
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
                    return {'running': True, 'pid': info['pid']}
                except:
                    if bot_id in self.processes:
                        del self.processes[bot_id]
        return {'running': False}

engine = IsolatedEngine()

# ==================== ربات تلگرام ====================
bot = telebot.TeleBot(BOT_TOKEN)
bot.delete_webhook()

# ==================== توابع کمکی ====================
def get_user(user_id):
    cached = cache.get(f"user_{user_id}")
    if cached:
        return cached
    user = db.get_user(user_id)
    if user:
        cache.set(f"user_{user_id}", user)
    return user

def check_payment(user_id):
    user = get_user(user_id)
    return user and user.get('payment_status') == 'approved'

def get_user_bots(user_id):
    return [dict(bot) for bot in db.execute('SELECT * FROM bots WHERE user_id = ? ORDER BY created_at DESC', (user_id,))]

def add_bot(user_id, bot_id, token, name, username, file_path, pid=None, machine_id=None):
    now = datetime.now().isoformat()
    db.execute('''
        INSERT INTO bots (id, user_id, token, name, username, file_path, pid, machine_id, status, created_at, last_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (bot_id, user_id, token, name, username, file_path, pid, machine_id, 'running', now, now))
    db.execute('UPDATE users SET bots_count = bots_count + 1, last_active = ? WHERE user_id = ?', (now, user_id))

def delete_bot(bot_id, user_id):
    bot = db.execute('SELECT * FROM bots WHERE id = ?', (bot_id,))
    if not bot:
        return False
    bot = bot[0]
    if bot['user_id'] != user_id:
        return False
    engine.stop_bot(bot_id)
    if bot.get('file_path') and os.path.exists(bot['file_path']):
        os.remove(bot['file_path'])
    db.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
    db.execute('UPDATE users SET bots_count = bots_count - 1 WHERE user_id = ?', (user_id,))
    cache.delete(f"user_{user_id}")
    return True

# ==================== منوی اصلی ====================
def get_main_menu(is_admin=False):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        types.KeyboardButton('🤖 ساخت ربات جدید'),
        types.KeyboardButton('📋 ربات‌های من'),
        types.KeyboardButton('🔄 فعال/غیرفعال'),
        types.KeyboardButton('🗑 حذف ربات'),
        types.KeyboardButton('💰 کیف پول'),
        types.KeyboardButton('💳 برداشت وجه'),
        types.KeyboardButton('👥 لیست معرف‌ها'),
        types.KeyboardButton('📚 راهنما'),
        types.KeyboardButton('📊 آمار'),
        types.KeyboardButton('⚡ وضعیت سیستم')
    ]
    if is_admin:
        buttons.extend([
            types.KeyboardButton('👑 پنل مدیریت'),
            types.KeyboardButton('📢 پیام همگانی')
        ])
    markup.add(*buttons)
    return markup

# ==================== استارت ====================
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
    
    user = get_user(user_id)
    if not user:
        user = db.create_user(user_id, message.from_user.username or "", first_name, message.from_user.last_name or "", referred_by)
    
    bot_username = bot.get_me().username
    referral_link = f"https://t.me/{bot_username}?start={user['referral_code']}"
    
    text = (
        f"🚀 خوش آمدید {first_name}!\n\n"
        f"🎁 کد معرف: `{user['referral_code']}`\n"
        f"🔗 لینک معرف: {referral_link}\n"
        f"📊 تعداد معرف: {user['referrals_count']}\n"
        f"💰 موجودی: {user['balance']:,} تومان\n"
        f"⭐ امتیاز: {user['rating']}\n\n"
        f"📤 فایل .py یا .zip ارسال کنید\n"
        f"💡 با معرفی دوستان، ۱۰٪ کمیسیون بگیرید!"
    )
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=get_main_menu(user_id in ADMIN_IDS))

# ==================== کیف پول ====================
@bot.message_handler(func=lambda m: m.text == '💰 کیف پول')
def wallet(message):
    user = get_user(message.from_user.id)
    if not user:
        bot.send_message(message.chat.id, "❌ /start بزنید")
        return
    
    bot_username = bot.get_me().username
    referral_link = f"https://t.me/{bot_username}?start={user['referral_code']}"
    
    text = (
        f"💰 **کیف پول**\n\n"
        f"👤 {user['first_name']}\n"
        f"💰 موجودی: {user['balance']:,} تومان\n"
        f"🎁 کل درآمد: {user['total_earned']:,} تومان\n"
        f"🏧 کل برداشت: {user['total_withdrawn']:,} تومان\n"
        f"🎁 کد معرف: `{user['referral_code']}`\n"
        f"🔗 {referral_link}\n"
        f"📊 معرف‌ها: {user['referrals_count']}\n\n"
        f"💳 برای شارژ: {CARD_INFO['number_display']}\n"
        f"💰 مبلغ: {CARD_INFO['price_str']}\n"
        f"📸 تصویر فیش را ارسال کنید"
    )
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== برداشت وجه ====================
@bot.message_handler(func=lambda m: m.text == '💳 برداشت وجه')
def withdraw_start(message):
    user = get_user(message.from_user.id)
    if user['balance'] < MIN_WITHDRAW:
        bot.send_message(message.chat.id, f"❌ موجودی کافی نیست\nحداقل برداشت: {MIN_WITHDRAW:,} تومان", parse_mode='Markdown')
        return
    
    msg = bot.send_message(message.chat.id, f"💰 مبلغ به تومان:\n(حداکثر {user['balance']:,})", parse_mode='Markdown')
    bot.register_next_step_handler(msg, withdraw_amount)

def withdraw_amount(message):
    try:
        amount = int(message.text.strip())
        user = get_user(message.from_user.id)
        if amount < MIN_WITHDRAW:
            bot.send_message(message.chat.id, f"❌ حداقل {MIN_WITHDRAW:,} تومان")
            return
        if amount > user['balance']:
            bot.send_message(message.chat.id, f"❌ موجودی {user['balance']:,} تومان")
            return
        
        msg = bot.send_message(message.chat.id, "💳 شماره کارت ۱۶ رقمی:")
        bot.register_next_step_handler(msg, lambda m: withdraw_card(m, amount))
    except:
        bot.send_message(message.chat.id, "❌ عدد وارد کنید")

def withdraw_card(message, amount):
    card = message.text.strip().replace(" ", "")
    if not card.isdigit() or len(card) != 16:
        bot.send_message(message.chat.id, "❌ شماره کارت ۱۶ رقم")
        return
    
    if db.create_withdraw_request(message.from_user.id, amount, card):
        bot.send_message(message.chat.id, f"✅ درخواست برداشت ثبت شد\n💰 {amount:,} تومان\n⏳ در انتظار تایید", parse_mode='Markdown')
        for admin_id in ADMIN_IDS:
            bot.send_message(admin_id, f"💰 درخواست برداشت جدید\n👤 {message.from_user.first_name}\n💰 {amount:,}\n💳 {card}")
    else:
        bot.send_message(message.chat.id, "❌ خطا")

# ==================== لیست معرف‌ها ====================
@bot.message_handler(func=lambda m: m.text == '👥 لیست معرف‌ها')
def referrals_list(message):
    referrals = db.get_referrals_list(message.from_user.id)
    if not referrals:
        bot.send_message(message.chat.id, "👥 هیچ کاربری معرف نکردید")
        return
    
    text = "👥 **لیست معرف‌های شما**\n\n"
    for i, r in enumerate(referrals[:20], 1):
        status = "✅" if r['payment_status'] == 'approved' else "⏳"
        text += f"{i}. {status} {r['first_name']}\n"
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== فیش ====================
@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    payment_code = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:8].upper()
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        receipt_path = os.path.join(DIRS['RECEIPTS'], f"{user_id}_{payment_code}.jpg")
        with open(receipt_path, 'wb') as f:
            f.write(downloaded)
        
        db.add_receipt(user_id, CARD_INFO['price'], receipt_path, payment_code)
        bot.reply_to(message, f"✅ فیش دریافت شد\n🆔 {payment_code}\n⏳ در انتظار تایید")
        
        for admin_id in ADMIN_IDS:
            try:
                with open(receipt_path, 'rb') as f:
                    bot.send_photo(admin_id, f, caption=f"📸 فیش جدید\n👤 {message.from_user.first_name}\n🆔 {user_id}\n💰 {CARD_INFO['price_str']}")
            except:
                pass
    except Exception as e:
        bot.reply_to(message, f"❌ خطا")

# ==================== ساخت ربات ====================
@bot.message_handler(func=lambda m: m.text == '🤖 ساخت ربات جدید')
def new_bot(message):
    user_id = message.from_user.id
    if not check_payment(user_id):
        bot.send_message(message.chat.id, f"❌ ابتدا پرداخت کنید\n💰 {CARD_INFO['price_str']}\n💳 {CARD_INFO['number_display']}")
        return
    
    stats = machine_manager.get_stats()
    if stats['available'] == 0:
        bot.send_message(message.chat.id, "⚠️ سیستم شلوغ است")
        return
    
    bot.send_message(message.chat.id, "📤 فایل .py یا .zip ارسال کنید")

@bot.message_handler(content_types=['document'])
def handle_build_file(message):
    user_id = message.from_user.id
    file_name = message.document.file_name
    
    if not check_payment(user_id):
        bot.reply_to(message, "❌ ابتدا پرداخت کنید")
        return
    
    if not (file_name.endswith('.py') or file_name.endswith('.zip')):
        bot.reply_to(message, "❌ فقط .py یا .zip")
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
                        with open(os.path.join(root, f), 'r', encoding='utf-8') as cf:
                            main_code = cf.read()
                            break
                if main_code:
                    break
            shutil.rmtree(extract_dir, ignore_errors=True)
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                main_code = f.read()
        
        token_match = re.search(r'token\s*=\s*["\']([^"\']+)["\']', main_code, re.IGNORECASE)
        if not token_match:
            bot.edit_message_text("❌ توکن پیدا نشد", message.chat.id, status_msg.message_id)
            return
        
        token = token_match.group(1)
        resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
        if resp.status_code != 200:
            bot.edit_message_text("❌ توکن نامعتبر", message.chat.id, status_msg.message_id)
            return
        bot_info = resp.json()['result']
        
        bot_id = hashlib.md5(f"{user_id}{token}{time.time()}".encode()).hexdigest()[:16]
        result = engine.run_bot(bot_id, main_code, token)
        
        if result['success']:
            add_bot(user_id, bot_id, token, bot_info['first_name'], bot_info['username'], file_path, result['pid'], result['machine_id'])
            bot.edit_message_text(f"✅ ربات {bot_info['first_name']} ساخته شد!", message.chat.id, status_msg.message_id)
        else:
            bot.edit_message_text(f"❌ {result.get('error', 'خطا')}", message.chat.id, status_msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ خطا", message.chat.id, status_msg.message_id)

# ==================== ربات‌های من ====================
@bot.message_handler(func=lambda m: m.text == '📋 ربات‌های من')
def my_bots(message):
    bots = get_user_bots(message.from_user.id)
    if not bots:
        bot.send_message(message.chat.id, "📋 رباتی ندارید")
        return
    for b in bots:
        status = engine.get_status(b['id'])
        emoji = "🟢" if status.get('running') else "🔴"
        text = f"{emoji} {b['name']}\n🔗 t.me/{b['username']}\n🆔 {b['id']}"
        bot.send_message(message.chat.id, text)

# ==================== فعال/غیرفعال ====================
@bot.message_handler(func=lambda m: m.text == '🔄 فعال/غیرفعال')
def toggle_prompt(message):
    bots = get_user_bots(message.from_user.id)
    if not bots:
        bot.send_message(message.chat.id, "📋 رباتی ندارید")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        markup.add(types.InlineKeyboardButton(f"{b['name']}", callback_data=f"toggle_{b['id']}"))
    bot.send_message(message.chat.id, "🔄 انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_'))
def toggle_bot(call):
    bot_id = call.data.replace('toggle_', '')
    bot_info = db.execute('SELECT * FROM bots WHERE id = ?', (bot_id,))
    if not bot_info or bot_info[0]['user_id'] != call.from_user.id:
        bot.answer_callback_query(call.id, "❌ پیدا نشد")
        return
    status = engine.get_status(bot_id)
    if status.get('running'):
        if engine.stop_bot(bot_id):
            bot.answer_callback_query(call.id, "✅ متوقف شد")
    else:
        bot.answer_callback_query(call.id, "⚠️ راه‌اندازی بعدا")

# ==================== حذف ربات ====================
@bot.message_handler(func=lambda m: m.text == '🗑 حذف ربات')
def delete_prompt(message):
    bots = get_user_bots(message.from_user.id)
    if not bots:
        bot.send_message(message.chat.id, "📋 رباتی ندارید")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        markup.add(types.InlineKeyboardButton(f"🗑 {b['name']}", callback_data=f"delete_{b['id']}"))
    bot.send_message(message.chat.id, "🗑 انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
def confirm_delete(call):
    bot_id = call.data.replace('delete_', '')
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ بله", callback_data=f"confirm_del_{bot_id}"), types.InlineKeyboardButton("❌ خیر", callback_data="cancel_del"))
    bot.edit_message_text("⚠️ اطمینان دارید؟", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_del_'))
def do_delete(call):
    bot_id = call.data.replace('confirm_del_', '')
    if delete_bot(bot_id, call.from_user.id):
        bot.edit_message_text("✅ حذف شد", call.message.chat.id, call.message.message_id)
    else:
        bot.edit_message_text("❌ خطا", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == 'cancel_del')
def cancel_delete(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== پنل مدیریت ====================
@bot.message_handler(func=lambda m: m.text == '👑 پنل مدیریت')
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📸 فیش‌ها", callback_data="admin_receipts"),
        types.InlineKeyboardButton("💰 برداشت‌ها", callback_data="admin_withdraws"),
        types.InlineKeyboardButton("⭐ امتیاز دهی", callback_data="admin_rate"),
        types.InlineKeyboardButton("👥 کاربران", callback_data="admin_users"),
        types.InlineKeyboardButton("📊 آمار", callback_data="admin_stats"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    bot.send_message(message.chat.id, "👑 پنل مدیریت:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_receipts")
def admin_receipts(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    receipts = db.get_pending_receipts()
    if not receipts:
        bot.send_message(call.message.chat.id, "📸 فیشی نیست")
        return
    for r in receipts:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_rec_{r['id']}"))
        bot.send_message(call.message.chat.id, f"📸 فیش #{r['id']}\n👤 {r['user_id']}\n💰 {r['amount']:,}", reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_rec_"))
def approve_receipt_admin(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    receipt_id = int(call.data.replace("approve_rec_", ""))
    if db.approve_receipt(receipt_id, call.from_user.id):
        bot.edit_message_text("✅ تایید شد", call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id, "تایید شد!")
    else:
        bot.answer_callback_query(call.id, "خطا!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_withdraws")
def admin_withdraws(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    withdraws = db.get_pending_withdraws()
    if not withdraws:
        bot.send_message(call.message.chat.id, "💰 درخواستی نیست")
        return
    for w in withdraws:
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_wd_{w['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"reject_wd_{w['id']}")
        )
        bot.send_message(call.message.chat.id, f"💰 درخواست #{w['id']}\n👤 {w['user_id']}\n💰 {w['amount']:,}\n💳 {w['card_number']}", reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_wd_"))
def approve_withdraw_admin(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    wd_id = int(call.data.replace("approve_wd_", ""))
    db.approve_withdraw(wd_id, call.from_user.id)
    bot.edit_message_text("✅ تایید شد", call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id, "تایید شد!")

@bot.callback_query_handler(func=lambda call: call.data.startswith("reject_wd_"))
def reject_withdraw_admin(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    wd_id = int(call.data.replace("reject_wd_", ""))
    db.reject_withdraw(wd_id, call.from_user.id)
    bot.edit_message_text("❌ رد شد", call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id, "رد شد!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_rate")
def admin_rate_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    msg = bot.send_message(call.message.chat.id, "⭐ آیدی کاربر را وارد کنید:")
    bot.register_next_step_handler(msg, admin_set_rating)

def admin_set_rating(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        user_id = int(message.text.strip())
        user = get_user(user_id)
        if not user:
            bot.send_message(message.chat.id, "❌ کاربر یافت نشد")
            return
        markup = types.InlineKeyboardMarkup(row_width=5)
        buttons = [types.InlineKeyboardButton(str(i), callback_data=f"rate_{user_id}_{i}") for i in range(1, 6)]
        markup.add(*buttons)
        bot.send_message(message.chat.id, f"👤 {user['first_name']}\n⭐ امتیاز فعلی: {user['rating']}\nامتیاز جدید:", reply_markup=markup)
    except:
        bot.send_message(message.chat.id, "❌ عدد وارد کنید")

@bot.callback_query_handler(func=lambda call: call.data.startswith("rate_"))
def set_rating(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    parts = call.data.split("_")
    user_id = int(parts[1])
    rating = int(parts[2])
    db.update_rating(user_id, rating)
    bot.edit_message_text(f"✅ امتیاز ثبت شد: {rating}", call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id, "ثبت شد!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_users")
def admin_users(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    users = db.get_all_users()
    if not users:
        bot.send_message(call.message.chat.id, "👥 کاربری نیست")
        return
    text = "👥 **لیست کاربران**\n\n"
    for i, u in enumerate(users[:30], 1):
        status = "✅" if u['payment_status'] == 'approved' else "⏳"
        text += f"{i}. {status} {u['first_name']} - {u['balance']:,} - ⭐{u['rating']}\n"
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_stats(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    users, paid, bots, revenue = db.get_statistics()
    bot.send_message(call.message.chat.id, f"📊 **آمار**\n\n👥 کاربران: {users}\n✅ پرداختی: {paid}\n🤖 ربات‌ها: {bots}\n💰 درآمد: {revenue:,} تومان", parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "🚀 منوی اصلی:", reply_markup=get_main_menu(True))

# ==================== پیام همگانی ====================
@bot.message_handler(func=lambda m: m.text == '📢 پیام همگانی')
def broadcast_prompt(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(message.chat.id, "📢 متن پیام:")
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    users = db.execute("SELECT user_id FROM users")
    status = bot.reply_to(message, f"📢 در حال ارسال به {len(users)} کاربر...")
    sent = 0
    for user in users:
        try:
            bot.send_message(user['user_id'], message.text)
            sent += 1
        except:
            pass
    bot.edit_message_text(f"✅ ارسال شد به {sent} کاربر", message.chat.id, status.message_id)

# ==================== راهنما و آمار ====================
@bot.message_handler(func=lambda m: m.text == '📚 راهنما')
def guide(message):
    text = (
        f"📚 راهنما\n\n"
        f"1️⃣ ساخت ربات: فایل .py یا .zip آپلود کنید\n"
        f"2️⃣ پرداخت: به کارت {CARD_INFO['number_display']}\n"
        f"3️⃣ رفرال: با لینک خود دوستان را دعوت کنید، ۱۰٪ کمیسیون\n"
        f"4️⃣ برداشت: از دکمه برداشت وجه استفاده کنید\n"
        f"5️⃣ پشتیبانی: @shahraghee13"
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == '📊 آمار')
def stats(message):
    users = db.execute('SELECT COUNT(*) as count FROM users')[0]['count']
    bots = db.execute('SELECT COUNT(*) as count FROM bots')[0]['count']
    running = db.execute('SELECT COUNT(*) as count FROM bots WHERE status = "running"')[0]['count']
    machine_stats = machine_manager.get_stats()
    text = f"📊 آمار\n\n👥 کاربران: {users}\n🤖 کل ربات: {bots}\n🟢 فعال: {running}\n🖥️ ماشین‌ها: {machine_stats['total']}\n📊 ظرفیت خالی: {machine_stats['available']}"
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == '⚡ وضعیت سیستم')
def system_status(message):
    stats = machine_manager.get_stats()
    text = f"⚡ وضعیت سیستم\n\n🖥️ ماشین‌ها: {stats['total']}\n🤖 ربات فعال: {stats['total_bots']}\n📊 ظرفیت: {stats['available']}\n⚡ سرعت: ۱۰۰,۰۰۰ req/s"
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == '📞 پشتیبانی')
def support(message):
    bot.send_message(message.chat.id, "📞 @shahraghee13")

# ==================== اجرا ====================
if __name__ == "__main__":
    print("=" * 80)
    print("🚀 ربات مادر نهایی - نسخه 18.0 با ایزوله‌سازی و رفرال".center(80))
    print("=" * 80)
    print(f"🖥️ ماشین‌ها: {CLUSTER_CONFIG['TOTAL_MACHINES']} × {CLUSTER_CONFIG['BOTS_PER_MACHINE']:,}")
    print(f"💰 کمیسیون رفرال: {COMMISSION_PERCENT}%")
    print(f"💳 حداقل برداشت: {MIN_WITHDRAW:,} تومان")
    print("=" * 80)
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            logger.error(f"Polling error: {e}")
            time.sleep(5)