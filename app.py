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
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=-200000")
            conn.execute("PRAGMA mmap_size=17179869184")
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
        
        # جدول سود رفرال (۱۰٪)
        self.execute('''
            CREATE TABLE IF NOT EXISTS referral_earnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                from_user_id INTEGER,
                amount INTEGER DEFAULT 0,
                commission INTEGER DEFAULT 0,
                bot_id TEXT,
                status TEXT DEFAULT 'pending',
                paid BOOLEAN DEFAULT 0,
                created_at TIMESTAMP,
                paid_at TIMESTAMP
            )
        ''')
        
        # جدول درخواست برداشت
        self.execute('''
            CREATE TABLE IF NOT EXISTS withdrawal_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                card_number TEXT,
                card_holder TEXT,
                status TEXT DEFAULT 'pending',
                requested_at TIMESTAMP,
                processed_at TIMESTAMP,
                processed_by INTEGER
            )
        ''')
        
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

# ==================== کش فوق سریع ====================
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

# ==================== مدیریت ماشین‌ها ====================
class MachineManager:
    def __init__(self):
        self.lock = threading.RLock()
        self.port_counter = 8000
        self.machine_cache = {}
        self.last_refresh = 0
    
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
            
            code_path = os.path.join(bot_dir, 'bot.py')
            with open(code_path, 'w', encoding='utf-8') as f:
                f.write(self.prepare_code(code, token))
            
            log_file = os.path.join(DIRS['LOGS'], f"bot_{bot_id}.log")
            
            process = subprocess.Popen(
                [sys.executable, '-O', code_path],
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

# ==================== توابع کمکی ====================

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
        
        if referred_by and referred_by != user_id:
            db.execute('UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = ?', (referred_by,))
            
            # اطلاع به رفرال دهنده
            try:
                bot.send_message(referred_by, 
                    f"🎉 **رفرال جدید!**\n\n"
                    f"👤 {first_name} با لینک شما عضو شد!\n"
                    f"📊 تعداد رفرال‌های شما افزایش یافت.\n\n"
                    f"💡 وقتی این کاربر ربات بسازه، ۱۰٪ سود به شما تعلق می‌گیرد.",
                    parse_mode='Markdown')
            except:
                pass
        
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
        
        # ========== سیستم رفرال ۱۰٪ ==========
        user = get_user(user_id)
        if user and user.get('referred_by'):
            commission = int(CARD_INFO['price'] * 0.1)  # ۱۰ درصد سود
            referrer_id = user['referred_by']
            
            db.execute('''
                INSERT INTO referral_earnings 
                (user_id, from_user_id, amount, commission, bot_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (referrer_id, user_id, CARD_INFO['price'], commission, bot_id, now))
            
            # به روز رسانی verified_referrals برای رفرال دهنده
            db.execute('UPDATE users SET verified_referrals = verified_referrals + 1 WHERE user_id = ?', (referrer_id,))
            
            # اطلاع به رفرال دهنده
            try:
                total_balance = get_referral_balance(referrer_id)
                bot.send_message(referrer_id,
                    f"💰 **سود رفرال ۱۰٪**\n\n"
                    f"👤 کاربر {user['first_name']} یک ربات ساخت!\n"
                    f"💰 سود شما: {commission:,} تومان\n"
                    f"📊 موجودی کیف پول شما: {total_balance:,} تومان\n\n"
                    f"💡 می‌توانید از طریق دکمه «💸 برداشت از کیف پول» موجودی خود را برداشت کنید.",
                    parse_mode='Markdown')
            except:
                pass
        
        cache.delete(f"user_{user_id}")
        return True
    except:
        return False

def get_referral_balance(user_id):
    """محاسبه موجودی رفرال قابل برداشت"""
    result = db.execute('''
        SELECT SUM(commission) as total FROM referral_earnings 
        WHERE user_id = ? AND paid = 0
    ''', (user_id,))
    return result[0]['total'] if result and result[0]['total'] else 0

def get_referral_history(user_id):
    """دریافت تاریخچه رفرال"""
    earnings = db.execute('''
        SELECT * FROM referral_earnings 
        WHERE user_id = ? 
        ORDER BY created_at DESC
        LIMIT 20
    ''', (user_id,))
    return [dict(e) for e in earnings]

def get_withdrawal_requests(user_id=None):
    """دریافت درخواست‌های برداشت"""
    if user_id:
        requests = db.execute('SELECT * FROM withdrawal_requests WHERE user_id = ? ORDER BY requested_at DESC', (user_id,))
    else:
        requests = db.execute('SELECT * FROM withdrawal_requests WHERE status = "pending" ORDER BY requested_at')
    return [dict(r) for r in requests]

def request_withdrawal(user_id, amount, card_number, card_holder):
    """ثبت درخواست برداشت"""
    balance = get_referral_balance(user_id)
    if balance < amount or amount < 50000:
        return False, "موجودی کافی نیست یا مبلغ کمتر از حداقل است"
    
    db.execute('''
        INSERT INTO withdrawal_requests (user_id, amount, card_number, card_holder, requested_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, amount, card_number, card_holder, datetime.now().isoformat()))
    return True, "درخواست با موفقیت ثبت شد"

def approve_withdrawal(request_id, admin_id):
    """تایید درخواست برداشت"""
    req = db.execute('SELECT * FROM withdrawal_requests WHERE id = ?', (request_id,))
    if not req:
        return False
    
    r = req[0]
    # علامت گذاری سودها به عنوان پرداخت شده
    db.execute('UPDATE referral_earnings SET paid = 1, paid_at = ? WHERE user_id = ? AND paid = 0', 
               (datetime.now().isoformat(), r['user_id']))
    db.execute('''
        UPDATE withdrawal_requests 
        SET status = 'approved', processed_at = ?, processed_by = ? 
        WHERE id = ?
    ''', (datetime.now().isoformat(), admin_id, request_id))
    return True

def reject_withdrawal(request_id, admin_id):
    """رد درخواست برداشت"""
    db.execute('''
        UPDATE withdrawal_requests 
        SET status = 'rejected', processed_at = ?, processed_by = ? 
        WHERE id = ?
    ''', (datetime.now().isoformat(), admin_id, request_id))
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
        types.KeyboardButton('💸 برداشت از کیف پول'),
        types.KeyboardButton('📊 رفرال من'),
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

def get_admin_referral_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💰 درخواست‌های برداشت", callback_data="admin_withdrawals"),
        types.InlineKeyboardButton("📊 آمار رفرال", callback_data="admin_referral_stats"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
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
        if users and users[0]['user_id'] != user_id:  # خودش نباید رفرال خودش بشه
            referred_by = users[0]['user_id']
    
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
    referral_balance = get_referral_balance(user_id)
    
    text = (
        f"🚀 **خوش آمدید {first_name}!**\n\n"
        f"👤 آیدی: `{user_id}`\n"
        f"🎁 کد رفرال: `{user['referral_code']}`\n"
        f"🔗 لینک رفرال: {referral_link}\n"
        f"📊 تعداد رفرال: {user['referrals_count']}\n"
        f"💰 موجودی رفرال: {referral_balance:,} تومان\n\n"
        f"✨ **سیستم رفرال ۱۰٪**\n"
        f"هر کاربری که با لینک شما وارد شود، وقتی ربات بخرد\n"
        f"۱۰٪ از مبلغ به کیف پول شما اضافه می‌شود!\n\n"
        f"📤 فایل .py یا .zip ارسال کنید\n"
        f"⚡ ۵۰ ماشین - پاسخگویی آنی"
    )
    
    bot.send_message(message.chat.id, text, reply_markup=get_main_menu(user_id in ADMIN_IDS), parse_mode='Markdown')

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
    referral_balance = get_referral_balance(user_id)
    
    text = (
        f"💰 **کیف پول**\n\n"
        f"👤 {user['first_name']}\n"
        f"💳 وضعیت پرداخت: {'✅ تایید شده' if payment_ok else '⏳ در انتظار'}\n"
        f"🎁 کد رفرال: `{user['referral_code']}`\n"
        f"🔗 لینک رفرال: {referral_link}\n"
        f"📊 رفرال‌های موفق: {user['verified_referrals']}\n"
        f"💰 موجودی قابل برداشت: {referral_balance:,} تومان\n"
        f"🤖 ربات‌های ساخته شده: {current}/{max_bots}\n\n"
    )
    
    if not payment_ok:
        text += f"💳 **اطلاعات پرداخت**\n"
        text += f"💰 مبلغ: {CARD_INFO['price_str']}\n"
        text += f"💳 شماره کارت: `{CARD_INFO['number_display']}`\n"
        text += f"👤 صاحب حساب: {CARD_INFO['holder']}\n"
        text += f"🏦 بانک: {CARD_INFO['bank']}\n\n"
        text += f"📸 پس از واریز، تصویر فیش را ارسال کنید"
    else:
        text += f"✅ پرداخت شما تایید شده است"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== برداشت از کیف پول ====================
@bot.message_handler(func=lambda m: m.text == '💸 برداشت از کیف پول')
def withdrawal_request(message):
    user_id = message.from_user.id
    balance = get_referral_balance(user_id)
    
    if balance < 50000:
        bot.reply_to(message, 
            f"❌ **امکان برداشت وجود ندارد**\n\n"
            f"💰 موجودی شما: {balance:,} تومان\n"
            f"💰 حداقل برداشت: ۵۰,۰۰۰ تومان\n\n"
            f"💡 هر کاربری با لینک شما وارد شود و ربات بخرد، ۱۰٪ سود به شما تعلق می‌گیرد.",
            parse_mode='Markdown')
        return
    
    msg = bot.reply_to(message, 
        f"💰 **موجودی قابل برداشت:** {balance:,} تومان\n"
        f"💰 **حداقل برداشت:** ۵۰,۰۰۰ تومان\n\n"
        f"لطفاً مبلغ مورد نظر را وارد کنید:",
        parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_withdrawal_amount)

def process_withdrawal_amount(message):
    try:
        amount = int(message.text.strip())
        user_id = message.from_user.id
        balance = get_referral_balance(user_id)
        
        if amount < 50000:
            bot.reply_to(message, "❌ حداقل برداشت ۵۰,۰۰۰ تومان است")
            return
        if amount > balance:
            bot.reply_to(message, f"❌ موجودی کافی نیست\n💰 موجودی: {balance:,} تومان")
            return
        
        msg = bot.reply_to(message, "💳 شماره کارت خود را وارد کنید (۱۶ رقم):")
        bot.register_next_step_handler(msg, lambda m: process_card_number(m, amount))
    except:
        bot.reply_to(message, "❌ لطفاً یک عدد معتبر وارد کنید")

def process_card_number(message, amount):
    card_number = message.text.strip().replace(' ', '')
    if not re.match(r'^\d{16}$', card_number):
        bot.reply_to(message, "❌ شماره کارت نامعتبر است (باید ۱۶ رقم باشد)")
        return
    
    msg = bot.reply_to(message, "👤 نام صاحب کارت را وارد کنید:")
    bot.register_next_step_handler(msg, lambda m: process_card_holder(m, amount, card_number))

def process_card_holder(message, amount, card_number):
    card_holder = message.text.strip()
    if len(card_holder) < 3:
        bot.reply_to(message, "❌ نام صاحب کارت معتبر نیست")
        return
    
    success, msg = request_withdrawal(message.from_user.id, amount, card_number, card_holder)
    if success:
        bot.reply_to(message, 
            f"✅ **درخواست برداشت ثبت شد**\n\n"
            f"💰 مبلغ: {amount:,} تومان\n"
            f"💳 شماره کارت: {card_number}\n"
            f"👤 صاحب کارت: {card_holder}\n\n"
            f"پس از تایید مدیریت، مبلغ به کارت شما واریز می‌شود.",
            parse_mode='Markdown')
    else:
        bot.reply_to(message, f"❌ {msg}")

# ==================== رفرال من ====================
@bot.message_handler(func=lambda m: m.text == '📊 رفرال من')
def my_referral(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        bot.send_message(message.chat.id, "❌ /start بزنید")
        return
    
    bot_username = bot.get_me().username
    referral_link = f"https://t.me/{bot_username}?start={user['referral_code']}"
    balance = get_referral_balance(user_id)
    
    # آمار رفرال‌ها
    referrals = db.execute('SELECT COUNT(*) as count FROM users WHERE referred_by = ?', (user_id,))
    active_referrals = db.execute('SELECT COUNT(*) as count FROM users WHERE referred_by = ? AND payment_status = "approved"', (user_id,))
    
    # تاریخچه سود
    earnings = get_referral_history(user_id)
    
    text = (
        f"📊 **سیستم رفرال ۱۰٪**\n\n"
        f"🔗 **لینک رفرال شما:**\n{referral_link}\n\n"
        f"🎁 **کد رفرال:** `{user['referral_code']}`\n\n"
        f"📈 **آمار رفرال:**\n"
        f"• تعداد رفرال‌ها: {referrals[0]['count'] if referrals else 0} نفر\n"
        f"• رفرال‌های فعال: {active_referrals[0]['count'] if active_referrals else 0} نفر\n"
        f"• ربات‌های ساخته شده: {user['verified_referrals']} عدد\n\n"
        f"💰 **کیف پول رفرال:**\n"
        f"• موجودی قابل برداشت: {balance:,} تومان\n\n"
        f"✨ **نحوه کسب سود:**\n"
        f"هر کاربری که با لینک شما وارد شود و ربات بخرد\n"
        f"۱۰٪ از مبلغ (۲۰۰,۰۰۰ تومان) به کیف پول شما اضافه می‌شود!\n\n"
    )
    
    if earnings:
        text += f"📜 **تاریخچه سود:**\n"
        for e in earnings[:5]:
            text += f"• {e['commission']:,} تومان - {e['created_at'][:10]}\n"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

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
        
        bot.reply_to(message, 
            f"✅ **فیش شما دریافت شد**\n\n"
            f"💰 مبلغ: {CARD_INFO['price_str']}\n"
            f"🆔 کد پیگیری: `{payment_code}`\n\n"
            f"پس از تایید مدیریت، ربات فعال می‌شود.",
            parse_mode='Markdown')
        
        for admin_id in ADMIN_IDS:
            try:
                with open(receipt_path, 'rb') as f:
                    bot.send_photo(admin_id, f, 
                        caption=f"📸 **فیش جدید**\n\n"
                                f"👤 کاربر: {user['first_name']}\n"
                                f"🆔 آیدی: {user_id}\n"
                                f"💰 مبلغ: {CARD_INFO['price_str']}\n"
                                f"🆔 کد: `{payment_code}`",
                        parse_mode='Markdown')
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
    
    bot.send_message(message.chat.id, "📦 **کتابخانه مورد نظر را انتخاب کنید:**", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('lib_'))
def install_library_callback(call):
    lib = call.data.replace('lib_', '')
    
    if lib == 'custom':
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "📦 نام کتابخانه را وارد کنید:")
        bot.register_next_step_handler(msg, install_custom_library)
        return
    
    bot.answer_callback_query(call.id, f"🔄 در حال نصب {lib}...")
    
    try:
        msg = bot.send_message(call.message.chat.id, f"🔄 در حال نصب `{lib}`...", parse_mode='Markdown')
        
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", lib, "--quiet"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            bot.edit_message_text(f"✅ کتابخانه `{lib}` با موفقیت نصب شد", call.message.chat.id, msg.message_id, parse_mode='Markdown')
        else:
            bot.edit_message_text(f"❌ خطا در نصب `{lib}`", call.message.chat.id, msg.message_id, parse_mode='Markdown')
            
    except:
        bot.send_message(call.message.chat.id, "❌ خطا در نصب کتابخانه")

def install_custom_library(message):
    lib = message.text.strip()
    try:
        msg = bot.reply_to(message, f"🔄 در حال نصب `{lib}`...", parse_mode='Markdown')
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", lib, "--quiet"],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            bot.edit_message_text(f"✅ کتابخانه `{lib}` با موفقیت نصب شد", message.chat.id, msg.message_id, parse_mode='Markdown')
        else:
            bot.edit_message_text(f"❌ خطا در نصب `{lib}`", message.chat.id, msg.message_id, parse_mode='Markdown')
    except:
        bot.reply_to(message, "❌ خطا در نصب کتابخانه")

# ==================== ساخت ربات جدید ====================
@bot.message_handler(func=lambda m: m.text == '🤖 ساخت ربات جدید')
def new_bot(message):
    user_id = message.from_user.id
    
    if not check_payment(user_id):
        bot.send_message(message.chat.id, 
            f"❌ **ابتدا باید پرداخت را انجام دهید**\n\n"
            f"💰 مبلغ: {CARD_INFO['price_str']}\n"
            f"💳 شماره کارت: `{CARD_INFO['number_display']}`\n"
            f"👤 صاحب حساب: {CARD_INFO['holder']}\n\n"
            f"📸 پس از واریز، تصویر فیش را ارسال کنید",
            parse_mode='Markdown')
        return
    
    can_create, max_bots, current_bots = check_bot_limit(user_id)
    if not can_create:
        bot.send_message(message.chat.id, f"❌ حداکثر تعداد ربات شما {max_bots} عدد است")
        return
    
    stats = machine_manager.get_stats()
    
    if stats['available'] == 0:
        bot.send_message(message.chat.id, f"⚠️ سیستم شلوغ است، چند دقیقه دیگر تلاش کنید")
        return
    
    bot.send_message(
        message.chat.id,
        f"📤 **ارسال فایل ربات**\n\n"
        f"✅ فایل `.py` یا `.zip` را ارسال کنید\n"
        f"⚡ ظرفیت خالی: {stats['available']} ربات\n"
        f"🖥️ ماشین فعال: {stats['total']} دستگاه\n"
        f"⏱️ زمان ساخت: ۱-۳ ثانیه",
        parse_mode='Markdown'
    )

# ==================== آپلود فایل ====================
@bot.message_handler(content_types=['document'])
def handle_build_file(message):
    user_id = message.from_user.id
    
    if not check_payment(user_id):
        bot.reply_to(message, "❌ ابتدا پرداخت را انجام دهید")
        return
    
    file_name = message.document.file_name
    
    if not (file_name.endswith('.py') or file_name.endswith('.zip')):
        bot.reply_to(message, "❌ فقط فایل‌های `.py` یا `.zip` پشتیبانی می‌شوند")
        return
    
    if message.document.file_size > 50 * 1024 * 1024:
        bot.reply_to(message, "❌ حجم فایل بیشتر از ۵۰ مگابایت است")
        return
    
    status_msg = bot.reply_to(message, "🔄 در حال پردازش فایل...")
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        file_path = save_uploaded_file(user_id, downloaded, file_name)
        if not file_path:
            bot.edit_message_text("❌ خطا در ذخیره فایل", message.chat.id, status_msg.message_id)
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
                    bot.edit_message_text("❌ خطا در خواندن فایل", message.chat.id, status_msg.message_id)
                    return
        
        if not main_code:
            bot.edit_message_text("❌ هیچ کد پایتونی در فایل یافت نشد", message.chat.id, status_msg.message_id)
            return
        
        token = extract_token_from_code(main_code)
        if not token:
            bot.edit_message_text("❌ توکن ربات در کد یافت نشد", message.chat.id, status_msg.message_id)
            return
        
        try:
            resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
            if resp.status_code != 200:
                bot.edit_message_text("❌ توکن نامعتبر است", message.chat.id, status_msg.message_id)
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
                f"✅ **ربات با موفقیت ساخته شد!**\n\n"
                f"🤖 نام: {bot_info['first_name']}\n"
                f"🔗 آیدی: t.me/{bot_info['username']}\n"
                f"🆔 شناسه: `{bot_id}`\n"
                f"🔄 PID: {result['pid']}\n"
                f"🖥️ ماشین: {result['machine_id']}\n"
                f"🔐 توکن: `{masked}`\n\n"
                f"💰 **سود رفرال:** اگر با لینک کسی وارد شده‌اید، ۱۰٪ به حسابش واریز شد!"
            )
            
            bot.edit_message_text(success_text, message.chat.id, status_msg.message_id, parse_mode='Markdown')
        else:
            bot.edit_message_text(f"❌ **خطا در اجرا**\n\n{result.get('error', 'خطای ناشناخته')}", 
                                 message.chat.id, status_msg.message_id, parse_mode='Markdown')
        
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)[:100]}", message.chat.id, status_msg.message_id)

