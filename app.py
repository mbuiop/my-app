#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
═══════════════════════════════════════════════════════════════════════════════
🚀 ربات مادر نهایی - نسخه 100.0 Enterprise Mega Scale
⚡ پشتیبانی از میلیون‌ها کاربر - معماری میکروسرویس کامل
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import time
import json
import redis
import signal
import secrets
import hashlib
import logging
import sqlite3
import threading
import subprocess
import zipfile
import shutil
import re
import queue
import uuid
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from functools import wraps
from collections import defaultdict
from typing import Optional, Dict, Any, List

import telebot
from telebot import types
import requests
from flask import Flask, request, jsonify
from prometheus_client import Counter, Gauge, Histogram, generate_latest, REGISTRY
import sentry_sdk
from sentry_sdk import capture_exception
from celery import Celery
from cryptography.fernet import Fernet
import boto3
from elasticsearch import Elasticsearch
import psutil
import schedule
from dotenv import load_dotenv

# ==================== بارگذاری متغیرهای محیطی ====================
load_dotenv()

# ==================== متغیرهای محیطی امن ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8266270866:AAF6m1x4weSUEvzIj1gkbIS_j0yAdxCSs78")
ADMIN_IDS = json.loads(os.getenv("ADMIN_IDS", "[327855654]"))
BOT_USERNAME = os.getenv("BOT_USERNAME", "ROBTTSAZE_bot")

# رمزنگاری
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key())
cipher = Fernet(ENCRYPTION_KEY)

# Redis
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Sentry
SENTRY_DSN = os.getenv("SENTRY_DSN", "")
if SENTRY_DSN:
    sentry_sdk.init(dsn=SENTRY_DSN, traces_sample_rate=0.1)

# AWS S3
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY", "")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY", "")
S3_BUCKET = os.getenv("S3_BUCKET", "mother-bot-backups")

# Elasticsearch
ELASTICSEARCH_HOST = os.getenv("ELASTICSEARCH_HOST", "localhost")

# Webhook
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

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
    'QUEUE': os.path.join(BASE_DIR, "queue"),
    'BACKUPS': os.path.join(BASE_DIR, "backups"),
    'ARCHIVE': os.path.join(BASE_DIR, "archive")
}

for dir_path in DIRS.values():
    os.makedirs(dir_path, exist_ok=True)

# ==================== تنظیمات پیش‌فرض ====================
DEFAULT_SETTINGS = {
    'card_number': "5892101187322777",
    'card_number_display': "5892 1011 8732 2777",
    'card_holder': "مرتضی نیکخو خنجری",
    'card_bank': "بانک ملی - سپهر",
    'subscription_price': 2000000,
    'subscription_price_str': "۲,۰۰۰,۰۰۰ تومان",
    'withdraw_percent': 7,
    'min_withdraw': 2000000,
    'max_builds_per_hour': 100,
    'max_concurrent_builds': 100,
    'rate_limit_per_second': 10,
    'rate_limit_per_minute': 100,
    'rate_limit_per_hour': 500,
    'health_check_interval': 30,
    'auto_scale_threshold': 70,
    'guide_text': "📚 راهنمای استفاده\n\n1️⃣ برای ساخت ربات، فایل .py یا .zip خود را ارسال کنید\n2️⃣ پس از پرداخت اشتراک ماهیانه، می‌توانید ربات بسازید\n3️⃣ هر کاربر می‌تواند تا سقف نامحدود ربات بسازد\n4️⃣ با دعوت دوستان، ۷٪ کمیسیون دریافت کنید\n5️⃣ پس از رسیدن به ۲ میلیون تومان، می‌توانید برداشت کنید"
}

# ==================== کتابخانه‌های محبوب ====================
POPULAR_LIBRARIES = {
    'requests': 'requests', 'aiohttp': 'aiohttp', 'httpx': 'httpx',
    'flask': 'flask', 'fastapi': 'fastapi', 'django': 'django',
    'sqlalchemy': 'sqlalchemy', 'asyncpg': 'asyncpg', 'redis': 'redis',
    'motor': 'motor', 'pyTelegramBotAPI': 'pyTelegramBotAPI',
    'aiogram': 'aiogram', 'numpy': 'numpy', 'pandas': 'pandas',
    'pillow': 'Pillow', 'beautifulsoup4': 'beautifulsoup4',
    'selenium': 'selenium', 'jdatetime': 'jdatetime',
    'cryptography': 'cryptography', 'loguru': 'loguru', 'tqdm': 'tqdm'
}

# ==================== لاگینگ ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            os.path.join(DIRS['LOGS'], 'mother_bot.log'),
            maxBytes=500*1024*1024,
            backupCount=10,
            encoding='utf-8'
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('MotherBot')

# ==================== اتصال به Redis ====================
class RedisManager:
    def __init__(self):
        self.redis_client = None
        self._connect()
    
    def _connect(self):
        try:
            self.redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD,
                decode_responses=True,
                socket_keepalive=True,
                retry_on_timeout=True,
                health_check_interval=30
            )
            self.redis_client.ping()
            logger.info("✅ Connected to Redis")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            self.redis_client = None
    
    def get(self, key):
        if self.redis_client:
            return self.redis_client.get(key)
        return None
    
    def set(self, key, value, ttl=3600):
        if self.redis_client:
            self.redis_client.setex(key, ttl, value)
    
    def delete(self, key):
        if self.redis_client:
            self.redis_client.delete(key)
    
    def incr(self, key):
        if self.redis_client:
            return self.redis_client.incr(key)
        return 0
    
    def exists(self, key):
        if self.redis_client:
            return self.redis_client.exists(key)
        return 0
    
    def expire(self, key, ttl):
        if self.redis_client:
            self.redis_client.expire(key, ttl)
    
    def lpush(self, key, value):
        if self.redis_client:
            return self.redis_client.lpush(key, value)
        return 0
    
    def rpop(self, key):
        if self.redis_client:
            return self.redis_client.rpop(key)
        return None
    
    def llen(self, key):
        if self.redis_client:
            return self.redis_client.llen(key)
        return 0
    
    def hset(self, key, field, value):
        if self.redis_client:
            self.redis_client.hset(key, field, value)
    
    def hget(self, key, field):
        if self.redis_client:
            return self.redis_client.hget(key, field)
        return None
    
    def hgetall(self, key):
        if self.redis_client:
            return self.redis_client.hgetall(key)
        return {}
    
    def sadd(self, key, *values):
        if self.redis_client:
            self.redis_client.sadd(key, *values)
    
    def srem(self, key, value):
        if self.redis_client:
            self.redis_client.srem(key, value)
    
    def smembers(self, key):
        if self.redis_client:
            return self.redis_client.smembers(key)
        return set()

redis_manager = RedisManager()

# ==================== Celery برای صف ساخت پیشرفته ====================
REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/1" if REDIS_PASSWORD else f"redis://{REDIS_HOST}:{REDIS_PORT}/1"

celery_app = Celery(
    'mother_bot',
    broker=REDIS_URL,
    backend=REDIS_URL.replace('/1', '/2')
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Tehran',
    enable_utc=False,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_retry_delay=60,
    task_max_retries=3
)

# ==================== Prometheus Metrics ====================
BUILDS_TOTAL = Counter('bot_builds_total', 'Total number of bot builds', ['status'])
ACTIVE_BOTS = Gauge('active_bots', 'Currently running bots')
QUEUE_SIZE = Gauge('build_queue_size', 'Current build queue size')
USERS_TOTAL = Gauge('users_total', 'Total registered users')
SUBSCRIPTIONS_ACTIVE = Gauge('subscriptions_active', 'Active subscriptions')
REQUEST_DURATION = Histogram('request_duration_seconds', 'Request duration', ['endpoint'])
ERRORS_TOTAL = Counter('errors_total', 'Total errors', ['type'])
BOTS_TOTAL = Gauge('bots_total', 'Total bots created')
DB_SIZE = Gauge('db_size_bytes', 'Database size in bytes')

# ==================== Elasticsearch برای لاگ مرکزی ====================
class ElasticsearchLogger:
    def __init__(self):
        self.es = None
        try:
            self.es = Elasticsearch([ELASTICSEARCH_HOST])
            logger.info("✅ Connected to Elasticsearch")
        except Exception as e:
            logger.error(f"Elasticsearch connection failed: {e}")
    
    def log(self, level, message, extra=None):
        if self.es:
            doc = {
                'timestamp': datetime.now().isoformat(),
                'level': level,
                'message': message,
                'service': 'mother-bot',
                'extra': extra or {}
            }
            try:
                self.es.index(index='mother-bot-logs', document=doc)
            except Exception as e:
                logger.error(f"Failed to log to Elasticsearch: {e}")

es_logger = ElasticsearchLogger()

# ==================== Flask Webhook Server ====================
flask_app = Flask(__name__)

@flask_app.route('/webhook', methods=['POST'])
def webhook():
    start_time = time.time()
    try:
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        REQUEST_DURATION.labels(endpoint='webhook').observe(time.time() - start_time)
        return 'OK', 200
    except Exception as e:
        ERRORS_TOTAL.labels(type='webhook').inc()
        capture_exception(e)
        logger.error(f"Webhook error: {e}")
        return 'Error', 500

@flask_app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'redis': redis_manager.redis_client is not None,
        'active_bots': ACTIVE_BOTS._value.get() if hasattr(ACTIVE_BOTS, '_value') else 0,
        'queue_size': QUEUE_SIZE._value.get() if hasattr(QUEUE_SIZE, '_value') else 0,
        'version': '100.0'
    })

@flask_app.route('/metrics', methods=['GET'])
def metrics():
    return generate_latest(REGISTRY)

