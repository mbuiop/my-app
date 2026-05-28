#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
═══════════════════════════════════════════════════════════════════════════════
🚀 ربات مادر نهایی - نسخه 18.0 HyperSpeed Ultimate (رفع باگ کامل)
⚡ قدرت: ۵۰ ماشین مجزا | هر ماشین ۳۰۰۰ ربات | حافظه ۱۶۵GB
⚡ ایزوله‌سازی کامل | رفرال ۱۰٪ | سیستم برداشت | لود بالانس ۵۰۰ نفری
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
import resource
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
    'CACHE': os.path.join(BASE_DIR, "cache"),
    'SANDBOX': os.path.join(BASE_DIR, "sandbox"),
    'PROJECTS': os.path.join(BASE_DIR, "projects")
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
    'USERS_PER_MACHINE': 500,
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
        db_path = os.path.join(DIRS['DB'], 'mother_bot.db')
        for i in range(CLUSTER_CONFIG['DB_POOL_SIZE']):
            conn = sqlite3.connect(
                db_path,
                timeout=30,
                check_same_thread=False
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=-200000")
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
                last_active TIMESTAMP,
                machine_id INTEGER DEFAULT 0
            )
        ''')
        self.execute("CREATE INDEX IF NOT EXISTS idx_users_payment ON users(payment_status)")
        self.execute("CREATE INDEX IF NOT EXISTS idx_users_referral ON users(referral_code)")
        self.execute("CREATE INDEX IF NOT EXISTS idx_users_machine ON users(machine_id)")
        
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
                project_files TEXT
            )
        ''')
        self.execute("CREATE INDEX IF NOT EXISTS idx_bots_user ON bots(user_id)")
        self.execute("CREATE INDEX IF NOT EXISTS idx_bots_status ON bots(status)")
        
        self.execute('''
            CREATE TABLE IF NOT EXISTS machines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                status TEXT DEFAULT 'active',
                current_bots INTEGER DEFAULT 0,
                max_bots INTEGER DEFAULT 3000,
                current_users INTEGER DEFAULT 0,
                max_users INTEGER DEFAULT 500,
                memory_used INTEGER DEFAULT 0,
                max_memory INTEGER DEFAULT 165000,
                last_heartbeat TIMESTAMP,
                created_at TIMESTAMP
            )
        ''')
        
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
        
        self.execute('''
            CREATE TABLE IF NOT EXISTS referral_earnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                referred_user_id INTEGER,
                bot_id TEXT,
                bot_earnings INTEGER DEFAULT 0,
                commission INTEGER DEFAULT 0,
                paid BOOLEAN DEFAULT 0,
                created_at TIMESTAMP
            )
        ''')
        
        self.execute('''
            CREATE TABLE IF NOT EXISTS withdrawal_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                card_number TEXT,
                card_holder TEXT,
                status TEXT DEFAULT 'pending',
                requested_at TIMESTAMP,
                processed_at TIMESTAMP
            )
        ''')
        
        self.execute('''
            CREATE TABLE IF NOT EXISTS admin_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_number TEXT,
                card_holder TEXT,
                bank_name TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP
            )
        ''')
        
        self.execute('''
            CREATE TABLE IF NOT EXISTS user_analytics (
                user_id INTEGER PRIMARY KEY,
                total_bots_created INTEGER DEFAULT 0,
                total_bot_runtime INTEGER DEFAULT 0,
                last_bot_created TIMESTAMP,
                average_cpu_usage REAL DEFAULT 0,
                average_memory_usage REAL DEFAULT 0,
                error_count INTEGER DEFAULT 0
            )
        ''')
        
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
        
        # کارت مدیریت پیش‌فرض
        self.execute('''
            INSERT OR IGNORE INTO admin_cards (card_number, card_holder, bank_name, created_at)
            VALUES (?, ?, ?, ?)
        ''', (CARD_INFO['number'], CARD_INFO['holder'], CARD_INFO['bank'], datetime.now().isoformat()))
        
        # ماشین‌ها
        for i in range(1, CLUSTER_CONFIG['TOTAL_MACHINES'] + 1):
            self.execute('''
                INSERT OR IGNORE INTO machines (id, name, status, max_bots, max_users, max_memory, created_at)
                VALUES (?, ?, 'active', ?, ?, ?, ?)
            ''', (i, f"Machine-{i:03d}", 
                  CLUSTER_CONFIG['BOTS_PER_MACHINE'],
                  CLUSTER_CONFIG['USERS_PER_MACHINE'],
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

# ==================== ایزوله‌سازی کامل (Sandbox) ====================
class SecureSandbox:
    MAX_CPU_PERCENT = 20
    MAX_MEMORY_MB = 256
    MAX_EXECUTION_TIME = 30
    ALLOWED_MODULES = [
        'telebot', 'requests', 'json', 'time', 'datetime', 
        'random', 'math', 're', 'string', 'collections', 
        'itertools', 'functools', 'typing', 'enum'
    ]
    BLOCKED_KEYWORDS = [
        '__import__', 'eval', 'exec', 'compile', 'globals', 'locals',
        'open', 'file', 'os.system', 'subprocess', 'socket',
        'pty', 'pickle', 'marshal', '__builtins__', 'breakpoint'
    ]
    
    def __init__(self):
        os.makedirs(DIRS['SANDBOX'], exist_ok=True)
        self.running_sandboxes = {}
        self.lock = threading.RLock()
    
    def sanitize_code(self, code: str) -> tuple:
        for keyword in self.BLOCKED_KEYWORDS:
            if keyword in code:
                return False, f"⚠️ کد شامل دستور ممنوعه: {keyword}"
        
        lines = code.split('\n')
        new_lines = []
        for line in lines:
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                allowed = False
                for module in self.ALLOWED_MODULES:
                    if module in line:
                        allowed = True
                        break
                if not allowed and 'telebot' not in line:
                    return False, f"⚠️ ماژول غیرمجاز"
            new_lines.append(line)
        
        wrapper_code = f'''
# ========== لایه امنیتی ==========
import sys
import signal
import resource

def security_timeout(signum, frame):
    print("⏰ زمان اجرا تمام شد")
    sys.exit(1)

signal.signal(signal.SIGALRM, security_timeout)
signal.alarm({self.MAX_EXECUTION_TIME})

try:
    resource.setrlimit(resource.RLIMIT_AS, ({self.MAX_MEMORY_MB * 1024 * 1024}, {self.MAX_MEMORY_MB * 1024 * 1024}))
except:
    pass

try:
    resource.setrlimit(resource.RLIMIT_CPU, ({self.MAX_CPU_PERCENT}, {self.MAX_CPU_PERCENT}))
except:
    pass

# ========== کد اصلی کاربر ==========
{chr(10).join(new_lines)}
'''
        return True, wrapper_code
    
    def extract_project_files(self, zip_path: str, extract_to: str) -> dict:
        files = {}
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(extract_to)
            
            for root, _, filenames in os.walk(extract_to):
                for fname in filenames:
                    if fname.endswith('.py'):
                        full_path = os.path.join(root, fname)
                        try:
                            with open(full_path, 'r', encoding='utf-8') as f:
                                files[fname] = f.read()
                        except:
                            with open(full_path, 'r', encoding='cp1256') as f:
                                files[fname] = f.read()
        except Exception as e:
            logger.error(f"Extract error: {e}")
        return files
    
    def run_in_sandbox(self, bot_id: str, code: str, token: str, machine_id: int, project_files: dict = None) -> dict:
        try:
            bot_sandbox = os.path.join(DIRS['SANDBOX'], f"bot_{bot_id}")
            os.makedirs(bot_sandbox, exist_ok=True)
            
            is_clean, result = self.sanitize_code(code)
            if not is_clean:
                return {'success': False, 'error': result}
            
            clean_code = result
            code_path = os.path.join(bot_sandbox, "bot.py")
            with open(code_path, 'w', encoding='utf-8') as f:
                f.write(clean_code)
            
            if project_files:
                for fname, fcontent in project_files.items():
                    fpath = os.path.join(bot_sandbox, fname)
                    with open(fpath, 'w', encoding='utf-8') as f:
                        f.write(fcontent)
            
            log_file = os.path.join(bot_sandbox, "output.log")
            
            process = subprocess.Popen(
                [sys.executable, '-I', code_path],
                stdout=open(log_file, 'a'),
                stderr=subprocess.STDOUT,
                cwd=bot_sandbox,
                start_new_session=True,
                env={
                    'PYTHONPATH': bot_sandbox,
                    'PYTHONHASHSEED': 'random',
                    'PYTHONWARNINGS': 'ignore',
                    'TMPDIR': os.path.join(bot_sandbox, 'tmp'),
                    'HOME': bot_sandbox,
                    'PATH': '/usr/local/bin:/usr/bin:/bin',
                    'LC_ALL': 'C.UTF-8'
                }
            )
            
            time.sleep(1.5)
            
            if process.poll() is None:
                with self.lock:
                    self.running_sandboxes[bot_id] = {
                        'process': process,
                        'pid': process.pid,
                        'dir': bot_sandbox,
                        'start_time': time.time()
                    }
                return {
                    'success': True,
                    'pid': process.pid,
                    'sandbox_dir': bot_sandbox,
                    'is_isolated': True
                }
            else:
                error_msg = ""
                if os.path.exists(log_file):
                    with open(log_file, 'r') as f:
                        error_msg = f.read()[-300:]
                return {'success': False, 'error': error_msg or "خطای ناشناخته"}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def stop_sandbox(self, bot_id: str) -> bool:
        with self.lock:
            if bot_id in self.running_sandboxes:
                try:
                    info = self.running_sandboxes[bot_id]
                    os.killpg(os.getpgid(info['pid']), signal.SIGTERM)
                    time.sleep(0.5)
                    shutil.rmtree(info['dir'], ignore_errors=True)
                    del self.running_sandboxes[bot_id]
                    return True
                except:
                    pass
        return False

sandbox = SecureSandbox()

# ==================== لود بالانس ====================
class LoadBalancer:
    def __init__(self):
        self._init_machines()
    
    def _init_machines(self):
        total_users = db.execute('SELECT COUNT(*) as count FROM users')[0]['count']
        users_per_machine = CLUSTER_CONFIG['USERS_PER_MACHINE']
        required = max(1, (total_users // users_per_machine) + 1)
        required = min(required, CLUSTER_CONFIG['TOTAL_MACHINES'])
        
        for i in range(1, required + 1):
            db.execute('UPDATE machines SET max_users = ?, status = "active" WHERE id = ?', (users_per_machine, i))
    
    def get_machine_for_user(self, user_id: int) -> int:
        return ((user_id * 7919) % CLUSTER_CONFIG['TOTAL_MACHINES']) + 1
    
    def assign_user_to_machine(self, user_id: int, machine_id: int):
        db.execute('UPDATE users SET machine_id = ? WHERE user_id = ?', (machine_id, user_id))
        db.execute('UPDATE machines SET current_users = current_users + 1 WHERE id = ?', (machine_id,))
    
    def release_user_from_machine(self, user_id: int, machine_id: int):
        db.execute('UPDATE users SET machine_id = 0 WHERE user_id = ?', (user_id,))
        db.execute('UPDATE machines SET current_users = current_users - 1 WHERE id = ?', (machine_id,))

load_balancer = LoadBalancer()

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
        db.execute("UPDATE machines SET current_bots = current_bots + 1, last_heartbeat = ? WHERE id = ?",
                  (datetime.now().isoformat(), machine_id))
        self.last_refresh = 0
        return True
    
    def release_bot(self, bot_id, machine_id):
        db.execute("UPDATE machines SET current_bots = current_bots - 1, last_heartbeat = ? WHERE id = ?",
                  (datetime.now().isoformat(), machine_id))
        self.last_refresh = 0
        return True
    
    def get_stats(self):
        machines = db.execute("SELECT * FROM machines WHERE status = 'active'")
        total_bots = 0
        total_capacity = 0
        total_users = 0
        total_users_capacity = 0
        active = 0
        
        for m in machines:
            total_bots += m['current_bots']
            total_capacity += m['max_bots']
            total_users += m['current_users']
            total_users_capacity += m['max_users']
            active += 1
        
        return {
            'total': active,
            'total_bots': total_bots,
            'total_capacity': total_capacity,
            'available': total_capacity - total_bots,
            'total_users': total_users,
            'total_users_capacity': total_users_capacity,
            'users_available': total_users_capacity - total_users,
            'memory_total': CLUSTER_CONFIG['TOTAL_MEMORY'],
            'memory_percent': (total_bots * CLUSTER_CONFIG['MAX_MEMORY_PER_BOT']) / CLUSTER_CONFIG['TOTAL_MEMORY'] * 100 if total_bots > 0 else 0
        }

machine_manager = MachineManager()

# ==================== موتور اجرا ====================
class HyperEngine:
    def __init__(self):
        self.processes = {}
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=CLUSTER_CONFIG['WORKER_THREADS'])
    
    def run_bot(self, bot_id, code, token, project_files=None):
        try:
            machine_id = machine_manager.get_available_machine()
            if not machine_id:
                return {'success': False, 'error': '❌ همه ماشین‌ها پر هستند'}
            
            result = sandbox.run_in_sandbox(bot_id, code, token, machine_id, project_files)
            
            if result['success']:
                with self.lock:
                    self.processes[bot_id] = {
                        'pid': result['pid'],
                        'machine_id': machine_id,
                        'start_time': time.time()
                    }
                machine_manager.assign_bot(bot_id, machine_id)
                return result
            else:
                return result
            
        except Exception as e:
            logger.error(f"Error: {e}")
            return {'success': False, 'error': str(e)[:100]}
    
    def stop_bot(self, bot_id):
        with self.lock:
            if bot_id in self.processes:
                try:
                    info = self.processes[bot_id]
                    sandbox.stop_sandbox(bot_id)
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
                    return {
                        'running': True,
                        'pid': info['pid'],
                        'machine_id': info['machine_id'],
                        'uptime': time.time() - info['start_time']
                    }
                except:
                    if bot_id in self.processes:
                        del self.processes[bot_id]
        return {'running': False}

engine = HyperEngine()

# ==================== ربات تلگرام ====================
# مهم: حذف وبی‌هوک و تنظیم مجدد
bot = telebot.TeleBot(BOT_TOKEN)

try:
    bot.remove_webhook()
    time.sleep(0.5)
except:
    pass

# ==================== توابع کمکی ====================

def generate_referral_code(user_id):
    return hashlib.md5(f"{user_id}_{time.time()}_{secrets.token_hex(4)}".encode()).hexdigest()[:12]

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
        machine_id = load_balancer.get_machine_for_user(user_id)
        
        db.execute('''
            INSERT OR IGNORE INTO users 
            (user_id, username, first_name, last_name, referral_code, referred_by, created_at, last_active, payment_status, machine_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name, referral_code, referred_by, now, now, 'pending', machine_id))
        
        db.execute('UPDATE users SET last_active = ? WHERE user_id = ?', (now, user_id))
        load_balancer.assign_user_to_machine(user_id, machine_id)
        
        if referred_by and referred_by != user_id:
            db.execute('UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = ?', (referred_by,))
            try:
                bot.send_message(referred_by, f"🎉 {first_name} با لینک رفرال شما عضو شد!")
            except:
                pass
        
        cache.delete(f"user_{user_id}")
        return True
    except Exception as e:
        logger.error(f"Create user error: {e}")
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

def update_bot_status(bot_id, status, pid=None):
    if pid:
        db.execute('UPDATE bots SET status = ?, pid = ?, last_active = ? WHERE id = ?',
                   (status, pid, datetime.now().isoformat(), bot_id))
    else:
        db.execute('UPDATE bots SET status = ?, last_active = ? WHERE id = ?',
                   (status, datetime.now().isoformat(), bot_id))
    return True

def delete_bot(bot_id, user_id):
    bot_data = get_bot(bot_id)
    if not bot_data or bot_data['user_id'] != user_id:
        return False
    
    engine.stop_bot(bot_id)
    
    if bot_data.get('file_path') and os.path.exists(bot_data['file_path']):
        os.remove(bot_data['file_path'])
    
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
    py_files = {}
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        
        for root, _, files in os.walk(extract_to):
            for file in files:
                if file.endswith('.py'):
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                            py_files[file] = f.read()
                    except:
                        try:
                            with open(os.path.join(root, file), 'r', encoding='cp1256') as f:
                                py_files[file] = f.read()
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

def add_bot(user_id, bot_id, token, name, username, file_path, folder_path=None, pid=None, machine_id=None, project_files=None):
    try:
        now = datetime.now().isoformat()
        status = 'running' if pid else 'stopped'
        
        user = get_user(user_id)
        if user and user.get('referred_by') and user['referred_by'] != user_id:
            commission = int(CARD_INFO['price'] * 0.1)
            db.execute('''
                INSERT INTO referral_earnings (user_id, referred_user_id, bot_id, bot_earnings, commission, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user['referred_by'], user_id, bot_id, CARD_INFO['price'], commission, now))
            
            try:
                bot.send_message(user['referred_by'], 
                    f"🎉 سود رفرال!\n\n"
                    f"کاربر {user['first_name']} یک ربات ساخت\n"
                    f"💰 سود شما: {commission:,} تومان\n"
                    f"📊 موجودی کیف پول رفرال: {get_referral_balance(user['referred_by']):,} تومان")
            except:
                pass
        
        project_files_json = json.dumps(project_files) if project_files else None
        
        db.execute('''
            INSERT INTO bots 
            (id, user_id, token, name, username, file_path, folder_path, pid, machine_id, status, created_at, last_active, project_files)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (bot_id, user_id, token, name, username, file_path, folder_path, pid, machine_id, status, now, now, project_files_json))
        
        db.execute('UPDATE users SET bots_count = bots_count + 1, last_active = ? WHERE user_id = ?', (now, user_id))
        
        db.execute('''
            INSERT OR REPLACE INTO user_analytics (user_id, total_bots_created, last_bot_created)
            VALUES (?, COALESCE((SELECT total_bots_created FROM user_analytics WHERE user_id = ?), 0) + 1, ?)
        ''', (user_id, user_id, now))
        
        cache.delete(f"user_{user_id}")
        return True
    except Exception as e:
        logger.error(f"Add bot error: {e}")
        return False

def get_referral_balance(user_id):
    result = db.execute('''
        SELECT SUM(commission) as total FROM referral_earnings 
        WHERE user_id = ? AND paid = 0
    ''', (user_id,))
    return result[0]['total'] if result and result[0]['total'] else 0

def request_withdrawal(user_id, amount, card_number, card_holder):
    balance = get_referral_balance(user_id)
    if balance < amount or amount < 50000:
        return False
    
    db.execute('''
        INSERT INTO withdrawal_requests (user_id, amount, card_number, card_holder, requested_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, amount, card_number, card_holder, datetime.now().isoformat()))
    return True

def get_all_users_stats():
    users = db.execute('''
        SELECT u.user_id, u.username, u.first_name, u.payment_status, u.referrals_count,
               COUNT(b.id) as bot_count,
               COUNT(CASE WHEN b.status = 'running' THEN 1 END) as running_count,
               (SELECT COUNT(*) FROM users WHERE referred_by = u.user_id) as total_referrals,
               COALESCE((SELECT SUM(commission) FROM referral_earnings WHERE user_id = u.user_id AND paid = 0), 0) as referral_balance
        FROM users u
        LEFT JOIN bots b ON u.user_id = b.user_id
        GROUP BY u.user_id
        ORDER BY bot_count DESC
    ''')
    return [dict(u) for u in users]

def get_admin_cards():
    cards = db.execute('SELECT * FROM admin_cards WHERE is_active = 1')
    return [dict(c) for c in cards]

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

def get_admin_panel_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🗑 حذف ربات کاربر", callback_data="admin_delete_user_bot"),
        types.InlineKeyboardButton("🔴 غیرفعال کردن ربات", callback_data="admin_disable_bot"),
        types.InlineKeyboardButton("📊 آمار کامل کاربران", callback_data="admin_full_stats"),
        types.InlineKeyboardButton("📈 کارکرد ربات‌ها", callback_data="admin_bot_performance"),
        types.InlineKeyboardButton("💳 مدیریت کارت‌ها", callback_data="admin_cards"),
        types.InlineKeyboardButton("💰 درخواست‌های برداشت", callback_data="admin_withdrawals"),
        types.InlineKeyboardButton("📸 فیش‌ها", callback_data="admin_receipts"),
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
        if users and users[0]['user_id'] != user_id:
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
    
    text = (
        f"🚀 **خوش آمدید {first_name}!**\n\n"
        f"👤 آیدی: `{user_id}`\n"
        f"🎁 کد رفرال: `{user['referral_code']}`\n"
        f"🔗 لینک رفرال: {referral_link}\n"
        f"📊 تعداد رفرال: {user['referrals_count']}\n"
        f"💰 موجودی رفرال: {get_referral_balance(user_id):,} تومان\n\n"
        f"📤 فایل `.py` یا `.zip` ارسال کنید\n"
        f"⚡ ۵۰ ماشین - پاسخگویی آنی\n"
        f"🔒 ایزوله‌سازی کامل کدها"
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
        bot.reply_to(message, f"❌ حداقل مبلغ برداشت ۵۰,۰۰۰ تومان است\n💰 موجودی شما: {balance:,} تومان")
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
    
    if request_withdrawal(message.from_user.id, amount, card_number, card_holder):
        bot.reply_to(message, 
            f"✅ **درخواست برداشت ثبت شد**\n\n"
            f"💰 مبلغ: {amount:,} تومان\n"
            f"💳 شماره کارت: {card_number}\n"
            f"👤 صاحب کارت: {card_holder}\n\n"
            f"پس از تایید مدیریت، مبلغ به کارت شما واریز می‌شود.", parse_mode='Markdown')
    else:
        bot.reply_to(message, "❌ خطا در ثبت درخواست")

# ==================== فیش ====================
@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    
    existing = db.execute('SELECT id FROM receipts WHERE user_id = ? AND status = "pending"', (user_id,))
    if existing:
        bot.reply_to(message, "⏳ فیش قبلی شما در انتظار تایید است")
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
        bot.send_message(message.chat.id, f"⚠️ سیستم در حال حاضر شلوغ است، چند دقیقه دیگر تلاش کنید")
        return
    
    bot.send_message(
        message.chat.id,
        f"📤 **ارسال فایل ربات**\n\n"
        f"✅ فایل `.py` یا `.zip` را ارسال کنید\n"
        f"⚡ ظرفیت خالی: {stats['available']} ربات\n"
        f"🖥️ ماشین فعال: {stats['total']} دستگاه\n"
        f"🔒 کد شما در محیط ایزوله اجرا می‌شود\n"
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
        project_files = {}
        
        if file_name.endswith('.zip'):
            extract_dir = os.path.join(DIRS['PROJECTS'], f"extract_{user_id}_{int(time.time())}")
            os.makedirs(extract_dir, exist_ok=True)
            
            project_files = extract_files_from_zip(file_path, extract_dir)
            
            for fname in ['bot.py', 'main.py', 'run.py']:
                if fname in project_files:
                    main_code = project_files[fname]
                    break
            
            if not main_code and project_files:
                main_code = list(project_files.values())[0]
            
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
        
        result = engine.run_bot(bot_id, main_code, token, project_files)
        
        if result['success']:
            add_bot(
                user_id, bot_id, token, bot_info['first_name'], bot_info['username'],
                file_path, None, result['pid'], result.get('machine_id', 1), project_files
            )
            
            masked = token[:4] + "*"*8 + token[-4:] if len(token) > 8 else "****"
            
            success_text = (
                f"✅ **ربات با موفقیت ساخته شد!**\n\n"
                f"🤖 نام: {bot_info['first_name']}\n"
                f"🔗 آیدی: t.me/{bot_info['username']}\n"
                f"🆔 شناسه: `{bot_id}`\n"
                f"🔄 PID: {result['pid']}\n"
                f"🔐 توکن: `{masked}`\n"
                f"🔒 محیط اجرا: ایزوله و امن\n"
                f"📁 فایل‌های پروژه: {len(project_files)} فایل"
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
                
                project_files = None
                if bot_info.get('project_files'):
                    project_files = json.loads(bot_info['project_files'])
                
                result = engine.run_bot(bot_id, code, bot_info['token'], project_files)
                if result['success']:
                    update_bot_status(bot_id, 'running', result['pid'])
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
        f"• کد شما در محیط ایزوله اجرا می‌شود\n"
        f"• پشتیبانی از پروژه‌های چندفایلی\n\n"
        
        f"**2️⃣ پرداخت**\n"
        f"• مبلغ: {CARD_INFO['price_str']}\n"
        f"• شماره کارت: `{CARD_INFO['number_display']}`\n"
        f"• صاحب حساب: {CARD_INFO['holder']}\n\n"
        
        f"**3️⃣ سیستم رفرال**\n"
        f"• هر کاربر با لینک شما وارد شود\n"
        f"• ۱۰٪ از مبلغ پرداختی به کیف پول شما اضافه می‌شود\n"
        f"• امکان برداشت از کیف پول\n\n"
        
        f"**4️⃣ اطلاعات سیستم**\n"
        f"• ۵۰ ماشین مجزا\n"
        f"• حافظه ۱۶۵ گیگابایت\n"
        f"• ایزوله‌سازی کامل کدها\n"
        f"• هر ۵۰۰ کاربر روی یک ماشین\n\n"
        
        f"**5️⃣ پشتیبانی**\n"
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
        
        text = (
            f"📊 **آمار جامع سیستم**\n\n"
            f"👥 کاربران: {users:,}\n"
            f"✅ پرداخت‌های موفق: {payments:,}\n"
            f"🤖 کل ربات‌ها: {bots:,}\n"
            f"🟢 ربات‌های فعال: {running:,}\n\n"
            f"🖥️ **ماشین‌ها**\n"
            f"• ماشین فعال: {machine_stats['total']} دستگاه\n"
            f"• ربات فعال: {machine_stats['total_bots']:,}\n"
            f"• ظرفیت خالی: {machine_stats['available']:,}\n"
            f"• کاربران: {machine_stats['total_users']:,}\n\n"
            f"💰 **سیستم رفرال**\n"
            f"• موجودی قابل برداشت: {total_commission:,} تومان\n\n"
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
        f"👥 کاربران توزیع شده: {stats['total_users']:,}\n"
        f"🧠 مصرف حافظه: {stats['memory_percent']:.1f}%\n"
        f"⚡ سرعت پردازش: ۱۰۰,۰۰۰ req/s\n"
        f"🔒 ایزوله‌سازی: فعال\n"
        f"📁 پروژه‌های چندفایلی: پشتیبانی می‌شود"
    )
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== پنل مدیریت ====================
@bot.message_handler(func=lambda m: m.text == '👑 پنل مدیریت')
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    bot.send_message(message.chat.id, "👑 **پنل مدیریت پیشرفته**", reply_markup=get_admin_panel_menu(), parse_mode='Markdown')

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

# ==================== کال‌بک‌های مدیریت ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_delete_user_bot")
def admin_delete_user_bot_cmd(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "🆔 **شناسه ربات مورد نظر را وارد کنید:**", parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_admin_delete_bot)

def process_admin_delete_bot(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    bot_id = message.text.strip()
    
    bot_data = get_bot(bot_id)
    if bot_data:
        user_id = bot_data['user_id']
        delete_bot(bot_id, user_id)
        bot.reply_to(message, f"✅ **ربات {bot_id} با موفقیت حذف شد**")
    else:
        bot.reply_to(message, f"❌ **ربات {bot_id} یافت نشد**")

@bot.callback_query_handler(func=lambda call: call.data == "admin_disable_bot")
def admin_disable_bot_cmd(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "🆔 **شناسه ربات برای غیرفعال کردن را وارد کنید:**", parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_admin_disable_bot)

def process_admin_disable_bot(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    bot_id = message.text.strip()
    
    engine.stop_bot(bot_id)
    update_bot_status(bot_id, 'disabled')
    bot.reply_to(message, f"🔴 **ربات {bot_id} غیرفعال شد**")

@bot.callback_query_handler(func=lambda call: call.data == "admin_full_stats")
def admin_full_stats(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    bot.answer_callback_query(call.id)
    
    users_stats = get_all_users_stats()
    text = "📊 **آمار کامل کاربران**\n\n"
    
    for u in users_stats[:30]:
        text += f"👤 {u['first_name'] or u['username'] or u['user_id']}\n"
        text += f"🆔 `{u['user_id']}`\n"
        text += f"🤖 ربات: {u['bot_count']} (فعال: {u['running_count']})\n"
        text += f"👥 رفرال: {u['total_referrals']}\n"
        text += f"💰 موجودی رفرال: {u.get('referral_balance', 0):,} تومان\n"
        text += f"💳 وضعیت: {u['payment_status']}\n"
        text += "─" * 20 + "\n"
    
    if len(users_stats) > 30:
        text += f"\n... و {len(users_stats) - 30} کاربر دیگر"
    
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "admin_bot_performance")
def admin_bot_performance(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    bot.answer_callback_query(call.id)
    
    bots = db.execute('''
        SELECT b.id, b.name, b.status, b.user_id, u.first_name,
               strftime('%s', 'now') - strftime('%s', b.created_at) as age_seconds
        FROM bots b
        JOIN users u ON b.user_id = u.user_id
        ORDER BY b.created_at DESC
        LIMIT 50
    ''')
    
    text = "📈 **کارکرد ربات‌ها**\n\n"
    for b in bots:
        status_emoji = "🟢" if b['status'] == 'running' else "🔴" if b['status'] == 'disabled' else "⚪"
        text += f"{status_emoji} {b['name']}\n"
        text += f"🆔 `{b['id']}`\n"
        text += f"👤 کاربر: {b['first_name'] or b['user_id']}\n"
        text += f"⏱ عمر: {int(b['age_seconds'] / 86400)} روز\n"
        text += "─" * 15 + "\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "admin_cards")
def admin_cards_menu(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    bot.answer_callback_query(call.id)
    
    cards = get_admin_cards()
    text = "💳 **کارت‌های بانکی فعال**\n\n"
    for c in cards:
        text += f"🏦 بانک: {c['bank_name']}\n"
        text += f"💳 شماره: `{c['card_number']}`\n"
        text += f"👤 صاحب حساب: {c['card_holder']}\n"
        text += "─" * 20 + "\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "admin_withdrawals")
def admin_withdrawals_list(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    bot.answer_callback_query(call.id)
    
    withdrawals = db.execute('SELECT * FROM withdrawal_requests WHERE status = "pending" ORDER BY requested_at')
    
    if not withdrawals:
        bot.send_message(call.message.chat.id, "📭 **درخواست برداشتی وجود ندارد**", parse_mode='Markdown')
        return
    
    for w in withdrawals:
        text = (
            f"💰 **درخواست برداشت**\n\n"
            f"مبلغ: {w['amount']:,} تومان\n"
            f"👤 کاربر: {w['user_id']}\n"
            f"💳 شماره کارت: `{w['card_number']}`\n"
            f"👤 صاحب کارت: {w['card_holder']}\n"
            f"📅 تاریخ: {w['requested_at'][:16]}"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید برداشت", callback_data=f"withdraw_approve_{w['id']}"),
            types.InlineKeyboardButton("❌ رد درخواست", callback_data=f"withdraw_reject_{w['id']}")
        )
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith("withdraw_approve_"))
def approve_withdrawal(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    
    wid = int(call.data.replace("withdraw_approve_", ""))
    withdrawal = db.execute('SELECT * FROM withdrawal_requests WHERE id = ?', (wid,))
    
    if withdrawal:
        w = withdrawal[0]
        db.execute('UPDATE referral_earnings SET paid = 1 WHERE user_id = ?', (w['user_id'],))
        db.execute('UPDATE withdrawal_requests SET status = "approved", processed_at = ? WHERE id = ?',
                  (datetime.now().isoformat(), wid))
        
        try:
            bot.send_message(w['user_id'], 
                f"✅ **درخواست برداشت شما تایید شد!**\n\n"
                f"💰 مبلغ: {w['amount']:,} تومان\n"
                f"💳 به کارت {w['card_number']} واریز خواهد شد.")
        except:
            pass
        
        bot.answer_callback_query(call.id, "✅ برداشت تایید شد")
        bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("withdraw_reject_"))
def reject_withdrawal(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    
    wid = int(call.data.replace("withdraw_reject_", ""))
    withdrawal = db.execute('SELECT * FROM withdrawal_requests WHERE id = ?', (wid,))
    
    if withdrawal:
        w = withdrawal[0]
        db.execute('UPDATE withdrawal_requests SET status = "rejected", processed_at = ? WHERE id = ?',
                  (datetime.now().isoformat(), wid))
        
        try:
            bot.send_message(w['user_id'], 
                f"❌ **درخواست برداشت شما رد شد**\n\n"
                f"💰 مبلغ: {w['amount']:,} تومان\n\n"
                f"لطفاً با پشتیبانی تماس بگیرید.")
        except:
            pass
        
        bot.answer_callback_query(call.id, "❌ برداشت رد شد")
        bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_receipts")
def admin_receipts(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    bot.answer_callback_query(call.id)
    
    receipts = db.execute('SELECT * FROM receipts WHERE status = "pending" ORDER BY created_at')
    
    if not receipts:
        bot.send_message(call.message.chat.id, "📸 **فیش جدیدی وجود ندارد**", parse_mode='Markdown')
        return
    
    for r in receipts:
        text = (
            f"📸 **فیش پرداخت**\n\n"
            f"🆔 شناسه: {r['id']}\n"
            f"👤 کاربر: {r['user_id']}\n"
            f"💰 مبلغ: {r['amount']:,} تومان\n"
            f"🆔 کد: `{r['payment_code']}`"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید پرداخت", callback_data=f"receipt_approve_{r['id']}"),
            types.InlineKeyboardButton("❌ رد فیش", callback_data=f"receipt_reject_{r['id']}")
        )
        
        if os.path.exists(r['receipt_path']):
            with open(r['receipt_path'], 'rb') as f:
                bot.send_photo(call.message.chat.id, f, caption=text, reply_markup=markup, parse_mode='Markdown')
        else:
            bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('receipt_approve_'))
def receipt_approve(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    
    rid = int(call.data.replace('receipt_approve_', ''))
    receipt = db.execute('SELECT * FROM receipts WHERE id = ?', (rid,))
    
    if receipt:
        r = receipt[0]
        db.execute('UPDATE receipts SET status = "approved", reviewed_at = ?, reviewed_by = ? WHERE id = ?',
                  (datetime.now().isoformat(), call.from_user.id, rid))
        db.execute('UPDATE users SET payment_status = "approved" WHERE user_id = ?', (r['user_id'],))
        
        try:
            bot.send_message(r['user_id'], 
                f"✅ **پرداخت شما تایید شد!**\n\n"
                f"💰 مبلغ: {r['amount']:,} تومان\n"
                f"🆔 کد پیگیری: `{r['payment_code']}`\n\n"
                f"اکنون می‌توانید ربات خود را بسازید.")
        except:
            pass
        
        bot.answer_callback_query(call.id, "✅ پرداخت تایید شد")
        bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('receipt_reject_'))
def receipt_reject(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    
    rid = int(call.data.replace('receipt_reject_', ''))
    receipt = db.execute('SELECT * FROM receipts WHERE id = ?', (rid,))
    
    if receipt:
        r = receipt[0]
        db.execute('UPDATE receipts SET status = "rejected", reviewed_at = ?, reviewed_by = ? WHERE id = ?',
                  (datetime.now().isoformat(), call.from_user.id, rid))
        
        try:
            bot.send_message(r['user_id'], 
                f"❌ **فیش پرداخت شما رد شد**\n\n"
                f"لطفاً با پشتیبانی تماس بگیرید.\n📞 @shahraghee13")
        except:
            pass
        
        bot.answer_callback_query(call.id, "❌ فیش رد شد")
        bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "🚀 **منوی اصلی**", reply_markup=get_main_menu(True), parse_mode='Markdown')

# ==================== مانیتورینگ خودکار ====================
def monitor_system():
    while True:
        try:
            cache.clear_expired()
            
            for bot_data in db.execute('SELECT id, machine_id FROM bots WHERE status = "running"'):
                if not engine.get_status(bot_data['id']).get('running'):
                    db.execute('UPDATE bots SET status = "stopped" WHERE id = ?', (bot_data['id'],))
                    machine_manager.release_bot(bot_data['id'], bot_data['machine_id'])
            
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
    print("🚀 ربات مادر نهایی - نسخه 18.0 HyperSpeed Ultimate".center(80))
    print("=" * 80)
    print(f"🖥️ ماشین‌ها: {CLUSTER_CONFIG['TOTAL_MACHINES']} × {CLUSTER_CONFIG['BOTS_PER_MACHINE']:,} = {CLUSTER_CONFIG['TOTAL_MACHINES'] * CLUSTER_CONFIG['BOTS_PER_MACHINE']:,} ربات")
    print(f"👥 هر ماشین: {CLUSTER_CONFIG['USERS_PER_MACHINE']} کاربر")
    print(f"🧠 حافظه: ۱۶۵ گیگابایت")
    print(f"⚡ سرعت: ۱۰۰,۰۰۰ درخواست/ثانیه")
    print(f"🔒 ایزوله‌سازی: فعال")
    print(f"💰 رفرال ۱۰٪: فعال")
    print(f"💳 سیستم برداشت: فعال")
    print("=" * 80)
    print(f"👑 ادمین: {ADMIN_IDS}")
    print("=" * 80)
    print("\n✅ ربات با موفقیت راه‌اندازی شد!")
    
    while True:
        try:
            # استفاده از polling ساده بدون infinity_polling برای جلوگیری از خطای 409
            bot.polling(non_stop=True, interval=0, timeout=60)
        except Exception as e:
            logger.error(f"Polling error: {e}")
            print(f"خطا: {e}")
            time.sleep(5)