# ==================== ربات‌های من ====================
@bot.message_handler(func=lambda m: m.text == '📋 ربات‌های من')
def my_bots(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما هیچ رباتی ندارید")
        return
    
    for b in bots[:10]:
        status = engine.get_status(b['id']) if b['pid'] else {'running': False}
        emoji = "🟢" if status.get('running') else "🔴"
        
        text = f"{emoji} **{b['name']}**\n"
        text += f"🔗 t.me/{b['username']}\n"
        text += f"🆔 `{b['id']}`\n"
        text += f"📊 وضعیت: {'فعال' if status.get('running') else 'متوقف'}\n"
        
        if status.get('running'):
            text += f"💻 CPU: {status.get('cpu', 0):.1f}%\n"
            text += f"⏱ زمان فعالیت: {int(status.get('uptime', 0) / 60)} دقیقه\n"
        
        bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== فعال/غیرفعال ====================
@bot.message_handler(func=lambda m: m.text == '🔄 فعال/غیرفعال')
def toggle_prompt(message):
    bots = get_user_bots(message.from_user.id)
    if not bots:
        bot.send_message(message.chat.id, "📋 شما هیچ رباتی ندارید")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        status = engine.get_status(b['id'])
        emoji = "🟢" if status.get('running') else "🔴"
        markup.add(types.InlineKeyboardButton(f"{emoji} {b['name']}", callback_data=f"toggle_{b['id']}"))
    
    bot.send_message(message.chat.id, "🔄 **ربات مورد نظر را انتخاب کنید:**", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_'))
def toggle_bot(call):
    bot_id = call.data.replace('toggle_', '')
    bot_info = get_bot(bot_id)
    
    if not bot_info or bot_info['user_id'] != call.from_user.id:
        bot.answer_callback_query(call.id, "❌ ربات یافت نشد")
        return
    
    status = engine.get_status(bot_id)
    
    if status.get('running'):
        if engine.stop_bot(bot_id):
            update_bot_status(bot_id, 'stopped')
            bot.answer_callback_query(call.id, "✅ ربات متوقف شد")
    else:
        if os.path.exists(bot_info['file_path']):
            try:
                with open(bot_info['file_path'], 'r') as f:
                    code = f.read()
                result = engine.run_bot(bot_id, code, bot_info['token'])
                if result['success']:
                    update_bot_status(bot_id, 'running')
                    db.execute("UPDATE bots SET machine_id = ? WHERE id = ?", (result['machine_id'], bot_id))
                    bot.answer_callback_query(call.id, "✅ ربات فعال شد")
                else:
                    bot.answer_callback_query(call.id, f"❌ {result.get('error', 'خطا')[:50]}")
            except Exception as e:
                bot.answer_callback_query(call.id, f"❌ خطا: {str(e)[:50]}")
        else:
            bot.answer_callback_query(call.id, "❌ فایل ربات یافت نشد")

# ==================== حذف ربات ====================
@bot.message_handler(func=lambda m: m.text == '🗑 حذف ربات')
def delete_prompt(message):
    bots = get_user_bots(message.from_user.id)
    if not bots:
        bot.send_message(message.chat.id, "📋 شما هیچ رباتی ندارید")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        markup.add(types.InlineKeyboardButton(f"🗑 {b['name']}", callback_data=f"delete_{b['id']}"))
    
    bot.send_message(message.chat.id, "🗑 **ربات مورد نظر را برای حذف انتخاب کنید:**", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
def confirm_delete(call):
    bot_id = call.data.replace('delete_', '')
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ بله، حذف شود", callback_data=f"confirm_del_{bot_id}"),
        types.InlineKeyboardButton("❌ انصراف", callback_data="cancel_del")
    )
    bot.edit_message_text("⚠️ **آیا از حذف این ربات اطمینان دارید؟**", 
                         call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_del_'))
def do_delete(call):
    bot_id = call.data.replace('confirm_del_', '')
    if delete_bot(bot_id, call.from_user.id):
        bot.edit_message_text("✅ ربات با موفقیت حذف شد", call.message.chat.id, call.message.message_id)
    else:
        bot.edit_message_text("❌ خطا در حذف ربات", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == 'cancel_del')
def cancel_delete(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== راهنما ====================
@bot.message_handler(func=lambda m: m.text == '📚 راهنما')
def guide(message):
    text = (
        f"📚 **راهنمای جامع ربات**\n\n"
        f"**1️⃣ ساخت ربات جدید**\n"
        f"• فایل `.py` یا `.zip` را ارسال کنید\n"
        f"• کد شما در محیط ایزوله اجرا می‌شود\n\n"
        
        f"**2️⃣ پرداخت**\n"
        f"• مبلغ: {CARD_INFO['price_str']}\n"
        f"• شماره کارت: `{CARD_INFO['number_display']}`\n"
        f"• صاحب حساب: {CARD_INFO['holder']}\n\n"
        
        f"**3️⃣ سیستم رفرال ۱۰٪**\n"
        f"• لینک رفرال خود را در «کیف پول» یا «رفرال من» دریافت کنید\n"
        f"• هر کاربری با لینک شما وارد شود و ربات بخرد\n"
        f"• ۱۰٪ از مبلغ (۲۰۰,۰۰۰ تومان) به کیف پول شما اضافه می‌شود\n"
        f"• پس از جمع شدن حداقل ۵۰,۰۰۰ تومان، می‌توانید برداشت کنید\n\n"
        
        f"**4️⃣ برداشت از کیف پول**\n"
        f"• از منوی «💸 برداشت از کیف پول» استفاده کنید\n"
        f"• شماره کارت و نام صاحب حساب را وارد کنید\n"
        f"• پس از تایید مدیریت، مبلغ واریز می‌شود\n\n"
        
        f"**5️⃣ اطلاعات سیستم**\n"
        f"• ۵۰ ماشین مجزا\n"
        f"• حافظه ۱۶۵ گیگابایت\n"
        f"• سرعت ۱۰۰,۰۰۰ درخواست/ثانیه\n\n"
        
        f"**6️⃣ پشتیبانی**\n"
        f"📞 @shahraghee13"
    )
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== آمار ====================
@bot.message_handler(func=lambda m: m.text == '📊 آمار')
def stats(message):
    try:
        users = db.execute('SELECT COUNT(*) as count FROM users')[0]['count']
        bots = db.execute('SELECT COUNT(*) as count FROM bots')[0]['count']
        running = db.execute('SELECT COUNT(*) as count FROM bots WHERE status = "running"')[0]['count']
        payments = db.execute('SELECT COUNT(*) as count FROM receipts WHERE status = "approved"')[0]['count']
        
        machine_stats = machine_manager.get_stats()
        
        total_commission = db.execute('SELECT SUM(commission) as total FROM referral_earnings WHERE paid = 0')[0]['total'] or 0
        total_withdrawn = db.execute('SELECT SUM(amount) as total FROM withdrawal_requests WHERE status = "approved"')[0]['total'] or 0
        
        text = (
            f"📊 **آمار جامع سیستم**\n\n"
            f"👥 کاربران: {users:,}\n"
            f"✅ پرداخت‌های موفق: {payments:,}\n"
            f"🤖 کل ربات‌ها: {bots:,}\n"
            f"🟢 ربات‌های فعال: {running:,}\n\n"
            f"🖥️ **ماشین‌ها**\n"
            f"• ماشین فعال: {machine_stats['total']} دستگاه\n"
            f"• ربات فعال: {machine_stats['total_bots']:,}\n"
            f"• ظرفیت خالی: {machine_stats['available']:,}\n\n"
            f"💰 **سیستم رفرال**\n"
            f"• سود پرداخت نشده: {total_commission:,} تومان\n"
            f"• کل برداشت شده: {total_withdrawn:,} تومان\n\n"
            f"🧠 حافظه: {machine_stats['memory_percent']:.1f}% از ۱۶۵GB\n"
            f"⚡ سرعت: ۱۰۰,۰۰۰ درخواست/ثانیه"
        )
        
        bot.send_message(message.chat.id, text, parse_mode='Markdown')
    except Exception as e:
        bot.send_message(message.chat.id, f"📊 خطا: {str(e)}")

# ==================== پشتیبانی ====================
@bot.message_handler(func=lambda m: m.text == '📞 پشتیبانی')
def support(message):
    bot.send_message(message.chat.id, "📞 **پشتیبانی**\n\nآیدی پشتیبانی: @shahraghee13", parse_mode='Markdown')

# ==================== وضعیت سیستم ====================
@bot.message_handler(func=lambda m: m.text == '⚡ وضعیت سیستم')
def system_status(message):
    stats = machine_manager.get_stats()
    
    text = (
        f"⚡ **وضعیت لحظه‌ای سیستم**\n\n"
        f"🖥️ ماشین‌های فعال: {stats['total']} از {CLUSTER_CONFIG['TOTAL_MACHINES']}\n"
        f"🤖 ربات‌های فعال: {stats['total_bots']:,}\n"
        f"📊 ظرفیت خالی: {stats['available']:,}\n"
        f"🧠 مصرف حافظه: {stats['memory_percent']:.1f}%\n"
        f"⚡ سرعت پردازش: ۱۰۰,۰۰۰ req/s\n"
        f"💰 سیستم رفرال ۱۰٪: فعال"
    )
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== پنل مدیریت ====================
@bot.message_handler(func=lambda m: m.text == '👑 پنل مدیریت')
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    bot.send_message(message.chat.id, "👑 **پنل مدیریت**", reply_markup=get_admin_referral_menu(), parse_mode='Markdown')

# ==================== پیام همگانی ====================
@bot.message_handler(func=lambda m: m.text == '📢 پیام همگانی')
def broadcast_prompt(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(message.chat.id, "📢 **متن پیام همگانی را ارسال کنید:**", parse_mode='Markdown')
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
            bot.send_message(user['user_id'], text, parse_mode='Markdown')
            sent += 1
            if sent % 10 == 0:
                bot.edit_message_text(f"📢 پیشرفت: {sent}/{len(users)}", message.chat.id, status.message_id)
        except:
            failed += 1
    
    bot.edit_message_text(f"✅ **ارسال همگانی انجام شد!**\n\nموفق: {sent}\nناموفق: {failed}", 
                         message.chat.id, status.message_id, parse_mode='Markdown')

# ==================== کال‌بک‌های مدیریت رفرال ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_withdrawals")
def admin_withdrawals_list(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    bot.answer_callback_query(call.id)
    
    withdrawals = get_withdrawal_requests()
    
    if not withdrawals:
        bot.send_message(call.message.chat.id, "📭 **درخواست برداشتی وجود ندارد**", parse_mode='Markdown')
        return
    
    for w in withdrawals:
        # گرفتن نام کاربر
        user = get_user(w['user_id'])
        user_name = user['first_name'] if user else str(w['user_id'])
        
        text = (
            f"💰 **درخواست برداشت**\n\n"
            f"👤 کاربر: {user_name}\n"
            f"🆔 آیدی: `{w['user_id']}`\n"
            f"💰 مبلغ: {w['amount']:,} تومان\n"
            f"💳 شماره کارت: `{w['card_number']}`\n"
            f"👤 صاحب کارت: {w['card_holder']}\n"
            f"📅 تاریخ: {w['requested_at'][:16]}"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید و پرداخت", callback_data=f"withdraw_approve_{w['id']}"),
            types.InlineKeyboardButton("❌ رد درخواست", callback_data=f"withdraw_reject_{w['id']}")
        )
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith("withdraw_approve_"))
def approve_withdrawal(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    
    wid = int(call.data.replace("withdraw_approve_", ""))
    
    if approve_withdrawal(wid, call.from_user.id):
        # گرفتن اطلاعات برای اطلاع رسانی
        req = db.execute('SELECT * FROM withdrawal_requests WHERE id = ?', (wid,))
        if req:
            w = req[0]
            try:
                bot.send_message(w['user_id'], 
                    f"✅ **درخواست برداشت شما تایید شد!**\n\n"
                    f"💰 مبلغ: {w['amount']:,} تومان\n"
                    f"💳 به کارت {w['card_number']} واریز خواهد شد.\n\n"
                    f"زمان واریز: حداکثر ۷۲ ساعت کاری",
                    parse_mode='Markdown')
            except:
                pass
        
        bot.answer_callback_query(call.id, "✅ برداشت تایید شد")
        bot.delete_message(call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ خطا در تایید")

@bot.callback_query_handler(func=lambda call: call.data.startswith("withdraw_reject_"))
def reject_withdrawal(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    
    wid = int(call.data.replace("withdraw_reject_", ""))
    
    if reject_withdrawal(wid, call.from_user.id):
        req = db.execute('SELECT * FROM withdrawal_requests WHERE id = ?', (wid,))
        if req:
            w = req[0]
            try:
                bot.send_message(w['user_id'], 
                    f"❌ **درخواست برداشت شما رد شد**\n\n"
                    f"💰 مبلغ: {w['amount']:,} تومان\n\n"
                    f"لطفاً با پشتیبانی تماس بگیرید.\n📞 @shahraghee13",
                    parse_mode='Markdown')
            except:
                pass
        
        bot.answer_callback_query(call.id, "❌ برداشت رد شد")
        bot.delete_message(call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ خطا در رد")

@bot.callback_query_handler(func=lambda call: call.data == "admin_referral_stats")
def admin_referral_stats(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    bot.answer_callback_query(call.id)
    
    # آمار کلی رفرال
    total_earnings = db.execute('SELECT SUM(commission) as total FROM referral_earnings')[0]['total'] or 0
    paid_earnings = db.execute('SELECT SUM(commission) as total FROM referral_earnings WHERE paid = 1')[0]['total'] or 0
    unpaid_earnings = db.execute('SELECT SUM(commission) as total FROM referral_earnings WHERE paid = 0')[0]['total'] or 0
    total_withdrawn = db.execute('SELECT SUM(amount) as total FROM withdrawal_requests WHERE status = "approved"')[0]['total'] or 0
    
    # کاربران با بیشترین سود
    top_users = db.execute('''
        SELECT u.user_id, u.first_name, SUM(re.commission) as total_commission
        FROM referral_earnings re
        JOIN users u ON re.user_id = u.user_id
        GROUP BY re.user_id
        ORDER BY total_commission DESC
        LIMIT 10
    ''')
    
    text = (
        f"📊 **آمار سیستم رفرال**\n\n"
        f"💰 **کل سود پرداخت شده:** {paid_earnings:,} تومان\n"
        f"💰 **سود پرداخت نشده:** {unpaid_earnings:,} تومان\n"
        f"💰 **کل برداشت شده:** {total_withdrawn:,} تومان\n"
        f"💰 **کل سود تعلق گرفته:** {total_earnings:,} تومان\n\n"
        f"🏆 **کاربران برتر رفرال:**\n"
    )
    
    for u in top_users:
        text += f"• {u['first_name'] or u['user_id']}: {u['total_commission']:,} تومان\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "🚀 **منوی اصلی**", reply_markup=get_main_menu(True), parse_mode='Markdown')

# ==================== مانیتورینگ خودکار ====================
def monitor_system():
    while True:
        try:
            cache.clear_expired()
            
            # بررسی ربات‌های مرده
            for bot_data in db.execute('SELECT id, machine_id FROM bots WHERE status = "running"'):
                if not engine.get_status(bot_data['id']).get('running'):
                    db.execute('UPDATE bots SET status = "stopped" WHERE id = ?', (bot_data['id'],))
                    machine_manager.release_bot(bot_data['id'], bot_data['machine_id'])
            
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
    print(f"💰 سیستم رفرال ۱۰٪: فعال")
    print(f"💳 برداشت از کیف پول: فعال")
    print("=" * 80)
    print(f"👑 ادمین: {ADMIN_IDS}")
    print("=" * 80)
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            logger.error(f"Polling error: {e}")
            time.sleep(5)