@flask_app.route('/backup', methods=['POST'])
def trigger_backup():
    auth_token = request.headers.get('X-Auth-Token')
    if auth_token != os.getenv('BACKUP_TOKEN', 'secret'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    threading.Thread(target=backup_database).start()
    return jsonify({'status': 'backup started', 'timestamp': datetime.now().isoformat()})

# ==================== دیتابیس ====================
class Database:
    def __init__(self):
        self.conn = None
        self._init_db()
        self._init_tables()
    
    def _init_db(self):
        db_path = os.path.join(DIRS['DB'], 'mother_bot.db')
        self.conn = sqlite3.connect(
            db_path,
            timeout=60,
            check_same_thread=False
        )
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA cache_size=-500000")
        self.conn.execute("PRAGMA page_size=8192")
        self.conn.execute("PRAGMA mmap_size=30000000000")
        
        # آپدیت متریک اندازه دیتابیس
        DB_SIZE.set(os.path.getsize(db_path))
    
    def execute(self, query, params=()):
        try:
            cursor = self.conn.execute(query, params)
            self.conn.commit()
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"DB error: {e}")
            es_logger.log('ERROR', f"DB error: {e}")
            return []
    
    def encrypt_token(self, token):
        return cipher.encrypt(token.encode()).decode()
    
    def decrypt_token(self, encrypted_token):
        return cipher.decrypt(encrypted_token.encode()).decode()
    
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
                warning_sent INTEGER DEFAULT 0,
                total_builds INTEGER DEFAULT 0,
                last_build_at TIMESTAMP,
                language TEXT DEFAULT 'fa',
                region TEXT DEFAULT 'IR',
                device_info TEXT,
                last_ip TEXT,
                is_banned INTEGER DEFAULT 0
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
                join_enabled INTEGER DEFAULT 1,
                join_block_message TEXT DEFAULT '🚫 سرور در حال حاضر پر است. لطفاً بعداً تلاش کنید.',
                health_status TEXT DEFAULT 'healthy',
                last_health_check TIMESTAMP,
                restart_count INTEGER DEFAULT 0,
                schedule_start TEXT,
                schedule_stop TEXT,
                webhook_url TEXT,
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
                max_bots INTEGER DEFAULT 10000,
                memory_used INTEGER DEFAULT 0,
                max_memory INTEGER DEFAULT 512000,
                cpu_usage REAL DEFAULT 0,
                last_heartbeat TIMESTAMP,
                created_at TIMESTAMP,
                auto_scaled INTEGER DEFAULT 0,
                region TEXT DEFAULT 'default',
                is_kubernetes_pod INTEGER DEFAULT 0
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
                resolved BOOLEAN DEFAULT 0,
                stack_trace TEXT
            )
        ''')
        
        # تنظیمات سیستم
        self.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # آمار روزانه
        self.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT PRIMARY KEY,
                new_users INTEGER DEFAULT 0,
                new_bots INTEGER DEFAULT 0,
                new_subscriptions INTEGER DEFAULT 0,
                total_revenue INTEGER DEFAULT 0,
                active_users INTEGER DEFAULT 0,
                total_requests INTEGER DEFAULT 0,
                avg_response_time REAL DEFAULT 0
            )
        ''')
        
        # فعالیت‌های کاربران
        self.execute('''
            CREATE TABLE IF NOT EXISTS user_activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                details TEXT,
                ip TEXT,
                created_at TIMESTAMP
            )
        ''')
        
        # بکاپ‌ها
        self.execute('''
            CREATE TABLE IF NOT EXISTS backups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                size INTEGER,
                location TEXT,
                created_at TIMESTAMP,
                status TEXT DEFAULT 'success'
            )
        ''')
        
        # تنظیمات پیش‌فرض
        for key, value in DEFAULT_SETTINGS.items():
            self.execute('INSERT OR IGNORE INTO system_settings (key, value) VALUES (?, ?)', (key, str(value)))
        
        # ایجاد ماشین‌ها
        for i in range(1, 101):
            self.execute('''
                INSERT OR IGNORE INTO machines (id, name, status, max_bots, max_memory, created_at, is_kubernetes_pod)
                VALUES (?, ?, 'active', ?, ?, ?, 1)
            ''', (i, f"k8s-pod-{i:03d}", 10000, 512000, datetime.now().isoformat()))

db = Database()

