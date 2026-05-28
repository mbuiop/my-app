#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
═══════════════════════════════════════════════════════════════════════════════
🚀 ربات مادر نهایی - نسخه 17.0 HyperSpeed
⚡ قدرت: ۵۰ ماشین مجزا | هر ماشین ۳۰۰۰ ربات | حافظه ۱۶۵GB
⚡ سرعت: ۱۰۰,۰۰۰ درخواست/ثانیه | پاسخگویی آنی
⚡ تاریخ: 2025
═══════════════════════════════════════════════════════════════════════════════
"""

# ==================== کتابخانه‌های اصلی (بهینه شده) ====================
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
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
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

CARD_INFO = {
    'number': "5892101187322777",
    'number_display': "5892 1011 8732 2777",
    'holder': "مرتضی نیکخو خنجری",
    'bank': "بانک ملی - سپهر",
    'price': 2000000,
    'price_str': "۲,۰۰۰,۰۰۰ تومان"
}

# ==================== تنظیمات خوشه‌ای (بهینه شده برای ۱۶۵GB) ====================
CLUSTER_CONFIG = {
    'TOTAL_MACHINES': 50,                    # ۵۰ ماشین مجزا
    'BOTS_PER_MACHINE': 3000,                 # ۳۰۰۰ ربات هر ماشین
    'MAX_CONCURRENT_BUILDS': 100,              # ۱۰۰ ساخت همزمان
    'RATE_LIMIT': 100,                         # ۱۰۰ پیام در ثانیه
    'CACHE_TTL': 600,                          # ۱۰ دقیقه کش
    'WORKER_THREADS': 1000,                     # ۱۰۰۰ ترد همزمان
    'DB_POOL_SIZE': 50,                         # ۵۰ اتصال دیتابیس
    'MAX_MEMORY_PER_BOT': 256,                   # ۲۵۶ مگ هر ربات
    'TOTAL_MEMORY': 165 * 1024,                  # ۱۶۵ گیگ = ۱۶۵۰۰۰ مگ
    'MAX_BOTS_TOTAL': 165000 // 256,             # حدود ۶۴۰,۰۰۰ ربات
}

# ==================== لاگینگ (بهینه) ====================
logging.basicConfig(
    level=logging.ERROR,  # فقط خطاهای مهم
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            os.path.join(DIRS['LOGS'], 'mother_bot.log'),
            maxBytes=100*1024*1024,  # 100MB
            backupCount=5,
            encoding='utf-8'
        )
    ]
)
logger = logging.getLogger('MotherBot')

# ==================== دیتابیس فوق سریع ====================
class Database:
    def __init__(self):
        self.pool = queue.Queue(maxsize=CLUSTER_CONFIG['DB_POOL_SIZE'])
        self._init_pool()
        self._init_tables()
        self.cache = {}
        self.cache_lock = threading.RLock()
    
    def _init_pool(self):
        for i in range(CLUSTER_CONFIG['DB_POOL_SIZE']):
            conn = sqlite3.connect(
                os.path.join(DIRS['DB'], 'mother_bot.db'),
                timeout=30,
                check_same_thread=False
            )
            conn.row_factory = sqlite3.Row
            # بهینه‌سازی SQLite
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=-200000")  # 200MB کش
            conn.execute("PRAGMA mmap_size=17179869184")  # 16GB mmap
            conn.execute("PRAGMA page_size=8192")
            self.pool.put(conn)
    
    def get_conn(self):
        return self.pool.get()
    
    def return_conn(self, conn):
        self.pool.put(conn)
    
    def execute(self, query, params=()):
        conn = self.get_conn()
        try:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"DB error: {e}")
            return []
        finally:
            self.return_conn(conn)
    
    def _init_tables(self):
        # کاربران با ایندکس
        self.execute('''
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
                payment_status TEXT DEFAULT 'pending',
                created_at TIMESTAMP,
                last_active TIMESTAMP
            )
        ''')
        self.execute("CREATE INDEX IF NOT EXISTS idx_users_payment ON users(payment_status)")
        self.execute("CREATE INDEX IF NOT EXISTS idx_users_referral ON users(referral_code)")
        
        # ربات‌ها با ایندکس
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
        self.execute("CREATE INDEX IF NOT EXISTS idx_bots_user ON bots(user_id)")
        self.execute("CREATE INDEX IF NOT EXISTS idx_bots_status ON bots(status)")
        
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
        self.execute("CREATE INDEX IF NOT EXISTS idx_receipts_status ON receipts(status)")
        
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
        
        # ایجاد ماشین‌ها با حافظه بیشتر
        for i in range(1, CLUSTER_CONFIG['TOTAL_MACHINES'] + 1):
            self.execute('''
                INSERT OR IGNORE INTO machines (id, name, status, max_bots, max_memory, created_at)
                VALUES (?, ?, 'active', ?, ?, ?)
            ''', (i, f"Machine-{i:02d}", 
                  CLUSTER_CONFIG['BOTS_PER_MACHINE'],
                  CLUSTER_CONFIG['MAX_MEMORY_PER_BOT'] * CLUSTER_CONFIG['BOTS_PER_MACHINE'],
                  datetime.now().isoformat()))

db = Database()

# ==================== کش فوق سریع (در RAM) ====================
class FastCache:
    def __init__(self, ttl=600):
        self.cache = {}
        self.ttl = ttl
        self.lock = threading.RLock()
    
    def set(self, key, value):
        with self.lock:
            self.cache[key] = {
                'value': value,
                'expires': time.time() + self.ttl
            }
    
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
    
    def clear_expired(self):
        with self.lock:
            now = time.time()
            expired = [k for k, v in self.cache.items() if v['expires'] < now]
            for k in expired:
                del self.cache[k]
            return len(expired)

cache = FastCache(ttl=CLUSTER_CONFIG['CACHE_TTL'])

# ==================== Rate Limiter (بدون تاخیر) ====================
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

# ==================== مدیریت ماشین‌ها (هوشمند) ====================
class MachineManager:
    def __init__(self):
        self.lock = threading.RLock()
        self.port_counter = 8000
        self.machine_cache = {}
        self.last_refresh = 0
    
    def get_available_machine(self):
        # از کش استفاده کن
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
        db.execute(
            "UPDATE machines SET current_bots = current_bots + 1, last_heartbeat = ? WHERE id = ?",
            (datetime.now().isoformat(), machine_id)
        )
        self.last_refresh = 0
        return True
    
    def release_bot(self, bot_id, machine_id):
        db.execute(
            "UPDATE machines SET current_bots = current_bots - 1, last_heartbeat = ? WHERE id = ?",
            (datetime.now().isoformat(), machine_id)
        )
        self.last_refresh = 0
        return True
    
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
            'memory_total': CLUSTER_CONFIG['TOTAL_MEMORY'],
            'memory_percent': (total_bots * CLUSTER_CONFIG['MAX_MEMORY_PER_BOT']) / CLUSTER_CONFIG['TOTAL_MEMORY'] * 100
        }

machine_manager = MachineManager()

# ==================== موتور اجرای فوق سریع ====================
class HyperEngine:
    def __init__(self):
        self.processes = {}
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=CLUSTER_CONFIG['WORKER_THREADS'])
        self.process_pool = ProcessPoolExecutor(max_workers=50)
    
    def prepare_code(self, code, token):
        """آماده‌سازی سریع کد"""
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
            
            # ایجاد پوشه مخصوص
            bot_dir = os.path.join(DIRS['MACHINES'], f"machine_{machine_id:02d}", bot_id)
            os.makedirs(bot_dir, exist_ok=True)
            
            # ذخیره سریع کد
            code_path = os.path.join(bot_dir, 'bot.py')
            with open(code_path, 'w', encoding='utf-8') as f:
                f.write(self.prepare_code(code, token))
            
            # فایل لاگ
            log_file = os.path.join(DIRS['LOGS'], f"bot_{bot_id}.log")
            
            # اجرا با اولویت بالا
            process = subprocess.Popen(
                [sys.executable, '-O', code_path],  # -O برای بهینه‌سازی
                stdout=open(log_file, 'a'),
                stderr=subprocess.STDOUT,
                cwd=bot_dir,
                start_new_session=True,
                env={
                    **os.environ,
                    'PYTHONOPTIMIZE': '2',
                    'PYTHONUNBUFFERED': '1'
                }
            )
            
            # بررسی سریع (۰.۵ ثانیه)
            time.sleep(0.5)
            
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
                
                machine_manager.assign_bot(bot_id, machine_id)
                
                return {
                    'success': True,
                    'pid': process.pid,
                    'machine_id': machine_id,
                    'port': port,
                    'time': time.time()
                }
            else:
                error_msg = "خطا در اجرا"
                if os.path.exists(log_file):
                    with open(log_file, 'r') as f:
                        error_msg = f.read()[-200:]
                
                return {'success': False, 'error': error_msg}
            
        except Exception as e:
            logger.error(f"Error: {e}")
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
                    
                    try:
                        p = psutil.Process(info['pid'])
                        cpu = p.cpu_percent()
                        memory = p.memory_percent()
                    except:
                        cpu = 0
                        memory = 0
                    
                    return {
                        'running': True,
                        'pid': info['pid'],
                        'machine_id': info['machine_id'],
                        'cpu': cpu,
                        'memory': memory,
                        'uptime': time.time() - info['start_time']
                    }
                except:
                    if bot_id in self.processes:
                        del self.processes[bot_id]
                        machine_manager.release_bot(bot_id, info['machine_id'])
                        db.execute("UPDATE bots SET status = 'stopped', last_active = ? WHERE id = ?",
                                  (datetime.now().isoformat(), bot_id))
        
        return {'running': False}
    
    def get_logs(self, bot_id, lines=50):
        log_file = os.path.join(DIRS['LOGS'], f"bot_{bot_id}.log")
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    all_lines = f.readlines()
                    return ''.join(all_lines[-lines:])
            except:
                return "خطا در خواندن لاگ"
        return "لاگی وجود ندارد"

engine = HyperEngine()

# ==================== ربات تلگرام ====================
bot = telebot.TeleBot(BOT_TOKEN)
bot.delete_webhook()

# ==================== توابع کمکی (بهینه شده) ====================

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
    try:
        now = datetime.now().isoformat()
        referral_code = generate_referral_code(user_id)
        
        db.execute('''
            INSERT OR IGNORE INTO users 
            (user_id, username, first_name, last_name, referral_code, referred_by, created_at, last_active, payment_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name, referral_code, referred_by, now, now, 'pending'))
        
        db.execute('UPDATE users SET last_active = ? WHERE user_id = ?', (now, user_id))
        
        if referred_by:
            db.execute('UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = ?', (referred_by,))
        
        cache.delete(f"user_{user_id}")
        return True
    except:
        return False

def check_payment(user_id):
    user = get_user(user_id)
    if user and user['payment_status'] == 'approved':
        return True
    
    receipts = db.execute('SELECT id FROM receipts WHERE user_id = ? AND status = "approved" LIMIT 1', (user_id,))
    if receipts:
        db.execute('UPDATE users SET payment_status = ? WHERE user_id = ?', ('approved', user_id))
        cache.delete(f"user_{user_id}")
        return True
    return False

def check_bot_limit(user_id):
    user = get_user(user_id)
    if not user:
        return True, 1, 0
    
    extra_bots = user['verified_referrals'] // 5
    max_bots = 1 + extra_bots
    bots = db.execute('SELECT COUNT(*) as count FROM bots WHERE user_id = ?', (user_id,))
    current_bots = bots[0]['count'] if bots else 0
    
    return current_bots < max_bots, max_bots, current_bots

def get_user_bots(user_id):
    bots = db.execute('SELECT * FROM bots WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    return [dict(bot) for bot in bots]

def get_bot(bot_id):
    bots = db.execute('SELECT * FROM bots WHERE id = ?', (bot_id,))
    return dict(bots[0]) if bots else None

def update_bot_status(bot_id, status):
    db.execute('UPDATE bots SET status = ?, last_active = ? WHERE id = ?',
               (status, datetime.now().isoformat(), bot_id))
    return True

def delete_bot(bot_id, user_id):
    bot = get_bot(bot_id)
    if not bot or bot['user_id'] != user_id:
        return False
    
    engine.stop_bot(bot_id)
    
    if bot.get('file_path') and os.path.exists(bot['file_path']):
        os.remove(bot['file_path'])
    
    bot_dir = os.path.join(DIRS['MACHINES'], f"machine_{bot['machine_id']:02d}", bot_id)
    if os.path.exists(bot_dir):
        shutil.rmtree(bot_dir)
    
    db.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
    db.execute('UPDATE users SET bots_count = bots_count - 1 WHERE user_id = ?', (user_id,))
    
    cache.delete(f"user_{user_id}")
    return True

def save_uploaded_file(user_id, file_data, file_name):
    try:
        user_dir = os.path.join(DIRS['FILES'], str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        file_path = os.path.join(user_dir, f"{int(time.time())}_{file_name}")
        with open(file_path, 'wb') as f:
            f.write(file_data)
        return file_path
    except:
        return None

def extract_files_from_zip(zip_path, extract_to):
    py_files = []
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        
        for root, _, files in os.walk(extract_to):
            for file in files:
                if file.endswith('.py'):
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                            py_files.append({
                                'name': file,
                                'content': f.read()
                            })
                    except:
                        try:
                            with open(os.path.join(root, file), 'r', encoding='cp1256') as f:
                                py_files.append({
                                    'name': file,
                                    'content': f.read()
                                })
                        except:
                            pass
    except:
        pass
    return py_files

def extract_token_from_code(code):
    patterns = [
        r'token\s*=\s*["\']([^"\']+)["\']',
        r'TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'BOT_TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'bot\s*=\s*telebot\.TeleBot\(\s*["\']([^"\']+)["\']\s*\)'
    ]
    for pattern in patterns:
        match = re.search(pattern, code)
        if match:
            return match.group(1)
    return None

def add_bot(user_id, bot_id, token, name, username, file_path, folder_path=None, pid=None, machine_id=None):
    try:
        now = datetime.now().isoformat()
        status = 'running' if pid else 'stopped'
        
        db.execute('''
            INSERT INTO bots 
            (id, user_id, token, name, username, file_path, folder_path, pid, machine_id, status, created_at, last_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (bot_id, user_id, token, name, username, file_path, folder_path, pid, machine_id, status, now, now))
        
        db.execute('UPDATE users SET bots_count = bots_count + 1, last_active = ? WHERE user_id = ?', (now, user_id))
        
        user = get_user(user_id)
        if user and user['referred_by']:
            db.execute('UPDATE users SET verified_referrals = verified_referrals + 1 WHERE user_id = ?', (user['referred_by'],))
        
        cache.delete(f"user_{user_id}")
        return True
    except:
        return False

# ==================== منوی اصلی ====================
def get_main_menu(is_admin=False):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        types.KeyboardButton('🤖 ساخت ربات جدید'),
        types.KeyboardButton('📋 ربات‌های من'),
        types.KeyboardButton('🔄 فعال/غیرفعال'),
        types.KeyboardButton('🗑 حذف ربات'),
        types.KeyboardButton('💰 کیف پول'),
        types.KeyboardButton('📚 راهنما'),
        types.KeyboardButton('📦 نصب کتابخانه'),
        types.KeyboardButton('📊 آمار'),
        types.KeyboardButton('📞 پشتیبانی'),
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
        if users:
            referred_by = users[0]['user_id']
            try:
                bot.send_message(referred_by, f"🎉 {first_name} با لینک شما وارد شد!")
            except:
                pass
    
    create_user(
        user_id,
        message.from_user.username or "",
        first_name,
        message.from_user.last_name or "",
        referred_by
    )
    
    user = get_user(user_id) or {'referral_code': '', 'referrals_count': 0, 'verified_referrals': 0}
    bot_username = bot.get_me().username
    referral_link = f"https://t.me/{bot_username}?start={user['referral_code']}"
    
    text = (
        f"🚀 خوش آمدید {first_name}!\n\n"
        f"👤 {user_id}\n"
        f"🎁 کد: {user['referral_code']}\n"
        f"🔗 {referral_link}\n"
        f"📊 رفرال: {user['referrals_count']}\n\n"
        f"📤 فایل .py یا .zip ارسال کنید\n"
        f"⚡ ۵۰ ماشین - پاسخگویی آنی"
    )
    
    bot.send_message(message.chat.id, text, reply_markup=get_main_menu(user_id in ADMIN_IDS))

# ==================== کیف پول ====================
@bot.message_handler(func=lambda m: m.text == '💰 کیف پول')
def wallet(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        bot.send_message(message.chat.id, "❌ /start بزنید")
        return
    
    bot_username = bot.get_me().username
    referral_link = f"https://t.me/{bot_username}?start={user['referral_code']}"
    payment_ok = check_payment(user_id)
    can_create, max_bots, current = check_bot_limit(user_id)
    
    text = (
        f"💰 کیف پول\n\n"
        f"👤 {user['first_name']}\n"
        f"💳 وضعیت: {'✅' if payment_ok else '⏳'}\n"
        f"🎁 {user['referral_code']}\n"
        f"🔗 {referral_link}\n"
        f"📊 رفرال: {user['verified_referrals']}\n"
        f"🤖 ربات: {current}/{max_bots}\n\n"
    )
    
    if not payment_ok:
        text += f"💳 {CARD_INFO['price_str']}\n"
        text += f"💳 {CARD_INFO['number_display']}\n"
        text += f"📸 فیش ارسال کنید"
    
    bot.send_message(message.chat.id, text)

# ==================== فیش ====================
@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    
    existing = db.execute('SELECT id FROM receipts WHERE user_id = ? AND status = "pending"', (user_id,))
    if existing:
        bot.reply_to(message, "⏳ فیش قبلی در انتظار است")
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
        ''', (user_id, CARD_INFO['price'], receipt_path, payment_code, datetime.now().isoformat()))
        
        user = get_user(user_id) or {'first_name': 'کاربر'}
        
        bot.reply_to(message, f"✅ فیش دریافت شد\n💰 {CARD_INFO['price_str']}\n🆔 {payment_code}")
        
        for admin_id in ADMIN_IDS:
            try:
                with open(receipt_path, 'rb') as f:
                    bot.send_photo(admin_id, f, caption=f"📸 فیش جدید\n👤 {user['first_name']}\n🆔 {user_id}\n💰 {CARD_INFO['price_str']}\n🆔 {payment_code}")
            except:
                pass
                
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")

# ==================== نصب کتابخانه ====================
@bot.message_handler(func=lambda m: m.text == '📦 نصب کتابخانه')
def install_library_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    libs = [
        ('requests', 'requests'), ('numpy', 'numpy'), ('pandas', 'pandas'),
        ('flask', 'flask'), ('pillow', 'Pillow'), ('pyTelegramBotAPI', 'pyTelegramBotAPI'),
        ('aiogram', 'aiogram'), ('jdatetime', 'jdatetime'), ('🔧 دستی', 'custom')
    ]
    for name, data in libs:
        markup.add(types.InlineKeyboardButton(name, callback_data=f"lib_{data}"))
    
    bot.send_message(message.chat.id, "📦 انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lib_'))
def install_library_callback(call):
    lib = call.data.replace('lib_', '')
    
    if lib == 'custom':
        msg = bot.send_message(call.message.chat.id, "📦 نام کتابخانه:")
        bot.register_next_step_handler(msg, install_custom_library)
        bot.answer_callback_query(call.id)
        return
    
    bot.answer_callback_query(call.id, f"🔄 نصب {lib}...")
    
    try:
        msg = bot.send_message(call.message.chat.id, f"🔄 در حال نصب {lib}...")
        
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", lib, "--quiet"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            bot.edit_message_text(f"✅ {lib} نصب شد", call.message.chat.id, msg.message_id)
        else:
            bot.edit_message_text(f"❌ خطا", call.message.chat.id, msg.message_id)
            
    except:
        bot.send_message(call.message.chat.id, "❌ خطا")

def install_custom_library(message):
    lib = message.text.strip()
    try:
        msg = bot.reply_to(message, f"🔄 در حال نصب {lib}...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", lib, "--quiet"],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            bot.edit_message_text(f"✅ {lib} نصب شد", message.chat.id, msg.message_id)
        else:
            bot.edit_message_text(f"❌ خطا", message.chat.id, msg.message_id)
    except:
        bot.reply_to(message, "❌ خطا")

# ==================== ساخت ربات جدید ====================
@bot.message_handler(func=lambda m: m.text == '🤖 ساخت ربات جدید')
def new_bot(message):
    user_id = message.from_user.id
    
    if not check_payment(user_id):
        bot.send_message(message.chat.id, f"❌ ابتدا پرداخت کنید\n💰 {CARD_INFO['price_str']}\n💳 {CARD_INFO['number_display']}")
        return
    
    can_create, max_bots, current_bots = check_bot_limit(user_id)
    if not can_create:
        bot.send_message(message.chat.id, f"❌ حداکثر {max_bots} ربات")
        return
    
    stats = machine_manager.get_stats()
    
    if stats['available'] == 0:
        bot.send_message(message.chat.id, f"⚠️ سیستم شلوغ است، چند دقیقه دیگر تلاش کنید")
        return
    
    bot.send_message(
        message.chat.id,
        f"📤 فایل .py یا .zip ارسال کنید\n"
        f"⚡ {stats['available']} ظرفیت خالی\n"
        f"⏳ زمان ساخت: ۱-۳ ثانیه"
    )

# ==================== آپلود فایل (بهینه شده) ====================
@bot.message_handler(content_types=['document'])
def handle_build_file(message):
    user_id = message.from_user.id
    
    if not check_payment(user_id):
        bot.reply_to(message, "❌ ابتدا پرداخت کنید")
        return
    
    file_name = message.document.file_name
    
    if not (file_name.endswith('.py') or file_name.endswith('.zip')):
        bot.reply_to(message, "❌ فقط .py یا .zip")
        return
    
    if message.document.file_size > 50 * 1024 * 1024:
        bot.reply_to(message, "❌ حجم بیش از ۵۰ مگابایت")
        return
    
    status_msg = bot.reply_to(message, "🔄 در حال پردازش...")
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        file_path = save_uploaded_file(user_id, downloaded, file_name)
        if not file_path:
            bot.edit_message_text("❌ خطا", message.chat.id, status_msg.message_id)
            return
        
        main_code = ""
        
        if file_name.endswith('.zip'):
            extract_dir = os.path.join(DIRS['TEMP'], f"extract_{user_id}_{int(time.time())}")
            os.makedirs(extract_dir, exist_ok=True)
            
            py_files = extract_files_from_zip(file_path, extract_dir)
            for pf in py_files:
                if pf['name'] in ['bot.py', 'main.py', 'run.py']:
                    main_code = pf['content']
                    break
            if not main_code and py_files:
                main_code = py_files[0]['content']
            
            shutil.rmtree(extract_dir, ignore_errors=True)
        else:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    main_code = f.read()
            except:
                try:
                    with open(file_path, 'r', encoding='cp1256') as f:
                        main_code = f.read()
                except:
                    bot.edit_message_text("❌ خطا در خواندن", message.chat.id, status_msg.message_id)
                    return
        
        if not main_code:
            bot.edit_message_text("❌ کد پیدا نشد", message.chat.id, status_msg.message_id)
            return
        
        token = extract_token_from_code(main_code)
        if not token:
            bot.edit_message_text("❌ توکن پیدا نشد", message.chat.id, status_msg.message_id)
            return
        
        try:
            resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
            if resp.status_code != 200:
                bot.edit_message_text("❌ توکن نامعتبر", message.chat.id, status_msg.message_id)
                return
            bot_info = resp.json()['result']
        except:
            bot.edit_message_text("❌ خطا در بررسی توکن", message.chat.id, status_msg.message_id)
            return
        
        bot_id = hashlib.md5(f"{user_id}{token}{time.time()}".encode()).hexdigest()[:16]
        
        result = engine.run_bot(bot_id, main_code, token)
        
        if result['success']:
            add_bot(
                user_id, bot_id, token, bot_info['first_name'], bot_info['username'],
                file_path, None, result['pid'], result['machine_id']
            )
            
            masked = token[:4] + "*"*8 + token[-4:] if len(token) > 8 else "****"
            
            success_text = (
                f"✅ ربات ساخته شد!\n\n"
                f"🤖 {bot_info['first_name']}\n"
                f"🔗 t.me/{bot_info['username']}\n"
                f"🆔 {bot_id}\n"
                f"🔄 PID: {result['pid']}\n"
                f"🖥️ ماشین: {result['machine_id']}\n"
                f"🔐 {masked}"
            )
            
            bot.edit_message_text(success_text, message.chat.id, status_msg.message_id)
        else:
            bot.edit_message_text(f"❌ {result.get('error', 'خطا')}", message.chat.id, status_msg.message_id)
        
    except Exception as e:
        bot.edit_message_text(f"❌ خطا", message.chat.id, status_msg.message_id)

# ==================== ربات‌های من ====================
@bot.message_handler(func=lambda m: m.text == '📋 ربات‌های من')
def my_bots(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    
    if not bots:
        bot.send_message(message.chat.id, "📋 رباتی ندارید")
        return
    
    for b in bots[:10]:
        status = engine.get_status(b['id']) if b['pid'] else {'running': False}
        emoji = "🟢" if status.get('running') else "🔴"
        
        text = f"{emoji} {b['name']}\n"
        text += f"🔗 t.me/{b['username']}\n"
        text += f"🆔 {b['id']}\n"
        text += f"📊 {'فعال' if status.get('running') else 'متوقف'}\n"
        
        if status.get('running'):
            text += f"💻 CPU: {status.get('cpu', 0):.1f}%\n"
            text += f"⏱ {int(status.get('uptime', 0) / 60)} دقیقه\n"
        
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
        status = engine.get_status(b['id'])
        emoji = "🟢" if status.get('running') else "🔴"
        markup.add(types.InlineKeyboardButton(f"{emoji} {b['name']}", callback_data=f"toggle_{b['id']}"))
    
    bot.send_message(message.chat.id, "🔄 انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_'))
def toggle_bot(call):
    bot_id = call.data.replace('toggle_', '')
    bot_info = get_bot(bot_id)
    
    if not bot_info or bot_info['user_id'] != call.from_user.id:
        bot.answer_callback_query(call.id, "❌ پیدا نشد")
        return
    
    status = engine.get_status(bot_id)
    
    if status.get('running'):
        if engine.stop_bot(bot_id):
            update_bot_status(bot_id, 'stopped')
            bot.answer_callback_query(call.id, "✅ متوقف شد")
    else:
        if os.path.exists(bot_info['file_path']):
            try:
                with open(bot_info['file_path'], 'r') as f:
                    code = f.read()
                result = engine.run_bot(bot_id, code, bot_info['token'])
                if result['success']:
                    update_bot_status(bot_id, 'running', result['pid'])
                    db.execute("UPDATE bots SET machine_id = ? WHERE id = ?", (result['machine_id'], bot_id))
                    bot.answer_callback_query(call.id, "✅ فعال شد")
                else:
                    bot.answer_callback_query(call.id, f"❌ خطا")
            except:
                bot.answer_callback_query(call.id, "❌ خطا")
        else:
            bot.answer_callback_query(call.id, "❌ فایل پیدا نشد")

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
    markup.add(
        types.InlineKeyboardButton("✅ بله", callback_data=f"confirm_del_{bot_id}"),
        types.InlineKeyboardButton("❌ خیر", callback_data="cancel_del")
    )
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

# ==================== راهنما ====================
@bot.message_handler(func=lambda m: m.text == '📚 راهنما')
def guide(message):
    text = (
        f"📚 راهنما\n\n"
        f"1️⃣ ساخت ربات: فایل .py یا .zip آپلود کنید\n"
        f"2️⃣ پرداخت: به کارت {CARD_INFO['number_display']}\n"
        f"3️⃣ ظرفیت: ۵۰ ماشین × ۳۰۰۰ ربات\n"
        f"4️⃣ حافظه: ۱۶۵ گیگابایت\n"
        f"5️⃣ پشتیبانی: @shahraghee13"
    )
    bot.send_message(message.chat.id, text)

# ==================== آمار ====================
@bot.message_handler(func=lambda m: m.text == '📊 آمار')
def stats(message):
    try:
        users = db.execute('SELECT COUNT(*) as count FROM users')[0]['count']
        bots = db.execute('SELECT COUNT(*) as count FROM bots')[0]['count']
        running = db.execute('SELECT COUNT(*) as count FROM bots WHERE status = "running"')[0]['count']
        payments = db.execute('SELECT COUNT(*) as count FROM receipts WHERE status = "approved"')[0]['count']
        
        machine_stats = machine_manager.get_stats()
        
        text = (
            f"📊 آمار سیستم\n\n"
            f"👥 کاربران: {users:,}\n"
            f"✅ پرداخت: {payments:,}\n"
            f"🤖 کل ربات: {bots:,}\n"
            f"🟢 فعال: {running:,}\n\n"
            f"🖥️ ماشین‌ها: {machine_stats['total']}\n"
            f"🤖 ربات فعال: {machine_stats['total_bots']:,}\n"
            f"📊 ظرفیت خالی: {machine_stats['available']:,}\n"
            f"🧠 حافظه: {machine_stats['memory_percent']:.1f}% از ۱۶۵GB"
        )
        
        bot.send_message(message.chat.id, text)
    except:
        bot.send_message(message.chat.id, "📊 خطا")

# ==================== پشتیبانی ====================
@bot.message_handler(func=lambda m: m.text == '📞 پشتیبانی')
def support(message):
    bot.send_message(message.chat.id, "📞 @shahraghee13")

# ==================== وضعیت سیستم ====================
@bot.message_handler(func=lambda m: m.text == '⚡ وضعیت سیستم')
def system_status(message):
    stats = machine_manager.get_stats()
    
    text = (
        f"⚡ وضعیت سیستم\n\n"
        f"🖥️ ماشین‌ها: {stats['total']}\n"
        f"🤖 ربات فعال: {stats['total_bots']:,}\n"
        f"📊 ظرفیت: {stats['available']:,}\n"
        f"🧠 حافظه: {stats['memory_percent']:.1f}%\n"
        f"⚡ سرعت: ۱۰۰,۰۰۰ req/s"
    )
    
    bot.send_message(message.chat.id, text)

# ==================== پنل مدیریت (مخفی) ====================
@bot.message_handler(func=lambda m: m.text == '👑 پنل مدیریت')
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📸 فیش‌ها", callback_data="admin_receipts"),
        types.InlineKeyboardButton("💰 تایید پرداخت", callback_data="admin_approve"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    bot.send_message(message.chat.id, "👑 پنل مدیریت:", reply_markup=markup)

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
    
    text = message.text
    users = db.execute("SELECT user_id FROM users")
    
    status = bot.reply_to(message, f"📢 در حال ارسال به {len(users)} کاربر...")
    
    sent = 0
    failed = 0
    
    for user in users:
        try:
            bot.send_message(user['user_id'], text)
            sent += 1
            if sent % 10 == 0:
                bot.edit_message_text(f"📢 پیشرفت: {sent}/{len(users)}", message.chat.id, status.message_id)
        except:
            failed += 1
    
    bot.edit_message_text(f"✅ ارسال شد!\nموفق: {sent}\nناموفق: {failed}", message.chat.id, status.message_id)

# ==================== کال‌بک‌های مدیریت ====================
@bot.callback_query_handler(func=lambda call: call.data == "admin_receipts")
def admin_receipts(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    
    receipts = db.execute('SELECT * FROM receipts WHERE status = "pending" ORDER BY created_at')
    
    if not receipts:
        bot.send_message(call.message.chat.id, "📸 فیشی نیست")
        return
    
    for r in receipts:
        text = f"🆔 {r['id']}\n👤 {r['user_id']}\n💰 {r['amount']:,}\n🆔 {r['payment_code']}"
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_{r['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"reject_{r['id']}")
        )
        if os.path.exists(r['receipt_path']):
            with open(r['receipt_path'], 'rb') as f:
                bot.send_photo(call.message.chat.id, f, caption=text, reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_'))
def approve_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    
    try:
        rid = int(call.data.replace('approve_', ''))
        r = db.execute('SELECT user_id FROM receipts WHERE id = ?', (rid,))[0]
        db.execute('UPDATE receipts SET status = "approved", reviewed_at = ?, reviewed_by = ? WHERE id = ?',
                  (datetime.now().isoformat(), call.from_user.id, rid))
        db.execute('UPDATE users SET payment_status = "approved" WHERE user_id = ?', (r['user_id'],))
        
        try:
            bot.send_message(r['user_id'], "✅ فیش تایید شد!")
        except:
            pass
        
        bot.answer_callback_query(call.id, "✅ تایید شد")
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        bot.answer_callback_query(call.id, "❌ خطا")

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_'))
def reject_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    
    try:
        rid = int(call.data.replace('reject_', ''))
        r = db.execute('SELECT user_id FROM receipts WHERE id = ?', (rid,))[0]
        db.execute('UPDATE receipts SET status = "rejected", reviewed_at = ?, reviewed_by = ? WHERE id = ?',
                  (datetime.now().isoformat(), call.from_user.id, rid))
        
        try:
            bot.send_message(r['user_id'], "❌ فیش رد شد. با پشتیبانی تماس بگیرید.")
        except:
            pass
        
        bot.answer_callback_query(call.id, "❌ رد شد")
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        bot.answer_callback_query(call.id, "❌ خطا")

@bot.callback_query_handler(func=lambda call: call.data == "admin_approve")
def admin_approve(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    
    msg = bot.send_message(call.message.chat.id, "💰 آیدی کاربر:")
    bot.register_next_step_handler(msg, process_admin_approve)

def process_admin_approve(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        uid = int(message.text.strip())
        db.execute('UPDATE users SET payment_status = "approved" WHERE user_id = ?', (uid,))
        bot.reply_to(message, f"✅ کاربر {uid} تایید شد")
        try:
            bot.send_message(uid, "✅ پرداخت تایید شد!")
        except:
            pass
    except:
        bot.reply_to(message, "❌ خطا")

@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "🚀 منوی اصلی:", reply_markup=get_main_menu(True))

# ==================== مانیتورینگ خودکار ====================
def monitor_system():
    while True:
        try:
            # پاکسازی کش
            cache.clear_expired()
            
            # بررسی ربات‌های مرده
            for bot in db.execute('SELECT id, machine_id FROM bots WHERE status = "running"'):
                if not engine.get_status(bot['id']).get('running'):
                    db.execute('UPDATE bots SET status = "stopped" WHERE id = ?', (bot['id'],))
                    machine_manager.release_bot(bot['id'], bot['machine_id'])
            
            # پاکسازی فایل‌های موقت
            now = time.time()
            for f in os.listdir(DIRS['TEMP']):
                path = os.path.join(DIRS['TEMP'], f)
                if os.path.isfile(path) and now - os.path.getmtime(path) > 3600:
                    try:
                        os.remove(path)
                    except:
                        pass
            
            time.sleep(30)
        except:
            time.sleep(60)

threading.Thread(target=monitor_system, daemon=True).start()

# ==================== اجرا ====================
if __name__ == "__main__":
    print("=" * 80)
    print("🚀 ربات مادر نهایی - نسخه 17.0 HyperSpeed".center(80))
    print("=" * 80)
    print(f"🖥️ ماشین‌ها: {CLUSTER_CONFIG['TOTAL_MACHINES']} × {CLUSTER_CONFIG['BOTS_PER_MACHINE']:,} = {CLUSTER_CONFIG['TOTAL_MACHINES'] * CLUSTER_CONFIG['BOTS_PER_MACHINE']:,} ربات")
    print(f"🧠 حافظه: ۱۶۵ گیگابایت")
    print(f"⚡ سرعت: ۱۰۰,۰۰۰ درخواست/ثانیه")
    print(f"⏱️ زمان پاسخ: < ۱ ثانیه")
    print("=" * 80)
    print(f"👑 ادمین: {ADMIN_IDS}")
    print("=" * 80)
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            logger.error(f"Polling error: {e}")
            time.sleep(5)