# ==================== بکاپ خودکار به S3 ====================
def backup_database():
    """بکاپ خودکار دیتابیس و آپلود در S3"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(DIRS['BACKUPS'], f"mother_bot_{timestamp}.db")
        
        # کپی دیتابیس
        shutil.copy2(os.path.join(DIRS['DB'], 'mother_bot.db'), backup_file)
        
        # فشرده‌سازی
        import gzip
        with open(backup_file, 'rb') as f_in:
            with gzip.open(f"{backup_file}.gz", 'wb') as f_out:
                f_out.writelines(f_in)
        
        os.remove(backup_file)
        backup_gz = f"{backup_file}.gz"
        
        # آپلود در S3
        if AWS_ACCESS_KEY and S3_BUCKET:
            s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)
            s3.upload_file(backup_gz, S3_BUCKET, f"backups/{timestamp}/mother_bot.db.gz")
            location = f"s3://{S3_BUCKET}/backups/{timestamp}/"
        else:
            location = "local"
        
        # ذخیره در دیتابیس
        size = os.path.getsize(backup_gz)
        db.execute('INSERT INTO backups (filename, size, location, created_at) VALUES (?, ?, ?, ?)',
                  (f"mother_bot_{timestamp}.db.gz", size, location, datetime.now().isoformat()))
        
        # حذف بکاپ‌های قدیمی
        cutoff = datetime.now() - timedelta(days=30)
        for f in os.listdir(DIRS['BACKUPS']):
            fpath = os.path.join(DIRS['BACKUPS'], f)
            if os.path.getctime(fpath) < cutoff.timestamp():
                os.remove(fpath)
        
        logger.info(f"✅ Backup created: {backup_gz}")
        
        # اطلاع به ادمین
        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(admin_id, f"✅ بکاپ خودکار انجام شد: {timestamp}\nحجم: {size/1024/1024:.2f} MB")
            except:
                pass
    
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        capture_exception(e)

def schedule_backups():
    """زمانبندی بکاپ هر ۶ ساعت"""
    while True:
        schedule.run_pending()
        time.sleep(60)

# تنظیم زمانبندی بکاپ
schedule.every(6).hours.do(backup_database)
threading.Thread(target=schedule_backups, daemon=True).start()

# ==================== Cache با Redis ====================
class RedisCache:
    def __init__(self, redis_manager):
        self.redis = redis_manager
    
    def get(self, key):
        val = self.redis.get(key)
        if val:
            try:
                return json.loads(val)
            except:
                return val
        return None
    
    def set(self, key, value, ttl=3600):
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        self.redis.set(key, value, ttl)
    
    def delete(self, key):
        self.redis.delete(key)
    
    def incr(self, key):
        return self.redis.incr(key)
    
    def exists(self, key):
        return self.redis.exists(key)

cache = RedisCache(redis_manager)

# ==================== Rate Limiter پیشرفته ====================
class AdvancedRateLimiter:
    def __init__(self):
        self.redis = redis_manager
    
    def is_allowed(self, user_id, limit_per_second=10, limit_per_minute=100, limit_per_hour=500):
        now = time.time()
        
        # بررسی در ثانیه
        sec_key = f"rate:sec:{user_id}:{int(now)}"
        sec_count = self.redis.incr(sec_key)
        if sec_count == 1:
            self.redis.expire(sec_key, 1)
        if sec_count > limit_per_second:
            return False
        
        # بررسی در دقیقه
        min_key = f"rate:min:{user_id}:{int(now/60)}"
        min_count = self.redis.incr(min_key)
        if min_count == 1:
            self.redis.expire(min_key, 60)
        if min_count > limit_per_minute:
            return False
        
        # بررسی در ساعت
        hour_key = f"rate:hour:{user_id}:{int(now/3600)}"
        hour_count = self.redis.incr(hour_key)
        if hour_count == 1:
            self.redis.expire(hour_key, 3600)
        if hour_count > limit_per_hour:
            return False
        
        return True
    
    def get_user_builds_today(self, user_id):
        today = datetime.now().date().isoformat()
        key = f"builds:{user_id}:{today}"
        cached = cache.get(key)
        if cached is not None:
            return cached
        result = db.execute("SELECT COUNT(*) as count FROM bots WHERE user_id = ? AND DATE(created_at) = ?", (user_id, today))
        count = result[0]['count'] if result else 0
        cache.set(key, count, ttl=3600)
        return count
    
    def increment_user_builds(self, user_id):
        today = datetime.now().date().isoformat()
        key = f"builds:{user_id}:{today}"
        count = self.get_user_builds_today(user_id) + 1
        cache.set(key, count, ttl=3600)
        return count

rate_limiter = AdvancedRateLimiter()

# ==================== صف ساخت ====================
class BuildQueue:
    def __init__(self):
        self.queue_name = "build_queue"
        self.processing = {}
        self.lock = threading.RLock()
    
    def add_build(self, user_id, file_path, file_name, chat_id, message_id, build_data):
        build_id = str(uuid.uuid4())[:8]
        build_item = {
            'id': build_id,
            'user_id': user_id,
            'file_path': file_path,
            'file_name': file_name,
            'chat_id': chat_id,
            'message_id': message_id,
            'added_at': time.time(),
            'build_data': build_data
        }
        
        redis_manager.lpush(self.queue_name, json.dumps(build_item))
        
        with self.lock:
            self.processing[build_id] = {'status': 'queued', 'position': self.get_queue_length()}
        
        QUEUE_SIZE.set(self.get_queue_length())
        return build_id
    
    def get_queue_length(self):
        return redis_manager.llen(self.queue_name)
    
    def get_status(self, build_id):
        with self.lock:
            if build_id in self.processing:
                return self.processing[build_id]
        return None

build_queue = BuildQueue()

# ==================== Celery Task برای ساخت ربات ====================
@celery_app.task(bind=True, max_retries=3)
def build_bot_task(self, build_data):
    """ساخت ربات با Celery - مقیاس بالا"""
    try:
        bot_id = build_data['bot_id']
        code = build_data['main_code']
        token = build_data['token']
        
        result = machine_manager.run_bot(bot_id, code, token)
        
        if result['success']:
            add_bot(
                build_data['user_id'],
                bot_id,
                token,
                build_data['bot_info']['first_name'],
                build_data['bot_info']['username'],
                build_data['file_path'],
                result['pid'],
                result['machine_id']
            )
            
            BUILDS_TOTAL.labels(status='success').inc()
            BOTS_TOTAL.inc()
            
            # کمیسیون رفرال
            user = get_user(build_data['user_id'])
            if user and user.get('referred_by'):
                commission = int(get_setting('subscription_price') * get_setting('withdraw_percent') / 100)
                add_wallet_balance(user['referred_by'], commission)
                
                try:
                    temp_bot = telebot.TeleBot(BOT_TOKEN)
                    temp_bot.send_message(user['referred_by'], f"🎉 کمیسیون {commission:,} تومان به کیف پول شما اضافه شد")
                except:
                    pass
            
            # ویرایش پیام
            try:
                temp_bot = telebot.TeleBot(BOT_TOKEN)
                temp_bot.edit_message_text(
                    f"✅ ربات {build_data['bot_info']['first_name']} با موفقیت ساخته شد!",
                    build_data['chat_id'],
                    build_data['message_id']
                )
            except:
                pass
            
        else:
            BUILDS_TOTAL.labels(status='failed').inc()
            
            try:
                temp_bot = telebot.TeleBot(BOT_TOKEN)
                temp_bot.edit_message_text(
                    f"❌ خطا در ساخت: {result.get('error', 'مشخص نشده')}",
                    build_data['chat_id'],
                    build_data['message_id']
                )
            except:
                pass
        
        QUEUE_SIZE.set(build_queue.get_queue_length())
        return result
    
    except Exception as e:
        BUILDS_TOTAL.labels(status='error').inc()
        ERRORS_TOTAL.labels(type='celery_build').inc()
        capture_exception(e)
        logger.error(f"Celery build error: {e}")
        raise self.retry(exc=e, countdown=60)

# ==================== Health Checker ====================
class HealthChecker:
    def __init__(self):
        self.checking = True
        self.thread = threading.Thread(target=self._monitor, daemon=True)
        self.thread.start()
    
    def _monitor(self):
        while self.checking:
            try:
                interval = get_setting('health_check_interval')
                
                for bot_rec in db.execute('SELECT id, token, status FROM bots WHERE status = "running"'):
                    bot_id = bot_rec['id']
                    
                    # بررسی با Redis
                    health_key = f"health:{bot_id}"
                    last_health = cache.get(health_key)
                    
                    if last_health and time.time() - last_health < interval:
                        continue
                    
                    token = db.decrypt_token(bot_rec['token'])
                    
                    try:
                        resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
                        if resp.status_code != 200:
                            self._restart_bot(bot_id)
                        else:
                            cache.set(health_key, time.time(), ttl=interval)
                    except:
                        self._restart_bot(bot_id)
                
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Health check error: {e}")
                time.sleep(60)
    
    def _restart_bot(self, bot_id):
        bot_rec = db.execute('SELECT * FROM bots WHERE id = ?', (bot_id,))
        if not bot_rec:
            return
        
        bot_rec = dict(bot_rec[0])
        machine_manager.stop_bot(bot_id)
        time.sleep(2)
        
        if os.path.exists(bot_rec['file_path']):
            try:
                with open(bot_rec['file_path'], 'r', encoding='utf-8', errors='ignore') as f:
                    code = f.read()
                
                token = db.decrypt_token(bot_rec['token'])
                result = machine_manager.run_bot(bot_id, code, token)
                if result['success']:
                    db.execute('UPDATE bots SET status = "running", machine_id = ?, pid = ?, last_active = ? WHERE id = ?',
                              (result['machine_id'], result['pid'], datetime.now().isoformat(), bot_id))
                    logger.info(f"✅ Auto-restarted bot {bot_id}")
                    
                    user = db.execute('SELECT user_id FROM bots WHERE id = ?', (bot_id,))
                    if user:
                        try:
                            bot.send_message(user[0]['user_id'], f"🔄 ربات {bot_rec['name']} به صورت خودکار ریستارت شد.")
                        except:
                            pass
                else:
                    db.execute('UPDATE bots SET status = "error" WHERE id = ?', (bot_id,))
            except Exception as e:
                logger.error(f"Failed to restart bot {bot_id}: {e}")

# ==================== Auto-Scale Manager ====================
class AutoScaleManager:
    def __init__(self):
        self.monitoring = True
        self.thread = threading.Thread(target=self._monitor, daemon=True)
        self.thread.start()
    
    def _monitor(self):
        while self.monitoring:
            try:
                threshold = get_setting('auto_scale_threshold')
                
                machines = db.execute("SELECT id, current_bots, max_bots FROM machines WHERE status = 'active'")
                total_capacity = sum(m['max_bots'] for m in machines)
                total_used = sum(m['current_bots'] for m in machines)
                usage_percent = (total_used / total_capacity) * 100 if total_capacity > 0 else 0
                
                ACTIVE_BOTS.set(total_used)
                
                if usage_percent > threshold:
                    self._scale_up()
                
                time.sleep(60)
            except Exception as e:
                logger.error(f"Auto-scale error: {e}")
                time.sleep(60)
    
    def _scale_up(self):
        """افزایش مقیاس"""
        try:
            # ایجاد ماشین جدید در دیتابیس
            new_id = len(db.execute("SELECT id FROM machines")) + 1
            db.execute('''
                INSERT INTO machines (id, name, status, max_bots, max_memory, created_at, is_kubernetes_pod)
                VALUES (?, ?, 'active', ?, ?, ?, 1)
            ''', (new_id, f"k8s-pod-{new_id:03d}", 10000, 512000, datetime.now().isoformat()))
            
            logger.info(f"✅ Scaled up - new machine {new_id} created")
            
            for admin_id in ADMIN_IDS:
                try:
                    bot.send_message(admin_id, f"📈 مقیاس سیستم افزایش یافت - ماشین جدید {new_id} اضافه شد")
                except:
                    pass
        
        except Exception as e:
            logger.error(f"Scale up failed: {e}")
    
    def get_scaling_recommendation(self):
        machines = db.execute("SELECT * FROM machines WHERE status = 'active'")
        total_capacity = sum(m['max_bots'] for m in machines)
        total_used = sum(m['current_bots'] for m in machines)
        usage_percent = (total_used / total_capacity) * 100 if total_capacity > 0 else 0
        
        if usage_percent > 80:
            return "⚠️ نیاز به مقیاس بالا - اضافه کردن ماشین جدید"
        elif usage_percent > 60:
            return "⚡ نزدیک به ظرفیت، پیشنهاد مقیاس"
        elif usage_percent < 20 and len(machines) > 5:
            return "📉 می‌توانید مقیاس را کاهش دهید"
        else:
            return "✅ ظرفیت کافی است"

# ==================== مدیریت ماشین‌ها ====================
class MachineManager:
    def __init__(self):
        self.port_counter = 8000
        self.processes = {}
        self.lock = threading.RLock()
    
    def get_available_machine(self):
        cached_machine = cache.get("available_machine")
        if cached_machine:
            return cached_machine
        
        machines = db.execute("SELECT * FROM machines WHERE status = 'active' ORDER BY current_bots ASC")
        for m in machines:
            if m['current_bots'] < m['max_bots']:
                cache.set("available_machine", m['id'], ttl=30)
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
        cache.delete("available_machine")
    
    def release_bot(self, bot_id, machine_id):
        db.execute("UPDATE machines SET current_bots = current_bots - 1 WHERE id = ?", (machine_id,))
        cache.delete("available_machine")
    
    def run_bot(self, bot_id, code, token):
        try:
            machine_id = self.get_available_machine()
            if not machine_id:
                return {'success': False, 'error': 'همه ماشین‌ها پر هستند'}
            
            port = self.get_available_port()
            bot_dir = os.path.join(DIRS['MACHINES'], f"machine_{machine_id:03d}", bot_id)
            os.makedirs(bot_dir, exist_ok=True)
            
            code_path = os.path.join(bot_dir, 'bot.py')
            encrypted_token = db.encrypt_token(token)
            
            join_check_code = f'''
# ========== سیستم مدیریت عضوگیری ==========
import sqlite3, os, time, threading
from functools import wraps

DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'database', 'mother_bot.db')
CHECK_INTERVAL = 30
join_enabled_cache = True
block_message_cache = "🚫 سرور پر است"

def update_cache():
    global join_enabled_cache, block_message_cache
    try:
        conn = sqlite3.connect(DB_PATH, timeout=3)
        cursor = conn.cursor()
        cursor.execute("SELECT join_enabled, join_block_message FROM bots WHERE id = ?", ("{bot_id}",))
        result = cursor.fetchone()
        conn.close()
        if result:
            join_enabled_cache = result[0] == 1
            block_message_cache = result[1] if result[1] else "🚫 سرور پر است"
    except:
        pass

def cache_updater():
    while True:
        update_cache()
        time.sleep(CHECK_INTERVAL)

threading.Thread(target=cache_updater, daemon=True).start()
update_cache()

def check_join_enabled(func):
    @wraps(func)
    def wrapper(message, *args, **kwargs):
        if not join_enabled_cache:
            bot.reply_to(message, block_message_cache)
            return
        return func(message, *args, **kwargs)
    return wrapper
# ===========================================
'''
            
            with open(code_path, 'w', encoding='utf-8') as f:
                f.write(join_check_code + "\n" + code)
            
            log_file = os.path.join(DIRS['LOGS'], f"bot_{bot_id}.log")
            
            process = subprocess.Popen(
                [sys.executable, code_path],
                stdout=open(log_file, 'a'),
                stderr=subprocess.STDOUT,
                cwd=bot_dir,
                start_new_session=True
            )
            
            time.sleep(1.5)
            
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
            'available': total_capacity - total_bots,
            'usage_percent': (total_bots / total_capacity) * 100 if total_capacity > 0 else 0
        }

# ایجاد نمونه‌ها
machine_manager = MachineManager()
health_checker = HealthChecker()
auto_scaler = AutoScaleManager()

# ==================== ربات تلگرام ====================
bot = telebot.TeleBot(BOT_TOKEN)
bot.delete_webhook()

# ==================== توابع کمکی ====================

def get_setting(key):
    cached = cache.get(f"setting_{key}")
    if cached is not None:
        return cached
    result = db.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
    if result:
        val = result[0]['value']
        if key in ['subscription_price', 'withdraw_percent', 'min_withdraw', 
                   'max_builds_per_hour', 'max_concurrent_builds', 'rate_limit_per_second',
                   'rate_limit_per_minute', 'rate_limit_per_hour',
                   'health_check_interval', 'auto_scale_threshold']:
            try:
                val = int(val)
            except:
                pass
        cache.set(f"setting_{key}", val, ttl=300)
        return val
    return DEFAULT_SETTINGS.get(key)

def update_setting(key, value):
    db.execute("UPDATE system_settings SET value = ? WHERE key = ?", (str(value), key))
    cache.delete(f"setting_{key}")

def generate_referral_code(user_id):
    return hashlib.md5(f"{user_id}_{time.time()}_{secrets.token_hex(4)}".encode()).hexdigest()[:12]

def get_user(user_id):
    cached = cache.get(f"user_{user_id}")
    if cached:
        return cached
    users = db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    if users:
        user = dict(users[0])
        cache.set(f"user_{user_id}", user, ttl=300)
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
    
    if referred_by and referred_by != user_id:
        db.execute('UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = ?', (referred_by,))
        db.execute('UPDATE daily_stats SET new_users = new_users + 1 WHERE date = ?', (datetime.now().date().isoformat(),))
    
    USERS_TOTAL.inc()
    cache.delete(f"user_{user_id}")
    return True

def check_subscription(user_id):
    user = get_user(user_id)
    if not user:
        return False
    
    if user.get('is_banned', 0) == 1:
        return False
    
    if user['subscription_status'] == 'active':
        if user['subscription_expiry']:
            expiry = datetime.fromisoformat(user['subscription_expiry'])
            if expiry > datetime.now():
                return True
            else:
                db.execute('UPDATE users SET subscription_status = "inactive", warning_sent = 0 WHERE user_id = ?', (user_id,))
                cache.delete(f"user_{user_id}")
    
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
    
    SUBSCRIPTIONS_ACTIVE.inc()
    
    db.execute('UPDATE daily_stats SET new_subscriptions = new_subscriptions + 1, total_revenue = total_revenue + ? WHERE date = ?',
              (get_setting('subscription_price'), datetime.now().date().isoformat()))
    
    build_guide = (
        "✅ **اشتراک شما با موفقیت فعال شد!**\n\n"
        "🎉 از اینکه ما را انتخاب کردید، سپاسگزاریم.\n\n"
        "🤖 **راهنمای ساخت ربات تلگرام:**\n\n"
        "1️⃣ **ساخت ربات در BotFather**\n"
        "   - به @BotFather بروید\n"
        "   - دستور `/newbot` را ارسال کنید\n"
        "   - نام و یوزرنیم انتخاب کنید\n"
        "   - توکن را کپی کنید\n\n"
        "2️⃣ **نوشتن کد ربات**\n"
        "   - فایل `bot.py` بنویسید\n"
        "   - توکن را در کد قرار دهید\n"
        "   - از `pyTelegramBotAPI` استفاده کنید\n\n"
        "3️⃣ **ارسال فایل**\n"
        "   - فایل را در همین گفتگو ارسال کنید\n"
        "   - حداکثر حجم: ۵۰ مگابایت\n\n"
        "4️⃣ **مدیریت ربات‌ها**\n"
        "   - از دکمه «ربات‌های من» لیست ربات‌ها را ببینید\n"
        "   - با دکمه «فعال/غیرفعال» ربات خود را خاموش یا روشن کنید\n"
        "   - با دکمه «حذف ربات» می‌توانید ربات را پاک کنید\n\n"
        "💡 **نکات مهم:**\n"
        "   - ربات شما به صورت ۲۴ ساعته روی سرورهای قدرتمند اجرا می‌شود\n"
        "   - در صورت قطع شدن، به صورت خودکار دوباره راه‌اندازی می‌شود\n\n"
        "📞 پشتیبانی: @shahraghee13"
    )
    
    bot.send_message(user_id, build_guide, parse_mode='Markdown')
    logger.info(f"Subscription activated for user {user_id}")

def add_wallet_balance(user_id, amount):
    user = get_user(user_id)
    if not user:
        return 0
    new_balance = user['wallet_balance'] + amount
    db.execute('UPDATE users SET wallet_balance = ? WHERE user_id = ?', (new_balance, user_id))
    cache.delete(f"user_{user_id}")
    return new_balance

def check_bot_limit(user_id):
    if not check_subscription(user_id):
        return False, 0, 0
    
    builds_today = rate_limiter.get_user_builds_today(user_id)
    max_builds = get_setting('max_builds_per_hour')
    if builds_today >= max_builds:
        return False, max_builds, builds_today
    
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
    if not bot_rec or (user_id and bot_rec['user_id'] != user_id):
        return False
    
    machine_manager.stop_bot(bot_id)
    
    if bot_rec.get('file_path') and os.path.exists(bot_rec['file_path']):
        os.remove(bot_rec['file_path'])
    
    bot_dir = os.path.join(DIRS['MACHINES'], f"machine_{bot_rec['machine_id']:03d}", bot_id)
    if os.path.exists(bot_dir):
        shutil.rmtree(bot_dir)
    
    db.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
    if user_id:
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
        match = re.search(pattern, code, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

def is_channel_bot(token):
    try:
        resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            result = data.get('result', {})
            if not result.get('is_bot', False) or result.get('type') == 'channel':
                return True, result.get('username', '')
            return False, result.get('username', '')
        return True, None
    except:
        return True, None

def add_bot(user_id, bot_id, token, name, username, file_path, pid=None, machine_id=None):
    now = datetime.now().isoformat()
    encrypted_token = db.encrypt_token(token)
    db.execute('''
        INSERT INTO bots 
        (id, user_id, token, name, username, file_path, pid, machine_id, status, created_at, last_active, join_enabled, join_block_message, health_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'running', ?, ?, 1, '🚫 سرور در حال حاضر پر است. لطفاً بعداً تلاش کنید.', 'healthy')
    ''', (bot_id, user_id, encrypted_token, name, username, file_path, pid, machine_id, now, now))
    db.execute('UPDATE users SET bots_count = bots_count + 1, total_builds = total_builds + 1, last_build_at = ? WHERE user_id = ?', (now, user_id))
    db.execute('UPDATE daily_stats SET new_bots = new_bots + 1 WHERE date = ?', (datetime.now().date().isoformat(),))
    cache.delete(f"user_{user_id}")
    return True

def log_error(error_type, message, user_id=None, bot_id=None, stack_trace=None):
    error_id = hashlib.md5(f"{time.time()}_{user_id}_{bot_id}_{secrets.token_hex(4)}".encode()).hexdigest()[:16]
    db.execute('''
        INSERT INTO errors (id, type, message, user_id, bot_id, timestamp, resolved, stack_trace)
        VALUES (?, ?, ?, ?, ?, ?, 0, ?)
    ''', (error_id, error_type, message[:500], user_id, bot_id, datetime.now().isoformat(), stack_trace))
    
    ERRORS_TOTAL.labels(type=error_type).inc()
    es_logger.log('ERROR', message, {'type': error_type, 'user_id': user_id, 'bot_id': bot_id})
    
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    db.execute('DELETE FROM errors WHERE timestamp < ?', (week_ago,))

def install_library(lib_name, chat_id, msg_id):
    try:
        process = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', lib_name, '--quiet'],
            capture_output=True,
            text=True,
            timeout=120
        )
        if process.returncode == 0:
            bot.edit_message_text(f"✅ کتابخانه {lib_name} نصب شد!", chat_id, msg_id)
            return True
        else:
            error = process.stderr[:200] if process.stderr else "خطا"
            bot.edit_message_text(f"❌ خطا: {error}", chat_id, msg_id)
            return False
    except subprocess.TimeoutExpired:
        bot.edit_message_text(f"❌ زمان نصب تمام شد!", chat_id, msg_id)
        return False
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)[:100]}", chat_id, msg_id)
        return False

# ==================== Rate Limit Decorator ====================
def rate_limit(limit_per_second=10, limit_per_minute=100, limit_per_hour=500):
    def decorator(func):
        @wraps(func)
        def wrapper(message, *args, **kwargs):
            user_id = message.from_user.id
            if not rate_limiter.is_allowed(user_id, limit_per_second, limit_per_minute, limit_per_hour):
                bot.reply_to(message, "🚫 لطفاً کمی صبر کنید...")
                return
            return func(message, *args, **kwargs)
        return wrapper
    return decorator

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
        types.KeyboardButton('📦 کتابخانه'),
        types.KeyboardButton('📊 آمار'),
        types.KeyboardButton('📞 پشتیبانی'),
        types.KeyboardButton('⚡ وضعیت صف'),
        types.KeyboardButton('📈 مصرف من')
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
    username = message.from_user.username or ""
    
    referred_by = None
    args = message.text.split()
    if len(args) > 1:
        code = args[1]
        users = db.execute('SELECT user_id FROM users WHERE referral_code = ?', (code,))
        if users and users[0]['user_id'] != user_id:
            referred_by = users[0]['user_id']
            bot.send_message(referred_by, f"🎉 {first_name} با لینک شما وارد شد!")
    
    create_user(user_id, username, first_name, message.from_user.last_name or "", referred_by)
    user = get_user(user_id)
    referral_link = f"https://t.me/{BOT_USERNAME}?start={user['referral_code']}"
    
    text = (f"🚀 خوش آمدید {first_name}!\n\n"
            f"👤 شناسه: `{user_id}`\n"
            f"🎁 کد معرف: `{user['referral_code']}`\n"
            f"🔗 لینک دعوت: `{referral_link}`\n"
            f"📊 دعوت‌ها: {user['referrals_count']}\n"
            f"💰 موجودی: {user['wallet_balance']:,} تومان")
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📋 کپی لینک", callback_data=f"copy_link_{user['referral_code']}"))
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=get_main_menu(user_id in ADMIN_IDS))

@bot.callback_query_handler(func=lambda call: call.data.startswith('copy_link_'))
def copy_link_callback(call):
    code = call.data.replace('copy_link_', '')
    link = f"https://t.me/{BOT_USERNAME}?start={code}"
    bot.answer_callback_query(call.id, f"✅ لینک کپی شد!\n{link}", show_alert=True)

# ==================== مصرف من ====================
@bot.message_handler(func=lambda m: m.text == '📈 مصرف من')
@rate_limit(5)
def my_usage(message):
    user_id = message.from_user.id
    builds_today = rate_limiter.get_user_builds_today(user_id)
    max_builds = get_setting('max_builds_per_hour')
    bots_count = len(get_user_bots(user_id))
    
    bar_length = int((builds_today / max_builds) * 20) if max_builds > 0 else 0
    bar = "█" * bar_length + "░" * (20 - bar_length)
    
    text = (f"📊 **مصرف شما امروز**\n\n"
            f"🤖 ساخت ربات: {builds_today}/{max_builds}\n"
            f"📈 {bar} {int((builds_today/max_builds)*100) if max_builds>0 else 0}%\n\n"
            f"📋 تعداد ربات‌های شما: {bots_count}\n"
            f"💾 فضای اشغالی: ~{bots_count * 2} MB")
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== کیف پول ====================
@bot.message_handler(func=lambda m: m.text == '💰 کیف پول و اشتراک')
@rate_limit(3)
def wallet(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        bot.send_message(message.chat.id, "❌ /start بزنید")
        return
    
    is_subscribed = check_subscription(user_id)
    expiry = datetime.fromisoformat(user['subscription_expiry']).strftime('%Y-%m-%d') if user['subscription_expiry'] else "ندارد"
    
    text = (f"💰 **کیف پول و اشتراک**\n\n"
            f"👤 {user['first_name']}\n"
            f"💳 وضعیت: {'✅ فعال' if is_subscribed else '❌ غیرفعال'}\n"
            f"📅 انقضا: {expiry}\n"
            f"💰 موجودی: {user['wallet_balance']:,} تومان\n"
            f"👥 دعوت‌ها: {user['referrals_count']}")
    
    if not is_subscribed:
        text += (f"\n\n💳 برای فعالسازی {get_setting('subscription_price_str')} را به کارت زیر واریز:\n"
                f"`{get_setting('card_number_display')}`\n"
                f"👤 {get_setting('card_holder')}\n"
                f"🏦 {get_setting('card_bank')}")
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

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
        
        db.execute('INSERT INTO receipts (user_id, amount, receipt_path, payment_code, created_at) VALUES (?, ?, ?, ?, ?)',
                  (user_id, get_setting('subscription_price'), receipt_path, payment_code, datetime.now().isoformat()))
        
        bot.reply_to(message, f"✅ فیش دریافت شد\n💰 {get_setting('subscription_price_str')}\n🆔 {payment_code}")
        
        for admin_id in ADMIN_IDS:
            try:
                with open(receipt_path, 'rb') as f:
                    bot.send_photo(admin_id, f, caption=f"📸 فیش جدید\n👤 {message.from_user.first_name}\n🆔 {user_id}\n💰 {get_setting('subscription_price_str')}")
            except:
                pass
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")
        log_error("receipt_error", str(e), user_id)

# ==================== دعوت دوستان ====================
@bot.message_handler(func=lambda m: m.text == '👥 دعوت دوستان')
@rate_limit(3)
def invite(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    referral_link = f"https://t.me/{BOT_USERNAME}?start={user['referral_code']}"
    
    text = (f"👥 **سیستم دعوت دوستان**\n\n"
            f"🎁 کد معرف: `{user['referral_code']}`\n"
            f"🔗 لینک: `{referral_link}`\n"
            f"📊 دعوت‌ها: {user['referrals_count']}\n"
            f"💰 کمیسیون هر دعوت: {get_setting('withdraw_percent')}%")
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📋 کپی لینک", callback_data=f"copy_link_{user['referral_code']}"))
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

# ==================== درخواست برداشت ====================
@bot.message_handler(func=lambda m: m.text == '💸 درخواست برداشت')
@rate_limit(2)
def withdraw_request(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if user['wallet_balance'] < get_setting('min_withdraw'):
        bot.send_message(message.chat.id, f"❌ موجودی {user['wallet_balance']:,} کمتر از حداقل {get_setting('min_withdraw'):,} است")
        return
    
    msg = bot.send_message(message.chat.id, "💳 شماره کارت:")
    bot.register_next_step_handler(msg, process_withdraw_card, user)

def process_withdraw_card(message, user):
    card_number = message.text.strip()
    msg = bot.send_message(message.chat.id, "👤 نام صاحب کارت:")
    bot.register_next_step_handler(msg, process_withdraw_holder, user, card_number)

def process_withdraw_holder(message, user, card_number):
    card_holder = message.text.strip()
    amount = user['wallet_balance']
    db.execute('INSERT INTO withdraw_requests (user_id, amount, card_number, card_holder, created_at, status) VALUES (?, ?, ?, ?, ?, "pending")',
              (user['user_id'], amount, card_number, card_holder, datetime.now().isoformat()))
    db.execute('UPDATE users SET wallet_balance = 0 WHERE user_id = ?', (user['user_id'],))
    cache.delete(f"user_{user['user_id']}")
    
    bot.send_message(message.chat.id, f"✅ درخواست {amount:,} تومان ثبت شد")
    
    for admin_id in ADMIN_IDS:
        bot.send_message(admin_id, f"💰 درخواست برداشت\n👤 {user['first_name']}\n🆔 {user['user_id']}\n💰 {amount:,} تومان")

# ==================== وضعیت صف ====================
@bot.message_handler(func=lambda m: m.text == '⚡ وضعیت صف')
@rate_limit(5)
def queue_status(message):
    queue_len = build_queue.get_queue_length()
    max_concurrent = get_setting('max_concurrent_builds')
    
    text = (f"⚡ **وضعیت صف ساخت ربات**\n\n"
            f"📊 در صف: {queue_len}\n"
            f"⚙️ حداکثر همزمان: {max_concurrent}\n"
            f"📈 ساخت امروز شما: {rate_limiter.get_user_builds_today(message.from_user.id)}/{get_setting('max_builds_per_hour')}")
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== ساخت ربات جدید ====================
@bot.message_handler(func=lambda m: m.text == '🤖 ساخت ربات جدید')
@rate_limit(3)
def new_bot(message):
    user_id = message.from_user.id
    
    if not check_subscription(user_id):
        guide_text = (
            "🚫 **اشتراک شما فعال نیست**\n\n"
            "برای ساخت ربات، ابتدا باید اشتراک خود را فعال کنید:\n\n"
            "💳 **مبلغ اشتراک:** {price}\n"
            "🏦 **شماره کارت:** `{card}`\n"
            "👤 **نام صاحب کارت:** {holder}\n"
            "🏛 **بانک:** {bank}\n\n"
            "📸 **مراحل پرداخت و فعال‌سازی:**\n"
            "1️⃣ مبلغ {price} را به کارت فوق واریز کنید\n"
            "2️⃣ رسید پرداخت (تصویر) را در همین گفتگو ارسال کنید\n"
            "3️⃣ پس از تایید توسط پشتیبان، اشتراک شما فعال می‌شود\n"
            "4️⃣ پس از فعال‌سازی، مجدداً روی دکمه «ساخت ربات جدید» کلیک کنید\n\n"
            "⏱ **زمان تایید:** معمولاً کمتر از ۲۴ ساعت\n"
            "📞 **پشتیبانی:** @shahraghee13"
        ).format(
            price=get_setting('subscription_price_str'),
            card=get_setting('card_number_display'),
            holder=get_setting('card_holder'),
            bank=get_setting('card_bank')
        )
        bot.send_message(message.chat.id, guide_text, parse_mode='Markdown')
        return
    
    can_create, max_bots, current_bots = check_bot_limit(user_id)
    if not can_create:
        limit = get_setting('max_builds_per_hour')
        bot.send_message(message.chat.id, f"❌ به حد مجاز {limit} ربات در ساعت رسیده‌اید")
        return
    
    bot.send_message(message.chat.id, "📤 فایل `.py` یا `.zip` ربات خود را ارسال کنید")

# ==================== آپلود فایل ====================
@bot.message_handler(content_types=['document'])
def handle_build_file(message):
    user_id = message.from_user.id
    
    if not check_subscription(user_id):
        bot.reply_to(message, "❌ اشتراک فعال نیست")
        return
    
    file_name = message.document.file_name
    if not (file_name.endswith('.py') or file_name.endswith('.zip')):
        bot.reply_to(message, "❌ فقط .py یا .zip")
        return
    
    if message.document.file_size > 50 * 1024 * 1024:
        bot.reply_to(message, "❌ حجم بیشتر از ۵۰ مگابایت")
        return
    
    status_msg = bot.reply_to(message, "🔄 در حال بررسی...")
    
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
            bot.edit_message_text("❌ فایل پایتون پیدا نشد", message.chat.id, status_msg.message_id)
            return
        
        token = extract_token_from_code(main_code)
        if not token:
            bot.edit_message_text("❌ توکن پیدا نشد", message.chat.id, status_msg.message_id)
            return
        
        is_channel, _ = is_channel_bot(token)
        if is_channel:
            bot.edit_message_text("❌ توکن کانال است!", message.chat.id, status_msg.message_id)
            return
        
        resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        if resp.status_code != 200:
            bot.edit_message_text("❌ توکن نامعتبر", message.chat.id, status_msg.message_id)
            return
        
        bot_info = resp.json()['result']
        
        rate_limiter.increment_user_builds(user_id)
        
        bot_id = hashlib.md5(f"{user_id}{token}{time.time()}".encode()).hexdigest()[:16]
        
        queue_len = build_queue.get_queue_length()
        QUEUE_SIZE.set(queue_len)
        bot.edit_message_text(f"🔄 اضافه شد به صف...\n📍 موقعیت: {queue_len + 1}", message.chat.id, status_msg.message_id)
        
        build_data = {
            'bot_id': bot_id,
            'user_id': user_id,
            'token': token,
            'bot_info': bot_info,
            'file_path': file_path,
            'main_code': main_code,
            'chat_id': message.chat.id,
            'message_id': status_msg.message_id
        }
        
        # اضافه به صف Redis
        build_queue.add_build(user_id, file_path, file_name, message.chat.id, status_msg.message_id, build_data)
        
        # ارسال به Celery
        build_bot_task.delay(build_data)
        
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)[:100]}", message.chat.id, status_msg.message_id)
        log_error("build_error", str(e), user_id)
        capture_exception(e)

# ==================== ربات‌های من ====================
@bot.message_handler(func=lambda m: m.text == '📋 ربات‌های من')
@rate_limit(5)
def my_bots(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    if not bots:
        bot.send_message(message.chat.id, "📋 رباتی ندارید")
        return
    for b in bots[:10]:
        status = machine_manager.get_status(b['id'])
        emoji = "🟢" if status.get('running') else "🔴"
        bot.send_message(message.chat.id, f"{emoji} {b['name']}\n🔗 t.me/{b['username']}")

# ==================== فعال/غیرفعال ====================
@bot.message_handler(func=lambda m: m.text == '🔄 فعال/غیرفعال')
@rate_limit(3)
def toggle_prompt(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    if not bots:
        bot.send_message(message.chat.id, "📋 رباتی ندارید")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        status = machine_manager.get_status(b['id'])
        emoji = "🟢" if status.get('running') else "🔴"
        markup.add(types.InlineKeyboardButton(f"{emoji} {b['name']}", callback_data=f"toggle_{b['id']}"))
    bot.send_message(message.chat.id, "🔄 انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_'))
def toggle_bot(call):
    bot_id = call.data.replace('toggle_', '')
    bot_rec = get_bot(bot_id)
    if not bot_rec or bot_rec['user_id'] != call.from_user.id:
        bot.answer_callback_query(call.id, "❌ یافت نشد")
        return
    status = machine_manager.get_status(bot_id)
    if status.get('running'):
        if machine_manager.stop_bot(bot_id):
            bot.answer_callback_query(call.id, "✅ متوقف شد")
        else:
            bot.answer_callback_query(call.id, "❌ خطا")
    else:
        if os.path.exists(bot_rec['file_path']):
            with open(bot_rec['file_path'], 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
            token = db.decrypt_token(bot_rec['token'])
            result = machine_manager.run_bot(bot_id, code, token)
            if result['success']:
                db.execute("UPDATE bots SET machine_id = ?, pid = ? WHERE id = ?", (result['machine_id'], result['pid'], bot_id))
                bot.answer_callback_query(call.id, "✅ فعال شد")
            else:
                bot.answer_callback_query(call.id, f"❌ {result.get('error')}")
        else:
            bot.answer_callback_query(call.id, "❌ فایل یافت نشد")

# ==================== حذف ربات ====================
@bot.message_handler(func=lambda m: m.text == '🗑 حذف ربات')
@rate_limit(3)
def delete_prompt(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
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
    markup.add(types.InlineKeyboardButton("✅ بله", callback_data=f"confirm_del_{bot_id}"), types.InlineKeyboardButton("❌ انصراف", callback_data="cancel_del"))
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

# ==================== کتابخانه ====================
@bot.message_handler(func=lambda m: m.text == '📦 کتابخانه')
@rate_limit(3)
def library_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    for name, lib in list(POPULAR_LIBRARIES.items())[:20]:
        markup.add(types.InlineKeyboardButton(f"📦 {name}", callback_data=f"lib_{lib}"))
    markup.add(types.InlineKeyboardButton("🔧 نصب دستی", callback_data="lib_manual"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="lib_back"))
    bot.reply_to(message, "📦 کتابخانه مورد نظر:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "lib_manual")
def library_manual(call):
    msg = bot.send_message(call.message.chat.id, "🔧 نام کتابخانه:")
    bot.register_next_step_handler(msg, install_custom_library)
    bot.answer_callback_query(call.id)

def install_custom_library(message):
    lib = message.text.strip()
    if not lib:
        bot.reply_to(message, "❌ نام کتابخانه")
        return
    status = bot.reply_to(message, f"🔄 نصب {lib}...")
    install_library(lib, message.chat.id, status.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lib_') and call.data not in ['lib_manual', 'lib_back'])
def install_selected_library(call):
    lib = call.data.replace('lib_', '')
    status = bot.send_message(call.message.chat.id, f"🔄 نصب {lib}...")
    install_library(lib, call.message.chat.id, status.message_id)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "lib_back")
def library_back(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "🚀 منوی اصلی:", reply_markup=get_main_menu(call.from_user.id in ADMIN_IDS))

# ==================== راهنما ====================
@bot.message_handler(func=lambda m: m.text == '📚 راهنما')
@rate_limit(3)
def guide(message):
    bot.send_message(message.chat.id, get_setting('guide_text'))

# ==================== آمار ====================
@bot.message_handler(func=lambda m: m.text == '📊 آمار')
@rate_limit(3)
def stats(message):
    users = db.execute('SELECT COUNT(*) as count FROM users')[0]['count']
    active_subs = db.execute('SELECT COUNT(*) as count FROM users WHERE subscription_status = "active"')[0]['count']
    bots = db.execute('SELECT COUNT(*) as count FROM bots')[0]['count']
    running = db.execute('SELECT COUNT(*) as count FROM bots WHERE status = "running"')[0]['count']
    total_wallet = db.execute('SELECT SUM(wallet_balance) as total FROM users')[0]['total'] or 0
    machine_stats = machine_manager.get_stats()
    queue_len = build_queue.get_queue_length()
    scaling_rec = auto_scaler.get_scaling_recommendation()
    
    text = (f"📊 **آمار سیستم**\n\n"
            f"👥 کاربران: {users:,}\n"
            f"✅ اشتراک فعال: {active_subs:,}\n"
            f"🤖 کل ربات‌ها: {bots:,}\n"
            f"🟢 ربات فعال: {running:,}\n"
            f"💰 کیف پول کل: {total_wallet:,} تومان\n"
            f"🖥️ ظرفیت: {machine_stats['available']:,} خالی از {machine_stats['total_capacity']:,}\n"
            f"📊 مصرف: {machine_stats['usage_percent']:.1f}%\n"
            f"⚡ صف ساخت: {queue_len}\n"
            f"{scaling_rec}")
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== پشتیبانی ====================
@bot.message_handler(func=lambda m: m.text == '📞 پشتیبانی')
@rate_limit(3)
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
        types.InlineKeyboardButton("⏹ توقف عضوگیری", callback_data="admin_stop_bot_join"),
        types.InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings"),
        types.InlineKeyboardButton("🔧 خطاها", callback_data="admin_errors"),
        types.InlineKeyboardButton("📊 گزارش", callback_data="admin_report"),
        types.InlineKeyboardButton("🖥️ مدیریت ماشین", callback_data="admin_machines"),
        types.InlineKeyboardButton("⚡ تنظیمات مقیاس", callback_data="admin_scale_settings"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    bot.send_message(message.chat.id, "👑 پنل مدیریت:", reply_markup=markup)

# ==================== مدیریت ماشین‌ها ====================
@bot.callback_query_handler(func=lambda call: call.data == "admin_machines")
def admin_machines(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    machines = db.execute("SELECT * FROM machines ORDER BY id")
    text = "🖥️ **وضعیت ماشین‌ها**\n\n"
    for m in machines[:20]:
        usage = (m['current_bots'] / m['max_bots']) * 100 if m['max_bots'] > 0 else 0
        status_emoji = "🟢" if m['status'] == 'active' else "🔴"
        text += f"{status_emoji} {m['name']}: {m['current_bots']}/{m['max_bots']} ({usage:.1f}%)\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "admin_scale_settings")
def admin_scale_settings(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📈 تغییر آستانه خودکار", callback_data="admin_set_threshold"),
        types.InlineKeyboardButton("⚙️ تغییر حداکثر همزمانی", callback_data="admin_set_concurrent"),
        types.InlineKeyboardButton("⏱️ تغییر فاصله چک سلامت", callback_data="admin_set_health_interval"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    bot.send_message(call.message.chat.id, "⚡ تنظیمات مقیاس:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_threshold")
def admin_set_threshold(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "📈 آستانه خودکار (درصد، مثال: 80):")
    bot.register_next_step_handler(msg, process_set_threshold)

def process_set_threshold(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        threshold = int(message.text.strip())
        if 30 <= threshold <= 95:
            update_setting('auto_scale_threshold', threshold)
            bot.reply_to(message, f"✅ آستانه به {threshold}% تغییر کرد")
        else:
            bot.reply_to(message, "❌ عدد بین 30 تا 95")
    except:
        bot.reply_to(message, "❌ عدد معتبر")

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_concurrent")
def admin_set_concurrent(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "⚙️ حداکثر ساخت همزمان (مثال: 20):")
    bot.register_next_step_handler(msg, process_set_concurrent)

def process_set_concurrent(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        concurrent = int(message.text.strip())
        if 1 <= concurrent <= 100:
            update_setting('max_concurrent_builds', concurrent)
            bot.reply_to(message, f"✅ حداکثر همزمانی به {concurrent} تغییر کرد")
        else:
            bot.reply_to(message, "❌ عدد بین 1 تا 100")
    except:
        bot.reply_to(message, "❌ عدد معتبر")

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_health_interval")
def admin_set_health_interval(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "⏱️ فاصله چک سلامت (ثانیه، مثال: 30):")
    bot.register_next_step_handler(msg, process_set_health_interval)

def process_set_health_interval(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        interval = int(message.text.strip())
        if 10 <= interval <= 300:
            update_setting('health_check_interval', interval)
            bot.reply_to(message, f"✅ فاصله چک به {interval} ثانیه تغییر کرد")
        else:
            bot.reply_to(message, "❌ عدد بین 10 تا 300")
    except:
        bot.reply_to(message, "❌ عدد معتبر")

# ==================== سایر کال‌بک‌های مدیریت ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_receipts")
def admin_receipts(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    receipts = db.execute('SELECT * FROM receipts WHERE status = "pending" ORDER BY created_at')
    if not receipts:
        bot.send_message(call.message.chat.id, "📸 فیشی وجود ندارد")
        return
    for r in receipts:
        user = get_user(r['user_id'])
        text = f"📸 فیش\n👤 {user['first_name'] if user else 'نامشخص'}\n💰 {r['amount']:,} تومان\n🆔 {r['payment_code']}"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_receipt_{r['id']}"),
                  types.InlineKeyboardButton("❌ رد", callback_data=f"reject_receipt_{r['id']}"))
        if os.path.exists(r['receipt_path']):
            with open(r['receipt_path'], 'rb') as f:
                bot.send_photo(call.message.chat.id, f, caption=text, reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_receipt_'))
def approve_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    rid = int(call.data.replace('approve_receipt_', ''))
    r = db.execute('SELECT user_id FROM receipts WHERE id = ?', (rid,))
    if r:
        db.execute('UPDATE receipts SET status = "approved", reviewed_by = ?, reviewed_at = ? WHERE id = ?',
                  (call.from_user.id, datetime.now().isoformat(), rid))
        activate_subscription(r[0]['user_id'])
        bot.answer_callback_query(call.id, "✅ اشتراک فعال شد و راهنما ارسال گردید")
        bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_receipt_'))
def reject_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    rid = int(call.data.replace('reject_receipt_', ''))
    db.execute('UPDATE receipts SET status = "rejected", reviewed_by = ?, reviewed_at = ? WHERE id = ?',
              (call.from_user.id, datetime.now().isoformat(), rid))
    bot.answer_callback_query(call.id, "❌ رد شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_withdraws")
def admin_withdraws(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    withdraws = db.execute('SELECT * FROM withdraw_requests WHERE status = "pending" ORDER BY created_at')
    if not withdraws:
        bot.send_message(call.message.chat.id, "💰 درخواستی وجود ندارد")
        return
    for w in withdraws:
        user = get_user(w['user_id'])
        text = f"💰 برداشت\n👤 {user['first_name'] if user else 'نامشخص'}\n💰 {w['amount']:,} تومان\n💳 {w['card_number']}"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_withdraw_{w['id']}"))
        bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_withdraw_'))
def approve_withdraw(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    wid = int(call.data.replace('approve_withdraw_', ''))
    db.execute('UPDATE withdraw_requests SET status = "approved", processed_at = ? WHERE id = ?',
              (datetime.now().isoformat(), wid))
    bot.answer_callback_query(call.id, "✅ تایید شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_users")
def admin_users(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🔍 جستجو", callback_data="admin_search_user"),
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
    msg = bot.send_message(call.message.chat.id, "🔍 آیدی کاربر:")
    bot.register_next_step_handler(msg, process_admin_search)

def process_admin_search(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        uid = int(message.text.strip())
        user = get_user(uid)
        if user:
            bots = db.execute('SELECT COUNT(*) as count FROM bots WHERE user_id = ?', (uid,))
            text = (f"👤 {user['first_name']}\n🆔 {user['user_id']}\n💰 موجودی: {user['wallet_balance']:,}\n"
                   f"✅ اشتراک: {'فعال' if user['subscription_status'] == 'active' else 'غیرفعال'}\n"
                   f"🤖 ربات: {bots[0]['count']}\n📊 ساخت امروز: {rate_limiter.get_user_builds_today(uid)}")
            bot.reply_to(message, text)
        else:
            bot.reply_to(message, "❌ یافت نشد")
    except:
        bot.reply_to(message, "❌ نامعتبر")

@bot.callback_query_handler(func=lambda call: call.data == "admin_delete_user")
def admin_delete_user(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "🗑 آیدی کاربر:")
    bot.register_next_step_handler(msg, process_admin_delete)

def process_admin_delete(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        uid = int(message.text.strip())
        for bot_rec in db.execute('SELECT id FROM bots WHERE user_id = ?', (uid,)):
            machine_manager.stop_bot(bot_rec['id'])
        db.execute('DELETE FROM users WHERE user_id = ?', (uid,))
        bot.reply_to(message, f"✅ کاربر {uid} حذف شد")
    except:
        bot.reply_to(message, "❌ خطا")

@bot.callback_query_handler(func=lambda call: call.data == "admin_add_balance")
def admin_add_balance(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "💰 آیدی و مبلغ (مثال: 123456 100000):")
    bot.register_next_step_handler(msg, process_add_balance)

def process_add_balance(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        parts = message.text.strip().split()
        uid = int(parts[0])
        amount = int(parts[1])
        add_wallet_balance(uid, amount)
        bot.reply_to(message, f"✅ {amount:,} تومان اضافه شد")
        bot.send_message(uid, f"💰 {amount:,} تومان به کیف پول شما اضافه شد")
    except:
        bot.reply_to(message, "❌ فرمت نامعتبر")

@bot.callback_query_handler(func=lambda call: call.data == "admin_activate_sub")
def admin_activate_sub(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "🎁 آیدی کاربر:")
    bot.register_next_step_handler(msg, process_activate_sub)

def process_activate_sub(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        uid = int(message.text.strip())
        activate_subscription(uid)
        bot.reply_to(message, f"✅ اشتراک {uid} فعال شد")
    except:
        bot.reply_to(message, "❌ خطا")

@bot.callback_query_handler(func=lambda call: call.data == "admin_bots")
def admin_bots(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📋 لیست ربات‌ها", callback_data="admin_list_bots"),
        types.InlineKeyboardButton("🗑 حذف ربات", callback_data="admin_delete_bot"),
        types.InlineKeyboardButton("🔄 ریستارت", callback_data="admin_fix_bot"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    bot.send_message(call.message.chat.id, "🤖 مدیریت ربات‌ها:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_stop_bot_join")
def admin_stop_bot_join(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    bots = db.execute('SELECT id, name, username, join_enabled FROM bots WHERE status = "running"')
    if not bots:
        bot.send_message(call.message.chat.id, "❌ ربات فعالی وجود ندارد")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        status_emoji = "🟢" if b['join_enabled'] == 1 else "🔴"
        markup.add(types.InlineKeyboardButton(f"{status_emoji} {b['name']}", callback_data=f"toggle_join_{b['id']}"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back"))
    bot.send_message(call.message.chat.id, "⏹ انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_join_'))
def toggle_join(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    bot_id = call.data.replace('toggle_join_', '')
    current = db.execute('SELECT join_enabled, name FROM bots WHERE id = ?', (bot_id,))
    if not current:
        bot.answer_callback_query(call.id, "❌ یافت نشد")
        return
    is_enabled = current[0]['join_enabled']
    bot_name = current[0]['name']
    if is_enabled == 1:
        msg = bot.send_message(call.message.chat.id, f"📝 پیام مسدودیت برای {bot_name}:")
        bot.register_next_step_handler(msg, lambda m: save_block_message(m, bot_id, call))
        bot.answer_callback_query(call.id)
    else:
        db.execute('UPDATE bots SET join_enabled = 1 WHERE id = ?', (bot_id,))
        bot.answer_callback_query(call.id, f"✅ عضوگیری {bot_name} فعال شد")
        bot.send_message(call.message.chat.id, f"✅ عضوگیری {bot_name} فعال شد")

def save_block_message(message, bot_id, original_call):
    if message.from_user.id not in ADMIN_IDS:
        return
    block_text = message.text.strip() or "🚫 سرور در حال حاضر پر است"
    bot_info = db.execute('SELECT name FROM bots WHERE id = ?', (bot_id,))
    bot_name = bot_info[0]['name'] if bot_info else "ربات"
    db.execute('UPDATE bots SET join_enabled = 0, join_block_message = ? WHERE id = ?', (block_text, bot_id))
    bot.send_message(message.chat.id, f"✅ عضوگیری {bot_name} متوقف شد\n📨 پیام: {block_text}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_list_bots")
def admin_list_bots(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    bots = db.execute('SELECT * FROM bots ORDER BY created_at DESC LIMIT 50')
    if not bots:
        bot.send_message(call.message.chat.id, "📋 رباتی وجود ندارد")
        return
    for b in bots:
        join_status = "🟢 فعال" if b['join_enabled'] == 1 else "🔴 غیرفعال"
        text = f"🤖 {b['name']}\n🆔 {b['id']}\n👤 کاربر: {b['user_id']}\n👥 عضوگیری: {join_status}"
        bot.send_message(call.message.chat.id, text)

@bot.callback_query_handler(func=lambda call: call.data == "admin_delete_bot")
def admin_delete_bot(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "🗑 آیدی ربات:")
    bot.register_next_step_handler(msg, process_admin_delete_bot)

def process_admin_delete_bot(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    bot_id = message.text.strip()
    if delete_bot(bot_id, None):
        bot.reply_to(message, f"✅ ربات {bot_id} حذف شد")
    else:
        bot.reply_to(message, "❌ یافت نشد")

@bot.callback_query_handler(func=lambda call: call.data == "admin_fix_bot")
def admin_fix_bot(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "🔧 آیدی ربات:")
    bot.register_next_step_handler(msg, process_fix_bot)

def process_fix_bot(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    bot_id = message.text.strip()
    bot_rec = get_bot(bot_id)
    if not bot_rec:
        bot.reply_to(message, "❌ یافت نشد")
        return
    machine_manager.stop_bot(bot_id)
    time.sleep(1)
    if os.path.exists(bot_rec['file_path']):
        with open(bot_rec['file_path'], 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()
        token = db.decrypt_token(bot_rec['token'])
        result = machine_manager.run_bot(bot_id, code, token)
        if result['success']:
            db.execute("UPDATE bots SET machine_id = ?, pid = ?, status = 'running' WHERE id = ?",
                      (result['machine_id'], result['pid'], bot_id))
            bot.reply_to(message, f"✅ {bot_id} ریستارت شد")
        else:
            bot.reply_to(message, f"❌ {result.get('error')}")
    else:
        bot.reply_to(message, "❌ فایل یافت نشد")

@bot.callback_query_handler(func=lambda call: call.data == "admin_settings")
def admin_settings(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("💳 کارت", callback_data="admin_set_card"),
        types.InlineKeyboardButton("💰 قیمت اشتراک", callback_data="admin_set_price"),
        types.InlineKeyboardButton("📝 راهنما", callback_data="admin_set_guide"),
        types.InlineKeyboardButton("📈 محدودیت ساخت", callback_data="admin_set_build_limit"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    bot.send_message(call.message.chat.id, "⚙️ تنظیمات:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_build_limit")
def admin_set_build_limit(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "📈 حداکثر ساخت در ساعت (مثال: 10):")
    bot.register_next_step_handler(msg, process_set_build_limit)

def process_set_build_limit(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        limit = int(message.text.strip())
        if 1 <= limit <= 500:
            update_setting('max_builds_per_hour', limit)
            bot.reply_to(message, f"✅ محدودیت به {limit} ربات در ساعت تغییر کرد")
        else:
            bot.reply_to(message, "❌ عدد بین 1 تا 500")
    except:
        bot.reply_to(message, "❌ عدد معتبر")

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_card")
def admin_set_card(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "💳 شماره کارت:")
    bot.register_next_step_handler(msg, process_set_card)

def process_set_card(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    card = message.text.strip()
    update_setting('card_number', card)
    display = ' '.join([card[i:i+4] for i in range(0, len(card), 4)])
    update_setting('card_number_display', display)
    bot.reply_to(message, f"✅ {display}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_price")
def admin_set_price(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "💰 قیمت (تومان):")
    bot.register_next_step_handler(msg, process_set_price)

def process_set_price(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        price = int(message.text.strip())
        update_setting('subscription_price', price)
        update_setting('subscription_price_str', f"{price:,} تومان")
        bot.reply_to(message, f"✅ {price:,} تومان")
    except:
        bot.reply_to(message, "❌ عدد")

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_guide")
def admin_set_guide(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "📝 متن راهنما:")
    bot.register_next_step_handler(msg, process_set_guide)

def process_set_guide(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    update_setting('guide_text', message.text.strip())
    bot.reply_to(message, "✅ ذخیره شد")

@bot.callback_query_handler(func=lambda call: call.data == "admin_errors")
def admin_errors(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    errors = db.execute('SELECT * FROM errors WHERE resolved = 0 ORDER BY timestamp DESC LIMIT 20')
    if not errors:
        bot.send_message(call.message.chat.id, "✅ خطایی وجود ندارد")
        return
    for e in errors:
        text = f"⚠️ {e['type']}\n📝 {e['message'][:100]}\n🕐 {e['timestamp'][:16]}"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ رفع شد", callback_data=f"resolve_error_{e['id']}"))
        bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('resolve_error_'))
def resolve_error(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    eid = call.data.replace('resolve_error_', '')
    db.execute('UPDATE errors SET resolved = 1 WHERE id = ?', (eid,))
    bot.answer_callback_query(call.id, "✅ ثبت شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_report")
def admin_report(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    users = db.execute('SELECT COUNT(*) as count FROM users')[0]['count']
    active = db.execute('SELECT COUNT(*) as count FROM users WHERE subscription_status = "active"')[0]['count']
    bots = db.execute('SELECT COUNT(*) as count FROM bots')[0]['count']
    running = db.execute('SELECT COUNT(*) as count FROM bots WHERE status = "running"')[0]['count']
    total_wallet = db.execute('SELECT SUM(wallet_balance) as total FROM users')[0]['total'] or 0
    machine_stats = machine_manager.get_stats()
    
    today = datetime.now().date().isoformat()
    daily = db.execute('SELECT * FROM daily_stats WHERE date = ?', (today,))
    if daily:
        d = daily[0]
        daily_text = f"\n📅 امروز: {d['new_users']} کاربر جدید، {d['new_bots']} ربات جدید"
    else:
        daily_text = ""
    
    text = (f"📊 **گزارش کامل**\n\n"
            f"👥 کاربران: {users}\n"
            f"✅ اشتراک فعال: {active}\n"
            f"🤖 کل ربات‌ها: {bots}\n"
            f"🟢 ربات فعال: {running}\n"
            f"💰 کیف پول کل: {total_wallet:,} تومان\n"
            f"🖥️ ظرفیت: {machine_stats['available']} خالی\n"
            f"⚡ مصرف: {machine_stats['usage_percent']:.1f}%{daily_text}")
    
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

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
    text = message.text
    users = db.execute("SELECT user_id FROM users WHERE is_banned = 0")
    sent = 0
    for user in users:
        try:
            bot.send_message(user['user_id'], text)
            sent += 1
            time.sleep(0.05)
        except:
            pass
    bot.reply_to(message, f"✅ به {sent} کاربر ارسال شد")

# ==================== مانیتورینگ ====================
def monitor_system():
    while True:
        try:
            for user in db.execute('SELECT user_id, subscription_expiry, subscription_status, warning_sent FROM users WHERE subscription_status = "active"'):
                if user['subscription_expiry']:
                    expiry = datetime.fromisoformat(user['subscription_expiry'])
                    if expiry < datetime.now():
                        db.execute('UPDATE users SET subscription_status = "inactive", warning_sent = 0 WHERE user_id = ?', (user['user_id'],))
                        bot.send_message(user['user_id'], f"⚠️ اشتراک شما منقضی شد!\n💰 {get_setting('subscription_price_str')}")
            
            today = datetime.now().date().isoformat()
            db.execute('INSERT OR IGNORE INTO daily_stats (date, new_users, new_bots, new_subscriptions, total_revenue) VALUES (?, 0, 0, 0, 0)', (today,))
            
            # آپدیت متریک‌ها
            USERS_TOTAL.set(db.execute('SELECT COUNT(*) as count FROM users')[0]['count'])
            SUBSCRIPTIONS_ACTIVE.set(db.execute('SELECT COUNT(*) as count FROM users WHERE subscription_status = "active"')[0]['count'])
            BOTS_TOTAL.set(db.execute('SELECT COUNT(*) as count FROM bots')[0]['count'])
            
            time.sleep(60)
        except Exception as e:
            logger.error(f"Monitor error: {e}")
            time.sleep(60)

threading.Thread(target=monitor_system, daemon=True).start()

# ==================== اجرا ====================
if __name__ == "__main__":
    print("=" * 80)
    print("🚀 ربات مادر نهایی - نسخه 100.0 Enterprise Mega Scale".center(80))
    print("=" * 80)
    print(f"👑 ادمین‌ها: {ADMIN_IDS}")
    print(f"🤖 نام ربات: @{BOT_USERNAME}")
    print(f"💾 Redis: {REDIS_HOST}:{REDIS_PORT}")
    print(f"📊 Prometheus Metrics: /metrics")
    print(f"❤️ Health Check: /health")
    print(f"🔐 رمزنگاری: فعال")
    print(f"📦 Celery: {REDIS_URL}")
    print(f"☁️ S3 Backup: {'فعال' if AWS_ACCESS_KEY else 'غیرفعال'}")
    print(f"📈 Elasticsearch: {ELASTICSEARCH_HOST}")
    print("=" * 80)
    
    # راه‌اندازی Flask server در یک ترد جداگانه
    def run_flask():
        flask_app.run(host='0.0.0.0', port=5000, threaded=True)
    
    threading.Thread(target=run_flask, daemon=True).start()
    
    # راه‌اندازی Webhook یا Polling
    if WEBHOOK_URL:
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
        print(f"✅ Webhook set to {WEBHOOK_URL}/webhook")
    else:
        print("⚠️ Running with polling mode")
        while True:
            try:
                bot.infinity_polling(timeout=60)
            except Exception as e:
                logger.error(f"Polling error: {e}")
                time.sleep(5)